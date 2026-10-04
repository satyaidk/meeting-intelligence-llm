// ActionGraph web UI - vanilla JavaScript, no build step.
// Every piece of data comes from the REST API under /api (see /docs).
//
// SECURITY NOTE: transcripts are untrusted input. Any text that came from the
// API is passed through esc() before it is inserted as HTML, so a transcript
// line like "<script>..." is shown as text instead of being executed.

"use strict";

const EXAMPLE = `Maya Chen: Let's kick off planning. We decided to use OAuth 2.0 for the mobile app.
Maya Chen: Priya will handle the authentication changes.
Maya Chen: We'll update the API design by Friday.
Maya Chen: Sam, please share the user research by Wednesday.
Alex Kim: One concern: the staging environment still runs the old database version.`;

// ---------------------------------------------------------------- helpers
const $ = (selector) => document.querySelector(selector);

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

const pill = (value) => `<span class="pill s-${esc(value)}">${esc(String(value).replace("_", " "))}</span>`;

async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, options);
  const isJson = response.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = isJson ? (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) : body;
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return body;
}

function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast${isError ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.add("hidden"), isError ? 7000 : 3500);
}

async function withBusy(button, work) {
  const label = button.textContent;
  button.disabled = true;
  button.textContent = "Working…";
  try {
    await work();
  } catch (err) {
    toast(err.message, true);
  } finally {
    button.disabled = false;
    button.textContent = label;
  }
}

// ------------------------------------------------------------------- tabs
const loaders = {
  actions: loadActions,
  review: loadReview,
  graph: loadGraph,
  meetings: loadMeetings,
};

// Returns the loader's promise so deep links can wait for the data.
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  return loaders[name]?.();
}

document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    history.replaceState(null, "", `#${tab.dataset.tab}`);
    showTab(tab.dataset.tab);
  }));

// Deep links: #review, #graph, #meetings, #actions, #actions/3 (opens action 3).
async function openDeepLink() {
  const [tab, arg] = location.hash.slice(1).split("/");
  if (!document.getElementById(`tab-${tab}`)) return;
  await showTab(tab);
  if (tab === "actions" && /^\d+$/.test(arg ?? "")) await showActionDetail(arg);
}

// ---------------------------------------------------------------- process
function showReport(report) {
  const usage = report.usage
    ? `<div class="meta">${report.usage.input_tokens} input / ${report.usage.output_tokens} output tokens</div>`
    : "";
  $("#process-result").innerHTML = `
    <div class="card">
      <h3>Meeting #${report.meeting_id} processed</h3>
      <div class="meta">${esc(report.provider)} / ${esc(report.model)} &middot; ${report.latency_seconds}s</div>
      <p>${report.actions_created} actions &middot; ${report.decisions_created} decisions &middot;
         ${report.risks_created} risks &middot; ${report.status_updates_applied} status updates applied
         &middot; <strong>${report.items_needing_review} need review</strong></p>
      ${usage}
      ${report.warnings.map((w) => `<div class="meta">⚠ ${esc(w)}</div>`).join("")}
    </div>`;
  refreshReviewCount();
}

$("#process-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  const data = Object.fromEntries(new FormData(form));
  withBusy(form.querySelector("button[type=submit]"), async () => {
    showReport(await api("/meetings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }));
    toast("Meeting processed");
  });
});

$("#upload-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.target;
  withBusy(form.querySelector("button[type=submit]"), async () => {
    showReport(await api("/meetings/upload", { method: "POST", body: new FormData(form) }));
    toast("Meeting processed");
  });
});

$("#insert-example").addEventListener("click", () => {
  const form = $("#process-form");
  form.title.value = "Example planning meeting";
  form.meeting_date.value = new Date().toISOString().slice(0, 10);
  form.transcript.value = EXAMPLE;
});

// ---------------------------------------------------------------- actions
async function loadActions() {
  const status = $("#status-filter").value;
  const actions = await api(`/actions${status ? `?status=${status}` : ""}`);
  $("#actions-body").innerHTML = actions.map((a) => `
    <tr data-id="${a.id}">
      <td>${a.id}</td>
      <td>${esc(a.task)}</td>
      <td>${esc(a.owner ?? "—")}</td>
      <td>${esc(a.due_date ?? a.deadline_text ?? "—")}</td>
      <td>${pill(a.status)}</td>
      <td>${pill(a.review_status)}</td>
      <td>${a.confidence.toFixed(2)}</td>
    </tr>`).join("") || `<tr><td colspan="7" class="meta">No action items yet. Process a meeting first.</td></tr>`;
  document.querySelectorAll("#actions-body tr[data-id]").forEach((row) =>
    row.addEventListener("click", () => showActionDetail(row.dataset.id)));
}

$("#status-filter").addEventListener("change", loadActions);

