-- Project Cortex: Supabase Database Schema
-- ==========================================
-- Run this in your Supabase SQL Editor to set up the database

-- Enable UUID extension
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable Vector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ==========================================
-- PHASE 1: Core Tables
-- ==========================================

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(255) UNIQUE NOT NULL,  -- Your app's user ID
    email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations table (chat history with model attribution)
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    model_used VARCHAR(100),
    intent VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster user lookups
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- user_memories table (long-term facts about the user)
CREATE TABLE IF NOT EXISTS user_memories (
    id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    tags TEXT[],
    confidence FLOAT DEFAULT 1.0,
    embedding VECTOR(1536),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    evidence TEXT[],
    version INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_user_memories_user_id ON user_memories(user_id);
CREATE INDEX IF NOT EXISTS idx_user_memories_tags ON user_memories USING GIN(tags);


-- ==========================================
-- PHASE 2: Financial Tables (uncomment when needed)
-- ==========================================

/*
-- Financial accounts linked via Plaid
CREATE TABLE IF NOT EXISTS financial_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    plaid_account_id VARCHAR(255) UNIQUE,
    institution_name VARCHAR(255),
    account_name VARCHAR(255),
    account_type VARCHAR(50),  -- 'checking', 'savings', 'credit', etc.
    current_balance DECIMAL(12, 2),
    available_balance DECIMAL(12, 2),
    last_synced TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transactions from Plaid
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    account_id UUID REFERENCES financial_accounts(id),
    plaid_transaction_id VARCHAR(255) UNIQUE,
    amount DECIMAL(12, 2) NOT NULL,
    category VARCHAR(100),
    merchant_name VARCHAR(255),
    description TEXT,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user_date ON transactions(user_id, transaction_date DESC);
*/

-- ==========================================
-- PHASE 3: Productivity Tables (uncomment when needed)
-- ==========================================

/*
-- Calendar events synced from Google/Outlook
CREATE TABLE IF NOT EXISTS calendar_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    external_id VARCHAR(255),  -- Google/Outlook event ID
    title VARCHAR(500) NOT NULL,
    description TEXT,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    location VARCHAR(500),
    source VARCHAR(50),  -- 'google', 'outlook'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_calendar_user_start ON calendar_events(user_id, start_time);
*/

-- ==========================================
-- PHASE 4: Learning Agent Tables
-- ==========================================

-- Agent feedback for learning loop
CREATE TABLE IF NOT EXISTS agent_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    task_id UUID,
    original_query TEXT NOT NULL,
    athena_response TEXT NOT NULL,
    user_rating INTEGER CHECK (user_rating >= 1 AND user_rating <= 5),
    user_edited_response TEXT,
    feedback_category VARCHAR(50),  -- 'helpful', 'incorrect', 'incomplete', 'could_improve'
    lesson_extracted TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_user ON agent_feedback(user_id, created_at DESC);

-- Extracted learnings from feedback
CREATE TABLE IF NOT EXISTS agent_learnings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    pattern_name VARCHAR(100) NOT NULL,
    instruction TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.5,
    times_reinforced INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, pattern_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_learnings_user ON agent_learnings(user_id, confidence DESC);

-- ==========================================
-- PHASE 5: Secure API Key Vault Tables
-- ==========================================

-- API key vault (encrypted storage)
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    encrypted_key TEXT NOT NULL,
    key_type VARCHAR(50),  -- 'oauth_token', 'api_key', 'bearer_token'
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    UNIQUE(user_id, service_name)
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON api_keys(user_id);

-- Audit log for key access
CREATE TABLE IF NOT EXISTS api_key_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    accessed_at TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_api_key_access_log_user ON api_key_access_log(user_id, accessed_at DESC);

-- ==========================================
-- PHASE 6: Health & Preferences (uncomment when needed)
-- ==========================================

/*
-- Health observations from Health Connect
CREATE TABLE IF NOT EXISTS health_observations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    observation_type VARCHAR(50) NOT NULL,  -- 'steps', 'heart_rate', 'sleep', etc.
    value DECIMAL(12, 4) NOT NULL,
    unit VARCHAR(20),
    recorded_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_user_type ON health_observations(user_id, observation_type, recorded_at DESC);

-- User preferences and learned patterns
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB,
    confidence FLOAT DEFAULT 0.5,
    learned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, preference_key)
);

-- Sensitive data access confirmations (security)
CREATE TABLE IF NOT EXISTS access_confirmations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,  -- 'health', 'financial', 'identity'
    confirmed_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    confirmation_method VARCHAR(50),  -- 'pin', 'biometric', '2fa'
    is_active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_confirmations_user ON access_confirmations(user_id, category, expires_at);
*/

-- ==========================================
-- PHASE 7: Memory Core v3.0 (Athena Brain)
-- ==========================================

-- memory_logs: Full history of interactions
CREATE TABLE IF NOT EXISTS memory_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_input TEXT,
    athena_response TEXT,
    summary TEXT,
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- agent_states: Persistence for sub-agents
CREATE TABLE IF NOT EXISTS agent_states (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_name, key)
);

