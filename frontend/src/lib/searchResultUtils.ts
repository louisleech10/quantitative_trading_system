// 創建新文件：frontend/src/lib/searchResultUtils.ts

export interface ActualStatistics {
  totalCases: number;
  positiveCases: number;
  negativeCases: number;
  uniqueSymbols: number;
  symbolsList: string[];
  positiveRatio: string;
  timeRange: {
    start: string | null;
    end: string | null;
  };
  marketPhases: Record<string, number>;
  // 新增：分離統計
  positiveMarketPhases: Record<string, number>;
  negativeMarketPhases: Record<string, number>;
  hourDistribution: Record<number, number>;
  dayOfWeekDistribution: Record<number, number>;
  positiveHourDistribution: Record<number, number>;
  negativeHourDistribution: Record<number, number>;
  positiveDayOfWeekDistribution: Record<number, number>;
  negativeDayOfWeekDistribution: Record<number, number>;
  // ===== 新增：市場分類和難度分布統計 =====
  marketClassDistribution: Record<string, number>;
  positiveMarketClassDistribution: Record<string, number>;
  negativeMarketClassDistribution: Record<string, number>;
  difficultyDistribution: Record<string, number>;
  positiveDifficultyDistribution: Record<string, number>;
  negativeDifficultyDistribution: Record<string, number>;
}

/**
 * 基於實際案例數據計算準確的統計信息
 * 優先使用這個函數，而不是後端提供的 summary 數據
 */
export const calculateActualStatistics = (cases: any[]): ActualStatistics => {
  if (!cases || cases.length === 0) {
    return {
      totalCases: 0,
      positiveCases: 0,
      negativeCases: 0,
      uniqueSymbols: 0,
      symbolsList: [],
      positiveRatio: 'N/A',
      timeRange: { start: null, end: null },
      marketPhases: {},
      positiveMarketPhases: {},
      negativeMarketPhases: {},
      hourDistribution: {},
      dayOfWeekDistribution: {},
      positiveHourDistribution: {},
      negativeHourDistribution: {},
      positiveDayOfWeekDistribution: {},
      negativeDayOfWeekDistribution: {},
      marketClassDistribution: {},
      positiveMarketClassDistribution: {},
      negativeMarketClassDistribution: {},
      difficultyDistribution: {},
      positiveDifficultyDistribution: {},
      negativeDifficultyDistribution: {}
    };
  }

  let positiveCases = 0;
  let negativeCases = 0;
  const symbolsSet = new Set<string>();
  const marketPhasesCount: Record<string, number> = {};
  const positiveMarketPhasesCount: Record<string, number> = {};
  const negativeMarketPhasesCount: Record<string, number> = {};
  const hourDistribution: Record<number, number> = {};
  const dayOfWeekDistribution: Record<number, number> = {};
  const positiveHourDistribution: Record<number, number> = {};
  const negativeHourDistribution: Record<number, number> = {};
  const positiveDayOfWeekDistribution: Record<number, number> = {};
  const negativeDayOfWeekDistribution: Record<number, number> = {};
  // ===== 新增：市場分類和難度分布統計 =====
  const marketClassCount: Record<string, number> = {};
  const positiveMarketClassCount: Record<string, number> = {};
  const negativeMarketClassCount: Record<string, number> = {};
  const difficultyCount: Record<string, number> = {};
  const positiveDifficultyCount: Record<string, number> = {};
  const negativeDifficultyCount: Record<string, number> = {};
  let earliestTime: Date | null = null;
  let latestTime: Date | null = null;

  cases.forEach(caseItem => {
    // ✅ 統計正反例數量（支持多種可能的字段名稱）
    const isPositive = caseItem.positive_case === 1 || 
                      caseItem.positive_case === true || 
                      caseItem.Positive_Case === 1 ||
                      caseItem.Positive_Case === true ||
                      caseItem.label === 1;
    
    if (isPositive) {
      positiveCases++;
    } else {
      negativeCases++;
    }

    // ✅ 收集交易對
    if (caseItem.symbol) {
      symbolsSet.add(caseItem.symbol);
    }

    // ✅ 統計市場階段
    if (caseItem.market_phase) {
      marketPhasesCount[caseItem.market_phase] = (marketPhasesCount[caseItem.market_phase] || 0) + 1;
      
      // 分離統計正例和反例的市場階段
      if (isPositive) {
        positiveMarketPhasesCount[caseItem.market_phase] = (positiveMarketPhasesCount[caseItem.market_phase] || 0) + 1;
      } else {
        negativeMarketPhasesCount[caseItem.market_phase] = (negativeMarketPhasesCount[caseItem.market_phase] || 0) + 1;
      }
    }

    // ✅ 統計時間分布
    if (caseItem.hour_of_day !== undefined && caseItem.hour_of_day !== null) {
      const hour = Number(caseItem.hour_of_day);
      if (!isNaN(hour)) {
        hourDistribution[hour] = (hourDistribution[hour] || 0) + 1;
        
        // 分離統計正例和反例的小時分布
        if (isPositive) {
          positiveHourDistribution[hour] = (positiveHourDistribution[hour] || 0) + 1;
        } else {
          negativeHourDistribution[hour] = (negativeHourDistribution[hour] || 0) + 1;
        }
      }
    }

    if (caseItem.day_of_week !== undefined && caseItem.day_of_week !== null) {
      const dayOfWeek = Number(caseItem.day_of_week);
      if (!isNaN(dayOfWeek)) {
        dayOfWeekDistribution[dayOfWeek] = (dayOfWeekDistribution[dayOfWeek] || 0) + 1;

        // 分離統計正例和反例的星期分布
        if (isPositive) {
          positiveDayOfWeekDistribution[dayOfWeek] = (positiveDayOfWeekDistribution[dayOfWeek] || 0) + 1;
        } else {
          negativeDayOfWeekDistribution[dayOfWeek] = (negativeDayOfWeekDistribution[dayOfWeek] || 0) + 1;
        }
      }
    }

    // ✅ 統計市場分類分布
    if (caseItem.market_class_name) {
      const marketClassName = caseItem.market_class_name;
      marketClassCount[marketClassName] = (marketClassCount[marketClassName] || 0) + 1;

      // 分離統計正例和反例的市場分類
      if (isPositive) {
        positiveMarketClassCount[marketClassName] = (positiveMarketClassCount[marketClassName] || 0) + 1;
      } else {
        negativeMarketClassCount[marketClassName] = (negativeMarketClassCount[marketClassName] || 0) + 1;
      }
    }

    // ✅ 統計難度分布
    if (caseItem.difficulty_level) {
      const difficulty = caseItem.difficulty_level;
      difficultyCount[difficulty] = (difficultyCount[difficulty] || 0) + 1;

      // 分離統計正例和反例的難度分布
      if (isPositive) {
        positiveDifficultyCount[difficulty] = (positiveDifficultyCount[difficulty] || 0) + 1;
      } else {
        negativeDifficultyCount[difficulty] = (negativeDifficultyCount[difficulty] || 0) + 1;
      }
    }

    // ✅ 計算時間範圍
    if (caseItem.timestamp) {
      try {
        const caseTime = new Date(caseItem.timestamp);
        if (!earliestTime || caseTime < earliestTime) {
          earliestTime = caseTime;
        }
        if (!latestTime || caseTime > latestTime) {
          latestTime = caseTime;
        }
      } catch (e) {
        // 忽略無效的時間戳
      }
    }
  });

  // ✅ 計算正負比例
  const positiveRatio = positiveCases > 0 && negativeCases > 0 
    ? `1:${(negativeCases / positiveCases).toFixed(1)}`
    : positiveCases > 0 && negativeCases === 0 
    ? '1:0 (僅正例)'
    : positiveCases === 0 && negativeCases > 0
    ? '0:1 (僅反例)'
    : 'N/A';

  return {
    totalCases: cases.length,
    positiveCases,
    negativeCases,
    uniqueSymbols: symbolsSet.size,
    symbolsList: Array.from(symbolsSet).sort(),
    positiveRatio,
    timeRange: {
      start: earliestTime?.toISOString() || null,
      end: latestTime?.toISOString() || null
    },
    marketPhases: marketPhasesCount,
    positiveMarketPhases: positiveMarketPhasesCount,
    negativeMarketPhases: negativeMarketPhasesCount,
    hourDistribution,
    dayOfWeekDistribution,
    positiveHourDistribution,
    negativeHourDistribution,
    positiveDayOfWeekDistribution,
    negativeDayOfWeekDistribution,
    marketClassDistribution: marketClassCount,
    positiveMarketClassDistribution: positiveMarketClassCount,
    negativeMarketClassDistribution: negativeMarketClassCount,
    difficultyDistribution: difficultyCount,
    positiveDifficultyDistribution: positiveDifficultyCount,
    negativeDifficultyDistribution: negativeDifficultyCount
  };
};

