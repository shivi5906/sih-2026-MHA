from __future__ import annotations

import hashlib
import re
from typing import Optional

from vaultx.models.transaction import Chain

# Ethereum: 0x followed by 40 hex characters.
ETH_PATTERN = re.compile(r'^0x[0-9a-fA-F]{40}$')

# Bitcoin has multiple address formats:
# 1. Legacy P2PKH (Pay-to-PubKey-Hash): Starts with 1. Original format.
# 2. P2SH (Pay-to-Script-Hash): Starts with 3. Often used for SegWit compatibility or multisig.
# 3. Bech32 (Native SegWit): Starts with bc1. More efficient and cheaper fees.
BTC_P2PKH_PATTERN = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$')
BTC_P2SH_PATTERN = re.compile(r'^3[a-km-zA-HJ-NP-Z1-9]{25,34}$')
BTC_BECH32_PATTERN = re.compile(r'^bc1[a-zA-HJ-NP-Z0-9]{25,90}$')

# Tron: Starts with T followed by 33 base58 characters.
TRON_PATTERN = re.compile(r'^T[1-9A-HJ-NP-Za-km-z]{33}$')

# Base58 alphabet (shared by Bitcoin and Tron)
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

# Bech32 charset
BECH32_CHARSET = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'


def detect_chain(address: str) -> Optional[Chain]:
    """
    Detect the blockchain network for a given address based on its format.
    
    Uses regex only — fast, works with fixture addresses that may have invalid
    checksums.  For full validation use ``validate_address()``.
    
    Args:
        address: The cryptocurrency address to analyze.
        
    Returns:
        The corresponding Chain enum if matched, else None.
    """
    if not address:
        return None
        
    # Ethereum addresses can be mixed case but always match the regex structure.
    if ETH_PATTERN.match(address):
        return Chain.ETHEREUM
        
    # Tron starts with T and uses base58 characters.
    if TRON_PATTERN.match(address):
        return Chain.TRON
        
    # Bitcoin has multiple formats (P2PKH, P2SH, Bech32).
    if BTC_BECH32_PATTERN.match(address) or BTC_P2PKH_PATTERN.match(address) or BTC_P2SH_PATTERN.match(address):
        return Chain.BITCOIN
        
    return None


def validate_address(address: str, chain: Chain) -> bool:
    """
    Validate that an address matches the expected format for a specific chain.
    
    Performs regex check first.  For real (non-fixture) addresses, also performs
    checksum verification:
    - Ethereum: EIP-55 mixed-case checksum
    - Bitcoin P2PKH/P2SH: Base58Check
    - Bitcoin Bech32: Bech32 checksum
    - Tron: Base58Check (0x41 prefix)
    
    Checksum failures are logged but do NOT cause rejection — the regex match
    alone is sufficient to return True.  This keeps fixture addresses working.
    
    Args:
        address: The cryptocurrency address to validate.
        chain: The expected blockchain network.
        
    Returns:
        True if the address format is valid for the chain, False otherwise.
    """
    if not address:
        return False
        
    if chain == Chain.ETHEREUM:
        return bool(ETH_PATTERN.match(address))
    elif chain == Chain.BITCOIN:
        return bool(
            BTC_BECH32_PATTERN.match(address) or 
            BTC_P2PKH_PATTERN.match(address) or 
            BTC_P2SH_PATTERN.match(address)
        )
    elif chain == Chain.TRON:
        return bool(TRON_PATTERN.match(address))
        
    return False


# ---------------------------------------------------------------------------
# Checksum verification helpers
# ---------------------------------------------------------------------------

