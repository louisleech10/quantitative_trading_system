"""FF-NAME Task 4.3 — golden 重凍與全量 reference（docs/FFNAME_SPEC.md v21 §G「重凍 golden 之處置與值 oracle」）。

處置清單之單一落點：`tests/_golden/ffname/contract.json` 之 `refreeze.dispositions`（檔 → K0／K1／K2／K3、理由、消費測試）
與 `refreeze.salt_only_fields`。本檔依類別獨立重算判定，收據（`refreeze.receipt`）之自報數字只作交叉比對：
- K0 不需重凍：現檔位元組＝baseline `frozen_at_head` 之該檔（不要求換名數）；消費測試另跑須綠。
- K1 改前快照只換鍵：映射取自改前 worktree 以該 golden 自身設定跑之組名點紀錄器（`handoffs/run_receipts/
  ffname_refreeze_maps/`），查無／歧義 ⇒ 失敗；改前檔經映射換鍵後，除契約 `name_hash_fields` 外每個值位元組相等；
  不得殘留會改名之舊名；可獨立重算之名雜湊（names sha、column_set_digest）以該 golden 自身函式重算比對。
- K2 彙總雜湊：新舊碼 sidecar 依名逐欄比對（不以多重集合代替）不符 0；多出之新欄須全屬 §G ⑥ 新增 lag 且位移已驗；
  現檔位元組綁定收據。
- K3：現檔＝改前檔恰套用契約 `k3_renames` 之鍵改名，值不動。
- 鹽差：`salt_only_fields` 之值＝現行碼 config hash，且去命名世代鹽重算＝改前值。
- 全量 reference（ETHUSDT 1h＋12h）100% parse 往返（欄名清單由本檔重算）。
"""

from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import pytest

import momentum.FeatureEngineering.feature_naming as fn
from tests.feature_engineering.ffname_helpers import (
    BASELINE_PATH,
    CONTRACT,
    REPO,
    baseline_immutability_problems,
    is_g6_new_lag,
)

REFREEZE = CONTRACT["refreeze"]
DISP: Dict[str, Dict[str, Any]] = REFREEZE["dispositions"]
RECEIPT = REPO / REFREEZE["receipt"]
MAPS_DIR = REPO / "handoffs" / "run_receipts" / "ffname_refreeze_maps"
SALT_KEY = "_feature_naming_version"


def _of(cls: str) -> List[str]:
    return sorted(rel for rel, d in DISP.items() if d["class"] == cls)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _receipt() -> Dict[str, Any]:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


