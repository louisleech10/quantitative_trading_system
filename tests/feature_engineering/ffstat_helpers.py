"""FF-STAT 驗收之共用 helper（docs/FFSTAT_SPEC.md §G、Task 1.1–4.1）。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）輕量設定：close 資料源、L1 trend、L2 只開 Ratio／Cross、
L3 rolling 5／13、L6.5 開 fracdiff（L1、L2）與 ADF 差分；輸出窗 `WINDOW` 之前留有足夠前史。
一切寫入經 `fftfmeta_golden_helpers.prepare_env` 隔離於 tmp。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.fftfmeta_golden_helpers import (
    HEALTHY,
    KLINE_DIR,
    PRIMARY_TF,
    SYMBOL,
    WINDOW,
    fast_payload,
    prepare_env,
)

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / "_golden" / "ffstat" / "contract.json").read_text(encoding="utf-8"))
META = CONTRACT["metadata_keys"]
EVENTS = CONTRACT["events"]
BASELINE_PATH = Path(__file__).resolve().parents[1] / "_golden" / "ffstat" / "baseline.json"

__all__ = [
    "CONTRACT", "META", "EVENTS", "BASELINE_PATH", "PRIMARY_TF", "SYMBOL", "WINDOW",
    "prepare_env", "stat_payload", "run_stat", "decisions",
]


def prepare_stat_env(monkeypatch: Any, tmp_path: Path, **env: str) -> Path:
    """`prepare_env` ＋把 d* 快取目錄導向 tmp（現行 `_d_star_cache_dir` 固定指向專案 data_cache，不受環境變數影響）。
    回傳隔離之 d* 快取目錄（§G：兩次 run 皆以各自隔離之空 d* 快取執行）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    import tempfile

    tmp_path.mkdir(parents=True, exist_ok=True)  # 子目錄（如 tmp_path / "on"）須先存在：prepare_env 會 chdir 進去
    prepare_env(monkeypatch, tmp_path, **env)
    target = tmp_path / "dstar_cache"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: target))
    # 本測試之系統暫存導向 <tmp>/sys_tmp（契約 test_tmp_isolation）：校準暫存殘留只查此處，不掃全系統 tmp
    sys_tmp = tmp_path / "sys_tmp"
    sys_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(sys_tmp))
    return target


def sys_tmp(tmp_path: Path) -> Path:
    """`prepare_stat_env` 所設之本測試系統暫存目錄。"""
    return tmp_path / "sys_tmp"


def first_output_timestamp(root: Path):
    """落盤基礎欄之第一列時間（讀任一基礎欄 parquet 之 timestamp 欄或 index）。"""
    import pandas as pd
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet"):
            continue
        frame = pq.read_table(p).to_pandas()
        if "timestamp" in frame.columns:
            ts = frame["timestamp"].iloc[0]
            return pd.to_datetime(ts, unit="ms", utc=True) if isinstance(ts, (int, float)) else pd.Timestamp(ts)
        return pd.Timestamp(frame.index[0])
    raise AssertionError("無基礎欄 parquet")


def stat_payload(training_tfs: Optional[List[str]] = None, *, fracdiff: bool = True, adf: bool = True,
                 cross_sectional: bool = False, **overrides: Any) -> Dict[str, Any]:
    """開平穩化之輕量真實設定（§G）。"""
    payload = fast_payload(list(training_tfs or [PRIMARY_TF]), **HEALTHY)
    payload["operators"] = {
        "enabled": True,
        "distance": {"enabled": False},
        "cross": {"enabled": True},
        "momentum": {"enabled": False},
        "ratio": {"enabled": True},
        "binary_signal": {"enabled": False},
        "worldquant": {"enabled": False},
    }
    payload["lag_features"] = {"enabled": False}  # L4 延遲欄於本票驗收無用途，關閉以控時長
    pre = payload["preprocessing"]
    pre["fractional_differencing"] = {"enabled": fracdiff, "apply_to": "non_stationary"}
    pre["adf_differencing"] = {"enabled": adf, "apply_to": "non_stationary"}
    if cross_sectional:
        # 參考標的預設 BTCUSDT 與本 helper 之 SYMBOL 相同 ⇒ L5 不適用（empty_not_applicable；b3b 實跑）⇒ 改以 ETHUSDT 為參考
        payload["cross_sectional"] = {"enabled": True, "reference_symbol": "ETHUSDT"}
    payload.update(overrides)
    return payload


