// toolgate panel — vanilla JS, no build step.
// Every DOM node is created with h(); server data never goes through innerHTML.

const root = document.getElementById("root");
const state = { me: null, tools: [], selected: null, route: "chat", param: null, chat: [], chatId: null, convs: [], chatBusy: false };


// ------------------------------------------------------------------ i18n (EN source strings are the keys)

const PT = {
 "Assistant": "Assistente", "Dashboard": "Painel", "Tools": "Ferramentas", "tools": "ferramentas", "Add tools": "Novas ferramentas",
 "Activity log": "Histórico", "People & permissions": "Pessoas e permissões", "Passwords & keys": "Senhas e chaves",
 "Control what your AI assistant can do.": "Controle o que seu assistente de IA pode fazer.",
 "Choose who can use each tool, keep passwords encrypted and see a record of every action.":
   "Escolha quem pode usar cada ferramenta, guarde senhas criptografadas e veja o registro de cada ação.",
 "Sign in": "Entrar", "Demo accounts": "Contas de teste", "user": "usuário", "password": "senha",
 "Ask in plain language. I only use the tools you're allowed to, and every answer is recorded.":
   "Pergunte do seu jeito. Só uso as ferramentas que você tem permissão para usar, e cada resposta fica registrada.",
 "Hi! I can check tax IDs (CPF/CNPJ), look up invoices and public-transfer agreements. Try one of the examples below.":
   "Olá! Eu valido CPF/CNPJ, consulto notas fiscais e convênios. Experimente um dos exemplos abaixo.",
 "Send": "Enviar", "Used": "Usou", "How I got this answer": "Como cheguei nesta resposta", "Raw data": "Dados brutos",
 "View in activity log": "Ver no histórico", "New chat": "Nova conversa",
 "What's happening in the last 24 hours.": "O que aconteceu nas últimas 24 horas.",
 "Tools you can use": "Ferramentas que você usa", "Calls today": "Chamadas hoje", "Your role": "Seu perfil",
 "built-in": "nativas", "added from the panel": "cadastradas no painel", "admin permissions": "permissões de admin",
 "Most used tools": "Ferramentas mais usadas", "Typical time": "Tempo típico", "Tool groups": "Grupos de ferramentas",
 "Log intact": "Histórico íntegro", "Log was altered at entry": "Histórico alterado no evento", "log hidden": "histórico oculto",
 "No calls yet. Ask the assistant something.": "Nenhuma chamada ainda. Pergunte algo ao assistente.",
 "Run any tool you have access to, or describe what you need and I'll find it.": "Rode qualquer ferramenta a que você tem acesso, ou descreva o que precisa que eu encontro.",
 "Describe what you need, e.g. “quais convênios estão atrasados em MS?”": "Descreva o que precisa, ex.: “quais convênios estão atrasados em MS?”",
 "Find tool": "Encontrar", "No good match. Try other words.": "Nada parecido. Tente outras palavras.",
 "search tools…": "buscar ferramentas…", "Pick a tool on the left.": "Escolha uma ferramenta à esquerda.",
 "Inputs (JSON)": "Entradas (JSON)", "What it expects": "O que ela espera", "Run": "Executar",
 "only reads": "só lê", "changes data": "altera dados", "the inputs are not valid JSON": "as entradas não são um JSON válido",
 "New tools go live only after another person approves them.": "Ferramentas novas só entram no ar depois que outra pessoa aprova.",
 "Submitted tools": "Ferramentas enviadas", "No tools submitted yet.": "Nenhuma ferramenta enviada ainda.",
 "Submit a new tool": "Enviar uma ferramenta nova",
 "Describe the tool as JSON. Passwords go in Passwords & keys and are referenced as {{secret:name}}. Addresses that aren't https, or point to private networks, are refused.":
   "Descreva a ferramenta em JSON. Senhas ficam em Senhas e chaves e são citadas como {{secret:nome}}. Endereços sem https, ou de redes privadas, são recusados.",
 "Send for review": "Enviar para revisão", "Sent. Another person needs to approve it.": "Enviado. Outra pessoa precisa aprovar.",
 "You need the registry.write permission to submit tools.": "Você precisa da permissão registry.write para enviar ferramentas.",
 "waiting for review": "aguardando revisão", "live": "no ar", "rejected": "rejeitada", "replaced": "substituída",
 "Version": "Versão", "Approve": "Aprovar", "Reject": "Rejeitar",
 "Every action is recorded with personal data masked. Each entry is sealed with the one before it, so any edit is detected.":
   "Toda ação fica registrada com dados pessoais mascarados. Cada registro é selado junto com o anterior, então qualquer edição é detectada.",
 "One request": "Uma requisição", "Show everything": "Mostrar tudo", "Nothing recorded yet.": "Nada registrado ainda.",
 "When": "Quando", "What": "O quê", "Who": "Quem", "Tool": "Ferramenta", "Result": "Resultado", "Seal": "Selo",
 "Entry": "Registro", "Data (personal info masked)": "Dados (informações pessoais mascaradas)",
 "Seal of the previous entry": "Selo do registro anterior", "Seal of this entry": "Selo deste registro", "first entry": "primeiro registro",
 "Close": "Fechar",
 "Used a tool": "Usou uma ferramenta", "Signed in": "Entrou", "Password or key": "Senha ou chave", "Tool registry": "Cadastro de ferramentas", "Permissions": "Permissões",
 "ok": "ok", "failed": "falhou", "denied": "negado", "stored": "guardado", "proposed": "enviado", "approved": "aprovado", "deleted": "excluído",
 "consumer_created": "sistema criado", "error": "erro",
 "Who can use what. Each role lists the tools it can call.": "Quem pode usar o quê. Cada perfil lista as ferramentas que pode chamar.",
 "People and systems": "Pessoas e sistemas", "Name": "Nome", "Type": "Tipo", "Role": "Perfil", "Status": "Situação",
 "person": "pessoa", "system": "sistema", "active": "ativo", "blocked": "bloqueado", "Block": "Bloquear", "Unblock": "Desbloquear",
 "Roles": "Perfis", "Connect another system": "Conectar outro sistema", "system name, e.g. grants-sync": "nome do sistema, ex.: grants-sync",
 "Create": "Criar", "Copy this key now. It won't be shown again.": "Copie esta chave agora. Ela não aparece de novo.",
 "Stored encrypted. Tools refer to them by name, and the values are never shown again.":
   "Guardadas criptografadas. As ferramentas usam pelo nome, e o valor nunca aparece de novo.",
 "Yours": "Suas", "Shared with everyone": "Compartilhadas com todos", "None yet.": "Nenhuma ainda.", "Delete": "Excluir",
 "Save a password or key": "Guardar uma senha ou chave", "name (lowercase_underscores)": "nome (minusculas_com_underline)",
 "value, never shown again": "valor, nunca exibido de novo", "share with everyone": "compartilhar com todos",
 "Save encrypted": "Guardar criptografado", "Saved, encrypted.": "Guardado, criptografado.",
 "Invoices": "Notas fiscais", "Agreements": "Convênios", "About the system": "Sobre o sistema",
 "proposing needs the registry.write permission": "propor exige a permissão registry.write",
 "open in the console": "abrir no console", "no tool matches": "nenhuma tool encontrada", "admin perms": "permissões de admin",
 "see this request in the audit trail": "ver esta requisição na trilha de auditoria", "request": "requisição",
 "show all": "mostrar tudo", "No events.": "Nenhum evento.",
 "Conversations": "Conversas", "+ new": "+ nova", "messages": "mensagens", "message": "mensagem", "waiting": "aguardando",
 "Rename": "Renomear", "Delete": "Excluir", "New title": "Novo título", "Delete this conversation?": "Excluir esta conversa?",
 "No conversations yet.": "Nenhuma conversa ainda.",
 "Workspace": "Espaço de trabalho",
 "exit": "sair",
 "Log out": "Sair",
 "Sign in →": "Entrar →",
 "One gateway.": "Um gateway.",
 "Every tool, governed.": "Toda tool, governada.",
 "Per-tool permissions, encrypted secrets and a tamper-evident trail in front of every MCP tool.": "Permissão por tool, secrets criptografados e uma trilha à prova de adulteração na frente de toda tool MCP.",
 "audit hidden": "auditoria oculta",
 "No calls yet. Open the console and run a tool.": "Nenhuma chamada ainda. Abra o console e rode uma tool.",
 "Tools visible to you": "Tools visíveis para você",
 "Calls": "Chamadas",
 "Error rate": "Taxa de erro",
 "Per tool": "Por tool",
 "Domains": "Domínios",
 "Overview": "Visão geral",
 "last 24 hours": "últimas 24 horas",
 "filter tools…": "filtrar tools…",
 "Pick a tool, or describe what you need above.": "Escolha uma tool ou descreva o que precisa acima.",
 "arguments are not valid JSON": "os argumentos não são um JSON válido",
 "Arguments": "Argumentos",
 "Input schema": "Schema de entrada",
 "Run ▸": "Executar ▸",
 "read-only": "somente leitura",
 "writes": "escreve",
 "Suggest": "Sugerir",
 "no confident match": "nenhuma sugestão confiável",
 "call any tool you are allowed to": "chame qualquer tool que você tem permissão",
 "Console": "Console",
 "draft created — another reviewer must approve it": "rascunho criado — outra pessoa precisa aprovar",
 "approve": "aprovar",
 "reject": "rejeitar",
 "Revisions": "Revisões",
 "No dynamic tools yet.": "Nenhuma tool dinâmica ainda.",
 "Propose": "Propor",
 "Credentials go in Secrets and are referenced as {{secret:name}}. Literal keys, http:// and private addresses are rejected.": "Credenciais ficam em Secrets e são referenciadas como {{secret:nome}}. Chaves literais, http:// e endereços privados são rejeitados.",
 "Submit draft": "Enviar rascunho",
 "Registry": "Registro",
 "dynamic tools · four-eyes review": "tools dinâmicas · revisão a quatro olhos",
 "close": "fechar",
 "Payload (masked at write time)": "Payload (mascarado na gravação)",
 "Audit trail": "Trilha de auditoria",
 "sha-256 hash chain · PII masked": "cadeia de hashes sha-256 · dados pessoais mascarados",
 "consumer id, e.g. grants-sync": "id do consumidor, ex.: grants-sync",
 "API key — shown once": "chave de API — exibida uma única vez",
 "block": "bloquear",
 "unblock": "desbloquear",
 "Access": "Acesso",
 "principals · roles · tool globs": "usuários · papéis · padrões de tools",
 "Principals": "Usuários e serviços",
 "New service consumer": "Novo consumidor de serviço",
 "Create": "Criar",
 "name (lowercase_underscores)": "nome (minusculas_com_underline)",
 "value — never shown again": "valor — nunca exibido de novo",
 "stored, encrypted": "guardado, criptografado",
 "delete": "excluir",
 "none": "nenhum",
 "Secrets": "Secrets",
 "fernet-encrypted · names only": "criptografados com fernet · só os nomes",
 "Yours": "Seus",
 "Shared (__system__)": "Compartilhados (__system__)",
 "Store a secret": "Guardar um secret",
 "shared with everyone": "compartilhado com todos",
 "Encrypt & store": "Criptografar e guardar",
 "Errors": "Erros",
 "When": "Quando",
 "Kind": "Tipo",
 "Actor": "Ator",
 "Outcome": "Resultado",
 "Hash": "Hash",
 "Id": "Id",
 "Status": "Situação",
 "Rev": "Rev",
 "Author": "Autor",
 "Describe what you need — e.g. “quais convênios estão atrasados em MS?”": "Descreva o que precisa — ex.: “quais convênios estão atrasados em MS?”",
 "Chat": "Chat",
 "ask in plain language · every call governed and audited": "pergunte em linguagem natural · toda chamada governada e auditada",
 "Ask about invoices, tax ids or agreements…": "Pergunte sobre notas, CPF/CNPJ ou convênios…",
 "Send ▸": "Enviar ▸",
 "how it was answered": "como foi respondido",
 "raw result": "resultado bruto",
 "new conversation": "nova conversa",
 "engine": "motor",
 "Hi! Ask me about invoices, CPF/CNPJ or public-transfer agreements. Every answer comes from a real tool call, checked against your permissions and written to the audit trail.": "Olá! Pergunte sobre notas fiscais, CPF/CNPJ ou convênios. Toda resposta vem de uma chamada real de tool, checada contra suas permissões e registrada na trilha de auditoria.",
 "waiting for your answer": "aguardando sua resposta",
 "dynamic": "dinâmica",
 "chain verified": "cadeia verificada",
 "broken at": "quebrada em",
 "verified": "verificados",
 "events": "eventos",
 "tampered at": "adulterada em",
 "native": "nativa"
};
let lang = (() => { try { return localStorage.getItem("lang"); } catch { return null; } })()
  || ((navigator.language || "").toLowerCase().startsWith("pt") ? "pt" : "en");
