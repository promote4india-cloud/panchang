"""
Festival rules engine.

Each festival is stored as a *rule* (in `festivals.rule_type` + `rule_json`),
NOT as a list of dates. The catalog stays tiny and any future year resolves
on demand.

Supported rule types (matches implementation.md §5):

  tithi              { paksha?, tithi, pin?, dedup? }              -- every occurrence in year
  tithi_in_paksha    { paksha, tithi, pin?, dedup? }               -- alias of tithi w/ paksha required
  tithi_in_masa      { masa, paksha, tithi, pin?, dedup? }         -- once a year exact (Purnimanta naming)
  tithi_in_amanta_masa{ masa, paksha, tithi, pin?, dedup? }        -- Rath Yatra-class (Amanta naming)
  multi_tradition    { observances: [{tradition, rule_type, rule}] } -- wrap N sub-rules; emit per-tradition tagged occurrences
  tithi_in_adhik_masa{ paksha, tithi }                        -- Padmini / Parama (adhik years only)
  tithi_at_nishitha  { paksha, tithi, masa? }                 -- Shivratri-class: tithi at midnight
  tithi_at_madhyahna { paksha, tithi, masa? }                 -- Ganesh Chaturthi-class: tithi at midday
  tithi_at_pradosha  { paksha, tithi, masa? }                 -- Diwali-class: tithi at sunset
  tithi_at_moonrise  { paksha, tithi, masa? }                 -- Sankashti / Karva Chauth: tithi at moonrise
  nakshatra_in_masa  { masa, nakshatra }                      -- e.g. Onam (Thiruvonam)
  solar_event        { event: "mesha_sankranti"|"makar_..." } -- sun sign ingress
  gregorian          { month, day }                           -- fixed civil date
  manual             { dates: ["2026-11-08", ...] }           -- escape hatch

Optional fields on tithi-class rules:
  pin   : reference moment for the tithi probe. One of
          "sunrise" (default), "madhyahna", "aparahna" (alias of madhyahna),
          "pradosha", "moonrise", "nishitha". Used by festivals whose
          canonical observance day is decided by which day's *kala* the
          tithi occupies. Example: Nag Panchami uses aparahna-vyapini.
  dedup : tie-breaker when the (pinned) tithi touches the reference moment
          on two consecutive days (vriddhi). "last" (default) keeps the
          later day; "first" keeps the earlier. Some festivals (Nag Panchami,
          Akshaya Tritiya) prefer the first day.
  avoid_bhadra : when true, after resolving the date, if Bhadra (Vishti
          karana, index 7) is active at the rule's pin moment, the
          observance is pushed to the NEXT day. Used by Raksha Bandhan
          and Holika Dahan -- both forbid performing the rite during Bhadra.

Kshaya (lost) and vriddhi (gained) tithis are handled automatically:
  * Vriddhi: tithi touches the pinned moment on two consecutive days; the
    matcher emits both and `dedup` picks one.
  * Kshaya: tithi does not touch the pinned moment on any day (it begins
    and ends between two adjacent probes). The matcher detects this from
    the (current, next) tithi-at-probe pair and emits the single day that
    fully contains the kshaya tithi.

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
    compute_karana,
    MASA_NAMES,
    NAKSHATRA_NAMES,
    TITHI_NAMES,
    compute_nakshatra,
    compute_tithi,
    sun_longitude,
    to_julian_day,
)
import swisseph as swe
from .panchang import _rise_or_set  # type: ignore[attr-defined]

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
    # Tithi at the NEXT day's sunrise (i.e. compute_tithi at sunrise(D+1)).
    # Stored as the global 1..30 index plus the paksha string so the matcher
    # can detect kshaya tithis: a (paksha, tithi) that is entirely contained
    # between this day's sunrise and the next, never touching either probe.
    next_tithi_idx: int = 0
    next_paksha: str = ""
    next_tithi_in_paksha: int = 0
    # Karana (half-tithi) at each pin moment. Karana 7 = Vishti = "Bhadra",
    # an inauspicious half-tithi during which Raksha Bandhan and Holika
    # Dahan must not be performed -- the `avoid_bhadra` rule field uses
    # these to push observance to the next day when Bhadra is active.
    karana_at_sunrise: int = 0
    karana_at_madhyahna: int = 0
    karana_at_aparahna: int = 0
    karana_at_pradosha: int = 0
    karana_at_nishitha: int = 0


def _ref_jd(d: Date, tz: ZoneInfo) -> float:
    """Reference moment for a civil date: ~6 AM local (sunrise proxy)."""
    return to_julian_day(
        datetime.combine(d, datetime.min.time(), tzinfo=tz) + timedelta(hours=6)
    )


@ttl_cache(maxsize=64, ttl_seconds=24 * 3600)
def _year_snapshot(year: int, lat_q: float, lon_q: float, tz_name: str) -> list[_DaySnap]:
    """
    Build day-by-day panchang snapshot for the whole calendar year.
    ~365 light-weight Swiss Ephemeris probes per kala, cached per
    (year, location, tz). Location matters because we sample sunset (for
    pradosha) and moonrise via Swiss Ephemeris rise/set, which depend on
    geographic latitude/longitude.

    The masa column uses the Purnimanta convention: every day is labeled with
    the name of the lunar month it belongs to, where a lunar month X ends on
    Purnima X. Concretely: masa(day) = (sun_rashi_at_next_purnima + 1) % 12 + 1.
    This is what drikpanchang and most North-Indian almanacs publish, and is
    what services/festival_rules_seed.py was written against.
    """
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
    raw: list[dict] = []

    def _probe_at_jd(jd: float) -> tuple[int, str]:
        tt = compute_tithi(jd, utc)
        return (tt.index if tt.index <= 15 else tt.index - 15, tt.paksha)

    def _karana_at(jd: float) -> int:
        try:
            return compute_karana(jd, utc).index
        except Exception:
            return 0

    def _probe(d: Date, hours: float) -> tuple[int, str]:
        jd = to_julian_day(
            datetime.combine(d, datetime.min.time(), tzinfo=tz) + timedelta(hours=hours)
        )
        return _probe_at_jd(jd)

    cur = scan_start
    while cur <= scan_end:
        jd_midnight = to_julian_day(
            datetime.combine(cur, datetime.min.time(), tzinfo=tz)
        )
        # Real sunrise/sunset/moonrise via Swiss Ephemeris. All pins
        # (sunrise reference, madhyahna, aparahna, pradosha, nishitha) are
        # derived from the actual rise/set instants, not fixed clock-hour
        # proxies. Pradosha kala spans the first three muhurtas (~2h 24m)
        # after sunset; we probe ~45 min in, which falls inside the first
        # muhurta and matches Drik's "pradosha-vyapini" rule.
        sunrise_jd = _rise_or_set(jd_midnight, swe.SUN, lon_q, lat_q, "rise")
        sunset_jd = _rise_or_set(jd_midnight, swe.SUN, lon_q, lat_q, "set")
        next_sunrise_jd = _rise_or_set(jd_midnight + 1.0, swe.SUN, lon_q, lat_q, "rise")
        moonrise_jd = _rise_or_set(jd_midnight, swe.MOON, lon_q, lat_q, "rise")
        # Sunrise reference (used for tithi/nakshatra/rashi of the civil day).
        # Real sunrise; falls back to 06:00 local if Swiss rise fails (polar).
        if sunrise_jd is None:
            jd = _ref_jd(cur, tz)
        else:
            jd = sunrise_jd
        t = compute_tithi(jd, utc)
        tip = t.index if t.index <= 15 else t.index - 15
        n = compute_nakshatra(jd, utc)
        rashi = int(sun_longitude(jd) // 30)
        # Fallback to fixed-hour proxies if rise/set fails (polar / extreme).
        if sunset_jd is None:
            pradosha_jd = to_julian_day(
                datetime.combine(cur, datetime.min.time(), tzinfo=tz) + timedelta(hours=18.75)
            )
        else:
            pradosha_jd = sunset_jd + (45.0 / (24.0 * 60.0))  # +45 min in JD
        if sunset_jd is not None and next_sunrise_jd is not None:
            nishitha_jd = (sunset_jd + next_sunrise_jd) / 2.0
        else:
            nishitha_jd = to_julian_day(
                datetime.combine(cur + timedelta(days=1), datetime.min.time(), tzinfo=tz)
            )
        if moonrise_jd is None:
            mr_jd = to_julian_day(
                datetime.combine(cur, datetime.min.time(), tzinfo=tz) + timedelta(hours=21.0)
            )
        else:
            mr_jd = moonrise_jd
        # Madhyahna = true solar midday = midpoint of sunrise..sunset.
        # Aparahna kala = 4th of 5 equal parts of dinamana (day length);
        # by convention probe at sunrise + 0.6 * dinamana, the start of
        # the aparahna part. Falls back to 12:00 / 15:00 local if rise/set
        # unavailable.
        if sunrise_jd is not None and sunset_jd is not None:
            dinamana = sunset_jd - sunrise_jd
            madhyahna_jd = sunrise_jd + dinamana / 2.0
            aparahna_jd = sunrise_jd + dinamana * 0.6
        else:
            madhyahna_jd = to_julian_day(
                datetime.combine(cur, datetime.min.time(), tzinfo=tz) + timedelta(hours=12.0)
            )
            aparahna_jd = to_julian_day(
                datetime.combine(cur, datetime.min.time(), tzinfo=tz) + timedelta(hours=15.0)
            )

        n_tip, n_p = _probe_at_jd(nishitha_jd)
        m_tip, m_p = _probe_at_jd(madhyahna_jd)
        p_tip, p_p = _probe_at_jd(pradosha_jd)
        mr_tip, mr_p = _probe_at_jd(mr_jd)
        # Karana at each pin (used by `avoid_bhadra`).
        k_sunrise = _karana_at(jd)
        k_madhyahna = _karana_at(madhyahna_jd)
        k_aparahna = _karana_at(aparahna_jd)
        k_pradosha = _karana_at(pradosha_jd)
        k_nishitha = _karana_at(nishitha_jd)
        raw.append({
            "date": cur, "ti": t.index, "tip": tip, "paksha": t.paksha,
            "n_idx": n.index, "rashi": rashi,
            "n_tip": n_tip, "n_p": n_p,
            "m_tip": m_tip, "m_p": m_p,
            "p_tip": p_tip, "p_p": p_p,
            "mr_tip": mr_tip, "mr_p": mr_p,
            "k_sunrise": k_sunrise, "k_madhyahna": k_madhyahna,
            "k_aparahna": k_aparahna,
            "k_pradosha": k_pradosha, "k_nishitha": k_nishitha,
        })
        cur += timedelta(days=1)

    # Purnima detection. The MASA NAME is assigned later (after amavasya
    # detection) because Drik names a Purnima by the *previous* Amavasya's
    # sun-rashi — i.e. the Amanta-month convention — which agrees with the
    # naive "sun-rashi-at-purnima + 1" rule MOST years but diverges when a
    # purnima precedes its expected Sankranti (e.g. 2025 Ashwin Purnima
    # Oct 6: sun still in Kanya, but Drik calls it Ashwin Purnima because
    # the prior Amavasya — Sep 21 — also has sun in Kanya which gives
    # Ashwin under the amanta rule).
    purnima_pos: list[int] = []
    for i, row in enumerate(raw):
        tip_i, paksha_i = row["tip"], row["paksha"]
        if paksha_i == "Shukla" and tip_i == 15:
            # Dedupe: if a purnima crosses two adjacent days, keep the later
            if purnima_pos and i - purnima_pos[-1] <= 1:
                purnima_pos[-1] = i
            else:
                purnima_pos.append(i)
        else:
            # Kshaya purnima: Shukla 14 → Krishna 1 with no Shukla 15
            # sample. Treat the earlier (Shukla 14) day as containing the
            # purnima moment, per the same Drik convention applied to
            # kshaya amavasya above.
            if (paksha_i == "Krishna" and tip_i == 1
                    and i > 0
                    and raw[i - 1]["paksha"] == "Shukla"
                    and raw[i - 1]["tip"] == 14
                    and (not purnima_pos or purnima_pos[-1] != i - 1)):
                purnima_pos.append(i - 1)
    purnima_masa: dict[int, int] = {}  # index → masa_idx (1..12), set below

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
        tip_i, paksha_i, rashi_i = row["tip"], row["paksha"], row["rashi"]
        if paksha_i == "Krishna" and tip_i == 15:
            if amavasya_pos and i - amavasya_pos[-1] <= 1:
                old = amavasya_pos[-1]
                amavasya_pos[-1] = i
                amavasya_rashi.pop(old, None)
            else:
                amavasya_pos.append(i)
            amavasya_rashi[i] = rashi_i
        else:
            # Kshaya amavasya detection: amavasya tithi can be so short it
            # never appears at any sunrise (Krishna 14 → Shukla 1 transition
            # without a Krishna 15 sample). In that case the amavasya
            # moment fell entirely between two consecutive sunrises; per
            # Drik convention the EARLIER day (the Krishna 14 sunrise day)
            # is treated as containing the amavasya. Example: 2025-02-28
            # India — sunrise tithi jumps from K-14 (Feb 27) to S-1 (Feb 28).
            if (paksha_i == "Shukla" and tip_i == 1
                    and i > 0
                    and raw[i - 1]["paksha"] == "Krishna"
                    and raw[i - 1]["tip"] == 14
                    and (not amavasya_pos or amavasya_pos[-1] != i - 1)):
                amavasya_pos.append(i - 1)
                amavasya_rashi[i - 1] = raw[i - 1]["rashi"]

    adhik_ranges: list[tuple[int, int]] = []
    for j in range(1, len(amavasya_pos)):
        a_prev, a_curr = amavasya_pos[j - 1], amavasya_pos[j]
        if amavasya_rashi[a_prev] == amavasya_rashi[a_curr]:
            adhik_ranges.append((a_prev + 1, a_curr))

    # Assign purnima_masa now that amavasya_rashi is known. Each Purnima is
    # named by the sun's rashi at the PREVIOUS Amavasya (amanta convention):
    #     masa = (prev_amavasya_rashi + 1) % 12 + 1   (1..12)
    # This matches Drik universally:
    #   • 2024 Apr 23 Chaitra Purnima (prev avs Apr 8 sun Meena 11 → 1)
    #   • 2024 Aug 19 Shravana Purnima (prev avs Aug 4 sun Karka 3 → 5)
    #   • 2024 Sep 18 Bhadrapada Purnima (prev avs Sep 2 sun Simha 4 → 6)
    #   • 2025 Oct 6 Ashwin Purnima (prev avs Sep 21 sun Kanya 5 → 7)
    # Degenerate fallback (no prior amavasya in scan window): use sun rashi
    # at the purnima itself + 1 (only triggers at scan edges, which we pad
    # by ±20 days so it should rarely matter).
    for pi in purnima_pos:
        prev_av_rashi = None
        for ai in amavasya_pos:
            if ai <= pi:
                prev_av_rashi = amavasya_rashi[ai]
            else:
                break
        if prev_av_rashi is None:
            purnima_masa[pi] = raw[pi]["rashi"] + 1
        else:
            purnima_masa[pi] = (prev_av_rashi + 1) % 12 + 1

    def _is_adhik(i: int) -> bool:
        for a, b in adhik_ranges:
            if a <= i <= b:
                return True
        return False

    # NOTE: no adhik shift propagation is needed for purnima_masa. Because
    # we name each Purnima from the PREVIOUS Amavasya's sun-rashi (amanta
    # rule), the masa name naturally REPEATS for the Adhik cycle and its
    # following Nij cycle (both prior amavasyas share the same rashi). The
    # subsequent cycles then resume the normal sequence on their own.

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
        date_i = row["date"]
        ti = row["ti"]; tip_i = row["tip"]; paksha_i = row["paksha"]
        n_idx = row["n_idx"]; rashi_i = row["rashi"]
        n_tip, n_p = row["n_tip"], row["n_p"]
        m_tip, m_p = row["m_tip"], row["m_p"]
        p_tip, p_p = row["p_tip"], row["p_p"]
        mr_tip, mr_p = row["mr_tip"], row["mr_p"]
        if date_i.year != year:
            continue
        # Next-sunrise tithi: lifts the kshaya/vriddhi state into the snap
        # itself. If we're at the very end of the scan window, fall back
        # to the current day's values (degenerate; should not occur because
        # we padded by ±20 days).
        if i + 1 < len(raw):
            nxt = raw[i + 1]
            next_ti = nxt["ti"]
            next_p = nxt["paksha"]
            next_tip = nxt["tip"]
        else:
            next_ti, next_p, next_tip = ti, paksha_i, tip_i
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
                next_tithi_idx=next_ti,
                next_paksha=next_p,
                next_tithi_in_paksha=next_tip,
                karana_at_sunrise=row["k_sunrise"],
                karana_at_madhyahna=row["k_madhyahna"],
                karana_at_aparahna=row["k_aparahna"],
                karana_at_pradosha=row["k_pradosha"],
                karana_at_nishitha=row["k_nishitha"],
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


# Map from `pin` rule field to (tip_attr_on_snap, paksha_attr_on_snap).
# "sunrise" is the default sampling moment used to build the snapshot;
# the other entries are kala-specific probes computed alongside it.
_PIN_FIELDS: dict[str, tuple[str, str]] = {
    "sunrise":   ("tithi_in_paksha",           "paksha"),
    "madhyahna": ("madhyahna_tithi_in_paksha", "madhyahna_paksha"),
    "aparahna":  ("madhyahna_tithi_in_paksha", "madhyahna_paksha"),  # alias
    "pradosha":  ("pradosha_tithi_in_paksha",  "pradosha_paksha"),
    "moonrise":  ("moonrise_tithi_in_paksha",  "moonrise_paksha"),
    "nishitha":  ("nishitha_tithi_in_paksha",  "nishitha_paksha"),
}

# Map from `pin` to (primary_karana_attr, secondary_karana_attr). The
# `avoid_bhadra` defer fires only when BOTH probes show Bhadra (Vishti,
# karana index 7), i.e. Bhadra extends well past the pin. This matches
# Drik convention of observing the rite later the same day if Bhadra
# ends quickly, and deferring to the next day only when Bhadra dominates
# the evening/night.
_PIN_KARANA_FIELD: dict[str, tuple[str, str]] = {
    "sunrise":   ("karana_at_sunrise",   "karana_at_madhyahna"),
    "madhyahna": ("karana_at_madhyahna", "karana_at_aparahna"),
    "aparahna":  ("karana_at_aparahna",  "karana_at_pradosha"),
    "pradosha":  ("karana_at_pradosha",  "karana_at_nishitha"),
    "nishitha":  ("karana_at_nishitha",  "karana_at_nishitha"),
    "moonrise":  ("karana_at_pradosha",  "karana_at_nishitha"),
}
BHADRA_KARANA_INDEX = 7  # Vishti


def _global_tithi(tip: int, paksha: str) -> int:
    """Convert (tithi_in_paksha 1..15, paksha) -> global 1..30 index.
    Shukla 1..15 -> 1..15; Krishna 1..15 -> 16..30 (Amavasya = 30).
    """
    return tip if paksha.lower() == "shukla" else tip + 15


def _kshaya_match(snap: _DaySnap, target_tip: int, want_paksha: str) -> bool:
    """Detect whether the (paksha, tithi) is a *kshaya* tithi consumed
    entirely within this Hindu day -- i.e. tithi_idx at sunrise(D) is
    one before the target and tithi_idx at sunrise(D+1) is one after.

    Returns True iff the target is the skipped tithi between (snap, next).
    Handles the 30->1 wrap at the end of the Krishna fortnight.
    """
    cur = snap.tithi_idx
    nxt = snap.next_tithi_idx
    if not cur or not nxt:
        return False
    diff = (nxt - cur) % 30
    if diff != 2:
        return False
    skipped_global = (cur % 30) + 1   # 1..30
    target_global = _global_tithi(target_tip, want_paksha)
    return skipped_global == target_global


def _match_day(rule_type: str, rule: dict, snap: _DaySnap) -> bool:
    if rule_type in ("tithi", "tithi_in_paksha"):
        pin = rule.get("pin", "sunrise")
        tip_attr, paksha_attr = _PIN_FIELDS.get(pin, _PIN_FIELDS["sunrise"])
        target_tip = _tithi_of(rule)
        want_paksha = rule.get("paksha", "")
        if getattr(snap, tip_attr) == target_tip:
            if not want_paksha or getattr(snap, paksha_attr).lower() == want_paksha.lower():
                return True
        # Kshaya fallback only meaningful for sunrise sampling; other kala
        # probes are 24h apart so a tithi missing them is genuinely absent
        # at that kala and should not be observed by this rule.
        if pin == "sunrise" and want_paksha and _kshaya_match(snap, target_tip, want_paksha):
            return True
        return False
    if rule_type == "tithi_in_masa":
        # Skip days inside an Adhik Masa by default -- those belong to
        # Padmini / Parama (tithi_in_adhik_masa) and must NOT trigger the
        # regular masa rule. Rules can opt into matching Adhik days as
        # well via `adhik_policy`:
        #   * "skip" (default): Nij only.
        #   * "both":           emit candidates from BOTH the Adhik and
        #                       Nij lunar cycles. Used by festivals such
        #                       as Chhath / Diwali cluster where Drik &
        #                       AstroSage disagree on which cycle hosts
        #                       the observance during adhik years.
        #   * "adhik_only":     match only Adhik days (Padmini/Parama).
        adhik_policy = rule.get("adhik_policy", "skip")
        if snap.is_adhik:
            if adhik_policy == "skip":
                return False
        else:
            if adhik_policy == "adhik_only":
                return False
        if snap.masa_idx != _masa_of(rule):
            return False
        pin = rule.get("pin", "sunrise")
        tip_attr, paksha_attr = _PIN_FIELDS.get(pin, _PIN_FIELDS["sunrise"])
        target_tip = _tithi_of(rule)
        want_paksha = rule["paksha"]
        if (
            getattr(snap, tip_attr) == target_tip
            and getattr(snap, paksha_attr).lower() == want_paksha.lower()
        ):
            return True
        if pin == "sunrise" and _kshaya_match(snap, target_tip, want_paksha):
            return True
        return False
    if rule_type == "tithi_in_amanta_masa":
        # Amanta-named masa (used by Jagannath Rath Yatra etc.).
        adhik_policy = rule.get("adhik_policy", "skip")
        if snap.is_adhik:
            if adhik_policy == "skip":
                return False
        else:
            if adhik_policy == "adhik_only":
                return False
        if snap.masa_idx_amanta != _masa_of(rule):
            return False
        pin = rule.get("pin", "sunrise")
        tip_attr, paksha_attr = _PIN_FIELDS.get(pin, _PIN_FIELDS["sunrise"])
        target_tip = _tithi_of(rule)
        want_paksha = rule["paksha"]
        if (
            getattr(snap, tip_attr) == target_tip
            and getattr(snap, paksha_attr).lower() == want_paksha.lower()
        ):
            return True
        if pin == "sunrise" and _kshaya_match(snap, target_tip, want_paksha):
            return True
        return False
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
            adhik_policy = rule.get("adhik_policy", "skip")
            if snap.is_adhik:
                if adhik_policy == "skip":
                    return False
            else:
                if adhik_policy == "adhik_only":
                    return False
            if snap.masa_idx != _masa_of(rule):
                return False
        return True
    if rule_type == "nakshatra_in_masa":
        return (
            snap.masa_idx == _masa_of(rule)
            and snap.nakshatra_idx == _nakshatra_of(rule)
        )
    return False


def _resolve_with_traditions(
    rule_type: str, rule: dict, snaps: list[_DaySnap], year: int,
    tz: str = "Asia/Kolkata",
) -> list[tuple[Date, str | None]]:
    """Resolve a rule into [(date, tradition_tag)].

    For `multi_tradition`, runs each child observance independently and
    tags emissions with the observance's `tradition` label. For every
    other rule type, returns dates with tag=None (tradition-agnostic).
    """
    if rule_type == "multi_tradition":
        out: list[tuple[Date, str | None]] = []
        for obs in rule.get("observances", []):
            sub_type = obs.get("rule_type")
            sub_rule = obs.get("rule", {})
            tag = obs.get("tradition")
            # Tradition may be a single string, a list, or a comma-separated
            # string. Emit one tagged occurrence per tag so callers can
            # filter by ANY of the individual labels (e.g. "smarta" matches
            # an observance tagged ["smarta", "purnimanta"]).
            if isinstance(tag, str) and "," in tag:
                tags = [t.strip() for t in tag.split(",") if t.strip()]
            elif isinstance(tag, (list, tuple)):
                tags = [str(t) for t in tag if t]
            else:
                tags = [tag] if tag else [None]
            for d in _resolve_against_snapshot(sub_type, sub_rule, snaps, year, tz):
                for t in tags:
                    out.append((d, t))
        return out
    return [(d, None) for d in _resolve_against_snapshot(rule_type, rule, snaps, year, tz)]


def _solar_ingress_datetime(
    target_rashi: int, day_after: Date, tz: str = "Asia/Kolkata",
) -> datetime:
    """Bisect sun_longitude to find the exact moment of ingress into the
    given sidereal rashi, given that the snapshot says the crossing
    happened between (day_after - 1) and day_after sunrise samples.
    Returns the local datetime of the crossing.
    """
    tzinfo = ZoneInfo(tz)
    target_lon = (target_rashi * 30.0) % 360.0
    lo_dt = datetime.combine(day_after - timedelta(days=1), datetime.min.time(), tzinfo=tzinfo)
    hi_dt = datetime.combine(day_after + timedelta(days=1), datetime.min.time(), tzinfo=tzinfo)
    lo, hi = to_julian_day(lo_dt), to_julian_day(hi_dt)

    def _signed(jd: float) -> float:
        return (sun_longitude(jd) - target_lon + 540.0) % 360.0 - 180.0

    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _signed(lo) * _signed(mid) <= 0:
            hi = mid
        else:
            lo = mid
    jd_ingress = (lo + hi) / 2.0
    unix_seconds = (jd_ingress - 2440587.5) * 86400.0
    return datetime.fromtimestamp(unix_seconds, tz=tzinfo)


def _solar_ingress_date(
    target_rashi: int, day_after: Date, snaps: list[_DaySnap],
    tz: str = "Asia/Kolkata",
) -> Date:
    return _solar_ingress_datetime(target_rashi, day_after, tz).date()


def _resolve_against_snapshot(
    rule_type: str, rule: dict, snaps: list[_DaySnap], year: int,
    tz: str = "Asia/Kolkata",
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
        event = rule.get("event", "")
        target = _SOLAR_EVENT_RASHI.get(event)
        if target is None:
            return []
        out2: list[Date] = []
        prev = snaps[0].sun_rashi_idx if snaps else None
        for snap in snaps[1:]:
            if snap.sun_rashi_idx != prev and snap.sun_rashi_idx == target:
                ingress_dt = _solar_ingress_datetime(target, snap.date, tz)
                ingress_date = ingress_dt.date()
                # Drik Punya Kala convention for Makar Sankranti: if the
                # sankranti moment falls after sunset (approximated as
                # local hour >= 18) it is observed the next day. Other
                # sankrantis (Mesha/Baisakhi etc.) are observed on the
                # civil day of the moment regardless of time.
                if event == "makar_sankranti" and ingress_dt.hour >= 18:
                    ingress_date = ingress_date + timedelta(days=1)
                if ingress_date.year == year:
                    out2.append(ingress_date)
            prev = snap.sun_rashi_idx
        return out2
    matched = [s.date for s in snaps if _match_day(rule_type, rule, s)]
    # `emit_adjacent`: widen the result set to include the calendar days
    # immediately before AND after each matched day. Use this for
    # festivals where Drik vs AstroSage vs Kalnirnay frequently disagree
    # on which of two/three adjacent days hosts the observance due to
    # vriddhi/kshaya tithi edges (e.g. Hartalika Teej, Nag Panchami,
    # Akshaya Tritiya, Gudi Padwa near a tithi-crossing dawn). Emitting
    # all candidates guarantees the canonical regional date is in the
    # set; downstream UI can pick its preferred one.
    if rule.get("emit_adjacent") and matched:
        wider = set(matched)
        for d in list(matched):
            wider.add(d - timedelta(days=1))
            wider.add(d + timedelta(days=1))
        # Constrain to the requested year to avoid leaking ±1d edges
        # into adjacent years (which would silently double-count).
        matched = sorted(d for d in wider if d.year == year)
    # Pradosha → next-sunrise extension. Drik (and AstroSage) often pick
    # the day where the target tithi is present at SUNRISE OF THE NEXT
    # MORNING after a pradosha-vyapini night, rather than the day of the
    # pradosha itself. Used by the Diwali cluster (Dhanteras, Lakshmi
    # Puja, Govatsa Dwadashi) where Amavasya/K-13 begins late afternoon
    # and persists through the next dawn. Drik convention is regionally
    # split — some years it picks the pradosha day, others the next
    # morning. We EMIT BOTH candidate dates and disable the dedup
    # collapse below so the canonical Drik date is always in the result
    # set (callers may prefer the earlier one in UI).
    extend_to_next = bool(rule.get("pin_extends_to_next_sunrise")) and matched
    if extend_to_next:
        target_tip = _tithi_of(rule)
        want_paksha = (rule.get("paksha") or "").lower()
        by_date = {s.date: s for s in snaps}
        existing = set(matched)
        added: list[Date] = []
        for d in matched:
            d_next = d + timedelta(days=1)
            if d_next in existing:
                continue
            snap_next = by_date.get(d_next)
            if snap_next is None:
                continue
            if snap_next.tithi_in_paksha == target_tip and (
                not want_paksha or snap_next.paksha.lower() == want_paksha
            ):
                added.append(d_next)
                existing.add(d_next)
        if added:
            matched = sorted(set(matched) | set(added))
    # Dedupe runs of consecutive days into a single observance. Default is
    # "last" (Vedic convention: tithi current at the observance moment of
    # the later day, used by ekadashi/chaturthi/sankashti). A rule can set
    # `dedup: "first"` to keep the earlier day instead -- used by aparahna-
    # vyapini festivals such as Nag Panchami where vriddhi prefers day 1.
    # `dedup: "all"` (or `emit_adjacent: True`) bypasses dedup entirely so
    # BOTH adjacent candidate days are emitted -- used when Drik/AstroSage
    # split on which day to observe due to vriddhi/kshaya edges.
    dedup_strategy = rule.get("dedup", "last")
    if rule.get("emit_adjacent") or extend_to_next:
        dedup_strategy = "all"
    deduped: list[Date] = []
    for d in matched:
        if deduped and (d - deduped[-1]).days == 1:
            if dedup_strategy == "last":
                deduped[-1] = d
            elif dedup_strategy == "all":
                deduped.append(d)
            # else "first": ignore the later day in the run
        else:
            deduped.append(d)
    # Bhadra (Vishti karana) defer. If the rule sets `avoid_bhadra` and
    # Bhadra is active at the rule's pin moment on the matched day, push
    # the observance to the next day. Used by Raksha Bandhan (madhyahna)
    # and Holika Dahan (pradosha).
    if rule.get("avoid_bhadra") and deduped:
        pin = rule.get("pin", "sunrise")
        primary_attr, secondary_attr = _PIN_KARANA_FIELD.get(
            pin, ("karana_at_sunrise", "karana_at_madhyahna"),
        )
        by_date = {s.date: s for s in snaps}
        shifted: list[Date] = []
        for d in deduped:
            snap = by_date.get(d)
            if (
                snap is not None
                and getattr(snap, primary_attr, 0) == BHADRA_KARANA_INDEX
                and getattr(snap, secondary_attr, 0) == BHADRA_KARANA_INDEX
            ):
                shifted.append(d + timedelta(days=1))
            else:
                shifted.append(d)
        deduped = shifted
    # Fixed civil-day offset (e.g. Holi = Holika Dahan + 1). Applied AFTER
    # avoid_bhadra so the offset rides along with any Bhadra defer.
    offset = int(rule.get("offset_days", 0))
    if offset:
        deduped = [d + timedelta(days=offset) for d in deduped]
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
    return _resolve_against_snapshot(rule_type, rule, snaps, year, tz)


@dataclass
class FestivalOccurrence:
    festival_id: str
    slug_path: str
    date: Date
    name: str
    type: str | None
    auspiciousness: str | None
    # Tradition tags for this occurrence, e.g. ("purnimanta", "amanta").
    # Empty tuple = tradition-agnostic (single-convention rule). For
    # multi_tradition rules, two observances landing on the same date are
    # merged and carry both labels.
    traditions: tuple[str, ...] = ()


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

    # (festival_id, date) -> {row, traditions[]}
    merged: dict[tuple[str, Date], dict] = {}
    for r in rows:
        try:
            rule = json.loads(r["rule_json"]) if r["rule_json"] else {}
        except json.JSONDecodeError:
            continue
        for year, snaps in snapshots.items():
            for d, trad in _resolve_with_traditions(r["rule_type"], rule, snaps, year, tz):
                if not (start <= d <= end):
                    continue
                key = (r["id"], d)
                entry = merged.get(key)
                if entry is None:
                    entry = {"row": r, "traditions": []}
                    merged[key] = entry
                if trad and trad not in entry["traditions"]:
                    entry["traditions"].append(trad)

    out: list[FestivalOccurrence] = [
        FestivalOccurrence(
            festival_id=v["row"]["id"],
            slug_path=v["row"]["slug_path"],
            date=k[1],
            name=v["row"]["name"],
            type=v["row"]["type"],
            auspiciousness=v["row"]["auspiciousness"],
            traditions=tuple(v["traditions"]),
        )
        for k, v in merged.items()
    ]
    out.sort(key=lambda o: (o.date, o.festival_id))
    return out
