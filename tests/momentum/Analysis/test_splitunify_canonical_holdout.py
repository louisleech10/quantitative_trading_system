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


def test_canonical_holdout_insufficient_rows_is_named_reason() -> None:
    """🔴 `Task 10.4` 邊界②：`_build_holdout_split_plan` 回 `SkippedResult`
    ⇒ `reason=canonical_holdout_insufficient_rows`，plans 為 None。

    🔴 **不 mock 切分器**——以真實 run 索引配一個大到切不出測試段的 `purge_gap`
    （隔離區吃光整條索引），走的是與生產端同一支 `_build_holdout_split_plan`。
    mock 會把「切分器何時判不足」這個真正的判準換成我自己的假設。

    鑑別力：把「非 tuple ⇒ 具名 reason」那段改成回 `plans=None, reason=None`
    ⇒ 下面兩條 assert 轉紅（靜默回空正是本條要擋的）。
    """
    _require(RUN_1H)
    resolve, _err = _resolver()
    index_len = len(_post_trim_index())
    got = resolve(
        ff_run=FF_1H, symbol=SYM, ic_config=_cfg(),
        purge_gap=index_len * 2,   # 隔離區比整條索引還長 ⇒ 切不出測試段
        lookahead_depth_rows=0,
    )
    assert got.reason == "canonical_holdout_insufficient_rows", (
        f"切不出測試段時未給具名原因（reason={got.reason!r}）——靜默回空會被當成『沒有邊界』"
    )
    assert got.train_plan is None and got.test_plan is None
    assert got.feature_index is not None, "切不出計畫不代表沒有 post-trim 索引"


def _post_trim_index():
    from momentum.factories import create_post_trim_index_loader

    return create_post_trim_index_loader()(RUN_1H)


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


def test_resolver_does_not_mutate_caller_config() -> None:
    """🔴 `CODEX-R41-P1-01`：resolver **不得**就地改寫呼叫端之 `ICConfig`。

    形態：同一個 config 物件先以較大深度、再以較小深度呼叫。就地改寫時第二次會
    **承襲第一次較大的 embargo** ⇒ 前一批之 lookahead 洩漏到下一批之 purge／holdout
    （掃描格逐格、retry、換事件批都會踩到）。
    鑑別力：把 `_config_with_embargo` 改回 `ic_config.embargo = raised` 即轉紅。
    """
    _require(RUN_1H, KLINE)
    resolve, _err = _resolver()
    cfg = _cfg()
    before = int(getattr(cfg, "embargo", 0) or 0)

    first = resolve(ff_run=FF_1H, symbol=SYM, ic_config=cfg,
                    purge_gap=156, lookahead_depth_rows=before + 5)
    assert int(getattr(cfg, "embargo", 0) or 0) == before, (
        f"呼叫端之 config 被就地改寫：{before} → {getattr(cfg, 'embargo', None)}"
    )
    second = resolve(ff_run=FF_1H, symbol=SYM, ic_config=cfg,
                     purge_gap=156, lookahead_depth_rows=0)
    assert first.embargo == before + 5
    assert second.embargo == before, (
        f"第二次承襲了第一次的 embargo（{second.embargo}）——跨批污染"
    )


def test_config_without_immutable_copy_path_is_fail_closed() -> None:
    """無不可變複本路徑之 config ⇒ fail-closed，**不得**退回就地改寫。"""
    from momentum.Analysis.event_samples.canonical_holdout import (
        CanonicalHoldoutError,
        _config_with_embargo,
    )

    class _Plain:
        embargo = 0

    with pytest.raises(CanonicalHoldoutError) as ei:
        _config_with_embargo(_Plain(), 7)
    assert ei.value.reason == "ic_config_not_copyable"


# ── `Task 10.4` fail-closed 出口之具名測試（r17 `CODEX-R17-P2-01`）────────────
# 🔴 出生理由：擴充後之驗收清單 179 passed，但本檔行覆蓋僅 90%，未覆蓋的 12 行
#    **全是具名 fail-closed 出口**。「全綠」與「這些出口還在」是兩件事——把任一條
#    raise 改成放行或回空索引，179 條沒有一條會紅。兩家對「要不要補」分歧
#    （codex 要、composer 判不必），離線裁定採較嚴版：補。
# 🔴 這些測試**不 mock 切分器**；用的是真實形狀之 `timestamps.parquet` 與純 parser 輸入。


