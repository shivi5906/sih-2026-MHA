from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .transaction import Chain

@dataclass
class AddressInfo:
    """Aggregated information about an address."""
    address: str
    chain: Chain
    total_received: Decimal
    total_sent: Decimal
    tx_count: int
    first_seen: Optional[int] = None
    last_seen: Optional[int] = None