const t = (s) => (lang === "pt" && PT[s]) || s;
function setLang(l) { lang = l; try { localStorage.setItem("lang", l); } catch {} document.documentElement.lang = l === "pt" ? "pt-BR" : "en"; render(); }
function langToggle() {
  return h("span", { class: "lang" }, ["en", "pt"].map((l) => h("button", { class: lang === l ? "on" : "", onclick: () => setLang(l) }, l.toUpperCase())));
}

// ------------------------------------------------------------------ helpers

function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "style") el.style.cssText = v; // CSSOM, allowed by the CSP (inline style attributes are not)
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

async function api(path, { method = "GET", body } = {}) {
  const res = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-Requested-With": "gateway-panel" },
    body: body === undefined ? undefined : JSON.stringify(body),
    credentials: "same-origin",
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.message || res.statusText), { status: res.status, data });
  return data;
}

function toast(message, bad = false) {
  const t = h("div", { class: "toast" + (bad ? " bad" : "") }, message);
  document.body.append(t);
  setTimeout(() => t.remove(), 3200);
}

const fmt = {
  time: (ts) => new Date(ts * 1000).toLocaleString(undefined, { hour12: false }),
  pct: (x) => `${(x * 100).toFixed(1)}%`,
  num: (x) => new Intl.NumberFormat().format(x),
};

