"""Cognee memory exposed to the Strands agent as tools.

Three tools, deliberately: two ways to read the personal brain and one way to
write to it. The split is not cosmetic — `recall_self` and `recall_world` hit
different datasets with different trust rules, and keeping them separate is
what stops a three-week-old scrape from being treated as a standing fact.
"""

from __future__ import annotations

import json

from strands import tool

from . import cognee_client as cog
from . import decay
from .config import DATASET_SELF, DATASET_WORLD, WORLD_FRESHNESS_HOURS


def _render(result) -> str:
    if isinstance(result, (dict, list)):
        return json.dumps(result, indent=2)[:6000]
    return str(result)[:6000]


@tool
def recall_self(query: str, time_aware: bool = True) -> str:
    """Recall what is true about the traveler — preferences, constraints, history.

    Results are recency-weighted: a decision the traveler reversed loses to the
    one that replaced it, even though both are still in the graph. Every result
    carries the date it was recorded and how long ago that was.

    Args:
        query: natural-language question about the traveler.
        time_aware: when True (default) apply recency decay. Set False only to
            demonstrate the failure mode — flat retrieval that treats an
            abandoned preference as though it still stood.
    """
    window = decay.DEFAULT_WINDOW_DAYS if time_aware else decay.FLAT_WINDOW_DAYS
    return decay.context(query, DATASET_SELF, window_days=window)


@tool
def recall_world(query: str) -> str:
    """Recall previously-fetched facts about the world (hours, closures, prices).

    These decay fast. Every result carries the timestamp it was fetched at.
    If what comes back is older than the freshness window, do NOT trust it —
    call the Bright Data search or scrape tool to re-check it live, then write
    the correction back with `remember`.
    """
    out = _render(cog.recall(query, DATASET_WORLD, search_type=cog.TEMPORAL))
    return (
        f"[freshness policy: anything fetched more than {WORLD_FRESHNESS_HOURS}h ago "
        f"must be re-verified live before you rely on it]\n\n{out}"
    )


@tool
def remember(fact: str, about_traveler: bool = True) -> str:
    """Write a new fact into the brain so it survives this conversation.

    Use this when you learn something durable — a new constraint the traveler
    states, or a correction the live web forced on a stale stored fact.

    Args:
        fact: the fact, written as a dated sentence, e.g.
            "On 2026-09-21 the traveler said they have no car this trip."
        about_traveler: True writes to the personal brain, False to world facts.
    """
    dataset = DATASET_SELF if about_traveler else DATASET_WORLD
    cog.ensure_dataset(dataset)
    cog.add_text([fact], dataset, node_set=["self" if about_traveler else "world"])
    cog.cognify(dataset, run_in_background=True)
    return f"Written to '{dataset}' and cognifying in the background: {fact}"


MEMORY_TOOLS = [recall_self, recall_world, remember]
