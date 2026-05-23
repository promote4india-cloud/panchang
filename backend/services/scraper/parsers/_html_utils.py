"""
Shared HTML helpers for astrosage page parsing.

Selectors are deliberately loose: we walk by tag (h1/h2/ul/p/a/img/meta) rather
than by class names, since astrosage's class names are not stable across
templates. Each helper accepts a BeautifulSoup root and returns plain
Python data — no DB writes, no network.
"""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

YEAR_SUFFIX_RE = re.compile(r"\s*\b(19|20|21)\d{2}\b.*$")
WS_RE = re.compile(r"\s+")

# Heuristic blacklist of h2 texts that aren't real sections (ads, day cards,
# nav widgets, date numerals, etc.).
NOISE_HEADING_RE = re.compile(
    r"^(more articles|day\s*\d+|\d+(st|nd|rd|th)?|"
    r"january|february|march|april|may|june|july|"
    r"august|september|october|november|december|"
    r"astrosage|buy\s+|punit pandey|today's festival|"
    r"share|comments|newsletter)\b",
    re.IGNORECASE,
)

# Maps astrosage section heading → our canonical field name.
SECTION_MAP = {
    "about": "about",
    "introduction": "about",
    "significance": "significance",
    "importance": "significance",
    "why": "significance",
    "history": "history",
    "historical legend": "history",
    "legend": "history",
    "story": "history",
    "katha": "history",
    "scripture": "scriptures",
    "scriptures": "scriptures",
    "as per vedic": "scriptures",
    "vedic text": "scriptures",
    "puja vidhi": "puja_vidhi",
    "vrat vidhi": "puja_vidhi",
    "ritual": "puja_vidhi",
    "rituals": "puja_vidhi",
    "puja and rituals": "puja_vidhi",
    "puja & rituals": "puja_vidhi",
    "how to": "puja_vidhi",
}

# Muhurat-specific section overrides (applied AFTER SECTION_MAP).
MUHURAT_SECTION_MAP = {
    "significance": "importance",
    "importance": "importance",
    "as per vedic": "vedic_basis",
    "vedic text": "vedic_basis",
}


def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def clean(text: str | None) -> str:
    if not text:
        return ""
    return WS_RE.sub(" ", text).strip()


def main_content(soup: BeautifulSoup) -> Tag:
    """Best guess at the editorial content container, falls back to <body>."""
    for sel in ("main", "article", "#main", "#content", ".content", ".main"):
        node = soup.select_one(sel)
        if node:
            return node
    return soup.body or soup  # type: ignore[return-value]


def page_title(soup: BeautifulSoup) -> str:
    """Cleaned h1 text without trailing year + boilerplate ('Diwali 2026 Puja Dates' → 'Diwali')."""
    h1 = soup.find("h1")
    raw = clean(h1.get_text(" ", strip=True) if h1 else "") or clean(soup.title.get_text() if soup.title else "")
    raw = YEAR_SUFFIX_RE.sub("", raw)
    # Strip trailing "Puja Dates", "Vrat", "Muhurat 2026 Dates" etc. left over
    raw = re.sub(r"\s+(puja dates|vrat|muhurat dates|dates|fast)\s*$", "", raw, flags=re.I)
    return raw.strip()


# Matches a 4-digit year anywhere in text (with surrounding whitespace).
_YEAR_INLINE_RE = re.compile(r"\s*\b(19|20|21)\d{2}\b\s*")

# Headings that bake in a specific year, date, or location are not durable
# (they'll be stale next year). For muhurat_subsections we blank them out
# rather than store "Pushya Nakshatra 2026 dates for New Delhi, India".
_EPHEMERAL_HEADING_RE = re.compile(
    r"\b(19|20|21)\d{2}\b"                                   # year
    r"|\b(mon|tue|wed|thu|fri|sat|sun)(day)?\b"              # weekday word
    r"|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"  # month word
    r"[a-z]*\b\s+\d{1,2}"
    r"|\bfor\s+[A-Z][a-z]+([\s-][A-Z][a-z]+)*,\s*[A-Z][a-z]+",  # 'for <City>, <Country>'
    re.I,
)


def _clean_subsection_heading(title: str) -> str:
    """Return '' for ephemeral headings (year/date/'for <city>'), else title."""
    if _EPHEMERAL_HEADING_RE.search(title):
        return ""
    return title


def page_subtitle(soup: BeautifulSoup) -> str | None:
    """Subtitle = H1 with the year stripped so it stays evergreen.

    Example: 'Diwali 2026 Puja Dates' -> 'Diwali Puja Dates'
             'Jagannath Rath Yatra 2026' -> 'Jagannath Rath Yatra'
    Returns None if nothing meaningful remains.
    """
    h1 = soup.find("h1")
    if not h1:
        return None
    raw = clean(h1.get_text(" ", strip=True))
    # Collapse the year + tidy any double spaces / leftover punctuation.
    cleaned = _YEAR_INLINE_RE.sub(" ", raw)
    cleaned = re.sub(r"\s+([,.;:])", r"\1", cleaned)
    cleaned = WS_RE.sub(" ", cleaned).strip(" ,.-–—")
    return cleaned or None


