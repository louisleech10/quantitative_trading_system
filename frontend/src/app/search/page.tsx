'use client';

import React, { useEffect, useState } from 'react';
import { Search, RefreshCw, AlertCircle, HelpCircle, ChevronDown, ChevronRight, Download } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { calculateActualStatistics, getStatisticsSummary, validateBackendStatistics, formatTimestamp } from '@/lib/searchResultUtils';
void formatTimestamp;
import { MarketPhasePieChart, HourDistributionPieChart, DayOfWeekPieChart, MarketClassPieChart, DifficultyPieChart } from '@/components/ui/PieChart';
import { useSearchStore } from '@/store/searchStore';
import { PriceChangeMethod, CaseData } from '@/lib/types';
import { fetchLookaheadDeclarationPreviewColumns } from '@/lib/api';
import {
  declaredWindowBarsForExport,
  initialDeclaredWindowBars,
  validateDeclaration,
  withExportDeclarationGuard,
  type ExportDeclarationState,
  type LookaheadDeclarationPreview,
} from '@/lib/lookaheadDeclaration';
import LookaheadDeclarationFields from '@/components/case/LookaheadDeclarationFields';
import {
  ATTACHED_HORIZONS,
  EVENT_EXPORT_CONTROL_KIND,
  EVENT_EXPORT_DECISION_OFFSET_BARS,
  EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
  EVENT_EXPORT_LABEL_RETURN_MODE,
  EVENT_EXPORT_SCENARIO,
  eventDimsToExportOptions,
  horizonCoverageLines,
  toEpochMs,
  twoStageExportBlockReason,
} from '@/lib/eventExport';
import { canonicalEventId } from '@/lib/eventId';
import EventDimensionFields, { type EventDimensionValues } from '@/components/case/EventDimensionFields';
import {
  EVENT_IC_DECAY_DISCLOSURE,
  SEARCH_DISCLOSURE_FIELDS,
  searchDisclosureLines,
} from '@/lib/eventFieldFormatters';
import { computeExportCounts } from '@/lib/exportCounts';



// 搜索請求接口 (符合您的 api.ts 設計)
interface SimpleSearchRequest {
  name: string;
  symbols: string[];
  timeframe: string;
  searchMode?: 'research' | 'realtime';
  startDate?: string | null;     // 新增：開始日期
  endDate?: string | null;       // 新增：結束日期
  priceChangeMethod?: PriceChangeMethod; // 價格變動計算方式
  priceChange?: number | null;
  volumeMultiplier?: number | null;
  closingStrength?: number | null;
  takerBuyRatio?: number | null;
  pricePosition?: number | null;
  saveResults?: boolean;
}

// 運算符選項
const OPERATORS = [
  { value: '>=', label: '大於等於 (≥)' },
  { value: '<=', label: '小於等於 (≤)' },
  { value: 'BETWEEN', label: '介於範圍' }
];

// 欄位說明
const FIELD_DESCRIPTIONS = {
  priceChange: '價格變化：當前收盤價相對於前一K線收盤價的變化百分比',
  volumeMultiplier: '成交量倍數：當前K線成交量相對於平均成交量的倍數',
  closingStrength: '收盤強度：收盤價在當根K線高低價範圍中的位置，1表示收在最高價',
  takerBuyRatio: '主動買入比例：主動買入成交量佔總成交量的比例',
  pricePosition: '價格位置：當前價格在近期價格範圍中的相對位置'
};

