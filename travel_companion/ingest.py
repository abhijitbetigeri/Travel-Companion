"""Seed the two datasets.

    python -m travel_companion.ingest self
    python -m travel_companion.ingest world --query "Batteries to Bluffs Trail hours"

WHY DATES ARE WRITTEN INTO THE PROSE
------------------------------------
Cognee's temporal cognification reads timestamps *out of the text* to build
event nodes with before/after/during edges. A JSON field called `ageDays`
means nothing to it. So every memory is rendered as a dated sentence —
"On 2025-10-26 I decided ..." — which is what makes SearchType.TEMPORAL able
to tell a 330-day-old decision from a 20-day-old one.

Get this wrong and TEMPORAL degrades to ordinary graph search, the A/B
collapses, and the whole demo has no punchline.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from . import cognee_client as cog
from .config import DATA_DIR, DATASET_SELF, DATASET_WORLD


def render_memory(entry: dict, now: datetime) -> str:
    """One memory -> one dated paragraph Cognee can place on a timeline."""
    when = (now - timedelta(days=entry["ageDays"])).date().isoformat()
    tags = ", ".join(entry.get("tags", []))
    return (
        f"On {when}, the traveler recorded a {entry['type']}: {entry['title']}.\n"
        f"{entry['content']}\n"
        f"Tags: {tags}.\n"
        f"This was recorded {entry['ageDays']} days ago."
    )


def ingest_self() -> None:
    now = datetime.now(timezone.utc)
    entries = json.loads((DATA_DIR / "self_memory.json").read_text())
    texts = [render_memory(e, now) for e in entries]

    cog.ensure_dataset(DATASET_SELF)
    print(f"staging {len(texts)} memories into '{DATASET_SELF}' ...")
    cog.add_text(texts, DATASET_SELF, node_set=["self", "traveler"])

    print("cognifying (this is the slow, billed call) ...")
    cog.cognify(DATASET_SELF)
    print("done.")

    oldest, newest = max(entries, key=lambda e: e["ageDays"]), min(
        entries, key=lambda e: e["ageDays"]
    )
    print(f"  span: {oldest['ageDays']}d .. {newest['ageDays']}d")
    print(f"  oldest: {oldest['title']}")
    print(f"  newest: {newest['title']}")


def ingest_world(snippets: list[str]) -> None:
    """World facts are stamped with the moment they were fetched.

    Same reason as above, opposite purpose: the agent needs to see how old a
    scraped fact is so it can decide to re-fetch instead of trusting it.
    """
    stamped = [
        f"Fetched from the live web at {datetime.now(timezone.utc).isoformat()}:\n{s}"
        for s in snippets
    ]
    cog.ensure_dataset(DATASET_WORLD)
    cog.add_text(stamped, DATASET_WORLD, node_set=["world", "scraped"])
    cog.cognify(DATASET_WORLD)
    print(f"ingested {len(stamped)} world facts into '{DATASET_WORLD}'")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", choices=["self", "world"])
    ap.add_argument("--query", help="world only: what to search Bright Data for")
    args = ap.parse_args()

    if args.target == "self":
        ingest_self()
    else:
        if not args.query:
            ap.error("--query is required for world ingest")
        from .brightdata import search_sync

        ingest_world(search_sync(args.query))


if __name__ == "__main__":
    main()
