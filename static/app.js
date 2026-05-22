"use strict";

// Pre-seeded users (created by the backend on first run).
const USERS = [
  { id: "admin", role: "Admin" },
  { id: "analyst", role: "Security Analyst" },
  { id: "hr_user", role: "HR" },
  { id: "finance_user", role: "Finance" },
  { id: "eng_user", role: "Engineering" },
  { id: "manager_user", role: "Manager" },
  { id: "employee_user", role: "Employee" },
  { id: "guest_user", role: "Guest" },
];

const SAMPLES = {
  hr: {
    filename: "sample_hr.txt",
    sensitivity: "CONFIDENTIAL",
    text: `COMPANY CONFIDENTIAL - HR Employee Records

Employee John Smith (EMP-98231) joined the People Operations team on 2023-04-12.
His corporate email is john.smith@acme-corp.com and his contact number is
+1-415-555-0148. Current annual compensation is $142,000. Performance rating for
the last cycle was "Exceeds Expectations".

Employee Maria Garcia (EMP-77410) reports directly to John Smith. Her email is
maria.garcia@acme-corp.com and her annual compensation is $128,500. Maria is
enrolled in the leadership development program for 2024.

Customer escalation contact for benefits queries is recorded under CUST-560192.
This document is internal only and must not be distributed outside the HR
department.`,
  },
  eng: {
    filename: "sample_eng.txt",
    sensitivity: "INTERNAL",
    text: `INTERNAL - Engineering Notes: Project Falcon

Project Falcon is the internal codename for the next-generation payments
gateway. The integration relies on S/MIME to provide both integrity and
confidentiality for message headers. S/MIME signs the headers so that any
tampering can be detected, which guarantees integrity, and it encrypts the
message body so that only the intended recipient can read it, which provides
confidentiality.

For SIP-based signaling, header integrity is protected by digitally signing the
SIP headers, while S/MIME ensures the confidentiality of sensitive header
fields by encrypting them. A receiver verifies the signature to confirm the
headers were not altered in transit.

The lead engineer on Project Falcon is Priya Nair (priya.nair@acme-corp.com).
The service account key for the staging environment is
sk-live-9f8d7a6b5c4e3d2f1a0b. Vendor work for the hardware security module is
covered under contract CTR-2024-0091. This document is internal only.`,
  },
};

// ---- helpers -------------------------------------------------------------
const $ = (id) => document.getElementById(id);

