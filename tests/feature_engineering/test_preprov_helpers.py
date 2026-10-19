"""FFDSTAR Task 1.6（docs/FFDSTAR_SPEC.md §G「讀取方式先行」）：測試輔助與凍結腳本改依 manifest 宣告讀取。

受測物：`tests/feature_engineering/preprov_helpers.declared_feature_files`（依 manifest 列群組檔之單一函式）與
`tests/`、`scripts/` 全部掃描型呼叫點之讀法——以清冊 `tests/_golden/preprov/reader_inventory.json`（AST 重掃對證；
CODEX-R5-P2-03）取代手寫三檔清單。真實 kline 短窗 run（同模組同格只生成一次）；run 目錄之竄改一律在 tmp 複本上做。
實作前應為紅；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import ast
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.requires_kline

#: §G 具名之「以檔名掃描 run 目錄取特徵」讀法所在檔（清冊之下限：每檔至少一個 `feature_run` 條目）
SECTION_G_READERS = (
    "scripts/freeze_failopen_baseline.py",
    "scripts/freeze_framepath_baseline.py",
    "tests/feature_engineering/ffstat_helpers.py",
)
#: 掃描點清冊（SPEC Task 1.6 驗證；CODEX-R5-P2-03）
READER_INVENTORY_PATH: Path = ph.GOLDEN_DIR / "reader_inventory.json"
INVENTORY_CLASSES = ("feature_run", "unrelated")
SCAN_ROOTS = ("tests", "scripts")
#: 掃描型呼叫：屬性呼叫 `<任意>.glob(`／`.rglob(`／`.iglob(`／`.iterdir(`；`os.listdir(`／`os.walk(`／`os.scandir(`；
#: 以 `from glob import glob` 等引入之裸名呼叫（SPEC grep `rglob\(|glob\(` 之字面亦命中 `iglob(`；`scandir` 為 `listdir` 之等效）
_ATTR_SCANS = frozenset({"glob", "rglob", "iglob", "iterdir"})
_OS_SCANS = frozenset({"listdir", "walk", "scandir"})
_MODULE_NAME_SCANS = {"glob": frozenset({"glob", "iglob"}), "os": _OS_SCANS}

InventoryKey = Tuple[str, str, str, int]

#: 清冊凍結基準（SPEC Task 1.6；CODEX-R6-P2-02）：本票 TODO 提交之清冊。既有 `feature_run` 條目只准因呼叫點消失
#: （改依 manifest）而離開清冊，不得改標為 `unrelated`。
FROZEN_INVENTORY_COMMIT = "2609aa1f"
FROZEN_INVENTORY_RELPATH = "tests/_golden/preprov/reader_inventory.json"


# ---------------------------------------------------------------------------------------------- 掃描點清冊（AST）

def _tracked_py_files() -> List[str]:
    """`tests/`、`scripts/` 下受版控之 .py（`git ls-files`；相對 repo 根、POSIX 分隔）。"""
    proc = subprocess.run(["git", "ls-files", "-z", "--", *SCAN_ROOTS], cwd=str(ph.REPO), check=True,
                          capture_output=True)
    return sorted(p for p in proc.stdout.decode("utf-8").split("\0") if p.endswith(".py"))


def _scan_targets(tree: ast.AST) -> Dict[str, str]:
    """檔內以 `from glob|os import <掃描函式> [as 別名]` 引入之裸名 → 原函式名。"""
    out: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in _MODULE_NAME_SCANS:
            for alias in node.names:
                if alias.name in _MODULE_NAME_SCANS[node.module]:
                    out[alias.asname or alias.name] = alias.name
    return out


def _is_scan_call(node: ast.Call, bare: Mapping[str, str]) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        if func.attr in _ATTR_SCANS:
            return True
        return func.attr in _OS_SCANS and isinstance(func.value, ast.Name) and func.value.id == "os"
    return isinstance(func, ast.Name) and func.id in bare


def scan_source(rel: str, source: str) -> List[Dict[str, Any]]:
    """單檔 AST 掃描：每個掃描型呼叫一筆 {path, qualname, call, occurrence, line}。

    鍵＝(path, 所屬函式／類別之 qualname〔模組層為 `<module>`〕, `ast.unparse` 之呼叫字面, 同鍵出現序)；行號僅供參考
    （行號漂移不影響鍵）。"""
    tree = ast.parse(source)
    bare = _scan_targets(tree)
    found: List[Tuple[int, int, str, str]] = []

    def walk(node: ast.AST, scope: Tuple[str, ...]) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # 裝飾器、預設值、基底類別於外層作用域求值；本體屬內層 qualname
            header: List[ast.AST] = list(node.decorator_list)
            if isinstance(node, ast.ClassDef):
                header += list(node.bases) + list(node.keywords)
            else:
                header += [node.args] + ([node.returns] if node.returns is not None else [])
            for sub in header:
                walk(sub, scope)
            for stmt in node.body:
                walk(stmt, scope + (node.name,))
            return
        if isinstance(node, ast.Call) and _is_scan_call(node, bare):
            found.append((node.lineno, node.col_offset, ".".join(scope) or "<module>", ast.unparse(node)))
        for child in ast.iter_child_nodes(node):
            walk(child, scope)

    walk(tree, ())
    seen: Dict[Tuple[str, str], int] = {}
    out: List[Dict[str, Any]] = []
    for line, _col, qualname, call in sorted(found):
        occurrence = seen.get((qualname, call), 0)
        seen[(qualname, call)] = occurrence + 1
        out.append({"path": rel, "qualname": qualname, "call": call, "occurrence": occurrence, "line": line})
    return out


def scan_repo() -> List[Dict[str, Any]]:
    """`tests/`、`scripts/` 受版控 .py 之全部掃描型呼叫點。"""
    out: List[Dict[str, Any]] = []
    for rel in _tracked_py_files():
        path = ph.REPO / rel
        if path.is_file():
            out.extend(scan_source(rel, path.read_text(encoding="utf-8")))
    return out


def inventory_key(entry: Mapping[str, Any]) -> InventoryKey:
    return (str(entry["path"]), str(entry["qualname"]), str(entry["call"]), int(entry["occurrence"]))


def load_inventory() -> Dict[str, Any]:
    return json.loads(READER_INVENTORY_PATH.read_text(encoding="utf-8"))


def inventory_completeness_violations(scanned: Sequence[Mapping[str, Any]], inventory: Mapping[str, Any]) -> List[str]:
    """清冊完整性：條目格式（分類∈封閉集、理由非空、鍵唯一）；掃描所得之每個呼叫點皆在清冊；`unrelated` 條目之呼叫點
    仍存在（防清冊陳舊）；§G 具名檔各至少一個 `feature_run` 條目。`feature_run` 條目之呼叫點消失＝已改依 manifest（合法）。"""
    out: List[str] = []
    entries = list(inventory.get("entries") or [])
    keys: Dict[InventoryKey, Mapping[str, Any]] = {}
    for entry in entries:
        key = inventory_key(entry)
        if key in keys:
            out.append(f"清冊鍵重複：{key}")
        keys[key] = entry
        if entry.get("class") not in INVENTORY_CLASSES:
            out.append(f"清冊分類不屬 {INVENTORY_CLASSES}：{key} → {entry.get('class')!r}")
        if not str(entry.get("reason") or "").strip():
            out.append(f"清冊條目無理由：{key}")
    live = {inventory_key(s): s for s in scanned}
    for key in sorted(set(live) - set(keys)):
        out.append(f"清冊外之掃描呼叫點：{key[0]}:{live[key]['line']} {key[1]} {key[2]}")
    for key in sorted(set(keys) - set(live)):
        if keys[key].get("class") == "unrelated":
            out.append(f"清冊陳舊（unrelated 呼叫點已不存在）：{key}")
    for rel in SECTION_G_READERS:
        if not any(k[0] == rel and e.get("class") == "feature_run" for k, e in keys.items()):
            out.append(f"§G 具名檔無 feature_run 條目：{rel}")
    return out


def feature_run_offenders(scanned: Sequence[Mapping[str, Any]], inventory: Mapping[str, Any]) -> Dict[str, List[str]]:
    """Task 1.6：{檔: 仍存在之 `feature_run` 呼叫點}（仍以檔名掃描 run 目錄取特徵；呼叫點消失＝已改依 manifest）。"""
    live = {inventory_key(s): s for s in scanned}
    out: Dict[str, List[str]] = {}
    for entry in inventory.get("entries") or []:
        if entry.get("class") != "feature_run":
            continue
        key = inventory_key(entry)
        hits = out.setdefault(key[0], [])
        if key in live:
            hits.append(f"{live[key]['line']}:{key[1]}:{key[2]}")
    return out


def load_frozen_inventory() -> Dict[str, Any]:
    """凍結基準清冊（`git show <FROZEN_INVENTORY_COMMIT>:<清冊路徑>`；讀 git 物件，不受工作區改動影響）。"""
    proc = subprocess.run(["git", "show", f"{FROZEN_INVENTORY_COMMIT}:{FROZEN_INVENTORY_RELPATH}"], cwd=str(ph.REPO),
                          check=True, capture_output=True)
    return json.loads(proc.stdout.decode("utf-8"))


def frozen_feature_run_violations(frozen: Mapping[str, Any], inventory: Mapping[str, Any],
                                  scanned: Sequence[Mapping[str, Any]]) -> List[str]:
    """凍結規則（不依賴現行清冊之分類標籤自證）：凍結基準中每個 `feature_run` 條目——仍在現行清冊者其分類須仍為
    `feature_run`（改標即紅）；已離開現行清冊者其呼叫點須已自 AST 掃描消失（只准因改依 manifest 而離開）。"""
    current = {inventory_key(e): e for e in inventory.get("entries") or []}
    live = {inventory_key(s) for s in scanned}
    out: List[str] = []
    for entry in frozen.get("entries") or []:
        if entry.get("class") != "feature_run":
            continue
        key = inventory_key(entry)
        if key in current:
            if current[key].get("class") != "feature_run":
                out.append(f"凍結 feature_run 條目被改標為 {current[key].get('class')!r}：{key}")
        elif key in live:
            out.append(f"凍結 feature_run 條目離開清冊而呼叫點仍在：{key}")
    return out


def feature_run_files_not_manifest_driven(inventory: Mapping[str, Any]) -> List[str]:
    """含 `feature_run` 條目之檔中，未改經 `declared_feature_files`／`declared_group_files` 依 manifest 宣告讀取者。"""
    files = sorted({str(e["path"]) for e in inventory.get("entries") or [] if e.get("class") == "feature_run"})
    out: List[str] = []
    for rel in files:
        text = (ph.REPO / rel).read_text(encoding="utf-8") if (ph.REPO / rel).is_file() else ""
        if not ("declared_feature_files" in text or "declared_group_files" in text):
            out.append(rel)
    return out


@pytest.fixture(scope="module")
def runs(tmp_path_factory: pytest.TempPathFactory) -> ph.RunCache:
    return ph.RunCache(tmp_path_factory.mktemp("preprov_helpers"))


def _copy_run(handle: ph.RunHandle, tmp_path: Path) -> Path:
    target = tmp_path / "run_copy"
    shutil.copytree(handle.run_dir, target, symlinks=True)
    return target


def _plant_undeclared(run_dir: Path, artifact_kind: str = "raw") -> Path:
    path = run_dir / artifact_kind / "undeclared_extra.parquet"
    pq.write_table(pa.table({"close_1h_trend_EMA_8": pa.array([1.0, 2.0], type=pa.float32())}), path)
    return path


def rejects_undeclared(listing: Callable[..., List[Path]], run_dir: Path) -> bool:
    """oracle：artifact 目錄下有未宣告 parquet 時，listing 必拋錯（不得把它當特徵檔列出）。"""
    planted = _plant_undeclared(run_dir)
    try:
        files = listing(run_dir, "raw")
    except ValueError:
        return True
    finally:
        planted.unlink(missing_ok=True)
    return planted not in [Path(p) for p in files]


# ---------------------------------------------------------------------------------------------- 驗證

def test_verification_01_declared_listing_matches_artifact_files_on_clean_run(runs: ph.RunCache) -> None:
    """乾淨 run（無非宣告檔）：宣告群組檔集合＝raw 目錄之 parquet 集合；依宣告讀之值指紋與逐檔讀者相同（讀法替換不改值）。"""
    handle = runs.get("h1_stat_off")
    declared = {p.resolve() for p in ph.declared_group_files(handle.run_dir, "raw")}
    on_disk = {p.resolve() for p in (handle.run_dir / "raw").glob("*.parquet")}
    assert declared and declared == on_disk
    fps = ph.value_fingerprints(handle.run_dir, "raw")["columns"]
    direct = {n for p in on_disk for n in pq.read_schema(str(p)).names if n not in ph.NON_FEATURE_COLUMNS}
    assert set(fps) == direct
    row_index = handle.run_dir / ph.row_index_rel(ph.load_manifest(handle.run_dir), "raw")
    assert row_index in ph.declared_feature_files(handle.run_dir, "raw")


def test_verification_02a_reader_inventory_complete() -> None:
    """掃描點清冊 `tests/_golden/preprov/reader_inventory.json` 完整（CODEX-R5-P2-03）：`tests/`、`scripts/` 受版控 .py 之
    全部 `glob(`／`rglob(`／`iglob(`／`iterdir(`／`os.listdir(`／`os.walk(`／`os.scandir(` 呼叫點（AST 重掃）皆在清冊、
    分類∈{feature_run, unrelated} 且附理由；unrelated 條目不陳舊；§G 具名檔各至少一個 feature_run 條目。"""
    scanned = scan_repo()
    assert scanned, "AST 掃描無任何呼叫點 ⇒ 掃描器空轉"
    assert inventory_completeness_violations(scanned, load_inventory()) == []


def test_verification_02_section_g_readers_are_manifest_driven() -> None:
    """清冊中 `feature_run` 類呼叫點不得再存在（不得以檔名掃描 run 目錄取特徵），所在檔改經 `declared_feature_files`／
    `declared_group_files` 依 manifest 宣告讀取（不得以「排除特定檔名」代替）。Task 1.6 實作前為紅。"""
    offenders = feature_run_offenders(scan_repo(), load_inventory())
    assert {k: v for k, v in offenders.items() if v} == {}
    missing = feature_run_files_not_manifest_driven(load_inventory())
    assert missing == []
    assert any(e.get("class") == "feature_run" for e in load_inventory()["entries"]), "清冊無 feature_run 條目 ⇒ 空轉"


def test_verification_02b_frozen_feature_run_entries_not_relabelled() -> None:
    """凍結基準（CODEX-R6-P2-02）：以 `2609aa1f` 之清冊為基準，其每個 `feature_run` 條目仍在現行清冊者分類仍為
    `feature_run`；離開清冊者其呼叫點已不存在（只准因改依 manifest 而離開）。新條目之分類由審碼審，不在此判。"""
    frozen = load_frozen_inventory()
    assert any(e.get("class") == "feature_run" for e in frozen["entries"]), "凍結基準無 feature_run 條目 ⇒ 空轉"
    assert frozen_feature_run_violations(frozen, load_inventory(), scan_repo()) == []


def test_verification_03_undeclared_or_missing_files_raise(runs: ph.RunCache, tmp_path: Path) -> None:
    """未宣告 parquet 出現於 artifact 目錄 ⇒ ValueError；宣告檔缺 ⇒ FileNotFoundError（皆不靜默）。"""
    run_dir = _copy_run(runs.get("h1_stat_off"), tmp_path)
    assert rejects_undeclared(ph.declared_feature_files, run_dir)
    victim = ph.declared_group_files(run_dir, "raw")[0]
    victim.unlink()
    with pytest.raises(FileNotFoundError):
        ph.declared_feature_files(run_dir, "raw")


def test_verification_04_helpers_independent_of_run_provenance() -> None:
    """獨立 oracle 不得呼叫受測物：`preprov_helpers` 不 import `run_provenance`；`independent_content_sha256`
    之組成欄位與契約 `content_sha256.entry_fields` 一致（契約變更須同步改獨立實作）。"""
    tree = ast.parse((ph.REPO / "tests/feature_engineering/preprov_helpers.py").read_text(encoding="utf-8"))
    imported = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
    assert not [m for m in imported if "run_provenance" in m]
    assert ph.contract()["content_sha256"]["entry_fields"] == ["relative_path", "columns", "row_count", "dtype",
                                                                "file_sha256"]


# ---------------------------------------------------------------------------------------------- 邊界

def test_boundary_01_processed_groups_and_processed_timestamps(runs: ph.RunCache) -> None:
    """邊界①：processed artifact 之群組與 `processed_timestamps.parquet` 皆由宣告列出。"""
    handle = runs.get("ic_first")
    manifest = ph.load_manifest(handle.run_dir)
    node = manifest["artifacts"]["processed"]
    expected = [handle.run_dir / g["path"] for g in node["groups"].values()]
    expected.append(handle.run_dir / node["row_index"]["path"])
    listed = ph.declared_feature_files(handle.run_dir, "processed")
    assert listed == expected
    assert (handle.run_dir / "processed_timestamps.parquet") in listed
    assert len(listed) >= 2


def test_boundary_02_ic_first_raw_deleted(runs: ph.RunCache) -> None:
    """邊界②：IC-first 已刪 raw 之 run——processed 照常列出；raw 之宣告檔不存在 ⇒ FileNotFoundError（不靜默回空）。"""
    handle = runs.get("ic_first")
    assert not (handle.run_dir / "raw").exists()
    assert ph.declared_feature_files(handle.run_dir, "processed")
    with pytest.raises(FileNotFoundError):
        ph.declared_feature_files(handle.run_dir, "raw")
    with pytest.raises(FileNotFoundError):
        ph.independent_content_sha256(handle.run_dir, "raw")


def test_boundary_03_multi_tf_groups(runs: ph.RunCache) -> None:
    """邊界③：多週期 run 之群組——宣告群組檔之欄涵蓋兩個週期之標記（1h、12h），與 raw 目錄 parquet 集合相同。"""
    from momentum.FeatureEngineering.feature_naming import strip_timeframe_tag

    handle = runs.get("h12h1_multi")
    names = ph.group_columns(handle.run_dir, "raw")
    tags = {n.split("_")[1] for n in names if strip_timeframe_tag(n) != n}
    assert {"1h", "12h"} <= tags
    declared = {p.resolve() for p in ph.declared_group_files(handle.run_dir, "raw")}
    assert declared == {p.resolve() for p in (handle.run_dir / "raw").glob("*.parquet")}


# ---------------------------------------------------------------------------------------------- mutation

def test_mutation_rglob_listing_accepts_undeclared_parquet(runs: ph.RunCache, monkeypatch: pytest.MonkeyPatch,
                                                            tmp_path: Path) -> None:
    """mutation（SPEC Task 1.6）：輔助函式改回 `rglob("*.parquet")` 且 run 目錄放入一個非宣告 parquet ⇒ 本檔 oracle 轉紅。"""
    run_dir = _copy_run(runs.get("h1_stat_off"), tmp_path)
    assert rejects_undeclared(ph.declared_feature_files, run_dir)

    def rglob_listing(run_dir: Path, artifact_kind: str = "raw") -> List[Path]:
        return sorted(Path(run_dir).rglob("*.parquet"))

    monkeypatch.setattr(ph, "declared_feature_files", rglob_listing)
    assert not rejects_undeclared(ph.declared_feature_files, run_dir)


def test_mutation_inventory_missing_feature_run_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.6；CODEX-R5-P2-03）：清冊載入點改回刪去一個 `feature_run` 條目之複本 ⇒ 完整性 oracle 轉紅，且紅因
    為該呼叫點成為「清冊外之掃描呼叫點」。該呼叫點若已因 Task 1.6 改寫而消失，以其鍵模擬仍存在（oracle 對任何活呼叫點皆須擋）。"""
    inventory = load_inventory()
    scanned = scan_repo()
    victim = next(e for e in inventory["entries"] if e["class"] == "feature_run")
    key = inventory_key(victim)
    if key not in {inventory_key(s) for s in scanned}:
        scanned = list(scanned) + [{k: victim[k] for k in ("path", "qualname", "call", "occurrence", "line")}]
    baseline = inventory_completeness_violations(scanned, inventory)
    mutant = copy.deepcopy(inventory)
    mutant["entries"] = [e for e in mutant["entries"] if inventory_key(e) != key]
    monkeypatch.setattr(sys.modules[__name__], "load_inventory", lambda: mutant)
    caught = [v for v in inventory_completeness_violations(scanned, load_inventory()) if v not in baseline]
    assert any(v.startswith("清冊外之掃描呼叫點") and key[2] in v for v in caught), caught


