from pathlib import Path

from vaultx.attribution.counterfactual import sensitivity
from vaultx.attribution.hypotheses import CONFIG_PATH, load_scoring_config, ranked_hypotheses, score_evidence
from vaultx.casedata.loader import load_case_data


def test_labeled_replay_is_not_high_and_unlabeled_rows_abstain():
    data = load_case_data()
    labeled = next(tx for tx in data.january_transactions if tx.metadata["peerName"] == "Xzzx.biz")
    hypotheses, evidence = ranked_hypotheses(labeled, data.january_transactions)
    assert hypotheses[0].hypothesis == "Xzzx.biz"
    assert hypotheses[0].band in {"MEDIUM", "LOW"}
    assert hypotheses[0].band != "HIGH"
    assert hypotheses[0].next_actions
    assert all(ranked_hypotheses(tx, data.january_transactions)[0][0].hypothesis == "NO_ATTRIBUTION" for tx in data.january_transactions if not tx.metadata["peerName"])
    config, _ = load_scoring_config()
    assert sensitivity(evidence, config)[evidence[0].id] is True


def test_score_is_monotonic_and_yaml_is_tunable(tmp_path: Path):
    data = load_case_data()
    tx = next(item for item in data.january_transactions if item.metadata["peerName"])
    _, evidence = ranked_hypotheses(tx, data.january_transactions)
    config, _ = load_scoring_config()
    assert score_evidence([evidence[1]], config).value < score_evidence(evidence, config).value
    tuned = tmp_path / "scoring.yaml"
    tuned.write_text(CONFIG_PATH.read_text().replace("known_deposit_match: 2.80", "known_deposit_match: 3.80"))
    changed, _ = load_scoring_config(tuned)
    assert score_evidence(evidence, changed).value != score_evidence(evidence, config).value
