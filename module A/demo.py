"""
VAULT-X Demo — Trace a suspicious wallet to an exchange.

Run this script to see the tracing engine in action on fixture data.
No API keys needed.

Usage:
    python demo.py
"""
import asyncio
import os
import sys
from decimal import Decimal

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(__file__))

from vaultx.config import Config, VaultxMode
from vaultx.models.transaction import Chain
from vaultx.models.trace import TraceConfig, StopReason
from vaultx.providers.fixture import FixtureProvider
from vaultx.chains.ethereum import EthereumAdapter
from vaultx.chains.bitcoin import BitcoinAdapter
from vaultx.chains.detection import detect_chain
from vaultx.exchanges.known import is_exchange
from vaultx.tracing.engine import TracingEngine


def print_header(text: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def exchanges_from_leaves(result):
    """Derive exchange dict from trace leaves (backward-compat helper)."""
    exchanges = {}
    for leaf in result.leaves:
        if leaf.reason == StopReason.LABELED and leaf.label:
            if leaf.label not in exchanges:
                exchanges[leaf.label] = []
            if leaf.arriving_hop:
                exchanges[leaf.label].append(leaf.arriving_hop)
    return exchanges


async def demo_ethereum_trace():
    """Trace a suspicious Ethereum wallet through to Binance."""
    print_header("ETHEREUM TRACE: Suspect → Binance")
    
    # Set up fixture-based config
    config = Config.__new__(Config)
    config.mode = VaultxMode.FIXTURE
    config.fixture_dir = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
    config.chains = {}
    
    provider = FixtureProvider(config)
    eth_adapter = EthereumAdapter(provider=provider)
    
    engine = TracingEngine(
        adapters={Chain.ETHEREUM: eth_adapter},
        config=TraceConfig(max_hops=10, min_taint_fraction=Decimal("0.001")),
        label_fn=is_exchange,
    )
    
    suspect = "0xaaa1111111111111111111111111111111111111"
    print(f"🔍 Starting trace from: {suspect}")
    print(f"   Chain: Ethereum")
    print()
    
    result = await engine.trace(suspect, chain=Chain.ETHEREUM)
    
    # Print each hop
    print("📡 Trace hops:")
    for hop in result.hops:
        taint_pct = hop.taint_fraction * 100
        print(f"   Hop {hop.hop_number}: {hop.from_address[:12]}... → {hop.to_address[:12]}...")
        print(f"          Value: {hop.value_native} ETH | Taint: {taint_pct:.1f}% ({hop.taint_amount:.4f} ETH)")
    
    # Print results
    print()
    exchanges_found = exchanges_from_leaves(result)
    if exchanges_found:
        print("🏦 EXCHANGES FOUND:")
        for name, hops in exchanges_found.items():
            for hop in hops:
                print(f"   ✅ {name} reached at {hop.to_address}")
                print(f"      via {hop.from_address[:12]}...")
                print(f"      Tainted amount arriving: {hop.taint_amount:.4f} ETH ({hop.taint_fraction*100:.1f}%)")
    else:
        print("❌ No exchanges found in trace.")
    
    # Print leaves (trace boundaries)
    print(f"\n🍃 Trace boundaries ({len(result.leaves)} leaves):")
    for leaf in result.leaves:
        label = f" [{leaf.label}]" if leaf.label else ""
        print(f"   {leaf.reason.name}: {leaf.address[:16]}...{label}")
    
    print(f"\n📊 Summary:")
    print(f"   Total hops traced: {result.total_hops}")
    print(f"   Duration: {result.duration_seconds:.3f}s")
    print(f"   Termination: {result.terminated_reason}")


async def demo_bitcoin_trace():
    """Trace a suspicious Bitcoin wallet through UTXO transactions."""
    print_header("BITCOIN TRACE: Suspect → Binance")
    
    config = Config.__new__(Config)
    config.mode = VaultxMode.FIXTURE
    config.fixture_dir = os.path.join(os.path.dirname(__file__), "tests", "fixtures")
    config.chains = {}
    
    provider = FixtureProvider(config)
    btc_adapter = BitcoinAdapter(provider=provider)
    
    engine = TracingEngine(
        adapters={Chain.BITCOIN: btc_adapter},
        config=TraceConfig(max_hops=10, min_taint_fraction=Decimal("0.001")),
        label_fn=is_exchange,
    )
    
    suspect = "bc1qsuspect11111111111111111111111111111"
    print(f"🔍 Starting trace from: {suspect}")
    print(f"   Chain: Bitcoin (UTXO model)")
    print()
    
    result = await engine.trace(suspect, chain=Chain.BITCOIN)
    
    print("📡 Trace hops:")
    for hop in result.hops:
        taint_pct = hop.taint_fraction * 100
        print(f"   Hop {hop.hop_number}: {hop.from_address[:16]}... → {hop.to_address[:16]}...")
        print(f"          Value: {hop.value_native} BTC | Taint: {taint_pct:.1f}%")
    
    print()
    exchanges_found = exchanges_from_leaves(result)
    if exchanges_found:
        print("🏦 EXCHANGES FOUND:")
        for name, hops in exchanges_found.items():
            for hop in hops:
                print(f"   ✅ {name} reached at {hop.to_address}")
                print(f"      Tainted BTC arriving: {hop.taint_amount} BTC")
    else:
        print("❌ No exchanges found in trace.")
    
    print(f"\n📊 Summary: {result.total_hops} hops, {result.duration_seconds:.3f}s, {result.terminated_reason}")


async def demo_chain_detection():
    """Show automatic chain detection from address format."""
    print_header("CHAIN DETECTION")
    
    test_addresses = [
        "0x28C6c06298d514Db089934071355E5743bf21d60",
        "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo",
        "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h",
        "TDqSquXBgUCLYvYC4XAofeEsNtJBBPMNkV",
        "not_a_real_address",
    ]
    
    for addr in test_addresses:
        chain = detect_chain(addr)
        chain_name = chain.name if chain else "UNKNOWN"
        icon = {"ETHEREUM": "⟠", "BITCOIN": "₿", "TRON": "◈"}.get(chain_name, "❓")
        print(f"   {icon} {addr[:42]:42s} → {chain_name}")


async def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║              VAULT-X  Chain & Trace Demo                ║")
    print("║         Blockchain Transaction Forensics Engine         ║")
    print("╚══════════════════════════════════════════════════════════╝")
    
    await demo_chain_detection()
    await demo_ethereum_trace()
    await demo_bitcoin_trace()
    
    print_header("DONE")
    print("   All traces completed using fixture data (no API keys needed).")
    print("   To trace real addresses, set VAULTX_MODE=live in .env")
    print("   and add your API keys.\n")


if __name__ == "__main__":
    asyncio.run(main())
