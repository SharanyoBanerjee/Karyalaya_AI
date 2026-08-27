// Sovereign AI Workbench Frontend Controller

let uploadedFileName = null;

document.addEventListener("DOMContentLoaded", () => {
    initNetworkMonitor();
    initFileUpload();
    initDeliverablesList();

    document.getElementById("btnRunTask").addEventListener("click", runAgentTask);
    document.getElementById("btnIngestSop").addEventListener("click", ingestSops);

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
        const fwVal = document.getElementById("netFirewallVal");
        const socketVal = document.getElementById("outboundSocketVal");
        const lastVal = document.getElementById("lastVerifiedVal");

        if (data.is_airgapped) {
            statusText.innerText = "SECURE (AIR-GAPPED)";
            statusText.style.color = "#10b981";
            countBadge.innerText = `${data.outbound_connection_count} Egress Connections`;
        } else {
            statusText.innerText = "WARNING (EGRESS DETECTED)";
            statusText.style.color = "#ef4444";
            countBadge.innerText = `${data.outbound_connection_count} Connections`;
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
    const uploadText = document.getElementById("uploadText");

    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "#2563eb";
    });

    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "#1e293b";
    });

    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "#1e293b";
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
                link.innerText = `📥 ${item.name}`;
                link.target = "_blank";
                listDiv.appendChild(link);
            });
        } else {
            listDiv.innerHTML = '<span class="small-text">No deliverables generated yet.</span>';
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
        entry.innerHTML = `${timestamp} <strong>FINAL ANSWER / DELIVERABLE:</strong><br>${content}`;
    } else {
        entry.innerHTML = `${timestamp} ${content}`;
    }

    consoleDiv.appendChild(entry);
    consoleDiv.scrollTop = consoleDiv.scrollHeight;
}

// Agent Task Runner (SSE Stream Reader)
async function runAgentTask() {
    const promptInput = document.getElementById("taskPrompt");
    const promptText = promptInput.value.trim();

    if (!promptText) {
        alert("Please enter a task description or query.");
        return;
    }

    const btn = document.getElementById("btnRunTask");
    btn.disabled = true;
    btn.innerText = "⏳ Agent Executing...";

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
            buffer = lines.pop(); // keep last partial line in buffer

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.replace("data: ", "").trim();
                    if (!jsonStr) continue;
                    
                    try {
                        const event = JSON.parse(jsonStr);
                        handleSseEvent(event);
                    } catch (err) {
                        console.error("SSE parse error:", err, line);
                    }
                }
            }
        }

    } catch (e) {
        appendTraceEntry("system", `Execution error: ${e}`);
    } finally {
        btn.disabled = false;
        btn.innerText = "▶ Execute Agent Task";
        initDeliverablesList(); // Refresh deliverables list
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
        } else if (d.phase === "FINAL ANSWER") {
            appendTraceEntry("final", d.content);
        } else if (d.phase === "STUCK_STATE") {
            appendTraceEntry("system", `<strong>AGENT STUCK:</strong> ${d.content}`);
        }
    }
}
