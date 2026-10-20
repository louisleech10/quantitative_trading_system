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
        if not bytes_bound(rel, entry.get("new_sha256")):
            bad.append(f"bytes_unbound:{rel}")
        if entry.get("value_hash_mismatch", 1) != 0:
            bad.append(f"receipt_mismatch:{rel}")
        if DISP[rel].get("recipe") == "failopen":  # 單元級 K0（主控 2026-10-19 裁定）：獨立重算＋收據一致
            bad += failopen_k0_problems(rel)
            claimed = sorted((u.get("unit"), u.get("unchanged")) for u in entry.get("k0_units") or [])
            if claimed != sorted((u, True) for u in REFREEZE.get("failopen_units_k0") or []):
                bad.append(f"k0_receipt_disagrees:{rel}")
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
    refused_cell = (entry.get("unit") is not None and DISP[rel].get("recipe") == "framepath" and not old_cols
                    and not new_cols and old_sc.get("scalars") == new_sc.get("scalars"))
    if not old_cols and not refused_cell:  # framepath 拒跑格（如 C9）兩側皆無欄且名無關項相等 ⇒ 允許
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
    bad += [f"extra_not_g6:{rel}:{c}" for c in extra if not is_g6_new_lag(_tagged_key(c))]
    g6 = sorted(c for c in extra if is_g6_new_lag(_tagged_key(c)))
    if g6 != sorted(entry.get("g6_new_lag") or []):
        bad.append(f"g6_list_disagrees:{rel}")
    if g6 and entry.get("g6_shift_verified") is not True:
        bad.append(f"g6_shift_unverified:{rel}")
    if str(entry.get("unit") or "").endswith("/multi") and DISP[rel].get("recipe") == "failopen":
        bad += [f"{p}:{rel}" for p in _probe_equivalence_problems(entry.get("probe_equivalence"))]
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
    if not bytes_bound(rel, entry.get("new_sha256")):
        bad.append(f"bytes_unbound:{rel}")
    return bad


# ---------------------------------------------------------------- FFDSTAR／PRE-PROV 後繼結構重凍（docs/FFDSTAR_SPEC.md §G 證法）

PREPROV_RECEIPT = REPO / "tests" / "_golden" / "preprov" / "refreeze_receipt.json"
#: §G 剝除之 manifest artifact 節點新鍵；failopen 快照中位元組含時間戳之 manifest 檔名
PREPROV_KEYS = ("content_sha256", "provenance")
PREPROV_MANIFEST_BASENAMES = frozenset({"feature_manifest.json", "manifest.json"})


def bytes_bound(rel: str, bound_sha: Optional[str]) -> bool:
    """現檔位元組綁定 FF-NAME 收據：sha256＝收據 `new_sha256`，或其唯一後繼為 PRE-PROV 結構重凍（`preprov_followon_problems`
    為空）。值項之比對（K2 sidecar 依名逐欄）不因此放寬。"""
    return _sha((REPO / rel).read_bytes()) == bound_sha or preprov_followon_problems(rel, bound_sha) == []


