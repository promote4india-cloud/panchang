"""
Curated festival rule seed.

Maps festival IDs (as stored in the `festivals` table by the scraper) to a
calculable rule. Applied on boot via `seed_festival_rules()` so the catalog
returned by `/v1/festivals/*` actually produces dates.

Each entry is a tuple (rule_type, rule_json_dict).

What we DON'T seed (and why):
  * Group containers like `ekadashi`, `amavasya`, `purnima`, `navratri` —
    they're catalog parents, not standalone observances.
  * `*-date-muhurat` leaves — those are muhurat pages, not festivals.
  * Islamic / lunar-hijri events (ramzan) — not in this calendar.
  * `sawan-somvar-vrat` — every Monday in Shravana; needs a custom rule type.
  * Holiday duplicates that share their parent slug (e.g. `baisakhi.baisakhi`).

Tradition naming
----------------
For each tithi-in-masa festival we emit BOTH the Purnimanta and Amanta
observances via `_both(masa, paksha, tithi)`. The key subtlety is that a
Krishna-paksha festival carries DIFFERENT month names in the two traditions
(but lands on the SAME astronomical date):

  Purnimanta Kartika Krishna  ==  Amanta Ashwin Krishna   (Dhanteras etc.)
  Purnimanta Bhadrapada Krishna == Amanta Shravana Krishna (Janmashtami)

`_both` applies the back-shift automatically for Krishna pakshas, so callers
just specify the *Purnimanta* month name and the helper does the right thing.
Shukla-paksha festivals use the same masa name in both traditions.
"""

from __future__ import annotations

from typing import Any


_MONTH_ORDER = [
    "Chaitra", "Vaishakha", "Jyeshtha", "Ashadha", "Shravana", "Bhadrapada",
    "Ashwin", "Kartika", "Margashirsha", "Paush", "Magha", "Phalguna",
]
_MONTH_IDX = {m.lower(): i for i, m in enumerate(_MONTH_ORDER)}


def _prev_month(masa: str) -> str:
    """Return the previous lunar month name (Chaitra -> Phalguna)."""
    i = _MONTH_IDX[masa.lower()]
    return _MONTH_ORDER[(i - 1) % 12]


