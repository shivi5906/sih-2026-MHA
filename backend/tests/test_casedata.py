from decimal import Decimal

from vaultx.casedata.loader import load_case_data


def test_bitfinex_case_data_quality_and_totals():
    case_data = load_case_data()
    assert sum((tx.amount for tx in case_data.theft_transactions), Decimal("0")) == Decimal("119754.81216269")
    january_total = sum((tx.amount for tx in case_data.january_transactions), Decimal("0"))
    assert january_total.quantize(Decimal("0.01")) == Decimal("876.82")
    assert case_data.report.date_swap_suspected is True
    assert case_data.report.no_address_overlap is True


def test_bitfinex_case_data_has_one_labeled_january_row():
    case_data = load_case_data()
    labels = [tx for tx in case_data.january_transactions if tx.metadata["peerName"] or tx.metadata["peerCategory"]]
    assert len(labels) == 1
    assert labels[0].metadata["peerName"] == "Xzzx.biz"
    assert labels[0].metadata["peerCategory"] == "exchange"
    assert labels[0].to == "15vrWRtHMaqhE54yPucDFZHs8a4BZVKVMn"
    assert labels[0].metadata["peerCluster"] == "1NTo6BEU7jciqhFMGWGjEKXegtdPyJtbrj"
    assert labels[0].amount == Decimal("4.17659523")
