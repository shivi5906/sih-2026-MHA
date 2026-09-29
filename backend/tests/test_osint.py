from app.osint import build_osint_report, graph_analytics, select_targets, vasp_channels

HYPOTHESES = [
    {"id": "Xzzx.biz", "hypothesis": "Xzzx.biz", "targetAddress": "15vrWRtHMaqhE54yPucDFZHs8a4BZVKVMn", "score": "0.5553966483205892", "epistemicLabel": "AMBIGUOUS", "supporting": ["EV-1"]},
    {"id": "NO_ATTRIBUTION", "hypothesis": "NO_ATTRIBUTION", "targetAddress": "15vrWRtHMaqhE54yPucDFZHs8a4BZVKVMn", "score": "0.3", "epistemicLabel": "NO_ATTRIBUTION", "band": "INSUFFICIENT"},
    {"id": "UNKNOWN_CUSTODIAL", "hypothesis": "UNKNOWN_CUSTODIAL", "targetAddress": "15vrWRtHMaqhE54yPucDFZHs8a4BZVKVMn", "score": "0.2", "epistemicLabel": "AMBIGUOUS"},
    {"id": "Binance", "hypothesis": "Binance", "targetAddress": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", "score": 0.91, "band": "HIGH", "epistemicLabel": "ATTRIBUTED"},
]
TXS = [
    {"id": "a", "from": "virtual:pool", "to": "1A", "amount": "5", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1470138609, "provenance": {"dataset": "d1"}},
    {"id": "b", "from": "1A", "to": "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo", "amount": "4.5", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1485323523, "provenance": {"dataset": "d1"}, "metadata": {"hopNumber": 1}},
    {"id": "c", "from": "1A", "to": "15vrWRtHMaqhE54yPucDFZHs8a4BZVKVMn", "amount": "0.4", "asset": "BTC", "chain": "Bitcoin", "timestamp": 1485323523, "provenance": {"dataset": "d2"}},
    {"id": "start", "from": "1Z", "to": "1Z", "amount": "0", "txHash": "none"},
]


def test_targets_skip_abstentions_and_rank_by_score():
    targets = select_targets(HYPOTHESES)
    assert [t["hypothesis"] for t in targets] == ["Binance", "Xzzx.biz"]


def test_phone_is_never_populated_and_unknown_vasp_has_no_channels():
    _, channels = vasp_channels("Xzzx.biz")
    assert all(c["status"] != "FOUND" for c in channels)
    phone = next(c for c in channels if c["platform"] == "Phone")
    assert phone["status"] == "NOT_PUBLIC" and phone["handle"] is None


def test_report_is_uncalibrated_mock_and_labelled():
    report = build_osint_report("run-1", "SNAPSHOT / CASE REPLAY", HYPOTHESES, TXS)
    assert report["calibrated"] is False and report["sahyogMock"] is True and report["connectorsLive"] is False
    top = report["targets"][0]
    assert top["vasp"] == "Binance" and top["priority"] == "HIGH" and top["chain"] == "Bitcoin"
    assert top["inflow"] == {"txCount": 1, "totalValue": 4.5, "asset": "BTC", "uniqueSenders": 1, "firstSeen": "2017-01-25", "lastSeen": "2017-01-25"}
    assert all(c["epistemicLabel"] in {"ATTRIBUTED", "UNCERTAIN"} for c in top["channels"])
    assert all(c["mock"] and c["status"] == "NOT_CONNECTED" for c in top["connectors"])
    assert report["targets"][1]["priority"] == "MEDIUM"


def test_graph_analytics_ignores_placeholder_self_loop():
    stats = graph_analytics(TXS, {"34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo"})
    assert stats["nodes"] == 4 and stats["edges"] == 3
    assert stats["totalValue"] == 9.9 and stats["valueIntoVasps"] == 4.5
    assert stats["topHubs"][0]["address"] == "1A"
    assert stats["hopDistribution"] == [{"hop": 1, "count": 1}]
    assert sum(b["count"] for b in stats["valueBuckets"]) == 3
    assert [p["month"] for p in stats["timeline"]] == ["2016-08", "2017-01"]


def test_empty_case_does_not_crash():
    report = build_osint_report("run-2", "", [], [])
    assert report["targets"] == [] and report["graphAnalytics"]["nodes"] == 0
