'use client';

import { useEffect, useMemo, useRef } from 'react';
import { BatchTaskStatus, FeatureTask } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1/features';

interface GenerationProgressProps {
  task: FeatureTask | null;
  batchTask?: BatchTaskStatus | null;
  symbols?: string[];
  /** When true, renders without the outer glass-panel wrapper (for embedding inside another panel). */
  naked?: boolean;
}

export default function GenerationProgress({
  task,
  batchTask = null,
  symbols = [],
  naked = false,
}: GenerationProgressProps) {
  const { progress, setProgress, setCurrentTask } = useFeatureFactoryStore();
  const isBatchMode = Boolean(batchTask);

  // Stable refs so the useEffect closure always has the latest callbacks/task
  // without needing them in the dependency array (which would re-create the WS on every update).
  const setProgressRef = useRef(setProgress);
  const setCurrentTaskRef = useRef(setCurrentTask);
  const taskRef = useRef(task);
  useEffect(() => { setProgressRef.current = setProgress; }, [setProgress]);
  useEffect(() => { setCurrentTaskRef.current = setCurrentTask; }, [setCurrentTask]);
  useEffect(() => { taskRef.current = task; }, [task]);

  useEffect(() => {
    if (isBatchMode) return;

    const taskId = task?.task_id;
    if (!taskId) return;

    let destroyed = false;   // set to true in cleanup so stale onclose never starts a new poll
    let wsConnected = false;
    let pollIntervalId: ReturnType<typeof setInterval> | null = null;

    // Apply a progress/status payload coming from either WS or HTTP polling.
    const applyPayload = (payload: {
      stage?: string | null;
      progress?: number;
      message?: string;
      status?: string;
    }) => {
      const t = taskRef.current;
      if (!t) return;
      // Backend _notify_callbacks does NOT include a `status` field — derive it from `stage`.
      const derivedStatus =
        payload.stage === 'completed' || payload.status === 'completed' ? 'completed'
        : payload.stage === 'failed' || payload.status === 'failed' ? 'failed'
        : payload.status ?? 'running';

      setProgressRef.current({
        status: derivedStatus,
        stage: payload.stage ?? undefined,
        progress: payload.progress,
        message: payload.message,
      });
      setCurrentTaskRef.current({
        ...t,
        status: derivedStatus,
        progress: payload.progress ?? t.progress,
        current_stage: payload.stage ?? t.current_stage,
      });
    };

    const stopPolling = () => {
      if (pollIntervalId !== null) {
        clearInterval(pollIntervalId);
        pollIntervalId = null;
      }
    };

    // HTTP polling fallback — used when WebSocket fails to connect.
    const startPolling = () => {
      if (destroyed) return;         // guard: do NOT start after cleanup
      if (pollIntervalId !== null) return;
      pollIntervalId = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE_URL}${API_PREFIX}/task/${taskId}`);
          if (!res.ok) {
            if (res.status === 404) {
              // Task is gone (server restarted or task expired).
              // Clear the store so this component unmounts and never polls again.
              stopPolling();
              setCurrentTaskRef.current(null);
            }
            return;
          }
          const s = await res.json() as {
            status: string;
            progress: number;
            current_stage: string | null;
          };
          applyPayload({ stage: s.current_stage ?? s.status, progress: s.progress, status: s.status });
          if (s.status === 'completed' || s.status === 'failed') stopPolling();
        } catch {
          // Network error — keep retrying.
        }
      }, 2000);
    };

    const ws = new WebSocket(`${WS_BASE_URL}/ws/features/${taskId}`);

    ws.onopen = () => { wsConnected = true; };

    ws.onmessage = (event) => {
      try {
        // Backend wraps every message as: { event: "progress"|"ping"|"connected", data: {...}, timestamp: "..." }
        const message = JSON.parse(event.data as string) as Record<string, unknown>;
        if (message.event === 'ping' || message.event === 'connected') return;
        if (message.event === 'progress' && message.data && typeof message.data === 'object') {
          applyPayload(message.data as { stage?: string; progress?: number; message?: string });
        }
      } catch (err) {
        console.error('[GenerationProgress] Failed to parse WS message', err);
      }
    };

    ws.onerror = () => {
      if (!wsConnected && !destroyed) {
        console.warn('[GenerationProgress] WebSocket failed to connect, falling back to HTTP polling');
        startPolling();
      }
    };

    ws.onclose = () => {
      // Only fall back to polling if we never successfully connected AND this effect is still live.
      if (!wsConnected && !destroyed) startPolling();
    };

    return () => {
      destroyed = true;  // must be set BEFORE ws.close() so the onclose callback sees it
      ws.close();
      stopPolling();
    };
  }, [task?.task_id, isBatchMode]); // Only re-create WS when the task_id changes — NOT on every status update.

  const statusBySymbol = useMemo(() => {
    if (!batchTask) {
      return [] as Array<[string, 'pending' | 'running' | 'completed' | 'failed']>;
    }

    const map = new Map<string, 'pending' | 'running' | 'completed' | 'failed'>();

    symbols.forEach((symbol) => map.set(symbol, 'pending'));

    Object.keys(batchTask.results ?? {}).forEach((symbol) => {
      map.set(symbol, 'completed');
    });

    Object.keys(batchTask.errors ?? {}).forEach((symbol) => {
      if (symbol !== '__batch__') {
        map.set(symbol, 'failed');
      }
    });

    if (batchTask.current_symbol && map.get(batchTask.current_symbol) === 'pending') {
      map.set(batchTask.current_symbol, 'running');
    }

    return Array.from(map.entries());
  }, [batchTask, symbols]);

  if (!task && !batchTask) return null;

  if (batchTask) {
    const pct = Math.round((batchTask.progress ?? 0) * 100);
    const failedEntries = Object.entries(batchTask.errors ?? {}).filter(([symbol]) => symbol !== '__batch__');
    const isFailed = batchTask.status === 'failed';
    const isCompleted = batchTask.status === 'completed' || batchTask.status === 'partial';
    const pctColor = isFailed ? 'text-rose-300' : isCompleted ? 'text-emerald-300' : 'text-amber-200';
    const barColor = isFailed
      ? 'bg-rose-400/70'
      : 'bg-gradient-to-r from-amber-400/70 to-emerald-400/60';

    const inner = (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          {naked ? (
            <span className="text-sm text-slate-300">批次進度（{batchTask.status}）</span>
          ) : (
            <div>
              <div className="text-lg font-semibold text-slate-100">生成進度</div>
              <div className="text-xs text-slate-400">批次模式（{batchTask.status}）</div>
            </div>
          )}
          <span className={`${naked ? 'text-sm' : 'text-xl'} font-semibold ${pctColor}`}>{pct}%</span>
        </div>

        <div className="h-2 rounded-full bg-white/5 overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${barColor}`}
            style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
          />
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
          <div className="rounded-lg bg-white/5 p-2 text-slate-300">狀態：{batchTask.status}</div>
          <div className="rounded-lg bg-white/5 p-2 text-slate-300">總數：{batchTask.total}</div>
          <div className="rounded-lg bg-white/5 p-2 text-emerald-300">完成：{batchTask.completed}</div>
          <div className="rounded-lg bg-white/5 p-2 text-rose-300">失敗：{batchTask.failed}</div>
          <div className="rounded-lg bg-white/5 p-2 text-slate-300">目前：{batchTask.current_symbol ?? 'N/A'}</div>
        </div>

        {statusBySymbol.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-slate-400">逐標的狀態</div>
            <div className="max-h-44 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 grid grid-cols-1 md:grid-cols-2 gap-2">
              {statusBySymbol.map(([symbol, status]) => (
                <div key={symbol} className="flex items-center justify-between text-xs rounded-md bg-white/5 px-2 py-1">
                  <span className="text-slate-200">{symbol}</span>
                  <span
                    className={
                      status === 'completed'
                        ? 'text-emerald-300'
                        : status === 'failed'
                        ? 'text-rose-300'
                        : status === 'running'
                        ? 'text-amber-300'
                        : 'text-slate-400'
                    }
                  >
                    {status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {failedEntries.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-rose-300">失敗標的</div>
            <div className="max-h-40 overflow-auto rounded-xl border border-rose-400/30 bg-rose-500/10 p-3 space-y-2">
              {failedEntries.map(([symbol, message]) => (
                <div key={symbol} className="text-xs">
                  <div className="text-rose-200 font-medium">{symbol}</div>
                  <div className="text-rose-100/90">{message}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );

    if (naked) {
      return <div className="mt-6 pt-5 border-t border-white/10">{inner}</div>;
    }

    return <div className="glass-panel rounded-2xl p-6">{inner}</div>;
  }

  if (!task) return null;

  const pct = Math.round((progress?.progress ?? task.progress ?? 0) * 100);
  const stageLabel = progress?.stage ?? task.current_stage ?? '等待啟動';
  const stageMessage = progress?.message;
  const isFailed = task.status === 'failed';
  const isCompleted = task.status === 'completed';
  const pctColor = isFailed ? 'text-rose-300' : isCompleted ? 'text-emerald-300' : 'text-amber-200';
  const barColor = isFailed
    ? 'bg-rose-400/70'
    : 'bg-gradient-to-r from-amber-400/70 to-cyan-400/60';

  const inner = (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        {naked ? (
          <span className="text-sm text-slate-300">{stageLabel}</span>
        ) : (
          <div>
            <div className="text-lg font-semibold text-slate-100">生成進度</div>
            <div className="text-xs text-slate-400">{stageLabel}</div>
          </div>
        )}
        <span className={`${naked ? 'text-sm' : 'text-xl'} font-semibold ${pctColor}`}>
          {pct}%
        </span>
      </div>

      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="text-xs text-slate-400">
        {stageMessage ?? (isCompleted ? '生成完成' : isFailed ? '生成失敗' : '等待進度更新...')}
      </div>
    </div>
  );

  if (naked) {
    return <div className="mt-6 pt-5 border-t border-white/10">{inner}</div>;
  }

  return (
    <div className="glass-panel rounded-2xl p-6">
      {inner}
    </div>
  );
}
