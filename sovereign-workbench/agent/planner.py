"""
Agent Loop Orchestrator for Sovereign AI Workbench.
Implements Plan -> Act -> Observe -> Reflect execution loop with tool calling.
Strictly local, capped at 8 iterations, with transparent UI step logging.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Generator

# Ensure project root is in sys.path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from router.classifier import ModelRouter
from agent.tools.file_io import read_workspace_file, write_workspace_file, list_workspace_files
from agent.tools.code_sandbox import execute_python_code
from agent.tools.doc_search import search_knowledge_base
from agent.tools.doc_generator import generate_approval_note
from agent.tools.spreadsheet import create_excel_report, read_excel_report
from ingestion.vlm_reader import ingest_document_scan

MAX_ITERATIONS = 8

class AgentOrchestrator:
    def __init__(self):
        self.router = ModelRouter()

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches tool execution to registered tool functions."""
        try:
            if tool_name == "doc_search":
                return search_knowledge_base(query=args.get("query", ""), top_k=args.get("top_k", 3))
            elif tool_name == "file_read":
                return read_workspace_file(file_path=args.get("file_path", ""))
            elif tool_name == "file_write":
                return write_workspace_file(file_path=args.get("file_path", ""), content=args.get("content", ""))
            elif tool_name == "file_list":
                return list_workspace_files(subfolder=args.get("subfolder", ""))
            elif tool_name == "code_sandbox":
                return execute_python_code(code_string=args.get("code", ""))
            elif tool_name == "doc_generator":
                return generate_approval_note(
                    title=args.get("title", "Inspection Approval Note"),
                    ref_number=args.get("ref_number", "REF-2026-001"),
                    plant_unit=args.get("plant_unit", "Refinery Unit"),
                    inspection_date=args.get("inspection_date", "2026-08-27"),
                    findings=args.get("findings", ["Physical inspection complete"]),
                    sop_reference=args.get("sop_reference", "Per SOP guidelines"),
                    recommendation=args.get("recommendation", "Recommended for approval"),
                    filename=args.get("filename", "Approval_Note.docx")
                )
            elif tool_name == "spreadsheet":
                return create_excel_report(
                    sheet_name=args.get("sheet_name", "Sheet1"),
                    headers=args.get("headers", ["ID", "Item", "Status"]),
                    rows=args.get("rows", []),
                    filename=args.get("filename", "Report.xlsx")
                )
            elif tool_name == "scan_ingest":
                return ingest_document_scan(file_path=args.get("file_path", ""))
            else:
                return {"status": "error", "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"status": "error", "error": f"Tool execution failure: {str(e)}"}

    def run_task(self, user_prompt: str, uploaded_file_path: str = None) -> Generator[Dict[str, Any], None, None]:
        """
        Executes the agentic loop. Yields step updates for real-time UI trace streaming.
        """
        # Step 1: Route request
        task_type, model_cfg, route_log = self.router.classify_request(user_prompt, has_image=bool(uploaded_file_path))
        
        yield {
            "step": 0,
            "phase": "ROUTER",
            "content": route_log,
            "task_type": task_type,
            "model_used": model_cfg["name"]
        }

        # System prompt with available tools and strict JSON output formatting
        system_prompt = (
            "You are an air-gapped Sovereign AI Workbench Agent serving government/defence/PSU operations.\n"
            "You work strictly via Plan -> Act -> Observe -> Reflect loop.\n\n"
            "AVAILABLE TOOLS:\n"
            "1. doc_search(query: str): Search local SOP knowledge base for compliance clauses.\n"
            "2. file_read(file_path: str): Read a file inside workspace.\n"
            "3. file_write(file_path: str, content: str): Write text file inside workspace.\n"
            "4. file_list(subfolder: str): List files in workspace.\n"
            "5. code_sandbox(code: str): Run Python script inside Docker sandbox with --network none.\n"
            "6. doc_generator(title: str, ref_number: str, plant_unit: str, inspection_date: str, findings: list, sop_reference: str, recommendation: str, filename: str): Generate official .docx file.\n"
            "7. spreadsheet(sheet_name: str, headers: list, rows: list, filename: str): Generate styled .xlsx Excel report.\n"
            "8. scan_ingest(file_path: str): Extract text/findings from scanned document/photo.\n\n"
            "RESPONSE FORMAT (You MUST respond in valid JSON with these keys):\n"
            "{\n"
            '  "plan": "Current high-level plan step",\n'
            '  "action": "tool_name OR final_answer",\n'
            '  "action_input": { tool arguments object },\n'
            '  "final_answer": "Final response text if action is final_answer",\n'
            '  "reflection": "Reflection on observation or progress"\n'
            "}"
        )

        history = []
        if uploaded_file_path:
            history.append(f"Uploaded File Available: {uploaded_file_path}")
        history.append(f"User Task: {user_prompt}")

        step = 1

        while step <= MAX_ITERATIONS:
            prompt = (
                f"TASK HISTORY:\n" + "\n".join(history) + "\n\n"
                f"Iteration {step}/{MAX_ITERATIONS}. Provide your next PLAN, ACTION (tool or final_answer), ACTION_INPUT, and REFLECTION in JSON."
            )

            try:
                raw_response = self.router.generate(
                    model_name=model_cfg["name"],
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.1
                )
            except Exception as e:
                yield {
                    "step": step,
                    "phase": "ERROR",
                    "content": f"Ollama generation failed: {e}"
                }
                break

            # Parse JSON action
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if json_match:
                try:
                    action_data = json.loads(json_match.group(0))
                except Exception:
                    action_data = None
            else:
                action_data = None

            if not action_data:
                # Fallback heuristics for unformatted model responses
                action_data = {
                    "plan": "Process request directly",
                    "action": "final_answer",
                    "action_input": {},
                    "final_answer": raw_response,
                    "reflection": "Completed response generation."
                }

            plan = action_data.get("plan", "Executing task step")
            action = action_data.get("action", "final_answer")
            action_input = action_data.get("action_input", {})
            reflection = action_data.get("reflection", "Step completed.")
            final_answer = action_data.get("final_answer", "")

            # Log plan update
            yield {
                "step": step,
                "phase": "PLAN & REFLECT",
                "plan": plan,
                "action": action,
                "reflection": reflection
            }

            if action == "final_answer" or not action:
                yield {
                    "step": step,
                    "phase": "FINAL ANSWER",
                    "content": final_answer or raw_response
                }
                break

            # Execute Tool Action
            yield {
                "step": step,
                "phase": "ACT",
                "tool": action,
                "arguments": action_input
            }

            observation = self._execute_tool(action, action_input)

            yield {
                "step": step,
                "phase": "OBSERVE",
                "tool": action,
                "observation": observation
            }

            # Append to history
            history.append(f"\nStep {step}: Action={action}({json.dumps(action_input)}) -> Observation={json.dumps(observation)}")
            step += 1

        if step > MAX_ITERATIONS:
            yield {
                "step": step,
                "phase": "STUCK_STATE",
                "content": f"Agent reached maximum iteration limit ({MAX_ITERATIONS}). Human input required."
            }


if __name__ == "__main__":
    agent = AgentOrchestrator()
    for trace in agent.run_task("Read SOP guidelines and generate an inspection approval note for Refinery Unit 4B valve inspection"):
        print(json.dumps(trace, indent=2))
