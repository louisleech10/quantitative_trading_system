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
  const positiveChartData: PieChartData[] = Object.entries(positiveData).map(([phase, count], index) => ({
    name: phase,
    value: count,
    color: COLORS[index % COLORS.length]
  }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData).map(([phase, count], index) => ({
    name: phase,
    value: count,
    color: COLORS[index % COLORS.length]
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
  const positiveChartData: PieChartData[] = Object.entries(positiveData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([hour, count], index) => ({
      name: `${hour}:00`,
      value: count,
      color: COLORS[index % COLORS.length]
    }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([hour, count], index) => ({
      name: `${hour}:00`,
      value: count,
      color: COLORS[index % COLORS.length]
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
  
  // 處理星期數，將 7 轉換為 0（週日）
  const normalizeDayOfWeek = (day: number): number => {
    return day === 7 ? 0 : day;
  };
  
  const positiveChartData: PieChartData[] = Object.entries(positiveData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count], index) => {
      const normalizedDay = normalizeDayOfWeek(Number(day));
      return {
        name: dayNames[normalizedDay] || `星期${day}`,
        value: count,
        color: COLORS[index % COLORS.length]
      };
    });

  const negativeChartData: PieChartData[] = Object.entries(negativeData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count], index) => {
      const normalizedDay = normalizeDayOfWeek(Number(day));
      return {
        name: dayNames[normalizedDay] || `星期${day}`,
        value: count,
        color: COLORS[index % COLORS.length]
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
