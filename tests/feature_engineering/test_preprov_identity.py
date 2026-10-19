"""PRE-PROV（docs/FFDSTAR_SPEC.md Task 2.1）：run 身分物件——IC 自同一次 manifest 解析取得 run 身分。

驗證（SPEC Task 2.1）：
- 身分取值與 manifest 逐鍵相等（鍵集取自契約 `run_identity_keys`，不另列舉）；
- 同一次 `load` 內 manifest 解析次數不因本 Task 增加（計數 monkeypatch `FeatureReader._parse_manifest_file`，
  其為全部 V2 讀取之單一 manifest 解析邊界）；
- 不一致案：解析之間 manifest 被替換 ⇒ 身分仍等於本次讀取所據之那一次解析。
邊界：①`config_hash` 未指定（latest 解析後才定身分）；②舊 run（無 `content_sha256` ⇒ `legacy`）。
mutation：身分改取第二次解析之 manifest 且其間 manifest 被替換 ⇒ 不一致案翻轉。

資料：真實 kline 短窗生成（`preprov_helpers.generate_short_run`，格 `h1_stat_on`，本模組只生成一次）；
「舊 run」與「替換之 manifest」皆以該真實 run 之 manifest 刪鍵／改值得之，不造特徵矩陣。
實作前應為紅：`resolve_run_identity` 為 stub，`FeatureLibrary` 無回傳身分之入口。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

import pandas as pd
import pytest

from momentum.FeatureEngineering import run_provenance as rp
from momentum.FeatureEngineering.feature_library import FeatureLibrary
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(1800)

# 契約為身分鍵之唯一真相源（SPEC §C）；直接讀 JSON，不經待測之 `load_contract`
CONTRACT: Dict[str, Any] = json.loads(rp.CONTRACT_PATH.read_text(encoding="utf-8"))
IDENTITY_KEYS: List[str] = list(CONTRACT["run_identity_keys"])

# SPEC Task 2.1「`load` 新增回傳身分之入口」未定名；本檔以此名呼叫（回 (DataFrame, RunIdentity)）。
LOAD_WITH_IDENTITY = "load_with_identity"

# 改前碼態（HEAD）一次 `FeatureLibrary.load` 之 manifest 解析次數：load_manifest_v2、list_features_v2、
# load_columns_v2、_attach_row_index→load_row_index_v2 各一次（feature_library.py:149-187、
# feature_reader.py:_resolve_manifest_v2）。本 Task 不得使之增加。
HEAD_PARSES_PER_LOAD = 4

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
    """以計數版取代單一 manifest 解析邊界；`on_parse(path, n)` 於第 n 次解析回傳前呼叫（n 從 1 起）。"""
    real = FeatureReader._parse_manifest_file
    calls: List[Path] = []

    def counting(path: Path) -> dict:
        result = real(path)
        calls.append(Path(path))
        if on_parse is not None:
            on_parse(Path(path), len(calls))
        return result

    monkeypatch.setattr(FeatureReader, "_parse_manifest_file", staticmethod(counting))
    return calls


def _replacement_case(lib: FeatureLibrary, run: Any, path: Path, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """不一致案之 oracle 輸入：第一次解析回傳後即把磁碟上 manifest 換成只改 raw `content_sha256` 之版本，
    之後之解析讀到替換版。回 {原值, 替換值, 身分取得之值}。"""
    original = json.loads(path.read_text(encoding="utf-8"))
    tampered = copy.deepcopy(original)
    tampered["artifacts"]["raw"]["content_sha256"] = TAMPERED_SHA
    assert original["artifacts"]["raw"].get("content_sha256") != TAMPERED_SHA
    resolved = path.resolve()

    def swap(parsed: Path, n: int) -> None:
        if n == 1 and parsed.resolve() == resolved:
            path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2), encoding="utf-8")

    _install_parse_counter(monkeypatch, swap)
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
    calls.clear()
    load_with_identity(lib, run)
    n_identity = len(calls)
    assert n_identity <= n_load, f"回傳身分之入口解析 manifest {n_identity} 次 > `load` 之 {n_load} 次（身分須取自同一次解析）"


# ---------------------------------------------------------------- 驗證：不一致案


def test_identity_from_same_parse_when_manifest_replaced(
    run: Any, restore_manifest: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """讀取中途 manifest 被替換 ⇒ 身分仍等於本次讀取第一次解析所得（不得於讀完後再解析一次取身分）。"""
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
