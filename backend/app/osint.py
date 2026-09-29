"""Open-source intelligence (OSINT) enrichment for attributed VASPs.

Runs after a trace has produced its graph and attribution hypotheses. The
highest-scoring attributed VASPs are enriched with:

* the VASP's public, organisation-level channels (X/Twitter, Telegram,
  Facebook, Instagram) from a small curated registry;
* pivot links an analyst can open to search public sources for the deposit
  address itself (block explorers, abuse databases, social search);
* placeholders for live OSINT connectors, which are NOT connected in this
  prototype (MOCK).

Account-holder identity (name, phone, e-mail) is never guessed. It is only
obtainable from the VASP through a lawful request (SAHYOG, MOCK here).

All scores are UNCALIBRATED heuristics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

import networkx as nx

from vaultx.exchanges.known import get_exchange_info

# Hypotheses that are abstentions rather than a named VASP.
NON_VASP_HYPOTHESES = {"NO_ATTRIBUTION", "UNKNOWN_CUSTODIAL", "UNKNOWN", ""}
MAX_TARGETS = 5
REGISTRY_SOURCE = "curated-vasp-registry (public profiles, tier C, re-verify before use)"

# Platform keys in display order. Phone is last and never populated from the registry.
PLATFORMS: list[tuple[str, str]] = [
    ("x", "X / Twitter"),
    ("telegram", "Telegram"),
    ("facebook", "Facebook"),
    ("instagram", "Instagram"),
    ("phone", "Phone"),
]
PLATFORM_URL = {
    "x": "https://x.com/{}",
    "telegram": "https://t.me/{}",
    "facebook": "https://www.facebook.com/{}",
    "instagram": "https://www.instagram.com/{}",
}

# Organisation-level public profiles only. A missing value means the registry
# holds no profile, not that one does not exist.
VASP_REGISTRY: dict[str, dict[str, Any]] = {
    "binance": {
        "displayName": "Binance",
        "website": "https://www.binance.com",
        "handles": {"x": "binance", "telegram": "binanceexchange", "facebook": "binance", "instagram": "binance"},
    },
    "coinbase": {
        "displayName": "Coinbase",
        "website": "https://www.coinbase.com",
        "handles": {"x": "coinbase", "facebook": "coinbase", "instagram": "coinbase"},
    },
    "kraken": {
        "displayName": "Kraken",
        "website": "https://www.kraken.com",
        "handles": {"x": "krakenfx", "facebook": "KrakenFX", "instagram": "krakenfx"},
    },
    "okx": {
        "displayName": "OKX",
        "website": "https://www.okx.com",
        "handles": {"x": "okx", "telegram": "OKXOfficial_English"},
    },
    "huobi": {
        "displayName": "HTX (formerly Huobi)",
        "website": "https://www.htx.com",
        "handles": {"x": "HTX_Global"},
    },
    "bitfinex": {
        "displayName": "Bitfinex",
        "website": "https://www.bitfinex.com",
        "handles": {"x": "bitfinex"},
    },
    "xzzx.biz": {
        "displayName": "Xzzx.biz",
        "website": None,
        "handles": {},
        "note": "Label comes from the case dataset only. No public profile is held in the registry.",
    },
}

LIVE_CONNECTORS = [
    ("X (Twitter) API v2", "Search posts mentioning the address or VASP handle."),
    ("Telegram (MTProto)", "Search public channels and groups for the address."),
    ("Meta Graph API", "Facebook and Instagram public page lookups."),
    ("Telecom / phone lookup", "Resolve a phone number once one is lawfully obtained."),
]


def _num(value: Any) -> float:
    try:
        return float(Decimal(str(value)))
    except (InvalidOperation, ValueError, TypeError):
        return 0.0


def _band(score: float, band: str | None) -> str:
    if band in {"HIGH", "MEDIUM", "LOW", "INSUFFICIENT"}:
        return band
    if score >= 0.85:
        return "HIGH"
    if score >= 0.60:
        return "MEDIUM"
    return "LOW"


def _priority(score: float, band: str) -> str:
    if band == "HIGH" or score >= 0.85:
        return "HIGH"
    if band == "MEDIUM" or score >= 0.5:
        return "MEDIUM"
    return "LOW"


def _real_transfers(transactions: list[dict]) -> list[dict]:
    """Drop the placeholder self-loop written when a trace found no hops."""
    return [tx for tx in transactions if tx.get("from") and tx.get("to") and tx.get("from") != tx.get("to")]


def _iso(ts: Any) -> str | None:
    try:
        value = int(ts)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")


def pivot_links(address: str, chain: str | None, vasp: str) -> list[dict[str, str]]:
    """Public search pivots for an address. Opening them is the analyst's action."""
    a = quote(address, safe="")
    chain_l = (chain or "").lower()
    links: list[dict[str, str]] = []
    if chain_l == "ethereum" or address.lower().startswith("0x"):
        links.append({"name": "Etherscan", "kind": "explorer", "url": f"https://etherscan.io/address/{a}"})
    elif chain_l == "tron" or address.startswith("T"):
        links.append({"name": "Tronscan", "kind": "explorer", "url": f"https://tronscan.org/#/address/{a}"})
    else:
        links.append({"name": "mempool.space", "kind": "explorer", "url": f"https://mempool.space/address/{a}"})
        links.append({"name": "WalletExplorer", "kind": "cluster", "url": f"https://www.walletexplorer.com/address/{a}"})
    links.append({"name": "Chainabuse", "kind": "abuse-db", "url": f"https://www.chainabuse.com/address/{a}"})
    links.append({"name": "X search: address", "kind": "social-search", "url": f"https://x.com/search?q={a}&f=live"})
    links.append({"name": "Web search: address", "kind": "web-search", "url": f"https://www.google.com/search?q=%22{a}%22"})
    if vasp:
        links.append({"name": "X search: VASP", "kind": "social-search", "url": f"https://x.com/search?q={quote(vasp, safe='')}&f=live"})
    return links