def _baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _blob(rel: str) -> Optional[bytes]:
    """改前位元組：baseline `frozen_at_head` 之該檔（git 物件；Phase 2 前、不可變）。"""
    head = _baseline().get("frozen_at_head")
    proc = subprocess.run(["git", "show", f"{head}:{rel}"], cwd=str(REPO), capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def _slug(rel: str) -> str:
    return rel.replace("tests/_golden/", "").replace(".json", "").replace("/", "__")


def _match(path: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


# ================================================================ 契約


def test_dispositions_cover_baseline_goldens():
    """每個 baseline 範圍之 golden 恰有一個處置；goldens＝非 K0；每項有理由與消費測試；K1／K2 有紀錄器 recipe。"""
    outside = {rel for rel, d in DISP.items() if d.get("outside_baseline")}
    assert sorted(set(DISP) - outside) == sorted(REFREEZE["baseline_goldens"])
    assert all(DISP[rel]["class"] != "K0" for rel in outside)  # baseline 範圍外者必有實際處置（不得以 K0 略過）
    assert sorted(REFREEZE["goldens"]) == sorted(rel for rel, d in DISP.items() if d["class"] != "K0")
    for rel, d in DISP.items():
        assert d["class"] in REFREEZE["classes"], rel
        assert str(d.get("reason", "")).strip() and d.get("consumers"), rel
        if d["class"] in ("K1", "K2"):
            assert d.get("recipe"), rel
    assert _baseline()["golden_values"].keys() == set(REFREEZE["baseline_goldens"])


def test_receipt_shape():
    receipt = _receipt()
    for key in ("schema_version", "command", "exit_code", "files", "salt_only", "full_reference"):
        assert key in receipt, key
    assert receipt["schema_version"] == REFREEZE["receipt_schema"]
    assert receipt["exit_code"] == 0
    assert sorted(e["path"] for e in receipt["files"]) == sorted(DISP)
    assert {e["path"]: e["class"] for e in receipt["files"]} == {rel: d["class"] for rel, d in DISP.items()}


_COLLECT_CACHE: Dict[tuple, List[str]] = {}


def _collect(consumers: List[str]) -> List[str]:
    """契約 consumers 經 `pytest --collect-only` 展開之 nodeid 全集（與收據工具同法、獨立重算）。"""
    key = tuple(consumers)
    if key not in _COLLECT_CACHE:
        import sys

        proc = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-qq", "-o", "log_cli=false",
                               "-p", "no:cacheprovider", *consumers], cwd=str(REPO), capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout[-500:]
        _COLLECT_CACHE[key] = sorted({ln.strip() for ln in proc.stdout.splitlines() if "::" in ln and not ln.startswith(" ")})
    return _COLLECT_CACHE[key]


def consumer_run_problems(rel: str, run: Optional[Dict[str, Any]], expected: Optional[List[str]] = None) -> List[str]:
    """審查 r1 P1-04／r2 P1-02：實際執行之 nodeid 集合＝契約 consumers 展開集合、total＝passed+failed+skipped、
    failed==0、非空；consumers 欄須逐字等於契約。"""
    consumers = DISP[rel]["consumers"]
    expected = _collect(consumers) if expected is None else expected
    if not run:
        return [f"consumer_run_missing:{rel}"]
    bad: List[str] = []
    executed = run.get("executed") or {}
    if not isinstance(executed, dict) or not executed:
        bad.append(f"consumer_nodeids_empty:{rel}")
    if list(run.get("consumers") or []) != list(consumers):
        bad.append(f"consumer_set_not_contract:{rel}")
    if set(executed) != set(expected):
        bad.append(f"consumer_nodeids_mismatch:{rel}")
    counts = [run.get(k) for k in ("passed", "failed", "skipped")]
    if not all(isinstance(x, int) for x in counts) or run.get("total") != sum(counts) or run.get("total") != len(executed):
        bad.append(f"consumer_counts_inconsistent:{rel}")
    elif run["failed"] != 0 or any(v in ("failed", "error") for v in executed.values()):
        bad.append(f"consumer_red:{rel}")
    elif run["passed"] <= 0:
        bad.append(f"consumer_nothing_passed:{rel}")
    return bad


def receipt_consumer_problems(receipt: Dict[str, Any]) -> List[str]:
    bad: List[str] = []
    for e in receipt["files"]:
        if e.get("decision") == "pre_existing_drift" and not e.get("value_hash_mismatch") and \
                _sha((REPO / e["path"]).read_bytes()) == _sha(_blob(e["path"]) or b""):
            continue  # SPEC v22：既有漂移（golden 位元組不動）之消費測試紅歸登記之既有漂移，由 K2 判定另驗
        bad += consumer_run_problems(e["path"], e.get("consumer_run"))
    return bad


def _a_green_k0_run() -> tuple:
    receipt = _receipt()
    for e in receipt["files"]:
        if e["class"] == "K0" and not consumer_run_problems(e["path"], e.get("consumer_run")):
            return e["path"], copy.deepcopy(e["consumer_run"])
    raise AssertionError("無可用之綠 K0 消費紀錄")


def test_mutation_consumer_wrong_nodeid_caught():
    """審查 r2 mutant：執行紀錄之某 nodeid 換成契約外之 nodeid（計數不變）⇒ consumer_nodeids_mismatch。"""
    rel, run = _a_green_k0_run()
    first = sorted(run["executed"])[0]
    run["executed"]["tests/feature_engineering/test_not_a_consumer.py::test_x"] = run["executed"].pop(first)
    assert f"consumer_nodeids_mismatch:{rel}" in consumer_run_problems(rel, run)


def test_mutation_consumer_empty_nodeids_caught():
    rel, run = _a_green_k0_run()
    run["executed"] = {}
    bad = consumer_run_problems(rel, run)
    assert f"consumer_nodeids_empty:{rel}" in bad and f"consumer_nodeids_mismatch:{rel}" in bad


def test_mutation_consumer_missing_nodeid_caught():
    """審查 r2 mutant：少跑一條契約 consumer（計數同步減少）⇒ consumer_nodeids_mismatch。"""
    rel, run = _a_green_k0_run()
    expected = _collect(DISP[rel]["consumers"])
    run["executed"].pop(sorted(run["executed"])[0])
    run["passed"] -= 1
    run["total"] -= 1
    assert f"consumer_nodeids_mismatch:{rel}" in consumer_run_problems(rel, run, expected) or \
        f"consumer_nodeids_empty:{rel}" in consumer_run_problems(rel, run, expected)


def test_receipt_every_consumer_green():
    assert receipt_consumer_problems(_receipt()) == []


def test_mutation_receipt_k0_consumer_red_caught():
    """mutant：K0 消費紀錄之一條 nodeid 改為 failed（計數同步）⇒ consumer_red（K0 紅即不得過）。"""
    rel, run = _a_green_k0_run()
    first = sorted(run["executed"])[0]
    run["executed"][first] = "failed"
    run["passed"] -= 1
    run["failed"] += 1
    receipt = copy.deepcopy(_receipt())
    next(e for e in receipt["files"] if e["path"] == rel)["consumer_run"] = run
    assert f"consumer_red:{rel}" in receipt_consumer_problems(receipt)


@pytest.mark.parametrize("rel", _of("INVENTORY"))
def test_inventory_regenerated_and_classified(rel):
    """SPEC v22：函式清冊以產生器重產；收據須記新增／刪除函式與逐一分類（交審碼），且改前檔與現檔差異只在清冊項。"""
    entry = next(e for e in _receipt()["files"] if e["path"] == rel)
    assert entry.get("regenerated") is True
    added = entry.get("added_functions") or {}
    assert all(str(v.get("class", "")).strip() and str(v.get("reason", "")).strip() for v in added.values()), added
    assert entry.get("new_sha256") == _sha((REPO / rel).read_bytes())


def test_spec_contract_receipt_versions_consistent():
    """審查 r1（codex P2-07）：契約 spec_version＝SPEC 檔頭版本；收據 schema 取自契約。"""
    import re

    head = (REPO / "docs" / "FFNAME_SPEC.md").read_text(encoding="utf-8").splitlines()
    version = next(re.search(r"版本：(v\d+)", line).group(1) for line in head[:10] if "版本：" in line)
    assert CONTRACT["spec_version"] == version
    assert REFREEZE["receipt_schema"].endswith(version)


# ================================================================ K0


def k0_problems(rel: str, current: Optional[bytes] = None) -> List[str]:
    old = _blob(rel)
    if old is None:
        return [f"no_blob:{rel}"]
    now = (REPO / rel).read_bytes() if current is None else current
    return [] if now == old else [f"k0_bytes_changed:{rel}"]


@pytest.mark.parametrize("rel", _of("K0"))
def test_k0_byte_identical(rel):
    assert k0_problems(rel) == []


def test_mutation_k0_byte_change_caught():
    rel = _of("K0")[0]
    assert k0_problems(rel, (REPO / rel).read_bytes() + b"\n") == [f"k0_bytes_changed:{rel}"]


# ================================================================ K1


def _rename_compare(old: Any, new: Any, mapping: Mapping[str, str], allowed: List[str], path: str = "") -> List[str]:
    """改前 vs 現檔：鍵與名字串依映射對應、名清單（排序）依映射對應；其餘葉位元組相等。回傳不等之路徑（`/` 連接、
    以改前鍵）。審查 r1：不再整批排除名雜湊欄位——呼叫端逐路徑要求獨立重算證據或契約例外。`allowed` 已不使用（保留簽章）。"""
    if isinstance(old, dict) and isinstance(new, dict):
        renamed = {mapping.get(str(k), str(k)): k for k in old}
        if set(renamed) != set(map(str, new)):
            return [f"{path}:keyset"]
        out: List[str] = []
        for nk, ok in renamed.items():
            child = f"{path}/{ok}" if path else str(ok)
            out += _rename_compare(old[ok], new[nk], mapping, allowed, child)
        return out
    if isinstance(old, list) and isinstance(new, list):
        if len(old) != len(new):
            return [f"{path}:len"]
        if old and all(isinstance(v, str) for v in old):
            return [] if sorted(mapping.get(v, v) for v in old) == sorted(new) else [f"{path}:names"]
        out = []
        for i, (a, b) in enumerate(zip(old, new)):
            out += _rename_compare(a, b, mapping, allowed, f"{path}/{i}" if path else str(i))
        return out
    if isinstance(old, str) and old in mapping:
        return [] if new == mapping[old] else [path]
    return [] if old == new else [path]


def _strings(node: Any) -> List[str]:
    if isinstance(node, dict):
        return [str(k) for k in node] + [s for v in node.values() for s in _strings(v)]
    if isinstance(node, list):
        return [s for v in node for s in _strings(v)]
    return [node] if isinstance(node, str) else []


def _pw_canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def _rename_keys_deep(node: Any, mapping: Mapping[str, str]) -> Any:
    if isinstance(node, dict):
        return {mapping.get(k, k): _rename_keys_deep(v, mapping) for k, v in node.items()}
    if isinstance(node, list):
        return [_rename_keys_deep(v, mapping) for v in node]
    return node


def _independent_hash_checks(rel: str, new: Any, map_doc: Optional[Mapping[str, Any]] = None,
                             old: Any = None) -> tuple:
    """名雜湊之獨立重算（以該 golden 自身函式）：回傳（已證實之路徑集合, 失敗清單）。每條路徑須「改前輸入⇒改前值」
    且「換名後⇒現值」兩者皆成立方列為已證實。"""
    bad: List[str] = []
    ok: set = set()
    mapping = (map_doc or {}).get("mapping") or {}
    if rel.endswith("icfirstalign/worker_counts.json"):
        from scripts import freeze_icfirstalign_baseline as frz

        groups = (map_doc or {}).get("groups_old") or []
        if not groups:
            return ok, ["worker_groups_missing"]
        a = frz._sha(sorted((lay, frz._sha(sorted(cols))) for lay, cols in groups)) == old["worker"]["groups_sha256"]
        b = frz._sha(sorted((lay, frz._sha(sorted(mapping[c] for c in cols))) for lay, cols in groups)) == \
            new["worker"]["groups_sha256"]
        (ok.add("worker/groups_sha256") if a and b else bad.append("worker_groups_sha256"))
    if rel.endswith("ratiounsafe/baseline.json"):
        for key, rec in new.items():
            if isinstance(rec, dict) and "names_sha256" in rec:
                a = _sha("\n".join(sorted(old[key]["names"])).encode("utf-8")) == old[key]["names_sha256"]
                b = _sha("\n".join(sorted(rec["names"])).encode("utf-8")) == rec["names_sha256"]
                (ok.add(f"{key}/names_sha256") if a and b else bad.append(f"names_sha256:{key}"))
    if rel.endswith("icfirstalign/calibration_baseline.json"):
        from momentum.FeatureEngineering.preprocessing.calibration import column_set_digest

        for mode in ("jia", "yi"):
            for setting, packets in new.get(mode, {}).items():
                for tf, packet in packets.items():
                    o = old[mode][setting][tf]
                    hit = [k for k, cols in (("v", sorted(o["values"])),
                                             ("ve", sorted(set(o["values"]) | set(o["empty_columns"]))))
                           if column_set_digest(cols) == o["column_set_digest"]]
                    cols_new = sorted(packet["values"]) if hit[:1] == ["v"] else \
                        sorted(set(packet["values"]) | set(packet["empty_columns"]))
                    if hit and column_set_digest(cols_new) == packet["column_set_digest"]:
                        ok.add(f"{mode}/{setting}/{tf}/column_set_digest")
                    else:
                        bad.append(f"column_set_digest:{mode}/{setting}/{tf}")
    if rel.endswith("probewinsor/baseline.json"):
        # 改前碼錄得之輸入（probewinsor_helpers.record_of 同式）：改前輸入⇒改前值、換名⇒現值
        inputs = json.loads((MAPS_DIR / "probewinsor__baseline.inputs.json").read_text(encoding="utf-8"))
        if inputs.get("source_head") != REFREEZE["pre_change_commit"]:
            return ok, ["pw_inputs_not_pre_change"]
        for cid, inp in inputs["cells"].items():
            o, n = old["cells"][cid], new["cells"][cid]
            late = inp.get("late")
            if late is not None and _sha("\n".join(sorted(late)).encode()) == o["probe_late_sha256"] and \
                    _sha("\n".join(sorted(mapping.get(x, x) for x in late)).encode()) == n["probe_late_sha256"]:
                ok.add(f"cells/{cid}/probe_late_sha256")
            ff = inp.get("first_finite")
            if ff is not None and _sha(_pw_canon(ff).encode()) == o["first_finite_sha256"] and \
                    _sha(_pw_canon(_rename_keys_deep(ff, mapping)).encode()) == n["first_finite_sha256"]:
                ok.add(f"cells/{cid}/first_finite_sha256")
            ss = inp.get("stable_start")
            if ss is not None and _sha(_pw_canon(ss).encode()) == o["stable_start_sha256"] and \
                    _sha(_pw_canon(_rename_keys_deep(ss, mapping)).encode()) == n["stable_start_sha256"]:
                ok.add(f"cells/{cid}/stable_start_sha256")
        # config_hash：鹽差另立，由 test_salt_only_probewinsor_config_hash 以現行碼獨立重算（此處只認該測試之證據）
        salt = json.loads((MAPS_DIR / "salt_proof.json").read_text(encoding="utf-8"))["probewinsor"]
        for cid in new["cells"]:
            proof = salt.get(f"cells/{cid}/config_hash") or {}
            if proof.get("proof") and proof.get("frozen") == old["cells"][cid]["config_hash"] and \
                    proof.get("new_anchor") == new["cells"][cid]["config_hash"]:
                ok.add(f"cells/{cid}/config_hash")
    return ok, bad


def k1_problems(rel: str, new_doc: Any = None, map_doc: Optional[Dict[str, Any]] = None) -> List[str]:
    old_bytes = _blob(rel)
    if old_bytes is None:
        return [f"no_blob:{rel}"]
    map_path = MAPS_DIR / f"{_slug(rel)}.json"
    if map_doc is None:
        if not map_path.is_file():
            return [f"no_map:{rel}"]
        map_doc = json.loads(map_path.read_text(encoding="utf-8"))
    bad: List[str] = []
    if map_doc.get("missing") or map_doc.get("ambiguous"):
        bad.append(f"map_unmapped:{rel}:{len(map_doc.get('missing') or [])}")
    if map_doc.get("golden_sha256") != _sha(old_bytes):
        bad.append(f"map_not_bound_to_pre_change:{rel}")
    mapping = map_doc.get("mapping") or {}
    if sum(1 for k, v in mapping.items() if k != v) <= 0:
        bad.append(f"no_rename:{rel}")
    old = json.loads(old_bytes.decode("utf-8"))
    new = json.loads((REPO / rel).read_text(encoding="utf-8")) if new_doc is None else new_doc
    # 改前檔之全部名皆須有映射（舊名字串出現於改前檔而不在映射 ⇒ 該名未經紀錄器涵蓋）
    names_in_old = {s for s in _strings(old)} & set(mapping)
    if not names_in_old and not map_doc.get("groups_old"):  # 檔內無欄名者（worker_counts）改以名雜湊獨立重算驗
        bad.append(f"map_unrelated:{rel}")
    if map_doc.get("source_head") != REFREEZE["pre_change_commit"]:
        bad.append(f"map_not_from_pre_change_commit:{rel}")  # 審查 r1：映射須出自改前碼態
    name_hash = list(DISP[rel].get("name_hash_fields") or [])
    exceptions = {p for p in (REFREEZE.get("rekey_exceptions") or {}).get(rel, {}) if not p.startswith("_")}
    verified, hash_bad = _independent_hash_checks(rel, new, map_doc, old)
    bad += [f"hash:{rel}:{x}" for x in hash_bad]
    for p in _rename_compare(old, new, mapping, []):
        if p in verified:
            continue  # 名雜湊：改前輸入⇒改前值、換名⇒現值皆已獨立證實
        if p in exceptions:
            bad.append(f"exception_changed:{rel}:{p}")  # 例外欄位須保留改前位元組（不得改值）
            continue
        bad.append(f"value:{rel}:{p}" if not _match(p, name_hash) else f"name_hash_unverified:{rel}:{p}")
    leftovers = sorted({s for s in _strings(new) if s in mapping and mapping[s] != s})
    bad += [f"leftover_old_name:{rel}:{s}" for s in leftovers[:20]]
    return bad


@pytest.mark.parametrize("rel", _of("K1"))
def test_k1_keys_renamed_values_unchanged(rel):
    assert k1_problems(rel) == []


def test_mutation_k1_value_tamper_caught():
    """mutant：換鍵時夾帶一個值變更 ⇒ value:<path>。"""
    rel = "tests/_golden/icfirstalign/l3_default_arm.json"
    new = json.loads((REPO / rel).read_text(encoding="utf-8"))
    first = sorted(new["columns"])[0]
    new["columns"][first] = "0" * 64
    assert any(p.startswith(f"value:{rel}:") for p in k1_problems(rel, new_doc=new))


def test_mutation_k1_unmapped_name_caught():
    """mutant：映射漏一個舊名（紀錄器未涵蓋）⇒ map_unmapped 與鍵集不符。"""
    rel = "tests/_golden/icfirstalign/l3_default_arm.json"
    map_doc = json.loads((MAPS_DIR / f"{_slug(rel)}.json").read_text(encoding="utf-8"))
    victim = sorted(map_doc["mapping"])[0]
    map_doc["mapping"].pop(victim)
    map_doc["missing"] = [victim]
    bad = k1_problems(rel, map_doc=map_doc)
    assert any(b.startswith(f"map_unmapped:{rel}") for b in bad) and any(":keyset" in b for b in bad)


def _probewinsor_reads(path: Path, module: Any) -> set:
    """靜態掃描單一測試檔：`<…baseline…>["cells"][X]` 之讀取解析為 (格 id, 欄位) 集合；X 為字面或參數化清單名，
    其後再以字面欄位取值者記該欄位，整格交出（如 ph.diff 比較全部鍵）者記 "*"。無法解析 ⇒ ("<unresolved>", "*")。"""
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    reads: set = set()
    for fn_node in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        params: Dict[str, List[str]] = {}
        for dec in fn_node.decorator_list:
            if isinstance(dec, ast.Call) and getattr(dec.func, "attr", "") == "parametrize" and len(dec.args) >= 2 \
                    and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[1], ast.Name):
                params[dec.args[0].value] = list(getattr(module, dec.args[1].id))
        for node in ast.walk(fn_node):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Subscript) \
                    and isinstance(node.value.slice, ast.Constant) and node.value.slice.value == "cells" \
                    and "baseline" in ast.unparse(node.value.value):
                key = node.slice
                cells = [key.value] if isinstance(key, ast.Constant) else \
                    (params[key.id] if isinstance(key, ast.Name) and key.id in params else ["<unresolved>"])
                parent = parents.get(node)
                field = parent.slice.value if isinstance(parent, ast.Subscript) and parent.value is node \
                    and isinstance(parent.slice, ast.Constant) else "*"
                reads.update((c, field) for c in cells)
    return reads