// JSON → highlighted <pre>, built from text nodes only.
function jsonView(value) {
  const pre = h("pre", { class: "json" });
  const text = JSON.stringify(value, null, 2) ?? "null";
  const re = /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g;
  let last = 0;
  for (const m of text.matchAll(re)) {
    pre.append(text.slice(last, m.index));
    const cls = m[1] ? (m[2] ? "k" : "s") : m[3] ? "b" : "n";
    pre.append(h("span", { class: cls }, m[1] || m[3] || m[4]), m[2] || "");
    last = m.index + m[0].length;
  }
  pre.append(text.slice(last));
  return pre;
}

function skeleton(schema) {
  const out = {};
  for (const [k, p] of Object.entries(schema.properties || {})) {
    if (!(schema.required || []).includes(k)) continue;
    out[k] = p.enum ? p.enum[0] : p.type === "integer" || p.type === "number" ? 0 : p.type === "boolean" ? false
      : p.type === "object" ? {} : "";
  }
  return out;
}

const can = (perm) => state.me?.admin_perms.includes(perm);

// ------------------------------------------------------------------ shell

const ROUTES = [
  ["chat", "Assistant", "01"],
  ["overview", "Dashboard", "02"],
  ["console", "Tools", "03"],
  ["registry", "Add tools", "04"],
  ["audit", "Activity log", "05", "audit.read"],
  ["access", "People & permissions", "06", "access.admin"],
  ["secrets", "Passwords & keys", "07"],
];
const DOMAINS = { invoices: "Invoices", grants: "Agreements", meta: "About the system", registry: "Tool registry" };

function shell(title, eyebrow, actions, ...content) {
  const nav = h("nav", { class: "nav" },
    ROUTES.filter(([, , , perm]) => !perm || can(perm)).map(([id, label, k]) =>
      h("a", { href: `#/${id}`, class: state.route === id ? "active" : "" }, t(label), h("span", { class: "k" }, k))),
  );
  return h("div", { class: "app" },
    h("aside", { class: "sidebar" },
      h("div", { class: "brand" },
        h("div", { class: "brand-mark" }, h("i"), h("i"), h("i"), h("i")),
        h("div", { class: "brand-name" }, "toolgate")),
      nav,
      h("div", { class: "row", style: "padding:0 10px 12px" }, langToggle()),
      h("div", { class: "whoami" },
        h("div", {}, h("b", {}, state.me.name), h("span", { class: "label" }, state.me.role)),
        h("button", { class: "btn ghost", onclick: logout }, t("Log out")))),
    h("main", { class: "main" },
      h("div", { class: "topbar" },
        h("div", {}, h("h1", {}, title), eyebrow ? h("p", { class: "intro", style: "margin-top:6px" }, eyebrow) : null),
        h("div", { class: "row" }, actions)),
      h("div", { class: "content" }, content)));
}

