# Panchang App — Backend API Endpoint Specification

Derived from the Penpot design `panchang` (file `bdb38471-86c5-8118-8008-091c1e01ef0d`),
which contains 11 mobile-app screens. Each endpoint below is justified by one or more screens.

> **⚠️ Scope update (revised plan):** All user-scoped endpoints — sections **§7 Reminders**,
> **§8 User Profile & Settings**, **§9 Location** (write side), and **§12 Auth** — are **no
> longer part of the backend**. That data lives entirely on the device (Hive + sqflite in
> the Flutter app) and reminders fire via `flutter_local_notifications`. The server is now
> stateless and public-read-only. Those sections are kept below for design reference but
> are marked as `[LOCAL-ONLY]`. The **effective backend endpoint count is ~22**, all `GET`.
> See [panchang-implementation-plan.md](panchang-implementation-plan.md) for the full
> architecture.

All endpoints are versioned under `/v1`. Default response format: `application/json`.
All "today" / date-aware endpoints accept these common query parameters unless noted:

| Param      | Type           | Notes                                                                                  |
|------------|----------------|----------------------------------------------------------------------------------------|
| `date`     | `YYYY-MM-DD`   | Defaults to user's local "today".                                                       |
| `lat`,`lon`| number         | Required for all astronomical calculations (sunrise, muhurat, tithi end-times, etc.).   |
| `tz`       | IANA tz string | e.g. `Asia/Kolkata`. Defaults to location's tz.                                         |
| `language` | ISO code       | `en`, `hi`, `bn`, `ta`, `te`, `mr`, `gu`, `kn`, `ml`, `pa`, `sa`, `or` (12 supported).  |

Auth: `Authorization: Bearer <jwt>` for user-scoped endpoints (reminders, profile, settings).

---

## 1. Panchang — Daily Dashboard

> **Screen:** `Daily Panchang Dashboard (Vibrant)`
> Fields shown: date, weekday, Vaishakha Shukla Tritiya, Festival Today (Parshurama Jayanti),
> Tithi (Shukla Tritiya), Nakshatra (Rohini), Sunrise (5:45 AM), Sunset (6:45 PM),
> Shubh Muhurat (11:50–12:45), Rahu Kaal (2:00–3:30), Daily Rashifal excerpt, Upcoming events strip.

### `GET /v1/panchang/today`
One-shot aggregate that powers the dashboard.
- **Query:** `date`, `lat`, `lon`, `tz`, `language`
- **Response (abridged):**
```json
{
  "date": "2026-05-16",
  "weekday": "Tuesday",
  "vikram_samvat": 2083,
  "masa": "Vaishakha",
  "paksha": "Shukla",
  "tithi": { "name": "Tritiya", "ends_at": "..." },
  "nakshatra": { "name": "Rohini", "ends_at": "..." },
  "yoga": { "name": "Saubhagya", "ends_at": "..." },
  "karana": { "name": "Vanij", "ends_at": "..." },
  "sun": { "rise": "05:45", "set": "18:45" },
  "festival_today": { "id": "parshurama-jayanti", "name": "Parshurama Jayanti" },
  "muhurat_summary": {
    "shubh":     { "label": "Shubh Muhurat", "start": "11:50", "end": "12:45" },
    "rahu_kaal": { "label": "Rahu Kaal",     "start": "14:00", "end": "15:30" }
  },
  "rashifal_excerpt": { "sign": "aries", "text": "..." },
  "upcoming_event_preview": { "date": "2026-05-19", "name": "Mohini Ekadashi" }
}
```

---

## 2. Tithi & Nakshatra Detail

> **Screen:** `Tithi & Nakshatra (Detail)`
> Tithi name, end time, paksha, lord; Nakshatra name, end time, symbol, deity, element;
> Yoga, Karana, Sun sign, Moon sign.

### `GET /v1/panchang/tithi-nakshatra`
- **Query:** `date`, `lat`, `lon`, `tz`, `language`
- **Response:**
```json
{
  "tithi": {
    "name": "Shukla Trayodashi",
    "ends_at_local": "21:46",
    "paksha": "Shukla (Bright)",
    "lord": "Kamadeva"
  },
  "nakshatra": {
    "name": "Rohini",
    "ends_at_local": "03:12+1",
    "symbol": "Ox Cart",
    "deity": "Brahma",
    "element": "Earth"
  },
  "yoga":   { "name": "Saubhagya" },
  "karana": { "name": "Vanij" },
  "sun_sign":  "Vrishabha",
  "moon_sign": "Vrishabha"
}
```

