#!/usr/bin/env python3
"""Patchright browser backend — anti-detection Playwright via local CDP.

Patchright (https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) is a
patched version of Playwright that bypasses bot detection systems
(Cloudflare, Datadome, PerimeterX, etc.) using C++-level fingerprint
spoofing — similar to Camoufox but based on Chromium.

This module provides a lightweight REST API server that wraps Patchright,
exposing the same interface as the Camofox backend so the browser tools
can route through it transparently.

When ``PATCHRIGHT_URL`` is set (e.g. ``http://localhost:9378``), the browser
tools route through this module instead of the default ``agent-browser`` CLI.

Setup::

    pip install patchright captcha-solver
    patchright install chromium

Then start the server (included as ``scripts/patchright_server.py``)::

    python scripts/patchright_server.py --port 9378

And set ``PATCHRIGHT_URL=http://localhost:9378`` in ``~/.hermes/.env``.

Environment Variables:
- PATCHRIGHT_URL: Base URL of the Patchright REST server
- PATCHRIGHT_HEADLESS: Run in headless mode (default: "true")
- PATCHRIGHT_PROXY: Proxy URL (e.g. "http://127.0.0.1:7897")
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import requests

from hermes_cli.config import cfg_get
from tools.registry import tool_error

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30


def get_patchright_url() -> str:
    """Return the configured Patchright server URL, or empty string."""
    return os.getenv("PATCHRIGHT_URL", "").rstrip("/")


def is_patchright_mode() -> bool:
    """True when Patchright backend is configured and no CDP override is active."""
    if os.getenv("BROWSER_CDP_URL", "").strip():
        return False
    return bool(get_patchright_url())


def check_patchright_available() -> bool:
    """Verify the Patchright server is reachable."""
    url = get_patchright_url()
    if not url:
        return False
    try:
        resp = requests.get(f"{url}/health", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

def patchright_navigate(url: str, task_id: str = "default") -> Dict[str, Any]:
    """Navigate to a URL via the Patchright server."""
    server_url = get_patchright_url()
    if not server_url:
        return tool_error("Patchright server URL not configured. Set PATCHRIGHT_URL.")

    try:
        resp = requests.post(
            f"{server_url}/navigate",
            json={"url": url, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return tool_error(
            "Cannot connect to Patchright server at "
            f"{server_url}. Is it running? "
            "Start with: python scripts/patchright_server.py --port 9378"
        )
    except Exception as e:
        return tool_error(f"Patchright navigate error: {e}")


# ---------------------------------------------------------------------------
# Snapshot (accessibility tree)
# ---------------------------------------------------------------------------

def patchright_snapshot(
    full: bool = False,
    task_id: str = "default",
    user_task: str = "",
) -> Dict[str, Any]:
    """Get page snapshot via Patchright server."""
    server_url = get_patchright_url()
    if not server_url:
        return tool_error("Patchright server URL not configured. Set PATCHRIGHT_URL.")

    try:
        resp = requests.post(
            f"{server_url}/snapshot",
            json={
                "full": full,
                "task_id": task_id,
                "user_task": user_task,
            },
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright snapshot error: {e}")


# ---------------------------------------------------------------------------
# Click / Type / Scroll
# ---------------------------------------------------------------------------

def patchright_click(ref: str, task_id: str = "default") -> Dict[str, Any]:
    """Click an element by ref (e.g. @e1)."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/click",
            json={"ref": ref, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright click error: {e}")


def patchright_type(ref: str, text: str, task_id: str = "default") -> Dict[str, Any]:
    """Type text into an element by ref."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/type",
            json={"ref": ref, "text": text, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright type error: {e}")


def patchright_scroll(
    direction: str = "down",
    amount: int = 3,
    task_id: str = "default",
) -> Dict[str, Any]:
    """Scroll the page."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/scroll",
            json={"direction": direction, "amount": amount, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright scroll error: {e}")


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def patchright_screenshot(task_id: str = "default") -> Dict[str, Any]:
    """Take a screenshot and return base64-encoded image."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/screenshot",
            json={"task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright screenshot error: {e}")


# ---------------------------------------------------------------------------
# CAPTCHA solving
# ---------------------------------------------------------------------------

def patchright_solve_captcha(task_id: str = "default") -> Dict[str, Any]:
    """Attempt to solve any detected CAPTCHA on the current page."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/solve_captcha",
            json={"task_id": task_id},
            timeout=60,  # CAPTCHAs can take longer
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright CAPTCHA solve error: {e}")


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

def patchright_new_tab(url: str, task_id: str = "default") -> Dict[str, Any]:
    """Open a new browser tab."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/new_tab",
            json={"url": url, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright new tab error: {e}")


def patchright_close_tab(tab_index: int, task_id: str = "default") -> Dict[str, Any]:
    """Close a browser tab by index."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/close_tab",
            json={"tab_index": tab_index, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright close tab error: {e}")


def patchright_list_tabs(task_id: str = "default") -> Dict[str, Any]:
    """List all open browser tabs."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/list_tabs",
            json={"task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright list tabs error: {e}")


# ---------------------------------------------------------------------------
# Cookie management
# ---------------------------------------------------------------------------

def patchright_get_cookies(task_id: str = "default") -> Dict[str, Any]:
    """Get all cookies for the current page."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/get_cookies",
            json={"task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright get cookies error: {e}")


def patchright_set_cookies(
    cookies: list,
    task_id: str = "default",
) -> Dict[str, Any]:
    """Set cookies for the current page."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/set_cookies",
            json={"cookies": cookies, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright set cookies error: {e}")


# ---------------------------------------------------------------------------
# Wait / utility
# ---------------------------------------------------------------------------

def patchright_wait(ms: int = 1000, task_id: str = "default") -> Dict[str, Any]:
    """Wait for a specified number of milliseconds."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/wait",
            json={"ms": ms, "task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright wait error: {e}")


def patchright_go_back(task_id: str = "default") -> Dict[str, Any]:
    """Navigate back in browser history."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/go_back",
            json={"task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright go_back error: {e}")


def patchright_get_page_content(task_id: str = "default") -> Dict[str, Any]:
    """Get the full HTML content of the current page."""
    server_url = get_patchright_url()
    try:
        resp = requests.post(
            f"{server_url}/page_content",
            json={"task_id": task_id},
            timeout=_DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return tool_error(f"Patchright page_content error: {e}")
