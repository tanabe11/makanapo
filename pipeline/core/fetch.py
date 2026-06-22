"""Shared HTTP layer: UA, timeout, retry, rate-limit, robots.txt respect.

Stdlib only (no external deps). Used by every source module.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse

USER_AGENT = "makanapo-bot/0.1 (+https://po.makana.fm)"
MIN_INTERVAL = 1.0  # seconds between requests (politeness rate-limit)

_last_request = 0.0
_robots_cache: dict[str, urllib.robotparser.RobotFileParser | None] = {}


def _allowed_by_robots(url: str) -> bool:
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base not in _robots_cache:
        # Fetch robots.txt with OUR User-Agent and parse it ourselves.
        # RobotFileParser.read() sends no UA, which some WAFs 403 -> the parser
        # then treats the whole site as disallowed (false positive).
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(
                base + "/robots.txt", headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                rp.parse(resp.read().decode("utf-8", errors="replace").splitlines())
        except Exception:
            rp = None  # robots unreadable / 404 -> allow (fail open)
        _robots_cache[base] = rp
    rp = _robots_cache[base]
    return True if rp is None else rp.can_fetch(USER_AGENT, url)


def _throttle() -> None:
    global _last_request
    wait = MIN_INTERVAL - (time.time() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.time()


def get_text(url: str, timeout: int = 30, retries: int = 2) -> str:
    if not _allowed_by_robots(url):
        raise PermissionError(f"robots.txt disallows: {url}")
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            _throttle()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001 - retry any transient error
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise last_err  # type: ignore[misc]


def get_json(url: str, **kwargs):
    return json.loads(get_text(url, **kwargs))
