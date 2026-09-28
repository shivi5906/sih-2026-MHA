from __future__ import annotations

from abc import ABC, abstractmethod

from vaultx.models.transaction import NormalizedTransaction, Chain
from vaultx.models.address import AddressInfo
from vaultx.providers.base import DataProvider


class ChainAdapter(ABC):
    """Abstract interface for blockchain-specific adapters.
    
    Each adapter knows how to:
    1. Call its chain's API via the DataProvider
    2. Parse the chain-specific response format
    3. Normalize transactions into NormalizedTransaction
    """
    def __init__(self, provider: DataProvider) -> None:
        self.provider = provider
    
    @property
    @abstractmethod
    def chain(self) -> Chain:
        """Returns the chain enum value for this adapter."""
        pass
    
    @abstractmethod
    async def get_transactions(self, address: str) -> list[NormalizedTransaction]:
        """Fetches and normalizes transactions for a given address."""
        pass
    
    @abstractmethod
    async def get_address_info(self, address: str) -> AddressInfo:
        """Fetches or computes address-level statistics."""
        pass
