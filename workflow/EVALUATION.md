# VAULT-X — Evaluation Plan

Version 0.1 · **No results are reported in this document.** It defines what will be measured and how. Results are produced by the harness in `tests/ground-truth/` and published only as measured, with the commit hash and run ID.

---

## 1. Goals

1. Quantify whether VAULT-X attributes the **correct** VASP, and — more importantly — how often it attributes the **wrong** one.
2. Verify the system **abstains** when evidence is insufficient.
3. Verify explanations are **complete, correct and reproducible**.
4. Establish whether the confidence score is **calibrated**.
5. Characterise performance and failure modes honestly.

**Priority order of metrics:** false attribution rate > abstention correctness > accuracy > completeness > speed. A tool that is right 95% of the time but confidently wrong 5% of the time is more dangerous than one that abstains more often.

---

## 2. Ground-truth design

Ground truth must be **independently known**, not derived from the same intelligence the system uses. Otherwise the evaluation measures lookup, not attribution.

### 2.1 Ground-truth sources (in order of preference)

| Source | Description | Strength | Caveats |
|---|---|---|---|
| **Controlled experiments** | Team-created wallets send small amounts through chosen intermediaries to **team-owned accounts** at real VASPs (deposit addresses obtained from the account) | Known truth for real deposit addresses | Check each VASP's terms of service; small amounts; record account/deposit creation evidence; do not disclose account identifiers publicly |
| **Local/test networks** | Anvil/Hardhat (EVM), Bitcoin regtest, Tron private net/testnet with synthetic "VASP" entities and scripted behaviours (deposit → sweep → hot wallet) | Full control incl. mixers, bridges, ambiguity | Not real-world distribution; used for logic correctness |
| **Publicly documented cases** | Court filings, government press releases, or VASP-published proof-of-reserves addresses that link addresses to entities | Real-world | Must be independent of intel DB seed; check licence/ethics; do not use victim-identifying data |
| **Synthetic fixtures** | Hand-constructed transaction sets for edge cases | Precise edge testing | Not evidence of real-world performance |
| **Authorised real closed cases** (pilot) | Cases with outcomes confirmed through lawful process | Best realism | Requires authorisation and data-protection controls; pilot phase only |

### 2.2 Separation rule

Maintain three disjoint sets:

* **Dev set** — used to design heuristics and tune weights.
* **Calibration set** — used only to fit/evaluate calibration and thresholds.
* **Holdout test set** — touched only for reporting; never inspected during tuning.

Intel snapshot for each evaluation run **excludes** any record that would leak the answer (i.e. the labels used to define the ground truth for that scenario). Each scenario declares `intel_exclusions`, and the harness verifies they are excluded.

### 2.3 Scenario definitions

| ID | Scenario | Truth | Expected system behaviour |
|---|---|---|---|
| **TEST-001** | Suspect wallet sends directly to a known deposit address of VASP A | VASP A | Attribute A, High band, direct deposit = YES, all reasons evidenced |
| **TEST-002** | Wallet → 1–3 intermediaries → deposit address of VASP A | VASP A | Attribute A; correct path; intermediaries identified; score ≤ TEST-001 (more hops, less certainty) |
| **TEST-003** | Cross-chain: chain X → supported bridge → chain Y → deposit address of VASP A | VASP A | Trace continues across bridge; attribute A; cross-chain link evidence present; if bridge pairing heuristic-only, band capped |
| **TEST-004** | Wallet whose funds never reach any labelled VASP (or reach an unlabelled custodian) | None / unknown | **NO_ATTRIBUTION**; gaps listed; no guessed VASP |
| **TEST-005** | Ambiguous: evidence for VASP A and VASP B is comparable (e.g. shared payment processor, conflicting labels) | Ambiguous by design | **AMBIGUOUS** with both hypotheses ranked; no single confident headline |
| **TEST-006** | Wallet → mixer/CoinJoin-like contract → deposit to VASP A | VASP A (known from construction) | Mixer flagged; band capped (Low/Medium); attribution either abstains or is low-confidence; never High |
| **TEST-007** | Multiple candidate VASPs on different branches of the trace (funds split to A and B) | Both A and B | Report both as separate terminals with value shares; not collapsed into one |

