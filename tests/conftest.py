from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pytest

# TESTSEL-HERMETIC（2026-11-14，TESTSEL I7 後查出）：測試不得寫正式資料根。實查正式
# `data_cache/features/registry.json` 90 筆中 57 筆指向已刪之 pytest 暫存目錄（測試以預設 registry 登記 run；
# FeatureFactory／create_feature_library() 未給根時之 `FeatureRegistry()`），另有 API case 流程以
# `FeatureStorage()` 預設根寫 `<case_id>.h5`。只改這兩個「未給路徑時之預設值」（只在測試行程），呼叫端明給之根、
# `FFACT_FEATURE_REGISTRY_PATH` 覆寫等語意一概不動（不設環境變數：該變數於產品覆寫一切明給之根，全域設定會改變
# 明給根之測試語意）。服務單例於模組匯入時即建（早於任何 fixture），故於本檔載入、任何 api／momentum 匯入之前生效。
# CGSA 工作根預設（`run_paths.default_cgsa_root`）之重導見本檔末段（2026-11-15）；其餘正式根寫入由 session 結束之
# 正式根寫入偵測（tests/fixtures/hermetic_guard_plugin.py，data_cache 全樹）具名列出。tests/feature_engineering/conftest.py 之每測試隔離維持不變。
import tempfile as _tempfile

_HERMETIC_TMP = _tempfile.TemporaryDirectory(prefix="testsel_hermetic_")  # 行程結束自刪
HERMETIC_ROOT = Path(_HERMETIC_TMP.name)

# TESTSEL I1f（SPEC Task 3.2 目標①）：NUMVIEW 批次共用生成快取根（tests/feature_engineering/numview_helpers.py
# `regen_batch_root()`）預設改為本 session 暫存根，不跨 session／工作樹沿用（原預設 $TMPDIR/numview-regen-batch 之鍵不含
# 測試碼與套件版本）；明給 NUMVIEW_REGEN_BATCH_ROOT 者照舊尊重。測試專用變數，不影響產品語意。
import os as _os

_os.environ.setdefault("NUMVIEW_REGEN_BATCH_ROOT", str(HERMETIC_ROOT / "numview-regen-batch"))
try:
    from momentum.FeatureEngineering import feature_registry as _feature_registry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage as _FeatureStorage

    _feature_registry.DEFAULT_REGISTRY_PATH = HERMETIC_ROOT / "features" / "registry.json"
    _FeatureStorage.__init__.__defaults__ = (str(HERMETIC_ROOT / "features"),)
except ModuleNotFoundError:  # CI 輕量環境（見下段 P1-5）
    pass

# P1-5(2026-07-24):治理守衛測試(tests/governance)自足,不需 pandas/momentum/h5py 等 IC 重依賴。
# 為讓 CI 用輕量環境(僅 pytest+pyyaml)跑治理測試,IC 專用的重 import 缺依賴時容錯跳過:
#   本機(全依賴)→ 正常載入,IC 測試 fixture 行為不變;
#   CI(輕量)→ 這些名字為 None,但**只有 IC 測試 fixture/hook 會用到它們**,治理測試不碰 → 不炸。
# (`from __future__ import annotations` 使 `-> pd.DataFrame` 等註解為字串,import 期不需 pandas。)
try:
    import pandas as pd
    from momentum.factories import create_kline_storage_manager
    from scripts.build_l65_golden import (
        TEST_INVENTORY_PATH,
        make_synthetic_l65_dataset,
        write_test_inventory_from_nodeids,
    )
    from tests.fixtures.data_manifest import (
        ManifestValidationError,
        verify_kline_entry,
    )
    _IC_DEPS_AVAILABLE = True
except ModuleNotFoundError:  # CI 輕量環境:IC 依賴缺 → 治理測試仍可跑
    pd = None  # type: ignore[assignment]
    create_kline_storage_manager = None  # type: ignore[assignment]
    TEST_INVENTORY_PATH = make_synthetic_l65_dataset = write_test_inventory_from_nodeids = None  # type: ignore[assignment]
    ManifestValidationError = KeyError  # type: ignore[assignment,misc]
    verify_kline_entry = None  # type: ignore[assignment]
    _IC_DEPS_AVAILABLE = False

