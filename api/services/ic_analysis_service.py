"""IC analysis service for task management."""

from __future__ import annotations

import asyncio
import json
import math
import threading
import uuid
from io import BytesIO
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import h5py
import numpy as np
import pandas as pd

from api.core.config import settings
from api.core.logging import get_logger
from api.models.ic_models import (
    DeepAnalysisRequest,
    ICAnalyzeRequest,
    ICFullAnalysisRequest,
    ICResultV2Response,
)
from momentum.factories import (
    create_feature_library,
    create_feature_reader,
    create_ic_analyzer,
    create_ic_artifact_writer,
    create_ic_reporter,
    create_kline_storage_manager,
    resolve_run_feature_count,
    sanitize_factor_returns,
)
from momentum.core.contracts import ICResult


logger = get_logger("api.ic_analysis_service")

#: 合理性上界＝2100-01-01（epoch 秒）。超出即判 parse failure（SPEC Task 7.7 ④ 之字面）。
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


def check_feature_run_coverage(
    *,
    timeframe_seconds: Dict[str, int],
    feature_manifest_time_range: Optional[Dict[str, Optional[str]]],
    event_windows,
) -> None:
    """Task 7.7 ③：特徵 run 是否涵蓋事件期。不涵蓋即 **fail-closed**（非警告）。

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
        return

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

    required_start = min(int(w.decision_at_ms) for w in windows)
    required_end = max(int(w.label_end_ms) for w in windows)
    if run_start_ms > required_start or required_end > run_end_ms:
        raise FeatureRunCoverageError(
            "feature_coverage_insufficient",
            f"特徵 run 之區間 [{run_start_ms}, {run_end_ms}] 未涵蓋事件期 "
            f"[{required_start}, {required_end}]（左界比 decision_at、右界比含答案窗之 label_end）",
        )


def _feature_run_time_range(*candidates: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
    """由 feature run 之路徑找出 `feature_manifest.json` 並原樣取出 `time_range`。

    🔴 **為什麼在 service 自己讀，而不是由 route 傳進來**：Task 7.7 要對證的是
    「**這次分析實際會載入的那個 run**」是否涵蓋事件期。若由外層先猜一個 run 再傳進來，
    就得複製一份 service 的 run 選擇邏輯——那正是 B9 花了五輪才修完的病
    （閘門與 loader 各算各的，於是每一輪冒出一種新的不一致）。
    這裡直接吃 service 自己已經解析完的 `features_path`／`meta_path`，**沒有第二份選擇邏輯**。

    🔴 **原樣取出、不轉型別**（Task 7.7 ①）：manifest 實測為 epoch 秒之數字字串。
    找不到 manifest ⇒ 回 `None`，由 gate 判 `feature_coverage_unknown_legacy_run`（fail-closed）。
    """
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        for base in (path if path.is_dir() else path.parent, path.parent.parent):
            manifest = base / "feature_manifest.json"
            if not manifest.is_file():
                continue
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            raw = payload.get("time_range") if isinstance(payload, dict) else None
            if isinstance(raw, dict):
                return {"start": raw.get("start"), "end": raw.get("end")}
            return None
    return None


def _resolve_feature_count(request, *, entrypoint: str = "analyze") -> Optional[int]:
    """GAP-3 UX Task 6.3：取這個 run 的特徵數。

    🔴 `CODEX-R4-P2-01`：本函式原本只呼叫 `resolve_run_feature_count`（只認顯式 hash）
      ⇒ **隱式 latest 與所有 `/full-analysis`** 的任務一律回 `None`，
      Task 6.3 的欄位在最常見的兩種用法下都是空的。
      改為委派 `ICAnalysisService.resolve_planned_feature_count`——
      **與止血閘、與實際載入路徑同一支解析**。

    🔴 解析失敗仍回 `None`——**不填假值**。UAT 已證實填充值比沒有更誤導
    （`progress==0.12` 卡 15 分鐘，使用者以為還在動）。
    """
    return ic_analysis_service.resolve_planned_feature_count(request, entrypoint=entrypoint)

FEATURE_KLINE_CACHE_DIR = "data_cache/feature_klines"


class ICAnalysisService:
    """IC analysis service for async task execution."""

    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self._lock = threading.Lock()
        self._last_task_id: Optional[str] = None
        self._feature_library = create_feature_library()

    @staticmethod
    def _plan_cross_sectional_load(request):
        """橫截面模式下**實際會餵給 `load_multi` 的 `(symbols, config_hashes)`**。

        🔴 **本方法是止血閘與實際載入的唯一共用來源**。R5 兩家各自打出一條反例，
          證明「把選擇規則在兩處各推導一次」即使搬進同一個 class 也不夠：

          | ID | 方向 | 原因 |
          |---|---|---|
          | `COMPOSER-R5-P1-01` | 該擋沒擋 | 逐筆 `config_hash` 為**空字串**時，解析器 `get_entry(…, "")` 回 `None` 放行；而 `load_multi` 看到 falsy hash 會走 `find_latest` ⇒ 實際載入 161,031 |
          | `CODEX-R5-P1-01` | 不該擋卻擋 | 同一 symbol 出現兩次時，loader 以 **symbol 為 dict key**（後者覆蓋前者），而解析器對每一筆取 max ⇒ 誤擋 |

          兩者都是「重新推導」而非「共用」的必然結果。改成本方法之後，
          兩條規則（**dict 去重、後者勝** ／ **空 hash 視同未指定**）各只存在一份。
        """
        runs = list(getattr(request, "cross_sectional_runs", None) or [])
        if runs:
            # 🔴 逐字沿用 loader 原本的 dict comprehension 語意：同 symbol **後者覆蓋前者**
            config_hashes = {item.symbol: item.config_hash for item in runs}
            symbols_resolved = [item.symbol for item in runs]
            return symbols_resolved, config_hashes
        if getattr(request, "symbols", None):
            return list(request.symbols), None
        return None, None

    def resolve_planned_feature_count(self, request, *, entrypoint: str = "analyze") -> Optional[int]:
        """GAP-3 UX Task 6.1／6.3：**這次分析實際會載入的那些 run** 有幾個特徵。

        🔴 **本方法存在的理由＝B9 四輪 review 的共同根因**。
          止血閘原本在 `api/routes/ic_analysis.py` 裡**手抄了一份與本 service 平行的解析**：
          閘門把候選塞成一袋取 `max()`，而本 service 走的是**互斥分支**；
          閘門每次請求 `FeatureRegistry()` 重讀磁碟，而本 service 的 `_feature_library`
          在**行程啟動時**建好、registry 只讀一次。兩份邏輯、兩份快照，於是四輪抓到四種不同步：

          | 輪次 | 形態 | finding |
          |---|---|---|
          | R1 | 袋子少一味（`features_path`）⇒ **該擋沒擋** | `CODEX-R1-P1-01`／`GROK-R1-P1-01` |
          | R2 | 袋子少一味（`cross_sectional_runs`）⇒ 該擋沒擋 | `CODEX-R2-P1-01` |
          | R3 | 袋子少一味（隱式 latest ×2）⇒ 該擋沒擋 | 三家一致 |
          | R4 | 袋子**多**一味 ⇒ **不該擋卻擋**；且兩份 registry 不同步 | `CODEX-R4-P1-01`／`P1-03` |

          修法不是再補一味，是**刪掉那份手抄邏輯**：由「決定要載入什麼的人」回答「它有多大」。
          鏡像因此成為**結構性質**，不再需要人工維護。

        🔴 **分支必須與 `_run_analysis`／`_run_full_analysis` 逐條對齊**（見下方逐段註解）；
          改動其一未改另一，等於把本方法退化回手抄副本。
        🔴 解析不出來回 `None`——**呼叫端自己決定要擋還是要放**，本方法不替它決定。
        🔴 全程只讀 registry（記憶體）與 manifest（數 KB JSON），**不開 HDF5**
          （Task 6.4 之硬性要求：止血閘擋下時不得已載入大矩陣）。
        """
        from momentum.factories import (
            feature_count_from_features_file,
            feature_count_from_registry_entry,
        )

        timeframe = getattr(request, "timeframe", None)

        # ── `/full-analysis`：對齊 `_run_full_analysis` ──
        #    🔴 **它與 `/analyze` 走的不是同一條載入路徑**：`_run_full_analysis` 直接把
        #    `request.features_path` 餵給 `analyzer.analyze`，**從不碰 registry**
        #    （沒有 `get_entry`／`find_latest_materialized`／`load_multi`）。
        #    因此對它去查 latest 會擋掉一個根本不會載入任何 registry run 的請求——
        #    那正是 `CODEX-R4-P1-01` 那一族的誤擋，只是換我自己在結構修正時犯。
        #    **主委自攻抓到，未進 review**；記在這裡是因為它示範了本方法的維護風險：
        #    「鏡像 service」只有在**逐個入口**對齊時才成立，多一個入口就多一份對齊責任。
        if entrypoint == "full_analysis":
            return feature_count_from_features_file(
                getattr(request, "features_path", None),
                symbol=getattr(request, "symbol", None), timeframe=timeframe,
            )

        # ── 橫截面：對齊 `_run_analysis` 之 `mode == "cross_sectional"` 分支 ──
        #    該分支走 `load_multi`，**完全不看**頂層 `features_path`／`config_hash`
        #    ⇒ 閘門也不得把它們算進來（`CODEX-R4-P1-01` 之後半）。
        if getattr(request, "mode", "longitudinal") == "cross_sectional":
            if not timeframe:
                return None
            symbols_resolved, config_hashes = self._plan_cross_sectional_load(request)
            if symbols_resolved is None:
                return None
            # 🔴 **逐字鏡像 `load_multi` 的行為**（`CODEX-R5-P1-01`＋`COMPOSER-R5-P1-01`）：
            #    ① 以 symbol 去重（dict key 語意；同 symbol 只會被載入一次、且用最後那筆 hash）
            #    ② hash 為 falsy（含**空字串**）⇒ 該標的走 `find_latest_materialized`，
            #       與 `feature_library.load(config_hash=None)` 之 `if config_hash:` 一致
            entries = []
            for sym in dict.fromkeys(symbols_resolved):
                raw = (config_hashes or {}).get(sym)
                run_hash = raw.strip() if isinstance(raw, str) else ""
                entries.append(
                    self._feature_library.get_entry(sym, timeframe, run_hash)
                    if run_hash
                    else self._feature_library.find_latest_materialized(sym, timeframe)
                )
            counts = [c for c in (feature_count_from_registry_entry(e) for e in entries)
                      if isinstance(c, int)]
            # 任一標的超標即擋整組——橫截面本來就把它們一起載入，擋掉一筆不會降低峰值
            return max(counts) if counts else None

        # ── longitudinal：對齊 `_run_analysis` 之 else 分支 ──
        #    該分支的最終載入對象是 `features_path`；呼叫端**明確給了** `features_path` 時，
        #    entry 只用來補 meta、**不參與載入** ⇒ 閘門不得再把 latest 算進來
        #    （`CODEX-R4-P1-01`：小 `features_path` 被不相干的大 latest 誤擋）。
        features_path = getattr(request, "features_path", None)
        symbol = getattr(request, "symbol", None)
        if features_path:
            return feature_count_from_features_file(
                features_path, symbol=symbol, timeframe=timeframe,
            )
        if not (symbol and timeframe):
            return None
        config_hash = (getattr(request, "config_hash", None) or "").strip()
        entry = (
            self._feature_library.get_entry(symbol, timeframe, config_hash)
            if config_hash
            else self._feature_library.find_latest_materialized(symbol, timeframe)
        )
        return feature_count_from_registry_entry(entry)

    @staticmethod
    def _run_event_label_stages(
        request: ICAnalyzeRequest,
        event_batch: Dict[str, Any],
        *,
        features_path: Optional[str],
        meta_path: Optional[str],
    ) -> Dict[str, Any]:
        """GAP-3 UX Task 7.0b ④ ＋ 7.7 ③ 之**五階段編排**（§D-3′-a（iii）之落地點）。

        🔴 **本方法是事件分支的唯一入口**，只在 `request.event_import_id` 存在時被呼叫
        ⇒ cross-sectional 與純特徵 longitudinal **不會**經過這裡（over 向：不得誤擋）。

        🔴 **`timeframe_seconds` 在這裡建構一次**，並以**同一物件**傳給 purge 與 feature-run gate
        （驗收以 `is` 比對）。禁各自建構、禁 gate 內直讀 `momentum/core/constants.py`。

        階段（逐字對應 §D-3′-a（iii)）：
        2. `prepare_analysis_windows` — 唯一產生 receipt 與 hash 之處，**只呼叫一次**
        3a. `check_feature_run_coverage` — 批次級 pass/fail，**不產生 event-id 子集**
        3b. `apply_event_coverage` — 回**新**物件（`replace`），同 token 同 hash
        4. `project_purge` — tuple → read-only Mapping，用完即棄
        5. `resolve_label_value_at_analyze` — 吃階段 2 之**物件**，不重跑 `align_events`

        回純資料 dict：`event_timestamps`／`event_label_values`／`prepared`／`purge`／`reason`。
        """
        from momentum.factories import create_event_sample_pipeline

        pipeline = create_event_sample_pipeline()
        records = tuple(event_batch.get("records") or ())
        if not records:
            raise ValueError(
                f"event_import_id={request.event_import_id!r} 之批次沒有任何 records（fail-closed）"
            )
        spec = event_batch.get("event_label_spec")
        symbols = sorted({str(r["symbol"]) for r in records})
        timeframes = sorted({str(r["timeframe"]) for r in records})

        # 🔴 **建構一次**：下面兩個 consumer 拿到的是**同一個** dict 物件。
        timeframe_seconds = pipeline.timeframe_seconds_for(timeframes)
        bars_by_tf = pipeline.bars_from_kline_cache(symbols, timeframes)

        prepared0 = pipeline.prepare_analysis_windows(          # 階段 2（spy: call_count == 1）
            records, bars_by_tf,
            event_label_spec=spec,
            event_import_id=request.event_import_id,
            lookahead_bars_declared=event_batch.get("lookahead_bars_declared") or {},
            timeframe_seconds=timeframe_seconds,
        )
        check_feature_run_coverage(                              # 階段 3a（批次級 pass/fail）
            timeframe_seconds=timeframe_seconds,                 # 🔴 同一物件
            feature_manifest_time_range=_feature_run_time_range(features_path, meta_path),
            event_windows=prepared0.windows,
        )
        # 階段 3b：本批 3a 為批次級，不剔除任何列 ⇒ allowed 維持全集（`replace` 仍產生新身分）。
        prepared1 = pipeline.apply_event_coverage(prepared0, prepared0.allowed_event_ids)
        purge = pipeline.project_purge(prepared1.purge_lower_bound_ms_by_symbol)  # 階段 4
        result = pipeline.resolve_label_value_at_analyze(         # 階段 5
            prepared1, bars_by_tf, event_label_spec=spec,
        )
        if not result.supported:
            raise ValueError(
                f"事件分析不支援本批之報酬語意（reason={result.reason}）"
                "——F-1′ 支援矩陣為 (trigger_close, close_to_close, k=0)"
            )
        # 🔴 `label_value is None`（尾端不足）之 eid **不進 IC**，且**不填 0**。
        per_tf = {(p.event_id, p.timeframe): p.feature_cutoff_ms for p in prepared1.per_tf}
        ts_map: Dict[int, float] = {}
        for w in prepared1.windows:
            value = result.label_values.get(w.event_id)
            if value is None:
                continue
            cutoff = per_tf.get((w.event_id, w.timeframe))
            if cutoff is None:
                continue
            ts_map[int(cutoff)] = float(value)
        return {
            "event_timestamps": sorted(ts_map),
            "event_label_values": ts_map,
            "prepared": prepared1,
            "purge": purge,
            "analysis_alignment_receipt_hash": prepared1.analysis_alignment_receipt_hash,
            "prepared_token": prepared1.prepared_token,
        }

    async def start_analysis(
        self,
        request: ICAnalyzeRequest,
        *,
        event_batch: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """Start IC analysis task.

        🔴 `event_batch`（GAP-3 Task 7.0b）由 **route 層**以 `request.event_import_id` 查出
        並傳入——**不是** service 自己查。理由：Rule 4 禁 service 互相 import，
        而事件批住在 `api/services/case_import_service.py`。route 不在 R4 掃描範圍。
        形狀＝`{"records": [...], "lookahead_bars_declared": {...}, "event_label_spec": {...}}`。
        """
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
            # store source info for apply_transforms
            "req_features_path": request.features_path,
            "req_symbol": request.symbol,
            "req_timeframe": request.timeframe,
            "req_config_hash": (request.config_hash or "").strip() or None,
            # GAP-3 UX Task 6.3：這個 run 有幾個特徵（只讀 registry；解析不出來就是 None，不填假值）。
            "feature_count": _resolve_feature_count(request),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC analysis task started: %s", task_id)
        asyncio.create_task(
            self._run_analysis(task_id, analyzer, request, config_override, event_batch=event_batch)
        )

        return {"task_id": task_id, "status": "running"}

    async def _run_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICAnalyzeRequest,
        config_override: Optional[Dict[str, Any]],
        *,
        event_batch: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Run IC analysis in background."""

        loop = asyncio.get_running_loop()

        def progress_callback(payload: Dict[str, Any]) -> None:
            stage_name = payload.get("stage_name") or payload.get("stage")
            progress = float(payload.get("progress", 0.0))
            message = payload.get("message")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress
                task_info["status"] = "running"

            notify_payload = {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            }
            loop.call_soon_threadsafe(self._notify_callbacks, task_id, notify_payload)

        try:
            if request.mode == "cross_sectional":
                if not request.timeframe:
                    raise ValueError("timeframe is required for cross_sectional mode")

                symbols_resolved, config_hashes = self._plan_cross_sectional_load(request)
                if symbols_resolved is None:
                    raise ValueError("cross_sectional mode requires cross_sectional_runs or symbols")

                if len(symbols_resolved) < 2:
                    raise ValueError("cross_sectional mode requires at least 2 symbols")

                multi_features = self._feature_library.load_multi(
                    symbols_resolved,
                    request.timeframe,
                    config_hashes=config_hashes,
                )
                frames: List[pd.DataFrame] = []
                for symbol, frame in multi_features.items():
                    if frame is None or frame.empty:
                        raise ValueError(f"Feature data is empty for {symbol}/{request.timeframe}")
                    symbol_frame = frame.copy()
                    symbol_frame["_symbol"] = symbol
                    frames.append(symbol_frame)

                cross_df = pd.concat(frames, axis=0)
                cross_df = cross_df.set_index("_symbol", append=True)

                labels_path = request.labels_path
                if not labels_path:
                    cross_df = self._append_cross_sectional_labels(
                        cross_df,
                        symbols_resolved,
                        request.timeframe,
                    )

                report = await asyncio.to_thread(
                    analyzer.analyze_cross_sectional,
                    features=cross_df,
                    labels_path=labels_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                    timeframe=request.timeframe,
                )
            else:
                symbol = request.symbol
                timeframe = request.timeframe
                config_hash = (request.config_hash or "").strip() or None
                features_path = request.features_path
                meta_path = request.meta_path
                resolved_config_hash: Optional[str] = config_hash

                if symbol and timeframe:
                    if config_hash:
                        entry = self._feature_library.get_entry(symbol, timeframe, config_hash)
                        # fail-closed 僅在需要由 registry 解析/物化資料時才強制——這才是 run-selector
                        # 消歧保證的作用點(features_path 缺席→避免靜默挑到別的 run)。呼叫端已明確
                        # 提供 features_path(如 golden replay/artifact 重放)時,不因該 run 未註冊而擋。
                        # 注意:此時 entry 不餵給 analyzer(分析改用 features_path),僅在 meta_path
                        # 亦缺席時用於補寫 meta(見下方 materialize/meta 分支);故 replay 呼叫端應一併
                        # 提供 meta_path 或 labels_path,否則未註冊 run 會缺 meta(下游 label 生成需之)。
                        if entry is None and not features_path:
                            raise ValueError(f"run not found: {symbol}/{timeframe}/{config_hash}")
                    else:
                        entry = self._feature_library.find_latest_materialized(
                            symbol,
                            timeframe,
                        )
                        if entry is None:
                            entry = None
                        else:
                            logger.warning(
                                "未指定 config_hash，回退最新 run %s/%s",
                                symbol,
                                timeframe,
                            )
                            resolved_config_hash = str(entry.get("config_hash") or "")

                    if entry and not features_path:
                        features_path, meta_path = self._materialize_features_for_ic(
                            symbol,
                            timeframe,
                            resolved_config_hash,
                        )
                    elif entry and not meta_path:
                        meta_path = self._write_ic_meta_json(
                            symbol,
                            timeframe,
                            resolved_config_hash,
                        )

                if not features_path:
                    raise ValueError("features_path is required when FeatureLibrary symbol/timeframe is unavailable")

                labels_path = request.labels_path
                kline_reader = None
                if not labels_path:
                    kline_reader = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)

                # ── GAP-3 UX Task 7.0b ④：事件分支之五階段編排（唯一取得點） ──────
                # 🔴 **只在 `event_import_id` 存在時進入**——這個 guard 就是 over 向的保護：
                #    cross-sectional（上方分支）與純特徵 longitudinal 都不會走到這裡。
                event_label_values = None
                event_timestamps = request.event_timestamps or None
                if request.event_import_id:
                    if event_batch is None:
                        raise ValueError(
                            f"event_import_id={request.event_import_id!r} 但未取得該批 records"
                            "——route 層須先查出並傳入（Rule 4 禁 service 互相 import）"
                        )
                    staged = self._run_event_label_stages(
                        request, event_batch,
                        features_path=features_path, meta_path=meta_path,
                    )
                    event_timestamps = staged["event_timestamps"]
                    event_label_values = staged["event_label_values"]
                    with self._lock:
                        info = self._tasks.get(task_id)
                        if info:
                            # 揭露本次分析用的 receipt 身分（Task 7.0b ⑩ 之可追溯性）
                            info["analysis_alignment_receipt_hash"] = staged[
                                "analysis_alignment_receipt_hash"
                            ]
                            info["prepared_token"] = staged["prepared_token"]

                report = await asyncio.to_thread(
                    analyzer.analyze,
                    features_path=features_path,
                    labels_path=labels_path or "",
                    meta_path=meta_path,
                    config_override=config_override,
                    progress_callback=progress_callback,
                    kline_reader=kline_reader,
                    event_timestamps=event_timestamps,
                    event_label_values=event_label_values,
                )

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = report

            # LA-1 B3-TASK-01：completion callback 必含 root 紅標
            completed_payload: Dict[str, Any] = {
                "task_id": task_id,
                "stage": "completed",
                "progress": 1.0,
                "message": "completed",
                "status": "completed",
            }
            if isinstance(report, dict):
                from momentum.Analysis.ic_reporter import normalize_analysis_status
                from momentum.core.contracts import deny_factor_in_ok_oos

                completed_payload["analysis_status"] = normalize_analysis_status(
                    report.get("analysis_status")
                )
                if "oos_guarantees" in report:
                    completed_payload["oos_guarantees"] = bool(report.get("oos_guarantees"))
                else:
                    completed_payload["oos_guarantees"] = (
                        completed_payload["analysis_status"] == "ok_oos"
                    )
                # LA-2 B3：root ok_oos + nested factor loud → deny
                try:
                    deny_factor_in_ok_oos(report)
                    deny_factor_in_ok_oos(completed_payload)
                except ValueError as deny_exc:
                    logger.error("deny_factor_in_ok_oos: %s", deny_exc)
                    completed_payload["analysis_status"] = "degraded_full_sample"
                    completed_payload["oos_guarantees"] = False
                    completed_payload["factor_deny_reason"] = str(deny_exc)
            else:
                completed_payload["analysis_status"] = "degraded_full_sample"
                completed_payload["oos_guarantees"] = False
            self._notify_callbacks(task_id, completed_payload)

            logger.info("IC analysis task completed: %s", task_id)

        except Exception as exc:
            logger.error("IC analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["current_stage"] = "failed"
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            payload = {
                "task_id": task_info["task_id"],
                "status": task_info["status"],
                "progress": task_info.get("progress", 0.0),
                "current_stage": task_info.get("current_stage"),
                "current_step": task_info.get("current_step"),
                "applied_tier": task_info.get("applied_tier", "intermediate"),
                "error": task_info.get("error"),
                # GAP-3 UX Task 6.3：這個 run 的特徵數。
                # 🔴 沒有就給 None，**不填假值**——UAT 已證實「progress==0.12 卡 15 分鐘」
                #    這種填充值比沒有更誤導（使用者以為在動）。
                "feature_count": task_info.get("feature_count"),
            }
            # LA-1 B3-ENUM-01：completed 時鏡像 root 紅標（fail-closed normalize）
            result = task_info.get("result")
            if isinstance(result, dict) and task_info.get("status") == "completed":
                from momentum.Analysis.ic_reporter import normalize_analysis_status

                payload["analysis_status"] = normalize_analysis_status(
                    result.get("analysis_status")
                )
                if "oos_guarantees" in result:
                    payload["oos_guarantees"] = bool(result.get("oos_guarantees"))
                else:
                    payload["oos_guarantees"] = (
                        payload["analysis_status"] == "ok_oos"
                    )
            return payload

    def get_result(self, task_id: str, schema_version: Optional[int] = None) -> Optional[Any]:
        """Get task result."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            result = task_info.get("result")

        if result is None:
            return None

        normalized = self._to_json_compatible(result)
        if isinstance(normalized, dict):
            # LA-2 B3-F2：回傳出口 deny root ok_oos + factor/diagnostic loud
            from momentum.core.contracts import deny_factor_in_ok_oos

            deny_factor_in_ok_oos(normalized)
            if not settings.ic_response_v2 or schema_version != 2:
                return normalized
            return self._build_v2_result(task_id, task_info, normalized)
        if not settings.ic_response_v2 or schema_version != 2:
            return {"raw": normalized}
        return self._build_v2_result(task_id, task_info, {})

    def _build_v2_result(
        self,
        task_id: str,
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build schema_version=2 response from the artifact as the single source of truth."""
        artifact_path = self._resolve_ic_v2_artifact_path(task_id, task_info, normalized_result)
        if artifact_path is None or not artifact_path.exists():
            response = ICResultV2Response(schema_version=2, artifact_uri=None, total_features=0)
            return response.model_dump()

        rows = create_ic_artifact_writer().read(artifact_path)
        sorted_rows = self._sort_artifact_rows(rows, "icir")
        top_n = self._resolve_v2_top_n(task_info)
        response = ICResultV2Response(
            schema_version=2,
            top_n_summary=sorted_rows[:top_n],
            artifact_uri=str(artifact_path),
            total_features=len(rows),
        )
        return response.model_dump()

    def _resolve_ic_v2_artifact_path(
        self,
        task_id: str,
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Optional[Path]:
        """Resolve the idempotent v2 artifact path for a task."""
        explicit = task_info.get("ic_response_v2_artifact_path")
        if explicit:
            return Path(str(explicit))

        config_hash = self._resolve_result_config_hash(task_info, normalized_result)
        if not config_hash:
            return None

        artifact_dir = Path(
            str(task_info.get("ic_artifact_dir") or settings.results_output_path / "ic_artifacts")
        )
        return artifact_dir / f"{task_id}_{config_hash}_v2.parquet"

    @staticmethod
    def _resolve_result_config_hash(
        task_info: Dict[str, Any],
        normalized_result: Dict[str, Any],
    ) -> Optional[str]:
        """Read config_hash from task metadata without guessing a replacement."""
        direct = task_info.get("req_config_hash")
        if direct:
            return str(direct)

        metadata = normalized_result.get("metadata")
        if isinstance(metadata, dict):
            config_hash = metadata.get("config_hash")
            if config_hash:
                return str(config_hash)
        return None

    @staticmethod
    def _sort_artifact_rows(rows: List[Dict[str, Any]], sort_by: str) -> List[Dict[str, Any]]:
        """Sort artifact rows for top-N derivation using artifact values only."""
        descending = sort_by != "p_value"

        def key(row: Dict[str, Any]) -> tuple[int, float]:
            value = row.get(sort_by)
            if value is None:
                return (1, 0.0)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return (1, 0.0)
            if math.isnan(numeric):
                return (1, 0.0)
            return (0, -numeric if descending else numeric)

        return sorted(rows, key=key)

    @staticmethod
    def _resolve_v2_top_n(task_info: Dict[str, Any]) -> int:
        """Resolve top-N from stored deep-analysis request metadata, defaulting to API contract."""
        raw_top_n = task_info.get("deep_analysis_top_n")
        if raw_top_n is None:
            request = task_info.get("deep_analysis_request")
            if isinstance(request, DeepAnalysisRequest):
                raw_top_n = request.top_n
            elif isinstance(request, dict):
                raw_top_n = request.get("top_n")
        if raw_top_n is None:
            return DeepAnalysisRequest().top_n
        return int(raw_top_n)

    def export_analysis(self, task_id: str, format_type: str, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Export IC analysis result into requested format."""

        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                raise ValueError(f"Task not found: {task_id}")
            report = task_info.get("result")
            deep_report = task_info.get("deep_analysis_result")

        if not isinstance(report, dict):
            raise ValueError(f"Result not found: {task_id}")

        # LA-2 B3-F2：匯出出口一律 deny ok_oos + factor/diagnostic loud
        from momentum.core.contracts import deny_factor_in_ok_oos

        deny_factor_in_ok_oos(report)
        if isinstance(deep_report, dict):
            # deep nested under root-like envelope for walk
            deny_factor_in_ok_oos(
                {
                    "analysis_status": report.get("analysis_status"),
                    "deep_analysis_report": deep_report,
                }
            )

        normalized_format = (format_type or "").strip().lower()
        if normalized_format not in {"json", "ai_json", "csv_summary", "csv_detailed", "markdown", "hdf5"}:
            raise TypeError(f"Unsupported format: {format_type}")

        if normalized_format == "hdf5":
            metadata = report.get("metadata", {}) if isinstance(report, dict) else {}
            export_path = self._resolve_filtered_path(metadata)
            # LA-1 B3-H5-01：拒 stale stable-path
            from momentum.Analysis.ic_reporter import assert_filtered_export_fresh

            fresh_path = assert_filtered_export_fresh(report, export_path)
            return {
                "type": "file",
                "path": fresh_path,
                "filename": fresh_path.name,
                "media_type": "application/x-hdf5",
            }

        reporter = create_ic_reporter(config={})
        payload_for_export = dict(report)
        if isinstance(deep_report, dict):
            payload_for_export.setdefault("deep_analysis_report", deep_report)

        if normalized_format == "json":
            # F2: raw JSON 出口 sanitizer(ok §U 放行 / legacy 裸 map 擋)
            safe_report = (
                sanitize_factor_returns(report) if isinstance(report, dict) else report
            )
            content = json.dumps(safe_report, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_report_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "ai_json":
            payload = reporter.generate_ai_json(payload_for_export, deep_report=deep_report)
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            return {
                "type": "bytes",
                "content": BytesIO(content),
                "filename": f"ic_ai_{task_id}.json",
                "media_type": "application/json; charset=utf-8",
            }

        if normalized_format == "csv_summary":
            csv_text = reporter.generate_summary_csv(payload_for_export, deep_report=deep_report)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_summary_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        if normalized_format == "csv_detailed":
            if not module_name:
                raise ValueError("module query parameter is required for csv_detailed")
            csv_text = reporter.generate_detailed_csv(payload_for_export, module_name)
            return {
                "type": "bytes",
                "content": BytesIO(csv_text.encode("utf-8")),
                "filename": f"ic_{module_name}_{task_id}.csv",
                "media_type": "text/csv; charset=utf-8",
            }

        markdown = reporter.generate_enhanced_markdown(payload_for_export, deep_report=deep_report)
        return {
            "type": "bytes",
            "content": BytesIO(markdown.encode("utf-8")),
            "filename": f"ic_report_{task_id}.md",
            "media_type": "text/markdown; charset=utf-8",
        }

    def list_features(
        self,
        features_path: Optional[str] = None,
        meta_path: Optional[str] = None,
        *,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        config_hash: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Read available feature list from V7 Parquet or legacy HDF5.

        V2 query: (symbol, timeframe, config_hash) → FeatureReader.list_features_v2.
        V7 path: features_path = 'parquet:{symbol}:{config_hash}' → FeatureReader.
        Legacy: features_path = '/path/to/file.h5' → h5py.
        """
        metadata = self._load_meta(meta_path)

        if symbol and timeframe and config_hash:
            reader = create_feature_reader()
            names = reader.list_features_v2(symbol, timeframe, config_hash)
            return self._build_feature_items(names, metadata)

        if not features_path:
            raise ValueError("features_path or (symbol, timeframe, config_hash) is required")

        # V7 Parquet path via FeatureReader
        if features_path.startswith("parquet:"):
            parts = features_path.split(":")
            if len(parts) != 3:
                raise ValueError("Invalid Parquet source format, expected parquet:{symbol}:{config_hash}")
            _, symbol, config_hash = parts
            reader = create_feature_reader()
            names = reader.list_features(symbol, config_hash)
            return self._build_feature_items(names, metadata)

        # Legacy HDF5 path
        path = Path(features_path)
        if not path.exists():
            raise FileNotFoundError(f"features_path not found: {features_path}")

        with h5py.File(path, "r") as h5_file:
            if "data" not in h5_file:
                raise ValueError("Invalid features HDF5: missing 'data' group")
            group = h5_file["data"]

            if "feature_names" in group:
                raw_names = group["feature_names"][:]
                names = [
                    item.decode("utf-8") if isinstance(item, bytes) else str(item)
                    for item in raw_names
                ]
            elif "features" in group and len(group["features"].shape) == 2:
                names = [f"feature_{i}" for i in range(group["features"].shape[1])]
            else:
                raise ValueError("Invalid features HDF5: missing feature_names/features")

        return self._build_feature_items(names, metadata)

    def compute_ic_from_l7_raw(
        self,
        symbol: str,
        timeframe: str,
        config_hash: str,
        label: pd.Series,
        *,
        feature_base_path: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        ic_threshold: Optional[float] = None,
        allow_partial_ic: bool = False,
        method: Optional[str] = None,
        label_horizon: Optional[str] = None,
        selection_window: Optional[Dict[str, Any]] = None,
        split_id: Optional[str] = None,
        ic_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run IC-First raw streaming selection through momentum factories."""

        analyzer = create_ic_analyzer(config_override)
        ic_engine = getattr(analyzer, "_ic_engine", None)
        if ic_engine is None:
            raise RuntimeError("IC analyzer does not expose an IC engine")

        reader = create_feature_reader(feature_base_path)
        result = ic_engine.compute_ic_from_l7_raw(
            symbol=symbol,
            tf=timeframe,
            config_hash=config_hash,
            label=label,
            feature_reader=reader,
            ic_threshold=ic_threshold,
            allow_partial_ic=allow_partial_ic,
            method=method,
            label_horizon=label_horizon,
            selection_window=selection_window,
            split_id=split_id,
            ic_params=ic_params,
        )
        return self._to_json_compatible(result.to_dict())

    @staticmethod
    def _build_feature_items(
        names: List[str],
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Build feature item list from names + optional metadata."""
        feature_items: List[Dict[str, Any]] = []
        for name in names:
            meta_item = metadata.get(name, {}) if isinstance(metadata.get(name, {}), dict) else {}
            feature_items.append({
                "feature_name": name,
                "category": meta_item.get("category"),
                "data_source": meta_item.get("data_source") or meta_item.get("source"),
                "family": meta_item.get("family"),
                "layer": meta_item.get("layer"),
            })
        return feature_items

    async def start_deep_analysis(self, task_id: str, request: DeepAnalysisRequest) -> Dict[str, str]:
        """Start deep analysis as a background task for an existing IC task."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"Task not found: {task_id}")

        status = self.get_task_status(task_id)
        if not status:
            raise ValueError(f"Task not found: {task_id}")
        if status.get("status") != "completed":
            raise ValueError(f"Task {task_id} is not ready for deep analysis")

        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info:
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = None
                task_info["progress"] = 0.0
                task_info["error"] = None

        logger.info("Deep analysis started for task: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_deep_analysis(task_id, analyzer, request)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_deep_analysis(self, task_id: str, analyzer: Any, request: DeepAnalysisRequest) -> None:
        override = self._build_deep_module_override(request)

        def progress_callback(payload: Dict[str, Any]) -> None:
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            current_step = payload.get("module_name") or payload.get("current_step")
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = "deep_analysis"
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            selected_features = self._resolve_selected_features(
                analyzer=analyzer,
                selected_features=request.selected_features,
                top_n=request.top_n,
            )

            deep_report = await asyncio.to_thread(
                analyzer.run_deep_analysis,
                selected_features,
                override,
                progress_callback,
                None,
            )
            serialized = self._serialize_deep_report(deep_report)
            serialized = self._attach_cross_symbol_context(serialized, analyzer)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["deep_analysis_result"] = serialized

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "completed",
                "progress": 1.0,
                "message": "deep analysis completed",
                "status": "completed",
            })
        except Exception as exc:
            logger.error("Deep analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["current_stage"] = "deep_analysis"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "deep_analysis",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_deep_analysis_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get deep analysis result."""
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            deep_result = task_info.get("deep_analysis_result")

        if deep_result is None:
            return None

        normalized = self._to_json_compatible(deep_result)
        if isinstance(normalized, dict):
            # F2: 讀出端 sanitize(ok 放行 / legacy 擋)
            return sanitize_factor_returns(normalized)
        return {"raw": normalized}

    async def start_full_analysis(self, request: ICFullAnalysisRequest) -> Dict[str, str]:
        """Start full analysis task (main + optional deep analysis)."""
        task_id = str(uuid.uuid4())
        config_override = self._build_config_override(request)
        analyzer = create_ic_analyzer(config_override)

        task_info = {
            "task_id": task_id,
            "status": "running",
            "progress": 0.0,
            "current_stage": None,
            "current_step": None,
            "error": None,
            "result": None,
            "deep_analysis_result": None,
            "analyzer": analyzer,
            "applied_tier": (request.feature_tiers.active_preset if request.feature_tiers else "intermediate"),
            "created_at": datetime.now().isoformat(),
            # 🔴 `CODEX-R4-P2-01`：`/full-analysis` 的 task_info 原本**沒有這個欄位**
            #    ⇒ Task 6.3 的特徵數在整個 full-analysis 路徑上一律回 None。
            "feature_count": _resolve_feature_count(request, entrypoint="full_analysis"),
        }

        with self._lock:
            self._tasks[task_id] = task_info
            self._last_task_id = task_id

        logger.info("IC full analysis task started: %s", task_id)
        self._start_background_coroutine(
            lambda: self._run_full_analysis(task_id, analyzer, request, config_override)
        )
        return {"task_id": task_id, "status": "running"}

    async def _run_full_analysis(
        self,
        task_id: str,
        analyzer: Any,
        request: ICFullAnalysisRequest,
        config_override: Optional[Dict[str, Any]],
    ) -> None:
        def progress_callback(payload: Dict[str, Any]) -> None:
            stage_name = payload.get("stage_name") or payload.get("stage")
            current_step = payload.get("module_name") or payload.get("current_step") or stage_name
            progress = max(0.0, min(1.0, float(payload.get("progress", 0.0))))
            message = payload.get("message")

            with self._lock:
                task_info = self._tasks.get(task_id)
                if not task_info:
                    return
                task_info["status"] = "running"
                task_info["current_stage"] = stage_name
                task_info["current_step"] = current_step
                task_info["progress"] = progress

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": stage_name,
                "current_step": current_step,
                "progress": progress,
                "message": message,
                "status": "running",
            })

        try:
            report = await asyncio.to_thread(
                analyzer.analyze,
                request.features_path,
                request.labels_path,
                request.meta_path,
                config_override,
                progress_callback,
                None,
                event_timestamps=getattr(request, "event_timestamps", None) or None,
            )

            deep_result: Optional[Dict[str, Any]] = None
            if request.deep_analysis:
                deep_request = request.deep_analysis_config or DeepAnalysisRequest()
                selected_features = self._resolve_selected_features(
                    analyzer=analyzer,
                    selected_features=deep_request.selected_features,
                    top_n=deep_request.top_n,
                )
                deep_override = self._build_deep_module_override(deep_request)
                deep_report = await asyncio.to_thread(
                    analyzer.run_deep_analysis,
                    selected_features,
                    deep_override,
                    progress_callback,
                    None,
                )
                deep_result = self._serialize_deep_report(deep_report)
                deep_result = self._attach_cross_symbol_context(deep_result, analyzer)
                if isinstance(report, dict):
                    report["deep_analysis_enabled"] = True
                    report["deep_analysis_report"] = deep_result

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "completed"
                    task_info["current_stage"] = "completed"
                    task_info["current_step"] = "completed"
                    task_info["progress"] = 1.0
                    task_info["result"] = report
                    task_info["deep_analysis_result"] = deep_result

            # LA-1 B3-TASK-01：full-analysis completion callback 必含 root 紅標
            full_completed_payload: Dict[str, Any] = {
                "task_id": task_id,
                "stage": "completed",
                "current_step": "completed",
                "progress": 1.0,
                "message": "full analysis completed",
                "status": "completed",
            }
            if isinstance(report, dict):
                from momentum.Analysis.ic_reporter import normalize_analysis_status
                from momentum.core.contracts import deny_factor_in_ok_oos

                full_completed_payload["analysis_status"] = normalize_analysis_status(
                    report.get("analysis_status")
                )
                if "oos_guarantees" in report:
                    full_completed_payload["oos_guarantees"] = bool(
                        report.get("oos_guarantees")
                    )
                else:
                    full_completed_payload["oos_guarantees"] = (
                        full_completed_payload["analysis_status"] == "ok_oos"
                    )
                # LA-2 B3-F2：full-analysis completion 亦 deny factor/diagnostic loud
                try:
                    deny_factor_in_ok_oos(report)
                    deny_factor_in_ok_oos(full_completed_payload)
                    if isinstance(deep_result, dict):
                        deny_factor_in_ok_oos(
                            {
                                "analysis_status": report.get("analysis_status"),
                                "deep_analysis_report": deep_result,
                            }
                        )
                except ValueError as deny_exc:
                    logger.error("deny_factor_in_ok_oos (full): %s", deny_exc)
                    full_completed_payload["analysis_status"] = "degraded_full_sample"
                    full_completed_payload["oos_guarantees"] = False
                    full_completed_payload["factor_deny_reason"] = str(deny_exc)
            else:
                full_completed_payload["analysis_status"] = "degraded_full_sample"
                full_completed_payload["oos_guarantees"] = False
            self._notify_callbacks(task_id, full_completed_payload)
        except Exception as exc:
            logger.error("IC full analysis task failed: %s", exc, exc_info=True)

            with self._lock:
                task_info = self._tasks.get(task_id)
                if task_info:
                    task_info["status"] = "failed"
                    task_info["current_stage"] = "failed"
                    task_info["current_step"] = "failed"
                    task_info["progress"] = 1.0
                    task_info["error"] = str(exc)

            self._notify_callbacks(task_id, {
                "task_id": task_id,
                "stage": "failed",
                "current_step": "failed",
                "progress": 1.0,
                "message": str(exc),
                "status": "failed",
            })

    def get_analyzer(self, task_id: Optional[str]) -> Optional[Any]:
        """Get analyzer for task."""
        if not task_id:
            return None
        with self._lock:
            task_info = self._tasks.get(task_id)
            if not task_info:
                return None
            return task_info.get("analyzer")

    def get_last_task_id(self) -> Optional[str]:
        """Get last task id."""
        with self._lock:
            return self._last_task_id

    async def apply_transforms(
        self,
        task_id: str,
        selected_features: List[str],
        rank: bool,
        zscore: bool,
        gaussian: bool,
        rank_window: int = 252,
        zscore_windows: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """Apply rank/zscore/gaussian to IC-selected features and persist the result.

        Intended for the IC-First workflow:
          Feature Factory (IC-First mode) → IC Gatekeeper → *here* → downstream ML

        Transform order: rank → zscore → gaussian (Gaussian always last).
        """
        return await asyncio.to_thread(
            self._apply_transforms_sync,
            task_id,
            selected_features,
            rank,
            zscore,
            gaussian,
            rank_window,
            zscore_windows or [100, 252],
        )

    def _apply_transforms_sync(
        self,
        task_id: str,
        selected_features: List[str],
        rank: bool,
        zscore: bool,
        gaussian: bool,
        rank_window: int,
        zscore_windows: List[int],
    ) -> Dict[str, Any]:
        import numpy as np
        import pandas as pd

        if not selected_features:
            raise ValueError("selected_features must not be empty")
        if not (rank or zscore or gaussian):
            raise ValueError("At least one transform (rank / zscore / gaussian) must be enabled")

        # --- 1. Get task info ---
        with self._lock:
            task_info = self._tasks.get(task_id)
        if task_info is None:
            raise ValueError(f"IC analysis task not found: {task_id}")

        symbol: Optional[str] = task_info.get("req_symbol")
        timeframe: Optional[str] = task_info.get("req_timeframe")
        features_path: Optional[str] = task_info.get("req_features_path")
        config_hash: Optional[str] = task_info.get("req_config_hash")

        # --- 2. Load feature DataFrame ---
        df = self._load_features_for_transforms(
            symbol,
            timeframe,
            features_path,
            config_hash=config_hash,
        )
        logger.info("[apply_transforms] Loaded features: %d rows x %d cols", len(df), len(df.columns))

        # --- 3. Filter to selected_features (only those actually present) ---
        valid_cols = [c for c in selected_features if c in df.columns]
        missing = set(selected_features) - set(valid_cols)
        if missing:
            logger.warning("[apply_transforms] %d requested features not found: %s…", len(missing), list(missing)[:5])
        if not valid_cols:
            raise ValueError("None of the selected_features exist in the loaded feature data")
        df = df[valid_cols].copy()

        transforms_applied: List[str] = []

        # --- 4a. Rank Transform ---
        if rank:
            df = df.rolling(rank_window, min_periods=max(rank_window // 2, 1)).rank(pct=True)
            transforms_applied.append("rank")
            logger.info("[apply_transforms] Applied rank transform (window=%d)", rank_window)

        # --- 4b. Adaptive Z-Score ---
        if zscore:
            primary_window = min(zscore_windows)
            rolling = df.rolling(primary_window, min_periods=max(primary_window // 2, 1))
            mu = rolling.mean()
            sigma = rolling.std().fillna(0.0).clip(lower=1e-8)
            df = (df - mu) / sigma
            transforms_applied.append("zscore")
            logger.info("[apply_transforms] Applied adaptive zscore (window=%d)", primary_window)

        # --- 4c. Gaussian Normalize (always last) ---
        if gaussian:
            try:
                from scipy.stats import norm as _norm
                clip_lo, clip_hi = 0.001, 0.999
                # Gaussian is meaningful only if input is already rank-like (0-1).
                # If rank was not applied, coerce to empirical CDF first.
                if not rank:
                    df = df.rank(pct=True, axis=0)
                df = df.clip(lower=clip_lo, upper=clip_hi).apply(lambda col: _norm.ppf(col))
                transforms_applied.append("gaussian")
                logger.info("[apply_transforms] Applied gaussian normalize")
            except ImportError:
                logger.error("[apply_transforms] scipy not available, skipping gaussian")

        # --- 5. Persist result（含 LA-1 B3 analysis_status attr）---
        result_report = task_info.get("result") if isinstance(task_info, dict) else None
        from momentum.Analysis.ic_reporter import normalize_analysis_status

        # B3-ENUM-01：非字面 ok_oos 一律 degraded（禁 default ok_oos）
        raw_status = None
        oos_guarantees: Optional[bool] = None
        if isinstance(result_report, dict):
            raw_status = result_report.get("analysis_status")
            if "oos_guarantees" in result_report:
                oos_guarantees = bool(result_report.get("oos_guarantees"))
        analysis_status = normalize_analysis_status(raw_status)
        if oos_guarantees is None:
            oos_guarantees = analysis_status == "ok_oos"

        output_dir = Path("data_cache/reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"post_ic_transforms_{task_id}.h5"
        df.to_hdf(str(output_path), key="features", mode="w", complevel=5)
        # oracle ⑤ / B3-XFORM-01：analysis_status attr 必寫；失敗 raise（禁吞回 success）
        from momentum.Analysis.ic_reporter import DegradedOOSViolation

        try:
            import h5py

            with h5py.File(str(output_path), "a") as handle:
                status_s = str(analysis_status)
                handle.attrs["analysis_status"] = status_s
                handle.attrs["oos_guarantees"] = bool(oos_guarantees)
                if "features" in handle:
                    handle["features"].attrs["analysis_status"] = status_s
        except DegradedOOSViolation:
            raise
        except Exception as exc:  # noqa: BLE001 — 轉唯一 gate exception
            logger.error(
                "[apply_transforms] failed to write analysis_status attr: %s",
                exc,
                exc_info=True,
            )
            raise DegradedOOSViolation(
                f"transforms HDF5 analysis_status attr write failed: {exc}"
            ) from exc
        logger.info("[apply_transforms] Saved %d x %d to %s", len(df), len(df.columns), output_path)

        return {
            "task_id": task_id,
            "selected_feature_count": len(valid_cols),
            "transforms_applied": transforms_applied,
            "output_path": str(output_path),
            "output_rows": len(df),
            "output_cols": len(df.columns),
            "analysis_status": analysis_status,
            "oos_guarantees": oos_guarantees,
        }

    def _load_features_for_transforms(
        self,
        symbol: Optional[str],
        timeframe: Optional[str],
        features_path: Optional[str],
        config_hash: Optional[str] = None,
    ):
        """Load feature DataFrame from FeatureLibrary (symbol/timeframe) or HDF5 path."""
        import pandas as pd

        if features_path:
            p = Path(features_path)
            if not p.exists():
                raise FileNotFoundError(f"Features path not found: {features_path}")
            if features_path.endswith(".h5") or features_path.endswith(".hdf5"):
                return pd.read_hdf(features_path)
            if features_path.endswith(".parquet"):
                return pd.read_parquet(features_path)
            raise ValueError(f"Unsupported features file format: {features_path}")

        if symbol and timeframe:
            try:
                return self._feature_library.load(
                    symbol,
                    timeframe,
                    config_hash=config_hash,
                )
            except Exception as exc:
                logger.warning("[apply_transforms] FeatureLibrary.load failed: %s; trying path fallback", exc)

        raise ValueError(
            "Cannot load features: no symbol/timeframe or features_path stored in task. "
            "Re-run IC analysis with a valid symbol+timeframe or features_path."
        )

    async def refilter(self, task_id: str, thresholds: Dict[str, Any]) -> Dict[str, Any]:
        """Refilter using cached IC results."""
        analyzer = self.get_analyzer(task_id)
        if analyzer is None:
            raise ValueError(f"task not found: {task_id}")

        report = analyzer.refilter(thresholds)
        with self._lock:
            task_info = self._tasks.get(task_id)
            if task_info:
                task_info["result"] = report

        return report

    def register_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Register notification callback."""
        with self._lock:
            self._callbacks.setdefault(task_id, []).append(callback)

    def unregister_notification_callback(
        self,
        task_id: str,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        """Unregister notification callback."""
        with self._lock:
            callbacks = self._callbacks.get(task_id, [])
            if callback in callbacks:
                callbacks.remove(callback)
            if not callbacks and task_id in self._callbacks:
                del self._callbacks[task_id]

    def _notify_callbacks(self, task_id: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            callbacks = list(self._callbacks.get(task_id, []))
        for callback in callbacks:
            try:
                callback(payload)
            except Exception as exc:
                logger.error("IC notification callback failed: %s", exc, exc_info=True)

    def _build_config_override(self, request: ICAnalyzeRequest) -> Optional[Dict[str, Any]]:
        override = request.config_override or {}
        if not isinstance(override, dict):
            raise ValueError("config_override must be a dict")

        if request.event_query:
            override = self._deep_merge(override, {
                "event_filter": {
                    "enabled": True,
                    "query": request.event_query,
                }
            })
        elif request.event_timestamps:
            # GAP-3 B5.2（CODEX-R1-P1-01）：只給 timestamps（從已匯入案例選事件）亦須啟用 event filter，
            # 否則 orchestrator 因 enabled=False 直接回 mode=none、事件被靜默丟棄
            override = self._deep_merge(override, {"event_filter": {"enabled": True}})

        if request.feature_filter:
            override = self._deep_merge(override, {
                "feature_filter": request.feature_filter.model_dump(exclude_none=True)
            })

        if request.deep_analysis_config and request.deep_analysis_config.config_override:
            override = self._deep_merge(override, request.deep_analysis_config.config_override)

        if request.feature_tiers:
            override = self._deep_merge(
                override,
                {"feature_tiers": request.feature_tiers.model_dump(exclude_none=True)},
            )

        if request.deep_analysis_config:
            override = self._deep_merge(
                override,
                self._build_deep_module_override(request.deep_analysis_config),
            )

        return override or None

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(base)
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _build_deep_module_override(self, request: DeepAnalysisRequest) -> Dict[str, Any]:
        """組 deep 模組 override;typed net_ic 欄最後注入,override 不得蓋 typed。

        注意:request 欄名 `net_ic`,config/模組鍵 `net_ic_analysis`——此處映射。
        config_override.net_ic_analysis 已於 Pydantic 層整節 reject(T-F12)。
        """
        modules = request.modules
        # 先吃 config_override(其他節仍允許);防禦性剔除 net_ic_analysis
        base: Dict[str, Any] = dict(request.config_override or {})
        base.pop("net_ic_analysis", None)

        net_ic = request.net_ic
        typed: Dict[str, Any] = {
            "factor_return": {"enabled": modules.factor_return},
            "factor_centrality": {"enabled": modules.factor_centrality},
            "trend_analysis": {"enabled": modules.trend_analysis},
            "parameter_sensitivity": {"enabled": modules.parameter_sensitivity},
            "rolling_oos": {"enabled": modules.rolling_oos},
            "factor_orthogonalization": {"enabled": modules.factor_orthogonalization},
            "factor_exposure": {"enabled": modules.factor_exposure},
            "long_short_analysis": {"enabled": modules.long_short_analysis},
            "feature_quality_diagnostics": {"enabled": modules.feature_quality_diagnostics},
            # typed 最後:enabled + cost 三鍵(T-F16 union 序列化由 _to_json_compatible 保形)
            "net_ic_analysis": {
                "enabled": modules.net_ic_analysis,
                "cost_enabled": bool(net_ic.cost_enabled),
                "cost_bps": net_ic.cost_bps,
            },
        }
        # merge 順序:base 先、typed 後 → typed 覆蓋同鍵
        return self._deep_merge(base, typed)

    def _resolve_selected_features(
        self,
        analyzer: Any,
        selected_features: Optional[List[str]],
        top_n: int,
    ) -> Optional[List[str]]:
        if selected_features:
            return selected_features

        top_features = analyzer.get_top_features(n=top_n)
        if not top_features:
            return None

        return [
            item.get("feature_name")
            for item in top_features
            if isinstance(item, dict) and item.get("feature_name")
        ]

    def _serialize_deep_report(self, deep_report: Any) -> Dict[str, Any]:
        if is_dataclass(deep_report):
            raw = asdict(deep_report)
        elif hasattr(deep_report, "model_dump"):
            raw = deep_report.model_dump()
        elif isinstance(deep_report, dict):
            raw = deep_report
        else:
            raw = {"raw": str(deep_report)}

        normalized = self._to_json_compatible(raw)
        if isinstance(normalized, dict):
            # F2: serializer + task storage 出口 sanitizer(ok 放行 / legacy 擋)
            return sanitize_factor_returns(normalized)
        return {"raw": normalized}

    def _attach_cross_symbol_context(self, deep_payload: Dict[str, Any], analyzer: Any) -> Dict[str, Any]:
        if not isinstance(deep_payload, dict):
            return deep_payload

        report = None
        if hasattr(analyzer, "get_report"):
            try:
                report = analyzer.get_report()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Unable to read analyzer report for deep payload merge: %s", exc)

        if not isinstance(report, dict):
            return deep_payload

        for key in ("cross_symbol_validation", "cross_sectional_symbol_ic"):
            if key in report and key not in deep_payload:
                deep_payload[key] = self._to_json_compatible(report.get(key))

        return deep_payload

    # conditional metric 三鍵(T-F16 / F2 ⑯):§U 形狀守恆,序列化時原樣保留禁扁平化
    _CONDITIONAL_METRIC_KEYS: frozenset[str] = frozenset(
        {"net_factor_return", "breakeven_cost_bps", "profitable_after_cost"}
    )
    _UNION_SHAPE_KEYS: frozenset[str] = frozenset({"status", "value", "reason"})

    def _to_json_compatible(self, value: Any, ic_response_v2: bool = False) -> Any:
        """Recursively normalize nested values for FastAPI/Pydantic serialization.

        T-F16:conditional metric 三鍵物件({status,value,reason})原樣保留禁扁平化。
        """

        if value is None:
            return value

        if isinstance(value, float):
            return value if math.isfinite(value) else None

        if isinstance(value, (str, int, bool)):
            return value

        if isinstance(value, np.generic):
            scalar = value.item()
            if isinstance(scalar, float):
                return scalar if math.isfinite(scalar) else None
            return scalar

        if isinstance(value, np.ndarray):
            return [
                self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                for item in value.tolist()
            ]

        if is_dataclass(value):
            payload = asdict(value)
            if isinstance(value, ICResult) and not ic_response_v2:
                payload.pop("eval_status", None)
            return self._to_json_compatible(payload, ic_response_v2=ic_response_v2)

        if hasattr(value, "model_dump"):
            return self._to_json_compatible(
                value.model_dump(),
                ic_response_v2=ic_response_v2,
            )

        if isinstance(value, dict):
            # discriminated union 形狀:{status, value, reason} — 遞迴保形,不抽 value
            if set(value.keys()) == self._UNION_SHAPE_KEYS:
                return {
                    "status": self._to_json_compatible(
                        value.get("status"), ic_response_v2=ic_response_v2
                    ),
                    "value": self._to_json_compatible(
                        value.get("value"), ic_response_v2=ic_response_v2
                    ),
                    "reason": self._to_json_compatible(
                        value.get("reason"), ic_response_v2=ic_response_v2
                    ),
                }
            out: Dict[str, Any] = {}
            for key, item in value.items():
                sk = str(key)
                # 三鍵在父 dict 層確保仍為物件(若誤傳裸值則包回 unavailable 形不在此;僅保 dict)
                if sk in self._CONDITIONAL_METRIC_KEYS and isinstance(item, dict):
                    out[sk] = self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                else:
                    out[sk] = self._to_json_compatible(item, ic_response_v2=ic_response_v2)
            return out

        if isinstance(value, (list, tuple, set)):
            return [
                self._to_json_compatible(item, ic_response_v2=ic_response_v2)
                for item in value
            ]

        if hasattr(value, "isoformat"):
            try:
                return value.isoformat()
            except Exception:
                pass

        return str(value)

    def _materialize_features_for_ic(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
    ) -> tuple[str, str]:
        """透過 FeatureLibrary 載入特徵並 materialize 成 orchestrator 可讀的 HDF5。"""
        features_df = self._feature_library.load(
            symbol,
            timeframe,
            config_hash=config_hash,
        )
        cache_dir = Path("data_cache/reports/ic_ingest_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_key = config_hash or "latest"
        safe_key = f"{symbol}_{timeframe}_{hash_key}".replace("/", "_")
        h5_path = cache_dir / f"{safe_key}.h5"
        meta_path = cache_dir / f"{safe_key}_meta.json"

        if not h5_path.exists():
            self._write_features_h5(h5_path, symbol, timeframe, features_df)
        if not meta_path.exists():
            meta_payload = self._build_ic_metadata_from_run(
                symbol,
                timeframe,
                config_hash,
                list(features_df.columns),
            )
            meta_path.write_text(
                json.dumps(meta_payload, ensure_ascii=False),
                encoding="utf-8",
            )
        return str(h5_path.resolve()), str(meta_path.resolve())

    @staticmethod
    def _write_features_h5(
        path: Path,
        symbol: str,
        timeframe: str,
        features_df: pd.DataFrame,
    ) -> None:
        """將 DataFrame 寫入 IC orchestrator 可讀的 HDF5 格式。"""
        path.parent.mkdir(parents=True, exist_ok=True)
        group_key = f"{symbol}/{timeframe}"
        index_values = features_df.index
        if isinstance(index_values, pd.DatetimeIndex):
            timestamps = index_values.view("int64") // 10**9
        else:
            timestamps = np.arange(len(features_df), dtype=np.int64)

        with h5py.File(path, "w") as file:
            group = file.create_group(group_key)
            group.create_dataset(
                "features",
                data=features_df.to_numpy(dtype=np.float32),
                compression="gzip",
            )
            group.create_dataset("timestamps", data=timestamps, compression="gzip")
            str_dtype = h5py.string_dtype(encoding="utf-8")
            group.create_dataset(
                "feature_names",
                data=np.array(features_df.columns.tolist(), dtype=object),
                dtype=str_dtype,
            )

    def _write_ic_meta_json(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
        feature_names: Optional[List[str]] = None,
    ) -> str:
        """寫入 IC 分析用的 metadata JSON（symbol/timeframe 供 label 生成）。"""
        cache_dir = Path("data_cache/reports/ic_ingest_cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_key = config_hash or "latest"
        safe_key = f"{symbol}_{timeframe}_{hash_key}".replace("/", "_")
        meta_path = cache_dir / f"{safe_key}_meta.json"
        meta_payload = self._build_ic_metadata_from_run(
            symbol,
            timeframe,
            config_hash,
            feature_names or [],
        )
        meta_path.write_text(
            json.dumps(meta_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(meta_path.resolve())

    def _build_ic_metadata_from_run(
        self,
        symbol: str,
        timeframe: str,
        config_hash: Optional[str],
        feature_names: List[str],
    ) -> Dict[str, Any]:
        """從 run catalog 建立 IC orchestrator 需要的 per-feature metadata。"""
        metadata: Dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "config_hash": config_hash,
        }
        catalog_path: Optional[Path] = None
        if config_hash:
            catalog_path = (
                Path("data_cache/features")
                / symbol
                / timeframe
                / config_hash
                / "feature_catalog_cache.parquet"
            )
        if catalog_path and catalog_path.exists():
            catalog_df = pd.read_parquet(catalog_path)
            for _, row in catalog_df.iterrows():
                name = str(row.get("name"))
                if not name:
                    continue
                metadata[name] = {
                    "name": name,
                    "category": row.get("category") or "unknown",
                    "layer": row.get("layer") or 1,
                }
        for feature_name in feature_names:
            if feature_name not in metadata:
                metadata[feature_name] = {
                    "name": feature_name,
                    "category": "unknown",
                    "layer": 1,
                }
        return metadata

    def _append_cross_sectional_labels(
        self,
        cross_df: pd.DataFrame,
        symbols: List[str],
        timeframe: str,
    ) -> pd.DataFrame:
        """從 kline 為橫截面特徵附加 return_1 標籤欄。"""
        from momentum.factories import create_label_generator

        kline_reader = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)
        label_generator = create_label_generator()
        working_df = cross_df.copy()

        if not isinstance(working_df.index, pd.MultiIndex):
            raise ValueError("cross-sectional features must use MultiIndex")

        index_names = list(working_df.index.names)
        symbol_level_idx = working_df.index.nlevels - 1
        if "_symbol" in index_names:
            symbol_level_idx = index_names.index("_symbol")

        for symbol in symbols:
            raw_data = kline_reader.read_klines(symbol, timeframe)
            if raw_data is None or raw_data.empty or "close" not in raw_data.columns:
                raise ValueError(f"kline data unavailable for {symbol}/{timeframe}")
            if "timestamp" not in raw_data.columns:
                raise ValueError(f"kline data missing timestamp for {symbol}/{timeframe}")
            ts_raw = raw_data["timestamp"]
            if not np.issubdtype(ts_raw.dtype, np.integer):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} must be integer epoch seconds, "
                    f"got {ts_raw.dtype}"
                )
            ts_values = ts_raw.to_numpy()
            if ts_values.size > 0 and np.any(ts_values < 0):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} contains negative values"
                )
            if ts_values.size > 1 and np.any(np.diff(ts_values) <= 0):
                raise ValueError(
                    f"kline timestamp for {symbol}/{timeframe} must be strictly "
                    "increasing without duplicates"
                )
            kline_index = pd.DatetimeIndex(pd.to_datetime(ts_raw, unit="s"))
            close = raw_data["close"].copy()
            close.index = kline_index
            label_series = label_generator.generate_returns_by_type(
                close,
                1,
                "log",
            )
            symbol_mask = working_df.index.get_level_values(symbol_level_idx) == symbol
            if not symbol_mask.any():
                continue
            symbol_index = working_df.index[symbol_mask].droplevel(symbol_level_idx)
            if not isinstance(symbol_index, pd.DatetimeIndex):
                symbol_index = pd.DatetimeIndex(pd.to_datetime(symbol_index))
            aligned = label_series.reindex(symbol_index)
            matched_mask = symbol_index.isin(kline_index)
            if bool(matched_mask.any()):
                matched_index = symbol_index[matched_mask]
                direct = label_series.reindex(matched_index)
                reindexed = aligned.reindex(matched_index)
                valid = direct.notna().to_numpy() & reindexed.notna().to_numpy()
                if bool(valid.any()):
                    np.testing.assert_allclose(
                        reindexed.to_numpy(dtype=np.float64)[valid],
                        direct.to_numpy(dtype=np.float64)[valid],
                        rtol=1e-5,
                        atol=1e-5,
                        err_msg=(
                            f"label misalignment for {symbol}/{timeframe} at matched timestamps"
                        ),
                    )
            working_df.loc[symbol_mask, "return_1"] = aligned.to_numpy()

        return working_df

    def _load_meta(self, meta_path: Optional[str]) -> Dict[str, Any]:
        if not meta_path:
            return {}

        path = Path(meta_path)
        if not path.exists():
            raise FileNotFoundError(f"meta_path not found: {meta_path}")

        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid meta JSON: {meta_path}") from exc

    def _resolve_filtered_path(self, metadata: Dict[str, Any]) -> Path:
        symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
        timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
        if symbol and timeframe:
            name = f"{symbol}_{timeframe}_filtered.h5"
        else:
            name = "filtered_features.h5"
        return Path("data_cache/features") / name

    def _start_background_coroutine(self, coroutine_factory: Callable[[], Any]) -> None:
        """Run async workflow in a daemon thread to avoid request-loop cancellation."""

        def runner() -> None:
            try:
                asyncio.run(coroutine_factory())
            except Exception as exc:
                logger.error("Background coroutine crashed: %s", exc, exc_info=True)

        threading.Thread(target=runner, daemon=True).start()


ic_analysis_service = ICAnalysisService()
