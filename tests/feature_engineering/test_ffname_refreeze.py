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
    registered = REFREEZE.get("no_column_records", {}).get(rel)
    if registered is not None:  # SPEC v15 §G：無逐欄紀錄之 golden 依登記類別分派 oracle
        if old:
            return [f"registered_but_has_records:{rel}"]
        if registered.get("class") == "name_free":
            return name_free_mismatches(rel, baseline)
        if registered.get("class") == "remap_recompute":
            return remap_recompute_mismatches(rel, baseline, mapping)
        return [f"unknown_oracle_class:{rel}:{registered.get('class')}"]
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


def name_free_mismatches(rel: str, baseline: Dict[str, Any]) -> List[str]:
    """SPEC v15 §G `name_free`：檔內無特徵欄名 ⇒ 重凍後位元組不變（現檔 sha256＝baseline `golden_file_sha256`）。"""
    recorded = (baseline.get("golden_file_sha256") or {}).get(rel)
    if not recorded:
        return [f"no_file_sha:{rel}"]
    return [] if _sha(REPO / rel) == recorded else [f"name_free_bytes_changed:{rel}"]


def _pre_change_golden(rel: str, baseline: Dict[str, Any]) -> bytes | None:
    """改前 golden 位元組：baseline `frozen_at_head` 之該檔（git 物件），且其 sha256 須＝baseline `golden_file_sha256`。"""
    import subprocess

    head = baseline.get("frozen_at_head")
    recorded = (baseline.get("golden_file_sha256") or {}).get(rel)
    if not head or not recorded:
        return None
    proc = subprocess.run(["git", "show", f"{head}:{rel}"], cwd=str(REPO), capture_output=True)
    if proc.returncode != 0 or hashlib.sha256(proc.stdout).hexdigest() != recorded:
        return None
    return proc.stdout


def _json_at(node: Any, path: str) -> Any:
    for key in path.split("/"):
        node = node[int(key)] if isinstance(node, list) else node[key]
    return node


def _leaf_paths(node: Any, prefix: str = "") -> List[str]:
    """JSON 全部葉路徑（`/` 連接，與 `_json_at` 同格式）；空容器本身視為葉。"""
    if isinstance(node, dict) and node:
        return [p for k, v in node.items() for p in _leaf_paths(v, f"{prefix}/{k}" if prefix else str(k))]
    if isinstance(node, list) and node:
        return [p for i, v in enumerate(node) for p in _leaf_paths(v, f"{prefix}/{i}" if prefix else str(i))]
    return [prefix]


def remap_expected_paths(rel: str, old: Any) -> set:
    """`remap_recompute` 須重算之封閉路徑集合＝改前 golden 全部葉路徑，扣除契約 `refreeze.remap_exempt_prefixes[rel]`
    （僅限執行環境與凍結提交等非產物欄位）。"""
    exempt = REFREEZE.get("remap_exempt_prefixes", {}).get(rel, [])
    return {p for p in _leaf_paths(old) if not any(p == e or p.startswith(e + "/") for e in exempt)}


def remap_recompute_mismatches(rel: str, baseline: Dict[str, Any], mapping: Dict[str, str]) -> List[str]:
    """SPEC v15 §G `remap_recompute`：以 golden 自身雜湊函式對重凍產物重算（新名經 baseline 映射之反函數換回舊名），
    結果之每一欄位須與改前 golden（`frozen_at_head` 之該檔）對應欄位相等。重算本體＝`freeze.remap_recompute_golden`
    （Task 4.3 實作；之前拋 NotImplementedError ⇒ 本 oracle 不通過，不得偽綠）。"""
    old_bytes = _pre_change_golden(rel, baseline)
    if old_bytes is None:
        return [f"pre_change_bytes_unavailable:{rel}"]
    inverse = {new: old for old, new in mapping.items()}
    try:
        recomputed = freeze.remap_recompute_golden(REPO / rel, inverse)
    except NotImplementedError:
        return [f"remap_recompute_unimplemented:{rel}"]
    if not recomputed:
        return [f"remap_recompute_empty:{rel}"]
    old = json.loads(old_bytes.decode("utf-8"))
    bad: List[str] = []
    # 審查 r16 CODEX-R16-P1-01：重算須涵蓋改前 golden 之全部葉路徑（扣除契約 `remap_exempt_prefixes`），缺漏或多出皆違規
    expected = remap_expected_paths(rel, old)
    bad += [f"remap_path_omitted:{rel}:{p}" for p in sorted(expected - set(recomputed))]
    bad += [f"remap_path_extra:{rel}:{p}" for p in sorted(set(recomputed) - expected)]
    for path, value in recomputed.items():
        try:
            if _json_at(old, path) != value:
                bad.append(f"remap_value:{rel}:{path}")
        except (KeyError, IndexError, ValueError, TypeError):
            bad.append(f"remap_path_missing:{rel}:{path}")
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
    # 逐欄 golden（未登記 no_column_records）方以 no_oracle 判；登記者依類別分派（見下兩條測試）
    target = next(rel for rel in REFREEZE["goldens"] if rel not in REFREEZE.get("no_column_records", {}))
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


