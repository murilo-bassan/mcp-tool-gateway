"""Web panel API + static frontend.

Two ways in:
  * people: `POST /api/login` sets an HttpOnly, SameSite=Strict session cookie;
    every mutating request must also send `X-Requested-With: gateway-panel`
    (a header a cross-site form cannot set) — a cheap, effective CSRF guard.
  * services: `POST /v1/call` with `X-API-Key: gw_...` (a consumer principal).

Every tool call — from either door — goes through `executor.execute`, the
same function the MCP server uses. The panel has no private shortcut.

    uvicorn web.app:app --port 8600
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from gateway import access, audit, catalog, chat, conversations, executor, intents, registry, secrets_store
from gateway.config import get_settings
from gateway.errors import AuthFailed, GatewayError, InvalidArguments, InvalidDefinition, NotFound, PermissionDenied, \
    RateLimited

STATIC = Path(__file__).parent / "static"
COOKIE = "gw_session"
CSRF_HEADER = "gateway-panel"

@asynccontextmanager
async def lifespan(_: FastAPI):
    if get_settings().demo_seed:
        access.seed_demo()
    yield


app = FastAPI(title="mcp-tool-gateway panel", version="0.1.0", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)

_STATUS = {AuthFailed: 401, PermissionDenied: 403, NotFound: 404, InvalidArguments: 422, InvalidDefinition: 422,
           RateLimited: 429}


@app.exception_handler(GatewayError)
async def gateway_error(request: Request, error: GatewayError) -> JSONResponse:
    status = next((code for cls, code in _STATUS.items() if isinstance(error, cls)), 400)
    return JSONResponse(error.as_dict(), status_code=status)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; "
        "img-src 'self' data:; script-src 'self'; frame-ancestors 'none'")
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------- auth dependencies

def current(request: Request) -> access.Principal:
    token = request.cookies.get(COOKIE)
    if not token:
        raise AuthFailed("not logged in")
    return access.from_session(token)


def mutating(request: Request, principal: access.Principal = Depends(current)) -> access.Principal:
    if request.headers.get("x-requested-with") != CSRF_HEADER:
        raise PermissionDenied("missing X-Requested-With header")
    return principal


def consumer(x_api_key: str = Header(default="")) -> access.Principal:
    return access.from_api_key(x_api_key)


# ---------------------------------------------------------------- session

class LoginBody(BaseModel):
    user: str
    password: str


@app.post("/api/login")
def login(body: LoginBody, request: Request, response: Response) -> dict[str, Any]:
    if request.headers.get("x-requested-with") != CSRF_HEADER:
        raise PermissionDenied("missing X-Requested-With header")
    try:
        token = access.login(body.user, body.password)
    except AuthFailed:
        audit.record(audit.Event(kind="login", actor=body.user, outcome="failed",
                                 payload={"ip": request.client.host if request.client else None}))
        raise
    audit.record(audit.Event(kind="login", actor=body.user, outcome="ok"))
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=get_settings().session_ttl_s,
                        secure=request.url.scheme == "https")
    return me(access.from_session(token))


@app.post("/api/logout")
def logout(request: Request, response: Response, _: access.Principal = Depends(mutating)) -> dict[str, bool]:
    access.logout(request.cookies.get(COOKIE, ""))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(principal: access.Principal = Depends(current)) -> dict[str, Any]:
    return {"id": principal.id, "name": principal.display_name, "kind": principal.kind, "role": principal.role.name,
            "tool_globs": principal.role.tool_globs, "admin_perms": principal.role.admin_perms}


# ---------------------------------------------------------------- tools

class CallBody(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.get("/api/tools")
def tools(principal: access.Principal = Depends(current)) -> list[dict[str, Any]]:
    return [t.describe() for t in catalog.visible_to(principal.role.allows_tool)]


@app.post("/api/call")
def call(body: CallBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    return executor.execute(principal, body.tool, body.arguments).model_dump()


class SuggestBody(BaseModel):
    request: str = Field(min_length=3)


@app.post("/api/suggest")
def suggest(body: SuggestBody, principal: access.Principal = Depends(mutating)) -> list[dict[str, Any]]:
    visible = [t for t in catalog.visible_to(principal.role.allows_tool) if not t.name.startswith(("meta.", "registry."))]
    return [{"tool": s.tool, "score": s.score, "reasons": list(s.reasons)} for s in intents.suggest(body.request, visible)]


class ChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    lang: str = Field(default="pt", pattern="^(pt|en)$")
    conversation_id: str | None = None   # omitted → a new conversation is created and returned


@app.post("/api/chat")
def chat_endpoint(body: ChatBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    conv = (conversations.get(principal.id, body.conversation_id) if body.conversation_id
            else conversations.create(principal.id, body.message, body.lang))
    engine = chat.engine()
    # the pending follow-up lives on the stored conversation, not in the browser
    if isinstance(engine, chat.DeterministicChat):
        reply = engine.reply(principal, body.message, body.lang, conv["pending"],  # type: ignore[arg-type]
                             conversations.last_call(principal.id, conv["id"]))
    else:
        reply = engine.reply(principal, body.message, body.lang, conv["pending"])  # type: ignore[arg-type]
    out = {"engine": engine.engine, **reply.__dict__}
    conversations.append(principal.id, conv["id"], body.message, out)
    return {**out, "conversation_id": conv["id"]}


@app.get("/api/conversations")
def conversations_list(principal: access.Principal = Depends(current)) -> list[dict[str, Any]]:
    return conversations.list_for(principal.id)


@app.get("/api/conversations/{conv_id}")
def conversation_get(conv_id: str, principal: access.Principal = Depends(current)) -> dict[str, Any]:
    return {**conversations.get(principal.id, conv_id), "messages": conversations.messages(principal.id, conv_id)}


class RenameBody(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@app.patch("/api/conversations/{conv_id}")
def conversation_rename(conv_id: str, body: RenameBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    return conversations.rename(principal.id, conv_id, body.title)


@app.delete("/api/conversations/{conv_id}")
def conversation_delete(conv_id: str, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    conversations.delete(principal.id, conv_id)
    return {"deleted": conv_id}


@app.post("/v1/call")
def service_call(body: CallBody, principal: access.Principal = Depends(consumer)) -> dict[str, Any]:
    return executor.execute(principal, body.tool, body.arguments).model_dump()


# ---------------------------------------------------------------- registry

@app.get("/api/registry")
def registry_list(principal: access.Principal = Depends(current)) -> list[dict[str, Any]]:
    return [r.model_dump() for r in registry.list_revisions()]


class ProposeBody(BaseModel):
    definition: registry.DynamicToolDefinition


@app.post("/api/registry/propose")
def registry_propose(body: ProposeBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    rev = registry.propose(body.definition, principal)
    audit.record(audit.Event(kind="registry", actor=principal.id, outcome="proposed",
                             payload={"name": rev.name, "revision": rev.revision}))
    return rev.model_dump()


class ReviewBody(BaseModel):
    name: str
    revision: int
    approve: bool


@app.post("/api/registry/review")
def registry_review(body: ReviewBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    rev = registry.review(body.name, body.revision, principal, body.approve)
    audit.record(audit.Event(kind="registry", actor=principal.id, outcome="approved" if body.approve else "rejected",
                             payload={"name": rev.name, "revision": rev.revision}))
    return rev.model_dump()


# ---------------------------------------------------------------- audit

@app.get("/api/audit")
def audit_list(kind: str | None = None, actor: str | None = None, tool: str | None = None, limit: int = 200,
               principal: access.Principal = Depends(current)) -> list[dict[str, Any]]:
    if not principal.can("audit.read"):  # without it, you see only your own calls
        actor = principal.id
    return [e.model_dump() for e in audit.search(kind, actor, tool, min(limit, 1000))]  # type: ignore[arg-type]


@app.get("/api/audit/verify")
def audit_verify(principal: access.Principal = Depends(current)) -> dict[str, Any]:
    principal.require("audit.read")
    return audit.verify_chain().model_dump()


@app.get("/api/audit/stats")
def audit_stats(principal: access.Principal = Depends(current)) -> dict[str, Any]:
    principal.require("audit.read")
    return audit.stats()


@app.get("/api/audit/correlation/{correlation}")
def audit_correlation(correlation: str, principal: access.Principal = Depends(current)) -> list[dict[str, Any]]:
    principal.require("audit.read")
    return [e.model_dump() for e in audit.correlated(correlation)]


# ---------------------------------------------------------------- access & secrets

@app.get("/api/access")
def access_overview(principal: access.Principal = Depends(current)) -> dict[str, Any]:
    principal.require("access.admin")
    return {"principals": [p.model_dump() for p in access.list_principals()],
            "roles": [r.model_dump() for r in access.list_roles()]}


class ConsumerBody(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9-]{2,40}$")
    role: str


@app.post("/api/access/consumers")
def create_consumer(body: ConsumerBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    principal.require("access.admin")
    created, key = access.create_consumer(body.id, body.role)
    audit.record(audit.Event(kind="access", actor=principal.id, outcome="consumer_created",
                             payload={"consumer": created.id, "role": body.role}))
    return {"id": created.id, "role": body.role, "api_key": key, "note": "shown once; store it now"}


class StatusBody(BaseModel):
    status: str = Field(pattern="^(active|blocked)$")


@app.post("/api/access/principals/{principal_id}/status")
def set_status(principal_id: str, body: StatusBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    principal.require("access.admin")
    if principal_id == principal.id:
        raise InvalidArguments("you cannot block yourself")
    access.set_status(principal_id, body.status)  # type: ignore[arg-type]
    audit.record(audit.Event(kind="access", actor=principal.id, outcome=f"status_{body.status}",
                             payload={"principal": principal_id}))
    return {"id": principal_id, "status": body.status}


class SecretBody(BaseModel):
    name: str
    value: str = Field(min_length=1)
    shared: bool = False


def _owner(principal: access.Principal, shared: bool) -> str:
    if shared:
        principal.require("secrets.write")
        return secrets_store.SYSTEM_OWNER
    return principal.id


@app.get("/api/secrets")
def secrets_list(principal: access.Principal = Depends(current)) -> dict[str, list[str]]:
    return {"mine": secrets_store.names(principal.id), "shared": secrets_store.names(secrets_store.SYSTEM_OWNER)}


@app.put("/api/secrets")
def secrets_put(body: SecretBody, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    owner = _owner(principal, body.shared)
    secrets_store.put(owner, body.name, body.value)
    audit.record(audit.Event(kind="secret", actor=principal.id, outcome="stored",
                             payload={"name": body.name, "shared": body.shared}))
    return {"name": body.name, "shared": body.shared}


@app.delete("/api/secrets/{name}")
def secrets_delete(name: str, shared: bool = False, principal: access.Principal = Depends(mutating)) -> dict[str, Any]:
    secrets_store.delete(_owner(principal, shared), name)
    audit.record(audit.Event(kind="secret", actor=principal.id, outcome="deleted", payload={"name": name}))
    return {"deleted": name}


# ---------------------------------------------------------------- static

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")
