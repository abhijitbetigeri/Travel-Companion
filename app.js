/* Travel Companion — interactive demo.
   The slider recomputes the ranking client-side. Same formula as decay.py:
       score = (1 / (1 + rank)) * exp(-ageDays / window)
   No network, no model. Drag it and the ranking physically reorders. */

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function md(text) {
  let html = "", inList = false;
  for (const raw of String(text).split("\n")) {
    const line = raw.trim();
    const close = () => { if (inList) { html += "</ul>"; inList = false; } };
    if (!line) { close(); continue; }
    const s = esc(line)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|\W)\*(?!\s)(.+?)(?<!\s)\*/g, "$1<em>$2</em>");
    if (/^#{1,6}\s/.test(line)) { close(); html += `<h4>${s.replace(/^#{1,6}\s*/, "")}</h4>`; }
    else if (/^[-*•]\s/.test(line)) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${s.replace(/^[-*•]\s*/, "")}</li>`;
    } else { close(); html += `<p>${s}</p>`; }
  }
  return html + (inList ? "</ul>" : "");
}

const score = (m, w) => (1 / (1 + m.rank)) * Math.exp(-m.ageDays / w);

let MEMS = [];

function renderRank(w) {
  const top = [...MEMS].sort((a, b) => score(b, w) - score(a, w)).slice(0, 8);
  const stale = top.filter((m) => m.superseded).length;

  $("live-rank").innerHTML = top
    .map((m, i) => `
      <li class="${m.superseded ? "is-stale" : "is-fresh"}" style="--i:${i}">
        <span class="lr-i">${i + 1}</span>
        <span class="lr-main">
          <b>${esc(m.title)}</b>
          ${m.superseded
            ? `<span class="tag stale">abandoned · ${esc(m.supersededBy)}</span>`
            : `<span class="tag fresh">still true</span>`}
        </span>
        <span class="lr-age">${m.ageDays}d</span>
      </li>`)
    .join("");

  $("stale-count").textContent = stale;
  $("counter").className = "counter" + (stale === 0 ? " clean" : "");
  $("window-out").textContent = w >= 3650 ? "no decay" : `${w} days`;
  document.querySelectorAll(".tick").forEach((b) =>
    b.classList.toggle("on", Number(b.dataset.w) === w));
}

function renderTimeline() {
  const max = Math.max(...MEMS.map((m) => m.ageDays));
  $("timeline").innerHTML = MEMS
    .map((m) => {
      const left = 100 - (m.ageDays / max) * 100;
      return `<span class="dot ${m.superseded ? "stale" : "fresh"}"
                    style="left:${left}%"
                    tabindex="0"
                    data-tip="${esc(m.title)} · ${m.ageDays}d ago"></span>`;
    })
    .join("") + `<i class="tl-axis"></i>
      <span class="tl-label tl-old">330 days ago</span>
      <span class="tl-label tl-new">today</span>`;
}

function wireTimeline() {
  const panel = $("mem-detail");
  document.querySelectorAll(".dot").forEach((dot, i) => {
    const show = () => {
      const m = MEMS[i];
      document.querySelectorAll(".dot").forEach((d) => d.classList.remove("on"));
      dot.classList.add("on");
      panel.hidden = false;
      panel.className = "mem-detail " + (m.superseded ? "stale" : "fresh");
      panel.innerHTML = `
        <div class="md-top">
          <span class="md-kind">${esc(m.kind)}</span>
          <span class="md-when">${esc(m.date)} · ${m.ageDays} days ago</span>
        </div>
        <h4>${esc(m.title)}</h4>
        <p>${esc(m.body)}</p>
        <span class="tag ${m.superseded ? "stale" : "fresh"}">
          ${m.superseded ? "abandoned · " + esc(m.supersededBy) : "still true today"}
        </span>`;
      panel.scrollIntoView({ block: "nearest", behavior: "smooth" });
    };
    dot.addEventListener("click", show);
    dot.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); show(); }
    });
  });
}

/* Reveal an answer behind its Ask button, one paragraph at a time. */
function wireAsk(btnId, gateId, bodyId, traceId) {
  const btn = $(btnId);
  if (!btn) return;
  btn.addEventListener("click", () => {
    $(gateId).classList.add("gone");
    setTimeout(() => {
      $(gateId).hidden = true;
      if (traceId && $(traceId)) $(traceId).hidden = false;
      const body = $(bodyId);
      body.hidden = false;
      body.querySelectorAll(":scope > *").forEach((el, i) => {
        el.style.animation = `rise .5s cubic-bezier(.2,.8,.2,1) ${i * 55}ms backwards`;
      });
    }, 260);
  });
}

async function main() {
  let d;
  try {
    d = await (await fetch("demo_data.json", { cache: "no-store" })).json();
  } catch {
    document.body.insertAdjacentHTML("afterbegin",
      `<p class="load-error">demo_data.json missing — run <code>./demo snapshot</code></p>`);
    return;
  }

  MEMS = d.allMemories || [];
  renderTimeline();
  wireTimeline();

  // ?w=45 deep-links a slider state — handy for screenshots and for jumping
  // straight to the punchline mid-demo.
  const w0 = Math.min(3650, Math.max(10, Number(new URLSearchParams(location.search).get("w")) || 3650));
  $("window").value = w0;
  renderRank(w0);

  $("captured").textContent = new Date(d.capturedAt).toLocaleString(undefined,
    { dateStyle: "medium", timeStyle: "short" });

  /* old app's beliefs */
  $("guardian-prefs").innerHTML = Object.entries(d.guardian.preferences)
    .map(([cat, vals]) => {
      const chips = vals.map((v) => {
        const bad = ["museum", "nightlife", "walking", "night"].includes(v);
        return `<code class="${bad ? "bad" : ""}">${esc(v)}</code>`;
      }).join("");
      return `<div class="pref-row"><dt>${esc(cat)}</dt><dd>${chips}</dd></div>`;
    }).join("") +
    `<div class="pref-row missing"><dt>knee</dt><dd><span class="absent">never recorded</span></dd></div>`;

  $("guardian-answer").innerHTML = md(d.guardian.answer);

  if (d.companion) {
    $("companion-answer").innerHTML = md(d.companion.answer);
    $("trace").innerHTML = d.companion.toolCalls
      .map((t, i) => `<span class="tool" style="animation-delay:${i * 80}ms">${esc(t)}</span>`)
      .join('<i class="arrow">→</i>');
  }

  wireAsk("ask-old", "gate-old", "guardian-answer", null);
  wireAsk("ask-new", "gate-new", "companion-answer", "trace");

  /* the interaction */
  const slider = $("window");
  slider.addEventListener("input", (e) => renderRank(Number(e.target.value)));
  document.querySelectorAll(".tick").forEach((b) =>
    b.addEventListener("click", () => {
      const target = Number(b.dataset.w);
      const from = Number(slider.value);
      const t0 = performance.now();
      const dur = 550;
      (function step(now) {
        const p = Math.min(1, (now - t0) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        const v = Math.round(from + (target - from) * eased);
        slider.value = v;
        renderRank(v);
        if (p < 1) requestAnimationFrame(step);
      })(t0);
    }));

  /* reveal */
  const io = new IntersectionObserver(
    (es) => es.forEach((e) => e.isIntersecting && e.target.classList.add("in")),
    { threshold: 0.06 });
  document.querySelectorAll(".beat").forEach((el) => { el.classList.add("reveal"); io.observe(el); });
}

main();
