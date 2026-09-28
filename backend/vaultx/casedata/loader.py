"""Bitfinex 2016 case-file loader; no on-chain facts are invented."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from vaultx.schemas import DataQualityIssue, DataQualityReport, NormalizedTx

CASE_DIR = Path(__file__).resolve().parents[2] / "data" / "cases" / "bitfinex2016"
THEFT_FILE = "2072_Unauthorized_Transaction_Bitfinex_Aug_2016.csv"
JAN2017_FILE = "20170127--Bitfinex_Hacked_Coins.csv"
THEFT_ORIGIN = "virtual:bitfinex-theft-tx"
HACKED_POOL_JAN2017 = "virtual:bitfinex-jan2017-pool"
SATOSHIS_PER_BTC = Decimal("100000000")


@dataclass(frozen=True)
class CaseData:
    theft_transactions: list[NormalizedTx]
    january_transactions: list[NormalizedTx]
    report: DataQualityReport

    @property
    def transactions(self) -> list[NormalizedTx]:
        return self.theft_transactions + self.january_transactions


def _timestamp(value: str) -> int:
    return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())


def _swap_month_day(value: str) -> int:
    parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    return int(datetime(parsed.year, parsed.day, parsed.month, parsed.hour, parsed.minute, parsed.second, tzinfo=timezone.utc).timestamp())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _satoshis(amount: Decimal) -> int:
    return int((amount * SATOSHIS_PER_BTC).to_integral_exact())


def _load_theft(path: Path) -> list[NormalizedTx]:
    digest = _sha256(path)
    result: list[NormalizedTx] = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            amount = Decimal(row["XBT Amount"])
            as_given = _timestamp(row["Received Time"])
            corrected = _swap_month_day(row["Received Time"])
            result.append(NormalizedTx(
                id=row["Transaction Hash"], tx_hash=row["Transaction Hash"], from_=THEFT_ORIGIN,
                to=row["Receiving Address"], amount=amount, satoshis=_satoshis(amount),
                timestamp=corrected, timestamp_as_given=as_given, timestamp_corrected=corrected,
                timestamp_assumed=True, epistemic_label="CASE_ASSERTED",
                provenance={"dataset": "bitfinex2016-theft", "file": path.name, "sha256": digest, "row": row_number},
                metadata={"displayTimestampTag": "assumed", "dateSwapSuspected": True},
            ))
    return result


def _load_january(path: Path) -> list[NormalizedTx]:
    digest = _sha256(path)
    result: list[NormalizedTx] = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for row_number, row in enumerate(csv.DictReader(stream), start=2):
            amount = Decimal(row["Sent"])
            timestamp = _timestamp(row["Date"])
            metadata = {"peerCluster": row["Peer Cluster"], "peerName": row["Peer Name"], "peerCategory": row["Peer Category"]}
            result.append(NormalizedTx(
                id=row["Transaction Hash"], tx_hash=row["Transaction Hash"], from_=HACKED_POOL_JAN2017,
                to=row["Receiving address"], amount=amount, satoshis=_satoshis(amount), timestamp=timestamp,
                block_number=int(row["Block Height"]), epistemic_label="CASE_ASSERTED",
                provenance={"dataset": "bitfinex2016-january2017", "file": path.name, "sha256": digest, "row": row_number}, metadata=metadata,
            ))
    return result


def load_case_data(case_dir: Path = CASE_DIR) -> CaseData:
    theft = _load_theft(case_dir / THEFT_FILE)
    january = _load_january(case_dir / JAN2017_FILE)
    theft_addresses = {tx.to for tx in theft}
    january_addresses = {tx.to for tx in january}
    labels = [tx for tx in january if tx.metadata["peerName"] or tx.metadata["peerCategory"]]
    report = DataQualityReport(
        row_counts={"theft": len(theft), "january2017": len(january)},
        duplicate_transactions={"theft": len(theft) - len({tx.tx_hash for tx in theft}), "january2017": len(january) - len({tx.tx_hash for tx in january})},
        date_swap_suspected=True, missing_labels={"january2017": len(january) - len(labels)},
        no_address_overlap=not bool(theft_addresses & january_addresses),
        issues=[
            DataQualityIssue(issue_code="DATE_SWAP_SUSPECTED", severity="warning", affected_rows=len(theft), message="Dataset A dates are parsed as given; corrected display dates assume month/day were swapped."),
            DataQualityIssue(issue_code="MISSING_PEER_LABELS", severity="info", affected_rows=len(january) - len(labels), message="Dataset B has one labeled row and remaining rows have no peer label."),
            DataQualityIssue(issue_code="NO_ADDRESS_OVERLAP", severity="info", message="The two files share no receiving addresses; this case data establishes no on-chain link between them."),
        ],
    )
    return CaseData(theft, january, report)


if __name__ == "__main__":
    print(json.dumps(load_case_data().report.model_dump(mode="json", by_alias=True), indent=2))
