-- HAKARI EVENT LOG SCHEMA
-- =======================

-- Enable UUID extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. MAIN EVENT TABLE
CREATE TABLE IF NOT EXISTS hakari_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ts TIMESTAMPTZ DEFAULT now(),
    instance_id TEXT NOT NULL,
    event_type TEXT NOT NULL, -- 'decision_made', 'result_recorded', 'policy_updated'
    platform TEXT,            -- 'prizepicks', 'underdog'
    mode TEXT,                -- 'autonomous', 'assisted', 'shadow'
    slip_id TEXT,             -- Correlates events for one slip
    event_version INTEGER DEFAULT 1,
    payload JSONB NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_hakari_events_ts ON hakari_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_hakari_events_slip_id ON hakari_events(slip_id);
CREATE INDEX IF NOT EXISTS idx_hakari_events_type ON hakari_events(event_type);
CREATE INDEX IF NOT EXISTS idx_hakari_events_instance ON hakari_events(instance_id);

-- 2. SLIP SUMMARY TABLE (Optional, derived view-like table for easy query)
CREATE TABLE IF NOT EXISTS hakari_slips (
    slip_id TEXT PRIMARY KEY,
    ts_created TIMESTAMPTZ DEFAULT now(),
    platform TEXT,
    mode TEXT,
    legs_count INTEGER,
    stake NUMERIC,
    submitted BOOLEAN DEFAULT FALSE,
    outcome TEXT DEFAULT 'PENDING', -- 'WON', 'LOST', 'PUSH'
    money_won_lost NUMERIC DEFAULT 0,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_hakari_slips_ts ON hakari_slips(ts_created DESC);

-- 3. RLS POLICIES (Simple Starting Point)
ALTER TABLE hakari_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE hakari_slips ENABLE ROW LEVEL SECURITY;

-- Allow everything for anon (if using simple API key setup for single user)
-- For multi-user, you'd restrict by user_id or instance_id
CREATE POLICY "Allow All Access" ON hakari_events
    FOR ALL
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Allow All Access" ON hakari_slips
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- 4. ANALYTICS VIEWS

-- Hit Rate by Stat Type
CREATE OR REPLACE VIEW v_hit_rate_by_stat AS
SELECT 
    e.platform,
    l->>'stat' as stat_type,
    count(*) as total_legs,
    sum(case when (l->>'hit')::boolean then 1 else 0 end) as hits,
    round(sum(case when (l->>'hit')::boolean then 1 else 0 end)::numeric / count(*), 3) as hit_rate
FROM hakari_events e,
     jsonb_array_elements(e.payload->'results') as l
WHERE e.event_type = 'result_recorded'
GROUP BY 1, 2
ORDER BY 3 DESC;

-- ROI by Tag
CREATE OR REPLACE VIEW v_roi_by_risk_tag AS
SELECT 
    t as risk_tag,
    count(distinct e.slip_id) as slips_involved,
    sum((e.payload->>'money_won_lost')::numeric) as total_pnl
FROM hakari_events e
JOIN hakari_events d ON d.slip_id = e.slip_id AND d.event_type = 'decision_made',
     jsonb_array_elements_text(d.payload->'thresholds_used'->'risk_tags') as t -- Assuming risk tags are at slip level or aggregated
WHERE e.event_type = 'result_recorded'
GROUP BY 1
ORDER BY 3 DESC;
