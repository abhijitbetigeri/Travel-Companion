# Travel Companion

A travel agent whose memory knows which version of you is still current.

Most agent-memory work fixes forgetting. This targets the opposite failure: an
agent that remembers everything, weights it all equally, and confidently acts
on preferences you abandoned months ago.

> **Supersession is a retrieval problem, not a storage problem.**
> Nothing is deleted or edited. The old memory is still in the graph — it just
> loses.

Built for **Battle of the Personal Brains** (Bright Data · Cognee · AWS Strands).

---

## The demo

One question, asked three ways. The traveler tore their knee 45 days ago and
has a hackathon in the morning.

> *"I have a free day in San Francisco before the hackathon. Plan it for me."*

| | Flat retrieval | Recency-weighted |
|---|---|---|
| Getting around | 20,000-step walking route | transit-adjacent, 3mi cap |
| Daytime | museum-anchored, pre-booked ticket | outdoors, no ticket |
| Evening | live music, 8:00pm onwards | done by 8:30pm |

Only one thing changed between those columns: the decay window.
Reversed decisions surfaced in the top 8 — **flat 4, weighted 0**.

```bash
./demo --prefs   # deterministic, no model calls, instant
```

Then the live half — a stored fact about the world goes stale, Bright Data
re-checks it, the plan changes again, and the correction is written back.

See [ARCHITECTURE.md](ARCHITECTURE.md) for how and why.

---

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env     # fill in Cognee, Bright Data, AWS
aws configure            # or export AWS creds
```

**Run the credential checks first.** Each of the three can fail in a boring
way, and finding out later is what kills projects:

```bash
./demo smoke
```

Set `MODEL_PROVIDER=bedrock` to use AWS, or `anthropic` to use the Anthropic
API directly. Bedrock is fully wired but blocked on this AWS account — see
Credit routing in [ARCHITECTURE.md](ARCHITECTURE.md).

## Seed the brain

```bash
./demo ingest self
./demo ingest world --query "Batteries to Bluffs Trail hours"
```

`cognify` is the slow, billed call. Seed once, then iterate on retrieval.

## Run

```bash
./demo                                    # the three-stage demo
./demo ask "your question"  # just the agent
```

---

## Stack

| Piece | What it does |
|---|---|
| **Cognee** (hosted tenant) | the brain — knowledge graph over the traveler's history |
| **Bright Data** (hosted MCP) | the live world — search and scrape |
| **AWS Strands** + Bedrock | the agent loop and its reasoning model |

## Credits

Lineage: [agent-memory](https://github.com/abhijitbetigeri/agent-memory) — the
supersession thesis and the 15-entry corpus, originally on Elasticsearch +
Mastra. [travel-guardian](https://github.com/abhijitbetigeri/travel-guardian) —
the domain ontology, and the append-only preference bug this exists to fix.
