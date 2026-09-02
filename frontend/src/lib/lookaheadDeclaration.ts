/**
 * GAP-3 UX Task 1.9／1.9′／1.11 — 答案窗宣告（前端純邏輯；D-7 之 L2 使用者介面）。
 *
 * 🔴 本檔**不**計算深度、**不**推測「實際用到第幾根」——registry 住
 * `lookahead_registry.py`（唯一 registry）；R 重開（SPEC D-8）後深度之唯一來源＝**使用者宣告**
 * （`lookahead_bars_declared[tf] = declared_window_bars[tf]`，不與任何欄位取 max）。前端只做三件事：
 *   ① **逐 tf** 各一個輸入框（多 TF 批不得以單一輸入框套用全部 tf）；
 *   ② 低於預設值（＝檔內／結果內最大可用 horizon）時**強制勾選**不可驗聲明；
 *   ③ 把宣告組成後端契約形狀送出。
 *
 * 🔴 **validator 唯一**（SPEC Task 1.9′ ⑦）：CSV 匯入頁與 `/search` 匯出頁都取用本檔之
 * `validateDeclaration` 同一函式參考；禁第二份實作。匯出端守衛 `withExportDeclarationGuard` 亦住本檔。
 *
 * 後端對同樣三件事各有 fail-closed 分支（鍵集不符／未勾調低／未宣告），
 * 前端這層只是**先講清楚**，不是唯一防線。
 */

/**
 * 後端 `/case/import-events/lookahead-declaration`（匯入端）與
 * `/case/lookahead-declaration/preview-columns`（匯出端）之**同一**回應形狀。
 */
export interface LookaheadDeclarationPreview {
  timeframes: string[];
  data_columns: string[];
  default_window_bars: Record<string, number>;
  /** R 重開後恆 true（每批都要宣告）；不是勾選理由。 */
  requires_declaration: boolean;
  referenced_columns: string[];
  /**
   * 「宣告值本身是不可驗聲明 ⇒ 須勾選」——由後端 `declaration_is_unverifiable` 算（與拒收判定同一函式）。
   * 缺此鍵（舊 preview）時前端退而看 `referenced_columns` 非空。
   */
  acknowledgement_required?: boolean;
}

/** 勾選理由①之唯一讀法（元件與 validator 共用；不得各自再推一次）。 */
export function acknowledgementRequiredByPreview(preview: LookaheadDeclarationPreview): boolean {
  return preview.acknowledgement_required ?? preview.referenced_columns.length > 0;
}

/** 送出形狀（與後端 `lookahead_declaration` Form 欄一致）。 */
export interface LookaheadDeclarationPayload {
  declared_window_bars: Record<string, number>;
  acknowledged_unverifiable: boolean;
}

/** UI 明示之警語——錯報的後果要講在使用者眼前，不是只寫在文件裡。 */
export const UNVERIFIABLE_DECLARATION_WARNING =
  '系統無法驗證此深度，錯報將導致資料洩漏';

/**
 * 逐 tf 之初始值＝後端給的預設（檔內最大可用 horizon）；**不得**自行給更小的值。
 *
 * 🔴 預設 `< 1`（＝檔內沒有任何可解析的未來欄）之 tf **留空不預填**（2026-09-01 UAT B10；
 * R35 裁定沿用）：`0` 是合法宣告值（「未用任何未來資訊」）但**須使用者明填**，留白≠0——
 * 系統不得替使用者宣告 0。留白走的是「尚未填寫」那條訊息：這個數字只有你知道。
 */
export function initialDeclaredWindowBars(preview: LookaheadDeclarationPreview): Record<string, number> {
  const out: Record<string, number> = {};
  for (const tf of preview.timeframes) {
    const d = preview.default_window_bars[tf] ?? 0;
    if (d >= 1) out[tf] = d;
  }
  return out;
}

/** 哪些 tf 被調低到預設值以下（＝需要勾選聲明的原因）。 */
export function loweredTimeframes(
  declared: Record<string, number>,
  preview: LookaheadDeclarationPreview,
): string[] {
  return preview.timeframes.filter((tf) => (declared[tf] ?? 0) < (preview.default_window_bars[tf] ?? 0));
}

export interface DeclarationValidation {
  ok: boolean;
  /** 阻擋送出的原因（給使用者看的中文句子）；`ok` 為 true 時為空陣列。 */
  problems: string[];
  requiresAcknowledgement: boolean;
}

/**
 * 送出前檢查：鍵集逐 tf 齊備、值為**非負整數**（任意非負整數；`0` 須明填、留白≠0）、調低者已勾選聲明。
 */
