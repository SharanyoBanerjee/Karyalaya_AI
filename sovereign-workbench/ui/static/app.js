// Karyalaya AI — Conversational Agent Frontend Controller

// ── Session & State ──────────────────────────────────────────────────────────
const SESSION_ID = crypto.randomUUID();

let uploadedTaskFile   = null;   // File name of the task scan/photo in uploads/
let currentDraftPayload = null;  // Active draft waiting for human approval
let currentDraftFile    = null;  // DRAFT_ filename for download link
let isAgentRunning      = false; // Prevent parallel submissions

// ── DOM Ready ────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    initTheme();
    initNetworkMonitor();
    initSopUpload();
    initTaskFileUpload();
    loadDeliverables();

    document.getElementById("btnSend").addEventListener("click", sendMessage);
    document.getElementById("btnReindex").addEventListener("click", reindexSops);
    document.getElementById("btnApproveDraft").addEventListener("click", approveDraft);
    document.getElementById("btnClearFile").addEventListener("click", clearTaskFile);

    // Textarea — send on Enter (not Shift+Enter), auto-resize
    const textarea = document.getElementById("chatInput");
    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    textarea.addEventListener("input", () => {
        textarea.style.height = "auto";
        textarea.style.height = Math.min(textarea.scrollHeight, 130) + "px";
    });

    // Poll network watchdog every 4 seconds
    setInterval(updateNetworkStatus, 4000);
});

// ── Theme Switcher ──────────────────────────────────────────────────────────
function initTheme() {
    const savedTheme = localStorage.getItem("karyalaya_theme") || "dark";
    applyTheme(savedTheme);

    const toggleBtn = document.getElementById("themeToggleBtn");
    if (toggleBtn) {
        toggleBtn.addEventListener("click", () => {
            const currentTheme = document.documentElement.getAttribute("data-theme") || "dark";
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            applyTheme(newTheme);
        });
    }
}

function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("karyalaya_theme", theme);
    const label = document.getElementById("themeToggleText");
    if (label) {
        label.innerText = theme === "dark" ? "Dark" : "Light";
    }
}

// ── Network Monitor ───────────────────────────────────────────────────────────
async function initNetworkMonitor() { await updateNetworkStatus(); }

async function updateNetworkStatus() {
    try {
        const res  = await fetch("/api/network_status");
        if (!res.ok) return;
        const data = await res.json();

        const isSecure = data.is_airgapped;
        const text     = document.getElementById("netStatusText");
        const count    = document.getElementById("connCountBadge");
        const metric   = document.getElementById("metricConnCount");
        const fwVal    = document.getElementById("netFirewallVal");
        const sockVal  = document.getElementById("outboundSocketVal");
        const lastVal  = document.getElementById("lastVerifiedVal");

        text.innerText  = isSecure ? "SECURE (AIR-GAPPED)" : "WARNING (EGRESS DETECTED)";
        text.style.color = isSecure ? "var(--green-text)" : "var(--red-text)";
        count.innerText = `${data.outbound_connection_count} Outbound`;
        if (metric)  metric.innerText   = data.outbound_connection_count;
        if (fwVal)   fwVal.innerText    = data.firewall_status  || "pfctl Active";
        if (sockVal) sockVal.innerText  = data.outbound_connection_count;
        if (lastVal) lastVal.innerText  = data.last_checked
            ? data.last_checked.split(" ")[1] || data.last_checked
            : new Date().toLocaleTimeString();
    } catch (_) {}
}

// ── Task File Upload (scan / photo) ───────────────────────────────────────────
function initTaskFileUpload() {
    document.getElementById("taskFileInput").addEventListener("change", async (e) => {
        if (e.target.files.length > 0) await uploadTaskFile(e.target.files[0]);
    });
}

