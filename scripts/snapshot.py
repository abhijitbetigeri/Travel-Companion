"""Capture a real run of both systems into demo_data.json.

    python scripts/snapshot.py            # everything (slow — runs the agent)
    python scripts/snapshot.py --no-agent # skip the slow agent leg

The demo UI is static and reads this file. That is deliberate: on stage the
page renders instantly from a captured *real* run rather than waiting on three
APIs and fourteen tool calls over venue wifi. Nothing is fabricated — rerun
this and the numbers move.
"""

from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from travel_companion import brightdata, decay, guardian  # noqa: E402
from travel_companion.agent import build  # noqa: E402
from travel_companion.config import DATASET_SELF  # noqa: E402

QUESTION = "I have a free day in San Francisco before the hackathon. Plan it for me."
RETRIEVAL_QUERY = "free day in San Francisco: walking, museums, tickets, evening plans"

SUPERSEDED = {
    "Walk the entire city - no transit, 20k steps a day": "knee injury, 45d ago",
    "Museum-first itineraries - anchor every day on a major museum": "reversed 25d ago",
    "Book the marquee ticketed attractions well in advance": "reversed 35d ago",
    "Live music is the point - build nights around late shows": "reversed 20d ago",
}

OUT = Path(__file__).resolve().parent.parent / "demo_data.json"


def main() -> None:
    data: dict = {"question": QUESTION, "capturedAt": datetime.now(timezone.utc).isoformat()}

    print("1/4  seeding + reading travel-guardian's live KV ...")
    memory = guardian.seed()
    data["guardian"] = {
        "preferences": memory["preferences"],
        "visitedCount": len(memory["visited"]),
        "url": "https://travel-guardian.butterbase.dev",
    }

    print("2/4  retrieving from Cognee and ranking both ways ...")
    mems = decay.retrieve(RETRIEVAL_QUERY, DATASET_SELF, top_k=25)

    def rows(window: int) -> list[dict]:
        return [
            {
                "title": m.title,
                "ageDays": m.age_days,
                "date": m.when.isoformat(),
                "kind": m.kind,
                "score": round(m.score(window), 6),
                "superseded": m.title in SUPERSEDED,
                "supersededBy": SUPERSEDED.get(m.title),
            }
            for m in decay.rank(mems, window_days=window, limit=8)
        ]

    data["ranking"] = {
        "total": len(mems),
        "spanDays": max(m.age_days for m in mems),
        "flat": rows(decay.FLAT_WINDOW_DAYS),
        "decayed": rows(decay.DEFAULT_WINDOW_DAYS),
        "window": decay.DEFAULT_WINDOW_DAYS,
    }
    data["ranking"]["flatStale"] = sum(r["superseded"] for r in data["ranking"]["flat"])
    data["ranking"]["decayedStale"] = sum(r["superseded"] for r in data["ranking"]["decayed"])

    print("3/4  asking travel-guardian (live) ...")
    data["guardian"]["answer"] = guardian.ask(QUESTION)

    if "--no-agent" in sys.argv:
        print("4/4  skipped (--no-agent)")
    else:
        print("4/4  running the full agent (slow — 14ish tool calls) ...")
        buf = io.StringIO()
        with brightdata.client() as bright:
            agent = build(bright)
            with redirect_stdout(buf):
                result = agent(QUESTION)
        stream = buf.getvalue()
        data["companion"] = {
            "answer": str(result),
            "toolCalls": [
                line.split("Tool #")[1].split(":", 1)[1].strip()
                for line in stream.splitlines()
                if line.startswith("Tool #") and ":" in line
            ],
        }

    OUT.write_text(json.dumps(data, indent=2))
    r = data["ranking"]
    print(f"\nwrote {OUT.name}")
    print(f"  {r['total']} memories, {r['spanDays']}d span")
    print(f"  stale in top 8 — flat {r['flatStale']}, decayed {r['decayedStale']}")
    if "companion" in data:
        print(f"  agent made {len(data['companion']['toolCalls'])} tool calls")


if __name__ == "__main__":
    main()
