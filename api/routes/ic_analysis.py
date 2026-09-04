"""IC analysis REST API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import math

import pandas as pd
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse

from api.core.logging import get_logger
from api.models.ic_models import (
    DeepAnalysisRequest,
    DeepAnalysisResponse,
    FeatureListItem,
    FeatureListResponse,
    ICAnalyzeRequest,
    ApplyTransformsRequest,
    ApplyTransformsResponse,
    ICAnalyzeResponse,
    ICFullAnalysisRequest,
    ICTaskStatusResponse,
    ICRefilterRequest,
)
from api.core.config import settings
from api.services.ic_analysis_service import ic_analysis_service
from momentum.factories import load_ic_config


router = APIRouter(prefix="/api/v1/ic")
logger = get_logger("api.routes.ic_analysis")


def _reject_when_over_feature_cap(request, *, entrypoint: str = "analyze") -> None:
    """GAP-3 UX Task 6.1：**啟動任務之前**擋下特徵數超量之分析請求。

    🔴 **本 Task 為過渡止血**：GAP-6 之分塊計算上線後由該機制取代，本函式屆時**一併刪除**
    （SPEC Task 6.1「存活至 GAP-6」）。不得留著空跑而成為永遠通過的假綠。

    🔴 **必須擋在 `ic_analysis_service.start_analysis` 之前**——Task 6.4 要證明
    「擋下時未載入大矩陣」，那個證明綁定「cap 檢查在任務建立之前」這個位置；
    檢查若被移到任務啟動之後，6.4 會量到已載入大矩陣之 footprint 而失去意義。

    🔴 **本閘的責任＝鏡像 service 會實際載入哪個 run**，而不是「看看請求上有沒有寫特徵數」。
      這句話是 R3 三家一致 finding（`CODEX-R3-P1-01`／`COMPOSER-R3-P1-01`／
      `GROK-R3-P1-01`＋`P1-02`）換來的。**原本這裡寫著「分析只有兩條路走得成」——那是錯的**，
      而且錯得很具體：`{"symbol":"BCHUSDT","timeframe":"12h"}`（省略 `config_hash`）與
      `{"mode":"cross_sectional","symbols":[...]}`（不帶 `cross_sectional_runs`）兩種 payload，
      閘門的候選全部解析不出 ⇒ 放行，而 service 隨後自己走 `find_latest_materialized`／
      `load_multi` 載入本機 latest（實測 161,031／161,092，cap 為 80,515）。
      三家各自實跑同一組對照：不帶 hash ⇒ 200 且 `start_analysis` 被呼叫；補上 hash ⇒ 400、`calls=0`。
      UI 因 `ICConfigPanel` 強制選 run 而不會走到，**裸 API 與腳本會**。

    🔴 解析不出特徵數 ⇒ **放行**（不擋）。這條**仍然保留**，但適用面已收窄到它原本該有的範圍：
      呼叫端給了 `features_path`（golden replay／artifact 重放）而該檔又讀不出 shape 時。
      擋住它會弄壞 golden replay 這個既有消費端。
      **具名破口**：API 呼叫端硬塞 `features_path` 指向一個 registry 查不到、header 也讀不出的
      大 run 可繞過本閘；因本 Task 是過渡止血且該路徑非使用者介面之路徑，接受之並具名記錄
      （見 `docs/GAP3UX_IMPL_HANDOFF.md` 殘留表）。

    🔴 **不提供「強制略過上限」之開關**（SPEC Task 6.1「不可做」）。
    """
    from momentum.factories import ic_report_reason

    # 🔴 **本層不得再自行解析**（`CODEX-R4-P1-01`／`P1-03`）。這裡原本有一段手抄的、
    #    與 service 平行的解析：把候選塞成一袋取 `max()`，而 service 走互斥分支；
    #    且此處每次 `FeatureRegistry()` 重讀磁碟，而 service 的 registry 在行程啟動時就讀好。
    #    兩份邏輯、兩份快照 ⇒ 四輪 review 抓到四種不同步（少一味＝該擋沒擋；多一味＝誤擋）。
    #    現在由「決定要載入什麼的人」回答「它有多大」，鏡像成為結構性質而非人工維護的副本。
    feature_count = ic_analysis_service.resolve_planned_feature_count(
        request, entrypoint=entrypoint)
    if feature_count is None:
        return
    cap = int(settings.ic_analysis_max_features)
    if feature_count <= cap:
        return
    raise HTTPException(status_code=400, detail={
        # reason 字面由契約取得（Task 6.0）；本層**不得**硬寫
        "reason": ic_report_reason("analysis_rejected"),
        "message": (
            # 🔴 **不得叫使用者去做他沒有介面可做的事**（2026-08-27 使用者裁定）。
            #    原文為「請先縮減特徵數再分析」——本專案沒有任何縮減特徵數的介面，
            #    那句話把「系統暫時做不到」寫成了「你操作錯了」，是一條死路。
            f"這個 run 有 {feature_count} 個特徵，本機一次載得下的上限是 {cap}；"
            f"直接分析會把記憶體吃爆，因此在啟動任務之前就擋下來。"
            f"上限由實跑量測導出（見 handoffs/run_receipts/gap3ux-b9-footprint.receipt.json），"
            f"綁本機記憶體大小。"
            f"這個 run 目前無法分析——分塊計算（GAP-6）上線後本限制會取消；"
            f"在那之前請改用特徵數較少的 run。"
        ),
        "feature_count": feature_count,
        "cap": cap,
    })


#: Task 7.0b ③：只給 `event_import_id` 時，`horizon_bars` 之缺省為**字面常數 1**。
#  🔴 **禁**以匯出檔／已落檔批之 `label_definition.window.horizon_bars` 種子化——
#  §D-3′-a 已裁定該欄語意為 D-7 深度宣告，分析層**禁止**讀成答案窗；
#  既有批之該欄殘值為 3，種子化即等於靜默給錯預設答案窗。
_DEFAULT_ANALYSIS_HORIZON_BARS = 1


def _resolve_event_batch(request: ICAnalyzeRequest) -> Optional[Dict[str, Any]]:
    """GAP-3 UX Task 7.0b ③(a)：以 `request.event_import_id` 查出該批已落檔 records。

    🔴 **為什麼查在 route 而不是 service**：Rule 4 禁 `api/services/*` 互相 import
    （`check_decoupling_imports.py` 之 R4 掃 AST，連函式內的 lazy import 也擋），
    而事件批住在 `api/services/case_import_service.py`。route **不在** R4 掃描範圍。
    ⇒ 這是「服務端查出、同一次分析內原子完成」在本 repo 之解耦規則下的落地形；
    **具名偏差**：SPEC 之編排草圖把查詢畫在 `_run_analysis` 內。

    🔴 **`G3-D2` D1.7（2026-09-04）改寫初始值規則**：不再取該批 F-0 種子＋常數 1，
    改為**依宣告深度導出之三種報酬選項預設**（見函式尾段）。`decision_offset_bars`
    仍取 F-0 種子（k 之參數化留 D4.3）。
    """
    if not request.event_import_id:
        return None
    from api.services.case_import_service import get_event_import_service

    detail = get_event_import_service().get_import(request.event_import_id)
    if detail is None:
        raise HTTPException(
            status_code=404, detail=f"event import {request.event_import_id!r} not found",
        )
    records = [dict(r) for r in (detail.records or [])]
    if not records:
        raise HTTPException(
            status_code=422,
            detail={"kind": "empty_event_batch",
                    "message": f"事件批 {request.event_import_id!r} 沒有任何 records"},
        )
    seed = records[0]
    # 🔴 **混 `decision_offset_bars` ⇒ fail-closed**（`CODEX-R2-P1-02`，B-D1 R2 實跑命中）：
    #    契約層允許逐列不同（`decision_offset_bars` 不在同質維度內），而本函式取 `records[0]`
    #    之 k、`_analysis_copy` 再把它**套用全批** ⇒ 其餘事件被對齊到**錯的決策根**，
    #    且值合法、沒有任何測試會紅。實測：`records_k=[0, 2]` ⇒ `resolved k=0`，
    #    第二個事件之 `decision_at` 變成 `t0`（依其宣告應為 `ot[t0_idx-2]`）。
    #    ⇒ 在能算錯之前先擋。k 之逐批參數化（record 值集合＋分析 k 分離）是 D4.3 的交付；
    #    在那之前，混 k 批**不進分析**，而不是挑一個 k 蒙混過去。
    ks = sorted({int(r["decision_offset_bars"]) for r in records
                 if isinstance(r.get("decision_offset_bars"), int)
                 and not isinstance(r.get("decision_offset_bars"), bool)})
    if len(ks) > 1:
        raise HTTPException(status_code=422, detail={
            "kind": "mixed_decision_offset_bars",
            "message": (
                f"事件批 {request.event_import_id!r} 之 decision_offset_bars 批內不一致（值＝{ks}）。"
                "分析時只能有一個決策位移；若照第一列取值，其餘事件會被對齊到錯的決策根，"
                "而算出來的數字仍是合法值、看不出異常。請拆批，或等 k 之分析參數化上線。"
            ),
        })
    spec = dict(request.event_label_spec or {})
    # 🔴 **`CODEX-R2-P1-01`（閉合輪抓到，真實批次跑不起來）**：深度宣告是**批次層 receipt**，
    #    住在 payload 的**頂層** `lookahead_declaration`，**不是**每一列上。
    #    首版只讀 `records[0]["lookahead_bars_declared"]` ⇒ 對真實批次（實測 780 列）拿到 `{}`，
    #    producer 隨即 fail-closed（`缺 timeframe '12h'`）⇒ **事件分析在真實資料上根本跑不完**。
    #    這正是我在 brief「我沒查的」第 5 列自己列出來的那件事——列出來了，但沒去打。
    #    ⇒ 順序：批次 receipt（權威）→ 逐列欄（`/search` 匯出之 Task 4.1 ③ 會寫）→ fail-closed。
    receipt = get_event_import_service()._stored_declaration(request.event_import_id)
    declared = (receipt or {}).get("lookahead_bars_declared")
    if not isinstance(declared, dict) or not declared:
        row_level = seed.get("lookahead_bars_declared")
        declared = row_level if isinstance(row_level, dict) and row_level else None
    if not declared:
        raise HTTPException(status_code=422, detail={
            "kind": "missing_lookahead_declaration",
            "message": (
                f"事件批 {request.event_import_id!r} 沒有答案窗深度宣告"
                "（批次 receipt 之 lookahead_bars_declared 與逐列欄皆缺）——"
                "purge 下界無從導出，故不進行分析。請重新匯入並填寫深度宣告。"
            ),
        })
    # ── `G3-D2` D1.7：`event_label_spec` 之初始值依**宣告深度**導出（裁定②③ 2026-09-03）──
    #
    # 🔴 **deterministic，無隨機、無「取第一列」之隱性取樣**：
    #    `trigger_tfs = sorted({r["timeframe"]})` ⇒ 單 tf 才有唯一深度可談。
    # 🔴 **仍禁讀 `label_definition.window.horizon_bars`**（§D-3′-a）：該欄語意是 D-7 深度宣告，
    #    分析層讀成答案窗即靜默給錯預設；深度一律取批次 receipt 之 `lookahead_bars_declared`。
    # 🔴 `setdefault` 語意不變：**請求明確給的值一律優先**，本段只補「沒給」的那些鍵。
    trigger_tfs = sorted({str(r.get("timeframe")) for r in records if r.get("timeframe")})
    mixed_tf = len(trigger_tfs) > 1
    if mixed_tf:
        # 混 tf 批**不自動選深度**：各 tf 之「一根」長度不同，取任一個都是猜。
        # ⇒ 退回「當根」（不依賴 h）並揭露，請使用者手動設定。
        preset_entry, preset_mode, preset_h = "trigger_open", "open_to_close", 1
        seed_note = "混合 timeframe 批，請手動設定量法與 h（未自動依深度選擇）"
    else:
        depth = int(declared.get(trigger_tfs[0], 0)) if trigger_tfs else 0
        if depth >= 1:
            # 「持有」：從 t₀ 開盤進場、持有 depth 根到收盤。
            preset_entry, preset_mode, preset_h = "trigger_open", "open_to_horizon_close", depth
            seed_note = f"本次量法＝持有（預設依宣告深度；續漲需手動選）；h＝{depth}（初始＝宣告深度）"
        else:
            # 「當根」：深度 0 ⇒ 事件當根內的漲跌，與 h 無關。
            preset_entry, preset_mode, preset_h = "trigger_open", "open_to_close", 1
            seed_note = "本次量法＝當根（預設依宣告深度；續漲需手動選）；當根不用 h"
    spec.setdefault("entry_price_semantic", preset_entry)
    spec.setdefault("label_return_mode", preset_mode)
    # 🔴 「當根」下 `horizon_bars` **仍送 1**（inert 哨兵）：`event_label_spec` 恆為恰四鍵，
    #    normalizer 對多一鍵少一鍵皆 fail-closed；`open_to_close` 之值與 h 無關（golden 已斷言）。
    spec.setdefault("horizon_bars", preset_h)
    spec.setdefault("decision_offset_bars", seed.get("decision_offset_bars"))
    return {
        "records": records,
        "event_label_spec": spec,
        "lookahead_bars_declared": dict(declared),
        # 揭露字串由**後端**產生（前端不重組）：它描述的是後端實際採用的初始值規則。
        "event_label_spec_seed_note": seed_note,
    }


@router.post("/analyze", response_model=ICAnalyzeResponse)
async def start_ic_analysis(request: ICAnalyzeRequest):
    """Start IC analysis task."""
    # Task 6.1：**在呼叫 service 之前**，任務尚未建立
    _reject_when_over_feature_cap(request)
    try:
        # 🔴 **非事件呼叫端之呼叫形狀逐字不變**（SPEC：legacy 路徑行為完全不變）：
        #    沒有 `event_import_id` 時**連 keyword 都不傳**，而不是傳 `event_batch=None`。
        #    差別看似無關緊要，但既有測試以 spy 包住 `start_analysis` 並比對呼叫形狀，
        #    多一個 keyword 就會讓那些 spy 全數 `TypeError`——實際踩到 10 條紅。
        event_batch = _resolve_event_batch(request)
        if event_batch is None:
            return await ic_analysis_service.start_analysis(request)
        return await ic_analysis_service.start_analysis(request, event_batch=event_batch)
    except HTTPException:
        # 🔴 `COMPOSER-R1-P1-04`／`CODEX-R1-P2-04`：`HTTPException` 繼承 `Exception`
        #    ⇒ 下面那個 `except Exception` 會把 `_resolve_event_batch` 拋的 **404 吞成 500**。
        #    實跑確認：帶不存在的 `event_import_id` 得到 500，body 裡才寫著「404: ... not found」。
        #    ⇒ 這裡必須先原樣放行，否則所有「我方刻意設計的 HTTP 狀態碼」都會被降級成 500。
        raise
    except ValueError as exc:
        logger.error("Invalid IC analysis request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start IC analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/task/{task_id}", response_model=ICTaskStatusResponse)
async def get_task_status(task_id: str):
    """Get IC analysis task status."""
    try:
        status = ic_analysis_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get task status: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/result/{task_id}")
async def get_result(task_id: str, schema_version: Optional[int] = Query(None)):
    """Get IC analysis result."""
    try:
        result = ic_analysis_service.get_result(task_id, schema_version)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get result: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/features/list", response_model=FeatureListResponse)
async def list_available_features(
    features_path: Optional[str] = Query(None, description="Legacy features path or parquet key"),
    meta_path: Optional[str] = None,
    symbol: Optional[str] = Query(None, description="Feature Library symbol"),
    timeframe: Optional[str] = Query(None, description="Feature Library timeframe"),
    config_hash: Optional[str] = Query(None, description="Feature Library config_hash"),
):
    """List available features from HDF5 + optional metadata."""
    try:
        features = ic_analysis_service.list_features(
            features_path=features_path,
            meta_path=meta_path,
            symbol=symbol,
            timeframe=timeframe,
            config_hash=config_hash,
        )
        return {
            "total": len(features),
            "features": [FeatureListItem(**item) for item in features],
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/deep-analysis/{task_id}", response_model=ICAnalyzeResponse)
async def start_deep_analysis(task_id: str, request: DeepAnalysisRequest):
    """Start deep analysis for an existing IC task."""
    try:
        return await ic_analysis_service.start_deep_analysis(task_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "Task not found" in message else 400
        raise HTTPException(status_code=status_code, detail=message)
    except Exception as exc:
        logger.error("Failed to start deep analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/deep-analysis/{task_id}/result", response_model=DeepAnalysisResponse)
async def get_deep_analysis_result(task_id: str):
    """Get deep analysis result for task."""
    try:
        status = ic_analysis_service.get_task_status(task_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        result = ic_analysis_service.get_deep_analysis_result(task_id)
        summary = None
        module_status = None
        if isinstance(result, dict):
            summary = {
                "total_modules": int(result.get("total_modules", 10)),
                "completed_count": int(result.get("completed_count", 0)),
                "skipped_count": int(result.get("skipped_count", 0)),
                "failed_count": int(result.get("failed_count", 0)),
                "total_execution_time_s": float(result.get("total_execution_time_s", 0.0)),
            }
            module_status = [
                {
                    "module_name": module_name,
                    "status": module_state,
                }
                for module_name, module_state in (result.get("module_summary") or {}).items()
            ]

        return {
            "task_id": task_id,
            "status": status.get("status", "running"),
            "progress": float(status.get("progress", 0.0)),
            "current_step": status.get("current_step"),
            "summary": summary,
            "module_status": module_status,
            "results": result,
            "applied_tier": status.get("applied_tier", "intermediate"),
            "error": status.get("error"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get deep analysis result: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/full-analysis", response_model=ICAnalyzeResponse)
async def start_full_analysis(request: ICFullAnalysisRequest):
    """Start one-shot full analysis workflow."""
    # Task 6.1：🔴 **本端點原本完全沒套閘門**（`CODEX-R1-P1-01`）——只擋 `/analyze`
    # 等於留了一扇同樣會把記憶體吃爆的門。閘門要擋的是「啟動分析任務」這件事，
    # 不是某一個 URL，所以**每個會啟動任務的入口都要套**。
    _reject_when_over_feature_cap(request, entrypoint="full_analysis")
    # 🔴 **三家全員（`CODEX-R1-P1-01`／`COMPOSER-R1-P1-03`／`GROK-R1-P1-03`）**：
    #    `ICFullAnalysisRequest` 繼承 `ICAnalyzeRequest` ⇒ 它**收得下** `event_import_id`，
    #    但 `_run_full_analysis` **不跑五階段、不跑 coverage 閘**，只把 `event_timestamps` 透傳
    #    ⇒ 使用者以為做了事件分析，實際上那個欄位被**靜默忽略**。
    #    ⇒ fail-closed：本端點本批不支援事件批，明說拒絕，不默默照跑。
    if getattr(request, "event_import_id", None):
        raise HTTPException(status_code=400, detail={
            "kind": "event_batch_not_supported_on_full_analysis",
            "message": (
                "/full-analysis 本批不支援事件批（event_import_id）——該端點不跑 GAP-3 之五階段"
                "編排與 feature-run 涵蓋閘。請改用 POST /api/v1/ic/analyze。"
            ),
        })
    try:
        return await ic_analysis_service.start_full_analysis(request)
    except ValueError as exc:
        logger.error("Invalid full analysis request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to start full analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/summary/{task_id}")
async def get_summary(task_id: str):
    """Get AI summary for IC analysis."""
    try:
        result = ic_analysis_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
        summary = _build_summary(result)
        return {"task_id": task_id, "summary": summary}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get summary: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/top-features")
async def get_top_features(
    n: int = Query(30, ge=1, le=500),
    sort_by: str = Query("icir"),
    task_id: Optional[str] = Query(None),
):
    """Get top features for the latest task."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        analyzer = ic_analysis_service.get_analyzer(resolved_task_id)
        if analyzer is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return analyzer.get_top_features(n=n, sort_by=sort_by)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get top features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/decay/{feature_name}")