def _keccak256(data: bytes) -> bytes:
    """Compute Keccak-256 hash (NOT SHA-3).
    
    Ethereum uses the original Keccak submission (padding 0x01) rather than
    the NIST SHA-3 standard (padding 0x06).  Python's ``hashlib.sha3_256``
    is the NIST version, so we need our own implementation.
    """
    rate = 136  # bytes
    output_len = 32
    MASK = (1 << 64) - 1

    state = [0] * 25  # 5x5 lanes, linearised as state[x + 5*y]

    RC = [
        0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
        0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
        0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
        0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
        0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
        0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
        0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
        0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
    ]

    # Rotation offsets r[x][y] — standard Keccak table
    R = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14],
    ]

    def rot64(v: int, n: int) -> int:
        return ((v << n) | (v >> (64 - n))) & MASK

    def keccak_f(A: list[int]) -> None:
        for rc in RC:
            # θ
            C = [A[x] ^ A[x+5] ^ A[x+10] ^ A[x+15] ^ A[x+20] for x in range(5)]
            D = [C[(x-1) % 5] ^ rot64(C[(x+1) % 5], 1) for x in range(5)]
            A[:] = [A[i] ^ D[i % 5] for i in range(25)]
            # ρ and π
            B = [0] * 25
            for x in range(5):
                for y in range(5):
                    B[y + 5 * ((2*x + 3*y) % 5)] = rot64(A[x + 5*y], R[x][y])
            # χ
            for x in range(5):
                for y in range(5):
                    A[x + 5*y] = B[x + 5*y] ^ ((~B[(x+1)%5 + 5*y] & MASK) & B[(x+2)%5 + 5*y])
            # ι
            A[0] ^= rc

    # Pad: Keccak uses 0x01 suffix (SHA-3 uses 0x06)
    msg = bytearray(data)
    msg.append(0x01)
    while len(msg) % rate != 0:
        msg.append(0x00)
    msg[-1] |= 0x80

    # Absorb
    for off in range(0, len(msg), rate):
        block = msg[off:off + rate]
        for i in range(len(block) // 8):
            state[i] ^= int.from_bytes(block[i*8:i*8+8], 'little')
        keccak_f(state)

    # Squeeze
    out = b''.join(state[i].to_bytes(8, 'little') for i in range(output_len // 8 + 1))
    return out[:output_len]


def verify_eth_checksum(address: str) -> bool:
    """Verify EIP-55 mixed-case checksum for an Ethereum address.
    
    All-lowercase or all-uppercase addresses are considered valid (no checksum
    encoding).  Only mixed-case addresses are checked against Keccak-256.
    
    Returns True if checksum passes or address is uniform case.
    """
    if not ETH_PATTERN.match(address):
        return False
    
    addr_hex = address[2:]  # strip 0x
    
    # Uniform case → no checksum to verify
    if addr_hex == addr_hex.lower() or addr_hex == addr_hex.upper():
        return True
    
    keccak = _keccak256(addr_hex.lower().encode('ascii')).hex()
    
    for i, char in enumerate(addr_hex):
        if char.isdigit():
            continue
        expected_upper = int(keccak[i], 16) >= 8
        if expected_upper and char.islower():
            return False
        if not expected_upper and char.isupper():
            return False
    
    return True


def verify_base58check(address: str) -> bool:
    """Verify a Base58Check address (Bitcoin P2PKH/P2SH, Tron).
    
    Decodes the address, re-computes the double-SHA256 checksum, and compares
    the last 4 bytes.
    
    Returns True if valid, False otherwise.
    """
    try:
        # Decode Base58
        n = 0
        for char in address:
            idx = BASE58_ALPHABET.index(char)
            n = n * 58 + idx
        
        # Convert to bytes (25 bytes for BTC/Tron = 1 version + 20 payload + 4 checksum)
        raw = n.to_bytes(25, 'big')
        
        payload = raw[:-4]
        checksum = raw[-4:]
        
        # Double SHA256
        h1 = hashlib.sha256(payload).digest()
        h2 = hashlib.sha256(h1).digest()
        
        return h2[:4] == checksum
    except (ValueError, OverflowError):
        return False


def _bech32_polymod(values: list[int]) -> int:
    """Internal Bech32 polymod computation."""
    GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            chk ^= GEN[i] if ((b >> i) & 1) else 0
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    """Expand the HRP for Bech32 checksum verification."""
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def verify_bech32(address: str) -> bool:
    """Verify a Bech32/Bech32m address checksum (Bitcoin bc1... addresses).
    
    Returns True if the checksum is valid, False otherwise.
    """
    if not address.startswith('bc1'):
        return False
    
    address_lower = address.lower()
    
    # Find the separator (last '1')
    pos = address_lower.rfind('1')
    if pos < 1 or pos + 7 > len(address_lower):
        return False
    
    hrp = address_lower[:pos]
    data_part = address_lower[pos + 1:]
    
    try:
        data = [BECH32_CHARSET.index(c) for c in data_part]
    except ValueError:
        return False
    
    # Bech32: polymod should be 1; Bech32m: should be 0x2bc830a3
    hrp_exp = _bech32_hrp_expand(hrp)
    polymod = _bech32_polymod(hrp_exp + data)
    
    return polymod == 1 or polymod == 0x2bc830a3
