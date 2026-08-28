/**
 * GAP-3 UX **Task 7.6 內容② ＋ Task 7.3 要點3** — **欄位級** formatter registry（單一 exported 物件）。
 *
 * 🔴 **共用之粒度是「欄位級」，不是「面板級」**（SPEC L3110–3114）：
 *    每個欄位一個 formatter，各頁**只選取自己的欄集**。
 *    寫成兩個各自硬編欄集的面板級 formatter＝第二份副本；
 *    寫成單一面板級共用則會逼其中一頁多顯示或少顯示欄位（兩頁欄集本來就不同）。
 *
 * 🔴 **值一律由呼叫端傳入實際設定**，本檔不知道任何預設值、也不去讀 store
 *    ——「顯示值 == 落檔實際值」才可能成立（Task 4.1b 邊界②之病因）。
 * 🔴 白話部分取自契約 `doc` 之鏡像（`eventContractDocs.ts`），本檔不另寫欄位語意。
 * 🔴 `t0`／`label` 為**逐列陣列**欄，signature 由 SPEC L3100–3104 定死：
 *    各自只吃**自己那個兩鍵陣列**，不得共用一個三鍵 records 輸入
 *    （否則 t0 之 formatter 讀得到 label，欄位語意重疊）。
 */

import { EVENT_CONTRACT_DOCS } from './eventContractDocs';

/** `t0` 欄之逐列形狀（SPEC L3095）。 */
export interface EventT0Row { event_id: string; t0_ms: number }
/** `label` 欄之逐列形狀（SPEC L3096）。 */
export interface EventLabelRow { event_id: string; label: 0 | 1 }
/** 逐 timeframe 之深度／purge 揭露輸入（**不得**塌成單一 scalar，§D-3′-a(ii)）。 */
export interface EventDepthRow {
  timeframe: string;
  bars: number;
  referencedColumns: readonly string[];
}

function isoOf(ms: number): string {
  return Number.isFinite(ms) ? new Date(ms).toISOString().replace('.000Z', 'Z') : '（無法解析）';
}

/**
 * 🔴 **單一** exported registry 物件。`/search`（Task 7.3）與 `/ic-analysis`（Task 7.6）
 *    斷言取用的是**同一個參考**——複製一份到另一頁會讓該斷言直接紅。
 */
export const EVENT_FIELD_FORMATTERS = {
  scenario: (v: string): string => `本批 scenario ＝ ${v} — ${EVENT_CONTRACT_DOCS.scenario}`,

  control_kind: (v: string): string => `control_kind ＝ ${v} — ${EVENT_CONTRACT_DOCS.control_kind}`,

  entry_price_semantic: (v: string): string =>
    `進場價語意（entry_price_semantic）＝ ${v} — ${EVENT_CONTRACT_DOCS.entry_price_semantic}`,

  label_return_mode: (v: string): string =>
    `報酬算法（label_return_mode）＝ ${v} — ${EVENT_CONTRACT_DOCS.label_return_mode}`,

  decision_offset_bars: (v: number): string =>
    `決策位移（decision_offset_bars）＝ ${v} 根 — ${EVENT_CONTRACT_DOCS.decision_offset_bars}`,

  /** 批次事實欄（Task 7.6）：批內單值，異質即 Task 1.8 拒收 ⇒ scalar。 */
  direction: (v: string): string =>
    `方向（direction）＝ ${v}——它決定 short 取負，是批次事實，不可在分析頁改`,

  /**
   * `t0`：**逐列**欄，無單一 scalar 語意 ⇒ formatter 由陣列**導出摘要**
   * （筆數＋首末時間），**不得**在前端另算一份 t0 語意（SPEC L3106）。
   */
  t0: (rows: readonly EventT0Row[]): string => {
    if (rows.length === 0) return 't0：這批沒有任何事件';
    const ms = rows.map((r) => r.t0_ms);
    return `t0：${rows.length} 筆，最早 ${isoOf(Math.min(...ms))}、最晚 ${isoOf(Math.max(...ms))}（epoch ms UTC）`;
  },

  /** `label`：**逐列**欄 ⇒ 摘要為 0／1 分佈。 */
  label: (rows: readonly EventLabelRow[]): string => {
    const pos = rows.filter((r) => r.label === 1).length;
    return `label：正例 ${pos} 筆／反例 ${rows.length - pos} 筆（共 ${rows.length} 筆，由你自己聲明）`;
  },

  /**
   * lookahead 深度：顯示 `lookahead_bars_declared`（**真實深度**），
   * **不是** `window.horizon_bars`——後者有下限 1 之 floor，深度 0 會被顯示成 1（§D-3′-a(i)）。
   */
  lookahead_depth: (row: EventDepthRow): string =>
    `lookahead 深度（${row.timeframe}）＝ ${row.bars} 根，來源＝你的篩選條件引用到的欄位`
    + (row.referencedColumns.length > 0 ? `：${row.referencedColumns.join('、')}` : '：無（沒有設篩選條件）'),

  /** purge 下界：公式權威在 §D-3′-a(ii)，本欄**只揭露結果**。 */
  purge_bars: (row: EventDepthRow): string =>
    `本批之 purge 下界（事件事實層，${row.timeframe}）＝ ${row.bars} 根——`
    + '這個深度來自你的 label 定義最遠引用到 t0 之後第幾根。'
    + '條件 IC 分析時之實際 purge 另取本次答案窗，取兩者較大者。',
} as const;

