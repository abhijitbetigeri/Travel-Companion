# The agent remembered everything, and got it wrong

*Building a memory layer that knows which version of you is still true —
Battle of the Personal Brains, September 2026. Third place.*

---

In June I built a travel assistant with persistent memory. It's still deployed.
Three months later I pointed it at a traveler who had changed their mind, and
watched it confidently plan a day around preferences that person had abandoned.

It told them to walk. They had torn their knee 45 days earlier.

That gap — between what an agent remembers and what's still true — turned out
to be the whole project.

## Most memory work is about forgetting. This is the other failure.

The agent-memory literature is largely about retention: how to stop a model
losing context, how to persist facts across sessions, how to recall the right
thing from a large store. Reasonable problems.

But there's a failure mode on the other side, and it's worse in a specific way:
an agent that remembers *everything*, weights it all equally, and acts on the
version of you that no longer exists. It doesn't look like a failure. It looks
like confident, personalized service. It just happens to be wrong.

People change their minds. They get injured, move cities, stop eating meat,
start again. A memory system that treats a decision from eleven months ago as
equal in standing to one from last week isn't remembering — it's hoarding.

## The traveler

Fifteen memories, 330 days. Four of the decisions were later reversed:

| They used to | Then |
|---|---|
| Walk 20k steps a day, no transit *(330d)* | Tore their knee — 3mi cap, transit-adjacent *(45d)* |
| Anchor every day on a museum *(300d)* | "Stop routing me through museums" *(25d)* |
| Pre-book marquee attractions *(280d)* | "Skip ticketed attractions" *(35d)* |
| Live music, late shows *(250d)* | "Nothing scheduled past 9pm" *(20d)* |

Plus present-tense context: in San Francisco for a hackathon, no car this trip.

Ask the June app to plan a free day and it produces a twenty-thousand-step
walking route, anchored on SFMOMA, with a pre-booked Alcatraz ticket and a
show at The Fillmore at 8pm.

Every single element is a preference the traveler has since reversed.

## Why the wrong answer wins on merit

The June app learns preferences by keyword matching. Here's its actual merge,
from `api.js`:

```javascript
if (!existingPrefs[p.category].includes(p.value)) {
  existingPrefs[p.category].push(p.value);
}
```

Append-only. Nothing is ever superseded, reweighted, or removed. Then every
stored preference gets flattened into one line of the system prompt, followed
by *"Tailor recommendations to these preferences without being asked."*

Run the traveler's fifteen memories through that and you get:

```
interests   art, museum, history, nightlife
mobility    walking
cuisine     budget, vegetarian
safety      night
```

`museum` was reversed 25 days ago. `nightlife`, 20 days ago. `walking`, 45 days
ago by a knee injury.

But the thing that actually stopped me was what *isn't* in that list.

**The knee injury never registered at all.** The traveler wrote
`"transit-adjacent"`. The keyword table looks for `"public transport"`.
Substring matching never fired, and the single most consequential fact about
this person fell on the floor.

No prompt engineering recovers a fact that was never stored.

## Supersession is a retrieval problem, not a storage problem

The obvious fix is to delete or overwrite the stale preference. I think that's
wrong, for a boring reason: **you don't know a preference is dead until
something contradicts it, and people revert.** The knee heals. The walking
comes back. Deletion is lossy and irreversible; ranking isn't.

So nothing gets deleted. The old memory stays in the graph, fully intact, and
simply ranks below the decision that replaced it:

```
score = relevance × exp(−age_days / window_days)
```

Multiplicative, deliberately. Relevance decides which memories are candidates
at all; recency only decides which of the *relevant* ones survive. Recency
never promotes an irrelevant memory — it just quiets an old one. At a 45-day
window, a 330-day memory is multiplied by `e^(−330/45) ≈ 0.0007`: roughly 900×
quieter than a three-week-old one, but still there, still retrievable, still
able to come back if the newer memory is itself superseded.

Reversed decisions surfaced in the traveler's top 8:

| | |
|---|---|
| Flat retrieval | **4** |
| Recency-weighted | **0** |

That number needs no LLM to reproduce. It's arithmetic on dates.

## What I got wrong about Cognee

I went in assuming this was a configuration problem. Cognee ships
`SearchType.TEMPORAL`, temporal cognification, event nodes with before/after
edges — surely supersession is a parameter.

It isn't, and finding that out was the most useful thing that happened all
night.

Cognee's half is genuinely right. Cognify pulled the dates out of my prose and
extracted the supersession relationships as real graph structure:

```
On 2026-08-08 … knee injury … supersedes the former "walk-everywhere" decision
On 2026-08-18 … Skip ticketed attractions … The advance-booking decision is superseded.
```

187 nodes, 702 edges, from fifteen sentences. The timeline is in there.

