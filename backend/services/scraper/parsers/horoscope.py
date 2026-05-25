"""
Horoscope page parser.

Four content shapes on www.astrosage.com/horoscope/:

  * daily, tomorrow  -> a single `.ui-large-content-box` containing
        `.ui-large-hdg`     (date label, e.g. 'Monday, May 25, 2026')
        `.ui-large-content` (the actual prediction text)
    Plus a "Today's Rating" widget (6 categories × 5 stars) above it.
    The daily page additionally carries sign-level EVERGREEN sections
    (overview, physical_appearance, mental_ability, characteristics,
    aspects_of_life, twelve_houses) that the parser returns under
    `sign_deepdive` so the service can persist them to `zodiac_signs`.

  * weekly, weekly_love  -> the FIRST `.ui-sign-content-box` widget on the page
        carries this page's primary prediction (the rest are cross-period
        preview cards). Inside it:
        first <b> = date range (e.g. 'Monday, May 25, 2026 - Sunday, May 31, 2026')
        remaining text = prediction; trailing 'More' button + disclaimer trimmed.

  * monthly, next_month, yearly  -> the page body is an H2-structured article
        with sections: General, Career, Finance, Health, Love/Marriage/Personal
        Relations, Family & Friends, Advice (and 'Trade & Finance' for yearly).

The parser is NOT registered with the crawl orchestrator's registry — the
horoscope flow is lazy-load + known-kind, so `parse_horoscope` is called
directly by `services/horoscope.py` with the period it already knows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import Tag

from . import _html_utils as h

PERIOD_DAILY_LIKE = {"daily", "tomorrow"}
PERIOD_WEEKLY_LIKE = {"weekly", "weekly_love"}
PERIOD_LONGFORM = {"monthly", "next_month", "yearly"}

CATEGORY_MAP: dict[str, str] = {
    "general": "prediction",
    "career": "career",
    "finance": "finance",
    "trade & finance": "finance",
    "wealth": "finance",
    "health": "health",
    "love/marriage/personal relations": "love",
    "love/marriage": "love",
    "love": "love",
    "family & friends": "family",
    "family": "family",
    "advice": "advice",
}

# Maps a rating label on the page → snake-case key in the ratings dict.
RATING_LABEL_MAP: dict[str, str] = {
    "health": "health",
    "wealth": "wealth",
    "family": "family",
    "love matters": "love_matters",
    "occupation": "occupation",
    "married life": "married_life",
}

# Deep-dive sections live only on the daily page (verified across all 7
# cached samples). Sign name varies, so we match by stable keywords.
_DEEPDIVE_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bzodiac\s+sign\b", re.I),                   "overview"),
    (re.compile(r"\bphysical\s+appearance\b", re.I),           "physical_appearance"),
    (re.compile(r"\bmental\s+ability\b", re.I),                "mental_ability"),
    (re.compile(r"\bcharacteristics\b", re.I),                 "characteristics"),
    (re.compile(r"\bsignify\b.*\baspects?\s+of\s+life\b", re.I), "aspects_of_life"),
    (re.compile(r"\b12\s+houses?\b|\btwelve\s+houses?\b", re.I), "twelve_houses"),
]

_DISCLAIMER_RE = re.compile(
    r"\s*These are generalized predictions.*$", re.IGNORECASE | re.DOTALL,
)
_MORE_RE = re.compile(r"\s+More\s*$")
_FILLED_STAR_RE = re.compile(r"star2\.gif$", re.I)


@dataclass
class ParsedSignDeepDive:
    sign: str
    language: str = "en"
    overview: str | None = None
    physical_appearance: str | None = None
    mental_ability: str | None = None
    characteristics: str | None = None
    aspects_of_life: str | None = None
    twelve_houses: str | None = None
    source_url: str | None = None


@dataclass
class ParsedHoroscope:
    sign: str
    period: str
    language: str = "en"
    date_label: str | None = None
    prediction: str | None = None
    love: str | None = None
    career: str | None = None
    finance: str | None = None
    health: str | None = None
    family: str | None = None
    advice: str | None = None
    # 6-key dict of 0..5 star ratings — set for daily/tomorrow only.
    ratings: dict[str, int] | None = None
    # Sign-level evergreen prose found on daily pages — service writes
    # this to `zodiac_signs`, not `horoscope_predictions`.
    sign_deepdive: ParsedSignDeepDive | None = None
    source_url: str | None = None


def _heading_norm(text: str) -> str:
    t = h.clean(text).lower().rstrip(":")
    # astrosage prefixes cross-link headings with '»' / '»' / '?'
    return t.lstrip("»»?•●").strip()


def _extract_ratings(soup) -> dict[str, int] | None:
    """Find the 'Today's Rating' grid (6 × col-sm-4 cards, 5 imgs each).
    Filled stars are `star2.gif`; empty stars are `star1.gif`.
    """
    anchor = soup.find("h2", string=lambda s: bool(s) and "Rating" in s)
    if not anchor:
        return None
    grid = anchor.find_next("div", class_="show-grid")
    if not grid:
        return None
    ratings: dict[str, int] = {}
    for col in grid.find_all("div", class_="col-sm-4"):
        b = col.find("b")
        label = h.clean(b.get_text(" ", strip=True) if b else "").rstrip(":").lower()
        key = RATING_LABEL_MAP.get(label)
        if not key:
            continue
        filled = sum(
            1 for img in col.find_all("img")
            if _FILLED_STAR_RE.search(img.get("src", "") or "")
        )
        ratings[key] = filled
    return ratings or None


def _extract_deepdive(soup, sign: str, language: str, url: str) -> ParsedSignDeepDive | None:
    """Walk H2 sections, match against deep-dive keyword patterns. Returns
    None if NO deep-dive headings are present (i.e. not the daily page)."""
    root = h.main_content(soup)
    h2s = [hh for hh in root.find_all("h2") if h.clean(hh.get_text(" ", strip=True))]
    out = ParsedSignDeepDive(sign=sign, language=language, source_url=url)
    seen: set[str] = set()
    matched_any = False
    for i, hh in enumerate(h2s):
        title = _heading_norm(hh.get_text(" ", strip=True))
        field_name: str | None = None
        for pat, fname in _DEEPDIVE_PATTERNS:
            if pat.search(title):
                field_name = fname
                break
        if not field_name or field_name in seen:
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
            setattr(out, field_name, body)
            seen.add(field_name)
            matched_any = True
    return out if matched_any else None


def _parse_daily_like(soup, sign: str, period: str, language: str, url: str) -> ParsedHoroscope:
    box = soup.select_one(".ui-large-content-box")
    date_label = None
    prediction = None
    if box:
        hdg = box.select_one(".ui-large-hdg")
        cnt = box.select_one(".ui-large-content")
        date_label = h.clean(hdg.get_text(" ", strip=True)) if hdg else None
        prediction = h.clean(cnt.get_text(" ", strip=True)) if cnt else None
    ratings = _extract_ratings(soup)
    # Deep-dive only exists on the actual daily page; tomorrow page has
    # the rating widget but no sign-level evergreen sections.
    deepdive = _extract_deepdive(soup, sign, language, url) if period == "daily" else None
    return ParsedHoroscope(
        sign=sign, period=period, language=language, source_url=url,
        date_label=date_label or None, prediction=prediction or None,
        ratings=ratings, sign_deepdive=deepdive,
    )


def _parse_weekly_like(soup, sign: str, period: str, language: str, url: str) -> ParsedHoroscope:
    widgets = soup.select(".ui-sign-content-box")
    if not widgets:
        return ParsedHoroscope(sign=sign, period=period, language=language, source_url=url)
    primary = widgets[0]
    date_b = primary.find("b")
    date_label = h.clean(date_b.get_text(" ", strip=True)) if date_b else None
    full = h.clean(primary.get_text(" ", strip=True))
    text = full
    if date_label and text.startswith(date_label):
        text = text[len(date_label):].strip()
    text = _MORE_RE.sub("", text)
    text = _DISCLAIMER_RE.sub("", text).strip()
    return ParsedHoroscope(
        sign=sign, period=period, language=language, source_url=url,
        date_label=date_label or None, prediction=text or None,
    )


def _parse_longform(soup, sign: str, period: str, language: str, url: str) -> ParsedHoroscope:
    root = h.main_content(soup)
    h2s = [hh for hh in root.find_all("h2") if h.clean(hh.get_text(" ", strip=True))]
    result = ParsedHoroscope(sign=sign, period=period, language=language, source_url=url)
    seen: set[str] = set()
    for i, hh in enumerate(h2s):
        field_name = CATEGORY_MAP.get(_heading_norm(hh.get_text(" ", strip=True)))
        if not field_name or field_name in seen:
            continue
        stop = h2s[i + 1] if i + 1 < len(h2s) else None
        parts: list[str] = []
        for sib in hh.next_elements:
            if sib is stop:
                break
            if isinstance(sib, Tag) and sib.name == "p":
                t = h.clean(sib.get_text(" ", strip=True))
                if t and not t.startswith("These are generalized"):
                    parts.append(t)
        body = "\n".join(parts).strip()
        if body:
            setattr(result, field_name, body)
            seen.add(field_name)
    # Surface the year/month label, if present in the title.
    h1 = soup.find("h1")
    if h1:
        result.date_label = h.clean(h1.get_text(" ", strip=True)) or None
    return result


def parse_horoscope(
    html_text: str, url: str, *, sign: str, period: str, language: str = "en",
) -> ParsedHoroscope:
    soup = h.soup_of(html_text)
    if period in PERIOD_DAILY_LIKE:
        return _parse_daily_like(soup, sign, period, language, url)
    if period in PERIOD_WEEKLY_LIKE:
        return _parse_weekly_like(soup, sign, period, language, url)
    if period in PERIOD_LONGFORM:
        return _parse_longform(soup, sign, period, language, url)
    raise ValueError(f"Unknown horoscope period: {period!r}")