_THUMB_SKIP_RE = re.compile(r"(loader|placeholder|spacer|blank)\.(gif|png|svg)$", re.I)


def thumbnail_url(soup: BeautifulSoup, base_url: str) -> str | None:
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        cand = og["content"].strip()
        if not _THUMB_SKIP_RE.search(cand):
            return urljoin(base_url, cand)
    # Fallback: first <img> inside main content with a real raster src
    for img in main_content(soup).find_all("img"):
        src = (img.get("src") or "").strip()
        if not src or _THUMB_SKIP_RE.search(src) or src.endswith(".svg"):
            continue
        if "/images/" in src or src.startswith(("http://", "https://")):
            return urljoin(base_url, src)
    return None


def _heading_to_field(text: str, *, muhurat: bool = False) -> str | None:
    norm = text.lower().strip().rstrip(":")
    if muhurat:
        for key, field in MUHURAT_SECTION_MAP.items():
            if key in norm:
                return field
    for key, field in SECTION_MAP.items():
        if key in norm:
            return field
    return None


def collect_sections(
    soup: BeautifulSoup, *, muhurat: bool = False
) -> tuple[str, dict[str, str], list[tuple[str, str]]]:
    """
    Walk H2 elements inside main content, group siblings until next H2.

    Returns:
        about_text:    paragraphs before the first H2 (intro)
        named:         dict of canonical_field -> joined text
        subsections:   raw (heading, body) list of OTHER non-noise sections,
                       useful for muhurat_subsections.
    """
    root = main_content(soup)
    # Drop empty h2s (astrosage uses bare <h2></h2> as visual separators).
    h2s = [h for h in root.find_all("h2") if clean(h.get_text(" ", strip=True))]

    # 1) about: paragraphs BEFORE the first non-noise h2 (intro).
    first_real_h2 = next(
        (h for h in h2s if not NOISE_HEADING_RE.match(clean(h.get_text(" ", strip=True)))),
        None,
    )
    about_parts: list[str] = []
    if first_real_h2 is not None:
        for child in root.descendants:
            if child is first_real_h2:
                break
            if getattr(child, "name", None) == "p":
                t = clean(child.get_text(" ", strip=True))
                if t:
                    about_parts.append(t)
    if not about_parts:
        # Fallback: substantial floating paragraphs anywhere in main content.
        # Filters out card chrome (short labels, dates, nav text).
        for p in root.find_all("p"):
            t = clean(p.get_text(" ", strip=True))
            if len(t) >= 100 and not NOISE_HEADING_RE.match(t):
                about_parts.append(t)
        # Cap to first ~6 substantial paragraphs to keep the field readable.
        about_parts = about_parts[:6]

    named: dict[str, list[str]] = {}
    subsections: list[tuple[str, str]] = []

    for i, h in enumerate(h2s):
        title = clean(h.get_text(" ", strip=True))
        if not title or NOISE_HEADING_RE.match(title):
            continue
        stop = h2s[i + 1] if i + 1 < len(h2s) else None
        body_parts: list[str] = []
        for sib in h.next_elements:
            if sib is stop:
                break
            if isinstance(sib, Tag) and sib.name in {"p", "li"}:
                t = clean(sib.get_text(" ", strip=True))
                if t:
                    body_parts.append(t)
        body = "\n".join(body_parts).strip()
        if not body:
            continue
        field = _heading_to_field(title, muhurat=muhurat)
        if field:
            named.setdefault(field, []).append(body)
        else:
            # Blank out headings that hard-code a year / date / city — those
            # go stale every Jan 1st. Body still wins as the content.
            subsections.append((_clean_subsection_heading(title), body))

    return (
        "\n\n".join(about_parts).strip(),
        {k: "\n\n".join(v).strip() for k, v in named.items()},
        subsections,
    )


# Phrases that mark a UL/OL as site chrome rather than editorial content
# (newsletter widgets, related-article rails, footer nav).
_LIST_NOISE_RE = re.compile(
    r"newsletter|daily horoscope|subscribe|follow us|related articles|"
    r"more articles|share this|read more|sign up|email us",
    re.I,
)


