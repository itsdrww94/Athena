# Athena Agent Guide
*Complete documentation for the Athena Agentic System*

## 🛡️ MASTER DIRECTIVE: Total Context Awareness with Guardrails

1.  **Analyze Raw Data**: Athena may analyze raw personal data (Uber, Social, Spotify, Google/YouTube, email) to extract patterns and improve assistance.
2.  **Evidence Vault**: Raw/precise/sensitive data (exact addresses, exact timestamps, raw queries, private messages, health details) must be stored **only in an encrypted Evidence Vault** with retention rules and access flags.
3.  **Derived Memory**: Long-term memory stores only **derived summaries**, stable preferences, constraints, goals, routines, and trends with Type/Confidence/Recency/Expiry and evidence references—**not raw logs**.
4.  **Hypothesis First**: Cross-dataset meaning must be expressed as **hypotheses** unless confirmed; require triangulation or repeated evidence for high confidence.
5.  **Context Capsules**: Agents receive a minimal **Context Capsule**: only relevant preferences/constraints/trends; never raw logs or sensitive content by default.
6.  **Hub-Only Writes**: Agents propose memory updates; **only Athena commits memory changes**.
7.  **Audit Loop**: Every ingestion ends with Patterns, Hypotheses, Adaptations, Memory updates, and a privacy audit of sensitive data access.

---

## 🧠 The Architecture: Scientist + Lab Notebook

Athena operates as a **Hub** (You) with **Specialist Spokes** (Agents) and a structured **Memory Lab**.

### A) Three Memory Layers
1.  **Long-Term Memory (LTM)** – *Stable Truths*
    *   Preferences, constraints, long-term goals, "rules of User", recurring likes/dislikes.
2.  **Working Memory (WM)** – *Trends & Current Phase (30–90 days)*
    *   "Action movies up this month", "Uber spend spiking Fridays", "Sleep shifted later".
3.  **Evidence Vault (EV)** – *Raw, Precise, Sensitive*
    *   Exact locations, timestamps, raw queries, email bodies, health details.
    *   **Encrypted + Access Controlled**. Athena queries it; never sprays it into prompts.

### B) The Pattern Engine
*   **Signal**: One event ("watched action movie")
*   **Pattern**: Repeated signals ("action watch share up 30% vs baseline")
*   **Hypothesis**: Explanation ("action is current wind-down mode") - *labeled as hypothesis*
*   **Action**: Adaptation ("recommend action first")

### C) Context Capsules
When launching an agent, Athena sends a **Capsule**:
*   Task goal + success criteria
*   Relevant preferences (domain-specific only)
*   Relevant constraints (budget, time)
*   Recent trends (from WM)
*   *Excluded*: Raw data, exact addresses, private messages (unless explicitly fetched from Vault)

---

## 📋 Quick Reference

| Agent | Command | Description |
|-------|---------|-------------|
| Finance Manager | `/finance` | 💰 Track expenses & budget model |
| Transaction Hunter | `/scan` | 📧 Scan receipts & normalize events |
| Deal Sniper | `/deals` | 🎯 Find deals matching *buying behavior* |
| News Brief | `/news` | 📰 Track interest shifts & brief |
| MSP Scout | `/events` | 🏙️ Pattern-matched event finding |
| Cinema Companion | `/movies` | 🎬 Taste model & trend detection |
| Health Sync | `/health` | 🏥 Correlation detector (Sleep ↔ Productivity) |
| Vet Manager | `/pets` | 🐱 Pet care consistency & forecasting |
| Notion Agent | `/notion` | 📝 **The Scribe** - Finance & Journal Sync |
| Parlay Agent | `/fever` | 🔥 **Hakari** - Jackpot Hunter & Risk Manager |
| Medic | `/medic` | 🏥 System telemetry & blame assignment |

---

## 📝 Notion Agent (`notion_agent.py`)
*Scientist Job: The Scribe - ensure digital records map to physical reality.*

*   **Log:** Financial records, journal entries, project updates.
*   **Store:**
    *   **LTM:** Page IDs of stable dashboards.
    *   **WM:** Recent journal sentiment.
    *   **EV:** Raw private journal text (if synced to Notion, treat Notion as a Vault).
*   **Compare Against:** Budget limits (Finance), Mood trends (Health).
*   **Context Capsule:** Current tagging taxonomy, budget limits.
*   **Commands:**
    *   `python agents/notion_agent.py log-expense --amount 50 --category Food --description "Groceries"`
    *   `python agents/notion_agent.py journal --content "Had a great day" --mood Happy`

| Protocol Omega | `/omega` | 🔴 Dead Man's Switch (Isolated) |
| Agent Factory | `/build` | 🏭 **GOD MODE** (Standard Enforcer) |

---

## 💰 Finance Manager (`finance_manager.py`)
*Scientist Job: Build spending model + detect drift vs goals.*

