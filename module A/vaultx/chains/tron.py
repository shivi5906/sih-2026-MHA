from __future__ import annotations

import hashlib
from decimal import Decimal

from vaultx.models.transaction import NormalizedTransaction, Chain, TxType
from vaultx.models.address import AddressInfo
from vaultx.chains.base import ChainAdapter


# Standard Bitcoin Base58 alphabet used by Tron
BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'

def hex_to_base58(hex_addr: str) -> str:
    """Converts a Tron hex address to its Base58Check format.
    
    Tron addresses in hex format are 21 bytes starting with 41.
    They are converted to Base58Check similarly to Bitcoin addresses.
    """
    if hex_addr.startswith("0x"):
        hex_addr = hex_addr[2:]
        
    try:
        raw_bytes = bytes.fromhex(hex_addr)
    except ValueError:
        return hex_addr
        
    # Double SHA256 for checksum
    hash1 = hashlib.sha256(raw_bytes).digest()
    hash2 = hashlib.sha256(hash1).digest()
    
    # Append first 4 bytes of hash2 as checksum
    check_bytes = raw_bytes + hash2[:4]
    
    # Convert to integer
    val = int.from_bytes(check_bytes, 'big')
    
    # Base58 encode
    encoded = ""
    while val > 0:
        val, mod = divmod(val, 58)
        encoded = BASE58_ALPHABET[mod] + encoded
        
    # Add leading '1's for zero bytes
    n_pad = 0
    for byte in check_bytes:
        if byte == 0:
            n_pad += 1
        else:
            break
            
    return ('1' * n_pad) + encoded


class TronAdapter(ChainAdapter):
    """Adapter for Tron utilizing the TronGrid API."""
    
    @property
    def chain(self) -> Chain:
        return Chain.TRON

    async def get_transactions(self, address: str) -> list[NormalizedTransaction]:
        """Fetches native TRX transfers and TRC-20 token transfers."""
        # ---- Native TRX transfers ----
        all_txs = []
        endpoint = f"/v1/accounts/{address}/transactions"
        params = {"limit": 200}
        
        while True:
            response = await self.provider.fetch('tron', endpoint, params, None)
            
            data = response.get("data", [])
            if not data:
                break
                
            all_txs.extend(data)
            
            meta = response.get("meta", {})
            fingerprint = meta.get("fingerprint")
            
            if not fingerprint:
                break
                
            params["fingerprint"] = fingerprint
            
        normalized = []
        
        def to_trx(sun: int) -> Decimal:
            return Decimal(sun) / Decimal(1_000_000)
            
        for tx in all_txs:
            raw_data = tx.get("raw_data", {})
            contracts = raw_data.get("contract", [])
            
            if not contracts:
                continue
                
            contract = contracts[0]
            # Filter for TransferContract type
            if contract.get("type") != "TransferContract":
                continue
                
            param = contract.get("parameter", {}).get("value", {})
            amount_sun = int(param.get("amount", 0))
            
            owner_hex = param.get("owner_address", "")
            to_hex = param.get("to_address", "")
            
            # Convert hex addresses to Base58Check
            from_addr = hex_to_base58(owner_hex) if owner_hex else ""
            to_addr = hex_to_base58(to_hex) if to_hex else ""
            
            # Timestamp is in milliseconds
            ts_ms = tx.get("block_timestamp", 0)
            timestamp = int(ts_ms / 1000)
            
            # Check success status
            ret = tx.get("ret", [{}])
            contract_ret = ret[0].get("contractRet", "")
            is_error = contract_ret != "SUCCESS"
            
            tx_id = tx.get("txID", "")
            
            normalized.append(
                NormalizedTransaction(
                    tx_id=tx_id,
                    chain=self.chain,
                    block_number=tx.get("blockNumber", 0),
                    timestamp=timestamp,
                    from_address=from_addr,
                    to_address=to_addr,
                    value_raw=amount_sun,
                    value_native=to_trx(amount_sun),
                    fee_raw=0,
                    is_error=is_error,
                    tx_type=TxType.TRANSFER,
                    raw_tx_id=tx_id
                )
            )
        
        # ---- TRC-20 token transfers ----
        try:
            trc20_endpoint = f"/v1/accounts/{address}/transactions/trc20"
            trc20_params = {"limit": 200}
            trc20_response = await self.provider.fetch('tron', trc20_endpoint, trc20_params, None)
            trc20_data = trc20_response.get("data", [])
        except (FileNotFoundError, Exception):
            trc20_data = []
        
        for tx in trc20_data:
            token_info = tx.get("token_info", {})
            decimals = int(token_info.get("decimals", 6))
            value_raw = int(tx.get("value", "0"))
            value_native = Decimal(value_raw) / Decimal(10 ** decimals)
            
            ts_ms = tx.get("block_timestamp", 0)
            timestamp = int(ts_ms / 1000)
            
            tx_id = tx.get("transaction_id", "")
            
            normalized.append(
                NormalizedTransaction(
                    tx_id=f"{tx_id}_trc20",
                    chain=self.chain,
                    block_number=0,
                    timestamp=timestamp,
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    value_raw=value_raw,
                    value_native=value_native,
                    fee_raw=0,
                    is_error=False,
                    tx_type=TxType.TOKEN_TRANSFER,
                    raw_tx_id=tx_id,
                    token_contract=token_info.get("address"),
                    token_symbol=token_info.get("symbol"),
                    token_decimals=decimals,
                )
            )
            
        return normalized

    async def get_address_info(self, address: str) -> AddressInfo:
        """Computes address info by aggregating the transaction history."""
        txs = await self.get_transactions(address)
        
        total_received = Decimal(0)
        total_sent = Decimal(0)
        first_seen = None
        last_seen = None
        
        for tx in txs:
            # Only count successful native transfers for balance
            if not tx.is_error and tx.tx_type != TxType.TOKEN_TRANSFER:
                if tx.to_address == address:
                    total_received += tx.value_native
                if tx.from_address == address:
                    total_sent += tx.value_native
                    
            if first_seen is None or tx.timestamp < first_seen:
                first_seen = tx.timestamp
            if last_seen is None or tx.timestamp > last_seen:
                last_seen = tx.timestamp
                
        return AddressInfo(
            address=address,
            chain=self.chain,
            total_received=total_received,
            total_sent=total_sent,
            tx_count=len(txs),
            first_seen=first_seen,
            last_seen=last_seen
        )