export function validateDeclaration(
  declared: Record<string, number>,
  acknowledged: boolean,
  preview: LookaheadDeclarationPreview,
): DeclarationValidation {
  const problems: string[] = [];
  const missing = preview.timeframes.filter((tf) => declared[tf] === undefined || declared[tf] === null);
  if (missing.length > 0) {
    problems.push(`尚未填寫 ${missing.join('、')} 的答案窗（每個 timeframe 各填一次，不可共用一格）`);
  }
  for (const tf of preview.timeframes) {
    const v = declared[tf];
    if (v === undefined || v === null) continue;
    if (!Number.isInteger(v) || v < 0) problems.push(`${tf} 的答案窗須為非負整數（未用未來資訊請明填 0），目前是 ${String(v)}`);
  }
  const extra = Object.keys(declared).filter((tf) => !preview.timeframes.includes(tf));
  if (extra.length > 0) problems.push(`${extra.join('、')} 不在這批資料的 timeframe 內`);

  const lowered = loweredTimeframes(declared, preview);
  // 🔴 兩個各自獨立的勾選理由（R1 `CODEX-R1-P1-02`）：
  //   ① 這批引用了系統驗不了深度的欄（`referenced_columns` 非空）——此時**宣告值本身**就是不可驗聲明；
  //   ② 使用者把值調到檔內／結果內最大可用 horizon 以下。
  // 🔴 R 重開後 `requires_declaration` 恆 True（每批都要**宣告**），故勾選理由①改看 `referenced_columns`
  //    ——「一律宣告」不等於「一律勾選」，否則勾選失去鑑別力。後端同一分拆（`unverifiable` vs `needs`）。
  const requiresAcknowledgement = acknowledgementRequiredByPreview(preview) || lowered.length > 0;
  if (requiresAcknowledgement && !acknowledged) {
    problems.push(
      lowered.length > 0
        ? `${lowered.join('、')} 的答案窗低於檔內最大可用 horizon；要調低必須勾選聲明（${UNVERIFIABLE_DECLARATION_WARNING}）`
        : `這批引用了系統無法驗證深度的欄位，宣告值屬無法驗證的聲明，必須勾選確認（${UNVERIFIABLE_DECLARATION_WARNING}）`,
    );
  }
  return { ok: problems.length === 0, problems, requiresAcknowledgement };
}

// ── GAP-3 UX Task 1.9′：`/search` 匯出端之宣告守衛 ───────────────────────────

/** `/search` 匯出面板之宣告 state（preview 尚未取得時為 `null`）。 */
export interface ExportDeclarationState {
  preview: LookaheadDeclarationPreview | null;
  declared: Record<string, number>;
  acknowledged: boolean;
}

/**
 * 擋下時顯示的原因；`null` ＝ 可匯出。
 *
 * 🔴 判定**只**呼叫 `validateDeclaration`（同一份 validator），本函式不另寫任何規則：
 * 缺 preview／缺 map／批內某 tf 無鍵／非 int／`< 0`／調低未勾聲明 ⇒ 擋。
 */
export function exportDeclarationBlockMessage(state: ExportDeclarationState): string | null {
  if (!state.preview) return '尚未取得這批結果的答案窗預填資料（取得前不會讓你匯出）';
  if (state.preview.timeframes.length === 0) return '這批結果讀不到 K 線週期，無法宣告答案窗（不會讓你匯出）';
  const v = validateDeclaration(state.declared, state.acknowledged, state.preview);
  return v.ok ? null : `匯出前請先完成答案窗宣告：\n${v.problems.join('\n')}`;
}

/**
 * 宣告 map 之匯出投影：`lookahead_bars_declared[tf] = declared_window_bars[tf]`——**逐鍵複製**，
 * 不與任何欄位取 max（SPEC D-8 規則②）。只在守衛放行後呼叫；JSON 與 CSV 兩條匯出共用同一份。
 */
export function declaredWindowBarsForExport(state: ExportDeclarationState): Record<string, number> {
  const out: Record<string, number> = {};
  for (const tf of state.preview?.timeframes ?? []) out[tf] = state.declared[tf];
  return out;
}

/**
 * 匯出前之宣告守衛：**未通過時，`proceed` 一次都不會被呼叫**。
 *
 * 🔴 形狀承襲 `withExportLowerBoundGuard`（D-004 A-021／D-002 A-010 之 `proceed` 結構保證）：
 * 把要保護的整段包進 `proceed`，「阻擋早於任何網路／下載動作」是**結構上保證**的事實，
 * 不是需要用原始碼形狀去檢查的性質。**不得**退回裸 `if (…) return;` 後接長串 `await`。
 * 兩條匯出（事件 JSON、可回灌 CSV）共用同一守衛實例。
 */
export async function withExportDeclarationGuard<T>(
  state: ExportDeclarationState,
  deps: { notify: (message: string) => void; proceed: () => Promise<T> },
): Promise<T | undefined> {
  const blocked = exportDeclarationBlockMessage(state);
  if (blocked !== null) {
    deps.notify(blocked);
    return undefined;
  }
  return deps.proceed();
}

/** 組出送給後端的宣告；未宣告（preview 不要求且使用者沒動）回 `null`。 */
export function buildDeclarationPayload(
  declared: Record<string, number>,
  acknowledged: boolean,
  preview: LookaheadDeclarationPreview | null,
): LookaheadDeclarationPayload | null {
  if (!preview || preview.timeframes.length === 0) return null;
  const windows: Record<string, number> = {};
  for (const tf of preview.timeframes) windows[tf] = declared[tf];
  return { declared_window_bars: windows, acknowledged_unverifiable: acknowledged };
}
