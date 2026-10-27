"""PRE-PROV（docs/FFDSTAR_SPEC.md Task 2.1）：run 身分物件——IC 自同一次 manifest 解析取得 run 身分。

驗證（SPEC Task 2.1）：
- 身分取值與 manifest 逐鍵相等（鍵集取自契約 `run_identity_keys`，不另列舉）；
- 同一次 `load` 內 manifest 解析次數不因本 Task 增加（計數 monkeypatch `FeatureReader._parse_manifest_file`，
  其為全部 V2 讀取之單一 manifest 解析邊界）；
- 不一致案：讀取完成後 manifest 被替換 ⇒ 身分仍等於本次讀取所據之那一次解析。
- 讀取一致性（b3 審碼 r1 CODEX-R1-P1-01；SPEC Task 2.1 改法）：一次讀取全程只解析一次 manifest；讀取中途 manifest
  （或整個 run 目錄被另一份真實 run）替換 ⇒ `ManifestChangedDuringReadError`，絕不回「A 之身分＋B 之資料」。
邊界：①`config_hash` 未指定（latest 解析後才定身分）；②舊 run（無 `content_sha256` ⇒ `legacy`）。
mutation：身分改取第二次解析之 manifest 且其間 manifest 被替換 ⇒ 不一致案翻轉；拿掉讀取結束之 sha256 確認 ⇒
verification_04 翻轉（回 A 之身分＋B 之資料）。

資料：真實 kline 短窗生成（`preprov_helpers.generate_short_run`，格 `h1_stat_on`，本模組只生成一次）；
「舊 run」與「替換之 manifest」皆以該真實 run 之 manifest 刪鍵／改值得之，不造特徵矩陣。
實作前應為紅：`resolve_run_identity` 為 stub，`FeatureLibrary` 無回傳身分之入口。
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pandas as pd
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader, ManifestChangedDuringReadError
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering import preprov_helpers as ph

# 契約為身分鍵之唯一真相源（SPEC §C）；直接讀 JSON，不經待測之 `load_contract`
CONTRACT: Dict[str, Any] = json.loads(rp.CONTRACT_PATH.read_text(encoding="utf-8"))
IDENTITY_KEYS: List[str] = list(CONTRACT["run_identity_keys"])

# SPEC Task 2.1「`load` 新增回傳身分之入口」未定名；本檔以此名呼叫（回 (DataFrame, RunIdentity)）。
LOAD_WITH_IDENTITY = "load_with_identity"

# 改前碼態（HEAD）一次 `FeatureLibrary.load` 之 manifest 解析次數：load_manifest_v2、list_features_v2、
# load_columns_v2、_attach_row_index→load_row_index_v2 各一次（feature_library.py:149-187、
# feature_reader.py:_resolve_manifest_v2）。本 Task 不得使之增加。
HEAD_PARSES_PER_LOAD = 4
# b3 審碼 r1（SPEC Task 2.1「讀取一致性」）：一次讀取全程只解析一次 manifest。
PARSES_PER_LOAD = 1

CELL = "h1_stat_on"
TAMPERED_SHA = "f" * 64


def expected_identity(manifest: Dict[str, Any], artifact_kind: str) -> Dict[str, Any]:
    """測試端獨立 oracle：自 manifest 原文逐鍵取 run 身分（不經 `resolve_run_identity`）。
    artifact 節點之 `feature_schema_hash` 優先、缺則取 manifest 根；`provenance_sha256`＝節點 `provenance.sha256`。"""
    node = (manifest.get("artifacts") or {}).get(artifact_kind) or {}
    prov = node.get("provenance")
    out = {
        "symbol": manifest.get("symbol"),
        "tf": manifest.get("tf"),
        "config_hash": manifest.get("config_hash"),
        "feature_schema_hash": node.get("feature_schema_hash", manifest.get("feature_schema_hash")),
        "feature_naming_version": manifest.get("feature_naming_version"),
        "artifact_kind": artifact_kind,
        "content_sha256": node.get("content_sha256"),
        "provenance_sha256": prov.get("sha256") if isinstance(prov, dict) else None,
        # NUMVIEW Task 4.2（D2）：artifact 節點之 algorithm_id 與事後路由身分（舊 run 無 ⇒ None）
        "algorithm_id": node.get("algorithm_id"),
        "route_identity": node.get("route_identity"),
    }
    assert set(out) == set(IDENTITY_KEYS), (
        f"契約 run_identity_keys {IDENTITY_KEYS} 與本 oracle 之鍵 {sorted(out)} 不一致——契約改動須同步 oracle"
    )
    return out


def strip_to_legacy(manifest: Dict[str, Any]) -> Dict[str, Any]:
    """舊 run 之 manifest：各 artifact 節點刪本票新鍵（`content_sha256`、`provenance`），其餘原樣（D6）。"""
    legacy = copy.deepcopy(manifest)
    for node in (legacy.get("artifacts") or {}).values():
        if isinstance(node, dict):
            node.pop("content_sha256", None)
            node.pop("provenance", None)
    return legacy


def manifest_path(run: Any) -> Path:
    return Path(run.run_dir) / FeatureReader.V2_MANIFEST_NAME


def read_manifest(run: Any) -> Dict[str, Any]:
    return json.loads(manifest_path(run).read_text(encoding="utf-8"))


def library_for(run: Any) -> FeatureLibrary:
    """以該 run 之隔離特徵根組 FeatureLibrary（registry＝`<root>/registry.json`，同 `registry_for_feature_root`）。"""
    root = Path(run.features_root)
    registry_path = root / "registry.json"
    assert registry_path.is_file(), f"前提不成立：隔離特徵根無 registry（{registry_path}）"
    return FeatureLibrary(FeatureRegistry(registry_path), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))


def load_with_identity(lib: FeatureLibrary, run: Any, *, config_hash: Optional[str] = "__run__") -> Tuple[pd.DataFrame, Any]:
    kwargs = {} if config_hash is None else {"config_hash": run.config_hash if config_hash == "__run__" else config_hash}
    return getattr(lib, LOAD_WITH_IDENTITY)(run.symbol, run.tf, **kwargs)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> Any:
    """真實 kline 短窗之單週期 run（只生成一次）。"""
    return ph.generate_short_run(tmp_path_factory.mktemp("preprov_identity"), CELL)


@pytest.fixture(scope="module")
def run_other(tmp_path_factory: pytest.TempPathFactory, run: Any) -> Any:
    """同設定（同 config_hash）重生、但隔離 kline 副本中改一根 K 線（靠近窗尾）之真實 run（讀取一致性案之「B」）。"""
    root = tmp_path_factory.mktemp("preprov_identity_other")
    axis = FeatureReader(str(run.features_root)).load_row_index_v2(run.symbol, run.tf, run.config_hash)
    assert axis is not None and len(axis) > 5, "前提不成立：run 無時間軸"
    kline = ph.copy_kline_with_one_bar_changed(root / "kline", symbol=run.symbol, tf=run.tf, when=str(axis[-3]))
    return ph.generate_short_run(root, CELL, symbol=run.symbol, kline_path=kline)


@pytest.fixture()
def restore_manifest(run: Any) -> Iterator[Path]:
    """本測試若改寫 manifest，結束時逐位元組還原（模組共用之 run 不受污染）。"""
    path = manifest_path(run)
    original = path.read_bytes()
    try:
        yield path
    finally:
        path.write_bytes(original)


def _install_parse_counter(monkeypatch: pytest.MonkeyPatch, on_parse: Optional[Callable[[Path, int], None]] = None) -> List[Path]:
    """以計數版取代單一 manifest 解析邊界；`on_parse(path, n)` 於第 n 次解析回傳前呼叫（n 從 1 起）。
    （b3 r1：解析邊界增關鍵字 `raw`——讀取端先讀位元組算 sha256 再以同一份位元組解析——計數版原樣轉交。）"""
    real = FeatureReader._parse_manifest_file
    calls: List[Path] = []

    def counting(path: Path, **kwargs: Any) -> dict:
        result = real(path, **kwargs)
        calls.append(Path(path))
        if on_parse is not None:
            on_parse(Path(path), len(calls))
        return result

    monkeypatch.setattr(FeatureReader, "_parse_manifest_file", staticmethod(counting))
    return calls


def _install_after_confirm(monkeypatch: pytest.MonkeyPatch, after: Callable[[], None]) -> None:
    """於讀取結束之單一確認點（`FeatureReader._confirm_manifest_unchanged`）通過**之後**呼叫 `after`（只第一次）。"""
    real = FeatureReader._confirm_manifest_unchanged
    fired: List[bool] = []

    def wrapped(snapshot: Any) -> None:
        real(snapshot)
        if not fired:
            fired.append(True)
            after()

    monkeypatch.setattr(FeatureReader, "_confirm_manifest_unchanged", staticmethod(wrapped))


def _tampered_bytes(path: Path) -> Tuple[Dict[str, Any], bytes]:
    """原 manifest 與只改 raw `content_sha256` 之替換版位元組。"""
    original = json.loads(path.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(original)
    tampered["artifacts"]["raw"]["content_sha256"] = TAMPERED_SHA
    assert original["artifacts"]["raw"].get("content_sha256") != TAMPERED_SHA
    return original, json.dumps(tampered, ensure_ascii=False, indent=2).encode("utf-8")


def _replacement_case(lib: FeatureLibrary, run: Any, path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """不一致案之 oracle 輸入：本次讀取完成（單一確認點通過）後、回傳前，把磁碟上 manifest 換成只改 raw
    `content_sha256` 之版本——之後任何再解析皆讀到替換版。回 {原值, 替換值, 身分取得之值}。
    （b3 r1：讀取**中途**替換改由讀取一致性拒讀，見 `test_identity_replacement_midway_refused`；本案保留「身分不得取自
    讀完後之另一次解析」之判定。）"""
    original = json.loads(path.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(original)
    tampered["artifacts"]["raw"]["content_sha256"] = TAMPERED_SHA
    assert original["artifacts"]["raw"].get("content_sha256") != TAMPERED_SHA

    def swap() -> None:
        path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2), encoding="utf-8")

    _install_after_confirm(monkeypatch, swap)
    _df, identity = load_with_identity(lib, run)
    return {"original": original["artifacts"]["raw"].get("content_sha256"), "tampered": TAMPERED_SHA,
            "got": identity.to_dict()["content_sha256"]}


# ---------------------------------------------------------------- 驗證：逐鍵相等


def test_identity_equals_manifest_per_key(run: Any) -> None:
    """身分取值與 manifest 逐鍵相等；鍵集＝契約 `run_identity_keys`；新 run 非 legacy；舊回傳形態不變。"""
    lib = library_for(run)
    manifest = read_manifest(run)
    expected = expected_identity(manifest, "raw")
    assert expected["content_sha256"], "前提不成立：新 run 之 raw 節點無 content_sha256（Task 1.3 未落地）"
    assert expected["provenance_sha256"], "前提不成立：新 run 之 raw 節點無 provenance.sha256（Task 1.3 未落地）"

    df, identity = load_with_identity(lib, run)
    assert isinstance(identity, rp.RunIdentity)
    got = identity.to_dict()
    assert set(got) == set(IDENTITY_KEYS)
    for key in IDENTITY_KEYS:
        assert got[key] == expected[key], f"身分鍵 {key}：{got[key]!r} ≠ manifest {expected[key]!r}"
    assert identity.legacy is False
    # 純函式同一 oracle
    assert rp.resolve_run_identity(manifest, "raw").to_dict() == expected
    # 舊回傳形態保留給既有 caller：`load` 之 DataFrame 與新入口所回者逐位元相同
    pd.testing.assert_frame_equal(df, lib.load(run.symbol, run.tf, config_hash=run.config_hash), check_exact=True)


# ---------------------------------------------------------------- 驗證：解析次數不增加


def test_manifest_parse_count_not_increased(run: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """同一次讀取之 manifest 解析次數：新入口 ≤ `load`，且 `load` 不超過改前碼態之次數。"""
    lib = library_for(run)
    calls = _install_parse_counter(monkeypatch)
    lib.load(run.symbol, run.tf, config_hash=run.config_hash)
    n_load = len(calls)
    assert 0 < n_load <= HEAD_PARSES_PER_LOAD, f"`load` 之 manifest 解析次數 {n_load} > 改前 {HEAD_PARSES_PER_LOAD}"
    # b3 r1 讀取一致性：全程只解析一次（欄位清單、群組檔、時間軸皆依該次解析；結束確認只比位元組、不解析）
    assert n_load == PARSES_PER_LOAD, f"`load` 之 manifest 解析次數 {n_load} ≠ {PARSES_PER_LOAD}"
    calls.clear()
    load_with_identity(lib, run)
    n_identity = len(calls)
    assert n_identity <= n_load, f"回傳身分之入口解析 manifest {n_identity} 次 > `load` 之 {n_load} 次（身分須取自同一次解析）"
    assert n_identity == PARSES_PER_LOAD, f"回傳身分之入口解析 manifest {n_identity} 次 ≠ {PARSES_PER_LOAD}"


# ---------------------------------------------------------------- 驗證：不一致案


def test_identity_from_same_parse_when_manifest_replaced(
    run: Any, restore_manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """讀取完成後、回傳前 manifest 被替換 ⇒ 身分仍等於本次讀取唯一一次解析所得（不得於讀完後再解析一次取身分）。"""
    case = _replacement_case(library_for(run), run, restore_manifest, monkeypatch)
    assert case["got"] == case["original"], f"身分取自替換後之 manifest：{case['got']!r}"
    assert case["got"] != case["tampered"]


def test_mutation_identity_from_second_parse(run: Any, restore_manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：身分改取讀完後第二次解析之 manifest ⇒ 替換期間取得替換值（不一致案翻轉）。"""

    def mutant(self: FeatureLibrary, symbol: str, timeframe: str, *, config_hash: Optional[str] = None, **kwargs: Any):
        df = self.load(symbol, timeframe, config_hash=config_hash, **kwargs)
        resolved = config_hash or self.find_latest_materialized(symbol, timeframe)["config_hash"]
        manifest = self._reader.load_run_manifest_v2(symbol, timeframe, resolved)  # 第二次解析
        return df, rp.resolve_run_identity(manifest, "raw")

    monkeypatch.setattr(FeatureLibrary, LOAD_WITH_IDENTITY, mutant, raising=False)
    case = _replacement_case(library_for(run), run, restore_manifest, monkeypatch)
    assert case["got"] != case["original"]
    assert case["got"] == case["tampered"]


