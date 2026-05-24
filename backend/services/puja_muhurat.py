"""
Festival worship / puja muhurat window computation.

For each festival occurrence whose `festival_id` is in `REGISTRY`,
compute one or more `PujaMuhurat` windows (e.g. Diwali Lakshmi Puja
Muhurat = Pradosh Kaal ∩ Amavasya tithi).

Windows are derived from the snapshot's already-computed
`sunrise_jd` / `sunset_jd` plus on-demand re-probes for next-sunrise
(cheap) and moonrise (cheap; only triggered for Karva-Chauth-class
rules). Tithi spans for intersection are obtained from the existing
`compute_tithi` bisection at the relevant kala center.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as Date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

import swisseph as swe

from .panchang import (
    compute_tithi,
    find_rise_or_set,
    from_julian_day,
    to_julian_day,
)


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PujaMuhurat:
    id: str
    name: str
    start_local: str            # "HH:MM" 24h
    end_local: str              # "HH:MM" 24h
    duration_minutes: int
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "start": self.start_local,
            "end": self.end_local,
            "duration_minutes": self.duration_minutes,
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Context (sunrise/sunset/next-sunrise pre-fetched; moonrise lazy)
# ---------------------------------------------------------------------------


@dataclass
class _Ctx:
    date: Date
    tz: ZoneInfo
    lat: float
    lon: float
    sunrise: datetime | None
    sunset: datetime | None
    next_sunrise: datetime | None
    _cache: dict = field(default_factory=dict)

    def moonrise(self) -> datetime | None:
        if "moonrise" not in self._cache:
            jd_mid = to_julian_day(
                datetime.combine(self.date, datetime.min.time(), tzinfo=self.tz)
            )
            jd = find_rise_or_set(
                jd_mid, swe.MOON, self.lon, self.lat, "rise",
                search_window_days=1.5, backward_first=True,
            )
            self._cache["moonrise"] = from_julian_day(jd, self.tz) if jd else None
        return self._cache["moonrise"]

    def day_unit(self) -> timedelta | None:
        if self.sunrise and self.sunset:
            return (self.sunset - self.sunrise) / 15
        return None

    def night_unit(self) -> timedelta | None:
        if self.sunset and self.next_sunrise:
            return (self.next_sunrise - self.sunset) / 15
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(start: datetime, end: datetime) -> tuple[str, str, int]:
    """Format a window as (HH:MM, HH:MM, duration_minutes)."""
    dur = int(round((end - start).total_seconds() / 60))
    return start.strftime("%H:%M"), end.strftime("%H:%M"), max(0, dur)


def _tithi_span_at(jd: float, tz: ZoneInfo) -> tuple[datetime, datetime] | None:
    """Return (start, end) of the tithi current at `jd`, in `tz`."""
    try:
        t = compute_tithi(jd, tz)
        return (
            datetime.fromisoformat(t.starts_at_local),
            datetime.fromisoformat(t.ends_at_local),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Kala windows
# ---------------------------------------------------------------------------


def _pradosh_kaal(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """First 3 muhurtas after sunset (~2h24m at equinox)."""
    unit = ctx.night_unit()
    if not ctx.sunset or unit is None:
        return None
    return ctx.sunset, ctx.sunset + 3 * unit


def _nishita_kala(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Middle muhurta of the night (8th of 15)."""
    unit = ctx.night_unit()
    if not ctx.sunset or unit is None:
        return None
    return ctx.sunset + 7 * unit, ctx.sunset + 8 * unit