Each scenario has **variants** (see §5) and multiple instances per chain (ETH, BTC, Tron) where applicable. A scenario record:

```yaml
id: TEST-002-ETH-003
chain: ethereum
mode: testnet|regtest|snapshot
seed_wallet: "0x…"
truth:
  type: VASP | NONE | AMBIGUOUS | MULTI
  vasp_ids: ["vasp-a"]
  expected_terminals: ["0x…"]
  expected_path_addresses: ["0x…", "0x…"]
  expected_direct_deposit: true
intel_exclusions: ["record-hash-…"]
params: {max_hops: 6, value_policy: proportional}
provenance: "how truth was established"
split: dev|calibration|test
```

---

## 3. Metrics

Let each scenario instance have truth `T` and system output `S` (primary hypothesis, or abstain/ambiguous).

### 3.1 Outcome classification

| Truth | System output | Outcome |
|---|---|---|
| VASP A | VASP A (band ≥ threshold) | **Correct attribution (TP)** |
| VASP A | VASP B | **False attribution (FP-wrong entity)** |
| VASP A | NO_ATTRIBUTION | **Missed (FN / abstention)** |
| NONE | NO_ATTRIBUTION | **Correct abstention (TN)** |
| NONE | any VASP | **False attribution (FP-spurious)** |
| AMBIGUOUS | AMBIGUOUS containing truth-set | **Correct ambiguity handling** |
| AMBIGUOUS | single confident VASP | **Overconfident (counts as false attribution)** |
| MULTI | all terminals reported | **Correct**; partial recall otherwise |

### 3.2 Metric definitions

| Metric | Definition | Notes |
|---|---|---|
| **Attribution accuracy (top-1)** | Correct attributions / scenarios with truth = VASP | Report with 95% CI (Wilson) |
| **Coverage** | Attributed (non-abstain) / all scenarios with truth = VASP | Accuracy is meaningless without coverage |
| **Precision (attributed)** | TP / (TP + FP) among non-abstained outputs | |
| **False attribution rate (FAR)** | (wrong-entity + spurious + overconfident) / all scenarios | **Headline safety metric**; report also FAR at each band |
| **Abstention correctness** | TN / all scenarios with truth = NONE | |
| **Ambiguity handling rate** | Correct AMBIGUOUS / AMBIGUOUS scenarios | |
| **Top-k accuracy** | Truth within top-k hypotheses | k = 1, 3 |
| **Terminal recall** (TEST-007) | Truth terminals found / truth terminals | Also precision |
| **Path correctness** | Jaccard(expected path addresses, extracted primary path) | Plus "path contains truth deposit address" boolean |
| **Trace completion** | Scenarios where the trace reached the expected terminal within limits / applicable scenarios | Report failure reasons (hop limit, fan-out cap, data gap, unsupported bridge) |
| **Cross-chain tracing success** | Successful bridge continuations / cross-chain scenarios | Split by bridge type and pairing method |
| **Evidence completeness** | Fraction of attribution reasons with (a) evidence record, (b) valid integrity hash, (c) raw artifact reference, (d) source/tier | Target defined before testing; 100% expected for deterministic parts |
| **Explanation faithfulness** | Leave-one-out: removing the evidence claimed as "supporting" lowers score; sum-of-contributions equals displayed score (tolerance ε) | Automated check |
| **Reproducibility** | Re-run from stored artifacts and manifest → identical output hash | Must be 100%; any mismatch is a bug |
| **Calibration** | Reliability diagram; Expected Calibration Error (ECE); Brier score; after calibration on the calibration set, evaluated on the test set | Applies only once N is adequate (see §7) |
| **Time to attribution** | Wall-clock from run start to hypotheses persisted; report median/p95 split by ingestion vs analysis, and provider latency | Record provider and mode |
| **Investigation-time comparison (optional)** | Time for a trained user to reach the same conclusion manually vs with VAULT-X | Small usability study; report N and method honestly |

### 3.3 Reporting format

For each run: commit hash, config versions, intel snapshot hash, dataset version, split, N per scenario type, metric values with confidence intervals, list of every FP/false-attribution with root-cause analysis. Failures are **not** filtered out.

```markdown
| Metric | Value | 95% CI | N | Run ID |
|---|---|---|---|---|
| Top-1 accuracy | _measured_ | _measured_ | _n_ | _id_ |
```