def vasp_channels(vasp: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    entry = VASP_REGISTRY.get(vasp.strip().lower())
    handles = (entry or {}).get("handles", {})
    channels: list[dict[str, Any]] = []
    for key, platform in PLATFORMS:
        if key == "phone":
            channels.append({
                "platform": platform, "handle": None, "url": None, "status": "NOT_PUBLIC",
                "epistemicLabel": "UNCERTAIN", "source": "none",
                "note": "Not publicly listed. Account-holder phone is obtainable only via lawful request to the VASP.",
            })
            continue
        handle = handles.get(key)
        if handle:
            channels.append({
                "platform": platform, "handle": f"@{handle}" if key in {"x", "instagram"} else handle,
                "url": PLATFORM_URL[key].format(handle), "status": "FOUND",
                "epistemicLabel": "ATTRIBUTED", "source": REGISTRY_SOURCE,
                "note": "Organisation-level public profile of the VASP, not of the account holder.",
            })
        else:
            channels.append({
                "platform": platform, "handle": None, "url": None, "status": "NOT_FOUND",
                "epistemicLabel": "UNCERTAIN", "source": REGISTRY_SOURCE,
                "note": "No profile held in the registry. Live connector not connected (MOCK).",
            })
    return entry, channels


def select_targets(hypotheses: list[dict], limit: int = MAX_TARGETS) -> list[dict]:
    """Highest-scoring named VASP hypotheses, one per (VASP, address)."""
    best: dict[tuple[str, str], dict] = {}
    for h in hypotheses:
        name = str(h.get("hypothesis") or "").strip()
        if name.upper() in NON_VASP_HYPOTHESES or h.get("epistemicLabel") == "NO_ATTRIBUTION":
            continue
        key = (name.lower(), str(h.get("targetAddress") or ""))
        score = _num(h.get("score"))
        if key not in best or score > _num(best[key].get("score")):
            best[key] = h
    return sorted(best.values(), key=lambda h: _num(h.get("score")), reverse=True)[:limit]


def _inflow(address: str, transfers: list[dict]) -> dict[str, Any]:
    incoming = [tx for tx in transfers if tx.get("to") == address]
    stamps = sorted(int(tx["timestamp"]) for tx in incoming if isinstance(tx.get("timestamp"), (int, float)) and tx["timestamp"] > 0)
    assets = Counter(tx.get("asset", "BTC") for tx in incoming)
    return {
        "txCount": len(incoming),
        "totalValue": round(sum(_num(tx.get("amount")) for tx in incoming), 8),
        "asset": assets.most_common(1)[0][0] if assets else None,
        "uniqueSenders": len({tx.get("from") for tx in incoming}),
        "firstSeen": _iso(stamps[0]) if stamps else None,
        "lastSeen": _iso(stamps[-1]) if stamps else None,
    }


def build_target(h: dict, transfers: list[dict]) -> dict[str, Any]:
    vasp = str(h.get("hypothesis"))
    address = str(h.get("targetAddress") or "")
    score = _num(h.get("score"))
    band = _band(score, h.get("band"))
    registry_hit = get_exchange_info(address) if address else None
    chain = next((tx.get("chain") for tx in transfers if tx.get("to") == address and tx.get("chain")), None)
    if chain is None and registry_hit is not None:
        chain = registry_hit.chain.name.title()
    entry, channels = vasp_channels(vasp)
    public = [c for c in channels if c["platform"] != "Phone"]
    coverage = sum(c["status"] == "FOUND" for c in public) / len(public)
    return {
        "id": str(h.get("id") or vasp),
        "vasp": (entry or {}).get("displayName", vasp),
        "targetAddress": address,
        "chain": chain,
        "attributionScore": round(score, 4),
        "band": band,
        "priority": _priority(score, band),
        "epistemicLabel": h.get("epistemicLabel", "ATTRIBUTED"),
        "osintCoverage": round(coverage, 4),
        "investigationPriority": round(0.7 * score + 0.3 * coverage, 4),
        "calibrated": False,
        "profile": {
            "entityType": "VASP",
            "website": (entry or {}).get("website"),
            "inRegistry": entry is not None,
            "knownHotWallet": registry_hit is not None,
            "note": (entry or {}).get("note"),
        },
        "inflow": _inflow(address, transfers),
        "channels": channels,
        "accountHolder": {
            "status": "LAWFUL_REQUEST_REQUIRED",
            "fields": ["Name / KYC identity", "Registered phone number", "Registered e-mail", "Login IP history"],
            "route": "SAHYOG (MOCK)",
            "epistemicLabel": "UNCERTAIN",
        },
        "pivots": pivot_links(address, chain, (entry or {}).get("displayName", vasp)),
        "connectors": [{"name": n, "purpose": p, "status": "NOT_CONNECTED", "mock": True} for n, p in LIVE_CONNECTORS],
        "supporting": list(h.get("supporting") or []),
        "nextActions": list(h.get("nextActions") or []),
    }


VALUE_BUCKETS = [(0, 0.01, "< 0.01"), (0.01, 0.1, "0.01-0.1"), (0.1, 1, "0.1-1"), (1, 10, "1-10"), (10, 100, "10-100"), (100, float("inf"), "100+")]


def graph_analytics(transactions: list[dict], vasp_addresses: set[str] | None = None) -> dict[str, Any]:
    """Structural statistics over every recorded transfer (not only rendered edges)."""
    transfers = _real_transfers(transactions)
    g = nx.DiGraph()
    for tx in transfers:
        src, dst, amt = tx["from"], tx["to"], _num(tx.get("amount"))
        if g.has_edge(src, dst):
            g[src][dst]["value"] += amt
            g[src][dst]["count"] += 1
        else:
            g.add_edge(src, dst, value=amt, count=1)

    in_val: dict[str, float] = defaultdict(float)
    out_val: dict[str, float] = defaultdict(float)
    for tx in transfers:
        amt = _num(tx.get("amount"))
        out_val[tx["from"]] += amt
        in_val[tx["to"]] += amt

    hubs = sorted(g.nodes, key=lambda n: (g.in_degree(n) + g.out_degree(n), in_val[n] + out_val[n]), reverse=True)[:6]
    buckets = Counter()
    for tx in transfers:
        amt = _num(tx.get("amount"))
        for lo, hi, name in VALUE_BUCKETS:
            if lo <= amt < hi:
                buckets[name] += 1
                break

    timeline: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "value": 0.0})
    for tx in transfers:
        day = _iso(tx.get("timestamp"))
        if day:
            month = day[:7]
            timeline[month]["count"] += 1
            timeline[month]["value"] += _num(tx.get("amount"))

    datasets = Counter((tx.get("provenance") or {}).get("dataset", "unknown") for tx in transfers)
    hops = Counter(int((tx.get("metadata") or {}).get("hopNumber")) for tx in transfers if str((tx.get("metadata") or {}).get("hopNumber", "")).isdigit())
    assets = Counter(tx.get("asset", "BTC") for tx in transfers)
    vasp_addresses = vasp_addresses or set()
    into_vasp = sum(_num(tx.get("amount")) for tx in transfers if tx["to"] in vasp_addresses)
    total_value = sum(_num(tx.get("amount")) for tx in transfers)

    return {
        "nodes": g.number_of_nodes(),
        "edges": len(transfers),
        "uniqueLinks": g.number_of_edges(),
        "totalValue": round(total_value, 8),
        "asset": assets.most_common(1)[0][0] if assets else None,
        "density": round(nx.density(g), 6) if g.number_of_nodes() > 1 else 0.0,
        "components": nx.number_weakly_connected_components(g) if g.number_of_nodes() else 0,
        "sources": sum(1 for n in g.nodes if g.in_degree(n) == 0),
        "sinks": sum(1 for n in g.nodes if g.out_degree(n) == 0),
        "valueIntoVasps": round(into_vasp, 8),
        "valueIntoVaspsShare": round(into_vasp / total_value, 6) if total_value else 0.0,
        "topHubs": [
            {"address": n, "inDegree": g.in_degree(n), "outDegree": g.out_degree(n), "value": round(in_val[n] + out_val[n], 8), "isVasp": n in vasp_addresses}
            for n in hubs
        ],
        "valueBuckets": [{"label": name, "count": buckets.get(name, 0)} for _, _, name in VALUE_BUCKETS],
        "timeline": [{"month": m, "count": int(v["count"]), "value": round(v["value"], 8)} for m, v in sorted(timeline.items())],
        "datasets": [{"name": k, "count": v} for k, v in datasets.most_common()],
        "hopDistribution": [{"hop": k, "count": v} for k, v in sorted(hops.items())],
        "epistemicLabel": "OBSERVED",
    }


