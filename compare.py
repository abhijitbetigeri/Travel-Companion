"""Head-to-head: the same traveler, the same question, two memory designs.

    python compare.py            # full run, both systems live
    python compare.py --prefs    # just the preference tables (instant, no LLM)
    python compare.py --seed     # re-seed travel-guardian's live KV first

LEFT  — travel-guardian (June 2026), still deployed at travel-guardian.butterbase.dev.
        Preferences extracted by substring matching, appended forever, flattened
        into one prompt line. No dates, no supersession.

RIGHT — Travel Companion (this repo). Same 15 memories cognified into a Cognee
        knowledge graph, retrieved, then recency-weighted so a reversed decision
        loses to the one that replaced it.

Both read from data/self_memory.json. One corpus, two designs, one question.
"""

from __future__ import annotations

import sys

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from travel_companion import brightdata, decay, guardian
from travel_companion.agent import build
from travel_companion.config import DATASET_SELF

console = Console()

QUESTION = "I have a free day in San Francisco before the hackathon. Plan it for me."
RETRIEVAL_QUERY = "free day in San Francisco: walking, museums, tickets, evening plans"

# What the traveler actually decided most recently, per data/self_memory.json.
CURRENT_TRUTH = {
    "mobility": "knee injury 45d ago — 3mi cap, no sustained hills, transit-adjacent",
    "interests": "stop routing me through museums (25d ago); outdoors, golden hour",
    "tickets": "skip ticketed attractions (35d ago)",
    "evening": "nothing scheduled past 9pm (20d ago)",
}


def preference_tables() -> None:
    memory = guardian.read() or guardian.seed()
    prefs = memory.get("preferences", {})

    left = Table(title="travel-guardian · append-only", title_style="bold red")
    left.add_column("category")
    left.add_column("stored preferences")
    for cat, vals in prefs.items():
        left.add_row(cat, ", ".join(vals))
    left.add_row("", "")
    left.add_row("[dim]dates[/dim]", "[red]none — every value equally weighted[/red]")

    mems = decay.retrieve(RETRIEVAL_QUERY, DATASET_SELF, top_k=25)
    winners = decay.rank(mems, window_days=decay.DEFAULT_WINDOW_DAYS, limit=6)
    right = Table(title="Travel Companion · recency-weighted", title_style="bold green")
    right.add_column("age", justify="right")
    right.add_column("what actually holds now")
    for m in winners:
        right.add_row(f"{m.age_days}d", m.title[:52])

    console.print(Columns([left, right], equal=True, expand=True))

    console.print("\n[bold]What travel-guardian's extractor got wrong[/bold]")
    console.print(
        "  [red]keeps[/red] 'museum'   — reversed 25 days ago\n"
        "  [red]keeps[/red] 'nightlife'— reversed 20 days ago\n"
        "  [red]keeps[/red] 'walking'  — reversed 45 days ago by the knee injury\n"
        "  [red]misses[/red] the knee injury entirely — 'transit-adjacent' does not\n"
        "         contain the literal string 'public transport', so substring\n"
        "         matching never fires on the single most important constraint\n"
    )


def main() -> None:
    if "--seed" in sys.argv:
        guardian.seed()
        console.print("[dim]re-seeded travel-guardian's live KV[/dim]")

    console.print(Panel.fit(QUESTION, title="one question", border_style="cyan"))
    console.rule("[bold]1. What each system believes about the traveler")
    preference_tables()

    if "--prefs" in sys.argv:
        return

    console.rule("[bold]2. travel-guardian (live at butterbase.dev)")
    console.print()
    console.print(Panel(guardian.ask(QUESTION), border_style="red"))

    console.rule("[bold]3. Travel Companion")
    console.print()
    with brightdata.client() as bright:
        agent = build(bright)
        console.print(Panel(str(agent(QUESTION)), border_style="green"))


if __name__ == "__main__":
    main()