def _probewinsor_cells_read_by_tests() -> set:
    """全部讀 probewinsor baseline 之測試檔（經 probewinsor_helpers 或直讀路徑）之 (格, 欄位) 讀取聯集。"""
    import importlib

    proc = subprocess.run(["grep", "-rln", "--include=*.py", "probewinsor/baseline.json\\|probewinsor_helpers", "tests"],
                          cwd=str(REPO), capture_output=True, text=True)
    reads: set = set()
    for rel in sorted(p for p in proc.stdout.split() if "__pycache__" not in p):
        if rel.endswith(("probewinsor_helpers.py", "test_ffname_refreeze.py")):
            continue
        module = importlib.import_module(rel[:-3].replace("/", "."))
        reads |= _probewinsor_reads(REPO / rel, module)
    return reads


def test_probewinsor_rekey_exceptions_unread_by_consumers():
    """審查 r1（codex）：probewinsor 無法以改前輸入重算之名雜湊欄位（契約 rekey_exceptions）——①只限 off.w1 格；
    ②消費測試（test_probewinsor.py）之 baseline 取格靜態掃描不含其格；③其他測試檔不讀 probewinsor baseline。"""
    rel = "tests/_golden/probewinsor/baseline.json"
    exc = {(p.split("/")[1], p.split("/")[2]) for p in REFREEZE["rekey_exceptions"][rel] if not p.startswith("_")}
    assert exc and all(cell.endswith(".off.w1") for cell, _f in exc)
    reads = _probewinsor_cells_read_by_tests()
    assert reads and not any(c == "<unresolved>" for c, _f in reads), sorted(reads)[:5]
    hit = sorted((c, f) for c, f in reads if (c, f) in exc or (f == "*" and any(c == ec for ec, _ in exc)))
    assert hit == [], hit


