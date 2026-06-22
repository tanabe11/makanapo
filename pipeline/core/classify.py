"""Deterministic food/service vs retail classifier (keyword-based).

Mall kamaaina pages list mostly retail; MVP scope is food & service only.
Returns 'food', 'service', or None (skip). Service checked first so a nail
salon's "20% off retail items" still classifies as service.
"""

from __future__ import annotations

import re

_SERVICE = re.compile(
    r"\b(spa|salon|nails?|mani|pedi|barber|massage|facial|fitness|yoga|gym|pilates"
    r"|brow|lash|hair|wax|grooming|skincare|treatment|free trial|trial class|classes)\b",
    re.I,
)
_FOOD = re.compile(
    r"\b(food|dining|menu|beverages?|drinks?|appetiz\w*|pupus?|restaurant|cafe|café"
    r"|coffee|crepes?|lemonade|grill|kitchen|sushi|ramen|poke|bakery|malasada|pho"
    r"|thai|teppan|lobster|seafood|pizza|burgers?|bbq|eatery|juice|boba|tea|ice cream"
    r"|brazil|happy hour|cocktails?|wine|brunch)\b",
    re.I,
)


def category_of(*texts: str | None) -> str | None:
    t = " ".join(x for x in texts if x)
    if _SERVICE.search(t):
        return "service"
    if _FOOD.search(t):
        return "food"
    return None
