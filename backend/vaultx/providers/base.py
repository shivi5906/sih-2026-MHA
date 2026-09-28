from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

class DataProvider(ABC):
    """Abstract interface for fetching raw API responses.
    
    Sits between chain adapters and the network. In fixture mode, reads
    from local JSON files. In live mode, hits actual blockchain APIs.
    This abstraction lets the entire tracing engine work identically
    regardless of data source.
    """
    
    @abstractmethod
    async def fetch(self, chain: str, endpoint: str, params: dict[str, Any] | None = None,
                    headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Fetch a raw API response."""
        ...
    
    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...
        
    async def __aenter__(self) -> DataProvider:
        return self
        
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
