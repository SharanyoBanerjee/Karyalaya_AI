"""
FastAPI Backend for Karyalaya AI.

Endpoints:
  GET  /                    — Web UI
  POST /api/chat            — SSE agent conversation (multi-turn, session-aware)
  POST /api/upload          — Task file upload (scans, photos)
  POST /api/upload_sop      — SOP file upload + immediate re-ingestion
  POST /api/ingest_sops     — Re-index all SOPs in workspace/sops/
  POST /api/approve_draft   — Human sign-off: the ONLY path to finalize_official_document
  GET  /api/deliverables    — List official deliverables
  GET  /api/deliverables/{filename} — Download a deliverable
  GET  /api/network_status  — Egress watchdog status

Session state is kept in memory (SESSIONS dict). Each browser tab gets a UUID session.
"""

import os
import sys
import json
import asyncio
import shutil
from typing import Dict, Any

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.planner import AgentOrchestrator
from network_monitor.egress_watchdog import get_network_status
from knowledge_base.ingest_pipeline import ingest_sops
from agent.tools.doc_generator import finalize_official_document, draft_payload_to_html
from agent.tools.file_io import WORKSPACE_DIR

app = FastAPI(title="Karyalaya AI", version="1.0.0")

STATIC_DIR        = os.path.join(os.path.dirname(__file__), "static")
UPLOADS_DIR       = os.path.join(WORKSPACE_DIR, "uploads")
DELIVERABLES_DIR  = os.path.join(WORKSPACE_DIR, "deliverables")
SOPS_UPLOAD_DIR   = os.path.join(WORKSPACE_DIR, "sops")

for d in (STATIC_DIR, UPLOADS_DIR, DELIVERABLES_DIR, SOPS_UPLOAD_DIR):
    os.makedirs(d, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

orchestrator = AgentOrchestrator()

# In-memory session store: session_id → session dict
# Each session holds: history, current_draft_payload, revision_count
SESSIONS: Dict[str, Dict[str, Any]] = {}


class DraftApprovalRequest(BaseModel):
    draft_payload: Dict[str, Any]
    session_id: str = ""


@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the web UI."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Karyalaya AI backend is running. index.html not found.</h3>"


@app.get("/api/network_status")
def api_network_status():
    """OS-level egress watchdog status."""
    return get_network_status()


@app.post("/api/chat")
async def api_chat(
    user_message: str = Form(...),
    session_id: str = Form(...),
    uploaded_file: str = Form(None),
):
    """
    Main conversational agent endpoint. Streams SSE events for real-time UI rendering.
    Maintains multi-turn conversation history and draft state per session_id.
    """
    # Initialise session on first message
    session = SESSIONS.setdefault(session_id, {
        "history": [],
        "current_draft_payload": None,
        "revision_count": 0,
    })

    # Append current user turn to history
    session["history"].append({"role": "user", "content": user_message})

    async def sse_generator():
        file_path = os.path.join(UPLOADS_DIR, uploaded_file) if uploaded_file else None

        agent_messages = []  # Collect agent output for history

        for step_data in orchestrator.run_task(
            user_prompt=user_message,
            uploaded_file_path=file_path,
            conversation_history=session["history"],
            current_draft_payload=session.get("current_draft_payload"),
        ):
            phase = step_data.get("phase")

            # Update session draft state and inject HTML preview
            if phase == "DRAFT_READY":
                payload = step_data.get("draft_payload", {})
                is_revision = step_data.get("is_revision", False)

                if is_revision:
                    session["revision_count"] += 1

                session["current_draft_payload"] = payload
                step_data["revision_count"] = session["revision_count"]
                step_data["preview_html"] = draft_payload_to_html(
                    payload, revision=session["revision_count"]
                )
                agent_messages.append(
                    f"[DRAFT {'REVISED' if is_revision else 'CREATED'} — Revision {session['revision_count']}]"
                )

            elif phase == "FINAL_ANSWER":
                agent_messages.append(step_data.get("content", ""))

            elif phase == "CLARIFYING_QUESTION":
                agent_messages.append(f"[CLARIFYING QUESTION]: {step_data.get('question', '')}")

            yield f"data: {json.dumps(step_data)}\n\n"
            await asyncio.sleep(0.03)

        # Record agent response in history for next turn
        if agent_messages:
            session["history"].append({
                "role": "agent",
                "content": " | ".join(agent_messages),
            })

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.post("/api/upload")
async def api_upload_file(file: UploadFile = File(...)):
    """Uploads a scan or task document to workspace/uploads/."""
    try:
        dest = os.path.join(UPLOADS_DIR, file.filename)
        with open(dest, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
        return {
            "status": "success",
            "filename": file.filename,
            "filepath": dest,
            "message": f"Uploaded {file.filename}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload_sop")
async def api_upload_sop(file: UploadFile = File(...)):
    """
    Accepts a SOP file (.pdf, .txt, .md), saves it to workspace/sops/,
    and immediately re-ingests the entire SOP directory into Chroma.
    """
    allowed = {".pdf", ".txt", ".md"}
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Accepted: .pdf, .txt, .md",
        )
    try:
        dest = os.path.join(SOPS_UPLOAD_DIR, file.filename)
        with open(dest, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        result = ingest_sops()
        return {
            "status": "success",
            "filename": file.filename,
            "chunks_indexed": result.get("total_chunks_ingested", 0),
            "message": (
                f"'{file.filename}' added to knowledge base — "
                f"{result.get('total_chunks_ingested', 0)} total chunks indexed."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest_sops")
def api_ingest_sops():
    """Triggers full re-ingestion of workspace/sops/ into local Chroma DB."""
    return ingest_sops()


@app.post("/api/approve_draft")
def api_approve_draft(req: DraftApprovalRequest):
    """
    Human Sign-Off endpoint.
    The ONLY code path that calls finalize_official_document(human_confirmed=True).
    Clears the session's active draft on success.
    """
    try:
        result = finalize_official_document(req.draft_payload, human_confirmed=True)

        # Clear draft state from session so the next task starts clean
        session = SESSIONS.get(req.session_id)
        if session:
            session["current_draft_payload"] = None
            session["revision_count"] = 0

        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/deliverables")
def api_list_deliverables():
    """Lists available official deliverable files."""
    files = []
    if os.path.exists(DELIVERABLES_DIR):
        for fname in sorted(os.listdir(DELIVERABLES_DIR)):
            if fname.startswith(".") or fname.startswith("DRAFT_"):
                continue
            fp = os.path.join(DELIVERABLES_DIR, fname)
            files.append({
                "name": fname,
                "size": os.path.getsize(fp),
                "created": os.path.getctime(fp),
            })
    return {"deliverables": files}


@app.get("/api/deliverables/{filename}")
def api_download_deliverable(filename: str):
    """Serves a deliverable file for download."""
    fp = os.path.join(DELIVERABLES_DIR, filename)
    if os.path.exists(fp):
        return FileResponse(path=fp, filename=filename, media_type="application/octet-stream")
    raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