### `GET /v1/reference/tithis`         → static catalog of 30 tithis (name, lord, significance)
### `GET /v1/reference/nakshatras`     → static catalog of 27 nakshatras (symbol, deity, element, pada info)

---

## 3. Muhurat Timings

> **Screens:** `Muhurat Timings (Detail)`, `Set Reminder (Muhurat)`, plus dashboard summary.
> Auspicious: Brahma, Abhijit, Vijay, Godhuli, Amrit Kalam.
> Inauspicious: Rahu Kaal, Yamaganda, Gulika Kaal, Dur Muhurat.

### `GET /v1/muhurat`
- **Query:** `date`, `lat`, `lon`, `tz`, `language`
- **Response:**
```json
{
  "auspicious": [
    { "id": "brahma",   "name": "Brahma Muhurat",  "start": "04:18", "end": "05:06" },
    { "id": "abhijit",  "name": "Abhijit Muhurat", "start": "11:42", "end": "12:24" },
    { "id": "vijay",    "name": "Vijay Muhurat",   "start": "14:12", "end": "14:54" },
    { "id": "godhuli",  "name": "Godhuli Muhurat", "start": "17:48", "end": "18:12" },
    { "id": "amrit",    "name": "Amrit Kalam",     "start": "20:30", "end": "22:06" }
  ],
  "inauspicious": [
    { "id": "rahu",     "name": "Rahu Kaal",  "start": "07:30", "end": "09:00" },
    { "id": "yamaganda","name": "Yamaganda",  "start": "10:30", "end": "12:00" },
    { "id": "gulika",   "name": "Gulika Kaal","start": "13:30", "end": "15:00" },
    { "id": "dur",      "name": "Dur Muhurat","start": "08:48", "end": "09:30" }
  ]
}
```

### `GET /v1/muhurat/{muhurat_id}` — single muhurat with explanation (for tap-through)

---

## 4. Sun & Moon Timings

> **Screen:** `Sun Timings (Detail)`
> Sunrise, Sunset, Daylight Duration, Moonrise, Moonset, Moon Phase.

### `GET /v1/celestial/sun-moon`
- **Query:** `date`, `lat`, `lon`, `tz`
- **Response:**
```json
{
  "sun": {
    "rise":  "06:42",
    "set":   "17:48",
    "day_length_minutes": 666
  },
  "moon": {
    "rise":  "20:24",
    "set":   "09:12",
    "phase": "waxing_gibbous",
    "illumination_pct": 78
  }
}
```

---

## 5. Festivals & Vrats

> **Screens:** `Festivals & Vrats (Vibrant)`, `Today's Festival (Detail)`, `Upcoming Events (Detail)`
> Featured cards (Diwali, Devutthana Ekadashi, Kartik Purnima), monthly calendar grid with
> festival markers, list table (date, festival, tithi/paksha, auspiciousness), spiritual tip,
> Today's Festival with rituals list.

### `GET /v1/festivals`
List/browse festivals.
- **Query:**
  - `from=YYYY-MM-DD`, `to=YYYY-MM-DD` (range; defaults to current month)
  - `type=major|vrat|tithi|fest|all` (filter)
  - `auspiciousness=high|moderate|low` (optional)
  - `lat`, `lon`, `tz`, `language`
- **Response (array of):**
```json
{
  "id": "diwali",
  "name": "Diwali, Lakshmi Puja",
  "date": "2024-11-01",
  "weekday": "Fri",
  "tithi": "Amavasya",
  "paksha": "Krishna",
  "type": "major_festival",
  "auspiciousness": "high",
  "short_description": "The festival of lights..."
}
```

### `GET /v1/festivals/today`
Festival(s) occurring today.
- **Query:** `date`, `lat`, `lon`, `tz`, `language`
- **Response:**
```json
{
  "festivals": [
    {
      "id": "vaishakha-purnima",
      "name": "Vaishakha Purnima",
      "subtitle": "Buddha Jayanti • Full Moon Day",
      "type": "purnima"
    }
  ]
}
```

