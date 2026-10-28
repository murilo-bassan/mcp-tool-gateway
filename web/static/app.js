// toolgate panel — vanilla JS, no build step.
// Every DOM node is created with h(); server data never goes through innerHTML.

const root = document.getElementById("root");
const state = { me: null, tools: [], selected: null, route: "chat", param: null, chat: [], chatId: null, convs: [], chatBusy: false };


// ------------------------------------------------------------------ i18n (EN source strings are the keys)

const PT = {
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
 "Role": "Papel",
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
 "Roles": "Papéis",
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
 "shared with everyone (needs secrets.write)": "compartilhado com todos (requer secrets.write)",
 "Encrypt & store": "Criptografar e guardar",
 "Tool": "Tool",
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
 "tools": "tools",
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
  ["chat", "Chat", "01"],
  ["overview", "Overview", "02"],
  ["console", "Console", "03"],
  ["registry", "Registry", "04"],
  ["audit", "Audit trail", "05", "audit.read"],
  ["access", "Access", "06", "access.admin"],
  ["secrets", "Secrets", "07"],
];

function shell(title, eyebrow, actions, ...content) {
  const nav = h("nav", { class: "nav" },
    h("div", { class: "label sep" }, t("Workspace")),
    ROUTES.filter(([, , , perm]) => !perm || can(perm)).map(([id, label, k]) =>
      h("a", { href: `#/${id}`, class: state.route === id ? "active" : "" }, t(label), h("span", { class: "k" }, k))),
  );
  return h("div", { class: "app" },
    h("aside", { class: "sidebar" },
      h("div", { class: "brand" },
        h("div", { class: "brand-mark" }, h("i"), h("i"), h("i"), h("i")),
        h("div", { class: "brand-name" }, "toolgate", h("span", {}, " /mcp"))),
      nav,
      h("div", { class: "row", style: "padding:0 10px 12px" }, langToggle()),
      h("div", { class: "whoami" },
        h("div", {}, h("b", {}, state.me.name), h("span", { class: "label" }, state.me.role)),
        h("button", { class: "btn ghost", onclick: logout, title: t("Log out") }, t("exit")))),
    h("main", { class: "main" },
      h("div", { class: "topbar" },
        h("div", {}, h("div", { class: "label" }, eyebrow), h("h1", {}, title)),
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
  const user = h("input", { class: "input", placeholder: "user", autocomplete: "username", value: "admin" });
  const pass = h("input", { class: "input", placeholder: "password", type: "password", autocomplete: "current-password" });
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
        h("div", { class: "brand-name" }, "toolgate", h("span", {}, " /mcp"))),
      h("h1", {}, t("One gateway."), h("br"), h("span", { class: "accent" }, t("Every tool, governed."))),
      h("p", { class: "muted" }, t("Per-tool permissions, encrypted secrets and a tamper-evident trail in front of every MCP tool.")),
      h("form", { onsubmit: submit }, user, pass, h("button", { class: "btn primary", type: "submit" }, t("Sign in →"))),
      h("div", { class: "hint mono muted" }, "demo: admin/admin · analyst/analyst · auditor/auditor"),
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

const avatar = () => h("div", { class: "avatar" }, h("i"), h("i"), h("i"), h("i"));

function bubble(m) {
  if (m.role === "user") return h("div", { class: "msg user" }, h("div", { class: "bubble" }, m.text));
  const ok = m.result !== undefined && m.result !== null;
  const meta = h("div", { class: "meta-row", style: "margin-top:8px" },
    m.tool ? h("span", { class: "chip violet" }, m.tool) : null,
    m.error ? h("span", { class: "chip bad" }, m.error.error) : ok ? h("span", { class: "chip ok" }, h("i", { class: "dot" }), "ok") : null,
    m.pending ? h("span", { class: "chip warn" }, t("waiting for your answer")) : null,
    m.correlation ? h("span", { class: "hash" }, m.correlation) : null);
  const details = [];
  if (m.trace?.length) details.push(h("details", {}, h("summary", { class: "label" }, t("how it was answered")), jsonView(m.trace)));
  if (ok) details.push(h("details", {}, h("summary", { class: "label" }, t("raw result")), jsonView(m.result)));
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
      h("a", { class: "btn primary", href: "#/chat", onclick: () => { state.chat = []; state.chatId = null; setTimeout(render, 0); } }, t("+ new"))),
    state.convs.length ? h("div", {}, state.convs.map((c) => h("div", { class: "conv" + (c.id === state.chatId ? " active" : "") },
      h("a", { href: `#/chat/${c.id}`, class: "conv-main" },
        h("div", { class: "conv-title" }, c.title),
        h("div", { class: "hash" }, `${when(c.updated_at)} · ${c.messages} ${t(c.messages === 1 ? "message" : "messages")}`,
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
      t("Hi! Ask me about invoices, CPF/CNPJ or public-transfer agreements. Every answer comes from a real tool call, checked against your permissions and written to the audit trail."))),
    state.chat.map(bubble),
    state.chatBusy ? h("div", { class: "msg bot" }, avatar(), h("div", { class: "bubble typing" }, h("i"), h("i"), h("i"))) : null);
  setTimeout(() => { log.scrollTop = log.scrollHeight; input.focus(); }, 0);
  return shell(t("Chat"), t("ask in plain language · every call governed and audited"),
    h("a", { class: "btn ghost", href: "#/chat", onclick: () => { state.chat = []; state.chatId = null; setTimeout(render, 0); } }, t("new conversation")),
    h("div", { class: "chat-layout" }, historyPanel(),
    h("section", { class: "card chat" },
      log,
      h("div", { class: "chat-examples" }, EXAMPLES[lang].map((ex) => h("button", { class: "suggestion", onclick: () => sendChat(ex) }, ex))),
      h("form", { class: "chat-form", onsubmit: (e) => { e.preventDefault(); sendChat(input.value); } },
        input, h("button", { class: "btn primary", type: "submit", disabled: state.chatBusy }, t("Send ▸"))))));
}

// ------------------------------------------------------------------ overview

async function overviewView() {
  const tools = state.tools;
  let stats = null, chain = null;
  if (can("audit.read")) [stats, chain] = await Promise.all([api("/api/audit/stats"), api("/api/audit/verify")]);
  const calls = stats?.total_calls ?? 0;
  const errors = stats ? stats.tools.reduce((a, t) => a + t.errors, 0) : 0;
  const dynamic = tools.filter((t) => t.origin === t("dynamic")).length;

  const kpi = (label, value, unit) => h("div", { class: "kpi" }, h("div", { class: "label" }, label),
    h("div", { class: "v" }, value, unit ? h("small", {}, unit) : null));

  const chainChip = !chain ? h("span", { class: "chip" }, t("audit hidden"))
    : chain.ok ? h("span", { class: "chip ok" }, h("i", { class: "dot" }), `${t("chain verified")} · ${chain.checked}`)
      : h("span", { class: "chip bad" }, h("i", { class: "dot" }), `broken at #${chain.first_broken_seq}`);

  const maxCalls = Math.max(1, ...(stats?.tools || []).map((t) => t.calls));
  const table = stats && stats.tools.length
    ? h("table", {},
      h("thead", {}, h("tr", {}, [t("Tool"), t("Calls"), "", t("Errors"), "p50", "p95"].map((c) => h("th", {}, c)))),
      h("tbody", {}, stats.tools.map((t) => h("tr", {},
        h("td", { class: "mono" }, t.tool),
        h("td", { class: "mono" }, fmt.num(t.calls)),
        h("td", {}, h("div", { class: "bar" }, h("i", { style: `width:${(t.calls / maxCalls) * 100}%` }))),
        h("td", {}, t.errors ? h("span", { class: "chip bad" }, `${t.errors} · ${fmt.pct(t.error_rate)}`) : h("span", { class: "muted mono" }, "0")),
        h("td", { class: "mono" }, `${t.p50_ms}ms`),
        h("td", { class: "mono" }, `${t.p95_ms}ms`)))))
    : h("div", { class: "empty" }, t("No calls yet. Open the console and run a tool."));

  const domains = {};
  tools.forEach((t) => { (domains[t.domain] ||= []).push(t); });

  return shell("Overview", t("last 24 hours"), chainChip,
    h("div", { class: "grid kpis" },
      kpi("Tools visible to you", tools.length, dynamic ? `${dynamic} dynamic` : t("native")),
      kpi("Calls", fmt.num(calls), "24h"),
      kpi("Error rate", calls ? fmt.pct(errors / calls) : "—"),
      kpi("Role", state.me.role, state.me.admin_perms.length ? `${state.me.admin_perms.length} admin perms` : "")),
    h("div", { class: "grid wide" },
      h("section", { class: "card scroll" }, h("header", {}, h("span", { class: "label" }, t("Per tool"))), table),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Domains"))),
        h("div", { class: "body stack" }, Object.entries(domains).map(([d, ts]) => h("div", { class: "row", style: "justify-content:space-between" },
          h("span", { class: "mono" }, d),
          h("span", { class: "row" }, h("span", { class: "muted mono" }, `${ts.length} ${t("tools")}`),
            ts.some((t) => t.origin === t("dynamic")) ? h("span", { class: "chip violet" }, t("dynamic")) : null)))))));
}

// ------------------------------------------------------------------ console

async function consoleView() {
  const filter = h("input", { class: "input", placeholder: t("filter tools…") });
  const list = h("div", { class: "toollist" });
  const detail = h("div", { class: "stack" });

  const drawList = () => {
    list.replaceChildren();
    const q = filter.value.toLowerCase();
    const groups = {};
    state.tools.filter((t) => !q || t.name.includes(q) || t.title.toLowerCase().includes(q))
      .forEach((t) => (groups[t.domain] ||= []).push(t));
    for (const [d, ts] of Object.entries(groups)) {
      list.append(h("div", { class: "group label" }, d));
      ts.forEach((t) => list.append(h("button", {
        class: "tool-item" + (state.selected?.name === t.name ? " active" : ""),
        onclick: () => { state.selected = t; drawList(); drawDetail(); },
      }, h("div", { class: "n" }, t.name), h("div", { class: "t" }, t.title))));
    }
  };

  const drawDetail = () => {
    const t = state.selected;
    if (!t) { detail.replaceChildren(h("div", { class: "card empty" }, t("Pick a tool, or describe what you need above."))); return; }
    const args = h("textarea", { spellcheck: "false" });
    args.value = JSON.stringify(skeleton(t.input_schema), null, 2);
    const out = h("div", { class: "stack" });
    const run = async () => {
      let parsed;
      try { parsed = JSON.parse(args.value || "{}"); } catch { toast("arguments are not valid JSON", true); return; }
      const r = await api("/api/call", { method: "POST", body: { tool: t.name, arguments: parsed } });
      out.replaceChildren(
        h("div", { class: "meta-row" },
          h("span", { class: r.ok ? "chip ok" : "chip bad" }, h("i", { class: "dot" }), r.ok ? "ok" : r.error.error),
          h("span", { class: "chip" }, `${r.duration_ms} ms`),
          h("span", { class: "hash" }, `correlation ${r.correlation}`)),
        jsonView(r.ok ? r.result : r.error));
    };
    detail.replaceChildren(
      h("section", { class: "card" },
        h("header", {},
          h("div", {}, h("div", { class: "mono accent" }, t.name), h("div", {}, t.title)),
          h("div", { class: "row" },
            h("span", { class: t.origin === t("dynamic") ? "chip violet" : "chip" }, t.origin + (t.revision ? ` r${t.revision}` : "")),
            h("span", { class: t.read_only ? "chip" : "chip warn" }, t.read_only ? t("read-only") : t("writes")))),
        h("div", { class: "body stack" },
          h("p", { class: "muted", style: "margin:0" }, t.description),
          h("div", { class: "grid two" },
            h("div", { class: "field" }, h("span", { class: "label" }, t("Arguments")), args,
              h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => run().catch((e) => toast(e.message, true)) }, t("Run ▸")))),
            h("div", { class: "field" }, h("span", { class: "label" }, t("Input schema")), jsonView(t.input_schema))))),
      out);
  };

  const ask = h("input", { class: "input", placeholder: t("Describe what you need — e.g. “quais convênios estão atrasados em MS?”") });
  const sugg = h("div", { class: "suggestions" });
  const suggest = async (e) => {
    e?.preventDefault();
    if (ask.value.trim().length < 3) return;
    const hits = await api("/api/suggest", { method: "POST", body: { request: ask.value } });
    sugg.replaceChildren(...(hits.length ? hits.map((s) => h("button", {
      class: "suggestion", title: s.reasons.join(" · "),
      onclick: () => { state.selected = state.tools.find((t) => t.name === s.tool); drawList(); drawDetail(); },
    }, s.tool, h("span", { class: "s" }, s.score.toFixed(2)))) : [h("span", { class: "muted mono" }, t("no confident match"))]));
  };

  filter.addEventListener("input", drawList);
  drawList(); drawDetail();
  return shell("Console", t("call any tool you are allowed to"), null,
    h("form", { class: "ask", onsubmit: suggest }, ask, h("button", { class: "btn", type: "submit" }, t("Suggest"))),
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
      toast("draft created — another reviewer must approve it"); render();
    } catch (e) { toast(e.data?.message || e.message, true); }
  };
  const review = async (r, approve) => {
    try { await api("/api/registry/review", { method: "POST", body: { name: r.name, revision: r.revision, approve } }); render(); }
    catch (e) { toast(e.message, true); }
  };
  const chip = { draft: "chip warn", approved: "chip ok", disabled: "chip bad", superseded: "chip" };
  return shell("Registry", t("dynamic tools · four-eyes review"), null,
    h("div", { class: "grid wide" },
      h("section", { class: "card scroll" }, h("header", {}, h("span", { class: "label" }, t("Revisions")), h("span", { class: "muted mono" }, `${revs.length}`)),
        revs.length ? h("table", {}, h("thead", {}, h("tr", {}, [t("Tool"), t("Rev"), t("Status"), t("Author"), ""].map((c) => h("th", {}, c)))),
          h("tbody", {}, revs.slice().reverse().map((r) => h("tr", {},
            h("td", {}, h("div", { class: "mono" }, r.name), h("div", { class: "hash" }, r.definition.http.url)),
            h("td", { class: "mono" }, r.revision),
            h("td", {}, h("span", { class: chip[r.status] }, r.status)),
            h("td", { class: "mono" }, r.author, r.reviewer ? h("div", { class: "hash" }, `✓ ${r.reviewer}`) : null),
            h("td", {}, r.status === "draft" && can("registry.review") && r.author !== state.me.id
              ? h("div", { class: "row" }, h("button", { class: "btn primary", onclick: () => review(r, true) }, t("approve")),
                h("button", { class: "btn danger", onclick: () => review(r, false) }, t("reject")))
              : null)))))
          : h("div", { class: "empty" }, t("No dynamic tools yet."))),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Propose")), h("span", { class: "chip violet" }, "JSON")),
        h("div", { class: "body stack" },
          h("p", { class: "muted", style: "margin:0" }, t("Credentials go in Secrets and are referenced as {{secret:name}}. Literal keys, http:// and private addresses are rejected.")),
          editor,
          h("div", { class: "row" }, h("button", { class: "btn primary", onclick: propose, disabled: !can("registry.write") }, t("Submit draft")))))));
}