async def get_decay(feature_name: str, task_id: Optional[str] = Query(None)):
    """Get IC decay for a feature."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        decay = (result.get("ic_decay") or {}).get(feature_name)
        if decay is None:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_name}")
        return decay
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get decay: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/quantile/{feature_name}")
async def get_quantile(feature_name: str, task_id: Optional[str] = Query(None)):
    """Get quantile returns for a feature."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        quantile = (result.get("quantile_returns") or {}).get(feature_name)
        if quantile is None:
            raise HTTPException(status_code=404, detail=f"Feature not found: {feature_name}")
        return quantile
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get quantile returns: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/correlation")
async def get_correlation(task_id: Optional[str] = Query(None)):
    """Get correlation matrix."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        return result.get("correlation_matrix", {})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get correlation matrix: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/grouped")
async def get_grouped(task_id: Optional[str] = Query(None)):
    """Get grouped IC results."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        result = ic_analysis_service.get_result(resolved_task_id) if resolved_task_id else None
        if result is None:
            raise HTTPException(status_code=404, detail="Result not found")
        return result.get("grouped_ic", {})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get grouped IC: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/config")
async def update_config(config_override: Dict[str, Any] = Body(...)):
    """Update IC config by returning merged config."""
    try:
        config = load_ic_config(api_override=config_override)
        return config.model_dump(by_alias=True)
    except Exception as exc:
        logger.error("Failed to update IC config: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/refilter")
