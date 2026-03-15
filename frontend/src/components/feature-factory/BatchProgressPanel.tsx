'use client';

import { useMemo } from 'react';
import { BatchTaskStatus } from '@/lib/types';

interface BatchProgressPanelProps {
  batchTask: BatchTaskStatus | null;
  symbols?: string[];
}

export default function BatchProgressPanel({ batchTask, symbols = [] }: BatchProgressPanelProps) {
  const statusBySymbol = useMemo(() => {
    const map = new Map<string, 'pending' | 'running' | 'completed' | 'failed'>();

    symbols.forEach((symbol) => map.set(symbol, 'pending'));

    Object.keys(batchTask?.results ?? {}).forEach((symbol) => {
      map.set(symbol, 'completed');
    });

    Object.keys(batchTask?.errors ?? {}).forEach((symbol) => {
      if (symbol !== '__batch__') {
        map.set(symbol, 'failed');
      }
    });

    if (batchTask?.current_symbol && map.get(batchTask.current_symbol) === 'pending') {
      map.set(batchTask.current_symbol, 'running');
    }

    return Array.from(map.entries());
  }, [batchTask, symbols]);

  if (!batchTask) {
    return (
      <div className="glass-panel rounded-2xl p-6 border border-white/10 text-sm text-slate-400">
        尚未啟動批次任務
      </div>
    );
  }

  const pct = Math.round(batchTask.progress * 100);
  const failedEntries = Object.entries(batchTask.errors ?? {}).filter(([symbol]) => symbol !== '__batch__');

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4 border border-white/10">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold text-slate-100">批次進度</div>
          <div className="text-xs text-slate-400">Task: {batchTask.task_id}</div>
        </div>
        <div className="text-xl font-semibold text-amber-200">{pct}%</div>
      </div>

      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-amber-400/70 to-emerald-400/60 transition-all duration-300"
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

      <div className="space-y-2">
        <div className="text-xs uppercase tracking-[0.2em] text-slate-400">逐標的狀態</div>
        <div className="max-h-52 overflow-auto rounded-xl border border-white/10 bg-white/5 p-3 grid grid-cols-1 md:grid-cols-2 gap-2">
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
          {statusBySymbol.length === 0 && (
            <div className="text-xs text-slate-400">尚無逐標的狀態資料</div>
          )}
        </div>
      </div>

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
    </div>
  );
}
