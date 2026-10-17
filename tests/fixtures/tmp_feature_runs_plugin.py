"""共用 pytest 外掛：於 tmp 以真實 K 線物化測試所需之小型 FF run（TESTREG Task 4.4 資料修復組）。

出生理由：一批測試寫死本機 `data_cache/features/` 下之特定 run（`4a8a0b37…`、`5ea07439…`、
`e53e2290…`、`f754aad4…`），2026-10-03 刪舊特徵檔後恆 skip／紅。業界作法＝測試自足、
不依賴本機殘存資料 ⇒ 本外掛以 `data_cache/feature_klines/kline_cache.h5`（**真實 K 線**，禁合成）
與最小可行之真實 FF 設定，於 session 暫存目錄**按需**（lazy）物化 run。

🔴 隔離：一切寫入落在 tmp（run、registry、CGSA 工作目錄）；物化期間沿用
`tests/feature_engineering/fftfmeta_golden_helpers.prepare_env`（tmp 隔離＋cwd 暫移 tmp），
**不碰**正式 `data_cache/features`／`registry.json`／`cgsa_work`／`reports`。

run 分組（同組一次物化、固定順序，故「latest」語意可預期）：
- `1h_long`：ETHUSDT、BCHUSDT 1h，同設定同日期窗 ⇒ **同一 config_hash 橫跨兩 symbol**
  （config_hash 含設定、日期窗、K 線末根時刻；兩幣 K 線末根相同）。日期窗自 K 線起點起，
  涵蓋各測試之事件批（2024-01 之受控事件、2025-01～2026-03 之落檔事件批）。
- `1h_short`：ETHUSDT 1h，起點恰為事件批 `20260909T130533Z-7f73e4c7` 最早事件之 t0
  ⇒ 該事件之特徵列鍵（前一根 1h 開盤）落在 post-trim 索引外而 coverage 仍涵蓋（「恰 1 筆界外」）。
- `12h`（2024-12-01 至 K 線末根）：設定 A 依序物化 BTCUSDT、ETHUSDT、BCHUSDT（同 hash 跨三幣），再以設定 B 物化
  BTCUSDT、ETHUSDT（B 後生成 ⇒ BTC／ETH 12h 之 latest 為 B；A、B 列數相同、特徵集不同）。

設定皆含 `momentum` 類 BOP（逐根 (close-open)/(high-low)，可對 K 線逐值對證）。
"""

from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

REPO = Path(__file__).resolve().parents[2]

#: 各 run 之規格：名稱 → (群組, symbol, timeframe, 設定名, start_date, end_date)
_LONG_1H_WINDOW = ("2024-01-01", "2026-03-10")
_SHORT_1H_WINDOW = ("2025-01-02", "2026-03-10")
#: 12h 迄日越過 K 線末根（2026-04-27 12:00）⇒ run 末列即 K 線末根，其 forward 標籤必無下一根（NaN）
_WINDOW_12H = ("2024-12-01", "2026-04-28")

RUN_SPECS: Dict[str, Tuple[str, str, str, str, str, str]] = {
    "eth_1h": ("1h_long", "ETHUSDT", "1h", "cfg_1h", *_LONG_1H_WINDOW),
    "bch_1h": ("1h_long", "BCHUSDT", "1h", "cfg_1h", *_LONG_1H_WINDOW),
    "eth_1h_short": ("1h_short", "ETHUSDT", "1h", "cfg_1h", *_SHORT_1H_WINDOW),
    "btc_12h_a": ("12h", "BTCUSDT", "12h", "cfg_12h_a", *_WINDOW_12H),
    "eth_12h_a": ("12h", "ETHUSDT", "12h", "cfg_12h_a", *_WINDOW_12H),
    "bch_12h_a": ("12h", "BCHUSDT", "12h", "cfg_12h_a", *_WINDOW_12H),
    "btc_12h_b": ("12h", "BTCUSDT", "12h", "cfg_12h_b", *_WINDOW_12H),
    "eth_12h_b": ("12h", "ETHUSDT", "12h", "cfg_12h_b", *_WINDOW_12H),
}
#: 群組內物化順序（dict 插入序即生成序）
_GROUP_ORDER: Dict[str, List[str]] = {}
for _name, _spec in RUN_SPECS.items():
    _GROUP_ORDER.setdefault(_spec[0], []).append(_name)


