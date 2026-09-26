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
             end_date: str = WINDOW[1], primary_tf: str = PRIMARY_TF, persist: bool = True,
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


def ic_first_supplied_off(tmp_path: Path) -> Tuple[Optional[Any], Dict[str, Dict[str, Any]]]:
    """平穩化關閉、`run_ic_first` 自帶 raw_data／layers（比照 `test_b6_warmup_trim` 之 IC-first 用法：先設輸出窗、
    以含前史之 ingest 起點讀原始資料、帶 config_hash）；呼叫端須先設 `IC_FIRST_OFF_ENV`。
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
    raw_data = factory._layer0_data_ingestion(
        SYMBOL, PRIMARY_TF, config,
        start_date=window.ingest_start if window.warmup_enabled else start, end_date=end,
    )
    _, layers = factory._run_l1_l6_for_ic_first(SYMBOL, PRIMARY_TF, config)
    result = ic_first_to_l65(
        factory, config, raw_data=raw_data, layers=layers,
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
