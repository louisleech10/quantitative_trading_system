/**
 * EVTLABEL Task 3.9：`LabelModeBanner` 之渲染。
 *
 * 🔴 這條在防的是「使用者以為分析用了他的 0/1，其實沒有」與反過來
 * 「拿一份負對照失敗的倖存者去餵 ML」。兩者都不會拋錯，只會安靜地誤導。
 */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import LabelModeBanner from '@/components/ic-analysis/LabelModeBanner';

// 本專案未全域啟用 auto-cleanup ⇒ 逐條清，否則後面的斷言會撞到多個同 testid 元素。
afterEach(cleanup);

describe('Task 3.9 — LabelModeBanner', () => {
  it('① 用了 0/1 ⇒ info，寫出驗證段正反數', () => {
    render(
      <LabelModeBanner
        labelMode={{ effective: 'imported_binary', requested: 'auto',
                     n_pos_selection: 41, n_neg_selection: 12 }}
      />,
    );
    const el = screen.getByTestId('label-mode-banner');
    expect(el.dataset.kind).toBe('info');
    expect(el.textContent).toContain('41');
    expect(el.textContent).toContain('12');
  });

  it('② auto 被退回 ⇒ warn，寫出中文原因', () => {
    render(
      <LabelModeBanner
        labelMode={{ effective: 'return_rule', requested: 'auto', reason: 'one_class' }}
      />,
    );
    const el = screen.getByTestId('label-mode-banner');
    expect(el.dataset.kind).toBe('warn');
    expect(el.textContent).toContain('只剩一類');
  });

  it('③ 🔴 負對照失敗 ⇒ danger 且 role=alert（螢幕閱讀器也要收到）', () => {
    render(
      <LabelModeBanner
        labelMode={{ effective: 'imported_binary', requested: 'imported_binary' }}
        survivorReason="negative_control_failed"
      />,
    );
    const el = screen.getByTestId('label-mode-banner');
    expect(el.dataset.kind).toBe('danger');
    expect(el.getAttribute('role')).toBe('alert');
    expect(el.textContent).toContain('不可餵 ML');
  });

  it('④ 區塊不足 ⇒ warn，標明預期限制', () => {
    render(
      <LabelModeBanner
        labelMode={{ effective: 'imported_binary', requested: 'auto' }}
        permutationStatus="unavailable:insufficient_blocks"
      />,
    );
    const el = screen.getByTestId('label-mode-banner');
    expect(el.dataset.kind).toBe('warn');
    expect(el.textContent).toContain('預期限制');
  });

  it('⑤ 全域 run（無 label_mode）⇒ 不渲染', () => {
    const { container } = render(<LabelModeBanner />);
    expect(container.firstChild).toBeNull();
  });

  it('⑥ 使用者自選報酬版 ⇒ 不渲染（那不是降級）', () => {
    const { container } = render(
      <LabelModeBanner labelMode={{ effective: 'return_rule', requested: 'return_rule' }} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