def _madhyahna(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Middle muhurta of the day (8th of 15)."""
    unit = ctx.day_unit()
    if not ctx.sunrise or unit is None:
        return None
    return ctx.sunrise + 7 * unit, ctx.sunrise + 8 * unit


def _aparahna(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Aparahna kala: parts 4-5 of 5 = day_span * 0.6 .. 0.8."""
    unit = ctx.day_unit()
    if not ctx.sunrise or unit is None:
        return None
    return ctx.sunrise + 9 * unit, ctx.sunrise + 12 * unit


def _purvahna(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Purvahna kala: first 1/5 of day = first 3 of 15 day-muhurtas."""
    unit = ctx.day_unit()
    if not ctx.sunrise or unit is None:
        return None
    return ctx.sunrise, ctx.sunrise + 3 * unit


def _sayahna(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Sayahna kala: last 1/5 of day = 12..15 day-muhurtas."""
    unit = ctx.day_unit()
    if not ctx.sunrise or unit is None:
        return None
    return ctx.sunrise + 12 * unit, ctx.sunrise + 15 * unit


def _godhuli(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """Twilight: 24 min straddling sunset."""
    if not ctx.sunset:
        return None
    return ctx.sunset - timedelta(minutes=12), ctx.sunset + timedelta(minutes=12)


def _brahma_muhurat(ctx: _Ctx) -> tuple[datetime, datetime] | None:
    """96 min to 48 min before sunrise."""
    if not ctx.sunrise:
        return None
    return ctx.sunrise - timedelta(minutes=96), ctx.sunrise - timedelta(minutes=48)


# ---------------------------------------------------------------------------
# Builders (return PujaMuhurat | None)
# ---------------------------------------------------------------------------


def _build_pradosh_kaal(ctx: _Ctx) -> PujaMuhurat | None:
    w = _pradosh_kaal(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "pradosh_kaal", "Pradosh Kaal", s, e, d,
        "First three muhurtas after sunset",
    )


def _build_lakshmi_puja_diwali(ctx: _Ctx) -> PujaMuhurat | None:
    """Lakshmi Puja Muhurat = Pradosh Kaal ∩ Amavasya tithi span."""
    p = _pradosh_kaal(ctx)
    if not p or not ctx.sunset:
        return None
    probe_dt = ctx.sunset + timedelta(minutes=30)
    jd = to_julian_day(probe_dt)
    span = _tithi_span_at(jd, ctx.tz)
    if not span:
        return None
    start = max(p[0], span[0])
    end = min(p[1], span[1])
    if start >= end:
        return None
    s, e, d = _fmt(start, end)
    return PujaMuhurat(
        "lakshmi_puja", "Lakshmi Puja Muhurat", s, e, d,
        "Pradosh Kaal during Amavasya tithi",
    )


def _build_nishita_puja(ctx: _Ctx) -> PujaMuhurat | None:
    w = _nishita_kala(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "nishita_puja", "Nishita Kaal", s, e, d,
        "Middle muhurta of the night",
    )


def _build_mahanishita_with_tithi(ctx: _Ctx) -> PujaMuhurat | None:
    """Mahashivratri / Janmashtami: Nishita ∩ current tithi span."""
    w = _nishita_kala(ctx)
    if not w:
        return None
    mid = w[0] + (w[1] - w[0]) / 2
    span = _tithi_span_at(to_julian_day(mid), ctx.tz)
    start, end = w
    if span:
        start = max(start, span[0])
        end = min(end, span[1])
    if start >= end:
        s, e, d = _fmt(*w)
        return PujaMuhurat(
            "nishita_puja", "Nishita Kaal", s, e, d,
            "Middle muhurta of the night",
        )
    s, e, d = _fmt(start, end)
    return PujaMuhurat(
        "nishita_puja", "Nishita Puja Muhurat", s, e, d,
        "Nishita Kaal during the festival tithi",
    )


def _build_madhyahna_puja(ctx: _Ctx) -> PujaMuhurat | None:
    w = _madhyahna(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "madhyahna_puja", "Madhyahna Puja Muhurat", s, e, d,
        "Solar-midday muhurta (8th of 15 day-muhurtas)",
    )


def _build_aparahna_puja(ctx: _Ctx) -> PujaMuhurat | None:
    w = _aparahna(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "aparahna_puja", "Aparahna Puja Muhurat", s, e, d,
        "Afternoon kala (3/5 to 4/5 of the day)",
    )


def _build_purvahna_puja(ctx: _Ctx) -> PujaMuhurat | None:
    w = _purvahna(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "purvahna_puja", "Purvahna Puja Muhurat", s, e, d,
        "Forenoon kala (first 1/5 of the day)",
    )


def _build_sayahna_puja(ctx: _Ctx) -> PujaMuhurat | None:
    w = _sayahna(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "sayahna_puja", "Sayahna Puja Muhurat", s, e, d,
        "Evening kala (last 1/5 of the day, before sunset)",
    )


def _build_godhuli(ctx: _Ctx) -> PujaMuhurat | None:
    w = _godhuli(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "godhuli", "Godhuli Bela", s, e, d,
        "Twilight window straddling sunset",
    )


def _build_brahma_muhurat(ctx: _Ctx) -> PujaMuhurat | None:
    w = _brahma_muhurat(ctx)
    if not w:
        return None
    s, e, d = _fmt(*w)
    return PujaMuhurat(
        "brahma_muhurat", "Brahma Muhurat", s, e, d,
        "96 min to 48 min before sunrise",
    )


def _build_moonrise_puja(ctx: _Ctx) -> PujaMuhurat | None:
    """Moonrise + 1h window (Karva Chauth, Sankashti Chaturthi)."""
    mr = ctx.moonrise()
    if not mr:
        return None
    s, e, d = _fmt(mr, mr + timedelta(minutes=60))
    return PujaMuhurat(
        "moonrise_puja", "Chandra Darshan / Arghya", s, e, d,
        "1-hour window after moonrise",
    )


def _build_sandhya_arghya(ctx: _Ctx) -> PujaMuhurat | None:
    """Chhath Sandhya Arghya: 30-min window leading up to sunset."""
    if not ctx.sunset:
        return None
    s_dt = ctx.sunset - timedelta(minutes=30)
    e_dt = ctx.sunset
    s, e, d = _fmt(s_dt, e_dt)
    return PujaMuhurat(
        "sandhya_arghya", "Sandhya Arghya", s, e, d,
        "Evening water offering at sunset",
    )


def _build_usha_arghya(ctx: _Ctx) -> PujaMuhurat | None:
    """Chhath Usha Arghya: 30-min window from sunrise."""
    if not ctx.sunrise:
        return None
    s_dt = ctx.sunrise
    e_dt = ctx.sunrise + timedelta(minutes=30)
    s, e, d = _fmt(s_dt, e_dt)
    return PujaMuhurat(
        "usha_arghya", "Usha Arghya", s, e, d,
        "Morning water offering at sunrise",
    )


_BUILDERS: dict[str, Callable[[_Ctx], PujaMuhurat | None]] = {
    "lakshmi_puja_diwali":     _build_lakshmi_puja_diwali,
    "pradosh_kaal":            _build_pradosh_kaal,
    "nishita_puja":            _build_nishita_puja,
    "nishita_with_tithi":      _build_mahanishita_with_tithi,
    "madhyahna_puja":          _build_madhyahna_puja,
    "aparahna_puja":           _build_aparahna_puja,
    "purvahna_puja":           _build_purvahna_puja,
    "sayahna_puja":            _build_sayahna_puja,
    "godhuli":                 _build_godhuli,
    "brahma_muhurat":          _build_brahma_muhurat,
    "moonrise_puja":           _build_moonrise_puja,
    "sandhya_arghya":          _build_sandhya_arghya,
    "usha_arghya":             _build_usha_arghya,
}


# Festival id -> ordered list of builder keys. Multiple muhurats per
# festival are emitted in this order. Festival ids not listed here
# produce an empty puja_muhurats list.
REGISTRY: dict[str, tuple[str, ...]] = {
    # ===== Diwali cluster =====
    "diwali":                              ("lakshmi_puja_diwali", "pradosh_kaal", "nishita_puja"),
    "diwali.diwali-date-muhurat":          ("lakshmi_puja_diwali", "pradosh_kaal", "nishita_puja"),
    "diwali.dhanteras":                    ("pradosh_kaal",),
    "diwali.dhanteras.dhanteras-date-muhurat": ("pradosh_kaal",),
    "diwali.narak-chaturdashi":            ("brahma_muhurat", "pradosh_kaal"),
    "diwali.narak-chaturdashi.narak-chaturdashi-date-muhurat": ("brahma_muhurat", "pradosh_kaal"),
    "diwali.govardhanpuja":                ("madhyahna_puja", "godhuli"),
    "diwali.govardhanpuja.govardhan-puja-date-muhurat": ("madhyahna_puja", "godhuli"),
    "diwali.bhai-dooj-date-muhurat":       ("madhyahna_puja", "aparahna_puja"),

    # ===== Karva Chauth / Sankashti (moonrise-based vratas) =====
    "karvachauth":                         ("pradosh_kaal", "moonrise_puja"),
    "karvachauth.karvachauth-date-moonrise-time": ("pradosh_kaal", "moonrise_puja"),
    "sankashti-chaturthi":                 ("moonrise_puja",),

    # ===== Shiva (Pradosh / Nishita) =====
    "shivratri":                           ("pradosh_kaal", "nishita_with_tithi"),
    "shivratri.mahashivratri":             ("nishita_with_tithi",),
    "shivratri.masik-shivratri":           ("nishita_with_tithi",),
    "pradosh-vrat":                        ("pradosh_kaal",),
    "sawan-somvar-vrat":                   ("brahma_muhurat", "pradosh_kaal"),

    # ===== Krishna / Vishnu =====
    "janmashtami":                         ("nishita_with_tithi",),
    "janmashtami.janmashtami":             ("nishita_with_tithi",),
    "dahi-handi":                          ("madhyahna_puja",),
    "jagannath-rath-yatra":                ("madhyahna_puja",),

    # ===== Ganesh =====
    "ganesh-chaturthi":                    ("madhyahna_puja",),
    "ganesh-chaturthi.ganesh-chaturthi":   ("madhyahna_puja",),
    "anant-chaturdashi":                   ("madhyahna_puja",),

    # ===== Ram / Hanuman =====
    "ram-navami":                          ("madhyahna_puja",),
    "rama-navami":                         ("madhyahna_puja",),
    "hanuman-jayanti":                     ("brahma_muhurat", "madhyahna_puja"),
    "hanuman-jayanti.chaitra-hanuman-jayanti": ("brahma_muhurat", "madhyahna_puja"),

    # ===== Durga / Navratri =====
    "navratri":                            ("purvahna_puja", "madhyahna_puja"),
    "navratri.chaitra-navratri":           ("purvahna_puja", "madhyahna_puja"),
    "navratri.sharad-navratri":            ("purvahna_puja", "madhyahna_puja"),
    "chaitra-navratri":                    ("purvahna_puja", "madhyahna_puja"),
    "navratri.ashadha-navratri":           ("madhyahna_puja",),
    "navratri.magha-navratri":             ("madhyahna_puja",),
    "gupta-navratri.ashadha":              ("madhyahna_puja",),
    "gupta-navratri.magha":                ("madhyahna_puja",),
    "durga-puja.mahalaya":                 ("aparahna_puja",),       # Pitru tarpan
    "durga-puja.saptami":                  ("madhyahna_puja",),
    "durga-puja.maha-ashtami":             ("madhyahna_puja", "nishita_puja"),
    "durga-puja.maha-navami":              ("madhyahna_puja",),
    "navratri.durga-puja":                 ("madhyahna_puja",),
    "navratri.durga-puja.durga-puja-date": ("madhyahna_puja",),
    # 9 Navratri days share Pratah/Madhyahna puja windows
    "chaitra-navratri.day1":               ("purvahna_puja", "madhyahna_puja"),
    "chaitra-navratri.day2":               ("madhyahna_puja",),
    "chaitra-navratri.day3":               ("madhyahna_puja",),
    "chaitra-navratri.day4":               ("madhyahna_puja",),
    "chaitra-navratri.day5":               ("madhyahna_puja",),
    "chaitra-navratri.day6":               ("madhyahna_puja",),
    "chaitra-navratri.day7":               ("madhyahna_puja",),
    "chaitra-navratri.day8":               ("madhyahna_puja", "nishita_puja"),
    "chaitra-navratri.day9":               ("madhyahna_puja",),
    "navratri.shailputri":                 ("madhyahna_puja",),
    "navratri.brahmacharini":              ("madhyahna_puja",),
    "navratri.chandraghanta":              ("madhyahna_puja",),
    "navratri.kushmanda":                  ("madhyahna_puja",),
    "navratri.skandmata":                  ("madhyahna_puja",),
    "navratri.katyayani":                  ("madhyahna_puja",),
    "navratri.kalratri":                   ("madhyahna_puja", "nishita_puja"),
    "navratri.mahagauri":                  ("madhyahna_puja",),
    "navratri.siddhidatri":                ("madhyahna_puja",),

    # ===== Dussehra (Vijaya Muhurat) =====
    "dussehra":                            ("aparahna_puja",),
    "dussehra.dussehra":                   ("aparahna_puja",),

    # ===== Holi =====
    "holi":                                ("pradosh_kaal",),
    "holi.holi-festival":                  ("madhyahna_puja",),
    "holi.holika-dahan":                   ("pradosh_kaal",),

    # ===== Saraswati / Basant =====
    "basant-panchmi":                      ("purvahna_puja",),
    "saraswati-puja":                      ("purvahna_puja",),

    # ===== Teej cluster =====
    "hartalika-teej":                      ("pradosh_kaal",),
    "hariyali-teej":                       ("pradosh_kaal",),
    "kajari-teej":                         ("pradosh_kaal", "moonrise_puja"),
    "teej":                                ("pradosh_kaal",),
    "teej.akshaya-tritiya":                ("madhyahna_puja",),

    # ===== Nag Panchami =====
    "nag-panchami":                        ("madhyahna_puja",),
    "nag-panchami.nag-panchami":           ("madhyahna_puja",),

    # ===== Raksha Bandhan / Upakarma =====
    "raksha-bandhan":                      ("aparahna_puja",),
    "avani-avittam":                       ("purvahna_puja",),

    # ===== Chhath =====
    "chhath-puja":                         ("sandhya_arghya", "usha_arghya"),
    "chhath-puja.nahay-khay":              ("brahma_muhurat",),
    "chhath-puja.kharna":                  ("pradosh_kaal",),
    "chhath-puja.usha-arghya":             ("usha_arghya",),
    "chaitra-chhath":                      ("sandhya_arghya", "usha_arghya"),
    "chaitra-chhath.nahay-khay":           ("brahma_muhurat",),
    "chaitra-chhath.kharna":               ("pradosh_kaal",),
    "chaitra-chhath.usha-arghya":          ("usha_arghya",),

    # ===== Vat Savitri / Vat Purnima =====
    "vat-savitri":                         ("purvahna_puja", "madhyahna_puja"),
    "vat-purnima":                         ("purvahna_puja", "madhyahna_puja"),

    # ===== Guru Purnima =====
    "guru-purnima":                        ("brahma_muhurat", "madhyahna_puja"),
    "guru-purnima.guru-purnima":           ("brahma_muhurat", "madhyahna_puja"),

    # ===== Sankranti / Ayana (Snan-daan: Brahma Muhurat) =====
    "sankranti":                           ("brahma_muhurat",),
    "makar-sankranti":                     ("brahma_muhurat", "madhyahna_puja"),
    "karka-sankranti":                     ("brahma_muhurat",),
    "pana-sankranti":                      ("brahma_muhurat",),
    "uttarayan":                           ("brahma_muhurat",),
    "dakshinayana":                        ("brahma_muhurat",),

    # ===== Regional New Year =====
    "gudi-padwa":                          ("purvahna_puja",),
    "gudi-padwa.gudi-padwa":               ("purvahna_puja",),
    "ugadi":                               ("purvahna_puja",),
    "ugadi.ugadi":                         ("purvahna_puja",),
    "cheti-chand":                         ("purvahna_puja",),
    "cheti-chand.cheti-chand":             ("purvahna_puja",),
    "baisakhi":                            ("brahma_muhurat", "madhyahna_puja"),
    "baisakhi.baisakhi":                   ("brahma_muhurat", "madhyahna_puja"),
    "puthandu":                            ("purvahna_puja",),
    "vishu":                               ("brahma_muhurat",),       # Vishukkani at dawn
    "pohela-boishakh":                     ("purvahna_puja",),
    "pohela-boishakh-bd":                  ("purvahna_puja",),
    "rongali-bihu":                        ("purvahna_puja",),
    "lohri":                               ("pradosh_kaal",),         # bonfire after sunset

    # ===== Pongal cluster =====
    "pongal":                              ("brahma_muhurat", "madhyahna_puja"),
    "pongal.bhogi":                        ("brahma_muhurat",),
    "pongal.mattu-pongal":                 ("madhyahna_puja",),
    "pongal.kaanum-pongal":                ("madhyahna_puja",),

    # ===== Onam =====
    "onam":                                ("purvahna_puja",),
    "onam.thiruvonam":                     ("purvahna_puja",),

    # ===== Purnima Snan parva =====
    "purnima.kartik-purnima":              ("brahma_muhurat", "pradosh_kaal"),  # Dev Diwali
    "purnima.magha-purnima":               ("brahma_muhurat",),
    "purnima.paush-purnima":               ("brahma_muhurat",),
    "purnima.vaishakha-purnima":           ("brahma_muhurat",),
    "purnima.chaitra-purnima":             ("brahma_muhurat",),
    "purnima.shravana-purnima":            ("brahma_muhurat",),
    "purnima.jyeshtha-purnima":            ("brahma_muhurat",),
    "purnima.ashwin-purnima":              ("brahma_muhurat", "nishita_puja"),  # Sharad Purnima
    "purnima.bhadrapada-purnima":          ("brahma_muhurat", "aparahna_puja"),  # Pitru Paksha start
    "purnima.margashirsha-purnima":        ("brahma_muhurat",),
    "purnima.phalguna-purnima":            ("brahma_muhurat", "pradosh_kaal"),   # Holika Dahan eve
    "dol-purnima":                         ("purvahna_puja",),

    # ===== Amavasya tarpan / snan =====
    "amavasya":                            ("aparahna_puja",),
    "amavasya.kartik-amavasya":            ("aparahna_puja", "pradosh_kaal"),
    "amavasya.magha-amavasya":             ("brahma_muhurat", "aparahna_puja"),  # Mauni Amavasya
    "amavasya.chaitra-amavasya":           ("aparahna_puja",),
    "amavasya.vaishakha-amavasya":         ("aparahna_puja",),
    "amavasya.jyeshtha-amavasya":          ("aparahna_puja",),                   # Shani Jayanti
    "amavasya.ashadha-amavasya":           ("aparahna_puja",),
    "amavasya.shravana-amavasya":          ("aparahna_puja",),                   # Hariyali Amavasya
    "amavasya.bhadrapada-amavasya":        ("aparahna_puja",),                   # Kushotpatini
    "amavasya.ashwin-amavasya":            ("aparahna_puja",),                   # Sarvapitri
    "amavasya.margashirsha-amavasya":      ("aparahna_puja",),
    "amavasya.phalguna-amavasya":          ("aparahna_puja",),
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def compute_puja_muhurats(
    festival_id: str,
    date: Date,
    snap,                       # _DaySnap; uses .sunrise_jd / .sunset_jd
    lat: float,
    lon: float,
    tz_name: str,
) -> list[PujaMuhurat]:
    """Return all puja muhurats configured for `festival_id` on `date`.

    Empty list when the festival has no registry entry or required
    rise/set instants are unavailable.
    """
    keys = REGISTRY.get(festival_id)
    if not keys or snap is None:
        return []
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        return []

    sunrise = (
        from_julian_day(snap.sunrise_jd, tz) if snap.sunrise_jd else None
    )
    sunset = (
        from_julian_day(snap.sunset_jd, tz) if snap.sunset_jd else None
    )
    # Next sunrise: probe at next-day midnight in tz.
    next_sunrise = None
    try:
        from .panchang import _rise_or_set  # type: ignore[attr-defined]
        jd_next_mid = to_julian_day(
            datetime.combine(date + timedelta(days=1), datetime.min.time(), tzinfo=tz)
        )
        ns_jd = _rise_or_set(jd_next_mid, swe.SUN, lon, lat, "rise")
        if ns_jd is not None:
            next_sunrise = from_julian_day(ns_jd, tz)
    except Exception:
        next_sunrise = None

    ctx = _Ctx(
        date=date, tz=tz, lat=lat, lon=lon,
        sunrise=sunrise, sunset=sunset, next_sunrise=next_sunrise,
    )

    out: list[PujaMuhurat] = []
    for key in keys:
        builder = _BUILDERS.get(key)
        if builder is None:
            continue
        try:
            m = builder(ctx)
        except Exception:
            m = None
        if m:
            out.append(m)
    return out