/**
 * 格式化時間戳，修復 00:00:00 顯示為空格的問題
 */
export const formatTimestamp = (timestamp: string): string => {
  if (!timestamp) return '';
  
  try {
    const date = new Date(timestamp);
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    const seconds = date.getSeconds().toString().padStart(2, '0');
    
    return `${hours}:${minutes}:${seconds}`;
  } catch (e) {
    return timestamp;
  }
};

/**
 * 獲取統計摘要文本
 */
export const getStatisticsSummary = (stats: ActualStatistics): string => {
  const parts = [
    `總共 ${stats.totalCases} 個案例`,
    `正例 ${stats.positiveCases} 個`,
    `反例 ${stats.negativeCases} 個`,
    `涉及 ${stats.uniqueSymbols} 個交易對`,
    `比例 ${stats.positiveRatio}`
  ];
  
  return parts.join('，');
};

/**
 * 驗證後端統計數據與實際數據的一致性
 */
export const validateBackendStatistics = (
  actualStats: ActualStatistics, 
  backendSummary: any
): { isConsistent: boolean; differences: string[] } => {
  const differences: string[] = [];
  
  if (backendSummary?.total_cases !== actualStats.totalCases) {
    differences.push(`總案例數不一致: 後端 ${backendSummary?.total_cases} vs 實際 ${actualStats.totalCases}`);
  }
  
  if (backendSummary?.positive_cases !== actualStats.positiveCases) {
    differences.push(`正例數不一致: 後端 ${backendSummary?.positive_cases} vs 實際 ${actualStats.positiveCases}`);
  }
  
  if (backendSummary?.negative_cases !== actualStats.negativeCases) {
    differences.push(`反例數不一致: 後端 ${backendSummary?.negative_cases} vs 實際 ${actualStats.negativeCases}`);
  }
  
  if (backendSummary?.unique_symbols !== actualStats.uniqueSymbols) {
    differences.push(`交易對數不一致: 後端 ${backendSummary?.unique_symbols} vs 實際 ${actualStats.uniqueSymbols}`);
  }
  
  return {
    isConsistent: differences.length === 0,
    differences
  };
};