async function logout() {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  state.me = null;
  render();
}

// ------------------------------------------------------------------ login

function loginView() {
  const user = h("input", { class: "input", placeholder: t("user"), autocomplete: "username", value: "admin" });
  const pass = h("input", { class: "input", placeholder: t("password"), type: "password", autocomplete: "current-password" });
  const submit = async (e) => {
    e.preventDefault();
    try {
      state.me = await api("/api/login", { method: "POST", body: { user: user.value, password: pass.value } });
      render();
    } catch (err) { toast(err.message, true); }
  };
  return h("div", { class: "login" },
    h("div", { class: "card" },
      h("div", { class: "brand", style: "padding:0" },
        h("div", { class: "brand-mark" }, h("i"), h("i"), h("i"), h("i")),
        h("div", { class: "brand-name" }, "toolgate")),
      h("h1", {}, t("Control what your AI assistant can do.")),
      h("p", { class: "muted" }, t("Choose who can use each tool, keep passwords encrypted and see a record of every action.")),
      h("form", { onsubmit: submit }, user, pass, h("button", { class: "btn primary", type: "submit" }, t("Sign in"))),
      h("div", { class: "hint muted" }, `${t("Demo accounts")}: admin/admin · analyst/analyst · auditor/auditor`),
      h("div", { style: "margin-top:14px" }, langToggle())));
}


// ------------------------------------------------------------------ chat

const EXAMPLES = {
  pt: ["valida o CNPJ 11.222.333/0001-81", "quais convênios estão atrasados em MS?", "calcula a retenção da NF-100010",
       "resumo dos convênios por estado", "valida um cpf pra mim"],
  en: ["validate CNPJ 11.222.333/0001-81", "which agreements are overdue in GO?", "compute withholding for NF-100010",
       "agreement totals by state", "show agreement AG-2024-1001"],
};

async function sendChat(text) {
  text = text.trim();
  if (!text || state.chatBusy) return;
  state.chat.push({ role: "user", text });
  state.chatBusy = true;
  render();
  try {
    const r = await api("/api/chat", { method: "POST", body: { message: text, lang, conversation_id: state.chatId } });
    state.chat.push({ role: "bot", ...r });
    if (state.chatId !== r.conversation_id) {
      state.chatId = r.conversation_id;
      history.replaceState(null, "", `#/chat/${r.conversation_id}`);
    }
  } catch (e) {
    state.chat.push({ role: "bot", text: e.message, error: { error: "request_failed" } });
  }
  state.chatBusy = false;
  try { state.convs = await api("/api/conversations"); } catch {}
  render();
}

function correlationLink(id) {
  if (!id) return null;
  return can("audit.read")
    ? h("a", { class: "chip", href: `#/audit/${id}`, title: id }, t("View in activity log"))
    : null;
}

const avatar = () => h("div", { class: "avatar" }, h("i"), h("i"), h("i"), h("i"));

function bubble(m) {
  if (m.role === "user") return h("div", { class: "msg user" }, h("div", { class: "bubble" }, m.text));
  const ok = m.result !== undefined && m.result !== null;
  const meta = h("div", { class: "meta-row", style: "margin-top:8px" },
    m.tool ? h("span", { class: "chip violet" }, `${t("Used")} ${m.tool}`) : null,
    m.error ? h("span", { class: "chip bad" }, m.error.error) : ok ? h("span", { class: "chip ok" }, h("i", { class: "dot" }), "ok") : null,
    m.pending ? h("span", { class: "chip warn" }, t("waiting for your answer")) : null,
    correlationLink(m.correlation));
  const details = [];
  if (m.trace?.length) details.push(h("details", {}, h("summary", { class: "label" }, t("How I got this answer")), jsonView(m.trace)));
  if (ok) details.push(h("details", {}, h("summary", { class: "label" }, t("Raw data")), jsonView(m.result)));
  return h("div", { class: "msg bot" }, avatar(),
    h("div", { class: "bubble" }, h("div", {}, m.text), m.tool || m.correlation ? meta : null, details));
}

async function openConversation(id) {
  if (!id) { state.chat = []; state.chatId = null; return; }
  if (state.chatId === id && state.chat.length) return;
  try {
    const c = await api(`/api/conversations/${id}`);
    state.chat = c.messages;
    state.chatId = id;
  } catch { state.chat = []; state.chatId = null; history.replaceState(null, "", "#/chat"); }
}

function when(ts) {
  const d = new Date(ts * 1000), now = new Date();
  return d.toDateString() === now.toDateString()
    ? d.toLocaleTimeString(lang === "pt" ? "pt-BR" : "en", { hour: "2-digit", minute: "2-digit" })
    : d.toLocaleDateString(lang === "pt" ? "pt-BR" : "en", { day: "2-digit", month: "short" });
}

