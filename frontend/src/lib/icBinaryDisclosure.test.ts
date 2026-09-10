/**
 * EVTLABEL Task 3.9：匯入標籤模式之表頭與 banner 文案。
 *
 * 🔴 這批測試在防兩件事：
 * ① **表頭自創名**。使用者 2026-09-10 定死「一律用統計學／業界標準名」。
 *    自創名會讓看得懂統計的人看不懂，也無法跟外部文獻對照。
 * ② **原因文案與後端枚舉脫節**。後端加了一個 reason 而前端沒有對應文案時，
 *    使用者會看到一串英文代碼；反過來前端多寫一個則是永遠不會出現的死文案。
 */
import { readFileSync } from 'fs';
import path from 'path';
import { describe, expect, it } from 'vitest';
import {
  BINARY_COLUMN_ORDER,
  LABEL_MODE_REASON_TEXT,
  binaryColumnLabels,
  binaryColumnTooltips,
  labelModeBannerText,
} from '@/lib/icLabelRule';

const contract = JSON.parse(
  readFileSync(
    path.resolve(__dirname, '../../../momentum/Analysis/contracts/event_label_mode.json'),
    'utf-8',
  ),
) as { summary_columns_binary: string[]; label_mode_reasons: string[] };

describe('Task 3.9 — 表頭用統計學標準名', () => {
  it('① 欄集與後端契約 `summary_columns_binary` 逐值相同', () => {
    expect([...BINARY_COLUMN_ORDER].sort()).toEqual([...contract.summary_columns_binary].sort());
  });

  it('② 每一欄都有標準名文案，且不是自創名', () => {
    const labels = binaryColumnLabels();
    for (const key of BINARY_COLUMN_ORDER) {
      expect(labels[key], `缺欄 ${key} 之文案`).toBeTruthy();
    }
    // 標準名逐一釘住——改成自創名（例如「分辨力」「區分度」）本條即紅
    expect(labels.auc).toBe('AUC');
    expect(labels.rank_biserial).toBe('rank-biserial r');
    expect(labels.mw_u).toBe('U');
    expect(labels.mw_p_value).toBe('p');
    expect(labels.mw_p_value_adj).toBe('q');
  });

  it('③ 主統計排在報酬版之前（欄序即優先序）', () => {
    expect(BINARY_COLUMN_ORDER[0]).toBe('rank_biserial');
    expect(BINARY_COLUMN_ORDER.indexOf('auc')).toBeLessThan(
      BINARY_COLUMN_ORDER.indexOf('mw_p_value_adj'),
    );
  });

  it('④ tooltip 講清楚 0.5／1 的意思與正負方向', () => {
    const tips = binaryColumnTooltips();
    expect(tips.auc).toContain('0.5');
    expect(tips.auc).toContain('1');
    expect(tips.rank_biserial).toContain('2·AUC−1');
    expect(tips.rank_biserial).toContain('絕對值');
  });
});

describe('Task 3.9 — 退回報酬版之原因文案', () => {
  it('① 契約裡的每一個 reason 都要有中文文案（否則使用者看到英文代碼）', () => {
    for (const reason of contract.label_mode_reasons) {
      expect(LABEL_MODE_REASON_TEXT[reason], `缺 ${reason} 之文案`).toBeTruthy();
    }
  });

  it('② 前端不得多出契約沒有的 reason（死文案）', () => {
    const extra = Object.keys(LABEL_MODE_REASON_TEXT).filter(
      (k) => !contract.label_mode_reasons.includes(k) && k !== 'conditional_ic_abandoned',
    );
    expect(extra).toEqual([]);
  });
});

describe('Task 3.9 — banner 文案', () => {
  it('① 用了 0/1 ⇒ info，並寫出驗證段的正反數與「報酬版在第二欄」', () => {
    const out = labelModeBannerText({
      effective: 'imported_binary', requested: 'auto',
      n_pos_selection: 41, n_neg_selection: 12,
    });
    expect(out?.kind).toBe('info');
    expect(out?.text).toContain('41');
    expect(out?.text).toContain('12');
    expect(out?.text).toContain('第二欄');
  });

  it('② auto 被退回 ⇒ warn，並說出原因（不是丟英文代碼）', () => {
    const out = labelModeBannerText({
      effective: 'return_rule', requested: 'auto', reason: 'class_below_min_selection',
    });
    expect(out?.kind).toBe('warn');
    expect(out?.text).toContain('已自動改用報酬規則');
    expect(out?.text).toContain('太少');
    expect(out?.text).not.toContain('class_below_min_selection');
  });

  it('③ 🔴 負對照失敗 ⇒ danger，且明講「不可餵 ML」', () => {
    const out = labelModeBannerText(
      { effective: 'imported_binary', requested: 'imported_binary' },
      'negative_control_failed',
    );
    expect(out?.kind).toBe('danger');
    expect(out?.text).toContain('不可餵 ML');
  });

  it('④ 區塊不足 ⇒ warn，且標明是**預期限制**不是錯誤', () => {
    const out = labelModeBannerText(
      { effective: 'imported_binary', requested: 'auto' },
      null,
      'unavailable:insufficient_blocks',
    );
    expect(out?.kind).toBe('warn');
    expect(out?.text).toContain('預期限制');
    expect(out?.text).toContain('不可餵 ML');
  });

  it('⑤ 使用者自己選 return_rule ⇒ 不顯示 banner（那不是降級）', () => {
    expect(labelModeBannerText({ effective: 'return_rule', requested: 'return_rule' })).toBeNull();
  });

  it('⑥ 沒有 label_mode ⇒ null（全域 run 不渲染）', () => {
    expect(labelModeBannerText(null)).toBeNull();
    expect(labelModeBannerText(undefined)).toBeNull();
  });

  it('⑦ 危險訊息之優先序：負對照失敗蓋過一切', () => {
    const out = labelModeBannerText(
      { effective: 'return_rule', requested: 'auto', reason: 'one_class' },
      'negative_control_failed',
      'unavailable:insufficient_blocks',
    );
    expect(out?.kind).toBe('danger');
  });
});