def _looks_like_nav_list(node: Tag) -> bool:
    """Reject UL/OL widgets: nav menus, newsletter signups, link rails."""
    items = node.find_all("li", recursive=False) or node.find_all("li")
    if not items:
        return True
    # Form widgets are never editorial lists.
    if node.find(["form", "input", "button", "select"]):
        return True
    text_all = clean(node.get_text(" ", strip=True))
    if _LIST_NOISE_RE.search(text_all):
        return True
    link_only = 0
    too_short = 0
    for li in items:
        txt = clean(li.get_text(" ", strip=True))
        # Treat as link-only when the li's text equals the text of an <a> it contains.
        a = li.find("a")
        if a and clean(a.get_text(" ", strip=True)) == txt:
            link_only += 1
        if len(txt) < 20:
            too_short += 1
    # If most items are bare links or tiny labels, it's chrome, not a ritual list.
    if link_only >= max(2, len(items) * 0.6):
        return True
    if too_short >= max(2, len(items) * 0.8):
        return True
    return False


def extract_bullet_list(soup: BeautifulSoup, heading_keywords: list[str]) -> list[str]:
    """
    Find an H2 whose text contains any keyword, then return the items of the
    next <ul>/<ol> that appears BEFORE the next H2. Skips nav/widget lists.
    Falls back to splitting paragraph text on the '●' bullet character
    (astrosage uses it inline).
    """
    root = main_content(soup)
    kw_re = re.compile("|".join(re.escape(k) for k in heading_keywords), re.I)
    # Astrosage uses bare <h2></h2> as visual separators — ignore them so the
    # ritual section isn't immediately bounded by an empty stub.
    headings = [
        hh for hh in root.find_all("h2")
        if clean(hh.get_text(" ", strip=True))
    ]
    for idx, hh in enumerate(headings):
        if not kw_re.search(hh.get_text(" ", strip=True)):
            continue
        # Bound the search to the section between this H2 and the next.
        stop = headings[idx + 1] if idx + 1 < len(headings) else None
        for sib in hh.next_elements:
            if sib is stop:
                break
            if not isinstance(sib, Tag):
                continue
            if sib.name in {"ul", "ol"}:
                if _looks_like_nav_list(sib):
                    continue
                items = [
                    clean(li.get_text(" ", strip=True))
                    for li in sib.find_all("li")
                ]
                items = [x for x in items if x]
                if items:
                    return items
            if sib.name == "p":
                txt = sib.get_text(" ", strip=True)
                if "●" in txt:
                    parts = [clean(p) for p in txt.split("●") if clean(p)]
                    if parts:
                        return parts
        # Heading matched but no usable list in its section — stop searching
        # to avoid leaking unrelated lists from other sections.
        break
    return []


def extract_faqs(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """
    FAQ blocks on astrosage are inconsistent; we look for either:
      - <details><summary>Q</summary>A</details>
      - alternating h3 (ending '?') + p siblings
    """
    out: list[tuple[str, str]] = []
    root = main_content(soup)
    for det in root.find_all("details"):
        s = det.find("summary")
        if not s:
            continue
        q = clean(s.get_text(" ", strip=True))
        det_copy_text = clean(det.get_text(" ", strip=True))
        a = det_copy_text[len(q):].strip()
        if q and a:
            out.append((q, a))
    if out:
        return out
    for h in root.find_all(["h3", "h4"]):
        q = clean(h.get_text(" ", strip=True))
        if not q.endswith("?"):
            continue
        nxt = h.find_next("p")
        if nxt:
            a = clean(nxt.get_text(" ", strip=True))
            if a:
                out.append((q, a))
    return out


def extract_internal_links(soup: BeautifulSoup, base_url: str, path_prefix: str) -> list[str]:
    """
    Return absolute astrosage URLs whose path starts with `path_prefix`
    (e.g. '/festival/' or '/muhurat/'), de-duplicated, in document order.
    """
    base = urlparse(base_url)
    seen: set[str] = set()
    out: list[str] = []
    for a in main_content(soup).find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:"):
            continue
        absu = urljoin(base_url, href)
        u = urlparse(absu)
        if u.hostname != base.hostname:
            continue
        if not u.path.startswith(path_prefix):
            continue
        # Drop query string and fragment for canonical comparison
        canonical = f"{u.scheme}://{u.hostname}{u.path}"
        if canonical in seen:
            continue
        seen.add(canonical)
        out.append(canonical)
    return out


def child_festival_slugs(soup: BeautifulSoup, parent_slug_path: str) -> list[str]:
    """
    From a festival_top page (e.g. /festival/diwali), return slug_paths of
    direct children, i.e. links whose path == '/festival/{parent}/<something>'.
    """
    out: list[str] = []
    seen: set[str] = set()
    prefix = f"/festival/{parent_slug_path}/"
    for a in main_content(soup).find_all("a", href=True):
        href = a["href"].strip()
        if not href.startswith(prefix) and not href.startswith(f"https://panchang.astrosage.com{prefix}"):
            continue
        path = urlparse(href).path
        # Slug path relative to /festival/
        sub = path[len("/festival/"):].strip("/")
        if sub and sub not in seen:
            seen.add(sub)
            out.append(sub)
    return out
