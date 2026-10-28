"""Dynamic tools: HTTP endpoints registered as data, governed like code.

Lifecycle of a definition (one row per revision):

    propose ──► draft ──review(approve)──► approved ──► superseded (by a newer approval)
                  │                           │
                  └──review(reject)──► disabled ◄─── disable

Rules enforced at proposal time, before any human looks at it:
  * the name is `<domain>.<action>` and cannot shadow a native tool or a reserved domain;
  * `input_schema` is a valid JSON Schema (Draft 2020-12) of type object;
  * every `{placeholder}` in the URL is a declared property;
  * the URL is https, and never a private/link-local address (SSRF), unless it is localhost
    and `allow_localhost` is set (demo and tests);
  * no header carries a literal credential — only `{{secret:name}}` references.

Approval is four-eyes: the reviewer needs `registry.review` and cannot be the author.
"""
from __future__ import annotations

import ipaddress
import json
import re
import time
from typing import Any, Literal
from urllib.parse import quote, urlsplit

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from pydantic import BaseModel, Field

from gateway import masking, secrets_store, store
from gateway.access import Principal
from gateway.catalog import CallContext, ToolSpec
from gateway.errors import InvalidDefinition, NotFound, PermissionDenied, ToolFailed

RESERVED_DOMAINS = {"meta", "registry", "invoices", "grants"}
_NAME = re.compile(r"^[a-z][a-z0-9_]{1,30}\.[a-z][a-z0-9_]{1,40}$")
_PLACEHOLDER = re.compile(r"\{([a-z_][a-z0-9_]*)\}")
_AUTH_HEADERS = {"authorization", "x-api-key", "api-key", "proxy-authorization"}
MAX_RESPONSE_BYTES = 1_000_000

# Tests swap this for an httpx.MockTransport; production leaves it None.
transport: httpx.BaseTransport | None = None
allow_localhost = False


class HttpBinding(BaseModel):
    method: Literal["GET", "POST"] = "GET"
    url: str                                          # "https://api.example.org/v1/items/{item_id}"
    query: dict[str, str] = Field(default_factory=dict)    # {"q": "{term}", "key": "{{secret:x}}"}
    headers: dict[str, str] = Field(default_factory=dict)
    json_body_from_args: bool = False
    timeout_s: float = Field(default=10, gt=0, le=60)


class DynamicToolDefinition(BaseModel):
    name: str
    title: str
    description: str = Field(min_length=10)
    input_schema: dict[str, Any]
    http: HttpBinding
    read_only: bool = True
    keywords: list[str] = Field(default_factory=list)


Status = Literal["draft", "approved", "disabled", "superseded"]


class Revision(BaseModel):
    name: str
    revision: int
    status: Status
    definition: DynamicToolDefinition
    author: str
    reviewer: str | None
    created_at: float
    reviewed_at: float | None


# ---------------------------------------------------------------- validation

def _check_host(url: str) -> None:
    parts = urlsplit(url.replace("{", "x").replace("}", "x"))
    host = parts.hostname or ""
    if host in {"localhost", "127.0.0.1"}:
        if not allow_localhost:
            raise InvalidDefinition("localhost targets are disabled")
        return
    if parts.scheme != "https":
        raise InvalidDefinition("dynamic tools must call https URLs")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return  # a hostname; DNS-rebinding protection belongs to an egress proxy, see docs/security.md
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise InvalidDefinition(f"address {host} is not allowed (private/link-local)")


def validate(defn: DynamicToolDefinition) -> None:
    from gateway import catalog

    if not _NAME.match(defn.name):
        raise InvalidDefinition("name must look like 'domain.action' (lowercase, digits, underscores)")
    if defn.name.split(".")[0] in RESERVED_DOMAINS:
        raise InvalidDefinition(f"domain '{defn.name.split('.')[0]}' is reserved for native tools")
    if any(t.name == defn.name for t in catalog.native_tools()):
        raise InvalidDefinition("name collides with a native tool")
    try:
        Draft202012Validator.check_schema(defn.input_schema)
    except SchemaError as error:
        raise InvalidDefinition(f"input_schema is not valid JSON Schema: {error.message}") from error
    if defn.input_schema.get("type") != "object":
        raise InvalidDefinition("input_schema must be of type 'object'")
    props = set(defn.input_schema.get("properties", {}))
    templated = " ".join([defn.http.url, *defn.http.query.values()])
    missing = set(_PLACEHOLDER.findall(re.sub(r"\{\{secret:[^}]+\}\}", "", templated))) - props
    if missing:
        raise InvalidDefinition(f"placeholders without a schema property: {sorted(missing)}")
    _check_host(defn.http.url)
    for header, value in defn.http.headers.items():
        has_ref = bool(secrets_store.references(value))
        literal = re.sub(r"\{\{secret:[^}]+\}\}", "", value)
        if header.lower() in _AUTH_HEADERS and not has_ref:
            raise InvalidDefinition(f"header '{header}' must use a {{{{secret:name}}}} reference, not a literal")
        if set(masking.found_kinds(literal)) & {"bearer", "api_key", "jwt"}:
            raise InvalidDefinition(f"header '{header}' looks like it carries a literal credential")


