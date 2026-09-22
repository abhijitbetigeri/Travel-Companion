# The pitch

**Demo:** https://abhijitbetigeri.github.io/Travel-Companion/demo.html
**Old app:** https://travel-guardian.butterbase.dev

One story. The knee. Everything hangs off it.

---

## Say this

**The setup** *(20s)*

> "I built a travel app in June. It remembers your preferences.
>
> This traveler loved walking. Twenty thousand steps a day, no transit.
> Museums. Late shows.
>
> Then forty-five days ago, they tore their knee."

**The problem** *(40s)* — *show the old app's answer*

> "Here's what my June app tells them today.
>
> 'You enjoy walking. Here's a forty-minute walk. Then a scenic walk. Then a
> longer walk to the Mission.'
>
> It has no idea about the knee. It never even recorded it.
>
> Because it learns preferences by keyword matching. The traveler said
> 'transit-adjacent.' The keyword list says 'public transport.' No match.
> The most important thing about this person just fell on the floor."

**The fix** *(40s)* — *show the ranking table*

> "So I rebuilt the memory.
>
> Every memory gets a date. When you search, recent memories outrank old ones
> that contradict them. Nothing is deleted — the old preference is still
> there, it just loses.
>
> Same fifteen memories, same question. Old way: four outdated preferences in
> the top eight. New way: zero."

**The payoff** *(40s)* — *show the new answer*

> "Now the same question gets: 2.7 miles. All transit. No tickets. Home before
> nine. And it tells you which decision each rule came from.
>
> It also checks the live web, because opening hours go stale in a way a knee
> injury doesn't. And when the web corrects it, it writes that back into
> memory."

**Close** *(15s)*

> "Memory shouldn't just store what you said. It should know which version of
> you is still true."

---

## The one line

> "Most agent memory forgets too much. Mine fixes the opposite problem —
> remembering things you've moved on from."

---

## If they ask

**"Why not delete the old preference?"**
> The knee heals. Then walking comes back on its own. Deleting is permanent;
> ranking isn't.

**"Isn't this just a better prompt?"**
> The old app never *had* the knee in memory. No prompt recovers a fact that
> was never stored.

**"Where's 45 days from?"**
> The gap in this data — the knee is 45 days old, everything it replaced is
> 250+. Tuned, not learned. I'd learn it next.

**"You're comparing two different models."**
> On the final answer, yes. But the ranking comparison has no model in it at
> all — it's arithmetic on dates. Run `./demo --prefs`. Four versus zero,
> every time.

**"Is the old app a strawman?"**
> It's still deployed, and `guardian.py` is a copy of its real code. Same
> keyword table, same append-only merge.

**"Why not Bedrock?"**
> Wired, one env var. The AWS account is new and not enabled for Bedrock yet —
> Amazon's own models fail the same way, so it isn't permissions.

---

## Runbook

**Before you go up:**

```bash
cd ~/projects/Travel-Companion
./demo --seed --prefs
```

Expect `walking` on the left, `Knee injury` on the right.

**Tabs, in order:**

1. https://abhijitbetigeri.github.io/Travel-Companion/demo.html
2. https://travel-guardian.butterbase.dev
3. Terminal, `./demo --prefs` typed but not run

**Scroll the demo page as you talk** — Act 1 for the problem, Act 2 for the
fix, Act 3 for the payoff.

**If someone wants proof it's live:** run `./demo --prefs`. Two seconds, hits
Cognee for real.

**If the wifi dies:** the page is static and already loaded. Keep going.

**If you see `command not found: python`:** use `./demo`, not `python`.

---

## Built with

Cognee for memory · Bright Data for the live web · AWS Strands for the agent
