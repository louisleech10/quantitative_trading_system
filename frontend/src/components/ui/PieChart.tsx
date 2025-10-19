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
  '#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00',
  '#ff00ff', '#00ffff', '#ff0000', '#0000ff', '#ffff00',
  '#ffa500', '#800080', '#008000', '#ff69b4', '#40e0d0'
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
        <p className="text-gray-500 text-sm">無數據</p>
      </div>
    );
  }

  // 計算總值用於百分比計算
  const totalValue = data.reduce((sum, item) => sum + item.value, 0);
  
  // 過濾數據：只顯示佔比大於3%的數據，其餘合併為"其他"
  const threshold = totalValue * 0.03; // 3%閾值
  const significantData: PieChartData[] = [];
  let otherValue = 0;
  
  data.forEach((item, index) => {
    if (item.value >= threshold) {
      significantData.push({
        ...item,
        color: item.color || COLORS[index % COLORS.length]
      });
    } else {
      otherValue += item.value;
    }
  });
  
  // 如果有小比例數據，添加"其他"類別
  if (otherValue > 0) {
    significantData.push({
      name: '其他',
      value: otherValue,
      color: '#d1d5db' // 灰色
    });
  }

  return (
    <div className="w-full" style={{ width, height }}>
      <h4 className="text-sm font-medium text-gray-700 mb-2 text-center">{title}</h4>
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
              fill="#8884d8"
              dataKey="value"
              stroke="#fff"
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
                backgroundColor: '#f9fafb',
                border: '1px solid #e5e7eb',
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
    'EXTREME_FEAR': '#dc2626',  // 深紅色
    'FEAR': '#ef4444',          // 紅色
    'NEUTRAL': '#ffc658',       // 黃色
    'GREED': '#82ca9d',         // 綠色
    'EXTREME_GREED': '#22c55e'  // 深綠色
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
    0: '#1e3a8a', 1: '#1e40af', 2: '#1d4ed8', 3: '#2563eb',
    4: '#3b82f6', 5: '#60a5fa', 6: '#93c5fd', 7: '#dbeafe',
    8: '#fef3c7', 9: '#fde68a', 10: '#fcd34d', 11: '#fbbf24',
    12: '#f59e0b', 13: '#f97316', 14: '#fb923c', 15: '#fdba74',
    16: '#fed7aa', 17: '#ffedd5', 18: '#fce7f3', 19: '#fbcfe8',
    20: '#f9a8d4', 21: '#f472b6', 22: '#ec4899', 23: '#db2777'
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
    '週日': '#ef4444',  // 紅色
    '週一': '#f97316',  // 橙色
    '週二': '#f59e0b',  // 琥珀色
    '週三': '#84cc16',  // 萊姆色
    '週四': '#22c55e',  // 綠色
    '週五': '#06b6d4',  // 青色
    '週六': '#8b5cf6'   // 紫色
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
  // 定義市場分類顏色映射 (C1-C12)
  const marketClassColors: Record<string, string> = {
    'C1': '#dc2626',   // 深紅色 (低波動+下降+異常低量)
    'C2': '#ef4444',   // 紅色 (低波動+下降+正常量)
    'C3': '#f87171',   // 淺紅色 (低波動+下降+異常高量)
    'C4': '#fbbf24',   // 黃色 (低波動+橫盤)
    'C5': '#84cc16',   // 淺綠色 (低波動+上升+異常低量)
    'C6': '#22c55e',   // 綠色 (低波動+上升+正常量)
    'C7': '#10b981',   // 深綠色 (低波動+上升+異常高量)
    'C8': '#f97316',   // 橙色 (高波動+劇烈波動+異常低量)
    'C9': '#fb923c',   // 淺橙色 (高波動+劇烈波動+正常量)
    'C10': '#fdba74',  // 極淺橙色 (高波動+劇烈波動+異常高量)
    'C11': '#8b5cf6',  // 紫色 (中波動組合)
    'C12': '#a78bfa'   // 淺紫色 (其他組合)
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
    '簡單': '#82ca9d',  // 綠色
    '中等': '#ffc658',  // 橙色
    '困難': '#ff7300',  // 深橙色
    '混合': '#d1d5db'   // 灰色
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
