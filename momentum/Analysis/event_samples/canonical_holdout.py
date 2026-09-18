"""SPLITUNIFY `Task 10.4`：canonical 邊界之**單一解析入口**（`R5-C1` 輸入 1–6、`R5-C2`）。

出生理由（v7 `R5-C1`）：事件掃描端與 IC 端各自導出切分邊界，而 canonical 邊界只能有一條。
比對腳本 `scripts/splitunify_ic_event_report_diff.py` 在 B10A 審碼輪被連續打穿兩次，
病根都是「腳本自己算了一份」——邊界寫死 `oos_test_size=0.2`、深度抬高之 embargo 沒接上。
⇒ 邊界解析一律**只有這一份**；IC 端、事件掃描端與比對腳本都呼叫它。

🔴 **不載整份特徵矩陣**（`Task 10.4` 實作要點 2）：只讀 FF run 之 `timestamps.parquet`
建出 post-trim 之列索引。本 run 之 `raw/` 實測 7.5 GB（含 L2 chunk），載進來即 OOM
（B10A 實跑兩次 `rc=137`）。邊界只需要索引，不需要值。

🔴 **本模組不 import `api/`**（Rule 1）。錯誤以具名例外表達，呼叫端自行映射。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime   # `_parse_time_range_endpoint` 之 ISO 解析（隨 coverage 一併搬入）
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

#: K 線讀取器之固定快取目錄（`Task 10.4` 實作要點 2：不得由呼叫端改指）。
#: 🔴 與應用層之 `data_cache/kline_cache.h5` **不是同一個檔**——後者由 headless 搜尋探針寫入、
#: 可能有缺口；量化主線一律用本目錄下之 `kline_cache.h5`。
FEATURE_KLINE_CACHE_DIR = "data_cache/feature_klines"

#: FF run 目錄之根。
_FEATURES_DIR = "data_cache/features"

#: 無邊界之具名原因（`Task 10.4` 邊界①②；值集與 `split_unify.json` 之語意對齊）。
REASON_DISABLED = "canonical_holdout_disabled"
REASON_INSUFFICIENT_ROWS = "canonical_holdout_insufficient_rows"


class CanonicalHoldoutError(Exception):
    """邊界解析之具名失敗（run 不存在、識別不符、交集為空等）。"""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = str(reason)
        self.message = str(message)
        super().__init__(f"{self.reason}: {self.message}")


@dataclass(frozen=True)
class CanonicalHoldout:
    """邊界解析之結果。

    `train_plan`／`test_plan` 為 `None` 時，`reason` 必為具名原因之一（不得同時為 None）。
    """

    train_plan: Optional[Any]
    test_plan: Optional[Any]
    feature_index: Optional[pd.Index]
    reason: Optional[str]
    oos_test_size: Optional[float]
    purge_gap: Optional[int]
    embargo: Optional[int]
    run_timeframe: str
    symbol: str


def resolve_run_dir(
    ff_run: str, *, symbols: Optional[Sequence[str]] = None, repo_root: Optional[Path] = None,
) -> Path:
    """以 `config_hash` 定位 FF run 目錄。

    🔴 **同一 `config_hash` 可存在於多個 symbol**（實測 BCHUSDT 與 ETHUSDT 同雜湊）
    ⇒ 必須以事件批之 symbol 篩選；篩選後仍多於一個即 fail-closed（不猜）。
    """
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[3]
    hits = sorted((root / _FEATURES_DIR).glob(f"*/*/{ff_run}"))
    if symbols:
        want = {str(s) for s in symbols}
        hits = [h for h in hits if h.parent.parent.name in want]
    if not hits:
        raise CanonicalHoldoutError(
            "feature_run_not_found",
            f"找不到 FF run {ff_run!r}（symbols={sorted(symbols or [])}）",
        )
    if len(hits) > 1:
        raise CanonicalHoldoutError(
            "feature_run_ambiguous",
            f"FF run {ff_run!r} 在多個路徑命中：{[str(h) for h in hits]}——不猜（fail-closed）",
        )
    return hits[0]


def load_post_trim_index(run_dir: Path) -> pd.Index:
    """由 run 之 `timestamps.parquet` 建 post-trim 之毫秒索引（**不載特徵值**）。

    🔴 索引是 post-trim 的——EVTALIGN 期間對齊把特徵頭尾裁掉之後的 universe，
    不是 K 線原始 universe（`D-002` §D2-3：裁頭尾各 5 根即位移 2 小時）。
    """
    ts_path = run_dir / "timestamps.parquet"
    if not ts_path.is_file():
        raise CanonicalHoldoutError(
            "feature_run_missing_timestamps",
            f"FF run 缺 {ts_path}——post-trim 索引無從建立（fail-closed）",
        )
    ts = pd.read_parquet(ts_path)["timestamp"].to_numpy().astype(np.int64) * 1000
    if ts.size == 0:
        raise CanonicalHoldoutError(
            "feature_run_empty_index", f"FF run {run_dir.name} 之 post-trim 索引為空（fail-closed）",
        )
    return pd.to_datetime(ts, unit="ms")


def bars_timeframes_for(
    trigger_timeframes: Sequence[str], run_timeframe: str,
) -> list:
    """bars 須載入之週期＝`trigger_timeframes ∪ {feature_run.timeframe}`（`R5-C9` 3.）。

    🔴 只載觸發週期是本票要修掉的缺陷之一：跨週期批（1h 事件 × 12h run）之
    `per_tf` 會缺 run 週期之列，判側錨點與特徵列鍵都取不到。
    """
    return sorted({str(t) for t in trigger_timeframes if t} | {str(run_timeframe)})


def _config_with_embargo(ic_config: Any, embargo: int) -> Any:
    """回一個 `embargo` 已設好之**複本**；呼叫端傳入之物件逐欄不變。

    🔴 `CODEX-R41-P1-01`：就地改寫會讓同一個 config 被重用時承襲前一次之 embargo。
    依序試三條不可變路徑，全部失敗即 fail-closed——**不得**退回就地改寫，
    那正是本函式要消滅的行為。
    """
    # ① Pydantic v2（本專案之 `ICConfig` 實際型別）
    model_copy = getattr(ic_config, "model_copy", None)
    if callable(model_copy):
        return model_copy(update={"embargo": int(embargo)})
    # ② Pydantic v1
    copy_fn = getattr(ic_config, "copy", None)
    if callable(copy_fn):
        try:
            return copy_fn(update={"embargo": int(embargo)})
        except TypeError:
            pass
    # ③ dataclass（含 frozen）
    import dataclasses as _dc

    if _dc.is_dataclass(ic_config):
        return _dc.replace(ic_config, embargo=int(embargo))
    raise CanonicalHoldoutError(
        "ic_config_not_copyable",
        f"{type(ic_config).__name__} 無不可變複本路徑（model_copy／copy／dataclass 皆不適用）"
        "——不得就地改寫呼叫端之 config（fail-closed）",
    )


def resolve_canonical_holdout(
    *,
    ff_run: str,
    symbol: str,
    ic_config: Any,
    purge_gap: int,
    lookahead_depth_rows: int,
    repo_root: Optional[Path] = None,
) -> CanonicalHoldout:
    """由 FF run 索引與 IC 設定導出**唯一**之 canonical 邊界。

    `purge_gap`：答案窗換算之 purge 下界（呼叫端由 `event_isolation.label_window_rows` 導出）。
    `lookahead_depth_rows`：批次宣告之 look-ahead 深度；用來**抬高** `embargo`。
      🔴 深度抬高是既有規則（EVTLABEL Task 2.1）：`embargo` 只承載「挑樣本時看了多遠」，
      答案窗由 `purge_gap` 承載。兩者相加才是總隔離，不得互相取代。

    邊界（`Task 10.4` 之①②）：
      ① `ic_train_test_split` 關閉 ⇒ `reason=canonical_holdout_disabled`、plans 為 None；
      ② `_build_holdout_split_plan` 回 `SkippedResult` ⇒ `reason=canonical_holdout_insufficient_rows`。
    """
    from momentum.Analysis.ic_filter_orchestrator import _build_holdout_split_plan

    run_dir = resolve_run_dir(ff_run, symbols=[symbol], repo_root=repo_root)
    run_tf = run_dir.parent.name
    # 🔴 **本條在現行唯一呼叫路徑下不可達**（r17 兩家與主委各自實測）：上一行已傳
    #    `symbols=[symbol]`，`resolve_run_dir` 先以 symbol 篩選 ⇒ 不符者一律在該處
    #    以 `feature_run_not_found` 擋下，永遠走不到這裡。三個共用同一 `config_hash`
    #    的幣種實測 `mismatch=False`。
    #    留著是為了「上一行哪天不再傳 `symbols`」時仍有守衛，**但不得**因為它存在
    #    就宣稱邊界③之「識別不符」由它承擔——實際承擔者是 `feature_run_not_found`
    #    （見 `test_symbol_mismatch_is_served_by_run_not_found`）。
    #    🔴 不為它補測試：要測就得 mock `resolve_run_dir`，那是替空殼造一個假綠。
    if run_dir.parent.parent.name != str(symbol):   # pragma: no cover - 見上
        raise CanonicalHoldoutError(
            "feature_run_symbol_mismatch",
            f"FF run {ff_run!r} 屬 {run_dir.parent.parent.name!r}，與事件批之 {symbol!r} 不符",
        )
    index = load_post_trim_index(run_dir)

    if not bool(getattr(ic_config, "ic_train_test_split", True)):
        return CanonicalHoldout(
            train_plan=None, test_plan=None, feature_index=index,
            reason=REASON_DISABLED, oos_test_size=None, purge_gap=None, embargo=None,
            run_timeframe=run_tf, symbol=str(symbol),
        )

    # 🔴 embargo 由深度抬高——但**絕不就地改寫呼叫端之 config**（`CODEX-R41-P1-01`）。
    #    前版做 `ic_config.embargo = raised`，於是同一個 config 物件重用時（掃描格逐格、
    #    retry、不同事件批）第二次會**承襲第一次較大的 embargo**：提出方實跑證據——
    #    先以深度 5 再以深度 0 呼叫，第二次回傳仍是 5 ⇒ 前一批之 lookahead 洩漏到下一批之
    #    purge／holdout。這不是數值誤差，是打破「輸入 config 屬於呼叫端」之可重入契約。
    #    ⇒ 一律傳 clone 給 `_build_holdout_split_plan`；三種形態各有不可變複本路徑。
    raised = max(int(getattr(ic_config, "embargo", 0) or 0), int(lookahead_depth_rows))
    cfg = _config_with_embargo(ic_config, raised)

    from momentum.core.constants import TIMEFRAME_SECONDS

    if run_tf not in TIMEFRAME_SECONDS:
        raise CanonicalHoldoutError(
            "feature_run_unknown_timeframe",
            f"FF run 之週期 {run_tf!r} 不在 TIMEFRAME_SECONDS 內（fail-closed）",
        )
    expected_freq = pd.Timedelta(seconds=int(TIMEFRAME_SECONDS[run_tf]))
    feats = pd.DataFrame(index=index)
    built = _build_holdout_split_plan(
        feats, cfg, str(symbol), expected_freq, purge_gap=int(purge_gap),
    )
    if not isinstance(built, tuple):
        return CanonicalHoldout(
            train_plan=None, test_plan=None, feature_index=index,
            reason=REASON_INSUFFICIENT_ROWS, oos_test_size=float(getattr(cfg, "oos_test_size", float("nan"))),
            purge_gap=int(purge_gap), embargo=raised, run_timeframe=run_tf, symbol=str(symbol),
        )
    train_plan, test_plan = built
    return CanonicalHoldout(
        train_plan=train_plan, test_plan=test_plan, feature_index=index, reason=None,
        oos_test_size=float(getattr(cfg, "oos_test_size", float("nan"))),
        purge_gap=int(purge_gap), embargo=raised, run_timeframe=run_tf, symbol=str(symbol),
    )


# ── `Task 10.4` 實作要點 2：coverage 判定由 `api/services` 搬入本模組 ──────────
# 🔴 出生理由（`CODEX-R45-P1-01`）：coverage 原本住在 `api/services/ic_analysis_service.py`，
#    而 canonical 邊界解析已下沉到本模組 ⇒ 事件掃描端要走同一套規則時只能再抄一份。
#    規則本體逐字搬移（判定與訊息不變）；service 端改為 re-export，既有 import 路徑不壞。

#: 合理性上界＝2100-01-01（epoch 秒）。超出即判 parse failure（SPEC Task 7.7 ④ 之字面）。
#: 🔴 與 `_parse_time_range_endpoint` 同批搬入：留在 service 端會讓搬過來的函式
#:    在 import 當下看起來正常、**跑到那一行才** NameError（本輪實際踩到）。
_EPOCH_SECONDS_UPPER_BOUND = 4102444800


class FeatureRunCoverageError(ValueError):
    """Task 7.7 之 fail-closed 例外。`reason` 取自 `ic_report_contract.reasons.analysis_rejected`。"""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(f"{reason}: {message}")


def _parse_time_range_endpoint(value: Any) -> int:
    """`time_range` 之單一端點字串 → epoch ms。**解析順序寫死：先數字後 ISO**（SPEC 7.7 ④）。

    🔴 為什麼順序不能反：現存非 legacy manifest 的 `time_range` 是 **epoch 秒之數字字串**
    （實測 12/14 份如此，例 `{"start": "1704067200", ...}`）。先試 `fromisoformat` 會對它直接
    raise ⇒ **全部現存 run 都會被判成 parse failure**。R5 版就是這樣寫的，三家全員以真實
    manifest 打穿。

    🔴 tz-naive ISO ⇒ fail-closed，**不當成 UTC**：把 naive 當 UTC 是個假設，
    假設錯了整個覆蓋判斷會偏移，而偏移多少取決於使用者的時區——看不出來也修不掉。
    """
    if not isinstance(value, str):
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"time_range 端點須為字串，實得 {type(value).__name__}",
        )
    s = value.strip()
    body = s[1:] if s.startswith("-") else s
    if body.isdigit():
        seconds = int(s)
        if not (0 < seconds < _EPOCH_SECONDS_UPPER_BOUND):
            raise FeatureRunCoverageError(
                "feature_coverage_unknown_timestamp_format",
                f"epoch 秒 {seconds} 落在合理範圍外（0, {_EPOCH_SECONDS_UPPER_BOUND}）",
            )
        return seconds * 1000
    try:
        parsed = datetime.fromisoformat(s)
    except ValueError as exc:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"既非十進位數字字串亦非 ISO 格式：{s!r}（{exc}）",
        ) from exc
    if parsed.tzinfo is None:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_timestamp_format",
            f"ISO 字串 {s!r} 為 tz-naive——不得假設為 UTC（假設錯誤會使覆蓋判斷整體偏移）",
        )
    return int(parsed.timestamp() * 1000)


@dataclass(frozen=True)
class FeatureRunCoverage:
    """`check_feature_run_coverage` 之結果（EVTALIGN Task 3.1）。

    `evaluated=False` ⇒ 沒有窗、什麼都沒判（呼叫端沿用 prepared 之全集）。
    `covered_event_ids`／`dropped`：逐事件分類；`dropped` 為 `(event_id, reason)`，
    reason 目前只有 `outside_feature_run`。
    """

    evaluated: bool
    run_start_ms: Optional[int]
    run_end_ms: Optional[int]
    covered_event_ids: tuple
    dropped: tuple

    def disclosure(self) -> Dict[str, Any]:
        """`metadata.period_alignment` 之 service 端部分——🔴 丟掉的事件**必列 ID**（`COMPOSER-R1-P2-01`／`GROK-R1-P1-02`：只報數不等價）。"""
        dropped_ids = sorted(str(eid) for eid, _ in self.dropped)
        return {
            "feature_run": {"start_ms": self.run_start_ms, "end_ms": self.run_end_ms},
            "dropped_events": {
                "count": len(dropped_ids),
                "ids": sorted(dropped_ids),
                "reason": "outside_feature_run",
            },
            "covered_event_count": len(self.covered_event_ids),
        }


def check_feature_run_coverage(
    *,
    timeframe_seconds: Dict[str, int],
    feature_manifest_time_range: Optional[Dict[str, Optional[str]]],
    event_windows,
) -> FeatureRunCoverage:
    """Task 7.7 ③ → EVTALIGN Task 3.1：特徵 run 對事件期之涵蓋，**逐事件**判定。

    🔴 語意變更（2026-09-08，R2 `CODEX-R2-P1-06`＋使用者原話④「還要手動重新生成特徵…太蠢了，是缺陷吧」）：
    原本是**批次級** pass/fail——任一事件超出 run 區間就整批 raise，使用者得回頭重生特徵。
    現在：超出 run 區間的事件**逐一剔除並揭露 ID**（呼叫端以 `apply_event_coverage` 縮集合、
    `period_alignment.dropped_events` 進報告），只有**全部**事件都不在區間內才 fail-closed。
    legacy run（無 time_range）與未知 timeframe 仍 fail-closed（無區間可對證，不能靜默放行）。

    🔴 **唯一入口、keyword-only**：禁 `args[N]`、禁第二入口、禁掛在 pipeline 上當替身。
    🔴 `timeframe_seconds` 是**注入之 map**——SPEC 明禁在本函式內直讀
    `momentum/core/constants.py::TIMEFRAME_SECONDS`。呼叫端建構一次、以**同一物件**
    同時傳給 purge 與本 gate，驗收以 `is` 比對。

    containment（批內全部列皆須成立）：
    ```
    run_start_ms <= min_e decision_at_ms(e)   且   max_e label_end_ms(e) <= run_end_ms
    ```
    🔴 左界用 `decision_at_ms` **而非** `min(t0)`：IC 之特徵截止規則是
    `max_close_ms <= decision_at`，`decision_offset_bars = k > 0` 時 `decision_at < t0`
    ⇒ 用 `min(t0)` 會放行「run 根本沒涵蓋決策時點」的批次，那是個 fail-open 窗口。
    """
    windows = tuple(event_windows)
    if not windows:
        # 沒有窗就沒有東西要涵蓋。這不是錯誤——上游已對「全部對齊失敗」有自己的 loud 路徑。
        return FeatureRunCoverage(False, None, None, (), ())

    # ② 逐列用**該列自己的** timeframe；批內多 TF 允許，但任一列不在注入之鍵集 ⇒ 整批擋。
    for w in windows:
        if w.timeframe not in timeframe_seconds:
            raise FeatureRunCoverageError(
                "feature_coverage_unknown_timeframe",
                f"事件 {w.event_id} 之 timeframe {w.timeframe!r} 不在注入之 timeframe_seconds 鍵集"
                f"（{sorted(timeframe_seconds)}）",
            )

    # ⑤ legacy run：`{"start": None, "end": None}`。
    # 🔴 **缺鍵與 `None` 同等處置**（`D-005` 之偵察輪裁定 1）：實掃 14 份 manifest 有 2 份
    #    完全沒有 `time_range` 鍵，而 SPEC ⑤ 只裁定了 `{None, None}`。兩者資訊量相同
    #    （都拿不到區間），分成兩個 reason 只會讓前端多一種要處理的字面；
    #    且 §C0 只能更嚴，缺鍵放行才是弱化。
    if not isinstance(feature_manifest_time_range, dict):
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_legacy_run",
            "feature run manifest 無 time_range（缺鍵或非 dict）——無法對證涵蓋範圍",
        )
    start_raw = feature_manifest_time_range.get("start")
    end_raw = feature_manifest_time_range.get("end")
    if start_raw is None or end_raw is None:
        raise FeatureRunCoverageError(
            "feature_coverage_unknown_legacy_run",
            f"feature run 之 time_range 為 legacy 形（start={start_raw!r} end={end_raw!r}）"
            "——不得視為『涵蓋全部』而放行",
        )

    run_start_ms = _parse_time_range_endpoint(start_raw)
    run_end_ms = _parse_time_range_endpoint(end_raw)

    # 逐事件：左界比 decision_at、右界比含答案窗之 label_end（閉區間）
    covered: list = []
    dropped: list = []
    for w in windows:
        if run_start_ms <= int(w.decision_at_ms) and int(w.label_end_ms) <= run_end_ms:
            covered.append(str(w.event_id))
        else:
            dropped.append((str(w.event_id), "outside_feature_run"))
    if not covered:
        required_start = min(int(w.decision_at_ms) for w in windows)
        required_end = max(int(w.label_end_ms) for w in windows)
        raise FeatureRunCoverageError(
            "feature_coverage_insufficient",
            f"特徵 run 之區間 [{run_start_ms}, {run_end_ms}] 與事件期 "
            f"[{required_start}, {required_end}] 無交集——{len(windows)} 筆事件全部落在 run 之外"
            f"（左界比 decision_at、右界比含答案窗之 label_end；被丟 ID 前 5 筆：{[e for e, _ in dropped[:5]]}）",
        )
    return FeatureRunCoverage(True, run_start_ms, run_end_ms, tuple(covered), tuple(dropped))


__all__ = [
    "FEATURE_KLINE_CACHE_DIR",
    "REASON_DISABLED",
    "REASON_INSUFFICIENT_ROWS",
    "CanonicalHoldout",
    "CanonicalHoldoutError",
    "bars_timeframes_for",
    "load_post_trim_index",
    "resolve_canonical_holdout",
    "resolve_run_dir",
    "FeatureRunCoverage",
    "FeatureRunCoverageError",
    "check_feature_run_coverage",
]