def test_name_free_goldens_byte_identical():
    """SPEC v15 §G `name_free`：重凍後位元組不變（sha256＝baseline `golden_file_sha256`）。"""
    baseline = _baseline()
    names = [rel for rel, e in REFREEZE["no_column_records"].items() if e["class"] == "name_free"]
    assert names
    assert {rel: name_free_mismatches(rel, baseline) for rel in names} == {rel: [] for rel in names}


def test_remap_recompute_oracle_reproduces_pre_change_bytes():
    """SPEC v15 §G `remap_recompute`：以 golden 自身雜湊函式於反向映射後重算＝改前 golden 對應欄位。
    重算本體屬 Task 4.3（`remap_recompute_golden`）；之前本測試必紅（remap_recompute_unimplemented），不得偽綠。"""
    baseline = _baseline()
    mapping = _mapping(baseline)
    names = [rel for rel, e in REFREEZE["no_column_records"].items() if e["class"] == "remap_recompute"]
    assert names
    assert {rel: remap_recompute_mismatches(rel, baseline, mapping) for rel in names} == {rel: [] for rel in names}


def test_mutation_remap_recompute_omitting_paths_is_caught(monkeypatch):
    """審查 r16 CODEX-R16-P1-01 mutant：重算只回傳部分路徑（省略發生差異之欄位）⇒ remap_path_omitted；
    對照組：回傳全部封閉路徑且值等於改前 ⇒ 無違規（證明 oracle 非恆紅）；多回傳一條 ⇒ remap_path_extra。"""
    baseline = _baseline()
    mapping = _mapping(baseline)
    rel = next(r for r, e in REFREEZE["no_column_records"].items() if e["class"] == "remap_recompute")
    old_bytes = _pre_change_golden(rel, baseline)
    assert old_bytes is not None
    old = json.loads(old_bytes.decode("utf-8"))
    expected = sorted(remap_expected_paths(rel, old))
    assert len(expected) > 1
    full = {p: _json_at(old, p) for p in expected}

    monkeypatch.setattr(freeze, "remap_recompute_golden", lambda path, inverse: dict(full))
    assert remap_recompute_mismatches(rel, baseline, mapping) == []
    partial = dict(list(full.items())[:1])
    monkeypatch.setattr(freeze, "remap_recompute_golden", lambda path, inverse: dict(partial))
    bad = remap_recompute_mismatches(rel, baseline, mapping)
    assert bad and all(b.startswith(f"remap_path_omitted:{rel}:") for b in bad)
    monkeypatch.setattr(freeze, "remap_recompute_golden", lambda path, inverse: {**full, "ffname_probe_extra": 1})
    assert remap_recompute_mismatches(rel, baseline, mapping) == [f"remap_path_extra:{rel}:ffname_probe_extra",
                                                                   f"remap_path_missing:{rel}:ffname_probe_extra"]


def test_mutation_name_free_bytes_changed_is_caught():
    """mutant：name_free golden 之 baseline 檔案 sha 與現檔不符（等同重凍改了位元組）⇒ name_free_bytes_changed。"""
    baseline = copy.deepcopy(_baseline())
    target = next(rel for rel, e in REFREEZE["no_column_records"].items() if e["class"] == "name_free")
    baseline["golden_file_sha256"][target] = "0" * 64
    assert name_free_mismatches(target, baseline) == [f"name_free_bytes_changed:{target}"]
    assert f"name_free_bytes_changed:{target}" in oracle_value_mismatches(target, baseline, _mapping(baseline))


def test_mutation_registered_golden_with_records_is_caught():
    """mutant：登記為無逐欄紀錄之 golden 於 baseline 卻有逐欄紀錄 ⇒ registered_but_has_records（不得混用兩種 oracle）。"""
    baseline = copy.deepcopy(_baseline())
    target = sorted(REFREEZE["no_column_records"])[0]
    baseline["golden_values"][target] = {"x": "0" * int(REFREEZE["golden_value_hash_len"])}
    assert oracle_value_mismatches(target, baseline, _mapping(baseline)) == [f"registered_but_has_records:{target}"]