def test_mutation_scanner_detects_planted_call_site(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation：掃描結果改為多一個清冊外之檔（植入呼叫點）⇒ 完整性 oracle 轉紅；並驗掃描器對屬性／`os.`／裸名引入
    三種寫法皆命中（防掃描器漏型）。"""
    source = ("import os\nfrom glob import glob as g\nfrom pathlib import Path\n\n"
              "def planted(run_dir):\n    a = sorted(Path(run_dir).rglob('*.parquet'))\n"
              "    b = os.listdir(run_dir)\n    c = [p for p in Path(run_dir).iterdir()]\n"
              "    d = g(str(run_dir) + '/*')\n    e = list(os.walk(run_dir))\n    return a, b, c, d, e\n")
    planted = scan_source("tests/feature_engineering/_planted_reader.py", source)
    assert [p["call"] for p in planted] == ["Path(run_dir).rglob('*.parquet')", "os.listdir(run_dir)",
                                            "Path(run_dir).iterdir()", "g(str(run_dir) + '/*')", "os.walk(run_dir)"]
    assert all(p["qualname"] == "planted" for p in planted)
    baseline = inventory_completeness_violations(scan_repo(), load_inventory())
    assert not any("_planted_reader.py" in v for v in baseline)
    real_scan = scan_repo
    monkeypatch.setattr(sys.modules[__name__], "scan_repo", lambda: list(real_scan()) + planted)
    violations = [v for v in inventory_completeness_violations(scan_repo(), load_inventory()) if v not in baseline]
    assert sum(v.startswith("清冊外之掃描呼叫點") and "_planted_reader.py" in v for v in violations) == len(planted)


#: CODEX-R6-P2-02 反例之清冊鍵（`scripts/benchmark_l65_v2.py:116` 附近；凍結基準中該檔唯一之 feature_run 條目）
_RELABEL_VICTIM: InventoryKey = ("scripts/benchmark_l65_v2.py", "_streaming_schema_checks",
                                 "features_root.rglob('*.parquet')", 0)


def test_mutation_inventory_feature_run_relabelled_unrelated(monkeypatch: pytest.MonkeyPatch) -> None:
    """mutation（SPEC Task 1.6；CODEX-R6-P2-02）：清冊載入點改回「`scripts/benchmark_l65_v2.py` 之
    `_streaming_schema_checks` rglob 條目改標為 `unrelated`」之複本（呼叫點仍在）⇒ 凍結規則 oracle 轉紅，且紅因為
    「被改標」。反證非空轉：同一 mutant 下既有之 `inventory_completeness_violations` 與
    `feature_run_files_not_manifest_driven` 皆不因此新增違規（該 reader 自兩集合消失＝原攻擊面）。"""
    frozen = load_frozen_inventory()
    victim = next(e for e in frozen["entries"] if inventory_key(e) == _RELABEL_VICTIM)
    assert victim["class"] == "feature_run"
    inventory = load_inventory()
    scanned = list(scan_repo())
    if _RELABEL_VICTIM not in {inventory_key(s) for s in scanned}:  # Task 1.6 改寫後呼叫點已消失：模擬改標者保留呼叫點
        scanned.append({k: victim[k] for k in ("path", "qualname", "call", "occurrence", "line")})
    mutant = copy.deepcopy(inventory)
    entries = [e for e in mutant["entries"] if inventory_key(e) != _RELABEL_VICTIM]
    entries.append(dict(victim, **{"class": "unrelated", "reason": "mutant：改標以避開 feature_run 檢查"}))
    mutant["entries"] = entries
    baseline_frozen = frozen_feature_run_violations(frozen, inventory, scanned)
    baseline_complete = inventory_completeness_violations(scanned, inventory)
    monkeypatch.setattr(sys.modules[__name__], "load_inventory", lambda: copy.deepcopy(mutant))
    caught = [v for v in frozen_feature_run_violations(frozen, load_inventory(), scanned) if v not in baseline_frozen]
    assert any("被改標" in v and _RELABEL_VICTIM[2] in v for v in caught), caught
    assert not [v for v in inventory_completeness_violations(scanned, load_inventory()) if v not in baseline_complete]
    assert _RELABEL_VICTIM[0] not in feature_run_files_not_manifest_driven(load_inventory())
