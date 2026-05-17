'use client';

import React, { useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Search, X, Info, ChevronDown, ChevronUp } from 'lucide-react';
import { useFeatureFactoryStore } from '@/store/featureFactoryStore';
import { FeaturePreview, FeatureSchema, SchemaIndicator } from '@/lib/types';
import CategorySection from './CategorySection';

// ─── Instant Tooltip（Portal 版，脫離父層 stacking context） ────
function ItemTooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);
  if (!text) return <>{children}</>;

  const tooltipEl = tip
    ? createPortal(
        <div
          className="fixed z-[9999] w-60 rounded-lg border border-white/15 bg-slate-900 px-2.5 py-2 text-[10px] text-slate-200 leading-relaxed shadow-xl pointer-events-none whitespace-pre-wrap"
          style={{
            left: Math.min(tip.x + 14, window.innerWidth - 256),
            top: Math.min(tip.y + 16, window.innerHeight - 160),
          }}
        >
          {text}
        </div>,
        document.body
      )
    : null;

  return (
    <span
      className="block min-w-0"
      onMouseEnter={(e) => setTip({ x: e.clientX, y: e.clientY })}
      onMouseMove={(e) => setTip({ x: e.clientX, y: e.clientY })}
      onMouseLeave={() => setTip(null)}
    >
      {children}
      {tooltipEl}
    </span>
  );
}

type LayerKey = 'layer1' | 'layer2' | 'layer3' | 'layer4' | 'layer5' | 'layer6' | 'layer6_5';

const LAYER_TABS: { key: LayerKey; label: string; shortLabel: string; desc: string }[] = [
  { key: 'layer1', label: 'Layer 1', shortLabel: 'L1', desc: '原始技術指標（TA-Lib）' },
  { key: 'layer2', label: 'Layer 2', shortLabel: 'L2', desc: '衍生運算元' },
  { key: 'layer3', label: 'Layer 3', shortLabel: 'L3', desc: '滾動統計聚合' },
  { key: 'layer4', label: 'Layer 4', shortLabel: 'L4', desc: '時間滯後特徵' },
  { key: 'layer5', label: 'Layer 5', shortLabel: 'L5', desc: '截面標準化' },
  { key: 'layer6', label: 'Layer 6', shortLabel: 'L6', desc: '高階複合信號' },
  { key: 'layer6_5', label: 'Layer 6.5', shortLabel: '6.5', desc: '特徵預處理' },
];

// ─── Layer 說明筆記（在 UI 中點擊 ⓘ 按鈕可展開） ────────────────
interface LayerNote {
  summary: string;
  sections: { title: string; content: string }[];
}

