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
    "makar-sankranti":      ("solar_event", {"event": "makar_sankranti"}),
    "uttarayan":            ("solar_event", {"event": "makar_sankranti"}),
    "pongal":               ("solar_event", {"event": "makar_sankranti"}),
    "baisakhi":             ("solar_event", {"event": "mesha_sankranti"}),
    "sankranti":            ("solar_event", {"event": "makar_sankranti"}),

    # -------------------------------------------------------------------
    # Gregorian
    # -------------------------------------------------------------------
    "lohri":     ("gregorian", {"month": 1, "day": 13}),
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
    #     the LATER of the two candidate days. Emit both, tagged per
    #     tradition, in each of purnimanta + amanta naming.
    "janmashtami":            ("multi_tradition", {"observances": [
        {"tradition": ["smarta", "purnimanta"], "rule_type": "tithi_in_masa",
         "rule": {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 8, "pin": "nishitha"}},
        {"tradition": ["smarta", "amanta"], "rule_type": "tithi_in_amanta_masa",
         "rule": {"masa": "Shravana", "paksha": "Krishna", "tithi": 8, "pin": "nishitha"}},
        {"tradition": ["vaishnava", "purnimanta"], "rule_type": "tithi_in_masa",
         "rule": {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 8, "dedup": "last"}},
        {"tradition": ["vaishnava", "amanta"], "rule_type": "tithi_in_amanta_masa",
         "rule": {"masa": "Shravana", "paksha": "Krishna", "tithi": 8, "dedup": "last"}},
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
    # Onam / Thiruvonam: Shravana nakshatra in Shravana masa (sun in Simha).
    "onam":            ("nakshatra_in_masa", {"masa": "Shravana", "nakshatra": "Shravana"}),
    "onam.thiruvonam": ("nakshatra_in_masa", {"masa": "Shravana", "nakshatra": "Shravana"}),
}


def seed_festival_rules() -> dict[str, int]:
    """
    Apply curated rules to the festivals table. Idempotent — UPDATEs only
    rows whose id is in RULES and whose rule_type is currently NULL or
    differs from the seed (so a manual override sticks until you remove it
    from the row or change the seed).

    Returns {'updated': n, 'unknown_ids': k}.
    """
    import json

    from .db import connect_rw

    conn = connect_rw()
    try:
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
        conn.commit()
        return {"updated": updated, "unknown_ids": unknown, "total_seed": len(RULES)}
    finally:
        conn.close()
