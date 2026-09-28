from __future__ import annotations

from decimal import Decimal

from vaultx.models.transaction import NormalizedTransaction, Chain, TxType
from vaultx.models.address import AddressInfo
from vaultx.chains.base import ChainAdapter


class BitcoinAdapter(ChainAdapter):
    """Adapter for Bitcoin using the Blockstream Esplora API format."""
    
    @property
    def chain(self) -> Chain:
        return Chain.BITCOIN

    async def get_transactions(self, address: str) -> list[NormalizedTransaction]:
        """Fetches transactions and performs proportional UTXO decomposition."""
        all_txs = []
        endpoint = f"/address/{address}/txs"
        
        while True:
            batch = await self.provider.fetch('bitcoin', endpoint, None, None)
            
            if not batch or not isinstance(batch, list):
                break
                
            all_txs.extend(batch)
            
            if len(batch) < 25:
                break
                
            # Chain requests for pagination
            last_txid = batch[-1].get("txid")
            endpoint = f"/address/{address}/txs/chain/{last_txid}"

        normalized = []
        
        def to_btc(satoshis: int) -> Decimal:
            return Decimal(satoshis) / Decimal(100_000_000)

        for tx in all_txs:
            txid = tx["txid"]
            status = tx.get("status", {})
            timestamp = status.get("block_time", 0)
            block_number = status.get("block_height", 0)
            fee = int(tx.get("fee", 0))
            is_error = False  # Confirmed/unconfirmed UTXO txs are generally valid if returned by the API
            
            vins = tx.get("vin", [])
            vouts = tx.get("vout", [])
            
            # Calculate total input value to allocate amounts proportionally
            total_input_value = sum(
                int(vin.get("prevout", {}).get("value", 0)) 
                for vin in vins 
                if vin.get("prevout")
            )
            
            # Collect co-spent input addresses for this transaction.
            # All inputs in the same tx are presumed to share ownership
            # (common-input-ownership heuristic). Track B uses this for
            # address clustering — Track A just exposes the raw fact.
            co_spent_addresses = list({
                v.get("prevout", {}).get("scriptpubkey_address")
                for v in vins
                if v.get("prevout", {}).get("scriptpubkey_address")
            })

            for vin_idx, vin in enumerate(vins):
                if vin.get("is_coinbase"):
                    continue
                    
                prevout = vin.get("prevout")
                if not prevout:
                    continue
                    
                from_addr = prevout.get("scriptpubkey_address")
                if not from_addr:
                    continue
                    
                vin_value = int(prevout.get("value", 0))
                
                # Proportion of total inputs this specific input represents
                proportion = Decimal(vin_value) / Decimal(total_input_value) if total_input_value else Decimal(0)
                
                for vout_idx, vout in enumerate(vouts):
                    if vout.get("scriptpubkey_type") == "op_return":
                        continue
                        
                    to_addr = vout.get("scriptpubkey_address")
                    if not to_addr:
                        continue
                        
                    vout_value = int(vout.get("value", 0))
                    
                    # Allocate value proportionally
                    allocated_value_raw = int(Decimal(vout_value) * proportion)
                    
                    # Create a unique pairing ID
                    unique_tx_id = f"{txid}:{vin_idx}:{vout_idx}"
                    
                    normalized.append(
                        NormalizedTransaction(
                            tx_id=unique_tx_id,
                            chain=self.chain,
                            block_number=block_number,
                            timestamp=timestamp,
                            from_address=from_addr,
                            to_address=to_addr,
                            value_raw=allocated_value_raw,
                            value_native=to_btc(allocated_value_raw),
                            fee_raw=fee,
                            is_error=is_error,
                            tx_type=TxType.TRANSFER,
                            raw_tx_id=txid,
                            metadata={"co_spent_addresses": co_spent_addresses},
                        )
                    )
                    
        return normalized

    async def get_address_info(self, address: str) -> AddressInfo:
        """Fetches address stats from the API directly."""
        endpoint = f"/address/{address}"
        data = await self.provider.fetch('bitcoin', endpoint, None, None)
        
        chain_stats = data.get("chain_stats", {})
        funded_satoshis = int(chain_stats.get("funded_txo_sum", 0))
        spent_satoshis = int(chain_stats.get("spent_txo_sum", 0))
        tx_count = int(chain_stats.get("tx_count", 0))
        
        # Calculate first and last seen based on the transactions
        txs = await self.get_transactions(address)
        first_seen = None
        last_seen = None
        
        if txs:
            valid_timestamps = [tx.timestamp for tx in txs if tx.timestamp > 0]
            if valid_timestamps:
                first_seen = min(valid_timestamps)
                last_seen = max(valid_timestamps)
            
        def to_btc(satoshis: int) -> Decimal:
            return Decimal(satoshis) / Decimal(100_000_000)
            
        return AddressInfo(
            address=address,
            chain=self.chain,
            total_received=to_btc(funded_satoshis),
            total_sent=to_btc(spent_satoshis),
            tx_count=tx_count,
            first_seen=first_seen,
            last_seen=last_seen
        )
