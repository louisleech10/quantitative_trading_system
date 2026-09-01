/**
 * GAP-3 UX Task 1.9／1.11 — 答案窗宣告（前端純邏輯；D-7 之 L2 使用者介面）。
 *
 * 🔴 本檔**不**計算深度、**不**推測「實際用到第幾根」——那兩件事分別住
 * `momentum/Analysis/event_samples/lookahead_depth.py`（唯一深度函式）與
 * `lookahead_registry.py`（唯一 registry）。前端只做三件事：
 *   ① **逐 tf** 各一個輸入框（多 TF 批不得以單一輸入框套用全部 tf）；
 *   ② 低於預設值（＝檔內最大可用 horizon）時**強制勾選**不可驗聲明；
 *   ③ 把宣告組成後端契約形狀送出。
 *
 * 後端對同樣三件事各有 fail-closed 分支（鍵集不符／未勾調低／未宣告），
 * 前端這層只是**先講清楚**，不是唯一防線。
 */

/** 後端 `/case/import-events/lookahead-declaration` 之回應形狀。 */
export interface LookaheadDeclarationPreview {
  timeframes: string[];
  data_columns: string[];
  default_window_bars: Record<string, number>;
  requires_declaration: boolean;
  referenced_columns: string[];
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
 * 🔴 預設 `< 1`（＝檔內沒有任何可解析的未來欄）之 tf **留空不預填**（2026-09-01 UAT B10）：
 * 原本一律填入後端的 `0`，而 `validateDeclaration` 自己就拒收 `0`（「須為正整數」）
 * ⇒ 畫面一開就帶著一個系統保證會拒絕的值，使用者既不能「調低」也看不出該填什麼。
 * 留空之後走的是「尚未填寫」那條訊息，指向的動作才是對的：這個數字只有你知道。
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
 * 送出前檢查：鍵集逐 tf 齊備、值為正整數（任意正整數，不限 1..12）、調低者已勾選聲明。
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
    if (!Number.isInteger(v) || v < 1) problems.push(`${tf} 的答案窗須為正整數，目前是 ${String(v)}`);
  }
  const extra = Object.keys(declared).filter((tf) => !preview.timeframes.includes(tf));
  if (extra.length > 0) problems.push(`${extra.join('、')} 不在這批資料的 timeframe 內`);

  const lowered = loweredTimeframes(declared, preview);
  // 🔴 兩個各自獨立的勾選理由（R1 `CODEX-R1-P1-02`）：
  //   ① 系統本來就驗不了這批的深度（L2 被觸發）——此時**宣告值本身**就是不可驗聲明；
  //   ② 使用者把值調到檔內最大可用 horizon 以下。
  // 原版只有 ②，於是「檔內沒有可解析欄（預設 0）＋自訂欄」這條最該勾的路徑反而不必勾。
  const requiresAcknowledgement = preview.requires_declaration || lowered.length > 0;
  if (requiresAcknowledgement && !acknowledged) {
    problems.push(
      lowered.length > 0
        ? `${lowered.join('、')} 的答案窗低於檔內最大可用 horizon；要調低必須勾選聲明（${UNVERIFIABLE_DECLARATION_WARNING}）`
        : `這批引用了系統無法驗證深度的欄位，宣告值屬無法驗證的聲明，必須勾選確認（${UNVERIFIABLE_DECLARATION_WARNING}）`,
    );
  }
  return { ok: problems.length === 0, problems, requiresAcknowledgement };
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
