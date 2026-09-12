"""SPLITUNIFY D-001 Task 8.2：producer 端 attest 與 `SplitPlan` 座標欄之契約測試。

規格：`docs/SPLITUNIFY_SPEC.D-001.md` Task 8.2 之固定文法斷言（producer 側）；
mutation `M-SU-D1-11`、`13`、`14`、`15`、`17`、`18`、`21`、`22`。

🔴 **本檔的核心紀律**：`CrossSymbolLeakageError` **繼承** `ValueError`
（`momentum/core/contracts.py:431`），所以 `pytest.raises(ValueError)` 對
「前置合法性閘」與「時間序往返閘」兩種失敗都會通過、**分不出來**。
若前置閘的測試只寫 `pytest.raises(ValueError)`，那麼把往返判準整個拿掉
（`M-SU-D1-18`）這些測試仍會全綠——那是廉價綠燈。
⇒ 前置閘一律額外斷言 `not isinstance(exc, CrossSymbolLeakageError)`。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import (
    CrossSymbolLeakageError,
    SplitPlan,
    attest_row_index_local,
    split_per_symbol,
)
from momentum.core.split_preview import build_row_time_fingerprint

SYM_A, SYM_B = "ETHUSDT", "BTCUSDT"
H1 = 3_600_000
BASE_S = 1_700_000_000          # epoch **秒**：本模組既有約定「純數字＝秒」
N_EACH = 12


def _interleaved_frame(n_each: int = N_EACH) -> pd.DataFrame:
    """兩標的於全框**交錯**（偶數列 A、奇數列 B），時間戳為 epoch 秒。"""
    rows = []
    for i in range(n_each):
        t = BASE_S + i * 3600
        rows.append({"symbol": SYM_A, "timestamp": t})
        rows.append({"symbol": SYM_B, "timestamp": t})
    return pd.DataFrame(rows)


def _splitter(group: pd.DataFrame):
    n = len(group)
    yield np.arange(0, n // 2, dtype=int), np.arange(n // 2 + 1, n, dtype=int)


def _expect_precheck_error(**kw) -> ValueError:
    """前置合法性閘應丟 `ValueError`，且**不得**是往返閘的 `CrossSymbolLeakageError`。"""
    with pytest.raises(ValueError) as ei:
        attest_row_index_local(role="attest-test", **kw)
    assert not isinstance(ei.value, CrossSymbolLeakageError), (
        "前置合法性閘必須排在往返比對**之前**；若丟出的是往返例外，代表前置閘被略過"
        "（負索引會回捲而使往返誤判相等——D-001 (4.7)）"
    )
    return ei.value


# ── producer 寫入之座標語意 ──────────────────────────────────────────────────
def test_interleaved_producer_writes_monotonic_local_ordinals() -> None:
    """兩標的於全框交錯時，各自的 `row_index_local` 必須連續遞增（Task 8.2 斷言）。"""
    plans = split_per_symbol(
        _interleaved_frame(), _splitter, "symbol", "timestamp",
        expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A, SYM_B},
    )
    assert len(plans) == 2
    for train, test in plans:
        for plan in (train, test):
            loc = np.asarray(plan.row_index_local)
            assert loc.size > 0, "空的序號讓後面的遞增斷言變成空洞通過"
            assert np.all(np.diff(loc) > 0)


def test_interleaved_producer_local_differs_from_full_frame_row_index() -> None:
    """交錯時 `row_index_local` 與全框 `row_index` **不得**恰好相等。

    若相等，這批 fixture 就藏得住「拿全框列號當標的內序號」的錯誤，
    整個 Task 8.2 的測試面會失去鑑別力（D-001 (4.18) 指定必測交錯的理由）。
    """
    plans = split_per_symbol(
        _interleaved_frame(), _splitter, "symbol", "timestamp",
        expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A, SYM_B},
    )
    differed = any(
        not np.array_equal(np.asarray(p.row_index_local), np.asarray(p.row_index))
        for tr, te in plans for p in (tr, te)
    )
    assert differed, "交錯 fixture 卻兩欄逐值相同 ⇒ fixture 沒造出交錯"


def test_single_symbol_frame_local_equals_row_index() -> None:
    """單標的 frame ⇒ `row_index_local` 逐值等於 `row_index`（Task 8.2 斷言）。"""
    frame = pd.DataFrame(
        {"symbol": [SYM_A] * N_EACH,
         "timestamp": [BASE_S + i * 3600 for i in range(N_EACH)]}
    )
    (train, test), = split_per_symbol(
        frame, _splitter, "symbol", "timestamp",
        expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A},
    )
    for plan in (train, test):
        assert np.array_equal(np.asarray(plan.row_index_local), np.asarray(plan.row_index))


# ── 時間序往返閘（只有這一類才是 CrossSymbolLeakageError）────────────────────
def test_attest_rejects_row_index_from_another_symbol() -> None:
    """`row_index` 含不屬於該 symbol 之列 ⇒ 往返必不等。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([0, 1, 2, 3], dtype=int)
    bad_ri = np.array([0, 2, 4, 7], dtype=int)      # 末列是另一個 symbol 的
    with pytest.raises(CrossSymbolLeakageError):
        attest_row_index_local(
            row_index=bad_ri, row_index_local=loc, sorted_positions=pos, role="attest-test",
        )


