"""
Sign-intro page parser for www.astrosage.com/horoscope/{sign}.asp.

Pulls only the PROSE editorial fields. Structural data (name, vedic_name,
symbol, date_range, lord) lives in Python constants in routers/reference.py
and is merged in at API read time — see services/zodiac.py.

Heading shape on astrosage's sign pages (sign-name varies, the keywords
don't):
    H2 'What is <Sign> Sign?'   -> summary
    H2 'What are <Sign> Traits?' -> traits
    H2 '<Sign> in Love'          -> love
    H2 '<Sign> Compatibility'    -> compatibility

The H1's leading paragraphs are a sensible fallback for `summary` when no
'What is <Sign> Sign?' heading is present.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import Tag

from . import _html_utils as h

_KEYWORD_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bwhat is\b.*\bsign\??$", re.I),       "summary"),
    (re.compile(r"\btraits?\b", re.I),                   "traits"),
    (re.compile(r"\bin\s+love\b", re.I),                 "love"),
    (re.compile(r"\bcompatibility\b", re.I),             "compatibility"),
]


@dataclass
class ParsedSignIntro:
    sign: str
    language: str = "en"
    summary: str | None = None
    traits: str | None = None
    love: str | None = None
    compatibility: str | None = None
    source_url: str | None = None


def _heading_field(text: str) -> str | None:
    txt = h.clean(text).lstrip("»»?•●").strip()
    for pat, field in _KEYWORD_MAP:
        if pat.search(txt):
            return field
    return None


def parse_sign_intro(
    html_text: str, url: str, *, sign: str, language: str = "en",
) -> ParsedSignIntro:
    soup = h.soup_of(html_text)
    root = h.main_content(soup)
    result = ParsedSignIntro(sign=sign, language=language, source_url=url)

    h2s = [hh for hh in root.find_all("h2") if h.clean(hh.get_text(" ", strip=True))]
    seen: set[str] = set()
    for i, hh in enumerate(h2s):
        field = _heading_field(hh.get_text(" ", strip=True))
        if not field or field in seen:
            continue
        stop = h2s[i + 1] if i + 1 < len(h2s) else None
        parts: list[str] = []
        for sib in hh.next_elements:
            if sib is stop:
                break
            if isinstance(sib, Tag) and sib.name in {"p", "li"}:
                t = h.clean(sib.get_text(" ", strip=True))
                if t and not t.startswith("These are generalized"):
                    parts.append(t)
        body = "\n".join(parts).strip()
        if body:
            setattr(result, field, body)
            seen.add(field)

    # Fallback for summary: lead paragraph(s) before the first non-noise H2.
    if not result.summary:
        about, _named, _extras = h.collect_sections(soup, muhurat=False)
        if about:
            result.summary = about

    return result