const LAYER_NOTES: Partial<Record<LayerKey, LayerNote>> = {
  layer1: {
    summary: 'TA-Lib 原始技術指標，是整個 Feature Factory 的資料來源基礎。',
    sections: [
      {
        title: '計算原理',
        content: '直接呼叫 TA-Lib 函式庫對 OHLCV 計算出指標序列。每個指標會依 scan_config.yaml 設定的參數（週期、組合）展開為多欄，例如 EMA_8、EMA_21、EMA_34 各為獨立欄位。',
      },
      {
        title: '六大類別',
        content: '趨勢（EMA/SMA/BBANDS…）、動量（RSI/MACD/ADX/CCI/STOCH…）、波動率（ATR/NATR/Parkinson…）、量能（OBV/VWAP/Volume_MA_Ratio…）、週期（HT_*）、型態（蠟燭型態 CDL*）。',
      },
      {
        title: '使用建議',
        content: '第一次探索建議全開，產出完整特徵後用 IC Analysis 篩選出真正有預測力的子集，再回來關掉貢獻低的指標以減少計算量。',
      },
    ],
  },
  layer2: {
    summary: '對 L1 指標做二次運算（距離/交叉/動量/比率/二元信號/WQ Alpha 運算元），將連續指標轉換為更具語義的特徵。',
    sections: [
      {
        title: 'distance（乖離率）',
        content: '公式：(close − indicator) / indicator。衡量價格相對均線的偏離幅度，適用 trend 類指標（EMA/SMA）。振盪類指標（MACD/RSI）不適用。',
      },
      {
        title: 'cross（快慢線差值）',
        content: '公式：快線 − 慢線。同一指標不同週期的兩兩配對差值，例如 EMA_12 − EMA_26（即 MACD 的概念延伸）。',
      },
      {
        title: 'worldquant 運算元',
        content: '⚠ sign/clip 只對值域有正負的指標有意義（如 MACD、CCI）。EMA/RSI 永遠為正，sign 後全為 +1（常數），Layer 7 會自動移除常數欄。',
      },
    ],
  },
  layer3: {
    summary: '對 L1/L2 特徵做滾動視窗統計聚合（mean/std/slope/rank/zscore/skew/kurt/min/max），放大時序模式。',
    sections: [
      {
        title: '視窗設定',
        content: '視窗大小在 scan_config.yaml 的 rolling_aggregation.windows 設定（預設 Fibonacci 數列）。視窗愈大，特徵愈平滑但滯後愈長。',
      },
      {
        title: '重要性',
        content: 'rank（百分位排名）和 zscore 是 IC 評分最高的兩個 aggregator，因為它們能消除絕對值尺度差異，讓不同指標可比較。slope 能捕捉趨勢加速/減速，也常有高 IC。',
      },
      {
        title: '計算量',
        content: 'L3 的特徵數量 = L1特徵數 × aggregator數 × window數，是整個 Factory 計算量最大的層。建議先用 IC 篩選 aggregator 優先順序，再決定開多少視窗。',
      },
    ],
  },
  layer4: {
    summary: '將 L1~L3 特徵向後移位（Lag），讓模型可以「看到過去的過去」。',
    sections: [
      {
        title: '參數設定',
        content: 'Lag 數量由 global_settings.sequence_length（序列長度）和 global_settings.max_lag_ratio（最大滯後比例）共同決定。實際 lag 列表 = Fibonacci 數列中 ≤ sequence_length × max_lag_ratio 的值。',
      },
      {
        title: '適用場景',
        content: '對動量類指標（RSI、MACD）做 lag 可捕捉「動量反轉」（T-5 的 RSI vs T-0 的 RSI）。對趨勢類指標做 lag 則捕捉「趨勢延伸」。',
      },
    ],
  },
  layer5: {
    summary: '跨標的截面特徵：以參考標的（預設 BTCUSDT）為基準，計算相對價格、Beta 係數、特異動量。',
    sections: [
      {
        title: '三大特徵',
        content: 'cs_relative_price = 標的收盤 / BTC收盤（相對比價）\ncs_beta = rolling_cov(R_標的, R_BTC) / rolling_var(R_BTC)（系統性風險暴露）\ncs_idiosyncratic_momentum = R_標的 − β × R_BTC（去除市場影響後的自身動量）',
      },
      {
        title: '為何 BTCUSDT 自身沒有 L5',
        content: '當 reference_symbol == symbol 時，cs_relative_price = 1（常數）、cs_beta = 1（常數），Layer 7 自動移除，等同跳過。',
      },
      {
        title: '基準標的',
        content: '可在下方「基準標的」欄位直接輸入變更（如 ETHUSDT、SOLUSDT）。不需修改 YAML 設定檔。',
      },
    ],
  },
  layer6: {
    summary: 'Meta Features（元特徵）：不從原始 K 線生成，而是整合 L1 指標輸出，提取更高維度的市場狀態訊號。',
    sections: [
      {
        title: '與 IC 篩選的關係',
        content: '⚠ 建議工作流程：第一次全開 L1~L6 → 執行 IC Analysis / SHAP 評估各 sub-engine 的貢獻 → 若某 sub-engine 所有特徵 IC 皆低 → 在 config 關閉以節省計算資源。Layer 6 計算成本低，不需要「先用 IC 決定再開」。',
      },
      {
        title: 'trend_consensus（趨勢共識）',
        content: '公式：mean(sign(EMA8>EMA21), sign(MACD_Hist), ADX>25)。三個指標方向一致 → +1；全反向 → -1。⚠ 依賴 L1 必須啟用 EMA + MACD + ADX。',
      },
      {
        title: 'momentum_divergence（動量發散度）',
        content: '公式：std(rank_pct(RSI), rank_pct(CCI), rank_pct(STOCH))。三者方向一致 → 接近 0；方向分歧 → 接近 0.5。⚠ 依賴 L1 啟用 RSI + CCI + STOCH。',
      },
      {
        title: 'volume_price_divergence（量價背離）',
        content: '公式：1 if sign(ΔPrice) ≠ sign(ΔVolume)，else 0。量縮價漲或量增價跌 → 1（潛在反轉）；量價同向 → 0。',
      },
      {
        title: 'volatility_regime（波動率狀態）',
        content: '公式：ATR_14 / ATR_55。> 1 代表近期波動高於長期均值（高風險期）；< 1 代表近期波動收斂（盤整期）。⚠ 依賴 L1 啟用 ATR。',
      },
      {
        title: 'interaction（交互特徵）',
        content: '三種乘積：①EMA趨勢強度 × RSI動量強度 ②ATR × 價格方向信號 ③成交量變化率 × 價格變化率。硬編碼使用 EMA_8/21、RSI_14、ATR_14。',
      },
      {
        title: 'time_features（時間特徵）',
        content: '輸出：HourOfDay / DayOfWeek / IsWeekend / MonthOfYear。\n12h 時框：K 線開盤時間固定為 UTC 0:00 和 12:00，HourOfDay 只有 {0, 12} 兩個值（正常行為），IC 接近 0，IC Analysis 後會自動淘汰。DayOfWeek / IsWeekend / MonthOfYear 均正常輸出。',
      },
      {
        title: '未來待實作',
        content: '① 特徵相關係數去冗餘（Pearson > 0.85 同群只留 IC 最高者）\n② Mutual Information 排序（非線性版 IC）\n③ 多重比較校正（Bonferroni，測試 N 個特徵時顯著性門檻 = 0.05/N）\n④ 動態候選指標（由 config 注入 _find_column 的候選清單，無需改程式碼）',
      },
    ],
  },
  layer6_5: {
    summary: '特徵預處理管線：在送入 ML 模型前對所有 L1~L6 特徵做標準化、去極值、穩態化。',
    sections: [
      {
        title: '處理順序',
        content: 'Winsorization（極值截斷）→ Rank Transform（百分位轉換）→ ZScore / Gaussian 正規化 → ADF 差分穩態化 → FracDiff（分數階差分）',
      },
      {
        title: 'Winsorization（占比 ~51% 計算時間）',
        content: '將超過 [1%, 99%] 分位數的值截斷至邊界。防止離群值主導梯度，是最重要的預處理步驟。',
      },
      {
        title: 'Rank Transform（占比 ~39% 計算時間）',
        content: '非參數化轉換，完全消除分佈假設。輸出 [0,1] 百分位排名，對任意分佈（正態/偏態/重尾）均有效。',
      },
    ],
  },
};