def test_attest_accepts_the_matching_roundtrip() -> None:
    """正例：往返成立即放行（否則上面那條可能是靠「什麼都擋」通過的）。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([0, 1, 2, 3], dtype=int)
    attest_row_index_local(
        row_index=pos[loc], row_index_local=loc, sorted_positions=pos, role="attest-test",
    )


def test_attest_rejects_when_roundtrip_differs_in_one_value() -> None:
    """只有**一個**值不等也必須擋（不得只比首尾或只比長度）。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([0, 1, 2, 3], dtype=int)
    bad_ri = pos[loc].copy()
    bad_ri[2] = 5
    with pytest.raises(CrossSymbolLeakageError):
        attest_row_index_local(
            row_index=bad_ri, row_index_local=loc, sorted_positions=pos, role="attest-test",
        )


def test_attest_accepts_unsorted_frame_order_when_local_is_correct() -> None:
    """該 symbol 的列在全框中**非**依時間排列時不得誤擋（R10：禁以 frame 序當判準）。

    `sorted_positions` 是「依時刻排序後」的全框位置，本身可以是亂序數字；
    改用 `_local_ordinals_for_symbol` 的 frame 序結果當判準，這條就會紅。
    """
    pos = np.array([7, 3, 9, 1], dtype=int)
    loc = np.array([0, 1, 2, 3], dtype=int)
    attest_row_index_local(
        row_index=pos[loc], row_index_local=loc, sorted_positions=pos, role="attest-test",
    )


# ── 前置合法性閘（一律不得是 CrossSymbolLeakageError）───────────────────────
def test_attest_precheck_rejects_negative_local() -> None:
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([-1, 1, 2, 3], dtype=int)
    exc = _expect_precheck_error(
        row_index=pos[np.array([0, 1, 2, 3])], row_index_local=loc, sorted_positions=pos,
    )
    assert "負值" in str(exc)


def test_attest_precheck_rejects_duplicate_local() -> None:
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([0, 1, 1, 2], dtype=int)
    exc = _expect_precheck_error(
        row_index=pos[np.array([0, 1, 1, 2])], row_index_local=loc, sorted_positions=pos,
    )
    assert "重複" in str(exc)


def test_attest_precheck_rejects_non_monotonic_local() -> None:
    pos = np.array([0, 2, 4, 6], dtype=int)
    loc = np.array([0, 2, 1, 3], dtype=int)
    exc = _expect_precheck_error(
        row_index=pos[np.array([0, 2, 1, 3])], row_index_local=loc, sorted_positions=pos,
    )
    assert "遞增" in str(exc)


def test_attest_precheck_rejects_length_mismatch() -> None:
    """長度不等必須擋——用 `zip` 實作會截斷成前綴比對而放行（`M-SU-D1-21`）。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    exc = _expect_precheck_error(
        row_index=np.array([0, 2, 4, 6], dtype=int),
        row_index_local=np.array([0, 1], dtype=int),
        sorted_positions=pos,
    )
    assert "長度" in str(exc)


def test_attest_precheck_rejects_empty_local_with_nonempty_row_index() -> None:
    """空序號配非空 `row_index` 不得空轉放行（等長前置先於「空則返回」）。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    _expect_precheck_error(
        row_index=np.array([0, 2, 4, 6], dtype=int),
        row_index_local=np.array([], dtype=int),
        sorted_positions=pos,
    )


