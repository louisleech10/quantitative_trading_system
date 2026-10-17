"""FF-NAME Task 4.3 — golden 重凍與全量 reference（docs/FFNAME_SPEC.md Task 4.3）。

重凍對象＝事實盤點 §E 所列 golden（清單之單一落點：`tests/_golden/ffname/contract.json` 之 `refreeze.goldens`）。
驗證：每檔重凍收據附「值雜湊不變、只欄名與名雜湊變」之對照；全量 reference（1h＋12h，設定沿用既有 reference）
100% `parse` 往返；failopen 系列測試綠（gate_cmd 另跑）。
邊界：重凍前之值雜湊若有任一不同 ⇒ 停、回 Phase 2（收據不得含值不符項）。
收據落點 `refreeze.receipt`（契約定）。審查 r12：值 oracle 一律取 Task 0.1 凍結之 `tests/_golden/ffname/baseline.json`
之 `golden_values`（Phase 2 前提交、不可變）；新 golden 之值雜湊由本檔以 `golden_value_fingerprints` 重算後比對；
收據自報數字只作交叉比對，不作判定依據。
"""

from __future__ import annotations

import collections
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import (
    BASELINE_PATH,
    CONTRACT,
    REPO,
    baseline_immutability_problems,
    load_freeze_module,
)

REFREEZE = CONTRACT["refreeze"]
RECEIPT = REPO / REFREEZE["receipt"]
freeze = load_freeze_module()


def _receipt() -> Dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _mapping(baseline: Dict[str, Any]) -> Dict[str, str]:
    parts = {row["old_name"]: freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                                   "ops": tuple(row.get("ops") or ())})
             for row in baseline["parts"]}
    return freeze.derive_mapping(parts, {k: p.tf for k, p in parts.items()})


def oracle_value_mismatches(rel: str, baseline: Dict[str, Any], mapping: Dict[str, str]) -> List[str]:
    """審查 r12 CODEX-R12-P1-04：值 oracle 一律取 Task 0.1 凍結之 baseline（`golden_values`，Phase 2 前提交、不可變）。
    新 golden 之逐欄值雜湊由本測試以 `golden_value_fingerprints` 重算：①值雜湊多重集合＝baseline 者（與欄名無關）；
    ②baseline 舊欄名可經身分映射者，其新名之值雜湊＝baseline 值雜湊；③新欄名全數可 parse 往返。"""
    old = baseline["golden_values"].get(rel)
    if not old:  # 審查 r13 P1-05：oracle 須非空（空 dict 與缺鍵同判）
        return [f"no_oracle:{rel}"]
    new = freeze.golden_value_fingerprints(REPO / rel)
    bad: List[str] = []
    if len(old) != baseline.get("golden_column_counts", {}).get(rel, -1):
        bad.append(f"oracle_incomplete:{rel}")
    if not new or len(new) != len(freeze.golden_columns(REPO / rel)):
        bad.append(f"fingerprint_incomplete:{rel}")
    if collections.Counter(new.values()) != collections.Counter(old.values()):
        bad.append(f"value_multiset:{rel}")
    for old_name, value_hash in old.items():
        new_name = mapping.get(old_name)
        if new_name is not None and new_name in new and new[new_name] != value_hash:
            bad.append(f"value_mapped:{rel}:{old_name}")
    for name in new:
        try:
            if fn.format_feature_name(fn.parse_feature_name(name)) != name:
                bad.append(f"name_roundtrip:{rel}:{name}")
        except fn.FeatureNameParseError:
            bad.append(f"name_parse:{rel}:{name}")
    return bad


def refreeze_violations(receipt: Dict[str, Any], baseline: Dict[str, Any] | None = None) -> List[str]:
    """重凍違規。判定依據＝baseline oracle 重算（`oracle_value_mismatches`）與現行 golden 位元組；
    收據之自報數字只作交叉比對（自報與重算不一致亦為違規，但自報為 0 不能使重算不符過關）。"""
    baseline = baseline if baseline is not None else _baseline()
    mapping = _mapping(baseline)
    bad: List[str] = []
    files = {e["path"]: e for e in receipt.get("files", [])}
    for rel in REFREEZE["goldens"]:
        computed = oracle_value_mismatches(rel, baseline, mapping)
        if computed:
            bad.append(f"value_changed:{rel}")
            bad.extend(computed)
        entry = files.get(rel)
        if entry is None:
            bad.append(f"missing:{rel}")
            continue
        if entry.get("value_hash_mismatch", 1) != 0:
            bad.append(f"value_changed:{rel}")  # 交叉比對：收據自報不符即停
        if entry.get("value_hash_mismatch", 1) != len(computed):
            bad.append(f"receipt_disagrees:{rel}")
        if entry.get("renamed_columns", 0) <= 0 and not entry.get("name_hash_changed", False):
            bad.append(f"no_name_change:{rel}")
        if entry.get("new_sha256") != _sha(REPO / rel):
            bad.append(f"bytes_unbound:{rel}")
    return bad


