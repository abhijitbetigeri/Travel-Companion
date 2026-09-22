/* Renders demo.html from demo_data.json — a captured real run. */

const $ = (id) => document.getElementById(id);

const esc = (s) =>
  String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

/* Very small markdown subset — the models emit **bold**, *em*, ## heads and - bullets. */
function md(text) {
  const lines = String(text).split("\n");
  let html = "";
  let inList = false;
  for (const raw of lines) {
    const line = raw.trim();
    const close = () => { if (inList) { html += "</ul>"; inList = false; } };
    if (!line) { close(); continue; }
    const inline = esc(line)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|\W)\*(?!\s)(.+?)(?<!\s)\*/g, "$1<em>$2</em>");
    if (/^#{1,6}\s/.test(line)) {
      close();
      html += `<h4>${inline.replace(/^#{1,6}\s*/, "")}</h4>`;
    } else if (/^[-*•]\s/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline.replace(/^[-*•]\s*/, "")}</li>`;
    } else {
      close();
      html += `<p>${inline}</p>`;
    }
  }
  if (inList) html += "</ul>";
  return html;
}

function rankRow(r, i) {
  const flag = r.superseded
    ? `<span class="tag stale">reversed · ${esc(r.supersededBy || "")}</span>`
    : `<span class="tag fresh">current</span>`;
  return `<li class="${r.superseded ? "is-stale" : "is-fresh"}">
      <span class="rank-i">${i + 1}</span>
      <span class="rank-body"><b>${esc(r.title)}</b>${flag}</span>
      <span class="rank-age">${r.ageDays}d</span>
    </li>`;
}

async function main() {
  let d;
  try {
    d = await (await fetch("demo_data.json", { cache: "no-store" })).json();
  } catch {
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<p class="load-error">demo_data.json not found — run <code>python scripts/snapshot.py</code></p>`
    );
    return;
  }

  $("question").textContent = `“${d.question}”`;
  $("captured").textContent = new Date(d.capturedAt).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  /* Act 1 */
  $("guardian-prefs").innerHTML = Object.entries(d.guardian.preferences)
    .map(([cat, vals]) => {
      const chips = vals
        .map((v) => {
          const bad = ["museum", "nightlife", "walking", "night"].includes(v);
          return `<code class="${bad ? "bad" : ""}">${esc(v)}</code>`;
        })
        .join("");
      return `<div class="pref-row"><dt>${esc(cat)}</dt><dd>${chips}</dd></div>`;
    })
    .join("");

  $("companion-beliefs").innerHTML = d.ranking.decayed
    .slice(0, 6)
    .map((m) => `<li><span class="age">${m.ageDays}d</span><span>${esc(m.title)}</span></li>`)
    .join("");

  /* Act 2 */
  $("window-label").textContent = `window = ${d.ranking.window}d`;
  $("rank-flat").innerHTML = d.ranking.flat.map(rankRow).join("");
  $("rank-decayed").innerHTML = d.ranking.decayed.map(rankRow).join("");
  $("flat-stale").textContent = d.ranking.flatStale;
  $("decayed-stale").textContent = d.ranking.decayedStale;

  /* Act 3 */
  $("guardian-answer").innerHTML = md(d.guardian.answer);
  if (d.companion) {
    $("companion-answer").innerHTML = md(d.companion.answer);
    $("tool-trace").innerHTML = d.companion.toolCalls
      .map((t, i) => `<span class="tool" style="animation-delay:${i * 90}ms">${esc(t)}</span>`)
      .join('<i class="arrow">→</i>');
  } else {
    $("companion-answer").textContent = "captured with --no-agent";
  }

  /* reveal on scroll */
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("in")),
    { threshold: 0.08 }
  );
  document.querySelectorAll(".act, .belief-card, .rank-col, .answer-pane, .verdict").forEach((el) => {
    el.classList.add("reveal");
    io.observe(el);
  });
}

main();
