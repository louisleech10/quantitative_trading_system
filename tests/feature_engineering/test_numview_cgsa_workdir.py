"""NUMVIEW Task 4.2 ⑦（docs/NUMVIEW_SPEC.md §C D7、R3-A；§V oracle ⑧ 工作目錄隔離）：CGSA 工作目錄身分。

D7：工作目錄路徑＝`<root>/<symbol>_<tf>_<完整 config_hash>/<完整 algorithm_id>`，由 `run_paths` 之純函式導出；
`FFACT_CGSA_WORK_DIR` 一律視為 `<root>`；葉目錄建立時先原子寫身分檔（四鍵）；任何讀取（含 `manifest.json` 存在檢查與
`resume_from_manifest`）之前先比對身分檔，相符且 manifest 存在才續跑；身分檔缺或任一鍵不符 ⇒ 不讀該目錄任何其他檔、
改名移出（`<葉>.stale-<UTC 時間>`）並建全新空目錄；`config_hash` 為空 ⇒ 一律全新、不續跑；刪除 run 以
`<symbol>_<tf>_<config_hash>` 層為單位。

驗證（SPEC Task 4.2 ⑦）：(a) 前八碼相同而完整不同之兩 `config_hash` ⇒ 兩條不同路徑；(b) 同 `config_hash`、不同
`algorithm_id` ⇒ 不同葉，先放入舊 `algorithm_id` 之 `manifest.json` 與群組檔（於舊葉，及於新 run 之目標路徑而身分檔
記舊值）後啟動新 run ⇒ 新 registry 建立前後皆不讀舊檔（開檔 spy 零次）、不續跑；(c) 葉身分檔被改一鍵 ⇒ 原目錄移為
`.stale-*`、新目錄為空（只含身分檔）、不續跑；(d) 舊命名葉（`config_hash[:8]`、無身分檔）不被讀取；(e) 覆寫根下兩個
不同身分之 run 落於不同葉（且身分不隨覆寫根改變）；(f) `config_hash` 為空 ⇒ 不續跑；(g) 刪除 run 移除該 `config_hash`
層下全部葉。另：身分相符＋manifest＋完整 L7 ⇒ 續跑（對照，證續跑閘可達）。
邊界（全域編號）：50 身分檔為空檔或非 JSON ⇒ 視同不符（移出、新建）；51 移出目的名已存在 ⇒ 時間戳加序號、不覆蓋既有
stale 目錄；52 `.stale-*` 不自動刪除、其內容不被本 Task 之碼讀取（spy）。
mutation：葉名改回 `config_hash[:8]` ⇒ (a) 紅；身分檔比對移到 `manifest.json` 存在檢查（並讀取）之後 ⇒ (b) 零讀取紅；
不符時改為續跑／沿用 ⇒ (c) 紅；覆寫值改回直接當葉目錄 ⇒ (e) 紅；Task 0.2 交叉 mutation「`FFACT_CGSA_WORK_DIR`
改入鹽」⇒ (e) 覆寫根下 run 之身分隨根路徑改變而紅。

測試接縫（實作須提供；名稱為本檔所定）：
- `run_paths.cgsa_config_layer_dir(root, symbol, timeframe, config_hash) -> Path`（`<symbol>_<tf>_<完整 config_hash>` 層）；
- `run_paths.cgsa_work_dir(root, symbol, timeframe, config_hash, algorithm_id) -> Path`（葉＝層／完整 algorithm_id）；
- `run_paths.utc_stamp() -> str`：`.stale-` 名之 UTC 時間戳唯一來源（邊界 51 以 monkeypatch 固定之）；
- `FeatureFactory._prepare_cgsa_registry(symbol, timeframe, config_hash="", algorithm_id="")`：預設根與覆寫根皆經
  `run_paths.cgsa_work_dir` 取葉；身分檔名與鍵讀契約 `cgsa_work_identity.{identity_file, identity_keys}`，內容為
  四鍵之 JSON 物件；續跑閘之 L7 manifest `algorithm_id` 鍵讀契約 `manifest_keys.algorithm_id`；
- `RunLifecycleManager.delete_run` 以 `run_paths.cgsa_config_layer_dir` 為刪除單位。
既有 `tests/test_cgsa_resume.py`、`tests/feature_engineering/test_run_lifecycle.py` 以舊葉名或覆寫值為工作目錄之斷言
須於實作同提交改寫並登記審清單（SPEC Task 4.2 既有 caller）；本檔不改之。

資料：不生成特徵；symbol／tf 自真實 `kline_cache.h5` 列舉；`config_hash`／`algorithm_id` 為測試字面之 md5／sha256。
一律於 tmp（chdir）下進行，不寫入專案 data_cache。秒級。
實作前應為紅（`_prepare_cgsa_registry` 無 `algorithm_id`、`run_paths` 無新函式、契約未填）；不得以 skip／xfail 暫避。
"""

