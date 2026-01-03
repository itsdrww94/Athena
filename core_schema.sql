-- Athena 2.0 Core Schema (Cloud-First Architecture)

-- 1. Unified Event Timeline
-- The single source of truth for all activity (Gmail, YouTube, etc.)
CREATE TABLE IF NOT EXISTS unified_events (
    event_id TEXT PRIMARY KEY,          -- Deterministic Hash
    event_type TEXT NOT NULL,           -- TRANSACTION, WATCH, etc.
    source TEXT NOT NULL,               -- gmail, youtube_takeout
    actor TEXT DEFAULT 'drew',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    privacy_level TEXT DEFAULT 'MED',
    raw_ref TEXT,                       -- Pointer to Vault (GCS)
    data JSONB DEFAULT '{}'::JSONB,     -- The payload
    derived JSONB DEFAULT '{}'::JSONB,  -- Computed features
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON unified_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON unified_events(event_type);

-- 2. Semantic Memory
-- Stable facts and preferences
CREATE TABLE IF NOT EXISTS memories_semantic (
    fact_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    category TEXT NOT NULL,             -- preference, goal
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_ref TEXT,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    embedding VECTOR(1536)              -- For pgvector search
);

-- 3. Episodic Memory (Capsules)
-- Compressed daily summaries
CREATE TABLE IF NOT EXISTS memories_episodic (
    episode_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    summary TEXT NOT NULL,
    highlights JSONB DEFAULT '{}'::JSONB,
    embedding VECTOR(1536),             -- For finding "similar days"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Patterns Registry
-- Detected habits and modes
CREATE TABLE IF NOT EXISTS patterns_registry (
    pattern_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,                 -- motif, association
    confidence FLOAT,
    status TEXT DEFAULT 'hypothesis',   -- hypothesis, confirmed, rejected
    meta JSONB DEFAULT '{}'::JSONB,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
