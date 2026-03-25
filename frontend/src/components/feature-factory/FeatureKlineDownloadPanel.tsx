'use client';

import { useState, useEffect, useCallback } from 'react';
import { Download, Database, RefreshCw, CheckCircle2, XCircle, Loader2, ChevronDown, ChevronUp } from 'lucide-react';

const SUPPORTED_TIMEFRAMES = [
  { value: '1m', label: '1分' },
  { value: '5m', label: '5分' },
  { value: '15m', label: '15分' },
  { value: '30m', label: '30分' },
  { value: '1h', label: '1時' },
  { value: '4h', label: '4時' },
  { value: '12h', label: '12時' },
  { value: '1d', label: '日線' },
  { value: '1w', label: '週線' },
] as const;

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface TaskProgress {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'partial' | 'failed';
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  progress_percent: number;
  current_symbol: string | null;
  current_timeframe: string | null;
  error_messages: string[];
  finished_at: string | null;
}

interface DownloadedEntry {
  symbol: string;
  timeframe: string;
  row_count: number;
  start_date: string;
  end_date: string;
  is_valid?: boolean | null;
  quality_errors?: string[];
  quality_warnings?: string[];
}

function parseSymbolInput(raw: string): string[] {
  return Array.from(
    new Set(
      raw
        .split(/[\s,，\n]+/)
        .map((s) => s.trim().toUpperCase())
        .filter((s) => s.length > 0)
    )
  );
}

interface FeatureKlineDownloadPanelProps {
  onDownloadComplete?: () => void;
}