from __future__ import annotations

import builtins
import contextvars
import copy
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple
from unittest.mock import Mock

import h5py
import pytest

from momentum.FeatureEngineering import numeric_view as nv
from momentum.FeatureEngineering import run_paths
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_config import PreprocessingConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.run_lifecycle import RunLifecycleManager
from tests.feature_engineering import preprov_helpers as ph

pytestmark = pytest.mark.timeout(600)

RAW: Dict[str, Any] = json.loads(nv.CONTRACT_PATH.read_text(encoding="utf-8"))
EMPTY = "<契約未填>"
#: SPEC Task 0.2／D7 點名之 output_only 鍵（CGSA 工作目錄根）
OVERRIDE_KEY = "FFACT_CGSA_WORK_DIR"
GROUP_FILE = "L1_numview_group.npy"
GROUP_BYTES = b"numview-group-bytes"
FIXED_STAMP = "20261021T000000Z"
IDENTITY_KEY_PARAMS: List[str] = list(RAW["cgsa_work_identity"].get("identity_keys") or []) or [EMPTY]


# ============================================================================================== 契約與工具

def _identity_name() -> str:
    name = RAW["cgsa_work_identity"].get("identity_file")
    assert isinstance(name, str) and name, "契約 cgsa_work_identity.identity_file 未填（Task 4.2）"
    return name


def _identity(symbol: str, tf: str, config_hash: str, algorithm_id: str) -> Dict[str, str]:
    """身分檔內容（SPEC D7 四鍵）；鍵集須等於契約 identity_keys。"""
    payload = {"symbol": symbol, "tf": tf, "config_hash": config_hash, "algorithm_id": algorithm_id}
    keys = list(RAW["cgsa_work_identity"].get("identity_keys") or [])
    assert set(keys) == set(payload), f"契約 cgsa_work_identity.identity_keys {keys} ≠ SPEC D7 四鍵"
    return payload


def _algorithm_key() -> str:
    key = RAW["manifest_keys"].get("algorithm_id")
    assert isinstance(key, str) and key, "契約 manifest_keys.algorithm_id 未填（Task 4.2）"
    return key


def _md5(tag: str) -> str:
    return hashlib.md5(tag.encode("utf-8")).hexdigest()