def test_mutation_k1_stale_name_hash_caught():
    """mutant：probewinsor 一個已重算之名雜湊改回舊命名世代之值（或任意值）⇒ name_hash_unverified（不再整批排除）。"""
    rel = "tests/_golden/probewinsor/baseline.json"
    new = json.loads((REPO / rel).read_text(encoding="utf-8"))
    old = json.loads(_blob(rel).decode("utf-8"))
    cid = "e1h.on.w1"
    new["cells"][cid]["first_finite_sha256"] = old["cells"][cid]["first_finite_sha256"] + "x"
    assert f"name_hash_unverified:{rel}:cells/{cid}/first_finite_sha256" in k1_problems(rel, new_doc=new)


# ================================================================ K3


def _deep_rename_keys(node: Any, renames: Mapping[str, str]) -> Any:
    if isinstance(node, dict):
        return {renames.get(k, k): _deep_rename_keys(v, renames) for k, v in node.items()}
    if isinstance(node, list):
        return [_deep_rename_keys(v, renames) for v in node]
    return node


def k3_problems(rel: str, new_doc: Any = None) -> List[str]:
    old_bytes = _blob(rel)
    if old_bytes is None:
        return [f"no_blob:{rel}"]
    renames = DISP[rel]["k3_renames"]
    old = json.loads(old_bytes.decode("utf-8"))
    new = json.loads((REPO / rel).read_text(encoding="utf-8")) if new_doc is None else new_doc
    if not any(k in renames for k in _strings(old)):
        return [f"k3_rename_absent_in_old:{rel}"]
    return [] if _deep_rename_keys(old, renames) == new else [f"k3_not_exact:{rel}"]


