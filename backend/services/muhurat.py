"""
Muhurat window calculations.

This module now exposes the classical 30-muhurta system for each civil date:

- 15 daytime muhurtas: sunrise -> sunset
- 15 nighttime muhurtas: sunset -> next sunrise

Each muhurta includes sequence, transliterated Sanskrit name, Devanagari name,
and category (auspicious/inauspicious).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date, datetime, timedelta, time
from typing import Literal, cast
from zoneinfo import ZoneInfo

from .panchang import compute_sun_moon  # your existing fn
from .panchang import compute_nakshatra  # for Amrit Kalam
from .panchang import to_julian_day


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MuhuratWindow:
    id: str
    name: str
    start: datetime  # tz-aware, local
    end: datetime    # tz-aware, local
    kind: Literal["auspicious", "inauspicious"]
    sequence: int | None = None
    sanskrit_name: str | None = None
    sanskrit_devanagari: str | None = None
    period: Literal["day", "night"] | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sequence": self.sequence,
            "name": self.name,
            "sanskrit_name": self.sanskrit_name,
            "sanskrit_devanagari": self.sanskrit_devanagari,
            "category": self.kind,
            "period": self.period,
            "start": self.start.strftime("%H:%M"),
            "end":   self.end.strftime("%H:%M"),
        }


@dataclass(frozen=True)
class MuhuratBundle:
    muhurtas: list[MuhuratWindow]

    def to_dict(self) -> dict:
        return {"muhurtas": [w.to_dict() for w in self.muhurtas]}


_THIRTY_MUHURTA_DEFS: list[dict[str, str]] = [
    {"id": "rudra", "name": "Rudra", "sanskrit": "Rudra", "devanagari": "रुद्र", "kind": "inauspicious"},
    {"id": "ahi", "name": "Ahi", "sanskrit": "Ahi", "devanagari": "आहि", "kind": "inauspicious"},
    {"id": "mitra", "name": "Mitra", "sanskrit": "Mitra", "devanagari": "मित्र", "kind": "auspicious"},
    {"id": "pitri", "name": "Pitri", "sanskrit": "Pitri", "devanagari": "पितृ", "kind": "inauspicious"},
    {"id": "vasu", "name": "Vasu", "sanskrit": "Vasu", "devanagari": "वसु", "kind": "auspicious"},
    {"id": "varaha", "name": "Varaha", "sanskrit": "Varaha", "devanagari": "वाराह", "kind": "auspicious"},
    {"id": "vishvedeva", "name": "Vishvedeva", "sanskrit": "Vishvedeva", "devanagari": "विश्वेदेव", "kind": "auspicious"},
    {"id": "vidhi", "name": "Vidhi", "sanskrit": "Vidhi", "devanagari": "विधि", "kind": "auspicious"},
    {"id": "sutamukhi", "name": "Sutamukhi", "sanskrit": "Sutamukhi", "devanagari": "सुतमुखी", "kind": "auspicious"},
    {"id": "puruhuta", "name": "Puruhuta", "sanskrit": "Puruhuta", "devanagari": "पुरुहूत", "kind": "inauspicious"},
    {"id": "vahini", "name": "Vahini", "sanskrit": "Vahini", "devanagari": "वाहिनी", "kind": "inauspicious"},
    {"id": "naktanakara", "name": "Naktanakara", "sanskrit": "Naktanakara", "devanagari": "नक्तनकरा", "kind": "inauspicious"},
    {"id": "varuna", "name": "Varuna", "sanskrit": "Varuna", "devanagari": "वरुण", "kind": "auspicious"},
    {"id": "aryaman", "name": "Aryaman", "sanskrit": "Aryaman", "devanagari": "अर्यमन्", "kind": "auspicious"},
    {"id": "bhaga", "name": "Bhaga", "sanskrit": "Bhaga", "devanagari": "भग", "kind": "inauspicious"},
    {"id": "girisha", "name": "Girisha", "sanskrit": "Girisha", "devanagari": "गिरीश", "kind": "auspicious"},
    {"id": "ajapada", "name": "Ajapada", "sanskrit": "Ajapada", "devanagari": "अजपाद", "kind": "inauspicious"},
    {"id": "ahirbudhnya", "name": "Ahirbudhnya", "sanskrit": "Ahirbudhnya", "devanagari": "अहिर्बुध्न्य", "kind": "auspicious"},
    {"id": "pushya", "name": "Pushya", "sanskrit": "Pushya", "devanagari": "पुष्य", "kind": "auspicious"},
    {"id": "ashvini", "name": "Ashvini", "sanskrit": "Ashvini", "devanagari": "अश्विनी", "kind": "auspicious"},
    {"id": "yama", "name": "Yama", "sanskrit": "Yama", "devanagari": "यम", "kind": "inauspicious"},
    {"id": "agni", "name": "Agni", "sanskrit": "Agni", "devanagari": "अग्नि", "kind": "auspicious"},
    {"id": "vidhatri", "name": "Vidhatri", "sanskrit": "Vidhatri", "devanagari": "विधातृ", "kind": "auspicious"},
    {"id": "kanda", "name": "Kanda", "sanskrit": "Kanda", "devanagari": "कण्ड", "kind": "auspicious"},
    {"id": "aditi", "name": "Aditi", "sanskrit": "Aditi", "devanagari": "अदिति", "kind": "auspicious"},
    {"id": "jiva-amrita", "name": "Jiva-Amrita", "sanskrit": "Jiva/Amrita", "devanagari": "जीव/अमृत", "kind": "auspicious"},
    {"id": "vishnu", "name": "Vishnu", "sanskrit": "Vishnu", "devanagari": "विष्णु", "kind": "auspicious"},
    {"id": "dyumadgadyuti", "name": "Dyumadgadyuti", "sanskrit": "Dyumadgadyuti", "devanagari": "द्युमद्गद्युति", "kind": "auspicious"},
    {"id": "brahma", "name": "Brahma", "sanskrit": "Brahma", "devanagari": "ब्रह्म", "kind": "auspicious"},
    {"id": "samudra", "name": "Samudra", "sanskrit": "Samudra", "devanagari": "समुद्र", "kind": "auspicious"},
]


def _build_thirty_muhurta_windows(
    sunrise: datetime,
    sunset: datetime,
    next_sunrise: datetime,
) -> list[MuhuratWindow]:
    day_span = sunset - sunrise
    night_span = next_sunrise - sunset
    day_unit = day_span / 15
    night_unit = night_span / 15

    out: list[MuhuratWindow] = []
    for i, meta in enumerate(_THIRTY_MUHURTA_DEFS, start=1):
        if i <= 15:
            start = sunrise + day_unit * (i - 1)
            end = sunrise + day_unit * i
            period: Literal["day", "night"] = "day"
        else:
            n = i - 16
            start = sunset + night_unit * n
            end = sunset + night_unit * (n + 1)
            period = "night"

        out.append(
            MuhuratWindow(
                id=meta["id"],
                name=meta["name"],
                start=start,
                end=end,
                kind=cast(Literal["auspicious", "inauspicious"], meta["kind"]),
                sequence=i,
                sanskrit_name=meta["sanskrit"],
                sanskrit_devanagari=meta["devanagari"],
                period=period,
            )
        )

    return out


# ---------------------------------------------------------------------------
# Weekday lookup tables
# ---------------------------------------------------------------------------
#
# Vedic weekday order: Sunday=0, Monday=1, ..., Saturday=6
# The day is divided into 8 equal parts from sunrise → sunset.
# Each table maps weekday → which 1-indexed part is that kaal.
#
# Sources: Standard Vedic almanac tables (drik panchang, kalnirnay).

# Rahu Kaal — 8 parts, position by weekday
_RAHU_KAAL_PART = {
    0: 8,  # Sunday    → 8th part  (last part of day)
    1: 2,  # Monday    → 2nd part
    2: 7,  # Tuesday   → 7th part
    3: 5,  # Wednesday → 5th part
    4: 6,  # Thursday  → 6th part
    5: 4,  # Friday    → 4th part
    6: 3,  # Saturday  → 3rd part
}

# Yamaganda Kaal — 8 parts, position by weekday
_YAMAGANDA_PART = {
    0: 5,  # Sunday
    1: 4,  # Monday
    2: 3,  # Tuesday
    3: 2,  # Wednesday
    4: 1,  # Thursday
    5: 7,  # Friday
    6: 6,  # Saturday
}

# Gulika Kaal — 8 parts, position by weekday
_GULIKA_PART = {
    0: 7,  # Sunday
    1: 6,  # Monday
    2: 5,  # Tuesday
    3: 4,  # Wednesday
    4: 3,  # Thursday
    5: 2,  # Friday
    6: 1,  # Saturday
}

# Dur Muhurat — day divided into 15 muhurtas (each = day_length / 15).
# Each weekday has 1 or 2 dur muhurtas. Values are 1-indexed muhurta numbers.
# (Based on classical references — Muhurta Chintamani)
_DUR_MUHURAT_PARTS = {
    0: [14],          # Sunday
    1: [12, 14],      # Monday
    2: [4, 9],        # Tuesday
    3: [5],           # Wednesday
    4: [8, 9],        # Thursday
    5: [6, 8],        # Friday
    6: [3],           # Saturday
}

# Amrit Kalam — nakshatra-specific time-of-day fraction
# Simplified: tied to which "pada" of the nakshatra is active.
# For v1 we use a per-nakshatra offset within the day (0..1).
# (Refine later with proper nakshatra-amrita-yoga rules.)
_AMRIT_KALAM_FRAC = {
    # nakshatra_number (1..27): (start_frac, end_frac) within day_length
    1:  (0.85, 0.95),  # Ashwini
    2:  (0.10, 0.20),  # Bharani
    3:  (0.30, 0.40),  # Krittika
    4:  (0.55, 0.65),  # Rohini
    5:  (0.75, 0.85),  # Mrigashira
    6:  (0.20, 0.30),  # Ardra
    7:  (0.45, 0.55),  # Punarvasu
    8:  (0.65, 0.75),  # Pushya
    9:  (0.85, 0.95),  # Ashlesha
    10: (0.05, 0.15),  # Magha
    11: (0.25, 0.35),  # Purva Phalguni
    12: (0.50, 0.60),  # Uttara Phalguni
    13: (0.70, 0.80),  # Hasta
    14: (0.15, 0.25),  # Chitra
    15: (0.35, 0.45),  # Swati
    16: (0.55, 0.65),  # Vishakha
    17: (0.75, 0.85),  # Anuradha
    18: (0.10, 0.20),  # Jyeshtha
    19: (0.30, 0.40),  # Mula
    20: (0.50, 0.60),  # Purva Ashadha
    21: (0.70, 0.80),  # Uttara Ashadha
    22: (0.20, 0.30),  # Shravana
    23: (0.40, 0.50),  # Dhanishta
    24: (0.60, 0.70),  # Shatabhisha
    25: (0.80, 0.90),  # Purva Bhadrapada
    26: (0.05, 0.15),  # Uttara Bhadrapada
    27: (0.25, 0.35),  # Revati
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vedic_weekday(d: Date) -> int:
    """Vedic weekday: Sunday=0 .. Saturday=6."""
    # Python's weekday(): Monday=0..Sunday=6  →  shift so Sunday=0
    return (d.weekday() + 1) % 7


def _slice(start: datetime, end: datetime, n_parts: int, part_index_1based: int
           ) -> tuple[datetime, datetime]:
    """Return the (start, end) of the k-th equal slice between two datetimes."""
    if not (1 <= part_index_1based <= n_parts):
        raise ValueError(f"part index {part_index_1based} out of 1..{n_parts}")
    total = (end - start).total_seconds()
    part_len = total / n_parts
    s = start + timedelta(seconds=part_len * (part_index_1based - 1))
    e = start + timedelta(seconds=part_len * part_index_1based)
    return s, e


# ---------------------------------------------------------------------------
# Individual muhurat constructors
# ---------------------------------------------------------------------------

def _brahma(sunrise: datetime) -> MuhuratWindow:
    """Brahma Muhurat: 96 min before sunrise → 48 min before sunrise."""
    return MuhuratWindow(
        id="brahma",
        name="Brahma Muhurat",
        start=sunrise - timedelta(minutes=96),
        end=sunrise - timedelta(minutes=48),
        kind="auspicious",
    )


def _abhijit(sunrise: datetime, sunset: datetime) -> MuhuratWindow:
    """Abhijit Muhurat: centered on solar noon, width = day_length / 15."""
    midday = sunrise + (sunset - sunrise) / 2
    half = (sunset - sunrise) / 30  # half of (day_length / 15)
    return MuhuratWindow(
        id="abhijit",
        name="Abhijit Muhurat",
        start=midday - half,
        end=midday + half,
        kind="auspicious",
    )


def _vijay(sunrise: datetime, sunset: datetime) -> MuhuratWindow:
    """Vijay Muhurat: 10th muhurta of the day (1 of 15)."""
    s, e = _slice(sunrise, sunset, 15, 10)
    return MuhuratWindow(
        id="vijay", name="Vijay Muhurat",
        start=s, end=e, kind="auspicious",
    )


def _godhuli(sunset: datetime) -> MuhuratWindow:
    """Godhuli Muhurat: ~24 minutes around sunset (cow-dust hour)."""
    return MuhuratWindow(
        id="godhuli", name="Godhuli Muhurat",
        start=sunset - timedelta(minutes=12),
        end=sunset + timedelta(minutes=12),
        kind="auspicious",
    )


def _amrit_kalam(sunrise: datetime, sunset: datetime,
                 nakshatra_number: int) -> MuhuratWindow:
    """Amrit Kalam: nakshatra-specific window within day length."""
    frac = _AMRIT_KALAM_FRAC.get(nakshatra_number, (0.80, 0.92))
    total = sunset - sunrise
    return MuhuratWindow(
        id="amrit", name="Amrit Kalam",
        start=sunrise + total * frac[0],
        end=sunrise + total * frac[1],
        kind="auspicious",
    )


def _rahu_kaal(sunrise: datetime, sunset: datetime, weekday: int) -> MuhuratWindow:
    s, e = _slice(sunrise, sunset, 8, _RAHU_KAAL_PART[weekday])
    return MuhuratWindow(
        id="rahu", name="Rahu Kaal",
        start=s, end=e, kind="inauspicious",
    )


def _yamaganda(sunrise: datetime, sunset: datetime, weekday: int) -> MuhuratWindow:
    s, e = _slice(sunrise, sunset, 8, _YAMAGANDA_PART[weekday])
    return MuhuratWindow(
        id="yamaganda", name="Yamaganda",
        start=s, end=e, kind="inauspicious",
    )


def _gulika(sunrise: datetime, sunset: datetime, weekday: int) -> MuhuratWindow:
    s, e = _slice(sunrise, sunset, 8, _GULIKA_PART[weekday])
    return MuhuratWindow(
        id="gulika", name="Gulika Kaal",
        start=s, end=e, kind="inauspicious",
    )


def _dur_muhurat(sunrise: datetime, sunset: datetime, weekday: int
                 ) -> list[MuhuratWindow]:
    """Dur Muhurat: 1 or 2 unfortunate muhurtas (out of 15) per weekday."""
    parts = _DUR_MUHURAT_PARTS[weekday]
    out: list[MuhuratWindow] = []
    for i, p in enumerate(parts, start=1):
        s, e = _slice(sunrise, sunset, 15, p)
        suffix = "" if len(parts) == 1 else f" ({i})"
        out.append(MuhuratWindow(
            id="dur" if len(parts) == 1 else f"dur_{i}",
            name=f"Dur Muhurat{suffix}",
            start=s, end=e, kind="inauspicious",
        ))
    return out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_muhurat(
    date: Date,
    lat: float,
    lon: float,
    tz: str = "Asia/Kolkata",
) -> MuhuratBundle:
    """
    Compute the classical 30 muhurtas for a given date and location.

    Args:
        date: Civil date.
        lat:  Latitude in degrees.
        lon:  Longitude in degrees.
        tz:   IANA timezone string.

    Returns:
        MuhuratBundle containing all 30 sequential muhurtas.
    """
    tzinfo = ZoneInfo(tz)

    # 1. Today's sunrise + sunset (local, tz-aware)
    sm_today = compute_sun_moon(date, lat, lon, tzinfo)
    sunrise = (
        datetime.fromisoformat(sm_today.sunrise_local)
        if sm_today.sunrise_local
        else None
    )
    sunset = (
        datetime.fromisoformat(sm_today.sunset_local)
        if sm_today.sunset_local
        else None
    )

    # 1b. Next sunrise (for 15 nighttime muhurtas)
    sm_next = compute_sun_moon(date + timedelta(days=1), lat, lon, tzinfo)
    next_sunrise = (
        datetime.fromisoformat(sm_next.sunrise_local)
        if sm_next.sunrise_local
        else None
    )

    if sunrise is None or sunset is None or next_sunrise is None:
        raise ValueError(
            f"No sunrise/sunset/next-sunrise for {date} at ({lat},{lon}) - polar region?"
        )

    windows = _build_thirty_muhurta_windows(sunrise, sunset, next_sunrise)
    return MuhuratBundle(muhurtas=windows)


def compute_muhurat_by_id(
    muhurat_id: str,
    date: Date,
    lat: float,
    lon: float,
    tz: str = "Asia/Kolkata",
) -> MuhuratWindow | None:
    """Look up a single muhurat by id (powers GET /v1/muhurat/{id})."""
    bundle = compute_muhurat(date, lat, lon, tz)
    for w in bundle.muhurtas:
        if w.id == muhurat_id:
            return w
    return None


# ---------------------------------------------------------------------------
# Festival-page muhurats (Pradosh Kaal, Vrishabha Kaal)
# Referenced by Dhanteras / Diwali pages on astrosage. Both are derivable.
# ---------------------------------------------------------------------------

def compute_pradosh_kaal(
    date: Date, lat: float, lon: float, tz: str = "Asia/Kolkata",
) -> MuhuratWindow:
    """
    Pradosh Kaal — the twilight window around sunset, traditionally defined as
    "the 3 muhurtas straddling sunset" i.e. 1.5 muhurtas before to 1.5 after.
    One muhurta = day_length / 15, so total width ≈ 2h24m on equinoxes.

    Practical convention used by drikpanchang & astrosage:
        start = sunset - 0.75 muhurta
        end   = sunset + 2.25 muhurta
    which yields the values shown in the Dhanteras page (Pradosh Kaal ~2h36m).
    """
    tzinfo = ZoneInfo(tz)
    sm = compute_sun_moon(date, lat, lon, tzinfo)
    if not (sm.sunrise_local and sm.sunset_local):
        raise ValueError(f"No sunset for {date} at ({lat},{lon})")

    sunrise = datetime.fromisoformat(sm.sunrise_local)
    sunset = datetime.fromisoformat(sm.sunset_local)
    muhurta = (sunset - sunrise) / 15
    return MuhuratWindow(
        id="pradosh",
        name="Pradosh Kaal",
        start=sunset - 0.75 * muhurta,
        end=sunset + 2.25 * muhurta,
        kind="auspicious",
    )


def compute_vrishabha_kaal(
    date: Date, lat: float, lon: float, tz: str = "Asia/Kolkata",
) -> MuhuratWindow | None:
    """
    Vrishabha Kaal — the interval on a given evening when the ascendant
    (lagna) sits in the sidereal sign Vrishabha (Taurus). Required for
    Dhanteras / Diwali Lakshmi Puja muhurat (Vrishabha is a fixed sign,
    making the puja stable).

    Algorithm: sample lagna every 4 min starting at sunset for 6 h, return
    the contiguous interval where the ascendant longitude (sidereal) is in
    [30°, 60°). Returns None if Vrishabha doesn't rise in that window
    (rare at high latitudes).
    """
    import swisseph as swe  # local import — already pinned in pyproject
    from .panchang import SIDEREAL_FLAG, to_julian_day, from_julian_day

    tzinfo = ZoneInfo(tz)
    sm = compute_sun_moon(date, lat, lon, tzinfo)
    if not sm.sunset_local:
        return None
    sunset = datetime.fromisoformat(sm.sunset_local)

    def asc_long(dt: datetime) -> float:
        jd = to_julian_day(dt.astimezone(ZoneInfo("UTC")))
        # houses_ex returns (cusps, ascmc); ascmc[0] is the ascendant in
        # TROPICAL longitude. Convert to sidereal by subtracting ayanamsa.
        _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"P", SIDEREAL_FLAG)
        ayan = swe.get_ayanamsa_ut(jd)
        return (ascmc[0] - ayan) % 360

    step = timedelta(minutes=4)
    horizon = sunset + timedelta(hours=6)
    start: datetime | None = None
    end: datetime | None = None
    t = sunset
    while t <= horizon:
        in_vrishabha = 30.0 <= asc_long(t) < 60.0
        if in_vrishabha and start is None:
            start = t
        elif not in_vrishabha and start is not None:
            end = t
            break
        t += step

    if start is None:
        return None
    if end is None:
        end = horizon

    return MuhuratWindow(
        id="vrishabha",
        name="Vrishabha Kaal",
        start=start,
        end=end,
        kind="auspicious",
    )