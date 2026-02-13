import asyncio
import csv
import os
from playwright.async_api import async_playwright

INPUT_TXT = "domains3.txt"
OUTPUT_CSV = "domain_screenshots.csv"
SCREENSHOT_DIR = "screenshots"
CONCURRENCY = 4        # 3–5 is safe on Windows
TIMEOUT_MS = 15000    # 15 seconds per site

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

async def capture(browser, sem, domain):
    async with sem:
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        url = f"https://{domain}"
        filename = f"{domain.replace('.', '_')}.png"
        path = os.path.join(SCREENSHOT_DIR, filename)

        # Resume-friendly: skip if already captured
        if os.path.exists(path):
            await page.close()
            return domain, url, path, "SKIPPED"

        try:
            await page.goto(url, timeout=TIMEOUT_MS, wait_until="networkidle")
            await page.screenshot(path=path, full_page=True)
            status = "OK"
        except Exception:
            # fallback to http if https fails
            try:
                url = f"http://{domain}"
                await page.goto(url, timeout=TIMEOUT_MS, wait_until="networkidle")
                await page.screenshot(path=path, full_page=True)
                status = "OK"
            except Exception:
                path = ""
                status = "ERROR"
        finally:
            await page.close()

        print(f"Snapshot: {domain} -> {status}")
        return domain, url, path, status

async def main():
    with open(INPUT_TXT, encoding="utf-8") as f:
        domains = [line.strip() for line in f if line.strip()]

    sem = asyncio.Semaphore(CONCURRENCY)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [capture(browser, sem, d) for d in domains]

        results = []
        for coro in asyncio.as_completed(tasks):
            results.append(await coro)

        await browser.close()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Domain", "Final_URL", "Screenshot_Path", "Screenshot_Status"])
        writer.writerows(results)

    print(f"\nDone! Screenshots saved in ./{SCREENSHOT_DIR}")
    print(f"CSV mapping saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    asyncio.run(main())