# 離線鐵則(IC1C TODO r7 / codex B2-B2):在任何測試模組 import api.main 之前
# stub Binance Client.ping,避免 collect/TestClient lifespan 觸外網。
# 沿用 ic_persist_redirect 的「fixture/conftest 層隔離」模式(模組載入時生效)。
try:
    from binance.client import Client as _BinanceClient

    _BinanceClient.ping = lambda self: {}  # type: ignore[method-assign]
except Exception:  # pragma: no cover - binance 未安裝時略過
    pass

pytest_plugins = [
    "tests.fixtures.ic_persist_redirect_plugin",
    "tests.fixtures.testreg_recorder_plugin",
    "tests.fixtures.tmp_feature_runs_plugin",  # TESTREG Task 4.4：tmp 物化真實 FF run（lazy）
    "tests.fixtures.hermetic_guard_plugin",  # TESTSEL I1a Task 1.1／1.4：data_cache 全樹寫入偵測、root handler 外洩清理
    "tests.fixtures.hardware_gate_plugin",  # TESTSEL I4e：本機記憶體不足之 RM-FULLSCALE 登記檔收集期具名 deselect
    "tests.fixtures.fullscale_layer_plugin",  # TESTSEL I4f：全規模層（fullscale）預設延後，--run-fullscale 執行
]

FEATURE_KLINE_CACHE_DIR = "data_cache/feature_klines"
FEATURE_KLINE_H5_PATH = Path(FEATURE_KLINE_CACHE_DIR) / "kline_cache.h5"


# TESTSEL-SEED BEGIN（tests/registry/test_conftest_seed.py::test_fixed_seed_order_independent 擷取本段驗收）
_SEED_BASE = 20261026
_MODULE_RNG_STATES: Dict[int, Dict[str, Any]] = {}


def _rng_state_get(obj: Any) -> Any:
    """亂數產生器物件之可還原狀態（numpy Generator／RandomState、random.Random）；非產生器 ⇒ None。"""
    import random as _random

    try:
        import numpy as _np
    except ModuleNotFoundError:  # pragma: no cover - 輕量環境
        _np = None  # type: ignore[assignment]
    if _np is not None and isinstance(obj, _np.random.Generator):
        return ("gen", obj.bit_generator.state)
    if _np is not None and isinstance(obj, _np.random.RandomState):
        return ("rs", obj.get_state())
    if isinstance(obj, _random.Random):
        return ("py", obj.getstate())
    return None


def _rng_state_set(obj: Any, state: Any) -> None:
    kind, value = state
    if kind == "gen":
        obj.bit_generator.state = value
    elif kind == "rs":
        obj.set_state(value)
    else:
        obj.setstate(value)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """TESTSEL（docs/TEST_SELECTION.md §6 第 5 項）：結果不依賴測試順序與選取子集（業界常規：pytest-randomly 之固定
    種子模式；同其以 `pytest_runtest_setup` hook 實作、不以 autouse fixture——不改任何測試之 fixture 閉包，
    TESTREG 碑收據綁定之 fixture_closure_sha256 不受影響）。每條測試之 fixture 建立前：
    ① 全域 `random` 與 `numpy.random` 以「固定基值＋nodeid 之 sha256」重設種子（同一 nodeid 恆同一種子）；
    ② 測試模組層之亂數產生器物件（numpy Generator／RandomState、random.Random；import 時建立、各測試共用者）還原為
       該模組首次執行測試前之狀態（＝import 完成時），使各測試所得序列不受同模組先跑之測試消耗量影響。
    測試內（或 function 範圍之 fixture／setup_method 內）自設種子者照常覆寫（其後執行）。非 function 範圍之 fixture
    另由下方 `pytest_fixture_setup` hook 以其範圍節點與名稱定種子並於建立後還原狀態。"""
    import hashlib
    import random as _random

    digest = hashlib.sha256(item.nodeid.encode("utf-8")).digest()
    seed = (_SEED_BASE + int.from_bytes(digest[:4], "big")) % (2 ** 32)
    _random.seed(seed)
    try:
        import numpy as _np

        _np.random.seed(seed)
    except ModuleNotFoundError:  # pragma: no cover - 輕量環境
        pass
    module = getattr(item, "module", None)
    if module is None:
        return
    saved = _MODULE_RNG_STATES.get(id(module))
    if saved is None:
        saved = {}
        for name, obj in list(vars(module).items()):
            state = _rng_state_get(obj)
            if state is not None:
                saved[name] = state
        _MODULE_RNG_STATES[id(module)] = saved
    for name, state in saved.items():
        obj = getattr(module, name, None)
        if obj is not None and _rng_state_get(obj) is not None:
            _rng_state_set(obj, state)