export default function SearchPage() {
  // 使用全局狀態管理
  const { currentResult, isLoading, error, setSearchResult, setLoading, setError } = useSearchStore();

  // 基礎狀態
  const [currentStage, setCurrentStage] = useState<string>('');
  // GAP-3 UX Task 4.1 ①：附帶報酬欄（預設全選 1..12）。
  // 🔴 **純供 Excel 攜帶**——不進 ic_feed、不決定任何 horizon、不參與深度導出。
  //    改變本清單**不得**影響 lookahead_bars_declared 與 window.horizon_bars（邊界①）。
  // 🔴 Task 4.1 ② 已移除「主答案窗」單選：答案窗依 §D-3′ 移到 IC 分析層，
  //    匯出端不再寫 label_value、不再讓使用者選 h。
  const [attachedHorizons, setAttachedHorizons] = useState<number[]>([...ATTACHED_HORIZONS]);
  // GAP-3 UX Task 1.9′（R 重開 D-8）：匯出端答案窗宣告——深度之**唯一來源**＝使用者逐 tf 宣告
  //    （`lookahead_bars_declared[tf] = declared_window_bars[tf]`，不與任何欄位取 max）。
  // 🔴 前端**不推斷深度**：預設值候選由後端 `preview_from_columns` 給（唯一實作，與匯入頁同一函式），
  //    validator 亦與匯入頁同一份 `validateDeclaration`（Task 1.9′ ⑦）。
  //    Phase 2 之「篩選條件 → 下界導出」整區已退役（使用者 2026-09-02 裁定）。
  const [declPreview, setDeclPreview] = useState<LookaheadDeclarationPreview | null>(null);
  const [declPreviewError, setDeclPreviewError] = useState<string | null>(null);
  const [declared, setDeclared] = useState<Record<string, number>>({});
  const [declAcknowledged, setDeclAcknowledged] = useState(false);
  // 🔴 R2 review（CODEX-R2-P1-01）：區分**使用者明填**與**系統預填**。只有使用者親手填過的 tf 才在附帶欄改變時保留
  //    （驗證⑤）；系統預填的值跟著新 preview 走——附帶欄全取消後預設變 0 ⇒ 該框**回到留空**，0 須使用者明填。
  //    否則「全選→預填 12→全取消」會留著一個使用者從未填過的 12 放行匯出。
  const declTouchedRef = React.useRef<Set<string>>(new Set());
  const declState: ExportDeclarationState = { preview: declPreview, declared, acknowledged: declAcknowledged };
  // GAP-3 UX Task 7.1：五個批次維度**可見可改**；初始值＝Task 7.0 之常數
  // （⇒ 使用者不動 UI 時匯出結果與 7.0 逐位元相同，SPEC 邊界②之 golden 不變由此成立）。
  const [eventDims, setEventDims] = useState<EventDimensionValues>({
    scenario: EVENT_EXPORT_SCENARIO,
    control_kind: EVENT_EXPORT_CONTROL_KIND,
    entry_price_semantic: EVENT_EXPORT_ENTRY_PRICE_SEMANTIC,
    label_return_mode: EVENT_EXPORT_LABEL_RETURN_MODE,
    decision_offset_bars: EVENT_EXPORT_DECISION_OFFSET_BARS,
  });
  
  // 搜索參數狀態
  const [searchParams, setSearchParams] = useState<SimpleSearchRequest>({
    name: '兩階段搜索測試',
    symbols: [],
    timeframe: '12h',
    searchMode: 'research',
    priceChangeMethod: PriceChangeMethod.CLOSE_TO_CLOSE, // 預設使用 CLOSE_TO_CLOSE (波段交易)
    priceChange: null,
    volumeMultiplier: null,
    closingStrength: null,
    takerBuyRatio: null,
    pricePosition: null,
    saveResults: false
  });

  const [symbolsInput, setSymbolsInput] = useState('');

  // ── GAP-3 UX Task 1.9′（匯出端宣告框）＋ Task 1.5 之三個計數 ───────────────────
  const exportRows = React.useMemo(
    () => (currentResult?.cases ?? []) as unknown as Record<string, unknown>[],
    [currentResult],
  );
  /** 🔴 三個數字（原 M／正例 X／反例 Y）之**唯一**計數來源；篩選已退役故無「將匯出 N 筆」。 */
  const exportCounts = React.useMemo(() => computeExportCounts(exportRows), [exportRows]);
  /** 批內出現之 timeframe 集合（宣告框逐 tf 各一框；多 TF 批不得以單一框套用全部 tf）。 */
  const exportTimeframes = React.useMemo(
    () => [...new Set(exportRows.map((r) => String(r.timeframe ?? searchParams.timeframe)))]
      .filter((tf) => tf && tf !== 'undefined'),
    [exportRows, searchParams.timeframe],
  );
  // 預填資料之輸入：**只有**使用者勾選、且會寫進匯出檔之附帶 `future_{h}bar_return` 欄（只影響**預設候選**，不影響已宣告值）。
  // 🔴 R1 review（GROK-R1-P1-01／CODEX-R1-P2-02）：不得把搜尋結果列的全部鍵送去——結果列恆帶系統內部的
  //    `future72_*`／`future24_*` 等欄（使用者在本頁看不到、也不會匯出），會把 1h 預設拉到 72，
  //    使用者照預設填就高估 purge；填真實的 12 反而被當成「調低」而多要一次勾選。
  const previewInputKey = JSON.stringify({
    attached: [...attachedHorizons].sort((a, b) => a - b),
    tfs: exportTimeframes,
  });

  // 換一批搜尋結果 ⇒ 舊宣告與舊 preview 皆作廢（不同批之 tf 集合與內容都可能不同）
  useEffect(() => {
    setDeclPreview(null);
    setDeclared({});
    setDeclAcknowledged(false);
    declTouchedRef.current = new Set();
  }, [currentResult]);

  useEffect(() => {
    // Task 1.9′ 實作要點 2：預設值候選來自後端 `preview_from_columns`（唯一實作；前端禁重寫換算表）。
    // 🔴 拿不到 preview ⇒ 守衛擋（`exportDeclarationBlockMessage`），不以任何預設深度代替。
    // 🔴 附帶欄改變只會**重取預設候選**：既有 preview 與已宣告值在重取期間保留（驗證⑤），
    //    不在此清空——清空會讓「改附帶欄後立刻匯出」被當成「尚未取得」而擋住。
    const { attached, tfs } = JSON.parse(previewInputKey) as { attached: number[]; tfs: string[] };
    setDeclPreviewError(null);
    if (tfs.length === 0) return;
    let cancelled = false;
    fetchLookaheadDeclarationPreviewColumns({
      columns: attached.map((h) => `future_${h}bar_return`),
      timeframes: tfs,
    })
      .then((p) => {
        if (cancelled) return;
        setDeclPreview(p);
        // 🔴 Task 1.9′ 驗證⑤＋R2 `CODEX-R2-P1-01`：使用者**明填**過的 tf 不因附帶欄／預設改變而被覆寫；
        //    系統**預填**的 tf 跟著新預設走——預設 `< 1` 者回到留空（`0` 須使用者明填，留白≠0）。
        setDeclared((prev) => {
          const init = initialDeclaredWindowBars(p);
          const next: Record<string, number> = { ...prev };
          for (const tf of p.timeframes) {
            if (declTouchedRef.current.has(tf)) continue;
            if (tf in init) next[tf] = init[tf]; else delete next[tf];
          }
          return next;
        });
      })
      .catch((err) => {
        if (cancelled) return;
        // 🔴 R1 review（CODEX-R1-P1-01）：重取失敗 ⇒ 舊 preview **作廢**（守衛據此擋），不得留著舊 preview 放行——
        //    否則「先成功、改附帶欄後端點拒」這條路徑會用過期預設放行匯出。已宣告值保留（重取成功後再驗）。
        setDeclPreview(null);
        setDeclPreviewError(err instanceof Error ? err.message : '無法取得答案窗預填資料');
      });
    return () => { cancelled = true; };
  }, [previewInputKey]);

  const parseSymbolsInput = (input: string): string[] =>
    input
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter((item) => item.length > 0);

  // 運算符狀態
  const [operators, setOperators] = useState({
    priceChange: '>=',
    volumeMultiplier: '>=',
    closingStrength: '>=',
    takerBuyRatio: '>=',
    pricePosition: '>='
  });

  // 範圍值狀態 (用於 BETWEEN 運算符)
  const [rangeValues, setRangeValues] = useState({
    priceChange: { min: null as number | null, max: null as number | null },
    volumeMultiplier: { min: null as number | null, max: null as number | null },
    closingStrength: { min: null as number | null, max: null as number | null },
    takerBuyRatio: { min: null as number | null, max: null as number | null },
    pricePosition: { min: null as number | null, max: null as number | null }
  });

  // 反例範圍值狀態 (用於反例 BETWEEN 運算符)
  const [negativeRangeValues, setNegativeRangeValues] = useState({
    priceChange: { min: null as number | null, max: null as number | null },
    volumeMultiplier: { min: null as number | null, max: null as number | null },
    closingStrength: { min: null as number | null, max: null as number | null },
    takerBuyRatio: { min: null as number | null, max: null as number | null },
    pricePosition: { min: null as number | null, max: null as number | null }
  }); 

  // 時間日期和交易量限制狀態
  const [timeParams, setTimeParams] = useState({
    startDate: '',
    endDate: '',
    volumeMin: null as number | null,
    volumeMax: null as number | null
  });

  // 反例搜索參數
  const [negativeParams, setNegativeParams] = useState({
    enabled: true,
    ratio: 2.0,
    enableTimeSeparation: true,
    timeSeparationDays: 3,
    enableRandomSampling: true,  // ===== 新增：隨機取樣開關 =====
    priceChange: null as number | null,
    volumeMultiplier: null as number | null,
    closingStrength: null as number | null,
    takerBuyRatio: null as number | null,
    pricePosition: null as number | null,
    customConditions: [] as unknown[]
  });

  // 反例運算符狀態
  const [negativeOperators, setNegativeOperators] = useState({
    priceChange: '<=',
    volumeMultiplier: '<=',
    closingStrength: '<=',
    takerBuyRatio: '<=',
    pricePosition: '<='
  });

  /**
   * 🔴 `G3-D2` D3.1：兩段式匯出之**第二段**條件（反例）。
   *
   * `/search` 頁上唯一的「兩段」來源就是「正例條件 ＋ 反例條件」，
   * 反例未啟用（`negativeParams.enabled === false`）⇒ 只有一段。
   * **這裡只組資料、不做判斷**：一段時的阻擋由 `buildEventContractRecords` 丟
   * `EventExportBlocked('two_stage_requires_two_stages')`——判斷寫在這裡就是第二份清單。
   *
   * 🔴 與 `api/routes/two_stage_search.py` **無關**：那支 router 不動不接
   * （SPEC D3.1 邊界①），它的產物沒有 provenance，不得被匯入為 two_stage 批。
   * 這裡取的是**使用者在本頁填的條件**，不是那支 router 的輸出。
   *
   * 兩條匯出路徑（JSON／CSV）共用本值——不得各寫一份。
   */
  /**
   * 🔴 `G3-D2` D3.1：**第一段**（正例）條件。原本 JSON 與 CSV 兩個匯出 handler
   * 各自寫了一份**逐字相同**的陣列；D3.1 需要在元件層就知道兩段內容（才能 disable 按鈕），
   * 順手把那份既有重複收成單一來源。兩個 handler 現在都用本值。
   */
  const positiveStageConditions = React.useMemo(() => [
    {
      parameter: 'price_change',
      operator: operators.priceChange,
      value: operators.priceChange === 'BETWEEN'
        ? [rangeValues.priceChange.min, rangeValues.priceChange.max]
        : searchParams.priceChange,
      unit: 'percent',
    },
    { parameter: 'volume_multiplier', operator: operators.volumeMultiplier, value: searchParams.volumeMultiplier },
    { parameter: 'closing_strength', operator: operators.closingStrength, value: searchParams.closingStrength },
    { parameter: 'taker_buy_ratio', operator: operators.takerBuyRatio, value: searchParams.takerBuyRatio },
    { parameter: 'price_position', operator: operators.pricePosition, value: searchParams.pricePosition },
  ].filter((c) => c.value !== null && c.value !== undefined), [operators, rangeValues, searchParams]);

  const negativeStageConditions = React.useMemo(() => [
    {
      parameter: 'price_change',
      operator: negativeOperators.priceChange,
      // 🔴 R1 `CODEX-R1-P1-03`：本行原本只讀 `negativeParams.priceChange`，
      //    而 BETWEEN 之值住 `negativeRangeValues`（正例那一支有處理、我複製時漏了）
      //    ⇒ 使用者選 BETWEEN 只填 range 時，整段被 `.filter()` 濾成 `[]`，
      //    第二段變空殼卻仍過「兩段」閘。**兩段條件的組法必須對稱。**
      value: negativeOperators.priceChange === 'BETWEEN'
        ? [negativeRangeValues.priceChange.min, negativeRangeValues.priceChange.max]
        : negativeParams.priceChange,
      unit: 'percent',
    },
    { parameter: 'volume_multiplier', operator: negativeOperators.volumeMultiplier, value: negativeParams.volumeMultiplier },
    { parameter: 'closing_strength', operator: negativeOperators.closingStrength, value: negativeParams.closingStrength },
    { parameter: 'taker_buy_ratio', operator: negativeOperators.takerBuyRatio, value: negativeParams.takerBuyRatio },
    { parameter: 'price_position', operator: negativeOperators.pricePosition, value: negativeParams.pricePosition },
  ].filter((c) => c.value !== null && c.value !== undefined),
  [negativeOperators, negativeParams, negativeRangeValues]);

  /** D3.1：兩段條件之組裝（反例未啟用 ⇒ 只有一段）。兩個 handler 與按鈕 disable 共用。 */
  const exportStageConditions = negativeParams.enabled
    ? [positiveStageConditions, negativeStageConditions]
    : [positiveStageConditions];

  /**
   * D3.1：匯出是否被阻擋（`undefined` ＝ 不擋）。
   * 🔴 判定**不在這裡寫**——呼叫 `eventExport.ts` 之 `twoStageExportBlockReason`，
   * 與 `buildEventContractRecords` 內丟例外用的是同一份。
   */
  const exportBlock = twoStageExportBlockReason({
    scenario: eventDims.scenario,
    stageConditions: exportStageConditions,
    lookaheadBarsDeclared: declaredWindowBarsForExport(declState),
  });

  // UI 狀態
  const [expandedSections, setExpandedSections] = useState({
    positive: true,
    negative: false,
    results: false
  });

  // 切換展開狀態
  const toggleSection = (section: keyof typeof expandedSections) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };


  // 執行兩階段搜索 - 修正為真實API調用
  const executeTwoStageSearch = async () => {
    try {
      setLoading(true);
      setError(null);
      setSearchResult(null);

      const normalizedSymbols = parseSymbolsInput(symbolsInput);

      
      console.log('開始執行搜索...');
      console.log('搜索參數:', searchParams);
      console.log('時間參數:', timeParams);
      console.log('反例參數:', negativeParams);
      
      // 準備API請求格式
      // 準備API條件數組
      const buildConditions = () => {
        const conditions = [];

        // 價格變化條件
        if (operators.priceChange === 'BETWEEN' && rangeValues.priceChange.min !== null && rangeValues.priceChange.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_change",
            operator: "between",
            value: [rangeValues.priceChange.min / 100, rangeValues.priceChange.max / 100], // 轉換為小數
            description: `價格變化介於 ${rangeValues.priceChange.min}% 到 ${rangeValues.priceChange.max}%`
          });
        } else if (searchParams.priceChange !== null && searchParams.priceChange !== undefined) {
          conditions.push({
            condition_type: "price",
            parameter: "price_change",
            operator: operators.priceChange,
            value: searchParams.priceChange / 100, // 轉換為小數
            description: `價格變化 ${operators.priceChange} ${searchParams.priceChange}%`
          });
        }

        // 成交量倍數條件
        if (operators.volumeMultiplier === 'BETWEEN' && rangeValues.volumeMultiplier.min !== null && rangeValues.volumeMultiplier.max !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "volume_multiplier",
            operator: "between",
            value: [rangeValues.volumeMultiplier.min, rangeValues.volumeMultiplier.max],
            description: `成交量倍數介於 ${rangeValues.volumeMultiplier.min} 到 ${rangeValues.volumeMultiplier.max}`
          });
        } else if (searchParams.volumeMultiplier !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "volume_multiplier",
            operator: operators.volumeMultiplier,
            value: searchParams.volumeMultiplier,
            description: `成交量倍數 ${operators.volumeMultiplier} ${searchParams.volumeMultiplier}`
          });
        }

        // 收盤強度條件
        if (operators.closingStrength === 'BETWEEN' && rangeValues.closingStrength.min !== null && rangeValues.closingStrength.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "closing_strength",
            operator: "between",
            value: [rangeValues.closingStrength.min, rangeValues.closingStrength.max],
            description: `收盤強度介於 ${rangeValues.closingStrength.min} 到 ${rangeValues.closingStrength.max}`
          });
        } else if (searchParams.closingStrength !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "closing_strength",
            operator: operators.closingStrength,
            value: searchParams.closingStrength,
            description: `收盤強度 ${operators.closingStrength} ${searchParams.closingStrength}`
          });
        }

        // 主動買入比例條件
        if (operators.takerBuyRatio === 'BETWEEN' && rangeValues.takerBuyRatio.min !== null && rangeValues.takerBuyRatio.max !== null) {
          conditions.push({
            condition_type: "volume", 
            parameter: "taker_buy_ratio",
            operator: "between",
            value: [rangeValues.takerBuyRatio.min, rangeValues.takerBuyRatio.max],
            description: `主動買入比例介於 ${rangeValues.takerBuyRatio.min} 到 ${rangeValues.takerBuyRatio.max}`
          });
        } else if (searchParams.takerBuyRatio !== null) {
          conditions.push({
            condition_type: "volume",
            parameter: "taker_buy_ratio", 
            operator: operators.takerBuyRatio,
            value: searchParams.takerBuyRatio,
            description: `主動買入比例 ${operators.takerBuyRatio} ${searchParams.takerBuyRatio}`
          });
        }

        // 價格位置條件
        if (operators.pricePosition === 'BETWEEN' && rangeValues.pricePosition.min !== null && rangeValues.pricePosition.max !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_position",
            operator: "between", 
            value: [rangeValues.pricePosition.min, rangeValues.pricePosition.max],
            description: `價格位置介於 ${rangeValues.pricePosition.min} 到 ${rangeValues.pricePosition.max}`
          });
        } else if (searchParams.pricePosition !== null) {
          conditions.push({
            condition_type: "price",
            parameter: "price_position",
            operator: operators.pricePosition,
            value: searchParams.pricePosition,
            description: `價格位置 ${operators.pricePosition} ${searchParams.pricePosition}`
          });
        }

        return conditions;
      };

      // 檢查是否有設定搜索條件
      const hasConditions = buildConditions().length > 0;

      // 如果有條件，必須提供必要參數
      if (hasConditions) {
        if (normalizedSymbols.length === 0) {
          setError('設定搜索條件時必須選擇至少一個交易對');
          return;
        }
        
        if (!timeParams.startDate || !timeParams.endDate) {
          setError('設定搜索條件時必須提供開始和結束日期');
          return;
        }
      }

      const apiRequest = {
        config: {
          name: searchParams.name,
          timeframe: searchParams.timeframe,
          search_mode: searchParams.searchMode,
          start_date: timeParams.startDate || null,
          end_date: timeParams.endDate || null,
          initial_conditions: buildConditions(),
          min_volume: timeParams.volumeMin || 100000
        },
        symbols: normalizedSymbols,
        save_results: searchParams.saveResults || false
      };

      console.log('發送API請求:', apiRequest);
      
      if (negativeParams.enabled) {
        // 執行完整的兩階段搜索
        console.log('啟用反例搜索，執行兩階段搜索');
        
        // ✅ 新增：使用統一架構 - 構建反例搜索請求對象
        const negativeSearchRequest: SimpleSearchRequest = {
          name: '反例搜索',
          symbols: normalizedSymbols,  // 使用相同的交易對
          timeframe: searchParams.timeframe,  // 使用相同的時間框架
          searchMode: searchParams.searchMode,
          priceChangeMethod: searchParams.priceChangeMethod, // 使用相同的價格計算方式
          priceChange: negativeParams.priceChange,
          volumeMultiplier: negativeParams.volumeMultiplier,
          closingStrength: negativeParams.closingStrength,
          takerBuyRatio: negativeParams.takerBuyRatio,
          pricePosition: negativeParams.pricePosition,
          saveResults: false
        };
        
        console.log('反例搜索請求對象:', negativeSearchRequest);
        console.log('反例運算符:', negativeOperators);
        console.log('反例範圍值:', negativeRangeValues);

        // ✅ 修改：API調用 - 注意參數順序已改變
        const result = await apiClient.executeTwoStageSearch(
          // 參數1：正例 SearchRequest 對象
          {
            name: apiRequest.config.name,
            timeframe: apiRequest.config.timeframe,
            searchMode: searchParams.searchMode,
            startDate: apiRequest.config.start_date,
            endDate: apiRequest.config.end_date,
            priceChangeMethod: searchParams.priceChangeMethod, // 價格計算方式
            priceChange: searchParams.priceChange,
            volumeMultiplier: searchParams.volumeMultiplier,
            takerBuyRatio: searchParams.takerBuyRatio,
            closingStrength: searchParams.closingStrength,
            symbols: apiRequest.symbols,
            saveResults: apiRequest.save_results
          },
          // 參數2：negativeRatio (number)
          negativeParams.ratio,
          // 參數3：enableTimeSeparation (boolean)
          negativeParams.enableTimeSeparation,
          // 參數4：timeSeparationDays (number)
          negativeParams.timeSeparationDays,
          // 參數5：onProgress (function)
          (stage: string, taskId?: string) => {
            setCurrentStage(`${stage}${taskId ? `, 任務ID: ${taskId}` : ''}`);
            console.log(`搜索階段: ${stage}${taskId ? `, 任務ID: ${taskId}` : ''}`);
          },
          // 參數6：negativeRequest (SearchRequest) - 🔥 新的統一架構
          negativeSearchRequest,
          // 參數7：negativeOperators (object) - 🔥 新的統一架構
          negativeOperators,
          // 參數8：negativeRangeValues (object) - 🔥 新的統一架構
          negativeRangeValues,
          // 參數9：operators (object) - 正例運算符
          operators,
          // 參數10：rangeValues (object) - 正例範圍值
          rangeValues,
          // 參數11：enableRandomSampling (boolean) - ===== 新增：隨機取樣開關 =====
          negativeParams.enableRandomSampling
        );

        // 直接設定搜索結果
        setSearchResult(result);
        console.log('兩階段搜索完成，結果:', result);
        return; // 提前返回，不執行下面的單一搜索邏輯
      
      } else {
        // 執行單一正例搜索（原有邏輯）
        console.log('未啟用反例搜索，執行單一正例搜索');
        setCurrentStage('正例搜索中...');
        
        const response = await apiClient.executeSearch(
          // 參數1：搜索請求對象（使用簡化的格式）
          {
            name: apiRequest.config.name,
            timeframe: apiRequest.config.timeframe,
            searchMode: searchParams.searchMode,
            startDate: apiRequest.config.start_date,
            endDate: apiRequest.config.end_date,
            priceChangeMethod: searchParams.priceChangeMethod, // 價格計算方式
            priceChange: searchParams.priceChange,
            volumeMultiplier: searchParams.volumeMultiplier,
            takerBuyRatio: searchParams.takerBuyRatio,
            closingStrength: searchParams.closingStrength,
            pricePosition: searchParams.pricePosition,  // 新增：確保包含所有欄位
            symbols: apiRequest.symbols,
            saveResults: apiRequest.save_results
          },
          // 參數2：operators - 正例運算符
          operators,
          // 參數3：rangeValues - 正例範圍值
          rangeValues
        );
        
        if (!response.success || !response.data) {
          throw new Error(`搜索任務啟動失敗: ${response.error?.message || '未知錯誤'}`);
        }
        
        const taskId = response.data.task_id;
        console.log('單一搜索任務啟動成功，任務ID:', taskId);
        
        // 等待搜索完成
        setCurrentStage('等待搜索完成...');
        await waitForTaskCompletion(taskId);
      }
      
      
    } catch (err) {
      console.error('階段搜索失敗:', err);
      
      // 分析錯誤類型並提供友善訊息
      let userFriendlyMessage = '';
      const errorMessage = err instanceof Error ? err.message : String(err);
      
      if (errorMessage.includes('未知錯誤') || errorMessage.includes('undefined')) {
        userFriendlyMessage = '在指定條件和時間範圍內未找到符合的案例。建議：放寬搜索條件或擴大時間範圍';
      } else if (errorMessage.includes('timeout')) {
        userFriendlyMessage = '搜索超時，可能是數據量過大或條件複雜。建議：縮小時間範圍或簡化搜索條件';
      } else if (errorMessage.includes('No cases found') || errorMessage.includes('沒有找到')) {
        userFriendlyMessage = '未找到符合條件的案例。建議：調整價格變化閾值，或擴大時間範圍';
      } else if (errorMessage.includes('422') || errorMessage.includes('參數驗證')) {
        userFriendlyMessage = '搜索參數有誤。請檢查：交易對格式、日期範圍是否正確';
      } else {
        userFriendlyMessage = `搜索失敗：${errorMessage}`;
      }
      
      setError(userFriendlyMessage);
    } finally {
      setLoading(false);
    }
  };

  // 等待任務完成
  const waitForTaskCompletion = async (taskId: string) => {
    const maxAttempts = 30;
    
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        console.log(`檢查任務狀態 (${attempt}/${maxAttempts}): ${taskId}`);
        
        const statusResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}`);
        
        if (!statusResponse.ok) {
          throw new Error(`狀態查詢失敗: ${statusResponse.status}`);
        }
        
        const statusData = await statusResponse.json();
        
        if (!statusData.success || !statusData.data) {
          throw new Error(`狀態查詢失敗: ${statusData.error?.message || '未知錯誤'}`);
        }
        
        const status = statusData.data.status.toUpperCase();
        console.log(`任務狀態: ${statusData.data.status} (標準化: ${status})`);
        
        if (status === 'COMPLETED') {
          setCurrentStage('獲取搜索結果...');
          const resultResponse = await fetch(`http://localhost:8000/api/v1/search/task/${taskId}/result`);
          
          if (!resultResponse.ok) {
            throw new Error(`結果獲取失敗: ${resultResponse.status}`);
          }
          
          const resultData = await resultResponse.json();
          
          if (!resultData.success || !resultData.data) {
            throw new Error(`結果獲取失敗: ${resultData.error?.message || '未知錯誤'}`);
          }
          
          setSearchResult(resultData.data);
          setCurrentStage(`搜索完成！找到 ${resultData.data.summary.total_cases} 個案例`);
          return;
          
        } else if (status === 'FAILED' || status === 'ERROR') {
          console.log('完整錯誤回應:', statusData);
          const errorMsg = statusData.data.message || statusData.data.error_message || statusData.message || '未知錯誤';
          throw new Error(`搜索任務失敗: ${errorMsg}`);
        }
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (err) {
        console.error(`任務狀態檢查錯誤 (嘗試 ${attempt}):`, err);
        
        if (attempt === maxAttempts) {
          throw new Error(`任務狀態檢查超時: ${err instanceof Error ? err.message : '未知錯誤'}`);
        }
      }
    }
  };

  // GAP-3 B5.2：匯出事件契約 JSON（新 schema；label 取正反例標記、t0＝timestamp→ms、規則摘要自動存；
  // 使用者仍可手改後投 /case/import-events。不做任何統計，只組記錄）
  const exportSearchResultsToEventJson = async () => {
    if (!currentResult || !currentResult.cases || currentResult.cases.length === 0) {
      alert('沒有搜索結果可以匯出');
      return;
    }
    // GAP-3 UX Task 1.9′ 守衛（承襲 `D-004 A-021(c)` 之 `proceed` 結構保證）：**宣告未通過 ⇒ fail-closed**。
    // 🔴 缺 preview／缺 map／批內某 tf 無鍵／非 int／`< 0`／調低未勾聲明 ⇒ 一個網路／下載動作都不許發生。
    //    判定與訊息都住在守衛裡（**單一實作**，只呼叫同一份 `validateDeclaration`）。
    // 🔴 整段匯出邏輯**包在 proceed 內**——「阻擋早於任何網路動作」因此是結構上保證的事實，
    //    不是需要用原始碼形狀去檢查的性質（GROK-R3-P2-01 等三條之修法）。
    //    **不得**退回裸 `if (…) return;` 後接長串 `await`（B5 R3 已否定之形狀）。
    return withExportDeclarationGuard(declState, {
      notify: alert,
      proceed: async () => {
    const { buildEventContractRecords } = await import('@/lib/eventExport');
    // 規則摘要（G3：條件自動存；值單位同 UI：% 與倍數）
    // 🔴 D3.1：改用元件層之 `positiveStageConditions`（原本這裡與 CSV handler 各有一份
    //    逐字相同的陣列；D3.1 需要在元件層知道兩段內容，順手收成單一來源）。
    const ruleConditions = positiveStageConditions;
    // GAP-3 UX Task 1.3：`source_file_digest` 綁**完整 CaseData 列**且**一律由後端計算**
    // （`/search` 結果端點回應之兩鍵）。前端只傳遞，不自算、不重新序列化。
    // 🔴 R 重開 D-8 規則①：匯出＝搜尋結果**全部**列（無篩選）；正反例判定在系統外完成。
    const payload = await buildEventContractRecords(currentResult.cases as CaseData[], {
      timeframe: searchParams.timeframe,
      conditions: ruleConditions,
      priceChangeMethod: String(searchParams.priceChangeMethod ?? ''),
      attachedHorizons,
      // D-8 規則②：`lookahead_bars_declared = declared_window_bars`（逐鍵複製；兩條匯出同一函式）
      lookaheadBarsDeclared: declaredWindowBarsForExport(declState),
      sourceFileText: currentResult.source_file_text ?? '',
      sourceFileDigest: currentResult.source_file_digest ?? '',
      // 🔴 Task 7.1：五維度**逐一**由 UI 狀態傳入。漏傳任一個都會讓落檔悄悄退回
      //    `eventExport.ts` 的預設值（介面有、沒傳）——Task 7.2 ② 之機械閘即守這件事。
      ...eventDimsToExportOptions(eventDims),
      // 🔴 D3.1：兩段條件。反例未啟用 ⇒ 只有一段 ⇒ 由 `buildEventContractRecords` 阻擋。
      stageConditions: exportStageConditions,
    });
    // GAP-3 UX Task 4.3 ＋ 5.3：**同一個**確認框（5.3 是 4.3 的擴寫，不另建第二個）。
    // 4.3＝逐附帶 horizon 列出筆數；5.3＝改為**主動顯示**每個附帶欄各有幾筆可算、幾筆缺，
    // 使用者不必自己去湊時間點才知道（SPEC L2092–2105：「現行只在缺…時跳，**改為**主動顯示」）。
    // 🔴 匯出端已無「答案窗缺欄」這件事（`label_value` 不在匯出檔內）⇒ 只剩附帶欄一類；
    //    訊息**不得**出現「主答案窗」字樣。缺欄**不阻擋匯出**（使用者仍可按確定）。
    const coverageLines = horizonCoverageLines(payload);
    if (coverageLines.length > 0) {
      const proceed = window.confirm(
        `每個附帶報酬欄各有幾筆算得出來（不必自己去湊案例時間點）：\n${coverageLines.join('\n')}\n\n`
        + '算不出來的那幾筆就不會帶該欄，其他欄與其他列都不受影響。'
        + '附帶欄只是給你在 Excel 裡看的，不影響匯入、也不決定任何分析用的答案窗。仍要匯出嗎？',
      );
      if (!proceed) return;
    }
    const stamp = new Date().toISOString().slice(0, 10);
    const download = (text: string, name: string, type: string) => {
      const url = URL.createObjectURL(new Blob([text], { type }));
      const link = document.createElement('a');
      link.href = url;
      link.download = name;
      link.click();
      URL.revokeObjectURL(url);
    };
    download(JSON.stringify(payload, null, 2), `events_${stamp}.json`, 'application/json;charset=utf-8;');
    // 同時下載「來源檔」：其 sha256 === 每列 source_file_digest；匯入時放 source_file 欄即可通過 verify
    download(payload.source_file_text, `events_${stamp}.source.json`, 'application/json;charset=utf-8;');
      },
    });
  };

  /**
   * CSV 導出 —— 🔴 **改為「可直接回灌」之契約 CSV**（2026-09-01 使用者裁定）。
   *
   * 病因（使用者 UAT B9）：舊版用展示用欄名（`Timestamp`／`Positive_Case`／`Price_Change_%`），
   * 與契約欄名、型別、單位全對不上 ⇒ 使用者在 Excel 標好正反例後**回不去**：
   * 要逐欄對映，還要手寫含兩個 64 位 hex digest 的批次預設 JSON。
   * 而「自己決定哪些是正例」正是本 epic 的核心前提。
   *
   * 🔴 **與 JSON 匯出走同一條路**（同一個 `buildEventContractRecords`）⇒ 兩種匯出不可能漂移；
   *    也因此**同樣受宣告守衛保護**（沒宣告答案窗就不讓匯出），不再是「CSV 可以繞過」。
   * 🔴 非契約之分析欄放進 `meta.`（契約自由欄）：Excel 裡照樣看得到、篩得動，
   *    且不會被 `unknown_field` 拒收。
   * 🔴 答案只有 `label` 一欄（0／1）；不再另寫 `Positive_Case`——
   *    兩欄並存時使用者改一個、系統讀另一個，是必然的誤會來源。
   */
  const exportSearchResultsToCSV = async () => {
    if (!currentResult || !currentResult.cases || currentResult.cases.length === 0) {
      alert('沒有搜索結果可以導出');
      return;
    }
    return withExportDeclarationGuard(declState, {
      notify: alert,
      proceed: async () => {
        const { buildEventContractRecords } = await import('@/lib/eventExport');
        const { buildEventContractCsv } = await import('@/lib/eventContractCsv');
        // 🔴 D3.1：與 JSON handler 同一份（元件層 `positiveStageConditions`）。
        const ruleConditions = positiveStageConditions;

        const filtered = currentResult.cases as CaseData[];   // D-8 規則①：全部列，無篩選
        const payload = await buildEventContractRecords(filtered, {
          timeframe: searchParams.timeframe,
          conditions: ruleConditions,
          priceChangeMethod: String(searchParams.priceChangeMethod ?? ''),
          attachedHorizons,
          // 🔴 Task 1.9′ 驗證⑥：與 JSON 路徑呼叫**同一函式**組 map（CSV 不得另組一份）
          lookaheadBarsDeclared: declaredWindowBarsForExport(declState),
          sourceFileText: currentResult.source_file_text ?? '',
          sourceFileDigest: currentResult.source_file_digest ?? '',
          ...eventDimsToExportOptions(eventDims),
          // 🔴 CSV 帶**全部**列（未標記者 `label` 留空給你在 Excel 補）——
          //    丟掉那些列等於剝奪你補標記的機會，而匯入端對缺 label 是整批拒收。
          includeUnlabeled: true,
          // 🔴 D3.1：與 JSON 路徑同一份（`negativeStageConditions` 為元件層單一來源）。
          stageConditions: exportStageConditions,
        });

        // 🔴 `meta.` 之內容＝**該列自己的**非契約欄；逐列取，不跨列共用。
        //    只帶原始數值（不轉百分比）——與篩選面板同一套單位，避免「兩個框單位不同」那個陷阱。
        //
        // 🔴 **不得改回白名單**（2026-09-02 使用者 UAT：`future_*bar_max_drawdown` 整批不見了）：
        //    原版是手寫 24 個欄名的 `META_KEYS`，於是搜尋結果新增／改名的欄一律**靜默消失**，
        //    而使用者要靠這些欄在 Excel 裡篩正反例。規則改為**可導出的補集**：
        //    「該列所有欄 − 已由契約欄承載者」。與後端 `_nested_fields()` 同一次修法
        //    （手寫清單漏項，見 `G3-D4`）——這是第二次踩，故兩端都不再留清單。
        /**
         * 原始欄 → 已承載它的契約欄。**唯一目的是避免同一件事出現兩個欄**，
         * 不是拿來過濾內容的白名單（每加一筆都要能說出「哪個契約欄已經表達了它」）。
         * `timestamp` 刻意**不列入**：契約的 `t0` 是 epoch 毫秒，人在 Excel 裡讀不了。
         */
        const SUPERSEDED_BY_CONTRACT_FIELD: Record<string, string> = { positive_case: 'label' };
        // 逐列對齊：`buildEventContractRecords` 會跳過無法解析 t0／無正反例標記之列，
        // 故以 `event_id` 對回原始列，不用位置索引（位置對不上就會張冠李戴）。
        const byEventId = new Map<string, Record<string, unknown>>();
        for (const row of filtered as unknown as Record<string, unknown>[]) {
          const t0 = toEpochMs(row.timestamp as string | number | null | undefined);
          if (t0 === null) continue;
          byEventId.set(
            canonicalEventId(String(row.symbol), String(row.timeframe || searchParams.timeframe), t0),
            row,
          );
        }
        const extras = (payload.records as Record<string, unknown>[]).map((rec) => {
          const src = byEventId.get(String(rec.event_id)) ?? {};
          const contractKeys = new Set(Object.keys(rec));
          const out: Record<string, unknown> = {};
          for (const [k, v] of Object.entries(src)) {
            if (v === undefined) continue;
            if (contractKeys.has(k)) continue;                    // 已是契約頂層欄，不重複輸出
            if (SUPERSEDED_BY_CONTRACT_FIELD[k] !== undefined) continue;
            out[k] = v;
          }
          return out;
        });

        const csv = buildEventContractCsv(payload.records as Record<string, unknown>[], extras);
        const stamp = new Date().toISOString().slice(0, 10);
        const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
        const link = document.createElement('a');
        link.href = url;
        link.download = `events_${stamp}.csv`;
        link.click();
        URL.revokeObjectURL(url);
      },
    });
  };

  // 渲染正例欄位輸入框
  const renderFieldInput = (fieldKey: keyof SimpleSearchRequest, label: string, placeholder: string) => {
    const operator = operators[fieldKey as keyof typeof operators];
    const fieldValue = searchParams[fieldKey] as number | null;
    const range = rangeValues[fieldKey as keyof typeof rangeValues];

    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="block text-sm font-medium text-slate-200">
            {label}
          </label>
          <div className="group relative">
            <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
            <div className="absolute left-0 top-6 hidden group-hover:block bg-[#1a233a] text-slate-100 text-xs rounded px-3 py-2 z-10 w-72 shadow-lg border border-white/10 backdrop-blur-xl">
              {FIELD_DESCRIPTIONS[fieldKey as keyof typeof FIELD_DESCRIPTIONS]}
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* 運算符選擇 */}
          <select
            value={operator}
            onChange={(e) => setOperators(prev => ({
              ...prev,
              [fieldKey]: e.target.value
            }))}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-sm text-slate-100"
          >
            {OPERATORS.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
          
          {/* 數值輸入 */}
          {operator === 'BETWEEN' ? (
            <>
              <input
                type="number"
                value={range.min || ''}
                onChange={(e) => setRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { ...prev[fieldKey as keyof typeof rangeValues], min: e.target.value ? parseFloat(e.target.value) : null }
                }))}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
                placeholder="最小值"
              />
              <input
                type="number"
                value={range.max || ''}
                onChange={(e) => setRangeValues(prev => ({
                  ...prev,
                  [fieldKey]: { ...prev[fieldKey as keyof typeof rangeValues], max: e.target.value ? parseFloat(e.target.value) : null }
                }))}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
                placeholder="最大值"
              />
            </>
          ) : (
            <input
              type="number"
              value={fieldValue || ''}
              onChange={(e) => setSearchParams(prev => ({
                ...prev,
                [fieldKey]: e.target.value ? parseFloat(e.target.value) : null
              }))}
              // 🔴 `G3-D2` D3.1：正例條件＝two_stage 之第一段；填了值第一段才非空。
              data-testid={`positive-field-${fieldKey}`}
              className="col-span-2 px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500"
              placeholder={placeholder}
            />
          )}
        </div>
      </div>
    );
  };

  // 渲染反例欄位輸入框
  const renderNegativeFieldInput = (fieldKey: 'priceChange', label: string, placeholder: string) => {
    const operator = negativeOperators[fieldKey];
    const fieldValue = negativeParams[fieldKey] as number | null;

    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="block text-sm font-medium text-slate-200">
            {label} (反例條件)
          </label>
          <div className="group relative">
            <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
            <div className="absolute left-0 top-6 hidden group-hover:block bg-[#1a233a] text-slate-100 text-xs rounded px-3 py-2 z-10 w-72 shadow-lg border border-white/10 backdrop-blur-xl">
              反例條件：用於篩選不符合預期表現的案例。通常與正例條件相反。
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2">
          {/* 運算符選擇 */}
          <select
            value={operator}
            onChange={(e) => setNegativeOperators(prev => ({
              ...prev,
              [fieldKey]: e.target.value
            }))}
            // 🔴 `G3-D2` D3.1 R1（`CODEX-R1-P1-03`）：選 BETWEEN 時值住 `negativeRangeValues`，
            //    第二段之組法必須跟著走；testid 供 DOM 驗收切到該分支。
            data-testid={`negative-op-${fieldKey}`}
            className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-sm text-slate-100"
          >
            {OPERATORS.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
          
          {/* 數值輸入 */}
          {operator === 'BETWEEN' ? (
            <>
              <input
                type="number"
                value={negativeRangeValues.priceChange?.min || ''}
                onChange={(e) => setNegativeRangeValues(prev => ({
                  ...prev,
                  priceChange: { 
                    ...prev.priceChange, 
                    min: e.target.value ? parseFloat(e.target.value) : null 
                  }
                }))}
                data-testid={`negative-range-min-${fieldKey}`}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-slate-100"
                placeholder="最小值"
              />
              <input
                type="number"
                value={negativeRangeValues.priceChange?.max || ''}
                onChange={(e) => setNegativeRangeValues(prev => ({
                  ...prev,
                  priceChange: { 
                    ...prev.priceChange, 
                    max: e.target.value ? parseFloat(e.target.value) : null 
                  }
                }))}
                data-testid={`negative-range-max-${fieldKey}`}
                className="px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-slate-100"
                placeholder="最大值"
              />
            </>
          ) : (
            <input
              type="number"
              value={fieldValue || ''}
              onChange={(e) => setNegativeParams(prev => ({
                ...prev,
                [fieldKey]: e.target.value ? parseFloat(e.target.value) : null
              }))}
              // 🔴 `G3-D2` D3.1：填了值第二段才非空；testid 供 DOM 驗收驅動。
              data-testid={`negative-field-${fieldKey}`}
              className="col-span-2 px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-slate-100 placeholder:text-slate-500"
              placeholder={placeholder}
            />
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full overflow-auto">
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* 頁面標題 */}
        <div>
          <h1 className="text-2xl font-medium text-slate-100 mb-2">階段案例搜索</h1>
          <p className="text-slate-400">
            設定正例搜索條件，系統將自動生成對應的反例數據集
          </p>
        </div>

        {/* 基本設定 */}
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-medium text-slate-100 mb-4">基本設定</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 搜索名稱 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                搜索名稱
              </label>
              <input
                type="text"
                value={searchParams.name}
                onChange={(e) => setSearchParams(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500"
                placeholder="例如: USDT突破策略搜索"
              />
            </div>
            
            {/* 交易對輸入 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                交易對 (支援多個，用逗號分隔)
              </label>
              <input
              type="text"
              value={symbolsInput}
              onChange={(e) => {
                setSymbolsInput(e.target.value);
              }}
              onBlur={() => {
                const symbols = parseSymbolsInput(symbolsInput);
                setSearchParams(prev => ({ ...prev, symbols }));
                setSymbolsInput(symbols.join(', '));
              }}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500"
              placeholder="例如: BTCUSDT, ETHUSDT 或 ETHUSDT，BNBUSDT"
            />
              <p className="text-sm text-slate-400 mt-1">
                支援：加密貨幣 (USDT對), 股票代碼, 期貨合約, RWA 標的等
              </p>
            </div>
            
            {/* 時間框架 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                時間框架
              </label>
              <select
                value={searchParams.timeframe}
                onChange={(e) => setSearchParams(prev => ({ ...prev, timeframe: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
              >
                <option value="4h">4小時</option>
                <option value="12h">12小時</option>
                <option value="1d">1天</option>
              </select>
            </div>
            
            {/* 價格變動計算方式 */}
            <div>
              <div className="flex items-center gap-2 mb-2">
                <label className="block text-sm font-medium text-slate-200">
                  價格變動計算方式
                </label>
                <div className="group relative">
                  <HelpCircle className="w-4 h-4 text-slate-500 cursor-help" />
                  <div className="absolute left-0 top-6 hidden group-hover:block bg-[#1a233a] text-slate-100 text-xs rounded px-3 py-2 z-10 w-96 shadow-lg border border-white/10 backdrop-blur-xl">
                    <p className="font-semibold mb-2">OPEN_TO_CLOSE (日內交易)：</p>
                    <p className="mb-2">計算當根K線內的價格變化 = (Close - Open) / Open</p>
                    <p className="mb-3">適合日內波動策略，不考慮跳空。</p>
                    <p className="font-semibold mb-2">CLOSE_TO_CLOSE (波段交易)：</p>
                    <p>計算相對前一根K線的價格變化 = pct_change()</p>
                    <p>適合波段策略，包含跳空影響。(預設)</p>
                  </div>
                </div>
              </div>
              <select
                value={searchParams.priceChangeMethod}
                onChange={(e) => setSearchParams(prev => ({ 
                  ...prev, 
                  priceChangeMethod: e.target.value as PriceChangeMethod 
                }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
              >
                <option value={PriceChangeMethod.CLOSE_TO_CLOSE}>
                  前收盤到當收盤 (波段交易，含跳空) - 預設
                </option>
                <option value={PriceChangeMethod.OPEN_TO_CLOSE}>
                  當開盤到當收盤 (日內交易)
                </option>
              </select>
              <p className="text-sm text-slate-400 mt-1">
                {searchParams.priceChangeMethod === PriceChangeMethod.CLOSE_TO_CLOSE 
                  ? '計算方式：(當根收盤價 - 前根收盤價) / 前根收盤價 * 100%' 
                  : '計算方式：(當根收盤價 - 當根開盤價) / 當根開盤價 * 100%'}
              </p>
            </div>

            {/* 搜索模式 */}
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                搜索模式
              </label>
              <select
                value={searchParams.searchMode || 'research'}
                onChange={(e) =>
                  setSearchParams((prev) => ({
                    ...prev,
                    searchMode: e.target.value as 'research' | 'realtime',
                  }))
                }
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
              >
                <option value="research">Research（保留完整 future 標籤）</option>
                <option value="realtime">Realtime（允許最新時間樣本）</option>
              </select>
              <p className="text-sm text-slate-400 mt-1">
                {searchParams.searchMode === 'realtime'
                  ? '即時模式會包含尾端最新案例，部分 future 欄位可能為空。'
                  : '研究模式會略過尾端 forward 期間，確保 future 欄位完整。'}
              </p>
            </div>
          </div>
          
          {/* 時間日期區間 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                開始日期
              </label>
              <input
                type="date"
                value={timeParams.startDate}
                onChange={(e) => setTimeParams(prev => ({ ...prev, startDate: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-200 mb-2">
                結束日期
              </label>
              <input
                type="date"
                value={timeParams.endDate}
                onChange={(e) => setTimeParams(prev => ({ ...prev, endDate: e.target.value }))}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100"
              />
            </div>
          </div>
          
          {/* 最小交易量 */}
          <div className="mt-6">
            <label className="block text-sm font-medium text-slate-200 mb-2">
              最小交易量 (USDT)
            </label>
            <input
              type="number"
              value={timeParams.volumeMin || ''}
              onChange={(e) => setTimeParams(prev => ({ 
                ...prev, 
                volumeMin: e.target.value ? parseFloat(e.target.value) : null 
              }))}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-400 text-slate-100 placeholder:text-slate-500"
              placeholder="留空 = 不限制，例如: 100000"
            />
            <p className="text-sm text-slate-400 mt-1">
              留空表示不對交易量設限制，輸入數值則過濾小於該值的案例
            </p>
          </div>
        </div>

        {/* 正例搜索條件 */}
        <div className="glass-panel rounded-xl">
          <div 
            className="p-4 border-b border-white/10 cursor-pointer hover:bg-white/5 flex items-center justify-between"
            onClick={() => toggleSection('positive')}
          >
            <h3 className="text-lg font-medium text-slate-100">正例搜索條件</h3>
            {expandedSections.positive ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
          
          {expandedSections.positive && (
            <div className="p-6">
              <div className="max-w-md">
                {renderFieldInput('priceChange', '價格變化 (%)', '例如: 5.0')}
              </div>
              
              <div className="mt-4 p-4 bg-blue-400/10 rounded-xl border border-blue-400/20">
                <p className="text-sm text-blue-300">
                  <strong>說明：</strong>正例搜索只需設定價格變化條件，其他30個參數會自動計算並輸出到CSV中供您後續分析使用。
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 反例搜索設定 */}
        <div className="glass-panel rounded-xl">
          <div
            className="p-4 border-b border-white/10 cursor-pointer hover:bg-white/5 flex items-center justify-between"
            onClick={() => toggleSection('negative')}
            // 🔴 `G3-D2` D3.1：反例區＝two_stage 之第二段來源；testid 供 DOM 驗收展開它。
            data-testid="negative-section-header"
          >
            <h3 className="text-lg font-medium text-slate-100">反例搜索設定</h3>
            {expandedSections.negative ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
          </div>
          
          {expandedSections.negative && (
            <div className="p-6 space-y-6">
              {/* 基本反例設定 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <label className="block text-sm font-medium text-slate-200 mb-2">
                    反例比例
                  </label>
                  <input
                    type="number"
                    value={negativeParams.ratio}
                    onChange={(e) => setNegativeParams(prev => ({ 
                      ...prev, 
                      ratio: parseFloat(e.target.value) || 2.0 
                    }))}
                    className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-slate-100"
                    placeholder="2.0"
                    step="1"
                    min="1"
                  />
                  <p className="text-sm text-slate-400 mt-1">反例數量 = 正例數量 × 比例</p>
                </div>
                
                <div>
                  <label className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={negativeParams.enableTimeSeparation}
                      onChange={(e) => setNegativeParams(prev => ({
                        ...prev,
                        enableTimeSeparation: e.target.checked
                      }))}
                      className="mr-2 h-4 w-4 text-rose-400 focus:ring-rose-400 border-white/10 rounded"
                    />
                    <span className="text-sm font-medium text-slate-200">
                      啟用時間分離
                    </span>
                  </label>
                  <p className="text-sm text-slate-400 mb-2">
                    防止反例與正例在時間上過於接近（按Symbol獨立計算）
                  </p>

                  {negativeParams.enableTimeSeparation && (
                    <div>
                      <label className="block text-sm font-medium text-slate-200 mb-2">
                        時間分離天數
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="30"
                        value={negativeParams.timeSeparationDays}
                        onChange={(e) => setNegativeParams(prev => ({
                          ...prev,
                          timeSeparationDays: parseInt(e.target.value) || 3
                        }))}
                        className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-md focus:outline-none focus:ring-2 focus:ring-rose-400 text-slate-100"
                        placeholder="3"
                      />
                      <p className="text-sm text-slate-400 mt-1">
                        反例將排除在同symbol正例前後N天內的案例（預設3天，0=關閉）
                      </p>
                    </div>
                  )}
                </div>

                {/* ===== 新增：隨機取樣開關 ===== */}
                <div>
                  <label className="flex items-center mb-2">
                    <input
                      type="checkbox"
                      checked={negativeParams.enableRandomSampling}
                      onChange={(e) => setNegativeParams(prev => ({
                        ...prev,
                        enableRandomSampling: e.target.checked
                      }))}
                      className="mr-2 h-4 w-4 text-rose-400 focus:ring-rose-400 border-white/10 rounded"
                    />
                    <span className="text-sm font-medium text-slate-200">
                      啟用隨機取樣
                    </span>
                  </label>
                  <p className="text-sm text-slate-400">
                    啟用時根據比例隨機選擇反例；關閉時返回所有符合條件的反例
                  </p>
                </div>

                <div className="flex items-center space-y-2">
                  <div>
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={negativeParams.enabled}
                        onChange={(e) => setNegativeParams(prev => ({
                          ...prev,
                          enabled: e.target.checked
                        }))}
                        // 🔴 `G3-D2` D3.1：本開關即「第二段存在與否」⇒ two_stage 之匯出阻擋
                        //    直接由它決定。testid 供 `twoStageExportWiring.test.tsx` 之 DOM 驗收使用。
                        data-testid="negative-enabled-toggle"
                        className="mr-2 w-4 h-4 text-rose-400 border-white/10 rounded focus:ring-rose-400"
                      />
                      <span className="text-sm text-slate-200 font-medium">
                        啟用反例搜索
                      </span>
                    </label>
                    <p className="text-sm text-slate-400 mt-1">關閉則只搜索正例</p>
                  </div>
                </div>
              </div>
              
              {/* 反例篩選條件 */}
              {negativeParams.enabled && (
                <div>
                  <h4 className="text-md font-medium text-slate-100 mb-4 border-b border-white/10 pb-2">
                    反例篩選條件 (可選)
                  </h4>
                  <p className="text-sm text-slate-400 mb-4">
                    設定反例的具體條件，通常與正例條件相反。留空則由系統自動生成。
                  </p>
                  
                  <div className="max-w-md">
                    {renderNegativeFieldInput('priceChange', '價格變化 (%)', '例如: -2.0')}
                  </div>

                  

                </div>
              )}
            </div>
          )}
        </div>

        {/* 執行按鈕 */}
        <div className="glass-panel rounded-xl p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-medium text-slate-100">執行搜索</h3>
              {currentStage && (
                <p className="text-sm text-blue-400 mt-1 font-medium">{currentStage}</p>
              )}
            </div>
            <button
              onClick={executeTwoStageSearch}
              disabled={isLoading}
              className="inline-flex items-center px-6 py-3 bg-blue-500 text-white rounded-lg font-medium hover:bg-blue-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <RefreshCw className="w-5 h-5 animate-spin mr-2" />
              ) : (
                <Search className="w-5 h-5 mr-2" />
              )}
              {isLoading ? '搜索中...' : '開始階段搜索'}
            </button>
          </div>
        </div>

        {/* 錯誤顯示 */}
        {error && (
          <div className="bg-rose-400/10 border border-rose-400/20 rounded-lg p-4">
            <div className="flex items-center gap-2 text-rose-400">
              <AlertCircle className="w-5 h-5" />
              <span className="font-medium">錯誤：{error}</span>
            </div>
          </div>
        )}

        {/* 搜索結果 */}
        {currentResult && (
          <div className="glass-panel rounded-xl p-6">
            <h3 className="text-lg font-medium text-slate-100 mb-4">搜索結果</h3>

            {(() => {
              // 計算實際統計數據
              const actualStats = calculateActualStatistics(currentResult.cases);
              
              // 驗證後端統計數據與實際數據的一致性
              const validation = validateBackendStatistics(actualStats, currentResult.summary);
              
              return (
                <>
                  {/* 統計卡片 */}
                  <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                    <div className="text-center p-4 bg-blue-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-blue-400">{actualStats.totalCases}</div>
                      <div className="text-sm text-slate-400">總案例數</div>
                    </div>
                    
                    <div className="text-center p-4 bg-emerald-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-emerald-400">{actualStats.positiveCases}</div>
                      <div className="text-sm text-slate-400">正例案例</div>
                      <div className="text-xs text-slate-500 mt-1">positive_case=1</div>
                    </div>
                    
                    <div className="text-center p-4 bg-rose-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-rose-400">{actualStats.negativeCases}</div>
                      <div className="text-sm text-slate-400">反例案例</div>
                      <div className="text-xs text-slate-500 mt-1">positive_case=0</div>
                    </div>
                    
                    <div className="text-center p-4 bg-purple-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-purple-400">{actualStats.uniqueSymbols}</div>
                      <div className="text-sm text-slate-400">交易對數</div>
                    </div>
                    
                    <div className="text-center p-4 bg-orange-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-orange-400">{currentResult.execution_time?.toFixed(1) || 'N/A'}s</div>
                      <div className="text-sm text-slate-400">執行時間</div>
                    </div>
                    
                    <div className="text-center p-4 bg-amber-400/10 rounded-lg">
                      <div className="text-2xl font-semibold text-amber-400">{actualStats.positiveRatio}</div>
                      <div className="text-sm text-slate-400">正負比例</div>
                    </div>
                  </div>

                  {/* 交易對詳情 */}
                  {actualStats.symbolsList.length > 0 && (
                    <div className="mt-4 p-3 bg-white/5 rounded-lg">
                      <div className="text-sm font-medium text-slate-300 mb-2">
                        包含的交易對 ({actualStats.uniqueSymbols} 個)：
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {actualStats.symbolsList.map(symbol => (
                          <span key={symbol} className="px-2 py-1 bg-blue-400/15 text-blue-400 text-xs rounded">
                            {symbol}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 統計摘要 */}
                  <div className="mt-4 p-3 bg-blue-400/10 rounded-lg border border-blue-400/20">
                    <div className="text-sm text-blue-300">
                      📊 {getStatisticsSummary(actualStats)}
                    </div>
                  </div>

                  {/* 數據一致性驗證 */}
                  {!validation.isConsistent && (
                    <div className="mt-4 p-3 bg-amber-400/10 border border-amber-400/20 rounded-lg">
                      <div className="text-sm text-amber-300">
                        <div className="font-medium mb-2">⚠️ 數據一致性警告：</div>
                        <ul className="list-disc list-inside space-y-1">
                          {validation.differences.map((diff, index) => (
                            <li key={index}>{diff}</li>
                          ))}
                        </ul>
                        <div className="mt-2 text-xs">
                          建議：使用實際統計數據（上方顯示）而非後端 summary 數據
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 市場階段分布 - 圓餅圖顯示 */}
                  {(Object.keys(actualStats.positiveMarketPhases).length > 0 || Object.keys(actualStats.negativeMarketPhases).length > 0) && (
                    <div className="mt-4 p-4 glass-panel rounded-xl">
                      <div className="text-lg font-medium text-slate-100 mb-4">市場階段分布</div>
                      
                      {/* 圓餅圖 */}
                      <MarketPhasePieChart 
                        positiveData={actualStats.positiveMarketPhases}
                        negativeData={actualStats.negativeMarketPhases}
                      />
                      
                      {/* 詳細數據標籤 */}
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* 正例市場階段分布 */}
                        {Object.keys(actualStats.positiveMarketPhases).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-emerald-400 mb-2">正例市場階段：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.positiveMarketPhases).map(([phase, count]) => (
                                <span key={`pos-${phase}`} className="px-2 py-1 bg-emerald-400/15 text-emerald-400 text-xs rounded">
                                  {phase}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {/* 反例市場階段分布 */}
                        {Object.keys(actualStats.negativeMarketPhases).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-rose-400 mb-2">反例市場階段：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.negativeMarketPhases).map(([phase, count]) => (
                                <span key={`neg-${phase}`} className="px-2 py-1 bg-rose-400/15 text-rose-400 text-xs rounded">
                                  {phase}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* 時間分布 - 圓餅圖顯示 */}
                  {(Object.keys(actualStats.hourDistribution).length > 0 || Object.keys(actualStats.dayOfWeekDistribution).length > 0) && (
                    <div className="mt-4 space-y-6">
                      {/* 小時分布圓餅圖 */}
                      {Object.keys(actualStats.hourDistribution).length > 0 && (
                        <div className="p-4 glass-panel rounded-xl">
                          <div className="text-lg font-medium text-slate-100 mb-4">小時分布 (Hour of Day)</div>
                          
                          {/* 圓餅圖 */}
                          <HourDistributionPieChart 
                            positiveData={actualStats.positiveHourDistribution}
                            negativeData={actualStats.negativeHourDistribution}
                          />
                          
                          {/* 詳細數據標籤 */}
                          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* 正例小時分布 */}
                            {Object.keys(actualStats.positiveHourDistribution).length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-emerald-400 mb-2">正例：</div>
                                <div className="flex flex-wrap gap-1">
                                  {Object.entries(actualStats.positiveHourDistribution)
                                    .sort(([a], [b]) => Number(a) - Number(b))
                                    .map(([hour, count]) => (
                                      <span key={`pos-hour-${hour}`} className="px-2 py-1 bg-emerald-400/15 text-emerald-400 text-xs rounded">
                                        {hour}:00 ({count})
                                      </span>
                                    ))}
                                </div>
                              </div>
                            )}
                            
                            {/* 反例小時分布 */}
                            {Object.keys(actualStats.negativeHourDistribution).length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-rose-400 mb-2">反例：</div>
                                <div className="flex flex-wrap gap-1">
                                  {Object.entries(actualStats.negativeHourDistribution)
                                    .sort(([a], [b]) => Number(a) - Number(b))
                                    .map(([hour, count]) => (
                                      <span key={`neg-hour-${hour}`} className="px-2 py-1 bg-rose-400/15 text-rose-400 text-xs rounded">
                                        {hour}:00 ({count})
                                      </span>
                                    ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                      
                      {/* 星期分布圓餅圖 */}
                      {Object.keys(actualStats.dayOfWeekDistribution).length > 0 && (
                        <div className="p-4 glass-panel rounded-xl">
                          <div className="text-lg font-medium text-slate-100 mb-4">星期分布 (Day of Week)</div>
                          
                          {/* 圓餅圖 */}
                          <DayOfWeekPieChart 
                            positiveData={actualStats.positiveDayOfWeekDistribution}
                            negativeData={actualStats.negativeDayOfWeekDistribution}
                          />
                          
                          {/* 詳細數據標籤 */}
                          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* 正例星期分布 */}
                            {Object.keys(actualStats.positiveDayOfWeekDistribution).length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-emerald-400 mb-2">正例：</div>
                                <div className="flex flex-wrap gap-1">
                                  {Object.entries(actualStats.positiveDayOfWeekDistribution)
                                    .sort(([a], [b]) => Number(a) - Number(b))
                                    .map(([day, count]) => {
                                      const dayNames = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
                                      const normalizedDay = Number(day) === 7 ? 0 : Number(day);
                                      return (
                                        <span key={`pos-day-${day}`} className="px-2 py-1 bg-emerald-400/15 text-emerald-400 text-xs rounded">
                                          {dayNames[normalizedDay] || `星期${day}`} ({count})
                                        </span>
                                      );
                                    })}
                                </div>
                              </div>
                            )}
                            
                            {/* 反例星期分布 */}
                            {Object.keys(actualStats.negativeDayOfWeekDistribution).length > 0 && (
                              <div>
                                <div className="text-sm font-medium text-rose-400 mb-2">反例：</div>
                                <div className="flex flex-wrap gap-1">
                                  {Object.entries(actualStats.negativeDayOfWeekDistribution)
                                    .sort(([a], [b]) => Number(a) - Number(b))
                                    .map(([day, count]) => {
                                      const dayNames = ['週日', '週一', '週二', '週三', '週四', '週五', '週六'];
                                      const normalizedDay = Number(day) === 7 ? 0 : Number(day);
                                      return (
                                        <span key={`neg-day-${day}`} className="px-2 py-1 bg-rose-400/15 text-rose-400 text-xs rounded">
                                          {dayNames[normalizedDay] || `星期${day}`} ({count})
                                        </span>
                                      );
                                    })}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ===== 新增：市場分類分布 - 圓餅圖顯示 ===== */}
                  {(Object.keys(actualStats.positiveMarketClassDistribution).length > 0 || Object.keys(actualStats.negativeMarketClassDistribution).length > 0) && (
                    <div className="mt-4 p-4 glass-panel rounded-xl">
                      <div className="text-lg font-medium text-slate-100 mb-4">市場分類分布</div>

                      {/* 圓餅圖 */}
                      <MarketClassPieChart
                        positiveData={actualStats.positiveMarketClassDistribution}
                        negativeData={actualStats.negativeMarketClassDistribution}
                      />

                      {/* 詳細數據標籤 */}
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* 正例市場分類分布 */}
                        {Object.keys(actualStats.positiveMarketClassDistribution).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-emerald-400 mb-2">正例市場分類：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.positiveMarketClassDistribution).map(([marketClass, count]) => (
                                <span key={`pos-market-${marketClass}`} className="px-2 py-1 bg-emerald-400/15 text-emerald-400 text-xs rounded">
                                  {marketClass}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 反例市場分類分布 */}
                        {Object.keys(actualStats.negativeMarketClassDistribution).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-rose-400 mb-2">反例市場分類：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.negativeMarketClassDistribution).map(([marketClass, count]) => (
                                <span key={`neg-market-${marketClass}`} className="px-2 py-1 bg-rose-400/15 text-rose-400 text-xs rounded">
                                  {marketClass}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* ===== 新增：難度分布 - 圓餅圖顯示 ===== */}
                  {(Object.keys(actualStats.positiveDifficultyDistribution).length > 0 || Object.keys(actualStats.negativeDifficultyDistribution).length > 0) && (
                    <div className="mt-4 p-4 glass-panel rounded-xl">
                      <div className="text-lg font-medium text-slate-100 mb-4">難度分布</div>

                      {/* 圓餅圖 */}
                      <DifficultyPieChart
                        positiveData={actualStats.positiveDifficultyDistribution}
                        negativeData={actualStats.negativeDifficultyDistribution}
                      />

                      {/* 詳細數據標籤 */}
                      <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* 正例難度分布 */}
                        {Object.keys(actualStats.positiveDifficultyDistribution).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-emerald-400 mb-2">正例難度：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.positiveDifficultyDistribution).map(([difficulty, count]) => (
                                <span key={`pos-difficulty-${difficulty}`} className="px-2 py-1 bg-emerald-400/15 text-emerald-400 text-xs rounded">
                                  {difficulty}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* 反例難度分布 */}
                        {Object.keys(actualStats.negativeDifficultyDistribution).length > 0 && (
                          <div>
                            <div className="text-sm font-medium text-rose-400 mb-2">反例難度：</div>
                            <div className="flex flex-wrap gap-2">
                              {Object.entries(actualStats.negativeDifficultyDistribution).map(([difficulty, count]) => (
                                <span key={`neg-difficulty-${difficulty}`} className="px-2 py-1 bg-rose-400/15 text-rose-400 text-xs rounded">
                                  {difficulty}: {count}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </>
              );
            })()}

            {/* GAP-3 UX Task 2.1／2.3：匯出前篩選面板＋即時筆數 */}
            <div className="mt-6 glass-panel rounded-xl p-4 border border-slate-800/80" data-testid="export-declaration-panel">
              <h4 className="font-bold text-slate-100">匯出設定</h4>
              <p className="mt-1 text-[11px] text-slate-400">
                匯出的是搜尋結果的<strong className="text-slate-200">全部</strong>列；正例／反例請在 Excel 裡用 CSV 自己篩、
                改好 <code>label</code> 後再回灌匯入。匯出前只需要你填一件事：答案窗。
              </p>

              {/* 三個數字之唯一計數來源（Task 1.5 同一函式） */}
              <p className="mt-3 text-sm text-slate-200" data-testid="export-counts">
                原 <strong data-testid="export-count-m">{exportCounts.M}</strong> 筆／
                你聲明的正例 <strong data-testid="export-count-x">{exportCounts.X}</strong>／
                反例 <strong data-testid="export-count-y">{exportCounts.Y}</strong>
                {exportCounts.droppedUnreadableLabel > 0 && (
                  <span className="text-amber-200" data-testid="export-count-unreadable">
                    （另有 {exportCounts.droppedUnreadableLabel} 筆沒有正反例標記——
                    事件 JSON 不收它們，<strong data-testid="export-count-csv">CSV 仍會含
                    {exportCounts.M} 筆</strong>，因為 CSV 是原始結果、不該因少一個旗標就丟整列）
                  </span>
                )}
              </p>

              {/* ── Task 1.9′：答案窗宣告框（與匯入頁**同一元件**、同一 validator） ───────── */}
              <div className="mt-4" data-testid="export-declaration">
                <p className="mb-2 text-xs text-amber-200/90">
                  請填<strong>正例與反例兩邊判定所用之最遠者</strong>（t₀ 之後第幾根；未用任何未來資訊請明填 0，留白不算 0）。
                  這個值會寫進匯出檔的 lookahead_bars_declared，並決定 train/test 的隔離寬度；
                  <strong>系統無法驗證此深度，錯報將導致資料洩漏</strong>。
                </p>
                {declPreview ? (
                  <LookaheadDeclarationFields
                    preview={declPreview}
                    declared={declared}
                    acknowledged={declAcknowledged}
                    problems={validateDeclaration(declared, declAcknowledged, declPreview).problems}
                    onChangeWindow={(tf, value) => {
                      declTouchedRef.current.add(tf);          // 使用者親手動過 ⇒ 之後預設改變不覆寫
                      setDeclared((prev) => {
                        const next = { ...prev };
                        // 留白（NaN）＝尚未填寫，不寫成 0（0 須明填）
                        if (Number.isNaN(value)) delete next[tf]; else next[tf] = value;
                        return next;
                      });
                    }}
                    onChangeAcknowledged={setDeclAcknowledged}
                  />
                ) : declPreviewError ? (
                  <p className="text-[11px] text-rose-200" data-testid="export-declaration-error">
                    無法取得答案窗預填資料：{declPreviewError}（取得前不會讓你匯出）
                  </p>
                ) : exportTimeframes.length === 0 ? (
                  <p className="text-[11px] text-rose-200" data-testid="export-declaration-error">
                    這批結果讀不到 K 線週期，無法宣告答案窗（不會讓你匯出）
                  </p>
                ) : (
                  <p className="text-[11px] text-slate-300" data-testid="export-declaration-pending">
                    正在取得答案窗預填資料；取得前不會讓你匯出。
                  </p>
                )}
              </div>

              {/* ── GAP-3 UX Task 4.1 ①：附帶報酬欄多選（預設全選 1..12） ───────────── */}
              <div className="mt-4 rounded border border-slate-800 bg-slate-900/40 p-3" data-testid="export-attached-columns">
                <p className="text-sm text-slate-200">
                  附帶報酬欄（純供 Excel 分析攜帶）
                  <span className="ml-2 text-[11px] text-slate-400">
                    勾選的每個 h 會在匯出檔加一欄 future_{'{h}'}bar_return
                  </span>
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {ATTACHED_HORIZONS.map((h) => (
                    <label key={h} className="flex items-center gap-1 text-xs text-slate-300">
                      <input
                        type="checkbox"
                        data-testid={`export-attached-h${h}`}
                        checked={attachedHorizons.includes(h)}
                        onChange={(e) => setAttachedHorizons((prev) => (e.target.checked
                          ? [...new Set([...prev, h])].sort((a, b) => a - b)
                          : prev.filter((v) => v !== h)))}
                      />
                      {h}
                    </label>
                  ))}
                </div>
              </div>

              {/* ── GAP-3 UX Task 7.1：五個批次維度**可見可改** ─────────────────────
                  🔴 可操作集合由 `selectable(path, dim)` 導出（契約 ∖ 具名排除常數），
                     本頁不知道任何值域；`/search` 之限制**只在此路徑**成立。 */}
              <div className="mt-4 rounded border border-slate-800 bg-slate-900/40 p-3" data-testid="export-event-dimensions">
                <p className="mb-2 text-sm text-slate-200">
                  這批事件的五個設定
                  <span className="ml-2 text-[11px] text-slate-400">
                    預設維持現行；灰掉的值旁邊寫了為什麼這條路徑不開放
                  </span>
                </p>
                <EventDimensionFields path="/search" values={eventDims} onChange={setEventDims} />
              </div>

              {/* ── GAP-3 UX Task 7.3：動態揭露本批設定（**取代** Task 4.1b 之獨立實作）─────
                  🔴 每一段都由 **Task 7.6 之欄位級 formatter registry** 產生，本頁只**選取自己的欄集**
                     （`SEARCH_DISCLOSURE_FIELDS`）；不得寫成硬編欄集之面板級 formatter
                     ——IC 分析頁欄集不同，面板級共用會逼其中一頁多顯示或少顯示。
                  🔴 值一律取自**使用者實際選的** `eventDims`／實際回傳之深度 map，禁寫死。
                  🔴 4.1b 之四項（scenario／深度／purge／control_kind）為本欄集之真子集，
                     其 testid 一併保留 ⇒ `eventExportDisclosureLegacy.test.tsx` 仍是「4.1b ⊆ 7.3」之執行期證明。 */}
              <div className="mt-3 rounded border border-sky-900/60 bg-sky-950/30 p-3 text-[11px] text-slate-300" data-testid="export-disclosure">
                <p className="text-xs font-medium text-sky-100">這批匯出實際會帶什麼（你沒選過但一直存在的設定）</p>
                {/* 🔴 R3 群集 B：**真的**由 `SEARCH_DISCLOSURE_FIELDS` 迭代產生。
                    原本是逐欄手寫七段、連 import 都沒有 ⇒ 往常數加欄不會改變任何 DOM，
                    而註解卻宣稱「本頁只選取自己的欄集」——那就是 7.3 要滅的第二份欄集。 */}
                {SEARCH_DISCLOSURE_FIELDS.flatMap((field) => searchDisclosureLines(field, {
                  dims: eventDims,
                  // 🔴 Task 1.9′ 覆蓋風險：深度自本頁之**宣告 state** 讀取（只揭露已填之 tf；未填＝尚未宣告）
                  depthByTimeframe: Object.fromEntries(
                    exportTimeframes.filter((tf) => Number.isInteger(declared[tf])).map((tf) => [tf, declared[tf]]),
                  ),
                })).map((line) => (
                  <p className="mt-1" key={line.testid} data-testid={line.testid}>{line.text}</p>
                ))}
              </div>

              {/* ── GAP-3 UX Task 7.4（＝ 4.1c 之同一文案來源）：條件 IC decay 之邊界揭露 ─── */}
              <p className="mt-2 text-[11px] text-amber-200/90" data-testid="export-no-ic-decay">
                {EVENT_IC_DECAY_DISCLOSURE}
              </p>
            </div>

            {/* CSV 導出按鈕 */}
            <div className="mt-6 flex justify-center">
              <button
                // 🔴 `void` 會把 `proceed` 內拋出的錯整個吞掉 ⇒ 使用者按了什麼都沒發生
                //    （B5 `CODEX-R2-P1-01` 已為 JSON 鈕修過同一條，本鈕改 async 後同樣適用）
                onClick={() => {
                  exportSearchResultsToCSV().catch((err: unknown) => {
                    alert(`匯出失敗：${err instanceof Error ? err.message : String(err)}`);
                  });
                }}
                // 🔴 D3.1：兩段式之阻擋 ⇒ 按鈕 disabled（理由顯示在下方）。
                //    判定來自 `twoStageExportBlockReason`，此處不另寫條件。
                disabled={exportBlock !== undefined}
                data-testid="export-contract-csv"
                className="flex items-center gap-2 px-6 py-3 bg-emerald-500 text-white rounded-lg font-medium hover:bg-emerald-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="匯出可直接回灌的 CSV：欄名就是契約欄名，你在 Excel 改完 label 就能直接上傳"
              >
                <Download className="w-5 h-5" />
                導出CSV檔案（可回灌）
              </button>
              <button
                // 🔴 R2 `CODEX-R2-P1-01`：`void` 會把 `proceed` 內拋出的錯**整個吞掉**
                //    ⇒ 使用者按了什麼都沒發生。任何未預期之錯都要看得見。
                onClick={() => {
                  exportSearchResultsToEventJson().catch((err: unknown) => {
                    alert(`匯出失敗：${err instanceof Error ? err.message : String(err)}`);
                  });
                }}
                disabled={exportBlock !== undefined}
                data-testid="export-gap3-events"
                className="ml-3 flex items-center gap-2 px-6 py-3 bg-sky-500/20 text-sky-100 border border-sky-400/40 rounded-lg font-medium hover:bg-sky-500/30 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="匯出事件契約 JSON＋來源檔（可手改後到「數據準備」匯入）"
              >
                <Download className="w-5 h-5" />
                匯出事件契約 JSON
              </button>
              {/* 🔴 `G3-D2` D3.1：兩段式之阻擋理由。**只顯示、不判斷**（判斷在
                  `twoStageExportBlockReason`），代號一併顯示以便對照契約／訊息。 */}
              {exportBlock && (
                <p className="mt-2 w-full text-xs text-amber-300" data-testid="export-blocked-reason">
                  {exportBlock.message}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