*   **Log (Events):** Purchases with category, amount, merchant, time_bucket.
*   **Store:**
    *   **LTM:** Budget rules, stable categories, recurring bills, goal targets.
    *   **WM:** Weekly spend trend, "leak categories", impulse windows.
    *   **EV:** Exact transaction IDs, full descriptions.
*   **Compare Against:** Goals (debt payoff), constraints, behavioral triggers.
*   **Context Capsule:** Current goals, caps, known subs, "impulse risk" level.
*   **Tweak:** **Friction Controls** - When impulse risk is high, throttle Deal Sniper.

## 📧 Transaction Hunter (`transaction_hunter.py`)
*Scientist Job: Turn messy inbox into clean finance events.*

*   **Log:** Receipt events with merchant, amount, date, inferred category.
*   **Store:**
    *   **LTM:** Trusted merchants + mapping rules ("Target → Household").
    *   **WM:** Recent purchase patterns.
    *   **EV:** Email body, attachments, PDFs.
*   **Compare Against:** Finance Manager ledger (reconcile missing).
*   **Context Capsule:** Category taxonomy, min confidence, "NO RAW STORAGE" rule.
*   **Tweak:** **Dedupe & Reconcile** - Prevent double-logging.

## 🎯 Deal Sniper (`deal_sniper.py`)
*Scientist Job: Identify deals matching actual behavior without feeding impulses.*

*   **Log:** Deal events with category, price, source, relevance.
*   **Store:**
    *   **LTM:** Allowed/banned categories, brand preferences.
    *   **WM:** Watchlist changes, "temptation categories".
    *   **EV:** Exact URLs, scraped text.
*   **Compare Against:** Current budget, impulse risk (WM), device inventory.
*   **Context Capsule:** Allowed domains, freeze rules, high-priority wants.
*   **Tweak:** **Cooldown Mode** - If overspending, show only *needs*, no candy.

## 🔥 Parlay Agent (`agents/parlay/agent.py`)
*Scientist Job: Hakari - Manage risk, detect fever, and exploit incentives.*

*   **Log:** Betting slips, fever state (heating up/boiling), jackpot hits.
*   **Store:**
    *   **LTM:** ROI history, favorite props, "bad beat" blacklist.
    *   **WM:** Current "Hot Streak" status (Fever Mode).
    *   **EV:** Exact slip projections.
*   **Compare Against:** Bankroll limits (Finance Manager).
*   **Context Capsule:** Active fevers, referee assignments, veteran fatigue.
*   **Tweak:** **Narrative Override** - Factoring in "Revenge Games" and "Birthday Games".
*   **Commands:**
    *   `/fever` - Detect Jackpots (Mispriced lines).
    *   `/bag_watch` - Identify contract incentives.
    *   `/ref_report` - Analyze referee bias (Whistle Index).
    *   `/vet_fade` - Identify tired veterans.

## 📰 News Brief (`news_brief.py`)
*Scientist Job: Track interest shifts + create consistent brief quality.*

*   **Log:** Topics consumed, categories requested, engagement signals.
*   **Store:**
    *   **LTM:** Preferred categories, brief style.
    *   **WM:** Current obsessions (e.g., "AI tools week").
    *   **EV:** Article URLs, raw summaries.
*   **Compare Against:** Learning goals & projects.
*   **Context Capsule:** Preferred topics/tone, avoid list.
*   **Tweak:** **Bias Check** - Rotate sources, flag uncertainty.

## 🏙️ MSP Scout (`msp_scout.py`)
*Scientist Job: Recommend events fitting patterns + constraints.*

*   **Log:** Event categories, times, generalized distances, RSVP signals.
*   **Store:**
    *   **LTM:** Preferred event types (tech, art).
    *   **WM:** "Going-out energy", weekend availability.
    *   **EV:** Exact venue address.
*   **Compare Against:** Transport constraints (no car), budget caps.
*   **Context Capsule:** Travel constraints, vibe, budget, "social battery".
*   **Tweak:** **Friction Scoring** - Rank by ease (distance/cost/weather).

## 🎬 Cinema Companion (`cinema_companion.py`)
*Scientist Job: Build "taste model" and detect trend shifts.*

*   **Log:** Watch/search events, genre vector, mood tags, ratings.
*   **Store:**
    *   **LTM:** Stable taste anchors, dislikes.
    *   **WM:** Recent drift ("action ↑", "comedies ↓"), time-of-day habits.
    *   **EV:** Exact watch history list.
*   **Compare Against:** Recent mood/energy patterns.
*   **Context Capsule:** Top 3 WM genres, hard dislikes, format prefs.
*   **Tweak:** **Three-Lane Recs** - 1. Safe, 2. Adjacent Novelty, 3. Curveball.

