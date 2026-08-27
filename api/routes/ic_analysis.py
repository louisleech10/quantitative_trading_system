"""IC analysis REST API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

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


def _reject_when_over_feature_cap(request) -> None:
    """GAP-3 UX Task 6.1：**啟動任務之前**擋下特徵數超量之分析請求。

    🔴 **本 Task 為過渡止血**：GAP-6 之分塊計算上線後由該機制取代，本函式屆時**一併刪除**
    （SPEC Task 6.1「存活至 GAP-6」）。不得留著空跑而成為永遠通過的假綠。

    🔴 **必須擋在 `ic_analysis_service.start_analysis` 之前**——Task 6.4 要證明
    「擋下時未載入大矩陣」，那個證明綁定「cap 檢查在任務建立之前」這個位置；
    檢查若被移到任務啟動之後，6.4 會量到已載入大矩陣之 footprint 而失去意義。

    🔴 解析不出特徵數 ⇒ **放行**（不擋）。理由是實查的：分析只有兩條路走得成——
      ①帶 `config_hash` ⇒ registry 一定查得到（查不到時 service 自己就 `raise run not found`）；
      ②呼叫端直接給 `features_path`（golden replay／artifact 重放）⇒ 那是已知該 run 的內部呼叫端。
      擋住第二條會弄壞 golden replay 這個既有消費端。
      **具名破口**：API 呼叫端硬塞 `features_path` 指向大 run 可繞過本閘；因本 Task 是過渡止血、
      且該路徑非使用者介面之路徑，接受之並具名記錄（見 `docs/GAP3UX_IMPL_HANDOFF.md` 殘留表）。

    🔴 **不提供「強制略過上限」之開關**（SPEC Task 6.1「不可做」）。
    """
    from momentum.factories import (
        feature_count_from_features_file,
        ic_report_reason,
        resolve_run_feature_count,
    )

    # 🔴 **兩個來源都要看，取最大值**（`CODEX-R1-P1-01`＋`GROK-R1-P1-01`，兩家一致）：
    #    只認 `config_hash` 時，呼叫端直接給 `features_path` 就能繞過；更糟的是
    #    「小 hash ＋ 實際大 `features_path`」可以**低報**。取 max 讓兩條路都守得住，
    #    且不必信任呼叫端宣稱的是哪一個。
    #    🔴 檔案側只讀 HDF5 header 之 shape，**不載入矩陣**（Task 6.4 之硬性要求）。
    candidates = [
        resolve_run_feature_count(
            config_hash=(request.config_hash or "").strip() or None,
            symbol=getattr(request, "symbol", None),
            timeframe=getattr(request, "timeframe", None),
        ),
        feature_count_from_features_file(getattr(request, "features_path", None)),
    ]
    known = [c for c in candidates if isinstance(c, int)]
    feature_count = max(known) if known else None
    if feature_count is None:
        return
    cap = int(settings.ic_analysis_max_features)
    if feature_count <= cap:
        return
    raise HTTPException(status_code=400, detail={
        # reason 字面由契約取得（Task 6.0）；本層**不得**硬寫
        "reason": ic_report_reason("analysis_rejected"),
        "message": (
            f"這個 run 有 {feature_count} 個特徵，超過目前上限 {cap}；"
            f"直接分析會把記憶體吃爆，因此在啟動任務之前就擋下來。"
            f"上限由實跑量測導出（見 handoffs/run_receipts/gap3ux-b9-footprint.receipt.json）；"
            f"請先縮減特徵數再分析。分塊計算上線後本限制會取消。"
        ),
        "feature_count": feature_count,
        "cap": cap,
    })


@router.post("/analyze", response_model=ICAnalyzeResponse)
async def start_ic_analysis(request: ICAnalyzeRequest):
    """Start IC analysis task."""
    # Task 6.1：**在呼叫 service 之前**，任務尚未建立
    _reject_when_over_feature_cap(request)
    try:
        return await ic_analysis_service.start_analysis(request)
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
    _reject_when_over_feature_cap(request)
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
    top_features = sorted(
        summary_table,
        key=lambda item: item.get("icir", float("-inf")),
        reverse=True,
    )[:5]

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