@pytest.mark.parametrize("rel", _of("K3"))
def test_k3_exact_key_renames(rel):
    assert k3_problems(rel) == []


def test_mutation_k3_extra_change_caught():
    rel = _of("K3")[0]
    new = json.loads((REPO / rel).read_text(encoding="utf-8"))
    branch = sorted(new)[0]
    col = sorted(new[branch])[0]
    new[branch][col]["value_sha256"] = "0" * 64
    assert k3_problems(rel, new_doc=new) == [f"k3_not_exact:{rel}"]


# ================================================================ K2


def k2_problems(rel: str, entry: Optional[Dict[str, Any]] = None, new_sidecar: Optional[Dict[str, Any]] = None) -> List[str]:
    """新舊碼 sidecar 依名逐欄比對（獨立重算）；收據自報不符數＝0 且與重算一致；現檔位元組綁定收據。"""
    if entry is None:
        entry = next((e for e in _receipt()["files"] if e["path"] == rel), None)
    if entry is None:
        return [f"missing:{rel}"]
    if entry.get("status") == "pending":
        return [f"pending:{rel}"]
    if "units" in entry:  # failopen（逐單元全窗）、framepath（逐格）：每單元獨立判定
        bad = []
        # 審查 r2（codex P1-01）：單元集合須恰等於契約清單（framepath 全 12 格、failopen 全 6 單元），缺或多即紅
        expected_units = REFREEZE["framepath_cells"] if DISP[rel].get("recipe") == "framepath" else \
            REFREEZE["failopen_units"]
        got_units = [str(u.get("unit")) for u in entry["units"]]
        if sorted(got_units) != sorted(expected_units) or len(set(got_units)) != len(got_units):
            bad.append(f"units_not_contract_set:{rel}:{sorted(set(expected_units) ^ set(got_units))}")
        for unit in entry["units"]:
            bad += [f"{unit.get('unit')}:{b}" for b in _k2_one(rel, unit, None) if not b.startswith("bytes_unbound")]
        if entry.get("new_sha256") != _sha((REPO / rel).read_bytes()):
            bad.append(f"bytes_unbound:{rel}")
        if entry.get("value_hash_mismatch", 1) != 0:
            bad.append(f"receipt_mismatch:{rel}")
        if not any(u.get("decision") == "refrozen" for u in entry["units"]) and \
                entry.get("new_sha256") != _sha(_blob(rel) or b""):
            bad.append(f"bytes_changed_without_refreeze:{rel}")
        return bad
    return _k2_one(rel, entry, new_sidecar)


