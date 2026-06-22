"""Extract schema.org JSON-LD blocks from an HTML page.

Standardized across many restaurant/business sites — one parser, many sources.
Returns a flat list of JSON-LD objects (handles arrays and @graph).
"""

from __future__ import annotations

import json
import re

_LD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)


def extract_jsonld(html: str | None) -> list[dict]:
    out: list[dict] = []
    for m in _LD.finditer(html or ""):
        raw = m.group(1).strip()
        try:
            data = json.loads(raw)
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and "@graph" in item and isinstance(item["@graph"], list):
                out.extend(g for g in item["@graph"] if isinstance(g, dict))
            elif isinstance(item, dict):
                out.append(item)
    return out