function historyPanel() {
  const rename = async (c) => {
    const title = prompt(t("New title"), c.title);
    if (title) { await api(`/api/conversations/${c.id}`, { method: "PATCH", body: { title } }); render(); }
  };
  const remove = async (c) => {
    if (!confirm(t("Delete this conversation?"))) return;
    await api(`/api/conversations/${c.id}`, { method: "DELETE" });
    if (state.chatId === c.id) { state.chat = []; state.chatId = null; location.hash = "#/chat"; }
    render();
  };
  return h("section", { class: "card conv-list" },
    h("header", {}, h("span", { class: "label" }, t("Conversations")),
      h("a", { class: "btn", href: "#/chat", onclick: () => { state.chat = []; state.chatId = null; setTimeout(render, 0); } }, t("New chat"))),
    state.convs.length ? h("div", {}, state.convs.map((c) => h("div", { class: "conv" + (c.id === state.chatId ? " active" : "") },
      h("a", { href: `#/chat/${c.id}`, class: "conv-main" },
        h("div", { class: "conv-title" }, c.title),
        h("div", { class: "label" }, `${when(c.updated_at)} · ${c.messages} ${t(c.messages === 1 ? "message" : "messages")}`,
          c.pending ? h("span", { class: "chip warn", style: "margin-left:6px" }, t("waiting")) : null)),
      h("div", { class: "conv-actions" },
        h("button", { class: "btn ghost", title: t("Rename"), onclick: () => rename(c) }, "✎"),
        h("button", { class: "btn ghost", title: t("Delete"), onclick: () => remove(c) }, "×")))))
      : h("div", { class: "empty" }, t("No conversations yet.")));
}

async function chatView() {
  await openConversation(state.param);
  state.convs = await api("/api/conversations");
  const input = h("textarea", { class: "input chat-input", rows: 2, placeholder: t("Ask about invoices, tax ids or agreements…") });
  input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(input.value); } });
  const log = h("div", { class: "chat-log" },
    h("div", { class: "msg bot" }, avatar(), h("div", { class: "bubble" },
      t("Hi! I can check tax IDs (CPF/CNPJ), look up invoices and public-transfer agreements. Try one of the examples below."))),
    state.chat.map(bubble),
    state.chatBusy ? h("div", { class: "msg bot" }, avatar(), h("div", { class: "bubble typing" }, h("i"), h("i"), h("i"))) : null);
  setTimeout(() => { log.scrollTop = log.scrollHeight; input.focus(); }, 0);
  return shell(t("Assistant"), t("Ask in plain language. I only use the tools you're allowed to, and every answer is recorded."), null,
    h("div", { class: "chat-layout" }, historyPanel(),
    h("section", { class: "card chat" },
      log,
      h("div", { class: "chat-examples" }, EXAMPLES[lang].map((ex) => h("button", { class: "suggestion", onclick: () => sendChat(ex) }, ex))),
      h("form", { class: "chat-form", onsubmit: (e) => { e.preventDefault(); sendChat(input.value); } },
        input, h("button", { class: "btn primary", type: "submit", disabled: state.chatBusy }, t("Send"))))));
}

// ------------------------------------------------------------------ overview

async function overviewView() {
  const tools = state.tools;
  let stats = null, chain = null;
  if (can("audit.read")) [stats, chain] = await Promise.all([api("/api/audit/stats"), api("/api/audit/verify")]);
  const calls = stats?.total_calls ?? 0;
  const errors = stats ? stats.tools.reduce((a, row) => a + row.errors, 0) : 0;
  const dynamic = tools.filter((tool) => tool.origin === "dynamic").length;

  const kpi = (label, value, unit) => h("div", { class: "kpi" }, h("div", { class: "label" }, t(label)),
    h("div", { class: "v" }, value, unit ? h("small", {}, unit) : null));

  const chainChip = !chain ? h("span", { class: "chip" }, t("log hidden"))
    : h("a", { class: chain.ok ? "chip ok" : "chip bad", href: "#/audit" }, h("i", { class: "dot" }),
      chain.ok ? `${t("Log intact")} · ${chain.checked}` : `${t("Log was altered at entry")} #${chain.first_broken_seq}`);

  // every row opens the tool in the console
  const maxCalls = Math.max(1, ...(stats?.tools || []).map((row) => row.calls));
  const table = stats && stats.tools.length
    ? h("table", {},
      h("thead", {}, h("tr", {}, [t("Tool"), t("Calls"), "", t("Errors"), t("Typical time")].map((c) => h("th", {}, c)))),
      h("tbody", {}, stats.tools.map((row) => h("tr", { class: "clickable", title: t("open in the console"), onclick: () => { location.hash = `#/console/${row.tool}`; } },
        h("td", {}, h("div", {}, state.tools.find((tool) => tool.name === row.tool)?.title || row.tool), h("div", { class: "hash" }, row.tool)),
        h("td", {}, fmt.num(row.calls)),
        h("td", {}, h("div", { class: "bar" }, h("i", { style: `width:${(row.calls / maxCalls) * 100}%` }))),
        h("td", {}, row.errors ? h("span", { class: "chip bad" }, `${row.errors} · ${fmt.pct(row.error_rate)}`) : h("span", { class: "muted mono" }, "0")),
        h("td", { class: "muted" }, `${row.p50_ms} ms`)))))
    : h("div", { class: "empty" }, t("No calls yet. Ask the assistant something."));

  const domains = {};
  tools.forEach((tool) => { (domains[tool.domain] ||= []).push(tool); });

  return shell(t("Dashboard"), t("What's happening in the last 24 hours."), chainChip,
    h("div", { class: "grid kpis" },
      kpi("Tools you can use", tools.length, dynamic ? `${dynamic} ${t("added from the panel")}` : t("built-in")),
      kpi("Calls today", fmt.num(calls)),
      kpi("Errors", calls ? fmt.pct(errors / calls) : "—"),
      kpi("Your role", state.me.role, state.me.admin_perms.length ? `${state.me.admin_perms.length} ${t("admin permissions")}` : "")),
    h("div", { class: "grid wide" },
      h("section", { class: "card scroll" }, h("header", {}, h("span", { class: "label" }, t("Most used tools"))), table),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Tool groups"))),
        h("div", { class: "body stack" }, Object.entries(domains).map(([d, ts]) => h("a", { class: "row domain-row", href: `#/console/${d}` },
          h("span", {}, t(DOMAINS[d] || d)),
          h("span", { class: "row" }, h("span", { class: "muted" }, `${ts.length} ${t("tools")}`),
            ts.some((tool) => tool.origin === "dynamic") ? h("span", { class: "chip violet" }, t("added from the panel")) : null)))))));
}