-- user_facts: Learned preferences and traits
CREATE TABLE IF NOT EXISTS user_facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key VARCHAR(100) NOT NULL,
    value JSONB,
    category VARCHAR(50) DEFAULT 'preference',
    source VARCHAR(50) DEFAULT 'inference',
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(key, category)
);

-- athena_monologue: Internal thought stream
CREATE TABLE IF NOT EXISTS athena_monologue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thought_process TEXT,
    action_taken VARCHAR(100),
    category VARCHAR(50),
    success_score INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- agent_registry: Task orchestration
CREATE TABLE IF NOT EXISTS agent_registry (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id VARCHAR(100) UNIQUE NOT NULL,
    agent_name VARCHAR(100),
    task_description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_output TEXT,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PHASE 8: Deep Mind Analysis (Causality Engine)
-- ============================================================================

-- 1. INFLUENCE_CLOUD (Causality Engine)
CREATE TABLE IF NOT EXISTS influence_cloud (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT DEFAULT 'media',
    keywords TEXT[] NOT NULL,
    consumed_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_influence_cloud_expires ON influence_cloud(expires_at);
CREATE INDEX IF NOT EXISTS idx_influence_cloud_category ON influence_cloud(category);
CREATE INDEX IF NOT EXISTS idx_influence_cloud_keywords ON influence_cloud USING GIN(keywords);

ALTER TABLE influence_cloud ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access to influence_cloud" ON influence_cloud;
CREATE POLICY "Full access to influence_cloud" ON influence_cloud FOR ALL USING (true) WITH CHECK (true);

-- 2. PRECOMPUTED_FEATURES (Analytics Cache)
CREATE TABLE IF NOT EXISTS precomputed_features (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    category TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value JSONB NOT NULL,
    period_start DATE,
    period_end DATE,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(category, feature_name, period_start)
);

CREATE INDEX IF NOT EXISTS idx_features_category ON precomputed_features(category);
CREATE INDEX IF NOT EXISTS idx_features_expires ON precomputed_features(expires_at);

ALTER TABLE precomputed_features ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access to precomputed_features" ON precomputed_features;
CREATE POLICY "Full access to precomputed_features" ON precomputed_features FOR ALL USING (true) WITH CHECK (true);

-- 3. ANALYSIS_AUDIT (Evidence Trail)
CREATE TABLE IF NOT EXISTS analysis_audit (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    session_id TEXT,
    query TEXT,
    analysis_mode TEXT,
    data_sources TEXT[],
    records_accessed INTEGER DEFAULT 0,
    conclusion TEXT,
    confidence REAL,
    evidence_summary JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON analysis_audit(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_mode ON analysis_audit(analysis_mode);

ALTER TABLE analysis_audit ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access to analysis_audit" ON analysis_audit;
CREATE POLICY "Full access to analysis_audit" ON analysis_audit FOR ALL USING (true) WITH CHECK (true);

-- 4. PURCHASE_ATTRIBUTIONS (Causality Results)
CREATE TABLE IF NOT EXISTS purchase_attributions (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    item_name TEXT NOT NULL,
    amount DECIMAL(10,2),
    purchase_date TIMESTAMP WITH TIME ZONE,
    influence_source TEXT,
    influence_category TEXT,
    matched_keywords TEXT[],
    confidence REAL DEFAULT 0.0,
    days_after_consumption INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::TEXT, NOW()) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attributions_source ON purchase_attributions(influence_source);
CREATE INDEX IF NOT EXISTS idx_attributions_category ON purchase_attributions(influence_category);

ALTER TABLE purchase_attributions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Full access to purchase_attributions" ON purchase_attributions;
CREATE POLICY "Full access to purchase_attributions" ON purchase_attributions FOR ALL USING (true) WITH CHECK (true);

-- Enable RLS on all tables
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_memories ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own data
DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
CREATE POLICY "Users can insert own conversations" ON conversations
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can view own memories" ON user_memories;
CREATE POLICY "Users can view own memories" ON user_memories
    FOR SELECT USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can manage own memories" ON user_memories;
CREATE POLICY "Users can manage own memories" ON user_memories
    FOR ALL USING (auth.uid()::text = user_id);

-- Enable RLS on new tables
ALTER TABLE agent_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_learnings ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_key_access_log ENABLE ROW LEVEL SECURITY;

-- Policies for learning agent tables
DROP POLICY IF EXISTS "Users can manage own feedback" ON agent_feedback;
CREATE POLICY "Users can manage own feedback" ON agent_feedback
    FOR ALL USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can manage own learnings" ON agent_learnings;
CREATE POLICY "Users can manage own learnings" ON agent_learnings
    FOR ALL USING (auth.uid()::text = user_id);

-- Policies for vault tables (read-only for users, managed by service role)
DROP POLICY IF EXISTS "Users can view own api_keys" ON api_keys;
CREATE POLICY "Users can view own api_keys" ON api_keys
    FOR SELECT USING (auth.uid()::text = user_id);

DROP POLICY IF EXISTS "Users can view own access_log" ON api_key_access_log;
CREATE POLICY "Users can view own access_log" ON api_key_access_log
    FOR SELECT USING (auth.uid()::text = user_id);
