"""
Muhurat detail-page parser. Produces a ParsedMuhurat.

Computable muhurats (the 9 already implemented in services/muhurat.py) get
`computable=True` here, so the public muhurat endpoint can prefer rule output
over scraped tables. Editorial text still comes from the scrape.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ..registry import ParsedMuhurat, register_parser
from . import _html_utils as h

# IDs already computed by services/muhurat.py — keep these in sync with that
# module's MUHURATS list.
COMPUTABLE_MUHURAT_IDS: set[str] = {
    "abhijit", "amrit-kalam", "brahma", "godhuli", "nishita",
    "rahu-kalam", "yamaganda", "gulika", "vijaya",
    "pradosh", "vrishabha-kaal",
}


@register_parser("muhurat_detail")
def parse_muhurat(html_text: str, url: str) -> ParsedMuhurat:
    soup = h.soup_of(html_text)
    parts = [p for p in urlparse(url).path.split("/") if p]
    slug = parts[-1] if parts else ""
    name = h.page_title(soup) or slug.replace("-", " ").title()
    about, named, extra = h.collect_sections(soup, muhurat=True)
    faqs = h.extract_faqs(soup)

    return ParsedMuhurat(
        muhurat_id=slug,
        category="event",
        computable=slug in COMPUTABLE_MUHURAT_IDS,
        source_url=url,
        language="en",
        name=name,
        description=about or None,
        vedic_basis=named.get("vedic_basis"),
        importance=named.get("importance"),
        subsections=extra,
        faqs=faqs,
    )
