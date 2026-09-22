"""Record a demo video of the live page, driving the real interactions.

    ./demo record

Produces docs/demo.webm — ~55 seconds, no narration, paced so each beat is
readable. Drives the actual deployed page, so nothing here is a mockup.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"
TMP = ROOT / ".rec"
import os
URL = os.environ.get("DEMO_URL", "https://abhijitbetigeri.github.io/Travel-Companion/")
W, H = 1440, 900


def glide(page, selector: str, pause: int = 600) -> None:
    """Scroll an element to a comfortable reading position, then hold."""
    page.eval_on_selector(
        selector,
        "el => el.scrollIntoView({behavior:'smooth', block:'start'})",
    )
    page.wait_for_timeout(pause)


def main() -> None:
    if TMP.exists():
        shutil.rmtree(TMP)
    OUT.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": W, "height": H},
            record_video_dir=str(TMP),
            record_video_size={"width": W, "height": H},
            device_scale_factor=2,
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(1800)  # let the hero settle

        # ── 1. the story + timeline ───────────────────────────────────
        glide(page, ".story", 1400)
        glide(page, ".timeline", 900)

        # Click by content, not index: dot order follows retrieval rank while
        # position follows age, and the recent dots overlap each other — so
        # dispatch the event directly rather than relying on hit-testing.
        def click_dot(fragment: str, hold: int) -> None:
            page.eval_on_selector(
                f'.dot[data-tip*="{fragment}"]', "el => el.click()")
            page.wait_for_timeout(hold)

        click_dot("Walk the entire city", 3000)   # 330d — the old self
        click_dot("Knee injury", 3400)            # 45d — the turn

        # ── 2. what the old app believes ──────────────────────────────
        glide(page, "#problem", 1000)
        glide(page, ".prefs", 2400)              # museum/nightlife/walking struck out
        glide(page, ".gotcha", 3000)             # the transit-adjacent line
        page.click("#ask-old")
        page.wait_for_timeout(4200)              # let the walking answer land

        # ── 3. the slider — the whole argument ────────────────────────
        glide(page, "#fix", 1200)
        glide(page, ".control", 1600)

        slider = page.locator("#window")
        box = slider.bounding_box()
        y = box["y"] + box["height"] / 2
        # the range is rtl: left edge = short window, right edge = no decay
        page.mouse.move(box["x"] + box["width"] - 8, y)
        page.mouse.down()
        steps = 55
        for i in range(steps + 1):
            frac = i / steps
            page.mouse.move(box["x"] + box["width"] - 8 - (box["width"] - 16) * frac, y)
            page.wait_for_timeout(34)
        page.mouse.up()
        page.wait_for_timeout(3400)              # hold on 0 / all-green

        # nudge back so the contrast is unmistakable, then return
        page.click('.tick[data-w="3650"]')
        page.wait_for_timeout(2200)
        page.click('.tick[data-w="45"]')
        page.wait_for_timeout(3000)

        # ── 4. the payoff ─────────────────────────────────────────────
        glide(page, "#payoff", 1200)
        page.click("#ask-new")
        page.wait_for_timeout(1200)
        glide(page, ".trace", 2600)              # tool calls, ending in remember
        page.eval_on_selector(
            "#companion-answer", "el => el.scrollTo({top: 260, behavior:'smooth'})")
        page.wait_for_timeout(3200)

        # ── 5. close ──────────────────────────────────────────────────
        glide(page, ".close", 3200)

        ctx.close()
        browser.close()

    src = next(TMP.glob("*.webm"))
    dst = OUT / "demo.webm"
    dst.unlink(missing_ok=True)
    shutil.move(str(src), dst)
    shutil.rmtree(TMP, ignore_errors=True)
    mb = dst.stat().st_size / 1e6
    print(f"wrote {dst.relative_to(ROOT)}  ({mb:.1f} MB)")


if __name__ == "__main__":
    sys.exit(main())
