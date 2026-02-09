'use client';

import { useState } from 'react';
import { Bot, PauseCircle, Play } from 'lucide-react';
import { useAutoResearch } from '@/hooks/useAutoResearch';

export default function AutoResearchPanel() {
  const {
    status,
    logs,
    startResearch,
    stopResearch,
    isRunning,
  } = useAutoResearch();

  const [targetMetric, setTargetMetric] = useState('auc');
  const [targetValue, setTargetValue] = useState(0.65);
  const [maxIterations, setMaxIterations] = useState(10);
  const [maxMinutes, setMaxMinutes] = useState(30);

  const handleStart = async () => {
    await startResearch({
      objective: { metric: targetMetric, target: targetValue },
      constraints: { max_iterations: maxIterations, max_time_minutes: maxMinutes },
    });
  };

  return (
    <div className="glass-panel rounded-2xl p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-rose-400/15 flex items-center justify-center">
          <Bot className="w-5 h-5 text-rose-200" />
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">AutoResearch</div>
          <div className="text-xs text-slate-400">自動研究迴圈控制面板</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div>
          <label className="text-xs text-slate-400">目標 Metric</label>
          <select
            value={targetMetric}
            onChange={(event) => setTargetMetric(event.target.value)}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          >
            <option value="auc">AUC</option>
            <option value="sharpe">Sharpe</option>
            <option value="ic">IC</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400">目標值</label>
          <input
            type="number"
            step="0.01"
            value={targetValue}
            onChange={(event) => setTargetValue(Number(event.target.value))}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">最大迭代</label>
          <input
            type="number"
            value={maxIterations}
            onChange={(event) => setMaxIterations(Number(event.target.value))}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">最大分鐘</label>
          <input
            type="number"
            value={maxMinutes}
            onChange={(event) => setMaxMinutes(Number(event.target.value))}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100"
          />
        </div>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          onClick={handleStart}
          disabled={isRunning}
          className="inline-flex items-center gap-2 rounded-xl border border-rose-300/30 bg-rose-400/10 px-4 py-2 text-sm text-rose-100 hover:bg-rose-400/20 transition disabled:opacity-50"
        >
          <Play className="w-4 h-4" />
          啟動研究
        </button>
        <button
          onClick={stopResearch}
          disabled={!isRunning}
          className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-300 hover:bg-white/10 transition disabled:opacity-50"
        >
          <PauseCircle className="w-4 h-4" />
          停止
        </button>
      </div>

      <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-2 text-xs text-slate-300">
        <div className="text-slate-400">狀態: {status?.status || 'idle'}</div>
        {logs.length === 0 ? (
          <div className="text-slate-500">尚無研究日誌。</div>
        ) : (
          <div className="space-y-2 max-h-40 overflow-auto">
            {logs.map((item, index) => (
              <div key={`${item.iteration}-${index}`} className="border-b border-white/5 pb-2">
                <div className="text-rose-100"># {item.iteration} {item.decision}</div>
                <div className="text-slate-400">{item.next_action}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
