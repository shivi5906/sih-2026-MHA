"""Chain adapter over recorded Bitfinex case data."""
from __future__ import annotations

from decimal import Decimal

from vaultx.casedata.loader import HACKED_POOL_JAN2017, THEFT_ORIGIN, CaseData, load_case_data
from vaultx.chains.base import ChainAdapter
from vaultx.models.address import AddressInfo
from vaultx.models.transaction import Chain, NormalizedTransaction, TxType


class CaseDatasetAdapter(ChainAdapter):
    """Expose recorded CSV movements to ``TracingEngine`` without network access."""

    def __init__(self, case_data: CaseData | None = None) -> None:
        self.case_data = case_data or load_case_data()
        self.provider = None

    @property
    def chain(self) -> Chain:
        return Chain.BITCOIN

    @staticmethod
    def _engine_transaction(tx) -> NormalizedTransaction:
        return NormalizedTransaction(
            tx_id=tx.id, raw_tx_id=tx.tx_hash, chain=Chain.BITCOIN,
            block_number=tx.block_number or 0, timestamp=tx.timestamp,
            from_address=tx.from_, to_address=tx.to, value_raw=tx.satoshis,
            value_native=tx.amount, fee_raw=0, is_error=False, tx_type=TxType.TRANSFER,
            metadata={**tx.metadata, "provenance": tx.provenance, "epistemic_label": tx.epistemic_label},
        )

    async def get_transactions(self, address: str) -> list[NormalizedTransaction]:
        target = address.lower()
        return [self._engine_transaction(tx) for tx in self.case_data.transactions if tx.from_.lower() == target or tx.to.lower() == target]

    async def get_address_info(self, address: str) -> AddressInfo:
        transactions = await self.get_transactions(address)
        target = address.lower()
        incoming = [tx.value_native for tx in transactions if tx.to_address.lower() == target]
        outgoing = [tx.value_native for tx in transactions if tx.from_address.lower() == target]
        timestamps = [tx.timestamp for tx in transactions]
        return AddressInfo(
            address=address, chain=self.chain, total_received=sum(incoming, Decimal("0")),
            total_sent=sum(outgoing, Decimal("0")), tx_count=len(transactions),
            first_seen=min(timestamps) if timestamps else None, last_seen=max(timestamps) if timestamps else None,
        )


VIRTUAL_NODE_IDS = (THEFT_ORIGIN, HACKED_POOL_JAN2017)
