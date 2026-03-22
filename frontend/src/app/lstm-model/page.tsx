/**
 * lstm-model/page.tsx
 *
 * LSTM / Transformer 序列模型頁面
 *
 * 狀態：骨幹已建立，待硬體升級後完整啟用
 * - M1 8GB：Mode A 技術可行（~500MB），Mode C OOM（需 lazy DataLoader）
 * - 建議硬體：Mac Mini M4 16GB+ 或 MacBook M5 Pro 24GB+
 */

'use client';

import React, { useState } from 'react';
import {
  Brain,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Cpu,
  MemoryStick,
  Zap,
  Info,
} from 'lucide-react';
import LSTMTrainingPanel from '@/components/model/LSTMTrainingPanel';

// ─────────────────────────────────────────────
// 硬體需求資料
// ─────────────────────────────────────────────

interface HardwareSpec {
  device: string;
  memory: string;
  modeA: 'ok' | 'marginal' | 'fail';
  modeC: 'ok' | 'marginal' | 'fail';
  speed: string;
  note: string;
  recommended?: boolean;
}

const hardwareSpecs: HardwareSpec[] = [
  {
    device: 'MacBook M1 8GB（現有）',
    memory: '8 GB 統一記憶體',
    modeA: 'marginal',
    modeC: 'fail',
    speed: '慢（10+ min/epoch）',
    note: 'OS+瀏覽器占用 ~3-4GB；Mode A ~500MB 技術可行，運氣成份高',
  },
  {
    device: 'Mac Mini M4 16GB',
    memory: '16 GB 統一記憶體',
    modeA: 'ok',
    modeC: 'marginal',
    speed: '中（2-4 min/epoch）',
    note: 'Mode C 需改 DataLoader 懶載入（尚未實作），CP值最高（約 $599）',
    recommended: true,
  },
  {
    device: 'MacBook M5 16GB',
    memory: '16 GB 統一記憶體',
    modeA: 'ok',
    modeC: 'marginal',
    speed: '中（2-3 min/epoch，M5 製程較 M4 更快）',
    note: 'M5 Neural Engine 效能更強，同 M4 Mini 等級，Mode C 仍需 lazy DataLoader',
  },
  {
    device: 'Mac Mini M4 Pro 24GB',
    memory: '24 GB 統一記憶體',
    modeA: 'ok',
    modeC: 'ok',
    speed: '快（<1 min/epoch）',
    note: 'Mode C lazy DataLoader 後輕鬆跑；推薦入門 Pro 選項（約 $999）',
    recommended: true,
  },
  {
    device: 'MacBook M5 Pro 24/36GB',
    memory: '24-36 GB 統一記憶體',
    modeA: 'ok',
    modeC: 'ok',
    speed: '快（<1 min/epoch）',
    note: 'M5 Pro MPS 效能大幅提升，最佳可攜性選擇',
    recommended: true,
  },
  {
    device: 'MacBook M5 Max 48GB+',
    memory: '48-128 GB 統一記憶體',
    modeA: 'ok',
    modeC: 'ok',
    speed: '極快（秒級/epoch）',
    note: '記憶體完全無壓力，甚至可跑多標的並行訓練',
  },
];

// ─────────────────────────────────────────────
// 子元件
// ─────────────────────────────────────────────

const StatusIcon = ({ status }: { status: 'ok' | 'marginal' | 'fail' }) => {
  if (status === 'ok') return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
  if (status === 'marginal') return <AlertTriangle className="h-4 w-4 text-amber-400" />;
  return <XCircle className="h-4 w-4 text-red-400" />;
};

const StatusLabel = ({ status }: { status: 'ok' | 'marginal' | 'fail' }) => {
  if (status === 'ok') return <span className="text-emerald-400 text-xs font-medium">可行</span>;
  if (status === 'marginal') return <span className="text-amber-400 text-xs font-medium">邊緣</span>;
  return <span className="text-red-400 text-xs font-medium">不可行</span>;
};

// ─────────────────────────────────────────────
// 主頁面
// ─────────────────────────────────────────────

