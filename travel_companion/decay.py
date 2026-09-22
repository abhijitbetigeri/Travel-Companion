"""Recency-weighted re-ranking over Cognee's retrieval.

WHY THIS EXISTS
---------------
Cognee stores the timeline correctly — cognify extracts "On 2026-08-08 … knee
injury … supersedes the former walk-everywhere decision" into the graph, dates
and all. What it does not do is *rank by recency*: SearchType.TEMPORAL answers
explicit time-range questions ("what happened before 2000?"), it does not
down-weight a stale preference in a general query. Ask it to plan a day and the
completion blends a 330-day-old decision with the 45-day-old one that reversed
it, and the stale one wins as often as not.

So the decay lives here, in the retrieval layer, where it always did:

    final_score = relevance * exp(-age_days / window_days)

Multiplicative, not a replacement — relevance still governs which memories are
candidates at all; recency only decides which of the *relevant* ones survive.
An abandoned preference is never deleted from the graph. It just loses.

The 45-day window comes from the reversal spacing in this corpus: the knee
injury is 45 days old, and every decision it superseded is 250+ days old, so
any window in that gap separates them. 45 is the tightest one that does.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone

from . import cognee_client as cog

# ingest.py writes every memory as "On YYYY-MM-DD, the traveler recorded a <type>: <title>."
ENTRY_RE = re.compile(
    r"On (\d{4}-\d{2}-\d{2}), the traveler recorded an? (\w+): (.+?)\.\n", re.MULTILINE
)

DEFAULT_WINDOW_DAYS = 45
FLAT_WINDOW_DAYS = 3650  # ten years — decay is effectively off


@dataclass
class Memory:
    when: date
    kind: str
    title: str
    body: str
    rank: int  # position in Cognee's relevance ordering, 0 = most relevant

    @property
    def age_days(self) -> int:
        return (datetime.now(timezone.utc).date() - self.when).days

    def score(self, window_days: int) -> float:
        # Relevance proxy: Cognee returns results already ordered, so decay the
        # rank into a [0,1] weight rather than inventing a similarity number.
        relevance = 1.0 / (1.0 + self.rank)
        return relevance * math.exp(-self.age_days / window_days)

    def render(self) -> str:
        return f"[{self.when} · {self.age_days}d ago] {self.title}\n{self.body}"


def _parse(blobs: list[str]) -> list[Memory]:
    """Split Cognee's chunk text back into individual dated memories."""
    out: list[Memory] = []
    for blob in blobs:
        marks = list(ENTRY_RE.finditer(blob))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(blob)
            out.append(
                Memory(
                    when=date.fromisoformat(m.group(1)),
                    kind=m.group(2),
                    title=m.group(3).strip(),
                    body=blob[m.end() : end].strip(),
                    rank=len(out),
                )
            )
    return out


def retrieve(query: str, dataset: str, top_k: int = 25) -> list[Memory]:
    """Pull candidate memories out of Cognee, un-ranked by time."""
    raw = cog.recall(query, dataset, search_type="CHUNKS", top_k=top_k, only_context=True)
    blobs: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            text = item.get("text") if isinstance(item, dict) else str(item)
            if text:
                blobs.append(text)
    elif isinstance(raw, str):
        blobs.append(raw)
    return _parse(blobs)


def rank(
    memories: list[Memory], window_days: int = DEFAULT_WINDOW_DAYS, limit: int = 8
) -> list[Memory]:
    return sorted(memories, key=lambda m: m.score(window_days), reverse=True)[:limit]


def context(
    query: str,
    dataset: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    limit: int = 8,
) -> str:
    """The context block a model should actually be given."""
    winners = rank(retrieve(query, dataset), window_days=window_days, limit=limit)
    if not winners:
        return "(no memories found)"
    return "\n\n".join(m.render() for m in winners)
