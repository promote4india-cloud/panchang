"""
Parser registry — maps URL templates to template-specific parsers.

A parser takes raw HTML + URL context and returns a typed dict ready for
upsert into festival_content / muhurat_content / etc.

Per-template parsers slot in under services/scraper/parsers/. They register
themselves via @register_parser('festival_leaf'), etc. This file is the
glue — it doesn't implement the parsing.

Template kinds we plan to support (from astrosage panchang sitemap):

    festival_root        /festival                          (catalog crawl)
    festival_top         /festival/<slug>                   (e.g. /festival/diwali)
    festival_leaf        /festival/<slug>/<sub>             (e.g. /festival/ekadashi/mohini-ekadashi)
    festival_leaf_3d     /festival/<slug>/<sub>/<sub2>      (e.g. .../dhanteras/dhanteras-date-muhurat)
    festival_today       /festival/today-festival
    muhurat_root         /muhurat                           (catalog crawl)
    muhurat_detail       /muhurat/<slug>                    (e.g. /muhurat/griha-pravesh-muhurat)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

TemplateKind = Literal[
    "festival_root", "festival_top", "festival_leaf", "festival_leaf_3d",
    "festival_today", "muhurat_root", "muhurat_detail",
]


@dataclass
class ParsedFestival:
    """Output of a festival-page parser. Maps directly to DB rows."""
    festival_id: str
    slug_path: str
    parent_id: str | None = None
    kind: str = "festival"                       # festivals.kind
    type: str | None = None                      # festivals.type
    auspiciousness: str | None = None
    rule_type: str | None = None
    rule_json: str | None = None
    thumbnail_url: str | None = None
    source_url: str | None = None
    # editorial:
    language: str = "en"
    name: str = ""
    subtitle: str | None = None
    about: str | None = None
    significance: str | None = None
    history: str | None = None
    scriptures: str | None = None
    puja_vidhi: str | None = None
    rituals: list[str] = field(default_factory=list)
    faqs: list[tuple[str, str]] = field(default_factory=list)
    # children discovered on a "top" page (e.g. Dhanteras link on /festival/diwali):
    child_slugs: list[str] = field(default_factory=list)


@dataclass
class ParsedMuhurat:
    """Output of a muhurat-page parser."""
    muhurat_id: str
    category: str = "event"                      # muhurat_types.category
    computable: bool = False
    source_url: str | None = None
    language: str = "en"
    name: str = ""
    description: str | None = None
    vedic_basis: str | None = None
    importance: str | None = None
    subsections: list[tuple[str, str]] = field(default_factory=list)
    faqs: list[tuple[str, str]] = field(default_factory=list)


ParserFn = Callable[[str, str], ParsedFestival | ParsedMuhurat]
# Signature: parser(html, url) -> Parsed{Festival|Muhurat}

_REGISTRY: dict[TemplateKind, ParserFn] = {}


def register_parser(kind: TemplateKind):
    def deco(fn: ParserFn) -> ParserFn:
        _REGISTRY[kind] = fn
        return fn
    return deco


def get_parser(kind: TemplateKind) -> ParserFn:
    if kind not in _REGISTRY:
        raise KeyError(
            f"No parser registered for template '{kind}'. "
            f"Add one in services/scraper/parsers/ and decorate with "
            f"@register_parser('{kind}')."
        )
    return _REGISTRY[kind]


def classify_url(path_parts: list[str]) -> TemplateKind:
    """Cheap dispatcher based on URL path segments after the host."""
    if not path_parts:
        raise ValueError("empty path")
    if path_parts[0] == "festival":
        if len(path_parts) == 1:
            return "festival_root"
        if path_parts[1] == "today-festival":
            return "festival_today"
        if len(path_parts) == 2:
            return "festival_top"
        if len(path_parts) == 3:
            return "festival_leaf"
        return "festival_leaf_3d"
    if path_parts[0] == "muhurat":
        return "muhurat_root" if len(path_parts) == 1 else "muhurat_detail"
    raise ValueError(f"Unknown URL shape: {'/'.join(path_parts)}")
