-- Kanshan PostgreSQL initialization
-- This script runs automatically when the postgres container starts for the first time.

CREATE SCHEMA IF NOT EXISTS profile;
CREATE SCHEMA IF NOT EXISTS seed;
CREATE SCHEMA IF NOT EXISTS writing;
CREATE SCHEMA IF NOT EXISTS sprout;
CREATE SCHEMA IF NOT EXISTS feedback;

-- Profile schema tables
CREATE TABLE IF NOT EXISTS profile.users (
    user_id VARCHAR PRIMARY KEY,
    nickname VARCHAR NOT NULL,
    email VARCHAR UNIQUE,
    username VARCHAR UNIQUE,
    password_hash VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    setup_state VARCHAR NOT NULL DEFAULT 'zhihu_pending'
);

CREATE TABLE IF NOT EXISTS profile.sessions (
    session_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL,
    expires_at VARCHAR
);

CREATE TABLE IF NOT EXISTS profile.zhihu_bindings (
    user_id VARCHAR PRIMARY KEY,
    zhihu_uid VARCHAR,
    access_token TEXT,
    binding_status VARCHAR NOT NULL DEFAULT 'not_started',
    bound_at VARCHAR,
    expired_at VARCHAR
);

CREATE TABLE IF NOT EXISTS profile.profile_data (
    id VARCHAR PRIMARY KEY DEFAULT 'default',
    data TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile.profile_versions (
    id VARCHAR PRIMARY KEY,
    target VARCHAR NOT NULL,
    snapshot TEXT NOT NULL,
    reason VARCHAR NOT NULL,
    created_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS profile.memory_update_requests (
    id VARCHAR PRIMARY KEY,
    interest_id VARCHAR NOT NULL,
    target_field VARCHAR NOT NULL,
    suggested_value TEXT NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS profile.writing_styles (
    user_id VARCHAR PRIMARY KEY,
    logic_depth INTEGER DEFAULT 3,
    stance_sharpness INTEGER DEFAULT 3,
    personal_experience INTEGER DEFAULT 3,
    expression_sharpness INTEGER DEFAULT 3,
    uncertainty_tolerance INTEGER DEFAULT 3,
    preferred_format VARCHAR DEFAULT 'long_article',
    evidence_vs_judgment VARCHAR DEFAULT 'balanced',
    opening_style VARCHAR DEFAULT 'question',
    title_style VARCHAR DEFAULT 'controversy',
    emotional_temperature VARCHAR DEFAULT 'rational',
    ai_assistance_boundary VARCHAR DEFAULT 'draft_only',
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS profile.llm_configs (
    user_id VARCHAR PRIMARY KEY,
    provider VARCHAR DEFAULT 'openai_compat',
    model VARCHAR DEFAULT 'gpt-5.5',
    base_url VARCHAR,
    api_key TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Sprout schema tables
CREATE TABLE IF NOT EXISTS sprout.opportunities (
    id VARCHAR PRIMARY KEY,
    seed_id VARCHAR,
    interest_id VARCHAR,
    run_id VARCHAR,
    trigger_type VARCHAR,
    status VARCHAR,
    score VARCHAR,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_sprout_opportunities_run_id ON sprout.opportunities (run_id);

CREATE TABLE IF NOT EXISTS sprout.runs (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR,
    interest_id VARCHAR,
    status VARCHAR,
    data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Content schema tables
CREATE SCHEMA IF NOT EXISTS content;

CREATE TABLE IF NOT EXISTS content.user_profile_snapshots (
    user_id VARCHAR PRIMARY KEY,
    snapshot JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    source_hash VARCHAR
);

CREATE TABLE IF NOT EXISTS content.user_shown_cards (
    user_id VARCHAR NOT NULL,
    card_id VARCHAR NOT NULL,
    shown_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, card_id)
);

CREATE TABLE IF NOT EXISTS profile.enrichment_jobs (
    job_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'queued',
    trigger VARCHAR NOT NULL DEFAULT 'oauth_bound',
    include_sources TEXT,
    temporary_profile TEXT,
    signal_counts TEXT,
    memory_update_request_ids TEXT,
    error_message TEXT,
    created_at VARCHAR NOT NULL,
    updated_at VARCHAR NOT NULL
);
