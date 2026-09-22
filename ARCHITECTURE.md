# Architecture

## The claim

An agent that remembers everything and weights it all equally will confidently
act on preferences you abandoned months ago. **Supersession is a retrieval
problem, not a storage problem** — nothing here is deleted or edited, the stale
memory is still in the graph, it just loses.

The same bug shows up twice, and this system fixes both with one idea:

| Where | The bug |
|---|---|
| Personal memory | A 330-day-old "walk 20k steps a day" outranks a 45-day-old knee injury |
| World memory | A three-week-old scraped opening time is cited as present fact |

## Topology

Both external services are reached over HTTPS. Nothing runs locally except the
agent process.

```
                 ┌──────────────────────────────┐
                 │  Bright Data (hosted MCP)    │
                 │  mcp.brightdata.com/mcp      │
                 │  search_engine, scrape_*     │
                 └──────────────┬───────────────┘
                                │ streamable HTTP
                                ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Strands Agent                                          │
  │  model: Bedrock (AWS credit)                            │
  │  tools: Bright Data MCP  +  recall_self                 │
  │                             recall_world                │
  │                             remember                    │
  └──────────────┬──────────────────────────────────────────┘
                 │ REST + X-Api-Key
                 ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Cognee (hosted tenant)   tenant-a394e3e6….aws.cognee.ai│
  │                                                         │
  │   dataset: self            dataset: world               │
  │   durable, supersedable    volatile, expires fast       │
  │   SearchType.TEMPORAL      + freshness gate             │
  └─────────────────────────────────────────────────────────┘
```

The tenant is **REST-only** — `/mcp`, `/api/v1/mcp` and `/sse` all 404. Cognee
is wrapped as Strands `@tool` functions in `travel_companion/tools.py`. That
turned out to be the better path anyway: wrapping REST directly is what gives
per-call control of `datasets` and `searchType`, which is exactly what the two
knobs below need.

## The two knobs

Every retrieval is one call to `/api/v1/recall` with two parameters. The entire
demo is these two knobs moving.

```
recall(query, datasets=["self"],  searchType="GRAPH_COMPLETION")  -> the wrong answer
recall(query, datasets=["self"],  searchType="TEMPORAL")          -> the right answer
recall(query, datasets=["world"], searchType="TEMPORAL")          -> what we know about the world
```

No second backend, no porting, no custom ranker. `TEMPORAL` is native to the
tenant's `SearchType` enum, alongside `GRAPH_COMPLETION`, `AGENTIC_COMPLETION`,
`CYPHER`, `FEELING_LUCKY` and 15 others.

## Two datasets, two lifecycles

This separation is the core design decision.

|  | `self` | `world` |
|---|---|---|
| Source | the traveler's own decisions, patterns, feedback | Bright Data scrapes |
| Written by | `ingest.py self`, and `remember` at runtime | `ingest.py world`, and `remember` after a live correction |
| Lifespan | durable — superseded, never deleted | hours — re-verify or discard |
| Retrieval | `TEMPORAL`; recent decisions beat older contradictions | `TEMPORAL` + a freshness gate that forces a live re-fetch |

Cognify both into one undifferentiated graph and the agent cannot tell "I tore
my knee" (true until something supersedes it) from "open until 10pm" (true for
about a day). Keeping them apart is what makes the freshness rule expressible
at all.

## Why dates are written into the prose

Cognee's temporal cognification reads timestamps **out of the text** to build
event nodes joined by before/after/during edges. A JSON field named `ageDays`
is invisible to it.

So `ingest.py` renders every memory as a dated sentence:

```
On 2025-10-26, the traveler recorded a decision: Walk the entire city — no transit, 20k steps a day.
…
This was recorded 330 days ago.
```

Get this wrong and `TEMPORAL` quietly degrades into ordinary graph search, the
A/B collapses, and the demo has no punchline. It is the highest-risk detail in
the build.

## Bright Data plays two roles

- **Write path, before the demo** — scrape → cognify into `world`. This *builds*
  the brain's picture of the outside world.
- **Read path, during the demo** — the agent calls Bright Data live to *check
  what memory claims*.

Same tool, two jobs. That duality is what makes this a personal brain grounded
in the live world rather than RAG with a scraper bolted on.

## The loop that closes

1. `recall_self` → current constraints (knee, no car, early nights, hackathon).
2. `recall_world` → a stored fact, with the timestamp it was fetched at.
3. Past the freshness window → Bright Data re-checks it **live**.
4. Live web contradicts stored memory → agent says so, fixes the plan.
5. `remember` writes the correction back.

Step 5 is the point. The brain is more correct after the conversation than
before it — learning demonstrated on stage, not asserted on a slide.

## The corpus

15 memories spanning 330 days, in `data/self_memory.json`. Four clean
reversals:

| Superseded | Current |
|---|---|
| Walk 20k steps a day, no transit (330d) | Knee injury — 3mi cap, transit-adjacent (45d) |
| Museum-first itineraries (300d) | Stop routing me through museums (25d) |
| Pre-book marquee ticketed attractions (280d) | Skip ticketed attractions (35d) |
| Live music, late shows (250d) | Nothing scheduled past 9pm (20d) |

Plus present-tense context: in SF for a hackathon (5d), no car (3d).

A flat retriever answers the question with a 20,000-step walking route ending
at an 8pm show. Every single one of those is a preference the traveler has
since reversed.

## Credit routing

Four LLM bills, three credits — the gap is the one people miss.

| Credit | Pays for |
|---|---|
| AWS | the Strands agent's reasoning (Bedrock) |
| Bright Data | search + scrape |
| Cognee | ingest, **cognify**, recall |

Cognify runs an LLM over every chunk to extract entities and temporal edges —
its own spend, separate from the agent's. Self-hosted Cognee defaults to
OpenAI (`llm_provider = "openai"`) and has no documented Bedrock path, so it
would bill a personal key. **Using the hosted tenant is what puts cognify on
the Cognee credit.**

The tenant's `/api/v1/quotas/usage` reports storage only, not tokens — there is
no token burn-down. Don't re-cognify the corpus casually.

## Files

```
travel_companion/
  config.py          env loading, dataset names, freshness window
  cognee_client.py   REST wrapper — datasets, add_text, cognify, recall
  brightdata.py      hosted MCP client + one-shot search for ingest
  tools.py           recall_self / recall_world / remember as @tool
  agent.py           Bedrock model + Bright Data MCP + memory tools
  ingest.py          seed both datasets; renders dates into prose
demo.py              flat vs temporal vs full agent
scripts/smoke.py     three credential checks
data/self_memory.json
```

## Known risks

- **Bedrock model access is per-region opt-in.** An un-enabled model returns
  AccessDenied, not "not found". `scripts/smoke.py bedrock` clears it.
- **MCP tools die outside the context manager.** The agent is built and run
  inside `with brightdata.client()`. Moving `Agent(...)` out of that block
  fails at tool-call time, not construction time.
- **Cognify is slow and billed.** Seed once, then iterate on retrieval.
- **If `TEMPORAL` doesn't separate the pairs**, the dates aren't landing in the
  graph. Check `/api/v1/visualize/json` for event nodes before debugging
  anything else.
