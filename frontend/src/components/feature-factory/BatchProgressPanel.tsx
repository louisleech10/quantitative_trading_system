'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Clock, Download, RotateCcw, Wifi, WifiOff } from 'lucide-react';
import { BatchTaskStatus, BatchTaskStatusValue } from '@/lib/types';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';

const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const RECONNECT_DELAY_MS = 5000;
const MAX_RECONNECT_ATTEMPTS = 3;

type SymbolStatus = 'pending' | 'running' | 'completed' | 'failed';

interface BatchProgressPanelProps {
  batchTask: BatchTaskStatus | null;
  symbols?: string[];
  naked?: boolean;
}

function isTerminalStatus(status: BatchTaskStatusValue): boolean {
  return ['completed', 'failed', 'partial'].includes(status);
}

function formatDuration(seconds?: number): string {
  if (!seconds || seconds <= 0) {
    return '估算中';
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainingSeconds = seconds % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  return `${remainingSeconds}s`;
}

function getStatusLabel(status: SymbolStatus): string {
  switch (status) {
    case 'completed':
      return 'completed';
    case 'failed':
      return 'failed';
    case 'running':
      return 'running';
    default:
      return 'pending';
  }
}

export default function BatchProgressPanel({ batchTask, symbols = [], naked = false }: BatchProgressPanelProps) {
  const {
    batchTask: storeBatchTask,
    applyBatchEvent,
    batchConnectionStatus,
    batchConnectionMessage,
    setBatchConnectionState,
    resumeBatch,
  } = useFeatureFactoryStore();
  const effectiveBatchTask = batchTask ?? storeBatchTask;
  const taskId = effectiveBatchTask?.task_id ?? effectiveBatchTask?.batch_id ?? null;
  const batchStatus = effectiveBatchTask?.status;
  const retryCountRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [isResuming, setIsResuming] = useState(false);

  useEffect(() => {
    if (!taskId || !batchStatus || isTerminalStatus(batchStatus)) {
      return undefined;
    }

    let socket: WebSocket | null = null;
    let closedByCleanup = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const connect = () => {
      clearReconnectTimer();
      const connectionState = retryCountRef.current > 0 ? 'reconnecting' : 'connecting';
      const retryMessage = retryCountRef.current > 0
        ? `WebSocket 斷線，5 秒後重連 (${retryCountRef.current}/${MAX_RECONNECT_ATTEMPTS})`
        : null;
      setBatchConnectionState(connectionState, retryMessage);
      socket = new WebSocket(`${WS_BASE_URL}/ws/features/batch/${encodeURIComponent(taskId)}`);

      socket.onopen = () => {
        retryCountRef.current = 0;
        setBatchConnectionState('connected', null);
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string) as Record<string, unknown>;
          if (message.event === 'ping') {
            socket?.send('ping');
            return;
          }
          const payload = message.event === 'batch_progress' && message.data && typeof message.data === 'object'
            ? message.data as Record<string, unknown>
            : message;
          applyBatchEvent(payload as Partial<BatchTaskStatus> & Record<string, unknown>);
        } catch (err) {
          console.error('[BatchProgressPanel] Failed to parse batch WebSocket message', err);
        }
      };

      socket.onerror = () => {
        socket?.close();
      };

      socket.onclose = () => {
        if (closedByCleanup) return;
        if (retryCountRef.current < MAX_RECONNECT_ATTEMPTS) {
          retryCountRef.current += 1;
          setBatchConnectionState(
            'reconnecting',
            `WebSocket 斷線，5 秒後重連 (${retryCountRef.current}/${MAX_RECONNECT_ATTEMPTS})`
          );
          reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
          return;
        }
        setBatchConnectionState('lost', 'Connection lost, please refresh');
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      clearReconnectTimer();
      socket?.close();
    };
  }, [applyBatchEvent, batchStatus, setBatchConnectionState, taskId]);

  const statusBySymbol = useMemo(() => {
    const map = new Map<string, SymbolStatus>();

    symbols.forEach((symbol) => map.set(symbol, 'pending'));

    Object.keys(effectiveBatchTask?.results ?? {}).forEach((symbol) => {
      map.set(symbol, 'completed');
    });

    Object.keys(effectiveBatchTask?.errors ?? {}).forEach((symbol) => {
      if (symbol !== '__batch__') {
        map.set(symbol, 'failed');
      }
    });

    if (effectiveBatchTask?.current_symbol && map.get(effectiveBatchTask.current_symbol) === 'pending') {
      map.set(effectiveBatchTask.current_symbol, 'running');
    }

    return Array.from(map.entries());
  }, [effectiveBatchTask, symbols]);

  const handleResume = async () => {
    if (!taskId) return;
    setIsResuming(true);
    try {
      await resumeBatch(taskId);
    } finally {
      setIsResuming(false);
    }
  };

  if (!effectiveBatchTask) {
    return (
      <div className={`${naked ? '' : 'glass-panel rounded-2xl'} p-6 border border-white/10 text-sm text-slate-400`}>
        尚未啟動批次任務。
      </div>
    );
  }

  const pct = Math.round((effectiveBatchTask.progress ?? 0) * 100);
  const failedEntries = Object.entries(effectiveBatchTask.errors ?? {}).filter(([symbol]) => symbol !== '__batch__');
  const outputPaths = effectiveBatchTask.output_paths ?? [];
  const perItemRss = effectiveBatchTask.per_item_rss ?? [];
  const canResume = Boolean(effectiveBatchTask.resume_available || effectiveBatchTask.status === 'failed');
  const currentItem = effectiveBatchTask.current_symbol
    ? `${effectiveBatchTask.current_symbol}${effectiveBatchTask.current_timeframe ? ` / ${effectiveBatchTask.current_timeframe}` : ''}`
    : 'N/A';
  const connectionIcon = batchConnectionStatus === 'connected'
    ? <Wifi className="w-4 h-4" aria-hidden="true" />
    : <WifiOff className="w-4 h-4" aria-hidden="true" />;
  const wrapperClassName = naked
    ? 'space-y-4'
    : 'glass-panel rounded-2xl p-6 space-y-4 border border-white/10';

  return (
    <div className={wrapperClassName} data-testid="batch-progress-panel">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold text-slate-100">批次進度</div>
          <div className="text-xs text-slate-400">Task: {effectiveBatchTask.task_id}</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-300">
            {connectionIcon}
            <span>{batchConnectionStatus}</span>
          </div>
          <div className="text-xl font-semibold text-amber-200">{pct}%</div>
        </div>
      </div>

      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-amber-400/70 to-emerald-400/60 transition-all duration-300"
          style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 text-xs">
        <div className="rounded-lg bg-white/5 p-2 text-slate-300">狀態：{effectiveBatchTask.status}</div>
        <div className="rounded-lg bg-white/5 p-2 text-slate-300">總數：{effectiveBatchTask.total}</div>
        <div className="rounded-lg bg-white/5 p-2 text-emerald-300">完成：{effectiveBatchTask.completed}</div>
        <div className="rounded-lg bg-white/5 p-2 text-rose-300">失敗：{effectiveBatchTask.failed}</div>
        <div className="rounded-lg bg-white/5 p-2 text-slate-300">目前：{currentItem}</div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs">
        <div className="rounded-lg bg-white/5 p-2 text-slate-300 flex items-center gap-2">
          <Clock className="w-4 h-4 text-amber-300" aria-hidden="true" />
          <span>ETA：{formatDuration(effectiveBatchTask.eta_seconds)}</span>
        </div>
        <div className="rounded-lg bg-white/5 p-2 text-slate-300">
          佇列：{effectiveBatchTask.queued ?? Math.max(effectiveBatchTask.total - effectiveBatchTask.completed - effectiveBatchTask.failed, 0)}
        </div>
        <div className="rounded-lg bg-white/5 p-2 text-slate-300">
          平行 symbol：{effectiveBatchTask.concurrent_symbols ?? 1}
        </div>
      </div>

      {batchConnectionMessage && (
        <div className="rounded-xl border border-amber-300/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-100 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{batchConnectionMessage}</span>
        </div>
      )}

      {effectiveBatchTask.memory_sanity_failed && (
        <div className="rounded-xl border border-amber-300/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-100">
          記憶體回收 sanity gate 觸發，後續 symbol 已降載執行。
        </div>
      )}

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-400">逐標的狀態</div>
        <div className="max-h-52 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 grid grid-cols-1 md:grid-cols-2 gap-2">
          {statusBySymbol.map(([symbol, status]) => (
            <div key={symbol} className="rounded-md bg-white/5 px-2 py-1">
              <div className="flex items-center justify-between text-xs">
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
                  {getStatusLabel(status)}
                </span>
              </div>
              {status === 'running'
                && symbol === effectiveBatchTask.current_symbol
                && effectiveBatchTask.current_stage && (
                <div className="mt-1 text-[11px] text-slate-400" data-testid={`layer-status-${symbol}`}>
                  {effectiveBatchTask.current_stage}
                  {effectiveBatchTask.stage_progress != null
                    ? ` (${Math.round(effectiveBatchTask.stage_progress * 100)}%)`
                    : ''}
                  {effectiveBatchTask.current_rss_mb != null
                    ? ` · RSS ${effectiveBatchTask.current_rss_mb}MB`
                    : ''}
                </div>
              )}
            </div>
          ))}
          {statusBySymbol.length === 0 && (
            <div className="text-xs text-slate-400">尚無逐標的狀態資料</div>
          )}
        </div>
      </div>

      {outputPaths.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Per-Symbol Output</div>
          <div className="max-h-48 overflow-auto rounded-xl border border-emerald-400/20 bg-emerald-500/10 p-3 space-y-2">
            {outputPaths.map((item) => (
              <div key={`${item.symbol}:${item.timeframe}:${item.path}`} className="grid grid-cols-[120px_1fr] gap-2 text-xs">
                <div className="text-emerald-200 font-medium">
                  {item.symbol}{item.timeframe ? ` / ${item.timeframe}` : ''}
                </div>
                <a
                  href={item.download_url ?? item.path}
                  className="inline-flex items-center gap-1 text-emerald-100/90 hover:text-emerald-50 break-all"
                >
                  <Download className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span>{item.path}</span>
                </a>
              </div>
            ))}
          </div>
        </div>
      )}

      {perItemRss.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-[0.2em] text-slate-400">RSS 回收摘要</div>
          <div className="max-h-36 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 grid grid-cols-1 md:grid-cols-2 gap-2">
            {perItemRss.map((item) => (
              <div key={`${item.symbol}:${item.timeframe}`} className="text-xs rounded-md bg-white/5 px-2 py-1 text-slate-300">
                {item.symbol} {item.timeframe}：Peak {item.rssPeakMB}MB / GC 後 {item.rssAfterGcMB}MB
              </div>
            ))}
          </div>
        </div>
      )}

      {failedEntries.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs uppercase tracking-[0.2em] text-rose-300">失敗標的</div>
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

      {canResume && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleResume}
            disabled={isResuming}
            className="inline-flex items-center gap-2 rounded-lg border border-amber-300/30 bg-amber-400/15 px-3 py-2 text-sm text-amber-100 hover:bg-amber-400/25 disabled:opacity-50"
          >
            <RotateCcw className={`w-4 h-4 ${isResuming ? 'animate-spin' : ''}`} aria-hidden="true" />
            {isResuming ? 'Resuming...' : 'Resume Batch'}
          </button>
        </div>
      )}
    </div>
  );
}
