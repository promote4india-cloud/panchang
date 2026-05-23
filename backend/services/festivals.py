"""
Festival rules engine.

Each festival is stored as a *rule* (in `festivals.rule_type` + `rule_json`),
NOT as a list of dates. The catalog stays tiny and any future year resolves
on demand.

Supported rule types (matches implementation.md §5):

  tithi              { paksha?, tithi }                       -- every occurrence in year
  tithi_in_paksha    { paksha, tithi }                        -- alias of tithi w/ paksha required
  tithi_in_masa      { masa, paksha, tithi }                  -- once a year exact (Purnimanta naming)
  tithi_in_amanta_masa{ masa, paksha, tithi }                 -- Rath Yatra-class (Amanta naming)
  tithi_in_adhik_masa{ paksha, tithi }                        -- Padmini / Parama (adhik years only)
  tithi_at_nishitha  { paksha, tithi, masa? }                 -- Shivratri-class: tithi at midnight
  tithi_at_madhyahna { paksha, tithi, masa? }                 -- Ganesh Chaturthi-class: tithi at midday
  tithi_at_pradosha  { paksha, tithi, masa? }                 -- Diwali-class: tithi at sunset
  tithi_at_moonrise  { paksha, tithi, masa? }                 -- Sankashti / Karva Chauth: tithi at moonrise
  nakshatra_in_masa  { masa, nakshatra }                      -- e.g. Onam (Thiruvonam)
  solar_event        { event: "mesha_sankranti"|"makar_..." } -- sun sign ingress
  gregorian          { month, day }                           -- fixed civil date
  manual             { dates: ["2026-11-08", ...] }           -- escape hatch

Performance design
------------------
The naive approach (each rule scans 365 days, each probe runs full Swiss
Ephemeris calcs) costs O(rules × days) heavy compute calls — minutes for
the full catalog. Instead we build ONE snapshot per (year, lat, lon, tz)
listing the tithi/paksha/masa/nakshatra/sun-rashi at each day's reference
moment, then every rule matches against the snapshot in O(1) per day.

The snapshot is memoized via services.cache.ttl_cache so subsequent calls
are instant.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date as Date, datetime, timedelta
from typing import Iterable
from zoneinfo import ZoneInfo

from .cache import ttl_cache
from .db import connect_ro
from .panchang import (
    MASA_NAMES,
    NAKSHATRA_NAMES,
    TITHI_NAMES,
    compute_nakshatra,
    compute_tithi,
    sun_longitude,
    to_julian_day,
)

# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

# Names of tithis 1..15 (same names used in both pakshas). Krishna Amavasya
# is named "Amavasya" instead of "Purnima"; we treat tithi 15 in either
# paksha as "the final tithi of that fortnight".
_TITHI_INDEX = {name.lower(): i + 1 for i, name in enumerate(TITHI_NAMES[:15])}
_TITHI_INDEX["amavasya"] = 15
_TITHI_INDEX["purnima"] = 15
_NAKSHATRA_INDEX = {name.lower(): i + 1 for i, name in enumerate(NAKSHATRA_NAMES)}
_MASA_INDEX = {name.lower(): i + 1 for i, name in enumerate(MASA_NAMES)}

# Common aliases
_NAKSHATRA_INDEX["sravana"] = _NAKSHATRA_INDEX["shravana"]
_MASA_INDEX["ashwina"] = _MASA_INDEX["ashwin"]
_MASA_INDEX["kartik"] = _MASA_INDEX["kartika"]
_MASA_INDEX["pausha"] = _MASA_INDEX["paush"]
_MASA_INDEX["margasirsha"] = _MASA_INDEX["margashirsha"]

_SOLAR_EVENT_RASHI = {
    "mesha_sankranti": 0,       # ~Apr 14 — Baisakhi / Vishu / Pohela Boishakh
    "vrishabha_sankranti": 1,
    "mithuna_sankranti": 2,
    "karka_sankranti": 3,       # Dakshinayana begins
    "simha_sankranti": 4,
    "kanya_sankranti": 5,
    "tula_sankranti": 6,
    "vrishchika_sankranti": 7,
    "dhanu_sankranti": 8,
    "makar_sankranti": 9,       # ~Jan 14 — Pongal / Uttarayan / Lohri (eve)
    "kumbha_sankranti": 10,
    "meena_sankranti": 11,
}


# ---------------------------------------------------------------------------
# Per-day snapshot
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class _DaySnap:
    date: Date
    tithi_idx: int          # 1..30
    tithi_in_paksha: int    # 1..15
    paksha: str             # 'Shukla' | 'Krishna'
    masa_idx: int           # 1..12 (Chaitra=1 .. Phalguna=12) — PURNIMANTA naming
    nakshatra_idx: int      # 1..27
    sun_rashi_idx: int      # 0..11
    # AMANTA masa: lunar month named by the rashi the sun is in at the
    # *preceding* amavasya. Used by Shukla-paksha festivals whose date
    # convention follows the Amanta (south/east Indian) calendar — e.g.
    # Jagannath Rath Yatra (Ashadha Shukla 2). Differs from `masa_idx`
    # for Shukla pakshas around solar-rashi boundaries.
    masa_idx_amanta: int = 0
    is_adhik: bool = False  # True for days inside an Adhik (Purushottam) Masa
    # Tithi prevailing at NISHITHA KALA (midnight) of the night that follows
    # this day's sunrise — i.e. ~00:00 IST of (date + 1). Shivratri-class
    # festivals are observed on the day whose night carries the target tithi.
    nishitha_tithi_in_paksha: int = 0
    nishitha_paksha: str = ""
    # Tithi at MADHYAHNA (midday, ~12:00 local). Used by Ganesh Chaturthi.
    madhyahna_tithi_in_paksha: int = 0
    madhyahna_paksha: str = ""
    # Tithi at PRADOSHA (just after sunset, ~18:00 local). Used by Diwali
    # Lakshmi Puja, Dhanteras and Pradosha vrats.
    pradosha_tithi_in_paksha: int = 0
    pradosha_paksha: str = ""
    # Tithi at MOONRISE proxy (~21:00 local). Used by Sankashti Chaturthi
    # and Karva Chauth which are decided by chaturthi at moonrise.
    moonrise_tithi_in_paksha: int = 0
    moonrise_paksha: str = ""


def _ref_jd(d: Date, tz: ZoneInfo) -> float:
    """Reference moment for a civil date: ~6 AM local (sunrise proxy)."""
    return to_julian_day(
        datetime.combine(d, datetime.min.time(), tzinfo=tz) + timedelta(hours=6)
    )


@ttl_cache(maxsize=64, ttl_seconds=24 * 3600)
def _year_snapshot(year: int, lat_q: float, lon_q: float, tz_name: str) -> list[_DaySnap]:
    """
    Build day-by-day panchang snapshot for the whole calendar year.
    ~365 light-weight Swiss Ephemeris probes. Cached per (year, location, tz).

    The masa column uses the Purnimanta convention: every day is labeled with
    the name of the lunar month it belongs to, where a lunar month X ends on
    Purnima X. Concretely: masa(day) = (sun_rashi_at_next_purnima + 1) % 12.
    This is what drikpanchang and most North-Indian almanacs publish, and is
    what services/festival_rules_seed.py was written against.

    lat/lon are accepted but unused inside the calc (festival rules don't
    need sunrise-precise resolution); they remain part of the cache key.
    """
    _ = (lat_q, lon_q)
    tz = ZoneInfo(tz_name)
    snaps: list[_DaySnap] = []
    d = Date(year, 1, 1)
    end = Date(year, 12, 31)
    # Pad scan to capture purnimas just past Dec 31 / before Jan 1 so the
    # purnima-anchored masa works at year edges.
    pad = timedelta(days=20)
    scan_start = d - pad
    scan_end = end + pad

    utc = ZoneInfo("UTC")
    raw: list[tuple[Date, int, int, str, int, int, int, str, int, str, int, str, int, str]] = []
    # (date, tithi_idx, tithi_in_paksha, paksha, nakshatra_idx, sun_rashi_idx,
    #  nishitha_tip, nishitha_paksha, madhyahna_tip, madhyahna_paksha,
    #  pradosha_tip, pradosha_paksha, moonrise_tip, moonrise_paksha)

    def _probe(d: Date, hours: float) -> tuple[int, str]:
        jd = to_julian_day(
            datetime.combine(d, datetime.min.time(), tzinfo=tz) + timedelta(hours=hours)
        )
        tt = compute_tithi(jd, utc)
        return (tt.index if tt.index <= 15 else tt.index - 15, tt.paksha)

    cur = scan_start
    while cur <= scan_end:
        jd = _ref_jd(cur, tz)
        t = compute_tithi(jd, utc)
        tip = t.index if t.index <= 15 else t.index - 15
        n = compute_nakshatra(jd, utc)
        rashi = int(sun_longitude(jd) // 30)
        # Kala probes — each picks the tithi prevailing at a specific moment
        # of the Hindu day. Local-clock times are good enough proxies for the
        # canonical kalas at Indian latitudes year-round.
        n_tip, n_p = _probe(cur + timedelta(days=1), 0.0)   # nishitha ≈ midnight
        m_tip, m_p = _probe(cur, 12.0)                       # madhyahna ≈ 12:00
        p_tip, p_p = _probe(cur, 18.0)                       # pradosha  ≈ 18:00
        mr_tip, mr_p = _probe(cur, 21.0)                     # moonrise  ≈ 21:00
        raw.append((
            cur, t.index, tip, t.paksha, n.index, rashi,
            n_tip, n_p, m_tip, m_p, p_tip, p_p, mr_tip, mr_p,
        ))
        cur += timedelta(days=1)

    # Purnima detection + masa naming (sun_rashi at purnima + 1, mod 12).
    purnima_pos: list[int] = []
    purnima_masa: dict[int, int] = {}  # index → masa_idx (1..12)
    for i, row in enumerate(raw):
        _d, _ti, tip_i, paksha_i, _ni, rashi_i = row[:6]
        if paksha_i == "Shukla" and tip_i == 15:
            # Dedupe: if a purnima crosses two adjacent days, keep the later
            if purnima_pos and i - purnima_pos[-1] <= 1:
                purnima_pos[-1] = i
                purnima_masa.pop(purnima_pos[-1], None)
            else:
                purnima_pos.append(i)
            purnima_masa[i] = (rashi_i + 1) % 12 + 1  # 1..12

    def _masa_for(i: int) -> int:
        # Find the next purnima index ≥ i.
        for pi in purnima_pos:
            if pi >= i:
                return purnima_masa[pi]
        # Past the last purnima we tracked — roll forward by one month name.
        if purnima_pos:
            last = purnima_masa[purnima_pos[-1]]
            return last % 12 + 1
        return 1  # degenerate fallback

    # Adhik Masa (Purushottam Masa) detection — Amanta criterion:
    #   A lunar cycle (amavasya → next amavasya) that contains NO solar
    #   sankranti is adhik. In our snapshot this is equivalent to: two
    #   CONSECUTIVE amavasyas falling with the sun in the same rashi.
    #   By convention the cycle BETWEEN them is the adhik month, named after
    #   the upcoming (Nij) month. Days from (first_amavasya + 1) through the
    #   second amavasya inclusive belong to that adhik cycle.
    #
    #   We use the Amanta criterion because all major almanacs (Drik,
    #   AstroSage, Mahalakshmi, Kalnirnay) label adhik-month observances
    #   (Padmini, Parama Ekadashi) by it — even those that otherwise display
    #   a Purnimanta calendar.
    amavasya_pos: list[int] = []
    amavasya_rashi: dict[int, int] = {}
    for i, row in enumerate(raw):
        _d, _ti, tip_i, paksha_i, _ni, rashi_i = row[:6]
        if paksha_i == "Krishna" and tip_i == 15:
            if amavasya_pos and i - amavasya_pos[-1] <= 1:
                old = amavasya_pos[-1]
                amavasya_pos[-1] = i
                amavasya_rashi.pop(old, None)
            else:
                amavasya_pos.append(i)
            amavasya_rashi[i] = rashi_i

    adhik_ranges: list[tuple[int, int]] = []
    for j in range(1, len(amavasya_pos)):
        a_prev, a_curr = amavasya_pos[j - 1], amavasya_pos[j]
        if amavasya_rashi[a_prev] == amavasya_rashi[a_curr]:
            adhik_ranges.append((a_prev + 1, a_curr))

    def _is_adhik(i: int) -> bool:
        for a, b in adhik_ranges:
            if a <= i <= b:
                return True
        return False

    # Adhik-masa shift propagation:
    #   When an adhik cycle is inserted, the NEXT lunar cycle re-uses the
    #   adhik's name (e.g. Nij Jyeshtha follows Adhik Jyeshtha), so every
    #   subsequent masa-name shifts back by one. We apply this by decrementing
    #   purnima_masa for every purnima past the end of each adhik range.
    if adhik_ranges:
        adhik_end_positions = sorted(end for _, end in adhik_ranges)
        for pi in purnima_pos:
            shift = sum(1 for end in adhik_end_positions if pi > end)
            if shift:
                purnima_masa[pi] = ((purnima_masa[pi] - 1 - shift) % 12) + 1

    # Amanta masa naming: day i belongs to the lunar cycle starting at the
    # most recent amavasya ≤ i. The cycle's name is derived from the sun's
    # rashi at that amavasya: masa = (rashi + 1) % 12 + 1. Used for Shukla-
    # paksha festivals whose canonical date convention is Amanta (e.g.
    # Jagannath Rath Yatra). For non-adhik years this is exact; adhik years
    # produce a name duplicate (handled per-festival via tithi_in_adhik_masa).
    def _amanta_masa_for(i: int) -> int:
        latest_av = -1
        latest_rashi = 0
        for ai in amavasya_pos:
            if ai <= i:
                latest_av = ai
                latest_rashi = amavasya_rashi[ai]
            else:
                break
        if latest_av < 0:
            # Before the first amavasya we tracked — back-compute by stepping
            # the first amavasya's name one month back.
            if amavasya_pos:
                first_rashi = amavasya_rashi[amavasya_pos[0]]
                return ((first_rashi - 1) % 12) % 12 + 1
            return 1
        return (latest_rashi + 1) % 12 + 1

    # Emit snapshots for Jan 1..Dec 31 only.
    for i, row in enumerate(raw):
        (date_i, ti, tip_i, paksha_i, n_idx, rashi_i,
         n_tip, n_p, m_tip, m_p, p_tip, p_p, mr_tip, mr_p) = row
        if date_i.year != year:
            continue
        snaps.append(
            _DaySnap(
                date=date_i,
                tithi_idx=ti,
                tithi_in_paksha=tip_i,
                paksha=paksha_i,
                masa_idx=_masa_for(i),
                masa_idx_amanta=_amanta_masa_for(i),
                nakshatra_idx=n_idx,
                sun_rashi_idx=rashi_i,
                is_adhik=_is_adhik(i),
                nishitha_tithi_in_paksha=n_tip,
                nishitha_paksha=n_p,
                madhyahna_tithi_in_paksha=m_tip,
                madhyahna_paksha=m_p,
                pradosha_tithi_in_paksha=p_tip,
                pradosha_paksha=p_p,
                moonrise_tithi_in_paksha=mr_tip,
                moonrise_paksha=mr_p,
            )
        )
    return snaps


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

def _masa_of(rule: dict, key: str = "masa") -> int:
    v = rule[key]
    return _MASA_INDEX[v.lower()] if isinstance(v, str) else int(v)


def _nakshatra_of(rule: dict, key: str = "nakshatra") -> int:
    v = rule[key]
    return _NAKSHATRA_INDEX[v.lower()] if isinstance(v, str) else int(v)


def _tithi_of(rule: dict, key: str = "tithi") -> int:
    v = rule[key]
    return _TITHI_INDEX[v.lower()] if isinstance(v, str) else int(v)


def _match_day(rule_type: str, rule: dict, snap: _DaySnap) -> bool:
    if rule_type in ("tithi", "tithi_in_paksha"):
        if snap.tithi_in_paksha != _tithi_of(rule):
            return False
        want_paksha = rule.get("paksha")
        if want_paksha and snap.paksha.lower() != want_paksha.lower():
            return False
        return True
    if rule_type == "tithi_in_masa":
        # Skip days inside an Adhik Masa — those belong to Padmini / Parama
        # (tithi_in_adhik_masa) and must NOT trigger the regular masa rule.
        if snap.is_adhik:
            return False
        return (
            snap.masa_idx == _masa_of(rule)
            and snap.tithi_in_paksha == _tithi_of(rule)
            and snap.paksha.lower() == rule["paksha"].lower()
        )
    if rule_type == "tithi_in_amanta_masa":
        # Amanta-named masa (used by Jagannath Rath Yatra etc.).
        if snap.is_adhik:
            return False
        return (
            snap.masa_idx_amanta == _masa_of(rule)
            and snap.tithi_in_paksha == _tithi_of(rule)
            and snap.paksha.lower() == rule["paksha"].lower()
        )
    if rule_type == "tithi_in_adhik_masa":
        return (
            snap.is_adhik
            and snap.tithi_in_paksha == _tithi_of(rule)
            and snap.paksha.lower() == rule["paksha"].lower()
        )
    if rule_type == "tithi_at_nishitha":
        # Match the tithi prevailing at midnight of the night that belongs
        # to this Hindu day. Used by Shivratri-class festivals. Optional
        # `masa` narrows the match to a single lunar month (Mahashivratri).
        if snap.nishitha_tithi_in_paksha != _tithi_of(rule):
            return False
        want_paksha = rule.get("paksha")
        if want_paksha and snap.nishitha_paksha.lower() != want_paksha.lower():
            return False
        if "masa" in rule:
            if snap.is_adhik or snap.masa_idx != _masa_of(rule):
                return False
        return True
    if rule_type in ("tithi_at_madhyahna", "tithi_at_pradosha", "tithi_at_moonrise"):
        # Generic kala-anchored tithi match. Optional `masa` narrows scope.
        tip_attr, paksha_attr = {
            "tithi_at_madhyahna": ("madhyahna_tithi_in_paksha", "madhyahna_paksha"),
            "tithi_at_pradosha":  ("pradosha_tithi_in_paksha",  "pradosha_paksha"),
            "tithi_at_moonrise":  ("moonrise_tithi_in_paksha",  "moonrise_paksha"),
        }[rule_type]
        if getattr(snap, tip_attr) != _tithi_of(rule):
            return False
        want_paksha = rule.get("paksha")
        if want_paksha and getattr(snap, paksha_attr).lower() != want_paksha.lower():
            return False
        if "masa" in rule:
            if snap.is_adhik or snap.masa_idx != _masa_of(rule):
                return False
        return True
    if rule_type == "nakshatra_in_masa":
        return (
            snap.masa_idx == _masa_of(rule)
            and snap.nakshatra_idx == _nakshatra_of(rule)
        )
    return False


def _resolve_against_snapshot(
    rule_type: str, rule: dict, snaps: list[_DaySnap], year: int
) -> list[Date]:
    if rule_type == "gregorian":
        try:
            return [Date(year, int(rule["month"]), int(rule["day"]))]
        except ValueError:
            return []
    if rule_type == "manual":
        out: list[Date] = []
        for s in rule.get("dates", []):
            try:
                d = Date.fromisoformat(s)
            except ValueError:
                continue
            if d.year == year:
                out.append(d)
        return out
    if rule_type == "solar_event":
        target = _SOLAR_EVENT_RASHI.get(rule.get("event", ""))
        if target is None:
            return []
        out2: list[Date] = []
        prev = snaps[0].sun_rashi_idx if snaps else None
        for snap in snaps[1:]:
            if snap.sun_rashi_idx != prev and snap.sun_rashi_idx == target:
                out2.append(snap.date)
            prev = snap.sun_rashi_idx
        return out2
    matched = [s.date for s in snaps if _match_day(rule_type, rule, s)]
    # Dedupe runs of consecutive days into a single observance (keep the last
    # day — Vedic convention: the day on which the tithi is current at the
    # relevant observance moment, which for ekadashi/chaturthi/sankashti is
    # typically the later of two adjacent 6-AM probes).
    deduped: list[Date] = []
    for d in matched:
        if deduped and (d - deduped[-1]).days == 1:
            deduped[-1] = d
        else:
            deduped.append(d)
    return deduped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_dates(
    rule_type: str,
    rule_json: str | dict,
    year: int,
    lat: float = 28.6139,
    lon: float = 77.2090,
    tz: str = "Asia/Kolkata",
) -> list[Date]:
    """Return all civil dates in `year` matching the festival rule."""
    rule = json.loads(rule_json) if isinstance(rule_json, str) else rule_json
    snaps = _year_snapshot(year, round(lat, 1), round(lon, 1), tz)
    return _resolve_against_snapshot(rule_type, rule, snaps, year)


@dataclass
class FestivalOccurrence:
    festival_id: str
    slug_path: str
    date: Date
    name: str
    type: str | None
    auspiciousness: str | None


def festivals_in_range(
    start: Date,
    end: Date,
    language: str = "en",
    lat: float = 28.6139,
    lon: float = 77.2090,
    tz: str = "Asia/Kolkata",
) -> list[FestivalOccurrence]:
    """
    Enumerate festival occurrences within [start, end] by:
      1) building (or reusing cached) panchang snapshots for each affected year,
      2) walking the catalog and matching each rule against the snapshot,
      3) filtering to the requested date window.
    """
    conn = connect_ro()
    try:
        rows = conn.execute(
            """
            SELECT f.id, f.slug_path, f.rule_type, f.rule_json, f.type, f.auspiciousness,
                   COALESCE(c.name, f.id) AS name
              FROM festivals f
              LEFT JOIN festival_content c
                ON c.festival_id = f.id AND c.language = ?
             WHERE f.rule_type IS NOT NULL
            """,
            (language,),
        ).fetchall()
    finally:
        conn.close()

    lat_q, lon_q = round(lat, 1), round(lon, 1)
    snapshots: dict[int, list[_DaySnap]] = {
        y: _year_snapshot(y, lat_q, lon_q, tz)
        for y in range(start.year, end.year + 1)
    }

    out: list[FestivalOccurrence] = []
    for r in rows:
        try:
            rule = json.loads(r["rule_json"]) if r["rule_json"] else {}
        except json.JSONDecodeError:
            continue
        for year, snaps in snapshots.items():
            for d in _resolve_against_snapshot(r["rule_type"], rule, snaps, year):
                if start <= d <= end:
                    out.append(FestivalOccurrence(
                        festival_id=r["id"],
                        slug_path=r["slug_path"],
                        date=d,
                        name=r["name"],
                        type=r["type"],
                        auspiciousness=r["auspiciousness"],
                    ))
    out.sort(key=lambda o: (o.date, o.festival_id))
    return out
