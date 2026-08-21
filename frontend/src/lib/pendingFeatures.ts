/**
 * 前端占位（不遺忘機制；使用者 2026-08-19 裁定）：所有「需要前端但現在不做」的殘留一律列於此，
 * 並在功能將來出現的位置放殼（PendingFeatureCard）。
 *
 * 🔴 SoT＝docs/IC_QUANT_GAP_REGISTRY.md（三值理由／觸發條件的權威文字住那裡）；本檔只放
 *   registry ID＋摘要＋建議施作階段＋殼要掛的位置。vitest（pendingFeatures.test.ts）讀 registry
 *   斷言：每個 registryId 存在於 registry、其「為何現在不做」三值（blocked-by／user-ruling／needs-research）
 *   與 registry 一致——殘留被收掉或改理由而本檔沒改就紅。收殘留時同步移除本檔條目與殼。
 */
export type ResidualKind = 'blocked-by' | 'user-ruling' | 'needs-research';

export interface PendingFeature {
  /** registry 表列之 ID（G1-R3／G2-R1…；GAP-3 尚無 R 編號者用 registry 章節名） */
  registryId: string;
  /** 使用者一句話看懂 */
  title: string;
  /** 三值理由（須與 registry 一致；vitest 機檢） */
  kind: ResidualKind;
  /** 為何現在不做（白話摘要；權威文字見 registry） */
  why: string;
  /** 建議施作階段（主委建議；非承諾） */
  suggestedPhase: string;
  /** 觸發條件（摘要） */
  trigger: string;
  /** 將來 UI 會出現在哪一頁（殼放置點） */
  location: string;
  /** registry 章節錨點（人讀） */
  registryAnchor: string;
}

export const PENDING_FEATURES: PendingFeature[] = [
  {
    registryId: 'G1-R3',
    title: 'GAP-1 策略層防過擬合：前端降級展示面板＋警語（DSR／MinBTL／PBO 三關、N 帳本狀態）',
    kind: 'user-ruling',
    why: '2026-08-17 交付範圍 A 不含 frontend（成熟度地圖：frontend 屬不完整層）。後端與 API 已就緒（ml_pipeline 回應之 strategy_validation 三鍵：eligibility／display_downgrade／warning_text_key）。',
    suggestedPhase: 'ML／Optuna 層重寫或宣告穩定、GAP-1 橋（G1-R1）接上時一起做；或使用者點名即做（純消費 API 三鍵，工作量小）。',
    trigger: '使用者要求 UI，或 G1-R1／R2 任一落地',
    location: '優化結果頁（/optimization-execution/result/[taskId]）策略驗證區塊',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-1 待補完」G1-R3',
  },
  {
    registryId: 'G1-R1',
    title: 'GAP-1 N 帳本生產者接線（Optuna／搜尋器每次 trial 寫入 N ledger）——UI 端顯示真實 N',
    kind: 'blocked-by',
    why: 'momentum/Optimization 屬不完整層，接上即於重寫時作廢；契約層（ledger／validator）已 fail-closed 就緒。',
    suggestedPhase: 'Optuna／搜尋器重寫或開工時（與 G1-R3 面板同批）。',
    trigger: 'Optuna／搜尋器重寫或開工時',
    location: '優化結果頁（策略驗證區塊之 N 來源顯示）',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-1 待補完」G1-R1',
  },
  {
    registryId: 'G2-R1',
    title: 'IC→ML 橋本體：從倖存者檔（ic_survivors_{case_id}.json）選因子餵 ML，強制 sample_scope／OOS 四欄',
    kind: 'user-ruling',
    why: '2026-08-18 使用者裁定橋本體 blocked-by ML 層（ML／回測屬不完整層、可能重寫；接上即隨殼作廢）。契約已於 GAP-2 落地（每次 IC 分析都會寫倖存者檔）。',
    suggestedPhase: 'ML 層重寫或宣告穩定後；屆時一併定「選因子漏斗」（自動門檻／手選／混合）——產品取捨，白話問使用者。',
    trigger: 'ML 層重寫或宣告穩定',
    location: '模式發現（/patterns）XGBoost 頁的因子來源選擇；目前只能 watchlist 手選',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-2 待補完」G2-R1',
  },
  {
    registryId: 'G2-R8',
    title: 'IC 頁狀態文案中文化（SectionStatusNotice 對 GAP-2 reason 如 disabled_by_config 顯示契約字面）',
    kind: 'user-ruling',
    why: '契約字面即 SoT、避免第二份文案表（GAP-2 B5 review 三家接受）。',
    suggestedPhase: '事件型（GAP-3）UI 開工時併入統一文案表（文案表 ⊆ 契約 reasons，機檢一致）。',
    trigger: '產品要中文友好文案時開 UX 小票',
    location: 'IC 分析頁各節狀態提示',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-2 待補完」G2-R8',
  },
  {
    registryId: 'G3-R9',
    title: 'GAP-3 正反例辨別表（第二張表）在 /ic-analysis 事件模式接真實分數（B4.1 pattern 橋 test 段分數）',
    kind: 'blocked-by',
    why: '匯入管線本身不產模型分數；分數來源＝B4.1 pattern 橋／ML 層（成熟度地圖：不完整層）。後端已回 not_computed:no_model_scores_in_event_pipeline，前端如實顯示原因。',
    suggestedPhase: 'ML 層宣告穩定或 B4.1 pattern 橋接上 UI 時一起做。',
    trigger: 'ML 層穩定／使用者點名要在事件模式看辨別表數值',
    location: '/ic-analysis 事件模式「正反例辨別表」區塊',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-3 殘留」G3-R9',
  },
  {
    registryId: 'G3-R10',
    title: 'GAP-3 事件匯入大檔：串流／分頁＋背景 worker（現為 bounded 上傳＋分塊解析；10k 事件對齊 ~73s 同步完成）',
    kind: 'user-ruling',
    why: 'W10：規模驗收為記錄型 receipt，不私定門檻；現行 MAX_FILE_SIZE 50MB＋CSV 分塊解析；真正串流／async worker 待需求與門檻由 SPEC amendment 定。',
    suggestedPhase: '使用者提出萬級以上匯入需求或 SPEC amendment 定效能門檻時。',
    trigger: '匯入規模或牆鐘需求明確化',
    location: '/data-preparation「匯入事件」（大檔進度條／背景任務）',
    registryAnchor: 'IC_QUANT_GAP_REGISTRY.md「GAP-3 殘留」G3-R10',
  },
];

export function findPendingFeature(registryId: string): PendingFeature | undefined {
  return PENDING_FEATURES.find((f) => f.registryId === registryId);
}