async function uploadTaskFile(file) {
    const form = new FormData();
    form.append("file", file);
    try {
        const res  = await fetch("/api/upload", { method: "POST", body: form });
        const data = await res.json();
        if (data.status === "success") {
            uploadedTaskFile = data.filename;
            document.getElementById("uploadedFileTagText").innerText = data.filename;
            document.getElementById("uploadedFileBar").style.display = "block";
            appendStatusLine(getTypingEl(), `Attached: ${data.filename}`);
        }
    } catch (e) {
        appendAgentBubble(`File upload failed: ${e}`);
    }
}

function clearTaskFile() {
    uploadedTaskFile = null;
    document.getElementById("uploadedFileBar").style.display = "none";
    document.getElementById("taskFileInput").value = "";
}

// ── SOP Upload & Reindex ─────────────────────────────────────────────────────
function initSopUpload() {
    document.getElementById("sopFileInput").addEventListener("change", async (e) => {
        if (e.target.files.length > 0) await uploadSop(e.target.files[0]);
    });
}

async function uploadSop(file) {
    const statusEl = document.getElementById("sopStatus");
    statusEl.innerText = `Uploading ${file.name}...`;
    const form = new FormData();
    form.append("file", file);
    try {
        const res  = await fetch("/api/upload_sop", { method: "POST", body: form });
        const data = await res.json();
        statusEl.innerText = data.message || `${file.name} indexed.`;
        document.getElementById("sopUploadText").innerText = "Upload SOP / Reference (PDF, TXT, MD)";
        document.getElementById("sopFileInput").value = "";
    } catch (e) {
        statusEl.innerText = `Upload failed: ${e}`;
    }
}

async function reindexSops() {
    const statusEl = document.getElementById("sopStatus");
    statusEl.innerText = "Re-indexing all SOPs...";
    try {
        const res  = await fetch("/api/ingest_sops", { method: "POST" });
        const data = await res.json();
        statusEl.innerText = `Re-index complete — ${data.total_chunks_ingested || 0} chunks indexed.`;
    } catch (e) {
        statusEl.innerText = `Re-index failed: ${e}`;
    }
}

// ── Deliverables ─────────────────────────────────────────────────────────────
async function loadDeliverables() {
    try {
        const res  = await fetch("/api/deliverables");
        const data = await res.json();
        const el   = document.getElementById("deliverablesList");
        el.innerHTML = "";
        if (data.deliverables && data.deliverables.length > 0) {
            data.deliverables.forEach(item => {
                const a = document.createElement("a");
                a.className = "deliverable-link";
                a.href      = `/api/deliverables/${encodeURIComponent(item.name)}`;
                a.innerText = item.name;
                a.target    = "_blank";
                el.appendChild(a);
            });
        } else {
            el.innerHTML = '<span class="small-text">No finalized deliverables yet.</span>';
        }
    } catch (_) {}
}

// ── Chat Message Rendering ───────────────────────────────────────────────────

/** Appends a user bubble to the thread. */
function appendUserBubble(text) {
    const thread = document.getElementById("chatThread");
    const wrap   = document.createElement("div");
    wrap.className = "chat-message user";
    const bubble   = document.createElement("div");
    bubble.className = "user-bubble";
    bubble.innerText = text;
    wrap.appendChild(bubble);
    thread.appendChild(wrap);
    thread.scrollTop = thread.scrollHeight;
    return wrap;
}

/**
 * Creates an agent message container with an initial bubble.
 * Returns the wrapper so status lines and extras can be appended to it.
 */
function createAgentMessage(initialText = "") {
    const thread = document.getElementById("chatThread");
    const wrap   = document.createElement("div");
    wrap.className = "chat-message agent";

    const bubble   = document.createElement("div");
    bubble.className = "agent-bubble";
    if (initialText) {
        bubble.innerText = initialText;
    } else {
        bubble.style.display = "none";
    }
    wrap.appendChild(bubble);

    thread.appendChild(wrap);
    thread.scrollTop = thread.scrollHeight;
    return { wrap, bubble };
}

