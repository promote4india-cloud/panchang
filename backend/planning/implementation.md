# Panchang App — Implementation Plan

> **Recommendation:** Stateless Python/FastAPI backend with Swiss Ephemeris for calculable
> endpoints + a small Postgres for editorial content (festivals, horoscope text). All user
> preferences, location, settings, and reminders live **only on the device** (Flutter local
> storage). No user accounts, no auth, no Redis.
>
> This document is the detailed plan to get from zero to a production-grade panchang service.

---

## 1. Architecture overview

```
┌──────────────────────────────────┐
│   Flutter mobile app             │
│   ┌────────────────────────────┐ │       HTTPS/JSON         ┌────────────────────────────┐
│   │ Local storage (Hive/sqflite│ │ ───────────────────────► │  FastAPI app (uvicorn)     │
│   │   - settings               │ │                          │                            │
│   │   - chosen location        │ │ ◄─────────────────────── │  ┌──────────────────────┐  │
│   │   - language               │ │                          │  │ panchang engine      │  │
│   │   - reminders              │ │                          │  │ (pyswisseph)         │  │
│   │   - cached responses       │ │     (optional CDN in     │  └──────────────────────┘  │
│   └────────────────────────────┘ │      front: CloudFlare   │  ┌──────────────────────┐  │
│   flutter_local_notifications     │      free tier)          │  │ festival rule engine │  │
│   (push fires on device, no FCM)  │                          │  └──────────────────────┘  │
└──────────────────────────────────┘                          │  ┌──────────────────────┐  │
                                                              │  │ content read-only    │  │
                                                              │  └──────────────────────┘  │
                                                              └────────┬───────────────────┘
                                                                       │
                                                              ┌────────▼───────────┐
                                                              │  PostgreSQL        │
                                                              │  (editorial only:  │
                                                              │   festival catalog,│
                                                              │   horoscope text)  │
                                                              │   - can also be    │
                                                              │     SQLite file    │
                                                              │     for tiny scale │
                                                              └────────────────────┘
```

### Why this split

- **Server is read-only and stateless.** No user accounts, no JWT, no sessions, no Redis.
  Every endpoint is either pure math or a content lookup. Scales horizontally trivially;
  one pod can serve thousands of req/s.
- **Device owns all user state.** Settings, language, location, reminders, push schedules
  live in `Hive` / `sqflite`. Zero PII leaves the device.
  Benefits: privacy by default, no GDPR scope on user data, no auth bugs, no DB cost for
  user data, app works offline against last cached responses.
- **Reminders fire locally.** `flutter_local_notifications` schedules notifications on the
  device clock — no FCM, no server-side scheduler, no push fees.
- **Caching is HTTP-native.** Responses carry `Cache-Control` headers. CloudFlare's free
  tier (or any CDN) caches by URL at the edge for free. The Flutter app also caches.
  No Redis. (Optional: small in-process `cachetools.TTLCache` inside FastAPI for hot keys.)
- **Editorial DB can start as SQLite.** Festivals + horoscope text fit in a few MB.
  Promote to Postgres only when you need concurrent writers (i.e. an editorial team).

---

## 2. Tech stack

### Backend

| Layer | Choice | Why |
|---|---|---|
| Framework | **FastAPI** | Async, automatic OpenAPI docs, Pydantic validation |
| ASGI server | **uvicorn** behind **gunicorn** | Standard production combo |
| Astronomy core | **pyswisseph** (Swiss Ephemeris) | Gold-standard accuracy; Lahiri ayanamsa native |
| Solar utilities | `swe.rise_trans()` or **skyfield** | Sunrise/sunset/twilight |
| Editorial DB | **SQLite** (start) → **PostgreSQL** (when needed) | Read-only at runtime; tiny dataset |
| ORM | **SQLAlchemy 2.x** + **Alembic** | Same code works for SQLite and Postgres |
| In-process cache | **`cachetools.TTLCache`** | Free, zero-infra; per-worker is fine since math is deterministic |
| Edge cache (optional) | **CloudFlare free tier** | Caches by URL via `Cache-Control` headers; free up to massive scale |
| Place search | **GeoNames** (`cities5000` + `cities500` + `admin1Codes` + `admin2Codes`) imported into **SQLite FTS5** | Offline autocomplete, < 5 ms, no per-request cost; FTS5 prefix `MATCH 'var*'` powers typeahead |
| Reverse-geocode → timezone | **`timezonefinder`** (PyPI) | Pure-offline polygon lookup; resolves any (lat, lon) to IANA tz string |
| DST / UTC offset | **`zoneinfo`** (stdlib) | Resolves IANA tz string to offset for any date |
| Observability | **OpenTelemetry → Grafana/Loki/Tempo** (or just stdout logs initially) | Trace a request app → API → DB |
| Containerization | **Docker** + **docker-compose** (dev) | Standard |
| CI/CD | **GitHub Actions** | Lint → test → build image → push |

