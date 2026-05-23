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
  * Adhik-masa-only ekadashis (padmini, parama) — adhik masa not modeled.
  * Islamic / lunar-hijri events (ramzan) — not in this calendar.
  * `sawan-somvar-vrat` — every Monday in Shravana; needs a custom rule type.
  * Holiday duplicates that share their parent slug (e.g. `baisakhi.baisakhi`).
"""

from __future__ import annotations

from typing import Any


# (rule_type, rule_payload)
RULES: dict[str, tuple[str, dict[str, Any]]] = {

    # -------------------------------------------------------------------
    # Solar events
    # -------------------------------------------------------------------
    "makar-sankranti":      ("solar_event", {"event": "makar_sankranti"}),
    "uttarayan":            ("solar_event", {"event": "makar_sankranti"}),
    "pongal":               ("solar_event", {"event": "makar_sankranti"}),
    "baisakhi":             ("solar_event", {"event": "mesha_sankranti"}),
    "mesha-sankranti":      ("solar_event", {"event": "mesha_sankranti"}),
    "sankranti":            ("solar_event", {"event": "makar_sankranti"}),

    # -------------------------------------------------------------------
    # Gregorian
    # -------------------------------------------------------------------
    "lohri":     ("gregorian", {"month": 1, "day": 13}),
    "christmas": ("gregorian", {"month": 12, "day": 25}),

    # -------------------------------------------------------------------
    # Tithi-in-masa (single occurrence per year)
    # -------------------------------------------------------------------
    # Chaitra (sun in Mesha)
    "gudi-padwa":             ("tithi_in_masa", {"masa": "Chaitra", "paksha": "Shukla", "tithi": 1}),
    "ugadi":                  ("tithi_in_masa", {"masa": "Chaitra", "paksha": "Shukla", "tithi": 1}),
    "cheti-chand":            ("tithi_in_masa", {"masa": "Chaitra", "paksha": "Shukla", "tithi": 2}),
    "ram-navami":             ("tithi_in_masa", {"masa": "Chaitra", "paksha": "Shukla", "tithi": 9}),
    "hanuman-jayanti":        ("tithi_in_masa", {"masa": "Chaitra", "paksha": "Shukla", "tithi": 15}),

    # Vaishakha (sun in Vrishabha)
    "akshaya-tritiya":        ("tithi_in_masa", {"masa": "Vaishakha", "paksha": "Shukla", "tithi": 3}),

    # Ashadha (sun in Karka)
    "jagannath-rath-yatra":   ("tithi_in_amanta_masa", {"masa": "Ashadha", "paksha": "Shukla", "tithi": 2}),
    "guru-purnima":           ("tithi_in_masa", {"masa": "Ashadha", "paksha": "Shukla", "tithi": 15}),

    # Shravana (sun in Simha)
    "hariyali-teej":          ("tithi_in_masa", {"masa": "Shravana", "paksha": "Shukla", "tithi": 3}),
    "nag-panchami":           ("tithi_in_amanta_masa", {"masa": "Shravana", "paksha": "Shukla", "tithi": 5}),
    "raksha-bandhan":         ("tithi_in_masa", {"masa": "Shravana", "paksha": "Shukla", "tithi": 15}),

    # Bhadrapada (sun in Kanya)
    "kajari-teej":            ("tithi_in_masa", {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 3}),
    "hartalika-teej":         ("tithi_in_masa", {"masa": "Bhadrapada", "paksha": "Shukla", "tithi": 3}),
    "ganesh-chaturthi":       ("tithi_at_madhyahna", {"masa": "Bhadrapada", "paksha": "Shukla", "tithi": 4}),
    "janmashtami":            ("tithi_in_masa", {"masa": "Bhadrapada", "paksha": "Krishna", "tithi": 8}),
    "anant-chaturdashi":      ("tithi_in_masa", {"masa": "Bhadrapada", "paksha": "Shukla", "tithi": 14}),

    # Ashwin (sun in Tula)
    "navratri":               ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 1}),
    "navratri.sharad-navratri": ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 1}),
    "navratri.shailputri":    ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 1}),
    "navratri.brahmacharini": ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 2}),
    "navratri.chandraghanta": ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 3}),
    "navratri.kushmanda":     ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 4}),
    "navratri.skandmata":     ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 5}),
    "navratri.katyayani":     ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 6}),
    "navratri.kalratri":      ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 7}),
    "navratri.mahagauri":     ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 8}),
    "navratri.siddhidatri":   ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 9}),
    "navratri.durga-puja":    ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 6}),
    "dussehra":               ("tithi_in_masa", {"masa": "Ashwin", "paksha": "Shukla", "tithi": 10}),

    # Kartika (sun in Vrishchika)
    "karvachauth":            ("tithi_at_moonrise", {"masa": "Kartika", "paksha": "Krishna", "tithi": 4}),
    "diwali.dhanteras":       ("tithi_in_masa", {"masa": "Kartika", "paksha": "Krishna", "tithi": 13}),
    "diwali.narak-chaturdashi": ("tithi_in_masa", {"masa": "Kartika", "paksha": "Krishna", "tithi": 14}),
    "diwali":                 ("tithi_at_pradosha", {"masa": "Kartika", "paksha": "Krishna", "tithi": 15}),
    "diwali.govardhanpuja":   ("tithi_in_masa", {"masa": "Kartika", "paksha": "Shukla", "tithi": 1}),
    "diwali.bhai-dooj-date-muhurat": ("tithi_in_masa", {"masa": "Kartika", "paksha": "Shukla", "tithi": 2}),
    "chhath-puja":            ("tithi_in_masa", {"masa": "Kartika", "paksha": "Shukla", "tithi": 6}),

    # Magha (sun in Kumbha)
    "basant-panchmi":         ("tithi_in_masa", {"masa": "Magha", "paksha": "Shukla", "tithi": 5}),
    "saraswati-puja":         ("tithi_in_masa", {"masa": "Magha", "paksha": "Shukla", "tithi": 5}),

    # Phalguna (sun in Meena)
    "shivratri.mahashivratri": ("tithi_at_nishitha", {"masa": "Phalguna", "paksha": "Krishna", "tithi": 14}),
    "holi.holika-dahan":      ("tithi_in_masa", {"masa": "Phalguna", "paksha": "Shukla", "tithi": 15}),
    "holi":                   ("tithi_in_masa", {"masa": "Phalguna", "paksha": "Shukla", "tithi": 15}),
    "holi.holi-festival":     ("tithi_in_masa", {"masa": "Phalguna", "paksha": "Krishna", "tithi": 1}),

    # -------------------------------------------------------------------
    # Purnima per month (purnima.<masa>-purnima)
    # -------------------------------------------------------------------
    "purnima.chaitra-purnima":        ("tithi_in_masa", {"masa": "Chaitra",     "paksha": "Shukla", "tithi": 15}),
    "purnima.vaishakha-purnima":      ("tithi_in_masa", {"masa": "Vaishakha",   "paksha": "Shukla", "tithi": 15}),
    "purnima.jyeshtha-purnima":       ("tithi_in_masa", {"masa": "Jyeshtha",    "paksha": "Shukla", "tithi": 15}),
    "purnima.ashadha-purnima":        ("tithi_in_masa", {"masa": "Ashadha",     "paksha": "Shukla", "tithi": 15}),
    "purnima.shravana-purnima":       ("tithi_in_masa", {"masa": "Shravana",    "paksha": "Shukla", "tithi": 15}),
    "purnima.bhadrapada-purnima":     ("tithi_in_masa", {"masa": "Bhadrapada",  "paksha": "Shukla", "tithi": 15}),
    "purnima.ashwin-purnima":         ("tithi_in_masa", {"masa": "Ashwin",      "paksha": "Shukla", "tithi": 15}),
    "purnima.kartik-purnima":         ("tithi_in_masa", {"masa": "Kartika",     "paksha": "Shukla", "tithi": 15}),
    "purnima.margashirsha-purnima":   ("tithi_in_masa", {"masa": "Margashirsha","paksha": "Shukla", "tithi": 15}),
    "purnima.paush-purnima":          ("tithi_in_masa", {"masa": "Paush",       "paksha": "Shukla", "tithi": 15}),
    "purnima.magha-purnima":          ("tithi_in_masa", {"masa": "Magha",       "paksha": "Shukla", "tithi": 15}),
    "purnima.phalguna-purnima":       ("tithi_in_masa", {"masa": "Phalguna",    "paksha": "Shukla", "tithi": 15}),

    # -------------------------------------------------------------------
    # Amavasya per month (paksha=Krishna, tithi=15 in our naming)
    # -------------------------------------------------------------------
    "amavasya.chaitra-amavasya":      ("tithi_in_masa", {"masa": "Chaitra",     "paksha": "Krishna", "tithi": 15}),
    "amavasya.vaishakha-amavasya":    ("tithi_in_masa", {"masa": "Vaishakha",   "paksha": "Krishna", "tithi": 15}),
    "amavasya.jyeshtha-amavasya":     ("tithi_in_masa", {"masa": "Jyeshtha",    "paksha": "Krishna", "tithi": 15}),
    "amavasya.ashadha-amavasya":      ("tithi_in_masa", {"masa": "Ashadha",     "paksha": "Krishna", "tithi": 15}),
    "amavasya.shravana-amavasya":     ("tithi_in_masa", {"masa": "Shravana",    "paksha": "Krishna", "tithi": 15}),
    "amavasya.bhadrapada-amavasya":   ("tithi_in_masa", {"masa": "Bhadrapada",  "paksha": "Krishna", "tithi": 15}),
    "amavasya.ashwin-amavasya":       ("tithi_in_masa", {"masa": "Ashwin",      "paksha": "Krishna", "tithi": 15}),
    "amavasya.kartik-amavasya":       ("tithi_in_masa", {"masa": "Kartika",     "paksha": "Krishna", "tithi": 15}),
    "amavasya.margashirsha-amavasya": ("tithi_in_masa", {"masa": "Margashirsha","paksha": "Krishna", "tithi": 15}),
    "amavasya.magha-amavasya":        ("tithi_in_masa", {"masa": "Magha",       "paksha": "Krishna", "tithi": 15}),
    "amavasya.phalguna-amavasya":     ("tithi_in_masa", {"masa": "Phalguna",    "paksha": "Krishna", "tithi": 15}),

    # -------------------------------------------------------------------
    # Ekadashi (each has a fixed masa + paksha)
    # -------------------------------------------------------------------
    "ekadashi.kamada-ekadashi":          ("tithi_in_masa", {"masa": "Chaitra",     "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.varuthini-ekadashi":       ("tithi_in_masa", {"masa": "Vaishakha",   "paksha": "Krishna", "tithi": 11}),
    "ekadashi.mohini-ekadashi":          ("tithi_in_masa", {"masa": "Vaishakha",   "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.apara-ekadashi":           ("tithi_in_masa", {"masa": "Jyeshtha",    "paksha": "Krishna", "tithi": 11}),
    "ekadashi.nirjala-ekadashi":         ("tithi_in_masa", {"masa": "Jyeshtha",    "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.yogini-ekadashi":          ("tithi_in_masa", {"masa": "Ashadha",     "paksha": "Krishna", "tithi": 11}),
    "ashadi-ekadashi":                   ("tithi_in_masa", {"masa": "Ashadha",     "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.kamika-ekadashi":          ("tithi_in_masa", {"masa": "Shravana",    "paksha": "Krishna", "tithi": 11}),
    "ekadashi.shravana-putrada-ekadashi":("tithi_in_masa", {"masa": "Shravana",    "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.aja-ekadashi":             ("tithi_in_masa", {"masa": "Bhadrapada",  "paksha": "Krishna", "tithi": 11}),
    "ekadashi.parsva-ekadashi":          ("tithi_in_masa", {"masa": "Bhadrapada",  "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.indira-ekadashi":          ("tithi_in_masa", {"masa": "Ashwin",      "paksha": "Krishna", "tithi": 11}),
    "ekadashi.papankusha-ekadashi":      ("tithi_in_masa", {"masa": "Ashwin",      "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.rama-ekadashi":            ("tithi_in_masa", {"masa": "Kartika",     "paksha": "Krishna", "tithi": 11}),
    "ekadashi.devutthana-ekadashi":      ("tithi_in_masa", {"masa": "Kartika",     "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.utpanna-ekadashi":         ("tithi_in_masa", {"masa": "Margashirsha","paksha": "Krishna", "tithi": 11}),
    "ekadashi.mokshada-ekadashi":        ("tithi_in_masa", {"masa": "Margashirsha","paksha": "Shukla",  "tithi": 11}),
    "ekadashi.shattila-ekadashi":        ("tithi_in_masa", {"masa": "Paush",       "paksha": "Krishna", "tithi": 11}),
    "ekadashi.jaya-ekadashi":            ("tithi_in_masa", {"masa": "Magha",       "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.vijaya-ekadashi":          ("tithi_in_masa", {"masa": "Phalguna",    "paksha": "Krishna", "tithi": 11}),
    "ekadashi.amalaki-ekadashi":         ("tithi_in_masa", {"masa": "Phalguna",    "paksha": "Shukla",  "tithi": 11}),
    "ekadashi.papmochani-ekadashi":      ("tithi_in_masa", {"masa": "Chaitra",     "paksha": "Krishna", "tithi": 11}),

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
