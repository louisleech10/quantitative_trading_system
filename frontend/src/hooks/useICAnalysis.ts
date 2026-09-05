import { useCallback, useEffect, useRef } from 'react';
import {
  DeepAnalysisConfig,
  DeepAnalysisResponse,
  FeatureListItem,
  ICAnalysisConfig,
  ICEventScanDisclosure,
  ICReport,
} from '@/lib/types';
import { useICAnalysisStore } from '@/store/icAnalysisStore';
import { httpErrorMessage } from '@/lib/httpError';
import { isSubmittableLabelSpec } from '@/lib/eventDimensions';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const API_PREFIX = '/api/v1/ic';

const requestJson = async <T>(path: string, options?: RequestInit): Promise<T> => {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(httpErrorMessage(payload, response.statusText));
  }

  return response.json();
};

const buildConfigOverride = (config: ICAnalysisConfig) => {
  const thresholds: Record<string, number> = {
    ic_mean_min: config.thresholds.ic_mean_min,
    icir_min: config.thresholds.icir_min,
    p_value_max: config.thresholds.p_value_max,
  };

  if (typeof config.thresholds.monotonicity_score_min === 'number') {
    thresholds.monotonicity_score_min = config.thresholds.monotonicity_score_min;
  }

  return {
    thresholds,
    redundancy: {
      correlation_threshold: config.thresholds.correlation_threshold,
    },
    labels: {
      horizons: config.horizons,
    },
  };
};

const buildRefilterPayload = (thresholds: ICAnalysisConfig['thresholds']) => ({
  ic_mean_min: thresholds.ic_mean_min,
  icir_min: thresholds.icir_min,
  p_value_max: thresholds.p_value_max,
  monotonicity_score_min: thresholds.monotonicity_score_min,
  correlation_threshold: thresholds.correlation_threshold,
});