async function showActionDetail(id) {
  const a = await api(`/actions/${id}`);
  const panel = $("#action-detail");
  panel.classList.remove("hidden");
  panel.innerHTML = `
    <h2>#${a.id} ${esc(a.task)}</h2>
    <div class="meta">Owner: ${esc(a.owner ?? "—")} &middot; Due: ${esc(a.due_date ?? a.deadline_text ?? "—")}
      &middot; ${pill(a.status)} ${pill(a.review_status)}</div>
    <div class="evidence">“${esc(a.evidence)}”</div>
    ${a.review_reasons.length ? `<ul class="reasons">${a.review_reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}
    ${a.blocking_risks.length ? `<p><strong>Blocked by:</strong> ${a.blocking_risks.map((r) => esc(r.description)).join("; ")}</p>` : ""}
    <h3>Timeline across meetings</h3>
    <ul class="timeline">${a.events.map((e) => `
      <li><strong>${esc(e.meeting_title ?? "Manual edit")}</strong>
        <span class="meta">${esc(e.event_type)}${e.from_status && e.from_status !== e.to_status ? `: ${esc(e.from_status)} → ${esc(e.to_status)}` : ""}
        ${e.deadline_text && e.event_type !== "created" ? ` · deadline “${esc(e.deadline_text)}”` : ""}
        ${e.applied ? "" : ` · ${pill(e.review_status)} not applied yet`}</span>
        ${e.note ? `<div class="meta">${esc(e.note)}</div>` : ""}
      </li>`).join("")}
    </ul>
    <h3>Edit</h3>
    <form id="edit-form" class="row">
      <input name="owner" placeholder="Owner" value="${esc(a.owner ?? "")}" style="max-width:180px">
      <input name="deadline" placeholder="Deadline (2026-10-02 or 'next Friday')" value="${esc(a.due_date ?? "")}" style="max-width:260px">
      <select name="status" style="max-width:150px">
        ${["open", "in_progress", "blocked", "done", "cancelled"].map((s) =>
          `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}
      </select>
      <button class="primary" type="submit">Save</button>
    </form>`;
  $("#edit-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.target;
    const changes = {};
    if (form.owner.value !== (a.owner ?? "")) changes.owner = form.owner.value;
    if (form.deadline.value !== (a.due_date ?? "")) changes.deadline = form.deadline.value;
    if (form.status.value !== a.status) changes.status = form.status.value;
    withBusy(form.querySelector("button"), async () => {
      await api(`/actions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(changes),
      });
      toast("Saved");
      await loadActions();
      await showActionDetail(id);
    });
  });
  panel.scrollIntoView({ behavior: "smooth" });
}

// ----------------------------------------------------------------- review
function reviewCard(kind, item, title, extra = "") {
  return `
    <div class="card">
      <div class="meta">${esc(kind)} #${item.id} &middot; confidence ${item.confidence.toFixed(2)}</div>
      <h3>${title}</h3>
      ${extra}
      <div class="evidence">“${esc(item.evidence)}”</div>
      <ul class="reasons">${item.review_reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
      <div class="row">
        <button class="ok" data-kind="${kind}" data-id="${item.id}" data-verdict="approve">Approve</button>
        <button class="bad" data-kind="${kind}" data-id="${item.id}" data-verdict="reject">Reject</button>
      </div>
    </div>`;
}

async function loadReview() {
  const q = await api("/review");
  const cards = [
    ...q.actions.map((a) => reviewCard("action", a, esc(a.task),
      `<div class="meta">Owner: ${esc(a.owner ?? "—")} · Due: ${esc(a.due_date ?? a.deadline_text ?? "—")}</div>`)),
    ...q.events.map((e) => reviewCard("event", e, `Status update for #${e.action_id}: ${esc(e.action_task)}`,
      `<div class="meta">${esc(e.from_status)} → ${esc(e.to_status)}${e.deadline_text ? ` · new deadline “${esc(e.deadline_text)}”` : ""}</div>`)),
    ...q.decisions.map((d) => reviewCard("decision", d, esc(d.text))),
    ...q.risks.map((r) => reviewCard("risk", r, `${esc(r.kind)}: ${esc(r.description)}`)),
  ];
  $("#review-list").innerHTML = cards.join("") || `<div class="card meta">Nothing to review. 🎉</div>`;
  $("#review-count").textContent = q.total || "";
  document.querySelectorAll("#review-list button[data-verdict]").forEach((button) =>
    button.addEventListener("click", () => withBusy(button, async () => {
      const { kind, id, verdict } = button.dataset;
      await api(`/review/${kind}/${id}/${verdict}`, { method: "POST" });
      toast(`${verdict === "approve" ? "Approved" : "Rejected"} ${kind} #${id}`);
      await loadReview();
    })));
}

async function refreshReviewCount() {
  try {
    $("#review-count").textContent = (await api("/review")).total || "";
  } catch { /* the header badge is best-effort */ }
}

// ------------------------------------------------------------------ graph
const GROUP_COLORS = {
  meeting: "#5c7cfa", action: "#40c057", person: "#fab005", decision: "#be4bdb", risk: "#fa5252",
};
const SHAPES = { meeting: "box", action: "ellipse", person: "dot", decision: "diamond", risk: "triangle" };

async function loadGraph() {
  const graph = await api("/graph");
  if (!window.vis) {
    $("#graph-canvas").innerHTML = `<p class="meta" style="padding:16px">Graph library could not load (offline?). Use “Copy as Mermaid” instead.</p>`;
    return;
  }
  const truncate = (text) => (text.length > 40 ? `${text.slice(0, 39)}…` : text);
  const nodes = graph.nodes.map((n) => ({
    id: n.id,
    label: truncate(n.label),
    title: `${n.type}: ${n.label}`,  // vis-network renders string titles as text
    shape: SHAPES[n.type],
    color: GROUP_COLORS[n.type],
    // Only set keys we need: an explicit `undefined` overrides vis-network's defaults
    // and makes diamond/triangle nodes (decisions, risks) render with no size at all.
    ...(n.type === "meeting" ? { font: { color: "#ffffff" } } : {}),
    ...(n.type === "person" ? { size: 14 } : { size: 18 }),
  }));
  const edges = graph.edges.map((e) => ({
    from: e.source, to: e.target, label: e.label || e.type.toLowerCase(), arrows: "to",
    font: { size: 10, align: "middle" }, color: e.type === "BLOCKS" ? "#fa5252" : "#adb5bd",
    dashes: e.type === "UPDATED",
  }));
  const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const network = new vis.Network($("#graph-canvas"), { nodes, edges }, {
    physics: { solver: "forceAtlas2Based", stabilization: { iterations: 200 } },
    nodes: { font: { color: dark ? "#e6e8ee" : "#1d2330" } },
    edges: { font: { color: dark ? "#9aa3b5" : "#667085", strokeWidth: 0 } },
  });
  // Zoom so every node is visible once the layout has settled.
  network.once("stabilizationIterationsDone", () => network.fit({ animation: false }));
}

$("#copy-mermaid").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(await api("/graph/mermaid"));
    toast("Mermaid diagram copied - paste it into a ```mermaid block on GitHub");
  } catch (err) {
    toast(err.message, true);
  }
});

// --------------------------------------------------------------- meetings
async function loadMeetings() {
  const meetings = await api("/meetings");
  $("#meetings-list").innerHTML = meetings.map((m) => `
    <details class="card" data-id="${m.id}">
      <summary><strong>${esc(m.title)}</strong> <span class="meta">${esc(m.meeting_date)} · ${esc(m.llm_provider)}/${esc(m.llm_model)}</span></summary>
      <div class="meeting-body meta">Loading…</div>
    </details>`).join("") || `<div class="card meta">No meetings yet.</div>`;
  document.querySelectorAll("#meetings-list details").forEach((el) =>
    el.addEventListener("toggle", async () => {
      if (!el.open || el.dataset.loaded) return;
      const m = await api(`/meetings/${el.dataset.id}`);
      el.dataset.loaded = "1";
      const list = (items, render) => (items.length ? `<ul>${items.map((i) => `<li>${render(i)}</li>`).join("")}</ul>` : `<p class="meta">none</p>`);
      el.querySelector(".meeting-body").outerHTML = `
        <p>${esc(m.summary)}</p>
        <p class="meta">Participants: ${esc(m.participants.join(", "))}</p>
        <h3>Decisions</h3>${list(m.decisions, (d) => esc(d.text))}
        <h3>New actions</h3>${list(m.actions, (a) => `${esc(a.task)} — ${esc(a.owner ?? "?")} ${pill(a.review_status)}`)}
        <h3>Updates to earlier actions</h3>${list(m.status_updates, (e) => `#${e.action_id} ${esc(e.action_task)}: ${esc(e.from_status)} → ${esc(e.to_status)} ${e.applied ? "" : pill(e.review_status)}`)}
        <h3>Risks</h3>${list(m.risks, (r) => `${pill(r.kind)} ${esc(r.description)}`)}`;
    }));
}

// ------------------------------------------------------------------- boot
(async function init() {
  const today = new Date().toISOString().slice(0, 10);
  document.querySelectorAll("input[type=date]").forEach((input) => { input.value = today; });
  try {
    const health = await api("/health");
    $("#provider-badge").textContent = `${health.llm_provider} · ${health.model} · v${health.version}`;
  } catch {
    $("#provider-badge").textContent = "API unreachable";
  }
  refreshReviewCount();
  window.addEventListener("hashchange", openDeepLink);
  openDeepLink().catch((err) => toast(err.message, true));
})();