def _k2_one(rel: str, entry: Dict[str, Any], new_sidecar: Optional[Dict[str, Any]]) -> List[str]:
    bad: List[str] = []
    try:
        old_sc = json.loads((REPO / entry["old_sidecar"]).read_text(encoding="utf-8"))
        new_sc = new_sidecar if new_sidecar is not None else json.loads((REPO / entry["new_sidecar"]).read_text(encoding="utf-8"))
        map_doc = json.loads((REPO / entry["map"]).read_text(encoding="utf-8"))
    except (KeyError, OSError, ValueError) as exc:
        return [f"k2_artifacts_unavailable:{rel}:{exc}"]
    if map_doc.get("missing") or map_doc.get("ambiguous"):
        bad.append(f"map_unmapped:{rel}")
    mapping = map_doc["mapping"]
    if old_sc.get("scalars") != new_sc.get("scalars"):
        bad.append(f"scalars:{rel}")
    old_cols, new_cols = old_sc["columns"], new_sc["columns"]
    if not old_cols:
        bad.append(f"empty_sidecar:{rel}")
    seen = set()
    for old_name, rec in old_cols.items():
        new_name = mapping.get(old_name)
        if new_name is None:
            bad.append(f"unmapped:{rel}:{old_name}")
            continue
        seen.add(new_name)
        if new_cols.get(new_name) != rec:
            bad.append(f"column:{rel}:{old_name}")
    extra = sorted(set(new_cols) - seen)
    bad += [f"extra_not_g6:{rel}:{c}" for c in extra if not is_g6_new_lag(c)]
    g6 = sorted(c for c in extra if is_g6_new_lag(c))
    if g6 != sorted(entry.get("g6_new_lag") or []):
        bad.append(f"g6_list_disagrees:{rel}")
    if g6 and entry.get("g6_shift_verified") is not True:
        bad.append(f"g6_shift_unverified:{rel}")
    if entry.get("value_hash_mismatch", 1) != 0 or bad:
        bad.append(f"receipt_mismatch:{rel}")
    # 審查 r1：改前紀錄須出自契約 pre_change_commit
    if entry.get("old_head") != REFREEZE["pre_change_commit"] or entry.get("old_pre_change_verified") is not True:
        bad.append(f"old_not_pre_change_commit:{rel}")
    # SPEC v22 重凍前提：refrozen ⇔ 改前碼重現改前 golden；不重現 ⇒ 終態 pre_existing_drift（golden 位元組不動）
    decision = entry.get("decision")
    if decision == "refrozen":
        if entry.get("pre_change_reproduced") is not True or entry.get("refrozen") is not True:
            bad.append(f"refrozen_without_premise:{rel}")
    elif decision == "pre_existing_drift":
        if entry.get("pre_change_reproduced") is not False or not str(entry.get("premise_detail") or "").strip():
            bad.append(f"drift_without_evidence:{rel}")
        if entry.get("unit") is None and _sha((REPO / rel).read_bytes()) != _sha(_blob(rel) or b""):
            bad.append(f"drift_but_bytes_changed:{rel}")
    else:
        bad.append(f"decision_invalid:{rel}:{decision}")
    if entry.get("new_sha256") != _sha((REPO / rel).read_bytes()):
        bad.append(f"bytes_unbound:{rel}")
    return bad