def test_receipt_shape():
    receipt = _receipt()
    for key in ("schema_version", "command", "exit_code", "files", "full_reference"):
        assert key in receipt, key
    assert receipt["exit_code"] == 0


def test_every_golden_refrozen_with_values_unchanged():
    assert refreeze_violations(_receipt()) == []


def test_full_reference_parse_roundtrip_100pct():
    full = _receipt()["full_reference"]
    assert sorted(full["timeframes"]) == sorted(REFREEZE["full_reference"]["timeframes"])
    assert full["total_columns"] > 0
    assert full["parse_failures"] == 0 and full["roundtrip_failures"] == 0
    assert full["feature_naming_version"] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_boundary_01_value_hash_difference_stops_refreeze():
    receipt = copy.deepcopy(_receipt())
    victim = receipt["files"][0]
    victim["value_hash_mismatch"] = 1
    assert f"value_changed:{victim['path']}" in refreeze_violations(receipt)


def test_baseline_has_value_oracle_for_every_golden():
    golden_values = _baseline()["golden_values"]
    assert sorted(golden_values) == sorted(REFREEZE["goldens"])


def test_values_recomputed_against_baseline_oracle():
    baseline = _baseline()
    mapping = _mapping(baseline)
    assert {rel: oracle_value_mismatches(rel, baseline, mapping) for rel in REFREEZE["goldens"]} == \
        {rel: [] for rel in REFREEZE["goldens"]}


def test_full_reference_columns_recomputed():
    """收據之全量 reference 欄名清單由本測試重算往返（自報之失敗數只作交叉比對）。"""
    full = _receipt()["full_reference"]
    columns = full["columns"]
    failures = [c for c in columns if fn.format_feature_name(fn.parse_feature_name(c)) != c]
    assert len(columns) == full["total_columns"] > 0
    assert failures == [] and full["parse_failures"] == len(failures)


def test_mutation_golden_and_receipt_changed_together_is_caught(monkeypatch):
    """審查 r12 CODEX-R12-P1-04 mutant：golden 值被改、收據同時寫 mismatch=0 與新 bytes 之 sha ⇒ baseline oracle 仍拒。"""
    baseline = _baseline()
    target = next(rel for rel in REFREEZE["goldens"] if baseline["golden_values"].get(rel))
    real = freeze.golden_value_fingerprints

    def tampered(path):
        out = dict(real(path))
        if str(path).endswith(target) and out:
            first = sorted(out)[0]
            out[first] = "0" * 64
        return out

    receipt = copy.deepcopy(_receipt())
    for entry in receipt["files"]:
        entry["value_hash_mismatch"] = 0
        entry["new_sha256"] = _sha(REPO / entry["path"])
    monkeypatch.setattr(freeze, "golden_value_fingerprints", tampered)
    violations = refreeze_violations(receipt, baseline)
    assert f"value_changed:{target}" in violations
    assert f"value_multiset:{target}" in violations


def test_baseline_oracle_is_anchored_and_immutable():
    """審查 r13 P1-05：值 oracle 所在之 baseline.json 須等於 Task 0.1 錨定之 sha（baseline.sha256 只有 1 筆提交）。"""
    assert baseline_immutability_problems() == []


def test_mutation_baseline_and_golden_emptied_together_is_caught(monkeypatch):
    """審查 r13 mutant：fingerprint 對 golden 回空、baseline 之 golden_values 亦挖空，收據寫 0 ⇒ 仍拒（no_oracle）。"""
    baseline = copy.deepcopy(_baseline())
    target = REFREEZE["goldens"][0]
    baseline["golden_values"][target] = {}
    monkeypatch.setattr(freeze, "golden_value_fingerprints", lambda path: {})
    receipt = copy.deepcopy(_receipt())
    for entry in receipt["files"]:
        entry["value_hash_mismatch"] = 0
    violations = refreeze_violations(receipt, baseline)
    assert f"no_oracle:{target}" in violations and f"value_changed:{target}" in violations


def test_mutation_unbound_golden_bytes_detected(monkeypatch, tmp_path):
    """mutant：重凍後另改 golden 位元組（收據未綁定）⇒ bytes_unbound。"""
    receipt = _receipt()
    target = REFREEZE["goldens"][0]
    fake = tmp_path / "golden_copy.json"
    fake.write_bytes((REPO / target).read_bytes() + b"\n")
    real_sha = _sha
    monkeypatch.setattr(sys.modules[__name__], "_sha", lambda p: real_sha(fake) if str(p).endswith(target) else real_sha(p))
    assert f"bytes_unbound:{target}" in refreeze_violations(receipt)