/** Appends a status line under an existing agent message wrapper. */
function appendStatusLine(wrap, text) {
    const line  = document.createElement("div");
    line.className = "status-line";
    line.innerHTML = `<span class="status-dot"></span><span>${text}</span>`;
    wrap.appendChild(line);
    document.getElementById("chatThread").scrollTop = document.getElementById("chatThread").scrollHeight;
}

/** Appends an inline code output block under an agent message wrapper. */
function appendCodeBlock(wrap, code, stdout, stderr) {
    const block = document.createElement("div");
    block.className = "code-block";

    const label = document.createElement("span");
    label.className = "code-block-label";
    label.innerText = "Code Sandbox Output";
    block.appendChild(label);

    if (code) {
        const src = document.createElement("pre");
        src.className = "code-source";
        src.innerText = code;
        block.appendChild(src);
        const hr = document.createElement("hr");
        hr.className = "code-divider";
        block.appendChild(hr);
    }

    if (stdout) {
        const out = document.createElement("pre");
        out.className = "code-stdout";
        out.innerText = stdout;
        block.appendChild(out);
    } else if (!stderr) {
        const empty = document.createElement("span");
        empty.className = "code-empty";
        empty.innerText = "(no output)";
        block.appendChild(empty);
    }

    if (stderr) {
        const err = document.createElement("pre");
        err.className = "code-stderr";
        err.innerText = stderr;
        block.appendChild(err);
    }

    wrap.appendChild(block);
    document.getElementById("chatThread").scrollTop = document.getElementById("chatThread").scrollHeight;
}

/**
 * Appends a clarifying question with an inline reply input.
 * Replying sends the user's answer as the next chat message.
 */
function appendClarifyQuestion(wrap, question) {
    const box = document.createElement("div");
    box.className = "clarify-box";

    const label = document.createElement("span");
    label.className = "clarify-label";
    label.innerText = "Clarification Required";
    box.appendChild(label);

    const qText = document.createElement("div");
    qText.className = "clarify-text";
    qText.innerText = question;
    box.appendChild(qText);

    const row = document.createElement("div");
    row.className = "clarify-input-row";

    const input = document.createElement("input");
    input.className   = "clarify-input";
    input.type        = "text";
    input.placeholder = "Type your answer...";

    const sendBtn = document.createElement("button");
    sendBtn.className = "btn-clarify-send";
    sendBtn.innerText = "Reply";

    const doReply = () => {
        const val = input.value.trim();
        if (!val) return;
        input.disabled = true;
        sendBtn.disabled = true;
        sendBtn.innerText = "Sent";
        // Inject into the chat textarea and send
        document.getElementById("chatInput").value = val;
        sendMessage();
    };

    sendBtn.addEventListener("click", doReply);
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") doReply(); });

    row.appendChild(input);
    row.appendChild(sendBtn);
    box.appendChild(row);
    wrap.appendChild(box);

    input.focus();
    document.getElementById("chatThread").scrollTop = document.getElementById("chatThread").scrollHeight;
}

/** Shows a typing indicator. Returns the wrapper element. */
function showTypingIndicator() {
    const thread = document.getElementById("chatThread");
    const wrap   = document.createElement("div");
    wrap.className = "chat-message agent";
    wrap.id        = "typingIndicator";
    wrap.innerHTML = `<div class="agent-bubble"><div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
    </div></div>`;
    thread.appendChild(wrap);
    thread.scrollTop = thread.scrollHeight;
    return wrap;
}

function removeTypingIndicator() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
}

/** Returns a scratch wrapper for status lines before the real agent message arrives. */
function getTypingEl() {
    return document.getElementById("typingIndicator") ||
           document.getElementById("chatThread").lastElementChild;
}

