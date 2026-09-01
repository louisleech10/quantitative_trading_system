/**
 * GAP-3 UX Task 1.9／1.11 — 答案窗宣告之前端規則。
 *
 * 這層擋的是「使用者按下送出之前」；後端對同樣三件事各有 fail-closed 分支
 * （鍵集不符／未勾調低／未宣告），故本檔只驗前端不自行放行、不自行推測深度。
 */
import { describe, expect, it } from 'vitest';

import {
  UNVERIFIABLE_DECLARATION_WARNING,
  buildDeclarationPayload,
  initialDeclaredWindowBars,
  loweredTimeframes,
  validateDeclaration,
  type LookaheadDeclarationPreview,
} from './lookaheadDeclaration';

const singleTf: LookaheadDeclarationPreview = {
  timeframes: ['12h'],
  data_columns: ['future_1bar_return', 'future_12bar_return'],
  default_window_bars: { '12h': 12 },
  requires_declaration: false,
  referenced_columns: [],
};

const multiTf: LookaheadDeclarationPreview = {
  timeframes: ['1h', '12h'],
  data_columns: ['future72_close_return'],
  default_window_bars: { '1h': 72, '12h': 6 },
  requires_declaration: true,
  referenced_columns: ['future72_close_return'],
};

describe('答案窗宣告：預設值', () => {
  it('初始值取後端給的檔內最大可用 horizon，不自行給更小的值', () => {
    expect(initialDeclaredWindowBars(singleTf)).toEqual({ '12h': 12 });
    // 小時命名欄在不同 tf 之根數不同 ⇒ 預設值本來就逐 tf 不同
    expect(initialDeclaredWindowBars(multiTf)).toEqual({ '1h': 72, '12h': 6 });
  });

  it('🔴 檔內無可解析未來欄（預設 0）⇒ **留空不預填**，且送出時報「尚未填寫」而非「須為正整數」', () => {
    // 出生事故 2026-09-01 UAT B10：預填 0 ⇒ 畫面一開就帶著一個驗證自己會拒的值。
    const noFuture: LookaheadDeclarationPreview = {
      ...singleTf, default_window_bars: { '12h': 0 }, requires_declaration: true,
    };
    expect(initialDeclaredWindowBars(noFuture)).toEqual({});
    const v = validateDeclaration(initialDeclaredWindowBars(noFuture), true, noFuture);
    expect(v.ok).toBe(false);
    expect(v.problems.join(' ')).toContain('尚未填寫');
    expect(v.problems.join(' ')).not.toContain('須為正整數');
  });
});

describe('答案窗宣告：調低須勾選聲明', () => {
  it('未勾選就調低 ⇒ 擋下並說明後果', () => {
    const v = validateDeclaration({ '12h': 4 }, false, singleTf);
    expect(loweredTimeframes({ '12h': 4 }, singleTf)).toEqual(['12h']);
    expect(v.ok).toBe(false);
    expect(v.requiresAcknowledgement).toBe(true);
    expect(v.problems.join(' ')).toContain(UNVERIFIABLE_DECLARATION_WARNING);
  });

  it('勾選後可調低；往上調（保守方向）永遠不需勾選', () => {
    expect(validateDeclaration({ '12h': 4 }, true, singleTf).ok).toBe(true);
    const up = validateDeclaration({ '12h': 20 }, false, singleTf);
    expect(up.ok).toBe(true);
    expect(up.requiresAcknowledgement).toBe(false);
  });
});

describe('答案窗宣告：逐 tf 各一格', () => {
  it('多 TF 批只填一個 tf ⇒ 擋下（不得以單一輸入框套用全部 tf）', () => {
    const v = validateDeclaration({ '1h': 72 }, true, multiTf);
    expect(v.ok).toBe(false);
    expect(v.problems.join(' ')).toContain('12h');
  });

  it('逐 tf 各填即通過，送出形狀鍵集恰為批內 tf', () => {
    const declared = { '1h': 72, '12h': 6 };
    // multiTf.requires_declaration 為 true ⇒ 仍須勾選（見下一組）
    expect(validateDeclaration(declared, true, multiTf).ok).toBe(true);
    const payload = buildDeclarationPayload(declared, true, multiTf);
    expect(Object.keys(payload!.declared_window_bars).sort()).toEqual(['12h', '1h']);
  });
});

describe('答案窗宣告：深度驗不了時一律須勾選（R1 CODEX-R1-P1-02）', () => {
  it('requires_declaration 為 true ⇒ 即使沒調低也要勾', () => {
    const declared = { '1h': 72, '12h': 6 };   // 皆等於預設，沒有調低
    expect(loweredTimeframes(declared, multiTf)).toEqual([]);
    const v = validateDeclaration(declared, false, multiTf);
    expect(v.ok).toBe(false);
    expect(v.requiresAcknowledgement).toBe(true);
    expect(v.problems.join(' ')).toContain(UNVERIFIABLE_DECLARATION_WARNING);
  });

  it('requires_declaration 為 false 且沒調低 ⇒ 不必勾（否則就是全面擋死，不是 fail-closed）', () => {
    const v = validateDeclaration({ '12h': 12 }, false, singleTf);
    expect(v.ok).toBe(true);
    expect(v.requiresAcknowledgement).toBe(false);
  });
});

describe('答案窗宣告：欄位值', () => {
  it('接受任意正整數（不限 1..12），拒非正整數', () => {
    expect(validateDeclaration({ '12h': 20 }, false, singleTf).ok).toBe(true);
    expect(validateDeclaration({ '12h': 0 }, true, singleTf).ok).toBe(false);
    expect(validateDeclaration({ '12h': 1.5 }, true, singleTf).ok).toBe(false);
    expect(validateDeclaration({ '12h': Number.NaN }, true, singleTf).ok).toBe(false);
  });
});
