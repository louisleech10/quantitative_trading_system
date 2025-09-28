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
  width = 300, 
  height = 300 
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ width, height }}>
        <p className="text-gray-500 text-sm">無數據</p>
      </div>
    );
  }

  // 為數據分配顏色
  const dataWithColors = data.map((item, index) => ({
    ...item,
    color: item.color || COLORS[index % COLORS.length]
  }));

  return (
    <div className="w-full">
      <h4 className="text-sm font-medium text-gray-700 mb-2 text-center">{title}</h4>
      <ResponsiveContainer width="100%" height={height}>
        <RechartsPieChart>
          <Pie
            data={dataWithColors}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {dataWithColors.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip 
            formatter={(value: number, name: string) => [
              `${value} 個案例`, 
              name
            ]}
          />
          <Legend />
        </RechartsPieChart>
      </ResponsiveContainer>
    </div>
  );
};

// 市場階段圓餅圖組件
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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {positiveChartData.length > 0 && (
        <PieChart 
          data={positiveChartData} 
          title="正例市場階段分布" 
          width={300} 
          height={250}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart 
          data={negativeChartData} 
          title="反例市場階段分布" 
          width={300} 
          height={250}
        />
      )}
    </div>
  );
};

// 小時分布圓餅圖組件
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
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {positiveChartData.length > 0 && (
        <PieChart 
          data={positiveChartData} 
          title="正例小時分布" 
          width={300} 
          height={250}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart 
          data={negativeChartData} 
          title="反例小時分布" 
          width={300} 
          height={250}
        />
      )}
    </div>
  );
};

// 星期分布圓餅圖組件
export const DayOfWeekPieChart: React.FC<{
  positiveData: Record<number, number>;
  negativeData: Record<number, number>;
}> = ({ positiveData, negativeData }) => {
  const dayNames = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
  
  const positiveChartData: PieChartData[] = Object.entries(positiveData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count], index) => ({
      name: dayNames[Number(day)],
      value: count,
      color: COLORS[index % COLORS.length]
    }));

  const negativeChartData: PieChartData[] = Object.entries(negativeData)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([day, count], index) => ({
      name: dayNames[Number(day)],
      value: count,
      color: COLORS[index % COLORS.length]
    }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {positiveChartData.length > 0 && (
        <PieChart 
          data={positiveChartData} 
          title="正例星期分布" 
          width={300} 
          height={250}
        />
      )}
      {negativeChartData.length > 0 && (
        <PieChart 
          data={negativeChartData} 
          title="反例星期分布" 
          width={300} 
          height={250}
        />
      )}
    </div>
  );
};