def run_stat(tmp_path: Path, payload: Dict[str, Any], *, start_date: Optional[str] = WINDOW[0],
             end_date: Optional[str] = WINDOW[1], primary_tf: str = PRIMARY_TF, persist: bool = True,
             force_regenerate: bool = True, kline_dir: str = KLINE_DIR) -> Tuple[Path, Any, Any]:
    """真實 kline 之 generate_features；回傳 (features_root, factory, result)。`start_date=None` 驗 Task 2.3；
    `kline_dir` 指向真實 kline 之 tmp 複本以驗洩漏證偽（改值只改複本）。"""
    root = tmp_path / "features"
    factory = create_feature_factory(cache_dir=kline_dir, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    result = factory.generate_features(
        SYMBOL, primary_tf, config_override=payload, force_regenerate=force_regenerate,
        start_date=start_date, end_date=end_date, persist=persist,
    )
    return root, factory, result


def decisions(result: Any) -> Dict[str, Dict[str, Any]]:
    """結果 metadata 之逐欄平穩化決策（契約 `metadata_keys.decisions`；Task 4.1 收據同源）。"""
    return dict(result.metadata[META["decisions"]])


def snapshot_tree(root: Path) -> Dict[str, str]:
    """目錄下每個檔之相對路徑 → sha256（零寫入斷言用）。"""
    import hashlib

    out: Dict[str, str] = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def kline_frame(symbol: str = SYMBOL, timeframe: str = PRIMARY_TF):
    """讀真實 `kline_cache.h5` 之 `<symbol>/<tf>/data` 為 DataFrame（UTC DatetimeIndex 升序；來源欄 float64）。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(Path(KLINE_DIR) / "kline_cache.h5", "r") as f:
        arr = f[symbol][timeframe]["data"][()]
    ts = arr["timestamp"].astype("int64")
    unit = "ms" if ts.max() > 10**12 else "s"
    idx = pd.to_datetime(ts, unit=unit, utc=True)
    cols = [n for n in arr.dtype.names if n != "timestamp"]
    frame = pd.DataFrame({c: arr[c].astype(np.float64) for c in cols}, index=idx)
    return frame.sort_index()


def kline_copy(tmp_path: Path) -> Path:
    """真實 kline 之 tmp 複本目錄（洩漏證偽：只改複本之值）。"""
    import shutil

    target = tmp_path / "klines"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(KLINE_DIR) / "kline_cache.h5", target / "kline_cache.h5")
    return target


def scale_kline_close(kline_dir: Path, start: str, end: str, factor: float, *, symbol: str = SYMBOL,
                      timeframe: str = PRIMARY_TF) -> int:
    """把複本中 `[start, end)` 之 close 乘以 `factor`（原地改複本）；回傳改動列數。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(kline_dir / "kline_cache.h5", "r+") as f:
        ds = f[symbol][timeframe]["data"]
        arr = ds[()]
        ts = arr["timestamp"].astype("int64")
        unit = "ms" if ts.max() > 10**12 else "s"
        idx = pd.to_datetime(ts, unit=unit, utc=True)
        mask = (idx >= pd.Timestamp(start, tz="UTC")) & (idx < pd.Timestamp(end, tz="UTC"))
        arr["close"][np.asarray(mask)] = arr["close"][np.asarray(mask)] * np.float32(factor)
        ds[...] = arr
        return int(mask.sum())


def drop_kline_rows_before(kline_dir: Path, before: str, *, symbol: str, timeframe: str = PRIMARY_TF) -> int:
    """把複本中 `before` 之前之列刪除（真實資料、以刪列模擬晚上市之標的；重建 dataset 並保留屬性）；回傳刪除列數。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(kline_dir / "kline_cache.h5", "r+") as f:
        group = f[symbol][timeframe]
        arr = group["data"][()]
        attrs = dict(group["data"].attrs)
        ts = arr["timestamp"].astype("int64")
        unit = "ms" if ts.max() > 10**12 else "s"
        keep = np.asarray(pd.to_datetime(ts, unit=unit, utc=True) >= pd.Timestamp(before, tz="UTC"))
        del group["data"]
        ds = group.create_dataset("data", data=arr[keep], maxshape=(None,), chunks=True)
        for key, value in attrs.items():
            ds.attrs[key] = value
        return int((~keep).sum())


def derived_fingerprints(root: Path) -> Dict[str, str]:
    """root 下全部 L6.5 衍生欄（`*_L65.parquet`）之 欄名 → 值 sha256（NaN mask 併入）；
    決策與 d 相同 ⇔ 衍生欄集合與值相同（append 模式）。"""
    import hashlib

    import numpy as np
    import pyarrow.parquet as pq

    out: Dict[str, str] = {}
    for p in sorted(root.rglob("*_L65.parquet")):
        table = pq.read_table(p)
        for n in table.column_names:
            if n in ("timestamp", "__index_level_0__", "index"):
                continue
            arr = np.asarray(table.column(n).to_numpy(zero_copy_only=False), dtype=np.float64)
            mask = np.isnan(arr)
            out[n] = hashlib.sha256(mask.tobytes() + np.where(mask, 0.0, arr).tobytes()).hexdigest()
    return out
IC_FIRST_OFF_ENV = {"FFACT_WARMUP_TRIM": "1", "FFACT_USE_CGSA": "0"}


def ic_first_to_l65(factory: Any, config: Any, **kwargs: Any) -> Optional[Any]:
    """呼叫 `run_ic_first`；回傳結果，或於 IC 階段既有之 `AlignmentViolationError` 時回傳 None。

    既有退化（主委實跑 2026-09-24，與本票無關、另立票）：真實 kline 下 `ICEngine._align_label_to_group`
    之 label 為時間戳 index、自 L7 raw 讀回之群組為 RangeIndex ⇒ IC 階段必拋（`test_b6_warmup_trim.py::
    test_warmup_trim_ic_first` 於 main 同紅）。FF-STAT 之決策與平穩化產出皆於 L6.5 形成、經 `write_raw`
    於 IC 階段之前落盤 ⇒ 驗收改在 L6.5 產物觀測。只吞此一型且須 L7 raw 已落盤（證明已過 L6.5）；
    其他例外（含 `CalibrationError`）一律上拋。"""
    from momentum.core.contracts import AlignmentViolationError

    root = Path(kwargs["storage"].base_path)
    try:
        return factory.run_ic_first(SYMBOL, PRIMARY_TF, config, **kwargs)
    except AlignmentViolationError:
        assert raw_artifact_fingerprints(root), "IC 階段前未見 L7 raw 產物：失敗發生於 L6.5 之前"
        return None


def raw_artifact_fingerprints(root: Path) -> Dict[str, Dict[str, Any]]:
    """root 下 L7 raw 產物（`<run_dir>/raw/*.parquet`＝L6.5 pre_ic 輸出）之 欄名 → 四 hash。"""
    import pyarrow.parquet as pq

    out: Dict[str, Dict[str, Any]] = {}
    for p in sorted(root.rglob("raw/*.parquet")):
        if any(part.startswith(".tmp-raw-") for part in p.parts):
            continue
        table = pq.read_table(p)
        for n in table.column_names:
            if n in ("timestamp", "__index_level_0__", "index"):
                continue
            out[n] = column_fingerprint(table.column(n).to_numpy(zero_copy_only=False))
    return out


def column_fingerprint(values: Any) -> Dict[str, Any]:
    """四 hash：dtype、shape、NaN mask、值（NaN 以 0 取代後之位元組）；與 `freeze_baseline.column_fingerprint` 同式。"""
    import hashlib

    import numpy as np

    arr = np.asarray(values)
    mask = np.isnan(arr) if arr.dtype.kind == "f" else np.zeros(arr.shape, dtype=bool)
    filled = np.where(mask, 0, arr) if arr.dtype.kind == "f" else arr
    return {"dtype": str(arr.dtype), "shape": list(arr.shape),
            "nan_mask": hashlib.sha256(mask.tobytes()).hexdigest(),
            "values": hashlib.sha256(np.ascontiguousarray(filled).tobytes()).hexdigest()}


def ic_first_supplied_off(tmp_path: Path, *, supplied: bool = True) -> Tuple[Optional[Any], Dict[str, Dict[str, Any]]]:
    """平穩化關閉、`run_ic_first` 自帶 raw_data／layers（比照 `test_b6_warmup_trim` 之 IC-first 用法：先設輸出窗、
    以含前史之 ingest 起點讀原始資料、帶 config_hash）；呼叫端須先設 `IC_FIRST_OFF_ENV`。
    `supplied=False`：同設定、同輸出窗，不帶 raw_data／layers（自算路徑）——v49 之對照組。
    回傳 (結果或 None, L7 raw 四 hash)——Task 2.1 舊行為守衛與 §G 凍結同源。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.warmup_window import resolve_output_window

    root = tmp_path / "features"
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    config = factory._resolve_config(stat_payload(fracdiff=False, adf=False))
    start, end = WINDOW
    window = resolve_output_window(config, PRIMARY_TF, start, end)
    factory._current_output_window = window
    extra: Dict[str, Any] = {}
    if supplied:
        extra["raw_data"] = factory._layer0_data_ingestion(
            SYMBOL, PRIMARY_TF, config,
            start_date=window.ingest_start if window.warmup_enabled else start, end_date=end,
        )
        _, extra["layers"] = factory._run_l1_l6_for_ic_first(SYMBOL, PRIMARY_TF, config)
    result = ic_first_to_l65(
        factory, config, **extra,
        config_hash=factory._compute_config_hash(config, SYMBOL, PRIMARY_TF, start_date=start, end_date=end),
        ic_engine=ICEngine({"methods": ["spearman"]}), feature_reader=FeatureReader(str(root)),
        storage=factory._storage, ic_threshold=0.0, persist=False,
    )
    return result, raw_artifact_fingerprints(root)


def attach_unit_calibration(preprocessor: Any, pre_history: Any, public_columns: Optional[List[str]] = None, *,
                            timeframe: Optional[str] = None, symbol: str = SYMBOL, config_hash: str = "unit") -> None:
    """前處理器單元測試用：以 `pre_history` 各欄最後 N 個有效值建封包並交付、核對（形同前置關卡之產物；
    全無有效值之欄列入 empty_columns）。`pre_history` 可為真實前史，亦可為單元測試之 frame 本身——後者只用於
    數值／等價性（serial vs parallel、快取、精度）測試，不用於洩漏驗收；生產端無此路徑（封包只由前置關卡產生）。
    index 非 DatetimeIndex 者以 UTC 秒序號代之；無時區者視為 UTC（同前置關卡之正規化）。"""
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.preprocessing import calibration as cal

    columns = [str(c) for c in (public_columns if public_columns is not None else pre_history.columns)]
    frame = pre_history.loc[:, columns]
    if preprocessor.winsor_config.get("enabled", False):
        # L6.5 先縮尾再做平穩化判定；校準值取同一縮尾後之值（同生產端校準域）
        frame = preprocessor._apply_winsorization(frame)
    if isinstance(frame.index, pd.DatetimeIndex):
        index = frame.index.tz_localize("UTC") if frame.index.tz is None else frame.index.tz_convert("UTC")
    else:
        index = pd.Timestamp("1970-01-01", tz="UTC") + pd.to_timedelta(np.arange(len(frame)), unit="s")
    frame = frame.set_axis(index, axis=0)
    timeframe = timeframe or preprocessor._decision_scope()[0]  # 未給則同前處理器脈絡之週期
    n = preprocessor._stationarity_n_for(timeframe)
    output_start = pd.Timestamp(index[-1]) + pd.Timedelta(seconds=1)
    values, first, last, empty = {}, {}, {}, []
    for column in columns:
        name = cal.tagged_column_name(column, timeframe)
        series = frame[column].astype(np.float64).rename(name)
        if not np.isfinite(series.to_numpy()).any():
            empty.append(name)
            continue
        values[name], first[name], last[name] = cal.calibration_window_before(series, output_start, n)
    key = cal.CalibrationKey(symbol=symbol, timeframe=timeframe, output_start=output_start, config_hash=config_hash,
                             n=n, column_set_digest=cal.column_set_digest(list(values)))
    packet = cal.CalibrationPacket(key=key, values=values, last_calibration_ts=last,
                                   calibration_source_sha256=cal.calibration_source_sha256(frame.astype(np.float64)),
                                   extras={"first_calibration_ts": first, "empty_columns": sorted(empty)})
    preprocessor.set_calibration({timeframe: packet}, symbol=symbol, output_start=output_start,
                                 config_hash=config_hash)
    preprocessor._prepare_calibration({timeframe: columns})


def all_nan_base_columns() -> set:
    """凍結基準中公開輸出全為 NaN 之基礎欄（nan_mask＝全 True 之 hash；依資料判定、不依欄名）。
    此類欄於校準域與公開域皆無任何有效值 ⇒ 無法做 ADF，決策以未檢定事件明示（b3b 審碼表具名）。"""
    import hashlib

    import numpy as np

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    out = set()
    for name, fp in baseline["base"].items():
        if fp["nan_mask"] == hashlib.sha256(np.ones(tuple(fp["shape"]), dtype=bool).tobytes()).hexdigest():
            out.add(name)
    return out


def base_fingerprints(root: Path) -> Dict[str, Dict[str, Any]]:
    """run 目錄下基礎欄（非 `*_L65.parquet`）之逐欄四 hash；與 `freeze_baseline.collect` 同一取檔範圍。"""
    import pyarrow.parquet as pq

    out: Dict[str, Dict[str, Any]] = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet"):
            continue
        table = pq.read_table(p)
        for n in table.column_names:
            if n not in ("timestamp", "__index_level_0__", "index"):
                out[n] = column_fingerprint(table.column(n).to_numpy(zero_copy_only=False))
    return out


def base_column_values(root: Path, names: Any) -> Dict[str, Any]:
    """run 目錄下基礎欄（非 `*_L65.parquet`）中指定欄之值（float64 ndarray；每檔只讀檔頭與所需欄）。"""
    import numpy as np
    import pyarrow.parquet as pq

    wanted = set(names)
    out: Dict[str, Any] = {}
    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet") or p.name == "timestamps.parquet" or not wanted:
            continue
        cols = [n for n in pq.read_schema(p).names if n in wanted]
        if not cols:
            continue
        table = pq.read_table(p, columns=cols)
        for n in cols:
            out[n] = np.asarray(table.column(n).to_numpy(zero_copy_only=False), dtype=np.float64)
            wanted.discard(n)
    return out


def approved_base_columns(baseline_columns: Any) -> set:
    """§G ①（v33／v34／v49）：改後基礎欄集合之期望＝改前基準欄集合＋經使用者核可之欄集合差異（最新 delta 收據之
    `added` 加入、`removed` 移除）。核可紀錄之 delta sha256 須等於 delta 收據（不等或非空而無核可 ⇒ 斷言失敗），
    未核可之差異不得進入期望。"""
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    rr = Path(__file__).resolve().parents[2] / "handoffs" / "run_receipts"
    deltas = sorted(rr.glob("*-ffstat-column-set-delta.json"))
    assert deltas, "缺欄集合差異收據"
    delta = json.loads(deltas[-1].read_text(encoding="utf-8"))["delta"]
    digest = sm.delta_sha256(delta)
    if delta != CONTRACT["column_set_delta"]["empty"]:
        approvals = sorted(rr.glob("*-ffstat-column-set-approval.json"))
        assert approvals, "delta 非空而無使用者核可紀錄"
        assert json.loads(approvals[-1].read_text(encoding="utf-8"))["delta_sha256"] == digest
    return (set(baseline_columns) | set(delta["added"])) - set(delta["removed"])


def public_fingerprints(root: Path) -> Dict[str, Dict[str, Any]]:
    """公開輸出之全部欄（基礎欄＋平穩化衍生欄）→ {NaN mask hash, float32 值 hash}；frame 路徑（`*_factory.h5`，
    全部欄同一檔）與 CGSA 路徑（基礎欄 parquet＋`*_L65.parquet` 衍生欄）同式，供 ⑪ 跨路徑比對。
    值一律轉 float32（兩路徑落盤精度）後比，NaN 以 0 取代。"""
    import hashlib

    import numpy as np
    import pyarrow.parquet as pq

    def fp(values: Any) -> Dict[str, Any]:
        arr = np.asarray(values, dtype=np.float32)
        nan = np.isnan(arr)
        return {"nan": hashlib.sha256(np.packbits(nan).tobytes()).hexdigest(),
                "values": hashlib.sha256(np.where(nan, np.float32(0), arr).tobytes()).hexdigest()}

    out: Dict[str, Dict[str, Any]] = {}
    for h5 in sorted(root.rglob("*_factory.h5")):
        symbol, timeframe = h5.name[: -len("_factory.h5")].rsplit("_", 1)
        frame = FeatureStorage(str(h5.parent)).load_factory_output(symbol, timeframe).features_df
        for name in frame.columns:
            out[str(name)] = fp(frame[name].to_numpy())
    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        table = pq.read_table(p)
        for n in table.column_names:
            if n not in ("timestamp", "__index_level_0__", "index"):
                out[n] = fp(table.column(n).to_numpy(zero_copy_only=False))
    return out


def _values_digest(values: Any) -> str:
    """值之指紋（有限值位置＋有限值之 float64 位元組；NaN 酬載不影響）。"""
    import hashlib

    import numpy as np

    v = np.asarray(values, dtype=np.float64)
    finite = np.isfinite(v)
    return hashlib.sha256(finite.tobytes() + np.where(finite, v, 0.0).tobytes()).hexdigest()


class DeadDropSpy:
    """§G⑦ v53（審查 r36 兩家 P1-03）：於生產死欄過濾點（L3 `_variance_filter_with_reasons`〔多窗路徑經
    `_batch_variance_filter` 亦走此〕；L7 串流寫入端 `dead_column_mask`；`find_dead_columns`）記錄每欄進入過濾時之
    首個有限值列（本 run 列號）與「自首個有限值起」之值指紋（A 另位移 offset＝M 列，使兩 run 之同時點對齊：兩 run
    自各自起點之預熱結構相同 ⇒ 同欄首個有限值之 run 內列號相同），與被剔除欄之值與重播參數。只供測試。"""

    def __init__(self, offset: int, timeframe: Optional[str] = None) -> None:
        self.offset = int(offset)
        self.timeframe = timeframe
        self.digest: Dict[Tuple[str, str], str] = {}
        self.first: Dict[Tuple[str, str], Optional[int]] = {}
        self.dropped: Dict[str, Dict[str, Any]] = {}

    def _public_name(self, name: str) -> str:
        """過濾點欄名 → 公開欄名（L3 過濾點尚未加週期標記；同生產 `_timeframe_tagged_name`，已標記者不動）。"""
        if not self.timeframe:
            return str(name)
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner

        return FeatureFactory._timeframe_tagged_name(str(name), self.timeframe,
                                                     set(TimeframeAligner._timeframe_seconds_keys()))

    def record(self, site: str, names: List[str], matrix: Any, dead: Any, params: Dict[str, Any]) -> None:
        import numpy as np

        arr = np.asarray(matrix, dtype=np.float64)
        if arr.ndim == 1:
            arr = arr.reshape(-1, 1)
        names = [self._public_name(n) for n in names]
        for i, name in enumerate(names):
            key = (site, str(name))
            col = arr[:, i]
            if key not in self.digest:
                finite = np.isfinite(col)
                first = int(np.argmax(finite)) if finite.any() else None
                self.first[key] = first
                self.digest[key] = _values_digest(col[self.offset + first:] if first is not None else col[:0])
            if bool(np.asarray(dead)[i]) and str(name) not in self.dropped:
                self.dropped[str(name)] = {"site": site, "values": col.copy(), "params": dict(params)}

    def install(self) -> Any:
        """掛上各過濾點之 spy；回傳還原函式。"""
        import sys

        import numpy as np

        from momentum.FeatureEngineering.operators import rolling_aggregator as ra
        from momentum.FeatureEngineering.utils import dead_feature_filter as dff

        spy = self
        orig_var = ra.RollingAggregator.__dict__["_variance_filter_with_reasons"]
        orig_mask = dff.dead_column_mask
        orig_find = dff.find_dead_columns

        def var_filter(df: Any, nan_threshold: float = 0.9) -> Any:
            kept, reasons = orig_var.__func__(df, nan_threshold)
            names = [str(c) for c in df.columns]
            spy.record("L3", names, df.to_numpy(dtype=np.float64), [n in reasons for n in names],
                       {"nan_threshold": nan_threshold})
            return kept, reasons

        def dead_mask(array: Any, min_valid_samples: int = 100) -> Any:
            mask = orig_mask(array, min_valid_samples=min_valid_samples)
            names = sys._getframe(1).f_locals.get("columns_list")
            assert names is not None and len(names) == np.asarray(array).shape[1], "L7 死欄點缺欄名（spy 失效）"
            spy.record("L7", [str(n) for n in names], array, mask, {"min_valid": min_valid_samples})
            return mask

        def find_dead(df: Any, min_valid_samples: int = 100, enabled: bool = True) -> Any:
            dead, diag = orig_find(df, min_valid_samples=min_valid_samples, enabled=enabled)
            numeric = [c for c in df.columns if np.issubdtype(np.asarray(df[c]).dtype, np.number)]
            if numeric:
                spy.record("L7", [str(c) for c in numeric], df[numeric].to_numpy(dtype=np.float64),
                           [str(c) in dead for c in numeric], {"min_valid": min_valid_samples})
            return dead, diag

        ra.RollingAggregator._variance_filter_with_reasons = staticmethod(var_filter)
        dff.dead_column_mask = dead_mask
        dff.find_dead_columns = find_dead

        def restore() -> None:
            ra.RollingAggregator._variance_filter_with_reasons = orig_var
            dff.dead_column_mask = orig_mask
            dff.find_dead_columns = orig_find

        return restore


def replay_dead_reason(entry: Dict[str, Any]) -> Optional[str]:
    """以同一純函式（`stable_mask.dead_column_decision`＋L3 之 inf 規則）重播剔除判定；未剔除回 None。"""
    import numpy as np

    from momentum.FeatureEngineering.operators.rolling_aggregator import _VARIANCE_FILTER_MIN_EFFECTIVE_N
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm

    values = np.asarray(entry["values"], dtype=np.float64)
    if entry["site"] == "L3":
        if np.isinf(values).any():
            return "has_inf"
        dec = sm.dead_column_decision(values, nan_rate_threshold=entry["params"]["nan_threshold"],
                                      min_valid=_VARIANCE_FILTER_MIN_EFFECTIVE_N)
    else:
        dec = sm.dead_column_decision(values, nan_rate_threshold=None, min_valid=entry["params"]["min_valid"])
    return str(dec.reason or "constant") if dec.dead else None


def dual_public_columns(root: Path):
    """§G⑦ 之公開欄串流：逐 parquet 檔（含 L6.5 之 `*_L65.parquet`，v52 審查 r35 codex P1-01）產出
    (欄名, 以絕對時間戳為 index 之 float64 Series)；不一次載入全部欄（8GB 本機）。"""
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        if p.name == "timestamps.parquet":
            continue
        frame = pq.read_table(p).to_pandas()
        if "timestamp" in frame.columns:
            idx = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        else:
            # L7 raw 群組 parquet 無時間欄：時間軸為 run 目錄之 timestamps.parquet（UTC epoch 秒）
            stamps = next((q for q in p.parents if (q / "timestamps.parquet").exists()), None)
            assert stamps is not None, f"找不到 {p} 所屬 run 之 timestamps.parquet"
            seconds = pq.read_table(stamps / "timestamps.parquet").column("timestamp").to_numpy()
            idx = pd.to_datetime(seconds, unit="s", utc=True)
            assert len(idx) == len(frame), p
        for n in frame.columns:
            if n not in ("timestamp", "__index_level_0__", "index"):
                yield n, pd.Series(frame[n].to_numpy(dtype=np.float64), index=idx)


def dual_start_report(tmp_path: Path, timeframe: str, payload: Dict[str, Any], source_kline_dir: str,
                      symbol: str = SYMBOL, b_mutator: Optional[Any] = None) -> Dict[str, Any]:
    """§G⑦（v51 分解判準；審查 r34 兩家 P1-01）雙起點收斂對證之唯一實作（測試與收據腳本共用）。

    單一原生週期（training=[tf]、primary=tf）、無起始日、平穩化關閉；A＝自資料起點，B′＝刪去前 M_tf 列之複本。
    M_tf＝K_max_tf（`warmup_window._collect_l1_warmup_bars`；獨立於受測遮罩）。兩次 run 皆以 spy 包 L1 輸出點之
    唯一遮罩函式 `stable_mask.apply_l1_mask`（鍵＝輸出點 spec〔engine、指標、欄、參數〕＋同鍵出現序）：
    - A：記每個 L1 輸出點遮罩前之值。
    - B′：記自身遮罩後之 L1 輸出（供 ①），再把遮罩前之值換成 A 同時點之值（A[M:]）後照常遮罩往下游。
    ① **L1 本欄收斂**：每個 L1 輸出點，B′ 自身遮罩後輸出自其首個有限值起與 A 同時點（A 遮罩後）比，A、B′ 皆有限之列
      ≥ min_overlap 且 |A−B′| ≤ tol × max(P75(|A|), std(A))，且有限值位置全等；不足 min_overlap 列 ⇒ `l1_ineligible`。
    ② **下游與起算點無關**：B′ 之 L1 值與 A 相同 ⇒ 每個非 start_dependent 公開欄自 B′ 首個有限值起與 A 之有限值位置
      全等、值逐一相等（落盤 float32）；任一列不等 ⇒ `exact_violations`（記最大絕對差、不等列數、重疊列數）。
    配對防呆：B′ 之 L1 輸出點於 A 無同鍵或長度差≠M ⇒ `injection_unmatched`（非空即不通過）。
    `violations`＝① 超容差／mask 不等 ∪ ② 不等 ∪ 配對失敗（測試斷言其為空）。
    """
    import shutil
    import sys

    import h5py
    import numpy as np
    import pandas as pd
    import pyarrow.parquet as pq

    from momentum.factories import create_feature_factory
    from momentum.FeatureEngineering.preprocessing import stable_mask as sm
    from momentum.FeatureEngineering.warmup_window import _collect_l1_warmup_bars

    cfg = CONTRACT["dual_start"]
    tol, min_overlap = float(cfg["tolerance"]), int(cfg["min_overlap_rows"])
    body = dict(payload)
    body["timeframes"] = {"primary": timeframe, "training": [timeframe]}
    for pre in ("fractional_differencing", "adf_differencing"):
        body.setdefault("preprocessing", {}).setdefault(pre, {})["enabled"] = False
    config = create_feature_factory(cache_dir=source_kline_dir, validate_continuity=False)._resolve_config(body)
    m = int(_collect_l1_warmup_bars(config))
    # v52：A 取來源末 R＝3M＋1,000 列（A 只需比 B′ 多 M 列前史；R 足以含 M＋F_max＋500——F_max ≤ M＋L2／L3 最大窗
    # ＋縮尾窗）。全史 2 萬列之 1h、4h 長歷史以強制 float32 落盤兩次 run 約需 20GB 磁碟與逾 8GB 記憶體，本機不可行
    with h5py.File(Path(source_kline_dir) / "kline_cache.h5", "r") as f:
        n_source = int(f[symbol][timeframe]["data"].shape[0])
    base_drop = max(0, n_source - (3 * m + 1000))
    real_mask = sm.apply_l1_mask

    def spec_key(seen: Dict[str, int]) -> Tuple[str, int]:
        spec = sys._getframe(2).f_locals.get("spec")
        assert spec is not None, "L1 遮罩呼叫點缺 spec（§G⑦ 分解之配對鍵）"
        label = f"{spec.engine}|{spec.indicator}|{spec.column}|{sorted(spec.params.items())}"
        occ = seen.get(label, 0)
        seen[label] = occ + 1
        return label, occ

    def run(label: str, drop_rows: int, spy: Any, dead_spy: "DeadDropSpy") -> Tuple[Path, Any]:
        kdir = tmp_path / f"k_{label}"
        kdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(source_kline_dir) / "kline_cache.h5", kdir / "kline_cache.h5")
        if drop_rows:
            with h5py.File(kdir / "kline_cache.h5", "r+") as f:
                group = f[symbol][timeframe]
                arr = group["data"][()]
                attrs = dict(group["data"].attrs)
                del group["data"]
                ds = group.create_dataset("data", data=arr[drop_rows:], maxshape=(None,), chunks=True)
                for key, value in attrs.items():
                    ds.attrs[key] = value
        root = tmp_path / f"features_{label}"
        factory = create_feature_factory(cache_dir=str(kdir), validate_continuity=False)
        factory._storage = FeatureStorage(str(root))
        sm.apply_l1_mask = spy
        restore_dead = dead_spy.install()
        # v52（審查 r35 codex P1-05）：兩次 run 皆以 float32 落盤——生產之落盤型別依值域逐段選 float16／float32
        # （`_select_parquet_storage_array`），隨起算點而變；② 驗的是計算本身，須比落盤前之值（float32 無損於 float32 計算）
        real_select = FeatureStorage.__dict__["_select_parquet_storage_array"]
        FeatureStorage._select_parquet_storage_array = classmethod(
            lambda cls, data: (np.ascontiguousarray(data, dtype=np.float32), "float32"))
        try:
            result = factory.generate_features(symbol, timeframe, config_override=body, force_regenerate=True,
                                               start_date=None, end_date=None, persist=True)
        finally:
            sm.apply_l1_mask = real_mask
            FeatureStorage._select_parquet_storage_array = real_select
            restore_dead()
        return root, result

    # A：記遮罩前之 L1 值（float64，含 origin、K 以重建 A 之遮罩後輸出）
    a_seen: Dict[str, int] = {}
    a_l1: Dict[Tuple[str, int], Tuple[Any, Any, int]] = {}

    def spy_a(values: Any, origin: Any, k: int) -> Any:
        key = spec_key(a_seen)
        a_l1[key] = (np.array(values, dtype=np.float64, copy=True), origin, int(k))
        return real_mask(values, origin, k)

    dead_a, dead_b = DeadDropSpy(offset=m, timeframe=timeframe), DeadDropSpy(offset=0, timeframe=timeframe)
    a_root, a_result = run("a", base_drop, spy_a, dead_a)
    start_dependent = set(a_result.metadata.get(CONTRACT["start_dependent_key"], []))
    first_rows, n_rows = [], 0
    for _, s in dual_public_columns(a_root):
        v = s.to_numpy()
        n_rows = len(v)
        if np.isfinite(v).any():
            first_rows.append(int(np.argmax(np.isfinite(v))))
    f_max = max(first_rows) if first_rows else 0
    report: Dict[str, Any] = {"timeframe": timeframe, "rows": n_rows, "m": m, "f_max": f_max, "source_rows": n_source,
                              "base_drop": base_drop,
                              "margin": n_rows - (m + f_max + min_overlap), "violations": {}, "ineligible": [],
                              "l1_max_error": {}, "l1_violations": {}, "l1_ineligible": {}, "exact_violations": {},
                              "mask_violations": [], "injection_unmatched": [], "all_nan": [], "overlap_rows": {},
                              "missing_public_columns": [], "extra_public_columns": []}
    # v52（使用者 2026-09-29 裁定 1d 深欄資料不足維持 blocked）：資格不足仍照跑 B′——① 逐 L1 輸出點各自判資格、
    # ② 以可得之重疊列逐值相等；`eligible` 為假即 blocked 收據（列數字），不得算通過

    # B′：記自身遮罩後之 L1 輸出，再注入 A 之同時點遮罩前值
    b_seen: Dict[str, int] = {}
    b_own: Dict[Tuple[str, int], Any] = {}

    def spy_b(values: Any, origin: Any, k: int) -> Any:
        key = spec_key(b_seen)
        own = real_mask(values, origin, k)
        b_own[key] = own
        src = a_l1.get(key)
        if src is None or len(src[0]) - len(own) != m:
            report["injection_unmatched"].append(f"{key[0]}#{key[1]}")
            return own
        return real_mask(src[0][m:], origin, k)

    b_root, b_result = run("b", base_drop + m, spy_b, dead_b)
    if b_mutator is not None:
        b_mutator(b_root)  # 僅供 mutant 測試：於比對前改動 B′ 之落盤產出

    # ① L1 本欄收斂（遮罩後、下游與縮尾之前）；累積型（倍數表 warmup_class＝cumulative，如 OBV、AD）無收斂點，
    # 與 start_dependent_columns 同樣不入（其值依起算點而異屬定義）
    from momentum.FeatureEngineering.atomic import warmup_lookup

    table = warmup_lookup.warmup_table()
    report["l1_cumulative_skipped"] = []
    for key, own in b_own.items():
        if key not in a_l1:
            continue
        if (table.get(key[0].split("|")[1].upper()) or {}).get("warmup_class") == "cumulative":
            report["l1_cumulative_skipped"].append(f"{key[0]}#{key[1]}")
            continue
        values, origin, k = a_l1[key]
        a_masked = np.asarray(real_mask(values, origin, k), dtype=np.float64)[m:]
        name = f"{key[0]}#{key[1]}"
        fb = np.isfinite(own)
        if not fb.any():
            continue
        first = int(np.argmax(fb))
        fa = np.isfinite(a_masked)
        if not np.array_equal(fa[first:], fb[first:]):
            report["l1_violations"][name] = "mask"
            continue
        both = fa & fb
        if both.sum() < min_overlap:
            report["l1_ineligible"][name] = int(both.sum())
            continue
        ref = a_masked[np.isfinite(a_masked)]
        scale = max(float(np.percentile(np.abs(ref), 75)), float(np.std(ref)), 1e-8)
        err = float(np.max(np.abs(a_masked[both] - own[both])) / scale)
        report["l1_max_error"][name] = err
        if err > tol:
            report["l1_violations"][name] = err

    # ② 下游與起算點無關（B′ 之 L1 與 A 相同 ⇒ 公開欄須與 A 逐一相等）
    # v52（審查 r35 codex P1-02）：欄集合須全等——A 有 B′ 無（扣除 start_dependent）、B′ 有 A 無皆違規
    b_cols = dict(dual_public_columns(b_root))
    n_b = len(next(iter(b_cols.values())).index) if b_cols else 0  # v55：B′ 列數（逐欄資格）
    for name, a in dual_public_columns(a_root):
        if name not in b_cols:
            if name not in start_dependent:
                report["missing_public_columns"].append(name)
            continue
        b = b_cols.pop(name)
        if name in start_dependent:
            continue
        av, bv = a.reindex(b.index).to_numpy(), b.to_numpy()
        fa, fb = np.isfinite(av), np.isfinite(bv)
        if not fa.any() and not fb.any():
            report["all_nan"].append(name)
            continue
        first = int(np.argmax(fb)) if fb.any() else len(fb)
        if not np.array_equal(fa[first:], fb[first:]):
            report["mask_violations"].append(name)
        both = fa & fb
        report["overlap_rows"][name] = int(both.sum())
        diff = np.abs(av[both] - bv[both])
        if diff.size and float(diff.max()) > 0.0:
            report["exact_violations"][name] = {"max_abs_diff": float(diff.max()), "rows_differ": int((diff > 0).sum()),
                                                "overlap": int(both.sum())}
    report["extra_public_columns"] = sorted(b_cols)
    # v55（審查 r39；使用者 2026-09-30「資料不足應該也只是某些特徵的某些參數而已吧？」、2026-09-26 前史不足逐欄跳過）：
    # 資格逐欄判定——某欄於較短之 B′ 內可比對之有效列 < min_overlap ⇒ 列入 `column_ineligible`（逐欄 blocked 收據，
    # 記列數），不作違規；可比對之列仍須逐值相等（上方 exact／mask 不變）。整體 margin 僅供參考，不作資格條件。
    report["rows_b"] = n_b
    report["column_ineligible"] = {name: int(n) for name, n in report["overlap_rows"].items() if n < min_overlap}
    # B′ 之 L1 輸出點（公開欄名）→ 遮罩後有效列數（未生成欄之上游證明用）
    b_l1_valid: Dict[str, int] = {}
    for key, own in b_own.items():
        col = dead_b._public_name(key[0].split("|")[2])
        b_l1_valid[col] = max(b_l1_valid.get(col, 0), int(np.isfinite(np.asarray(own, dtype=np.float64)).sum()))

    def upstream_l1(name: str) -> Optional[str]:
        """公開欄 → 其 L1 上游（最長之「L1 欄名＋底線」前綴）；找不到回 None（不開脫）。"""
        hits = [c for c in b_l1_valid if name == c or name.startswith(c + "_")]
        return max(hits, key=len) if hits else None

    # v53（審查 r36 兩家 P1-03）：欄集合差異須為可重播之死欄判定——缺席之 run 於 metadata 記有原因、以其過濾點之
    # 實際值重播同一純函式得同一原因、且該值於重疊段與另一 run 同一過濾點之值指紋相同；否則違規
    reasons = {"a": dict(a_result.metadata.get("column_set_reasons") or {}),
               "b": dict(b_result.metadata.get("column_set_reasons") or {})}
    report["column_set_explained"] = {}
    report["column_set_unexplained"] = {}

    def explain(name: str, absent: str) -> Optional[str]:
        spy_absent, spy_present = (dead_b, dead_a) if absent == "b" else (dead_a, dead_b)
        recorded = reasons[absent].get(name)
        entry = spy_absent.dropped.get(name)
        if absent == "b":
            # v55：B′ 內可驗之有效列 < min_overlap ⇒ 逐欄 blocked（非違規）。證據須機械：①過濾點紀錄之 B′ 首個
            # 有效列 ⇒ 有效列＝n_b−首列；②未生成（無紀錄）⇒ 其 L1 上游於 B′ 遮罩後有效列數。證明不了即落回下方判定。
            valid_b: Optional[int] = None
            evidence = ""
            if entry is not None:
                vals = np.asarray(entry["values"], dtype=np.float64)
                fin = np.isfinite(vals)
                valid_b = int(len(vals) - int(np.argmax(fin))) if fin.any() else 0
                evidence = "valid_rows_at_drop_site"
            elif not recorded:
                up = upstream_l1(name)
                if up is not None:
                    valid_b = b_l1_valid[up]
                    evidence = f"upstream_l1:{up}"
            if valid_b is not None and valid_b < min_overlap:
                report["column_ineligible"][name] = valid_b
                report["column_set_explained"][name] = {"absent_in": absent, "site": entry["site"] if entry else None,
                                                        "reason": str(recorded) if recorded else None,
                                                        "evidence": f"insufficient_rows_in_shorter_run:{evidence}",
                                                        "valid_rows_b": valid_b}
                return None
        if not recorded:
            return "no_recorded_reason"
        if entry is None:
            return "no_drop_point_record"
        replayed = replay_dead_reason(entry)
        if replayed != str(recorded):
            return f"replay_mismatch:{recorded}->{replayed}"
        key = (entry["site"], name)
        other = spy_present.digest.get(key)
        if other is None:
            return "other_run_not_seen_at_site"
        values = np.asarray(entry["values"], dtype=np.float64)
        finite = np.isfinite(values)
        own_first = int(np.argmax(finite)) if finite.any() else None
        note = "overlap_equal"
        if own_first is None:
            # 缺席 run 全無有限值：須為預熱超過該 run 之長度——另一 run 之首個有限值列（run 內列號）≥ 缺席 run 列數
            other_first = spy_present.first.get(key)
            if absent != "b" or other_first is None or other_first < len(values):
                return "all_nan_not_explained_by_warmup"
            note = "warmup_exceeds_run"
        else:
            own = values[own_first:] if absent == "b" else values[m + own_first:]
            if spy_present.first.get(key) != own_first:
                return "first_valid_row_differs"
            if _values_digest(own) != other:
                return "overlap_values_differ"
        report["column_set_explained"][name] = {"absent_in": absent, "site": entry["site"], "reason": str(recorded),
                                                "evidence": note}
        return None

    for name in report["missing_public_columns"]:
        why = explain(name, "b")
        if why:
            report["column_set_unexplained"][name] = why
    for name in report["extra_public_columns"]:
        why = explain(name, "a")
        if why:
            report["column_set_unexplained"][name] = why
    report["ineligible"] = sorted(report["l1_ineligible"])
    report["violations"] = {**{f"column_set:{k}": why for k, why in report["column_set_unexplained"].items()},
                            **{f"L1:{k}": v for k, v in report["l1_violations"].items()},
                            **{f"exact:{k}": v["max_abs_diff"] for k, v in report["exact_violations"].items()},
                            **{f"mask:{k}": "mask" for k in report["mask_violations"]},
                            **{f"unmatched:{k}": "unmatched" for k in report["injection_unmatched"]}}
    # v55：資格逐欄——全部 L1 輸出點與公開欄皆有 ≥ min_overlap 列可驗方為整週期合資格；`margin` 保留供參考
    report["eligible"] = not report["ineligible"] and not report["column_ineligible"]
    return report