// ------------------------------------------------------------------ console

async function consoleView() {
  // "#/console/<tool>" opens that tool; "#/console/<domain>" filters the list
  const fromLink = state.param && state.tools.find((tool) => tool.name === state.param);
  if (fromLink) state.selected = fromLink;
  const filter = h("input", { class: "input", placeholder: t("search tools…"), value: state.param && !fromLink ? state.param : "" });
  const list = h("div", { class: "toollist" });
  const detail = h("div", { class: "stack" });

  const drawList = () => {
    list.replaceChildren();
    const q = filter.value.toLowerCase();
    const groups = {};
    state.tools.filter((tool) => !q || tool.name.includes(q) || tool.domain.includes(q) || tool.title.toLowerCase().includes(q))
      .forEach((tool) => (groups[tool.domain] ||= []).push(tool));
    for (const [d, ts] of Object.entries(groups)) {
      list.append(h("div", { class: "group label" }, t(DOMAINS[d] || d)));
      ts.forEach((tool) => list.append(h("button", {
        class: "tool-item" + (state.selected?.name === tool.name ? " active" : ""),
        onclick: () => pick(tool),
      }, h("div", { class: "n" }, tool.title), h("div", { class: "t mono" }, tool.name))));
    }
    if (!Object.keys(groups).length) list.append(h("div", { class: "empty" }, t("no tool matches")));
  };

  const pick = (tool) => {
    state.selected = tool;
    history.replaceState(null, "", `#/console/${tool.name}`);
    drawList(); drawDetail();
  };

  const drawDetail = () => {
    const tool = state.selected;
    if (!tool) { detail.replaceChildren(h("div", { class: "card empty" }, t("Pick a tool on the left."))); return; }
    const args = h("textarea", { spellcheck: "false" });
    args.value = JSON.stringify(skeleton(tool.input_schema), null, 2);
    const out = h("div", { class: "stack" });
    const run = async () => {
      let parsed;
      try { parsed = JSON.parse(args.value || "{}"); } catch { toast(t("the inputs are not valid JSON"), true); return; }
      const r = await api("/api/call", { method: "POST", body: { tool: tool.name, arguments: parsed } });
      out.replaceChildren(
        h("div", { class: "meta-row" },
          h("span", { class: r.ok ? "chip ok" : "chip bad" }, h("i", { class: "dot" }), r.ok ? "ok" : r.error.error),
          h("span", { class: "chip" }, `${r.duration_ms} ms`),
          correlationLink(r.correlation)),
        jsonView(r.ok ? r.result : r.error));
    };
    detail.replaceChildren(
      h("section", { class: "card" },
        h("header", {},
          h("div", {}, h("div", { style: "font-weight:600;font-size:17px" }, tool.title), h("div", { class: "mono muted" }, tool.name)),
          h("div", { class: "row" },
            tool.origin === "dynamic" ? h("span", { class: "chip violet" }, t("added from the panel")) : null,
            h("span", { class: tool.read_only ? "chip" : "chip warn" }, tool.read_only ? t("only reads") : t("changes data")))),
        h("div", { class: "body stack" },
          h("p", { class: "muted", style: "margin:0" }, tool.description),
          h("div", { class: "grid two" },
            h("div", { class: "field" }, h("span", { class: "label" }, t("Inputs (JSON)")), args,
              h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => run().catch((e) => toast(e.message, true)) }, t("Run")))),
            h("div", { class: "field" }, h("span", { class: "label" }, t("What it expects")), jsonView(tool.input_schema))))),
      out);
  };

  const ask = h("input", { class: "input", placeholder: t("Describe what you need, e.g. “quais convênios estão atrasados em MS?”") });
  const sugg = h("div", { class: "suggestions" });
  const suggest = async (e) => {
    e?.preventDefault();
    if (ask.value.trim().length < 3) return;
    const hits = await api("/api/suggest", { method: "POST", body: { request: ask.value } });
    sugg.replaceChildren(...(hits.length ? hits.map((s) => h("button", {
      class: "suggestion", title: s.reasons.join(" · "),
      onclick: () => pick(state.tools.find((tool) => tool.name === s.tool)),
    }, state.tools.find((tool) => tool.name === s.tool)?.title || s.tool)) : [h("span", { class: "muted" }, t("No good match. Try other words."))]));
  };

  filter.addEventListener("input", drawList);
  drawList(); drawDetail();
  return shell(t("Tools"), t("Run any tool you have access to, or describe what you need and I'll find it."), null,
    h("form", { class: "ask", onsubmit: suggest }, ask, h("button", { class: "btn", type: "submit" }, t("Find tool"))),
    sugg,
    h("div", { class: "grid split" },
      h("section", { class: "card" }, h("header", {}, filter), list),
      detail));
}

// ------------------------------------------------------------------ registry

const TEMPLATE = {
  name: "weather.forecast",
  title: "Daily forecast",
  description: "Forecast for a city from an example upstream API.",
  input_schema: { type: "object", properties: { city: { type: "string" } }, required: ["city"] },
  http: { method: "GET", url: "https://api.example.org/v1/forecast/{city}", headers: { Authorization: "Bearer {{secret:weather_token}}" } },
  read_only: true,
  keywords: ["previsao", "tempo", "forecast"],
};

