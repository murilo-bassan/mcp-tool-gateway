"""The tool catalog: one list, whatever the tool's origin.

A `ToolSpec` is what both the MCP server and the web panel see. Native tools
are Python functions declared with `@native`; dynamic tools are approved
registry definitions (`registry.py`) turned into specs at lookup time. The
executor never cares which is which.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gateway.errors import NotFound

Handler = Callable[[dict[str, Any], "CallContext"], Any]


@dataclass(frozen=True)
class CallContext:
    """What a handler may know about the call. Deliberately small."""
    principal_id: str
    correlation: str


@dataclass(frozen=True)
class ToolSpec:
    name: str                      # "<domain>.<action>", the global identifier
    title: str
    description: str
    input_schema: dict[str, Any]
    handler: Handler
    read_only: bool = True
    origin: str = "native"         # "native" | "dynamic"
    revision: int = 0
    keywords: tuple[str, ...] = field(default_factory=tuple)

    @property
    def domain(self) -> str:
        return self.name.split(".", 1)[0]

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name, "title": self.title, "description": self.description, "domain": self.domain,
            "input_schema": self.input_schema, "read_only": self.read_only, "origin": self.origin,
            "revision": self.revision,
        }


_NATIVE: dict[str, ToolSpec] = {}


def native(name: str, *, title: str, description: str, schema: dict[str, Any], read_only: bool = True,
           keywords: tuple[str, ...] = ()) -> Callable[[Handler], Handler]:
    """Declares a native tool. Duplicate names fail at import time, not at call time."""
    def register(fn: Handler) -> Handler:
        if name in _NATIVE:
            raise ValueError(f"duplicate native tool '{name}'")
        _NATIVE[name] = ToolSpec(name=name, title=title, description=description, input_schema=schema,
                                 handler=fn, read_only=read_only, keywords=keywords)
        return fn
    return register


def object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or [], "additionalProperties": False}


def _load_domains() -> None:
    # Importing a domain module runs its @native decorators.
    from gateway.domains import governance, grants, invoices, meta  # noqa: F401


def native_tools() -> list[ToolSpec]:
    _load_domains()
    return sorted(_NATIVE.values(), key=lambda t: t.name)


def all_tools() -> list[ToolSpec]:
    from gateway import registry
    return native_tools() + registry.approved_specs()


def get(name: str) -> ToolSpec:
    _load_domains()
    if name in _NATIVE:
        return _NATIVE[name]
    from gateway import registry
    spec = registry.approved_spec(name)
    if spec is None:
        raise NotFound(f"tool '{name}' not found", detail={"tool": name})
    return spec


def visible_to(role_allows: Callable[[str], bool]) -> list[ToolSpec]:
    """Only the tools a principal may call — an LLM should never see a tool it cannot use."""
    return [t for t in all_tools() if role_allows(t.name)]