def _preprov_aggregate(files: List[Dict[str, Any]]) -> str:
    """failopen 產物清單之 aggregate（獨立重算；同凍結檔之定義：sort_keys、(",", ":")、ensure_ascii）。"""
    blob = json.dumps(files, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return _sha(blob)


def _preprov_structural_problems(rel: str, old: Dict[str, Any], new: Dict[str, Any],
                                 items: List[Dict[str, Any]]) -> List[str]:
    """舊（FF-NAME 綁定之位元組）→ 新（現檔）之差異只在 PRE-PROV 結構欄，且每處改動恰為收據該項之 frozen_before → new_value。
    framepath：只各格 `fingerprint.manifest_sha256`；failopen：只收據列名單元之 `artifacts`，且新清單＝舊清單＋`provenance/`
    項，共有項中非 manifest 檔之 size／sha256 不變，新 aggregate 依清單獨立重算相符。"""
    recipe = DISP.get(rel, {}).get("recipe")
    by_item = {str(i.get("item")): i for i in items}
    o, n = copy.deepcopy(old), copy.deepcopy(new)
    bad: List[str] = []
    if recipe == "framepath":
        for doc in (o, n):
            for node in (doc.get("cells") or {}).values():
                (node.get("fingerprint") or {}).pop("manifest_sha256", None)
        for cell, node in (new.get("cells") or {}).items():
            before = (((old.get("cells") or {}).get(cell) or {}).get("fingerprint") or {}).get("manifest_sha256")
            after = (node.get("fingerprint") or {}).get("manifest_sha256")
            item = by_item.get(cell) or {}
            if before != after and (item.get("frozen_before"), item.get("stripped_recomputed"),
                                    item.get("new_value")) != (before, before, after):
                bad.append(f"preprov_unjustified:{cell}")
    elif recipe == "failopen":
        for unit, item in by_item.items():
            symbol = unit.split("/")[0]
            for doc in (o, n):
                ((doc.get("multi_tf") or {}).get(symbol) or {}).pop("artifacts", None)
            oa = ((old.get("multi_tf") or {}).get(symbol) or {}).get("artifacts") or {}
            na = ((new.get("multi_tf") or {}).get(symbol) or {}).get("artifacts") or {}
            summary = lambda a: {"file_count": a.get("file_count"), "aggregate_sha256": a.get("aggregate_sha256")}  # noqa: E731
            if summary(oa) != item.get("frozen_before") or summary(na) != item.get("new_value"):
                bad.append(f"preprov_unjustified:{unit}")
            files = na.get("files") or []
            if na.get("file_count") != len(files) or na.get("aggregate_sha256") != _preprov_aggregate(files):
                bad.append(f"preprov_aggregate_inconsistent:{unit}")
            ow = {(e.get("root"), e["path"]): e for e in oa.get("files") or []}
            nw = {(e.get("root"), e["path"]): e for e in files}
            if set(ow) - set(nw):
                bad.append(f"preprov_files_removed:{unit}")
            if any(Path(p).parts[:1] != ("provenance",) for _r, p in set(nw) - set(ow)):
                bad.append(f"preprov_non_provenance_added:{unit}")
            if any((ow[k].get("size"), ow[k].get("sha256")) != (nw[k].get("size"), nw[k].get("sha256"))
                   for k in set(ow) & set(nw) if Path(k[1]).name not in PREPROV_MANIFEST_BASENAMES):
                bad.append(f"preprov_data_bytes_changed:{unit}")
    else:
        return [f"preprov_not_affected:{rel}"]
    if o != n:
        bad.append(f"preprov_non_structural_change:{rel}")
    return bad


def _preprov_diff_path_ok(recipe: Optional[str], path: str) -> bool:
    if recipe == "framepath":
        segs = path.split("#", 1)[-1].split(".")
        return "#" in path and len(segs) == 3 and segs[0] == "artifacts" and segs[2] in PREPROV_KEYS
    parts = Path(path).parts
    return len(parts) >= 2 and (parts[1] == "provenance" or parts[-1] in PREPROV_MANIFEST_BASENAMES)


def preprov_followon_problems(rel: str, bound_sha: Optional[str], *, receipt: Optional[Dict[str, Any]] = None,
                              current: Optional[bytes] = None, base: Optional[bytes] = None) -> List[str]:
    """FFDSTAR／PRE-PROV §G：現檔不等於 FF-NAME 綁定位元組時，唯一可接受之來由＝PRE-PROV 結構重凍收據
    （`tests/_golden/preprov/refreeze_receipt.json`）該檔段：已寫入、exit_code 0、`sha256_before`＝FF-NAME 綁定、
    `sha256_after`＝現檔、`base_commit` 之該檔 sha256＝`sha256_before`；每項 equal（剝除後＝凍結值）、差異路徑只在新鍵／
    `provenance/`；且獨立比對舊新兩版，改動只在結構欄、恰為收據所列（`_preprov_structural_problems`）。
    `receipt`／`current`／`base` 供變異測試注入，預設讀收據、現檔與 `git show <base_commit>:<rel>`。"""
    if receipt is None:
        if not PREPROV_RECEIPT.is_file():
            return ["preprov_receipt_missing"]
        receipt = json.loads(PREPROV_RECEIPT.read_text(encoding="utf-8"))
    section = next((f for f in receipt.get("files") or [] if f.get("path") == rel), None)
    if section is None:
        return [f"preprov_section_missing:{rel}"]
    current = (REPO / rel).read_bytes() if current is None else current
    if base is None:
        proc = subprocess.run(["git", "show", f"{section.get('base_commit')}:{rel}"], cwd=str(REPO), capture_output=True)
        base = proc.stdout if proc.returncode == 0 else b""
    bad: List[str] = []
    if receipt.get("schema_version") != 1:
        bad.append("preprov_schema")
    if section.get("written") is not True or section.get("exit_code") != 0:
        bad.append(f"preprov_not_written:{rel}")
    if not bound_sha or section.get("sha256_before") != bound_sha or _sha(base) != bound_sha:
        bad.append(f"preprov_before_not_ffname_bound:{rel}")
    if section.get("sha256_after") != _sha(current):
        bad.append(f"preprov_after_not_current:{rel}")
    items = section.get("items") or []
    if not items or any(i.get("equal") is not True for i in items):
        bad.append(f"preprov_item_not_equal:{rel}")
    recipe = DISP.get(rel, {}).get("recipe")
    bad += [f"preprov_diff_path:{p}" for i in items for p in i.get("diff_paths") or []
            if not _preprov_diff_path_ok(recipe, str(p))]
    if bad:
        return bad
    return _preprov_structural_problems(rel, json.loads(base.decode("utf-8")), json.loads(current.decode("utf-8")),
                                        items)


def _failopen_node(doc: Dict[str, Any], unit: str) -> Any:
    symbol, _, kind = unit.partition("/")
    if kind == "multi":
        return (doc.get("multi_tf") or {}).get(symbol)
    return ((doc.get("single_tf") or {}).get(symbol) or {}).get(kind)


def failopen_k0_problems(rel: str, doc: Optional[Dict[str, Any]] = None) -> List[str]:
    """契約 failopen_units_k0 之單元：現檔該單元節點（正規 JSON）＝改前碼態 pre_change_commit 之 golden 同節點，且未登記
    unit_commits（未經重凍）。獨立以 git show 讀改前 golden，不信收據。"""
    if doc is None:
        doc = json.loads((REPO / rel).read_text(encoding="utf-8"))
    pre = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{REFREEZE['pre_change_commit']}:{rel}"],
                                    check=True, capture_output=True, text=True).stdout)
    bad = []
    for unit in REFREEZE.get("failopen_units_k0") or []:
        now, before = _failopen_node(doc, unit), _failopen_node(pre, unit)
        if now is None or json.dumps(now, sort_keys=True) != json.dumps(before, sort_keys=True):
            bad.append(f"k0_unit_changed:{unit}")
        if unit in ((doc.get("environment") or {}).get("unit_commits") or {}):
            bad.append(f"k0_unit_refrozen:{unit}")
    return bad