async function registryView() {
  const revs = await api("/api/registry");
  const editor = h("textarea", { spellcheck: "false", style: "min-height:320px" });
  editor.value = JSON.stringify(TEMPLATE, null, 2);
  const propose = async () => {
    try {
      await api("/api/registry/propose", { method: "POST", body: { definition: JSON.parse(editor.value) } });
      toast(t("Sent. Another person needs to approve it.")); render();
    } catch (e) { toast(e.data?.message || e.message, true); }
  };
  const review = async (r, approve) => {
    try { await api("/api/registry/review", { method: "POST", body: { name: r.name, revision: r.revision, approve } }); render(); }
    catch (e) { toast(e.message, true); }
  };
  const chip = { draft: "chip warn", approved: "chip ok", disabled: "chip bad", superseded: "chip" };
  const status = { draft: "waiting for review", approved: "live", disabled: "rejected", superseded: "replaced" };
  return shell(t("Add tools"), t("New tools go live only after another person approves them."), null,
    h("div", { class: "grid wide" },
      h("section", { class: "card scroll" }, h("header", {}, h("span", { class: "label" }, t("Submitted tools")), h("span", { class: "muted" }, `${revs.length}`)),
        revs.length ? h("table", {}, h("thead", {}, h("tr", {}, [t("Tool"), t("Version"), t("Status"), t("Who"), ""].map((c) => h("th", {}, c)))),
          h("tbody", {}, revs.slice().reverse().map((r) => h("tr", {},
            h("td", {}, h("div", { class: "mono" }, r.name), h("div", { class: "hash" }, r.definition.http.url)),
            h("td", {}, r.revision),
            h("td", {}, h("span", { class: chip[r.status] }, t(status[r.status] || r.status))),
            h("td", {}, r.author, r.reviewer ? h("div", { class: "label" }, `✓ ${r.reviewer}`) : null),
            h("td", {}, r.status === "draft" && can("registry.review") && r.author !== state.me.id
              ? h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => review(r, true) }, t("Approve")),
                h("button", { class: "btn danger", onclick: () => review(r, false) }, t("Reject")))
              : null)))))
          : h("div", { class: "empty" }, t("No tools submitted yet."))),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Submit a new tool"))),
        h("div", { class: "body stack" },
          h("p", { class: "muted", style: "margin:0" }, t("Describe the tool as JSON. Passwords go in Passwords & keys and are referenced as {{secret:name}}. Addresses that aren't https, or point to private networks, are refused.")),
          editor,
          can("registry.write") ? h("div", { class: "row" }, h("button", { class: "btn primary", onclick: propose }, t("Send for review")))
            : h("span", { class: "chip" }, t("You need the registry.write permission to submit tools."))))));
}

// ------------------------------------------------------------------ audit

const KINDS = { tool_call: "Used a tool", login: "Signed in", secret: "Password or key", registry: "Tool registry", access: "Permissions" };

async function auditView() {
  const corr = state.param;
  const [events, chain] = await Promise.all([
    api(corr ? `/api/audit?correlation=${encodeURIComponent(corr)}` : "/api/audit?limit=300"), api("/api/audit/verify")]);
  const drawer = h("aside", { class: "drawer" });
  const open = (e) => {
    drawer.replaceChildren(
      h("header", {}, h("div", {}, h("div", { class: "label" }, `${t("Entry")} #${e.seq}`), h("b", {}, t(KINDS[e.kind] || e.kind))),
        h("button", { class: "btn ghost", onclick: () => drawer.classList.remove("open") }, t("Close"))),
      h("div", { class: "body" },
        h("div", { class: "meta-row" }, h("span", { class: "chip" }, e.actor || "—"), e.tool ? h("span", { class: "chip violet" }, e.tool) : null,
          h("span", { class: e.outcome === "ok" ? "chip ok" : "chip warn" }, t(e.outcome || "—"))),
        h("div", { class: "field" }, h("span", { class: "label" }, t("Data (personal info masked)")), jsonView(e.payload)),
        h("div", { class: "field" }, h("span", { class: "label" }, t("Seal of the previous entry")), h("span", { class: "hash" }, e.prev_hash || t("first entry"))),
        h("div", { class: "field" }, h("span", { class: "label" }, t("Seal of this entry")), h("span", { class: "hash" }, e.hash))));
    drawer.classList.add("open");
  };
  return shell(t("Activity log"), t("Every action is recorded with personal data masked. Each entry is sealed with the one before it, so any edit is detected."), chain.ok
    ? h("span", { class: "chip ok" }, h("i", { class: "dot" }), `${t("Log intact")} · ${chain.checked}`)
    : h("span", { class: "chip bad" }, h("i", { class: "dot" }), `${t("Log was altered at entry")} #${chain.first_broken_seq}`),
    corr ? h("div", { class: "row" }, h("span", { class: "label" }, t("One request")), h("span", { class: "chip violet" }, corr),
      h("a", { class: "btn ghost", href: "#/audit" }, t("Show everything"))) : null,
    h("section", { class: "card scroll" },
      events.length ? null : h("div", { class: "empty" }, t("Nothing recorded yet.")),
      h("table", {}, h("thead", {}, h("tr", {}, ["#", t("When"), t("What"), t("Who"), t("Tool"), t("Result"), t("Seal")].map((c) => h("th", {}, c)))),
        h("tbody", {}, events.map((e) => h("tr", { class: "clickable", onclick: () => open(e) },
          h("td", { class: "muted" }, e.seq),
          h("td", {}, fmt.time(e.ts)),
          h("td", {}, t(KINDS[e.kind] || e.kind)),
          h("td", {}, e.actor || "—"),
          h("td", { class: "mono" }, e.tool || "—"),
          h("td", {}, h("span", { class: e.outcome === "ok" ? "chip ok" : "chip warn" }, t(e.outcome || "—"))),
          h("td", { class: "hash" }, e.hash.slice(0, 10))))))),
    drawer);
}

