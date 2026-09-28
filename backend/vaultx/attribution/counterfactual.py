from __future__ import annotations

from vaultx.attribution.hypotheses import score_evidence
from vaultx.schemas import Evidence


def sensitivity(evidence: list[Evidence], config: dict) -> dict[str, bool]:
    """True means removal of this one item crosses the abstention threshold."""
    return {item.id: score_evidence([other for other in evidence if other.id != item.id], config).value < config["abstention_threshold"] for item in evidence}
