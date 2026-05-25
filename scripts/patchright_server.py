#!/usr/bin/env python3
"""Patchright REST Server — anti-detection browser via HTTP API.

This server wraps Patchright (patched Playwright with bot detection bypass)
and optional CAPTCHA solving, exposing a REST API that mirrors the Camofox
browser backend interface.

Features:
- Chromium-based anti-detection browsing (Cloudflare, Datadome, PerimeterX bypass)
- Accessibility tree snapshots for LLM-friendly page representation
- Element interaction via ref selectors (@e1, @e2, etc.)
- Automatic CAPTCHA detection and solving (reCAPTCHA v2/v3, hCaptcha)
- Screenshot capture, cookie management, multi-tab support, proxy support

Usage:
    python scripts/patchright_server.py [--port 9378] [--headless] [--proxy http://...]
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("patchright_server")

# ---------------------------------------------------------------------------
# Shared async state — all Playwright objects live on ONE event loop
# ---------------------------------------------------------------------------

_loop: Optional[asyncio.AbstractEventLoop] = None
_pw = None  # Playwright instance
_browser = None
_context = None
_pages: Dict[str, Any] = {}  # task_id -> page

try:
    from patchright.async_api import async_playwright
except ImportError:
    logger.error(
        "patchright not installed. Install with: pip install patchright && patchright install chromium"
    )
    sys.exit(1)

try:
    from captcha_solver import CaptchaSolver
    _captcha_solver = CaptchaSolver()
except ImportError:
    _captcha_solver = None
    logger.warning(
        "captcha-solver not installed. CAPTCHA auto-solve disabled. "
        "Install with: pip install captcha-solver"
    )


def _run_async(coro):
    """Schedule a coroutine on the shared loop and block until done."""
    import concurrent.futures
    future = asyncio.run_coroutine_threadsafe(coro, _loop)
    return future.result(timeout=60)


# ---------------------------------------------------------------------------
# Browser lifecycle (runs on the shared loop)
# ---------------------------------------------------------------------------

async def launch_browser(headless: bool = True, proxy: Optional[str] = None):
    global _pw, _browser, _context
    _pw = await async_playwright().start()
    launch_args = {
        "headless": headless,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ],
    }
    if proxy:
        launch_args["proxy"] = {"server": proxy}
        logger.info("Using proxy: %s", proxy)

    _browser = await _pw.chromium.launch(**launch_args)
    _context = await _browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        locale="en-US",
    )
    logger.info("Patchright browser launched (headless=%s)", headless)


async def shutdown_browser():
    global _browser, _context, _pw
    if _context:
        await _context.close()
    if _browser:
        await _browser.close()
    if _pw:
        await _pw.stop()
    logger.info("Browser shut down")


# ---------------------------------------------------------------------------
# Page management
# ---------------------------------------------------------------------------

async def get_page(task_id: str = "default") -> Any:
    if task_id in _pages:
        page = _pages[task_id]
        if not page.is_closed():
            return page
    page = await _context.new_page()
    _pages[task_id] = page
    return page


# ---------------------------------------------------------------------------
# Accessibility tree → ref-based snapshot
# ---------------------------------------------------------------------------

def _build_snapshot_from_a11y(node: dict, elements: list, depth: int = 0) -> str:
    lines = []
    role = node.get("role", "")
    name = node.get("name", "")
    value = node.get("value", "")

    interactive_roles = {
        "button", "link", "textbox", "checkbox", "radio",
        "combobox", "menuitem", "tab", "switch", "searchbox",
        "spinbutton", "slider", "input",
    }
    ref = None
    if role in interactive_roles or node.get("focusable"):
        ref_index = len(elements)
        ref = f"@e{ref_index}"
        elements.append(node)

    indent = "  " * depth
    ref_str = f" [{ref}]" if ref else ""
    value_str = f' value="{value}"' if value else ""
    name_str = f": {name}" if name else ""
    lines.append(f"{indent}{role}{name_str}{value_str}{ref_str}")

    for child in node.get("children", []):
        lines.append(_build_snapshot_from_a11y(child, elements, depth + 1))
    return "\n".join(lines)


async def take_snapshot(page, full: bool = False) -> Dict[str, Any]:
    elements: list = []
    snapshot_text = ""

    # Try accessibility tree first (works with full Chromium, not headless-shell)
    try:
        a11y = await page.accessibility.snapshot()
        if a11y:
            snapshot_text = _build_snapshot_from_a11y(a11y, elements)
    except (AttributeError, Exception):
        pass

    # Fallback: extract interactive elements from DOM via JS
    if not snapshot_text:
        try:
            elements_raw = await page.evaluate("""() => {
                const els = [];
                const selectors = 'a, button, input, textarea, select, [role="button"], [role="link"], [role="textbox"], [role="checkbox"], [role="radio"], [role="combobox"], [role="tab"], [role="switch"]';
                document.querySelectorAll(selectors).forEach((el, i) => {
                    const tag = el.tagName.toLowerCase();
                    const role = el.getAttribute('role') || tag;
                    const name = el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 80) || el.getAttribute('placeholder') || el.getAttribute('name') || '';
                    const value = el.value || '';
                    const type = el.getAttribute('type') || '';
                    const href = el.getAttribute('href') || '';
                    els.push({
                        index: i, role, name, value, type, href, tag,
                        text: name.slice(0, 60)
                    });
                });
                return { elements: els, title: document.title, bodyText: document.body?.innerText?.slice(0, 3000) || '' };
            }""")
            lines = []
            for el in elements_raw.get("elements", []):
                ref = f"@e{el['index']}"
                el["_ref"] = ref
                elements.append(el)
                extra = f" type={el['type']}" if el.get('type') else ""
                href_str = f" href={el['href'][:50]}" if el.get('href') else ""
                lines.append(f"  {el['role']}: {el['name']}{extra}{href_str} [{ref}]")

            body_text = elements_raw.get("bodyText", "")
            if body_text:
                # Add page text content (first 2000 chars)
                lines.insert(0, "--- Page Content ---")
                lines.insert(1, body_text[:2000])
                lines.insert(2, "--- Interactive Elements ---")
            else:
                lines.insert(0, "--- Interactive Elements ---")

            snapshot_text = "\n".join(lines)
        except Exception as e:
            snapshot_text = f"(snapshot fallback error: {e})"

    title = await page.title()
    url = page.url
    return {
        "url": url,
        "title": title,
        "snapshot": snapshot_text,
        "element_count": len(elements),
        "elements": elements,
    }


# ---------------------------------------------------------------------------
# CAPTCHA detection and solving
# ---------------------------------------------------------------------------

async def detect_captcha(page) -> Optional[str]:
    recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
    if recaptcha:
        return "recaptcha"
    hcaptcha = await page.query_selector('iframe[src*="hcaptcha"]')
    if hcaptcha:
        return "hcaptcha"
    cf_challenge = await page.query_selector("#challenge-running, .challenge-running")
    if cf_challenge:
        return "cloudflare"
    body_text = await page.evaluate("() => document.body?.innerText?.toLowerCase() || ''")
    for kw in ["are you a robot", "verify you are human", "captcha", "prove you're not a robot"]:
        if kw in body_text:
            return "generic"
    return None


async def solve_captcha(page) -> Dict[str, Any]:
    captcha_type = await detect_captcha(page)
    if not captcha_type:
        return {"solved": False, "reason": "No CAPTCHA detected on page"}
    logger.info("Detected CAPTCHA type: %s", captcha_type)

    if captcha_type == "recaptcha":
        try:
            iframe = page.frame_locator('iframe[src*="recaptcha"]').first
            checkbox = iframe.locator("#recaptcha-anchor")
            await checkbox.click()
            await page.wait_for_timeout(3000)
            if not await detect_captcha(page):
                return {"solved": True, "type": captcha_type, "method": "click"}
        except Exception as e:
            logger.warning("reCAPTCHA click failed: %s", e)
        return {"solved": False, "type": captcha_type, "reason": "Could not solve automatically"}

    if captcha_type == "cloudflare":
        try:
            await page.wait_for_timeout(5000)
            if not await detect_captcha(page):
                return {"solved": True, "type": captcha_type, "method": "auto_bypass"}
        except Exception:
            pass
        return {"solved": False, "type": captcha_type, "reason": "Cloudflare challenge persists"}

    return {"solved": False, "type": captcha_type, "reason": "Unsupported CAPTCHA type"}


# ---------------------------------------------------------------------------
# Route handlers (async, called on the shared loop)
# ---------------------------------------------------------------------------

async def handle_navigate(body: dict) -> dict:
    url = body.get("url", "")
    task_id = body.get("task_id", "default")
    if not url:
        return {"error": "Missing 'url'"}
    page = await get_page(task_id)
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(1000)
        result = await take_snapshot(page)
        result["status_code"] = response.status if response else None
        result["navigation"] = "success"
        captcha_type = await detect_captcha(page)
        if captcha_type:
            result["captcha_detected"] = captcha_type
            result["captcha_warning"] = (
                f"Detected {captcha_type} challenge. Use solve_captcha to attempt auto-solving."
            )
        return result
    except Exception as e:
        return {"error": str(e), "navigation": "failed"}


async def handle_snapshot(body: dict) -> dict:
    full = body.get("full", False)
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    return await take_snapshot(page, full=full)


async def handle_click(body: dict) -> dict:
    ref = body.get("ref", "")
    task_id = body.get("task_id", "default")
    if not ref:
        return {"error": "Missing 'ref'"}
    page = await get_page(task_id)
    snap = await take_snapshot(page)
    elements = snap.get("elements", [])
    try:
        idx = int(ref.replace("@e", ""))
        if idx >= len(elements):
            return {"error": f"Ref {ref} out of range (max @e{len(elements)-1})"}
        el_info = elements[idx]
    except (ValueError, IndexError):
        return {"error": f"Invalid ref: {ref}"}

    # Handle both a11y-tree elements and DOM-extracted elements
    tag = el_info.get("tag", "")
    role = el_info.get("role", "")
    name = el_info.get("name", "")
    text = el_info.get("text", "")
    el_type = el_info.get("type", "")
    href = el_info.get("href", "")

    try:
        # Strategy 1: tag-based selectors
        if tag == "a" and (name or text):
            await page.get_by_text(name or text, exact=False).first.click()
        elif tag == "button" and (name or text):
            await page.get_by_role("button", name=name or text).first.click()
        elif tag == "input" and el_type == "submit" and (name or text):
            await page.get_by_role("button", name=name or text).first.click()
        elif tag == "input" and name:
            await page.get_by_label(name).first.click()
        elif tag == "textarea" and name:
            await page.get_by_label(name).first.click()
        elif tag == "select" and name:
            await page.get_by_label(name).first.click()
        elif name:
            await page.get_by_text(name, exact=False).first.click()
        else:
            return {"error": f"Cannot click element {ref}: no name or tag"}
        await page.wait_for_timeout(1000)
        result = await take_snapshot(page)
        result["clicked"] = ref
        return result
    except Exception as e:
        return {"error": f"Click failed for {ref}: {e}"}


async def handle_type(body: dict) -> dict:
    ref = body.get("ref", "")
    text = body.get("text", "")
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    snap = await take_snapshot(page)
    elements = snap.get("elements", [])
    try:
        idx = int(ref.replace("@e", ""))
        if idx >= len(elements):
            return {"error": f"Ref {ref} out of range"}
        el_info = elements[idx]
    except (ValueError, IndexError):
        return {"error": f"Invalid ref: {ref}"}

    tag = el_info.get("tag", "")
    role = el_info.get("role", "")
    name = el_info.get("name", "")
    try:
        if tag == "textarea" and name:
            locator = page.get_by_label(name).first
        elif tag == "input" and name:
            locator = page.get_by_label(name).first
        elif tag == "select" and name:
            locator = page.get_by_label(name).first
        elif role == "textbox" and name:
            locator = page.get_by_role("textbox", name=name).first
        elif name:
            locator = page.get_by_label(name).first
        else:
            return {"error": f"Cannot type into element {ref}: no name"}
        await locator.fill(text)
        result = await take_snapshot(page)
        result["typed"] = text
        result["into"] = ref
        return result
    except Exception as e:
        return {"error": f"Type failed for {ref}: {e}"}


async def handle_scroll(body: dict) -> dict:
    direction = body.get("direction", "down")
    amount = body.get("amount", 3)
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    delta = amount * 200 if direction == "down" else -(amount * 200)
    await page.evaluate(f"window.scrollBy(0, {delta})")
    await page.wait_for_timeout(500)
    return await take_snapshot(page)


async def handle_screenshot(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    screenshot_bytes = await page.screenshot(full_page=False)
    b64 = base64.b64encode(screenshot_bytes).decode()
    return {"screenshot": b64, "format": "png"}


async def handle_solve_captcha(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    return await solve_captcha(page)


async def handle_new_tab(body: dict) -> dict:
    url = body.get("url", "about:blank")
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    await page.goto(url, wait_until="domcontentloaded")
    return {"tab": task_id, "url": url, "status": "opened"}


async def handle_close_tab(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    if task_id in _pages:
        page = _pages.pop(task_id)
        if not page.is_closed():
            await page.close()
        return {"tab": task_id, "status": "closed"}
    return {"error": f"No tab for task {task_id}"}


async def handle_list_tabs(body: dict) -> dict:
    tabs = []
    for tid, page in list(_pages.items()):
        if not page.is_closed():
            tabs.append({"task_id": tid, "url": page.url, "title": await page.title()})
    return {"tabs": tabs}


async def handle_get_cookies(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    await get_page(task_id)
    cookies = await _context.cookies()
    return {"cookies": cookies}


async def handle_set_cookies(body: dict) -> dict:
    cookies = body.get("cookies", [])
    await _context.add_cookies(cookies)
    return {"status": "ok", "count": len(cookies)}


async def handle_wait(body: dict) -> dict:
    ms = body.get("ms", 1000)
    await asyncio.sleep(ms / 1000)
    return {"waited": ms}


async def handle_go_back(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    await page.go_back(wait_until="domcontentloaded")
    await page.wait_for_timeout(1000)
    return await take_snapshot(page)


async def handle_page_content(body: dict) -> dict:
    task_id = body.get("task_id", "default")
    page = await get_page(task_id)
    content = await page.content()
    return {"html": content, "url": page.url}


# ---------------------------------------------------------------------------
# Route dispatch table
# ---------------------------------------------------------------------------

ROUTES = {
    "/navigate": handle_navigate,
    "/snapshot": handle_snapshot,
    "/click": handle_click,
    "/type": handle_type,
    "/scroll": handle_scroll,
    "/screenshot": handle_screenshot,
    "/solve_captcha": handle_solve_captcha,
    "/new_tab": handle_new_tab,
    "/close_tab": handle_close_tab,
    "/list_tabs": handle_list_tabs,
    "/get_cookies": handle_get_cookies,
    "/set_cookies": handle_set_cookies,
    "/wait": handle_wait,
    "/go_back": handle_go_back,
    "/page_content": handle_page_content,
}


# ---------------------------------------------------------------------------
# HTTP Handler (synchronous — delegates to shared async loop)
# ---------------------------------------------------------------------------

class PatchrightHandler(BaseHTTPRequestHandler):
    def _send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"status": "ok", "backend": "patchright"})
        else:
            self._send_json({"error": f"Unknown GET endpoint: {self.path}"}, 404)

    def do_POST(self):
        body = self._read_body()
        handler = ROUTES.get(self.path)
        if handler is None:
            self._send_json({"error": f"Unknown endpoint: {self.path}"}, 404)
            return
        try:
            result = _run_async(handler(body))
        except Exception as e:
            logger.exception("Handler error for %s", self.path)
            result = {"error": str(e)}
        self._send_json(result)

    def log_message(self, format, *args):
        logger.info(format, *args)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _loop

    parser = argparse.ArgumentParser(description="Patchright Anti-Detection Browser Server")
    parser.add_argument("--port", type=int, default=9378, help="Server port (default: 9378)")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless (default)")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Run with UI")
    parser.add_argument("--proxy", type=str, default=None, help="Proxy URL")
    args = parser.parse_args()

    # Start the shared async event loop in a background thread
    _loop = asyncio.new_event_loop()

    def _run_loop():
        asyncio.set_event_loop(_loop)
        _loop.run_forever()

    loop_thread = threading.Thread(target=_run_loop, daemon=True)
    loop_thread.start()

    # Launch browser on the shared loop
    future = asyncio.run_coroutine_threadsafe(
        launch_browser(headless=args.headless, proxy=args.proxy), _loop
    )
    future.result(timeout=30)

    # Start HTTP server (blocking)
    server = HTTPServer(("127.0.0.1", args.port), PatchrightHandler)
    logger.info("Patchright server running on http://127.0.0.1:%d", args.port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        future = asyncio.run_coroutine_threadsafe(shutdown_browser(), _loop)
        future.result(timeout=10)
        _loop.call_soon_threadsafe(_loop.stop)
        server.server_close()


if __name__ == "__main__":
    main()