// ------------------------------------------------------------------ access

async function accessView() {
  const data = await api("/api/access");
  const id = h("input", { class: "input", placeholder: t("system name, e.g. grants-sync") });
  const role = h("select", {}, data.roles.map((r) => h("option", { value: r.name }, r.name)));
  const keyBox = h("div");
  const create = async () => {
    try {
      const r = await api("/api/access/consumers", { method: "POST", body: { id: id.value, role: role.value } });
      keyBox.replaceChildren(h("div", { class: "card body stack" }, h("span", { class: "label accent" }, t("Copy this key now. It won't be shown again.")),
        h("code", { class: "mono", style: "word-break:break-all" }, r.api_key)));
    } catch (e) { toast(e.message, true); }
  };
  const toggle = async (p) => {
    try { await api(`/api/access/principals/${p.id}/status`, { method: "POST", body: { status: p.status === "active" ? "blocked" : "active" } }); render(); }
    catch (e) { toast(e.message, true); }
  };
  const kinds = { user: "person", service: "system" };
  return shell(t("People & permissions"), t("Who can use what. Each role lists the tools it can call."), null,
    h("div", { class: "grid two" },
      h("section", { class: "card scroll" }, h("header", {}, h("span", { class: "label" }, t("People and systems"))),
        h("table", {}, h("thead", {}, h("tr", {}, [t("Name"), t("Type"), t("Role"), t("Status"), ""].map((c) => h("th", {}, c)))),
          h("tbody", {}, data.principals.map((p) => h("tr", {},
            h("td", {}, p.id), h("td", {}, h("span", { class: "chip" }, t(kinds[p.kind] || p.kind))),
            h("td", {}, p.role.name),
            h("td", {}, h("span", { class: p.status === "active" ? "chip ok" : "chip bad" }, t(p.status))),
            h("td", {}, p.id !== state.me.id ? h("button", { class: "btn ghost", onclick: () => toggle(p) }, p.status === "active" ? t("Block") : t("Unblock")) : null)))))),
      h("div", { class: "stack" },
        h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Roles"))),
          h("div", { class: "body stack" }, data.roles.map((r) => h("div", { class: "stack", style: "gap:6px" },
            h("div", { class: "row" }, h("b", {}, r.name), h("span", { class: "muted" }, r.description)),
            h("div", { class: "row" }, r.tool_globs.map((g) => h("span", { class: "chip ok" }, g)), r.admin_perms.map((g) => h("span", { class: "chip violet" }, g))))))),
        h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Connect another system"))),
          h("div", { class: "body stack" }, id, role, h("div", { class: "row" }, h("button", { class: "btn primary", onclick: create }, t("Create"))), keyBox)))));
}

// ------------------------------------------------------------------ secrets

async function secretsView() {
  const data = await api("/api/secrets");
  const name = h("input", { class: "input", placeholder: t("name (lowercase_underscores)") });
  const value = h("input", { class: "input", type: "password", placeholder: t("value, never shown again"), autocomplete: "off" });
  const shared = h("input", { type: "checkbox" });
  const save = async () => {
    try { await api("/api/secrets", { method: "PUT", body: { name: name.value, value: value.value, shared: shared.checked } }); toast(t("Saved, encrypted.")); render(); }
    catch (e) { toast(e.data?.detail?.[0]?.msg || e.message, true); }
  };
  const del = async (n, isShared) => { await api(`/api/secrets/${n}?shared=${isShared}`, { method: "DELETE" }); render(); };
  const list = (names, isShared) => names.length ? names.map((n) => h("div", { class: "row", style: "justify-content:space-between" },
    h("span", { class: "mono" }, `{{secret:${n}}}`), h("button", { class: "btn ghost", onclick: () => del(n, isShared) }, t("Delete"))))
    : [h("span", { class: "muted" }, t("None yet."))];
  return shell(t("Passwords & keys"), t("Stored encrypted. Tools refer to them by name, and the values are never shown again."), null,
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Yours"))), h("div", { class: "body stack" }, list(data.mine, false)),
        h("header", {}, h("span", { class: "label" }, t("Shared with everyone"))), h("div", { class: "body stack" }, list(data.shared, true))),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Save a password or key"))),
        h("div", { class: "body stack" }, name, value,
          can("secrets.write") ? h("label", { class: "row muted" }, shared, t("share with everyone")) : null,
          h("div", { class: "row" }, h("button", { class: "btn primary", onclick: save }, t("Save encrypted")))))));
}

// ------------------------------------------------------------------ router

const VIEWS = { chat: chatView, overview: overviewView, console: consoleView, registry: registryView, audit: auditView, access: accessView, secrets: secretsView };

async function render() {
  if (!state.me) {
    try { state.me = await api("/api/me"); } catch { root.replaceChildren(loginView()); return; }
  }
  const [route, param] = (location.hash.replace("#/", "") || "chat").split("?")[0].split("/");
  state.route = route;
  state.param = param || null;
  if (!VIEWS[state.route]) state.route = "chat";
  try {
    state.tools = await api("/api/tools");
    if (state.selected) state.selected = state.tools.find((tool) => tool.name === state.selected.name) || null;
    root.replaceChildren(await VIEWS[state.route]());
  } catch (e) {
    if (e.status === 401) { state.me = null; root.replaceChildren(loginView()); return; }
    toast(e.message, true);
  }
}

window.addEventListener("hashchange", render);
render();
