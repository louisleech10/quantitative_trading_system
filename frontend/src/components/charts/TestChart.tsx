/**
 * TestChart組件
 *
 * 用於測試圖表基礎設施和API調用的測試組件
 *
 * 功能：
 * - 測試圖表初始化和渲染
 * - 測試API調用與數據獲取
 * - 測試K線數據顯示
 * - 測試T點標記
 */

'use client';

import { useEffect, useState } from 'react';
import { useChart } from '../../hooks/useChart';
import { candlestickSeriesOptions, formatTime, formatPrice } from '../../utils/chartConfig';
import { UTCTimestamp } from 'lightweight-charts';
void formatPrice;

const toUtcTime = (timestamp: number): UTCTimestamp => timestamp as UTCTimestamp;

/**
 * K線數據接口
 */
interface KlineData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  taker_buy_volume: number;
  taker_ratio: number;
}

/**
 * API響應接口
 */
interface ChartDataResponse {
  success: boolean;
  data?: {
    case_timestamp: number;
    klines: KlineData[];
    center_index: number;
    metadata: {
      symbol: string;
      timeframe: string;
      total_bars: number;
      time_range: {
        start: number;
        end: number;
      };
    };
  };
  error?: {
    code: string;
    message: string;
  };
}

/**
 * TestChart組件Props
 */
interface TestChartProps {
  symbol: string;
  caseTimestamp: number;
  timeframe: string;
  maxBars?: number;
}

/**
 * TestChart組件
 */
export function TestChart({
  symbol,
  caseTimestamp,
  timeframe,
  maxBars = 200
}: TestChartProps) {
  const { chartContainerRef, chartInstance, isReady } = useChart();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartDataResponse['data'] | null>(null);

  // 獲取圖表數據
  useEffect(() => {
    const fetchChartData = async () => {
      setLoading(true);
      setError(null);

      try {
        // 構建API URL
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const url = `${apiUrl}/api/v1/chart/data?symbol=${symbol}&case_timestamp=${caseTimestamp}&timeframe=${timeframe}&max_bars=${maxBars}`;

        console.log('Fetching chart data from:', url);

        // 發送API請求
        const response = await fetch(url);
        const data: ChartDataResponse = await response.json();

        if (!response.ok) {
          throw new Error(data.error?.message || `HTTP error! status: ${response.status}`);
        }

        if (!data.success || !data.data) {
          throw new Error(data.error?.message || 'Failed to fetch chart data');
        }

        console.log('Chart data received:', data.data);
        setChartData(data.data);

      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Unknown error';
        console.error('Failed to fetch chart data:', errorMessage);
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [symbol, caseTimestamp, timeframe, maxBars]);

  // 渲染K線數據到圖表
  useEffect(() => {
    if (!chartInstance || !isReady || !chartData) {
      return;
    }

    try {
      // 添加K線系列
      const candlestickSeries = chartInstance.addCandlestickSeries(candlestickSeriesOptions);

      // 轉換數據格式
      const formattedKlines = chartData.klines.map(kline => ({
        time: toUtcTime(kline.timestamp), // Lightweight Charts使用timestamp作為time
        open: kline.open,
        high: kline.high,
        low: kline.low,
        close: kline.close,
      }));

      // 設置數據
      candlestickSeries.setData(formattedKlines);

      // 標記T點（案例時間點）
      const tMarker = {
        time: toUtcTime(chartData.case_timestamp),
        position: 'aboveBar' as const,
        color: '#fb7185',
        shape: 'arrowDown' as const,
        text: 'T',
      };

      candlestickSeries.setMarkers([tMarker]);

      // 自動縮放到適合的範圍
      chartInstance.timeScale().fitContent();

      console.log('Chart rendered successfully with', formattedKlines.length, 'klines');
      console.log('Center index (T position):', chartData.center_index);

    } catch (err) {
      console.error('Failed to render chart:', err);
      setError(err instanceof Error ? err.message : 'Failed to render chart');
    }
  }, [chartInstance, isReady, chartData]);

  return (
    <div className="w-full h-full flex flex-col">
      {/* 信息欄 */}
      <div className="p-4 glass-panel border-b border-white/10">
        <h3 className="text-lg font-semibold text-slate-100">
          測試圖表：{symbol} / {timeframe}
        </h3>
        <p className="text-sm text-slate-400">
          案例時間點T：{formatTime(caseTimestamp)}
        </p>
        {chartData && (
          <div className="mt-2 text-sm text-slate-400">
            <p>
              數據範圍：{formatTime(chartData.metadata.time_range.start)} 至{' '}
              {formatTime(chartData.metadata.time_range.end)}
            </p>
            <p>
              K線數量：{chartData.metadata.total_bars} 根，T點位置：第 {chartData.center_index + 1} 根
            </p>
          </div>
        )}
      </div>

      {/* 圖表容器 */}
      <div className="flex-1 relative">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#1a233a]/90 backdrop-blur-xl z-10">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-100 mx-auto mb-4"></div>
              <p className="text-slate-400">載入圖表數據中...</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-[#1a233a]/90 backdrop-blur-xl z-10 p-8">
            <div className="max-w-md text-center">
              <div className="text-rose-400 text-4xl mb-4">⚠️</div>
              <h4 className="text-lg font-semibold text-slate-100 mb-2">載入失敗</h4>
              <p className="text-rose-300">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="mt-4 px-4 py-2 bg-blue-500/20 text-blue-100 border border-blue-500/40 rounded hover:bg-blue-500/30"
              >
                重試
              </button>
            </div>
          </div>
        )}

        <div
          ref={chartContainerRef}
          className="w-full h-full"
          style={{ minHeight: '400px' }}
        />
      </div>
    </div>
  );
}
