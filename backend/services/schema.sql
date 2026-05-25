-- Editorial / scraped-content schema (additive — coexists with GeoNames tables).
-- All tables use CREATE IF NOT EXISTS so this can run on every startup.
-- One physical file: data/sqlite.db (same as locations service).

-- ---------------------------------------------------------------------------
-- 1. Festival catalog (identity + rule for date derivation)
--    Dates are NEVER stored as rows — they're computed by services/festivals.py
--    from the rule_type + rule_json, per implementation.md §5.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festivals (
    id              TEXT PRIMARY KEY,            -- 'diwali', 'mohini-ekadashi', 'dhanteras'
    parent_id       TEXT REFERENCES festivals(id) ON DELETE SET NULL,
    slug_path       TEXT NOT NULL UNIQUE,        -- 'diwali' | 'diwali/dhanteras' | 'ekadashi/mohini-ekadashi'
    kind            TEXT NOT NULL,               -- 'festival' | 'vrat' | 'fest_group' | 'muhurat_event'
    type            TEXT,                        -- 'major_festival'|'tithi'|'purnima'|'amavasya'|'ekadashi'|'navratri-day'|...
    auspiciousness  TEXT,                        -- 'high'|'moderate'|'low'
    -- Rule for date derivation (see services/festivals.py)
    rule_type       TEXT,                        -- 'tithi'|'tithi_in_masa'|'tithi_in_paksha'|'nakshatra_in_masa'|'solar_event'|'gregorian'|'manual'|NULL
    rule_json       TEXT,                        -- JSON: {masa, paksha, tithi, nakshatra, month, day, ...}
    -- JSON array of region/community/sect tags identifying WHERE/by WHOM this
    -- festival is observed. NULL or empty array = universal (shown for every
    -- tradition query). Non-empty = festival is shown only when the caller's
    -- requested tradition bag intersects this set. Tags are free-form strings
    -- matching the vocabulary in routers/festivals.py REGION_TRADITIONS values
    -- (e.g. 'kerala','malayali','south','amanta','tamil','sikh','vaishnava').
    -- Distinct from `rule_json`'s `multi_tradition.observances[].tradition`
    -- which tags individual date-VARIANTS of the same festival.
    scope_traditions TEXT,
    thumbnail_url   TEXT,
    source_url      TEXT,                        -- canonical astrosage URL
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_festivals_parent ON festivals(parent_id);
CREATE INDEX IF NOT EXISTS idx_festivals_kind   ON festivals(kind);

-- ---------------------------------------------------------------------------
-- 2. Editorial text per language (one row per festival × language).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_content (
    festival_id     TEXT NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,               -- 'en','hi','bn','ta','te','mr','gu','kn','ml','pa','sa','or'
    name            TEXT NOT NULL,               -- 'Dhanteras'
    subtitle        TEXT,                        -- 'Day 1 of Diwali' / 'Most auspicious fast day'
    about           TEXT,                        -- intro paragraph(s) (markdown)
    significance    TEXT,                        -- "Importance of ..." section
    history         TEXT,                        -- "Historical Legend ..." section
    scriptures      TEXT,                        -- "Scriptures related to ..." section
    puja_vidhi      TEXT,                        -- "Puja Vidhi" narrative section
    scraped_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_url      TEXT NOT NULL,
    PRIMARY KEY (festival_id, language)
);

-- ---------------------------------------------------------------------------
-- 3. Ordered ritual bullets (e.g. "On Ekadashi day, take a bath at daybreak ...")
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_rituals (
    festival_id     TEXT NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    position        INTEGER NOT NULL,
    text            TEXT NOT NULL,
    PRIMARY KEY (festival_id, language, position)
);

-- ---------------------------------------------------------------------------
-- 4. FAQ Q&A pairs at bottom of every astrosage festival page.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_faqs (
    festival_id     TEXT NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    position        INTEGER NOT NULL,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    PRIMARY KEY (festival_id, language, position)
);

-- ---------------------------------------------------------------------------
-- 5. Muhurat type catalog (13 special muhurats from sitemap + the 9 computable ones).
--    `computable=1` rows are derived by services/muhurat.py — DB only adds editorial.
--    `computable=0` rows (griha-pravesh, mundan, vehicle-purchase, …) come from scrape.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS muhurat_types (
    id              TEXT PRIMARY KEY,            -- 'griha-pravesh'|'abhijit'|'rahu'|'pradosh-kaal'|...
    category        TEXT NOT NULL,               -- 'auspicious'|'inauspicious'|'event'|'yoga'
    computable      INTEGER NOT NULL DEFAULT 0,  -- 1 if services/muhurat.py computes it
    source_url      TEXT
);

-- ---------------------------------------------------------------------------
-- 6. Muhurat editorial content per language.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS muhurat_content (
    muhurat_id      TEXT NOT NULL REFERENCES muhurat_types(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,                        -- intro paragraph
    vedic_basis     TEXT,                        -- "as per Vedic Texts" section
    importance      TEXT,                        -- "Importance of ..." section
    scraped_at      TEXT NOT NULL DEFAULT (datetime('now')),
    source_url      TEXT NOT NULL,
    PRIMARY KEY (muhurat_id, language)
);

-- ---------------------------------------------------------------------------
-- 7. Free-form heading/body subsections (e.g. "Different Types of Griha Pravesh").
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS muhurat_subsections (
    muhurat_id      TEXT NOT NULL REFERENCES muhurat_types(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    position        INTEGER NOT NULL,
    heading         TEXT NOT NULL,
    body            TEXT NOT NULL,
    PRIMARY KEY (muhurat_id, language, position)
);

CREATE TABLE IF NOT EXISTS muhurat_faqs (
    muhurat_id      TEXT NOT NULL REFERENCES muhurat_types(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    position        INTEGER NOT NULL,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    PRIMARY KEY (muhurat_id, language, position)
);

-- ---------------------------------------------------------------------------
-- 8. Raw HTML cache — lets us re-parse after scraper improvements without
--    re-hitting astrosage. Body is gzipped to keep size sane.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scraped_pages (
    url             TEXT PRIMARY KEY,
    scope           TEXT NOT NULL,               -- 'festival'|'muhurat'|'festival_list'|'muhurat_list'
    ref_id          TEXT,                        -- festivals.id or muhurat_types.id (when known)
    language        TEXT NOT NULL,
    http_status     INTEGER NOT NULL,
    etag            TEXT,
    fetched_at      TEXT NOT NULL DEFAULT (datetime('now')),
    body_gzip       BLOB NOT NULL,
    parser_version  INTEGER NOT NULL DEFAULT 1,
    parse_error     TEXT
);
CREATE INDEX IF NOT EXISTS idx_scraped_scope ON scraped_pages(scope, ref_id);

-- ---------------------------------------------------------------------------
-- 9. FTS5 for full-text search across editorial text (optional, useful for
--    /v1/festivals/search and a future "what festival mentions Ayodhya?" feature).
-- ---------------------------------------------------------------------------
CREATE VIRTUAL TABLE IF NOT EXISTS festival_content_fts USING fts5(
    festival_id UNINDEXED,
    language    UNINDEXED,
    name,
    subtitle,
    about,
    significance,
    tokenize='unicode61 remove_diacritics 2'
);

-- ---------------------------------------------------------------------------
-- 10. Crawl job log + per-URL task checkpoint.
--     Lets a long-running crawler be cancelled and resumed without losing work.
--     `crawl_tasks` is keyed by URL (global) so a re-run picks up pending/failed
--     entries from any previous job. `last_job_id` tells you which job touched it.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id              TEXT PRIMARY KEY,            -- uuid hex
    scope           TEXT NOT NULL,               -- 'all'|'festivals'|'muhurats'
    language        TEXT NOT NULL,
    status          TEXT NOT NULL,               -- 'running'|'completed'|'cancelled'|'failed'
    started_at      TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at     TEXT,
    is_resume       INTEGER NOT NULL DEFAULT 0,
    force           INTEGER NOT NULL DEFAULT 0,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);

CREATE TABLE IF NOT EXISTS crawl_tasks (
    url             TEXT PRIMARY KEY,
    last_job_id     TEXT REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    scope           TEXT NOT NULL,               -- 'festival'|'muhurat'
    depth           INTEGER NOT NULL,
    status          TEXT NOT NULL,               -- 'pending'|'running'|'done'|'failed'|'cancelled'
    error           TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_crawl_tasks_status ON crawl_tasks(status);
CREATE INDEX IF NOT EXISTS idx_crawl_tasks_job    ON crawl_tasks(last_job_id);

-- ---------------------------------------------------------------------------
-- 11. Persistent cache for expensive festival year snapshots.
--     Keyed by (year, quantized lat/lon, tz spec, ayanamsa, schema version)
--     so warm snapshots survive process restarts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_year_snapshots (
    year            INTEGER NOT NULL,
    lat_key         TEXT NOT NULL,
    lon_key         TEXT NOT NULL,
    tz_name         TEXT NOT NULL,
    ayanamsa        TEXT NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload_gzip    BLOB NOT NULL,
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (year, lat_key, lon_key, tz_name, ayanamsa, schema_version)
);
CREATE INDEX IF NOT EXISTS idx_festival_snapshot_updated
    ON festival_year_snapshots(updated_at);

-- ---------------------------------------------------------------------------
-- 11b. Horoscope predictions (sign × period × language × period_key).
--      Populated lazily by services/horoscope.py — on a cache miss the
--      service scrapes the matching www.astrosage.com page, parses, and
--      UPSERTs here. Subsequent reads (and every read across processes)
--      hit this table without going to the wire.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS horoscope_predictions (
    sign          TEXT NOT NULL,           -- 'aries'..'pisces'
    period        TEXT NOT NULL,           -- 'daily'|'tomorrow'|'weekly'|'weekly_love'|'monthly'|'next_month'|'yearly'
    language      TEXT NOT NULL,           -- 'en','hi',...
    -- period_key buckets a prediction to its calendar window:
    --   daily/tomorrow → 'YYYY-MM-DD'
    --   weekly/weekly_love → 'YYYY-Www' (ISO week)
    --   monthly/next_month → 'YYYY-MM'
    --   yearly → 'YYYY'
    period_key    TEXT NOT NULL,
    date_label    TEXT,                    -- raw label scraped from astrosage (e.g. 'Monday, May 25, 2026')
    prediction    TEXT,                    -- primary body (General section for monthly/yearly)
    love          TEXT,
    career        TEXT,
    finance       TEXT,
    health        TEXT,
    family        TEXT,
    advice        TEXT,
    -- JSON-encoded 6-key dict of 0..5 star ratings, only set for daily/tomorrow:
    -- {"health":4,"wealth":5,"family":5,"love_matters":1,"occupation":1,"married_life":1}
    ratings_json  TEXT,
    source_url    TEXT NOT NULL,
    scraped_at    TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (sign, period, language, period_key)
);
CREATE INDEX IF NOT EXISTS idx_horoscope_scraped_at
    ON horoscope_predictions(scraped_at);

-- ---------------------------------------------------------------------------
-- 11c. Zodiac sign editorial PROSE per language. Populated lazily from
--      www.astrosage.com/horoscope/{sign}.asp on first read of
--      GET /v1/reference/zodiac-signs/{id}.
--
--      Structural fields (name, vedic_name, symbol, date_range, lord) are
--      NOT stored here — they live in Python constants and are merged into
--      the API response at read time. Only fields the scrape produces are
--      persisted, keeping a single source of truth per field.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zodiac_signs (
    id                  TEXT NOT NULL,     -- 'aries'..'pisces'
    language            TEXT NOT NULL,
    -- From www.astrosage.com/horoscope/{sign}.asp (sign_intro parser):
    summary             TEXT,              -- "What is <Sign> Sign?" body / lead paragraph(s)
    traits              TEXT,
    love                TEXT,
    compatibility       TEXT,
    -- From www.astrosage.com/horoscope/daily-{sign}-horoscope.asp (horoscope
    -- parser's deep-dive extractor). Filled opportunistically whenever the
    -- daily horoscope is scraped for this sign × language; safe to be NULL
    -- if only sign_intro has been fetched so far.
    overview            TEXT,              -- "<Sign> Zodiac Sign" body
    physical_appearance TEXT,
    mental_ability      TEXT,
    characteristics     TEXT,
    aspects_of_life     TEXT,              -- "What does <Sign> sign signify in various aspects of life?"
    twelve_houses       TEXT,              -- "What do all 12 houses signify for <Sign> born?"
    source_url          TEXT NOT NULL,
    scraped_at          TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (id, language)
);

-- ---------------------------------------------------------------------------
-- 12. GeoNames location tables (used by services/locations.py).
--     Source of truth for /v1/locations/{search,resolve,{id}}.
--     The build pipeline (locations.build_database) explicitly DROPs these
--     before reloading, so CREATE IF NOT EXISTS here is safe for both
--     first-boot and post-build re-runs of this file via ensure_schema().
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geonames_cities (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    asciiname     TEXT NOT NULL,
    country       TEXT NOT NULL,
    admin1_code   TEXT,
    admin2_code   TEXT,
    lat           REAL NOT NULL,
    lon           REAL NOT NULL,
    tz            TEXT NOT NULL,
    population    INTEGER NOT NULL DEFAULT 0,
    feature_code  TEXT
);
CREATE INDEX IF NOT EXISTS idx_cities_country ON geonames_cities(country);

CREATE TABLE IF NOT EXISTS geonames_admin1 (
    code        TEXT PRIMARY KEY,                -- e.g. "IN.36"
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS geonames_admin2 (
    code        TEXT PRIMARY KEY,                -- e.g. "IN.36.182"
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS countries (
    iso2     TEXT PRIMARY KEY,
    name     TEXT NOT NULL
);

-- FTS5 typeahead index. unicode61 + remove_diacritics so "varan" matches
-- "Vārāṇasī" and "वाराणसी" (when altnames are loaded).
CREATE VIRTUAL TABLE IF NOT EXISTS cities_fts USING fts5(
    name,
    content='',
    tokenize="unicode61 remove_diacritics 2"
);

-- R*Tree for /resolve's nearest-city query.
CREATE VIRTUAL TABLE IF NOT EXISTS cities_rtree USING rtree(
    id,
    min_lat, max_lat,
    min_lon, max_lon
);