@pytest.mark.parametrize("rel", _of("K2"))
def test_k2_sidecar_per_name_equal(rel):
    assert k2_problems(rel) == []


def test_mutation_k2_framepath_missing_cell_caught():
    """審查 r2（codex P1-01）mutant：framepath 收據少一格（其餘格全綠）⇒ units_not_contract_set（不得以部分彙總過關）。"""
    rel = "tests/_golden/framepath/cgsa_fingerprint.json"
    cells = list(REFREEZE["framepath_cells"])
    assert len(cells) == 12
    fake_unit = {"unit": None, "decision": "refrozen", "value_hash_mismatch": 0}
    entry = {"path": rel, "class": "K2", "units": [dict(fake_unit, unit=c) for c in cells[:-1]], "value_hash_mismatch": 0,
             "new_sha256": _sha((REPO / rel).read_bytes())}
    bad = k2_problems(rel, entry)
    assert any(b.startswith(f"units_not_contract_set:{rel}") and cells[-1] in b for b in bad)
    entry["units"].append(dict(fake_unit, unit=cells[-1]))
    assert not any(b.startswith(f"units_not_contract_set:{rel}") for b in k2_problems(rel, entry))


def test_mutation_k2_drift_claim_with_mismatch_caught():
    """mutant：收據宣稱 pre_existing_drift 卻有依名不符（或缺改前不重現證據）⇒ 拒收。"""
    entry = next(e for e in _receipt()["files"] if e["class"] == "K2" and e.get("decision") == "pre_existing_drift")
    tampered = copy.deepcopy(entry)
    tampered["pre_change_reproduced"] = True
    assert f"drift_without_evidence:{entry['path']}" in k2_problems(entry["path"], tampered)
    tampered = copy.deepcopy(entry)
    tampered["old_head"] = "0" * 40
    assert f"old_not_pre_change_commit:{entry['path']}" in k2_problems(entry["path"], tampered)


def test_mutation_k2_swapped_values_caught():
    """mutant：新碼 sidecar 兩欄值互換（值多重集合不變）⇒ 依名比對必紅（證明不以多重集合代替）。"""
    entry = next(e for e in _receipt()["files"] if e["class"] == "K2" and e.get("new_sidecar"))
    new_sc = json.loads((REPO / entry["new_sidecar"]).read_text(encoding="utf-8"))
    cols = new_sc["columns"]
    names = [n for n in sorted(cols) if cols[n] != cols[sorted(cols)[0]]]
    a, b = sorted(cols)[0], names[0]
    cols[a], cols[b] = cols[b], cols[a]
    assert any(p.startswith(f"column:{entry['path']}:") for p in k2_problems(entry["path"], entry, new_sidecar=new_sc))


# ================================================================ 鹽差


def _hash_with(fn_, strip: bool) -> str:
    import momentum.FeatureEngineering.feature_factory as ff_mod

    real = ff_mod.json.dumps

    def dumps(obj, *a, **k):
        if strip and isinstance(obj, dict) and SALT_KEY in obj:
            obj = {kk: v for kk, v in obj.items() if kk != SALT_KEY}
        return real(obj, *a, **k)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ff_mod.json, "dumps", dumps)
        return fn_()


def test_salt_only_failopen_config_hash():
    """failopen：登記欄位＝現行碼 config hash，去命名世代鹽重算＝改前值（只差 Task 4.1 鹽）。"""
    from momentum.factories import create_feature_factory
    from tests.feature_engineering.test_failopen_correctness import _freeze_baseline_module

    rel = "tests/_golden/failopen/baseline.json"
    frz = _freeze_baseline_module()
    old = json.loads(_blob(rel).decode("utf-8"))
    now = json.loads((REPO / rel).read_text(encoding="utf-8"))
    fac = create_feature_factory(cache_dir=str(frz.KLINE_PATH.parent), validate_continuity=False)
    start, end = frz._window_dates()
    for field in REFREEZE["salt_only_fields"][rel]["fields"]:
        parts = field.split("/")
        if parts[0] == "single_tf":
            payload, primary, sym = frz._fixed_config_payload([parts[2]], parts[2]), parts[2], parts[1]
        else:
            payload, primary, sym = frz._fixed_config_payload(list(frz.TIMEFRAMES), frz.PRIMARY_TIMEFRAME), \
                frz.PRIMARY_TIMEFRAME, parts[1]
        cfg = fac._resolve_config(payload)
        calc = lambda: fac._compute_config_hash(cfg, sym, primary, start_date=start, end_date=end)  # noqa: E731
        node_old, node_now = old, now
        for p in parts:
            node_old, node_now = node_old[p], node_now[p]
        assert _hash_with(calc, strip=True) == node_old, field
        assert _hash_with(calc, strip=False) == node_now, field


