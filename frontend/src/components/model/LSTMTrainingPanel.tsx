/**
 * LSTMTrainingPanel.tsx
 *
 * LSTM / Transformer 序列模型訓練面板（骨幹版）
 *
 * Features:
 * - 設定 window_size / hidden_size / epochs 等超參數
 * - 啟動非同步訓練任務
 * - Polling 進度追蹤（train_loss / val_loss / val_auc）
 * - Loss 曲線視覺化（Recharts LineChart）
 * - 訓練完成後顯示關鍵指標
 *
 * 未來優化：
 * - 加入 WebSocket 即時 epoch 更新
 * - 加入 Attention Heat Map 視覺化
 * - 接入 Optuna 自動超參數搜索
 */

'use client';

import React, { useState, useRef, useCallback } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

// ─────────────────────────────────────────────
// 型別定義
// ─────────────────────────────────────────────

interface LSTMConfig {
  window_size: number;
  hidden_size: number;
  num_layers: number;
  dropout: number;
  epochs: number;
  batch_size: number;
  learning_rate: number;
}

interface LSTMTaskStatus {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  current_epoch: number;
  total_epochs: number;
  message: string;
  train_loss_history: number[];
  val_loss_history: number[];
  best_val_loss: number;
  best_epoch: number;
  val_auc: number;
  n_train_samples: number;
  n_val_samples: number;
  error?: string;
}

interface LossChartPoint {
  epoch: number;
  train_loss: number;
  val_loss: number;
}

interface Props {
  /** 符號，用來決定從哪個 HDF5 讀取 K 線 */
  symbol?: string;
  /** 時間框架 */
  timeframe?: string;
  /** 訓練完成後的回調 */
  onTrainingComplete?: (taskId: string, valAuc: number) => void;
}

// ─────────────────────────────────────────────
// API 呼叫工具
// ─────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

