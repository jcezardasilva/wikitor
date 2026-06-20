const $ = (s) => document.querySelector(s);
const api = async (path, opts) => {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
};

// ---------- Abas ----------
const tabs = {
  assist: ["#tab-assist", "#view-assist"],
  browse: ["#tab-browse", "#view-browse"],
  edit: ["#tab-edit", "#view-edit"],
};
function showTab(name) {
  for (const [k, [btn, view]] of Object.entries(tabs)) {
    $(btn).classList.toggle("active", k === name);
    $(view).classList.toggle("hidden", k !== name);
  }
}
for (const [k, [btn]] of Object.entries(tabs)) $(btn).onclick = () => showTab(k);

// ---------- Sidebar / índice ----------
async function loadIndex() {
  const master = await api("/api/index");
  const side = $("#sidebar");
  if (!master.assuntos.length) {
    side.innerHTML = '<div class="muted">Wiki vazia. Crie um documento.</div>';
    return;
  }
  side.innerHTML = "";
  for (const a of master.assuntos) {
    const subj = await api("/api/subjects/" + a.assunto);
    const box = document.createElement("div");
    box.className = "subject";
    box.innerHTML = `<div class="s-title">${a.assunto} <span class="muted">(${a.total_docs})</span></div>`;
    for (const nivel of ["iniciante", "intermediario", "avancado"]) {
      const items = subj.niveis[nivel] || [];
      if (!items.length) continue;
      box.insertAdjacentHTML("beforeend", `<div class="nivel-label">${nivel}</div>`);
      for (const it of items) {
        const link = document.createElement("div");
        link.className = "doc-link";
        link.textContent = it.titulo;
        link.title = it.resumo;
        link.onclick = () => openDoc(it.id);
        box.appendChild(link);
      }
    }
    side.appendChild(box);
  }
}

async function openDoc(id) {
  showTab("browse");
  const doc = await api("/api/docs/" + id);
  $("#doc-view").innerHTML =
    `<div class="doc-meta">assunto: <b>${doc.assunto}</b> · nível: <b>${doc.nivel}</b> · ${doc.atualizado_em}` +
    ` · <a href="#" id="edit-this">editar</a> · <a href="#" id="edit-ai">editar com IA</a></div>` +
    `<div class="rendered">${marked.parse(doc.conteudo || "")}</div>`;
  $("#edit-this").onclick = (e) => { e.preventDefault(); loadIntoEditor(doc); };
  $("#edit-ai").onclick = (e) => { e.preventDefault(); assistSeed(doc); showTab("assist"); };
}

// ---------- Edição manual ----------
function loadIntoEditor(doc) {
  $("#e-id").value = doc.id || "";
  $("#e-titulo").value = doc.titulo || "";
  $("#e-assunto").value = doc.assunto || "";
  $("#e-nivel").value = doc.nivel || "iniciante";
  $("#e-conteudo").value = doc.conteudo || "";
  $("#edit-status").textContent = doc.id ? "Editando: " + doc.id : "Novo documento";
  showTab("edit");
}
$("#btn-new").onclick = () => loadIntoEditor({});
$("#btn-save").onclick = async () => {
  const body = {
    id: $("#e-id").value || null,
    titulo: $("#e-titulo").value.trim(),
    assunto: $("#e-assunto").value.trim(),
    nivel: $("#e-nivel").value,
    conteudo: $("#e-conteudo").value,
  };
  if (!body.titulo || !body.assunto) { $("#edit-status").textContent = "Título e assunto são obrigatórios."; return; }
  $("#edit-status").textContent = "Salvando e gerando resumo…";
  try {
    const doc = await api("/api/docs", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    $("#edit-status").textContent = "Salvo: " + doc.id;
    await loadIndex();
    openDoc(doc.id);
  } catch (e) { $("#edit-status").textContent = "Erro: " + e.message; }
};

// ---------- Helpers de chat ----------
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

function appendMsg(logEl, role, html, opts = {}) {
  logEl.querySelector(".chat-empty")?.remove();
  const el = document.createElement("div");
  el.className = "msg " + role + (opts.thinking ? " thinking" : "");
  el.innerHTML = html;
  logEl.appendChild(el);
  logEl.scrollTop = logEl.scrollHeight;
  return el;
}

function renderSources(fontes) {
  if (!fontes || !fontes.length) return "";
  return "<div class='msg-sources'><span class='muted'>Fontes:</span> " +
    fontes.map((f) => `<span class="source-chip" data-id="${f.id}">${escapeHtml(f.titulo)}</span>`).join("") +
    "</div>";
}

// ---------- Assistente IA unificado (responde, redige e salva) ----------
const aLog = $("#assist-log");
let aHistory = [];        // [{role, content}]
let aContextDoc = null;   // markdown do doc em edição (quando "editar com IA")
let aDocId = null;        // id do doc em edição (para atualizar o mesmo arquivo)

// Prepara a conversa para editar um documento existente.
function assistSeed(doc) {
  aHistory = [];
  aContextDoc = doc.conteudo || null;
  aDocId = doc.id || null;
  aLog.innerHTML = "";
  appendMsg(aLog, "assistant",
    `Vamos trabalhar em <b>${escapeHtml(doc.titulo)}</b>. O que você quer mudar ou melhorar? ` +
    `Quando estiver pronto, é só pedir para salvar.`);
}

async function assistSend(texto) {
  appendMsg(aLog, "user", escapeHtml(texto));
  aHistory.push({ role: "user", content: texto });
  const thinking = appendMsg(aLog, "assistant", "pensando…", { thinking: true });
  try {
    const res = await api("/api/ai/assistant", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages: aHistory, contexto_doc: aContextDoc, doc_id: aDocId }),
    });
    thinking.classList.remove("thinking");
    let html = `<div class="rendered">${marked.parse(res.resposta || "")}</div>`;
    if (res.acao === "resposta") html += renderSources(res.fontes);
    if (res.acao === "salvo" && res.doc) html += renderSources([res.doc]);
    thinking.innerHTML = html;
    thinking.querySelectorAll(".source-chip").forEach(
      (c) => (c.onclick = () => openDoc(c.dataset.id)));

    // Mantém o histórico para a IA; respostas de salvamento não entram como turno de conversa.
    if (res.acao !== "salvo") aHistory.push({ role: "assistant", content: res.resposta || "" });
    if (res.acao === "salvo") {
      await loadIndex();
      // documento salvo passa a ser o contexto de edição (refinamentos seguintes atualizam o mesmo)
      aDocId = res.doc ? res.doc.id : aDocId;
      const novo = aDocId ? await api("/api/docs/" + aDocId) : null;
      aContextDoc = novo ? novo.conteudo : aContextDoc;
    }
    aLog.scrollTop = aLog.scrollHeight;
  } catch (e) { thinking.classList.remove("thinking"); thinking.innerHTML = "Erro: " + e.message; }
}

$("#btn-assist").onclick = () => {
  const inp = $("#a-msg");
  const texto = inp.value.trim();
  if (!texto) return;
  inp.value = "";
  assistSend(texto);
};
$("#a-msg").addEventListener("keydown", (e) => { if (e.key === "Enter") $("#btn-assist").click(); });

loadIndex();