// ── Draft Panel ───────────────────────────────────────────────────────────────
function openDraftPanel(draftPayload, previewHtml, revisionCount, draftFile) {
    currentDraftPayload = draftPayload;
    currentDraftFile    = draftFile;

    const panel      = document.getElementById("draftPanel");
    const container  = document.getElementById("mainContainer");
    const preview    = document.getElementById("draftPreviewScroll");
    const revLabel   = document.getElementById("revisionLabel");
    const dlLink     = document.getElementById("draftDownloadLink");

    panel.style.display = "flex";
    container.classList.add("draft-open");

    revLabel.innerText = revisionCount > 0 ? `Revision ${revisionCount}` : "Initial Draft";
    preview.innerHTML  = previewHtml;

    if (draftFile) {
        dlLink.href = `/api/deliverables/${encodeURIComponent(draftFile)}`;
    }

    preview.scrollTop = 0;
}

function closeDraftPanel() {
    document.getElementById("draftPanel").style.display = "none";
    document.getElementById("mainContainer").classList.remove("draft-open");
    currentDraftPayload = null;
    currentDraftFile    = null;
}

async function approveDraft() {
    if (!currentDraftPayload) return;

    const btn = document.getElementById("btnApproveDraft");
    btn.disabled  = true;
    btn.innerText = "Finalizing...";

    try {
        const res  = await fetch("/api/approve_draft", {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify({ draft_payload: currentDraftPayload, session_id: SESSION_ID }),
        });
        const data = await res.json();

        if (data.status === "success") {
            closeDraftPanel();
            appendUserBubble("[Human sign-off confirmed]");
            const { wrap, bubble } = createAgentMessage(
                `Official document finalized: '${data.official_filename}'. ` +
                "It is now available in the Official Deliverables panel. " +
                "The AI never submitted this — your explicit sign-off did."
            );
            document.getElementById("lowConfBanner").style.display = "none";
            loadDeliverables();
        } else {
            btn.disabled  = false;
            btn.innerText = "Confirm & Finalize (.docx)";
            appendAgentBubble(`Approval failed: ${data.error || "unknown error"}`);
        }
    } catch (e) {
        btn.disabled  = false;
        btn.innerText = "Confirm & Finalize (.docx)";
        appendAgentBubble(`Approval error: ${e}`);
    }
}

/** Convenience: append a standalone agent bubble (for errors, simple messages). */
function appendAgentBubble(text) {
    const { bubble } = createAgentMessage(text);
    return bubble;
}

// ── Main Send / SSE Loop ──────────────────────────────────────────────────────
async function sendMessage() {
    const textarea = document.getElementById("chatInput");
    const text     = textarea.value.trim();
    if (!text || isAgentRunning) return;

    isAgentRunning = true;
    textarea.value = "";
    textarea.style.height = "auto";

    // Disable send button during execution
    const btn = document.getElementById("btnSend");
    btn.disabled  = true;
    btn.innerText = "Working...";

    appendUserBubble(text);

    // Show typing indicator
    const typingWrap = showTypingIndicator();

    // The live agent message container (we create it on first real content)
    let agentWrap   = null;
    let agentBubble = null;
    let agentBubbleText = "";

    const formData = new FormData();
    formData.append("user_message",   text);
    formData.append("session_id",     SESSION_ID);
    if (uploadedTaskFile) {
        formData.append("uploaded_file", uploadedTaskFile);
    }

    try {
        const response = await fetch("/api/chat", { method: "POST", body: formData });
        const reader   = response.body.getReader();
        const decoder  = new TextDecoder();
        let buffer     = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const raw = line.slice(6).trim();
                if (!raw) continue;
                let event;
                try   { event = JSON.parse(raw); }
                catch { continue; }

                handleEvent(event, typingWrap, {
                    getAgentWrap: () => agentWrap,
                    setAgentWrap: (w) => { agentWrap = w; },
                    getAgentBubble: () => agentBubble,
                    setAgentBubble: (b) => { agentBubble = b; },
                    getBubbleText: () => agentBubbleText,
                    setBubbleText: (t) => { agentBubbleText = t; },
                });
            }
        }
    } catch (e) {
        removeTypingIndicator();
        appendAgentBubble(`Connection error: ${e}`);
    } finally {
        removeTypingIndicator();
        isAgentRunning  = false;
        btn.disabled    = false;
        btn.innerText   = "Send";
        // Clear task file after each submission
        clearTaskFile();
    }
}