def _sha(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _real(path: Any) -> str:
    return os.path.realpath(os.fspath(path))


def _kline_cell() -> Tuple[str, str]:
    """真實 kline 之第一個 symbol×tf（自 kline_cache.h5 列舉，不寫死）。"""
    with h5py.File(ph.KLINE_FILE, "r") as f:
        symbols = sorted(f.keys())
        assert symbols, "kline_cache.h5 無 symbol"
        tfs = sorted(f[symbols[0]].keys())
    assert tfs, f"{symbols[0]} 無週期"
    return symbols[0], tfs[0]


def bare_factory(tmp: Path) -> FeatureFactory:
    """最小 FeatureFactory（同 tests/test_cgsa_resume.py 之 fixture）；特徵根＝`tmp/features`。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = FeatureStorage(str(Path(tmp) / "features"))
    factory._registry = FeatureRegistry(Path(tmp) / "registry.json")
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_config_hash = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    factory._cgsa_force_fresh = False
    factory.layer_results = {}
    return factory


def write_complete_l7_manifest(storage: FeatureStorage, symbol: str, tf: str, config_hash: str,
                               algorithm_id: str) -> None:
    """完整 L7 manifest（續跑閘放行之前提，同 test_cgsa_resume）＋頂層與 raw 節點之 `algorithm_id`。"""
    run_dir = storage.feature_run_dir(symbol, tf, config_hash)
    run_dir.mkdir(parents=True, exist_ok=True)
    key = _algorithm_key()
    node = {"schema_version": "raw_v2", "expected_layers": ["L1"], "present_layers": ["L1"], "failed_layers": [],
            "expected_timeframes": [tf], "present_timeframes": [tf], "failed_timeframes": [],
            "quality_status": "complete", key: algorithm_id}
    (run_dir / storage.L7_V2_MANIFEST_NAME).write_text(json.dumps({"artifacts": {"raw": node}, key: algorithm_id}),
                                                      encoding="utf-8")


def seed_leaf(leaf: Path, identity_text: Optional[str]) -> None:
    """於 `leaf` 放 registry manifest＋群組檔；`identity_text` 非 None ⇒ 另寫身分檔（原文）。"""
    leaf.mkdir(parents=True, exist_ok=True)
    (leaf / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
    (leaf / GROUP_FILE).write_bytes(GROUP_BYTES)
    if identity_text is not None:
        (leaf / _identity_name()).write_text(identity_text, encoding="utf-8")


def snapshot(directory: Path) -> Dict[str, bytes]:
    return {str(p.relative_to(directory)): p.read_bytes() for p in sorted(Path(directory).rglob("*")) if p.is_file()}


def stale_dirs(leaf: Path) -> List[Path]:
    return sorted(p for p in Path(leaf).parent.iterdir() if p.name.startswith(Path(leaf).name + ".stale-"))


def patch_everywhere(monkeypatch: pytest.MonkeyPatch, name: str, original: Any, replacement: Any) -> int:
    """把 momentum／api 已載入模組中綁定到 `original` 之 `name` 一律換成 `replacement`（mutant 不依賴 import 形式）。"""
    hits = 0
    for module in list(sys.modules.values()):
        modname = getattr(module, "__name__", "") or ""
        if modname.startswith(("momentum", "api")) and getattr(module, name, None) is original:
            monkeypatch.setattr(module, name, replacement)
            hits += 1
    return hits


def install_open_spy(mp: pytest.MonkeyPatch, watch: Sequence[Path], events: List[Tuple[str, str]]) -> None:
    """記錄對 `watch` 各路徑（含其下與 `.stale-*` 兄弟）之開檔，與 ColumnGroupRegistry 之建立／續跑（同一有序串列）。"""
    roots = [_real(w) for w in watch]

    def hit(target: Any) -> Optional[str]:
        try:
            path = _real(target)
        except TypeError:
            return None
        for r in roots:
            if path == r or path.startswith(r + os.sep) or path.startswith(r + ".stale-"):
                return path
        return None

    real_builtin, real_io, real_os = builtins.open, io.open, os.open

    def b_open(file: Any, *a: Any, **k: Any) -> Any:
        h = hit(file)
        if h:
            events.append(("open", h))
        return real_builtin(file, *a, **k)

    def i_open(file: Any, *a: Any, **k: Any) -> Any:
        h = hit(file)
        if h:
            events.append(("open", h))
        return real_io(file, *a, **k)

    def o_open(path: Any, *a: Any, **k: Any) -> Any:
        h = hit(path)
        if h:
            events.append(("open", h))
        return real_os(path, *a, **k)

    mp.setattr(builtins, "open", b_open)
    mp.setattr(io, "open", i_open)
    mp.setattr(os, "open", o_open)
    real_init = ColumnGroupRegistry.__init__

    def init(self: Any, work_dir: Any, *a: Any, **k: Any) -> None:
        events.append(("registry", _real(work_dir)))
        real_init(self, work_dir, *a, **k)

    mp.setattr(ColumnGroupRegistry, "__init__", init)


def reads_before_registry(events: Sequence[Tuple[str, str]], leaf: Path) -> List[str]:
    """新 registry 於 `leaf` 建立之前，對 `leaf`（含其 `.stale-*`）之開檔；身分檔除外。"""
    leaf_s = _real(leaf)
    allowed = os.path.join(leaf_s, _identity_name())
    out: List[str] = []
    for kind, path in events:
        if kind == "registry" and path == leaf_s:
            return out
        if kind == "open" and (path == leaf_s or path.startswith(leaf_s + os.sep) or path.startswith(leaf_s + ".stale-")) \
                and path != allowed:
            out.append(path)
    out.append("未見新 registry 於該葉建立")
    return out


def opens_under(events: Sequence[Tuple[str, str]], directory: Path) -> List[str]:
    d = _real(directory)
    return [p for kind, p in events if kind == "open" and (p == d or p.startswith(d + os.sep))]


class Ctx:
    """單一測試之隔離情境：cwd＝tmp、無覆寫根、`resume_from_manifest` 為 Mock（呼叫次數＝續跑次數）。"""

    def __init__(self, tmp: Path, resume: Mock) -> None:
        self.tmp = Path(tmp)
        self.root = Path(os.getcwd()) / "data_cache" / "cgsa_work"
        self.resume = resume
        self.symbol, self.tf = _kline_cell()

    def factory(self) -> FeatureFactory:
        return bare_factory(self.tmp)

    def prepare(self, config_hash: str, algorithm_id: str, factory: Optional[FeatureFactory] = None) -> Any:
        """於 context 副本內呼叫 `_prepare_cgsa_registry`（工廠註冊之 contextvar 不外洩）。"""
        f = factory or self.factory()
        return contextvars.copy_context().run(
            lambda: f._prepare_cgsa_registry(self.symbol, self.tf, config_hash, algorithm_id=algorithm_id))

    def leaf(self, config_hash: str, algorithm_id: str, root: Optional[Path] = None) -> Path:
        return run_paths.cgsa_work_dir(root or self.root, self.symbol, self.tf, config_hash, algorithm_id)

    def l7(self, config_hash: str, algorithm_id: str) -> None:
        write_complete_l7_manifest(self.factory()._storage, self.symbol, self.tf, config_hash, algorithm_id)


@pytest.fixture()
def ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Ctx]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(OVERRIDE_KEY, raising=False)
    resume = Mock(return_value="resumed")
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume)
    yield Ctx(tmp_path, resume)


# ============================================================================================== oracle（純函式；mutation 共用）

def prefix_collision_case(c: Ctx) -> Dict[str, Any]:
    """(a)：前八碼相同而完整不同之兩 config_hash（同 algorithm_id）經工廠所得之葉。"""
    ch_a = _md5("numview-prefix-a")
    ch_b = ch_a[:8] + _md5("numview-prefix-b")[8:]
    assert ch_a[:8] == ch_b[:8] and ch_a != ch_b
    aid = _sha("numview-prefix")
    a, b = c.prepare(ch_a, aid).work_dir, c.prepare(ch_b, aid).work_dir
    return {"distinct": _real(a) != _real(b), "a": a, "b": b, "ch_a": ch_a, "ch_b": ch_b, "aid": aid}


def algorithm_switch_case(c: Ctx) -> Dict[str, Any]:
    """(b)：同 config_hash、舊 algorithm_id 之葉（含 manifest 與群組檔）＋新 run 目標路徑上身分記舊值之殘留；啟動新 run。"""
    ch, old, new = _md5("numview-b"), _sha("numview-b-old"), _sha("numview-b-new")
    old_leaf, new_leaf = c.leaf(ch, old), c.leaf(ch, new)
    seed_leaf(old_leaf, json.dumps(_identity(c.symbol, c.tf, ch, old)))
    seed_leaf(new_leaf, json.dumps(_identity(c.symbol, c.tf, ch, old)))
    c.l7(ch, new)
    old_before, target_before = snapshot(old_leaf), snapshot(new_leaf)
    events: List[Tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        install_open_spy(mp, [old_leaf, new_leaf], events)
        registry = c.prepare(ch, new)
        list(registry.iter_all())
    stale = stale_dirs(new_leaf)
    return {
        "leaf_is_new": _real(registry.work_dir) == _real(new_leaf) and _real(new_leaf) != _real(old_leaf),
        "resumed": c.resume.call_count,
        "old_leaf_opens": opens_under(events, old_leaf),
        "target_reads_before_registry": reads_before_registry(events, new_leaf),
        "old_leaf_intact": snapshot(old_leaf) == old_before,
        "target_moved_intact": len(stale) == 1 and {k: v for k, v in snapshot(stale[0]).items()} == target_before,
    }


ALGORITHM_SWITCH_OK = {"leaf_is_new": True, "resumed": 0, "old_leaf_opens": [], "target_reads_before_registry": [],
                       "old_leaf_intact": True, "target_moved_intact": True}


def mismatch_case(c: Ctx, identity_text: str, tag: str) -> Dict[str, Any]:
    """(c)／邊界 50：葉身分檔為 `identity_text`（與本次身分不符），另有 manifest、群組檔與完整 L7 ⇒ 啟動本次 run。"""
    ch, aid = _md5(f"numview-{tag}"), _sha(f"numview-{tag}")
    leaf = c.leaf(ch, aid)
    seed_leaf(leaf, identity_text)
    c.l7(ch, aid)
    before = snapshot(leaf)
    registry = c.prepare(ch, aid)
    stale = stale_dirs(leaf)
    new_files = snapshot(leaf)
    return {
        "resumed": c.resume.call_count,
        # 續跑時 resume 為 Mock（回字串、無 work_dir）⇒ 視為非同一新葉（mutant 案）
        "same_path": _real(getattr(registry, "work_dir", "")) == _real(leaf),
        "moved_intact": len(stale) == 1 and snapshot(stale[0]) == before,
        "new_leaf_only_identity": set(new_files) <= {_identity_name()},
        "new_identity_correct": json.loads(new_files.get(_identity_name(), b"null")) == _identity(c.symbol, c.tf, ch, aid),
    }


MISMATCH_OK = {"resumed": 0, "same_path": True, "moved_intact": True, "new_leaf_only_identity": True,
               "new_identity_correct": True}


def override_case(c: Ctx, monkeypatch: pytest.MonkeyPatch) -> Dict[str, Any]:
    """(e)：覆寫根下三個身分（同 ch 不同 aid、不同 ch 同 aid）之葉。"""
    override = c.tmp / "override_root"
    monkeypatch.setenv(OVERRIDE_KEY, str(override))
    ch1, ch2, a1, a2 = _md5("numview-e1"), _md5("numview-e2"), _sha("numview-e1"), _sha("numview-e2")
    dirs = [c.prepare(ch, aid).work_dir for ch, aid in ((ch1, a1), (ch1, a2), (ch2, a1))]
    root_s = _real(override)
    return {
        "distinct": len({_real(d) for d in dirs}) == 3,
        "under_root_not_root": all(_real(d).startswith(root_s + os.sep) for d in dirs),
        "match_run_paths": [_real(d) for d in dirs] == [_real(c.leaf(ch, aid, override))
                                                        for ch, aid in ((ch1, a1), (ch1, a2), (ch2, a1))],
    }


def identity_stable_across_override_roots(c: Ctx, monkeypatch: pytest.MonkeyPatch) -> bool:
    """Task 0.2 交叉：同設定於兩個不同覆寫根下解析之 algorithm_id 與鹽相同（根不入身分）。"""
    for key in [k for k in os.environ if k.startswith("FFACT_")]:
        monkeypatch.delenv(key)
    pre = PreprocessingConfig().model_dump()
    caps = dict(nv.detect_capabilities())
    ids = []
    for name in ("override_a", "override_b"):
        monkeypatch.setenv(OVERRIDE_KEY, str(c.tmp / name))
        fp = nv.resolve_numeric_fingerprint(preprocessing_config=copy.deepcopy(pre), environ=dict(os.environ),
                                            capabilities=caps)
        ids.append((nv.algorithm_id(fp), json.dumps(nv.config_hash_salt(fp), sort_keys=True, default=str)))
    return ids[0] == ids[1]


# ============================================================================================== 驗證 (a)–(g)

def test_cgsa_leaf_distinguishes_full_config_hash(ctx: Ctx) -> None:
    """(a)：前八碼相同而完整不同之兩 `config_hash` ⇒ 兩條不同路徑；葉＝`<root>/<symbol>_<tf>_<完整 config_hash>/<完整 algorithm_id>`。"""
    case = prefix_collision_case(ctx)
    assert case["distinct"] is True
    for ch, leaf in ((case["ch_a"], case["a"]), (case["ch_b"], case["b"])):
        layer = run_paths.cgsa_config_layer_dir(ctx.root, ctx.symbol, ctx.tf, ch)
        assert _real(leaf) == _real(ctx.leaf(ch, case["aid"])) == _real(Path(layer) / case["aid"])
        assert Path(layer).name == f"{run_paths.safe_token(ctx.symbol)}_{run_paths.safe_token(ctx.tf)}_{ch}"
        assert _real(Path(layer).parent) == _real(ctx.root)


def test_cgsa_matching_identity_resumes(ctx: Ctx) -> None:
    """對照：身分檔四鍵相符＋registry manifest＋完整 L7（同 algorithm_id）⇒ 續跑（證本檔之不續跑案非因閘不可達）。"""
    ch, aid = _md5("numview-match"), _sha("numview-match")
    seed_leaf(ctx.leaf(ch, aid), json.dumps(_identity(ctx.symbol, ctx.tf, ch, aid)))
    ctx.l7(ch, aid)
    assert ctx.prepare(ch, aid) == "resumed" and ctx.resume.call_count == 1


def test_cgsa_new_algorithm_id_zero_reads_of_old_files(ctx: Ctx) -> None:
    """(b)：同 config_hash、不同 algorithm_id ⇒ 不同葉；舊葉之 manifest.json 與群組檔於新 registry 建立前後皆零開檔、
    不續跑；新 run 目標路徑上身分記舊值之殘留 ⇒ 建立前除身分檔外零開檔，原樣移為 `.stale-*`。"""
    assert algorithm_switch_case(ctx) == ALGORITHM_SWITCH_OK


@pytest.mark.parametrize("key", IDENTITY_KEY_PARAMS)
def test_cgsa_identity_key_altered_moves_leaf_to_stale(ctx: Ctx, key: str) -> None:
    """(c)：葉身分檔被改一鍵 ⇒ 原目錄（原樣）移為 `.stale-*`、同路徑新目錄只含正確身分檔、不續跑。"""
    assert key in (RAW["cgsa_work_identity"].get("identity_keys") or []), "契約 identity_keys 為空（Task 4.2 未填）"
    tag = f"c-{key}"
    ch, aid = _md5(f"numview-{tag}"), _sha(f"numview-{tag}")
    altered = _identity(ctx.symbol, ctx.tf, ch, aid)
    altered[key] = altered[key] + "_numview_altered"
    assert mismatch_case(ctx, json.dumps(altered), tag) == MISMATCH_OK


def test_cgsa_old_named_leaf_not_read(ctx: Ctx) -> None:
    """(d)：舊命名葉（`<symbol>_<tf>_<config_hash[:8]>`、無身分檔）存在 ⇒ 全程零開檔、內容不變、不續跑、不被當工作目錄。"""
    ch, aid = _md5("numview-d"), _sha("numview-d")
    old = ctx.root / f"{run_paths.safe_token(ctx.symbol)}_{run_paths.safe_token(ctx.tf)}_{ch[:8]}"
    seed_leaf(old, None)
    ctx.l7(ch, aid)
    before = snapshot(old)
    events: List[Tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        install_open_spy(mp, [old], events)
        registry = ctx.prepare(ch, aid)
        list(registry.iter_all())
    assert opens_under(events, old) == [] and snapshot(old) == before
    assert ctx.resume.call_count == 0 and _real(registry.work_dir) != _real(old)


def test_cgsa_override_root_separates_identities(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """(e)：`FFACT_CGSA_WORK_DIR` 覆寫下，不同身分之 run 落於覆寫根下之不同葉（皆為根之子孫、非根本身、等於 run_paths 導出）；
    覆寫根屬契約 output_only 且不入身分（同設定於兩根之 algorithm_id 與鹽相同）。"""
    assert OVERRIDE_KEY in (RAW["selector_classes"].get("output_only_keys") or []), "契約 output_only_keys 未含覆寫根"
    assert override_case(ctx, monkeypatch) == {"distinct": True, "under_root_not_root": True, "match_run_paths": True}
    assert identity_stable_across_override_roots(ctx, monkeypatch) is True


def test_cgsa_empty_config_hash_never_resumes(ctx: Ctx) -> None:
    """(f)：`config_hash` 為空 ⇒ 無法建立身分，一律全新空目錄、不續跑（前一 run 留下之 manifest 與群組檔不沿用）。"""
    aid = _sha("numview-f")
    first = ctx.prepare("", aid)
    (Path(first.work_dir) / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
    (Path(first.work_dir) / GROUP_FILE).write_bytes(GROUP_BYTES)
    second = ctx.prepare("", aid)
    assert ctx.resume.call_count == 0
    assert not (Path(second.work_dir) / "manifest.json").exists() and not (Path(second.work_dir) / GROUP_FILE).exists()


def test_cgsa_delete_run_removes_whole_config_layer(ctx: Ctx) -> None:
    """(g)：刪除 run 以 `<symbol>_<tf>_<config_hash>` 層為單位，移除其下全部 algorithm_id 葉；他 config_hash 之層不動。"""
    ch, other_ch = _md5("numview-g"), _md5("numview-g-other")
    for c_hash, aid in ((ch, _sha("numview-g1")), (ch, _sha("numview-g2")), (other_ch, _sha("numview-g1"))):
        leaf = Path(ctx.prepare(c_hash, aid).work_dir)
        (leaf / "manifest.json").write_text(json.dumps({"config_hash": c_hash, "groups": []}), encoding="utf-8")
    features = ctx.tmp / "features"
    registry = FeatureRegistry(features / "registry.json")
    manager = RunLifecycleManager(features, ctx.root, features / ".locks", registry)
    feature_leaf = ph.Path(features) / ctx.symbol / ctx.tf / ch
    feature_leaf.mkdir(parents=True, exist_ok=True)
    (feature_leaf / "data.bin").write_bytes(b"features")
    registry.add({"symbol": ctx.symbol, "timeframe": ctx.tf, "config_hash": ch, "created_at": 1.0,
                  "last_generated_at": 1.0})
    layer = run_paths.cgsa_config_layer_dir(ctx.root, ctx.symbol, ctx.tf, ch)
    other_layer = run_paths.cgsa_config_layer_dir(ctx.root, ctx.symbol, ctx.tf, other_ch)
    assert len([p for p in Path(layer).iterdir() if p.is_dir()]) == 2, "前提不成立：層下應有兩個 algorithm_id 葉"
    result = manager.delete_run(ctx.symbol, ctx.tf, ch)
    assert result.errors == [] and not Path(layer).exists() and Path(other_layer).is_dir()


# ============================================================================================== 邊界 50–52

@pytest.mark.parametrize("identity_text", ["", "{not json"], ids=["empty_file", "non_json"])
def test_boundary_50_identity_file_empty_or_non_json(ctx: Ctx, identity_text: str) -> None:
    """邊界③（Task 4.2）：身分檔為空檔或非 JSON ⇒ 視同不符：原樣移出為 `.stale-*`、建新葉（只含正確身分檔）、不續跑。"""
    assert mismatch_case(ctx, identity_text, f"b50-{len(identity_text)}") == MISMATCH_OK


def test_boundary_51_stale_name_collision_gets_sequence(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """邊界④（Task 4.2）：移出目的名已存在（時間戳固定）⇒ 時間戳加序號；既有 stale 目錄內容不被覆蓋，連續兩次各得新名。"""
    assert patch_everywhere(monkeypatch, "utc_stamp", run_paths.utc_stamp, lambda: FIXED_STAMP) >= 1
    ch, aid = _md5("numview-b51"), _sha("numview-b51")
    leaf = ctx.leaf(ch, aid)
    existing = Path(str(leaf) + ".stale-" + FIXED_STAMP)
    existing.mkdir(parents=True)
    (existing / "sentinel.txt").write_text("numview-existing-stale", encoding="utf-8")
    sentinel_before = snapshot(existing)
    names: List[str] = []
    for round_no in range(2):
        altered = _identity(ctx.symbol, ctx.tf, ch, aid)
        altered["tf"] = f"{altered['tf']}_numview_round{round_no}"
        seed_leaf(leaf, json.dumps(altered))
        ctx.l7(ch, aid)
        ctx.prepare(ch, aid)
        names = [p.name for p in stale_dirs(leaf)]
    assert snapshot(existing) == sentinel_before
    assert len(names) == 3 and len(set(names)) == 3
    assert all(n.startswith(leaf.name + ".stale-" + FIXED_STAMP) for n in names)
    assert ctx.resume.call_count == 0


def test_boundary_52_stale_dirs_kept_and_never_read(ctx: Ctx) -> None:
    """邊界⑤（Task 4.2）：`.stale-*` 不被自動刪除，其後同身分之新建與續跑皆不開其任何檔、內容不變。"""
    ch, aid = _md5("numview-b52"), _sha("numview-b52")
    altered = _identity(ctx.symbol, ctx.tf, ch, aid)
    altered["symbol"] = altered["symbol"] + "_numview_altered"
    leaf = ctx.leaf(ch, aid)
    seed_leaf(leaf, json.dumps(altered))
    ctx.l7(ch, aid)
    ctx.prepare(ch, aid)
    stale = stale_dirs(leaf)
    assert len(stale) == 1, "前提不成立：不符之葉未移為 .stale-*"
    before = snapshot(stale[0])
    events: List[Tuple[str, str]] = []
    with pytest.MonkeyPatch.context() as mp:
        install_open_spy(mp, [stale[0]], events)
        ctx.prepare(ch, aid)  # 新葉只有身分檔 ⇒ 不續跑
        (leaf / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
        resumed = ctx.prepare(ch, aid)  # 身分相符＋manifest＋完整 L7 ⇒ 續跑
    assert resumed == "resumed" and ctx.resume.call_count == 1
    assert stale[0].is_dir() and snapshot(stale[0]) == before and opens_under(events, stale[0]) == []


# ============================================================================================== mutation

def test_mutation_leaf_name_back_to_prefix(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：葉名改回 `config_hash[:8]`（不含 algorithm_id）⇒ (a) 兩條路徑相撞而紅。"""
    def prefix_leaf(root: Path, symbol: str, timeframe: str, config_hash: str, algorithm_id: str = "") -> Path:
        return (Path(root) / f"{run_paths.safe_token(symbol)}_{run_paths.safe_token(timeframe)}_{config_hash[:8]}").resolve()

    assert patch_everywhere(monkeypatch, "cgsa_work_dir", run_paths.cgsa_work_dir, prefix_leaf) >= 1
    assert prefix_collision_case(ctx)["distinct"] is False


def test_mutation_identity_check_after_manifest_read(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：身分檔比對移到 `manifest.json` 存在檢查（並讀取）之後 ⇒ (b) 之零讀取斷言紅。"""
    real = FeatureFactory._prepare_cgsa_registry

    def manifest_first(self: Any, symbol: str, timeframe: str, config_hash: str = "", algorithm_id: str = "") -> Any:
        leaf = run_paths.cgsa_work_dir(Path(os.getcwd()) / "data_cache" / "cgsa_work", symbol, timeframe, config_hash,
                                       algorithm_id)
        manifest = Path(leaf) / "manifest.json"
        if manifest.exists():
            with open(manifest, encoding="utf-8") as handle:
                json.load(handle)
        return real(self, symbol, timeframe, config_hash, algorithm_id=algorithm_id)

    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", manifest_first)
    assert algorithm_switch_case(ctx)["target_reads_before_registry"] != []


def test_mutation_mismatch_resumes(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：身分不符時改為沿用（閘所見之身分檔被視為相符）⇒ (c) 不續跑／移出之斷言紅。"""
    real = FeatureFactory._prepare_cgsa_registry

    def ignore_mismatch(self: Any, symbol: str, timeframe: str, config_hash: str = "", algorithm_id: str = "") -> Any:
        leaf = run_paths.cgsa_work_dir(Path(os.getcwd()) / "data_cache" / "cgsa_work", symbol, timeframe, config_hash,
                                       algorithm_id)
        if Path(leaf).is_dir():
            (Path(leaf) / _identity_name()).write_text(
                json.dumps(_identity(symbol, timeframe, config_hash, algorithm_id)), encoding="utf-8")
        return real(self, symbol, timeframe, config_hash, algorithm_id=algorithm_id)

    monkeypatch.setattr(FeatureFactory, "_prepare_cgsa_registry", ignore_mismatch)
    ch, aid = _md5("numview-m-c"), _sha("numview-m-c")
    altered = _identity(ctx.symbol, ctx.tf, ch, aid)
    altered["config_hash"] = altered["config_hash"] + "_numview_altered"
    case = mismatch_case(ctx, json.dumps(altered), "m-c")
    assert case["resumed"] == 1 and case != MISMATCH_OK


def test_mutation_override_root_used_as_leaf(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant：覆寫值改回直接當葉目錄（不分身分）⇒ (e) 不同身分之 run 落於同一目錄而紅。"""
    def root_as_leaf(root: Path, symbol: str, timeframe: str, config_hash: str, algorithm_id: str = "") -> Path:
        return Path(root).expanduser().resolve()

    assert patch_everywhere(monkeypatch, "cgsa_work_dir", run_paths.cgsa_work_dir, root_as_leaf) >= 1
    case = override_case(ctx, monkeypatch)
    assert case["distinct"] is False and case["under_root_not_root"] is False


def test_mutation_cgsa_work_dir_in_salt(ctx: Ctx, monkeypatch: pytest.MonkeyPatch) -> None:
    """mutant（Task 0.2 交叉）：`FFACT_CGSA_WORK_DIR` 改入鹽與 fingerprint ⇒ (e) 覆寫根下 run 之身分隨根路徑改變而紅。"""
    real = nv.resolve_numeric_fingerprint

    def root_in_salt(**kwargs: Any) -> Dict[str, Any]:
        return {**real(**kwargs), "numview_mutant_cgsa_root": dict(kwargs["environ"]).get(OVERRIDE_KEY)}

    monkeypatch.setattr(nv, "resolve_numeric_fingerprint", root_in_salt)
    assert identity_stable_across_override_roots(ctx, monkeypatch) is False
