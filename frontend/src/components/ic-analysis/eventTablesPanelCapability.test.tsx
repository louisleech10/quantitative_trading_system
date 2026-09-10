/**
 * SPLITUNIFY Task 3.3 ④：切分 capability 之畫面揭露。
 *
 * 判準字面之唯一來源＝`docs/SPLITUNIFY_TODO.md` Task 3.3；本檔只把它機械化：
 *   ①`split === 'unavailable'` ⇒ **禁再顯示** train／test／purge 計數
 *   ②兩條 reason 之文案**必須可分辨**（不得同一句話）
 *   ③reason 字面來自契約檔，前端不得手打第二份
 *
 * 🔴 ①之斷言刻意寫成「畫面上不得出現 train/test/purge 這些字」而不是「不得出現 0」——
 *    後者在別處也可能有 0，抓不準；前者是這條規則的直接形態。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import EventTablesPanel from '@/components/ic-analysis/EventTablesPanel';
import {
  REASON_NO_UNIVERSE,
  REASON_UNVERIFIABLE_LOOKAHEAD,
  splitCapabilityView,
} from '@/lib/splitCapability';
import type { EventAnalyzeResponse } from '@/lib/types';

afterEach(() => cleanup());

const CONTRACT_SPLIT_UNIFY = resolve(__dirname, '../../../../momentum/Analysis/contracts/split_unify.json');
const CONTRACT_EVENT_IMPORT = resolve(__dirname, '../../../../momentum/Analysis/contracts/event_import_contract.json');

/** event-study-only 之回應：**沒有** n_train／n_test／n_purged（後端已刪，不是填 0）。 */
function response(reason: string): EventAnalyzeResponse {
  return {
    import_id: 'imp-nosplit',
    summary: { n_input: 4, n_aligned: 4, n_align_failures: 0, split: null, execution_mode: 'event_study_only' },
    align_failures: [],
    capability: { split: 'unavailable', reason },
    embargo: { applied_ms: null, source: 'not_applicable_event_study_only' },
    tables: {
      event_forward_return_table: {
        capability_status: 'ok',
        horizons: [1],
        primary_macro: { '1': { mean: 0.01, n_symbols: 1 } },
        sensitivity_micro: { '1': { mean: 0.01, median: 0.01, win_rate: 0.5, n: 4, n_effective: 4 } },
        common: { estimand_scope: 'full_sample_not_oos', formal_pooled_inference_allowed: false, reason: 'no_event_split_plan' },
      },
      binary_discrimination_table: { capability_status: 'not_computed', reason: 'no_model_scores_in_event_pipeline' },
    },
    event_timestamps: [1704067200000],
  } as unknown as EventAnalyzeResponse;
}

describe('EventTablesPanel — 切分 capability', () => {
  it('reason 字面逐字等於契約檔（前端不得手打第二份）', () => {
    const splitUnify = JSON.parse(readFileSync(CONTRACT_SPLIT_UNIFY, 'utf8'));
    const eventContract = JSON.parse(readFileSync(CONTRACT_EVENT_IMPORT, 'utf8'));
    expect(splitUnify.fail_closed_reasons).toContain(REASON_NO_UNIVERSE);
    expect(REASON_NO_UNIVERSE).toBe('canonical_feature_universe_unavailable');
    expect(eventContract.capability_reason_bindings.l3_lookahead_unverifiable).toBe(REASON_UNVERIFIABLE_LOOKAHEAD);
    expect(eventContract.capability_unavailable_reasons).toContain(REASON_UNVERIFIABLE_LOOKAHEAD);
  });

  it('兩條 reason 的文案必須可分辨（同一句話＝把可修的事講成不可修）', () => {
    const a = splitCapabilityView({ split: 'unavailable', reason: REASON_NO_UNIVERSE });
    const b = splitCapabilityView({ split: 'unavailable', reason: REASON_UNVERIFIABLE_LOOKAHEAD });
    expect(a.hasSplit).toBe(false);
    expect(b.hasSplit).toBe(false);
    expect(a.text).not.toBe(b.text);
    expect(a.text.length).toBeGreaterThan(0);
    expect(b.text.length).toBeGreaterThan(0);
  });

  it.each([
    ['無 universe', REASON_NO_UNIVERSE],
    ['深度不可證', REASON_UNVERIFIABLE_LOOKAHEAD],
  ])('%s：unavailable ⇒ 不得顯示 train／test／purge 計數', (_name, reason) => {
    render(<EventTablesPanel importId="imp-nosplit" data={response(reason)} />);
    const panel = screen.getByTestId('event-tables-panel');
    expect(panel.textContent ?? '').not.toMatch(/train|test|purge/);
    const banner = screen.getByTestId('event-split-capability');
    expect(banner.getAttribute('data-split-reason')).toBe(reason);
    expect(banner.textContent ?? '').toContain('未執行切分');
  });

  it('未知 reason ⇒ 照原字面顯示（不吞成「其他原因」）', () => {
    const view = splitCapabilityView({ split: 'unavailable', reason: 'some_future_reason' });
    expect(view.hasSplit).toBe(false);
    expect(view.text).toContain('some_future_reason');
  });

  it('capability 為 ok（或未給）⇒ 維持既有行為，仍顯示計數', () => {
    const withSplit = {
      ...response(REASON_NO_UNIVERSE),
      capability: { split: 'ok' },
      summary: { n_input: 4, n_aligned: 4, n_align_failures: 0, n_train: 3, n_test: 1, n_purged: 0 },
    } as unknown as EventAnalyzeResponse;
    render(<EventTablesPanel importId="imp-split" data={withSplit} />);
    expect(screen.getByTestId('event-tables-panel').textContent ?? '').toMatch(/train/);
    expect(screen.queryByTestId('event-split-capability')).toBeNull();
  });
});
