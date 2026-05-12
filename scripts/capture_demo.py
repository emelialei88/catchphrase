"""Capture a demo screenshot of Catchphrase with an enriched card.
Run with the dev server already up at http://localhost:7823.
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUT = Path(__file__).parent.parent / "docs" / "screenshot.png"
PHRASE = "hit the ground running"


async def main():
    OUT.parent.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(viewport={"width": 900, "height": 900}, device_scale_factor=2)
        page = await ctx.new_page()

        await page.goto("http://localhost:7823")
        await page.wait_for_selector("#phrase-input")

        await page.fill("#phrase-input", PHRASE)
        await page.click("#enrich-btn")

        # Wait for the card to render
        await page.wait_for_selector("#card-section:not(.hidden)", timeout=30_000)
        await page.wait_for_timeout(500)  # settle animations

        # Clip to the actual #app content so we don't capture the empty min-height area below.
        box = await page.evaluate(
            "() => { const r = document.getElementById('app').getBoundingClientRect();"
            "       return { x: 0, y: 0, w: window.innerWidth, h: Math.ceil(r.bottom + 24) }; }"
        )
        await page.set_viewport_size({"width": box["w"], "height": box["h"]})
        await page.screenshot(path=str(OUT), full_page=False)
        await browser.close()
        print(f"saved {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
