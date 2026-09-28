from __future__ import annotations
import pytest
from decimal import Decimal
from vaultx.models.transaction import Chain, TxType


@pytest.mark.asyncio
async def test_ethereum_parses_fixture(eth_adapter):
    """Verify the Ethereum adapter correctly parses Etherscan V2 responses."""
    txs = await eth_adapter.get_transactions('0xaaa1111111111111111111111111111111111111')
    assert len(txs) == 2  # tx0 (receive) + tx1 (send)

    # First tx: incoming 10 ETH
    tx0 = txs[0]
    assert tx0.chain == Chain.ETHEREUM
    assert tx0.tx_id == '0xeth_tx0'
    assert tx0.from_address == '0xfff0000000000000000000000000000000000000'
    assert tx0.to_address == '0xaaa1111111111111111111111111111111111111'
    assert tx0.value_native == Decimal('10')
    assert tx0.value_raw == 10000000000000000000
    assert tx0.timestamp == 1699900000
    assert tx0.block_number == 17000000
    assert tx0.is_error is False
    assert tx0.tx_type == TxType.TRANSFER

    # Second tx: outgoing 5 ETH
    tx1 = txs[1]
    assert tx1.tx_id == '0xeth_tx1'
    assert tx1.from_address == '0xaaa1111111111111111111111111111111111111'
    assert tx1.to_address == '0xbbb2222222222222222222222222222222222222'
    assert tx1.value_native == Decimal('5')
    assert tx1.timestamp == 1700000000


@pytest.mark.asyncio
async def test_ethereum_values_are_decimal(eth_adapter):
    txs = await eth_adapter.get_transactions('0xaaa1111111111111111111111111111111111111')
    for tx in txs:
        assert isinstance(tx.value_native, Decimal)


@pytest.mark.asyncio
async def test_ethereum_direction(eth_adapter):
    txs = await eth_adapter.get_transactions('0xaaa1111111111111111111111111111111111111')
    addr = '0xaaa1111111111111111111111111111111111111'
    assert txs[0].direction(addr) == 'incoming'
    assert txs[1].direction(addr) == 'outgoing'


@pytest.mark.asyncio
async def test_bitcoin_utxo_decomposition(btc_adapter):
    """Verify Bitcoin adapter decomposes UTXO transactions into input->output pairs."""
    txs = await btc_adapter.get_transactions('bc1qsuspect11111111111111111111111111111')
    # TX1 has 1 input (funder) -> 2 outputs (suspect + funder change) = 2 normalized txs
    # TX2 has 1 input (suspect) -> 2 outputs (intermediary + change) = 2 normalized txs
    # Total: 4 normalized transactions
    assert len(txs) == 4

    # All should be on Bitcoin chain
    for tx in txs:
        assert tx.chain == Chain.BITCOIN
        assert isinstance(tx.value_native, Decimal)
        assert tx.tx_type == TxType.TRANSFER

    # Find the tx from suspect to intermediary
    suspect_to_intermed = [t for t in txs if 
        t.from_address == 'bc1qsuspect11111111111111111111111111111' and
        t.to_address == 'bc1qintermed2222222222222222222222222222']
    assert len(suspect_to_intermed) == 1
    tx = suspect_to_intermed[0]
    assert tx.raw_tx_id == 'btc_tx2'
    # With 1 input of 50000 and 2 outputs (40000 + 9500), the proportional allocation
    # for the 40000 output = (50000/50000) * 40000 = 40000 sats
    assert tx.value_raw == 40000
    assert tx.value_native == Decimal('40000') / Decimal('100000000')  # 0.0004 BTC


@pytest.mark.asyncio
async def test_tron_normalization(tron_adapter):
    """Verify Tron adapter converts hex addresses, sun amounts, and ms timestamps."""
    # The fixture file is named for the base58-converted suspect address
    txs = await tron_adapter.get_transactions('TRXcKoEvHr6Y38VMcDYGBEYKznvH3XUX4g')
    assert len(txs) == 2

    # First tx: receive 100 TRX (100000000 sun) 
    tx0 = txs[0]
    assert tx0.chain == Chain.TRON
    assert tx0.tx_id == 'tron_tx1'
    assert tx0.value_native == Decimal('100')  # 100000000 sun / 1000000
    assert tx0.value_raw == 100000000
    # Timestamp should be in seconds (1700000000), not milliseconds
    assert tx0.timestamp == 1700000000
    # Addresses should be Base58Check, not hex
    assert tx0.from_address.startswith('T') or tx0.from_address[0].isdigit()
    assert not tx0.from_address.startswith('41')  # should not be hex

    # Second tx: send 80 TRX
    tx1 = txs[1]
    assert tx1.tx_id == 'tron_tx2'
    assert tx1.value_native == Decimal('80')
    assert tx1.timestamp == 1700100000
