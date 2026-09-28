"""Pydantic v2 API schemas for VAULT-X."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class NormalizedTx(CamelModel):
    id: str
    tx_hash: str
    from_: str = Field(alias="from", serialization_alias="from")
    to: str
    amount: Decimal
    satoshis: int
    asset: str = "BTC"
    timestamp: int
    chain: str = "Bitcoin"
    fee: Decimal | None = None
    block_number: int | None = None
    confidence: Decimal | None = None
    timestamp_as_given: int | None = None
    timestamp_corrected: int | None = None
    timestamp_assumed: bool = False
    epistemic_label: str = "OBSERVED"
    provenance: dict[str, str | int]
    metadata: dict[str, Any] = Field(default_factory=dict)


class Address(CamelModel):
    id: str
    address: str
    chain: str
    label: str | None = None
    risk_level: str = "unknown"
    entity_type: str | None = None
    tags: list[str] = Field(default_factory=list)
    last_seen: int | None = None


class Evidence(CamelModel):
    id: str
    case_id: str
    type: str
    source: str
    timestamp: int
    weight: Decimal
    confidence: Decimal
    description: str
    verified: bool
    hash: str


class Hypothesis(CamelModel):
    id: str
    case_id: str
    target_address: str
    hypothesis: str
    score: Decimal
    epistemic_label: str
    signals: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class RunManifest(CamelModel):
    id: str
    case_id: str
    trace_steps: list[dict[str, Any]] = Field(default_factory=list)
    completed_at: int | None = None
    status: str


class GraphNode(CamelModel):
    id: str
    label: str
    data: dict[str, Any]


class GraphEdge(CamelModel):
    id: str
    source: str
    target: str
    data: dict[str, Any]
    epistemic_label: str = "OBSERVED"


class DataQualityIssue(CamelModel):
    issue_code: str
    severity: str
    message: str
    affected_rows: int = 0


class DataQualityReport(CamelModel):
    row_counts: dict[str, int]
    duplicate_transactions: dict[str, int]
    date_swap_suspected: bool
    missing_labels: dict[str, int]
    no_address_overlap: bool
    issues: list[DataQualityIssue]


def normalized_tx_from_dataclass(transaction: Any) -> NormalizedTx:
    """Map the existing engine dataclass without changing its contract."""
    chain = transaction.chain.name.capitalize()
    asset = transaction.token_symbol or ("BTC" if chain == "Bitcoin" else chain.upper())
    return NormalizedTx(
        id=transaction.tx_id, tx_hash=transaction.raw_tx_id, from_=transaction.from_address,
        to=transaction.to_address, amount=transaction.value_native,
        satoshis=transaction.value_raw if chain == "Bitcoin" else 0, asset=asset,
        timestamp=transaction.timestamp, chain=chain, block_number=transaction.block_number,
        provenance={"dataset": "engine", "file": "normalized-transaction", "row": 0, "sha256": ""},
        metadata=transaction.metadata or {},
    )
