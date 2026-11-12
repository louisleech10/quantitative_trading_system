"""Feature browser service.

特徵瀏覽器頁面已併入 Feature Factory，本 service 僅保留跨 Symbol Coverage
Matrix 計算（委派 CoverageAnalyzer，只讀 V2 特徵 run）。舊特徵檔載入器
（HDF5 檔、FeatureLibrary／Parquet 舊位址字串、CSV）生產零呼叫者，已隨 FRAMEPATH 刪除。

ICPERF Task 0.6 (h) ⑦／③（L1c）：三個計算改背景任務（`api.core.background_jobs`，NOCAP Task 5.3 共用元件）——
`submit_*` 於呼叫端執行緒做便宜之輸入驗證（< 2 個 Symbol ⇒ ValueError），建任務後於背景執行；分析器之 `on_step`
安全點回報進度並檢查取消。Group Feature 任務計算一次、保存完整排序結果快照（不截斷），結果端點自該快照切片分頁。
同步方法保留（舊預設之對照與相容）。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from api.core.background_jobs import BackgroundJobStore, JobContext
from api.core.config import settings
from api.core.logging import get_logger
from momentum.factories import create_coverage_analyzer


logger = get_logger("api.feature_browser_service")

#: 任務種類（紀錄之 kind）
KIND_COVERAGE_MATRIX = "coverage_matrix"
KIND_GROUP_COVERAGE = "group_coverage"
KIND_GROUP_FEATURE_COVERAGE = "group_feature_coverage"
#: 以 offset／limit 分頁之任務種類（結果含 total）
PAGED_KINDS = frozenset({KIND_GROUP_FEATURE_COVERAGE})


def _normalize_symbols(symbols: Optional[List[str]]) -> List[str]:
    normalized = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
    if len(normalized) < 2:
        raise ValueError("Coverage Matrix 需至少 2 個 Symbol")
    return normalized


def _step_hook(ctx: JobContext) -> Callable[[str, int, int], None]:
    """分析器安全點：先檢查取消（已請求 ⇒ JobCancelled 向上拋），再原子寫入進度。"""

    def hook(phase: str, processed: int, total: int) -> None:
        ctx.check_cancel()
        ctx.progress(phase, processed, total)

    return hook


def page_group_feature_result(result: Dict[str, Any], offset: int, limit: Optional[int]) -> Dict[str, Any]:
    """自完整結果快照切片：`features`／`matrix`／`divergence` 同取 [offset, offset+limit)；其餘欄不變；
    `limit`＝None ⇒ 取至結尾（全量匯出）。回傳附 `total`（截斷前特徵數）、`offset`、`limit`。"""
    features = list(result.get("features", []))
    total = len(features)
    end = total if limit is None else offset + limit
    window = features[offset:end]
    matrix = result.get("matrix", {})
    divergence = result.get("divergence", {})
    page = dict(result)
    page["features"] = window
    page["matrix"] = {name: matrix[name] for name in window if name in matrix}
    page["divergence"] = {name: divergence[name] for name in window if name in divergence}
    page["total"] = total
    page["offset"] = offset
    page["limit"] = total if limit is None else limit
    return page


class FeatureBrowserService:
    """Service layer for feature browser APIs（僅 Coverage Matrix；計算經背景任務）。"""

    def __init__(self, job_store: Optional[BackgroundJobStore] = None) -> None:
        self._coverage_analyzer = create_coverage_analyzer()
        self.job_store = job_store if job_store is not None else BackgroundJobStore(settings.feature_browser_jobs_dir)

    # ------------------------------------------------------------------ 同步計算（任務本體與相容對照）

    def get_coverage_matrix(
        self,
        symbols: List[str],
        timeframe: str,
        feature_names: Optional[List[str]] = None,
        feature_base_path: str = "data_cache/features",
        on_step: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        normalized_symbols = _normalize_symbols(symbols)
        normalized_features = [item.strip() for item in (feature_names or []) if item and item.strip()]
        kwargs: Dict[str, Any] = {}
        if on_step is not None:
            kwargs["on_step"] = on_step
        return self._coverage_analyzer.compute_symbol_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_names=normalized_features,
            feature_base_path=feature_base_path,
            **kwargs,
        )

    def get_group_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        feature_base_path: str = "data_cache/features",
        on_step: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        normalized_symbols = _normalize_symbols(symbols)
        kwargs: Dict[str, Any] = {}
        if on_step is not None:
            kwargs["on_step"] = on_step
        return self._coverage_analyzer.compute_group_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_base_path=feature_base_path,
            **kwargs,
        )

    def get_group_feature_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        group_name: str,
        feature_base_path: str = "data_cache/features",
        top_n: Optional[int] = 100,
        on_step: Optional[Callable[[str, int, int], None]] = None,
    ) -> Dict[str, Any]:
        """`top_n`＝None ⇒ 完整排序結果（任務路徑）；整數 ⇒ 前 top_n（同步相容路徑）。"""
        normalized_symbols = _normalize_symbols(symbols)
        kwargs: Dict[str, Any] = {}
        if on_step is not None:
            kwargs["on_step"] = on_step
        return self._coverage_analyzer.compute_group_feature_coverage(
            symbols=normalized_symbols,
            timeframe=timeframe,
            group_name=group_name,
            feature_base_path=feature_base_path,
            top_n=top_n,
            **kwargs,
        )

    # ------------------------------------------------------------------ 背景任務

    def _submit(self, kind: str, params: Dict[str, Any], compute: Callable[[JobContext], Dict[str, Any]],
                summarize: Callable[[Dict[str, Any]], Dict[str, Any]]) -> str:
        store = self.job_store
        job_id = store.create(kind, params)

        def run(ctx: JobContext) -> Dict[str, Any]:
            result = compute(ctx)
            ctx.set_summary(summarize(result))
            return result

        store.start(job_id, run)
        logger.info("Coverage 任務已建立：%s（%s）", job_id, kind)
        return job_id

    def submit_coverage_matrix(self, symbols: List[str], timeframe: str, feature_names: Optional[List[str]] = None,
                               feature_base_path: str = "data_cache/features") -> str:
        normalized_symbols = _normalize_symbols(symbols)
        params = {"symbols": normalized_symbols, "timeframe": timeframe, "feature_names": list(feature_names or []),
                  "feature_base_path": feature_base_path}
        return self._submit(
            KIND_COVERAGE_MATRIX, params,
            lambda ctx: self.get_coverage_matrix(normalized_symbols, timeframe, feature_names, feature_base_path,
                                                 on_step=_step_hook(ctx)),
            lambda result: {"features": len(result.get("features", [])), "symbols": len(result.get("symbols", [])),
                            **(result.get("summary") or {})},
        )

    def submit_group_coverage(self, symbols: List[str], timeframe: str,
                              feature_base_path: str = "data_cache/features") -> str:
        normalized_symbols = _normalize_symbols(symbols)
        params = {"symbols": normalized_symbols, "timeframe": timeframe, "feature_base_path": feature_base_path}
        return self._submit(
            KIND_GROUP_COVERAGE, params,
            lambda ctx: self.get_group_coverage(normalized_symbols, timeframe, feature_base_path, on_step=_step_hook(ctx)),
            lambda result: {"groups": len(result.get("groups", [])), "symbols": len(result.get("symbols", [])),
                            **(result.get("summary") or {})},
        )

    def submit_group_feature_coverage(self, symbols: List[str], timeframe: str, group_name: str,
                                      feature_base_path: str = "data_cache/features") -> str:
        normalized_symbols = _normalize_symbols(symbols)
        params = {"symbols": normalized_symbols, "timeframe": timeframe, "group_name": group_name,
                  "feature_base_path": feature_base_path}
        return self._submit(
            KIND_GROUP_FEATURE_COVERAGE, params,
            lambda ctx: self.get_group_feature_coverage(normalized_symbols, timeframe, group_name, feature_base_path,
                                                        top_n=None, on_step=_step_hook(ctx)),
            lambda result: {"total": len(result.get("features", [])), "symbols": len(result.get("symbols", [])),
                            "group_name": result.get("group_name")},
        )


feature_browser_service = FeatureBrowserService()
