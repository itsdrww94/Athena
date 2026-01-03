#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║             A N A L Y S I S   E N G I N E S   P A C K A G E                   ║
║                    "The Deep Mind"                                             ║
║                                                                               ║
║  Four engines for comprehensive behavioral data science                       ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Engines:
1. Chronobiologist - Time patterns, sleep, peak focus
2. Sociologist - Relationships, sentiment, communication
3. BehavioralEconomist - Spending patterns, triggers
4. Correlator - Cross-dataset intelligence

Usage:
    from analysis_engines import DeepMind
    
    dm = DeepMind(data_dir="~/athena_data/me")
    profile = dm.run_deep_analysis()
"""

from .utils import normalize_timestamp, clean_pii, load_json_stream
from .chronobiologist import Chronobiologist
from .sociologist import Sociologist
from .economist import BehavioralEconomist
from .correlator import Correlator
from .deep_mind import DeepMind

__all__ = [
    'normalize_timestamp',
    'clean_pii', 
    'load_json_stream',
    'Chronobiologist',
    'Sociologist',
    'BehavioralEconomist',
    'Correlator',
    'DeepMind'
]