export function useICAnalysis() {
  const {
    setTask,
    setProgress,
    setFeatureCount,
    setEventScanDisclosure,
    setStatus,
    setError,
    setReport,
  } = useICAnalysisStore();

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);
  const terminalRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  const fetchResult = useCallback(
    async (taskId: string) => {
      const result = await requestJson<ICReport>(`/result/${taskId}`);
      setReport(result);
      return result;
    },
    [setReport]
  );

  /**
   * 🔴 R1 三家全員之 P1 修法（其一）：把 **WS progress 事件**帶的掃描格數併進揭露欄。
   *
   * **併入不覆蓋**：`scan_results` 要等終態才有，這裡只更新 `scan_done`／`scan_total`
   * ⇒ 掃描進行中畫面就能顯示「第幾格／共幾格」，而不是等到最後才一次跳出來。
   * 尚無 disclosure 物件時（非事件分析或還沒拿到 `/task`）建一個**只有掃描進度**的骨架，
   * 其餘欄位維持 `null`——**不猜**任何上界。
   */
  const mergeScanProgress = useCallback((done: number | null, total: number) => {
    const prev = useICAnalysisStore.getState().eventScanDisclosure;
    const prevScan = prev?.event_label_scan ?? null;
    setEventScanDisclosure({
      ...(prev ?? {}),
      event_label_scan: {
        scan_total: total,
        scan_done: done ?? prevScan?.scan_done ?? 0,
        scan_results: prevScan?.scan_results ?? [],
        capability: prevScan?.capability ?? 'available',
        reason: prevScan?.reason ?? null,
        message: prevScan?.message ?? null,
      },
    });
  }, [setEventScanDisclosure]);

  const fetchTaskStatus = useCallback(
    async (taskId: string) => {
      const status = await requestJson<{
        task_id: string;
        status: string;
        progress: number;
        current_stage?: string | null;
        error?: string | null;
        feature_count?: number | null;   // GAP-3 UX Task 6.3
        // `G3-D2` D4.2／D4.3：事件分析之揭露欄（非事件路徑一律缺席）
        decision_offset_bars_capability?: string | null;
        decision_offset_bars_reason?: string | null;
        decision_offset_bars_record_values?: number[] | null;
        decision_offset_bars_analysis?: number | null;
        decision_offset_bars_scan_max?: number | null;
        bounds_scope_symbol?: string | null;
        bounds_scope_excluded_events?: number | null;
        k_max_feasible_at_h?: number | null;
        h_max_feasible_at_k?: number | null;
        k_bound_status?: string | null;
        h_bound_status?: string | null;
        event_label_scan?: ICEventScanDisclosure['event_label_scan'];
      }>(`/task/${taskId}`);
      setStatus(status.status as 'pending' | 'running' | 'completed' | 'failed');
      setProgress(status.progress ?? 0, status.current_stage ?? null);
      // Task 6.3：解析不到就是 null，**不填假值**
      setFeatureCount(typeof status.feature_count === "number" ? status.feature_count : null);
      // 🔴 `G3-D2` D4.2／D4.3：揭露欄**整組**由後端來；任一欄都不在前端補值。
      //    非事件分析路徑（後端不放這些鍵）⇒ 整個物件為 `null`，面板顯示「要分析過才知道」。
      setEventScanDisclosure(
        status.decision_offset_bars_capability === undefined
          && status.k_bound_status === undefined
          && status.event_label_scan === undefined
          ? null
          : {
            decision_offset_bars_capability: status.decision_offset_bars_capability ?? null,
            decision_offset_bars_reason: status.decision_offset_bars_reason ?? null,
            decision_offset_bars_record_values: status.decision_offset_bars_record_values ?? null,
            decision_offset_bars_analysis: status.decision_offset_bars_analysis ?? null,
            decision_offset_bars_scan_max: status.decision_offset_bars_scan_max ?? null,
            bounds_scope_symbol: status.bounds_scope_symbol ?? null,
            bounds_scope_excluded_events: status.bounds_scope_excluded_events ?? null,
            k_max_feasible_at_h: status.k_max_feasible_at_h ?? null,
            h_max_feasible_at_k: status.h_max_feasible_at_k ?? null,
            k_bound_status: status.k_bound_status ?? null,
            h_bound_status: status.h_bound_status ?? null,
            event_label_scan: status.event_label_scan ?? null,
          },
      );

      if (status.status === 'failed') {
        terminalRef.current = true;
        clearTimers();
        setError(status.error || 'IC analysis failed');
      } else if (status.status === 'completed') {
        terminalRef.current = true;
        clearTimers();
        await fetchResult(taskId);
      }

      return status;
    },
    [clearTimers, fetchResult, setError, setProgress, setStatus, setFeatureCount, setEventScanDisclosure]
  );

  const startPolling = useCallback(
    (taskId: string) => {
      if (pollIntervalRef.current || terminalRef.current) {
        return;
      }
      setError(null);
      pollIntervalRef.current = setInterval(() => {
        void fetchTaskStatus(taskId).catch((err) => {
          setError(err instanceof Error ? err.message : 'IC analysis polling failed');
        });
      }, 2000);
    },
    [fetchTaskStatus, setError]
  );

  const connectProgress = useCallback((taskId: string) => {
    if (!taskId) {
      return;
    }

    terminalRef.current = false;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE_URL}/ws/ic-analysis/${taskId}`);

    // 🔴 UAT B15（2026-09-02，G3-D11）：任務可能在訂閱前就已 failed／completed（例如 coverage 閘在幾十毫秒內拒），
    //    那筆通知不會再來；連上時**先拉一次現況**，終態直接收斂，不再永遠顯示「執行中」。
    //    後端 WS 連上時也會補推終態快照——兩端各守一次，任一端漏了都不會卡死。
    ws.onopen = () => {
      void fetchTaskStatus(taskId)
        .then((s) => {
          if (s.status === 'failed' || s.status === 'completed') ws.close();
        })
        .catch(() => { /* 交給 WS 訊息／輪詢；不在此喊通用錯誤 */ });
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message?.event === 'progress' && message?.data) {
          const payload = message.data;
          // 收到有效進度 = 連線健康，清掉先前的 transient「連線失敗」誤報
          if (payload.status !== 'failed') {
            setError(null);
          }
          setProgress(payload.progress ?? 0, payload.stage ?? payload.current_stage ?? null);
          if (payload.status) {
            setStatus(payload.status);
          }
          // 🔴 **R1 三家全員之 P1**（`CODEX-R1-P1-02`／`COMPOSER-R1-P1-01`／`GROK-R1-P1-01`）：
          //    WS 是**生產預設通道**，輪詢只在重連失敗 ≥3 次後才啟動 ⇒ 快樂路徑上
          //    `eventScanDisclosure` 永遠停在 WS open 那一刻的值，掃描矩陣與兩上界對使用者不可達。
          //    這與 `7904c0dd` 要修的「幽靈功能」同病，只是層次從「props 沒傳」移到「store 沒刷新」。
          //    ⇒ (a) 掃描進度逐格併進 store；(b) 終態改走 `fetchTaskStatus`（它會 hydrate
          //    整組揭露欄，並在 completed 時自行 `fetchResult`）。
          if (typeof payload.scan_total === 'number') {
            mergeScanProgress(payload.scan_done ?? null, payload.scan_total);
          }
          if (payload.status === 'failed') {
            terminalRef.current = true;
            clearTimers();
            setError(payload.message || payload.error || 'IC analysis failed');
            // 失敗任務不得留著上一次的上界／矩陣（`CODEX-R1-P2-03`）。
            setEventScanDisclosure(null);
            ws.close();
            return;
          }
          if (payload.status === 'completed') {
            terminalRef.current = true;
            clearTimers();
            // 🔴 **不是** `fetchResult`：那支只設 report、不碰揭露欄。
            //    `fetchTaskStatus` 於 completed 分支會自行呼叫 `fetchResult`，故不重複。
            void fetchTaskStatus(taskId).catch(() => { void fetchResult(taskId); });
            ws.close();
            return;
          }
          return;
        }

        if (message?.event === 'ping') {
          ws.send(JSON.stringify({ type: 'pong' }));
          return;
        }
      } catch (err) {
        console.error('[useICAnalysis] Failed to parse message', err);
      }
    };

    ws.onerror = () => {
      // 不在 transient onerror 喊通用「連線失敗」(會誤報且不清除)。
      // 交給 onclose retry(≤3)→ poll fallback;真失敗由 poll/status.error 顯真錯誤(U-2)。
    };

    ws.onclose = () => {
      if (terminalRef.current) {
        return;
      }

      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }

      if (retryCountRef.current >= 3) {
        startPolling(taskId);
        return;
      }

      retryCountRef.current += 1;
      reconnectTimerRef.current = setTimeout(() => {
        connectProgress(taskId);
      }, 3000);
    };

    wsRef.current = ws;
  }, [clearTimers, fetchResult, fetchTaskStatus, mergeScanProgress, setError, setEventScanDisclosure, setProgress, setStatus, startPolling]);

  const startAnalysis = useCallback(
    async (config: ICAnalysisConfig) => {
      const hasLibrarySelection = Boolean(
        config.symbol && config.timeframe && config.config_hash
      );
      const hasCrossSectionSelection = Boolean(
        config.mode === 'cross_sectional' &&
        config.timeframe &&
        (config.cross_sectional_runs?.length || 0) >= 2
      );

      if (!hasLibrarySelection && !hasCrossSectionSelection) {
        throw new Error('請選擇 Run 或橫截面批次');
      }

      // 🔴 `G3-D2` D1.7 送出守衛：事件批路徑之 `event_label_spec` 若不是三個報酬量法之一，
      //    **在此擋下、不發 fetch**。理由：矩陣外組合送到後端只會拿到 fail-closed 錯誤，
      //    使用者看到的是「分析被拒絕」而不知道是量法設定的問題。
      //    ⚠️ 只在**明確給了** spec 時檢查：沒給時由後端依宣告深度導出預設（D1.7 後端半邊）。
      if (config.mode === 'event' && config.event_import_id && config.event_label_spec
          && !isSubmittableLabelSpec(config.event_label_spec)) {
        throw new Error(
          '報酬量法不是可分析的組合——請在分析參數區重選「當根／續漲／持有」其中一種',
        );
      }

      const effectiveConfig = useICAnalysisStore.getState().getEffectiveConfig();
      const featureFilter = useICAnalysisStore.getState().featureFilter;
      const isCrossSectionalMode = config.mode === 'cross_sectional';

      const normalizedFeatureFilter = {
        include_features:
          featureFilter.include_features && featureFilter.include_features.length > 0
            ? featureFilter.include_features
            : undefined,
        exclude_features:
          featureFilter.exclude_features && featureFilter.exclude_features.length > 0
            ? featureFilter.exclude_features
            : undefined,
        include_pattern: featureFilter.include_pattern?.trim() || undefined,
        include_categories:
          featureFilter.include_categories && featureFilter.include_categories.length > 0
            ? featureFilter.include_categories
            : undefined,
        include_data_sources:
          featureFilter.include_data_sources && featureFilter.include_data_sources.length > 0
            ? featureFilter.include_data_sources
            : undefined,
        include_families:
          featureFilter.include_families && featureFilter.include_families.length > 0
            ? featureFilter.include_families
            : undefined,
        max_features:
          typeof featureFilter.max_features === 'number' && featureFilter.max_features > 0
            ? featureFilter.max_features
            : undefined,
      };

      const hasFeatureFilter = Object.values(normalizedFeatureFilter).some((value) => value !== undefined);

      const payload = {
        mode: isCrossSectionalMode ? 'cross_sectional' : 'longitudinal',
        symbol: isCrossSectionalMode ? undefined : config.symbol || undefined,
        symbols: isCrossSectionalMode ? config.cross_sectional_symbols || [] : undefined,
        cross_sectional_runs: isCrossSectionalMode ? config.cross_sectional_runs || [] : undefined,
        timeframe: config.timeframe || undefined,
        config_hash: isCrossSectionalMode ? undefined : config.config_hash || undefined,
        config_override: {
          ...buildConfigOverride(config),
          ...(effectiveConfig.feature_tiers ? { feature_tiers: effectiveConfig.feature_tiers } : {}),
        },
        feature_tiers: effectiveConfig.feature_tiers,
        feature_filter: hasFeatureFilter ? normalizedFeatureFilter : undefined,
        event_query: config.mode === 'event' ? config.event_query?.trim() || undefined : undefined,
        // ── GAP-3 UX Task 7.0b ③：選了事件批 ⇒ 送 `event_import_id` ＋ `event_label_spec` ──
        // 🔴 **此時不得再送 `event_timestamps`**：後端定死兩者互斥（同時給 ⇒ 422），
        //    因為兩者都在說「要分析哪些事件」，同時給就有兩個真相源。
        // 🔴 前端**不再自算時間戳**（Task 7.7 ⑦）：映射改由後端依 receipt 之
        //    `decision_at_ms` 產生。原本前端用的是**原始 t0**，`k > 0` 時會把特徵取樣點
        //    推到決策時點之後。
        ...(config.mode === 'event' && config.event_import_id
          ? {
              event_import_id: config.event_import_id,
              // 🔴 **前端不再送任何預設 spec**（`CODEX-R2-P1-03`，B-D1 R2 實跑命中）。
              //    原版在使用者沒設定時明送 `{ horizon_bars: 1 }`；後端 D1.7 用 `setdefault`
              //    依宣告深度導出預設，而 `setdefault` **壓不過已存在的鍵**
              //    ⇒ 宣告深度 3 的批，「持有」實際跑成 h=1，且值合法、沒有測試會紅。
              //    這就是「兩端都有、但沒接上」——後端邏輯正確卻**不可達**。
              //    ⇒ 使用者未設定時**整個鍵省略**，由後端導出；有設定才照送。
              //    （`horizon_bars` 仍**禁**以匯出檔之 `label_definition.window.horizon_bars`
              //     種子化——那欄語意是 D-7 深度宣告，分析層讀成答案窗即靜默給錯值。）
              ...(config.event_label_spec ? { event_label_spec: config.event_label_spec } : {}),
              // 🔴 `G3-D2` D4.3：掃描網格是**請求頂層 sibling**（不在 spec 內）。
              //    未掃描 ⇒ 整個鍵省略——送 `{}` 在後端仍代表「有掃描」（`is not None`），
              //    會讓「沒開掃描」變成「掃一個一格的網格」。
              ...(config.event_label_scan ? { event_label_scan: config.event_label_scan } : {}),
            }
          : {
              // legacy 非事件批路徑（例如只用 `event_query` 篩）行為不變。
              event_timestamps:
                config.mode === 'event' && config.event_timestamps && config.event_timestamps.length > 0
                  ? config.event_timestamps
                  : undefined,
            }),
      };

      const result = await requestJson<{ task_id: string; status: string }>('/analyze', {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      // 🔴 `COMPOSER-R1-P2-01`：新任務啟動即清掉上一次的揭露欄——否則第二次分析在
      //    首次 /task 回應之前，面板會拿**上一批**的上界與掃描矩陣當成這一批的。
      setEventScanDisclosure(null);
      setTask(result.task_id, result.status === "running" ? "running" : "pending");
      setStatus(result.status === 'running' ? 'running' : 'pending');
      retryCountRef.current = 0;
      connectProgress(result.task_id);

      return result.task_id;
    },
    [connectProgress, setStatus, setTask]
  );

  const fetchSummary = useCallback(async (taskId: string) => {
    const data = await requestJson<{ task_id: string; summary: string }>(`/summary/${taskId}`);
    return data.summary;
  }, []);

  const fetchAvailableFeatures = useCallback(
    async (symbol: string, timeframe: string, configHash: string) => {
      const params = new URLSearchParams({
        symbol,
        timeframe,
        config_hash: configHash,
      });
      const data = await requestJson<{ total: number; features: FeatureListItem[] }>(
        `/features/list?${params.toString()}`
      );
      return data.features;
    },
    []
  );

  const startDeepAnalysis = useCallback(
    async (taskId: string, config: DeepAnalysisConfig) => {
      // request 欄名 net_ic;模組鍵 net_ic_analysis — service 負責映射
      const payload = {
        selected_features: config.selected_features,
        top_n: config.top_n ?? 30,
        modules: config.modules,
        config_override: config.config_override,
        net_ic: config.net_ic ?? { cost_enabled: false, cost_bps: null },
      };
      const result = await requestJson<{ task_id: string; status: string }>(`/deep-analysis/${taskId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });

      // 🔴 `COMPOSER-R1-P2-01`：新任務啟動即清掉上一次的揭露欄——否則第二次分析在
      //    首次 /task 回應之前，面板會拿**上一批**的上界與掃描矩陣當成這一批的。
      setEventScanDisclosure(null);
      setTask(result.task_id, result.status === "running" ? "running" : "pending");
      setStatus(result.status === 'running' ? 'running' : 'pending');
      retryCountRef.current = 0;
      connectProgress(result.task_id);

      return result.task_id;
    },
    [connectProgress, setStatus, setTask]
  );

  const fetchDeepAnalysisResult = useCallback(async (taskId: string) => {
    return requestJson<DeepAnalysisResponse>(`/deep-analysis/${taskId}/result`);
  }, []);

  const refilter = useCallback(
    async (taskId: string, thresholds: ICAnalysisConfig['thresholds']) => {
      const result = await requestJson<ICReport>(`/refilter?task_id=${taskId}`, {
        method: 'POST',
        body: JSON.stringify({ thresholds: buildRefilterPayload(thresholds) }),
      });
      setReport(result);
      return result;
    },
    [setReport]
  );

  const applyTransforms = useCallback(
    async (
      taskId: string,
      payload: {
        selected_features: string[];
        rank: boolean;
        zscore: boolean;
        gaussian: boolean;
        rank_window?: number;
        zscore_windows?: number[];
      }
    ) => {
      return requestJson<{
        task_id: string;
        selected_feature_count: number;
        transforms_applied: string[];
        output_path: string;
        output_rows: number;
        output_cols: number;
      }>(`/apply-transforms/${taskId}`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
    },
    []
  );

  useEffect(() => {
    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
      }
    };
  }, []);

  return {
    startAnalysis,
    fetchTaskStatus,
    fetchResult,
    fetchSummary,
    fetchAvailableFeatures,
    startDeepAnalysis,
    fetchDeepAnalysisResult,
    refilter,
    applyTransforms,
    connectProgress,
  };
}
