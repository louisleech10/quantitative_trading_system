'use client';

import { useEffect, useMemo, useState } from 'react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { useFeatureFactory } from '@/hooks/useFeatureFactory';
import { exportChartToPNG } from '@/lib/exportUtils';
import FeatureNameSegmentFilter from '@/components/feature-factory/FeatureNameSegmentFilter';
import type { VifRow } from '@/lib/types';

interface FeatureCorrelationHeatmapProps {
  taskId: string;
}

const methods: Array<'pearson' | 'spearman' | 'kendall'> = ['pearson', 'spearman', 'kendall'];
const FEATURE_NAME_LIMIT = 1000000;

/**
 * 業界標準 RdBu_r 色彩映射（與 matplotlib/seaborn 一致）:
 *   -1 → 深藍 (5,48,97)   ← 負相關
 *    0 → 近白 (247,247,247) ← 無相關
 *   +1 → 深紅 (103,0,31)  ← 正相關
 */
const getRdBuColor = (value: number): { bg: string; textColor: string } => {
  const v = Math.max(-1, Math.min(1, value));
  let r: number, g: number, b: number;
  if (v >= 0) {
    r = Math.round(247 + v * (103 - 247));
    g = Math.round(247 + v * (0 - 247));
    b = Math.round(247 + v * (31 - 247));
  } else {
    const t = -v;
    r = Math.round(247 + t * (5 - 247));
    g = Math.round(247 + t * (48 - 247));
    b = Math.round(247 + t * (97 - 247));
  }
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  const textColor = luminance > 0.6 ? '#1e293b' : '#f1f5f9';
  return { bg: `rgb(${r},${g},${b})`, textColor };
};

/** 依本系統 7-segment 命名慣例產生短標籤 */
const shortLabel = (name: string, full = false): string => {
  if (full) return name;
  const parts = name.split('_');
  if (parts.length <= 4) return name;
  const indicator = parts[3] ?? parts[2];
  const tail = parts.slice(-2).join('_');
  if (tail.startsWith(indicator)) return tail;
  return `${indicator}_…_${tail}`;
};

/** 三種相關係數的特性說明 */
const METHOD_INFO: Record<
  string,
  { formula: string; steps: string[]; pros: string; cons: string; whyNotDefault?: string; recommend?: boolean }
> = {
  pearson: {
    formula: 'ρ = Cov(X,Y) / (σ_X × σ_Y)',
    steps: [
      '① 計算每個時間點的 X̄（均值）、Ȳ',
      '② Cov(X,Y) = Σ(Xᵢ−X̄)(Yᵢ−Ȳ) / n　← 共變異數',
      '③ σ_X = √Var(X)，σ_Y = √Var(Y)　← 標準差',
      '④ ρ = Cov / (σ_X × σ_Y)，值域 [−1, +1]',
      '例：X=[1,2,3]，Y=[2,4,5]  →  ρ ≈ 0.98（強線性正相關）',
    ],
    pros: '計算最快（O(n)），直覺理解線性相關強度',
    cons: '對異常值/肥尾極度敏感；只捕捉線性關係；假設常態分佈——量化因子通常非常態',
    recommend: false,
  },
  spearman: {
    formula: 'ρ_s = 1 − 6Σd²/[n(n²−1)]　d = rank(Xᵢ) − rank(Yᵢ)',
    steps: [
      '① 把 X 的每個值換成它的「排名」→ rank_X',
      '② 同樣對 Y 做排名 → rank_Y',
      '③ d = rank_X − rank_Y（每筆差值）',
      '④ 代入公式得 ρ_s',
      '例：X=[1,2,3]，rank=[1,2,3]；Y=[4,1,3]，rank=[3,1,2] → d=[−2,1,1] → ρ_s = 0.5',
    ],
    pros: 'rank-based 對極端值免疫；捕捉「單調」關係（不限線性）；無常態分佈假設',
    cons: '資料量極大時比 Pearson 稍慢（但可接受）',
    recommend: true,
  },
  kendall: {
    formula: 'τ = (C − D) / C(n,2)　C=一致對數，D=不一致對數，C(n,2)=n(n−1)/2',
    steps: [
      '① 取所有 ½n(n−1) 個資料對 (i,j)，i < j',
      '② 若 Xᵢ<Xⱼ 且 Yᵢ<Yⱼ（或都大）→ 一致對 C+1',
      '③ 否則（Xᵢ<Xⱼ 但 Yᵢ>Yⱼ）→ 不一致對 D+1',
      '④ τ = (C−D) / (總對數)，值域 [−1, +1]',
      '例：n=4 → 6對；若 C=5, D=1 → τ = 4/6 ≈ 0.67',
    ],
    pros: '統計上最穩健，ties（相同值）處理最準確，小樣本 p-value 更可信',
    cons: '計算複雜度 O(n²)——1000 筆 × 100 特徵 = 億級比較，幾分鐘起跳',
    whyNotDefault: 'Kendall 統計穩健性最強，但在量化場景中因子動輒數萬行×幾千個，O(n²) 的時間代價讓互動式分析完全無法接受。Spearman 同為 rank-based（穩健性接近），但 O(n log n) 快得多，是業界共識的平衡選擇。',
    recommend: false,
  },
};

