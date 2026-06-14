'use client';

import { useEffect, useRef } from 'react';
import { BatchTaskStatus, FeatureTask } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import BatchProgressPanel from './BatchProgressPanel';

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
  const { progress, setProgress, setCurrentTask, enqueueCompletion } = useFeatureFactoryStore();
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
      retention_prompt?: boolean;
      run_identity?: { symbol: string; timeframe: string; config_hash: string };
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
        retention_prompt: payload.retention_prompt,
        run_identity: payload.run_identity,
      });
      if (derivedStatus === 'completed' && payload.retention_prompt && payload.run_identity) {
        enqueueCompletion(payload.run_identity);
      }
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
            retention_prompt?: boolean;
            run_identity?: { symbol: string; timeframe: string; config_hash: string };
          };
          applyPayload({ stage: s.current_stage ?? s.status, progress: s.progress, status: s.status,
            retention_prompt: s.retention_prompt, run_identity: s.run_identity });
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

  if (!task && !batchTask) return null;

  if (batchTask) {
    if (naked) {
      return (
        <div className="mt-6 pt-5 border-t border-white/10">
          <BatchProgressPanel batchTask={batchTask} symbols={symbols} naked />
        </div>
      );
    }

    return <BatchProgressPanel batchTask={batchTask} symbols={symbols} />;
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
