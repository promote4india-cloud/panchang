-- Editorial / scraped-content schema for PostgreSQL.
-- All tables use CREATE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS.
-- One database shared by all services (GeoNames + editorial content).

-- Enable trigram extension for fast prefix/fuzzy location search.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------------------------------------------------------------------------
-- 1. Festival catalog
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festivals (
    id              TEXT PRIMARY KEY,
    parent_id       TEXT REFERENCES festivals(id) ON DELETE SET NULL,
    slug_path       TEXT NOT NULL UNIQUE,
    kind            TEXT NOT NULL,
    type            TEXT,
    auspiciousness  TEXT,
    rule_type       TEXT,
    rule_json       TEXT,
    scope_traditions TEXT,
    thumbnail_url   TEXT,
    source_url      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_festivals_parent ON festivals(parent_id);
CREATE INDEX IF NOT EXISTS idx_festivals_kind   ON festivals(kind);

-- ---------------------------------------------------------------------------
-- 2. Editorial text per language
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_content (
    festival_id     TEXT NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    name            TEXT NOT NULL,
    subtitle        TEXT,
    about           TEXT,
    significance    TEXT,
    history         TEXT,
    scriptures      TEXT,
    puja_vidhi      TEXT,
    llm_cleaned_at  TEXT,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_url      TEXT NOT NULL,
    PRIMARY KEY (festival_id, language)
);

-- ---------------------------------------------------------------------------
-- 3. Ordered ritual bullets
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_rituals (
    festival_id     TEXT NOT NULL REFERENCES festivals(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    position        INTEGER NOT NULL,
    text            TEXT NOT NULL,
    PRIMARY KEY (festival_id, language, position)
);

-- ---------------------------------------------------------------------------
-- 4. Festival FAQs
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
-- 5. Muhurat type catalog
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS muhurat_types (
    id              TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    computable      INTEGER NOT NULL DEFAULT 0,
    source_url      TEXT
);

-- ---------------------------------------------------------------------------
-- 6. Muhurat editorial content per language
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS muhurat_content (
    muhurat_id      TEXT NOT NULL REFERENCES muhurat_types(id) ON DELETE CASCADE,
    language        TEXT NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    vedic_basis     TEXT,
    importance      TEXT,
    llm_cleaned_at  TEXT,
    scraped_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    source_url      TEXT NOT NULL,
    PRIMARY KEY (muhurat_id, language)
);

-- ---------------------------------------------------------------------------
-- 7. Muhurat subsections
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
-- 8. Raw HTML cache (gzipped body stored as BYTEA)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS scraped_pages (
    url             TEXT PRIMARY KEY,
    scope           TEXT NOT NULL,
    ref_id          TEXT,
    language        TEXT NOT NULL,
    http_status     INTEGER NOT NULL,
    etag            TEXT,
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    body_gzip       BYTEA NOT NULL,
    parser_version  INTEGER NOT NULL DEFAULT 1,
    parse_error     TEXT
);
CREATE INDEX IF NOT EXISTS idx_scraped_scope ON scraped_pages(scope, ref_id);

-- ---------------------------------------------------------------------------
-- 9. Crawl job log + per-URL task checkpoint
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS crawl_jobs (
    id              TEXT PRIMARY KEY,
    scope           TEXT NOT NULL,
    language        TEXT NOT NULL,
    status          TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    is_resume       INTEGER NOT NULL DEFAULT 0,
    force           INTEGER NOT NULL DEFAULT 0,
    note            TEXT
);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON crawl_jobs(status);

CREATE TABLE IF NOT EXISTS crawl_tasks (
    url             TEXT PRIMARY KEY,
    last_job_id     TEXT REFERENCES crawl_jobs(id) ON DELETE SET NULL,
    scope           TEXT NOT NULL,
    depth           INTEGER NOT NULL,
    status          TEXT NOT NULL,
    error           TEXT,
    attempts        INTEGER NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_crawl_tasks_status ON crawl_tasks(status);
CREATE INDEX IF NOT EXISTS idx_crawl_tasks_job    ON crawl_tasks(last_job_id);

-- ---------------------------------------------------------------------------
-- 10. Festival year snapshot cache (gzipped payload)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS festival_year_snapshots (
    year            INTEGER NOT NULL,
    lat_key         TEXT NOT NULL,
    lon_key         TEXT NOT NULL,
    tz_name         TEXT NOT NULL,
    ayanamsa        TEXT NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload_gzip    BYTEA NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (year, lat_key, lon_key, tz_name, ayanamsa, schema_version)
);
CREATE INDEX IF NOT EXISTS idx_festival_snapshot_updated
    ON festival_year_snapshots(updated_at);

-- ---------------------------------------------------------------------------
-- 11. Horoscope predictions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS horoscope_predictions (
    sign          TEXT NOT NULL,
    period        TEXT NOT NULL,
    language      TEXT NOT NULL,
    period_key    TEXT NOT NULL,
    date_label    TEXT,
    prediction    TEXT,
    love          TEXT,
    career        TEXT,
    finance       TEXT,
    health        TEXT,
    family        TEXT,
    advice        TEXT,
    ratings_json  TEXT,
    llm_cleaned_at TEXT,
    source_url    TEXT NOT NULL,
    scraped_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (sign, period, language, period_key)
);
CREATE INDEX IF NOT EXISTS idx_horoscope_scraped_at
    ON horoscope_predictions(scraped_at);

-- ---------------------------------------------------------------------------
-- 12. Zodiac sign editorial prose per language
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS zodiac_signs (
    id                  TEXT NOT NULL,
    language            TEXT NOT NULL,
    summary             TEXT,
    traits              TEXT,
    love                TEXT,
    compatibility       TEXT,
    overview            TEXT,
    physical_appearance TEXT,
    mental_ability      TEXT,
    characteristics     TEXT,
    aspects_of_life     TEXT,
    twelve_houses       TEXT,
    llm_cleaned_at      TEXT,
    source_url          TEXT NOT NULL,
    scraped_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, language)
);

-- ---------------------------------------------------------------------------
-- 13. GeoNames location tables
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geonames_cities (
    id            BIGINT PRIMARY KEY,
    name          TEXT NOT NULL,
    asciiname     TEXT NOT NULL,
    country       TEXT NOT NULL,
    admin1_code   TEXT,
    admin2_code   TEXT,
    lat           DOUBLE PRECISION NOT NULL,
    lon           DOUBLE PRECISION NOT NULL,
    tz            TEXT NOT NULL,
    population    BIGINT NOT NULL DEFAULT 0,
    feature_code  TEXT
);
CREATE INDEX IF NOT EXISTS idx_cities_country ON geonames_cities(country);
-- Bounding-box index for /resolve nearest-city query (replaces R*Tree).
CREATE INDEX IF NOT EXISTS idx_cities_lat_lon ON geonames_cities(lat, lon);
-- Trigram indexes for prefix/fuzzy location name search (replaces FTS5).
CREATE INDEX IF NOT EXISTS idx_cities_name_trgm     ON geonames_cities USING GIN (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_cities_ascii_trgm    ON geonames_cities USING GIN (asciiname gin_trgm_ops);

CREATE TABLE IF NOT EXISTS geonames_admin1 (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS geonames_admin2 (
    code        TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    ascii_name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS countries (
    iso2     TEXT PRIMARY KEY,
    name     TEXT NOT NULL
)
