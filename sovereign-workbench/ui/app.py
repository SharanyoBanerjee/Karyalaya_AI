"""
FastAPI Backend Application for Sovereign AI Workbench.
Serves web UI, handles uploads, streams SSE agent traces, and exposes human draft approval endpoints.
Strictly local, no external web calls or CDNs.
"""

import os
import sys
import json
import asyncio
import shutil
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.planner import AgentOrchestrator
from network_monitor.egress_watchdog import get_network_status
from knowledge_base.ingest_pipeline import ingest_sops
from agent.tools.doc_generator import finalize_official_document
from agent.tools.file_io import WORKSPACE_DIR

app = FastAPI(title="Sovereign AI Workbench", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOADS_DIR = os.path.join(WORKSPACE_DIR, "uploads")
DELIVERABLES_DIR = os.path.join(WORKSPACE_DIR, "deliverables")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DELIVERABLES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

orchestrator = AgentOrchestrator()


class DraftApprovalRequest(BaseModel):
    draft_payload: Dict[str, Any]


@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the primary web user interface."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h3>Sovereign AI Workbench Backend Running.</h3>"


@app.get("/api/network_status")
def api_network_status():
    """Returns OS-level egress watchdog status."""
    return get_network_status()


@app.post("/api/ingest_sops")
def api_ingest_sops():
    """Triggers local SOP vector database ingestion."""
    return ingest_sops()


@app.post("/api/upload")
async def api_upload_file(file: UploadFile = File(...)):
    """Uploads a scanned report or document file into workspace/uploads/."""
    try:
        file_location = os.path.join(UPLOADS_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {
            "status": "success",
            "filename": file.filename,
            "filepath": file_location,
            "message": f"Successfully uploaded {file.filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/execute")
async def api_execute_task(user_prompt: str = Form(...), uploaded_file: str = Form(None)):
    """
    Executes an agent task and streams Server-Sent Events (SSE) for live UI trace rendering.
    """
    async def sse_event_generator():
        yield f"data: {json.dumps({'type': 'start', 'prompt': user_prompt})}\n\n"
        
        file_path = os.path.join(UPLOADS_DIR, uploaded_file) if uploaded_file else None

        for step_data in orchestrator.run_task(user_prompt=user_prompt, uploaded_file_path=file_path):
            yield f"data: {json.dumps({'type': 'trace', 'data': step_data})}\n\n"
            await asyncio.sleep(0.05)

        yield f"data: {json.dumps({'type': 'complete'})}\n\n"

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")


@app.post("/api/approve_draft")
def api_approve_draft(req: DraftApprovalRequest):
    """
    Human Review Sign-Off Endpoint:
    Receives explicit human approval from UI, finalizes official .docx document, and saves to deliverables.
    """
    try:
        res = finalize_official_document(req.draft_payload)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/deliverables/{filename}")
def api_download_deliverable(filename: str):
    """Serves generated .docx or .xlsx deliverable files."""
    file_path = os.path.join(DELIVERABLES_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename, media_type='application/octet-stream')
    raise HTTPException(status_code=404, detail=f"Deliverable file {filename} not found.")


@app.get("/api/deliverables")
def api_list_deliverables():
    """Lists available generated deliverables."""
    files = []
    if os.path.exists(DELIVERABLES_DIR):
        for f in os.listdir(DELIVERABLES_DIR):
            if not f.startswith("."):
                f_path = os.path.join(DELIVERABLES_DIR, f)
                files.append({
                    "name": f,
                    "size": os.path.getsize(f_path),
                    "created": os.path.getctime(f_path)
                })
    return {"deliverables": files}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
