// Sovereign AI Workbench Frontend Controller — High-Contrast Dark Theme Edition

let uploadedFileName = null;
let currentDraftPayload = null;

document.addEventListener("DOMContentLoaded", () => {
    initNetworkMonitor();
    initFileUpload();
    initDeliverablesList();

    document.getElementById("btnRunTask").addEventListener("click", runAgentTask);
    document.getElementById("btnIngestSop").addEventListener("click", ingestSops);
    document.getElementById("btnApproveDraft").addEventListener("click", approveCurrentDraft);

    // Poll network watchdog every 3 seconds
    setInterval(updateNetworkStatus, 3000);
});

// Network Egress Watchdog Polling
async function initNetworkMonitor() {
    await updateNetworkStatus();
}

async function updateNetworkStatus() {
    try {
        const res = await fetch("/api/network_status");
        if (!res.ok) return;
        const data = await res.json();

        const statusText = document.getElementById("netStatusText");
        const countBadge = document.getElementById("connCountBadge");
        const metricConnCount = document.getElementById("metricConnCount");
        const fwVal = document.getElementById("netFirewallVal");
        const socketVal = document.getElementById("outboundSocketVal");
        const lastVal = document.getElementById("lastVerifiedVal");

        if (data.is_airgapped) {
            statusText.innerText = "SECURE (AIR-GAPPED)";
            statusText.style.color = "#10b981";
            countBadge.innerText = `${data.outbound_connection_count} Outbound Connections`;
        } else {
            statusText.innerText = "WARNING (EGRESS DETECTED)";
            statusText.style.color = "#ef4444";
            countBadge.innerText = `${data.outbound_connection_count} Outbound Connections`;
        }

        if (metricConnCount) {
            metricConnCount.innerText = data.outbound_connection_count;
        }

        fwVal.innerText = data.firewall_status || "pfctl Active";
        socketVal.innerText = `${data.outbound_connection_count} External Sockets`;
        lastVal.innerText = data.last_checked || new Date().toLocaleTimeString();

    } catch (e) {
        console.error("Network monitor update failed:", e);
    }
}

// File Upload Handler
function initFileUpload() {
    const dropZone = document.getElementById("uploadZone");
    const fileInput = document.getElementById("fileInput");

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "#facc15";
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "rgba(255, 255, 255, 0.14)";
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "rgba(255, 255, 255, 0.14)";
        if (e.dataTransfer.files.length > 0) {
            fileInput.files = e.dataTransfer.files;
            handleUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener("change", () => {
        if (fileInput.files.length > 0) {
            handleUpload(fileInput.files[0]);
        }
    });
}

async function handleUpload(file) {
    const uploadText = document.getElementById("uploadText");
    uploadText.innerText = `Uploading ${file.name}...`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (data.status === "success") {
            uploadedFileName = data.filename;
            uploadText.innerText = `Uploaded: ${data.filename} (${(file.size / 1024).toFixed(1)} KB)`;
            appendTraceEntry("system", `Uploaded file '${data.filename}' ready for multimodal ingestion.`);
        } else {
            uploadText.innerText = "Upload failed.";
        }
    } catch (e) {
        uploadText.innerText = "Upload error.";
        console.error(e);
    }
}

// SOP Ingestion
async function ingestSops() {
    const statusDiv = document.getElementById("sopIngestStatus");
    statusDiv.innerText = "Ingesting plant SOPs into Chroma Vector DB...";
    try {
        const res = await fetch("/api/ingest_sops", { method: "POST" });
        const data = await res.json();
        statusDiv.innerText = `Ingestion complete: ${data.total_chunks_ingested || 0} chunks indexed.`;
        appendTraceEntry("system", `Re-ingested plant SOPs into local Chroma DB (${data.files_processed} files processed).`);
    } catch (e) {
        statusDiv.innerText = "Ingestion failed.";
    }
}

// List Deliverables
async function initDeliverablesList() {
    try {
        const res = await fetch("/api/deliverables");
        const data = await res.json();
        const listDiv = document.getElementById("deliverablesList");
        listDiv.innerHTML = "";

        if (data.deliverables && data.deliverables.length > 0) {
            data.deliverables.forEach(item => {
                const link = document.createElement("a");
                link.className = "deliverable-link";
                link.href = `/api/deliverables/${encodeURIComponent(item.name)}`;
                link.innerText = `Download: ${item.name}`;
                link.target = "_blank";
                listDiv.appendChild(link);
            });
        } else {
            listDiv.innerHTML = '<span class="small-text">No finalized deliverables yet.</span>';
        }
    } catch (e) {
        console.error("Failed to load deliverables:", e);
    }
}