async function startLSTMTraining(
  symbol: string,
  timeframe: string,
  config: LSTMConfig
): Promise<{ task_id: string }> {
  const res = await fetch(`${API_BASE}/api/v1/lstm/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, timeframe, config }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

async function fetchLSTMTaskStatus(taskId: string): Promise<LSTMTaskStatus> {
  const res = await fetch(`${API_BASE}/api/v1/lstm/task/${taskId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ─────────────────────────────────────────────
// 子元件：指標方塊
// ─────────────────────────────────────────────

function MetricBadge({ label, value, good }: { label: string; value: string; good?: boolean }) {
  const color =
    good === undefined
      ? 'text-slate-200'
      : good
      ? 'text-green-400'
      : 'text-red-400';
  return (
    <div className="bg-slate-800/60 rounded-lg p-3 text-center">
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  );
}

// ─────────────────────────────────────────────
// 主元件
// ─────────────────────────────────────────────

const DEFAULT_CONFIG: LSTMConfig = {
  window_size: 48,
  hidden_size: 128,
  num_layers: 2,
  dropout: 0.2,
  epochs: 50,
  batch_size: 256,
  learning_rate: 0.001,
};

export default function LSTMTrainingPanel({
  symbol = 'BTCUSDT',
  timeframe = '1h',
  onTrainingComplete,
}: Props) {
  const [config, setConfig] = useState<LSTMConfig>(DEFAULT_CONFIG);
  const [panelStatus, setPanelStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [taskStatus, setTaskStatus] = useState<LSTMTaskStatus | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── 派生資料：Loss 曲線 ──
  const lossChartData: LossChartPoint[] = (taskStatus?.train_loss_history ?? []).map(
    (tl, i) => ({
      epoch: i + 1,
      train_loss: parseFloat(tl.toFixed(5)),
      val_loss: parseFloat((taskStatus?.val_loss_history[i] ?? 0).toFixed(5)),
    })
  );

  // ── 啟動訓練 ──
  const handleStart = useCallback(async () => {
    setErrorMsg('');
    setPanelStatus('running');
    setTaskStatus(null);
    try {
      const { task_id } = await startLSTMTraining(symbol, timeframe, config);
      // 開始 polling
      pollingRef.current = setInterval(async () => {
        try {
          const status = await fetchLSTMTaskStatus(task_id);
          setTaskStatus(status);
          if (status.status === 'completed') {
            clearInterval(pollingRef.current!);
            setPanelStatus('completed');
            onTrainingComplete?.(task_id, status.val_auc);
          } else if (status.status === 'failed') {
            clearInterval(pollingRef.current!);
            setPanelStatus('failed');
            setErrorMsg(status.error ?? '未知錯誤');
          }
        } catch (e) {
          // polling 暫時失敗不中斷，等下一次
          console.warn('LSTM status polling error:', e);
        }
      }, 2000);
    } catch (e) {
      setPanelStatus('failed');
      setErrorMsg(e instanceof Error ? e.message : '啟動失敗');
    }
  }, [symbol, timeframe, config, onTrainingComplete]);

  const handleStop = useCallback(() => {
    if (pollingRef.current) clearInterval(pollingRef.current);
    setPanelStatus('idle');
  }, []);

  // ── 設定欄位 ──
  const configFields: Array<{ key: keyof LSTMConfig; label: string; step: number; min: number }> = [
    { key: 'window_size', label: 'Window Size（根）', step: 1, min: 1 },
    { key: 'hidden_size', label: 'Hidden Size', step: 16, min: 16 },
    { key: 'num_layers', label: 'LSTM Layers', step: 1, min: 1 },
    { key: 'dropout', label: 'Dropout', step: 0.05, min: 0 },
    { key: 'epochs', label: 'Epochs', step: 10, min: 10 },
    { key: 'batch_size', label: 'Batch Size', step: 64, min: 32 },
    { key: 'learning_rate', label: 'Learning Rate', step: 0.0001, min: 0.00001 },
  ];

  const isRunning = panelStatus === 'running';

  return (
    <div className="bg-slate-900/80 rounded-xl border border-slate-700/60 p-6 space-y-6">
      {/* 標題 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-100">
            LSTM 序列模型訓練
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {symbol} / {timeframe}｜Window={config.window_size} 根 K 線
          </p>
        </div>
        <span
          className={`text-xs px-2 py-1 rounded-full font-medium ${
            panelStatus === 'completed'
              ? 'bg-green-900/50 text-green-300'
              : panelStatus === 'running'
              ? 'bg-blue-900/50 text-blue-300'
              : panelStatus === 'failed'
              ? 'bg-red-900/50 text-red-300'
              : 'bg-slate-700/60 text-slate-400'
          }`}
        >
          {panelStatus === 'idle' && '待機'}
          {panelStatus === 'running' && `訓練中 ${taskStatus?.progress ?? 0}%`}
          {panelStatus === 'completed' && '已完成'}
          {panelStatus === 'failed' && '失敗'}
        </span>
      </div>

      {/* 設定區 */}
      {panelStatus === 'idle' && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {configFields.map(({ key, label, step, min }) => (
            <div key={key}>
              <label className="text-xs text-slate-400 mb-1 block">{label}</label>
              <input
                type="number"
                step={step}
                min={min}
                value={config[key]}
                onChange={(e) =>
                  setConfig((prev) => ({ ...prev, [key]: parseFloat(e.target.value) }))
                }
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          ))}
        </div>
      )}

      {/* 進度訊息 */}
      {isRunning && taskStatus && (
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-slate-400">
            <span>{taskStatus.message}</span>
            <span>
              Epoch {taskStatus.current_epoch} / {taskStatus.total_epochs}
            </span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-1.5">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${taskStatus.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Loss 曲線 */}
      {lossChartData.length > 1 && (
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-3">Loss 曲線</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={lossChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="epoch"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                label={{ value: 'Epoch', position: 'insideBottom', offset: -2, fill: '#94a3b8', fontSize: 11 }}
              />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} width={55} />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#cbd5e1' }}
              />
              <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
              <Line
                type="monotone"
                dataKey="train_loss"
                name="Train Loss"
                stroke="#60a5fa"
                dot={false}
                strokeWidth={1.5}
              />
              <Line
                type="monotone"
                dataKey="val_loss"
                name="Val Loss"
                stroke="#34d399"
                dot={false}
                strokeWidth={1.5}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* 完成後指標 */}
      {panelStatus === 'completed' && taskStatus && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricBadge
            label="Val AUC"
            value={taskStatus.val_auc.toFixed(4)}
            good={taskStatus.val_auc >= 0.55}
          />
          <MetricBadge
            label="Best Epoch"
            value={`${taskStatus.best_epoch} / ${taskStatus.total_epochs}`}
          />
          <MetricBadge
            label="Best Val Loss"
            value={taskStatus.best_val_loss.toFixed(5)}
          />
          <MetricBadge
            label="訓練樣本"
            value={`${taskStatus.n_train_samples.toLocaleString()} + ${taskStatus.n_val_samples.toLocaleString()}`}
          />
        </div>
      )}

      {/* 錯誤訊息 */}
      {panelStatus === 'failed' && errorMsg && (
        <div className="bg-red-900/30 border border-red-700/50 rounded-lg p-3 text-sm text-red-300">
          {errorMsg}
        </div>
      )}

      {/* 操作按鈕 */}
      <div className="flex gap-3">
        {panelStatus === 'idle' && (
          <button
            onClick={handleStart}
            className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            開始訓練
          </button>
        )}
        {isRunning && (
          <button
            onClick={handleStop}
            className="px-5 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-lg transition-colors"
          >
            停止監控
          </button>
        )}
        {(panelStatus === 'completed' || panelStatus === 'failed') && (
          <button
            onClick={() => {
              setPanelStatus('idle');
              setTaskStatus(null);
              setErrorMsg('');
            }}
            className="px-5 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 text-sm font-medium rounded-lg transition-colors"
          >
            重置
          </button>
        )}
      </div>
    </div>
  );
}