def test_failopen_units_partition_contract():
    """failopen_units（重凍對證）與 failopen_units_k0（單元級 K0）互斥，聯集恰為 golden 之全部單元；K0 須附理由。"""
    rel = "tests/_golden/failopen/baseline.json"
    doc = json.loads((REPO / rel).read_text(encoding="utf-8"))
    all_units = {f"{s}/multi" for s in doc["multi_tf"]} | {f"{s}/{tf}" for s, tfs in doc["single_tf"].items() for tf in tfs}
    k2_units, k0_units = set(REFREEZE["failopen_units"]), set(REFREEZE.get("failopen_units_k0") or [])
    assert not (k2_units & k0_units)
    assert k2_units | k0_units == all_units
    assert len(REFREEZE["failopen_units"]) == len(k2_units)
    if k0_units:
        assert str(REFREEZE.get("failopen_units_k0_reason") or "").strip()


def test_failopen_k0_units_bytes_unchanged():
    assert failopen_k0_problems("tests/_golden/failopen/baseline.json") == []


def test_mutation_failopen_k0_unit_altered_caught():
    """K0 單元節點任一值被改（如重凍寫入）或被登記 unit_commits ⇒ 紅；工具端判定同。"""
    rel = "tests/_golden/failopen/baseline.json"
    doc = json.loads((REPO / rel).read_text(encoding="utf-8"))
    units = REFREEZE.get("failopen_units_k0") or []
    if not units:
        pytest.skip("契約無 failopen_units_k0")
    tool = _refreeze_tool()
    for unit in units:
        bad = copy.deepcopy(doc)
        node = _failopen_node(bad, unit)
        node["config_hash"] = "0" * len(str(node.get("config_hash") or "x"))
        assert f"k0_unit_changed:{unit}" in failopen_k0_problems(rel, bad)
        assert not next(u for u in tool.failopen_k0_status(rel, bad) if u["unit"] == unit)["unchanged"]
        bad2 = copy.deepcopy(doc)
        bad2["environment"].setdefault("unit_commits", {})[unit] = "deadbeef"
        assert f"k0_unit_refrozen:{unit}" in failopen_k0_problems(rel, bad2)
        assert not next(u for u in tool.failopen_k0_status(rel, bad2) if u["unit"] == unit)["unchanged"]
    assert all(u["unchanged"] for u in tool.failopen_k0_status(rel, doc))


def _consumer_reruns() -> List[Any]:
    doc = json.loads((REPO / "handoffs/run_receipts/ffname_refreeze_consumers.json").read_text(encoding="utf-8"))
    return [(rel, run) for rel, run in doc.items() if isinstance(run, dict) and run.get("rerun")]