// Append Entry to Visible Trace Console
function appendTraceEntry(type, content, extra = {}) {
    const consoleDiv = document.getElementById("traceConsole");
    const entry = document.createElement("div");
    entry.className = `trace-entry ${type}`;

    const timestamp = `<span class="timestamp">[${new Date().toLocaleTimeString()}]</span>`;
    
    if (type === "router") {
        entry.innerHTML = `${timestamp} <strong>MODEL ROUTER:</strong> ${content}`;
        document.getElementById("traceModelBadge").innerText = `Model: ${extra.model || 'qwen2.5:7b'}`;
    } else if (type === "act") {
        entry.innerHTML = `${timestamp} <strong>ACTION (Step ${extra.step}):</strong> Tool <code>${extra.tool}</code> called with args: <pre>${JSON.stringify(extra.args, null, 2)}</pre>`;
    } else if (type === "observe") {
        entry.innerHTML = `${timestamp} <strong>OBSERVATION:</strong> <pre>${JSON.stringify(extra.obs, null, 2)}</pre>`;
    } else if (type === "plan") {
        entry.innerHTML = `${timestamp} <strong>PLAN & REFLECT (Step ${extra.step}):</strong> ${extra.plan}<br><em>Reflection: ${extra.reflection}</em>`;
    } else if (type === "final") {
        entry.innerHTML = `${timestamp} <strong>AGENT OUTPUT:</strong><br>${content}`;
    } else {
        entry.innerHTML = `${timestamp} ${content}`;
    }

    consoleDiv.appendChild(entry);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

// Display Human Review Panel
function showHumanReviewPanel(draftPayload) {
    currentDraftPayload = draftPayload;
    const reviewPanel = document.getElementById("humanReviewPanel");
    const previewBox = document.getElementById("draftPreviewBox");

    previewBox.innerHTML = `
        <strong>Document Title:</strong> ${draftPayload.title || "Inspection Approval Note"}<br>
        <strong>Reference No:</strong> ${draftPayload.ref_number || "REF-2026-001"}<br>
        <strong>Plant Unit:</strong> ${draftPayload.plant_unit || "Plant Unit"}<br>
        <strong>Inspection Date:</strong> ${draftPayload.inspection_date || "2026-08-27"}<br><br>
        <strong>Key Findings:</strong>
        <ul>${(draftPayload.findings || []).map(f => `<li>${f}</li>`).join("")}</ul><br>
        <strong>SOP Grounding:</strong> ${draftPayload.sop_reference || "N/A"}<br>
        <strong>Recommendation:</strong> ${draftPayload.recommendation || "N/A"}<br>
    `;

    reviewPanel.style.display = "block";
    reviewPanel.scrollIntoView({ behavior: 'smooth' });
}

// Approve Current Draft (Human Sign-Off)
async function approveCurrentDraft() {
    if (!currentDraftPayload) return;

    const btn = document.getElementById("btnApproveDraft");
    btn.disabled = true;
    btn.innerText = "Finalizing Official Document...";

    try {
        const res = await fetch("/api/approve_draft", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ draft_payload: currentDraftPayload })
        });
        const data = await res.json();

        if (data.status === "success") {
            appendTraceEntry("system", `<strong>HUMAN SIGN-OFF CONFIRMED:</strong> Official document finalized as '${data.official_filename}'.`);
            document.getElementById("humanReviewPanel").style.display = "none";
            currentDraftPayload = null;
            initDeliverablesList();
        } else {
            alert(`Approval error: ${data.error}`);
        }
    } catch (e) {
        alert(`Approval error: ${e}`);
    } finally {
        btn.disabled = false;
        btn.innerText = "Confirm & Finalize Official Deliverable (.docx)";
    }
}

// Agent Task Runner (SSE Stream Reader)
async function runAgentTask() {
    const promptInput = document.getElementById("taskPrompt");
    const promptText = promptInput.value.trim();

    if (!promptText) {
        alert("Please enter a task description or query.");
        return;
    }

    // Reset warnings and review panels
    document.getElementById("lowConfidenceBanner").style.display = "none";
    document.getElementById("humanReviewPanel").style.display = "none";

    const btn = document.getElementById("btnRunTask");
    btn.disabled = true;
    btn.innerText = "Agent Executing...";

    appendTraceEntry("system", `<strong>NEW TASK SUBMITTED:</strong> "${promptText}"`);

    const formData = new FormData();
    formData.append("user_prompt", promptText);
    if (uploadedFileName) {
        formData.append("uploaded_file", uploadedFileName);
    }

    try {
        const response = await fetch("/api/execute", {
            method: "POST",
            body: formData
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.replace("data: ", "").trim();
                    if (!jsonStr) continue;
                    
                    try {
                        const event = JSON.parse(jsonStr);
                        handleSseEvent(event);
                    } catch (err) {
                        console.error("SSE parse error:", err);
                    }
                }
            }
        }

    } catch (e) {
        appendTraceEntry("system", `Execution error: ${e}`);
    } finally {
        btn.disabled = false;
        btn.innerText = "Execute Agent Task";
    }
}

function handleSseEvent(event) {
    if (event.type === "trace") {
        const d = event.data;
        if (d.phase === "ROUTER") {
            appendTraceEntry("router", d.content, { model: d.model_used });
        } else if (d.phase === "PLAN & REFLECT") {
            appendTraceEntry("plan", d.plan, { step: d.step, plan: d.plan, reflection: d.reflection });
        } else if (d.phase === "ACT") {
            appendTraceEntry("act", "", { step: d.step, tool: d.tool, args: d.arguments });
        } else if (d.phase === "OBSERVE") {
            appendTraceEntry("observe", "", { step: d.step, obs: d.observation });

            // Check for low-confidence extraction flag
            if (d.observation && d.observation.low_confidence_flag) {
                document.getElementById("lowConfidenceBanner").style.display = "flex";
            }
            // Check for human review requirement from doc_generator
            if (d.observation && d.observation.requires_human_approval && d.observation.draft_payload) {
                showHumanReviewPanel(d.observation.draft_payload);
            }
        } else if (d.phase === "FINAL ANSWER") {
            appendTraceEntry("final", d.content);
        } else if (d.phase === "STUCK_STATE") {
            appendTraceEntry("system", `<strong>AGENT STUCK:</strong> ${d.content}`);
        }
    }
}