async def refilter(
    request: ICRefilterRequest,
    task_id: Optional[str] = Query(None),
):
    """Refilter IC results with new thresholds."""
    try:
        resolved_task_id = task_id or ic_analysis_service.get_last_task_id()
        if not resolved_task_id:
            raise HTTPException(status_code=404, detail="Task not found")
        return await ic_analysis_service.refilter(resolved_task_id, request.thresholds)
    except ValueError as exc:
        logger.error("Invalid refilter request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to refilter: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}")
async def export_filtered_features(task_id: str):
    """Export filtered features HDF5.

    LA-1 B3-H5-01：export 前驗當次 run freshness；stale stable-path → 404。
    """
    try:
        result = ic_analysis_service.get_result(task_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")

        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        export_path = _resolve_filtered_path(metadata)
        from momentum.Analysis.ic_reporter import assert_filtered_export_fresh

        try:
            fresh_path = assert_filtered_export_fresh(
                result if isinstance(result, dict) else None,
                export_path,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return FileResponse(fresh_path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export filtered features: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export/{task_id}/{format}")
async def export_analysis(
    task_id: str,
    format: str,
    module: Optional[str] = Query(default=None),
):
    """Export analysis report in multi-format outputs."""
    try:
        export_result = ic_analysis_service.export_analysis(
            task_id=task_id,
            format_type=format,
            module_name=module,
        )
        logger.info("Export success: task_id=%s, format=%s, module=%s", task_id, format, module)

        if export_result["type"] == "file":
            return FileResponse(
                path=export_result["path"],
                media_type=export_result["media_type"],
                filename=export_result["filename"],
            )

        headers = {
            "Content-Disposition": f"attachment; filename=\"{export_result['filename']}\"",
        }
        if export_result["type"] == "bytes":
            content = export_result["content"]
            if hasattr(content, "getvalue"):
                content = content.getvalue()
            return Response(
                content=content,
                media_type=export_result["media_type"],
                headers=headers,
            )
        return StreamingResponse(
            export_result["content"],
            media_type=export_result["media_type"],
            headers=headers,
        )
    except ValueError as exc:
        message = str(exc)
        if "Task not found" in message or "Result not found" in message:
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=422, detail=message)
    except TypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export analysis: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/export-csv/{task_id}")
async def export_filtered_csv(task_id: str):
    """Export filtered features as CSV.

    LA-1 B3 oracle ⑤：HTTP header ``X-Analysis-Status`` + 檔首註解行。
    """
    try:
        analyzer = ic_analysis_service.get_analyzer(task_id)
        if analyzer is None:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        filtered_df = analyzer.get_filtered_features()
        if filtered_df is None or filtered_df.empty:
            raise HTTPException(status_code=404, detail="Filtered features not found")

        result = ic_analysis_service.get_result(task_id)
        # LA-1 B3-ENUM-01：讀取點 fail-closed — 非字面 ok_oos 一律 degraded
        from momentum.Analysis.ic_reporter import normalize_analysis_status

        if isinstance(result, dict):
            raw_status = result.get("analysis_status")
        else:
            raw_status = None  # 缺 result / 非 dict → degraded
        analysis_status = normalize_analysis_status(raw_status)

        from io import StringIO

        buf = StringIO()
        buf.write(f"# analysis_status={analysis_status}\n")
        filtered_df.to_csv(buf, index=True)
        return Response(
            content=buf.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={
                "X-Analysis-Status": analysis_status,
                "Content-Disposition": f'attachment; filename="ic_filtered_{task_id}.csv"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to export CSV: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/apply-transforms/{task_id}", response_model=ApplyTransformsResponse)
async def apply_transforms(task_id: str, request: ApplyTransformsRequest):
    """Apply L6.5 post-processing (rank/zscore/gaussian) to IC-selected features.

    Designed for the IC-First workflow:
      1. Feature Factory (IC-First mode) generates L1-L7 with winsor+fracdiff only.
      2. IC Gatekeeper filters to the best features.
      3. Call this endpoint to apply rank/zscore/gaussian to those features.

    Transform order is always: rank → zscore → gaussian.
    """
    try:
        result = await ic_analysis_service.apply_transforms(
            task_id=task_id,
            selected_features=request.selected_features,
            rank=request.rank,
            zscore=request.zscore,
            gaussian=request.gaussian,
            rank_window=request.rank_window,
            zscore_windows=request.zscore_windows,
        )
        return ApplyTransformsResponse(**result)
    except (FileNotFoundError, ValueError) as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc))
    except Exception as exc:
        logger.error("apply-transforms failed for task %s: %s", task_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


def _resolve_filtered_path(metadata: Dict[str, Any]) -> Path:
    symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
    timeframe = metadata.get("timeframe") if isinstance(metadata, dict) else None
    if symbol and timeframe:
        name = f"{symbol}_{timeframe}_filtered.h5"
    else:
        name = "filtered_features.h5"
    return Path("data_cache/features") / name


def _build_summary(report: Dict[str, Any]) -> str:
    summary_table = report.get("summary_table", []) if isinstance(report, dict) else []

    def _icir_key(item: Dict[str, Any]) -> float:
        # 🔴 UAT B15（2026-09-02，票 `G3-D15`）：degraded／full-sample 或樣本極少時 `icir` 鍵**存在但為 None**
        #    （`get(..., -inf)` 對「鍵在、值 None」無效）⇒ `None < None` TypeError ⇒ `/ic/summary` 500 ⇒ 畫面紅字。
        #    非有限值一律排最後，不當成數字。
        v = item.get("icir")
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) else float("-inf")

    top_features = sorted(summary_table, key=_icir_key, reverse=True)[:5]

    lines = [
        "# IC Gatekeeper Summary",
        "",
        "## Key Findings",
    ]

    if top_features:
        for item in top_features:
            lines.append(
                f"- {item.get('feature_name')}: ICIR={item.get('icir')}, IC Mean={item.get('ic_mean')}"
            )
    else:
        lines.append("- No features passed the filter.")

    lines.extend(
        [
            "",
            "## Regime Analysis",
            "- Regime statistics available in grouped_ic section.",
            "",
            "## Recommendations",
            "- Review thresholds if too few features passed.",
            "",
            "## Risk Warnings",
            "- Event sample size may reduce statistical confidence.",
        ]
    )

    return "\n".join(lines)
