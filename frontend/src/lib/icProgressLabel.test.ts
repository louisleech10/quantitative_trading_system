import { describe, expect, it } from 'vitest';

import { icEtaLabel, icFallbackLabel, icSubProgressLabel, icTaskWarningLabel } from './icProgressLabel';

describe('icFallbackLabel（降級重跑即時說明）', () => {
  it('沒有降級 ⇒ null', () => {
    expect(icFallbackLabel(null)).toBeNull();
  });
  it('有列數就講差多少；未知原因原樣顯示', () => {
    const s = icFallbackLabel({ reason: 'rolling_warmup_insufficient', details: { train_rows: 66, test_rows: 13, min_test_rows: 131 } })!;
    expect(s).toContain('測試段 13 列 < 需要 131 列');
    expect(s).toContain('不會重跑一輪');
    expect(icFallbackLabel({ reason: 'weird' })).toContain('weird');
  });
});

describe('icSubProgressLabel（EVTALIGN Task 4.1）', () => {
  it('後端沒送 ⇒ null（不顯示 0/0 假數字）', () => {
    expect(icSubProgressLabel(null)).toBeNull();
    expect(icSubProgressLabel({ step: 'winsorize', done: 0, total: 0, eta_seconds: null, eta_state: null })).toBeNull();
  });

  it('estimating ⇒ 「預估中」，不顯示假 ETA', () => {
    expect(icSubProgressLabel({ step: 'winsorize', done: 53, total: 157, eta_seconds: null, eta_state: 'estimating' }))
      .toBe('winsorize 53/157（剩餘 預估中）');
    // 即使後端夾帶了數字，state 不是 ok 也不信
    expect(icEtaLabel({ step: null, done: 1, total: 2, eta_seconds: 12, eta_state: 'estimating' })).toBe('預估中');
  });

  it('ok ⇒ 秒／分／小時三種格式', () => {
    expect(icEtaLabel({ step: null, done: 1, total: 2, eta_seconds: 40.4, eta_state: 'ok' })).toBe('約 40 秒');
    expect(icEtaLabel({ step: null, done: 1, total: 2, eta_seconds: 125, eta_state: 'ok' })).toBe('約 2 分 5 秒');
    expect(icEtaLabel({ step: null, done: 1, total: 2, eta_seconds: 3720, eta_state: 'ok' })).toBe('約 1 小時 2 分');
    expect(icEtaLabel({ step: null, done: 2, total: 2, eta_seconds: 0, eta_state: 'done' })).toBe('完成');
  });

  it('WARN 文案：已知代碼講清楚「照跑不擋」，未知代碼原樣顯示不吞', () => {
    expect(icTaskWarningLabel({ code: 'memory_pressure_observed' })).toContain('照跑');
    expect(icTaskWarningLabel({ code: 'something_new' })).toBe('後端警告：something_new');
  });
});