// ─── Layer 說明展開區塊 ────────────────────────────────────────
function LayerNotePanel({ layerKey }: { layerKey: LayerKey }) {
  const [open, setOpen] = useState(false);
  const note = LAYER_NOTES[layerKey];
  if (!note) return null;

  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 text-[10px] text-slate-400 hover:text-cyan-300 transition"
      >
        <Info size={11} />
        <span>{open ? '收起說明' : '查看此 Layer 說明與注意事項'}</span>
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>
      {open && (
        <div className="mt-1.5 rounded-lg border border-cyan-400/20 bg-cyan-400/5 p-3 space-y-2.5">
          <p className="text-[11px] text-cyan-100 leading-relaxed">{note.summary}</p>
          {note.sections.map((sec) => (
            <div key={sec.title}>
              <div className="text-[10px] font-semibold text-cyan-300/80 mb-0.5">{sec.title}</div>
              <p className="text-[10px] text-slate-300 leading-relaxed whitespace-pre-line">{sec.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** 各 Layer 項目的豐富描述：short=顯示文字，detail=計算方法說明（用於 tooltip） */
const RICH_DESCRIPTIONS: Record<string, Record<string, { short: string; detail: string }>> = {
  layer2: {
    distance: {
      short: '價格與指標相對乖離',
      detail: '公式：(數據源 − 指標) / 指標\n衡量指標偏離其計算基礎（如收盤價）的相對距離。\n例：(close − EMA26) / EMA26 反映價格偏離均線的幅度。\n\n套用範圍：trend 類指標（EMA、SMA、DEMA…）\n「振盪類」指標（MACD、RSI、CCI…）不適用，因其本身已是衍生值。',
    },
    cross: {
      short: '快慢線交叉差值',
      detail: '公式：快線 − 慢線\n將同一指標的不同期數兩兩配對，輸出差值序列，而非 0/1 事件信號。\n例：EMA_12 − EMA_26（即 MACD 線的概念延伸）。\n\n套用範圍：有「多組期數參數」的指標，如 EMA(12/26)、SMA(5/20)。\n單一期數指標（如 ATR、MACD 本身）無法配對，不會展開此欄。',
    },
    momentum: {
      short: '指標自身變化率',
      detail: '公式：(x(t) − x(t−N)) / x(t−N)\nN 由 config.lags 決定（預設 [3, 5, 8] 期）。\n正值 = 近期上漲加速，負值 = 近期下跌加速。\n\n套用範圍：所有 L1 指標（apply_to: all）。',
    },
    ratio: {
      short: '快慢線數值比率',
      detail: '公式：快線 / 慢線\n與 cross 相同的配對邏輯，但輸出比率而非差值，可消除量綱。\n例：EMA_12 / EMA_26 接近 1 代表快慢線收斂。\n\n套用範圍：有「多組期數參數」的指標（同 cross）。',
    },
    binary_signal: {
      short: '閾值二元信號',
      detail: '依 config 中的規則將連續指標轉為 0/1 信號。\n預設規則（可自訂）：\n  RSI > 70 → 超買 (Overbought)\n  RSI < 30 → 超賣 (Oversold)\n  ADX > 25 → 強趨勢 (Strong_Trend)\n  CCI > 100 → 超買 | CCI < -100 → 超賣\n  MFI > 80 → 超買 | MFI < 20 → 超賣\n\n✎ 自訂方式：編輯 config/scan_config.yaml\n  operators.binary_signal.rules:\n    - indicator: RSI      # 要套用的指標名稱\n      condition: "> 80"   # 觸發條件（支援 >, <, >=, <=, ==）\n      name_suffix: "ExtremBuy"  # 輸出欄位後綴\n\n套用範圍：config 中明確列出規則的指標。',
    },
    worldquant: {
      short: 'WQ Alpha 運算元',
      detail: '集成 WorldQuant 101 Alpha 公式框架，共 2 大類：\n\n【時序滾動運算元】（窗口：5/13/21 期）\n・ts_argmax  — 滾動窗口內最大值的相對位置（0-based）\n・ts_argmin  — 滾動窗口內最小值的相對位置\n・ts_rank    — 當前值在窗口內的百分位排名 [0,1]\n・decay_linear — 線性衰減加權均值，近期比重大\n・ts_corr    — 與參考序列的滾動相關係數（需設 corr_with）\n\n【靜態變換（不含窗口）】\n・sign   — 符號：+1 / -1 / 0\n  ⚠ 需指標可為負值（EMA/RSI 永正 → 全 +1 → 常數 → 自動移除）\n  ✓ 適用：MACD、CCI、OBV 變化量等\n・log1p  — 保號對數 sign(x)×log(1+|x|)，壓縮量級\n・abs    — 絕對值，只保留強度\n・clip   — 截斷至 [−3, 3]\n  ⚠ 需指標值本身接近 0 為中心\n  ✓ 適用：zscore 類特徵；EMA(2000+) 截斷後 = 3 → 常數 → 自動移除\n\n常數欄位（std=0）在 Layer 7 驗證時自動移除，不算 bug。',
    },
  },
  layer3: {
    slope: {
      short: '趨勢斜率',
      detail: '對滾動視窗做線性回歸，輸出斜率 β₁。\nβ₁ > 0 代表上升趨勢，數值愈大斜率愈陡峭。',
    },
    std: {
      short: '波動幅度',
      detail: '計算滾動視窗的樣本標準差 σ = √(Σ(x−μ)²/(n−1))。\n數值愈大，指標在視窗內波動愈劇烈。',
    },
    mean: {
      short: '平均水平',
      detail: '計算滾動視窗的算術平均值 μ = ΣX / n。\n代表中心趨勢，可作為多項衍生指標的基準線。',
    },
    rank: {
      short: '百分位排名',
      detail: '計算當前值在滾動視窗內的百分位排名，範圍 [0, 1]。\n0 = 歷史最低，1 = 歷史最高，0.5 = 中位數水準。',
    },
    zscore: {
      short: '標準化偏離',
      detail: '標準化分數 Z = (x − μ) / σ。\nZ=2 代表當前值高於均值 2 個標準差，可識別異常值。',
    },
    skew: {
      short: '分佈偏態',
      detail: '計算三階標準化矩，衡量分佈不對稱性。\n> 0 為右偏（右尾長），< 0 為左偏（左尾長）。',
    },
    kurt: {
      short: '峰態厚尾',
      detail: '計算四階標準化矩，衡量極端值頻率。\n> 3 為尖峰厚尾（黑天鵝風險高）；< 3 為平坦薄尾。',
    },
    min: {
      short: '滾動最小值',
      detail: '滾動視窗內的最低值。\n可用於識別支撐位，或作為 Donchian Channel 的下軌。',
    },
    max: {
      short: '滾動最大值',
      detail: '滾動視窗內的最高值。\n可用於識別壓力位，或作為 Donchian Channel 的上軌。',
    },
    range: {
      short: '振幅極差',
      detail: '極差 = max − min，衡量視窗內的總振幅。\n類似 ATR，但基於任意指標序列而非價格本身。',
    },
  },
  layer5: {
    relative_price: {
      short: '相對價格',
      detail: '當前標的價格相對參考標的（如 BTC）的比值或差值。\n反映標的的相對強弱與獨立走勢。',
    },
    beta: {
      short: 'Beta 係數',
      detail: '計算標的收益率對參考標的的滾動回歸係數 β。\nβ > 1 表示放大市場波動；β < 1 表示低於市場波動。',
    },
    idiosyncratic_momentum: {
      short: '特異動量',
      detail: '去除市場（BTC）共同動量後的殘差動量。\n衡量標的自身的超額動量，是多空選股的核心因子。',
    },
    cs_rank: {
      short: '截面排名',
      detail: '在所有標的中計算當前指標的截面百分位排名。\n消除跨標的量綱差異，適合多標的輪動策略。',
    },
    cs_zscore: {
      short: '截面標準化',
      detail: '跨標的截面 Z-Score：(x − μ_cross) / σ_cross。\n識別相對強度偏離程度，正值代表相對強勢。',
    },
    cs_momentum: {
      short: '截面動量排名',
      detail: '在標的組合中計算動量的截面百分位排名。\n動量輪動策略的核心：持有高截面動量標的。',
    },
  },
  layer6: {
    consensus: {
      short: '多指標共識',
      detail: '統計多個技術指標的看漲/看跌信號比例，輸出 [−1, 1] 的共識分數。\n> 0.5 代表多數指標看漲。',
    },
    interaction: {
      short: '特徵交互',
      detail: '對選定特徵兩兩計算乘積 f₁ × f₂。\n捕捉單一特徵無法表達的聯合非線性效果。',
    },
    time_features: {
      short: '時間週期特徵',
      detail: '提取 hour_sin/cos（日內週期）、day_of_week_sin/cos（週次週期）。\n使模型感知時間規律性，提升跨時段泛化能力。',
    },
    trend_consensus: {
      short: '趨勢一致性',
      detail: '評估多期 EMA/SMA 陣列的多頭排列程度（短期 > 中期 > 長期）。\n輸出 [0, 1] 分數，1 = 完美多頭排列。',
    },
    momentum_divergence: {
      short: '動量背離',
      detail: '比對 RSI/MACD 走勢與價格方向的差異。\n頂背離（價新高但指標不創高）暗示趨勢可能反轉。',
    },
    volume_price_divergence: {
      short: '量價背離',
      detail: '比較量能與價格變動方向的一致性。\n量增價跌（潛在積累）或量縮價漲（上漲無力）= 背離信號。',
    },
    volatility_regime: {
      short: '波動率區間',
      detail: '使用滾動標準差或 HMM 模型識別目前市場狀態。\n輸出：低波動（趨勢市）/ 中波動 / 高波動（震盪市）。',
    },
  },
  layer6_5: {
    winsorization: {
      short: '極值截斷',
      detail: '將超過上下分位數（預設 [1%, 99%]）的極端值截斷至邊界。\n防止離群值主導模型訓練，穩定特徵分佈。',
    },
    rank_transform: {
      short: '百分位轉換',
      detail: '將特徵值映射至截面 [0, 1] 百分位排名。\n非參數化轉換，完全消除分佈假設，對任意分佈有效。',
    },
    adaptive_zscore: {
      short: '自適應標準化',
      detail: '以滾動視窗的均值和標準差進行 Z-Score 標準化。\n自動適應時序分佈漂移，比全局 Z-Score 更穩健。',
    },
    gaussian_normalize: {
      short: '高斯化轉換',
      detail: '使用 QuantileTransformer 將任意分佈特徵轉換為標準高斯分佈。\n適合假設常態的線性模型（如 Lasso、Ridge）。',
    },
    adf_differencing: {
      short: 'ADF 差分穩態化',
      detail: 'ADF 單根檢定後，若序列非穩態則做一階差分：Δx(t) = x(t) − x(t−1)。\n確保序列統計特性穩定，避免偽回歸問題。',
    },
    fractional_differencing: {
      short: '分數階差分',
      detail: '以 0 < d < 1 的分數階微分（FracDiff），兼顧保留長期記憶性與達到弱穩態。\n介於原始序列（d=0）和一階差分（d=1）之間。',
    },
  },
};

interface LayerPanelProps {
  schema: FeatureSchema | null;
}

export default function LayerPanel({ schema }: LayerPanelProps) {
  const [activeLayer, setActiveLayer] = useState<LayerKey>('layer1');

  const {
    config,
    preview,
    indicatorSearch,
    setIndicatorSearch,
    toggleIndicator,
    toggleAllInCategory,
    toggleCategory,
    toggleAggregator,
    toggleAllAggregators,
    toggleMetaSubEngine,
    toggleCrossFeature,
    toggleOperator,
    updateConfigPartial,
  } = useFeatureFactoryStore();

  // Layer 1 toggle
  const handleLayerToggle = useCallback(
    (layerKey: LayerKey, enabled: boolean) => {
      switch (layerKey) {
        case 'layer2':
          updateConfigPartial({ operators: { ...(config?.operators ?? {}), enabled } });
          break;
        case 'layer3':
          updateConfigPartial({ rolling_aggregation: { ...(config?.rolling_aggregation ?? {}), enabled } });
          break;
        case 'layer4':
          updateConfigPartial({ lag_features: { ...(config?.lag_features ?? {}), enabled } });
          break;
        case 'layer5':
          updateConfigPartial({ cross_sectional: { ...(config?.cross_sectional ?? {}), enabled } });
          break;
        case 'layer6':
          updateConfigPartial({ meta_features: { ...(config?.meta_features ?? {}), enabled } });
          break;
        case 'layer6_5':
          updateConfigPartial({ preprocessing: { ...(config?.preprocessing ?? {}), enabled } });
          break;
        default:
          break;
      }
    },
    [config, updateConfigPartial]
  );

  const isLayerEnabled = useCallback(
    (layerKey: LayerKey): boolean => {
      if (!schema) return true;
      const layer = schema.layers[layerKey];
      if (!layer) return true;
      if (layerKey === 'layer2') return (config?.operators?.enabled as boolean | undefined) !== false;
      if (layerKey === 'layer3') return config?.rolling_aggregation?.enabled !== false;
      if (layerKey === 'layer4') return config?.lag_features?.enabled !== false;
      if (layerKey === 'layer5') return config?.cross_sectional?.enabled === true;
      if (layerKey === 'layer6') return config?.meta_features?.enabled !== false;
      if (layerKey === 'layer6_5') return config?.preprocessing?.enabled === true;
      return layer.enabled;
    },
    [schema, config]
  );

  if (!schema) {
    return (
      <div className="glass-panel rounded-2xl p-6">
        <div className="text-sm text-slate-400">載入 Schema 中...</div>
      </div>
    );
  }

  return (
      <div className="px-4 pb-4 space-y-4">
      {/* Search bar (C6) */}
      <div className="relative">
        <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={indicatorSearch}
          onChange={(e) => setIndicatorSearch(e.target.value)}
          placeholder="搜尋指標名稱..."
          className="w-full rounded-lg border border-white/10 bg-white/5 pl-8 pr-8 py-1.5 text-xs text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-300/40"
        />
        {indicatorSearch && (
          <button
            type="button"
            onClick={() => setIndicatorSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Tab navigation */}
      <div className="flex flex-wrap gap-1">
        {LAYER_TABS.map((tab) => {
          const layerEnabled = isLayerEnabled(tab.key);
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveLayer(tab.key)}
              title={tab.desc}
              className={`rounded-md px-2.5 py-1 text-[11px] transition border ${
                activeLayer === tab.key
                  ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                  : 'bg-white/5 text-slate-400 border-white/10 hover:border-cyan-300/30'
              } ${!layerEnabled ? 'opacity-50' : ''}`}
            >
              {tab.shortLabel}
            </button>
          );
        })}
      </div>

      {/* Layer content */}
      <LayerContent
        schema={schema}
        config={config}
        layerKey={activeLayer}
        layerEnabled={isLayerEnabled(activeLayer)}
        searchFilter={indicatorSearch}
        preview={preview}
        onLayerToggle={(enabled) => handleLayerToggle(activeLayer, enabled)}
        onCategoryToggle={toggleCategory}
        onItemToggle={toggleIndicator}
        onSelectAll={toggleAllInCategory}
        onAggregatorToggle={toggleAggregator}
        onAllAggregatorsToggle={toggleAllAggregators}
        onMetaToggle={toggleMetaSubEngine}
        onCrossFeatureToggle={toggleCrossFeature}
        onOperatorToggle={toggleOperator}
        onReferenceSymbolChange={(symbol) =>
          updateConfigPartial({ cross_sectional: { ...(config?.cross_sectional ?? {}), reference_symbol: symbol } })
        }
      />
    </div>
  );
}

// ─── Layer Content Renderer ─────────────────────────────────────────

interface LayerContentProps {
  schema: FeatureSchema;
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  layerKey: LayerKey;
  layerEnabled: boolean;
  searchFilter: string;
  preview: FeaturePreview | null;
  onLayerToggle: (enabled: boolean) => void;
  onCategoryToggle: (cat: string, enabled: boolean) => void;
  onItemToggle: (cat: string, name: string, enabled: boolean) => void;
  onSelectAll: (cat: string, enabled: boolean) => void;
  onAggregatorToggle: (name: string, enabled: boolean) => void;
  onAllAggregatorsToggle: (enabled: boolean) => void;
  onMetaToggle: (name: string, enabled: boolean) => void;
  onCrossFeatureToggle: (name: string, enabled: boolean) => void;
  onOperatorToggle: (name: string, enabled: boolean) => void;
  onReferenceSymbolChange: (symbol: string) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  trend: '趨勢', momentum: '動量', volatility: '波動', volume: '量能',
  cycle: '週期', pattern: '型態', statistics: '統計',
  microstructure: '微觀結構', entropy: '資訊熵', tail_risk: '尾部風險',
};

const LAYER1_ENGINE_TOOLTIPS: Record<string, string> = {
  microstructure:
    '量化市場微觀結構，衡量流動性與交易摩擦成本\n\n指標與數據源：\n' +
    '• Amihud 流動性（close, volume/quote_volume）\n  → 值越高，流動性越差、衝擊成本越大\n' +
    '• Kyle Lambda（close, volume）\n  → 每單位成交量造成的價格衝擊\n' +
    '• Roll 隱含價差（close）\n  → 從序列共變異數估計買賣價差\n' +
    '• CS 價差（high, low）\n  → 從高低價估計買賣價差\n' +
    '• OFI 訂單流失衡（taker_ratio 必要，範圍 -1~+1）\n  → 正值=買方主導；負值=賣方主導\n' +
    '• Large Trade Ratio（quote_volume, trades）\n  → >1 機構資金入場訊號\n' +
    '• VPIN 知情交易概率（close, volume，範圍 0~1）\n  → 越高，知情交易風險越高',

  entropy:
    '量化價格序列的可預測性與複雜度\n\n指標與數據源：\n' +
    '• Shannon 熵（close_return, volume, taker_ratio）\n  → 值越低，序列規律性越強（可預測）\n' +
    '• 近似熵 ApEn（close_return）\n  → 值越低，序列越可預測\n' +
    '• 樣本熵 SampEn（close_return）\n  → 比 ApEn 更穩健，低=可預測\n' +
    '• Hurst 指數（close_return，範圍 0~1）\n  → >0.5 動量持續；<0.5 均值回歸；≈0.5 隨機遊走\n' +
    '• 碎形維度（close_return，範圍 1~2）\n  → ≈1 強趨勢；≈1.5 隨機；≈2 高頻震盪\n' +
    '• 排列熵（close_return，範圍 0~1）\n  → 越高，序列越隨機',

  tail_risk:
    '量化報酬分布的極端風險與偏態特性\n\n指標與數據源：\n' +
    '• CVaR 條件風險值（close）\n  → 超過 VaR 的平均損失；負值越大，尾部風險越高\n' +
    '• RV 分解 上行/下行/RSJ（close）\n  → RSJ>0 正偏態（漲多跌少）；RSJ<0 負偏態\n' +
    '• 上下行波動比（close）\n  → >1 表示上漲波動大於下跌波動\n' +
    '• 利潤概率比 GPR（close）\n  → >1 正期望值；<1 負期望值\n' +
    '• JB 常態性統計量（close）\n  → 越大，偏離常態分布越嚴重\n' +
    '• 最大回撤 MDD（close，範圍 0~-∞）\n  → 近 0 表示近期無大回撤',
};

function LayerContent({
  schema,
  config,
  layerKey,
  layerEnabled,
  searchFilter,
  preview,
  onLayerToggle,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
  onAggregatorToggle,
  onAllAggregatorsToggle,
  onMetaToggle,
  onCrossFeatureToggle,
  onOperatorToggle,
  onReferenceSymbolChange,
}: LayerContentProps) {
  const layer = schema.layers[layerKey];
  if (!layer) return <div className="text-xs text-slate-500">未知 Layer</div>;

  const showLayerToggle = ['layer2', 'layer3', 'layer4', 'layer5', 'layer6', 'layer6_5'].includes(layerKey);

  return (
    <div className="space-y-3">
      {/* Layer-level toggle */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-medium text-slate-200">{layer.name}</span>
          {LAYER_TABS.find((t) => t.key === layerKey) && (
            <div className="text-[10px] text-slate-400 mt-0.5">
              {LAYER_TABS.find((t) => t.key === layerKey)!.desc}
            </div>
          )}
        </div>
        {showLayerToggle && (
          <button
            type="button"
            onClick={() => onLayerToggle(!layerEnabled)}
            className={`rounded-md border px-2 py-1 text-[10px] transition ${
              layerEnabled
                ? 'bg-cyan-400/15 text-cyan-100 border-cyan-300/40'
                : 'bg-white/5 text-slate-500 border-white/10'
            }`}
          >
            {layerEnabled ? '● 啟用' : '○ 停用'}
          </button>
        )}
      </div>

      {/* Layer 說明展開區塊 */}
      <LayerNotePanel layerKey={layerKey} />

      {/* Per-layer content */}
      {layerKey === 'layer1' && (
        <Layer1Content
          categories={schema.layers.layer1.categories}
          config={config}
          layerDisabled={!layerEnabled}
          searchFilter={searchFilter}
          preview={preview}
          onCategoryToggle={onCategoryToggle}
          onItemToggle={onItemToggle}
          onSelectAll={onSelectAll}
        />
      )}
      {layerKey === 'layer2' && (
        <Layer2Content
          operators={schema.layers.layer2.operators}
          config={config}
          layerDisabled={!layerEnabled}
          onOperatorToggle={onOperatorToggle}
        />
      )}
      {layerKey === 'layer3' && (
        <Layer3Content
          aggregators={schema.layers.layer3.aggregators}
          config={config}
          windows={schema.layers.layer3.windows}
          layerDisabled={!layerEnabled}
          onAggregatorToggle={onAggregatorToggle}
          onAllToggle={onAllAggregatorsToggle}
        />
      )}
      {layerKey === 'layer4' && (
        <Layer4Content layer={schema.layers.layer4} layerDisabled={!layerEnabled} />
      )}
      {layerKey === 'layer5' && (
        <Layer5Content
          features={schema.layers.layer5.features}
          config={config}
          layerDisabled={!layerEnabled}
          onFeatureToggle={onCrossFeatureToggle}
          onReferenceSymbolChange={onReferenceSymbolChange}
        />
      )}
      {layerKey === 'layer6' && (
        <Layer6Content
          subEngines={schema.layers.layer6.sub_engines}
          config={config}
          layerDisabled={!layerEnabled}
          onToggle={onMetaToggle}
        />
      )}
      {layerKey === 'layer6_5' && (
        <Layer65Content layer={schema.layers.layer6_5} layerDisabled={!layerEnabled} />
      )}
      {/* hover hint */}
      {layerKey !== 'layer1' && (
        <div className="flex items-center gap-1 pt-0.5">
          <span className="text-[9px] text-slate-500">✦ 懸停右側說明文字可查看完整計算說明</span>
        </div>
      )}
    </div>
  );
}

// ─── Layer 1 ────────────────────────────────────────────────────

function Layer1Content({
  categories,
  config,
  layerDisabled,
  searchFilter,
  preview,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
}: {
  categories: FeatureSchema['layers']['layer1']['categories'];
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  layerDisabled: boolean;
  searchFilter: string;
  preview: FeaturePreview | null;
  onCategoryToggle: (cat: string, enabled: boolean) => void;
  onItemToggle: (cat: string, name: string, enabled: boolean) => void;
  onSelectAll: (cat: string, enabled: boolean) => void;
}) {
  const categoryOrder = [
    'trend', 'momentum', 'volatility', 'volume',
    'statistics', 'cycle', 'pattern',
    'tail_risk', 'microstructure', 'entropy',
  ];

  return (
    <div className="space-y-2">
      {categoryOrder.map((catKey) => {
        const cat = categories[catKey];
        if (!cat) return null;
        const catConfig = config?.atomic_indicators?.[catKey];
        const baseItems: SchemaIndicator[] = cat.indicators || cat.features || [];
        const items: SchemaIndicator[] = baseItems.map((item) => {
          if (catConfig?.indicators) {
            const matched = catConfig.indicators.find((ind) => ind.name === item.name);
            return {
              ...item,
              enabled: matched?.enabled ?? item.enabled,
            };
          }
          if (catConfig?.features) {
            return {
              ...item,
              enabled: catConfig.features[item.name]?.enabled ?? item.enabled,
            };
          }
          return item;
        });

        return (
          <CategorySection
            key={catKey}
            label={CATEGORY_LABELS[catKey] || catKey}
            description={cat.description}
            level={cat.level}
            enabled={catConfig?.enabled ?? cat.enabled}
            items={items}
            layerDisabled={layerDisabled}
            featureCount={preview?.breakdown?.[catKey]}
            searchFilter={searchFilter}
            engineTooltip={LAYER1_ENGINE_TOOLTIPS[catKey]}
            onCategoryToggle={(enabled) => onCategoryToggle(catKey, enabled)}
            onItemToggle={(name, enabled) => onItemToggle(catKey, name, enabled)}
            onSelectAll={() => onSelectAll(catKey, true)}
            onDeselectAll={() => onSelectAll(catKey, false)}
          />
        );
      })}
    </div>
  );
}

// ─── Layer 2 ────────────────────────────────────────────────────

function Layer2Content({
  operators,
  config,
  layerDisabled,
  onOperatorToggle,
}: {
  operators: FeatureSchema['layers']['layer2']['operators'];
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  layerDisabled: boolean;
  onOperatorToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className={`space-y-0.5 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(operators).map(([name, op]) => {
          const enabled =
            (config?.operators?.[name] && typeof config.operators![name] === 'object'
              ? (config.operators![name] as { enabled?: boolean }).enabled
              : undefined) ?? op.enabled;
          const rich = RICH_DESCRIPTIONS.layer2?.[name];
          const displayDesc = rich?.short || op.description;
          const tooltipText = rich?.detail || op.description;
          return (
            <label
              key={name}
              className={`flex flex-col rounded px-2 py-1.5 cursor-pointer transition ${
                enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={enabled}
                  disabled={layerDisabled}
                  onChange={(e) => onOperatorToggle(name, e.target.checked)}
                  className="h-3 w-3 rounded border-white/20 bg-white/5 accent-cyan-400 flex-shrink-0"
                />
                <span className="font-medium text-xs truncate">{name}</span>
              </div>
              <ItemTooltip text={tooltipText}>
                <span className="text-[10px] text-slate-400 pl-[18px] leading-tight truncate block cursor-help">
                  {displayDesc}
                </span>
              </ItemTooltip>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ─── Layer 3 ────────────────────────────────────────────────────

function Layer3Content({
  aggregators,
  config,
  windows,
  layerDisabled,
  onAggregatorToggle,
  onAllToggle,
}: {
  aggregators: FeatureSchema['layers']['layer3']['aggregators'];
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  windows: number[];
  layerDisabled: boolean;
  onAggregatorToggle: (name: string, enabled: boolean) => void;
  onAllToggle: (enabled: boolean) => void;
}) {
  const resolvedAggregators = Object.fromEntries(
    Object.entries(aggregators).map(([name, agg]) => {
      const cfgAgg =
        config?.rolling_aggregation?.aggregators && !Array.isArray(config.rolling_aggregation.aggregators)
          ? config.rolling_aggregation.aggregators[name]
          : undefined;
      return [name, { ...agg, enabled: cfgAgg?.enabled ?? agg.enabled }];
    })
  ) as FeatureSchema['layers']['layer3']['aggregators'];

  const allEnabled = Object.values(resolvedAggregators).every((a) => a.enabled);

  return (
    <div className={`space-y-1.5 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="flex items-center gap-2 text-[10px]">
        <span className="text-slate-400">
          視窗：{windows.map((w) => (
            <span key={w} className="inline-block ml-1 px-1 rounded bg-white/5 text-slate-300">{w}</span>
          ))}
        </span>
        <button
          type="button"
          className="ml-auto text-cyan-300 hover:text-cyan-100 transition"
          onClick={() => onAllToggle(!allEnabled)}
        >
          {allEnabled ? '全取消' : '全選'}
        </button>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(resolvedAggregators).map(([name, agg]) => {
          const rich = RICH_DESCRIPTIONS.layer3?.[name];
          const displayDesc = rich?.short || agg.description;
          const tooltipText = rich ? `${rich.short}\n\n${rich.detail}` : agg.description;
          return (
            <label
              key={name}
              className={`flex flex-col rounded px-2 py-1.5 cursor-pointer transition ${
                agg.enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={agg.enabled}
                  disabled={layerDisabled}
                  onChange={(e) => onAggregatorToggle(name, e.target.checked)}
                  className="h-3 w-3 rounded border-white/20 bg-white/5 accent-cyan-400 flex-shrink-0"
                />
                <span className="font-medium text-xs truncate">{name}</span>
              </div>
              <ItemTooltip text={tooltipText}>
                <span className="text-[10px] text-slate-400 pl-[18px] leading-tight truncate block cursor-help">
                  {displayDesc}
                </span>
              </ItemTooltip>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ─── Layer 4 ────────────────────────────────────────────────────

function Layer4Content({
  layer,
  layerDisabled,
}: {
  layer: FeatureSchema['layers']['layer4'];
  layerDisabled: boolean;
}) {
  const lagItems = [
    {
      name: 'Lag-1',
      short: '前 1 期滯後',
      detail: '將指標向後移動 1 期：x_lag1(t) = x(t−1)。\n最常用的滯後特徵，捕捉「昨日值對今日的影響」。',
    },
    {
      name: 'Lag-N',
      short: '多期滯後序列',
      detail: '依全域設定的 sequence_length 和 lag_strategy 自動生成多期滯後。\n例：Fibonacci 間隔（1,2,3,5,8,13...）可有效涵蓋短中長期記憶。',
    },
    {
      name: '排除規則',
      short: layer.exclude_patterns.length > 0 ? layer.exclude_patterns.join(', ') : '（無）',
      detail: '符合排除規則的特徵不會生成滯後版本。\n通常用於排除已含有時序資訊的特徵（如 slope、zscore 等）。',
    },
  ];
  return (
    <div className={`space-y-1.5 ${layerDisabled ? 'opacity-50' : ''}`}>
      <div className="flex items-center gap-2 text-[10px] text-slate-400">
        <span>套用範圍：</span>
        <span className="text-slate-200">{layer.apply_to}</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {lagItems.map((item) => (
          <div
            key={item.name}
            className="flex flex-col rounded px-2 py-1.5 bg-white/[0.03]"
          >
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500 flex-shrink-0" />
              <span className="font-medium text-xs text-slate-200 truncate">{item.name}</span>
            </div>
            <ItemTooltip text={item.detail}>
              <span className="text-[10px] text-slate-400 pl-[13px] leading-tight truncate block cursor-help">
                {item.short}
              </span>
            </ItemTooltip>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-slate-400 px-1">滯後期數由全域設定（sequence_length）管理</div>
    </div>
  );
}

// ─── Layer 5 ────────────────────────────────────────────────────

function Layer5Content({
  features,
  config,
  layerDisabled,
  onFeatureToggle,
  onReferenceSymbolChange,
}: {
  features: FeatureSchema['layers']['layer5']['features'];
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  layerDisabled: boolean;
  onFeatureToggle: (name: string, enabled: boolean) => void;
  onReferenceSymbolChange: (symbol: string) => void;
}) {
  const refSymbol = config?.cross_sectional?.reference_symbol ?? 'BTCUSDT';
  return (
    <div className={`space-y-1.5 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      {/* 基準標的 (reference_symbol) */}
      <div className="flex items-center gap-2 px-1">
        <span className="text-[11px] text-slate-400 whitespace-nowrap">基準標的</span>
        <input
          type="text"
          value={refSymbol}
          onChange={(e) => onReferenceSymbolChange(e.target.value.toUpperCase())}
          disabled={layerDisabled}
          placeholder="BTCUSDT"
          className="flex-1 max-w-[120px] rounded border border-white/10 bg-white/5 px-2 py-0.5 text-xs text-slate-100 placeholder:text-slate-500 focus:border-cyan-400/50 focus:outline-none focus:ring-0"
        />
        <span className="text-[10px] text-slate-500">跨截面計算的參照標的</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(features).map(([name, feat]) => {
          const enabled =
            config?.cross_sectional?.features && !Array.isArray(config.cross_sectional.features)
              ? (config.cross_sectional.features[name]?.enabled ?? feat.enabled)
              : feat.enabled;
          const rich = RICH_DESCRIPTIONS.layer5?.[name];
          const displayDesc = rich?.short || feat.description || name;
          const tooltipText = rich ? `${rich.short}\n\n${rich.detail}` : feat.description;
          return (
            <label
              key={name}
              className={`flex flex-col rounded px-2 py-1.5 cursor-pointer transition ${
                enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={enabled}
                  disabled={layerDisabled}
                  onChange={(e) => onFeatureToggle(name, e.target.checked)}
                  className="h-3 w-3 rounded border-white/20 bg-white/5 accent-cyan-400 flex-shrink-0"
                />
                <span className="font-medium text-xs truncate">{name}</span>
              </div>
              <ItemTooltip text={tooltipText}>
                <span className="text-[10px] text-slate-400 pl-[18px] leading-tight truncate block cursor-help">
                  {displayDesc}
                </span>
              </ItemTooltip>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ─── Layer 6 ────────────────────────────────────────────────────

function Layer6Content({
  subEngines,
  config,
  layerDisabled,
  onToggle,
}: {
  subEngines: FeatureSchema['layers']['layer6']['sub_engines'];
  config: ReturnType<typeof useFeatureFactoryStore.getState>['config'];
  layerDisabled: boolean;
  onToggle: (name: string, enabled: boolean) => void;
}) {
  return (
    <div className={`space-y-0.5 ${layerDisabled ? 'opacity-50 pointer-events-none' : ''}`}>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(subEngines).map(([name, engine]) => {
          const enabled =
            (config?.meta_features as Record<string, unknown> | undefined)?.[name] as boolean | undefined;
          const resolvedEnabled = enabled ?? engine.enabled;
          const rich = RICH_DESCRIPTIONS.layer6?.[name];
          const displayDesc = rich?.short || engine.description;
          const tooltipText = rich ? `${rich.short}\n\n${rich.detail}` : engine.description;
          return (
            <label
              key={name}
              className={`flex flex-col rounded px-2 py-1.5 cursor-pointer transition ${
                resolvedEnabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400 hover:bg-white/5'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  checked={resolvedEnabled}
                  disabled={layerDisabled}
                  onChange={(e) => onToggle(name, e.target.checked)}
                  className="h-3 w-3 rounded border-white/20 bg-white/5 accent-cyan-400 flex-shrink-0"
                />
                <span className="font-medium text-xs truncate">{name}</span>
              </div>
              <ItemTooltip text={tooltipText}>
                <span className="text-[10px] text-slate-400 pl-[18px] leading-tight truncate block cursor-help">
                  {displayDesc}
                </span>
              </ItemTooltip>
            </label>
          );
        })}
      </div>
    </div>
  );
}

// ─── Layer 6.5 ──────────────────────────────────────────────────

function Layer65Content({
  layer,
  layerDisabled,
}: {
  layer: FeatureSchema['layers']['layer6_5'];
  layerDisabled: boolean;
}) {
  return (
    <div className={`text-xs space-y-1 ${layerDisabled ? 'opacity-50' : ''}`}>
      <div className="text-slate-400">
        模式: <span className="text-slate-200">{layer.mode}</span>
      </div>
      <div className="grid grid-cols-3 gap-1">
        {Object.entries(layer.methods).map(([name, method]) => {
          const rich = RICH_DESCRIPTIONS.layer6_5?.[name];
          const displayDesc = rich?.short || method.description;
          const tooltipText = rich ? `${rich.short}\n\n${rich.detail}` : method.description;
          return (
            <div
              key={name}
              className={`flex flex-col rounded px-2 py-1.5 ${
                method.enabled ? 'bg-cyan-400/10 text-slate-100' : 'text-slate-400'
              }`}
            >
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${method.enabled ? 'bg-cyan-400' : 'bg-slate-600'}`} />
                <span className="font-medium text-xs truncate">{name}</span>
              </div>
              <ItemTooltip text={tooltipText}>
                <span className="text-[10px] text-slate-400 pl-[13px] leading-tight truncate block cursor-help">
                  {displayDesc}
                </span>
              </ItemTooltip>
            </div>
          );
        })}
      </div>
      <div className="text-[10px] text-slate-400">Layer 6.5 的方法啟用控制在前處理設定面板中操作</div>
    </div>
  );
}