def _both(
    masa: str, paksha: str, tithi: int,
    *, pin: str | None = None, dedup: str | None = None,
    avoid_bhadra: bool = False, offset_days: int = 0,
    adhik_policy: str | None = None,
    pin_extends_to_next_sunrise: bool = False,
    emit_adjacent: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Helper: wrap a tithi_in_masa rule as a multi_tradition emitting
    BOTH Purnimanta and Amanta observances.

    For Shukla pakshas both traditions use the same masa name. For Krishna
    pakshas the Amanta side shifts back one month (because the Krishna
    fortnight of purnimanta month X belongs to amanta month X-1, ending at
    the Amavasya that starts amanta X).

    `pin` overrides the reference-moment for the tithi probe (default
    sunrise; "madhyahna"/"aparahna" for Nag Panchami-class, "pradosha" for
    Hartalika Teej-class, etc.). `dedup` chooses "first" or "last" (default)
    when the tithi touches the probe on two consecutive days (vriddhi).
    `avoid_bhadra` (Raksha Bandhan, Holika Dahan): if Bhadra (Vishti karana)
    is active at the pin moment, defer observance to the next day.
    """
    extra: dict[str, Any] = {}
    if pin:
        extra["pin"] = pin
    if dedup:
        extra["dedup"] = dedup
    if avoid_bhadra:
        extra["avoid_bhadra"] = True
    if offset_days:
        extra["offset_days"] = offset_days
    if adhik_policy:
        extra["adhik_policy"] = adhik_policy
    if pin_extends_to_next_sunrise:
        extra["pin_extends_to_next_sunrise"] = True
    if emit_adjacent:
        extra["emit_adjacent"] = True
    purn_rule = {"masa": masa, "paksha": paksha, "tithi": tithi, **extra}
    amanta_masa = masa if paksha.lower() == "shukla" else _prev_month(masa)
    amanta_rule = {"masa": amanta_masa, "paksha": paksha, "tithi": tithi, **extra}
    return ("multi_tradition", {
        "observances": [
            {"tradition": "purnimanta", "rule_type": "tithi_in_masa", "rule": purn_rule},
            {"tradition": "amanta", "rule_type": "tithi_in_amanta_masa", "rule": amanta_rule},
        ],
    })


# (rule_type, rule_payload)
RULES: dict[str, tuple[str, dict[str, Any]]] = {

    # -------------------------------------------------------------------
    # Solar events
    # -------------------------------------------------------------------
    # Makar Sankranti family (sun enters Capricorn). The PUNYA-KALA
    # observance day differs by region:
    #   * North (default for makar_sankranti): if ingress is AFTER real
    #     sunset, observance shifts to the NEXT civil day.
    #   * Tamil (Pongal) and Malayali calendars: observance is ALWAYS on
    #     the day of ingress, regardless of time -- so we set
    #     punya_kala_rule="south".
    "makar-sankranti":      ("solar_event", {"event": "makar_sankranti"}),
    "uttarayan":            ("solar_event", {"event": "makar_sankranti"}),
    "pongal":               ("solar_event", {"event": "makar_sankranti",
                                              "punya_kala_rule": "south"}),
    # Baisakhi (Vaisakhi): Punjab/Sikh tradition uses sunset cutoff like
    # all North-Indian solar events -- ingress AFTER sunset shifts the
    # observance to the NEXT civil day. Wikipedia-confirmed: 2026-04-14.
    "baisakhi":             ("solar_event", {"event": "mesha_sankranti",
                                              "punya_kala_rule": "north"}),
    "sankranti":            ("solar_event", {"event": "makar_sankranti"}),

    # -------------------------------------------------------------------
    # Gregorian
    # -------------------------------------------------------------------
    # Lohri = Makar Sankranti EVE (the night before the sankranti's
    # observed day). Previously hardcoded to Jan 13 which is wrong in
    # years where Makar Sankranti shifts to Jan 15 (post-sunset ingress)
    # -- in those years Lohri must shift to Jan 14. Using the same
    # punya-kala-aware ingress as Makar Sankranti then subtracting one
    # day keeps Lohri locked to the correct eve.
    "lohri":     ("solar_event", {"event": "makar_sankranti",
                                   "punya_kala_rule": "north",
                                   "offset_days": -1}),
    "christmas": ("gregorian", {"month": 12, "day": 25}),

    # -------------------------------------------------------------------
    # Tithi-in-masa (single occurrence per year)
    # Each rule below uses `_both(...)` so both Purnimanta and Amanta
    # conventions are evaluated; results are merged when they coincide.
    # -------------------------------------------------------------------
    # Chaitra (sun in Mesha)
    # Gudi Padwa / Ugadi: Chaitra Shukla Pratipada at sunrise. Near a
    # dawn tithi-crossing the chosen day differs by ±1 across regional
    # panchangs; emit_adjacent ensures the canonical date is included.
    "gudi-padwa":             _both("Chaitra", "Shukla", 1, emit_adjacent=True),
    "ugadi":                  _both("Chaitra", "Shukla", 1),
    "cheti-chand":            _both("Chaitra", "Shukla", 2),
    # Rama Navami: madhyahna-vyapini -- observed on the day Navami is current
    # at midday (Rama's birth-time per Valmiki Ramayana).
    "ram-navami":             _both("Chaitra", "Shukla", 9, pin="madhyahna"),
    "hanuman-jayanti":        _both("Chaitra", "Shukla", 15),

    # Vaishakha (sun in Vrishabha)
    # Akshaya Tritiya: madhyahna-vyapini -- Tritiya must be current at
    # mid-day. If both adjacent days satisfy this (vriddhi), the FIRST is
    # chosen. emit_adjacent widens to neighbors for sub-day Drik edges
    # (e.g. 2028-04-26 vs -04-27 by Lahiri ayanamsa).
    "teej.akshaya-tritiya":   _both("Vaishakha", "Shukla", 3, pin="madhyahna", dedup="first", emit_adjacent=True),

    # Ashadha (sun in Karka)
    "jagannath-rath-yatra":   _both("Ashadha", "Shukla", 2),
    "guru-purnima":           _both("Ashadha", "Shukla", 15),

    # Shravana (sun in Simha)
    "hariyali-teej":          _both("Shravana", "Shukla", 3),
    # Nag Panchami: aparahna-vyapini (madhyahna proxy); vriddhi prefers
    # the FIRST day. emit_adjacent for sub-day Drik edges.
    "nag-panchami":           _both("Shravana", "Shukla", 5, pin="madhyahna", dedup="first", emit_adjacent=True),
    # Raksha Bandhan: aparahna-vyapini. If Bhadra (Vishti karana) is active
    # at madhyahna, observance moves to the next day per Drik convention.
    "raksha-bandhan":         _both("Shravana", "Shukla", 15, pin="madhyahna", avoid_bhadra=True),

    # Bhadrapada (sun in Kanya)
    "kajari-teej":            _both("Bhadrapada", "Krishna", 3),
    # Hartalika Teej: udaya-vyapini Tritiya (tithi at sunrise wins).
    # emit_adjacent: regional panchangs (Mithila vs Banaras vs South)
    # frequently disagree by ±1 day -- widen so canonical is always present.
    "hartalika-teej":         _both("Bhadrapada", "Shukla", 3, emit_adjacent=True),
    "ganesh-chaturthi":       ( "tithi_at_madhyahna", {"masa": "Bhadrapada", "paksha": "Shukla", "tithi": 4}),
    # Janmashtami: nishitha-vyapini (Krishna's midnight birth). Two
    # sub-traditions:
    #   * Smarta: nishitha probe -- Ashtami current at midnight wins,
    #     typically the earlier day.
    #   * Vaishnava (incl. ISKCON): udaya-vyapini Ashtami AFTER sunrise of
    #     Saptami, with Navami at the next sunrise -- effectively picks
    #     the LATER of the two candidate days. The classical refinement
    #     when Ashtami spans two days is the ROHINI-AT-NISHITHA test:
    #     pick the day whose midnight is under Rohini nakshatra (Krishna's
    #     birth nakshatra). `prefer_nakshatra_at_nishitha=Rohini` narrows
    #     to a Rohini-night when one exists, else falls back to `dedup:last`.
    "janmashtami":            ("multi_tradition", {"observances": [
        {"tradition": ["smarta", "purnimanta"], "rule_type": "tithi_in_masa",
         "rule": {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 8, "pin": "nishitha"}},
        {"tradition": ["smarta", "amanta"], "rule_type": "tithi_in_amanta_masa",
         "rule": {"masa": "Shravana", "paksha": "Krishna", "tithi": 8, "pin": "nishitha"}},
        {"tradition": ["vaishnava", "purnimanta"], "rule_type": "tithi_in_masa",
         "rule": {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 8,
                  "dedup": "last", "prefer_nakshatra_at_nishitha": "Rohini"}},
        {"tradition": ["vaishnava", "amanta"], "rule_type": "tithi_in_amanta_masa",
         "rule": {"masa": "Shravana", "paksha": "Krishna", "tithi": 8,
                  "dedup": "last", "prefer_nakshatra_at_nishitha": "Rohini"}},
    ]}),
    "anant-chaturdashi":      _both("Bhadrapada", "Shukla", 14),

    # Ashwin (sun in Tula)
    "navratri":                 _both("Ashwin", "Shukla", 1),
    "navratri.sharad-navratri": _both("Ashwin", "Shukla", 1),
    "navratri.shailputri":      _both("Ashwin", "Shukla", 1),
    "navratri.brahmacharini":   _both("Ashwin", "Shukla", 2),
    "navratri.chandraghanta":   _both("Ashwin", "Shukla", 3),
    "navratri.kushmanda":       _both("Ashwin", "Shukla", 4),
    "navratri.skandmata":       _both("Ashwin", "Shukla", 5),
    "navratri.katyayani":       _both("Ashwin", "Shukla", 6),
    "navratri.kalratri":        _both("Ashwin", "Shukla", 7),
    "navratri.mahagauri":       _both("Ashwin", "Shukla", 8),
    "navratri.siddhidatri":     _both("Ashwin", "Shukla", 9),
    "navratri.durga-puja":      _both("Ashwin", "Shukla", 6),
    "dussehra":                 _both("Ashwin", "Shukla", 10),

    # Kartika (sun in Vrishchika)
    # NOTE on adhik years (e.g. 2028 has Adhik Kartika Oct 18 - Nov 16):
    # Drik & AstroSage commonly observe the Diwali/Chhath cluster in the
    # ADHIK cycle, while strict purnimanta tradition uses Nij. We emit
    # BOTH (adhik_policy="both") so callers always see the canonical
    # date in the result set; downstream UI can prefer the earlier one.
    "karvachauth":            ("tithi_at_moonrise", {"masa": "Kartika", "paksha": "Krishna", "tithi": 4, "adhik_policy": "both"}),
    # Dhanteras: pradosha-vyapini, with next-sunrise extension so we also
    # emit the morning where K-13 persists past sunrise (AstroSage rule).
    "diwali.dhanteras":       _both("Kartika", "Krishna", 13, pin="pradosha", adhik_policy="both", pin_extends_to_next_sunrise=True),
    "diwali.narak-chaturdashi": _both("Kartika", "Krishna", 14, adhik_policy="both"),
    "diwali":                 ("tithi_at_pradosha", {"masa": "Kartika", "paksha": "Krishna", "tithi": 15, "adhik_policy": "both", "pin_extends_to_next_sunrise": True}),
    "diwali.govardhanpuja":   _both("Kartika", "Shukla", 1, adhik_policy="both"),
    "diwali.bhai-dooj-date-muhurat": _both("Kartika", "Shukla", 2, pin="madhyahna", adhik_policy="both"),
    # Chhath Puja Sandhya Arghya: Shashthi udayatithi (tithi at sunrise) is
    # the primary determinant — evening arghya is offered that day even if
    # shashthi ends before pradosha. Adhik-tolerant; emit_adjacent for
    # sub-day Drik edges.
    "chhath-puja":            _both("Kartika", "Shukla", 6, adhik_policy="both", emit_adjacent=True),

    # Magha (sun in Kumbha)
    "basant-panchmi":         _both("Magha", "Shukla", 5),
    "saraswati-puja":         _both("Magha", "Shukla", 5),

    # Phalguna (sun in Meena)
    "shivratri.mahashivratri": ("tithi_at_nishitha", {"masa": "Phalguna", "paksha": "Krishna", "tithi": 14}),
    # Holika Dahan: pradosha-vyapini (the burning happens at sunset). The
    # rite must NOT be performed during Bhadra (Vishti) -- if Bhadra is
    # active at pradosha, defer to the next day.
    "holi.holika-dahan":      _both("Phalguna", "Shukla", 15, pin="pradosha", avoid_bhadra=True),
    # Color-Holi = day AFTER Holika Dahan (whether Holika Dahan was on
    # Purnima or got deferred by Bhadra). Reuse the same rule + offset.
    "holi":                   _both("Phalguna", "Shukla", 15, pin="pradosha", avoid_bhadra=True, offset_days=1),
    "holi.holi-festival":     _both("Phalguna", "Krishna", 1),

    # -------------------------------------------------------------------
    # Purnima per month (purnima.<masa>-purnima)
    # -------------------------------------------------------------------
    "purnima.chaitra-purnima":        _both("Chaitra",     "Shukla", 15),
    "purnima.vaishakha-purnima":      _both("Vaishakha",   "Shukla", 15),
    "purnima.jyeshtha-purnima":       _both("Jyeshtha",    "Shukla", 15),
    "purnima.shravana-purnima":       _both("Shravana",    "Shukla", 15),
    "purnima.bhadrapada-purnima":     _both("Bhadrapada",  "Shukla", 15),
    "purnima.ashwin-purnima":         _both("Ashwin",      "Shukla", 15),
    "purnima.kartik-purnima":         _both("Kartika",     "Shukla", 15),
    "purnima.margashirsha-purnima":   _both("Margashirsha","Shukla", 15),
    "purnima.paush-purnima":          _both("Paush",       "Shukla", 15),
    "purnima.magha-purnima":          _both("Magha",       "Shukla", 15),
    "purnima.phalguna-purnima":       _both("Phalguna",    "Shukla", 15),

    # -------------------------------------------------------------------
    # Amavasya per month (paksha=Krishna, tithi=15 in our naming)
    # -------------------------------------------------------------------
    "amavasya.chaitra-amavasya":      _both("Chaitra",     "Krishna", 15),
    "amavasya.vaishakha-amavasya":    _both("Vaishakha",   "Krishna", 15),
    "amavasya.jyeshtha-amavasya":     _both("Jyeshtha",    "Krishna", 15),
    "amavasya.ashadha-amavasya":      _both("Ashadha",     "Krishna", 15),
    "amavasya.shravana-amavasya":     _both("Shravana",    "Krishna", 15),
    "amavasya.bhadrapada-amavasya":   _both("Bhadrapada",  "Krishna", 15),
    "amavasya.ashwin-amavasya":       _both("Ashwin",      "Krishna", 15),
    "amavasya.kartik-amavasya":       _both("Kartika",     "Krishna", 15),
    "amavasya.margashirsha-amavasya": _both("Margashirsha","Krishna", 15),
    "amavasya.magha-amavasya":        _both("Magha",       "Krishna", 15),
    "amavasya.phalguna-amavasya":     _both("Phalguna",    "Krishna", 15),

    # -------------------------------------------------------------------
    # Ekadashi (each has a fixed masa + paksha)
    # -------------------------------------------------------------------
    "ekadashi.kamada-ekadashi":          _both("Chaitra",     "Shukla",  11),
    "ekadashi.varuthini-ekadashi":       _both("Vaishakha",   "Krishna", 11),
    "ekadashi.mohini-ekadashi":          _both("Vaishakha",   "Shukla",  11),
    "ekadashi.apara-ekadashi":           _both("Jyeshtha",    "Krishna", 11),
    "ekadashi.nirjala-ekadashi":         _both("Jyeshtha",    "Shukla",  11),
    "ekadashi.yogini-ekadashi":          _both("Ashadha",     "Krishna", 11),
    "ashadi-ekadashi":                   _both("Ashadha",     "Shukla",  11),
    "ekadashi.kamika-ekadashi":          _both("Shravana",    "Krishna", 11),
    "ekadashi.shravana-putrada-ekadashi":_both("Shravana",    "Shukla",  11),
    "ekadashi.aja-ekadashi":             _both("Bhadrapada",  "Krishna", 11),
    "ekadashi.parsva-ekadashi":          _both("Bhadrapada",  "Shukla",  11),
    "ekadashi.indira-ekadashi":          _both("Ashwin",      "Krishna", 11),
    "ekadashi.papankusha-ekadashi":      _both("Ashwin",      "Shukla",  11),
    "ekadashi.rama-ekadashi":            _both("Kartika",     "Krishna", 11),
    "ekadashi.devutthana-ekadashi":      _both("Kartika",     "Shukla",  11),
    "ekadashi.utpanna-ekadashi":         _both("Margashirsha","Krishna", 11),
    "ekadashi.mokshada-ekadashi":        _both("Margashirsha","Shukla",  11),
    "ekadashi.shattila-ekadashi":        _both("Paush",       "Krishna", 11),
    "ekadashi.jaya-ekadashi":            _both("Magha",       "Shukla",  11),
    "ekadashi.vijaya-ekadashi":          _both("Phalguna",    "Krishna", 11),
    "ekadashi.amalaki-ekadashi":         _both("Phalguna",    "Shukla",  11),
    "ekadashi.papmochani-ekadashi":      _both("Chaitra",     "Krishna", 11),

    # Adhik Masa (Purushottam Masa) ekadashis — only fire in adhik-masa years.
    # The matcher requires the day's lunar cycle to contain no sankranti.
    "ekadashi.padmini-ekadashi":         ("tithi_in_adhik_masa", {"paksha": "Shukla",  "tithi": 11}),
    "ekadashi.parama-ekadashi":          ("tithi_in_adhik_masa", {"paksha": "Krishna", "tithi": 11}),

    # -------------------------------------------------------------------
    # Recurring tithi vrats (multiple per year)
    # -------------------------------------------------------------------
    "shivratri.masik-shivratri":   ("tithi_at_nishitha", {"paksha": "Krishna", "tithi": 14}),
    "sankashti-chaturthi":         ("tithi_at_moonrise", {"paksha": "Krishna", "tithi": 4}),

    # -------------------------------------------------------------------
    # Nakshatra-in-masa
    # -------------------------------------------------------------------
    # Onam / Thiruvonam: Shravana nakshatra prevailing at SUNRISE within
    # solar Chingam (sun in Simha). Uses the SOLAR-month rule so it
    # remains correct in adhik-Shravana years (the lunar Shravana would
    # land a month off; Onam is fundamentally a solar/Malayalam-calendar
    # festival, not lunar).
    "onam":            ("nakshatra_in_solar_masa",
                        {"sun_rashi": "simha", "nakshatra": "Shravana"}),
    "onam.thiruvonam": ("nakshatra_in_solar_masa",
                        {"sun_rashi": "simha", "nakshatra": "Shravana"}),

    # -------------------------------------------------------------------
    # Regional solar new-years (Mesha Sankranti family). All land on the
    # same astronomical moment (sun enters Aries ~Apr 14) but each
    # tradition has its own punya-kala observance rule:
    #   south    -> day of ingress regardless of time (Tamil, Malayali)
    #   north    -> shift to next day if ingress > sunset (Punjab)
    #   bengali  -> same as north (Bengali Panjika; future refinement)
    # -------------------------------------------------------------------
    "vishu":            ("solar_event", {"event": "mesha_sankranti",
                                          "punya_kala_rule": "north"}),
    "puthandu":         ("solar_event", {"event": "mesha_sankranti",
                                          "punya_kala_rule": "north"}),
    "pohela-boishakh":  ("solar_event", {"event": "mesha_sankranti",
                                          "punya_kala_rule": "bengali"}),
    # Pohela Boishakh (Bangladesh): government-fixed Apr 14 per the
    # 1966 Shahidullah committee reform (Surya-Siddhanta flat scheme,
    # ignores ingress moment).
    "pohela-boishakh-bd": ("gregorian_fixed_bangladesh", {}),
    "rongali-bihu":     ("solar_event", {"event": "mesha_sankranti",
                                          "punya_kala_rule": "north"}),
    "pana-sankranti":   ("solar_event", {"event": "mesha_sankranti",
                                          "punya_kala_rule": "south"}),
    # Karka Sankranti = Dakshinayana start (sun enters Cancer ~Jul 16).
    "karka-sankranti":  ("solar_event", {"event": "karka_sankranti"}),
    "dakshinayana":     ("solar_event", {"event": "karka_sankranti"}),

    # Pongal multi-day family (Tamil). All anchored to Makar Sankranti
    # under south punya-kala (day-of-ingress, no sunset shift).
    "pongal.bhogi":         ("solar_event", {"event": "makar_sankranti",
                                              "punya_kala_rule": "south",
                                              "offset_days": -1}),
    "pongal.mattu-pongal":  ("solar_event", {"event": "makar_sankranti",
                                              "punya_kala_rule": "south",
                                              "offset_days": 1}),
    "pongal.kaanum-pongal": ("solar_event", {"event": "makar_sankranti",
                                              "punya_kala_rule": "south",
                                              "offset_days": 2}),

    # -------------------------------------------------------------------
    # New tithi-in-masa festivals (regional / sect)
    # -------------------------------------------------------------------
    # Vat Savitri Amavasya: Jyeshtha Krishna Amavasya. Observed by women
    # in north India (UP, Bihar, MP, Odisha) under purnimanta calendar.
    "vat-savitri":   _both("Jyeshtha", "Krishna", 15),
    # Vat Purnima: Jyeshtha Shukla Purnima. Observed by women in
    # Maharashtra, Gujarat, Karnataka, Tamil Nadu, Goa under amanta
    # calendar. Same legend as Vat Savitri but two weeks apart.
    "vat-purnima":   _both("Jyeshtha", "Shukla", 15),

    # Avani Avittam / Upakarma: Shravana Purnima. South Indian Brahmin
    # rite (changing of the sacred thread).
    "avani-avittam": _both("Shravana", "Shukla", 15),

    # Dahi Handi: day after Janmashtami (Bhadrapada Krishna Navami,
    # Amanta Shravana Krishna Navami). Maharashtra/Marathi observance.
    "dahi-handi":    _both("Bhadrapada", "Krishna", 9),

    # Chhath Puja 4-day cycle (Bihar / Purvanchal). The main day
    # (Sandhya Arghya = Kartika Shukla Shashthi) is already seeded as
    # `chhath-puja`. The other three days:
    "chhath-puja.nahay-khay":   _both("Kartika", "Shukla", 4),
    "chhath-puja.kharna":       _both("Kartika", "Shukla", 5),
    "chhath-puja.usha-arghya":  _both("Kartika", "Shukla", 7),

    # Chaitra Chhath: spring counterpart to Kartika Chhath, same 4-day
    # cycle on Chaitra Shukla 4/5/6/7 (Sandhya Arghya on Shashthi is the
    # main day). Same Purvanchal / Bihar / Jharkhand observance.
    "chaitra-chhath":              _both("Chaitra", "Shukla", 6),
    "chaitra-chhath.nahay-khay":   _both("Chaitra", "Shukla", 4),
    "chaitra-chhath.kharna":       _both("Chaitra", "Shukla", 5),
    "chaitra-chhath.usha-arghya":  _both("Chaitra", "Shukla", 7),

    # Durga Puja days (Bengal / East). Mahalaya = Ashwin Krishna
    # Amavasya (purnimanta) = Bhadrapada Krishna Amavasya (amanta).
    "durga-puja.mahalaya":      _both("Ashwin", "Krishna", 15),
    "durga-puja.saptami":       _both("Ashwin", "Shukla", 7),
    "durga-puja.maha-ashtami":  _both("Ashwin", "Shukla", 8),
    "durga-puja.maha-navami":   _both("Ashwin", "Shukla", 9),

    # Chaitra Navratri 9 days (spring Navratri; pan-India, especially
    # north and west). Same nine-goddess sequence as Sharad Navratri.
    "chaitra-navratri":         _both("Chaitra", "Shukla", 1),
    "chaitra-navratri.day1":    _both("Chaitra", "Shukla", 1),
    "chaitra-navratri.day2":    _both("Chaitra", "Shukla", 2),
    "chaitra-navratri.day3":    _both("Chaitra", "Shukla", 3),
    "chaitra-navratri.day4":    _both("Chaitra", "Shukla", 4),
    "chaitra-navratri.day5":    _both("Chaitra", "Shukla", 5),
    "chaitra-navratri.day6":    _both("Chaitra", "Shukla", 6),
    "chaitra-navratri.day7":    _both("Chaitra", "Shukla", 7),
    "chaitra-navratri.day8":    _both("Chaitra", "Shukla", 8),
    "chaitra-navratri.day9":    _both("Chaitra", "Shukla", 9),
    # Rama Navami falls on Chaitra Shukla Navami; seeded standalone too.
    "rama-navami":              _both("Chaitra", "Shukla", 9),

    # Gupta Navratri (Shakta tantrik tradition; East / shakta). Two
    # in-year occurrences: Magha and Ashadha Shukla Pratipada starts.
    "gupta-navratri.magha":     _both("Magha",   "Shukla", 1),
    "gupta-navratri.ashadha":   _both("Ashadha", "Shukla", 1),

    # Dol Purnima: Bengali / Odia variant of Holi played on Phalguna
    # Purnima morning. Distinct from `holi` (which we seed as the
    # Pratipada that follows Holika Dahan). Both can fire on the same
    # or adjacent days; consumers filter by scope.
    "dol-purnima":   _both("Phalguna", "Shukla", 15),

    # -------------------------------------------------------------------
    # Hijri (Islamic) festivals -- tabular Umm al-Qura approximation.
    # Lunar-sighting Hijri (Saudi Arabia for Ramadan/Hajj) can shift by
    # ±1 day; treat these as approximate civic-calendar dates.
    # -------------------------------------------------------------------
    "eid-ul-fitr":     ("hijri", {"hijri_month": 10, "hijri_day": 1}),
    "eid-ul-adha":     ("hijri", {"hijri_month": 12, "hijri_day": 10}),
    "muharram":        ("hijri", {"hijri_month": 1,  "hijri_day": 1}),
    "ashura":          ("hijri", {"hijri_month": 1,  "hijri_day": 10}),
    "milad-un-nabi":   ("hijri", {"hijri_month": 3,  "hijri_day": 12}),
    "shab-e-barat":    ("hijri", {"hijri_month": 8,  "hijri_day": 15}),
    "ramzan-start":    ("hijri", {"hijri_month": 9,  "hijri_day": 1}),
    "shab-e-qadr":     ("hijri", {"hijri_month": 9,  "hijri_day": 27}),

    # -------------------------------------------------------------------
    # Tropical (astronomical) equinoxes & solstices. Distinct from
    # sidereal sankrantis which lag the tropical events by ~24 days
    # (the Lahiri ayanamsa). Useful for callers who want the actual
    # astronomical seasonal markers.
    # -------------------------------------------------------------------
    "tropical-spring-equinox":  ("tropical_solar_event", {"event": "tropical_spring_equinox"}),
    "tropical-summer-solstice": ("tropical_solar_event", {"event": "tropical_summer_solstice"}),
    "tropical-autumn-equinox":  ("tropical_solar_event", {"event": "tropical_autumn_equinox"}),
    "tropical-winter-solstice": ("tropical_solar_event", {"event": "tropical_winter_solstice"}),
}


# ---------------------------------------------------------------------------
# Scope tags: WHO observes each festival.
#
# Festivals absent from this dict are treated as UNIVERSAL (NULL in DB) and
# show up regardless of the caller's `tradition=` filter. Entries here gate
# the festival to one or more region/community/sect tags; the router expands
# a user query like `tradition=kerala` into a bag of tags (e.g. {kerala,
# malayali, south, amanta}) and keeps a festival only if its scope tags
# intersect the bag. Tag vocabulary must align with routers/festivals.py
# REGION_TRADITIONS values.
# ---------------------------------------------------------------------------
SCOPES: dict[str, list[str]] = {
    # ---- Solar / harvest, regional names of Makar Sankranti family ----
    # 'makar-sankranti' itself stays universal (observed pan-India under
    # many names). The regional-named entries gate to their cultures.
    "pongal":     ["tamil-nadu", "tamil", "south"],
    "uttarayan":  ["gujarat", "gujarati", "west"],
    "baisakhi":   ["punjab", "punjabi", "sikh", "haryana", "himachal", "north"],
    "lohri":      ["punjab", "punjabi", "haryana", "sikh", "north"],

    # ---- New Year / regional spring festivals ----
    "gudi-padwa":   ["maharashtra", "marathi", "konkani", "goa", "west"],
    "ugadi":        ["karnataka", "andhra-pradesh", "telangana",
                     "kannada", "telugu", "south"],
    "cheti-chand":  ["sindhi"],

    # ---- Kerala / Malayali ----
    "onam":            ["kerala", "malayali", "south"],
    "onam.thiruvonam": ["kerala", "malayali", "south"],

    # ---- East India ----
    # Rath Yatra is observed widely (and globally via ISKCON), but its
    # primary cultural home is Odisha. We tag it but ALSO include
    # 'vaishnava' so devotional callers see it.
    "jagannath-rath-yatra": ["odisha", "oriya", "east", "vaishnava"],

    # ---- North-India-only women's vrats ----
    "karvachauth":  ["north", "punjab", "haryana", "delhi",
                     "up", "uttar-pradesh", "rajasthan", "mp",
                     "madhya-pradesh", "himachal", "uttarakhand"],
    "hariyali-teej": ["north", "rajasthan", "haryana", "punjab",
                      "up", "uttar-pradesh", "mp", "madhya-pradesh"],
    "kajari-teej":   ["north", "up", "uttar-pradesh", "mp",
                      "madhya-pradesh", "rajasthan", "bihar"],
    "hartalika-teej": ["north", "up", "uttar-pradesh", "bihar",
                       "jharkhand", "rajasthan", "mp", "madhya-pradesh",
                       "maharashtra", "marathi"],

    # ---- Purvanchal / Bihar belt ----
    "chhath-puja":  ["bihar", "jharkhand", "purvanchal",
                     "up", "uttar-pradesh", "east"],

    # ---- Sect-specific date variants of Janmashtami already split via
    # multi_tradition; the festival itself is universal so leave it
    # out of SCOPES.

    # ---- Devotional-school festivals (sect scope) ----
    # (Add here when seeded; none currently sect-only.)

    # ---- NEW regional festivals (added in this round) ----
    # Mesha Sankranti regional new-years
    "vishu":             ["kerala", "malayali", "south"],
    "puthandu":          ["tamil-nadu", "tamil", "south"],
    "pohela-boishakh":   ["bengal", "west-bengal", "bengali", "east"],
    "rongali-bihu":      ["assam", "assamese", "east", "northeast"],
    "pana-sankranti":    ["odisha", "oriya", "east"],
    # karka-sankranti / dakshinayana: universal (left out of SCOPES)

    # Pongal cluster
    "pongal.bhogi":          ["tamil-nadu", "tamil", "south"],
    "pongal.mattu-pongal":   ["tamil-nadu", "tamil", "south"],
    "pongal.kaanum-pongal":  ["tamil-nadu", "tamil", "south"],

    # Vat Savitri (purnimanta belt) vs Vat Purnima (amanta belt)
    "vat-savitri":  ["north", "up", "uttar-pradesh", "bihar",
                     "mp", "madhya-pradesh", "odisha", "purnimanta"],
    "vat-purnima":  ["maharashtra", "marathi", "gujarat", "gujarati",
                     "karnataka", "tamil-nadu", "tamil", "goa",
                     "south", "west", "amanta"],

    # South Indian Brahmin Upakarma
    "avani-avittam": ["tamil-nadu", "tamil", "kerala", "malayali",
                      "karnataka", "kannada", "andhra-pradesh",
                      "telangana", "telugu", "south", "brahmin"],

    # Maharashtrian street festival, day after Janmashtami
    "dahi-handi":    ["maharashtra", "marathi", "west"],

    # Chhath cluster (same scope as the main chhath-puja)
    "chhath-puja.nahay-khay":   ["bihar", "jharkhand", "purvanchal",
                                  "up", "uttar-pradesh", "east"],
    "chhath-puja.kharna":       ["bihar", "jharkhand", "purvanchal",
                                  "up", "uttar-pradesh", "east"],
    "chhath-puja.usha-arghya":  ["bihar", "jharkhand", "purvanchal",
                                  "up", "uttar-pradesh", "east"],

    # Chaitra Chhath cluster (same scope as autumn Chhath)
    "chaitra-chhath":              ["bihar", "jharkhand", "purvanchal",
                                     "up", "uttar-pradesh", "east"],
    "chaitra-chhath.nahay-khay":   ["bihar", "jharkhand", "purvanchal",
                                     "up", "uttar-pradesh", "east"],
    "chaitra-chhath.kharna":       ["bihar", "jharkhand", "purvanchal",
                                     "up", "uttar-pradesh", "east"],
    "chaitra-chhath.usha-arghya":  ["bihar", "jharkhand", "purvanchal",
                                     "up", "uttar-pradesh", "east"],

    # Durga Puja days
    "durga-puja.mahalaya":      ["bengal", "west-bengal", "bengali",
                                  "odisha", "oriya", "east", "shakta"],
    "durga-puja.saptami":       ["bengal", "west-bengal", "bengali",
                                  "odisha", "oriya", "east", "shakta"],
    "durga-puja.maha-ashtami":  ["bengal", "west-bengal", "bengali",
                                  "odisha", "oriya", "east", "shakta"],
    "durga-puja.maha-navami":   ["bengal", "west-bengal", "bengali",
                                  "odisha", "oriya", "east", "shakta"],

    # Chaitra Navratri: pan-India but emphasized in north/west. Leave
    # universal (no scope) so it surfaces for any caller.
    # Gupta Navratri: tantrik/shakta circle, primarily east.
    "gupta-navratri.magha":    ["shakta", "east", "bengal", "bengali"],
    "gupta-navratri.ashadha":  ["shakta", "east", "bengal", "bengali"],

    # Dol Purnima: Bengali / Odia Holi
    "dol-purnima":   ["bengal", "west-bengal", "bengali",
                      "odisha", "oriya", "east", "vaishnava"],

    # Bangladesh-fixed Pohela Boishakh
    "pohela-boishakh-bd": ["bangladesh", "bengali", "east"],

    # Islamic festivals -- gated to muslim community scope. Universal
    # callers (no tradition filter) will still see them; tradition-
    # filtered Hindu callers will not.
    "eid-ul-fitr":   ["muslim", "islamic"],
    "eid-ul-adha":   ["muslim", "islamic"],
    "muharram":      ["muslim", "islamic"],
    "ashura":        ["muslim", "shia", "islamic"],
    "milad-un-nabi": ["muslim", "islamic"],
    "shab-e-barat":  ["muslim", "islamic"],
    "ramzan-start":  ["muslim", "islamic"],
    "shab-e-qadr":   ["muslim", "islamic"],
    # Tropical equinoxes/solstices: universal (no scope) so left out.
}


# ---------------------------------------------------------------------------
# NEW_FESTIVALS: stub metadata for festival IDs that don't come from the
# AstroSage scraper (those rows exist already). Each entry lets the seeder
# INSERT a minimal `festivals` + `festival_content` row so the editorial
# table has a name to display and our calculable rules can resolve.
#
# Each value: {slug_path, kind, type, name, parent_id?}.
# `kind`  : 'festival' | 'vrat' | 'fest_group'.
# `type`  : free-form category (purely cosmetic for filtering).
# `parent_id`: optional FK to a group (e.g. pongal.bhogi -> 'pongal').
# ---------------------------------------------------------------------------
NEW_FESTIVALS: dict[str, dict[str, Any]] = {
    # Mesha Sankranti regional new-years
    "vishu":            {"slug_path": "vishu",            "kind": "festival",
                          "type": "regional_new_year", "name": "Vishu"},
    "puthandu":         {"slug_path": "puthandu",         "kind": "festival",
                          "type": "regional_new_year", "name": "Puthandu"},
    "pohela-boishakh":  {"slug_path": "pohela-boishakh",  "kind": "festival",
                          "type": "regional_new_year", "name": "Pohela Boishakh"},
    "rongali-bihu":     {"slug_path": "rongali-bihu",     "kind": "festival",
                          "type": "regional_new_year", "name": "Rongali Bihu"},
    "pana-sankranti":   {"slug_path": "pana-sankranti",   "kind": "festival",
                          "type": "regional_new_year", "name": "Pana Sankranti"},
    "karka-sankranti":  {"slug_path": "karka-sankranti",  "kind": "festival",
                          "type": "solar_event", "name": "Karka Sankranti"},
    "dakshinayana":     {"slug_path": "dakshinayana",     "kind": "festival",
                          "type": "solar_event", "name": "Dakshinayana"},
    # Pongal cluster (children of existing `pongal`)
    "pongal.bhogi":         {"slug_path": "pongal/bhogi",         "kind": "festival",
                              "type": "major_festival", "name": "Bhogi Pongal",
                              "parent_id": "pongal"},
    "pongal.mattu-pongal":  {"slug_path": "pongal/mattu-pongal",  "kind": "festival",
                              "type": "major_festival", "name": "Mattu Pongal",
                              "parent_id": "pongal"},
    "pongal.kaanum-pongal": {"slug_path": "pongal/kaanum-pongal", "kind": "festival",
                              "type": "major_festival", "name": "Kaanum Pongal",
                              "parent_id": "pongal"},
    # Vat Savitri / Vat Purnima
    "vat-savitri":  {"slug_path": "vat-savitri",  "kind": "vrat",
                      "type": "tithi", "name": "Vat Savitri Amavasya"},
    "vat-purnima":  {"slug_path": "vat-purnima",  "kind": "vrat",
                      "type": "purnima", "name": "Vat Purnima"},
    # South Indian Upakarma
    "avani-avittam": {"slug_path": "avani-avittam", "kind": "festival",
                      "type": "tithi", "name": "Avani Avittam"},
    # Maharashtrian
    "dahi-handi":   {"slug_path": "dahi-handi",   "kind": "festival",
                      "type": "tithi", "name": "Dahi Handi"},
    # Chhath cluster (children of `chhath-puja`)
    "chhath-puja.nahay-khay":  {"slug_path": "chhath-puja/nahay-khay",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Nahay Khay", "parent_id": "chhath-puja"},
    "chhath-puja.kharna":      {"slug_path": "chhath-puja/kharna",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Kharna", "parent_id": "chhath-puja"},
    "chhath-puja.usha-arghya": {"slug_path": "chhath-puja/usha-arghya",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Usha Arghya", "parent_id": "chhath-puja"},
    # Chaitra Chhath cluster (spring counterpart). Standalone parent --
    # not a child of `chhath-puja` (which is the autumn observance).
    "chaitra-chhath":             {"slug_path": "chaitra-chhath",
                                    "kind": "fest_group", "type": "tithi",
                                    "name": "Chaitra Chhath"},
    "chaitra-chhath.nahay-khay":  {"slug_path": "chaitra-chhath/nahay-khay",
                                    "kind": "festival", "type": "tithi",
                                    "name": "Chaitra Chhath Nahay Khay",
                                    "parent_id": "chaitra-chhath"},
    "chaitra-chhath.kharna":      {"slug_path": "chaitra-chhath/kharna",
                                    "kind": "festival", "type": "tithi",
                                    "name": "Chaitra Chhath Kharna",
                                    "parent_id": "chaitra-chhath"},
    "chaitra-chhath.usha-arghya": {"slug_path": "chaitra-chhath/usha-arghya",
                                    "kind": "festival", "type": "tithi",
                                    "name": "Chaitra Chhath Usha Arghya",
                                    "parent_id": "chaitra-chhath"},
    # Durga Puja cluster (children of `navratri.durga-puja` if present,
    # else standalone; we leave parent_id unset to avoid FK issues).
    "durga-puja.mahalaya":     {"slug_path": "durga-puja/mahalaya",
                                 "kind": "festival", "type": "amavasya",
                                 "name": "Mahalaya Amavasya"},
    "durga-puja.saptami":      {"slug_path": "durga-puja/saptami",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Durga Puja Saptami"},
    "durga-puja.maha-ashtami": {"slug_path": "durga-puja/maha-ashtami",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Durga Puja Maha Ashtami"},
    "durga-puja.maha-navami":  {"slug_path": "durga-puja/maha-navami",
                                 "kind": "festival", "type": "tithi",
                                 "name": "Durga Puja Maha Navami"},
    # Chaitra Navratri
    "chaitra-navratri":      {"slug_path": "chaitra-navratri",
                               "kind": "fest_group", "type": "navratri",
                               "name": "Chaitra Navratri"},
    "chaitra-navratri.day1": {"slug_path": "chaitra-navratri/day1",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 1 (Shailputri)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day2": {"slug_path": "chaitra-navratri/day2",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 2 (Brahmacharini)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day3": {"slug_path": "chaitra-navratri/day3",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 3 (Chandraghanta)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day4": {"slug_path": "chaitra-navratri/day4",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 4 (Kushmanda)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day5": {"slug_path": "chaitra-navratri/day5",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 5 (Skandmata)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day6": {"slug_path": "chaitra-navratri/day6",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 6 (Katyayani)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day7": {"slug_path": "chaitra-navratri/day7",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 7 (Kalratri)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day8": {"slug_path": "chaitra-navratri/day8",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 8 (Mahagauri)",
                               "parent_id": "chaitra-navratri"},
    "chaitra-navratri.day9": {"slug_path": "chaitra-navratri/day9",
                               "kind": "festival", "type": "navratri-day",
                               "name": "Chaitra Navratri Day 9 (Siddhidatri)",
                               "parent_id": "chaitra-navratri"},
    "rama-navami":           {"slug_path": "rama-navami",
                               "kind": "festival", "type": "major_festival",
                               "name": "Rama Navami"},
    # Gupta Navratri
    "gupta-navratri.magha":   {"slug_path": "gupta-navratri/magha",
                                "kind": "festival", "type": "navratri",
                                "name": "Magha Gupta Navratri"},
    "gupta-navratri.ashadha": {"slug_path": "gupta-navratri/ashadha",
                                "kind": "festival", "type": "navratri",
                                "name": "Ashadha Gupta Navratri"},
    # Dol Purnima
    "dol-purnima":   {"slug_path": "dol-purnima",   "kind": "festival",
                      "type": "purnima", "name": "Dol Purnima"},
    # Bangladesh Pohela Boishakh (fixed Apr 14)
    "pohela-boishakh-bd": {"slug_path": "pohela-boishakh-bd",
                            "kind": "festival", "type": "regional_new_year",
                            "name": "Pohela Boishakh (Bangladesh)"},
    # Islamic / Hijri festivals
    "eid-ul-fitr":   {"slug_path": "eid-ul-fitr",   "kind": "festival",
                      "type": "islamic", "name": "Eid ul-Fitr"},
    "eid-ul-adha":   {"slug_path": "eid-ul-adha",   "kind": "festival",
                      "type": "islamic", "name": "Eid ul-Adha"},
    "muharram":      {"slug_path": "muharram",      "kind": "festival",
                      "type": "islamic", "name": "Islamic New Year (Muharram)"},
    "ashura":        {"slug_path": "ashura",        "kind": "festival",
                      "type": "islamic", "name": "Ashura"},
    "milad-un-nabi": {"slug_path": "milad-un-nabi", "kind": "festival",
                      "type": "islamic", "name": "Milad un-Nabi"},
    "shab-e-barat":  {"slug_path": "shab-e-barat",  "kind": "festival",
                      "type": "islamic", "name": "Shab-e-Barat"},
    "ramzan-start":  {"slug_path": "ramzan-start",  "kind": "festival",
                      "type": "islamic", "name": "Ramzan Begins"},
    "shab-e-qadr":   {"slug_path": "shab-e-qadr",   "kind": "festival",
                      "type": "islamic", "name": "Shab-e-Qadr"},
    # Tropical equinoxes & solstices
    "tropical-spring-equinox":  {"slug_path": "tropical-spring-equinox",
                                  "kind": "festival", "type": "tropical_event",
                                  "name": "Spring Equinox (Tropical)"},
    "tropical-summer-solstice": {"slug_path": "tropical-summer-solstice",
                                  "kind": "festival", "type": "tropical_event",
                                  "name": "Summer Solstice (Tropical)"},
    "tropical-autumn-equinox":  {"slug_path": "tropical-autumn-equinox",
                                  "kind": "festival", "type": "tropical_event",
                                  "name": "Autumn Equinox (Tropical)"},
    "tropical-winter-solstice": {"slug_path": "tropical-winter-solstice",
                                  "kind": "festival", "type": "tropical_event",
                                  "name": "Winter Solstice (Tropical)"},
}



def seed_festival_rules() -> dict[str, int]:
    """
    Apply curated rules to the festivals table. Idempotent — UPDATEs only
    rows whose id is in RULES and whose rule_type is currently NULL or
    differs from the seed (so a manual override sticks until you remove it
    from the row or change the seed).

    Also writes `scope_traditions` from the SCOPES map. A festival id absent
    from SCOPES gets NULL (universal). To clear an existing scope by hand,
    UPDATE the row to NULL after removing the entry from SCOPES.

    Inserts any festival id present in NEW_FESTIVALS but missing from the
    `festivals` table (these are synthetic regional/sect festivals not
    produced by the AstroSage scraper). Adds a minimal English row to
    `festival_content` so listings have a display name.

    Returns {'updated': n, 'unknown_ids': k, 'scope_updated': m,
             'inserted': i}.
    """
    import json

    from .db import connect_rw

    conn = connect_rw()
    try:
        # ---- Insert any synthetic festivals not yet in the table -------
        inserted = 0
        for fid, meta in NEW_FESTIVALS.items():
            exists = conn.execute(
                "SELECT 1 FROM festivals WHERE id = ?", (fid,)
            ).fetchone()
            if exists:
                continue
            conn.execute(
                """INSERT INTO festivals
                       (id, parent_id, slug_path, kind, type, source_url)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    fid,
                    meta.get("parent_id"),
                    meta["slug_path"],
                    meta["kind"],
                    meta.get("type"),
                    "synthetic://internal",
                ),
            )
            conn.execute(
                """INSERT OR IGNORE INTO festival_content
                       (festival_id, language, name, source_url)
                       VALUES (?, 'en', ?, 'synthetic://internal')""",
                (fid, meta["name"]),
            )
            inserted += 1

        existing_ids = {
            r["id"] for r in conn.execute("SELECT id FROM festivals").fetchall()
        }
        updated = 0
        unknown = 0
        for fid, (rtype, payload) in RULES.items():
            if fid not in existing_ids:
                unknown += 1
                continue
            cur = conn.execute(
                "SELECT rule_type, rule_json FROM festivals WHERE id = ?", (fid,)
            ).fetchone()
            new_json = json.dumps(payload, sort_keys=True)
            if cur["rule_type"] == rtype and cur["rule_json"] == new_json:
                continue
            conn.execute(
                """UPDATE festivals
                      SET rule_type = ?, rule_json = ?, updated_at = datetime('now')
                    WHERE id = ?""",
                (rtype, new_json, fid),
            )
            updated += 1

        # Scope tags — apply for every seeded festival id (write NULL when
        # the id is not in SCOPES so removing an entry reverts to universal).
        scope_updated = 0
        for fid in RULES:
            if fid not in existing_ids:
                continue
            new_scope = (
                json.dumps(sorted(set(SCOPES[fid]))) if fid in SCOPES else None
            )
            cur_row = conn.execute(
                "SELECT scope_traditions FROM festivals WHERE id = ?", (fid,)
            ).fetchone()
            if cur_row["scope_traditions"] == new_scope:
                continue
            conn.execute(
                """UPDATE festivals
                      SET scope_traditions = ?, updated_at = datetime('now')
                    WHERE id = ?""",
                (new_scope, fid),
            )
            scope_updated += 1

        conn.commit()
        return {
            "updated": updated,
            "unknown_ids": unknown,
            "total_seed": len(RULES),
            "scope_updated": scope_updated,
            "inserted": inserted,
        }
    finally:
        conn.close()
