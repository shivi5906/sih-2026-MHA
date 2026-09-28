from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import yaml

from vaultx.attribution.signals import contradiction, known_deposit_match
from vaultx.schemas import Evidence, Hypothesis, NormalizedTx, RunManifest

CONFIG_PATH = Path(__file__).parent / "scoring" / "0.1.0.yaml"


@dataclass(frozen=True)
class Score:
    value: float
    band: str


def load_scoring_config(path: Path = CONFIG_PATH) -> tuple[dict, str]:
    raw = path.read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest()


def score_evidence(evidence: list[Evidence], config: dict) -> Score:
    odds = float(config["prior_log_odds"])
    seen: dict[str, int] = {}
    for item in evidence:
        count = seen.get(item.independence_group, 0)
        factors = config["diminishing_returns"]
        factor = factors[min(count, len(factors) - 1)]
        seen[item.independence_group] = count + 1
        odds += float(config["signal_weights"].get(item.type, 0)) * float(config["tier_multipliers"][item.source_tier]) * factor
    value = 1 / (1 + math.exp(-odds))
    if value >= config["band_cutoffs"]["HIGH"]: band = "HIGH"
    elif value >= config["band_cutoffs"]["MEDIUM"]: band = "MEDIUM"
    elif value >= config["abstention_threshold"]: band = "LOW"
    else: band = "INSUFFICIENT"
    return Score(value, band)


def ranked_hypotheses(tx: NormalizedTx, all_transactions: list[NormalizedTx], manifest: RunManifest | None = None, config_path: Path = CONFIG_PATH) -> tuple[list[Hypothesis], list[Evidence]]:
    config, digest = load_scoring_config(config_path)
    if manifest is not None:
        manifest.scoring_config_sha256 = digest
        manifest.calibrated = False
    label = known_deposit_match(tx)
    if label is None:
        return ([Hypothesis(id="NO_ATTRIBUTION", case_id="bitfinex2016", target_address=tx.to, hypothesis="NO_ATTRIBUTION", score=0.80, epistemic_label="NO_ATTRIBUTION", band="INSUFFICIENT", calibrated=False, next_actions=["Obtain independent ownership evidence before attributing."], supporting=[], contradicting=[]), Hypothesis(id="UNKNOWN_CUSTODIAL", case_id="bitfinex2016", target_address=tx.to, hypothesis="UNKNOWN_CUSTODIAL", score=0.20, epistemic_label="AMBIGUOUS", band="INSUFFICIENT", calibrated=False)], [])
    evidence = [label, contradiction(tx, all_transactions)]
    evidence = [item for item in evidence if item]
    score = score_evidence(evidence, config)
    candidate = tx.metadata["peerName"]
    primary = Hypothesis(id=candidate, case_id="bitfinex2016", target_address=tx.to, hypothesis=candidate, score=score.value, epistemic_label="AMBIGUOUS", band=score.band, calibrated=False, supporting=[label.id], contradicting=[item.id for item in evidence if item.type == "contradiction"], next_actions=["Find a second independent source for the label.", "Obtain lawful confirmation of deposit-address ownership."])
    alternatives = [Hypothesis(id="NO_ATTRIBUTION", case_id="bitfinex2016", target_address=tx.to, hypothesis="NO_ATTRIBUTION", score=0.30, epistemic_label="NO_ATTRIBUTION", band="INSUFFICIENT", calibrated=False), Hypothesis(id="UNKNOWN_CUSTODIAL", case_id="bitfinex2016", target_address=tx.to, hypothesis="UNKNOWN_CUSTODIAL", score=0.20, epistemic_label="AMBIGUOUS", band="INSUFFICIENT", calibrated=False)]
    return sorted([primary, *alternatives], key=lambda item: item.score, reverse=True), evidence
