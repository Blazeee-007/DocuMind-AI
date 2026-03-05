/**
 * DocuMind AI — Frontend Application
 * Vanilla JS: upload, analysis, chat, markdown rendering
 */

const API_BASE = "http://localhost:8000";

// ── State ──────────────────────────────────────────────────────────────────
let docId = null;
let isSending = false;

// ── DOM refs ───────────────────────────────────────────────────────────────
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const progressWrap = document.getElementById("progressWrap");
const progressBar = document.getElementById("progressBar");
const progressLabel = document.getElementById("progressLabel");
const filePreview = document.getElementById("filePreview");
const fileIcon = document.getElementById("fileIcon");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const btnRemove = document.getElementById("btnRemove");
const uploadError = document.getElementById("uploadError");

const analysisSection = document.getElementById("analysisSection");
const chatSection = document.getElementById("chatSection");

const statWords = document.getElementById("statWords");
const statPages = document.getElementById("statPages");
const statRead = document.getElementById("statRead");
const statType = document.getElementById("statType");

const btnSummarize = document.getElementById("btnSummarize");
const btnExtract = document.getElementById("btnExtract");
const btnNewFile = document.getElementById("btnNewFile");

const skeletonWrap = document.getElementById("skeletonWrap");
const resultPanel = document.getElementById("resultPanel");
const resultTitle = document.getElementById("resultTitle");
const resultContent = document.getElementById("resultContent");
const btnCopy = document.getElementById("btnCopy");

const chatWindow = document.getElementById("chatWindow");
const chatEmpty = document.getElementById("chatEmpty");
const chatInput = document.getElementById("chatInput");
const btnSend = document.getElementById("btnSend");

// ── Helpers ────────────────────────────────────────────────────────────────