function esc(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function currentUser() {
  return $("userSelect").value;
}

async function api(path, options = {}) {
  options.headers = Object.assign(
    { "X-User-Id": currentUser() },
    options.headers || {}
  );
  const res = await fetch(path, options);
  const raw = await res.text();
  let data;
  try {
    data = JSON.parse(raw);
  } catch (e) {
    data = raw;
  }
  if (!res.ok) {
    const detail = data && data.detail ? data.detail : JSON.stringify(data);
    throw new Error(`${res.status} — ${detail}`);
  }
  return data;
}

function badge(text, cls) {
  return `<span class="badge ${cls}">${esc(text)}</span>`;
}

const STATUS_CLS = {
  ok: "b-green",
  partially_redacted: "b-amber",
  no_context: "b-slate",
  redacted: "b-red",
  error: "b-red",
};
const RISK_CLS = { low: "b-green", medium: "b-amber", high: "b-red" };
const DECISION_CLS = { ALLOW: "b-green", REDACT: "b-amber", DENY: "b-red" };
const VERDICT_CLS = { pass: "b-green", warn: "b-amber", fail: "b-red" };
const ACTION_CLS = { released: "b-green", masked: "b-amber" };

// ---- user picker ---------------------------------------------------------
function initUsers() {
  const sel = $("userSelect");
  USERS.forEach((u) => {
    const opt = document.createElement("option");
    opt.value = u.id;
    opt.textContent = `${u.id}  (${u.role})`;
    sel.appendChild(opt);
  });
  sel.value = "hr_user";
  const sync = () => {
    const u = USERS.find((x) => x.id === sel.value);
    $("userRole").textContent = u ? u.role : "";
  };
  sel.addEventListener("change", sync);
  sync();
}

// ---- server health -------------------------------------------------------
async function pingServer() {
  try {
    const res = await fetch("/health");
    if (res.ok) $("serverDot").classList.add("up");
  } catch (e) {
    /* leave dot red */
  }
}

// ---- ingest --------------------------------------------------------------
async function doIngest() {
  const box = $("ingestResult");
  const file = $("fileInput").files[0];
  const raw = $("rawText").value.trim();

  if (!file && !raw) {
    box.className = "result show";
    box.innerHTML = `<span class="err">Provide a file or paste some text.</span>`;
    return;
  }

  const fd = new FormData();
  if (file) {
    fd.append("file", file);
  } else {
    fd.append("raw_text", raw);
    fd.append("filename", $("filenameInput").value.trim() || "pasted.txt");
  }
  fd.append("sensitivity_level", $("sensSelect").value);
  const roles = $("rolesInput").value.trim();
  if (roles) fd.append("allowed_roles", roles);

  const btn = $("ingestBtn");
  btn.disabled = true;
  btn.textContent = "Ingesting…";
  box.className = "result show";
  box.innerHTML = "Processing (first run downloads the embedding model)…";

  try {
    const d = await api("/ingest/document", { method: "POST", body: fd });
    const stats = Object.entries(d.masking_stats || {})
      .map(([k, v]) => `${k}:${v}`)
      .join(", ") || "none";
    box.innerHTML = `
      ${badge("ingested", "b-green")}
      <div class="kv"><b>Document</b><span class="mono">${esc(d.document_id)}</span></div>
      <div class="kv"><b>Sensitivity</b><span>${esc(d.sensitivity_level)}</span></div>
      <div class="kv"><b>Allowed roles</b><span>${esc((d.allowed_roles || []).join(", "))}</span></div>
      <div class="kv"><b>Chunks</b><span>${d.chunks_indexed}</span></div>
      <div class="kv"><b>Sensitive spans</b><span>${d.sensitive_spans_detected}</span></div>
      <div class="kv"><b>Tokens created</b><span>${d.tokens_created}</span></div>
      <div class="kv"><b>Masking</b><span>${esc(stats)}</span></div>`;
  } catch (e) {
    box.innerHTML = `<span class="err">${esc(e.message)}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Ingest document";
  }
}

// ---- ask -----------------------------------------------------------------
async function doAsk() {
  const query = $("queryInput").value.trim();
  if (!query) return;

  const btn = $("askBtn");
  btn.disabled = true;
  btn.textContent = "Running pipeline…";
  $("answerPanel").classList.remove("hidden");
  $("answerBox").textContent = "Running the multi-agent pipeline…";
  $("answerMeta").innerHTML = "";

  try {
    const d = await api("/chat/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });
    renderAnswer(d);
    if (d.request_id) $("auditInput").value = d.request_id;
  } catch (e) {
    $("answerBox").innerHTML = `<span class="err">${esc(e.message)}</span>`;
  } finally {
    btn.disabled = false;
    btn.textContent = "Send query";
  }
}

function renderAnswer(d) {
  $("answerBox").textContent = d.answer || "(empty response)";

  let html = `<div class="badges">
    ${badge("status: " + d.status, STATUS_CLS[d.status] || "b-slate")}
    ${badge("risk: " + d.risk_level, RISK_CLS[d.risk_level] || "b-slate")}
    ${badge("intent: " + d.intent, "b-indigo")}
    ${badge("evidence: " + d.evidence_items, "b-slate")}
  </div>`;

  const guard = d.injection_guard || {};
  if (guard.flagged) {
    html += `<div class="banner-warn"><strong>Prompt-injection detected.</strong>
      Reasons: ${esc((guard.reasons || []).join(", "))} ·
      risk score ${esc(guard.risk_score)}. The pipeline treated this request as
      suspicious and kept tokens masked.</div>`;
  }

  if (Array.isArray(d.subqueries) && d.subqueries.length > 1) {
    html += `<div class="section-label">Subqueries</div>`;
    html += d.subqueries.map((s) => `<div class="kv">• ${esc(s)}</div>`).join("");
  }

  const chunks = d.retrieved_chunks || [];
  html += `<div class="section-label">Retrieved chunks &amp; RBAC decisions</div>`;
  if (chunks.length) {
    html += `<table><tr><th>Chunk</th><th>Sensitivity</th><th>Decision</th>
      <th>Reason</th><th>Injection?</th></tr>`;
    chunks.forEach((c) => {
      html += `<tr>
        <td class="mono">${esc(c.chunk_id)}</td>
        <td>${esc(c.sensitivity_level)}</td>
        <td>${badge(c.decision, DECISION_CLS[c.decision] || "b-slate")}</td>
        <td>${esc(c.reason)}</td>
        <td>${c.injection_in_chunk ? "⚠ yes" : "no"}</td>
      </tr>`;
    });
    html += `</table>`;
  } else {
    html += `<div class="kv">No chunks passed retrieval for this role.</div>`;
  }

  const detok = d.detokenization || [];
  if (detok.length) {
    html += `<div class="section-label">De-tokenization decisions</div>`;
    html += `<table><tr><th>Token</th><th>Action</th><th>Reason</th></tr>`;
    detok.forEach((t) => {
      html += `<tr>
        <td class="mono">${esc(t.token)}</td>
        <td>${badge(t.action, ACTION_CLS[t.action] || "b-slate")}</td>
        <td>${esc(t.reason)}</td>
      </tr>`;
    });
    html += `</table>`;
  }

  const v = d.verification || {};
  if (v.verdict) {
    html += `<div class="section-label">Answer verification</div>`;
    html += `<div class="kv"><b>Verdict</b>
      ${badge(v.verdict, VERDICT_CLS[v.verdict] || "b-slate")}</div>`;
    html += `<div class="kv"><b>Grounding</b><span>${esc(v.grounding)}</span></div>`;
    if ((v.issues || []).length) {
      html += `<div class="kv"><b>Issues</b><span>${esc(v.issues.join("; "))}</span></div>`;
    }
  }

  const trace = d.trace || [];
  if (trace.length) {
    html += `<details><summary>Agent pipeline trace (${trace.length} steps)</summary>`;
    trace.forEach((t) => {
      html += `<div class="trace-step">
        <span class="trace-agent">${esc(t.agent)}</span>
        <span>${esc(t.message)}</span></div>`;
    });
    html += `</details>`;
  }

  html += `<div class="kv mono" style="margin-top:10px;color:#94a3b8;">
    request_id: ${esc(d.request_id)}</div>`;

  $("answerMeta").innerHTML = html;
}

// ---- audit ---------------------------------------------------------------
async function doAudit() {
  const id = $("auditInput").value.trim();
  const box = $("auditResult");
  if (!id) {
    box.innerHTML = `<span class="err">Enter a request_id.</span>`;
    return;
  }
  box.innerHTML = "Fetching…";
  try {
    const d = await api("/audit/" + encodeURIComponent(id));
    box.innerHTML = `<pre>${esc(JSON.stringify(d, null, 2))}</pre>`;
  } catch (e) {
    box.innerHTML = `<span class="err">${esc(e.message)}</span>`;
  }
}

// ---- wire up -------------------------------------------------------------
function init() {
  initUsers();
  pingServer();

  $("ingestBtn").addEventListener("click", doIngest);
  $("askBtn").addEventListener("click", doAsk);
  $("auditBtn").addEventListener("click", doAudit);

  document.querySelectorAll(".chip[data-sample]").forEach((chip) => {
    chip.addEventListener("click", () => {
      const s = SAMPLES[chip.dataset.sample];
      $("rawText").value = s.text;
      $("filenameInput").value = s.filename;
      $("sensSelect").value = s.sensitivity;
      $("fileInput").value = "";
    });
  });

  document.querySelectorAll(".chip[data-q]").forEach((chip) => {
    chip.addEventListener("click", () => {
      $("queryInput").value = chip.dataset.q;
    });
  });
}

document.addEventListener("DOMContentLoaded", init);