---

## 4. Methodology

1. **Freeze** code, scoring config, and intel snapshot; record hashes.
2. **Load** scenarios (snapshot fixtures or testnet/regtest state) with `intel_exclusions` applied; harness asserts exclusions.
3. **Execute** the full pipeline through the public API (not internal functions) to test the real path, including auth and audit.
4. **Compare** outputs to truth using the outcome table.
5. **Compute** metrics and confidence intervals; store raw per-scenario results.
6. **Analyse failures** manually; classify root cause (data gap, heuristic error, intel gap, scoring weight, bug).
7. **Iterate on the dev set only**; re-freeze and re-run; holdout evaluated once per release candidate.
8. **Regression gates in CI:** any decrease in reproducibility, any new false attribution on the regression set, or evidence-completeness < defined threshold blocks merge.

---

## 5. Test dimensions and variants

### 5.1 Chain coverage

Each applicable scenario instantiated on Ethereum (native + ERC-20), Tron (TRX + TRC-20), Bitcoin (UTXO with multiple inputs/outputs, change outputs).

### 5.2 Variants to include

| Dimension | Variants |
|---|---|
| Hop count | 1, 2, 3, 5, beyond max_hops |
| Value policy | proportional, FIFO, poison |
| Splitting | 1→N fan-out, N→1 consolidation, peeling chain |
| Timing | seconds apart vs days apart; out-of-window |
| Assets | native, stablecoin, multiple tokens, token with no price |
| Deposit behaviour | classic single-use deposit address; reused deposit address; deposit addresses that don't sweep immediately |
| Label quality | Tier A only; Tier C only; conflicting labels; stale label |
| Data completeness | trace API unavailable; provider rate-limited; partial pages |
| Adversarial | dust/poisoning transactions; fake "deposit-like" behaviour by a non-VASP service; address reuse |

---

## 6. Specific test batteries

### 6.1 False-positive testing

Goal: find inputs where VAULT-X names a VASP but shouldn't.

* **Non-VASP look-alikes:** payment processors, OTC desks, escrow/P2P services, DeFi aggregators that sweep like exchanges; each labelled truth = `NONE` or `UNKNOWN_CUSTODIAL` where the intel DB lacks them.
* **Coincidental proximity:** suspect wallet sends dust or unrelated funds to a known VASP address (victim interacting with exchange) — should not attribute a *flow of interest* unless value share is material.
* **Label conflicts and stale labels:** address moved between owners; conflicting Tier-C labels.
* **Heuristic traps:** Bitcoin CoinJoin/PayJoin (common-input false clustering); shared wallets/custodial pooled infrastructure; exchange-to-exchange transfers.
* **Poisoned intel:** synthetic malicious label injected into a snapshot; system must cap or flag via tiers/independence groups.
* **Acceptance rule:** reported FAR must include these adversarial cases separately from the "clean" set, so the headline is not flattered by easy cases.

### 6.2 Ambiguous attribution testing (TEST-005 family)

* Two VASPs with near-equal evidence; verify `AMBIGUOUS` presented and margin threshold documented.
* Verify UI/API never shows a single "likely VASP" headline when ambiguity is flagged.
* Sweep the ambiguity margin threshold and plot false-attribution vs coverage.
* Check that counterfactual output lists distinguishing evidence gaps for each pair.

### 6.3 Cross-chain testing (TEST-003 family)

* Supported bridge with reliable correlation key (event nonce/message ID): expect exact pairing.
* Bridge pairing by amount/time only: expect `Inferred` link and band cap.
* Unsupported bridge: expect `BRIDGE_UNSUPPORTED` stop and a next-action suggestion; not a silent termination and not a guessed continuation.
* Multiple concurrent bridge transfers of similar amounts (pairing ambiguity).
* Round-trip (A→B→A) and multi-bridge (A→B→C).
* Metric: cross-chain success rate, wrong-pairing rate.

### 6.4 Mixer/obfuscation testing (TEST-006 family)

* Simple mixer contract on devnet (deposit fixed denominations, withdraw later); Bitcoin CoinJoin-like transactions on regtest.
* Verify: mixer flagged; downstream attribution capped; no High band; report states the limitation.

### 6.5 Evidence and integrity testing