// ------------------------------------------------------------------ audit

async function auditView() {
  const [events, chain] = await Promise.all([api("/api/audit?limit=300"), api("/api/audit/verify")]);
  const drawer = h("aside", { class: "drawer" });
  const open = (e) => {
    drawer.replaceChildren(
      h("header", {}, h("div", {}, h("div", { class: "label" }, `event #${e.seq}`), h("div", { class: "mono" }, e.kind)),
        h("button", { class: "btn ghost", onclick: () => drawer.classList.remove("open") }, t("close"))),
      h("div", { class: "body" },
        h("div", { class: "meta-row" }, h("span", { class: "chip" }, e.actor || "—"), e.tool ? h("span", { class: "chip violet" }, e.tool) : null,
          h("span", { class: e.outcome === "ok" ? "chip ok" : "chip warn" }, e.outcome || "—")),
        h("div", { class: "field" }, h("span", { class: "label" }, t("Payload (masked at write time)")), jsonView(e.payload)),
        h("div", { class: "field" }, h("span", { class: "label" }, "prev_hash"), h("span", { class: "hash" }, e.prev_hash || "genesis")),
        h("div", { class: "field" }, h("span", { class: "label" }, "hash"), h("span", { class: "hash" }, e.hash))));
    drawer.classList.add("open");
  };
  return shell("Audit trail", t("sha-256 hash chain · PII masked"), chain.ok
    ? h("span", { class: "chip ok" }, h("i", { class: "dot" }), `${t("verified")} ${chain.checked} ${t("events")}`)
    : h("span", { class: "chip bad" }, h("i", { class: "dot" }), `tampered at #${chain.first_broken_seq}`),
    h("section", { class: "card" },
      h("table", {}, h("thead", {}, h("tr", {}, ["#", t("When"), t("Kind"), t("Actor"), t("Tool"), t("Outcome"), "ms", t("Hash")].map((c) => h("th", {}, c)))),
        h("tbody", {}, events.map((e) => h("tr", { class: "clickable", onclick: () => open(e) },
          h("td", { class: "mono muted" }, e.seq),
          h("td", { class: "mono" }, fmt.time(e.ts)),
          h("td", {}, h("span", { class: "chip" }, e.kind)),
          h("td", { class: "mono" }, e.actor || "—"),
          h("td", { class: "mono" }, e.tool || "—"),
          h("td", {}, h("span", { class: e.outcome === "ok" ? "chip ok" : "chip warn" }, e.outcome || "—")),
          h("td", { class: "mono" }, e.duration_ms ?? "—"),
          h("td", { class: "hash" }, e.hash.slice(0, 12))))))),
    drawer);
}

