# Karyalaya AI (कार्यालय AI)
### Air-Gapped Autonomous Intelligence for Government, Defence & PSU Operations

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Status: Sovereign & Air-Gapped](https://img.shields.io/badge/Network-100%25%20Air--Gapped-emerald.svg)]()
[![Inference: Local-Only](https://img.shields.io/badge/Inference-Local%20Ollama%2FvLLM-orange.svg)]()
[![Design: Neumorphic Soft UI](https://img.shields.io/badge/Design-Neumorphic%20Tactile-blueviolet.svg)]()

---

## 📌 Overview

**Karyalaya AI** is a fully self-hosted, air-gapped agentic AI workbench engineered for high-security environments—including defence manufacturing, oil refineries, nuclear power facilities, and government public sector undertakings (PSUs).

In sovereign and classified operations, routine knowledge tasks (e.g., verifying hydrostatic valve test reports, cross-referencing plant Standard Operating Procedures, executing data verification scripts, and preparing signed approval notes) cannot touch cloud AI due to strict confidentiality mandates. 

Karyalaya AI delivers a multimodal, tool-using, agentic AI assistant that runs **100% locally** on your organization's internal workstation or private GPU server with **zero external telemetry and zero outbound network egress**.

---

## 🌟 Key Capabilities

1. **100% Sovereign & Air-Gapped**: Runs entirely offline using local open-weight models (served via Ollama / vLLM). No cloud APIs, no external telemetry, and no CDN dependencies.
2. **Dynamic Task Routing**: Automatically selects the optimal open-weight model for each query (`Qwen2.5-Coder` for scripts, `Qwen2.5-14B/7B` for document reasoning, `Qwen2-VL` for image/scan parsing) via a configuration-driven router (`model_registry.yaml`).
3. **Multimodal Ingestion**: Ingests scanned inspection sheets, handwritten logs, photos, and engineering diagrams via local OCR (PaddleOCR/Tesseract) with Vision-Language Model fallback (`Qwen2-VL-7B`). Surfaces low-confidence flags if visual clarity is under 75%.
4. **Local Knowledge Base (RAG)**: Indexes internal manuals, plant SOPs, and circulars inside a local file-based Chroma vector store. Answers are strictly grounded in organizational documents with cited paragraphs.
5. **Autonomous Plan-Act-Observe-Reflect Agent**: Executes multi-step workflows, runs verification scripts in a network-disabled Docker sandbox (`--network none`), analyzes data tables, and iteratively refines deliverables.
6. **Programmatic Office Deliverable Generation**: Directly exports ready-to-use, cleanly formatted `.docx` approval notes, `.xlsx` workbooks, and `.pptx` slides.
7. **Strict Human-in-the-Loop Governance**: Hard permission gates enforce that the AI agent can only generate drafts. Official deliverables require explicit human review and cryptographic/one-click sign-off.
8. **Real-Time Network Sovereignty Watchdog**: A background kernel/host monitor tracks all socket activity using `pfctl` (macOS) or `iptables` (Linux), providing live visual proof of 0 outbound connections.
9. **Neumorphic Soft-UI Interface**: Features a tactile, low-fatigue design with flat balanced colors, zero high-contrast outlines, real-time SSE streaming agent traces, inline document previews, and a light/dark theme toggle.

---

## 🏗 System Architecture

```
                                  ┌────────────────────────┐
                                  │   User Interface (UI)   │
                                  │ (Neumorphic Light/Dark)│
                                  └───────────┬────────────┘
                                              │  HTTP / SSE
                                              ▼
                                  ┌────────────────────────┐
                                  │   FastAPI Web Server   │
                                  └───────────┬────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │      Model Router       │                       │    Network Watchdog     │
        │ (model_registry.yaml)   │                       │ (pfctl / socket check)  │
        └────────────┬────────────┘                       └────────────┬────────────┘
                     │                                                 │ Live Status
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │   Local Model Pool      │                       │   UI Security Badge     │
        │  (Ollama Local Daemon)  │                       │   (0 Outbound Sockets)  │
        ├─────────────────────────┤                       └─────────────────────────┘
        │ • Qwen2.5-Coder-7B      │
        │ • Qwen2.5-14B-Instruct  │
        │ • Qwen2-VL-7B (Vision)  │
        │ • Nomic-Embed-Text / BGE│
        └────────────┬────────────┘
                     │
                     ▼
        ┌───────────────────────────────────────────────────────────┐
        │               Autonomous Agent Loop                       │
        │             (Plan ➔ Act ➔ Observe ➔ Reflect)              │
        └──────┬────────────┬─────────────┬────────────┬────────────┘
               │            │             │            │
               ▼            ▼             ▼            ▼
        ┌──────────┐ ┌────────────┐ ┌───────────┐ ┌─────────────────┐
        │ File I/O │ │ Code Box   │ │ Local RAG │ │ Doc Generator   │
        │ (Scoped) │ │(Docker Net │ │ (ChromaDB │ │ (.docx / .xlsx) │
        │          │ │   None)    │ │   SOPs)   │ │  (Draft/Final)  │
        └──────────┘ └────────────┘ └───────────┘ └────────┬────────┘
                                                           │
                                                           ▼
                                            ┌─────────────────────────────┐
                                            │ Human-in-the-Loop Sign-Off  │
                                            │ (Permission Gate / Review)  │
                                            └──────────────┬──────────────┘
                                                           │
                                                           ▼
                                            ┌─────────────────────────────┐
                                            │    Official Deliverable     │
                                            │   workspace/deliverables/   │
                                            └─────────────────────────────┘
```

---

## 📂 Repository Structure

```
SIH1127_PrototypeMain/
├── README.md                           # Comprehensive documentation & guide
├── Architecture.md                     # Architectural decisions & component specs
├── PRD.md                              # Product Requirements Document
├── Phases.md                           # Milestone roadmap (Phases 1–9)
├── Rules.md                            # Hard engineering & air-gapped constraints
├── SampleSOPs/                         # Sample plant standard operating procedures
└── sovereign-workbench/                # Core Application Package
    ├── agent/
    │   ├── planner.py                  # Autonomous multi-step agent orchestrator
    │   └── tools/
    │       ├── file_io.py              # Scoped workspace file reader/writer
    │       ├── code_sandbox.py         # Docker sandbox with network disabled
    │       ├── doc_search.py           # Chroma vector store retriever
    │       ├── spreadsheet.py          # Excel/CSV data parser and aggregator
    │       └── doc_generator.py        # DOCX generator with human sign-off gate
    ├── ingestion/
    │   ├── ocr.py                      # Local PaddleOCR / Tesseract extraction
    │   └── vlm_reader.py               # Vision-Language Model scan interpreter
    ├── knowledge_base/
    │   ├── ingest_pipeline.py          # SOP document chunker & ChromaDB indexer
    │   └── vector_store/               # Local persistent Chroma vector store
    ├── network_monitor/
    │   └── egress_watchdog.py          # Real-time pfctl/socket egress monitor
    ├── router/
    │   ├── classifier.py               # Rule & heuristic model selector
    │   └── model_registry.yaml         # Config-driven model endpoints & limits
    ├── ui/
    │   ├── app.py                      # FastAPI server & Server-Sent Events stream
    │   └── static/
    │       ├── index.html              # Modern 3-column control room layout
    │       ├── style.css               # Tactile Neumorphic design system (Dark/Light)
    │       └── app.js                  # Frontend state machine & SSE event stream
    ├── workspace/                      # Scoped working directory (uploads/deliverables)
    └── test_flagship_pipeline.py       # End-to-end integration verification test
```

---

## ⚡ How It Works

### 1. Model Routing
Incoming user queries are analyzed by `ModelRouter`. The task classification maps to the optimal local model:
- **Coding / Script Execution**: `qwen2.5-coder:7b` (High-efficiency code synthesis).
- **Document Reasoning / SOP Grounding**: `qwen2.5:14b-instruct` or `qwen2.5:7b` (Deep instruction adherence).
- **Multimodal Visual Inspection**: `qwen2-vl:7b` (Diagrams, handwriting, valve scans).

### 2. Autonomous Agent Execution (Plan ➔ Act ➔ Observe ➔ Reflect)
When a task is submitted:
1. **Plan**: Formulates a clear, step-by-step strategy based on available tools.
2. **Act**: Invokes local tools (e.g. searching the vector store for `SOP-702`, parsing uploaded CSVs, or generating Python verification scripts).
3. **Observe**: Receives structured output from tool executions (e.g., Docker stdout or document excerpts).
4. **Reflect**: Evaluates completeness. If discrepancies exist or parameters fail verification, it self-corrects.
5. **Clarify (If Ambiguous)**: If vital input is missing, the agent halts and renders an inline question block in the chat thread.

### 3. Human-in-the-Loop Sign-Off Governance
- The AI agent is cryptographically restricted from directly publishing final official records.
- When drafting notes, it generates an **AI Draft** and opens an inline structured preview panel.
- The human officer can inspect the findings, request revisions in the chat, or click **Confirm & Finalize (.docx)**.
- Finalization invokes `finalize_official_document(human_confirmed=True)`, stamping the approved deliverable in `workspace/deliverables/`.

---

## 🚀 Getting Started

### Prerequisites

1. **Operating System**: macOS (Apple Silicon M-Series recommended for local GGUF acceleration) or Linux (Ubuntu 22.04+ with NVIDIA GPU / CPU).
2. **Python**: Version `3.10` or higher.
3. **Ollama**: Local model serving engine ([ollama.ai](https://ollama.ai/)).
4. **Docker Desktop**: For isolated code sandbox execution.

---

### Step 1: Clone the Repository & Set Up Environment

```bash
git clone https://github.com/SharanyoBanerjee/Karyalaya_AI.git
cd Karyalaya_AI

# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn python-docx python-pptx openpyxl chromadb \
            sentence-transformers Pillow pydantic PyYAML psutil
```

---

### Step 2: Pull Local Open-Weight Models via Ollama

Ensure the Ollama daemon is running (`ollama serve`), then pull the required models:

```bash
# Document reasoning model
ollama pull qwen2.5:14b       # (or qwen2.5:7b for machines with <16GB RAM)

# Code generation model
ollama pull qwen2.5-coder:7b

# Multimodal Vision model
ollama pull qwen2-vl:7b

# Local Embeddings model
ollama pull nomic-embed-text
```

---

### Step 3: Index Plant SOPs into Local Vector Store

Ingest existing plant standard operating procedures and technical reference files:

```bash
python3 -c "from sovereign_workbench.knowledge_base.ingest_pipeline import ingest_sops; ingest_sops()"
```

*(You can also upload and re-index SOPs directly from the web interface at any time).*

---

### Step 4: Launch the Karyalaya AI Workbench

Start the local FastAPI application server:

```bash
python3 sovereign-workbench/ui/app.py
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

---

### Step 5: Run the End-to-End Verification Test

To test the entire pipeline (Network check ➔ Image generation ➔ VLM OCR ➔ Model routing ➔ SOP search ➔ AI Draft ➔ Human sign-off ➔ DOCX deliverable generation):

```bash
python3 sovereign-workbench/test_flagship_pipeline.py
```

---

## 🖥 User Interface Guide

The Karyalaya AI interface is designed with a **Tactile Neumorphic Soft-UI** to eliminate visual fatigue during long monitoring shifts:

| Component | Description |
|---|---|
| **Top Navigation Bar** | Displays organization branding, **Theme Toggle** (Light / Dark), and the real-time **Air-Gapped Security Badge** (0 Outbound Sockets). |
| **Left Sidebar** | • **System Metrics Grid**: Sockets, Local Inference (100%), Step Caps.<br>• **Network Sovereignty Panel**: Firewall status, Docker sandbox lockdown.<br>• **Reference Documents**: Drag-and-drop zone for PDF/TXT/MD SOP indexing.<br>• **Official Deliverables**: Direct downloads for human-approved `.docx` notes. |
| **Center Chat Console** | • **SSE Live Stream**: Real-time visualization of model routing, plan steps, and code execution outputs.<br>• **Zero High-Contrast Outlines**: Soft inset input wells and raised tactile action buttons.<br>• **File Attachment Button**: Upload scan photos, logs, or CSV tables. |
| **Right Draft Review Panel** | Slides in when a draft document is generated. Renders a formatted preview with metadata tables, findings, and SOP citations. Includes the **Confirm & Finalize** button. |

---

## 🔒 Security & Air-Gap Compliance

| Protection Layer | Enforcement Mechanism |
|---|---|
| **No Cloud Dependency** | All models execute via local endpoints (`http://localhost:11434`). Zero cloud API fallbacks exist in the codebase. |
| **Code Sandbox Isolation** | Docker containers execute with `--network none`, preventing generated scripts from attempting outbound connections. |
| **Host Egress Watchdog** | macOS `pfctl` / Linux kernel firewall monitors active sockets and alerts the UI instantly if egress is attempted. |
| **Filesystem Sandboxing** | All file read/write operations are strictly jailed to the `sovereign-workbench/workspace/` folder. |
| **Zero Telemetry** | UI assets, web fonts, and scripts are self-contained with no external CDN or analytics pings. |

---

## 🔮 Roadmap & Future Updates

- [x] **Phase 1–8 (v1 Prototype)**: Local Ollama serving, dynamic model router, local ChromaDB RAG, multi-step agent loop, vision model ingestion, DOCX generation, Neumorphic UI, and live egress watchdog.
- [ ] **Phase 9: Enterprise GPU Cluster Scaling**:
  - Transition model serving from Ollama to **vLLM** for high-throughput batching on enterprise NVIDIA H100 / A100 clusters.
  - Scale vector storage to **Qdrant Distributed Cluster** for millions of technical records.
  - Unlock 32B–72B reasoning models (`Qwen2.5-72B-Instruct`, `DeepSeek-R1-Distill`).
- [ ] **Role-Based Access Control (RBAC) & Multi-User Vaults**:
  - Integration with air-gapped LDAP / Active Directory.
  - Granular document-level permission controls and departmental compartmentalization.
- [ ] **Cryptographic Audit Trails**:
  - Hardware Security Module (HSM) and smart-card digital signatures (PKI) for final document authorization.
  - Append-only cryptographic audit logs for every agent reasoning step.
- [ ] **Specialized Engineering Parsers**:
  - Native parsing for CAD/DXF engineering blueprints and SCADA time-series telemetry dumps.

---

## 📜 License

Karyalaya AI is distributed under the **MIT License**. All underlying models (Qwen series, Nomic Embed) are subject to their respective open-weight community licenses.
