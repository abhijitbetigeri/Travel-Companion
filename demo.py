"""The demo. One question, three retrievals, one visible change of mind.

    python demo.py

Stage 1 and 2 are the same question against the same memory, differing only in
whether retrieval is time-aware. That is the whole argument: the traveler tore
their knee 45 days ago, and flat retrieval still hands back the 330-day-old
"walk 20k steps a day" decision as though it stood.

Stage 3 is the live half — the world moves, and stored world facts rot.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from travel_companion import brightdata
from travel_companion import cognee_client as cog
from travel_companion.agent import build
from travel_companion.config import DATASET_SELF

console = Console()

QUESTION = "I have a free day in San Francisco before the hackathon. Plan it for me."

# Each pair is (superseded decision, the decision that replaced it).
SUPERSESSIONS = [
    ("Walk 20k steps a day, no transit (330d)", "Knee injury, 3mi cap, transit-adjacent (45d)"),
    ("Museum-first itineraries (300d)", "Stop routing me through museums (25d)"),
    ("Pre-book marquee ticketed attractions (280d)", "Skip ticketed attractions (35d)"),
    ("Live music, late shows (250d)", "Nothing scheduled past 9pm (20d)"),
]


def header(n: int, title: str, subtitle: str) -> None:
    console.print()
    console.rule(f"[bold]{n}. {title}")
    console.print(f"[dim]{subtitle}[/dim]\n")


def main() -> None:
    console.print(Panel.fit(QUESTION, title="the question", border_style="cyan"))

    console.print("\n[dim]four reversals sitting in this memory:[/dim]")
    for old, new in SUPERSESSIONS:
        console.print(f"  [red]{old}[/red]  ->  [green]{new}[/green]")

    header(1, "Flat retrieval", "same memory, no sense of time — the failure mode")
    flat = cog.recall(QUESTION, DATASET_SELF, search_type=cog.GRAPH, top_k=10)
    console.print(str(flat)[:2000])

    header(2, "Time-aware retrieval", "SearchType.TEMPORAL — recent decisions win")
    temporal = cog.recall(QUESTION, DATASET_SELF, search_type=cog.TEMPORAL, top_k=10)
    console.print(str(temporal)[:2000])

    header(3, "The full agent", "memory + live web + write-back")
    with brightdata.client() as bright:
        agent = build(bright)
        console.print(str(agent(QUESTION)))


if __name__ == "__main__":
    main()