def build_osint_report(run_id: str, banner: str, hypotheses: list[dict], transactions: list[dict]) -> dict[str, Any]:
    transfers = _real_transfers(transactions)
    targets = [build_target(h, transfers) for h in select_targets(hypotheses)]
    vasp_addresses = {t["targetAddress"] for t in targets if t["targetAddress"]}
    found = sum(1 for t in targets for c in t["channels"] if c["status"] == "FOUND")
    return {
        "runId": run_id,
        "banner": banner or "SNAPSHOT / CASE REPLAY",
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "calibrated": False,
        "sahyogMock": True,
        "connectorsLive": False,
        "summary": {
            "targets": len(targets),
            "highPriority": sum(t["priority"] == "HIGH" for t in targets),
            "channelsFound": found,
            "channelsChecked": len(targets) * len(PLATFORMS),
            "hypothesesConsidered": len(hypotheses),
        },
        "targets": targets,
        "graphAnalytics": graph_analytics(transactions, vasp_addresses),
        "disclaimer": (
            "Public channels are organisation-level VASP profiles from a curated registry (tier C) and must be "
            "re-verified before use. No live OSINT connector is connected (MOCK). Account-holder identity, including "
            "phone numbers, is only obtainable through a lawful request. All scores are UNCALIBRATED."
        ),
    }
