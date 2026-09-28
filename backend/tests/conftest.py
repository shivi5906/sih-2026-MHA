from __future__ import annotations
import os
import pytest
from decimal import Decimal

from vaultx.config import Config, VaultxMode
from vaultx.models.trace import TraceConfig
from vaultx.models.transaction import Chain
from vaultx.providers.fixture import FixtureProvider
from vaultx.chains.ethereum import EthereumAdapter
from vaultx.chains.bitcoin import BitcoinAdapter
from vaultx.chains.tron import TronAdapter


@pytest.fixture
def config():
    """Config pointing to test fixtures directory."""
    cfg = Config.__new__(Config)
    cfg.mode = VaultxMode.FIXTURE
    cfg.fixture_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
    cfg.chains = {}
    cfg.trace_defaults = None
    return cfg


@pytest.fixture
def trace_config():
    return TraceConfig(
        max_hops=10,
        max_duration_seconds=300,
        min_taint_fraction=Decimal('0.001'),
        min_value_native=Decimal('0.0001')
    )


@pytest.fixture
def fixture_provider(config):
    return FixtureProvider(config)


@pytest.fixture
def eth_adapter(fixture_provider):
    return EthereumAdapter(provider=fixture_provider)


@pytest.fixture
def btc_adapter(fixture_provider):
    return BitcoinAdapter(provider=fixture_provider)


@pytest.fixture
def tron_adapter(fixture_provider):
    return TronAdapter(provider=fixture_provider)
