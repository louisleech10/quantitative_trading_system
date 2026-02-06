'use client';

import React from 'react';
import { PieChart as RechartsPieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface PieChartData {
  name: string;
  value: number;
  color: string;
}

interface PieChartProps {
  data: PieChartData[];
  title: string;
  width?: number;
  height?: number;
}

// 預定義的顏色調色板
const COLORS = [
  '#60a5fa', '#fb7185', '#34d399', '#fbbf24', '#a78bfa',
  '#f472b6', '#22d3ee', '#fb923c', '#2dd4bf', '#818cf8',
  '#a3e635', '#c084fc', '#fb7185', '#38bdf8', '#e879f9'
];

export const PieChart: React.FC<PieChartProps> = ({ 
  data, 
  title, 
  width = 350, 
  height = 300 
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <p className="text-slate-400 text-sm">無數據</p>
      </div>
    );
  }

  // 計算總值用於百分比計算
  const totalValue = data.reduce((sum, item) => sum + item.value, 0);

  // 顯示所有數據，不進行過濾
  const significantData: PieChartData[] = data.map((item, index) => ({
    ...item,
    color: item.color || COLORS[index % COLORS.length]
  }));

  return (
    <div className="w-full" style={{ width, height }}>
      <h4 className="text-sm font-medium text-slate-200 mb-2 text-center">{title}</h4>
      {/* 增加上方的 padding 避免被切掉 */}
      <div style={{ paddingTop: '20px' }}>
        <ResponsiveContainer width="100%" height={height - 80}>
          <RechartsPieChart>
            <Pie
              data={significantData}
              cx="50%"
              cy="50%"
              outerRadius={75}
              innerRadius={0}
              fill="#60a5fa"
              dataKey="value"
              stroke="rgba(255,255,255,0.1)"
              strokeWidth={2}
            >
              {significantData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip 
              formatter={(value: number, name: string) => [
                `${value} 個案例 (${((value / totalValue) * 100).toFixed(1)}%)`, 
                name
              ]}
              contentStyle={{ 
                fontSize: '12px',
                backgroundColor: '#1a233a',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '6px'
              }}
            />
            <Legend 
              fontSize={11}
              wrapperStyle={{ 
                fontSize: '11px',
                paddingTop: '15px'
              }}
              layout="horizontal"
              align="center"
              verticalAlign="bottom"
              formatter={(value, entry: any) => {
                const percentage = ((entry.payload.value / totalValue) * 100).toFixed(0);
                return `${value} ${percentage}%`;
              }}
            />
          </RechartsPieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

// 優化後的市場階段圓餅圖組件
export const MarketPhasePieChart: React.FC<{
  positiveData: Record<string, number>;
  negativeData: Record<string, number>;
}> = ({ positiveData, negativeData }) => {
  // 定義市場階段顏色映射
  const marketPhaseColors: Record<string, string> = {
    'EXTREME_FEAR': '#fb7185',
    'FEAR': '#f43f5e',
    'NEUTRAL': '#fbbf24',
    'GREED': '#34d399',
    'EXTREME_GREED': '#22c55e'
  };

  const positiveChartData: PieChartData[] = Object.entries(positiveData).map(([phase, count]) => ({
    name: phase,
    value: count,
    color: marketPhaseColors[phase] || COLORS[0]
  }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData).map(([phase, count]) => ({
    name: phase,
    value: count,
    color: marketPhaseColors[phase] || COLORS[0]
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {positiveChartData.length > 0 && (
        <PieChart 
          data={positiveChartData} 
          title="正例市場階段分布" 
          width={350} 
          height={300}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart 
          data={negativeChartData} 
          title="反例市場階段分布" 
          width={350} 
          height={300}
        />
      )}
    </div>
  );
};

// 優化後的小時分布圓餅圖組件
export const HourDistributionPieChart: React.FC<{
  positiveData: Record<number, number>;
  negativeData: Record<number, number>;
}> = ({ positiveData, negativeData }) => {
  // 定義24小時顏色映射（使用漸變色）
  const hourColors: Record<number, string> = {
    0: '#60a5fa', 1: '#4f8fe8', 2: '#3a7ed6', 3: '#2b6dc4',
    4: '#60a5fa', 5: '#60a5fa', 6: '#93c5fd', 7: '#22d3ee',
    8: '#fbbf24', 9: '#fbbf24', 10: '#fb923c', 11: '#fb923c',
    12: '#fb7185', 13: '#f472b6', 14: '#c084fc', 15: '#a78bfa',
    16: '#34d399', 17: '#2dd4bf', 18: '#a3e635', 19: '#84cc16',
    20: '#38bdf8', 21: '#22d3ee', 22: '#818cf8', 23: '#e879f9'
  };

  const positiveChartData: PieChartData[] = Object.entries(positiveData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([hour, count]) => ({
      name: `${hour}:00`,
      value: count,
      color: hourColors[Number(hour)] || COLORS[0]
    }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([hour, count]) => ({
      name: `${hour}:00`,
      value: count,
      color: hourColors[Number(hour)] || COLORS[0]
    }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {positiveChartData.length > 0 && (
        <PieChart 
          data={positiveChartData} 
          title="正例小時分布" 
          width={350} 
          height={300}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart 
          data={negativeChartData} 
          title="反例小時分布" 
          width={350} 
          height={300}
        />
      )}
    </div>
  );
};

// 優化後的星期分布圓餅圖組件
export const DayOfWeekPieChart: React.FC<{
  positiveData: Record<number, number>;
  negativeData: Record<number, number>;
}> = ({ positiveData, negativeData }) => {
  const dayNames = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];

  // 定義星期顏色映射
  const dayColors: Record<string, string> = {
    '週日': '#fb7185',
    '週一': '#fb923c',
    '週二': '#fbbf24',
    '週三': '#a3e635',
    '週四': '#34d399',
    '週五': '#22d3ee',
    '週六': '#a78bfa'
  };

  // 處理星期數，將 7 轉換為 0（週日）
  const normalizeDayOfWeek = (day: number): number => {
    return day === 7 ? 0 : day;
  };

  const positiveChartData: PieChartData[] = Object.entries(positiveData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count]) => {
      const normalizedDay = normalizeDayOfWeek(Number(day));
      const dayName = dayNames[normalizedDay] || `星期${day}`;
      return {
        name: dayName,
        value: count,
        color: dayColors[dayName] || COLORS[0]
      };
    });

  const negativeChartData: PieChartData[] = Object.entries(negativeData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count]) => {
      const normalizedDay = normalizeDayOfWeek(Number(day));
      const dayName = dayNames[normalizedDay] || `星期${day}`;
      return {
        name: dayName,
        value: count,
        color: dayColors[dayName] || COLORS[0]
      };
    });

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {positiveChartData.length > 0 && (
        <PieChart
          data={positiveChartData}
          title="正例星期分布"
          width={350}
          height={300}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart
          data={negativeChartData}
          title="反例星期分布"
          width={350}
          height={300}
        />
      )}
    </div>
  );
};

// ===== 新增：市場分類分布圓餅圖組件 =====
export const MarketClassPieChart: React.FC<{
  positiveData: Record<string, number>;
  negativeData: Record<string, number>;
}> = ({ positiveData, negativeData }) => {
  // 定義市場分類顏色映射 (使用中文名稱)
  const marketClassColors: Record<string, string> = {
    '低位盤整': '#fb7185',
    '穩定震盪': '#fb7185',
    '溫和上漲': '#a3e635',
    '高位震盪': '#fbbf24',
    '標準盤整': '#a78bfa',
    '標準上漲': '#34d399',
    '活躍上漲': '#2dd4bf',
    '劇烈震盪': '#fb923c',
    '強勁上漲': '#fb923c',
    '強勁下跌': '#fb7185',
    '極端波動': '#e879f9',
    '其他組合': '#64748b',
    '混合': '#64748b'
  };

  const positiveChartData: PieChartData[] = Object.entries(positiveData).map(([marketClass, count]) => ({
    name: marketClass,
    value: count,
    color: marketClassColors[marketClass] || COLORS[0]
  }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData).map(([marketClass, count]) => ({
    name: marketClass,
    value: count,
    color: marketClassColors[marketClass] || COLORS[0]
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {positiveChartData.length > 0 && (
        <PieChart
          data={positiveChartData}
          title="正例市場分類分布"
          width={350}
          height={300}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart
          data={negativeChartData}
          title="反例市場分類分布"
          width={350}
          height={300}
        />
      )}
    </div>
  );
};

// ===== 新增：難度分布圓餅圖組件 =====
export const DifficultyPieChart: React.FC<{
  positiveData: Record<string, number>;
  negativeData: Record<string, number>;
}> = ({ positiveData, negativeData }) => {
  // 定義難度顏色映射
  const difficultyColors: Record<string, string> = {
    '簡單': '#34d399',
    '中等': '#fbbf24',
    '困難': '#fb923c',
    '混合': '#64748b'
  };

  const positiveChartData: PieChartData[] = Object.entries(positiveData).map(([difficulty, count]) => ({
    name: difficulty,
    value: count,
    color: difficultyColors[difficulty] || COLORS[0]
  }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData).map(([difficulty, count]) => ({
    name: difficulty,
    value: count,
    color: difficultyColors[difficulty] || COLORS[0]
  }));

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {positiveChartData.length > 0 && (
        <PieChart
          data={positiveChartData}
          title="正例難度分布"
          width={350}
          height={300}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart
          data={negativeChartData}
          title="反例難度分布"
          width={350}
          height={300}
        />
      )}
    </div>
  );
};