# ---------------------------------------------------------------- 驗證：讀取一致性（b3 審碼 r1 CODEX-R1-P1-01）


def test_identity_replacement_midway_refused(
    run: Any, restore_manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """讀取**中途**（唯一一次解析回傳後）manifest 被替換 ⇒ `load` 與 `load_with_identity` 皆拋
    `ManifestChangedDuringReadError`（不重試、不回任何身分）。"""
    lib = library_for(run)
    _original, tampered = _tampered_bytes(restore_manifest)
    resolved = restore_manifest.resolve()
    original_bytes = restore_manifest.read_bytes()

    def swap(parsed: Path, n: int) -> None:
        if n == 1 and parsed.resolve() == resolved:
            restore_manifest.write_bytes(tampered)

    calls = _install_parse_counter(monkeypatch, swap)
    with pytest.raises(ManifestChangedDuringReadError):
        load_with_identity(lib, run)
    assert len(calls) == PARSES_PER_LOAD
    restore_manifest.write_bytes(original_bytes)
    calls.clear()
    with pytest.raises(ManifestChangedDuringReadError):
        lib.load(run.symbol, run.tf, config_hash=run.config_hash)
    assert len(calls) == PARSES_PER_LOAD


def _swap_run_dir(dst: Path, src: Path) -> None:
    """把 run 目錄 `dst` 之內容（manifest 與全部特徵檔）整個換成 `src` 之內容（同 config_hash 重生之模擬）。"""
    shutil.rmtree(dst)
    shutil.copytree(src, dst)


def _concurrent_case(run: Any, run_other: Any, work: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """真實兩 run（A＝`run`、B＝同設定改一根 K 線重生之 `run_other`）：複製 A 之隔離特徵根到 `work`，唯一一次解析回傳後
    把 `work` 內 run 目錄整個換成 B 之內容，再呼叫 `load_with_identity`。回 {結果或例外, A／B 身分與資料}。"""
    assert run_other.config_hash == run.config_hash and run_other.symbol == run.symbol and run_other.tf == run.tf, \
        "前提不成立：B 與 A 須為同 symbol／tf／config_hash（同路徑重生）"
    manifest_a, manifest_b = read_manifest(run), read_manifest(run_other)
    sha_a = manifest_a["artifacts"]["raw"].get("content_sha256")
    sha_b = manifest_b["artifacts"]["raw"].get("content_sha256")
    assert sha_a and sha_b and sha_a != sha_b, "前提不成立：A／B 之 raw content_sha256 須皆存在且不同（值確有改變）"
    groups_a = {g: (i.get("path"), tuple(i.get("columns", []))) for g, i in manifest_a["artifacts"]["raw"]["groups"].items()}
    groups_b = {g: (i.get("path"), tuple(i.get("columns", []))) for g, i in manifest_b["artifacts"]["raw"]["groups"].items()}
    assert groups_a == groups_b, "前提不成立：A／B 之群組檔路徑與欄須相同（使以 A 之解析讀 B 之檔可讀出資料）"

    root = work / "concurrent_features_root"  # tmp_path 下之 features/ 已由隔離 fixture 佔用
    shutil.copytree(Path(run.features_root), root)
    run_dir = root / run.symbol / run.tf / run.config_hash
    assert run_dir.is_dir(), f"前提不成立：複製後無 run 目錄 {run_dir}"
    lib = FeatureLibrary(FeatureRegistry(root / "registry.json"), FeatureStorage(str(root)),
                         feature_reader=FeatureReader(str(root)))
    data_b = library_for(run_other).load(run.symbol, run.tf, config_hash=run.config_hash)
    data_a = lib.load(run.symbol, run.tf, config_hash=run.config_hash)
    assert not data_a.equals(data_b), "前提不成立：A／B 讀回之特徵值須不同"

    resolved = (run_dir / FeatureReader.V2_MANIFEST_NAME).resolve()

    def swap(parsed: Path, n: int) -> None:
        if n == 1 and parsed.resolve() == resolved:
            _swap_run_dir(run_dir, Path(run_other.run_dir))

    _install_parse_counter(monkeypatch, swap)
    out: Dict[str, Any] = {"identity_a": expected_identity(manifest_a, "raw"),
                           "identity_b": expected_identity(manifest_b, "raw"), "data_a": data_a, "data_b": data_b}
    try:
        out["result"] = load_with_identity(lib, run)
    except ManifestChangedDuringReadError as exc:
        out["error"] = exc
    # 替換確已發生（非空轉）：run 目錄之 manifest 已為 B 之位元組
    assert (run_dir / FeatureReader.V2_MANIFEST_NAME).read_bytes() == (Path(run_other.run_dir) / FeatureReader.V2_MANIFEST_NAME).read_bytes()
    return out


def test_verification_04_concurrent_replacement_refused(
    run: Any, run_other: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """讀取一致性（SPEC Task 2.1 改法）：同 config_hash 之 run 於讀取中途被另一份真實 run（manifest 與全部特徵檔）
    整個替換 ⇒ `load_with_identity` 拋 `ManifestChangedDuringReadError`，絕不回「A 之身分＋B 之資料」。"""
    case = _concurrent_case(run, run_other, tmp_path, monkeypatch)
    assert "result" not in case, (
        f"讀取中途被替換卻回傳結果：身分 content_sha256={case['result'][1].to_dict()['content_sha256']!r}")
    assert isinstance(case["error"], ManifestChangedDuringReadError)


def test_mutation_no_end_of_load_confirmation(
    run: Any, run_other: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutant：拿掉讀取結束之 sha256 確認 ⇒ verification_04 翻轉——回傳 A 之身分卻帶 B 之資料（錯配實際發生）。"""
    monkeypatch.setattr(FeatureReader, "_confirm_manifest_unchanged", staticmethod(lambda snapshot: None))
    case = _concurrent_case(run, run_other, tmp_path, monkeypatch)
    assert "error" not in case, "mutant 下仍拒讀：verification_04 之拒讀不來自結束確認"
    df, identity = case["result"]
    assert identity.to_dict() == case["identity_a"], "mutant 之身分應取自唯一一次解析（A）"
    pd.testing.assert_frame_equal(df, case["data_b"], check_exact=True)
    assert not df.equals(case["data_a"])


# ---------------------------------------------------------------- 邊界


def test_boundary_01_latest_resolved_before_identity(run: Any) -> None:
    """邊界①：`config_hash` 未指定 ⇒ 先依 registry 解析 latest，身分之 `config_hash` 為解析後之真值且逐鍵等於該 run。"""
    lib = library_for(run)
    entry = lib.find_latest_materialized(run.symbol, run.tf)
    assert entry is not None, "前提不成立：隔離 registry 無 latest run"
    resolved = str(entry["config_hash"])
    assert resolved == run.config_hash, "前提不成立：隔離 registry 之 latest 非本模組之 run"
    _df, identity = load_with_identity(lib, run, config_hash=None)
    got = identity.to_dict()
    assert got["config_hash"] == resolved and got["config_hash"] not in ("", "latest", None)
    assert got == expected_identity(read_manifest(run), "raw")


def test_boundary_02_legacy_run(run: Any, restore_manifest: Path) -> None:
    """邊界②：舊 run（manifest 無 `content_sha256`／`provenance`）⇒ 身分標 legacy、兩雜湊為 None、其餘鍵照 manifest；
    特徵讀取不受影響（D6：DataFrame 與新 run 讀回逐位元相同）。"""
    lib = library_for(run)
    df_new = lib.load(run.symbol, run.tf, config_hash=run.config_hash)
    legacy = strip_to_legacy(read_manifest(run))
    restore_manifest.write_text(json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")

    df, identity = load_with_identity(lib, run)
    assert identity.legacy is True
    got = identity.to_dict()
    assert got["content_sha256"] is None and got["provenance_sha256"] is None
    assert got == expected_identity(legacy, "raw")
    assert rp.resolve_run_identity(legacy, "raw").legacy is True
    pd.testing.assert_frame_equal(df, df_new, check_exact=True)
