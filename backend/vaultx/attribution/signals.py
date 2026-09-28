from __future__ import annotations

import hashlib
from decimal import Decimal

from vaultx.schemas import Evidence, NormalizedTx


def _evidence(kind: str, tx: NormalizedTx, description: str, *, tier: str = "C", group: str = "case-file", label: str = "OBSERVED") -> Evidence:
    evidence_id = hashlib.sha256(f"{kind}:{tx.id}".encode()).hexdigest()[:16]
    return Evidence(id=f"EV-{evidence_id}", case_id="bitfinex2016", type=kind, source=tx.provenance["file"], timestamp=tx.timestamp, weight=Decimal("1"), confidence=Decimal("1"), description=description, verified=False, hash="", tx_refs=[tx.tx_hash], source_tier=tier, independence_group=group, epistemic_label=label)


def known_deposit_match(tx: NormalizedTx) -> Evidence | None:
    name = tx.metadata.get("peerName")
    if not name:
        return None
    return _evidence("known_deposit_match", tx, f"Dataset-B peer label records {name}; this is a single unverified source.", group="dataset-b-peer-label")


def hot_wallet_forward(candidate: NormalizedTx, labeled_addresses: set[str]) -> Evidence | None:
    if candidate.to not in labeled_addresses:
        return None
    return _evidence("hot_wallet_forward", candidate, "Candidate forwards to a labeled address.", tier="B", group="forwarding")


def sweep_fan_out(transactions: list[NormalizedTx]) -> Evidence | None:
    outputs = [tx for tx in transactions if tx.from_.startswith("virtual:") and Decimal("3.45") <= tx.amount <= Decimal("4.99")]
    blocks = {tx.block_number for tx in outputs if tx.block_number is not None}
    if len(outputs) < 10 or len(blocks) > 10:
        return None
    return _evidence("sweep_fan_out", outputs[0], f"{len(outputs)} uniform 3.45–4.99 BTC outputs appear across {len(blocks)} blocks.", group="dataset-b-pattern", label="INFERRED")


def contradiction(tx: NormalizedTx, transactions: list[NormalizedTx]) -> Evidence | None:
    if not tx.metadata.get("peerName"):
        return None
    uniform = [item for item in transactions if Decimal("3.45") <= item.amount <= Decimal("4.99")]
    return _evidence("contradiction", tx, f"The label appears on one of {len(uniform)} uniform outputs; no independent ownership confirmation is present.", group="dataset-b-peer-label", label="UNCERTAIN")
