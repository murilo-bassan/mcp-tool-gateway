# ADR 0006 — A deterministic intent baseline before any LLM router

**Status:** accepted

## Context
"Which tool fits this request?" can be answered by an LLM, but then every
suggestion costs latency and money, varies between runs, and has no floor to
compare against.

## Decision
`meta.suggest_tool` uses a deterministic scorer: accent-folded keyword phrases
(declared per tool, PT and EN), token overlap with the tool's text, and difflib
similarity for typos. It returns the score *and the reasons*.

## Consequences
- Microseconds, free, reproducible, explainable.
- It is weak on paraphrase and on requests that mention two domains — that is
  the point: it is the baseline the companion repo `llm-routing-eval-lab`
  benchmarks LLM, embedding and hybrid routers against, on a labeled golden set.