* Modify a stored evidence row / raw artifact / hash chain link → verification must fail and audit event must fire.
* Delete or reorder evidence → chain verification fails.
* Merkle inclusion proofs verify for every evidence record in a report.
* Report re-verification by an independent script outside the codebase.

### 6.6 AI-layer testing

* **Query interpretation:** a labelled set of natural-language queries with expected structured queries; measure exact-match and validation-failure rates; every failure must degrade safely.
* **Summary faithfulness:** automated check that every address/hash/amount/evidence ID in generated text exists in input; injection tests (malicious strings in labels/notes) must not alter behaviour or leak data.
* **No-write/no-DB test:** verify the AI gateway has no path to unrestricted queries.
* Report rejection/regeneration rates; do not claim "no hallucination", claim only measured validator outcomes.

### 6.6 Security/authorization testing

RBAC matrix (role × endpoint × case ownership), audit completeness (every read/write yields an event), token expiry/refresh, SSRF/injection tests on address inputs and free-text fields, dependency and container scans.

### 6.7 Performance testing

**Tooling:** Locust for API/queue load; timing harness for pipeline stages; OpenTelemetry traces.

| Test | Method | Reported |
|---|---|---|
| Single-run latency | Fixed scenarios in snapshot mode (removes provider variance) and, separately, live mode with recorded provider latency | Median/p95 per stage |
| Concurrency | N simultaneous investigations, increasing until degradation | Throughput, queue length, error rate |
| Fan-out stress | Hot-wallet-like nodes with very high degree | Behaviour of caps/aggregation; memory |
| Large graph rendering | Element counts at, and beyond, the cap | Frame rate / interaction latency on reference hardware |
| Provider failure injection | 429s, timeouts, malformed responses | Recovery, `PARTIAL` flags, no silent data loss |
| Soak | Multi-hour steady load | Memory growth, connection leaks |
| Graph projection | Rebuild time for runs of varying size | Seconds vs edges |

Hardware, dataset sizes and configuration must be reported with every performance number. No target numbers are asserted in advance beyond "interactive first results" as a design goal.

---

## 7. Statistical considerations

* Report **confidence intervals**, not point estimates; Wilson intervals for proportions.
* State N for each metric. With small N (typical for SIH-stage controlled experiments) intervals will be wide — say so; do not present percentages such as "100%" without N.
* Calibration requires enough labelled instances per confidence bin; until then keep the **UNCALIBRATED** tag and do not describe scores as probabilities.
* Multiple-comparison caution: avoid tuning against the holdout.
* Distribution shift: results on constructed scenarios do not predict real-world accuracy; the README and reports must say this.

---

## 8. Reproducibility of the evaluation itself

* All scenario definitions, fixtures, and metric code are versioned.
* Testnet/regtest states are reproducible from scripts (`scripts/build_scenario.py`) with pinned seeds.
* Each evaluation run outputs `evaluation/<run_id>/results.json`, `report.md`, and per-scenario traces.
* CI stores artifacts; a change to scoring weights requires a before/after evaluation diff in the PR description.

---

## 9. Acceptance thresholds (to be set before running, by the team)

Set and record thresholds prior to seeing test results, e.g.:

| Item | Threshold (placeholder — team to decide) |
|---|---|
| False attribution rate on holdout (clean + adversarial reported separately) | _TBD_ |
| Correct abstention on TEST-004 | _TBD_ |
| No High-band attribution in TEST-005/006 | must hold (invariant) |
| Reproducibility | 100% (invariant) |
| Evidence completeness of deterministic evidence | 100% (invariant) |
| Explanation faithfulness | _TBD_ |

Invariants failing block release; other thresholds gate the "technical MVP" milestone.

---

## 10. Reporting template

```markdown
# Evaluation Run <run_id>
Commit: … · Scoring config: … · Intel snapshot: … · Dataset: … · Split: test
## Summary (with N and CIs)
## Per-scenario results (TEST-001…007 × chain)
## False attributions (each with root cause)
## Abstention and ambiguity behaviour
## Cross-chain results
## Calibration (if applicable)
## Performance (hardware, config)
## Known limitations of this evaluation
```

**Known limitations to state in every report:** small/constructed datasets; intel coverage constraints; provider variance; results do not generalise automatically to real investigations.
