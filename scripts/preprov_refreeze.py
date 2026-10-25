#!/usr/bin/env python3
"""FFDSTAR／PRE-PROV b4：結構凍結項之重凍（docs/FFDSTAR_SPEC.md §G「結構凍結之重凍」證法、Task 3.1）。

受影響項（盤點 handoffs/run_receipts/20261020-ffdstar-b4-plan.md §1）：
- framepath：`tests/_golden/framepath/cgsa_fingerprint.json` 各格 `fingerprint.manifest_sha256`（落盤之 10 格因 manifest
  artifact 節點新增 `content_sha256`、`provenance` 而變；C7〔registry manifest〕與 C9〔拒絕格〕須不變）。
- failopen：`tests/_golden/failopen/baseline.json` 之 `multi_tf.BTCUSDT.artifacts`（run 目錄新增 `provenance/` 紀錄檔；
  ETHUSDT multi 屬 FF-NAME K0 單元、位元組不得動，不在本工具範圍）。

證法（§G）：於同一次改後之真實 run，把 manifest 各 artifact 節點之 `content_sha256`、`provenance` 與 `provenance/` 路徑
剝除後，依原凍結算法（`scripts/freeze_framepath_baseline.py`、`scripts/freeze_failopen_baseline.py` 之函式，本檔不另寫
雜湊演算法）重算，須等於現行凍結值；相等 ⇒ 才以含新鍵之值重凍，只改寫上列結構欄；不等 ⇒ rc=1、凍結檔不寫、停下歸因。

failopen 之比對域（具名限制）：凍結之 `aggregate_sha256` 含兩個 manifest 檔（run 之 `feature_manifest.json`、registry 之
`manifest.json`）之位元組，其內有生成當下之時間戳（`feature_storage.py` 之 created_at／updated_at、
`column_group_registry.py` 之 created_at），任何重跑（含改前碼）皆不能重現 ⇒ 逐項比：檔案集合（含兩 manifest 之存在）
全等，且 manifest 以外每檔之 size 與 sha256（含 parquet 位元組）全等；manifest 本身之「只多兩新鍵」由 framepath 項
（同一寫入端、比對域剔除時間戳之 canonical sha）證明。

收據：`tests/_golden/preprov/refreeze_receipt.json`（每檔一段：command、exit_code、base_commit、前後檔 sha256、逐項
frozen_before／stripped_recomputed／equal／new_value／diff_paths）。`--check`：重算並比對，不寫任何檔。

NUMVIEW Task 4.2（docs/NUMVIEW_SPEC.md §G 結構凍結；`--profile numview`，CLI 預設）：同一證法，剝除改為 NUMVIEW 之 manifest
新鍵（artifact 節點與頂層之 fingerprint／algorithm_id／路由身分、頂層 observed_arms；鍵名讀契約）——PRE-PROV 之
`content_sha256`／`provenance` 已重凍入現行凍結值，故不再剝除；另 `probewinsor` 項：各格 config_hash 以「去 NUMVIEW 鹽
（契約 `config_hash_salt.key`）依原算法重算＝凍結值」證之（D1；只算 hash、不生成）。收據
`tests/_golden/numview/refreeze_receipt.json`。failopen 不在 NUMVIEW 範圍（新增之 CGSA 葉身分檔屬中繼資料，由該測試之
比對域排除）。`--profile preprov` 為上列原設定（函式預設值即此 profile）。

用法（真實資料重型跑；單行程串行、獨占、不與委員輪並行）：
  PYTHONPATH=. venv/bin/python scripts/preprov_refreeze.py framepath [--check] [--cells C1,C2]   # 約 30 分（12 格）
  PYTHONHASHSEED=0 PYTHONPATH=. venv/bin/python scripts/preprov_refreeze.py failopen --profile preprov [--check]   # 約 36 分
  PYTHONPATH=. venv/bin/python scripts/preprov_refreeze.py probewinsor [--check]   # 秒級（只算 hash）
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA_VERSION = 1
RECEIPT_REL = "tests/_golden/preprov/refreeze_receipt.json"
FRAMEPATH_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
FAILOPEN_REL = "tests/_golden/failopen/baseline.json"
#: §G 剝除之 manifest artifact 節點新鍵（FFDSTAR Task 1.3 ⑦／1.4）
STRIPPED_KEYS: Tuple[str, ...] = ("content_sha256", "provenance")
#: §G 剝除之 manifest 頂層新鍵（PRE-PROV 無；NUMVIEW 見 `activate_numview`）
STRIPPED_ROOT_KEYS: Tuple[str, ...] = ()
#: config_hash 鹽鍵（PRE-PROV 無；NUMVIEW 見 `activate_numview`）
SALT_KEY: Optional[str] = None
#: 剝除之 run 根路徑段（紀錄檔目錄）
PROVENANCE_DIR = "provenance"
#: failopen 受影響單元（ETHUSDT/multi 為 FF-NAME K0，不得動）
FAILOPEN_UNITS: Tuple[str, ...] = ("BTCUSDT/multi",)
#: failopen 快照中位元組含生成時間戳之 manifest 檔名（逐項比對只比存在）
MANIFEST_BASENAMES = frozenset({"feature_manifest.json", "manifest.json"})
FRAMEPATH_FIELD = "manifest_sha256"


class RefreezeError(RuntimeError):
    """前置條件不成立（具名拒寫）。"""


def activate_numview() -> None:
    """NUMVIEW Task 4.2 之剝除設定（鍵名讀契約 `manifest_keys`、`config_hash_salt.key`；收據另寫 NUMVIEW 之檔）。"""
    global RECEIPT_REL, STRIPPED_KEYS, STRIPPED_ROOT_KEYS, SALT_KEY
    contract = json.loads((REPO / "momentum/FeatureEngineering/contracts/numeric_view.json").read_text(encoding="utf-8"))
    keys = contract["manifest_keys"]
    RECEIPT_REL = "tests/_golden/numview/refreeze_receipt.json"
    STRIPPED_KEYS = tuple(keys[r] for r in ("fingerprint", "algorithm_id", "route_identity"))
    STRIPPED_ROOT_KEYS = STRIPPED_KEYS + (keys["observed_arms"],)
    SALT_KEY = str(contract["config_hash_salt"]["key"])


def _framepath_module() -> Any:
    return importlib.import_module("scripts.freeze_framepath_baseline")


def _failopen_module() -> Any:
    return importlib.import_module("scripts.freeze_failopen_baseline")


# ---------------------------------------------------------------------------------------------- 剝除（純函式）

def strip_manifest(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    """manifest 之深拷貝，刪各 artifact 節點之 `STRIPPED_KEYS` 與頂層之 `STRIPPED_ROOT_KEYS`（不存在者略過；其餘鍵原樣）。"""
    out = copy.deepcopy(dict(manifest))
    for key in STRIPPED_ROOT_KEYS:
        out.pop(key, None)
    for node in (out.get("artifacts") or {}).values():
        if isinstance(node, dict):
            for key in STRIPPED_KEYS:
                node.pop(key, None)
    return out


def json_key_diffs(a: Any, b: Any, prefix: str = "") -> List[str]:
    """兩 JSON 值之差異路徑（以 . 串接之物件鍵；一側缺鍵 ⇒ 該鍵路徑；陣列與純量整體比）。"""
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[str] = []
        for key in sorted(set(a) | set(b), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in a or key not in b:
                out.append(path)
            else:
                out += json_key_diffs(a[key], b[key], path)
        return out
    return [] if a == b else [prefix or "<root>"]


def is_structural_manifest_path(path: str) -> bool:
    """manifest 差異路徑（`<檔>#<鍵路徑>`）是否恰為新鍵：`artifacts.<kind>.<STRIPPED_KEYS 之一>` 或頂層之
    `STRIPPED_ROOT_KEYS` 之一（一側缺鍵時差異路徑即該鍵本身）。"""
    key_path = path.split("#", 1)[1] if "#" in path else path
    segs = key_path.split(".")
    if len(segs) == 1:
        return segs[0] in STRIPPED_ROOT_KEYS
    return len(segs) == 3 and segs[0] == "artifacts" and segs[2] in STRIPPED_KEYS


def is_provenance_path(path: str) -> bool:
    return Path(str(path)).parts[:1] == (PROVENANCE_DIR,)


# ---------------------------------------------------------------------------------------------- framepath

def framepath_manifest_values(manifests: Mapping[str, Mapping[str, Any]], domain: Mapping[str, Any]
                              ) -> Tuple[str, str, List[str]]:
    """(剝除後值, 全值, 差異路徑)。兩值皆依原凍結算法：`{run 內相對路徑: filter_manifest(m)}` 之 `_canonical_sha256`
    （同 `freeze_framepath_baseline._fingerprint`）；剝除值先 `strip_manifest` 再篩。差異路徑＝`<檔>#<鍵路徑>`。"""
    fp = _framepath_module()
    full = {rel: fp.filter_manifest(m, domain) for rel, m in manifests.items()}
    stripped = {rel: fp.filter_manifest(strip_manifest(m), domain) for rel, m in manifests.items()}
    diffs = [f"{rel}#{p}" for rel in sorted(manifests) for p in json_key_diffs(stripped[rel], full[rel])]
    return fp._canonical_sha256(stripped), fp._canonical_sha256(full), diffs


def framepath_item(cell: str, frozen_fp: Mapping[str, Any], fresh_fp: Mapping[str, Any],
                   manifests: Optional[Mapping[str, Mapping[str, Any]]], domain: Mapping[str, Any],
                   memory_errors: Sequence[str] = ()) -> Dict[str, Any]:
    """單格之重凍判定。`manifests`＝改後 run 落盤之 feature manifest（鍵＝fingerprint `path_receipt.manifests`）；
    None ⇒ 該格無落盤 feature manifest（C7 registry、C9 拒絕），其值須原樣不變。
    equal ⇔ ①剝除值＝凍結值 ②其餘 fingerprint 項以 `compare_cell` 無差異 ③記憶體閘無錯 ④自盤上重算之全值＝子行程
    fingerprint 之值（確認剝除作用於同一批 manifest）⑤差異路徑皆為新鍵。"""
    fp = _framepath_module()
    frozen = frozen_fp.get(FRAMEPATH_FIELD)
    without = lambda d: {k: v for k, v in d.items() if k != FRAMEPATH_FIELD}  # noqa: E731
    other = list(memory_errors) + list(fp.compare_cell(without(frozen_fp), without(fresh_fp)))
    if manifests is None:
        stripped = full = fresh_fp.get(FRAMEPATH_FIELD)
        diffs: List[str] = []
    else:
        stripped, full, diffs = framepath_manifest_values(manifests, domain)
        if full != fresh_fp.get(FRAMEPATH_FIELD):
            other.append(f"盤上重算之全值 {full} ≠ 子行程 fingerprint {fresh_fp.get(FRAMEPATH_FIELD)}")
    bad_paths = [p for p in diffs if not is_structural_manifest_path(p)]
    other += [f"差異路徑非新鍵：{p}" for p in bad_paths]
    equal = stripped == frozen and not other
    return {"item": cell, "field": f"cells.{cell}.fingerprint.{FRAMEPATH_FIELD}", "frozen_before": frozen,
            "stripped_recomputed": stripped, "equal": equal, "new_value": full, "changed": full != frozen,
            "diff_paths": diffs, "other_diffs": other}


def _cell_manifests(work_root: Path, cell: str, fresh_fp: Mapping[str, Any]) -> Optional[Dict[str, Dict[str, Any]]]:
    keys = list((fresh_fp.get("path_receipt") or {}).get("manifests") or [])
    if not keys or "registry" in keys:
        return None
    root = Path(work_root) / cell / "features"
    return {k: json.loads((root / k).read_text(encoding="utf-8")) for k in keys}


def run_framepath(cells: Sequence[str], frozen_doc: Mapping[str, Any], work_root: Path) -> List[Dict[str, Any]]:
    """逐格（單行程串行）以 `freeze_framepath_baseline.run_cell` 真實生成並判定；每格判定後刪其工作目錄。"""
    fp = _framepath_module()
    domain = fp.load_compare_domain()
    items = []
    for cell in cells:
        out = fp.run_cell(cell, work_root)
        manifests = _cell_manifests(work_root, cell, out["fingerprint"])
        items.append(framepath_item(cell, frozen_doc["cells"][cell]["fingerprint"], out["fingerprint"], manifests,
                                    domain, fp.memory_gate_errors(cell, out["memory"])))
        shutil.rmtree(Path(work_root) / cell, ignore_errors=True)
    return items


def apply_framepath(doc: Dict[str, Any], items: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    out = copy.deepcopy(doc)
    for item in items:
        out["cells"][item["item"]]["fingerprint"][FRAMEPATH_FIELD] = item["new_value"]
    return out


def framepath_dumps(doc: Any) -> str:
    """同 `freeze_framepath_baseline.freeze` 之寫檔格式。"""
    return json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


# ---------------------------------------------------------------------------------------------- failopen

def _entry_key(entry: Mapping[str, Any]) -> str:
    return f"{entry.get('root')}/{entry['path']}" if entry.get("root") is not None else str(entry["path"])


def strip_artifacts(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    """產物清單剔除 `provenance/` 項後，依原算法（`_sha256_json(entries)`）重算 file_count／aggregate_sha256。"""
    fo = _failopen_module()
    entries = [dict(e) for e in artifacts.get("files") or [] if not is_provenance_path(e["path"])]
    return {"files": entries, "file_count": len(entries), "aggregate_sha256": fo._sha256_json(entries)}


def artifact_entry_diffs(want: Mapping[str, Any], got: Mapping[str, Any]) -> List[str]:
    """逐項比對：檔案集合全等；`MANIFEST_BASENAMES` 以外之項 size／sha256 全等（manifest 只比存在，見檔頭）。"""
    w = {_entry_key(e): e for e in want.get("files") or []}
    g = {_entry_key(e): e for e in got.get("files") or []}
    out = [f"缺檔 {k}" for k in sorted(set(w) - set(g))] + [f"多檔 {k}" for k in sorted(set(g) - set(w))]
    for key in sorted(set(w) & set(g)):
        if Path(w[key]["path"]).name in MANIFEST_BASENAMES:
            continue
        if (w[key].get("size"), w[key].get("sha256")) != (g[key].get("size"), g[key].get("sha256")):
            out.append(f"位元組不同 {key}")
    if len(w) != len(want.get("files") or []) or len(g) != len(got.get("files") or []):
        out.append("清單內有重複路徑")
    return out


def _summary(artifacts: Mapping[str, Any]) -> Dict[str, Any]:
    return {"file_count": artifacts.get("file_count"), "aggregate_sha256": artifacts.get("aggregate_sha256")}


#: failopen 單元之值項（同 `test_failopen_correctness._assert_multi_tf_baseline_matches` 所比）
FAILOPEN_VALUE_KEYS: Tuple[Tuple[str, ...], ...] = (("merged_L7", "canonical_sha256"), ("group_set_sha256",),
                                                     ("feature_count",), ("config_hash",))


def _dig(node: Any, path: Sequence[str]) -> Any:
    for key in path:
        node = node.get(key) if isinstance(node, dict) else None
    return node


def failopen_item(unit: str, frozen_record: Mapping[str, Any], fresh_record: Mapping[str, Any]) -> Dict[str, Any]:
    """單元之重凍判定。equal ⇔ ①凍結清單不含 `provenance/` 項（未曾重凍）②剝除後逐項全等（`artifact_entry_diffs`）
    ③值項全等 ④全值相對凍結值之差異只在 `provenance/` 項與 manifest 檔。"""
    frozen, full = frozen_record.get("artifacts") or {}, fresh_record.get("artifacts") or {}
    stripped = strip_artifacts(full)
    other: List[str] = []
    if any(is_provenance_path(e["path"]) for e in frozen.get("files") or []):
        other.append("凍結清單已含 provenance/ 項（已重凍）")
    other += artifact_entry_diffs(frozen, stripped)
    other += [f"值項不同 {'.'.join(p)}" for p in FAILOPEN_VALUE_KEYS if _dig(frozen_record, p) != _dig(fresh_record, p)]
    w = {_entry_key(e): e for e in frozen.get("files") or []}
    g = {_entry_key(e): e for e in full.get("files") or []}
    diffs = sorted([k for k in set(g) - set(w)] + [k for k in set(w) & set(g)
                                                   if (w[k].get("size"), w[k].get("sha256"))
                                                   != (g[k].get("size"), g[k].get("sha256"))])
    other += [f"差異路徑非 provenance／manifest：{k}" for k in diffs
              if not (is_provenance_path(g[k]["path"]) or Path(g[k]["path"]).name in MANIFEST_BASENAMES)]
    return {"item": unit, "field": f"multi_tf.{unit.split('/')[0]}.artifacts", "comparison": "entrywise",
            "frozen_before": _summary(frozen), "stripped_recomputed": _summary(stripped), "equal": not other,
            "new_value": _summary(full), "changed": _summary(full) != _summary(frozen), "diff_paths": diffs,
            "manifest_bytes_unverifiable": sorted(k for k in w if Path(w[k]["path"]).name in MANIFEST_BASENAMES),
            "other_diffs": other, "_artifacts": full}


def run_failopen(units: Sequence[str], frozen_doc: Mapping[str, Any], temp_root: Path) -> List[Dict[str, Any]]:
    """逐單元以 `freeze_failopen_baseline._multi_tf_record` 真實生成並判定（其產物清單經 `_combined_artifact_hashes`）。"""
    fo = _failopen_module()
    fo._require_fixed_environment()
    items = []
    for unit in units:
        symbol = unit.split("/")[0]
        record = fo._multi_tf_record(symbol, temp_root)
        items.append(failopen_item(unit, frozen_doc["multi_tf"][symbol], record))
    return items


def apply_failopen(doc: Dict[str, Any], items: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    out = copy.deepcopy(doc)
    for item in items:
        out["multi_tf"][item["item"].split("/")[0]]["artifacts"] = item["_artifacts"]
    return out


def failopen_dumps(doc: Any) -> str:
    """同 `freeze_failopen_baseline._write_json` 之寫檔格式。"""
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------------------------- probewinsor（NUMVIEW）

PROBEWINSOR_REL = "tests/_golden/probewinsor/baseline.json"
#: probewinsor 錨點形本即不含之鹽（`test_probewinsor._hash_violations`：探測鹽之格 hash ≠ 錨點）
PROBE_SALT_KEY = "_probe_l65_gate"


@contextlib.contextmanager
def config_hash_pairs(extra_strip: Sequence[str] = ()) -> Iterator[Dict[str, str]]:
    """期間每次 `FeatureFactory._compute_config_hash` 記（回傳值 → 去 `SALT_KEY` 依原算法之值）（§G 證法；同 FF-NAME
    之鹽證法：同一 payload 刪鍵後之 json.dumps 重算）。`extra_strip`：凍結值本即不含之鍵，兩值皆先刪；回傳值即此形。"""
    import momentum.FeatureEngineering.feature_factory as ff_mod

    pairs: Dict[str, str] = {}
    real_hash = ff_mod.FeatureFactory._compute_config_hash
    real_dumps = ff_mod.json.dumps

    def stripping(keys: Sequence[str]) -> Any:
        def dumps(obj: Any, *a: Any, **k: Any) -> str:
            if isinstance(obj, dict) and any(key in obj for key in keys):
                obj = {kk: v for kk, v in obj.items() if kk not in keys}
            return real_dumps(obj, *a, **k)
        return dumps

    def spy(self: Any, *a: Any, **k: Any) -> str:
        try:
            ff_mod.json.dumps = stripping(tuple(extra_strip))
            full = real_hash(self, *a, **k)
            ff_mod.json.dumps = stripping(tuple(extra_strip) + (str(SALT_KEY),))
            pairs[full] = real_hash(self, *a, **k)
        finally:
            ff_mod.json.dumps = real_dumps
        return full

    ff_mod.FeatureFactory._compute_config_hash = spy
    try:
        yield pairs
    finally:
        ff_mod.FeatureFactory._compute_config_hash = real_hash


def run_probewinsor(frozen_doc: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """probewinsor 各格之 config_hash（只算 hash、不生成；NUMVIEW profile）：錨點形＝去探測鹽；去 NUMVIEW 鹽之錨點形須＝
    凍結值，新值＝含 NUMVIEW 鹽之錨點形。"""
    if SALT_KEY is None:
        raise RefreezeError("probewinsor 只限 NUMVIEW profile")
    import tests.feature_engineering.test_probewinsor as tp

    factory = tp._factory()
    items = []
    for cid in tp._CELLS:
        with config_hash_pairs(extra_strip=(PROBE_SALT_KEY,)) as pairs:
            full = tp._hash_of(factory, cid)
        frozen = frozen_doc["cells"][cid]["config_hash"]
        stripped = pairs.get(full)
        items.append({"item": cid, "field": f"cells.{cid}.config_hash", "frozen_before": frozen,
                      "stripped_recomputed": stripped, "equal": stripped == frozen, "new_value": full,
                      "changed": full != frozen, "diff_paths": [],
                      "other_diffs": [] if stripped == frozen else [f"去鹽重算 {stripped} ≠ 凍結值 {frozen}"]})
    return items


def apply_probewinsor(doc: Dict[str, Any], items: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    out = copy.deepcopy(doc)
    for item in items:
        out["cells"][item["item"]]["config_hash"] = item["new_value"]
    return out


def probewinsor_dumps(doc: Any) -> str:
    """同 `freeze_probewinsor_baseline` 之寫檔格式。"""
    return json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------------------------- 收據與寫檔

def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(*args: str) -> Tuple[int, bytes]:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    return proc.returncode, proc.stdout


def load_receipt(path: Path) -> Dict[str, Any]:
    if Path(path).is_file():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    if SALT_KEY is not None:
        return {"schema_version": SCHEMA_VERSION, "spec": "docs/NUMVIEW_SPEC.md §G 結構凍結、Task 4.2（沿用 FFDSTAR §G 證法）",
                "stripped_keys": list(STRIPPED_KEYS), "stripped_root_keys": list(STRIPPED_ROOT_KEYS),
                "config_hash_salt_key": SALT_KEY, "files": []}
    return {"schema_version": SCHEMA_VERSION, "spec": "docs/FFDSTAR_SPEC.md §G 證法、Task 3.1",
            "stripped_keys": list(STRIPPED_KEYS), "files": []}


def receipt_section(receipt: Mapping[str, Any], rel: str) -> Optional[Dict[str, Any]]:
    return next((f for f in receipt.get("files") or [] if f.get("path") == rel), None)


def put_section(receipt: Dict[str, Any], section: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(receipt, schema_version=SCHEMA_VERSION)
    out["files"] = [f for f in receipt.get("files") or [] if f.get("path") != section["path"]] + [section]
    out["files"].sort(key=lambda f: f["path"])
    return out


def _public_items(items: Iterable[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: v for k, v in item.items() if not k.startswith("_")} for item in items]


def build_section(rel: str, command: str, items: Sequence[Mapping[str, Any]], *, base_commit: str,
                  sha_before: str, sha_after: str, written: bool) -> Dict[str, Any]:
    ok = bool(items) and all(i["equal"] for i in items)
    return {"path": rel, "command": command, "exit_code": 0 if ok else 1, "base_commit": base_commit,
            "sha256_before": sha_before, "sha256_after": sha_after, "written": written,
            "items": _public_items(items)}


def preflight(rel: str, dumps: Any, receipt: Mapping[str, Any]) -> Tuple[bytes, str]:
    """寫入模式之前置：①凍結檔與 HEAD 版逐位元相同（未提交改動 ⇒ 拒）②既有收據段已寫入且現檔＝其 sha256_after ⇒ 已重凍、拒
    ③以寫檔格式重序列化現檔逐位元相同（保證只改結構欄）。回 (現檔位元組, HEAD sha)。"""
    current = (REPO / rel).read_bytes()
    rc, head = _git("rev-parse", "HEAD")
    rc2, blob = _git("show", f"HEAD:{rel}")
    if rc != 0 or rc2 != 0:
        raise RefreezeError(f"git 取 HEAD 或 HEAD:{rel} 失敗")
    if blob != current:
        raise RefreezeError(f"{rel} 與 HEAD 版不同（有未提交改動），拒寫")
    section = receipt_section(receipt, rel)
    if section and section.get("written") and section.get("sha256_after") == _sha(current):
        raise RefreezeError(f"{rel} 已依收據重凍（sha256_after 相符）；只可 --check")
    if dumps(json.loads(current.decode("utf-8"))).encode("utf-8") != current:
        raise RefreezeError(f"{rel} 以寫檔格式重序列化不逐位元相同，無法保證只改結構欄，拒寫")
    return current, head.decode().strip()


def check_baseline(rel: str, receipt: Mapping[str, Any]) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """--check 之剝除比對基準：收據段已寫入且現檔＝其 sha256_after ⇒ 重凍前版本（`git show <base_commit>:<rel>`，其 sha256
    須＝收據 sha256_before）與該段；否則現檔與 None。"""
    current = (REPO / rel).read_bytes()
    section = receipt_section(receipt, rel)
    if not (section and section.get("written") and section.get("sha256_after") == _sha(current)):
        return json.loads(current.decode("utf-8")), None
    rc, blob = _git("show", f"{section.get('base_commit')}:{rel}")
    if rc != 0 or _sha(blob) != section.get("sha256_before"):
        raise RefreezeError(f"收據 base_commit {section.get('base_commit')} 之 {rel} 不可取或 sha256 ≠ sha256_before")
    return json.loads(blob.decode("utf-8")), section


def check_errors(kind: str, items: Sequence[Mapping[str, Any]], current_doc: Mapping[str, Any],
                 refrozen: bool) -> List[str]:
    """--check 判定：各項 equal（剝除值對重凍前凍結值）；已重凍 ⇒ 另須全值＝現檔之值（failopen 逐項比）。"""
    errs = [f"{i['item']}：剝除後不等於凍結值 {i['other_diffs'][:5]}" for i in items if not i["equal"]]
    if not refrozen:
        return errs
    for item in items:
        name = item["item"]
        if kind == "framepath":
            if item["new_value"] != current_doc["cells"][name]["fingerprint"][FRAMEPATH_FIELD]:
                errs.append(f"{name}：全值 ≠ 現檔")
        elif kind == "probewinsor":
            if item["new_value"] != current_doc["cells"][name]["config_hash"]:
                errs.append(f"{name}：config_hash ≠ 現檔")
        else:
            current = current_doc["multi_tf"][name.split("/")[0]]["artifacts"]
            errs += [f"{name}：{d}" for d in artifact_entry_diffs(current, item["_artifacts"])]
    return errs


def _write_atomic(path: Path, text: str) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def finalize(kind: str, golden_path: Path, rel: str, current: bytes, head: str, items: Sequence[Mapping[str, Any]],
             command: str, receipt: Dict[str, Any], receipt_path: Path) -> int:
    """寫入模式之收尾：全部項 equal ⇒ 只改結構欄後寫凍結檔；任一不等 ⇒ 凍結檔不寫（rc=1）。兩者皆寫收據段
    （exit_code／written 如實）。"""
    ok = bool(items) and all(i["equal"] for i in items)
    sha_before = sha_after = _sha(current)
    if ok:
        doc = json.loads(current.decode("utf-8"))
        new_doc = {"framepath": apply_framepath, "failopen": apply_failopen,
                   "probewinsor": apply_probewinsor}[kind](doc, items)
        text = DUMPS[kind](new_doc)
        _write_atomic(Path(golden_path), text)
        sha_after = _sha(text.encode("utf-8"))
    section = build_section(rel, command, items, base_commit=head, sha_before=sha_before, sha_after=sha_after,
                            written=ok)
    Path(receipt_path).parent.mkdir(parents=True, exist_ok=True)
    _write_atomic(Path(receipt_path), json.dumps(put_section(receipt, section), ensure_ascii=False, indent=1) + "\n")
    return 0 if ok else 1


DUMPS = {"framepath": framepath_dumps, "failopen": failopen_dumps, "probewinsor": probewinsor_dumps}
GOLDEN_REL = {"framepath": FRAMEPATH_REL, "failopen": FAILOPEN_REL, "probewinsor": PROBEWINSOR_REL}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kind", choices=("framepath", "failopen", "probewinsor"))
    ap.add_argument("--profile", choices=("numview", "preprov"), default="numview",
                    help="剝除設定（numview＝NUMVIEW Task 4.2；preprov＝FFDSTAR／PRE-PROV b4，已定案）")
    ap.add_argument("--check", action="store_true", help="重算並比對，不寫任何檔")
    ap.add_argument("--cells", default="", help="framepath 只跑列出之格（逗號分隔；只限 --check）")
    ap.add_argument("--work-root", default="", help="生成工作根（預設系統暫存下新目錄，結束刪除）")
    ap.add_argument("--receipt", default="", help="收據路徑（預設依 profile）")
    args = ap.parse_args(argv)
    if args.profile == "numview":
        if args.kind == "failopen":
            raise RefreezeError("failopen 不在 NUMVIEW 重凍範圍（見檔頭）；PRE-PROV 之重算用 --profile preprov")
        activate_numview()
    args.receipt = args.receipt or str(REPO / RECEIPT_REL)
    command = "scripts/preprov_refreeze.py " + " ".join(argv if argv is not None else sys.argv[1:])
    rel = GOLDEN_REL[args.kind]
    receipt_path = Path(args.receipt)
    receipt = load_receipt(receipt_path)
    fp_cells = list(_framepath_module().CELLS)
    cells = [c.strip() for c in args.cells.split(",") if c.strip()] or fp_cells
    if set(cells) - set(fp_cells):
        raise RefreezeError(f"未知格 {sorted(set(cells) - set(fp_cells))}")
    if args.cells and (not args.check or args.kind != "framepath"):
        raise RefreezeError("--cells 只限 framepath --check（寫入模式須跑全部格）")
    if args.check:
        frozen_doc, section = check_baseline(rel, receipt)
        current, head = (REPO / rel).read_bytes(), ""
    else:
        current, head = preflight(rel, DUMPS[args.kind], receipt)
        frozen_doc, section = json.loads(current.decode("utf-8")), None
    work_root = Path(args.work_root) if args.work_root else Path(tempfile.mkdtemp(prefix="preprov_refreeze_"))
    try:
        if args.kind == "framepath":
            items = run_framepath(cells, frozen_doc, work_root)
        elif args.kind == "probewinsor":
            items = run_probewinsor(frozen_doc)
        else:
            items = run_failopen(FAILOPEN_UNITS, frozen_doc, work_root)
    finally:
        if not args.work_root:
            shutil.rmtree(work_root, ignore_errors=True)
    for item in items:
        print(f"{item['item']}: equal={item['equal']} changed={item['changed']} other={item['other_diffs'][:3]}")
    if args.check:
        errs = check_errors(args.kind, items, json.loads(current.decode("utf-8")), section is not None)
        print(json.dumps({"kind": args.kind, "refrozen": section is not None, "errors": errs}, ensure_ascii=False))
        return 1 if errs else 0
    rc = finalize(args.kind, REPO / rel, rel, current, head, items, command, receipt, receipt_path)
    print(f"preprov_refreeze {args.kind}：{'已重凍' if rc == 0 else '不等，凍結檔未寫'}；收據 {receipt_path}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