def _payload(timeframe: str, rolling_windows: List[int]) -> Dict[str, Any]:
    """最小可行之真實 FF 設定：只 close 資料源、atomic 只開 momentum 之 BOP／RSI、L6.5 只開縮尾。"""
    from tests.feature_engineering.fftfmeta_golden_helpers import HEALTHY, fast_payload
    from tests.feature_engineering.ff_truncation_mr_helpers import _ALL_ATOMIC_CATEGORIES

    cfg = fast_payload([timeframe], **copy.deepcopy(HEALTHY))
    cfg["timeframes"] = {"primary": timeframe, "training": [timeframe], "alignment_mode": "open_minus"}
    cfg["atomic_indicators"] = {c: {"enabled": False} for c in _ALL_ATOMIC_CATEGORIES}
    cfg["atomic_indicators"]["momentum"] = {
        "enabled": True,
        "indicators": [{"name": "BOP"}, {"name": "RSI", "periods": [14]}],
    }
    cfg["rolling_aggregation"] = {"enabled": True, "windows": list(rolling_windows)}
    return cfg


_CONFIGS = {
    "cfg_1h": lambda: _payload("1h", [5]),
    "cfg_12h_a": lambda: _payload("12h", [5, 13]),
    "cfg_12h_b": lambda: _payload("12h", [5]),
}


@dataclass(frozen=True)
class MaterializedRun:
    """一個已物化之 tmp run。`index_s`＝生成當下之主時間軸（epoch 秒 int64，供獨立比對）。"""

    name: str
    symbol: str
    timeframe: str
    config_hash: str
    run_dir: Path
    start_date: str
    end_date: str
    index_s: "np.ndarray" = field(repr=False, compare=False)

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "feature_manifest.json"


class TmpFeatureRuns:
    """session 範圍之 tmp run 倉：`get(name)` 首次請求時物化該 run 所屬群組。"""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.features_root = root / "data_cache" / "features"
        self.registry = self.features_root / "registry.json"
        self._runs: Dict[str, MaterializedRun] = {}
        self.timings_s: Dict[str, float] = {}

    def get(self, name: str) -> MaterializedRun:
        if name not in RUN_SPECS:
            raise KeyError(f"未知之 tmp run 名稱：{name}（可用：{sorted(RUN_SPECS)}）")
        if name not in self._runs:
            self._materialize_group(RUN_SPECS[name][0])
        return self._runs[name]

    def _materialize_group(self, group: str) -> None:
        import numpy as np
        import pandas as pd

        from momentum.factories import create_feature_factory
        from momentum.FeatureEngineering.feature_storage import FeatureStorage
        from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, prepare_env

        started = time.perf_counter()
        mp = pytest.MonkeyPatch()
        try:
            prepare_env(mp, self.root)
            mp.setenv("FFACT_FEATURE_REGISTRY_PATH", str(self.registry))
            for name in _GROUP_ORDER[group]:
                _grp, symbol, tf, cfg_name, start, end = RUN_SPECS[name]
                factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
                factory._storage = FeatureStorage(str(self.features_root))
                result = factory.generate_features(
                    symbol, tf, config_override=_CONFIGS[cfg_name](), force_regenerate=True,
                    start_date=start, end_date=end, persist=True,
                )
                index = result.features_df.index
                if isinstance(index, pd.DatetimeIndex):
                    seconds = index.view("int64") // 10**9
                else:  # 生成結果之主時間軸為 epoch 秒之整數 index
                    seconds = np.asarray(index, dtype="int64")
                config_hash = str(result.metadata["config_hash"])
                self._runs[name] = MaterializedRun(
                    name=name, symbol=symbol, timeframe=tf, config_hash=config_hash,
                    run_dir=self.features_root / symbol / tf / config_hash,
                    start_date=start, end_date=end,
                    index_s=np.array(seconds, dtype="int64", copy=True),
                )
        finally:
            mp.undo()
        self.timings_s[group] = time.perf_counter() - started
        self._check_group(group)

    def _check_group(self, group: str) -> None:
        """物化前提不符 ⇒ fixture 錯誤（fail-closed；以 raise 而非 assert）。"""
        if not self.registry.is_file():
            raise RuntimeError(f"tmp registry 未產生：{self.registry}")
        for name in _GROUP_ORDER[group]:
            run = self._runs[name]
            for required in ("feature_manifest.json", "timestamps.parquet", "raw"):
                if not (run.run_dir / required).exists():
                    raise RuntimeError(f"tmp run {name} 缺 {required}：{run.run_dir}")
            manifest = json.loads(run.manifest_path.read_text(encoding="utf-8"))
            tr = manifest.get("time_range") if isinstance(manifest, dict) else None
            if not (isinstance(tr, dict) and tr.get("start") and tr.get("end")):
                raise RuntimeError(f"tmp run {name} 之 manifest 無 time_range：{tr!r}")
        if group == "1h_long" and self._runs["eth_1h"].config_hash != self._runs["bch_1h"].config_hash:
            raise RuntimeError("同設定同日期窗之 ETH／BCH 1h run 未得同一 config_hash（跨 symbol 前提不成立）")
        if group == "12h":
            a = {self._runs[n].config_hash for n in ("btc_12h_a", "eth_12h_a", "bch_12h_a")}
            b = {self._runs[n].config_hash for n in ("btc_12h_b", "eth_12h_b")}
            if len(a) != 1 or len(b) != 1 or a == b:
                raise RuntimeError(f"12h 設定 A／B 之 config_hash 前提不成立：A={a} B={b}")


