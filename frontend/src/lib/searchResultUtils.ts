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
      marketPhases: {}
    };
  }

  let positiveCases = 0;
  let negativeCases = 0;
  const symbolsSet = new Set<string>();
  const marketPhasesCount: Record<string, number> = {};
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
    marketPhases: marketPhasesCount
  };
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