## 🏥 Health Sync (`health_sync.py`)
*Scientist Job: Detect correlations carefully (Sleep ↔ Spend ↔ Work).*

*   **Log:** Sleep duration/quality, activity, routines (time buckets).
*   **Store:**
    *   **LTM:** Stable health routines.
    *   **WM:** Week-to-week changes, recovery/debt trend.
    *   **EV:** Raw wearable data, sensitive notes.
*   **Compare Against:** Finance impulse windows, late-night media spikes.
*   **Context Capsule:** Consent boundaries, what metrics matter.
*   **Tweak:** **Separate Vault Policy** - Health data never informs non-health agents without explicit allow.

## 🐱 Vet Manager (`vet_manager.py`)
*Scientist Job: Keep pet care consistent + forecast costs.*

*   **Log:** Food changes, visits, meds, symptoms, expenses.
*   **Store:**
    *   **LTM:** Pet profiles, stable diet, vet contacts.
    *   **WM:** Recent changes (new food).
    *   **EV:** Vet records, invoices, medical details.
*   **Compare Against:** Pet budget, calendar.
*   **Context Capsule:** Brand prefs, schedule, budget.
*   **Tweak:** **Inventory Forecasting** - Estimate run-out dates.

## 🏥 Medic (`medic.py`)
*Scientist Job: System telemetry only.*

*   **Log:** Uptime, CPU, errors.
*   **Store:**
    *   **LTM:** Known recurring issues.
    *   **WM:** Instability trends.
    *   **EV:** Raw logs.
*   **Compare Against:** Agent failures.
*   **Context Capsule:** Technical constraints only (NO personal data).
*   **Tweak:** **Blame Assignment** - Tag failures as Data, Model, or System.

## 🔴 Protocol Omega (`protocol_omega.py`)
*Dead Man's Switch - Isolated*

*   **Rule:** **Walled Off**. No enrichment from personal data.
*   **Store:**
    *   **LTM:** Emergency contact policy.
    *   **EV:** Triggers, sensitive instructions (Locked).
*   **Context Capsule:** None.
*   **Tweak:** **Two-Key Confirmation** for irreversible actions.

## 🏭 Agent Factory (`agent_factory.py`)
*GOD MODE - Standard Enforcer*

*   **Scientist Job:** Enforce standards so new agents don't poison memory.
*   **Requirements:** Must implement output contract, declare memory R/W, support capsules.
*   **Tweak:** **Agent Sandbox** - New agents start read-only.

---

## 🧪 Weekly Lab Routine (Automated)

1.  **Ingest:** Agent outputs → Normalize to Events.
2.  **Update Trends:** Refresh Working Memory (30-90d).
3.  **Drift Detection:** Check taste, spend, routine drifts.
4.  **Generate Artifacts:**
    *   *Trend Report*
    *   *Hypothesis List* (Confidence Scored)
    *   *Adaptation Plan*
5.  **Memory Arbitration:** Add/Update/Expire LTM/WM items.
6.  **Audit:** Review sensitive data access and capsule leakage.

---

## � Access Control Policy

**Athena operates on strict permission levels to prevent chaos.**

### Levels
*   **Level 0 (Observe)**: Read summaries only. No writes.
*   **Level 1 (Propose)**: Read LTM/WM. Can propose memory updates. No actions.
*   **Level 2 (Gatekeeper)**: Read + Limited Vault. Can issuing **APPROVE/WARN/BLOCK** decisions.
*   **Level 3 (Execute)**: Read All (Need-to-Know). Can write to services/Notion. **Actions Gated** by Hub/User.
*   **Level 4 (Admin)**: Athena Hub Only. Commits memory, sets policy.

### Global Rules
1.  **Hub-Only Commit**: Agents only *propose* memory updates. Only Athena commits them.
2.  **No Direct Calls**: Agents never call agents. They utilize the Hub.
3.  **The Gate**: Money/Booking/Irreversible actions require **User Confirmation**.
4.  **Protocol Omega**: Is isolated. No data in, no data out.

### Autonomy Protocols
**Athena enforces three modes of autonomy:**

1.  **Always-on Sensors (Mode: Sensor)**
    *   **Role**: Read inputs, create events. **Append-Only**.
    *   **Agents**: Transaction Hunter, Medic, Notion (Filing).
    *   **Rule**: Never edit totals or curated dashboards.

2.  **Scheduled Analysts (Mode: Analyst)**
    *   **Role**: Daily/Weekly summaries and trend detection.
    *   **Agents**: Financial Advisor, Deal Sniper (Throttled), News, Health.
    *   **Rule**: Reactive + Periodic. No constant noise.

3.  **On-Demand Executors (Mode: Executor)**
    *   **Role**: High-impact actions (Spend, Book, Edit).
    *   **Agents**: Agent Factory, Omega, Notion (Dashboards).
    *   **Rule**: **GATED**. Requires Athena + User Confirmation.

