"""
HAKARI CONFIGURATION
--------------------
Central configuration for decision thresholds, safety guardrails, and agent settings.
"""

# Risk Profiles
RISK_PROFILES = {
    "conservative": {
        "min_edge": 0.08,
        "min_confidence": 0.55,
        "max_risk_tags": 0,
        "sigma_floor": 0.8
    },
    "balanced": {
        "min_edge": 0.06,
        "min_confidence": 0.45,
        "max_risk_tags": 1,
        "sigma_floor": 0.75
    },
    "aggressive": {
        "min_edge": 0.04,
        "min_confidence": 0.35,
        "max_risk_tags": 2,
        "sigma_floor": 0.7
    }
}

# Autonomous Mode Constraints
AUTONOMOUS_CONSTRAINTS = {
    "stake_min": 1.0,
    "stake_max": 5.0,
    "max_team_players": 3,
    "legs_range": (3, 6),
    "require_approval_changes_count": 2,
    "require_approval_severity_score": 0.7,
    "min_parsing_confidence": 0.85
}

# Safety Gates & Throttling
SAFETY_GATES = {
    "max_slips_per_day": 5,
    "cooldown_after_loss_hours": 4,
    "drawdown_pause_threshold": 0.15, # 15% drawdown triggers pause
    "random_delay_range": (2.0, 8.0)  # Seconds
}

# Reinforcement Learning Settings
RL_SETTINGS = {
    "min_samples_for_update": 20,
    "max_update_delta": 0.01,
    "target_win_rate": 0.56
}

# Disagreement Detector
DISAGREEMENT_THRESHOLDS = {
    "probability_diff_trigger": 0.12, # Delta between projection and motif prob
    "confidence_penalty": 0.15,
    "skip_borderline": True
}
