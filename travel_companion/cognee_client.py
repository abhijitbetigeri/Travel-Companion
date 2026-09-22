"""Thin REST client for the hosted Cognee tenant.

The tenant is REST-only — there is no MCP endpoint on it (/mcp, /api/v1/mcp,
/sse all 404). Auth is the X-Api-Key header. Full spec: {COGNEE_BASE_URL}/docs

Wrapping REST directly (rather than the cognee-integration-strands package,
which wraps the *local* library) is what gives us per-call control over
`datasets` and `searchType` — the two knobs the whole demo turns on.
"""

from __future__ import annotations

import requests

from .config import COGNEE_API_KEY, COGNEE_BASE_URL

TIMEOUT = 180


def _headers() -> dict:
    return {"X-Api-Key": COGNEE_API_KEY, "Content-Type": "application/json"}


def _post(path: str, payload: dict) -> dict | list:
    r = requests.post(
        f"{COGNEE_BASE_URL}{path}", headers=_headers(), json=payload, timeout=TIMEOUT
    )
    r.raise_for_status()
    return r.json() if r.content else {}


def _get(path: str) -> dict | list:
    r = requests.get(f"{COGNEE_BASE_URL}{path}", headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json() if r.content else {}


# --- datasets -------------------------------------------------------------


def list_datasets() -> list:
    return _get("/api/v1/datasets/")


def ensure_dataset(name: str) -> str:
    """Create the dataset if it doesn't exist. Returns its id."""
    for ds in list_datasets():
        if ds.get("name") == name:
            return ds["id"]
    created = _post("/api/v1/datasets/", {"name": name})
    return created["id"]


def dataset_status() -> dict | list:
    return _get("/api/v1/datasets/status")


# --- write path -----------------------------------------------------------


def add_text(texts: list[str], dataset: str, node_set: list[str] | None = None) -> dict:
    """Stage raw text into a dataset. Does not build the graph — cognify does."""
    payload: dict = {"textData": texts, "datasetName": dataset}
    if node_set:
        payload["nodeSet"] = node_set
    return _post("/api/v1/add_text", payload)


def cognify(
    dataset: str,
    ontology_key: str | None = None,
    run_in_background: bool = False,
) -> dict:
    """Build the knowledge graph over everything staged in `dataset`.

    This is the expensive call — it runs an LLM over every chunk to extract
    entities, relationships and temporal edges. Billed to the Cognee credit.
    Don't re-run it casually.
    """
    payload: dict = {"datasets": [dataset], "runInBackground": run_in_background}
    if ontology_key:
        payload["ontologyKey"] = ontology_key
    return _post("/api/v1/cognify", payload)


# --- read path ------------------------------------------------------------

# Verified against the tenant's SearchType enum.
TEMPORAL = "TEMPORAL"  # time-aware: the thesis. Recent facts beat stale ones.
GRAPH = "GRAPH_COMPLETION"  # flat graph retrieval: the "before" in the A/B.
AGENTIC = "AGENTIC_COMPLETION"  # multi-iteration, for harder questions.


def recall(
    query: str,
    dataset: str,
    search_type: str = TEMPORAL,
    top_k: int = 10,
    only_context: bool = False,
) -> dict | list:
    """Query one dataset with one retrieval strategy.

    `dataset` and `search_type` are the two knobs the demo turns on:
      recall(q, "self", TEMPORAL) -> current preferences
      recall(q, "self", GRAPH)    -> the same memory, flattened (wrong on purpose)
      recall(q, "world", ...)     -> what we scraped about the world
    """
    return _post(
        "/api/v1/recall",
        {
            "query": query,
            "datasets": [dataset],
            "searchType": search_type,
            "topK": top_k,
            "onlyContext": only_context,
        },
    )


def quota() -> dict:
    """Storage usage only — the tenant does not expose token burn-down."""
    return _get("/api/v1/quotas/usage")