// ------------------------------------------------------------------ access

async function accessView() {
  const data = await api("/api/access");
  const id = h("input", { class: "input", placeholder: t("consumer id, e.g. grants-sync") });
  const role = h("select", {}, data.roles.map((r) => h("option", { value: r.name }, r.name)));
  const keyBox = h("div");
  const create = async () => {
    try {
      const r = await api("/api/access/consumers", { method: "POST", body: { id: id.value, role: role.value } });
      keyBox.replaceChildren(h("div", { class: "card body stack" }, h("span", { class: "label accent" }, t("API key — shown once")),
        h("code", { class: "mono", style: "word-break:break-all" }, r.api_key)));
    } catch (e) { toast(e.message, true); }
  };
  const toggle = async (p) => {
    try { await api(`/api/access/principals/${p.id}/status`, { method: "POST", body: { status: p.status === "active" ? "blocked" : "active" } }); render(); }
    catch (e) { toast(e.message, true); }
  };
  return shell("Access", t("principals · roles · tool globs"), null,
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Principals"))),
        h("table", {}, h("thead", {}, h("tr", {}, [t("Id"), t("Kind"), t("Role"), t("Status"), ""].map((c) => h("th", {}, c)))),
          h("tbody", {}, data.principals.map((p) => h("tr", {},
            h("td", { class: "mono" }, p.id), h("td", {}, h("span", { class: "chip" }, p.kind)),
            h("td", { class: "mono" }, p.role.name),
            h("td", {}, h("span", { class: p.status === "active" ? "chip ok" : "chip bad" }, p.status)),
            h("td", {}, p.id !== state.me.id ? h("button", { class: "btn ghost", onclick: () => toggle(p) }, p.status === "active" ? t("block") : t("unblock")) : null)))))),
      h("div", { class: "stack" },
        h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Roles"))),
          h("div", { class: "body stack" }, data.roles.map((r) => h("div", { class: "stack", style: "gap:6px" },
            h("div", { class: "row" }, h("b", {}, r.name), h("span", { class: "muted" }, r.description)),
            h("div", { class: "row" }, r.tool_globs.map((g) => h("span", { class: "chip ok" }, g)), r.admin_perms.map((g) => h("span", { class: "chip violet" }, g))))))),
        h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("New service consumer"))),
          h("div", { class: "body stack" }, id, role, h("div", { class: "row" }, h("button", { class: "btn primary", onclick: create }, t("Create"))), keyBox)))));
}

