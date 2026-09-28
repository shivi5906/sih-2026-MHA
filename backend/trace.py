"""
VAULT-X Live & Offline Wallet Tracer CLI

Run live transaction traces on real blockchain addresses or offline fixtures.

Usage:
    python trace.py <ADDRESS> [--max-hops 10] [--min-taint 0.001]
    python trace.py (interactive prompt)
"""
import sys
import os
import argparse
import asyncio
import logging
from decimal import Decimal

# Fix Windows console encoding for Unicode output
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(__file__))

from vaultx.config import get_config, VaultxMode
from vaultx.models.transaction import Chain
from vaultx.models.trace import TraceConfig, StopReason
from vaultx.chains.detection import detect_chain
from vaultx.chains.ethereum import EthereumAdapter
from vaultx.chains.bitcoin import BitcoinAdapter
from vaultx.chains.tron import TronAdapter
from vaultx.providers.fixture import FixtureProvider
from vaultx.providers.live import LiveProvider
from vaultx.exchanges.known import is_exchange
from vaultx.tracing.engine import TracingEngine


def print_header(text: str) -> None:
    print(f"\n{'='*65}")
    print(f"  {text}")
    print(f"{'='*65}\n")


async def run_trace(address: str, max_hops: int = 10, min_taint: float = 0.001):
    config = get_config()
    
    # 1. Detect chain
    chain = detect_chain(address)
    if not chain:
        print(f"❌ Error: Could not determine blockchain network for address: {address}")
        print("   Supported formats: Ethereum (0x...), Bitcoin (1..., 3..., bc1...), Tron (T...)")
        return

    chain_icon = {Chain.ETHEREUM: "⟠ Ethereum", Chain.BITCOIN: "₿ Bitcoin", Chain.TRON: "◈ Tron"}.get(chain, str(chain))
    
    # 2. Initialize Data Provider (Live vs Fixture)
    is_live = config.mode == VaultxMode.LIVE
    mode_label = "🔴 LIVE NETWORK API" if is_live else "🧪 FIXTURE MODE"
    
    print_header(f"VAULT-X TRACE | {mode_label}")
    print(f"🔍 Target Address: {address}")
    print(f"🌐 Chain:          {chain_icon}")
    print(f"⚙️  Max Hops:       {max_hops} | Min Taint: {min_taint * 100:.2f}%\n")
    
    if is_live:
        provider = LiveProvider(config)
    else:
        print("⚠️  VAULTX_MODE is not set to 'live' in .env — running on offline fixtures.")
        provider = FixtureProvider(config)
        
    adapters = {
        Chain.ETHEREUM: EthereumAdapter(provider=provider),
        Chain.BITCOIN: BitcoinAdapter(provider=provider),
        Chain.TRON: TronAdapter(provider=provider),
    }
    
    engine = TracingEngine(
        adapters=adapters,
        config=TraceConfig(max_hops=max_hops, min_taint_fraction=Decimal(str(min_taint))),
        label_fn=is_exchange,
    )
    
    try:
        print("⏳ Fetching transaction data and tracing funds forward...\n")
        
        scanned_count = 0
        def show_progress(hop_num: int, addr: str, total_txs: int, outgoing_txs: int):
            nonlocal scanned_count
            scanned_count += 1
            print(f"   [{scanned_count}] Hop {hop_num} 🔎 {addr[:14]}... ({total_txs} txs found, {outgoing_txs} outgoing)")

        result = await engine.trace(address, chain=chain, on_progress=show_progress)
        print()
        
        if result.hops:
            display_hops = result.hops[:15]
            print(f"📡 Trace Hops Found ({len(result.hops)} total, showing top {len(display_hops)}):")
            for hop in display_hops:
                taint_pct = hop.taint_fraction * 100
                print(f"   [Hop {hop.hop_number}] {hop.from_address[:16]}... ──> {hop.to_address[:16]}...")
                print(f"            Value: {hop.value_native} {chain.name} | Taint: {taint_pct:.2f}% ({hop.taint_amount:.4f} {chain.name})")
                print(f"            Tx: {hop.tx_id[:20]}...\n")
            if len(result.hops) > 15:
                print(f"   ... and {len(result.hops) - 15} more hops recorded.\n")
        else:
            print("ℹ️  No outgoing transactions found for this address matching taint criteria.")

        # Derive exchanges from leaves
        exchanges_found: dict[str, list] = {}
        for leaf in result.leaves:
            if leaf.reason == StopReason.LABELED and leaf.label and leaf.arriving_hop:
                if leaf.label not in exchanges_found:
                    exchanges_found[leaf.label] = []
                exchanges_found[leaf.label].append(leaf.arriving_hop)

        if exchanges_found:
            print("\n🏦 EXCHANGES IDENTIFIED:")
            for name, hops in exchanges_found.items():
                for hop in hops:
                    print(f"   ✅ [EXCHANGE REACHED] {name.upper()}")
                    print(f"      Address: {hop.to_address}")
                    print(f"      Hop Distance: {hop.hop_number}")
                    print(f"      Arriving Tainted Amount: {hop.taint_amount:.4f} {chain.name} ({hop.taint_fraction*100:.2f}%)")
        else:
            print("\n❌ No known exchange wallets reached within the specified max hops.")
        
        # Show trace boundaries
        incomplete = [l for l in result.leaves if l.reason == StopReason.FETCH_FAILED]
        if incomplete:
            print(f"\n⚠️  INCOMPLETE BRANCHES ({len(incomplete)}):")
            for leaf in incomplete:
                print(f"   ⚠️  {leaf.address[:20]}... — {leaf.error_detail}")
            
        print(f"\n📊 Summary:")
        print(f"   • Total Hops Evaluated: {result.total_hops}")
        print(f"   • Trace Leaves:         {len(result.leaves)}")
        print(f"   • Trace Duration:       {result.duration_seconds:.3f} seconds")
        print(f"   • Termination Reason:   {result.terminated_reason}")
        print(f"{'='*65}\n")
        
    finally:
        if is_live and hasattr(provider, 'close'):
            await provider.close()


def main():
    parser = argparse.ArgumentParser(description="VAULT-X Blockchain Transaction Tracer")
    parser.add_argument("address", nargs="?", help="Wallet address to trace (Ethereum, Bitcoin, or Tron)")
    parser.add_argument("--max-hops", type=int, default=10, help="Maximum hop depth (default: 10)")
    parser.add_argument("--min-taint", type=float, default=0.001, help="Minimum taint threshold (default: 0.001)")
    
    args = parser.parse_args()
    
    address = args.address
    if not address:
        print("\n=== VAULT-X Interactive Live Trace ===")
        print("Paste a cryptocurrency wallet address to trace:")
        print("  - Ethereum: e.g. 0x28C6c06298d514Db089934071355E5743bf21d60")
        print("  - Bitcoin:  e.g. 34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo")
        print("  - Tron:     e.g. TN3W4H6rK2ce4vX9YnFQHwKENnHjoxb3m9")
        print()
        try:
            address = input("Wallet Address > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)
            
    if not address:
        print("No address provided. Exiting.")
        sys.exit(1)
        
    asyncio.run(run_trace(address, max_hops=args.max_hops, min_taint=args.min_taint))


if __name__ == "__main__":
    main()