# TESTSEL-SEED-FIXTURE BEGIN
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_fixture_setup(fixturedef: Any, request: Any) -> Any:
    """TESTSEL：非 function 範圍（class／module／package／session）之 fixture 只在第一個用到它之測試建立，其亂數輸入
    原依該測試之種子與先前消耗而變（全檔跑與子集跑不同）。本 hook（非 fixture，不改任何 fixture 閉包）於其函式執行前
    以「固定基值＋範圍＋範圍節點 nodeid＋fixture 名」重設全域 `random`／`numpy.random` 種子；執行後把全域與該模組層
    亂數產生器還原為執行前狀態——觸發它之測試其後所得序列與未觸發時相同。"""
    if getattr(fixturedef, "scope", "function") == "function":
        yield
        return
    import hashlib
    import random as _random

    try:
        import numpy as _np
    except ModuleNotFoundError:  # pragma: no cover - 輕量環境
        _np = None  # type: ignore[assignment]
    node = getattr(request, "node", None)
    key = f"{fixturedef.scope}:{getattr(node, 'nodeid', '')}:{fixturedef.argname}"
    seed = (_SEED_BASE + int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:4], "big")) % (2 ** 32)
    saved_py = _random.getstate()
    saved_np = _np.random.get_state() if _np is not None else None
    try:
        module = request.module
    except Exception:  # session 範圍無 module
        module = None
    saved_mod = {}
    for name, obj in (list(vars(module).items()) if module is not None else []):
        state = _rng_state_get(obj)
        if state is not None:
            saved_mod[name] = state
    _random.seed(seed)
    if _np is not None:
        _np.random.seed(seed)
    try:
        yield
    finally:
        _random.setstate(saved_py)
        if _np is not None:
            _np.random.set_state(saved_np)
        for name, state in saved_mod.items():
            obj = getattr(module, name, None)
            if obj is not None and _rng_state_get(obj) is not None:
                _rng_state_set(obj, state)
# TESTSEL-SEED-FIXTURE END
# TESTSEL-SEED END


@pytest.fixture(scope="session")
def synthetic_l65_dataset() -> pd.DataFrame:
    """Deterministic Layer 6.5 fixture: 1000 rows x 100 mixed-stationarity columns."""

    return make_synthetic_l65_dataset(rows=1000, cols=100, stationary_ratio=0.6)


@pytest.fixture
def ic_first_factory(tmp_path: Path) -> Callable[[str, str], Dict[str, Path]]:
    """Return isolated IC-First scaffold paths for tests."""

    def _factory(symbol: str = "SYNTHETIC", tf: str = "fixture") -> Dict[str, Path]:
        run_dir = tmp_path / "features" / symbol / tf / "ic_first"
        raw_dir = run_dir / "raw"
        processed_dir = run_dir / "processed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        return {
            "run_dir": run_dir,
            "raw_dir": raw_dir,
            "processed_dir": processed_dir,
            "selected_path": run_dir / f"ic_selected_features_{symbol}_{tf}.json",
        }

    return _factory


