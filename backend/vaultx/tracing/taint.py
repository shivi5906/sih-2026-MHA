from __future__ import annotations
from decimal import Decimal

"""Proportional (haircut) taint tracking.

When a wallet holds a mix of 'clean' and 'traced' money, we need to decide
how much taint carries forward through outgoing transactions.

Three common approaches:
- FIFO: Oldest money moves first — arbitrary, gameable
- Poison: Any taint = entire balance tainted — over-attributes
- Proportional: Taint fraction = tainted_amount / total_received — fair, standard in AML

We use Proportional because:
1. It's mathematically fair — taint is distributed based on actual ratio
2. It's the industry standard (Chainalysis, Elliptic use this)
3. It's defensible in legal proceedings
4. It naturally handles merges (multiple tainted inputs) by summing taint fractions
"""

class TaintTracker:
    """Tracks the proportion of tainted funds in addresses based on proportional taint.
    
    Maintains per-address bookkeeping of total_received, tainted_amount, and
    total_spent.  Outflows deduct taint proportionally so the remaining taint
    budget decreases correctly — taint can never be created from nothing.
    """
    
    def __init__(self) -> None:
        """Initialize the TaintTracker with an empty internal store."""
        # Maps address -> {"tainted_amount": Decimal, "total_received": Decimal,
        #                   "total_spent": Decimal, "taint_spent": Decimal}
        self._data: dict[str, dict[str, Decimal]] = {}
        
    def _ensure(self, address: str) -> dict[str, Decimal]:
        """Ensure an entry exists for *address* and return it."""
        if address not in self._data:
            self._data[address] = {
                "tainted_amount": Decimal('0'),
                "total_received": Decimal('0'),
                "total_spent": Decimal('0'),
                "taint_spent": Decimal('0'),
            }
        return self._data[address]

    def record_incoming(self, address: str, amount: Decimal, taint_amount: Decimal) -> None:
        """Record an incoming transaction to an address, updating its taint profile.
        
        Args:
            address: The receiving address.
            amount: The total amount received in this transaction.
            taint_amount: The portion of the amount that is tainted.
        """
        amount = max(Decimal('0'), amount)
        taint_amount = max(Decimal('0'), min(taint_amount, amount))
        
        entry = self._ensure(address)
        entry["total_received"] += amount
        entry["tainted_amount"] += taint_amount

    def get_taint_fraction(self, address: str) -> Decimal:
        """Get the current fraction of *remaining* funds that are tainted.
        
        Accounts for outflows: remaining taint = tainted_in - taint_spent,
        remaining balance = total_received - total_spent.
        
        Returns:
            The taint fraction (0.0 to 1.0). Returns 0 if no data.
        """
        if address not in self._data:
            return Decimal('0')
        
        entry = self._data[address]
        remaining_balance = entry["total_received"] - entry["total_spent"]
        if remaining_balance <= Decimal('0'):
            return Decimal('0')
            
        remaining_taint = entry["tainted_amount"] - entry["taint_spent"]
        if remaining_taint <= Decimal('0'):
            return Decimal('0')
        
        fraction = remaining_taint / remaining_balance
        # Clamp to [0, 1] for safety
        return max(Decimal('0'), min(Decimal('1'), fraction))
        
    def calculate_outgoing_taint(self, address: str, outgoing_value: Decimal) -> tuple[Decimal, Decimal]:
        """Calculate the taint for an outgoing transaction and deduct it.
        
        The taint carried forward is ``outgoing_value × current_fraction``.
        Both total_spent and taint_spent are updated so subsequent calls
        see a reduced (but never inflated) taint budget.
        
        Args:
            address: The address sending funds.
            outgoing_value: The total value being sent.
            
        Returns:
            A tuple of (taint_amount_carried, taint_fraction).
        """
        outgoing_value = max(Decimal('0'), outgoing_value)
        fraction = self.get_taint_fraction(address)
        taint_amount_carried = outgoing_value * fraction
        
        # Deduct from the address's remaining budget
        entry = self._ensure(address)
        entry["total_spent"] += outgoing_value
        entry["taint_spent"] += taint_amount_carried
        
        # Conservation invariant: taint_spent can never exceed tainted_amount
        if entry["taint_spent"] > entry["tainted_amount"]:
            entry["taint_spent"] = entry["tainted_amount"]
        
        return taint_amount_carried, fraction
    
    def get_total_received(self, address: str) -> Decimal:
        """Get the total received amount recorded for an address.
        
        Args:
            address: The address to query.
            
        Returns:
            The total received amount, or 0 if no data.
        """
        if address not in self._data:
            return Decimal('0')
        return self._data[address]["total_received"]
    
    def get_remaining_balance(self, address: str) -> Decimal:
        """Get the remaining (unspent) balance for an address."""
        if address not in self._data:
            return Decimal('0')
        entry = self._data[address]
        return max(Decimal('0'), entry["total_received"] - entry["total_spent"])

    def get_remaining_taint(self, address: str) -> Decimal:
        """Get the remaining (unspent) taint for an address."""
        if address not in self._data:
            return Decimal('0')
        entry = self._data[address]
        return max(Decimal('0'), entry["tainted_amount"] - entry["taint_spent"])
        
    def reset(self) -> None:
        """Clear all tracking data."""
        self._data.clear()
