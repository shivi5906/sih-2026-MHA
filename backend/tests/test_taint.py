from __future__ import annotations
import pytest
from decimal import Decimal
from vaultx.tracing.taint import TaintTracker


def test_full_taint():
    """100% tainted funds: all outgoing should carry full taint."""
    tracker = TaintTracker()
    tracker.record_incoming('addr1', Decimal('100'), Decimal('100'))
    
    taint_amount, taint_fraction = tracker.calculate_outgoing_taint('addr1', Decimal('50'))
    assert taint_fraction == Decimal('1')
    assert taint_amount == Decimal('50')


def test_proportional_taint():
    """50% tainted: 10 ETH tainted + 10 ETH clean -> 50% taint on all outflows."""
    tracker = TaintTracker()
    tracker.record_incoming('addr1', Decimal('10'), Decimal('10'))  # tainted
    tracker.record_incoming('addr1', Decimal('10'), Decimal('0'))   # clean
    
    taint_amount, taint_fraction = tracker.calculate_outgoing_taint('addr1', Decimal('5'))
    assert taint_fraction == Decimal('0.5')
    assert taint_amount == Decimal('2.5')


def test_taint_through_split():
    """Taint distributes proportionally through multiple outgoing txs."""
    tracker = TaintTracker()
    tracker.record_incoming('addr1', Decimal('100'), Decimal('30'))  # 30% tainted
    
    # Each outgoing tx should carry 30% taint
    amt1, frac1 = tracker.calculate_outgoing_taint('addr1', Decimal('60'))
    assert frac1 == Decimal('0.3')
    assert amt1 == Decimal('18')  # 60 * 0.3
    
    amt2, frac2 = tracker.calculate_outgoing_taint('addr1', Decimal('40'))
    assert frac2 == Decimal('0.3')
    assert amt2 == Decimal('12')  # 40 * 0.3


def test_negligible_taint():
    """Very small taint fraction should be preserved accurately."""
    tracker = TaintTracker()
    tracker.record_incoming('addr1', Decimal('1000000'), Decimal('1'))
    
    taint_amount, taint_fraction = tracker.calculate_outgoing_taint('addr1', Decimal('500'))
    assert taint_fraction == Decimal('0.000001')
    assert taint_amount == Decimal('0.0005')


def test_zero_total_received():
    """Edge case: no recorded incoming should return 0 taint."""
    tracker = TaintTracker()
    taint_amount, taint_fraction = tracker.calculate_outgoing_taint('unknown_addr', Decimal('50'))
    assert taint_fraction == Decimal('0')
    assert taint_amount == Decimal('0')


def test_reset():
    """Reset should clear all data."""
    tracker = TaintTracker()
    tracker.record_incoming('addr1', Decimal('100'), Decimal('100'))
    tracker.reset()
    assert tracker.get_taint_fraction('addr1') == Decimal('0')
