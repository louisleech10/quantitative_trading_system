// frontend/src/components/pattern/FeatureImportanceChart.tsx
/**
 * FeatureImportanceChart.tsx
 * 
 * 顯示 XGBoost 特徵重要性條形圖
 * 
 * Features:
 * - 水平條形圖顯示前 N 個重要特徵
 * - 顏色編碼（前3名使用不同顏色）
 * - 可切換重要性計算方法（gain/weight/cover）
 * - PNG 匯出功能
 */

'use client';

import React, { useRef, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import html2canvas from 'html2canvas';
import type { FeatureImportance } from '@/lib/patternTypes';

interface Props {
  featureImportance: FeatureImportance[];
  topN?: number;
}

export default function FeatureImportanceChart({ featureImportance, topN = 10 }: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const [method, setMethod] = useState<string>('gain');
  
  // 只取前 N 個
  const data = featureImportance
    .filter(fi => fi.method === method)
    .slice(0, topN)
    .map(fi => ({
      feature: fi.feature,
      importance: fi.importance,
      rank: fi.rank
    }));
  
  const handleExportPNG = () => {
    if (!chartRef.current) return;
    
    html2canvas(chartRef.current).then(canvas => {
      const link = document.createElement('a');
      link.download = `feature_importance_${Date.now()}.png`;
      link.href = canvas.toDataURL();
      link.click();
    });
  };
  
  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        沒有特徵重要性資料
      </div>
    );
  }
  
  // 定義顏色（前3名使用特殊顏色）
  const getColor = (rank: number) => {
    if (rank === 1) return '#fb7185'; // rose-400
    if (rank === 2) return '#fb923c'; // orange-400
    if (rank === 3) return '#fbbf24'; // amber-400
    return '#60a5fa'; // blue-400
  };
  
  return (
    <div className="glass-panel rounded-xl border border-white/10 p-4">
      {/* 標題與控制 */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-100">特徵重要性 (Top {topN})</h3>
        <div className="flex gap-2 items-center">
          {/* 方法選擇 */}
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="px-3 py-1 border border-white/10 rounded text-sm bg-slate-900/60 text-slate-200"
          >
            <option value="gain">Gain</option>
            <option value="weight">Weight</option>
            <option value="cover">Cover</option>
          </select>
          
          {/* 匯出按鈕 */}
          <button
            onClick={handleExportPNG}
            className="px-3 py-1 bg-emerald-500/20 text-emerald-100 border border-emerald-500/40 text-sm rounded hover:bg-emerald-500/30"
          >
            匯出 PNG
          </button>
        </div>
      </div>
      
      {/* 圖表 */}
      <div ref={chartRef}>
        <ResponsiveContainer width="100%" height={400}>
          <BarChart 
            data={data} 
            layout="vertical"
            margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 'auto']} />
            <YAxis dataKey="feature" type="category" width={90} />
            <Tooltip 
              content={<CustomTooltip />}
              cursor={{ fill: 'rgba(96, 165, 250, 0.1)' }}
            />
            <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getColor(entry.rank)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      
      {/* 說明 */}
      <div className="mt-4 text-xs text-slate-400">
        <p>🔴 第1名 | 🟠 第2名 | 🟡 第3名 | 🔵 其他</p>
        <p className="mt-1">重要性值已正規化，總和為 1</p>
      </div>
    </div>
  );
}

// 自訂 Tooltip
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || payload.length === 0) return null;
  
  const data = payload[0].payload;
  
  return (
    <div className="bg-[#1a233a] p-3 border border-white/10 rounded shadow-xl shadow-black/30">
      <p className="font-semibold text-slate-100 mb-1">排名 #{data.rank}</p>
      <p className="text-sm text-slate-300 mb-1">{data.feature}</p>
      <p className="text-sm text-slate-200">
        重要性: <span className="font-semibold text-slate-100">{(data.importance * 100).toFixed(2)}%</span>
      </p>
    </div>
  );
}