function formatBytes(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function mimeIcon(filename) {
    const ext = filename.split(".").pop().toLowerCase();
    return { pdf: "📕", docx: "📘", txt: "📄", csv: "📊" }[ext] || "📄";
}

function mimeLabel(mimeType) {
    const m = {
        "application/pdf": "PDF",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
        "text/plain": "TXT",
        "text/csv": "CSV",
    };
    return m[mimeType] || mimeType;
}

function showError(msg) {
    uploadError.textContent = msg;
    uploadError.classList.remove("hidden");
}

function hideError() {
    uploadError.classList.add("hidden");
    uploadError.textContent = "";
}

// ── Minimal markdown → HTML renderer ──────────────────────────────────────

function renderMarkdown(md) {
    let html = md
        // Headings
        .replace(/^### (.+)$/gm, "<h3>$1</h3>")
        .replace(/^## (.+)$/gm, "<h2>$1</h2>")
        .replace(/^# (.+)$/gm, "<h1>$1</h1>")
        // Bold / italic
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        // Inline code
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        // Blockquotes
        .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
        // Unordered lists
        .replace(/^\s*[-*•] (.+)$/gm, "<li>$1</li>")
        // Ordered lists
        .replace(/^\s*\d+\. (.+)$/gm, "<li>$1</li>")
        // Double line breaks → paragraphs
        .split(/\n\n+/)
        .map(p => {
            p = p.trim();
            if (!p) return "";
            if (/^<(h[1-3]|blockquote|li)/.test(p)) {
                // Wrap consecutive <li> in <ul>
                if (p.includes("<li>")) return "<ul>" + p + "</ul>";
                return p;
            }
            return "<p>" + p.replace(/\n/g, "<br>") + "</p>";
        })
        .join("\n");
    return html;
}

// ── Upload flow ────────────────────────────────────────────────────────────

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

btnRemove.addEventListener("click", resetUpload);
btnNewFile.addEventListener("click", resetUpload);

async function handleFile(file) {
    hideError();

    // Client-side sanity checks
    const allowed = [".pdf", ".docx", ".txt", ".csv"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
        showError(`Unsupported file type "${ext}". Please upload a PDF, DOCX, TXT, or CSV file.`);
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showError("File is too large. Maximum allowed size is 10 MB.");
        return;
    }

    // Show preview
    fileIcon.textContent = mimeIcon(file.name);
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);
    filePreview.classList.remove("hidden");

    // Show progress
    progressWrap.classList.remove("hidden");
    progressBar.style.width = "0%";
    progressLabel.textContent = "Uploading…";
    animateProgress(0, 60, 800);

    // Upload
    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
        const json = await res.json();

        if (!res.ok) {
            showError(json.detail || "Upload failed. Please try again.");
            progressWrap.classList.add("hidden");
            return;
        }

        animateProgress(60, 100, 300);
        setTimeout(() => {
            progressWrap.classList.add("hidden");
            onUploadSuccess(json);
        }, 400);

    } catch (err) {
        showError("Could not reach the server. Make sure the backend is running on port 8000.");
        progressWrap.classList.add("hidden");
    }
}

function animateProgress(from, to, duration) {
    const start = performance.now();
    function step(now) {
        const t = Math.min((now - start) / duration, 1);
        progressBar.style.width = (from + (to - from) * t) + "%";
        if (t < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

function onUploadSuccess(data) {
    docId = data.doc_id;

    // Populate stats
    statWords.textContent = data.word_count.toLocaleString();
    statPages.textContent = data.page_count;
    statRead.textContent = data.reading_time_minutes + " min";
    statType.textContent = mimeLabel(data.file_type);

    progressLabel.textContent = "✓ Uploaded!";
    analysisSection.classList.remove("hidden");
    chatSection.classList.remove("hidden");
    analysisSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetUpload() {
    // Clear session on server if one exists
    if (docId) {
        fetch(`${API_BASE}/session/${docId}`, { method: "DELETE" }).catch(() => { });
        docId = null;
    }

    // Reset UI
    fileInput.value = "";
    filePreview.classList.add("hidden");
    progressWrap.classList.add("hidden");
    progressBar.style.width = "0%";
    hideError();
    analysisSection.classList.add("hidden");
    chatSection.classList.add("hidden");
    resultPanel.classList.add("hidden");
    skeletonWrap.classList.add("hidden");
    resultContent.innerHTML = "";

    // Clear chat
    chatWindow.innerHTML = "";
    chatWindow.appendChild(chatEmpty);
    chatEmpty.classList.remove("hidden");
    chatInput.value = "";

    // Reset stat chips
    [statWords, statPages, statRead, statType].forEach(el => el.textContent = "—");
}

// ── Analysis ───────────────────────────────────────────────────────────────

btnSummarize.addEventListener("click", () => runAnalysis("summarize"));
btnExtract.addEventListener("click", () => runAnalysis("extract"));

async function runAnalysis(mode) {
    if (!docId) return;
    setAnalysisLoading(true);
    hideError();

    try {
        const endpoint = mode === "summarize" ? `/analyze/${docId}` : `/extract/${docId}`;
        const res = await fetch(API_BASE + endpoint, { method: "POST" });
        const json = await res.json();

        if (!res.ok) {
            showError(json.detail || "Analysis failed. Please try again.");
            setAnalysisLoading(false);
            return;
        }

        resultTitle.textContent = mode === "summarize" ? "📋 Summary" : "🔍 Extracted Data";
        resultContent.innerHTML = mode === "summarize"
            ? buildSummaryHtml(json)
            : buildExtractHtml(json);

        setAnalysisLoading(false);
        resultPanel.classList.remove("hidden");

    } catch (err) {
        showError("Network error. Make sure the backend is running.");
        setAnalysisLoading(false);
    }
}

function setAnalysisLoading(isLoading) {
    btnSummarize.disabled = isLoading;
    btnExtract.disabled = isLoading;
    skeletonWrap.classList.toggle("hidden", !isLoading);
    if (isLoading) resultPanel.classList.add("hidden");
}

function buildSummaryHtml(data) {
    const keyPoints = Array.isArray(data.key_points)
        ? data.key_points.map(p => `<li>${escHtml(p)}</li>`).join("")
        : "";
    const topics = Array.isArray(data.main_topics)
        ? data.main_topics.map(t => `<span class="source-pill">${escHtml(t)}</span>`).join("")
        : "";

    return `
    <h2>Executive Summary</h2>
    <p>${escHtml(data.executive_summary)}</p>
    <h2>Key Points</h2>
    <ul>${keyPoints}</ul>
    <h2>Main Topics</h2>
    <div class="source-pills">${topics}</div>
    <h2>Tone</h2>
    <p><strong>${escHtml(data.tone)}</strong></p>
    <p style="margin-top:12px;font-size:0.75rem;color:var(--text-muted)">Model: ${escHtml(data.model_used)}</p>
  `;
}

function buildExtractHtml(data) {
    const entities = Array.isArray(data.entities) && data.entities.length
        ? `<table><thead><tr><th>Type</th><th>Value</th></tr></thead><tbody>
        ${data.entities.slice(0, 20).map(e => `<tr><td><code>${escHtml(e.type || "")}</code></td><td>${escHtml(e.value || "")}</td></tr>`).join("")}
       </tbody></table>`
        : "<p>No named entities found.</p>";

    const facts = Array.isArray(data.key_facts) && data.key_facts.length
        ? "<ul>" + data.key_facts.map(f => `<li>${escHtml(f)}</li>`).join("") + "</ul>"
        : "<p>No key facts extracted.</p>";

    const lists = Array.isArray(data.lists) && data.lists.length
        ? "<ul>" + data.lists.slice(0, 20).map(l => `<li>${escHtml(l)}</li>`).join("") + "</ul>"
        : "<p>No lists found.</p>";

    return `
    <h2>Named Entities</h2>${entities}
    <h2>Key Facts</h2>${facts}
    <h2>Lists</h2>${lists}
    <p style="margin-top:12px;font-size:0.75rem;color:var(--text-muted)">Model: ${escHtml(data.model_used)}</p>
  `;
}

function escHtml(str) {
    if (typeof str !== "string") str = String(str ?? "");
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

// Copy button
btnCopy.addEventListener("click", () => {
    const text = resultContent.innerText || "";
    navigator.clipboard.writeText(text).then(() => {
        const orig = btnCopy.textContent;
        btnCopy.textContent = "✓ Copied!";
        setTimeout(() => { btnCopy.textContent = orig; }, 2000);
    });
});

// ── Chat ───────────────────────────────────────────────────────────────────

// Suggestion chips
document.querySelectorAll(".suggestion-chip").forEach(chip => {
    chip.addEventListener("click", () => {
        chatInput.value = chip.getAttribute("data-q");
        sendMessage();
    });
});

chatInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

btnSend.addEventListener("click", sendMessage);

// Auto-resize textarea
chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + "px";
});

async function sendMessage() {
    const q = chatInput.value.trim();
    if (!q || isSending || !docId) return;

    isSending = true;
    btnSend.disabled = true;

    // Hide empty state
    chatEmpty.classList.add("hidden");

    // Append user bubble
    appendMessage("user", q);
    chatInput.value = "";
    chatInput.style.height = "auto";

    // Show typing indicator
    const typingId = appendTyping();

    try {
        const res = await fetch(`${API_BASE}/chat/${docId}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: q }),
        });
        const json = await res.json();
        removeTyping(typingId);

        if (!res.ok) {
            appendMessage("assistant", `⚠️ ${json.detail || "Something went wrong. Please try again."}`);
        } else {
            appendMessage("assistant", json.answer, json.sources);
        }
    } catch (err) {
        removeTyping(typingId);
        appendMessage("assistant", "⚠️ Could not reach the server. Make sure the backend is running.");
    }

    isSending = false;
    btnSend.disabled = false;
    chatInput.focus();
}

function appendMessage(role, text, sources = []) {
    const div = document.createElement("div");
    div.className = `msg msg-${role}`;

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = role === "user" ? "👤" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble markdown-body";
    bubble.innerHTML = renderMarkdown(text);

    // Source pills for assistant
    if (role === "assistant" && sources && sources.length > 0) {
        const pills = document.createElement("div");
        pills.className = "source-pills";
        sources.slice(0, 3).forEach(s => {
            const p = document.createElement("span");
            p.className = "source-pill";
            p.title = s;
            p.textContent = "📎 " + s.substring(0, 60) + (s.length > 60 ? "…" : "");
            pills.appendChild(p);
        });
        bubble.appendChild(pills);
    }

    div.appendChild(avatar);
    div.appendChild(bubble);
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div;
}

function appendTyping() {
    const div = document.createElement("div");
    div.className = "msg msg-assistant";
    div.id = "typing-" + Date.now();

    const avatar = document.createElement("div");
    avatar.className = "msg-avatar";
    avatar.textContent = "🤖";

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerHTML = `<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>`;

    div.appendChild(avatar);
    div.appendChild(bubble);
    chatWindow.appendChild(div);
    chatWindow.scrollTop = chatWindow.scrollHeight;
    return div.id;
}

function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}
