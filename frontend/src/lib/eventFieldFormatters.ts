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

  /**
   * `G3-D2` D1.5／D1.6：`label_origin`＝這批的答案是**怎麼來的**（provenance）。
   *
   * 🔴 批次事實欄，scalar（批內常數）。異質 ⇒ 由 `_ALWAYS_HOMOGENEOUS_DIMENSIONS`
   *    （**無條件**同質組）拒收，**不是** Task 1.8 那個受 `enforce_batch_homogeneity`
   *    旗標控制的組——該旗標預設 `False`，掛在它底下等於預設不檢查。
   *    （R2 之三家全員 finding 與 R3 之 grok／composer 皆指出原註解歸屬寫錯；
   *     歸屬寫錯正是 R2 群集 1 的成因之一，故不留著。）
   * 🔴 **舊批可能沒有這一欄** ⇒ 傳 `null`／`undefined` 時顯示「（未宣告）」而**不是**空字串或猜測值：
   *    猜一個值等於替使用者宣告 provenance，那正是本欄要防的事。
   */
  label_origin: (v: string | null | undefined): string => {
    const shown = (typeof v === 'string' && v !== '') ? v : '（未宣告）';
    return `答案來源（label_origin）＝ ${shown} — ${EVENT_CONTRACT_DOCS.label_origin}`;
  },

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
  // 🔴 R 重開（SPEC D-8／Task 1.9′）：深度來源＝**你在匯出前宣告的值**（正反例判定所用之最遠者），
  //    不再由篩選條件引用欄導出（Phase 2 退役）；本行**禁**殘留對 `exportFilters` 之讀取。
  lookahead_depth: (row: EventDepthRow): string =>
    `lookahead 深度（${row.timeframe}）＝ ${row.bars} 根，來源＝你在匯出前宣告的值（正反例判定所用之最遠者）`,

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
  // 🔴 原文寫「待 GAP-6 之 IC-Analysis 整體處理」——`GAP-6` 是**我們的施工票號**，
  //    使用者看到只會困惑（2026-09-02 使用者：「以後使用者哪知道什麼是 GAP3？」）。
  //    票號留在上方註解供追溯，畫面上只講「還沒做、之後會做」。
  + '一次得到整條 decay 曲線是之後的工作，目前還沒有。';

/**
 * `/search` 匯出面板之欄集（Task 7.3 要點1 之七項）。
 * 🔴 `control_kind` 為必列項——4.1b 宣稱 7.3 為其嚴格超集，而原清單漏掉它。
 */
export const SEARCH_DISCLOSURE_FIELDS: readonly EventFieldKey[] = [
  'scenario', 'control_kind', 'entry_price_semantic', 'label_return_mode',
  'decision_offset_bars', 'lookahead_depth', 'purge_bars',
];

/** `searchDisclosureLines` 之輸入：本批之實際設定（**全部**由呼叫端傳入，本模組不讀 store）。 */
export interface SearchDisclosureContext {
  dims: {
    scenario: string;
    control_kind: string;
    entry_price_semantic: string;
    label_return_mode: string;
    decision_offset_bars: number | '';
  };
  /** 逐 timeframe 之真實深度（＝使用者宣告之 `declared_window_bars`）；空 map ＝ 尚未宣告。 */
  depthByTimeframe: Record<string, number>;
}

/**
 * 🔴 **R3 群集 B**（`CODEX-R3-P2-02`＋`GROK-R3-P2-01`，兩家獨立命中）：
 * 把 `/search` 揭露區之欄集**真的**由 `SEARCH_DISCLOSURE_FIELDS` 驅動。
 *
 * 原缺陷：`page.tsx` 之註解宣稱「本頁只選取自己的欄集」，但 JSX 是**逐欄手寫**七段、
 * 連 import 都沒有 ⇒ 往常數加欄不會改變任何 DOM，而 IC 頁確實是 `.map` 驅動、兩頁不對稱。
 * 這正是 7.3 要滅的「第二份欄集」——**宣稱大於實作**（本 epic 最常見之自傷）。
 *
 * 逐 timeframe 之欄（`lookahead_depth`／`purge_bars`）一個欄位會產生**多行**，
 * 故回傳陣列而非單一字串；`testid` 一併由本函式決定，頁面不再自己拼。
 */
export function searchDisclosureLines(
  field: EventFieldKey, ctx: SearchDisclosureContext,
): { testid: string; text: string }[] {
  const f = EVENT_FIELD_FORMATTERS;
  switch (field) {
    case 'scenario':
      return [{ testid: 'export-disclosure-scenario', text: f.scenario(ctx.dims.scenario) }];
    case 'control_kind':
      return [{ testid: 'export-disclosure-control-kind', text: f.control_kind(ctx.dims.control_kind) }];
    case 'entry_price_semantic':
      return [{
        testid: 'export-disclosure-entry-price-semantic',
        text: f.entry_price_semantic(ctx.dims.entry_price_semantic),
      }];
    case 'label_return_mode':
      return [{
        testid: 'export-disclosure-label-return-mode',
        text: f.label_return_mode(ctx.dims.label_return_mode),
      }];
    case 'decision_offset_bars':
      return [{
        testid: 'export-disclosure-decision-offset-bars',
        text: f.decision_offset_bars(Number(ctx.dims.decision_offset_bars)),
      }];
    case 'lookahead_depth': {
      const tfs = Object.keys(ctx.depthByTimeframe);
      // 🔴 尚未宣告**不是**「深度為 0」（0 須明填）——顯式講出來，且該狀態下匯出本來就被守衛擋住。
      if (tfs.length === 0) {
        return [{
          testid: 'export-disclosure-depth-pending',
          text: 'lookahead 深度：尚未宣告（宣告前不會讓你匯出）',
        }];
      }
      // 🔴 逐 tf 各一行，不得塌成單一 scalar（§D-3′-a(ii)）
      return tfs.map((tf) => ({
        testid: `export-disclosure-depth-${tf}`,
        text: f.lookahead_depth({ timeframe: tf, bars: ctx.depthByTimeframe[tf] }),
      }));
    }
    case 'purge_bars':
      return Object.keys(ctx.depthByTimeframe).map((tf) => ({
        testid: `export-disclosure-purge-${tf}`,
        text: f.purge_bars({ timeframe: tf, bars: ctx.depthByTimeframe[tf] }),
      }));
    default:
      // 欄集加了新欄卻沒在此對應 ⇒ **fail-loud**，不靜默少顯示一項（那正是 7.3 要防的）
      throw new Error(`searchDisclosureLines: 欄位 ${field} 尚未接線`);
  }
}

/**
 * `/ic-analysis` 之**批次事實欄**欄集（Task 7.6 三分表之封閉集合）。
 * 🔴 `direction` 歸批次事實（決定 short 取負、是 §G G-3 之 golden input），**不**進 `event_label_spec`。
 */
export const IC_BATCH_FACT_FIELDS: readonly EventFieldKey[] = [
  // 🔴 D1.6：`label_origin` 為第六鍵（覆寫 Task 7.6 之原五鍵封閉集合）。
  //    順序與後端 `EventBatchFacts` 之欄序一致，方便逐欄對讀。
  'scenario', 'control_kind', 'direction', 'label_origin', 't0', 'label',
];
