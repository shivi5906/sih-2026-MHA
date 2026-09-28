from __future__ import annotations
import pytest
from vaultx.models.transaction import Chain
from vaultx.chains.detection import detect_chain, validate_address


def test_detect_ethereum():
    assert detect_chain('0xaaa1111111111111111111111111111111111111') == Chain.ETHEREUM
    assert detect_chain('0x28C6c06298d514Db089934071355E5743bf21d60') == Chain.ETHEREUM


def test_detect_bitcoin_p2pkh():
    assert detect_chain('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa') == Chain.BITCOIN


def test_detect_bitcoin_p2sh():
    assert detect_chain('34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo') == Chain.BITCOIN


def test_detect_bitcoin_bech32():
    assert detect_chain('bc1qsuspect11111111111111111111111111111') == Chain.BITCOIN


def test_detect_tron():
    assert detect_chain('TDqSquXBgUCLYvYC4XAofeEsNtJBBPMNkV') == Chain.TRON


def test_detect_invalid():
    assert detect_chain('') is None
    assert detect_chain('not_an_address') is None
    assert detect_chain('0x123') is None


def test_validate_address_correct_chain():
    assert validate_address('0xaaa1111111111111111111111111111111111111', Chain.ETHEREUM) is True
    assert validate_address('bc1qsuspect11111111111111111111111111111', Chain.BITCOIN) is True
    assert validate_address('TDqSquXBgUCLYvYC4XAofeEsNtJBBPMNkV', Chain.TRON) is True


def test_validate_address_wrong_chain():
    assert validate_address('0xaaa1111111111111111111111111111111111111', Chain.BITCOIN) is False
    assert validate_address('bc1qsuspect11111111111111111111111111111', Chain.ETHEREUM) is False
