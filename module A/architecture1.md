# VAULT-X — Chain & Trace Engine

Blockchain transaction tracing engine for cryptocurrency forensics. Given a suspicious wallet address, traces funds forward hop-by-hop across **Ethereum**, **Bitcoin**, and **Tron** until they reach a known crypto exchange — where KYC records can identify the wallet owner.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  TracingEngine (BFS)                 │
│  TaintTracker (proportional) + TraceGraph (NetworkX) │
├─────────────────────────────────────────────────────┤
│     EthereumAdapter  │  BitcoinAdapter  │ TronAdapter│
│     (Etherscan V2)   │  (Blockstream)   │ (TronGrid) │
├─────────────────────────────────────────────────────┤
│          DataProvider (fixture / live / caching)     │
└─────────────────────────────────────────────────────┘
```

### Key Design Decisions

- **Proportional taint analysis**: When a wallet mixes clean and traced funds, taint is distributed proportionally (industry standard used by Chainalysis/Elliptic). See `vaultx/tracing/taint.py` for detailed rationale.
- **UTXO decomposition**: Bitcoin transactions with N inputs × M outputs are decomposed into individual from→to pairs with proportionally allocated values. See `vaultx/chains/bitcoin.py`.
- **Fixture-first**: The entire system works end-to-end without API keys using synthetic fixture data. Live mode is a config change, not a code change.

## Quick Start

```bash
# Install dependencies
pip install aiohttp networkx python-dotenv pytest pytest-asyncio

# Run all tests (fixture mode, no API keys needed)
python -m pytest tests/ -v

# Run a trace (Python)
import asyncio
from decimal import Decimal
from vaultx.config import Config
from vaultx.models.transaction import Chain
from vaultx.models.trace import TraceConfig
from vaultx.providers.fixture import FixtureProvider
from vaultx.chains.ethereum import EthereumAdapter
from vaultx.tracing.engine import TracingEngine

async def main():
    config = Config()
    provider = FixtureProvider(config)
    eth_adapter = EthereumAdapter(provider=provider)
    
    engine = TracingEngine(
        adapters={Chain.ETHEREUM: eth_adapter},
        config=TraceConfig(max_hops=10)
    )
    
    result = await engine.trace(
        '0xaaa1111111111111111111111111111111111111',
        chain=Chain.ETHEREUM
    )
    
    print(f"Exchanges found: {list(result.exchanges_found.keys())}")
    print(f"Total hops: {result.total_hops}")
    print(f"Terminated: {result.terminated_reason}")
    
    for name, hops in result.exchanges_found.items():
        for hop in hops:
            print(f"  → {name} via {hop.from_address[:10]}... "
                  f"(taint: {hop.taint_fraction:.1%}, value: {hop.value_native} ETH)")

asyncio.run(main())
```

## Configuration

Copy `.env.example` to `.env` and fill in:

```bash
# Mode: fixture (default), live, record
VAULTX_MODE=fixture

# API keys (only needed in live/record mode)
ETHERSCAN_API_KEY=your_key_here
TRONGRID_API_KEY=your_key_here

# Fixture data directory
VAULTX_FIXTURE_DIR=tests/fixtures
```

### Switching to Live Mode

1. Sign up for API keys at [Etherscan](https://etherscan.io/apis) and [TronGrid](https://www.trongrid.io/)
2. Set keys in `.env`
3. Set `VAULTX_MODE=live` (or `record` to cache responses)
4. That's it — no code changes needed

## Project Structure

```
vault-x/
├── vaultx/
│   ├── config.py              # Central configuration (env vars, modes)
│   ├── models/
│   │   ├── transaction.py     # NormalizedTransaction, Chain, TxType
│   │   ├── address.py         # AddressInfo
│   │   └── trace.py           # TraceConfig, TraceHop, TraceResult
│   ├── chains/
│   │   ├── base.py            # Abstract ChainAdapter
│   │   ├── detection.py       # Address → chain detection (regex)
│   │   ├── ethereum.py        # Etherscan V2 adapter
│   │   ├── bitcoin.py         # Blockstream Esplora adapter
│   │   └── tron.py            # TronGrid adapter
│   ├── providers/
│   │   ├── base.py            # Abstract DataProvider
│   │   ├── live.py            # Rate-limited HTTP client
│   │   ├── fixture.py         # Fixture/replay provider
│   │   └── caching.py         # Record-replay caching
│   ├── tracing/
│   │   ├── engine.py          # BFS forward tracer
│   │   ├── taint.py           # Proportional taint tracker
│   │   └── graph.py           # NetworkX graph + queries
│   └── exchanges/
│       └── known.py           # Known exchange address registry
├── tests/
│   ├── fixtures/              # Synthetic API responses
│   ├── test_detection.py      # Chain detection tests
│   ├── test_normalization.py  # Per-chain parsing tests
│   ├── test_taint.py          # Taint math tests
│   ├── test_graph.py          # Graph query tests
│   └── test_tracing.py        # End-to-end tracing tests
├── pyproject.toml
└── .env.example
```

## Tracing Algorithm

The engine uses BFS (breadth-first search) with proportional taint propagation:

1. Start with suspect address (taint = 100%)
2. Fetch outgoing transactions
3. For each outgoing tx, calculate taint carried forward:
   - `taint_fraction = tainted_received / total_received`
   - `taint_carried = tx_value × taint_fraction`
4. If recipient is a known exchange → record as terminal (exchange found!)
5. Otherwise, enqueue recipient for further tracing
6. Stop conditions: max hops, timeout, taint below threshold

## Supported Chains

| Chain | API | Auth | Rate Limit |
|-------|-----|------|------------|
| Ethereum | Etherscan V2 | API key (query param) | 5 req/s |
| Bitcoin | Blockstream Esplora | None | ~50 req/s |
| Tron | TronGrid | API key (header) | 15 req/s |

## License

Hackathon project — VAULT-X Track A (Chain & Trace)
