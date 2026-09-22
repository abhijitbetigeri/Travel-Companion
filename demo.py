"""The demo. One question, one memory, one variable.

    python demo.py            # full run
    python demo.py --ranking  # just the ranking table (no model calls, instant)

Stage 1 is deterministic and needs no LLM: the same 15 memories, ranked twice,
differing only in the decay window. Four of the traveler's decisions were later
reversed, and flat ranking puts the reversed ones on top.
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from travel_companion import brightdata, decay
from travel_companion.agent import build
from travel_companion.config import DATASET_SELF

console = Console()

QUESTION = "I have a free day in San Francisco before the hackathon. Plan it for me."
RETRIEVAL_QUERY = "free day in San Francisco: walking, museums, tickets, evening plans"

SUPERSEDED = {
    "Walk the entire city - no transit, 20k steps a day",
    "Museum-first itineraries - anchor every day on a major museum",
    "Book the marquee ticketed attractions well in advance",
    "Live music is the point - build nights around late shows",
}


def ranking_table() -> None:
    mems = decay.retrieve(RETRIEVAL_QUERY, DATASET_SELF, top_k=25)
    console.print(f"\n[dim]{len(mems)} memories in the brain, spanning "
                  f"{max(m.age_days for m in mems)} days[/dim]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("#", width=3)
    table.add_column("Flat ranking (decay off)")
    table.add_column("age", justify="right", width=6)
    table.add_column("Recency-weighted (45d)")
    table.add_column("age", justify="right", width=6)

    flat = decay.rank(mems, window_days=decay.FLAT_WINDOW_DAYS, limit=8)
    warm = decay.rank(mems, window_days=decay.DEFAULT_WINDOW_DAYS, limit=8)

    for i, (f, w) in enumerate(zip(flat, warm), 1):
        fo = f.title in SUPERSEDED
        wo = w.title in SUPERSEDED
        table.add_row(
            str(i),
            f"[red]{f.title[:44]}[/red]" if fo else f.title[:44],
            f"[red]{f.age_days}d[/red]" if fo else f"{f.age_days}d",
            f"[red]{w.title[:44]}[/red]" if wo else f"[green]{w.title[:44]}[/green]",
            f"[red]{w.age_days}d[/red]" if wo else f"[green]{w.age_days}d[/green]",
        )

    console.print(table)
    console.print(
        f"\n[red]red[/red] = a decision the traveler has since reversed. "
        f"Flat surfaces {sum(m.title in SUPERSEDED for m in flat)} of them in its top 8; "
        f"recency-weighted surfaces {sum(m.title in SUPERSEDED for m in warm)}.\n"
    )


def main() -> None:
    console.print(Panel.fit(QUESTION, title="the question", border_style="cyan"))

    console.rule("[bold]1. The same memory, ranked two ways")
    ranking_table()

    if "--ranking" in sys.argv:
        return

    console.rule("[bold]2. The agent: memory + live web + write-back")
    console.print()
    with brightdata.client() as bright:
        agent = build(bright)
        console.print(str(agent(QUESTION)))


if __name__ == "__main__":
    main()
