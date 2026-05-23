"""
Festival page parser. One implementation covers all three depths:

    /festival/<slug>                  -> festival_top
    /festival/<slug>/<sub>            -> festival_leaf
    /festival/<slug>/<sub>/<sub2>     -> festival_leaf_3d

The shape of the page is essentially the same — title, intro, named sections,
optional bullet list of rituals. festival_top pages additionally expose links
to child festivals (e.g. /festival/diwali links Dhanteras, Bhai Dooj, etc.),
which we capture in `child_slugs` so the orchestrator can BFS them.
"""

from __future__ import annotations

from urllib.parse import urlparse

from ..registry import ParsedFestival, register_parser
from . import _html_utils as h


def _slug_path(url: str) -> str:
    parts = [p for p in urlparse(url).path.split("/") if p]
    # Drop leading "festival"
    return "/".join(parts[1:]) if parts and parts[0] == "festival" else "/".join(parts)


def _id_from_slug(slug_path: str) -> str:
    """Slashes aren't great in URL path params, so we collapse to dots."""
    return slug_path.replace("/", ".")


def _parent_id(slug_path: str) -> str | None:
    parts = slug_path.split("/")
    return _id_from_slug("/".join(parts[:-1])) if len(parts) > 1 else None


def _parse_festival(html_text: str, url: str) -> ParsedFestival:
    soup = h.soup_of(html_text)
    slug_path = _slug_path(url)
    fid = _id_from_slug(slug_path)
    parent = _parent_id(slug_path)

    name = h.page_title(soup) or slug_path.split("/")[-1].replace("-", " ").title()
    subtitle = h.page_subtitle(soup)
    about, named, _extra = h.collect_sections(soup, muhurat=False)
    rituals = h.extract_bullet_list(soup, ["ritual", "vidhi", "puja"])
    faqs = h.extract_faqs(soup)
    children = h.child_festival_slugs(soup, slug_path) if "/" not in slug_path else []

    return ParsedFestival(
        festival_id=fid,
        slug_path=slug_path,
        parent_id=parent,
        kind="festival",
        type=None,
        auspiciousness=None,
        rule_type=None,
        rule_json=None,
        thumbnail_url=h.thumbnail_url(soup, url),
        source_url=url,
        language="en",
        name=name,
        subtitle=subtitle if subtitle and subtitle != name else None,
        about=about or None,
        significance=named.get("significance"),
        history=named.get("history"),
        scriptures=named.get("scriptures"),
        puja_vidhi=named.get("puja_vidhi"),
        rituals=rituals,
        faqs=faqs,
        child_slugs=children,
    )


# Same logic for all three depths — the orchestrator decides what to do with children.
register_parser("festival_top")(_parse_festival)
register_parser("festival_leaf")(_parse_festival)
register_parser("festival_leaf_3d")(_parse_festival)
