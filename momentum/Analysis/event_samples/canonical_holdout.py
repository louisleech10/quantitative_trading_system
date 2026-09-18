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
    if run_dir.parent.parent.name != str(symbol):
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
]