**Removed vs. previous draft:** Redis, fastapi-users / JWT auth, APScheduler, Celery,
firebase-admin (server-side). None are needed.

### Mobile (Flutter)

| Layer | Choice | Why |
|---|---|---|
| Framework | **Flutter 3.x** | iOS + Android from one codebase |
| State mgmt | **Riverpod** | Mature, testable |
| HTTP | **dio** + **retrofit** (generated from OpenAPI) | Type-safe client |
| **Local storage** | **Hive** (KV) for settings + cached API responses; **sqflite** for reminders | Pure on-device persistence |
| **Local notifications** | **flutter_local_notifications** | Schedules reminders on device clock; no FCM needed |
| Geolocation | **geolocator** | One-tap location fetch when user picks "automatic" |
| Location autocomplete UI | **flutter_typeahead** | Debounced text field that calls `/v1/locations/search` on each keystroke |
| i18n | **flutter intl** | Shares string keys with backend i18n YAMLs |
| Routing | **go_router** | Declarative, deep-link ready |

---

## 3. Repository layout (monorepo)

```
panchang/
├── backend/
│   ├── pyproject.toml
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory
│   │   ├── config.py                  # Pydantic Settings (env-driven, 12-factor)
│   │   ├── deps.py                    # Common dependencies (db, redis, current_user)
│   │   ├── core/
│   │   │   ├── panchang/
│   │   │   │   ├── ephemeris.py       # pyswisseph wrapper, ayanamsa setup
│   │   │   │   ├── tithi.py
│   │   │   │   ├── nakshatra.py
│   │   │   │   ├── yoga_karana.py
│   │   │   │   ├── muhurat.py         # 5 auspicious + 4 inauspicious windows
│   │   │   │   ├── sun_moon.py        # rise/set, day length, phase
│   │   │   │   └── rashi.py           # sun sign, moon sign
│   │   │   ├── festivals/
│   │   │   │   ├── rules.py           # tithi-based festival date resolver
│   │   │   │   ├── catalog.py         # static catalog loader
│   │   │   │   └── matcher.py         # "what festival is on date X?"
│   │   │   ├── i18n.py                # 12-language string resolver
│   │   │   ├── cache.py               # cachetools TTLCache helpers, key builders
│   │   │   └── locations/
│   │   │       ├── search.py          # FTS5 prefix MATCH + ranking SQL
│   │   │       ├── resolve.py         # timezonefinder + nearest-city haversine
│   │   │       └── importer.py        # one-shot GeoNames → SQLite loader
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── panchang.py        # /panchang/today, /panchang/tithi-nakshatra
│   │   │   │   ├── muhurat.py         # /muhurat, /muhurat/{id}
│   │   │   │   ├── celestial.py       # /celestial/sun-moon
│   │   │   │   ├── festivals.py       # /festivals, /festivals/today, etc.
│   │   │   │   ├── horoscope.py       # /horoscope/{sign}
│   │   │   │   ├── locations.py       # /locations/search, /resolve, /{id}
│   │   │   │   ├── reference.py       # static catalogs (tithis, nakshatras, signs, langs)
│   │   │   │   └── app_meta.py
│   │   ├── models/                    # SQLAlchemy ORM — editorial content only
│   │   │   ├── festival.py
│   │   │   ├── horoscope_content.py
│   │   │   └── location.py            # geonames_cities, admin1, admin2 tables + FTS5 virtual table
│   │   ├── schemas/                   # Pydantic request/response models
│   │   └── services/
│   │       └── horoscope_generator.py # nightly LLM/editorial pipeline (later)
│   ├── data/
│   │   ├── ephemeris/                 # Swiss Ephemeris .se1 files (~3 MB)
│   │   ├── festivals.yaml             # seed catalog (source of truth)
│   │   ├── geonames/                  # downloaded at build time, not committed
│   │   │   ├── cities5000.txt         # ~50k populated places worldwide (~8 MB)
│   │   │   ├── cities500.txt          # ~200k incl. small Indian towns (~35 MB)
│   │   │   ├── admin1CodesASCII.txt   # state/province names (e.g. IN.36 → Uttar Pradesh)
│   │   │   └── admin2Codes.txt        # district names
│   │   └── i18n/                      # 12 language string tables
│   ├── tests/
│   │   ├── test_tithi.py              # verify against published panchang (e.g. drikpanchang.com)
│   │   ├── test_muhurat.py
│   │   ├── test_sun_moon.py
│   │   ├── test_festivals.py
│   │   └── test_api.py                # FastAPI TestClient integration
│   └── Dockerfile
├── mobile/                            # Flutter app
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart
│   │   ├── api/                       # generated from OpenAPI
│   │   ├── local/                     # ALL user state lives here
│   │   │   ├── settings_store.dart    # Hive box: language, appearance, location, prefs
│   │   │   ├── reminders_repo.dart    # sqflite: CRUD for reminders
│   │   │   ├── notification_service.dart  # wraps flutter_local_notifications
│   │   │   └── response_cache.dart    # Hive: cache GET responses by URL+date
│   │   ├── screens/
│   │   │   ├── dashboard.dart
│   │   │   ├── tithi_nakshatra.dart
│   │   │   ├── muhurat.dart
│   │   │   ├── sun_timings.dart
│   │   │   ├── festivals_list.dart
│   │   │   ├── festival_detail.dart
│   │   │   ├── upcoming_events.dart
│   │   │   ├── horoscope.dart
│   │   │   ├── set_reminder.dart
│   │   │   ├── settings.dart
│   │   │   └── language_picker.dart
│   │   ├── widgets/
│   │   ├── state/                     # Riverpod providers
│   │   └── theme/
│   └── test/
├── openapi/
│   └── panchang.yaml                  # source of truth for client generation
├── docs/
│   ├── architecture.md
│   ├── panchang-math.md               # explanation of tithi/muhurat formulas
│   └── api-endpoints.md               # the one we already drafted
├── docker-compose.yml                 # local dev: postgres + redis + backend
└── .github/workflows/
    ├── backend-ci.yml
    └── mobile-ci.yml
```