def _run_dir_with_timestamps(tmp_path, *, symbol="ETHUSDT", tf="1h", values=None):
    """造一個**形狀真實**的 run 目錄：`<symbol>/<tf>/<hash>/timestamps.parquet`。

    🔴 `values=None` 代表不寫該檔（測缺檔）；`values=[]` 代表寫一個空索引。
    欄名與單位與生產一致（`timestamp`＝epoch 秒），故走的是同一條讀取路徑。
    """
    d = tmp_path / "data_cache/features" / symbol / tf / ("f" * 32)
    d.mkdir(parents=True)
    if values is not None:
        pd.DataFrame({"timestamp": np.array(values, dtype=np.int64)}).to_parquet(
            d / "timestamps.parquet",
        )
    return d


def test_missing_timestamps_parquet_is_named_error(tmp_path) -> None:
    """run 目錄在、`timestamps.parquet` 不在 ⇒ 具名 `feature_run_missing_timestamps`。

    🔴 這是本票之關鍵不變式：涵蓋判定（manifest）通過**不保證**索引存在。
    此處若靜默回空索引，處置帳會把每一筆都記成 `feature_row_not_in_feature_index`
    ——一份看起來很有內容、實際全錯的帳。
    鑑別力：把該 raise 改成 `return pd.DatetimeIndex([])` ⇒ 本條轉紅。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        CanonicalHoldoutError, load_post_trim_index,
    )

    with pytest.raises(CanonicalHoldoutError) as ei:
        load_post_trim_index(_run_dir_with_timestamps(tmp_path, values=None))
    assert ei.value.reason == "feature_run_missing_timestamps"


def test_empty_post_trim_index_is_named_error(tmp_path) -> None:
    """`timestamps.parquet` 在但零列 ⇒ 具名 `feature_run_empty_index`，不回空索引。

    鑑別力：拿掉 `ts.size == 0` 那道閘 ⇒ 本條轉紅（會回一個合法但空的索引）。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        CanonicalHoldoutError, load_post_trim_index,
    )

    with pytest.raises(CanonicalHoldoutError) as ei:
        load_post_trim_index(_run_dir_with_timestamps(tmp_path, values=[]))
    assert ei.value.reason == "feature_run_empty_index"


def test_unknown_run_timeframe_is_named_error(tmp_path) -> None:
    """run 目錄之週期段不在 `TIMEFRAME_SECONDS` ⇒ 具名 `feature_run_unknown_timeframe`。

    🔴 走**完整 resolver**（非直呼內部函式）：`repo_root` 指向 tmp 之 data_cache，
    索引與目錄形狀皆真實，只有週期字面是未知值。
    鑑別力：拿掉該閘 ⇒ 後續 `pd.Timedelta(seconds=...)` 會以 `KeyError` 炸在別處
    （非具名），本條之 `reason` 斷言轉紅。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        CanonicalHoldoutError, resolve_canonical_holdout,
    )

    run = _run_dir_with_timestamps(tmp_path, tf="7h", values=[1_700_000_000 + 3600 * i for i in range(50)])
    with pytest.raises(CanonicalHoldoutError) as ei:
        resolve_canonical_holdout(
            ff_run=run.name, symbol="ETHUSDT", ic_config=_cfg(),
            purge_gap=1, lookahead_depth_rows=0, repo_root=tmp_path,
        )
    assert ei.value.reason == "feature_run_unknown_timeframe"


def test_time_range_endpoint_non_string_is_named_error() -> None:
    """`time_range` 端點非字串 ⇒ 具名 `feature_coverage_unknown_timestamp_format`。

    🔴 不得以 `int()` 兜底：manifest 實測為「epoch 秒之**數字字串**」，
    型別一變就代表落檔格式換了，猜一個轉型只會把格式漂移變成安靜的數值偏移。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        FeatureRunCoverageError, _parse_time_range_endpoint,
    )

    with pytest.raises(FeatureRunCoverageError) as ei:
        _parse_time_range_endpoint(1_700_000_000)
    assert ei.value.reason == "feature_coverage_unknown_timestamp_format"