@pytest.fixture
def requires_kline_data() -> Callable[..., pd.DataFrame]:
    """Factory fixture：要求真實 kline；缺檔或列數不足時 pytest.fail（非 skip）。"""

    def _require(
        symbol: str,
        timeframe: str,
        *,
        min_rows: Optional[int] = None,
        verify_manifest: bool = True,
    ) -> pd.DataFrame:
        if not FEATURE_KLINE_H5_PATH.is_file():
            pytest.fail(
                f"requires_kline: missing kline cache file: {FEATURE_KLINE_H5_PATH}"
            )

        if verify_manifest:
            try:
                verify_kline_entry(
                    symbol,
                    timeframe,
                    cache_dir=FEATURE_KLINE_CACHE_DIR,
                    min_rows=min_rows,
                )
            except (ManifestValidationError, KeyError) as exc:
                pytest.fail(f"requires_kline manifest mismatch: {exc}")

        storage = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)
        try:
            df = storage.read_klines(symbol, timeframe, validate_continuity=False)
        except Exception as exc:
            pytest.fail(
                f"requires_kline: failed reading {symbol}/{timeframe}: {exc}"
            )

        if df is None or df.empty:
            pytest.fail(
                f"requires_kline: no data for {symbol}/{timeframe} in {FEATURE_KLINE_H5_PATH}"
            )

        effective_min = min_rows if min_rows is not None else 1
        if len(df) < effective_min:
            pytest.fail(
                f"requires_kline: {symbol}/{timeframe} has {len(df)} rows, "
                f"need >= {effective_min}"
            )
        return df

    return _require


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: Any) -> None:
    """TESTSPEED（使用者 2026-09-29 裁定方向 B）：預設「上次失敗者先跑」（pytest 內建 --ff；不略過任何測試、
    只調整順序，修完後先看到原失敗者之結果）。只在 cacheprovider 啟用時生效——治理腳本以 `-p no:cacheprovider`
    呼叫者不受影響（寫入 addopts 會使其 `unrecognized arguments: --ff`）；使用者明示 --lf／--ff／--nf 時不覆寫。"""
    if not config.pluginmanager.has_plugin("cacheprovider"):
        return
    option = config.option
    if not any(getattr(option, name, False) for name in ("lf", "failedfirst", "newfirst")):
        option.failedfirst = True


# 正式資料根寫入偵測（data_cache 全樹、測試時段內寫入 ⇒ session 非零）：tests/fixtures/hermetic_guard_plugin.py
# （TESTSEL I1a Task 1.1；取代原「只報 data_cache/features、cgsa_work 兩頂層目錄」之偵測）。
#
# L6.5 測試清單 `tests/golden/l65/test_inventory.txt` 之正式產生者為 `scripts/build_l65_golden.collect_existing_l65_tests`
# （自行解析 collect-only 輸出寫檔）。原本此處於「任何」`--collect-only` 皆改寫入庫清單，致子集收集改寫 golden
# （TESTSEL I1a 實測：test_l65_golden_inventory_exists 與手動 collect 皆改寫）⇒ 移除（Task 1.5）。


# TESTSEL-HERMETIC（2026-11-15，收尾 E6）：CGSA 工作根「呼叫端未給根、未設 FFACT_CGSA_WORK_DIR」時之預設
# （`run_paths.default_cgsa_root`，相對路徑依當下 cwd 解析）若落在正式 data_cache ⇒ 改指本 session 暫存。
# 不設環境變數：該變數使 run_lifecycle 刪除改走「跳過 CGSA」分支（run_lifecycle.py:141），全域設定會令刪除測試失去覆蓋；
# 亦會入執行環境指紋。cwd 已切到他處（如 tmp_path）之測試維持依 cwd 之原語意。
try:
    from momentum.FeatureEngineering import run_paths as _run_paths

    _ORIG_DEFAULT_CGSA_ROOT = _run_paths.default_cgsa_root
    PROD_DATA_CACHE = (Path(__file__).resolve().parent.parent / "data_cache").resolve()

    def hermetic_default_cgsa_root() -> Path:
        """預設 CGSA 根解析後落在正式 data_cache（含經符號連結）⇒ session 暫存；否則原值。"""
        rel = _ORIG_DEFAULT_CGSA_ROOT()
        resolved = (Path.cwd() / rel).resolve()
        if resolved == PROD_DATA_CACHE or PROD_DATA_CACHE in resolved.parents:
            return HERMETIC_ROOT / "cgsa_work"
        return rel

    _run_paths.default_cgsa_root = hermetic_default_cgsa_root
except ModuleNotFoundError:  # CI 輕量環境（見 P1-5）
    pass
