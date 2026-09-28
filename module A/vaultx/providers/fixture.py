from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

from vaultx.config import Config
from vaultx.providers.base import DataProvider

logger = logging.getLogger(__name__)

class FixtureProvider(DataProvider):
    """Fixture/replay provider that reads from local JSON files."""
    
    def __init__(self, config: Config) -> None:
        self.config = config
        # Config.fixture_dir is the attribute name set by the Config class
        self.fixtures_dir = Path(config.fixture_dir)
        
    def _extract_address_action(self, chain: str, endpoint: str, params: dict[str, Any] | None) -> tuple[str, str]:
        """Extract the target address and action based on the chain's conventions."""
        params = params or {}
        address = "unknown"
        action = "default"
        
        chain_lower = chain.lower()
        if chain_lower == 'ethereum':
            address = params.get('address', 'unknown')
            action = params.get('action', 'unknown')
        elif chain_lower == 'bitcoin':
            # e.g., /address/bc1q.../txs
            parts = endpoint.strip('/').split('/')
            if len(parts) >= 2 and parts[0] == 'address':
                address = parts[1]
            if len(parts) >= 3:
                action = parts[2]
            else:
                action = 'txs'
        elif chain_lower == 'tron':
            # e.g., /v1/accounts/TABC.../transactions
            # or    /v1/accounts/TABC.../transactions/trc20
            parts = endpoint.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'v1' and parts[1] == 'accounts':
                address = parts[2]
            if len(parts) >= 5:
                # e.g. transactions/trc20 → "transactions_trc20"
                action = '_'.join(parts[3:])
            elif len(parts) >= 4:
                action = parts[3]
            else:
                action = 'transactions'
                
        return address, action

    def _get_fixture_path(self, chain: str, address: str, action: str) -> Path:
        """Generate the file path for the fixture."""
        return self.fixtures_dir / chain.lower() / f"{address}_{action}.json"

    async def fetch(self, chain: str, endpoint: str, params: dict[str, Any] | None = None,
                    headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Fetch data from the local fixture JSON file."""
        address, action = self._extract_address_action(chain, endpoint, params)
        file_path = self._get_fixture_path(chain, address, action)
        
        logger.debug(f"Fixture provider reading from: {file_path}")
        
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture missing for chain '{chain}', address '{address}', action '{action}' at {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    async def close(self) -> None:
        """Clean up resources. Not needed for fixtures."""
        pass
        
    def list_available_fixtures(self) -> list[str]:
        """List all available fixture files."""
        if not self.fixtures_dir.exists():
            return []
        return [str(p.relative_to(self.fixtures_dir)) for p in self.fixtures_dir.rglob("*.json")]