def test_time_range_endpoint_unparseable_string_is_named_error() -> None:
    """既非十進位數字字串亦非 ISO ⇒ 具名 `feature_coverage_unknown_timestamp_format`。

    鑑別力：把 `except ValueError` 改成吞掉並回 0 ⇒ 本條轉紅，而涵蓋判定會把
    run 起點當成 1970 年 ⇒ 任何事件都「在涵蓋範圍內」。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        FeatureRunCoverageError, _parse_time_range_endpoint,
    )

    with pytest.raises(FeatureRunCoverageError) as ei:
        _parse_time_range_endpoint("not-a-timestamp")
    assert ei.value.reason == "feature_coverage_unknown_timestamp_format"


def test_config_copy_fallbacks_do_not_mutate_caller() -> None:
    """Pydantic v1 之 `copy(update=)` 與 dataclass 之 `replace` 兩條後備路徑。

    🔴 生產之 `ICConfig` 走 Pydantic v2（`model_copy`），這兩條**只在型別換掉時**才用到
    ——正因如此它們最容易在無人察覺下腐爛成「就地改寫」，而就地改寫正是
    `CODEX-R41-P1-01` 要消滅的行為（前一批之 embargo 洩漏到下一批）。
    本條逐條釘住：回傳之 embargo 已抬高，且**呼叫端物件逐欄不變**。
    """
    import dataclasses

    from momentum.Analysis.event_samples.canonical_holdout import _config_with_embargo

    class _V1Like:
        """只有 `copy(update=)` 之物件（Pydantic v1 形狀）。"""

        def __init__(self, embargo: int) -> None:
            self.embargo = embargo

        def copy(self, update=None):
            return _V1Like(int((update or {}).get("embargo", self.embargo)))

    v1 = _V1Like(3)
    got = _config_with_embargo(v1, 11)
    assert got is not v1 and got.embargo == 11
    assert v1.embargo == 3, "Pydantic v1 後備路徑就地改寫了呼叫端之 config"

    @dataclasses.dataclass(frozen=True)
    class _DCLike:
        embargo: int

    dc = _DCLike(embargo=3)
    got2 = _config_with_embargo(dc, 11)
    assert got2 is not dc and got2.embargo == 11
    assert dc.embargo == 3


def test_v1_copy_rejecting_update_kwarg_falls_through_to_dataclass() -> None:
    """`copy()` 不吃 `update=` 而丟 `TypeError` ⇒ 不得中止，續試 dataclass 路徑。

    🔴 這條守的是「後備鏈不得在中途斷掉」：若 `except TypeError` 改成 `raise`，
    一個同時是 dataclass、又剛好有無參數 `copy()` 的 config 會被誤判為不可複製。
    """
    import dataclasses

    from momentum.Analysis.event_samples.canonical_holdout import _config_with_embargo

    @dataclasses.dataclass
    class _BadCopy:
        embargo: int

        def copy(self):          # 不接受 `update=` ⇒ 呼叫時 TypeError
            raise AssertionError("本體不該被執行——TypeError 在呼叫當下就發生")

    src = _BadCopy(embargo=2)
    got = _config_with_embargo(src, 9)
    assert got.embargo == 9 and src.embargo == 2


def test_symbol_mismatch_is_served_by_run_not_found() -> None:
    """🔴 邊界③之「識別不符」**實際由 `feature_run_not_found` 承擔**，不是 `feature_run_symbol_mismatch`。

    `resolve_run_dir` 先以 symbol 篩選；`resolve_canonical_holdout` 傳的正是
    `symbols=[symbol]` ⇒ 檔案裡那條 `feature_run_symbol_mismatch` 在現行唯一呼叫
    路徑下**不可達**。本條把「真正會發生的那個 reason」釘住，免得日後有人看到那條
    死守衛就以為邊界③已被它覆蓋（空殼守衛之假保證）。

    🔴 本條刻意用**真實存在於別的 symbol 之 `config_hash`**：同一雜湊實測橫跨
    BCHUSDT／BTCUSDT／ETHUSDT 三個幣種，所以「找得到目錄、但不屬於本 symbol」
    這個情境是真的，不是造出來的。
    """
    _require(RUN_1H)
    from momentum.Analysis.event_samples.canonical_holdout import resolve_run_dir

    # 同一 hash 在 ETHUSDT 之下確實存在
    assert resolve_run_dir(FF_1H, symbols=[SYM]).parent.parent.name == SYM

    resolve, err_cls = _resolver()
    with pytest.raises(err_cls) as ei:
        resolve(ff_run=FF_1H, symbol="NOSUCHUSDT", ic_config=_cfg(),
                purge_gap=156, lookahead_depth_rows=144)
    assert ei.value.reason == "feature_run_not_found", (
        f"識別不符之具名 reason 改變了（實得 {ei.value.reason!r}）"
        "——邊界③之字面契約以本條為準"
    )