export default function FeatureKlineDownloadPanel({ onDownloadComplete }: FeatureKlineDownloadPanelProps) {
  const [symbolInput, setSymbolInput] = useState('BTCUSDT');
  const [selectedTimeframes, setSelectedTimeframes] = useState<string[]>(['12h']);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [forceRedownload, setForceRedownload] = useState(false);

  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [downloadedEntries, setDownloadedEntries] = useState<DownloadedEntry[]>([]);
  const [showDownloaded, setShowDownloaded] = useState(false);
  const [isLoadingList, setIsLoadingList] = useState(false);

  const [allUsdtSymbols, setAllUsdtSymbols] = useState<string[]>([]);
  const [isLoadingUsdt, setIsLoadingUsdt] = useState(false);

  // ── 輪詢進度 ──────────────────────────────────────────────
  useEffect(() => {
    if (!taskId) return;

    let pollCount = 0;
    let timerId: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const res = await fetch(`${API}/api/v1/feature-data/kline/download-status/${taskId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: TaskProgress = await res.json();
        setProgress(data);

        if (data.status === 'completed' || data.status === 'partial' || data.status === 'failed') {
          refreshDownloadedList();
          if (data.status === 'completed' || data.status === 'partial') {
            onDownloadComplete?.();
          }
          return;
        }

        pollCount++;
        const interval = Math.min(1000 + pollCount * 300, 3000);
        timerId = setTimeout(poll, interval);
      } catch {
        timerId = setTimeout(poll, 5000);
      }
    };

    poll();
    return () => clearTimeout(timerId);
  }, [taskId]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── 取得已下載清單 ─────────────────────────────────────────
  const refreshDownloadedList = useCallback(async () => {
    setIsLoadingList(true);
    try {
      const res = await fetch(`${API}/api/v1/feature-data/kline/list`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setDownloadedEntries(data.entries ?? []);
    } catch (err) {
      console.error('取得已下載清單失敗', err);
    } finally {
      setIsLoadingList(false);
    }
  }, []);

  useEffect(() => {
    refreshDownloadedList();
  }, [refreshDownloadedList]);

  // ── 載入 ALL_USDT 清單 ────────────────────────────────────
  const loadAllUsdtSymbols = async () => {
    if (allUsdtSymbols.length > 0) {
      setSymbolInput('ALL_USDT');
      return;
    }
    setIsLoadingUsdt(true);
    try {
      const res = await fetch(`${API}/api/v1/feature-data/exchange/usdt-symbols`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setAllUsdtSymbols(data.symbols ?? []);
      setSymbolInput('ALL_USDT');
    } catch (err) {
      setError(`取得 ALL_USDT 清單失敗：${err instanceof Error ? err.message : err}`);
    } finally {
      setIsLoadingUsdt(false);
    }
  };

  // ── 啟動下載 ───────────────────────────────────────────────
  const handleStartDownload = async () => {
    const symbols = parseSymbolInput(symbolInput);
    if (symbols.length === 0) {
      setError('請輸入至少一個標的');
      return;
    }
    if (selectedTimeframes.length === 0) {
      setError('請至少選擇一個時間框架');
      return;
    }

    setError(null);
    setProgress(null);
    setTaskId(null);
    setIsStarting(true);

    try {
      const body = {
        symbols,
        timeframes: selectedTimeframes,
        start_date: startDate || null,
        end_date: endDate || null,
        force_redownload: forceRedownload,
      };

      const res = await fetch(`${API}/api/v1/feature-data/kline/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail ?? `HTTP ${res.status}`);
      }

      const data = await res.json();
      setTaskId(data.task_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : '啟動下載失敗');
    } finally {
      setIsStarting(false);
    }
  };

  const previewSymbols = parseSymbolInput(symbolInput);
  const isRunning = progress?.status === 'pending' || progress?.status === 'running';
  const isDone = progress?.status === 'completed' || progress?.status === 'partial' || progress?.status === 'failed';

  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      {/* 標題 */}
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-cyan-400/15 flex items-center justify-center">
          <Database className="w-5 h-5 text-cyan-200" />
        </div>
        <div>
          <div className="text-lg font-semibold text-slate-100">Feature K 線下載</div>
          <div className="text-xs text-slate-400">獨立於案例系統，資料存於 data_cache/feature_klines/</div>
        </div>
      </div>

      {/* 標的輸入 */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.2em] text-slate-400">目標標的</label>
        <textarea
          value={symbolInput}
          onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
          rows={3}
          disabled={isRunning}
          className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:ring-2 focus:ring-cyan-300/40 resize-none disabled:opacity-50"
          placeholder={'BTCUSDT, ETHUSDT, SOLUSDT\n或每行一個，ALL_USDT = 所有 USDT 對'}
        />
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={loadAllUsdtSymbols}
            disabled={isRunning || isLoadingUsdt}
            className="inline-flex items-center gap-1 rounded-lg border border-white/15 px-3 py-1 text-xs text-slate-200 hover:bg-white/5 disabled:opacity-50 transition"
          >
            {isLoadingUsdt ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Download className="w-3 h-3" />
            )}
            ALL_USDT
          </button>
          {['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT'].map((s) => (
            <button
              key={s}
              type="button"
              disabled={isRunning}
              onClick={() => {
                const cur = parseSymbolInput(symbolInput);
                if (!cur.includes(s)) setSymbolInput([...cur, s].join(', '));
              }}
              className="rounded-lg border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:bg-white/5 disabled:opacity-50 transition"
            >
              + {s}
            </button>
          ))}
          <span className="text-[11px] text-slate-500">
            共 {previewSymbols.length} 個標的（ALL_USDT 展開後計）
          </span>
        </div>
      </div>

      {/* 時間框架 */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.2em] text-slate-400">時間框架（可多選）</label>
        <div className="flex flex-wrap gap-2">
          {SUPPORTED_TIMEFRAMES.map((tf) => {
            const checked = selectedTimeframes.includes(tf.value);
            return (
              <button
                key={tf.value}
                type="button"
                disabled={isRunning}
                onClick={() => {
                  setSelectedTimeframes((prev) =>
                    checked ? prev.filter((x) => x !== tf.value) : [...prev, tf.value]
                  );
                }}
                className={`rounded-lg px-3 py-1.5 text-xs border transition ${
                  checked
                    ? 'bg-cyan-400/20 border-cyan-300/40 text-cyan-200'
                    : 'border-white/10 text-slate-400 hover:bg-white/5 hover:text-slate-200'
                } disabled:opacity-50`}
              >
                {tf.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 日期範圍 */}
      <div className="space-y-2">
        <label className="text-xs uppercase tracking-[0.2em] text-slate-400">日期範圍（可選）</label>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[11px] text-slate-500 mb-1">開始日期</div>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              disabled={isRunning}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-300/40 [color-scheme:dark] disabled:opacity-50"
            />
          </div>
          <div>
            <div className="text-[11px] text-slate-500 mb-1">結束日期</div>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              disabled={isRunning}
              className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-300/40 [color-scheme:dark] disabled:opacity-50"
            />
          </div>
        </div>
        <div className="text-[11px] text-slate-500">留空則下載全部可用歷史資料（到今天）</div>
      </div>

      {/* 強制重新下載 */}
      <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
        <input
          type="checkbox"
          checked={forceRedownload}
          onChange={(e) => setForceRedownload(e.target.checked)}
          disabled={isRunning}
          className="accent-cyan-400"
        />
        強制重新下載（覆蓋已有資料）
      </label>

      {/* 錯誤訊息 */}
      {error && (
        <div className="flex items-center gap-2 rounded-xl p-3 border border-rose-400/30 bg-rose-400/10 text-rose-200 text-sm">
          <XCircle className="w-4 h-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* 啟動按鈕 */}
      <button
        onClick={handleStartDownload}
        disabled={isRunning || isStarting}
        className="w-full inline-flex items-center justify-center gap-2 rounded-xl px-4 py-3 bg-cyan-400/20 text-cyan-100 border border-cyan-300/30 hover:bg-cyan-400/30 transition disabled:opacity-50 font-medium"
      >
        {isStarting ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> 啟動中…</>
        ) : isRunning ? (
          <><Loader2 className="w-4 h-4 animate-spin" /> 下載中…</>
        ) : (
          <><Download className="w-4 h-4" /> 啟動下載</>
        )}
      </button>

      {/* 進度顯示 */}
      {progress && (
        <div className="space-y-3">
          {/* 進度條 */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-400">
              <span>
                {progress.current_symbol
                  ? `${progress.current_symbol} ${progress.current_timeframe ?? ''}`
                  : progress.status}
              </span>
              <span className="font-semibold text-slate-200">
                {progress.completed_jobs}/{progress.total_jobs} ({progress.progress_percent}%)
              </span>
            </div>
            <div className="w-full bg-white/5 rounded-full h-2.5 overflow-hidden">
              <div
                className={`h-full transition-all duration-300 rounded-full ${
                  progress.status === 'completed'
                    ? 'bg-emerald-400'
                    : progress.status === 'failed'
                    ? 'bg-rose-400'
                    : progress.status === 'partial'
                    ? 'bg-amber-400'
                    : 'bg-cyan-400'
                }`}
                style={{ width: `${progress.progress_percent}%` }}
              />
            </div>
          </div>

          {/* 成功/失敗統計 */}
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="rounded-lg bg-white/5 p-2">
              <div className="text-lg font-semibold text-slate-100">{progress.total_jobs}</div>
              <div className="text-[10px] text-slate-500">總計</div>
            </div>
            <div className="rounded-lg bg-emerald-400/10 p-2">
              <div className="text-lg font-semibold text-emerald-300">{progress.completed_jobs}</div>
              <div className="text-[10px] text-slate-500">成功</div>
            </div>
            <div className="rounded-lg bg-rose-400/10 p-2">
              <div className="text-lg font-semibold text-rose-300">{progress.failed_jobs}</div>
              <div className="text-[10px] text-slate-500">失敗</div>
            </div>
          </div>

          {/* 完成提示 */}
          {isDone && (
            <div
              className={`flex items-center gap-2 rounded-xl p-3 border text-sm ${
                progress.status === 'completed'
                  ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
                  : progress.status === 'partial'
                  ? 'border-amber-400/30 bg-amber-400/10 text-amber-200'
                  : 'border-rose-400/30 bg-rose-400/10 text-rose-200'
              }`}
            >
              {progress.status === 'completed' ? (
                <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              ) : (
                <XCircle className="w-4 h-4 flex-shrink-0" />
              )}
              {progress.status === 'completed'
                ? `下載完成，共 ${progress.completed_jobs} 個工作`
                : progress.status === 'partial'
                ? `部分完成：${progress.completed_jobs} 成功，${progress.failed_jobs} 失敗`
                : '下載失敗'}
            </div>
          )}

          {/* 錯誤訊息列表 */}
          {progress.error_messages.length > 0 && (
            <div className="rounded-xl border border-rose-400/20 bg-rose-400/5 p-3 space-y-1 max-h-32 overflow-auto">
              <div className="text-[11px] font-semibold text-rose-300 mb-1">錯誤訊息</div>
              {progress.error_messages.map((msg, i) => (
                <div key={i} className="text-[11px] text-rose-200/80">{msg}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 已下載清單 */}
      <div className="border-t border-white/10 pt-4 space-y-2">
        <button
          type="button"
          onClick={() => {
            setShowDownloaded((v) => !v);
            if (!showDownloaded) refreshDownloadedList();
          }}
          className="w-full flex items-center justify-between text-sm text-slate-300 hover:text-slate-100 transition"
        >
          <span className="flex items-center gap-2">
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingList ? 'animate-spin' : ''}`} />
            已下載資料
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-slate-400">
              {downloadedEntries.length}
            </span>
          </span>
          {showDownloaded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {showDownloaded && (
          <div className="rounded-xl border border-white/10 overflow-hidden">
            {downloadedEntries.length === 0 ? (
              <div className="p-4 text-center text-sm text-slate-500">尚未下載任何資料</div>
            ) : (
              <table className="w-full text-xs text-slate-300">
                <thead className="bg-white/5">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">標的</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">TF</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">K 線數</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">起</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">訖</th>
                    <th className="px-3 py-2 text-left font-medium text-slate-400">品質</th>
                  </tr>
                </thead>
                <tbody>
                  {downloadedEntries.map((e, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-white/2' : ''}>
                      <td className="px-3 py-1.5 font-mono">{e.symbol}</td>
                      <td className="px-3 py-1.5">{e.timeframe}</td>
                      <td className="px-3 py-1.5 text-cyan-300">{e.row_count.toLocaleString()}</td>
                      <td className="px-3 py-1.5 text-slate-500">{e.start_date}</td>
                      <td className="px-3 py-1.5 text-slate-500">{e.end_date}</td>
                      <td className="px-3 py-1.5">
                        {e.is_valid === null || e.is_valid === undefined ? (
                          <span className="text-slate-600">—</span>
                        ) : e.is_valid ? (
                          <span className="text-emerald-400" title="品質正常，無缺口或異常">✓ 正常</span>
                        ) : (
                          <div>
                            <span className="text-rose-400">✗ 異常</span>
                            {(e.quality_errors ?? []).length > 0 && (
                              <div className="mt-0.5 space-y-0.5">
                                {(e.quality_errors ?? []).map((err, ei) => (
                                  <div key={ei} className="text-[10px] text-rose-300/80 leading-tight">{err}</div>
                                ))}
                              </div>
                            )}
                            {(e.quality_warnings ?? []).length > 0 && (
                              <div className="mt-0.5 space-y-0.5">
                                {(e.quality_warnings ?? []).map((w, wi) => (
                                  <div key={wi} className="text-[10px] text-amber-300/80 leading-tight">{w}</div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