export default function FeatureCorrelationHeatmap({ taskId }: FeatureCorrelationHeatmapProps) {
  const { explorerSelectedFeatures, setExplorerSelectedFeatures } = useFeatureFactoryStore();
  const sharedFeatureNames = useFeatureFactoryStore((state) => state.explorerFeatureNamesByTask[taskId]);
  const { browseCorrelation, browseFeatures, browseVif } = useFeatureFactory();
  const [method, setMethod] = useState<'pearson' | 'spearman' | 'kendall'>('spearman');
  const [available, setAvailable] = useState<string[]>([]);
  const [filteredAvailable, setFilteredAvailable] = useState<string[]>([]);
  const [matrix, setMatrix] = useState<number[][]>([]);
  const [labels, setLabels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFullLabels, setShowFullLabels] = useState(false);
  const [showMethodInfo, setShowMethodInfo] = useState(false);
  const [vifRows, setVifRows] = useState<VifRow[]>([]);
  const [vifLoading, setVifLoading] = useState(false);
  const [vifError, setVifError] = useState<string | null>(null);
  const [showVifDetail, setShowVifDetail] = useState(false);

  useEffect(() => {
    let active = true;
    if (sharedFeatureNames) {
      setAvailable(sharedFeatureNames);
      return;
    }

    browseFeatures(taskId, { offset: 0, limit: FEATURE_NAME_LIMIT, sortBy: 'name', sortOrder: 'asc', detailLevel: 'names' })
      .then((resp) => {
        if (!active) return;
        setAvailable(resp.features.map((item) => item.name));
      })
      .catch(() => {
        if (!active) return;
        setAvailable([]);
      });

    return () => {
      active = false;
    };
  }, [browseFeatures, taskId, sharedFeatureNames]);

  const selected = useMemo(() => Array.from(new Set(explorerSelectedFeatures)).slice(0, 50), [explorerSelectedFeatures]);

  useEffect(() => {
    if (selected.length < 2) {
      setMatrix([]);
      setLabels([]);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    browseCorrelation(taskId, selected, method)
      .then((resp) => {
        if (!active) return;
        setLabels(resp.features);
        setMatrix(resp.matrix);
      })
      .catch((err) => {
        if (!active) return;
        setError(err instanceof Error ? err.message : '載入相關矩陣失敗');
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseCorrelation, taskId, selected, method]);

  // VIF：與相關矩陣同步，選中特徵 ≥ 2 時自動計算
  useEffect(() => {
    if (selected.length < 2) {
      setVifRows([]);
      return;
    }

    let active = true;
    setVifLoading(true);

    setVifError(null);
    browseVif(taskId, selected)
      .then((resp) => {
        if (!active) return;
        setVifRows(resp.items);
        setVifError(null);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setVifRows([]);
        setVifError(err instanceof Error ? err.message : '無法取得 VIF 資料，請確認後端服務已重啟');
      })
      .finally(() => {
        if (!active) return;
        setVifLoading(false);
      });

    return () => {
      active = false;
    };
  }, [browseVif, taskId, selected]);

  const toggleFeature = (feature: string) => {
    const current = new Set(explorerSelectedFeatures);
    if (current.has(feature)) {
      current.delete(feature);
      setExplorerSelectedFeatures(Array.from(current));
      return;
    }
    if (current.size >= 50) return;
    current.add(feature);
    setExplorerSelectedFeatures(Array.from(current));
  };

  // 根據特徵數量自動配置格子大小
  const n = labels.length;
  const showNumbers = n > 0 && n <= 15;
  const cellPx = n <= 15 ? 44 : n <= 30 ? 26 : 16;
  // 全名模式：行標籤加寬；欄標籤改直排 (-90°)，需要更高的 header row
  const labelColW = showFullLabels ? 200 : 110;
  const headerRowH = showFullLabels ? 160 : 96;

  return (
    <div className="glass-panel rounded-2xl p-4 space-y-3">
      {/* ── 工具列 ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="text-sm text-slate-300">Correlation Heatmap（最多 50）</div>
        <button
          onClick={() => {
            const picks = filteredAvailable.filter((name) => name.startsWith('ms_')).slice(0, 50);
            setExplorerSelectedFeatures(picks);
          }}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200 hover:bg-white/5"
        >
          選取 Microstructure
        </button>
        <button
          onClick={() => {
            setExplorerSelectedFeatures(filteredAvailable.slice(0, 20));
          }}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200 hover:bg-white/5"
        >
          前 20
        </button>
        <select
          value={method}
          onChange={(e) => setMethod(e.target.value as 'pearson' | 'spearman' | 'kendall')}
          className="ml-auto rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-slate-100"
        >
          {methods.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <button
          onClick={() => setShowFullLabels((v) => !v)}
          className={`text-xs px-2 py-1 rounded border hover:bg-white/5 ${
            showFullLabels ? 'border-sky-400/60 text-sky-300' : 'border-white/10 text-slate-200'
          }`}
          title="切換完整特徵名 / 短名顯示"
        >
          {showFullLabels ? '短名' : '全名'}
        </button>
        <button
          onClick={() => exportChartToPNG('feature-correlation-heatmap', 'feature_correlation', taskId)}
          className="text-xs px-2 py-1 rounded border border-white/10 text-slate-200 hover:bg-white/5"
        >
          匯出 PNG
        </button>
        {selected.length > 0 && (
          <button
            onClick={() => setExplorerSelectedFeatures([])}
            className="text-xs px-2 py-1 rounded border border-rose-400/40 text-rose-300 hover:bg-rose-400/10"
            title="取消所有已選特徵"
          >
            ✕ 清除全部選取（{selected.length}）
          </button>
        )}
        <button
          onClick={() => setShowMethodInfo((v) => !v)}
          className={`text-xs px-2 py-1 rounded border hover:bg-white/5 ${
            showMethodInfo ? 'border-violet-400/60 text-violet-300' : 'border-white/10 text-slate-400'
          }`}
          title="顯示 Pearson / Spearman / Kendall 說明"
        >
          ？方法說明
        </button>
      </div>

      {/* ── 方法說明面板 ── */}
      {showMethodInfo && (
        <div className="rounded-xl border border-white/10 bg-slate-900/60 p-4 space-y-3">
          <div className="text-sm font-semibold text-slate-100">三種相關係數比較</div>
          {methods.map((m) => {
            const info = METHOD_INFO[m];
            const isActive = method === m;
            return (
              <div
                key={m}
                className={`rounded-lg p-3 text-xs space-y-1.5 border ${
                  isActive
                    ? 'border-amber-400/50 bg-amber-400/8'
                    : 'border-white/8 bg-white/3'
                }`}
              >
                {/* 標題列 */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`font-bold text-sm ${isActive ? 'text-amber-300' : 'text-slate-100'}`}>
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </span>
                  {info.recommend && (
                    <span className="bg-emerald-500/20 text-emerald-300 text-[10px] px-1.5 py-0.5 rounded-full border border-emerald-400/30">
                      ★ 量化推薦
                    </span>
                  )}
                  {isActive && (
                    <span className="bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.5 rounded-full border border-amber-400/30">
                      目前使用
                    </span>
                  )}
                </div>

                {/* 公式 */}
                <div className="font-mono text-sky-300 bg-slate-800/60 rounded px-2 py-1 text-[11px] tracking-wide">
                  {info.formula}
                </div>

                {/* 計算步驟 */}
                <div className="space-y-0.5">
                  <div className="text-slate-400 text-[10px] font-semibold uppercase tracking-wider">計算步驟</div>
                  {info.steps.map((step, i) => (
                    <div key={i} className="text-slate-300 text-[11px] leading-relaxed pl-1">{step}</div>
                  ))}
                </div>

                {/* 優缺點 */}
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <div>
                    <div className="text-[10px] text-emerald-400/70 font-semibold mb-0.5">優點</div>
                    <div className="text-emerald-300 text-[11px] leading-relaxed">{info.pros}</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-rose-400/70 font-semibold mb-0.5">缺點</div>
                    <div className="text-rose-300 text-[11px] leading-relaxed">{info.cons}</div>
                  </div>
                </div>

                {/* Kendall 專屬：為何不推薦 */}
                {info.whyNotDefault && (
                  <div className="rounded border border-amber-400/20 bg-amber-400/5 px-2 py-1.5 text-[11px] text-amber-200/80">
                    <span className="font-semibold text-amber-300">為何不推薦？ </span>
                    {info.whyNotDefault}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── 特徵名稱篩選 ── */}
      <FeatureNameSegmentFilter features={available} onFilteredFeaturesChange={setFilteredAvailable} />
      <div className="flex gap-3 min-w-0">
        <div className="w-72 shrink-0">
          {/* ── 特徵選取標籤 ── */}
          <div className="max-h-[560px] overflow-y-auto rounded border border-white/5 bg-black/20 py-1">
            {/* 已選但不在篩選前 500 裡的特徵：固定置頂 */}
            {selected
              .filter((name) => !filteredAvailable.slice(0, 500).includes(name))
              .map((name) => (
                <button
                  key={`pinned-${name}`}
                  onClick={() => toggleFeature(name)}
                  title={name}
                  className="w-full text-left truncate text-xs px-2 py-1 rounded bg-amber-400/20 text-amber-200"
                >
                  {name} ✕
                </button>
              ))}
            {filteredAvailable.slice(0, 500).map((name) => (
              <button
                key={name}
                onClick={() => toggleFeature(name)}
                title={name}
                className={`w-full text-left truncate text-xs px-2 py-1 rounded ${
                  selected.includes(name) ? 'bg-amber-400/20 text-amber-200' : 'text-slate-300 hover:bg-white/5'
                }`}
              >
                {name}
              </button>
            ))}
          </div>
        </div>
        <div className="flex-1 min-w-0">
          {/* ── 熱力圖主體 ── */}
      {loading ? (
        <div className="text-xs text-slate-400">載入中...</div>
      ) : error ? (
        <div className="text-xs text-rose-300">{error}</div>
      ) : matrix.length === 0 ? (
        <div className="text-xs text-slate-400">請至少選擇 2 個特徵。</div>
      ) : (
        <div id="feature-correlation-heatmap" className="overflow-auto space-y-3">
          {/* 高相關警示摘要 */}
          {(() => {
            const highCorrPairs: Array<{ a: string; b: string; v: number }> = [];
            matrix.forEach((row, ri) =>
              row.forEach((val, ci) => {
                if (ci > ri && Math.abs(val) >= 0.8) {
                  highCorrPairs.push({ a: labels[ri], b: labels[ci], v: val });
                }
              }),
            );
            if (highCorrPairs.length === 0) return null;
            return (
              <div className="rounded-lg border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-300">
                ⚠ 高相關對（|ρ| ≥ 0.8）共 {highCorrPairs.length} 組 — 建議每組只保留 IC 較高的因子
                <span className="ml-2 text-amber-400/70">
                  {highCorrPairs.slice(0, 3).map((p) => `${shortLabel(p.a, false)}↔${shortLabel(p.b, false)}(${p.v.toFixed(2)})`).join('、')}
                  {highCorrPairs.length > 3 ? ` 等` : ''}
                </span>
              </div>
            );
          })()}

          {/* 矩陣：行標籤 + 欄標籤 + 格子 */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `${labelColW}px repeat(${n}, ${cellPx}px)`,
              gridTemplateRows: `${headerRowH}px repeat(${n}, ${cellPx}px)`,
              gap: '2px',
            }}
          >
            {/* 左上角空格 */}
            <div />

            {/* 欄標籤：全名模式用 -90°（直立），短名模式用 -45° */}
            {labels.map((name) => (
              <div
                key={`col-${name}`}
                title={name}
                style={{ height: headerRowH, display: 'flex', alignItems: 'flex-end', justifyContent: 'center' }}
              >
                <div
                  style={{
                    transform: showFullLabels ? 'rotate(-90deg)' : 'rotate(-45deg)',
                    transformOrigin: showFullLabels ? 'center center' : 'bottom center',
                    whiteSpace: 'nowrap',
                    fontSize: 10,
                    color: '#94a3b8',
                    maxWidth: showFullLabels ? 150 : 90,
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    lineHeight: 1,
                    marginBottom: showFullLabels ? 0 : 4,
                  }}
                >
                  {shortLabel(name, showFullLabels)}
                </div>
              </div>
            ))}

            {/* 每一列：行標籤 + 格子 */}
            {matrix.map((row, rowIndex) => (
              <>
                {/* 行標籤 */}
                <div
                  key={`row-label-${rowIndex}`}
                  title={labels[rowIndex]}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    paddingRight: 6,
                    fontSize: 10,
                    color: '#94a3b8',
                    overflow: 'hidden',
                    whiteSpace: 'nowrap',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {shortLabel(labels[rowIndex], showFullLabels)}
                </div>

                {/* 格子 */}
                {row.map((value, colIndex) => {
                  const { bg, textColor } = getRdBuColor(value);
                  const isDiag = rowIndex === colIndex;
                  const isHighCorr = !isDiag && Math.abs(value) >= 0.8;
                  return (
                    <div
                      key={`${rowIndex}-${colIndex}`}
                      title={`${labels[rowIndex]} ↔ ${labels[colIndex]}\nρ = ${value.toFixed(4)}`}
                      style={{
                        backgroundColor: bg,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 9,
                        fontWeight: 600,
                        color: showNumbers ? textColor : undefined,
                        outline: isHighCorr ? '2px solid rgba(251,191,36,0.85)' : undefined,
                        outlineOffset: '-1px',
                        borderRadius: 2,
                      }}
                    >
                      {showNumbers && !isDiag ? value.toFixed(2) : null}
                      {showNumbers && isDiag ? '1' : null}
                    </div>
                  );
                })}
              </>
            ))}
          </div>

          {/* 色階說明條 */}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[10px] text-slate-500">-1</span>
            <div
              style={{
                flex: 1,
                height: 10,
                borderRadius: 4,
                background: 'linear-gradient(to right, rgb(5,48,97), rgb(103,169,207), rgb(247,247,247), rgb(214,96,77), rgb(103,0,31))',
              }}
            />
            <span className="text-[10px] text-slate-500">+1</span>
            <span className="text-[10px] text-slate-500 ml-3">藍=負相關 · 白=無相關 · 紅=正相關</span>
          </div>

          <div className="flex items-center gap-4 text-[11px] text-slate-400">
            <span>選中 {n} 個特徵</span>
            <span className="flex items-center gap-1">
              <span
                style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, outline: '2px solid rgba(251,191,36,0.85)' }}
              />
              ｜ρ｜≥ 0.8（高相關，建議去冗餘）
            </span>
          </div>
        </div>
      )}

      {/* ── VIF 共線性診斷表 ── */}
      {selected.length >= 2 && (
        <div className="rounded-xl border border-slate-600/40 bg-slate-900/60 p-4 space-y-3">
          {/* 標題列 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-100">VIF 共線性診斷</span>
              {vifLoading && (
                <span className="text-[11px] text-slate-400 animate-pulse">計算中...</span>
              )}
            </div>
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-emerald-400">● &lt;5 穩定</span>
              <span className="text-amber-400">● 5-10 警告</span>
              <span className="text-rose-400">● &gt;10 嚴重</span>
            </div>
          </div>

          {/* 錯誤提示 */}
          {vifError && !vifLoading && (
            <div className="rounded-lg border border-rose-400/30 bg-rose-400/8 px-3 py-2 text-[11px] text-rose-300">
              ⚠ {vifError}
            </div>
          )}

          {/* 無資料（無錯誤情況） */}
          {vifRows.length === 0 && !vifLoading && !vifError && (
            <div className="text-[11px] text-slate-400">無資料</div>
          )}

          {/* 表格 */}
          {vifRows.length > 0 && (
            <div className="max-h-52 overflow-auto rounded-lg border border-white/8">
              <table className="w-full text-[12px]">
                <thead className="sticky top-0 bg-slate-800/90">
                  <tr className="text-slate-300 border-b border-white/10">
                    <th className="text-left py-2 px-3 font-medium">特徵名稱</th>
                    <th className="text-right py-2 px-3 font-medium w-20">VIF 值</th>
                    <th className="text-center py-2 px-3 font-medium w-24">狀態</th>
                  </tr>
                </thead>
                <tbody>
                  {vifRows.map((row, idx) => (
                    <tr
                      key={row.feature_name}
                      className={`border-b border-white/5 ${idx % 2 === 0 ? 'bg-white/2' : ''}`}
                    >
                      <td className="py-2 px-3 leading-tight" title={row.feature_name}>
                        <div className="text-slate-100 font-medium text-[13px]">
                          {shortLabel(row.feature_name)}
                        </div>
                        <div className="text-slate-400 text-[11px] mt-0.5 break-all leading-snug">
                          {row.feature_name}
                        </div>
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-bold text-slate-100 tabular-nums text-[14px]">
                        {row.vif.toFixed(2)}
                      </td>
                      <td className="py-2 px-3 text-center">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${
                            row.status === 'stable'
                              ? 'text-emerald-200 bg-emerald-500/20 border-emerald-400/40'
                              : row.status === 'warning'
                                ? 'text-amber-200 bg-amber-500/20 border-amber-400/40'
                                : 'text-rose-200 bg-rose-500/20 border-rose-400/40'
                          }`}
                        >
                          {row.status === 'stable' ? '✓ 穩定' : row.status === 'warning' ? '⚠ 警告' : '✗ 嚴重'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* VIF 計算原理說明（可縮合） */}
          <div className="rounded-lg border border-sky-400/20 bg-sky-400/5">
            {/* 標題列（點擊展開/收合） */}
            <button
              onClick={() => setShowVifDetail((v) => !v)}
              className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-sky-400/5 rounded-lg transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-sky-300 font-semibold text-[12px]">VIF 是怎麼計算的？</span>
                <span className="text-[10px] text-sky-400/60 border border-sky-400/20 rounded px-1.5 py-0.5">業界標準</span>
              </div>
              <span className="text-slate-400 text-[11px]">{showVifDetail ? '▲ 收合' : '▼ 展開'}</span>
            </button>

            {showVifDetail && (
              <div className="px-3 pb-3 space-y-3 text-[12px] text-slate-300 leading-relaxed border-t border-sky-400/10 pt-2.5">

                {/* 計算方法 */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">計算方法</div>
                  <div>
                    <span className="text-slate-400">方法一（直覺）：</span>
                    把第 i 個特徵當成「應變數」，用其他所有特徵做線性迴歸得到 R²，
                    則 <span className="font-mono text-sky-300">VIF_i = 1 / (1 − R²_i)</span>。
                    R² 越高（越可被其他特徵線性替代）→ VIF 越大。
                  </div>
                  <div>
                    <span className="text-slate-400">方法二（矩陣法，本系統採用 ✓）：</span>
                    <span className="font-mono text-sky-300 mx-1">VIF = diag(R⁻¹)</span>
                    R 為 Pearson 相關矩陣，取偽逆的對角元素——與方法一完全等價，一次算出全部特徵，
                    是 statsmodels、pandas 等主流函式庫的實作方式，亦是量化業界標準做法。
                  </div>
                  <div className="rounded border border-white/8 bg-slate-800/60 px-3 py-2 font-mono text-[11px] text-slate-200 space-y-0.5">
                    <div className="text-slate-400 mb-1">數值範例（A、B 高度相關，C 獨立）：</div>
                    <div>R = [[1, 0.9, 0.1],</div>
                    <div className="pl-4">[0.9, 1, 0.1],</div>
                    <div className="pl-4">[0.1, 0.1, 1]]</div>
                    <div className="mt-1">R⁻¹ 對角 → <span className="text-amber-300">VIF = [5.26, 5.26, 1.02]</span></div>
                    <div className="text-slate-400 text-[10px] mt-1">A、B 互相關 0.9 → VIF 5.26（警告）；C 獨立 → VIF ≈ 1（穩定）</div>
                  </div>
                </div>

                {/* 標準操作流程 */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">標準去除流程（迭代）</div>
                  <div className="space-y-1">
                    {[
                      { step: '①', text: '計算所有選中特徵的 VIF' },
                      { step: '②', text: '找出 VIF 最大且 > 10 的特徵' },
                      { step: '③', text: '對比它與相關特徵的 IC 值 → 移除 IC 較低的那個' },
                      { step: '④', text: '重新計算剩餘特徵的 VIF（移掉一個後數值會連帶變化）' },
                      { step: '⑤', text: '重複 ②–④，直到所有 VIF < 10' },
                    ].map(({ step, text }) => (
                      <div key={step} className="flex items-start gap-2">
                        <span className="text-sky-400 font-mono font-bold shrink-0">{step}</span>
                        <span className="text-slate-300">{text}</span>
                      </div>
                    ))}
                  </div>
                  <div className="rounded border border-amber-400/20 bg-amber-400/5 px-3 py-2 text-[11px] text-amber-200">
                    ⚠ 為何要一個一個移除，而非一次全刪？若 A 的 VIF=15 是因為 A≈B+C，
                    刪掉 B 後 C 的 VIF 可能從 8 降到 2。一次全刪反而損失有效因子。
                  </div>
                </div>

                {/* 閾值 */}
                <div className="flex items-center gap-4 pt-0.5 text-[11px]">
                  <span className="text-emerald-400">VIF &lt; 5 → 穩定，可入模</span>
                  <span className="text-amber-400">5–10 → 警告，考慮移除</span>
                  <span className="text-rose-400">&gt;10 → 嚴重，強烈建議移除</span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
        </div>
      </div>
    </div>
  );
}
