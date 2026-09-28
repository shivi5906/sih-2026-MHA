"""Uncalibrated, evidence-backed attribution ranking."""
from __future__ import annotations

import json

from vaultx.attribution.hypotheses import ranked_hypotheses
from vaultx.casedata.loader import load_case_data


def main() -> None:
    case_data = load_case_data()
    tx = next(item for item in case_data.january_transactions if item.metadata["peerName"] == "Xzzx.biz")
    hypotheses, evidence = ranked_hypotheses(tx, case_data.january_transactions)
    print("SNAPSHOT / CASE REPLAY")
    print(json.dumps({"hypotheses": [item.model_dump(by_alias=True, mode="json") for item in hypotheses], "evidenceIds": [item.id for item in evidence]}, indent=2))


if __name__ == "__main__":
    main()
