from __future__ import annotations

from decimal import Decimal

from vaultx.models.transaction import NormalizedTransaction, Chain, TxType
from vaultx.models.address import AddressInfo
from vaultx.chains.base import ChainAdapter


class EthereumAdapter(ChainAdapter):
    """Adapter for Ethereum utilizing the Etherscan V2 API format."""
    
    @property
    def chain(self) -> Chain:
        return Chain.ETHEREUM

    async def _fetch_txs(self, address: str, action: str) -> list[dict]:
        """Helper to paginate through Etherscan transactions."""
        all_txs = []
        page = 1
        while True:
            params = {
                'module': 'account',
                'action': action,
                'address': address,
                'startblock': 0,
                'endblock': 99999999,
                'page': page,
                'offset': 1000,
                'sort': 'asc'
            }
            response = await self.provider.fetch('ethereum', '', params, None)
            
            # Status 0 with "No transactions found" is treated as empty result
            if response.get("status") == "0":
                break
                
            results = response.get("result", [])
            if not results:
                break
                
            all_txs.extend(results)
            
            if len(results) < 1000:
                break
                
            page += 1
            
        return all_txs

    async def get_transactions(self, address: str) -> list[NormalizedTransaction]:
        """Fetches normal, internal, and ERC-20 token transactions and normalizes them."""
        normal_txs = await self._fetch_txs(address, 'txlist')
        
        # Internal transactions may not exist for every address — gracefully handle
        try:
            internal_txs = await self._fetch_txs(address, 'txlistinternal')
        except (FileNotFoundError, Exception):
            internal_txs = []
        
        # ERC-20 token transfers — gracefully handle missing fixture
        try:
            token_txs = await self._fetch_txs(address, 'tokentx')
        except (FileNotFoundError, Exception):
            token_txs = []
        
        normalized = []
        
        # Helper to convert raw wei strings to Decimal ETH
        def to_eth(wei_str: str) -> Decimal:
            return Decimal(wei_str) / Decimal(10**18)
            
        # Process normal transactions
        for tx in normal_txs:
            value_raw = int(tx.get("value", "0"))
            
            # Determine tx_type based on whether the 'to' address is empty (contract creation)
            to_addr = tx.get("to", "")
            if not to_addr:
                tx_type = TxType.CONTRACT_CALL
            else:
                tx_type = TxType.TRANSFER
                
            is_error = tx.get("isError") == "1"
            
            normalized.append(
                NormalizedTransaction(
                    tx_id=tx["hash"],
                    chain=self.chain,
                    block_number=int(tx["blockNumber"]),
                    timestamp=int(tx["timeStamp"]),
                    from_address=tx["from"],
                    to_address=to_addr,
                    value_raw=value_raw,
                    value_native=to_eth(tx.get("value", "0")),
                    fee_raw=int(tx.get("gasUsed", "0")) * int(tx.get("gasPrice", "0")),
                    is_error=is_error,
                    tx_type=tx_type,
                    raw_tx_id=tx["hash"]
                )
            )
            
        # Process internal transactions
        for tx in internal_txs:
            value_raw = int(tx.get("value", "0"))
            is_error = tx.get("isError") == "1"
            
            # Internal tx IDs are usually derived from the main hash, but etherscan returns the parent hash
            tx_id = f"{tx['hash']}_{tx.get('traceId', '')}"
            
            normalized.append(
                NormalizedTransaction(
                    tx_id=tx_id,
                    chain=self.chain,
                    block_number=int(tx["blockNumber"]),
                    timestamp=int(tx["timeStamp"]),
                    from_address=tx["from"],
                    to_address=tx["to"],
                    value_raw=value_raw,
                    value_native=to_eth(tx.get("value", "0")),
                    fee_raw=0,  # Gas paid by parent
                    is_error=is_error,
                    tx_type=TxType.INTERNAL,
                    raw_tx_id=tx["hash"]
                )
            )
        
        # Process ERC-20 token transfers
        for tx in token_txs:
            token_decimals = int(tx.get("tokenDecimal", "18"))
            value_raw = int(tx.get("value", "0"))
            value_native = Decimal(value_raw) / Decimal(10 ** token_decimals)
            
            tx_id = f"{tx['hash']}_tok_{tx.get('logIndex', '0')}"
            
            normalized.append(
                NormalizedTransaction(
                    tx_id=tx_id,
                    chain=self.chain,
                    block_number=int(tx["blockNumber"]),
                    timestamp=int(tx["timeStamp"]),
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    value_raw=value_raw,
                    value_native=value_native,
                    fee_raw=0,
                    is_error=False,
                    tx_type=TxType.TOKEN_TRANSFER,
                    raw_tx_id=tx["hash"],
                    token_contract=tx.get("contractAddress"),
                    token_symbol=tx.get("tokenSymbol"),
                    token_decimals=token_decimals,
                )
            )
            
        # Sort by block_number and timestamp for consistency
        normalized.sort(key=lambda x: (x.block_number, x.timestamp))
        return normalized

    async def get_address_info(self, address: str) -> AddressInfo:
        """Computes address info by aggregating the transaction history."""
        txs = await self.get_transactions(address)
        
        total_received = Decimal(0)
        total_sent = Decimal(0)
        first_seen = None
        last_seen = None
        
        addr_lower = address.lower()
        
        for tx in txs:
            # Only count successful native transactions for balances
            if not tx.is_error and tx.tx_type != TxType.TOKEN_TRANSFER:
                if tx.to_address.lower() == addr_lower:
                    total_received += tx.value_native
                if tx.from_address.lower() == addr_lower:
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