def decision_change_report(baseline_decisions: Dict[str, Dict[str, Any]],
                           decisions_now: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """§G ②′ 與基準相比之決策改變（Task 4.1 golden 收據之唯一來源）：逐欄 (fracdiff, ADF 差分階數) 舊→新、
    依「舊->新」分類計數、其中原屬名字免檢之欄。只比兩邊皆有之欄。"""
    changed: Dict[str, Dict[str, Any]] = {}
    for col in sorted(set(baseline_decisions) & set(decisions_now)):
        old = [bool(baseline_decisions[col]["fracdiff"]), int(baseline_decisions[col]["adf_diff_order"])]
        new = [bool(decisions_now[col]["fracdiff"]), int(decisions_now[col]["adf_differenced"] or 0)]
        if old != new:
            changed[col] = {"old": old, "new": new, "name_exempt": bool(baseline_decisions[col]["name_exempt"])}
    by_kind: Dict[str, int] = {}
    for c in changed.values():
        key = f"{tuple(c['old'])}->{tuple(c['new'])}"
        by_kind[key] = by_kind.get(key, 0) + 1
    return {"changed_columns": changed, "changed_count": len(changed), "by_kind": dict(sorted(by_kind.items())),
            "name_exempt_changed": sorted(c for c, v in changed.items() if v["name_exempt"])}