def test_attest_precheck_rejects_out_of_range_local() -> None:
    pos = np.array([0, 2, 4, 6], dtype=int)
    exc = _expect_precheck_error(
        row_index=np.array([0, 2, 4, 6], dtype=int),
        row_index_local=np.array([0, 1, 2, 4], dtype=int),
        sorted_positions=pos,
    )
    assert "超出" in str(exc)


@pytest.mark.parametrize(
    "bad_local",
    [
        np.array([0.0, 1.0, 2.0, 3.0], dtype="float64"),
        np.array([True, False, True, False]),
        np.array([0, 1, 2, 3], dtype=object),
    ],
    ids=["float", "bool", "object"],
)
def test_attest_precheck_rejects_non_integer_dtype(bad_local) -> None:
    """整數值的浮點／布林／物件型都不得靠轉型救（`M-SU-D1-22`）。"""
    pos = np.array([0, 2, 4, 6], dtype=int)
    exc = _expect_precheck_error(
        row_index=np.array([0, 2, 4, 6], dtype=int),
        row_index_local=bad_local,
        sorted_positions=pos,
    )
    assert "dtype" in str(exc)


# ── `SplitPlan` 兩個 row 欄之不可變性（縱深防禦層）──────────────────────────
def _plan(row_index, local) -> SplitPlan:
    ms = np.asarray([1_700_000_000_000 + i * H1 for i in range(64)], dtype="int64")
    loc = np.asarray(local, dtype=int)
    return SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray(row_index, dtype=int),
        time_bounds=(int(ms[loc[0]]), int(ms[loc[-1]])),
        purge_gap=0,
        embargo=0,
        purge_semantic="rows",
        base_universe_hash="u",
        symbol=SYM_A,
        row_index_local=loc,
        row_time_fingerprint=build_row_time_fingerprint(
            positions=loc, feature_ts_ms=ms[loc], symbol=SYM_A, base_universe_hash="u",
        ),
    )


def test_plan_row_arrays_reject_in_place_write() -> None:
    """建構後對兩欄原地寫入 ⇒ 丟例外（`M-SU-D1-14`）。"""
    plan = _plan([0, 2, 4], [0, 1, 2])
    for field in ("row_index", "row_index_local"):
        arr = getattr(plan, field)
        with pytest.raises(ValueError):
            arr[0] = 999


def test_plan_row_arrays_are_defensively_copied() -> None:
    """建構後改動呼叫端持有的來源陣列 ⇒ plan 內兩欄不變（`M-SU-D1-13`）。"""
    src_ri = np.array([0, 2, 4], dtype=int)
    src_loc = np.array([0, 1, 2], dtype=int)
    plan = _plan(src_ri, src_loc)
    src_ri[0] = 111
    src_loc[0] = 222
    assert int(np.asarray(plan.row_index)[0]) == 0
    assert int(np.asarray(plan.row_index_local)[0]) == 0


def test_plan_row_arrays_reject_setflags_write_true() -> None:
    """唯讀旗標可被翻回，故底層 buffer 必須本身不可變（R10 實測；`M-SU-D1-17`）。

    只做 `setflags(write=False)` 的版本會讓這條紅——那正是要擋的實作。
    """
    plan = _plan([0, 2, 4], [0, 1, 2])
    for field in ("row_index", "row_index_local"):
        with pytest.raises(ValueError):
            getattr(plan, field).setflags(write=True)


# ── 🔴 b8 審碼 R1：codex 兩條 P1 的回歸測試（主委已獨立複驗成立）─────────────
#    這兩條攻的是 **producer 路徑**，不是 attest 函式本身——上面那些測試直接呼叫 attest，
#    所以 dtype 閘看得到原始型別；但 producer 先 `astype(int)` 再 attest 時，閘被繞過。
#    `M-SU-D1-22` 抓不到它，正是因為它測的是函式而非路徑。


