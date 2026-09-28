from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum, auto
from typing import Any, Optional

class Chain(Enum):
    """Supported blockchain networks."""
    ETHEREUM = auto()
    BITCOIN = auto()
    TRON = auto()

class TxType(Enum):
    """Types of transactions."""
    TRANSFER = auto()
    CONTRACT_CALL = auto()
    INTERNAL = auto()
    COINBASE = auto()
    TOKEN_TRANSFER = auto()

@dataclass
class NormalizedTransaction:
    """A standardized transaction representation across all chains."""
    tx_id: str
    chain: Chain
    block_number: int
    timestamp: int
    from_address: str
    to_address: str
    value_raw: int
    value_native: Decimal
    fee_raw: int
    is_error: bool
    tx_type: TxType
    raw_tx_id: str
    # Token transfer fields (None for native transfers)
    token_contract: Optional[str] = None
    token_symbol: Optional[str] = None
    token_decimals: Optional[int] = None
    # Generic metadata bag for chain-specific facts (e.g. co-spend addresses)
    metadata: Optional[dict[str, Any]] = field(default=None, repr=False)
    
    def direction(self, address: str) -> str:
        """
        Determine the direction of the transaction relative to an address.
        
        Args:
            address: The address to check against.
            
        Returns:
            'incoming', 'outgoing', or 'self'.
        """
        addr_lower = address.lower()
        from_lower = self.from_address.lower()
        to_lower = self.to_address.lower()

        if from_lower == addr_lower and to_lower == addr_lower:
            return "self"
        elif from_lower == addr_lower:
            return "outgoing"
        elif to_lower == addr_lower:
            return "incoming"
        else:
            return "unrelated"
