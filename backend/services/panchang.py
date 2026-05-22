"""
panchang.py — Vedic Panchang astronomical core

Implements the calculations from implementation.md §4:
  - Tithi (lunar day, 1–30)
  - Nakshatra (lunar mansion, 1–27)
  - Yoga (sun+moon longitude index, 1–27)
  - Karana (half-tithi, 1–11)
  - Sun/moon rise & set
  - Moon phase
  - Rashi (sun sign & moon sign)

All longitudes are SIDEREAL using LAHIRI ayanamsa (the standard for Indian panchang).
All times are returned in the user's local timezone unless explicitly UTC.

Verification target: drikpanchang.com for 2026-05-20, lat=25.32, lon=83.0 (Varanasi).

Run:
    pip install pyswisseph pytz
    python panchang.py --date 2026-05-20 --lat 25.32 --lon 83.0 --tz Asia/Kolkata
    python panchang.py --test
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

import swisseph as swe

# ---------------------------------------------------------------------------
# Constants & catalogs
# ---------------------------------------------------------------------------

# Use Lahiri ayanamsa (Indian government standard, ~24° offset from tropical)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

# Set ephemeris path if you have Swiss Ephemeris .se1 files locally.
# If not, pyswisseph falls back to its built-in Moshier ephemeris which is
# accurate to ~1 arc-second for dates 3000 BCE to 3000 CE. Good enough.
# swe.set_ephe_path("/path/to/ephe")

SIDEREAL_FLAG = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

# 30 tithis: 15 in Shukla (waxing) + 15 in Krishna (waning)
TITHI_NAMES = [
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima",  # Shukla
    "Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami",
    "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
    "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Amavasya",  # Krishna
]

# Lord of each tithi (per Brihat Parashara Hora Shastra)
TITHI_LORDS = [
    "Agni", "Brahma", "Gauri", "Ganesha", "Naga",
    "Kartikeya", "Surya", "Shiva", "Durga", "Yama",
    "Vishvedeva", "Vishnu", "Kamadeva", "Shiva", "Chandra",
] * 2  # same lords cycle through Krishna paksha

NAKSHATRA_NAMES = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha",
    "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
    "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati",
    "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha",
    "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAKSHATRA_DEITIES = [
    "Ashwini Kumaras", "Yama", "Agni", "Brahma", "Soma (Chandra)",
    "Rudra", "Aditi", "Brihaspati", "Sarpa (Nagas)", "Pitrs",
    "Bhaga", "Aryaman", "Savitr", "Vishvakarma", "Vayu",
    "Indra-Agni", "Mitra", "Indra", "Nirriti", "Apas",
    "Vishvedevas", "Vishnu", "Vasus", "Varuna",
    "Aja Ekapada", "Ahir Budhnya", "Pushan",
]

NAKSHATRA_SYMBOLS = [
    "Horse's head", "Yoni (womb)", "Razor/Flame", "Ox cart", "Deer's head",
    "Teardrop", "Bow and quiver", "Cow's udder", "Coiled serpent", "Throne",
    "Front legs of bed", "Back legs of bed", "Hand", "Pearl", "Coral",
    "Triumphal arch", "Lotus", "Earring", "Roots/Lion's tail", "Fan",
    "Elephant tusk", "Three footprints", "Drum", "Empty circle",
    "Sword", "Twins", "Fish",
]

NAKSHATRA_ELEMENTS = [
    "Earth", "Earth", "Earth", "Earth", "Earth",       # Mesha/Vrishabha
    "Water", "Water", "Water", "Water", "Water",       # Mithuna/Karka
    "Fire", "Fire", "Fire", "Fire", "Fire",            # Simha/Kanya (Bhumi)
    "Fire", "Fire", "Fire", "Air", "Air",
    "Air", "Air", "Air", "Ether",
    "Ether", "Ether", "Ether",
]

YOGA_NAMES = [
    "Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana",
    "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda",
    "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
    "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva",
    "Siddha", "Sadhya", "Shubha", "Shukla", "Brahma",
    "Indra", "Vaidhriti",
]

# Karana: 11 total. 7 movable cycle through positions 1–56, then 4 fixed
# occupy positions 57–60. Half-tithi index 0–59 maps to a karana.
KARANA_NAMES_MOVABLE = ["Bava", "Balava", "Kaulava", "Taitila", "Gara", "Vanij", "Vishti"]
KARANA_NAMES_FIXED = ["Shakuni", "Chatushpada", "Naga", "Kimstughna"]

RASHI_NAMES = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena",
]
RASHI_LORDS = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury",
               "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

# ---------------------------------------------------------------------------
# Low-level: Julian day & longitudes
# ---------------------------------------------------------------------------

def to_julian_day(dt_utc: datetime) -> float:
    """Convert a UTC datetime to Julian Day (UT)."""
    if dt_utc.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    dt_utc = dt_utc.astimezone(timezone.utc)
    hours = dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600
    return swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, hours)


def from_julian_day(jd: float, tz: ZoneInfo) -> datetime:
    """Convert a Julian Day (UT) to a tz-aware local datetime."""
    y, m, d, h = swe.revjul(jd)
    hour = int(h)
    minute_f = (h - hour) * 60
    minute = int(minute_f)
    second = int(round((minute_f - minute) * 60))
    # Guard against rounding to 60
    if second == 60:
        second = 0; minute += 1
    if minute == 60:
        minute = 0; hour += 1
    dt = datetime(y, m, d, hour, minute, second, tzinfo=timezone.utc)
    return dt.astimezone(tz)


def sun_longitude(jd: float) -> float:
    """Sidereal longitude of Sun in degrees, 0–360."""
    lon, _ = swe.calc_ut(jd, swe.SUN, SIDEREAL_FLAG)
    return lon[0] % 360


def moon_longitude(jd: float) -> float:
    """Sidereal longitude of Moon in degrees, 0–360."""
    lon, _ = swe.calc_ut(jd, swe.MOON, SIDEREAL_FLAG)
    return lon[0] % 360


# ---------------------------------------------------------------------------
# Core panchang elements
# ---------------------------------------------------------------------------

@dataclass
class TithiInfo:
    index: int              # 1–30
    name: str
    paksha: str             # "Shukla" or "Krishna"
    lord: str
    starts_at_local: str    # ISO timestamp; when current tithi began
    ends_at_local: str      # when it ends

@dataclass
class NakshatraInfo:
    index: int              # 1–27
    name: str
    deity: str
    symbol: str
    element: str
    pada: int               # 1–4 (quarter of the nakshatra)
    starts_at_local: str
    ends_at_local: str

@dataclass
class YogaInfo:
    index: int              # 1–27
    name: str
    starts_at_local: str
    ends_at_local: str

@dataclass
class KaranaInfo:
    index: int              # 1–11
    name: str
    starts_at_local: str
    ends_at_local: str


def _find_boundary_crossing(
    jd_start: float, jd_end: float,
    boundary_value: float,
    value_fn,
    tolerance_seconds: float = 1.0,
) -> float:
    """
    Bisection to find the JD at which value_fn(jd) crosses `boundary_value`.
    value_fn must return a monotonically increasing value modulo 360 within [jd_start, jd_end].

    We work in unwrapped space: if the value wraps from ~359° to ~1°, we add 360 to keep it monotonic.
    """
    tol_jd = tolerance_seconds / 86400.0

    def normalized(jd: float, ref: float) -> float:
        v = value_fn(jd)
        # Unwrap: if v jumped backward past ref, it crossed 360
        while v < ref - 180:
            v += 360
        while v > ref + 180:
            v -= 360
        return v

    v_start = value_fn(jd_start)
    # Unwrap boundary so it lies in [v_start, v_start + 360)
    b = boundary_value
    while b < v_start:
        b += 360
    while b - v_start > 360:
        b -= 360

    lo, hi = jd_start, jd_end
    while hi - lo > tol_jd:
        mid = (lo + hi) / 2
        v_mid = normalized(mid, v_start)
        if v_mid < b:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _diff_lon(jd: float) -> float:
    """(Moon - Sun) longitude mod 360. Drives tithi & karana."""
    return (moon_longitude(jd) - sun_longitude(jd)) % 360


def _sum_lon(jd: float) -> float:
    """(Moon + Sun) longitude mod 360. Drives yoga."""
    return (moon_longitude(jd) + sun_longitude(jd)) % 360


def compute_tithi(jd: float, tz: ZoneInfo) -> TithiInfo:
    """
    Tithi = floor(((moon - sun) mod 360) / 12) + 1
    Each tithi is 12° of moon-sun elongation.
    """
    diff = _diff_lon(jd)
    n = int(diff // 12)               # 0..29
    idx_1based = n + 1                 # 1..30

    # Boundaries: tithi N spans [N*12, (N+1)*12) degrees
    lower_boundary = n * 12
    upper_boundary = (n + 1) * 12

    # Find start: search up to 1.5 days back (max tithi length ~26h)
    starts_jd = _find_boundary_crossing(jd - 1.6, jd, lower_boundary, _diff_lon)
    ends_jd = _find_boundary_crossing(jd, jd + 1.6, upper_boundary, _diff_lon)

    paksha = "Shukla" if n < 15 else "Krishna"

    return TithiInfo(
        index=idx_1based,
        name=TITHI_NAMES[n],
        paksha=paksha,
        lord=TITHI_LORDS[n],
        starts_at_local=from_julian_day(starts_jd, tz).isoformat(timespec="seconds"),
        ends_at_local=from_julian_day(ends_jd, tz).isoformat(timespec="seconds"),
    )


def compute_nakshatra(jd: float, tz: ZoneInfo) -> NakshatraInfo:
    """
    Nakshatra = floor(moon_lon / (360/27)) + 1
    Each nakshatra spans 13°20' = 800 arc-minutes.
    Pada = quarter within the nakshatra (each pada = 3°20').
    """
    SEGMENT = 360 / 27  # 13.3333...
    moon = moon_longitude(jd)
    n = int(moon // SEGMENT)            # 0..26
    idx_1based = n + 1

    # Pada
    pos_within = moon - n * SEGMENT
    pada = int(pos_within // (SEGMENT / 4)) + 1   # 1..4

    lower = n * SEGMENT
    upper = (n + 1) * SEGMENT

    starts_jd = _find_boundary_crossing(jd - 1.2, jd, lower, moon_longitude)
    ends_jd = _find_boundary_crossing(jd, jd + 1.2, upper, moon_longitude)

    return NakshatraInfo(
        index=idx_1based,
        name=NAKSHATRA_NAMES[n],
        deity=NAKSHATRA_DEITIES[n],
        symbol=NAKSHATRA_SYMBOLS[n],
        element=NAKSHATRA_ELEMENTS[n],
        pada=pada,
        starts_at_local=from_julian_day(starts_jd, tz).isoformat(timespec="seconds"),
        ends_at_local=from_julian_day(ends_jd, tz).isoformat(timespec="seconds"),
    )


def compute_yoga(jd: float, tz: ZoneInfo) -> YogaInfo:
    """Yoga = floor(((sun + moon) mod 360) / (360/27)) + 1"""
    SEGMENT = 360 / 27
    s = _sum_lon(jd)
    n = int(s // SEGMENT)
    idx_1based = n + 1

    lower = n * SEGMENT
    upper = (n + 1) * SEGMENT

    starts_jd = _find_boundary_crossing(jd - 1.5, jd, lower, _sum_lon)
    ends_jd = _find_boundary_crossing(jd, jd + 1.5, upper, _sum_lon)

    return YogaInfo(
        index=idx_1based,
        name=YOGA_NAMES[n],
        starts_at_local=from_julian_day(starts_jd, tz).isoformat(timespec="seconds"),
        ends_at_local=from_julian_day(ends_jd, tz).isoformat(timespec="seconds"),
    )


def compute_karana(jd: float, tz: ZoneInfo) -> KaranaInfo:
    """
    Karana = half-tithi. 60 half-tithis per lunar month, each 6° of elongation.
    Karana cycle (0-indexed half-tithi → karana name):
        positions 0..56 (offsets 1..57): movable karanas cycle 8 times through 7 names
        position 57 (after Chaturdashi/Amavasya): Shakuni
        position 58: Chatushpada
        position 59: Naga
        ... wait, the convention:
        - 1st half of Pratipada (Shukla) is always Kimstughna (fixed)
        - then movable 8x7 = 56 positions
        - last 3 half-tithis (Krishna Chaturdashi 2nd + Amavasya 1st & 2nd) are
          Shakuni, Chatushpada, Naga

    Reference: https://en.wikipedia.org/wiki/Karana_(Panchangam)
    """
    diff = _diff_lon(jd)
    half_idx = int(diff // 6)   # 0..59 (60 half-tithis per cycle)

    if half_idx == 0:
        name = "Kimstughna"      # fixed, first half of Shukla Pratipada
        karana_1based = 11       # we index fixed karanas 8..11; Kimstughna is 11 traditionally
    elif half_idx >= 57:
        # Last 3: Shakuni (57), Chatushpada (58), Naga (59)
        fixed = ["Shakuni", "Chatushpada", "Naga"]
        name = fixed[half_idx - 57]
        karana_1based = 8 + (half_idx - 57)  # 8, 9, 10
    else:
        # Movable: position 1..56 → cycle through 7 names
        movable_pos = (half_idx - 1) % 7
        name = KARANA_NAMES_MOVABLE[movable_pos]
        karana_1based = movable_pos + 1   # 1..7

    lower = half_idx * 6
    upper = (half_idx + 1) * 6
    starts_jd = _find_boundary_crossing(jd - 0.8, jd, lower, _diff_lon)
    ends_jd = _find_boundary_crossing(jd, jd + 0.8, upper, _diff_lon)

    return KaranaInfo(
        index=karana_1based,
        name=name,
        starts_at_local=from_julian_day(starts_jd, tz).isoformat(timespec="seconds"),
        ends_at_local=from_julian_day(ends_jd, tz).isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# Sun / Moon rise & set
# ---------------------------------------------------------------------------

@dataclass
class SunMoon:
    sunrise_local: Optional[str]
    sunset_local: Optional[str]
    day_length_minutes: Optional[int]
    moonrise_local: Optional[str]
    moonset_local: Optional[str]
    moon_phase: str
    moon_illumination_pct: float


def _rise_or_set(jd_start: float, body: int, lon: float, lat: float, kind: str) -> Optional[float]:
    """
    Returns the JD (UT) of the next rise/set after jd_start, or None if none in 1 day.
    kind: 'rise' or 'set'.
    """
    flag = swe.CALC_RISE if kind == "rise" else swe.CALC_SET
    # geopos is a single tuple (lon, lat, alt); atmo params default to standard sea-level.
    ret, tret = swe.rise_trans(
        jd_start,            # tjd_ut
        body,                # ipl (planet number)
        flag,                # rsmi (rise/set flag)
        (lon, lat, 0.0),     # geopos (lon, lat, altitude_m)
    )
    if ret < 0:
        return None
    return tret[0]

def compute_sun_moon(local_date: date, lat: float, lon: float, tz: ZoneInfo) -> SunMoon:
    """
    Sunrise/set, moonrise/set, day length, moon phase for a given local date.
    We start the search at local midnight (in UT) and look forward 24h.
    """
    local_midnight = datetime.combine(local_date, datetime.min.time(), tzinfo=tz)
    jd_start = to_julian_day(local_midnight)

    sun_rise_jd = _rise_or_set(jd_start, swe.SUN, lon, lat, "rise")
    sun_set_jd = _rise_or_set(jd_start, swe.SUN, lon, lat, "set")
    moon_rise_jd = _rise_or_set(jd_start, swe.MOON, lon, lat, "rise")
    moon_set_jd = _rise_or_set(jd_start, swe.MOON, lon, lat, "set")

    sunrise_local = from_julian_day(sun_rise_jd, tz).isoformat(timespec="seconds") if sun_rise_jd else None
    sunset_local = from_julian_day(sun_set_jd, tz).isoformat(timespec="seconds") if sun_set_jd else None
    moonrise_local = from_julian_day(moon_rise_jd, tz).isoformat(timespec="seconds") if moon_rise_jd else None
    moonset_local = from_julian_day(moon_set_jd, tz).isoformat(timespec="seconds") if moon_set_jd else None

    day_length_minutes = None
    if sun_rise_jd and sun_set_jd:
        day_length_minutes = int(round((sun_set_jd - sun_rise_jd) * 24 * 60))

    # Moon phase from elongation at local noon
    noon = datetime.combine(local_date, datetime.min.time(), tzinfo=tz) + timedelta(hours=12)
    jd_noon = to_julian_day(noon)
    elongation = (moon_longitude(jd_noon) - sun_longitude(jd_noon)) % 360
    moon_phase = _moon_phase_name(elongation)
    illumination_pct = round((1 - math.cos(math.radians(elongation))) / 2 * 100, 1)

    return SunMoon(
        sunrise_local=sunrise_local,
        sunset_local=sunset_local,
        day_length_minutes=day_length_minutes,
        moonrise_local=moonrise_local,
        moonset_local=moonset_local,
        moon_phase=moon_phase,
        moon_illumination_pct=illumination_pct,
    )


def _moon_phase_name(elongation_deg: float) -> str:
    """Return the standard 8-phase name from sun-moon elongation."""
    bands = [
        (22.5, "new_moon"),
        (67.5, "waxing_crescent"),
        (112.5, "first_quarter"),
        (157.5, "waxing_gibbous"),
        (202.5, "full_moon"),
        (247.5, "waning_gibbous"),
        (292.5, "last_quarter"),
        (337.5, "waning_crescent"),
        (360.1, "new_moon"),
    ]
    for upper, name in bands:
        if elongation_deg < upper:
            return name
    return "new_moon"


# ---------------------------------------------------------------------------
# Rashi (sun sign & moon sign)
# ---------------------------------------------------------------------------

@dataclass
class RashiInfo:
    sun_sign: str
    sun_sign_lord: str
    moon_sign: str
    moon_sign_lord: str


def compute_rashi(jd: float) -> RashiInfo:
    sun_idx = int(sun_longitude(jd) // 30)   # 0..11
    moon_idx = int(moon_longitude(jd) // 30)
    return RashiInfo(
        sun_sign=RASHI_NAMES[sun_idx],
        sun_sign_lord=RASHI_LORDS[sun_idx],
        moon_sign=RASHI_NAMES[moon_idx],
        moon_sign_lord=RASHI_LORDS[moon_idx],
    )


# ---------------------------------------------------------------------------
# Top-level aggregate (powers GET /v1/panchang/today)
# ---------------------------------------------------------------------------

@dataclass
class Panchang:
    date: str
    weekday: str
    tithi: TithiInfo
    nakshatra: NakshatraInfo
    yoga: YogaInfo
    karana: KaranaInfo
    rashi: RashiInfo
    sun_moon: SunMoon


def compute_panchang(local_date: date, lat: float, lon: float, tz_name: str) -> Panchang:
    """
    Compute the full panchang for a local date at a given location.
    Reference moment for tithi/nakshatra/yoga/karana is LOCAL SUNRISE
    (Vedic convention: a "day" starts at sunrise).
    """
    tz = ZoneInfo(tz_name)
    sm = compute_sun_moon(local_date, lat, lon, tz)

    # Reference moment: local sunrise (or noon if polar)
    if sm.sunrise_local:
        ref_dt = datetime.fromisoformat(sm.sunrise_local)
    else:
        ref_dt = datetime.combine(local_date, datetime.min.time(), tzinfo=tz) + timedelta(hours=12)
    jd_ref = to_julian_day(ref_dt)

    tithi = compute_tithi(jd_ref, tz)
    nak = compute_nakshatra(jd_ref, tz)
    yoga = compute_yoga(jd_ref, tz)
    karana = compute_karana(jd_ref, tz)
    rashi = compute_rashi(jd_ref)

    weekday = WEEKDAY_NAMES[local_date.weekday()]

    return Panchang(
        date=local_date.isoformat(),
        weekday=weekday,
        tithi=tithi,
        nakshatra=nak,
        yoga=yoga,
        karana=karana,
        rashi=rashi,
        sun_moon=sm,
    )


def panchang_to_dict(p: Panchang) -> dict:
    """JSON-serializable form."""
    return {
        "date": p.date,
        "weekday": p.weekday,
        "tithi": asdict(p.tithi),
        "nakshatra": asdict(p.nakshatra),
        "yoga": asdict(p.yoga),
        "karana": asdict(p.karana),
        "rashi": asdict(p.rashi),
        "sun_moon": asdict(p.sun_moon),
    }


# ---------------------------------------------------------------------------
# CLI / smoke tests
# ---------------------------------------------------------------------------

def _print_panchang(p: Panchang) -> None:
    print(f"\n{'=' * 60}")
    print(f" Panchang for {p.date} ({p.weekday})")
    print(f"{'=' * 60}")
    print(f" Tithi     : {p.tithi.paksha} {p.tithi.name}  (lord: {p.tithi.lord})")
    print(f"             ends {p.tithi.ends_at_local}")
    print(f" Nakshatra : {p.nakshatra.name}  pada {p.nakshatra.pada}")
    print(f"             deity: {p.nakshatra.deity} | symbol: {p.nakshatra.symbol}")
    print(f"             ends {p.nakshatra.ends_at_local}")
    print(f" Yoga      : {p.yoga.name}")
    print(f"             ends {p.yoga.ends_at_local}")
    print(f" Karana    : {p.karana.name}")
    print(f"             ends {p.karana.ends_at_local}")
    print(f" Sun sign  : {p.rashi.sun_sign}  (lord: {p.rashi.sun_sign_lord})")
    print(f" Moon sign : {p.rashi.moon_sign}  (lord: {p.rashi.moon_sign_lord})")
    print(f" Sunrise   : {p.sun_moon.sunrise_local}")
    print(f" Sunset    : {p.sun_moon.sunset_local}")
    print(f" Day length: {p.sun_moon.day_length_minutes} min")
    print(f" Moonrise  : {p.sun_moon.moonrise_local}")
    print(f" Moonset   : {p.sun_moon.moonset_local}")
    print(f" Moon phase: {p.sun_moon.moon_phase} ({p.sun_moon.moon_illumination_pct}% illum.)")
    print()


def run_tests():
    """Sanity checks against known reference points."""
    print("\n=== Panchang smoke tests ===\n")

    # Test 1: Varanasi, 2026-05-20
    print("Test 1: Varanasi (25.32, 83.0) on 2026-05-20")
    p = compute_panchang(date(2026, 5, 20), 25.32, 83.0, "Asia/Kolkata")
    _print_panchang(p)
    print(f"  ➜ Compare with drikpanchang.com for cross-validation.\n")

    # Test 2: Bangalore today (illustrative)
    print("Test 2: Bangalore (12.97, 77.59) today")
    p = compute_panchang(date.today(), 12.97, 77.59, "Asia/Kolkata")
    _print_panchang(p)

    # Test 3: Sanity — tithi cycle
    print("Test 3: Tithi progression over 5 consecutive days (Bangalore)")
    for i in range(5):
        d = date.today() + timedelta(days=i)
        p = compute_panchang(d, 12.97, 77.59, "Asia/Kolkata")
        print(f"  {d}: {p.tithi.paksha} {p.tithi.name:14s} | {p.nakshatra.name:18s} | {p.sun_moon.moon_phase}")

    print("\n✓ Tests done. Verify Test 1 against drikpanchang.com.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="YYYY-MM-DD (default: today)")
    parser.add_argument("--lat", type=float, default=25.32)
    parser.add_argument("--lon", type=float, default=83.0)
    parser.add_argument("--tz", type=str, default="Asia/Kolkata")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()

    if args.test:
        run_tests()
    else:
        d = date.fromisoformat(args.date) if args.date else date.today()
        p = compute_panchang(d, args.lat, args.lon, args.tz)
        _print_panchang(p)