# Architecture

## The claim

An agent that remembers everything and weights it all equally will confidently
act on preferences you abandoned months ago.

> **Supersession is a retrieval problem, not a storage problem.**
> Nothing is deleted or edited. The stale memory is still in the graph — it
> just loses.

The same bug appears twice, and one idea fixes both:

| Where | The failure |
|---|---|
| Personal memory | A 330-day-old "walk 20k steps a day" outranks a 45-day-old knee injury |
| World memory | A three-week-old scraped opening time gets cited as present fact |

---

## Topology

Both external services are reached over HTTPS. Nothing runs locally except the
agent process.

```
        ┌───────────────────────────────────┐
        │  Bright Data — hosted MCP server  │
        │  mcp.brightdata.com/mcp           │
        │  search_engine · scrape_as_markdown
        │  search_engine_batch · scrape_batch
        └─────────────────┬─────────────────┘
                          │ streamable HTTP
                          ▼
  ┌───────────────────────────────────────────────────┐
  │  Strands Agent                        agent.py    │
  │                                                   │
  │  model    BedrockModel | AnthropicModel           │
  │  tools    Bright Data MCP tools                   │
  │           + recall_self   ─┐                      │
  │           + recall_world   │  tools.py            │
  │           + remember      ─┘                      │
  └───────────────────────┬───────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
     ┌─────────────────┐   ┌───────────────────────┐
     │  decay.py       │   │  cognee_client.py     │
     │  recency        │──▶│  REST + X-Api-Key     │
     │  re-ranking     │   └───────────┬───────────┘
     └─────────────────┘               │
                                       ▼
  ┌───────────────────────────────────────────────────┐
  │  Cognee — hosted tenant                           │
  │                                                   │
  │   dataset: self          dataset: world           │
  │   durable                volatile                 │
  │   supersedable           expires in hours         │
  │   recency-ranked         freshness-gated          │
  │                                                   │
  │   187 nodes · 702 edges, built by cognify         │
  └───────────────────────────────────────────────────┘
```

The tenant is **REST-only** — `/mcp`, `/api/v1/mcp` and `/sse` all 404. Cognee
is wrapped as Strands `@tool` functions rather than consumed as MCP. That turned
out better anyway: wrapping REST directly gives per-call control of `datasets`
and `searchType`, which the ranking layer needs.

---

## The four layers

### 1 · Ingest — `ingest.py`

Fifteen memories in `data/self_memory.json`, each with a relative `ageDays`.
Ingest renders every one as a **dated sentence**:

```
On 2025-10-26, the traveler recorded a decision: Walk the entire city — no
transit, 20k steps a day.
[body]
Tags: mobility, walking, routing.
This was recorded 330 days ago.
```

**Why prose and not a field.** Cognee extracts timestamps *out of the text* to
build event nodes joined by before/after/during edges. A JSON key named
`ageDays` is invisible to it.

This rendering is load-bearing twice — cognify's temporal extraction reads it,
and `decay.py`'s `ENTRY_RE` parses chunks back into individual memories by
matching exactly this shape. Change the wording and retrieval silently returns
zero memories.

### 2 · Storage — Cognee

```
POST /api/v1/datasets/    create `self` and `world`
POST /api/v1/add_text     stage the dated prose
POST /api/v1/cognify      build the graph  ← the slow, billed call
POST /api/v1/recall       retrieve, scoped by dataset + searchType
GET  /api/v1/visualize    standalone graph viewer (see graph.html)
```

Cognify does its half correctly. Dates *and* supersession language land in the
graph as real structure:

```
On 2026-08-08 … knee injury … supersedes the former "walk-everywhere" decision
On 2026-08-18 … Skip ticketed attractions … The advance-booking decision is superseded.
```

### 3 · Ranking — `decay.py` ← the contribution

**Cognee stores the timeline; it does not rank by it.** Measured, not assumed.

