from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Set

from vaultx.models.transaction import Chain


@dataclass
class ExchangeInfo:
    """Information about a known cryptocurrency exchange."""
    name: str
    chain: Chain
    addresses: Set[str]
    hot_wallet: bool


# Map lowercase addresses to their ExchangeInfo
KNOWN_EXCHANGES: dict[str, ExchangeInfo] = {}


def _add_exchange(name: str, chain: Chain, addresses: list[str], hot_wallet: bool = True) -> None:
    """Helper to populate KNOWN_EXCHANGES."""
    info = ExchangeInfo(name=name, chain=chain, addresses=set(addresses), hot_wallet=hot_wallet)
    for addr in addresses:
        # We store addresses in lowercase to ensure case-insensitive lookups, 
        # which helps for Ethereum (mixed case checksum) and others.
        KNOWN_EXCHANGES[addr.lower()] = info


# Ethereum Exchanges
_add_exchange(
    "Binance",
    Chain.ETHEREUM,
    [
        "0x28C6c06298d514Db089934071355E5743bf21d60", # Binance 14
        "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549", # Binance 15
        "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d", # Binance 8
        "0x47ac0fb3F2D84898e4D9E7b4DaB3C24507a6D503", # Binance 7
        "0xbe0eb53f46cd790cd13851d5eff43d12404d33e8", # Binance 16
        "0xF977814e90dA44bFA03b6295A0616a897441aceC", # Binance 9
        "0x3f5CE5FBFe3E9af3971dD833D26ba9b5C936f0bE", # Binance 1
        "0xD551234Ae421e3BCBA99A0Da6d7360741CAFaFD5"  # Binance 2
    ]
)
_add_exchange(
    "Coinbase",
    Chain.ETHEREUM,
    [
        "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3", # Coinbase 1
        "0x503B4090cd8D5F1A5955be74170707e773133333", # Coinbase 2
        "0xA092e0a293674620f4c022301389c9A2A44f6211"  # Coinbase Hot Wallet
    ]
)
_add_exchange(
    "Kraken",
    Chain.ETHEREUM,
    [
        "0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2", # Kraken 1
        "0x0A869d79a7052C7f1b55a8ebabbea3420F0D1E13"  # Kraken 2
    ]
)
_add_exchange(
    "OKX",
    Chain.ETHEREUM,
    [
        "0x6cC5F688a315f3dC28A7781717a9A798a59fDA7b", # OKX 1
        "0x50B19D0101861783B8e72D7F05a3B6d2FDF5D22b"  # OKX 2
    ]
)

# Bitcoin Exchanges
_add_exchange(
    "Binance",
    Chain.BITCOIN,
    ["34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", "bc1qm34lsc65zpw79lxes69zkqmk6ee3ewf0j77s3h"]
)
_add_exchange(
    "Coinbase",
    Chain.BITCOIN,
    ["3KZ526NxCVXbKwwP66RgM3pte6zW4gY1tD"]
)
_add_exchange(
    "Kraken",
    Chain.BITCOIN,
    ["bc1qr4dl5wa7kl8yu792dceg9z5knl2gkn220lk7a9"]
)

# Tron Exchanges
_add_exchange(
    "Binance",
    Chain.TRON,
    ["TDqSquXBgUCLYvYC4XAofeEsNtJBBPMNkV", "TNXoiAJ3dct8Fjg4M9fkLFh9S2v9TXc32G"]
)
_add_exchange(
    "Huobi",
    Chain.TRON,
    ["THGKJwmvSAnzPVKTDFJzC3YWGL3RjS1ADj"]
)


def is_exchange(address: str) -> Optional[str]:
    """
    Check if an address belongs to a known exchange.
    
    Args:
        address: The cryptocurrency address to check.
        
    Returns:
        The name of the exchange if found, else None.
    """
    if not address:
        return None
    
    info = KNOWN_EXCHANGES.get(address.lower())
    return info.name if info else None


def get_exchange_info(address: str) -> Optional[ExchangeInfo]:
    """
    Get full exchange information for a known address.
    
    Args:
        address: The cryptocurrency address to lookup.
        
    Returns:
        ExchangeInfo object if found, else None.
    """
    if not address:
        return None
        
    return KNOWN_EXCHANGES.get(address.lower())
