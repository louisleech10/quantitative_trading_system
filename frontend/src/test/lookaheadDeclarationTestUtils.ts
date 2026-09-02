/**
 * `/search` 頁測試共用：匯出端答案窗宣告（GAP-3 UX Task 1.9′）之 preview mock 與「填宣告」動作。
 *
 * 🔴 R 重開（SPEC D-8）後匯出前**必須**逐 tf 宣告並勾選不可驗聲明，否則守衛不呼叫 `proceed`。
 * 舊測試以 `fetchLookaheadDepth` 之回傳 map 當深度來源；現改為：mock `fetchLookaheadDeclarationPreviewColumns`
 * 回 `previewOf(map)`（map 只當**預設候選**），再由 `declareFromPreview()` 把同一 map **當使用者宣告填進去**。
 * 這樣「匯出檔之 `lookahead_bars_declared` == map」之既有斷言仍成立，且成立的理由是宣告而非導出。
 */
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { expect } from 'vitest';
import type { LookaheadDeclarationPreview } from '@/lib/lookaheadDeclaration';

let lastDefaults: Record<string, number> = {};

/** 由「逐 tf 預設值」組出後端 preview 形狀；同時記住 map 供 `declareFromPreview()` 使用。 */
export function previewOf(defaults: Record<string, number>): LookaheadDeclarationPreview {
  lastDefaults = { ...defaults };
  return {
    timeframes: Object.keys(defaults),
    data_columns: [],
    default_window_bars: { ...defaults },
    requires_declaration: true,
    referenced_columns: [],
    acknowledgement_required: false,
  };
}

/**
 * 等宣告框出現，逐 tf 填入 `declared`（預設＝上一次 `previewOf` 之 map；`0` 也**明填**），並勾選聲明。
 * 回傳實際填入之 map（供斷言比對，不寫死數字）。
 */
export async function declareFromPreview(
  declared: Record<string, number> = lastDefaults,
): Promise<Record<string, number>> {
  await waitFor(() => expect(screen.getByTestId('lookahead-declaration')).toBeTruthy());
  for (const [tf, v] of Object.entries(declared)) {
    fireEvent.change(screen.getByTestId(`lookahead-window-${tf}`), { target: { value: String(v) } });
  }
  // 勾選列只在「調低於預設」或「引用了驗不了的欄」時出現；有就勾
  const ack = screen.queryByTestId('lookahead-acknowledge') as HTMLInputElement | null;
  if (ack && !ack.checked) fireEvent.click(ack);
  return { ...declared };
}