# ---------------------------------------------------------------- lifecycle

def _row(row: Any) -> Revision:
    return Revision(name=row["name"], revision=row["revision"], status=row["status"],
                    definition=DynamicToolDefinition.model_validate_json(row["definition"]),
                    author=row["author"], reviewer=row["reviewer"],
                    created_at=row["created_at"], reviewed_at=row["reviewed_at"])


def propose(defn: DynamicToolDefinition, author: Principal) -> Revision:
    author.require("registry.write")
    validate(defn)
    with store.transaction() as conn:
        last = conn.execute("SELECT MAX(revision) FROM tool_definitions WHERE name = ?", (defn.name,)).fetchone()[0]
        rev = (last or 0) + 1
        conn.execute(
            "INSERT INTO tool_definitions (name, revision, status, definition, author, created_at)"
            " VALUES (?, ?, 'draft', ?, ?, ?)",
            (defn.name, rev, defn.model_dump_json(), author.id, time.time()),
        )
    return get_revision(defn.name, rev)


def get_revision(name: str, revision: int) -> Revision:
    with store.reading() as conn:
        row = conn.execute("SELECT * FROM tool_definitions WHERE name = ? AND revision = ?", (name, revision)).fetchone()
    if row is None:
        raise NotFound(f"{name} rev {revision} not found")
    return _row(row)


def review(name: str, revision: int, reviewer: Principal, approve: bool) -> Revision:
    reviewer.require("registry.review")
    current = get_revision(name, revision)
    if current.status != "draft":
        raise InvalidDefinition(f"only drafts can be reviewed (this one is {current.status})")
    if current.author == reviewer.id:
        raise PermissionDenied("four-eyes rule: the author cannot review their own tool")
    with store.transaction() as conn:
        if approve:
            conn.execute("UPDATE tool_definitions SET status = 'superseded' WHERE name = ? AND status = 'approved'",
                         (name,))
        conn.execute("UPDATE tool_definitions SET status = ?, reviewer = ?, reviewed_at = ? WHERE name = ? AND revision = ?",
                     ("approved" if approve else "disabled", reviewer.id, time.time(), name, revision))
    return get_revision(name, revision)


def disable(name: str, actor: Principal) -> None:
    actor.require("registry.review")
    with store.transaction() as conn:
        conn.execute("UPDATE tool_definitions SET status = 'disabled' WHERE name = ? AND status = 'approved'", (name,))


def list_revisions(status: Status | None = None) -> list[Revision]:
    with store.reading() as conn:
        if status:
            rows = conn.execute("SELECT * FROM tool_definitions WHERE status = ? ORDER BY name, revision", (status,))
        else:
            rows = conn.execute("SELECT * FROM tool_definitions ORDER BY name, revision")
        return [_row(r) for r in rows.fetchall()]


# ---------------------------------------------------------------- execution

def _render(template: str, args: dict[str, Any], owner: str, url_part: bool) -> str:
    with_secrets = secrets_store.render(template, owner)
    return _PLACEHOLDER.sub(lambda m: quote(str(args.get(m.group(1), "")), safe="") if url_part
                            else str(args.get(m.group(1), "")), with_secrets)


def _handler(defn: DynamicToolDefinition):
    def call(args: dict[str, Any], ctx: CallContext) -> Any:
        b = defn.http
        url = _render(b.url, args, ctx.principal_id, url_part=True)
        query = {k: _render(v, args, ctx.principal_id, url_part=False) for k, v in b.query.items()}
        headers = {k: _render(v, args, ctx.principal_id, url_part=False) for k, v in b.headers.items()}
        headers["X-Correlation-Id"] = ctx.correlation
        try:
            with httpx.Client(timeout=b.timeout_s, follow_redirects=False, transport=transport) as client:
                response = client.request(b.method, url, params=query, headers=headers,
                                          json=args if b.json_body_from_args else None)
        except httpx.HTTPError as error:
            raise ToolFailed(f"upstream unreachable: {type(error).__name__}") from error
        if len(response.content) > MAX_RESPONSE_BYTES:
            raise ToolFailed("upstream response too large", detail={"bytes": len(response.content)})
        if response.status_code >= 400:
            raise ToolFailed(f"upstream answered {response.status_code}",
                             detail={"status": response.status_code, "body": response.text[:300]})
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"text": response.text[:5000]}
    return call


def _spec(rev: Revision) -> ToolSpec:
    d = rev.definition
    return ToolSpec(name=d.name, title=d.title, description=d.description, input_schema=d.input_schema,
                    handler=_handler(d), read_only=d.read_only, origin="dynamic", revision=rev.revision,
                    keywords=tuple(d.keywords))


def approved_specs() -> list[ToolSpec]:
    return [_spec(r) for r in list_revisions("approved")]


def approved_spec(name: str) -> ToolSpec | None:
    with store.reading() as conn:
        row = conn.execute("SELECT * FROM tool_definitions WHERE name = ? AND status = 'approved'", (name,)).fetchone()
    return _spec(_row(row)) if row else None
