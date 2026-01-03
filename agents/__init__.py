"""
Athena Agents Package
=====================
Central registry for all Athena agents.
Each agent now has its own subfolder for modular development.

Import agents like:
    from agents import LocalDataAnalyzer, run_local_data_analysis
    from agents import run_ingestion
    from agents.nba import NBAProjectionEngine
"""

# Backward-compatible imports for existing code
# These re-export from the new subfolder structure

# DNA Ingest
try:
    from agents.dna_ingest.agent import run_ingestion
except ImportError:
    run_ingestion = None

# Local Data Analyzer
try:
    from agents.local_data_analyzer.agent import LocalDataAnalyzer, run_local_data_analysis
except ImportError:
    LocalDataAnalyzer = None
    run_local_data_analysis = None

# NBA/Parlay
try:
    from agents.nba.logic import NBAProjectionEngine
    from agents.nba.context import EnhancedContext
    from agents.nba.suggestion_engine import SuggestionEngine
except ImportError:
    NBAProjectionEngine = None
    EnhancedContext = None
    SuggestionEngine = None

try:
    from agents.parlay.agent import ParlayAnalyzer
except ImportError:
    ParlayAnalyzer = None

# Media
try:
    from agents.cinema_companion.agent import CinemaCompanion
except ImportError:
    CinemaCompanion = None

try:
    from agents.dj_booth.agent import DJBooth
except ImportError:
    DJBooth = None

try:
    from agents.news_brief.agent import NewsBrief
except ImportError:
    NewsBrief = None

# Utilities
try:
    from agents.archive_search.agent import ArchiveSearchAgent
except ImportError:
    ArchiveSearchAgent = None

try:
    from agents.web_surfer.agent import WebSurfer
except ImportError:
    WebSurfer = None

# Health & Life
try:
    from agents.health_sync.agent import HealthSync
except ImportError:
    HealthSync = None

try:
    from agents.medic.agent import MedicAgent
except ImportError:
    MedicAgent = None

try:
    from agents.vet_manager.agent import VetManager
except ImportError:
    VetManager = None

try:
    from agents.life_ops.agent import LifeOps
except ImportError:
    LifeOps = None

# Finance
try:
    from agents.deal_sniper.agent import DealSniper
except ImportError:
    DealSniper = None

try:
    from agents.transaction_hunter.agent import TransactionHunter
except ImportError:
    TransactionHunter = None

try:
    from agents.msp_scout.agent import MSPScout
except ImportError:
    MSPScout = None

# Productivity
try:
    from agents.notion.agent import NotionAgent
except ImportError:
    NotionAgent = None

try:
    from agents.drive_harvester.agent import DriveHarvester
except ImportError:
    DriveHarvester = None

try:
    from agents.travel_agent.agent import TravelAgent
except ImportError:
    TravelAgent = None

# Safety
try:
    from agents.impulse_shield.agent import ImpulseShield
except ImportError:
    ImpulseShield = None

try:
    from agents.protocol_omega.agent import ProtocolOmega
except ImportError:
    ProtocolOmega = None

# Factory
try:
    from agents.agent_factory import AgentFactory, get_agent
except ImportError:
    AgentFactory = None
    get_agent = None

__all__ = [
    # Core
    "run_ingestion",
    "LocalDataAnalyzer", 
    "run_local_data_analysis",
    
    # NBA
    "NBAProjectionEngine",
    "EnhancedContext", 
    "SuggestionEngine",
    "ParlayAnalyzer",
    
    # Media
    "CinemaCompanion",
    "DJBooth",
    "NewsBrief",
    
    # Utilities
    "ArchiveSearchAgent",
    "WebSurfer",
    
    # Health
    "HealthSync",
    "MedicAgent",
    "VetManager",
    "LifeOps",
    
    # Finance
    "DealSniper",
    "TransactionHunter",
    "MSPScout",
    
    # Productivity
    "NotionAgent",
    "DriveHarvester",
    "TravelAgent",
    
    # Safety
    "ImpulseShield",
    "ProtocolOmega",
    
    # Factory
    "AgentFactory",
    "get_agent",
]