export type EventFieldKey = keyof typeof EVENT_FIELD_FORMATTERS;

/**
 * GAP-3 UX **Task 7.4 ＝ Task 4.1c 之唯一文案來源**（SPEC L2985–2990）。
 *
 * 🔴 **兩處不得各寫一份**——4.1c 原本是 `search/page.tsx` 之 JSX 行內字串，
 *    7.4 要求「同一 exported 常數（斷言同一參考）」⇒ 抽到這裡，page 只引用。
 * 🔴 措辭邊界：**不得**把重新匯出講成換答案窗之手段。
 *    既有之 4.1c 驗收（`eventExportNoIcDecay.test.tsx`）採**更嚴**的字面判準
 *    ——「重新匯出」四字一次都不得出現，連「**不需**重新匯出」也不行。
 *    本常數改以「不必再匯出一次」表達同一件事：語意不變、**不放寬**既有守衛
 *    （為了讓自己的新文案通過而去鬆綁既有斷言，就是本 epic 反覆付過代價的形態）。
 * 🔴 存活至 GAP-6：屆時若交付 multi-horizon IC 則整段撤除。
 */
export const EVENT_IC_DECAY_DISCLOSURE =
  '條件 IC decay 曲線（一次分析同時得到多個 h 的 IC）非本批交付；附帶的 future_* 欄不進入 ic_feed。'
  + '要看不同答案窗，請於 IC 分析頁改答案窗重跑分析——同一批事件事實可以重複分析，不必再匯出一次。'
  + '一次得到整條 decay 曲線待 GAP-6 之 IC-Analysis 整體處理。';

/**
 * `/search` 匯出面板之欄集（Task 7.3 要點1 之七項）。
 * 🔴 `control_kind` 為必列項——4.1b 宣稱 7.3 為其嚴格超集，而原清單漏掉它。
 */
export const SEARCH_DISCLOSURE_FIELDS: readonly EventFieldKey[] = [
  'scenario', 'control_kind', 'entry_price_semantic', 'label_return_mode',
  'decision_offset_bars', 'lookahead_depth', 'purge_bars',
];

/**
 * `/ic-analysis` 之**批次事實欄**欄集（Task 7.6 三分表之封閉集合）。
 * 🔴 `direction` 歸批次事實（決定 short 取負、是 §G G-3 之 golden input），**不**進 `event_label_spec`。
 */
export const IC_BATCH_FACT_FIELDS: readonly EventFieldKey[] = [
  'scenario', 'control_kind', 'direction', 't0', 'label',
];