def test_salt_only_probewinsor_config_hash():
    """probewinsor 各格：現值＝現行碼 hash（探測鹽之格以不含探測鹽之錨點形）；去命名世代鹽＝改前錨點值。"""
    import tests.feature_engineering.test_probewinsor as tp

    rel = "tests/_golden/probewinsor/baseline.json"
    old = json.loads(_blob(rel).decode("utf-8"))["cells"]
    now = json.loads((REPO / rel).read_text(encoding="utf-8"))["cells"]
    fac = tp._factory()
    import momentum.FeatureEngineering.feature_factory as ff_mod

    real = ff_mod.json.dumps

    def strip_probe(obj, *a, **k):
        if isinstance(obj, dict) and "_probe_l65_gate" in obj:
            obj = {kk: v for kk, v in obj.items() if kk != "_probe_l65_gate"}
        return real(obj, *a, **k)

    for cid in tp._CELLS:
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(ff_mod.json, "dumps", strip_probe)
            anchor_now = tp._hash_of(fac, cid)
        assert now[cid]["config_hash"] == anchor_now, cid
        with pytest.MonkeyPatch.context() as mp:
            def strip_both(obj, *a, **k):
                if isinstance(obj, dict):
                    obj = {kk: v for kk, v in obj.items() if kk not in ("_probe_l65_gate", SALT_KEY)}
                return real(obj, *a, **k)

            mp.setattr(ff_mod.json, "dumps", strip_both)
            assert tp._hash_of(fac, cid) == old[cid]["config_hash"], cid


def test_receipt_salt_entries_agree():
    entries = _receipt()["salt_only"]
    assert entries and all(e.get("proof") is True for e in entries)


# ================================================================ 全量 reference


def full_reference_spec_problems(full: Dict[str, Any]) -> List[str]:
    """審查 r1（codex P1-03）：ETHUSDT、1h＋12h、3 個月窗（收據記實際 start／end，跨度須在契約容差內）。"""
    import pandas as pd

    spec = REFREEZE["full_reference"]
    bad: List[str] = []
    if full.get("symbol") != spec["symbol"]:
        bad.append("symbol")
    if sorted(full.get("timeframes") or []) != sorted(spec["timeframes"]):
        bad.append("timeframes")
    window = full.get("window") or [None, None]
    if not all(window):
        bad.append("window_missing")
    else:
        days = (pd.Timestamp(window[1]) - pd.Timestamp(window[0])).days
        lo, hi = spec["window_tolerance_days"]
        if not lo <= days <= hi:
            bad.append(f"window_span:{days}")
    return bad


def test_full_reference_spec_enforced():
    assert full_reference_spec_problems(_receipt()["full_reference"]) == []


def test_mutation_full_reference_wrong_symbol_or_window_caught():
    full = copy.deepcopy(_receipt()["full_reference"])
    full["symbol"] = "BTCUSDT"
    full["window"] = [None, None]
    assert {"symbol", "window_missing"} <= set(full_reference_spec_problems(full))


def test_full_reference_parse_roundtrip_100pct():
    full = _receipt()["full_reference"]
    assert sorted(full["timeframes"]) == sorted(REFREEZE["full_reference"]["timeframes"])
    assert full["total_columns"] > 0
    assert full["parse_failures"] == 0 and full["roundtrip_failures"] == 0
    assert full["feature_naming_version"] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_full_reference_columns_recomputed():
    """收據之全量 reference 欄名清單由本測試重算往返（自報之失敗數只作交叉比對）。"""
    full = _receipt()["full_reference"]
    columns = full["columns"]
    failures = [c for c in columns if fn.format_feature_name(fn.parse_feature_name(c)) != c]
    assert len(columns) == full["total_columns"] > 0
    assert failures == [] and full["parse_failures"] == len(failures)


# ================================================================ 基準錨


def test_baseline_oracle_is_anchored_and_immutable():
    """baseline.json 須等於 Task 0.1 錨定之 sha（baseline.sha256 只有 1 筆提交）。"""
    assert baseline_immutability_problems() == []


def test_mutation_receipt_claim_cannot_override_recomputation():
    """mutant：收據把 K2 不符自報為 0、K1 改前檔被改值 ⇒ 判定仍依獨立重算（K1 value 違規不受收據影響）。"""
    rel = "tests/_golden/icfirstalign/l3_default_arm.json"
    new = json.loads((REPO / rel).read_text(encoding="utf-8"))
    tampered = copy.deepcopy(new)
    tampered["column_count"] = int(tampered.get("column_count", 0)) + 1
    assert any(p.startswith(f"value:{rel}:") for p in k1_problems(rel, new_doc=tampered))
