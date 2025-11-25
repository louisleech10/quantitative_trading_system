/**
 * Lightweight Charts 配置
 *
 * 定義圖表的預設主題、樣式和格式化設置
 */

import { DeepPartial, ChartOptions, ColorType } from 'lightweight-charts';

/**
 * 圖表顏色主題
 */
export const chartColors = {
  // K線顏色（漲綠跌紅）
  upColor: '#26a69a',       // 上漲顏色（綠色）
  downColor: '#ef5350',     // 下跌顏色（紅色）
  upWickColor: '#26a69a',   // 上漲影線顏色
  downWickColor: '#ef5350', // 下跌影線顏色

  // 背景和網格
  backgroundColor: '#ffffff',
  gridColor: '#e0e0e0',
  textColor: '#333333',

  // 案例標記顏色
  caseMarkerColor: '#ff1744',  // 紅色虛線標記案例時間點T
};

/**
 * 深色主題顏色
 */
export const darkChartColors = {
  upColor: '#26a69a',
  downColor: '#ef5350',
  upWickColor: '#26a69a',
  downWickColor: '#ef5350',

  backgroundColor: '#1e1e1e',
  gridColor: '#2a2a2a',
  textColor: '#d1d4dc',

  caseMarkerColor: '#ff1744',
};

/**
 * 預設圖表選項（淺色主題）
 */
export const defaultChartOptions: DeepPartial<ChartOptions> = {
  layout: {
    background: {
      type: ColorType.Solid,
      color: chartColors.backgroundColor
    },
    textColor: chartColors.textColor,
  },
  grid: {
    vertLines: { color: chartColors.gridColor },
    horzLines: { color: chartColors.gridColor },
  },
  crosshair: {
    mode: 0, // CrosshairMode.Magnet - 自動吸附到最近的數據點
    vertLine: {
      visible: true,
      labelVisible: true,
    },
    horzLine: {
      visible: true,
      labelVisible: true,
    },
  },
  rightPriceScale: {
    borderColor: chartColors.gridColor,
    autoScale: true,
  },
  timeScale: {
    borderColor: chartColors.gridColor,
    timeVisible: true,
    secondsVisible: false,
    // 啟用時間軸的拖曳和縮放
    rightOffset: 5,
    barSpacing: 6,
    minBarSpacing: 1,
    fixLeftEdge: false,
    fixRightEdge: false,
    lockVisibleTimeRangeOnResize: false,
    rightBarStaysOnScroll: false,
    shiftVisibleRangeOnNewBar: false,
  },
  // 啟用滑鼠互動
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
    horzTouchDrag: true,
    vertTouchDrag: true,
  },
  handleScale: {
    axisPressedMouseMove: {
      time: true,
      price: true,
    },
    axisDoubleClickReset: {
      time: true,
      price: true,
    },
    mouseWheel: true,
    pinch: true,
  },
  // 不使用 autoSize，避免覆蓋尺寸
  autoSize: false,
};

/**
 * 深色主題圖表選項
 */
export const darkChartOptions: DeepPartial<ChartOptions> = {
  ...defaultChartOptions,
  layout: {
    background: {
      type: ColorType.Solid,
      color: darkChartColors.backgroundColor
    },
    textColor: darkChartColors.textColor,
  },
  grid: {
    vertLines: { color: darkChartColors.gridColor },
    horzLines: { color: darkChartColors.gridColor },
  },
  rightPriceScale: {
    borderColor: darkChartColors.gridColor,
    autoScale: true,
  },
  timeScale: {
    borderColor: darkChartColors.gridColor,
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 5,
    barSpacing: 6,
    minBarSpacing: 1,
    fixLeftEdge: false,
    fixRightEdge: false,
    lockVisibleTimeRangeOnResize: false,
    rightBarStaysOnScroll: false,
    shiftVisibleRangeOnNewBar: false,
  },
};

/**
 * K線系列預設選項
 */
export const candlestickSeriesOptions = {
  upColor: chartColors.upColor,
  downColor: chartColors.downColor,
  borderUpColor: chartColors.upColor,
  borderDownColor: chartColors.downColor,
  wickUpColor: chartColors.upWickColor,
  wickDownColor: chartColors.downWickColor,
};

/**
 * 時間格式化函數（UTC時間）
 *
 * @param timestamp - Unix時間戳（秒）
 * @returns 格式化的UTC時間字符串
 *
 * 注意：使用UTC時間與後端API保持一致，避免時區轉換混淆
 */
export function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000);

  // 使用 UTC 時間方法，與後端 API 的 timestamp 保持一致
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * 價格格式化函數
 *
 * @param price - 價格數值
 * @returns 格式化的價格字符串
 */
export function formatPrice(price: number): string {
  // 根據價格大小決定小數位數
  if (price >= 1000) {
    return price.toFixed(2);
  } else if (price >= 1) {
    return price.toFixed(4);
  } else {
    return price.toFixed(6);
  }
}

/**
 * 成交量格式化函數
 *
 * @param volume - 成交量數值
 * @returns 格式化的成交量字符串
 */
export function formatVolume(volume: number): string {
  if (volume >= 1_000_000) {
    return (volume / 1_000_000).toFixed(2) + 'M';
  } else if (volume >= 1_000) {
    return (volume / 1_000).toFixed(2) + 'K';
  } else {
    return volume.toFixed(2);
  }
}

/**
 * 百分比格式化函數
 *
 * @param value - 0-1之間的數值
 * @returns 格式化的百分比字符串
 */
export function formatPercentage(value: number): string {
  return (value * 100).toFixed(2) + '%';
}