def test_consumer_rerun_merge_provenance_and_state():
    """補跑合併（consumers --rerun-nodeids --merge）：狀態閘於收據所錄之證據上重判為空；逐 nodeid 出處涵蓋執行集合恰一次，
    補跑 nodeid 出自補跑 log 目錄、其餘出自先前 log 目錄；補跑之 nodeid 皆在其所屬測試檔內；HEAD 自先前 run 起未動。"""
    tool = _refreeze_tool()
    for rel, run in _consumer_reruns():
        rr = run["rerun"]
        allowed = sorted({n.split("::", 1)[0] for n in rr["nodeids"]})
        assert tool.rerun_state_problems(rr["state"], allowed) == []
        assert rr["state"]["head_moves_since_prior"] == [] and rr["state"]["head_now"]
        assert set(rr["provenance"]) == set(run["executed"])
        for nodeid, prov in rr["provenance"].items():
            if nodeid in rr["nodeids"]:
                assert prov == {"source": "rerun", "log_dir": rr["log_dir"]}
            else:
                assert prov == {"source": "prior", "log_dir": rr["prior_log_dir"]}
        assert rr["pytest_rc"] == 0


def test_mutation_consumer_rerun_merge_refused():
    """狀態閘變異：生產碼（momentum/ 等）於兩次 run 間變動 ⇒ 拒合併；非補跑 nodeid 所在之測試檔變動 ⇒ 拒；HEAD 移動 ⇒ 拒；
    本工具被消費測試引用時其變動亦拒；收據所錄之真實狀態 ⇒ 不拒。"""
    tool = _refreeze_tool()
    reruns = _consumer_reruns()
    if not reruns:
        pytest.skip("收據無補跑合併")
    for _rel, run in reruns:
        rr = run["rerun"]
        allowed = sorted({n.split("::", 1)[0] for n in rr["nodeids"]})
        state = rr["state"]
        assert tool.rerun_state_problems(state, allowed) == []
        cases = (
            ({**state, "code_changed": list(state["code_changed"]) + ["momentum/FeatureEngineering/feature_factory.py"]},
             "production_changed:momentum/FeatureEngineering/feature_factory.py"),
            ({**state, "code_changed": list(state["code_changed"]) + ["momentum/FeatureEngineering/"]},
             "production_changed:momentum/FeatureEngineering/"),
            ({**state, "tests_changed": list(state["tests_changed"]) + ["tests/feature_engineering/test_failopen_layers.py"]},
             "test_changed:tests/feature_engineering/test_failopen_layers.py"),
            ({**state, "head_moves_since_prior": ["0" * 40]}, "head_moved:"),
            ({**state, "runner_referenced_by": ["tests/feature_engineering/test_failopen_golden.py"],
              "code_changed": ["scripts/ffname_refreeze.py"]}, "production_changed:scripts/ffname_refreeze.py"),
        )
        for bad_state, expect in cases:
            assert any(p.startswith(expect) for p in tool.rerun_state_problems(bad_state, allowed)), expect


_PROBE_VOLATILE = {"created_at", "updated_at"}


