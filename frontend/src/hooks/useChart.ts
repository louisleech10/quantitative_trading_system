/**
 * useChart Hook
 *
 * 用於管理Lightweight Charts實例的自定義Hook
 *
 * 功能：
 * - 初始化圖表實例
 * - 處理視窗resize（響應式）
 * - 組件卸載時清理資源（避免記憶體洩漏）
 */

import { useRef, useEffect, useState } from 'react';
import {
  createChart,
  IChartApi,
  DeepPartial,
  ChartOptions
} from 'lightweight-charts';
import { defaultChartOptions } from '../utils/chartConfig';

/**
 * useChart Hook 參數
 */
interface UseChartOptions {
  /**
   * 自定義圖表選項（會與預設選項合併）
   */
  chartOptions?: DeepPartial<ChartOptions>;
}

/**
 * useChart Hook 返回值
 */
interface UseChartReturn {
  /**
   * 圖表容器的ref（綁定到DOM元素）
   */
  chartContainerRef: React.RefObject<HTMLDivElement>;

  /**
   * 圖表實例（在初始化後可用）
   */
  chartInstance: IChartApi | null;

  /**
   * 圖表是否已準備好（初始化完成且容器已掛載）
   */
  isReady: boolean;
}

/**
 * useChart - 管理Lightweight Charts實例
 *
 * @param options - Hook選項
 * @returns UseChartReturn
 *
 * @example
 * ```tsx
 * function MyChart() {
 *   const { chartContainerRef, chartInstance, isReady } = useChart();
 *
 *   useEffect(() => {
 *     if (chartInstance && isReady) {
 *       // 使用圖表實例...
 *       const candlestickSeries = chartInstance.addCandlestickSeries();
 *       // ...
 *     }
 *   }, [chartInstance, isReady]);
 *
 *   return <div ref={chartContainerRef} style={{ width: '100%', height: '400px' }} />;
 * }
 * ```
 */
export function useChart(options?: UseChartOptions): UseChartReturn {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<IChartApi | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  
  // 使用 ref 緩存 chartOptions，避免引用變化導致重新創建圖表
  const chartOptionsRef = useRef(options?.chartOptions);

  const [isReady, setIsReady] = useState(false);
  const [chartInstance, setChartInstance] = useState<IChartApi | null>(null);

  // 只在首次掛載時創建圖表，不因 options 變化而重新創建
  useEffect(() => {
    // 確保容器存在
    if (!chartContainerRef.current) {
      return;
    }

    // 合併圖表選項（使用緩存的選項）
    const mergedOptions: DeepPartial<ChartOptions> = {
      ...defaultChartOptions,
      ...chartOptionsRef.current,
    };

    // 創建圖表實例
    const chart = createChart(chartContainerRef.current, mergedOptions);
    chartInstanceRef.current = chart;
    setChartInstance(chart);

    // 標記為已準備
    setIsReady(true);

    // 設置響應式調整
    const handleResize = () => {
      if (chartContainerRef.current && chartInstanceRef.current) {
        const { width, height } = chartContainerRef.current.getBoundingClientRect();
        chartInstanceRef.current.applyOptions({
          width,
          height,
        });
      }
    };

    // 使用ResizeObserver監聽容器大小變化
    resizeObserverRef.current = new ResizeObserver(handleResize);
    resizeObserverRef.current.observe(chartContainerRef.current);

    // 初始調整大小
    handleResize();

    // 清理函數
    return () => {
      // 移除ResizeObserver
      if (resizeObserverRef.current && chartContainerRef.current) {
        resizeObserverRef.current.unobserve(chartContainerRef.current);
        resizeObserverRef.current.disconnect();
      }

      // 銷毀圖表實例（避免記憶體洩漏）
      if (chartInstanceRef.current) {
        chartInstanceRef.current.remove();
        chartInstanceRef.current = null;
        setChartInstance(null);
      }

      setIsReady(false);
    };
  }, []); // 移除 options?.chartOptions 依賴，只在首次掛載時創建圖表

  return {
    chartContainerRef,
    chartInstance,
    isReady,
  };
}
