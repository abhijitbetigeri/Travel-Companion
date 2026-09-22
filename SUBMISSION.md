# Devpost submission — copy-paste

## Elevator pitch (163 chars)

A travel agent that plans your day from your own history — and knows which of
your preferences you've since abandoned. Old memories aren't deleted, they just lose.

---

## About the project

```markdown
## Inspiration

In June I built a travel assistant with persistent memory. It's still deployed.
Three months later I fed it a traveler who had changed their mind — and watched
it confidently plan a day around preferences that person had abandoned.

It told them to walk. They tore their knee 45 days ago.

Most agent-memory work is about forgetting too much. This is the opposite
failure, and nobody was working on it: an agent that remembers everything,
weights it all equally, and acts on the version of you that no longer exists.

## What it does

Travel Companion plans a day from a traveler's own history, and knows which of
their preferences still hold.

The traveler has 15 memories spanning 330 days. Four of their decisions were
later reversed:

| They used to | Now |
|---|---|
| Walk 20k steps a day, no transit (330d) | Knee injury — 3mi cap, transit-adjacent (45d) |
| Anchor every day on a museum (300d) | Stop routing me through museums (25d) |
| Pre-book marquee attractions (280d) | Skip ticketed attractions (35d) |
| Live music, late shows (250d) | Nothing scheduled past 9pm (20d) |

Ask the old app to plan a day and it says "knowing you enjoy walking — here's a
forty-minute walk, then a scenic walk, then a longer walk to the Mission."

Ask Travel Companion and it says 2.7 miles, all transit-adjacent, no tickets,
timed to golden hour, home before nine — and it cites the date of every
constraint it honored.

Then it checks the live web, because opening hours go stale in a way a knee
injury doesn't, and writes corrections back into memory.

**The demo is interactive.** Drag the decay window and watch the abandoned
preferences physically fall out of the traveler's top 8, live:
https://abhijitbetigeri.github.io/Travel-Companion/

## How we built it

**Cognee** — the memory. Each of the 15 memories is rendered as a *dated
sentence* ("On 2025-10-26, the traveler recorded a decision: …") and cognified
into a knowledge graph. That rendering matters: Cognee extracts the timeline
out of the prose, so a JSON field called `ageDays` would have been invisible
to it. Two datasets with different lifecycles — `self` (durable, supersedable)
and `world` (expires fast).

**Bright Data** — the live world, via their hosted remote MCP server. Used two
ways: to build the `world` dataset up front, and for the agent to re-verify
stale facts mid-conversation.

**AWS Strands** — the agent loop. Bright Data's MCP tools plus three custom
`@tool` functions: `recall_self`, `recall_world`, `remember`.

**The ranking layer** — the part that's ours:

```
final_score = relevance × exp(−age_days / window_days)
```

Multiplicative, not a replacement. Relevance decides which memories are
candidates; recency decides which of the relevant ones survive. Nothing is
deleted — the abandoned preference is still in the graph and simply loses.

## Challenges we ran into

**Cognee stores the timeline but doesn't rank by it.** We assumed
`SearchType.TEMPORAL` would solve supersession. It doesn't — it answers
explicit range questions ("what happened before 2000?"), not "what still holds
now". We measured it: TEMPORAL and GRAPH_COMPLETION returned near-identical
itineraries, both routing through Alcatraz, one of them explicitly chasing the
20,000-step goal. Cognify's half was perfect — dates *and* supersession
language landed in the graph. Only the ranking was missing. So we built it.

**Bedrock was blocked three different ways.** First `bedrock:InvokeModel`
wasn't in the IAM policy. Then the Anthropic use-case form. Then Error 002 on
*every* model — including Amazon's own Nova, which ruled out a model-specific
gate and pointed at a brand-new account not yet enabled for Bedrock inference.
Strands is model-agnostic, so `MODEL_PROVIDER` switches providers with no other
change, and we kept building.

**Credits don't map one-to-one onto bills.** There are four LLM bills in this
architecture and three credits. Cognify runs its own inference, separate from
the agent's, and self-hosted Cognee defaults to OpenAI with no documented
Bedrock path — so self-hosting would have quietly billed a personal key. Using
the hosted tenant is what put cognify on the Cognee credit.

## Accomplishments that we're proud of

**The comparison isn't a strawman.** `guardian.py` is a port of the June app's
real memory code — its literal keyword table, its append-only `.push()` merge,
its prompt assembly. The same 15 memories go through its own algorithm. And the
app is still deployed, so you can check.

**Its own extractor indicted it better than we could.** Running it produced
`interests: [art, museum, history, nightlife]`, `mobility: [walking]` — three
reversed preferences kept. And the knee injury missing entirely, because the
traveler wrote "transit-adjacent" and the keyword table looks for "public
transport". Substring matching never fired on the single most consequential
fact about this person.

**Reversed decisions in the top 8: flat 4, recency-weighted 0.** And that
number needs no LLM to reproduce — it's arithmetic on dates.

**The loop closes.** The agent's last tool call is `remember`. It writes back
what the live web taught it, so the brain is more correct after the
conversation than before it.

## What we learned

**Supersession is a retrieval problem, not a storage problem.** The instinct is
to delete or overwrite the old preference. But you don't know a preference is
dead until something contradicts it, and people revert — the knee heals.
Ranking is reversible; deletion isn't.

**"Which version of you" needs two different clocks.** Who you are supersedes
slowly. What's true about the world expires in hours. Cognify both into one
undifferentiated graph and the agent will cite a three-week-old scrape as
present fact — the same bug, on the world side.

**Read the vendor's retrieval semantics before designing around them.** A
feature named "temporal" did something quite different from what we needed, and
we only found out by measuring the output.

## What's next for Travel Companion

- **Learn the decay window instead of tuning it.** 45 days separates this
  corpus cleanly because the knee is 45 days old and everything it superseded
  is 250+. That won't generalize — it should be inferred from observed reversal
  spacing.
- **Per-memory-type windows.** A dietary restriction and a mood about museums
  shouldn't decay at the same rate.
- **Explicit supersession edges.** Cognify already extracts the language
  ("supersedes the former walk-everywhere decision") into the graph. We rank
  around it; we should read it.
- **Close the loop on the world side too** — let the freshness gate schedule
  its own re-scrapes rather than waiting to be asked.
```

---

## Built with

```
cognee, bright-data, aws-strands, model-context-protocol, python,
knowledge-graph, amazon-bedrock, anthropic-claude, rest-api, javascript,
html, css, github-pages
```

## "Try it out" links

```
https://abhijitbetigeri.github.io/Travel-Companion/
https://github.com/abhijitbetigeri/Travel-Companion
https://travel-guardian.butterbase.dev
```

## Image gallery

1. `docs/shots/full.png` — the whole argument in one image
2. `docs/shots/1-hero.png` — hero, 3:2

## Video demo

Optional. 30 seconds: drag the slider from *No decay* to *45 days*, counter
runs 4 → 0.
