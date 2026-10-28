"""Deterministic intent matching: a natural-language request → ranked tool suggestions.

No LLM on purpose. It runs in microseconds, costs nothing, behaves the same
on every call, and is the *baseline* every smarter router has to beat — the
llm-routing-eval-lab repo benchmarks exactly this against LLM routers.

Scoring mixes three signals over accent-folded, lowercased text:
  * keyword phrase hits (declared per tool, PT and EN),
  * token overlap with the tool's title + description,
  * fuzzy similarity (difflib) to absorb typos.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

from gateway.catalog import ToolSpec

_STOP = {"a", "o", "e", "de", "da", "do", "das", "dos", "um", "uma", "para", "por", "com", "no", "na", "em",
         "the", "of", "to", "and", "for", "in", "on", "me", "quero", "preciso", "por favor", "please", "show"}


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]+", " ", folded.lower()).strip()


def tokens(text: str) -> set[str]:
    return {t for t in normalize(text).split() if t not in _STOP and len(t) > 1}


@dataclass(frozen=True)
class Suggestion:
    tool: str
    score: float
    reasons: tuple[str, ...]


def score(request: str, tool: ToolSpec) -> Suggestion:
    req_norm = normalize(request)
    req_tokens = tokens(request)
    reasons: list[str] = []
    s = 0.0

    matched: list[str] = []
    for kw in sorted(tool.keywords, key=len, reverse=True):
        kw_norm = normalize(kw)
        if kw_norm and kw_norm in req_norm and not any(kw_norm in m for m in matched):
            matched.append(kw_norm)
            s += 2.0 + 0.5 * kw_norm.count(" ")
            reasons.append(f"keyword '{kw}'")

    doc_tokens = tokens(f"{tool.title} {tool.description}")
    overlap = req_tokens & doc_tokens
    if overlap:
        s += len(overlap) / max(len(req_tokens), 1)
        reasons.append(f"overlap {sorted(overlap)}")

    best_fuzzy = 0.0
    for rt in req_tokens:
        for kt in {t for kw in tool.keywords for t in tokens(kw)} | doc_tokens:
            if abs(len(rt) - len(kt)) <= 3:
                best_fuzzy = max(best_fuzzy, difflib.SequenceMatcher(None, rt, kt).ratio())
    if 0.8 <= best_fuzzy < 1.0:
        s += best_fuzzy - 0.5
        reasons.append(f"fuzzy {best_fuzzy:.2f}")

    return Suggestion(tool=tool.name, score=round(s, 3), reasons=tuple(reasons))


def suggest(request: str, tools: list[ToolSpec], top_k: int = 3, min_score: float = 0.5) -> list[Suggestion]:
    ranked = sorted((score(request, t) for t in tools), key=lambda x: -x.score)
    return [r for r in ranked if r.score >= min_score][:top_k]