### `GET /v1/festivals/{id}`
Full detail for a festival (powers Today's Festival screen).
- **Query:** `language`
- **Response:**
```json
{
  "id": "vaishakha-purnima",
  "name": "Vaishakha Purnima",
  "subtitle": "Buddha Jayanti • Full Moon Day",
  "about": "Vaishakha Purnima marks the birth, enlightenment ...",
  "rituals": [
    "Holy bath at sunrise",
    "Offer prayers to Buddha",
    "Charity (Daan) to the needy",
    "Light diyas in the evening",
    "Fast and chant mantras"
  ],
  "significance": "...",
  "next_occurrences": ["2026-05-23", "2027-05-12"]
}
```

### `GET /v1/festivals/upcoming`
Powers "Upcoming Events" strip on dashboard + dedicated screen (grouped Next 7 Days / This Month).
- **Query:** `from`, `window=7d|30d|90d`, `language`, `lat`, `lon`, `tz`
- **Response:**
```json
{
  "groups": [
    {
      "label": "Next 7 Days",
      "items": [
        { "date": "2026-05-19", "weekday": "MON", "name": "Ekadashi Vrat",
          "subtitle": "Most auspicious fast day", "type": "vrat" }
      ]
    },
    {
      "label": "This Month",
      "items": [ ... ]
    }
  ]
}
```

### `GET /v1/festivals/calendar`
Monthly grid (powers "Featured Festivals" calendar view, with day-cell markers).
- **Query:** `year`, `month`, `lat`, `lon`, `tz`, `language`
- **Response:**
```json
{
  "year": 2024, "month": 11,
  "masa": "Kartika",
  "days": [
    { "day": 1, "weekday": "FRI", "events": [{"id":"diwali","name":"Diwali","type":"major"}] },
    { "day": 7, "weekday": "THU", "events": [{"id":"chhath-puja","name":"Chhath Puja","type":"major"}] }
  ]
}
```

### `GET /v1/spiritual-tip`
Daily/monthly tip card on the Festivals screen.
- **Query:** `date`, `language`
- **Response:** `{ "tip": "Kartika is the most sacred month. Lighting a lamp..." }`

---

## 6. Horoscope (Rashifal)

> **Screen:** `Daily Horoscope (Vibrant)`
> Sign tabs (Aries…Pisces), period tabs (Daily/Weekly/Monthly), prediction text, auspicious %,
> categorized insights (Love, Career, Health), Planetary Transits, Ritual of the Day, View Full Chart.

### `GET /v1/horoscope/{sign}`
- **Path:** `sign` ∈ `aries|taurus|gemini|cancer|leo|virgo|libra|scorpio|sagittarius|capricorn|aquarius|pisces`
- **Query:**
  - `period=daily|weekly|monthly` (default `daily`)
  - `date=YYYY-MM-DD`
  - `language`
- **Response:**
```json
{
  "sign": "aries",
  "period": "daily",
  "date": "2023-10-24",
  "auspicious_score": 95,
  "context_tag": "Shardiya Navratri",
  "prediction": "Today marks a period of significant growth...",
  "categories": {
    "love":   "A harmonious day for relationships...",
    "career": "Strategic moves will pay off...",
    "health": "Vitality is high..."
  },
  "ritual_of_the_day": "Light a sandalwood incense at sunset...",
  "planetary_transits_summary": "Sun enters Libra today..."
}
```

### `GET /v1/horoscope/{sign}/transits`
Planetary transits detail (for "View Full Chart" tap-through).
- **Query:** `date`, `language`

### `GET /v1/reference/zodiac-signs` — static list of 12 signs (name, symbol, date range, lord)

---

## 7. Reminders   `[LOCAL-ONLY — not in backend]`

> **Lives in the Flutter app**, not on the server. Reminders are stored in a local
> `sqflite` table and scheduled via `flutter_local_notifications` on the device clock.
> No network call, no auth, no FCM. Section kept for schema reference — the same shape
> is what the local table uses.

> **Screen:** `Set Reminder (Muhurat)`, plus "Daily Rahu Kaal", "Important Festivals", "Notifications for major tithis" toggles in Settings.

### `~~POST /v1/reminders~~`  → local insert into `reminders` table
- **Body:**
```json
{
  "type": "muhurat",
  "ref_id": "abhijit",
  "date": "2026-05-18",
  "start_time_local": "11:42",
  "remind_before_minutes": 15,
  "channels": { "notification": true, "sound": true, "vibration": true },
  "repeat": { "enabled": true, "interval_minutes": 5, "max_times": 3 }
}
```
- **Returns:** `{ "id": "rem_...", "scheduled_at_utc": "2026-05-18T06:12:00Z" }`

### `GET /v1/reminders`           → list user's reminders
### `GET /v1/reminders/{id}`      → fetch one
### `PATCH /v1/reminders/{id}`    → update
### `DELETE /v1/reminders/{id}`   → cancel

### `PUT /v1/reminders/preferences`
Bulk toggles from Settings → REMINDERS section.
- **Body:** `{ "rahu_kaal_daily": true, "important_festivals": true, "major_tithis": true }`

---

## 8. User Profile & Settings   `[LOCAL-ONLY — not in backend]`

> **Lives in a Hive box** in the Flutter app. No server-side user records exist.

> **Screen:** `Settings (Vibrant)` — profile (Aravind Sharma, "Vedic Practitioner since 2018"),
> Location section, Preferences (language, appearance), Reminders, App version footer, ToS/Privacy links.

### `~~GET /v1/me~~`                    → read from local Hive
### `~~PATCH /v1/me~~`                  → write to local Hive
### `~~GET /v1/me/settings~~`           → read from local Hive
### `~~PATCH /v1/me/settings~~`         → write to local Hive
- **Body example:**
```json
{
  "language": "en",
  "appearance": "system",
  "location": { "mode": "auto" }
}
```

---

## 9. Location

> **Screen:** Settings `LOCATION` section ("Currently: Varanasi, India", Automatic Detection / Manual Entry).
>
> **Chosen location is stored locally.** The backend exposes three read-only endpoints:
> autocomplete **search**, **resolve** (reverse-geocode a GPS fix to its IANA tz), and a
> **detail-by-id** for re-localizing a saved location when the user switches language.

### `~~PUT /v1/me/location~~`  `[LOCAL-ONLY]`  → write to local Hive
- **Body (manual):** `{ "mode": "manual", "id": 1253405 }`
- **Body (auto):**   `{ "mode": "auto", "lat": 25.32, "lon": 83.0, "accuracy_m": 35 }`

### `GET /v1/locations/search?q=auran&country=IN&language=hi&limit=10&include_small=false`

Autocomplete for Manual Entry. **Designed for typeahead** — the client debounces
keystrokes 150–250 ms and re-queries on every prefix. Server runs a SQLite FTS5
`MATCH 'auran*'` query (prefix match against `name` + `alternatenames`), so latency is
sub-5 ms and the URL is fully CDN-cacheable.

**Query params:**

| param           | required | default | notes                                                                          |
|-----------------|----------|---------|--------------------------------------------------------------------------------|
| `q`             | yes      | —       | 1–64 chars. Matches Latin or native scripts (e.g. `varan`, `वारा`)              |
| `country`       | no       | none    | ISO-3166-1 alpha-2. If set, those rows rank first; others still returned       |
| `language`      | no       | `en`    | Affects `name_localized`, `admin1_localized`, `country_localized`, `display_label` |
| `limit`         | no       | `10`    | Max 25                                                                         |
| `include_small` | no       | `false` | `false` → searches `cities5000` (≈50k rows). `true` → `cities500` (≈200k rows, villages) |

**Ranking rules** (deterministic, applied in order):
1. Exact name match before alt-name match
2. Rows where `country == :country` before everything else
3. `feature_code` priority: `PPLC` (national capital) → `PPLA` (1st-order admin capital) → `PPLA2` (district HQ) → `PPLA3` → `PPL`
4. Higher `population` first
5. Lower `geonameid` as final tiebreaker (stable)

**Response:**
```json
{
  "results": [
    {
      "id": 1278149,
      "name": "Aurangabad",
      "name_localized": "औरंगाबाद",
      "admin2": "Aurangabad",
      "admin1": "Maharashtra",
      "admin1_localized": "महाराष्ट्र",
      "country": "IN",
      "country_localized": "भारत",
      "lat": 19.8762,
      "lon": 75.3433,
      "tz": "Asia/Kolkata",
      "population": 1175116,
      "feature_code": "PPLA2",
      "display_label": "औरंगाबाद, महाराष्ट्र, भारत"
    },
    {
      "id": 1278147,
      "name": "Aurangabad",
      "name_localized": "औरंगाबाद",
      "admin2": "Aurangabad",
      "admin1": "Bihar",
      "admin1_localized": "बिहार",
      "country": "IN",
      "country_localized": "भारत",
      "lat": 24.7714,
      "lon": 84.3746,
      "tz": "Asia/Kolkata",
      "population": 95929,
      "feature_code": "PPLA2",
      "display_label": "औरंगाबाद, बिहार, भारत"
    }
  ]
}
```

**Disambiguation contract:**
- `display_label` is **always** safe to render verbatim. The server picks the shortest form
  that uniquely identifies the row within the result set: `"Name, Admin1, Country"` by
  default, `"Name, Admin2 dist., Admin1, Country"` only when two rows in the same response
  would otherwise collide.
- The mobile UI **must** also render `admin1` (or `country` if `admin1` is absent) as a
  subtitle line so collisions are visually obvious even when the user only glances at the
  name. **Never** show just `name` alone in autocomplete rows.
- For countries where `admin1` is too granular to help (e.g. Japan prefectures), the server
  sets `admin1` to `null` in the localized payload and falls back to country in `display_label`.

**Caching:** `Cache-Control: public, max-age=86400, stale-while-revalidate=604800`. Search
responses depend only on `(q, country, language, limit, include_small)` — fully URL-keyed,
ideal for CloudFlare edge cache. Typical hit ratio after warmup: > 95% (everyone types
`var`, `vara`, `varan`…).

---

### `GET /v1/locations/resolve?lat=25.32&lon=82.97&language=en`

Reverse-resolve a raw GPS fix from the device's "Automatic Detection" button to a
timezone + nearest known city. Uses `timezonefinder` (offline polygon lookup) for `tz`
and a SQLite spatial query (`cities5000` haversine distance, R\*Tree-indexed) for the
nearest city. Always returns a `tz` even if no city is within range.

**Response:**
```json
{
  "tz": "Asia/Kolkata",
  "nearest_city": {
    "id": 1253405,
    "name": "Varanasi",
    "admin1": "Uttar Pradesh",
    "country": "IN",
    "lat": 25.3167,
    "lon": 82.9739,
    "display_label": "Varanasi, Uttar Pradesh, India",
    "distance_km": 0.62
  }
}
```

**Caching:** `Cache-Control: public, max-age=604800`. Quantize `lat`/`lon` to 0.1° on the
client before calling (`25.3`, `83.0`) so neighbours share a cache key.

---

### `GET /v1/locations/{id}?language=hi`

Return the canonical row for a single GeoNames `id`. Used by the app when:
- the user switches app language and the saved-location chip needs to re-localize
- a stale Hive entry needs to be revalidated after a GeoNames import bumps populations

**Response:** same single-row shape as one element of `/locations/search`.

**Caching:** `Cache-Control: public, max-age=86400, immutable`.

---

## 10. Languages

> **Screen:** `Language Picker` — 12 supported languages with native + English names.

### `GET /v1/reference/languages`
- **Response:**
```json
[
  { "code": "en", "name_native": "English",   "name_en": "English" },
  { "code": "hi", "name_native": "हिन्दी",     "name_en": "Hindi" },
  { "code": "bn", "name_native": "বাংলা",     "name_en": "Bengali" },
  { "code": "ta", "name_native": "தமிழ்",     "name_en": "Tamil" },
  { "code": "te", "name_native": "తెలుగు",    "name_en": "Telugu" },
  { "code": "mr", "name_native": "मराठी",     "name_en": "Marathi" },
  { "code": "gu", "name_native": "ગુજરાતી",  "name_en": "Gujarati" },
  { "code": "kn", "name_native": "ಕನ್ನಡ",     "name_en": "Kannada" },
  { "code": "ml", "name_native": "മലയാളം",   "name_en": "Malayalam" },
  { "code": "pa", "name_native": "ਪੰਜਾਬੀ",   "name_en": "Punjabi" },
  { "code": "sa", "name_native": "संस्कृतम्",  "name_en": "Sanskrit" },
  { "code": "or", "name_native": "ଓଡ଼ିଆ",     "name_en": "Odia" }
]
```

---

## 11. App Meta

> **Screen:** Settings footer — "Vedic Panchang v2.4.1", Terms of Service, Privacy Policy links.

### `GET /v1/app/meta`
- **Response:**
```json
{
  "app_name": "Vedic Panchang",
  "version": "2.4.1",
  "tagline": "Alignment with the Cosmos",
  "links": {
    "terms_of_service": "https://...",
    "privacy_policy":   "https://..."
  },
  "min_supported_version": "2.3.0"
}
```

---

## 12. Auth   `[REMOVED — no longer needed]`

Since all user-scoped state lives on the device, the backend has no auth. This section
is intentionally empty.

~~- `POST /v1/auth/login`           → email/phone + OTP or password~~
~~- `POST /v1/auth/refresh`         → refresh JWT~~
~~- `POST /v1/auth/logout`~~
~~- `POST /v1/auth/register`~~

---

# Screen → Endpoint Matrix

| Screen                                | Primary endpoints                                                                                                                     |
|---------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Daily Panchang Dashboard (Vibrant)    | `GET /panchang/today` (one call), or composed from `/muhurat`, `/celestial/sun-moon`, `/festivals/today`, `/festivals/upcoming`, `/horoscope/{sign}` |
| Tithi & Nakshatra (Detail)            | `GET /panchang/tithi-nakshatra`, `GET /reference/tithis`, `GET /reference/nakshatras`                                                |
| Muhurat Timings (Detail)              | `GET /muhurat`                                                                                                                        |
| Sun Timings (Detail)                  | `GET /celestial/sun-moon`                                                                                                             |
| Festivals & Vrats (Vibrant)           | `GET /festivals` (table), `GET /festivals/calendar` (grid), `GET /spiritual-tip`                                                      |
| Today's Festival (Detail)             | `GET /festivals/today`, `GET /festivals/{id}`                                                                                         |
| Upcoming Events (Detail)              | `GET /festivals/upcoming?window=30d`                                                                                                  |
| Daily Horoscope (Vibrant)             | `GET /horoscope/{sign}?period=daily\|weekly\|monthly`, `GET /horoscope/{sign}/transits`, `GET /reference/zodiac-signs`               |
| Set Reminder (Muhurat)                | `GET /muhurat`, `POST /reminders`, `PUT /reminders/preferences`                                                                       |
| Settings (Vibrant)                    | `GET /me`, `GET /me/settings`, `PATCH /me/settings`, `PUT /reminders/preferences`, `GET /app/meta`                                   |
| Language Picker                       | `GET /reference/languages`, `PATCH /me/settings` (with `{"language":"xx"}`)                                                          |

---

# Endpoint Count Summary

After removing user-scoped endpoints (now local):

- **Aggregate / dashboard:** 1
- **Panchang reference data:** 4 (tithi-nakshatra, tithis, nakshatras, sun-moon)
- **Muhurat:** 2
- **Festivals & Vrats:** 6 (list, today, detail, upcoming, calendar, tip)
- **Horoscope:** 3
- **Reference catalogs:** 3 (languages, signs, plus tithis/nakshatras above)
- **Locations (read-only search):** 2
- **App meta:** 1

**Total backend endpoints: ~22, all `GET`, all public, all cacheable.**

**Local-only (in Flutter, not backend):** ~14 — reminders CRUD, profile, settings,
location choice, auth (now removed entirely).

---

# Cross-cutting concerns

- **Caching:** All endpoints are public `GET`s with strong `Cache-Control` headers (HTTP
  caching via CloudFlare free tier + in-process `cachetools.TTLCache`). No Redis.
  Reference (`/reference/*`, `/app/meta`, `/reference/languages`) → `max-age=86400, immutable`.
  Date-aware endpoints (`/panchang/today`, `/muhurat`, `/celestial/sun-moon`, `/festivals/today`) →
  `max-age=3600, stale-while-revalidate=86400` keyed on `(date,lat,lon,language)`.
  Quantize `lat`/`lon` to 0.5° on the client when building the URL for cache consolidation.
- **i18n:** Every text-bearing endpoint accepts `language` (12 codes). All strings localized server-side.
- **Geo:** Astronomical endpoints REQUIRE `lat`/`lon`/`tz`; reject with 400 if missing.
- **Pagination:** `/festivals` supports `cursor` + `limit` if a year-range query returns >100 items.
- **Errors:** `{ "error": { "code": "...", "message": "...", "details": {...} } }`.
- **Auth:** None. Server is public-read.