// ------------------------------------------------------------------ secrets

async function secretsView() {
  const data = await api("/api/secrets");
  const name = h("input", { class: "input", placeholder: t("name (lowercase_underscores)") });
  const value = h("input", { class: "input", type: "password", placeholder: t("value — never shown again"), autocomplete: "off" });
  const shared = h("input", { type: "checkbox", disabled: !can("secrets.write") });
  const save = async () => {
    try { await api("/api/secrets", { method: "PUT", body: { name: name.value, value: value.value, shared: shared.checked } }); toast("stored, encrypted"); render(); }
    catch (e) { toast(e.data?.detail?.[0]?.msg || e.message, true); }
  };
  const del = async (n, isShared) => { await api(`/api/secrets/${n}?shared=${isShared}`, { method: "DELETE" }); render(); };
  const list = (names, isShared) => names.length ? names.map((n) => h("div", { class: "row", style: "justify-content:space-between" },
    h("span", { class: "mono" }, `{{secret:${n}}}`), h("button", { class: "btn ghost", onclick: () => del(n, isShared) }, t("delete"))))
    : [h("span", { class: "muted" }, t("none"))];
  return shell("Secrets", t("fernet-encrypted · names only"), null,
    h("div", { class: "grid two" },
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Yours"))), h("div", { class: "body stack" }, list(data.mine, false)),
        h("header", {}, h("span", { class: "label" }, t("Shared (__system__)"))), h("div", { class: "body stack" }, list(data.shared, true))),
      h("section", { class: "card" }, h("header", {}, h("span", { class: "label" }, t("Store a secret"))),
        h("div", { class: "body stack" }, name, value,
          h("label", { class: "row muted" }, shared, t("shared with everyone (needs secrets.write)")),
          h("div", { class: "row" }, h("button", { class: "btn primary", onclick: save }, t("Encrypt & store")))))));
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
    if (state.selected) state.selected = state.tools.find((t) => t.name === state.selected.name) || null;
    root.replaceChildren(await VIEWS[state.route]());
  } catch (e) {
    if (e.status === 401) { state.me = null; root.replaceChildren(loginView()); return; }
    toast(e.message, true);
  }
}

window.addEventListener("hashchange", render);
render();
