# The pitch — 3 minutes

**Demo page:** https://abhijitbetigeri.github.io/Travel-Companion/demo.html
**Terminal backup:** `./demo --prefs` (instant, no network)

Scroll the demo page as you talk. One act per beat.

---

## 0:00 — the hook

> "Three months ago I built a travel assistant with persistent memory. It's
> still deployed — you can open it right now.
>
> I'm going to show you why its memory is broken, and then fix it."

*(Have travel-guardian.butterbase.dev open in a tab. Real system, still running.)*

---

## 0:20 — the problem · ACT 1

> "Here's a traveler with fifteen memories over eleven months. Same corpus,
> two memory designs.
>
> The old app extracts preferences by substring matching, then **appends them
> forever**. Look what it believes: museums, nightlife, walking.
>
> Every one of those is something the traveler reversed. They asked to stop
> being routed through museums twenty-five days ago. Nothing past 9pm, twenty
> days ago. And walking — they **tore their knee** forty-five days ago."

**Then the line that lands:**

> "But here's the part that actually got me. The knee injury isn't in that list
> at all. It says *'transit-adjacent'*. The keyword table looks for
> *'public transport'*. Substring matching never fires.
>
> The single most important fact about this traveler is **invisible** to its
> memory."

---

## 0:50 — the insight · ACT 2

> "Most agent-memory work is about forgetting. This is the opposite failure:
> remembering everything, weighting it equally, and confidently acting on
> preferences you abandoned months ago.
>
> And the fix isn't deletion. **Supersession is a retrieval problem, not a
> storage problem.**"

*(point at the formula)*

> "Relevance times exponential decay on age. Multiplicative — relevance still
> picks the candidates, recency decides which of the relevant ones survive.
>
> Nothing is deleted. The old memory is still in the graph. It just loses."

*(point at the scoreboard)*

> "Reversed decisions in the top eight: **flat four, weighted zero.**
> One variable changed — the decay window."

---

## 1:40 — the answers · ACT 3

> "Same question to both. The old app says — and I quote — *'knowing you enjoy
> walking, a forty-minute walk, a scenic walk, a longer walk to the Mission.'*
> No idea about the knee.
>
> Mine: two point seven miles, all transit-adjacent, outdoors, no tickets,
> timed to golden hour, done before nine. And it **cites the date** of every
> constraint it honored."

*(point at the tool trace)*

> "Six tool calls. It recalls who you are from Cognee. It checks the live world
> through Bright Data — because opening hours rot in a way a knee injury
> doesn't. And the last call is **`remember`**.
>
> It wrote back what the web just taught it. The brain is more correct after
> this conversation than before it."

---

## 2:30 — the close

> "Two datasets with two different lifespans — who you are, which supersedes;
> and what's true right now, which expires. Cognee holds both. Bright Data
> keeps the second one honest. Strands is the agent loop.
>
> The old app is still live if you want to try it. Both are on GitHub."

---

# If they ask

**"Why not just delete the old preference?"**
> Because you don't know it's dead until something contradicts it, and people
> revert. The knee heals. Deletion is lossy and irreversible; ranking isn't.

**"Where did 45 days come from?"**
> The reversal spacing in this corpus — the knee is 45 days old, everything it
> superseded is 250-plus. Any window in that gap separates them; 45 is the
> tightest that does. It's tuned, not learned. Per-memory-type windows would be
> better and I'd do that next.

**"Doesn't Cognee already do temporal?"**
> It stores the timeline correctly — cognify pulled the dates *and* the
> supersession language into the graph. But `SearchType.TEMPORAL` answers
> explicit range questions, "what happened before 2000". It doesn't recency-rank
> a general query. I measured it: TEMPORAL and GRAPH_COMPLETION returned nearly
> the same itinerary, both routing through Alcatraz. So the ranking layer is
> mine, on top of their retrieval.

**"Is the old app a strawman?"**
> No — `guardian.py` is a port of its real code. Its literal keyword table, its
> `.push()` merge, its prompt assembly. Same fifteen memories through its own
> algorithm. And the deployed version is right there.

**"Why not Bedrock?"**
> It's wired — one env var. The AWS account is new and not yet enabled for
> Bedrock inference; every model returns Error 002, including Amazon's own Nova,
> so it isn't a permissions problem. Strands is model-agnostic by design.

---

# Runbook

## T–5 min · prep

```bash
cd ~/projects/Travel-Companion
./demo --seed --prefs
```

One command: re-seeds travel-guardian's KV (7-day TTL) **and** prints the
belief tables so you can confirm it worked. You want to see `walking` on the
left and `Knee injury` on the right.

Open three tabs, in this order:

1. https://abhijitbetigeri.github.io/Travel-Companion/demo.html — scroll to top
2. https://travel-guardian.butterbase.dev
3. Terminal in the repo, `./demo --prefs` typed but **not** run

Load tab 1 fully now. Once loaded it is static — wifi can die and it still works.

## The run · 3 minutes

**① Tab 2 — the old app** · 15s
Show it's a real deployed thing. Don't interact, just establish it exists.

> "Three months ago I built this. It's still running. I'm going to show you
> why its memory is broken, then fix it."

**② Tab 1 — Act 1** · 35s
Point at the left card: `art, museum, history, nightlife` / `walking`.

> "Same fifteen memories, two designs. This one appends preferences forever.
> Museums — they asked me to stop, 25 days ago. Nightlife — reversed 20 days
> ago. Walking — they tore their knee 45 days ago."

**③ Act 1, the fault box** · 20s — **the moment**

> "But the knee isn't in that list at all. The memory says 'transit-adjacent'.
> The keyword table looks for 'public transport'. Substring matching never
> fires. The most important fact about this traveler is invisible."

**Pause. Two seconds. Let them read it.**

**④ Act 2** · 40s

> "Supersession is a retrieval problem, not a storage problem."

Point at the formula, then the scoreboard.

> "Relevance times decay on age. Multiplicative — relevance picks the
> candidates, recency decides which survive. Nothing is deleted; the old
> memory just loses. Reversed decisions in the top eight: flat four,
> weighted zero."

**⑤ Act 3** · 50s
Left pane, read the quote verbatim:

> "'Knowing you enjoy walking… a forty-minute walk… a longer walk to the
> Mission.' No idea about the knee."

Right pane:

> "Mine: 2.7 miles, transit-adjacent, no tickets, golden hour, done before
> nine — and it cites the date of every constraint."

Point at the tool-trace chips:

> "Cognee for who you are. Bright Data for what's true right now. And the last
> call is `remember` — it wrote back what the web just taught it."

**⑥ Close** · 20s

> "Two datasets, two lifespans. Who you are supersedes. What's true now
> expires. The old app's still live if you want to try it."

## If a judge wants proof it's real

Tab 3: `./demo --prefs` — about 2 seconds, hits Cognee live, prints the same
tables. No LLM, no slide.

If they want the whole loop: `./demo` — but that's 1–2 minutes of tool calls.
Only offer it in Q&A, and talk over it.

## Failure modes

| If | Then |
|---|---|
| Wifi dies | Tab 1 is already loaded and fully static. Keep going. |
| `./demo --prefs` errors | Skip it. The page carries the argument alone. |
| Asked about Bedrock | Wired, one env var. Account is new, not yet enabled — Amazon's own Nova fails identically, so it isn't permissions. |
| Asked if guardian is a strawman | `guardian.py` is a port of the real `api.js`. Same keyword table, same `.push()`. Offer to show the file. |
| `command not found: python` | Use `./demo`, not `python`. It handles the venv and the cwd. |

## Pre-flight

```bash
./demo smoke     # expect: all 3 checks passed
```
