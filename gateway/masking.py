"""Masks personal data and credentials before anything is written to the audit trail.

The trail is the most-read, longest-lived data in the system, so it is where a
leak hurts most. Masking runs on the *serialized* payload, which means a value
is caught wherever it hides: an argument, a nested response, an error message.

Brazilian identifiers keep their last digits so an operator can still tell two
records apart ("***.***.*89-01"), which is what support tickets need.
"""
from __future__ import annotations

import re
from typing import Any

# Order matters: more specific patterns first (a CNPJ contains a CPF-length run).
_PATTERNS: list[tuple[str, re.Pattern[str], Any]] = [
    ("bearer", re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]{12,}"), lambda m: "Bearer ***"),
    ("api_key", re.compile(r"\b(sk|pk|rk|or)-[A-Za-z0-9_\-]{16,}\b"), lambda m: f"{m.group(1)}-***"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b"), lambda m: "jwt:***"),
    ("email", re.compile(r"\b([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*@([A-Za-z0-9.\-]+\.[A-Za-z]{2,})\b"),
     lambda m: f"{m.group(1)}***@{m.group(2)}"),
    ("cnpj", re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"), lambda m: "**.***.***/****-" + _digits(m)[-2:]),
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), lambda m: "***.***.*" + _digits(m)[-4:-2] + "-" + _digits(m)[-2:]),
    ("card", re.compile(r"\b(?:\d[ -]?){13,16}\b"), lambda m: "card:****" + _digits(m)[-4:]),
    ("phone", re.compile(r"(?<!\d)(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}-?\d{4}(?!\d)"), lambda m: "phone:***" + _digits(m)[-2:]),
]

# Keys whose values are always secret, whatever they look like.
_SECRET_KEYS = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|authorization|cookie)")


def _digits(match: re.Match[str]) -> str:
    return re.sub(r"\D", "", match.group(0))


def mask_text(text: str) -> str:
    for _, pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def mask(value: Any) -> Any:
    """Masks a JSON-like value recursively; dict keys that name secrets lose their value entirely."""
    if isinstance(value, dict):
        return {k: ("***" if _SECRET_KEYS.search(str(k)) and v not in (None, "") else mask(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [mask(v) for v in value]
    if isinstance(value, str):
        return mask_text(value)
    return value


def found_kinds(text: str) -> list[str]:
    """Which kinds of sensitive data appear in `text` (used by tests and the panel's preview)."""
    return [name for name, pattern, _ in _PATTERNS if pattern.search(text)]