---

## 4. Calculable endpoints — math reference

All formulas assume **sidereal longitudes** using **Lahiri ayanamsa** (the standard for Indian panchang).

### Tithi
$$\text{tithi}_n = \left\lfloor \frac{(\lambda_{\text{moon}} - \lambda_{\text{sun}}) \bmod 360}{12} \right\rfloor + 1 \quad (1..30)$$

- 1..15 = Shukla Paksha (waxing), 16..30 = Krishna Paksha (waning).
- End-time of current tithi: solve for the next instant when the difference crosses the next 12° boundary (Newton's method over hourly samples).

### Nakshatra
$$\text{nak}_n = \left\lfloor \frac{\lambda_{\text{moon}}}{360/27} \right\rfloor + 1 \quad (1..27)$$

End-time: solve for moon crossing next 13°20′ boundary.

### Yoga
$$\text{yoga}_n = \left\lfloor \frac{(\lambda_{\text{sun}} + \lambda_{\text{moon}}) \bmod 360}{360/27} \right\rfloor + 1$$

### Karana
- Half of a tithi. 11 karanas, 4 fixed + 7 movable. Indexed by half-tithi number with the known fixed-karana exceptions.

### Sun/Moon rise & set
- `swe.rise_trans(jd, swe.SUN, geopos, ...)` returns the next rise/set in UT. Convert to local time.

### Muhurat windows (require sunrise + sunset)

Let `D = sunset - sunrise` (day length), `N = next_sunrise - sunset` (night length).

| Muhurat | Rule |
|---|---|
| **Brahma** | Starts 96 min before sunrise, ends 48 min before sunrise |
| **Abhijit** | Midday ± `D/30` (≈ 48 min wide, centered on solar noon) |
| **Vijay** | 10th muhurta of the day (`D/15` × 9 from sunrise, lasts `D/15`) |
| **Godhuli** | 24 min around sunset |
| **Amrit Kalam** | Tied to current nakshatra's amrita period; lookup table |
| **Rahu Kaal** | 8th of the day, position depends on weekday |
| **Yamaganda** | Same construction, different weekday → position table |
| **Gulika Kaal** | Same, weekday lookup |
| **Dur Muhurat** | 1 or 2 specific muhurtas per day depending on weekday |

A 5-row weekday → fraction table powers Rahu/Yamaganda/Gulika trivially.

### Sun sign / Moon sign (Rashi)
$$\text{rashi} = \left\lfloor \frac{\lambda}{30} \right\rfloor + 1 \quad (1..12)$$

Mesha=1 (Aries), Vrishabha=2 (Taurus), ... Meena=12 (Pisces).

### Moon phase
From elongation angle `(λ_moon - λ_sun) mod 360`:
- 0–22.5°: new moon → waxing crescent
- 22.5–67.5°: waxing crescent
- 67.5–112.5°: first quarter
- 112.5–157.5°: waxing gibbous
- 157.5–202.5°: full moon
- ...etc.

---

## 5. Festival rules engine

Most Indian festivals are **deterministic functions of panchang state**. Encode them as rules, not as a list of dates.

`data/festivals.yaml` shape:

```yaml
- id: ekadashi
  name_key: festival.ekadashi
  type: vrat
  auspiciousness: high
  rule:
    type: tithi
    tithi: 11           # both pakshas
  rituals_key: festival.ekadashi.rituals

- id: diwali
  name_key: festival.diwali
  type: major_festival
  auspiciousness: high
  rule:
    type: tithi_in_masa
    masa: kartika
    paksha: krishna
    tithi: 30           # amavasya

- id: kartik-purnima
  name_key: festival.kartik_purnima
  rule:
    type: tithi_in_masa
    masa: kartika
    paksha: shukla
    tithi: 15           # purnima

- id: sankashti-chaturthi
  rule:
    type: tithi
    paksha: krishna
    tithi: 4

- id: maha-shivaratri
  rule:
    type: tithi_in_masa
    masa: phalguna
    paksha: krishna
    tithi: 14
```

Rule types to implement:
- `tithi` — every occurrence of a tithi (both pakshas)
- `tithi_in_paksha` — every occurrence in named paksha
- `tithi_in_masa` — once a year, exact tithi+paksha+masa
- `nakshatra_in_masa` — e.g. Onam (Shravana nakshatra in Bhadrapada)
- `solar_event` — Makar Sankranti (Sun enters Capricorn), Mesha Sankranti
- `gregorian` — fixed-date holidays (Republic Day, etc.) for completeness
- `eclipse` — solar/lunar (Swiss Ephemeris gives these)

This means `/festivals/calendar?year=2027&month=3` produces **correct dates for years far into the future without a single DB row of dated entries.**

---

## 6. Phased rollout

### Phase 0 — Foundations (week 1)
- [ ] Set up monorepo, pyproject, docker-compose with just the backend (SQLite file mounted)
- [ ] FastAPI skeleton with `/health` and `/v1/app/meta`
- [ ] CI: lint (ruff, mypy), pytest with coverage gate ≥80%
- [ ] Pre-commit hooks
- [ ] OpenAPI auto-export to `openapi/panchang.yaml`

### Phase 1 — Astronomy core (week 1–2)
- [ ] Vendor Swiss Ephemeris files into `data/ephemeris/`
- [ ] `core.panchang.ephemeris` — wrapper, ayanamsa config
- [ ] Implement tithi, nakshatra, yoga, karana with end-time solvers
- [ ] Implement sun/moon rise/set, day length, moon phase
- [ ] Implement muhurat windows (all 9)
- [ ] **Tests** — verify against drikpanchang.com or similar published source for 10 sample dates × 3 cities. Coverage ≥90% on math modules.

### Phase 2 — Calculable API endpoints (week 2)
- [ ] `GET /v1/panchang/today` (the dashboard aggregate)
- [ ] `GET /v1/panchang/tithi-nakshatra`
- [ ] `GET /v1/muhurat`
- [ ] `GET /v1/celestial/sun-moon`
- [ ] In-process `TTLCache` for hot keys (1h TTL); set `Cache-Control: public, max-age=3600`
- [ ] Static reference catalogs (`/reference/tithis`, `/reference/nakshatras`, `/reference/zodiac-signs`, `/reference/languages`)
- [ ] i18n: load 12 language tables, resolve via `Accept-Language` or `?language=`

### Phase 3 — Festivals (week 3)
- [ ] Festival rule engine in `core.festivals.rules`
- [ ] Seed `festivals.yaml` with ~100 major festivals + vrats
- [ ] `GET /v1/festivals/today`, `/v1/festivals/upcoming`, `/v1/festivals/calendar`, `/v1/festivals/{id}`
- [ ] Tests vs. known dates for 2024–2027

### Phase 4 — On-device storage in Flutter (week 3–4)
*No server work this phase — entirely client-side.*
- [ ] Hive boxes for settings: `language`, `appearance`, `location` (id, lat, lon, tz, display_label), preferences toggles
- [ ] sqflite schema for reminders: `id, type, ref_id, date, start_time_local, remind_before_minutes, channels_json, repeat_json`
- [ ] `notification_service.dart`: wrap `flutter_local_notifications`, schedule on insert, cancel on delete
- [ ] Permission flow for notifications (iOS prompt) + exact-alarm permission (Android 13+)
- [ ] Background fetch / WorkManager to refresh tomorrow's panchang once a day (so reminders that reference tithi end-times stay accurate)
- [ ] Migrate-on-launch helper for future schema bumps
- [ ] Re-localize saved location on language switch: call `GET /v1/locations/{id}?language=<new>` and overwrite the Hive entry

### Phase 4b — Location service (backend, week 3–4) **NEW**
*Powers Manual Entry autocomplete + Automatic Detection's reverse-geocode.*

**Where the data lives:** the raw GeoNames TSVs are **never committed to the repo** and
**never fetched at runtime**. They are downloaded **at Docker build time** by
`scripts/download_geonames.py`, parsed into a SQLite file at
`data/locations.db` (with normal tables + an FTS5 virtual table + an R\*Tree), and that
SQLite file is **baked into the container image**. At runtime the API just opens it
read-only from the local filesystem — no network call to geonames.org, no separate DB
server, no per-request I/O cost beyond a SQLite query. Rebuilding the image (monthly cron
in CI) refreshes the data.

- [ ] Download script `scripts/download_geonames.py`: pulls `cities5000.txt`, `cities500.txt`, `admin1CodesASCII.txt`, `admin2Codes.txt` from `https://download.geonames.org/export/dump/` into `data/geonames/` (runs at Docker build time, not at runtime)
- [ ] `core/locations/importer.py`: parses GeoNames TSVs → normalized SQLAlchemy tables:
  - `geonames_cities` (id PK, name, asciiname, country, admin1_code, admin2_code, lat, lon, tz, population, feature_code)
  - `geonames_admin1` (code PK e.g. `IN.36`, name, ascii_name)
  - `geonames_admin2` (code PK e.g. `IN.36.182`, name, ascii_name)
  - `cities_fts` (SQLite **FTS5 virtual table** over `name || ' ' || asciiname || ' ' || alternatenames`, tokenizer `unicode61 remove_diacritics 2`)
  - R\*Tree spatial index `cities_rtree` on `(lat, lon)` for `/resolve`'s nearest-city query
- [ ] `core/locations/search.py`: prefix-MATCH query with the ranking SQL in API spec §9; localized admin/country names looked up from a small `localizations.yaml` for the 12 supported languages (only a few hundred strings)
- [ ] `core/locations/resolve.py`: `timezonefinder.TimezoneFinder(in_memory=True)` singleton; haversine on R\*Tree-filtered candidates
- [ ] `GET /v1/locations/search`, `GET /v1/locations/resolve`, `GET /v1/locations/{id}` with `Cache-Control` headers per spec
- [ ] Tests: collision cases (Aurangabad-MH vs Aurangabad-BR, Hyderabad-IN vs Hyderabad-PK, Rampur × N); native-script search (`वाराणसी`); empty / 1-char `q` returns 400; `q` injection (FTS5 special chars escaped)


### Phase 5 — Editorial content (week 4–5)
- [ ] Horoscope content storage (sign × period × language × date)
- [ ] Admin endpoints (or simple Django-admin-style UI) for editors
- [ ] Optional: nightly LLM generation job with human-review queue
- [ ] Spiritual tip rotation

### Phase 6 — Flutter app (parallel from week 2)
- [ ] Generate Dart client from `openapi/panchang.yaml` via `openapi-generator`
- [ ] Implement 11 screens in `lib/screens/`
- [ ] Riverpod providers for each domain
- [ ] Offline caching with `hive` for last-fetched panchang (so app works on subway)
- [ ] Localization with Flutter's `intl` package, sharing string keys with backend i18n
- [ ] FCM setup for receiving reminder pushes

### Phase 7 — Observability, hardening, release (week 6)
- [ ] OpenTelemetry instrumentation (or just structured stdout logs to start)
- [ ] Rate limiting (`slowapi`) per IP — protects against scraping/abuse
- [ ] Optional: put **CloudFlare free tier** in front of the API domain for edge caching + DDoS protection
- [ ] Load test: 1000 req/s on a single backend pod
- [ ] Security audit: OWASP top 10 checklist, dependency scan (`pip-audit`, `dart pub outdated`)
- [ ] Production deploy: a managed PaaS (Fly.io, Railway, Render — free tiers exist)
- [ ] Mobile: TestFlight (iOS) + internal track (Android) → public

---

## 7. Caching strategy (no Redis)

Three layers, each free. Most requests never reach Python.

### Layer 1 — HTTP cache headers (the workhorse)

Every GET response sets `Cache-Control`. CloudFlare's free tier (or any CDN) caches the
response by URL at the edge. Browser/mobile HTTP clients also obey these headers.

| Endpoint                         | `Cache-Control`                                             |
|----------------------------------|-------------------------------------------------------------|
| `/panchang/today`                | `public, max-age=3600, stale-while-revalidate=86400`        |
| `/panchang/tithi-nakshatra`      | `public, max-age=3600, stale-while-revalidate=86400`        |
| `/muhurat`                       | `public, max-age=3600, stale-while-revalidate=86400`        |
| `/celestial/sun-moon`            | `public, max-age=21600` (6h)                                |
| `/festivals/today`               | `public, max-age=86400` (24h)                               |
| `/festivals/calendar`            | `public, max-age=604800` (7d)                               |
| `/festivals/{id}`                | `public, max-age=604800, immutable` (until deploy bumps it) |
| `/reference/*`, `/app/meta`      | `public, max-age=86400, immutable`                          |

Quantize lat/lon to ~0.5° (~50 km) in the URL itself so users in the same city land on
the **same cache key** at the edge. Example: `?lat=25.5&lon=83.0` instead of
`?lat=25.317&lon=83.005`. Do the quantization on the client when building the URL.

### Layer 2 — In-process Python cache (free, zero infra)

For hot keys that miss the CDN (cold edge node, no CDN configured yet), wrap the
math in `cachetools.TTLCache`:

```python
from cachetools import TTLCache, cached

_panchang_cache = TTLCache(maxsize=4096, ttl=3600)

@cached(_panchang_cache, key=lambda date, lat, lon, lang: (date, lat, lon, lang))
def compute_panchang_today(date, lat, lon, lang):
    ...
```

- Per-worker (each uvicorn worker has its own dict). That's fine: panchang is
  deterministic, recomputing is ~10ms, and on hot keys you still get >90% hit rate per worker.
- No serialization cost (returns Python objects directly).
- Zero memory pressure: 4096 entries × ~2 KB = 8 MB cap.

### Layer 3 — Flutter on-device response cache

`response_cache.dart` (Hive box) stores last-fetched JSON per URL with a TTL. Benefits:
- App opens instantly with last-known data, then refreshes.
- Works fully offline for previously-viewed dates.
- Zero round trips when the user toggles between screens within the same minute.

### Cache invalidation
- **Panchang/celestial:** never invalidated (deterministic; just expire by TTL).
- **Editorial:** bump a `?v={deploy_id}` query param in the URL on every deploy. Old URLs
  age out naturally; new URLs are fresh.

### When (if ever) to add Redis
Only if you want the in-process cache to be **shared across workers** AND you have many
workers AND the CDN isn't an option. For this app, that day will likely never come.

---

## 8. i18n strategy

- Server **always** returns localized strings. Client never translates panchang terms.
- Source of truth: `backend/data/i18n/{lang}.yaml`.
- String IDs follow `domain.subdomain.key` (e.g. `tithi.shukla_pratipada`).
- Build-time check: every key in `en.yaml` must exist in all 11 other files (CI fail otherwise).
- Flutter side: same string keys exposed via `intl` so any client-only labels (e.g. "Cancel") share the dictionary.

12 languages: en, hi, bn, ta, te, mr, gu, kn, ml, pa, sa, or.

---

## 9. Testing strategy

Per the org's 80% coverage rule:

### Unit tests (hermetic, fast)
- Math modules: golden-value tests. Pin 30 sample dates × 5 cities. Compare against published panchang.
- Festival rules: 100 known festival dates between 2020–2030. Assert resolver returns the right one.
- i18n: every endpoint exercised in 3 languages (en, hi, sa) to catch missing keys.

### Integration tests
- FastAPI `TestClient` with in-memory SQLite + fakeredis. Hit every endpoint.
- Reminder lifecycle: create → schedule fires → push payload built correctly (FCM mocked).

### Contract tests
- OpenAPI schema validates every response. Schema drift = test fail.

### Mobile tests
- Widget tests per screen with mocked API.
- Golden image tests for dashboard rendering (catch theme regressions).

### Manual / nightly
- E2E flow: install app → set location to Varanasi → today's panchang matches drikpanchang.com.
- Calendar correctness for next 5 years sampled monthly.

---

## 10. Security checklist (OWASP top 10)

Without auth or user data on the server, the surface area is small.

| Risk | Mitigation |
|---|---|
| A01 Broken access control | N/A — no user-scoped endpoints; everything is public read |
| A02 Cryptographic failures | TLS only (Let's Encrypt); no secrets exchanged with clients |
| A03 Injection | SQLAlchemy parameterized queries; Pydantic input validation; no raw SQL |
| A04 Insecure design | Rate limits per IP; strict input ranges (lat ∈ [-90,90], etc.) |
| A05 Misconfiguration | Locked-down CORS; security headers via `secure` middleware |
| A06 Vulnerable components | `pip-audit` + Dependabot in CI |
| A07 Auth failures | N/A — no auth |
| A08 Software/data integrity | Signed Docker images; checksum-verified ephemeris files |
| A09 Logging/monitoring | Structured stdout logs; alert on 5xx spike |
| A10 SSRF | No user-supplied URLs fetched by server |

**On-device data (Flutter)** has its own concerns: encrypt the Hive box with a key from
platform keystore (`flutter_secure_storage`) if you store anything sensitive. For settings
and reminder text, plain Hive is fine.

---

## 11. Operational concerns

### Cost projections (rough, monthly)
- Single backend pod (256 MB RAM is enough) on Fly.io / Railway / Render free tier: **$0**.
- Editorial data ships as a SQLite file inside the container image: **$0**.
- CloudFlare free tier in front: **$0**.
- Push notifications: fire on-device (no FCM): **$0**.
- TLS cert: Let's Encrypt: **$0**.
- **Realistic total: $0–$5/mo** until you outgrow the free tier (~10k DAU).
- When you outgrow it: ~$5–$10/mo for a small VM / paid tier. Postgres only enters the
  picture if you hire an editorial team that needs concurrent writes.

### Scaling triggers
- p95 latency > 200ms → add backend replicas, ensure CDN is enabled.
- CDN hit rate < 80% → tighten lat/lon quantization or align TTLs.
- SQLite write lock contention → promote editorial DB to Postgres.

### Backup
- SQLite editorial DB: it's in the container image; the source YAMLs are in git.
  Restore = redeploy.
- No user data on server → nothing to back up there.
- User data on device: standard OS-level backup (iCloud / Google Drive) handles it via
  the app's normal `documents` directory.

---

## 12. Concrete kickoff checklist

A 1-day sprint to prove the spike. Uses **`uv`** (Astral) as the Python package manager —
faster than poetry, drop-in `pyproject.toml`, single static binary, no virtualenv juggling.

```bash
# Day 1, morning
# 1. Install uv once (Windows PowerShell)
#    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
#    (macOS / Linux: curl -LsSf https://astral.sh/uv/install.sh | sh)

mkdir panchang && cd panchang
git init

# 2. Scaffold the backend project
uv init backend --package --python 3.12
cd backend

# 3. Add runtime deps (writes to pyproject.toml, locks to uv.lock)
uv add fastapi "uvicorn[standard]" pyswisseph pydantic pydantic-settings \
       sqlalchemy alembic cachetools timezonefinder httpx pyyaml slowapi

# 4. Add dev deps
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy

# 5. Project folders + Swiss Ephemeris files
mkdir -p data/ephemeris app/core/panchang tests
curl -L https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1 -o data/ephemeris/sepl_18.se1
curl -L https://www.astro.com/ftp/swisseph/ephe/semo_18.se1 -o data/ephemeris/semo_18.se1
curl -L https://www.astro.com/ftp/swisseph/ephe/seas_18.se1 -o data/ephemeris/seas_18.se1

# 6. Run things with uv run (no manual venv activation needed)
uv run pytest -q
uv run uvicorn app.main:app --reload
```

Then implement `tithi.py` + `test_tithi.py` and prove that for `2026-05-20, lat=25.32, lon=83.0` we get the same tithi as drikpanchang.com. That single passing test validates the entire approach.

---

## 13. What this plan deliberately does NOT include (yet)

- **Astrology features** (birth charts, kundli matching) — would justify a separate service later.
- **Social/community features** (festival photo sharing) — out of scope for v1.
- **Audio (mantras, aartis)** — needs a content team; punt to v2.
- **Wearables** — Phase 8+, once API is stable.
- **In-app purchases** — depends on monetization decision (ads vs. subscription).

These are intentionally deferred so the team can ship the core panchang experience first.

---

## Appendix A — Library install reference

### Backend (Python 3.12+, managed by `uv`)
```toml
# pyproject.toml (PEP 621 — uv reads this directly, no [tool.poetry] section)
[project]
name = "panchang-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.27",
  "pyswisseph>=2.10.3",
  "pydantic>=2.6",
  "pydantic-settings>=2.2",
  "sqlalchemy>=2.0",
  "alembic>=1.13",
  "cachetools>=5.3",            # in-process TTL cache (replaces Redis)
  "timezonefinder>=6.5",        # offline lat/lon → IANA tz for /locations/resolve
  "httpx>=0.27",
  "pyyaml>=6.0",
  "slowapi>=0.1.9",             # IP rate limiting
]

[dependency-groups]
dev = [
  "pytest>=8.0",
  "pytest-asyncio>=0.23",
  "pytest-cov>=4.1",
  "ruff>=0.3",
  "mypy>=1.9",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Lockfile: `uv.lock` (auto-managed, commit it). Install on a fresh checkout with
`uv sync` (creates `.venv`, installs from lock, fully reproducible).

**Dropped:** `redis`, `apscheduler`, `firebase-admin`, `python-jose`, `passlib`, `asyncpg`,
`fakeredis`. Add `asyncpg` back later if/when you promote SQLite → Postgres.

### Mobile (Flutter 3.19+)
```yaml
dependencies:
  flutter: { sdk: flutter }
  flutter_riverpod: ^2.5.0
  dio: ^5.4.0
  retrofit: ^4.1.0
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  sqflite: ^2.3.0                       # reminders DB
  path_provider: ^2.1.0
  flutter_local_notifications: ^17.0.0  # on-device push, no FCM
  flutter_secure_storage: ^9.0.0        # optional, for encrypting Hive key
  geolocator: ^11.0.0
  flutter_typeahead: ^5.2.0             # debounced autocomplete for /locations/search
  intl: ^0.19.0
  go_router: ^13.2.0
  workmanager: ^0.5.2                   # background refresh for tomorrow's panchang

dev_dependencies:
  build_runner: ^2.4.0
  retrofit_generator: ^8.1.0
  hive_generator: ^2.0.1
  flutter_test: { sdk: flutter }
```

**Dropped:** `firebase_core`, `firebase_messaging`. No server-issued push.

---

## Appendix B — Ephemeris file licensing

Swiss Ephemeris is dual-licensed:
- **AGPL** (free for open-source projects).
- **Commercial license** (~€750 one-time per closed-source app) — required if your app is closed-source.

For a commercial closed-source app, budget for this license. The math is worth it; the alternative is implementing VSOP87 from scratch (years of work).

---

*End of plan.*