@pytest.fixture(scope="session")
def tmp_feature_run_store(tmp_path_factory: pytest.TempPathFactory) -> TmpFeatureRuns:
    """session 範圍之 tmp run 倉（lazy：不呼叫 `get` 就不物化任何 run）。"""
    return TmpFeatureRuns(tmp_path_factory.mktemp("tmp_feature_runs"))


class TmpFeatureRunEnv:
    """單一測試期間之 run 定位重導（不 chdir）；`activate(*names)` 物化並回傳指定 run。

    重導內容（皆經 `monkeypatch`，測試結束自動還原）：
    - `canonical_holdout._FEATURES_DIR`（`resolve_run_dir` 之根）改為 tmp 之絕對路徑；
    - `FFACT_FEATURE_REGISTRY_PATH` 指向 tmp registry 之**本測試複本**（測試對 registry 之寫入
      不污染 session 倉，亦不碰正式 registry）；
    - `FeatureStorage`／`FeatureReader` 之預設根改為 tmp（`create_feature_library()` 無參建構時用之）。
    """

    def __init__(self, store: TmpFeatureRuns, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self.store = store
        self._mp = monkeypatch
        self.registry = tmp_path / "tmp_runs_registry.json"

    def activate(self, *names: str) -> Dict[str, MaterializedRun]:
        from momentum import factories
        from momentum.Analysis.event_samples import canonical_holdout
        from momentum.FeatureEngineering.feature_reader import FeatureReader
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        runs = {name: self.store.get(name) for name in names}   # 物化須在重導之前（其內自行隔離 cwd／env）
        features_root = str(self.store.features_root)
        self._mp.setattr(canonical_holdout, "_FEATURES_DIR", features_root)
        self._mp.setattr(FeatureStorage.__init__, "__defaults__", (features_root,))
        self._mp.setattr(FeatureReader.__init__, "__defaults__", (features_root,))
        # `create_feature_reader(feature_base_path=None)` 內以 `or "data_cache/features"` 兜底 ⇒ 改其預設值
        self._mp.setattr(factories.create_feature_reader, "__defaults__", (features_root,))
        self.registry.write_text(self.store.registry.read_text(encoding="utf-8"), encoding="utf-8")
        self._mp.setenv("FFACT_FEATURE_REGISTRY_PATH", str(self.registry))
        return runs


@pytest.fixture
def tmp_feature_run_env(tmp_feature_run_store: TmpFeatureRuns, monkeypatch: pytest.MonkeyPatch,
                        tmp_path: Path) -> TmpFeatureRunEnv:
    """函式範圍：取得 `TmpFeatureRunEnv`，於測試內呼叫 `activate(...)` 才物化／重導。"""
    return TmpFeatureRunEnv(tmp_feature_run_store, monkeypatch, tmp_path)