def _probe_equivalence_problems(check: Optional[Dict[str, Any]], proof: Optional[Dict[str, Any]] = None) -> List[str]:
    """委員會 r3 (a)：failopen multi 之 ⑥ 位移值取自串流寫出入口之唯讀探針 ⇒ k2 條目須帶探針檢查（本紀錄探針有效、無錯），
    且引用之等價證明須（獨立重判各計數與歸類，不信 equal 自報）：
    主比對（掛 vs 不掛探針，同單元全窗）：unit_record（除 perf）同、逐欄 sidecar 同、資料檔逐檔位元組同；位元組差只准
    `.json` 中介檔且遮罩逐次變動欄（created_at／updated_at／本 run 暫存路徑）後內容相等，被遮罩欄於兩 run 確有不同值；
    對照比對（兩份皆不掛探針）：資料檔與逐欄亦全等，且主比對之 .json 差檔在對照比對中同樣出現（非探針所致）。"""
    if not isinstance(check, dict):
        return ["probe_check_missing"]
    bad: List[str] = []
    if check.get("problems"):
        bad.append("probe_check_problems")
    calls = check.get("probe_calls") or []
    if not calls or any(c.get("errors") for c in calls) or not all(int(c.get("captured", 0)) > 0 for c in calls):
        bad.append("probe_not_effective")
    if proof is None:
        try:
            proof = json.loads((REPO / str(check.get("receipt"))).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return bad + ["probe_proof_unavailable"]
    if proof.get("schema_version") != "ffname-probe-equivalence-v3" or proof.get("problems") or proof.get("equal") is not True:
        bad.append("probe_proof_not_equal")
    main, control = proof.get("main") or {}, proof.get("control") or {}
    for name, part in (("main", main), ("control", control)):
        if part.get("unit_record_differs") or part.get("sidecar_tables_differ") or part.get("data_files_differ") \
                or part.get("json_differ_after_mask"):
            bad.append(f"probe_proof_not_equal:{name}")
        diffs = list(part.get("json_differ_masked_equal") or []) + list(part.get("json_differ_no_mask") or [])
        if any(not str(k).endswith(".json") for k in diffs):
            bad.append(f"probe_proof_data_file_diff:{name}")
        if int(part.get("artifact_files_byte_equal", -1)) + len(diffs) != int(part.get("artifact_files_compared", -2)) \
                or int(part.get("artifact_files_compared", 0)) <= 0 \
                or not (part.get("sidecar_columns_compared") or {}).get("merged_L7"):
            bad.append(f"probe_proof_counts:{name}")
        if part.get("unit") != check.get("proof_unit"):
            bad.append(f"probe_proof_unit:{name}")
    if main.get("json_differ_no_mask"):
        bad.append("probe_proof_main_without_mask")
    if (main.get("a") or {}).get("probe_installed") is not True or (main.get("b") or {}).get("probe_installed") is not False \
            or (control.get("a") or {}).get("probe_installed") is True or (control.get("b") or {}).get("probe_installed") is not False:
        bad.append("probe_proof_flags")
    seen_without_probe = {str(k).split("/", 1)[1] for k in list(control.get("json_differ_masked_equal") or [])
                          + list(control.get("json_differ_no_mask") or []) + list(control.get("json_differ_after_mask") or {})}
    if any(str(k).split("/", 1)[1] not in seen_without_probe for k in main.get("json_differ_masked_equal") or []):
        bad.append("probe_proof_unexplained_diff")
    for k in main.get("json_differ_masked_equal") or []:
        vol = (main.get("volatile_values") or {}).get(k) or {}
        keys = set((vol.get("a") or {})) | set((vol.get("b") or {}))
        if not (keys - {"run_prefix_strings"}) <= _PROBE_VOLATILE:
            bad.append(f"probe_proof_volatile_keys:{k}")
        prefixes = vol.get("run_prefix") or [None, None]
        if (vol.get("a") or {}) == (vol.get("b") or {}) and prefixes[0] == prefixes[1]:
            bad.append(f"probe_proof_masked_without_change:{k}")
    if not (proof.get("with_probe") or {}).get("probe_calls") or proof.get("unit") != check.get("proof_unit"):
        bad.append("probe_proof_unit")
    return bad


def test_mutation_probe_equivalence_tamper_caught():
    """探針等價證明竄改（藏資料檔差、sidecar 差、改計數、把資料檔列為 .json 差、主比對 .json 差在對照中未見、遮罩欄
    無變化、探針未擷取）⇒ 各自紅；收據之真實證明 ⇒ 綠。"""
    entry = next((e for e in _receipt()["files"] if e["path"] == "tests/_golden/failopen/baseline.json"), None)
    units = [u for u in (entry or {}).get("units", []) if str(u.get("unit")).endswith("/multi")]
    if not units or not units[0].get("probe_equivalence"):
        pytest.fail("failopen multi 單元 k2 條目缺 probe_equivalence（委員會 r3 (a) 要求）")
    check = units[0]["probe_equivalence"]
    proof = json.loads((REPO / check["receipt"]).read_text(encoding="utf-8"))
    assert _probe_equivalence_problems(check, proof) == []
    first_json = (proof["main"].get("json_differ_masked_equal") or ["x/none.json"])[0]
    for mutate, expect in (
        (lambda p: p["main"].update(data_files_differ=["x/raw/a.parquet"]), "probe_proof_not_equal:main"),
        (lambda p: p["control"].update(sidecar_tables_differ={"merged_L7": 1}), "probe_proof_not_equal:control"),
        (lambda p: p["main"].update(artifact_files_byte_equal=p["main"]["artifact_files_byte_equal"] - 1),
         "probe_proof_counts:main"),
        (lambda p: p["main"].update(json_differ_masked_equal=p["main"]["json_differ_masked_equal"] + ["x/raw/b.parquet"],
                                    artifact_files_byte_equal=p["main"]["artifact_files_byte_equal"] - 1),
         "probe_proof_data_file_diff:main"),
        (lambda p: p["control"].update(json_differ_masked_equal=[], json_differ_no_mask=[], json_differ_after_mask={}),
         "probe_proof_unexplained_diff"),
        (lambda p: p["main"]["volatile_values"].update({first_json: {"a": {"created_at": ["1"]}, "b": {"created_at": ["1"]},
                                                                     "run_prefix": ["/r", "/r"]}}),
         f"probe_proof_masked_without_change:{first_json}"),
        (lambda p: p["main"]["volatile_values"].update({first_json: {"a": {"groups": ["1"]}, "b": {"groups": ["2"]},
                                                                     "run_prefix": ["/r", "/s"]}}),
         f"probe_proof_volatile_keys:{first_json}"),
        (lambda p: p["main"]["b"].update(probe_installed=True), "probe_proof_flags"),
    ):
        bad_proof = copy.deepcopy(proof)
        mutate(bad_proof)
        assert expect in _probe_equivalence_problems(check, bad_proof)
    assert "probe_not_effective" in _probe_equivalence_problems({**check, "probe_calls": [{"captured": 0, "errors": []}]}, proof)


def _tagged_key(key: str) -> str:
    """framepath 群組鍵 `<group_id>/<未標記欄>` ⇒ 以群組週期標記之欄名；落盤欄名原樣。"""
    if "/" not in key:
        return key
    gid, col = key.split("/", 1)
    return fn.tag_timeframe(col, gid.lstrip("@").split("_", 1)[0])


def _refreeze_tool() -> Any:
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("ffname_refreeze_tool", REPO / "scripts" / "ffname_refreeze.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["ffname_refreeze_tool"] = module
    spec.loader.exec_module(module)
    return module


def test_framepath_group_key_mapping_and_lag_check():
    """framepath persist=False 格（C7）之欄鍵為 `<group_id>/<未標記欄>`：①欄經紀錄器映射（未標記形）、L1 群組 id 依 §G ⑧
    由新欄身分導出、非 L1 群組 id 不變；②⑥ 檢查先以群組週期標記再判（群組鍵不得因 parse 失敗而崩）。"""
    tool = _refreeze_tool()
    assert tool.split_group_key("1h_L1_trend_BBANDS-Lower/close_trend_BBANDS-Lower_13") == \
        ("1h_L1_trend_BBANDS-Lower", "close_trend_BBANDS-Lower_13")
    assert tool.split_group_key("close_1h_trend_EMA_8") == (None, "close_1h_trend_EMA_8")
    assert tool.framepath_new_group_id("1h_L1_trend_BBANDS-Lower", "close_trend_BBANDS-Lower_13") == \
        "1h_L1_trend_BBANDS-Lower"
    assert tool.framepath_new_group_id("12h_L1_pattern_BullishCount_W5", "ohlc_pattern_BullishCount_5") == \
        "12h_L1_pattern_BullishCount"  # ⑧：改前逐窗拆群 ⇒ 改後單一群
    assert tool.framepath_new_group_id("1h_L3_rolling_W13_Kurt_1", "close_trend_EMA_8_Kurt-W13") == "1h_L3_rolling_W13_Kurt_1"
    assert tool.tagged_column_of_key("1h_L4_lag/ohlc_pattern_BullishCount_5_Lag-1") == "ohlc_1h_pattern_BullishCount_5_Lag-1"
    assert tool._lag_shift_ok({}, "1h_L4_lag/ohlc_pattern_BullishCount_5_Lag-1") is None  # ⑥ 新增 lag（群組鍵）
    assert tool._lag_shift_ok({}, "1h_L4_lag/close_trend_EMA_8_Lag-1").startswith("base_not_g6")
    assert tool._lag_shift_ok({}, "1h_L1_trend_EMA/close_trend_EMA_8") == "not_lag"
    # 實跑映射：C7 之每個舊群組鍵 ⇒ 新群組鍵，群組 id 合規則、欄名＝未標記新名
    map_path = MAPS_DIR / "framepath__cgsa_fingerprint__C7.json"
    if map_path.is_file():
        mapping = json.loads(map_path.read_text(encoding="utf-8"))["mapping"]
        comp = {k: v for k, v in mapping.items() if "/" in k}
        assert comp
        for old_key, new_key in comp.items():
            gid, col = old_key.split("/", 1)
            ngid, ncol = new_key.split("/", 1)
            fn.parse_feature_name(ncol, tagged=False)
            assert ngid == tool.framepath_new_group_id(gid, ncol), old_key


def test_failopen_untagged_key_lag_check():
    """failopen registry 之欄為未標記名：①群組鍵 `<gid>/<未標記欄>` 以群組週期標記後判 ⑥（多週期單元各鍵週期取自其群組）；
    ②非群組之未標記鍵只在給定單週期單元週期時標記後判，不給即 unparseable（不猜週期）；③真不能 parse 者 fail-closed。"""
    tool = _refreeze_tool()
    assert tool._lag_shift_ok({}, "12h_L4_lag/ohlc_pattern_BearishCount_13_Lag-1") is None
    assert tool._lag_shift_ok({}, "@12h/ohlc_pattern_BearishCount_13_Lag-1") is None                # failopen 週期鍵
    assert tool.split_group_key("@12h/close_trend_EMA_8") == ("@12h", "close_trend_EMA_8")
    mapped, _miss, _amb = tool.build_key_mapping(
        {"parts": [], "tagged_index": [], "post_ic": []}, [])  # 空集合不崩
    assert mapped == {}
    assert tool._lag_shift_ok({}, "1h_L4_lag/volume_volume_VolumeMA-Ratio_20_Lag-3") is None
    assert tool._lag_shift_ok({}, "ohlc_pattern_BearishCount_13_Lag-1") == "unparseable"          # 未給週期：不猜
    assert tool._lag_shift_ok({}, "ohlc_pattern_BearishCount_13_Lag-1", "12h") is None           # 單週期單元
    assert tool._lag_shift_ok({}, "close_trend_EMA_8_Lag-1", "12h").startswith("base_not_g6")
    assert tool._lag_shift_ok({}, "not a feature name", "12h") == "unparseable"
    assert tool._lag_shift_ok({}, "ohlc_12h_pattern_BearishCount_13_Lag-1") is None              # 已標記形照常
    # k2_compare：多出之未標記 ⑥ 欄於單週期單元判為 g6、於未給週期時判為不符（不偽綠）
    new_cols = {"12h_L1_x/close_trend_EMA_8": {"v": 1}, "ohlc_pattern_BearishCount_13_Lag-1": {"v": 2}}
    mapping = {"12h_L1_x/close_trend_EMA_8": "12h_L1_x/close_trend_EMA_8"}
    old_cols = {"12h_L1_x/close_trend_EMA_8": {"v": 1}}
    assert tool.k2_compare(old_cols, new_cols, mapping, fields=(), unit_tf="12h")["g6_new_lag"] == \
        ["ohlc_pattern_BearishCount_13_Lag-1"]
    assert any("unparseable" in m for m in tool.k2_compare(old_cols, new_cols, mapping, fields=())["mismatches"])


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


def _ffname_bound_bytes(rel: str) -> bytes:
    """FF-NAME 綁定之位元組：PRE-PROV 重凍收據已寫該檔段 ⇒ `git show <base_commit>:<rel>`（重凍前版）；否則現檔。
    變異測試之「舊版」須取此，不得取重凍後之現檔（否則現檔已含紀錄檔項，合成之新版會被誤判為改資料）。"""
    if PREPROV_RECEIPT.is_file():
        receipt = json.loads(PREPROV_RECEIPT.read_text(encoding="utf-8"))
        section = next((f for f in receipt.get("files") or [] if f.get("path") == rel and f.get("written") is True), None)
        if section is not None:
            return subprocess.run(["git", "show", f"{section['base_commit']}:{rel}"], cwd=str(REPO),
                                  capture_output=True, check=True).stdout
    return (REPO / rel).read_bytes()


def _preprov_case(rel: str, mutate: Any, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """以 FF-NAME 綁定之位元組（`_ffname_bound_bytes`）為舊版、`mutate(新版 dict)` 為新版，組 PRE-PROV 收據段（變異測試用）。"""
    base = _ffname_bound_bytes(rel)
    new = json.loads(base.decode("utf-8"))
    mutate(new)
    current = json.dumps(new, indent=1).encode("utf-8")
    section = {"path": rel, "command": "test", "exit_code": 0, "base_commit": "HEAD", "sha256_before": _sha(base),
               "sha256_after": _sha(current), "written": True, "items": items}
    return {"receipt": {"schema_version": 1, "files": [section]}, "current": current, "base": base,
            "bound": _sha(base), "section": section}


def _framepath_preprov_case(extra: Any = None, **item_over: Any) -> Dict[str, Any]:
    rel = "tests/_golden/framepath/cgsa_fingerprint.json"
    old = json.loads(_ffname_bound_bytes(rel).decode("utf-8"))["cells"]["C1"]["fingerprint"]["manifest_sha256"]
    item = {"item": "C1", "frozen_before": old, "stripped_recomputed": old, "equal": True, "new_value": "f" * 64,
            "diff_paths": ["BTCUSDT/1h/h/feature_manifest.json#artifacts.raw.provenance",
                           "BTCUSDT/1h/h/feature_manifest.json#artifacts.raw.content_sha256"]}
    item.update(item_over)

    def mutate(doc: Dict[str, Any]) -> None:
        doc["cells"]["C1"]["fingerprint"]["manifest_sha256"] = "f" * 64
        if extra is not None:
            extra(doc)

    return _preprov_case(rel, mutate, [item])


def _preprov_problems(case: Dict[str, Any], rel: str) -> List[str]:
    return preprov_followon_problems(rel, case["bound"], receipt=case["receipt"], current=case["current"],
                                     base=case["base"])


def test_preprov_followon_framepath_rule():
    """FFDSTAR／PRE-PROV §G：framepath 只改收據核可格之 `manifest_sha256`（frozen_before＝剝除重算＝舊值、new_value＝新值、
    差異路徑只在新鍵）⇒ 接受；其餘任一不符 ⇒ 拒（不放寬值項）。"""
    rel = "tests/_golden/framepath/cgsa_fingerprint.json"
    assert _preprov_problems(_framepath_preprov_case(), rel) == []
    values = lambda d: d["cells"]["C1"]["fingerprint"].__setitem__("row_count", -1)  # noqa: E731
    assert f"preprov_non_structural_change:{rel}" in _preprov_problems(_framepath_preprov_case(values), rel)
    other_cell = lambda d: d["cells"]["C2"]["fingerprint"].__setitem__("manifest_sha256", "e" * 64)  # noqa: E731
    assert "preprov_unjustified:C2" in _preprov_problems(_framepath_preprov_case(other_cell), rel)
    assert f"preprov_item_not_equal:{rel}" in _preprov_problems(_framepath_preprov_case(equal=False), rel)
    assert "preprov_unjustified:C1" in _preprov_problems(_framepath_preprov_case(stripped_recomputed="0" * 64), rel)
    assert "preprov_unjustified:C1" in _preprov_problems(_framepath_preprov_case(new_value="0" * 64), rel)
    bad_path = "BTCUSDT/1h/h/feature_manifest.json#generation_metadata.x"
    assert f"preprov_diff_path:{bad_path}" in _preprov_problems(_framepath_preprov_case(diff_paths=[bad_path]), rel)
    case = _framepath_preprov_case()
    assert f"preprov_before_not_ffname_bound:{rel}" in preprov_followon_problems(
        rel, "0" * 64, receipt=case["receipt"], current=case["current"], base=case["base"])
    case["section"]["written"] = False
    assert f"preprov_not_written:{rel}" in _preprov_problems(case, rel)


def _failopen_preprov_case(extra: Any = None) -> Dict[str, Any]:
    rel = "tests/_golden/failopen/baseline.json"
    old = json.loads(_ffname_bound_bytes(rel).decode("utf-8"))["multi_tf"]["BTCUSDT"]["artifacts"]
    files = copy.deepcopy(old["files"])
    root = next(e["root"] for e in files if e["path"] == "feature_manifest.json")
    for entry in files:
        if entry["path"] == "feature_manifest.json":
            entry["sha256"], entry["size"] = "a" * 64, entry["size"] + 10
    files.append({"root": root, "path": "provenance/raw_columns.parquet", "size": 1, "sha256": "b" * 64})
    files.sort(key=lambda e: (e["root"], e["path"]))
    if extra is not None:
        extra(files)
    new_art = {"files": files, "file_count": len(files), "aggregate_sha256": _preprov_aggregate(files)}
    summary = lambda a: {"file_count": a["file_count"], "aggregate_sha256": a["aggregate_sha256"]}  # noqa: E731
    item = {"item": "BTCUSDT/multi", "comparison": "entrywise", "frozen_before": summary(old),
            "stripped_recomputed": summary(old), "equal": True, "new_value": summary(new_art),
            "diff_paths": [f"{root}/feature_manifest.json", f"{root}/provenance/raw_columns.parquet"]}
    return _preprov_case(rel, lambda d: d["multi_tf"]["BTCUSDT"].__setitem__("artifacts", new_art), [item])


def test_preprov_followon_failopen_rule():
    """FFDSTAR／PRE-PROV §G：failopen BTC multi 產物清單只多 `provenance/` 項、manifest 位元組可變、其餘項 size／sha256 不變
    ⇒ 接受；資料檔位元組變、新增非紀錄檔、刪檔 ⇒ 拒。"""
    rel = "tests/_golden/failopen/baseline.json"
    assert _preprov_problems(_failopen_preprov_case(), rel) == []

    def data_changed(files: List[Dict[str, Any]]) -> None:
        next(e for e in files if e["path"].endswith(".parquet") and "provenance" not in e["path"])["sha256"] = "c" * 64

    assert "preprov_data_bytes_changed:BTCUSDT/multi" in _preprov_problems(_failopen_preprov_case(data_changed), rel)
    added = lambda f: f.append({"root": f[0]["root"], "path": "raw/extra.parquet", "size": 1, "sha256": "d" * 64})  # noqa: E731
    assert "preprov_non_provenance_added:BTCUSDT/multi" in _preprov_problems(_failopen_preprov_case(added), rel)
    removed = lambda f: f.remove(next(e for e in f if e["path"].endswith(".npy")))  # noqa: E731
    assert "preprov_files_removed:BTCUSDT/multi" in _preprov_problems(_failopen_preprov_case(removed), rel)


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
