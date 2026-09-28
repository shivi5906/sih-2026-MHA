from __future__ import annotations
import os
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Dict, Optional

from dotenv import load_dotenv

class VaultxMode(Enum):
    """Execution mode for VAULT-X."""
    FIXTURE = "fixture"
    LIVE = "live"
    RECORD = "record"

@dataclass
class ChainConfig:
    """Configuration for a specific blockchain provider."""
    api_base_url: str
    api_key: Optional[str] = None
    rate_limit_qps: int = 5
    extra_headers: Dict[str, str] = field(default_factory=dict)

@dataclass
class TraceDefaults:
    """Default settings for tracing."""
    max_hops: int = 10
    max_duration_seconds: int = 300
    min_taint_fraction: Decimal = Decimal('0.001')
    min_value_wei: int = 1000

class Config:
    """Central configuration class."""
    def __init__(self) -> None:
        load_dotenv()
        
        mode_str = os.getenv("VAULTX_MODE", "fixture").lower()
        try:
            self.mode = VaultxMode(mode_str)
        except ValueError:
            self.mode = VaultxMode.FIXTURE
            
        self.fixture_dir = os.getenv("VAULTX_FIXTURE_DIR", "tests/fixtures")
        
        self.trace_defaults = TraceDefaults()
        
        self.chains: Dict[str, ChainConfig] = {
            "ethereum": ChainConfig(
                api_base_url="https://api.etherscan.io/v2/api?chainid=1",
                api_key=os.getenv("ETHERSCAN_API_KEY"),
                rate_limit_qps=3,
            ),
            "bitcoin": ChainConfig(
                api_base_url="https://blockstream.info/api",
                api_key=None,
                rate_limit_qps=3,
            ),
            "tron": ChainConfig(
                api_base_url="https://api.trongrid.io",
                api_key=os.getenv("TRONGRID_API_KEY"),
                rate_limit_qps=15,
                extra_headers={"TRON-PRO-API-KEY": os.getenv("TRONGRID_API_KEY", "")} if os.getenv("TRONGRID_API_KEY") else {}
            )
        }

_config_instance: Optional[Config] = None

def get_config() -> Config:
    """Return a singleton configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