def test_producer_rejects_float_ordinals_before_cast() -> None:
    """`CODEX-R1-P1-01`：dtype 閘必須擋在 `astype(int)` **之前**。

    修正前實跑：`float64 [0.,1.,2.]` 靜默救活成 `int64 [0,1,2]` 並產出 plan。
    """
    def splitter(group: pd.DataFrame):
        yield (np.array([0.0, 1.0, 2.0], dtype="float64"),
               np.array([5.0, 6.0], dtype="float64"))

    with pytest.raises(ValueError, match="dtype"):
        split_per_symbol(
            _interleaved_frame(), splitter, "symbol", "timestamp",
            expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A, SYM_B},
        )


def test_producer_rejects_bool_ordinals_by_dtype_gate_not_by_luck() -> None:
    """bool 序號必須由 **dtype 閘**擋下，而不是碰巧被別的閘攔到。

    🔴 修正前它也會 raise，但訊息是「時間戳非嚴格遞增」——bool 當索引取到逆序時刻而已。
    斷言限定 `dtype` 才分得出是哪一道閘擋的；不限定就會變成沒有鑑別力的測試
    （與本檔開頭那條紀律同源）。
    """
    def splitter(group: pd.DataFrame):
        yield np.array([True, False, True]), np.array([5, 6], dtype=int)

    with pytest.raises(ValueError, match="dtype"):
        split_per_symbol(
            _interleaved_frame(), splitter, "symbol", "timestamp",
            expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A, SYM_B},
        )


def test_producer_rejects_nat_anywhere_on_the_time_axis() -> None:
    """`CODEX-R1-P1-02`：`NaT` 只要在時間軸上就要擋，**不限**被選中的列。

    修正前只對被選列做時刻正規化 ⇒ 未選列的缺時刻無人擋，卻仍參與 rows 單位的
    purge／embargo 計數，等於拿「不知道何時」的列當隔離區的刻度。
    """
    ts = [pd.Timestamp(BASE_S + i * 3600, unit="s") for i in range(N_EACH)]
    ts[8] = pd.NaT                      # 第 8 列不在 train(0-2)、也不在 test(5-6)
    frame = pd.DataFrame({"symbol": [SYM_A] * N_EACH, "timestamp": ts})

    def splitter(group: pd.DataFrame):
        yield np.arange(0, 3, dtype=int), np.arange(5, 7, dtype=int)

    with pytest.raises(ValueError, match="NaT"):
        split_per_symbol(
            frame, splitter, "symbol", "timestamp",
            expected_freq="1h", base_universe_hash="u", allowed_symbols={SYM_A},
        )


def test_adapter_path_nat_raises_the_contract_exception_not_nameerror() -> None:
    """🔴 b8 審碼 R2 三家一致：adapter 的 NaT 閘引用了**未匯入**的 `AlignmentViolationError`。

    這是主委修 `CODEX-R1-P1-02` 時**自己引入**的缺陷：該閘觸發時拋 `NameError`，
    而 `NameError` 不在 `ValueError` 階層，會穿透呼叫端既有的
    `except ValueError`／`except AlignmentViolationError` ⇒ 契約例外形同未交付。

    上一條測試只覆蓋 `split_per_symbol` 路徑，所以缺 import 全綠漏網——
    **同一道閘在兩條 producer 路徑上各需一條測試**。
    """
    from momentum.core.contracts import AlignmentViolationError
    from momentum.Analysis.ic_split_adapter import ICSplitAdapter

    ts = [pd.Timestamp(BASE_S + i * 3600, unit="s") for i in range(N_EACH)]
    ts[8] = pd.NaT
    frame = pd.DataFrame({"symbol": [SYM_A] * N_EACH, "timestamp": ts})

    with pytest.raises(AlignmentViolationError, match="NaT"):
        ICSplitAdapter._with_row_positions(frame, "symbol", "timestamp")


def test_adapter_path_accepts_a_clean_time_axis() -> None:
    """正例：時間軸乾淨時 adapter 路徑不得誤擋（否則上面那條可能是靠「什麼都擋」通過的）。"""
    from momentum.Analysis.ic_split_adapter import ICSplitAdapter

    ts = [pd.Timestamp(BASE_S + i * 3600, unit="s") for i in range(N_EACH)]
    frame = pd.DataFrame({"symbol": [SYM_A] * N_EACH, "timestamp": ts})
    out = ICSplitAdapter._with_row_positions(frame, "symbol", "timestamp")
    assert len(out) == N_EACH
    assert "_split_row_pos" in out.columns
