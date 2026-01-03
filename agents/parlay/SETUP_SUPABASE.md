# Supabase Setup Guide for Hakari

This guide details how to configure the Supabase backend for persistent event logging.

## 1. Create Supabase Project
1. Go to [Supabase Console](https://supabase.com/dashboard).
2. Click **New Project**.
3. Name: `Hakari-DB` (or similar).
4. Set database password and region (e.g., US East).
5. Wait for provisioning.

## 2. Environment Variables
Get your **Project URL** and **anon public key** from `Settings > API`.
Add them to your `.env` file in the `Athena_Project` root (or `agents/parlay/.env`):

```bash
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5...
HAKARI_INSTANCE_ID=hakari-cli-01
```

## 3. Database Schema
1. Go to **SQL Editor** in the left sidebar.
2. Open the file `agents/parlay/supabase_schema.sql` from this repo.
3. Copy the entire content.
4. Paste into the SQL Editor in Supabase.
5. Click **Run**.
   - This creates `hakari_events` table.
   - Enables `pgcrypto` extension for UUIDs.
   - Sets up indexes and basic RLS policies.
   - Creates analytics views (`v_hit_rate_by_stat`, etc).

## 4. Verification
1. Go to **Table Editor**.
2. Confirm `hakari_events` exists.
3. Run the Hakari agent:
   ```bash
   python agent.py --command /status
   ```
   or
   ```bash
   python agent.py --command /flush
   ```
4. You should see logs appear in the `hakari_events` table.

## 5. Security Note (RLS)
The provided schema includes a "Allow All Access" policy for simplicity (`USING (true)`). 
For production multi-user environments, you should restrict this:
```sql
CREATE POLICY "Agent Access" ON hakari_events
  FOR ALL
  USING (instance_id = current_setting('app.current_instance_id', true));
```
(Requires setting headers in the client). 
For now, the default API key protection is sufficient for a personal agent.