`SearchType.TEMPORAL` answers explicit range questions ("what happened before
2000?"). It does not down-weight a stale preference in a general query. Asked
to plan a day, `TEMPORAL` and `GRAPH_COMPLETION` returned near-identical
itineraries — both via Alcatraz, both anchored on SFMOMA, one explicitly
chasing the 20,000-step goal and booking The Fillmore until 10pm. All four are
decisions the traveler reversed.

So the ranking sits on top of Cognee's retrieval:

```
score = relevance × exp(−age_days / window_days)

relevance = 1 / (1 + rank)     # Cognee returns results ordered; decay the rank
                               # rather than inventing a similarity number
```

**Multiplicative, not a replacement.** Relevance decides which memories are
candidates at all; recency decides which of the relevant ones survive. A
330-day memory at `window=45` is multiplied by `e^(−330/45) ≈ 0.0007` — roughly
900× quieter than a 20-day one. It isn't removed. It loses.

| Rank | Flat (window 3650d) | Recency-weighted (45d) |
|---|---|---|
| 1 | Walk 20k steps a day — **330d** | Skip ticketed attractions — 35d |
| 2 | Museum-first itineraries — **300d** | In SF for a hackathon — 5d |
| 3 | Skip ticketed attractions — 35d | Stop routing me through museums — 25d |
| 4 | Pre-book marquee tickets — **280d** | Golden hour is the constraint — 12d |
| 5 | Live music, late shows — **250d** | No car this trip — 3d |

**Reversed decisions in the top 8: flat 4, weighted 0.** Reproducible with no
LLM — it's arithmetic on dates (`./demo --prefs`).

### 4 · Agent — `agent.py`

A Strands `Agent` whose tool list is Bright Data's MCP tools plus the three
memory tools. Everything runs inside the MCP context manager; tools taken from
an `MCPClient` stop working the moment that block exits.

The system prompt encodes the policy, not the plan: recall before assuming,
trust recent decisions over older contradictions, re-verify world facts past
the freshness window, write corrections back.

---

## Two datasets, two lifecycles

The core design decision.

| | `self` | `world` |
|---|---|---|
| Source | the traveler's decisions, patterns, feedback | Bright Data scrapes |
| Written by | `ingest self`, and `remember` at runtime | `ingest world`, and `remember` after a live correction |
| Lifespan | durable — superseded, never deleted | hours — re-verify or discard |
| Retrieval | `CHUNKS` + recency decay | `TEMPORAL` + a freshness gate forcing live re-fetch |

Cognify both into one undifferentiated graph and the agent cannot tell "I tore
my knee" — true until something supersedes it — from "open until 10pm," true
for about a day. Keeping them apart is what makes the freshness rule
expressible at all.

---

## Bright Data plays two roles

- **Write path** — scrape → cognify into `world`. Builds the brain's picture of
  the outside world.
- **Read path** — the agent calls it live, mid-conversation, to *check what
  memory claims*.

Same tool, two jobs. That duality is what makes this a personal brain grounded
in the live world rather than RAG with a scraper bolted on.

---

## One request, end to end

```
"I have a free day in San Francisco before the hackathon. Plan it for me."

 1. recall_self          decay.retrieve → CHUNKS from `self`
                         decay._parse   → 15 Memory objects with dates
                         decay.rank     → top 8 by relevance × recency
 2. recall_world         stored facts + their fetch timestamps
 3. search_engine        past the freshness window → verify live
 4. scrape_batch         pull the current detail
 5. …                    agent reconciles memory against the live world
 6. remember             write the correction back to Cognee
```

That trace is real — captured in `demo_data.json`, rendered as chips on the
demo page.

---

## The control group — `guardian.py`

The comparison is not a strawman. `guardian.py` is a faithful port of the June
app's real memory code from
[`travel-guardian/frontend/src/api.js`](https://github.com/abhijitbetigeri/travel-guardian/blob/main/frontend/src/api.js):

- its literal `PREF_KEYWORDS` table (api.js:144-149)
- `extract` ≡ `saveConversationMemory` — substring matching, no LLM
- `accumulate` ≡ the append-only merge (api.js:168-179):
  `if (!existingPrefs[c].includes(v)) existingPrefs[c].push(v)`
- `build_memory_context` ≡ `chatWithAgent`'s prompt assembly (api.js:194-208)

Feed it the same 15 memories and its own algorithm produces:

```
interests   art, museum, history, nightlife
mobility    walking
cuisine     budget, vegetarian
safety      night
```

Three of those are reversed decisions. And the knee injury never registers at
all — the traveler wrote `"transit-adjacent"`, the keyword table looks for
`"public transport"`, and substring matching never fires on the single most
consequential constraint.

The app is still deployed at `travel-guardian.butterbase.dev`, and
`guardian.py` queries it live, so the comparison is checkable rather than
asserted.

---

## Module map

```
travel_companion/
  config.py           env, dataset names, freshness window, model provider
  cognee_client.py    REST wrapper — datasets, add_text, cognify, recall
  decay.py            recency re-ranking over Cognee retrieval — the thesis
  brightdata.py       hosted MCP client + one-shot search for ingest
  tools.py            recall_self / recall_world / remember as @tool
  agent.py            model + Bright Data MCP + memory tools
  ingest.py           seed both datasets; renders dates into prose
  guardian.py         faithful port of the June app — the control group

compare.py            head-to-head; --prefs is instant and needs no LLM
demo                  launcher; handles venv and cwd
scripts/
  smoke.py            three credential checks
  snapshot.py         capture a real run → demo_data.json
  record.py           drive the live page with Playwright → docs/demo.webm

index.html            the interactive demo — slider recomputes ranking client-side
app.js · demo.css · styles.css
graph.html            the actual Cognee graph, 187 nodes / 702 edges
demo_data.json        captured real run, powering the static page
data/self_memory.json 15 memories, 330-day span, four reversals
```

---

## Credit routing

Four LLM bills, three credits — the gap is easy to miss.

| Credit | Pays for |
|---|---|
| Cognee | ingest, **cognify**, recall |
| Bright Data | search + scrape |
| AWS | the Strands agent's reasoning (Bedrock) |
| — | *cognify's own inference, if self-hosted* |

Cognify runs an LLM over every chunk to extract entities and temporal edges —
its own spend, separate from the agent's. Self-hosted Cognee defaults to OpenAI
(`llm_provider = "openai"`, no documented Bedrock path), so self-hosting would
quietly bill a personal key. **The hosted tenant is what puts cognify on the
Cognee credit.**

The tenant's `/api/v1/quotas/usage` reports storage only, not tokens — there's
no burn-down. Don't re-cognify casually.

---

## Known limitations

- **The 45-day window is tuned, not learned.** It separates this corpus because
  the knee is 45 days old and everything it superseded is 250+. A corpus with
  different reversal spacing needs a different window. Per-memory-type windows
  would be better still.
- **`decay.py` parses dates out of chunk text.** If `ingest.py`'s rendering
  changes, `ENTRY_RE` must change with it or retrieval silently returns zero
  memories. `./demo --prefs` catches this instantly — no model, and it prints
  the parsed count.
- **Supersession edges are extracted but unused.** Cognify already puts
  *"supersedes the former walk-everywhere decision"* into the graph. The ranker
  works around that structure rather than reading it.
- **MCP tools die outside the context manager.** The agent is built and run
  inside `with brightdata.client()`. Moving `Agent(...)` out of that block
  fails at tool-call time, not construction time.
- **Bedrock is wired but unusable on the current AWS account.** Every model
  returns `ValidationException Error 002` — including Amazon's own Nova, which
  rules out the Anthropic use-case gate. IAM is correct and the inference
  profiles are ACTIVE; the account is new and not yet enabled for Bedrock
  inference. `MODEL_PROVIDER` switches providers with no other change.