export default function LSTMModelPage() {
  const [showHardwareGuide, setShowHardwareGuide] = useState(true);

  return (
    <div className="min-h-screen bg-[#0A0F1C] text-slate-100 p-6 space-y-6">
      {/* ── 頁面標題 ── */}
      <div className="flex items-center gap-3">
        <Brain className="h-7 w-7 text-amber-400" />
        <div>
          <h1 className="text-2xl font-semibold text-slate-100">序列模型</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            LSTM / Transformer 時序預測模型 — 與 XGBoost 互補的深度學習引擎
          </p>
        </div>
        <span className="ml-auto text-[10px] font-semibold px-2.5 py-1 rounded-full bg-amber-400/15 text-amber-400 border border-amber-400/30">
          待硬體升級後完整啟用
        </span>
      </div>

      {/* ── 硬體限制警告橫幅 ── */}
      <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-amber-300 mb-1">
              目前硬體狀態：M1 8GB — 部分功能受限
            </h3>
            <div className="text-xs text-slate-400 space-y-1">
              <p>
                <span className="text-amber-400 font-medium">Mode A（事件切片，~14,600 筆）：</span>
                技術上可行（~500MB），OS 與瀏覽器競爭記憶體下偶發 OOM，訓練速度慢。
              </p>
              <p>
                <span className="text-red-400 font-medium">Mode C（連續完整時序，~350萬筆）：</span>
                現行程式碼一次載入記憶體約 20GB+，直接 OOM。需改用 DataLoader 懶載入後 16GB 以上可行。
              </p>
              <p className="text-slate-500">
                骨幹程式碼已建立（lazy import，不影響系統啟動）。API 端點 <code className="text-slate-300">/api/v1/lstm/</code> 待硬體升級後補建。
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* ── 硬體需求指南（可折疊）── */}
      <div className="rounded-xl border border-white/10 bg-[#1a233a]/40">
        <button
          className="w-full flex items-center justify-between px-5 py-4 text-left"
          onClick={() => setShowHardwareGuide(v => !v)}
        >
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-slate-400" />
            <span className="text-sm font-medium text-slate-200">硬體需求指南 — 要幾 GB 才夠跑？</span>
          </div>
          {showHardwareGuide
            ? <ChevronUp className="h-4 w-4 text-slate-400" />
            : <ChevronDown className="h-4 w-4 text-slate-400" />}
        </button>

        {showHardwareGuide && (
          <div className="px-5 pb-5 space-y-4">
            {/* 記憶體計算說明 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <MemoryStick className="h-3.5 w-3.5 text-blue-400" />
                  Mode A 記憶體需求估算
                </div>
                <div className="text-slate-500 space-y-0.5">
                  <p>Input tensor: 14,600 × 48 × ~50 × 4B ≈ <span className="text-slate-300">140 MB</span></p>
                  <p>梯度 + Optimizer state: ≈ <span className="text-slate-300">50 MB</span></p>
                  <p>Batch + 中間活化值: ≈ <span className="text-slate-300">200 MB</span></p>
                  <p className="border-t border-white/10 pt-1 text-slate-300 font-medium">總計: ~400–600 MB</p>
                </div>
              </div>
              <div className="rounded-lg border border-white/10 bg-white/5 p-3 space-y-1.5">
                <div className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <MemoryStick className="h-3.5 w-3.5 text-purple-400" />
                  Mode C 記憶體需求估算
                </div>
                <div className="text-slate-500 space-y-0.5">
                  <p>全量載入: 3.5M × 48 × 50 × 4B ≈ <span className="text-red-400 font-medium">33 GB（OOM）</span></p>
                  <p>改 DataLoader 懶載入後:</p>
                  <p>每 batch 256 筆 ≈ <span className="text-slate-300">25 MB</span></p>
                  <p>H5 快取 + 索引 ≈ <span className="text-slate-300">2–4 GB</span></p>
                  <p className="border-t border-white/10 pt-1 text-slate-300 font-medium">總計: ~6–8 GB（需 lazy DataLoader）</p>
                </div>
              </div>
            </div>

            {/* Transformer vs LSTM 比較 */}
            <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-xs">
              <div className="flex items-center gap-1.5 text-slate-300 font-medium mb-2">
                <Zap className="h-3.5 w-3.5 text-yellow-400" />
                Transformer vs LSTM — 記憶體差異
              </div>
              <p className="text-slate-500">
                seq_len=48 時，Transformer Self-Attention 額外開銷 ≈ 256 × 48² × hidden_dim × 4B ≈
                <span className="text-slate-300"> 60–150 MB</span>，與 LSTM 差異極小。
                <span className="text-emerald-400"> 相同硬體等級均適用。</span>
              </p>
            </div>

            {/* 硬體比較表 */}
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/10">
                    <th className="text-left py-2 pr-4 text-slate-400 font-medium">設備</th>
                    <th className="text-center py-2 px-3 text-slate-400 font-medium">記憶體</th>
                    <th className="text-center py-2 px-3 text-slate-400 font-medium">Mode A</th>
                    <th className="text-center py-2 px-3 text-slate-400 font-medium">Mode C</th>
                    <th className="text-left py-2 px-3 text-slate-400 font-medium">訓練速度</th>
                    <th className="text-left py-2 pl-3 text-slate-400 font-medium">備註</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {hardwareSpecs.map((spec) => (
                    <tr
                      key={spec.device}
                      className={`${spec.recommended ? 'bg-emerald-400/5' : ''}`}
                    >
                      <td className="py-2.5 pr-4">
                        <div className="flex items-center gap-1.5">
                          {spec.recommended && (
                            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-400/20 text-emerald-400 border border-emerald-400/30 whitespace-nowrap">
                              推薦
                            </span>
                          )}
                          <span className={spec.recommended ? 'text-slate-200' : 'text-slate-400'}>
                            {spec.device}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-center text-slate-400">{spec.memory}</td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-col items-center gap-0.5">
                          <StatusIcon status={spec.modeA} />
                          <StatusLabel status={spec.modeA} />
                        </div>
                      </td>
                      <td className="py-2.5 px-3">
                        <div className="flex flex-col items-center gap-0.5">
                          <StatusIcon status={spec.modeC} />
                          <StatusLabel status={spec.modeC} />
                        </div>
                      </td>
                      <td className="py-2.5 px-3 text-slate-400">{spec.speed}</td>
                      <td className="py-2.5 pl-3 text-slate-500">{spec.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 最終建議 */}
            <div className="rounded-lg border border-blue-400/20 bg-blue-400/5 p-3 text-xs">
              <div className="flex items-start gap-2">
                <Info className="h-3.5 w-3.5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-slate-400 space-y-1">
                  <p>
                    <span className="text-blue-300 font-medium">最划算選擇：</span>
                    Mac Mini M4 16GB（$599 USD）— Mode A 完全無壓力，Mode C 需等 lazy DataLoader 實作後可跑。
                  </p>
                  <p>
                    <span className="text-blue-300 font-medium">最舒適選擇：</span>
                    Mac Mini M4 Pro 24/48GB（$999+ USD）或 MacBook M5 Pro 24GB — 兩種模式完全可行，速度快。
                  </p>
                  <p>
                    <span className="text-blue-300 font-medium">M5 vs M4：</span>
                    M5 製程更先進，Neural Engine TOPS 更高，現已可購入；M4 Pro 仍是 CP 值穩定選項。
                  </p>
                  <p>
                    <span className="text-slate-500">⚠ Apple Silicon 統一記憶體（Unified Memory）由 CPU / GPU / Neural Engine 共享，
                    與桌面 GPU 獨立顯存不同——選購時記憶體比 CPU 核心數更重要。</span>
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── 待建功能清單 ── */}
      <div className="rounded-xl border border-white/10 bg-[#1a233a]/40 p-5">
        <h3 className="text-sm font-medium text-slate-200 mb-3 flex items-center gap-2">
          <Brain className="h-4 w-4 text-slate-400" />
          硬體升級後待建項目
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          {[
            { label: 'api/routes/lstm.py', desc: 'POST /train、GET /task/{id}、POST /predict 三端點', priority: 'P1' },
            { label: 'momentum/factories.py', desc: '加入 create_lstm_engine() factory 函式', priority: 'P1' },
            { label: 'Mode C DataLoader', desc: 'H5 懶載入 Dataset，避免全量載入 OOM', priority: 'P1' },
            { label: 'WebSocket 即時 epoch 更新', desc: 'api/websocket/lstm_ws.py（對標 optimization_ws）', priority: 'P2' },
            { label: 'Optuna 超參數搜索', desc: '將 LSTM config 接入現有 Optuna 框架', priority: 'P2' },
            { label: 'Attention Heatmap', desc: 'Transformer 注意力權重視覺化面板', priority: 'P3' },
            { label: 'XGBoost + LSTM Ensemble', desc: '機率校準後加權融合（probability_calibrator 已有）', priority: 'P3' },
          ].map((item) => (
            <div key={item.label} className="flex items-start gap-2 p-2 rounded-lg bg-white/5 border border-white/10">
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full flex-shrink-0 mt-0.5 ${
                item.priority === 'P1' ? 'bg-amber-400/20 text-amber-400 border border-amber-400/30' :
                item.priority === 'P2' ? 'bg-blue-400/20 text-blue-400 border border-blue-400/30' :
                'bg-slate-400/20 text-slate-400 border border-slate-400/30'
              }`}>
                {item.priority}
              </span>
              <div>
                <div className="text-slate-300 font-mono">{item.label}</div>
                <div className="text-slate-500 mt-0.5">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── 訓練面板（骨幹） ── */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <h2 className="text-base font-medium text-slate-200">訓練面板</h2>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-400/15 text-amber-400 border border-amber-400/30">
            骨幹 — API 端點尚未建立
          </span>
        </div>
        <LSTMTrainingPanel />
      </div>
    </div>
  );
}
