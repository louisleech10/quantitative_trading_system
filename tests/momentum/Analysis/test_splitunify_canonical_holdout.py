"""SPLITUNIFY `Task 10.4`：canonical 邊界之單一解析入口（真實資料）。

🔴 **本檔一律用真實資料**（`data_cache/features/`、`data_cache/feature_klines/kline_cache.h5`）；
禁合成 fixture（CLAUDE.md 資料真實性鐵律）。資料缺席時 `skip`。

驗的是什麼：邊界只有一條。下沉前比對腳本自己算了一份（`oos_test_size` 寫死 0.2、
深度抬高之 embargo 沒接上），B10A 審碼兩度被打穿；現在 IC 端與腳本都呼叫同一支。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
RUN_1H = REPO / "data_cache/features/ETHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5"
RUN_12H = REPO / "data_cache/features/ETHUSDT/12h/e53e22906c35363757f4cd49d27f973e"
KLINE = REPO / "data_cache/feature_klines/kline_cache.h5"
SYM = "ETHUSDT"
FF_1H = "4a8a0b3726cc906ab3534994605e77f5"


def _require(*paths: Path) -> None:
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        pytest.skip(f"真實資料缺席（不得以合成 fixture 代替）：{missing}")


def _resolver():
    from momentum.factories import create_canonical_holdout_resolver

    return create_canonical_holdout_resolver()


def _cfg():
    from momentum.factories import load_ic_config

    return load_ic_config()


def test_canonical_holdout_matches_ic_build_holdout_split_plan() -> None:
    """🔴 邊界與 IC 生產端之 `_build_holdout_split_plan` **逐值相等**。

    比的是 `test_plan.row_index` 與 `row_time_fingerprint`——不是只比列數。
    鑑別力：把 `oos_test_size` 改一個值即整條轉紅（B10A 實測 0.2→0.3 ⇒ 邊界位移）。
    """
    _require(RUN_1H, KLINE)
    from momentum.Analysis.event_samples.canonical_holdout import load_post_trim_index
    from momentum.Analysis.ic_filter_orchestrator import _build_holdout_split_plan
    from momentum.core.constants import TIMEFRAME_SECONDS

    resolve, _err = _resolver()
    purge_gap, depth = 156, 144
    got = resolve(
        ff_run=FF_1H, symbol=SYM, ic_config=_cfg(),
        purge_gap=purge_gap, lookahead_depth_rows=depth,
    )
    assert got.reason is None, f"真實 run 不應無邊界：{got.reason}"

    # 獨立重算：直接呼叫生產端建構函式（同一支，但由本測試自己組參數）。
    cfg = _cfg()
    cfg.embargo = max(int(getattr(cfg, "embargo", 0) or 0), depth)
    index = load_post_trim_index(RUN_1H)
    expect = _build_holdout_split_plan(
        pd.DataFrame(index=index), cfg, SYM,
        pd.Timedelta(seconds=int(TIMEFRAME_SECONDS["1h"])), purge_gap=purge_gap,
    )
    assert isinstance(expect, tuple), "獨立重算未得到 plan 對"
    _tr, te = expect
    assert np.array_equal(
        np.asarray(got.test_plan.row_index), np.asarray(te.row_index)
    ), "test 段之 row_index 與生產端不符"
    assert got.test_plan.row_time_fingerprint == te.row_time_fingerprint, (
        "逐列指紋不符——列數相同不代表選到同一批列"
    )


def test_embargo_is_raised_by_declared_depth() -> None:
    """深度抬高 `embargo` 是既有規則（答案窗由 `purge_gap` 承載，兩者相加才是總隔離）。

    鑑別力：拿掉抬高 ⇒ `embargo` 退回 config 值、test 段起點前移。
    """
    _require(RUN_1H, KLINE)
    resolve, _err = _resolver()
    base = int(getattr(_cfg(), "embargo", 0) or 0)
    got = resolve(
        ff_run=FF_1H, symbol=SYM, ic_config=_cfg(),
        purge_gap=156, lookahead_depth_rows=base + 144,
    )
    assert got.embargo == base + 144, f"embargo 未被深度抬高：{got.embargo}"


def test_same_config_hash_across_symbols_requires_symbol_filter() -> None:
    """🔴 同一 `config_hash` **真的**跨多個 symbol 存在——實測本 run 之雜湊同時見於
    `BCHUSDT`／`BTCUSDT`／`ETHUSDT`。

    ⇒ 不篩 symbol 就會命中多個，取首個即是**拿到別的幣種之 run**（B10A 實際踩過）。
    本條把兩件事一起釘住：①不篩 ⇒ fail-closed（不猜）；②篩了 ⇒ 落在該 symbol 底下。
    鑑別力：把 `resolve_run_dir` 之多命中分支改成 `return hits[0]` 即轉紅。
    """
    _require(RUN_1H)
    from momentum.Analysis.event_samples.canonical_holdout import (
        CanonicalHoldoutError,
        resolve_run_dir,
    )

    all_hits = sorted((REPO / "data_cache/features").glob(f"*/*/{FF_1H}"))
    if len({h.parent.parent.name for h in all_hits}) < 2:
        pytest.skip("本機該 config_hash 未跨 symbol，本條之前提不成立")

    with pytest.raises(CanonicalHoldoutError) as ei:
        resolve_run_dir(FF_1H)  # 不給 symbols ⇒ 多命中
    assert ei.value.reason == "feature_run_ambiguous", (
        f"多命中未 fail-closed：{ei.value.reason}"
    )
    for sym in sorted({h.parent.parent.name for h in all_hits}):
        got = resolve_run_dir(FF_1H, symbols=[sym])
        assert got.parent.parent.name == sym, f"篩 {sym} 卻拿到 {got.parent.parent.name}"


def test_missing_run_is_named_error() -> None:
    """run 不存在 ⇒ 具名錯誤，不是 IndexError／FileNotFoundError。"""
    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve(ff_run="0" * 32, symbol=SYM, ic_config=_cfg(),
                purge_gap=156, lookahead_depth_rows=144)
    assert ei.value.reason == "feature_run_not_found"


def test_canonical_holdout_disabled_is_named_reason() -> None:
    """🔴 `Task 10.4` 邊界①：切分關閉 ⇒ 具名原因，plans 為 None（不是靜默回空）。"""
    _require(RUN_1H)
    resolve, _err = _resolver()
    cfg = _cfg()
    cfg.ic_train_test_split = False
    got = resolve(ff_run=FF_1H, symbol=SYM, ic_config=cfg,
                  purge_gap=156, lookahead_depth_rows=144)
    assert got.reason == "canonical_holdout_disabled"
    assert got.train_plan is None and got.test_plan is None
    assert got.feature_index is not None, "關閉切分不代表沒有 post-trim 索引"


def test_canonical_holdout_cross_tf_per_tf_has_run_timeframe() -> None:
    """🔴 `R5-C9` 3.：bars 之週期集合須為 `trigger_timeframes ∪ {run.timeframe}`。

    12h 事件 × 1h run：只載觸發週期（12h）時，`per_tf` 會缺 1h 列 ⇒ 判側錨點與
    特徵列鍵都取不到。本條把該聯集釘死。
    """
    from momentum.Analysis.event_samples.canonical_holdout import bars_timeframes_for

    assert bars_timeframes_for(["12h"], "1h") == ["12h", "1h"]
    assert bars_timeframes_for(["1h"], "12h") == ["12h", "1h"]
    assert bars_timeframes_for(["12h"], "12h") == ["12h"], "同週期不得重複"
    assert bars_timeframes_for(["12h", "4h"], "1h") == ["12h", "1h", "4h"]


def test_post_trim_index_is_not_raw_kline_universe() -> None:
    """post-trim 索引取自 run 之 `timestamps.parquet`，**不是** K 線原始 universe。

    兩者在未裁切時逐值相同，裁頭尾之後就位移（`D-002` §D2-3 實測：裁 5 根 ⇒ 位移 2 小時）
    ⇒ 必須共用同一個 universe，不是共用同一條公式。
    """
    _require(RUN_1H)
    from momentum.Analysis.event_samples.canonical_holdout import load_post_trim_index

    idx = load_post_trim_index(RUN_1H)
    ts = pd.read_parquet(RUN_1H / "timestamps.parquet")["timestamp"].to_numpy()
    assert len(idx) == len(ts), "索引長度須等於 run 之 timestamps 列數"
    assert int(idx[0].value // 10**6) == int(ts[0]) * 1000, "首列時刻須逐值相符"


def test_kline_cache_dir_is_feature_klines_not_app_cache() -> None:
    """🔴 K 線讀取器固定 `data_cache/feature_klines`，不得由呼叫端改指。

    應用層之 `data_cache/kline_cache.h5` 是另一個檔（headless 探針會寫入、可能有缺口），
    量化主線用錯檔會拿到不同的 bars。
    """
    from momentum.Analysis.event_samples.canonical_holdout import FEATURE_KLINE_CACHE_DIR

    assert FEATURE_KLINE_CACHE_DIR == "data_cache/feature_klines"