/**
 * Routes a single SSE event to the correct rendering function.
 * Uses a refs object to share mutable agent-message state without globals.
 */
function handleEvent(event, typingWrap, refs) {
    const phase = event.phase;

    // Helper: ensure we have an agent message container
    function ensureAgentWrap() {
        if (!refs.getAgentWrap()) {
            removeTypingIndicator();
            const { wrap, bubble } = createAgentMessage("");
            refs.setAgentWrap(wrap);
            refs.setAgentBubble(bubble);
        }
    }

    switch (phase) {

        case "ROUTER":
            // Show model routing as first status line
            ensureAgentWrap();
            appendStatusLine(refs.getAgentWrap(),
                `Routing to ${event.model_used} (${event.task_type} task)`);
            break;

        case "STATUS":
            ensureAgentWrap();
            appendStatusLine(refs.getAgentWrap(), event.content);
            break;

        case "PLAN":
            // Show plan step as a status line (terse)
            ensureAgentWrap();
            appendStatusLine(refs.getAgentWrap(), event.plan);
            break;

        case "ACT":
            // Tool call is already summarised by the STATUS event; skip to avoid duplication
            break;

        case "OBSERVE":
            // Internal; not shown in chat to keep the UI clean
            break;

        case "CODE_OUTPUT":
            ensureAgentWrap();
            appendCodeBlock(refs.getAgentWrap(), event.code, event.stdout, event.stderr);
            // Show low-confidence banner if the scan result was uncertain
            if (event.observation && event.observation.low_confidence_flag) {
                document.getElementById("lowConfBanner").style.display = "flex";
            }
            break;

        case "CLARIFYING_QUESTION":
            ensureAgentWrap();
            if (refs.getAgentBubble() && !refs.getBubbleText()) {
                refs.getAgentBubble().innerText = event.question;
                refs.getAgentBubble().style.display = "block";
                refs.setBubbleText(event.question);
            }
            appendClarifyQuestion(refs.getAgentWrap(), event.question);
            break;

        case "DRAFT_READY": {
            ensureAgentWrap();
            const isRevision = event.is_revision;
            const revCount   = event.revision_count || 0;
            const msg = isRevision
                ? `Draft revised (Revision ${revCount}). Review the updated version in the panel.`
                : "Draft document created. Review it in the panel on the right, then type feedback or click Confirm to finalize.";

            if (refs.getAgentBubble()) {
                refs.getAgentBubble().innerText = msg;
                refs.getAgentBubble().style.display = "block";
                refs.setBubbleText(msg);
            }

            openDraftPanel(
                event.draft_payload,
                event.preview_html,
                revCount,
                event.draft_file,
            );
            break;
        }

        case "FINAL_ANSWER":
            ensureAgentWrap();
            if (refs.getAgentBubble()) {
                refs.getAgentBubble().innerText = event.content;
                refs.getAgentBubble().style.display = "block";
                refs.setBubbleText(event.content);
            }
            break;

        case "STUCK_STATE":
            ensureAgentWrap();
            if (refs.getAgentBubble()) {
                refs.getAgentBubble().innerText = event.content;
                refs.getAgentBubble().style.display = "block";
                refs.setBubbleText(event.content);
            }
            break;

        case "ERROR":
            ensureAgentWrap();
            appendStatusLine(refs.getAgentWrap(), `Error: ${event.content}`);
            break;

        default:
            break;
    }
}