But `TEMPORAL` answers *explicit range questions* — "what happened before
2000?", "events between 2001 and 2004". It does not down-weight a stale
preference in a general query. I measured it: asked to plan a day, `TEMPORAL`
and `GRAPH_COMPLETION` returned near-identical itineraries. Both routed through
Alcatraz. Both anchored on SFMOMA. `TEMPORAL` explicitly proposed *"hitting the
20k-step goal"* and booked The Fillmore until 10pm.

**Cognee stores the timeline. It doesn't rank by it.** Those are different
capabilities, and a feature named "temporal" can plausibly mean either. The
only way I found out was by reading the output instead of the documentation.

So the ranking layer became the contribution — ~115 lines sitting on top of
Cognee's retrieval, not replacing it.

## Two kinds of memory need two clocks

Once the personal side worked, the same bug reappeared on the other side.

The agent also reads the live web through Bright Data — opening hours,
closures, prices. Cognify those scrapes into the same graph and the agent will
happily cite a three-week-old scraped opening time as present fact. Identical
failure, different domain.

But the fix can't be identical, because the lifespans aren't:

| | `self` | `world` |
|---|---|---|
| "I tore my knee" | true until something supersedes it | — |
| "Open until 10pm" | — | true for about a day |
| Retrieval | recency-weighted | freshness-gated → re-fetch live |

So: two datasets, two policies. Personal memories decay slowly and supersede.
World facts expire hard, and past the window the agent doesn't trust them — it
re-checks with Bright Data and writes the correction back.

That write-back is the part I like most. The agent's last tool call in a full
run is `remember`. The brain is more correct after the conversation than before
it — not because someone retrained it, but because it noticed its own stale
fact and fixed it.

## The architecture

```
Bright Data (hosted MCP) ──┐
                           ├──▶ Strands Agent ──▶ decay.py ──▶ Cognee (hosted)
recall_self / recall_world ┘                                    self · world
remember
```

Three sponsor tools, each doing one job:

- **Cognee** — the memory. Dated prose in, knowledge graph out, scoped
  retrieval by dataset.
- **Bright Data** — the live world, through their hosted MCP server. Used twice:
  to build the `world` dataset, and to verify it mid-conversation.
- **Strands** — the agent loop. Bright Data's MCP tools and three `@tool`
  memory functions in one list; the model decides the order.

A real trace from the captured run:

```
recall_self → recall_world → search_engine_batch → scrape_batch → search_engine → remember
```

Nobody scripted that sequence. The model checked memory, noticed the world
facts were stale, verified live, and wrote back.

Full detail in [ARCHITECTURE.md](ARCHITECTURE.md).

## Three things that cost me time

**Cognee reads dates out of prose, not fields.** My corpus stored `ageDays: 330`
as JSON. Invisible to cognify. Every memory has to be rendered as a dated
sentence — *"On 2025-10-26, the traveler recorded a decision: …"* — before the
timeline exists at all. This is the highest-risk detail in the build and it's
load-bearing twice, because the re-ranker parses that same shape back out.

**Four LLM bills, three credits.** Cognify runs its own inference, separate from
the agent's. Self-hosted Cognee defaults to OpenAI with no documented Bedrock
path — so self-hosting would have quietly billed a personal key while the Cognee
credit sat unused. The hosted tenant is what puts cognify on the right bill.

**A brand-new AWS account can't invoke Bedrock at all.** Not an IAM problem, not
the Anthropic use-case form — `Error 002` on *every* model including Amazon's
own Nova, which is what ruled out the model-specific explanations. Strands being
model-agnostic meant one env var kept the build moving.

## What I'd do next

- **Learn the window instead of tuning it.** 45 days separates this corpus
  because the knee is 45 days old and everything it superseded is 250+. That
  won't generalize. It should be inferred from observed reversal spacing.
- **Per-type windows.** A dietary restriction and a passing mood about museums
  shouldn't decay at the same rate.
- **Read the supersession edges.** Cognify already extracted *"supersedes the
  former walk-everywhere decision"* into the graph. I rank around that
  structure; I should be reading it.
- **Let the freshness gate schedule its own re-scrapes** rather than waiting to
  be asked.

## The thing worth keeping

The demo that worked wasn't the itinerary. It was a slider.

Drag the decay window from *no decay* to *45 days* and the traveler's abandoned
preferences physically fall out of the ranking while a counter runs 4 → 0. No
model call, no network — arithmetic on dates, recomputed in the browser. Handing
someone the laptop and letting them drag it themselves did more than any amount
of explaining.

Which is maybe the real lesson. The interesting claim here isn't that memory
should be a knowledge graph, or that agents should check the live web. It's
narrower and more checkable:

**Memory shouldn't just store what you said. It should know which version of
you is still true.**

---

*Live demo · [abhijitbetigeri.github.io/Travel-Companion](https://abhijitbetigeri.github.io/Travel-Companion/)*
*Code · [github.com/abhijitbetigeri/Travel-Companion](https://github.com/abhijitbetigeri/Travel-Companion)*
*The "before" app, still running · [travel-guardian.butterbase.dev](https://travel-guardian.butterbase.dev)*
