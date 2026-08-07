"""
spa_verify_template.py — Generic SPA verification script skeleton.

Copy this file to:
    <framework-session-path>/verification_artifacts/scripts/verify_<task-slug>.py

and fill in every # TODO section.

Usage:
    python3 verify_<task>.py --url URL [--browser {chromium,firefox,webkit}]
                             [--headed] [--slow-mo MS] [--viewport WxH]
                             [--no-screenshots] [--no-video] [--video-dir DIR]

    --browser        Browser engine to use. When omitted, auto-detects in order:
                     chromium → firefox → webkit.
    --headed         Run browser visibly for replay/debugging (default: headless).
    --slow-mo MS     Slow-motion delay in milliseconds for headed replay.
    --viewport WxH   Explicit viewport size, e.g. 1920x1080.
                     Omit to use the standard 1920x1080 (1080p) viewport.
    --no-screenshots Skip saving screenshot files (screenshots are saved by default).
    --no-video       Skip saving browser video recordings (video is saved by default).
    --video-dir DIR  Directory where the video file is stored.
                     Defaults to verification_artifacts/videos/.

The script navigates to a live URL, checks a set of Visual Check Points (VCPs),
writes verification_artifacts/logs/verification_log.txt, and exits 0 (all pass) or 1 (any fail).

Rules:
- Do not trigger irreversible side effects against production or shared environments.
  Submit-like actions are allowed only when the target is local, mocked, seeded,
  disposable, or explicitly marked safe by the spec/test plan.
- Fresh navigation on every run.
- At least one screenshot per VCP; clicks also capture before/after screenshots.
- Never full_page=True.
- Before any click, highlight the target element, take a screenshot, click, then
  take a second screenshot. Use highlight_and_click() for this.
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
ARTIFACTS_DIR = SCRIPT_DIR.parent
SESSION_DIR = ARTIFACTS_DIR.parent
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
VIDEOS_DIR = ARTIFACTS_DIR / "videos"
LOGS_DIR = ARTIFACTS_DIR / "logs"
LOG_FILE = LOGS_DIR / "verification_log.txt"

# ── Screenshot counter ─────────────────────────────────────────────────────────
# Global counter so every screenshot in a run gets a unique, always-increasing
# number. Filename pattern: verify_<task-slug>-<N>-<description>.png
_shot_counter: int = 0
_SCRIPT_NAME = Path(__file__).stem  # e.g. "verify_completed-to-blocked"


def next_shot(slug: str) -> Path:
    """Return the next numbered screenshot path and bump the global counter."""
    global _shot_counter
    _shot_counter += 1
    return SCREENSHOTS_DIR / f"{_SCRIPT_NAME}-{_shot_counter}-{slug}.png"


# ── Parameters ─────────────────────────────────────────────────────────────────
def parse_args():
    # -- DO NOT CHANGE THIS FUNCTION UNLESS YOU ADD NEW CLI PARAMETERS! --
    p = argparse.ArgumentParser(description="Verify a web task on a live SPA.")
    p.add_argument("--url", required=True, help="The URL to navigate to for verification.")
    p.add_argument(
        "--browser",
        default=None,
        choices=["chromium", "firefox", "webkit"],
        help="Browser engine to use. Defaults to auto-detect (chromium preferred, then firefox, then webkit).",
    )
    p.add_argument("--headed", action="store_true", help="Run browser visibly for replay/debugging")
    p.add_argument("--slow-mo", type=int, default=0, help="Slow motion delay in ms for headed replay")
    p.add_argument(
        "--viewport",
        default=None,
        metavar="WxH",
        help="Viewport size as WxH, e.g. 1920x1080. Omit to use the standard 1920x1080 (1080p) viewport.",
    )
    p.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Skip saving screenshot files. Useful for headed replay runs. Screenshots are saved by default.",
    )
    p.add_argument(
        "--no-video",
        action="store_true",
        help="Skip saving browser video recordings. Video is saved by default.",
    )
    p.add_argument(
        "--video-dir",
        default=None,
        metavar="DIR",
        help="Directory where the video file is stored. Defaults to verification_artifacts/videos/.",
    )
    # TODO: add any additional task-specific parameters here, e.g.:
    # p.add_argument("--expected-value", default="", help="Value that should appear on screen.")


    return p.parse_args()


def _parse_viewport(value: str) -> dict:
    """Parse 'WxH' string into a Playwright viewport dict."""
    try:
        w, h = value.lower().split("x")
        return {"width": int(w), "height": int(h)}
    except (ValueError, AttributeError):
        raise argparse.ArgumentTypeError(
            f"Invalid --viewport format {value!r}. Expected WxH, e.g. 1920x1080."
        )


# ── Logging helpers ────────────────────────────────────────────────────────────
_log_lines: list[str] = []

def log(line: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {line}"
    print(entry)
    _log_lines.append(entry)

def vcp_pass(n: int, detail: str):
    log(f"VCP{n} PASS: {detail}")

def vcp_fail(n: int, detail: str):
    log(f"VCP{n} FAIL: {detail}")

def flush_log():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text("\n".join(_log_lines) + "\n")


# ── Interaction helpers ────────────────────────────────────────────────────────
async def highlight_and_click(page, locator, slug: str, save_screenshots: bool = True) -> tuple[str, str]:
    """
    Highlight *locator* with a red outline, wait 500 ms, take a 'before' screenshot,
    click the element, wait 500 ms, then take an 'after' screenshot.

    The two short waits give any running animations, React re-renders, or
    component off-loading time to settle so the resulting screenshots are
    artifact-free.

    Args:
        page:             Playwright Page object.
        locator:          The element locator to act on.
        slug:             Short identifier used in screenshot filenames,
                          e.g. "openmenu" → verify_task-2-openmenu_before.png
        save_screenshots: When False, skips writing screenshot files (mirrors --no-screenshots).

    Returns:
        (before_path, after_path) as strings, or ('', '') when screenshots are disabled.
    """
    await locator.evaluate("el => el.style.outline = '3px solid red'")
    await page.wait_for_timeout(500)  # let outline / transitions settle
    before_path = ""
    if save_screenshots:
        before_path = str(next_shot(f"{slug}_before"))
        await page.screenshot(path=before_path)
    await locator.click()
    await page.wait_for_timeout(500)  # let click state / animations settle
    after_path = ""
    if save_screenshots:
        after_path = str(next_shot(f"{slug}_after"))
        await page.screenshot(path=after_path)
    try:
        await locator.evaluate("el => el.style.outline = ''", timeout=1000)
    except Exception:
        print(f"Warning: failed to remove highlight from {slug} after click.")
    return before_path, after_path


# ── Main verification ──────────────────────────────────────────────────────────
async def run_verification(args):
    from playwright.async_api import async_playwright

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    all_pass = True
    save_ss = not args.no_screenshots
    save_video = not args.no_video
    # When recording video, force slow-motion to 500 ms so every action is visible.
    slow_mo = 500 if save_video else args.slow_mo
    video_dir = Path(args.video_dir) if args.video_dir else VIDEOS_DIR
    video_dir.mkdir(parents=True, exist_ok=True)

    # Resolve viewport / video size (Playwright recommends aligning them)
    if args.viewport:
        viewport = _parse_viewport(args.viewport)
        video_size = viewport.copy()
    else:
        viewport = {"width": 1920, "height": 1080}
        video_size = viewport.copy()

    async with async_playwright() as pw:
        browser_type = await pick_browser(pw, args.browser)
        if browser_type is None:
            tried = [args.browser] if args.browser else ["chromium", "firefox", "webkit"]
            log(f"ERROR: No supported browser found (tried: {', '.join(tried)}). Install one with: python3 -m playwright install <browser>")
            flush_log()
            sys.exit(1)

        log(f"Browser: {browser_type.name} (headless={not args.headed})")
        browser = await browser_type.launch(
            headless=not args.headed,
            slow_mo=slow_mo,
        )
        context_kwargs = {"viewport": viewport}
        if save_video:
            context_kwargs["record_video_dir"] = str(video_dir)
            context_kwargs["record_video_size"] = video_size
        ctx = await browser.new_context(**context_kwargs)
        page = await ctx.new_page()

        # ── Navigation ────────────────────────────────────────────────────────
        log(f"Navigating to: {args.url}")
        await page.goto(args.url, wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")

        # ── Start recording warm-up ───────────────────────────────────────────
        # Wait 1 s after navigation so the video starts on a settled frame.
        await asyncio.sleep(1)

        # ── VCP: Page loaded ─────────────────────────────────────────────────
        # TODO: replace with the actual expected URL fragment or title for your site.
        current_url = page.url
        title = await page.title()
        screenshot_path = str(next_shot("startup"))
        if save_ss:
            await page.screenshot(path=screenshot_path)

        # TODO: tighten by waiting for a real visible element specific to this task.
        try:
            await page.get_by_role("heading").first.wait_for(state="visible")
            vcp_pass(1, f"Initial page state visible. URL={current_url} Title={title!r}")
        except Exception as e:
            vcp_fail(1, f"Initial page state not proven. URL={current_url} Title={title!r}; error={e}")
            all_pass = False

        # Print ARIA for debugging
        print("\n--- VCP1 ARIA snapshot (body) ---")
        print((await page.locator("body").aria_snapshot())[:2000])
        print("---\n")

        # ── VCP: TODO — check for the primary state you want to verify ───────
        # Example: click a button and confirm the resulting state is visible.
        # Use highlight_and_click() so every click is captured in two screenshots.
        #
        # btn = page.get_by_role("button", name="TODO: button label")
        # before_path, after_path = await highlight_and_click(page, btn, "openmenu", save_screenshots=save_ss)
        # result_el = page.get_by_role("heading", name="TODO: expected heading")
        # if await result_el.is_visible():
        #     vcp_pass(2, f"Expected state visible after click. before={before_path} after={after_path}")
        # else:
        #     vcp_fail(2, f"Expected state not found after click. before={before_path} after={after_path}")
        #     all_pass = False
        #
        # TODO: implement VCP

        # ── End recording cool-down ───────────────────────────────────────────
        # Wait 1 s after the last action so the final state is fully captured.
        await asyncio.sleep(1)

        # ── Cleanup ───────────────────────────────────────────────────────────
        # Close context *before* browser so video is flushed
        await ctx.close()
        video_path = ""
        if save_video and page.video:
            try:
                raw_path = Path(await page.video.path())
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                named_path = video_dir / f"{_SCRIPT_NAME}-{timestamp}.webm"
                raw_path.rename(named_path)
                video_path = str(named_path)
                log(f"Video saved to: {video_path}")
            except Exception as e:
                log(f"Warning: failed to retrieve or rename video: {e}")

        await browser.close()

    flush_log()
    return all_pass


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    args = parse_args()
    passed = asyncio.run(run_verification(args))
    print("\n" + ("=" * 50))
    print("VERIFICATION RESULT:", "✅ ALL VCPs PASSED" if passed else "❌ ONE OR MORE VCPs FAILED")
    print(f"Log written to: {LOG_FILE}")
    sys.exit(0 if passed else 1)


async def pick_browser(pw, preferred: str | None):
    """
    Try to launch a supported browser in order:
    1. preferred (if --browser was explicitly passed)
    2. chromium
    3. firefox
    4. webkit

    Returns the first successful BrowserType or None if none are available.
    """
    candidates = [preferred] if preferred else ["chromium", "firefox", "webkit"]
    for name in candidates:
        try:
            browser_type = getattr(pw, name)
            # quick smoke test
            b = await browser_type.launch()
            await b.close()
            return browser_type
        except Exception:
            continue
    return None
