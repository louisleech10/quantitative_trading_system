/**
 * SPLITUNIFY Task 4.1：`splitAuthority` 之值集對證與顯示規則。
 *
 * 判準：SPEC C-6／C-8——值集**自契約讀**（禁前端第二份）；`n_test` 為 null 時顯示「無」，
 * **永遠不顯示 0**（0 讀起來是「算過，結果是零個」＝本票要消滅的假數字）。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import {
  SPLIT_AUTHORITY_VALUES,
  SPLIT_UNIFY_KEYS,
  splitAuthorityLabel,
  splitUnifyView,
  type SplitUnifyDisclosure,
} from '@/lib/splitAuthority';

const CONTRACT_PATH = resolve(__dirname, '../../../momentum/Analysis/contracts/split_unify.json');
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, 'utf8'));

const OK: SplitUnifyDisclosure = {
  n_test: 13,
  split_authority: 'kline_holdout',
  boundary_hash: 'a'.repeat(64),
  per_symbol_counts: { ETHUSDT: 13 },
  reason: null,
};

describe('splitAuthority — 值集與契約對證', () => {
  it('值集逐字等於契約（前端不得手打第二份）', () => {
    expect([...SPLIT_AUTHORITY_VALUES]).toEqual(CONTRACT.split_authority_values);
    expect([...SPLIT_UNIFY_KEYS]).toEqual(CONTRACT.split_unify_keys);
  });

  it('契約之 canonical 鍵恰一個，且就是 split_unify.n_test', () => {
    expect(CONTRACT.test_segment_count_keys.canonical).toBe('metadata.split_unify.n_test');
  });

  it('未知權威值照原字面顯示（不吞成「其他」）', () => {
    expect(splitAuthorityLabel('kline_holdout')).toContain('K 線');
    expect(splitAuthorityLabel('some_future_authority')).toBe('some_future_authority');
    expect(splitAuthorityLabel(null)).toBe('未提供');
  });
});

describe('splitUnifyView — 顯示規則', () => {
  it('有數字 ⇒ 顯示該數字＋來源', () => {
    const v = splitUnifyView(OK)!;
    expect(v.hasCount).toBe(true);
    expect(v.countText).toBe('13');
    expect(v.authorityText).toContain('K 線');
    expect(v.reason).toBeNull();
  });

  it('🔴 n_test 為 null ⇒ 顯示「無」，不得顯示 0', () => {
    const v = splitUnifyView({ ...OK, n_test: null, boundary_hash: null, per_symbol_counts: {}, reason: 'multi_symbol_projection_unsupported' })!;
    expect(v.hasCount).toBe(false);
    expect(v.countText).toBe('無');
    expect(v.countText).not.toBe('0');
    expect(v.reason).toBe('multi_symbol_projection_unsupported');
  });

  it('n_test 為 0 是合法的數字（真的零個），與 null 不同', () => {
    const v = splitUnifyView({ ...OK, n_test: 0, per_symbol_counts: {} })!;
    expect(v.hasCount).toBe(true);
    expect(v.countText).toBe('0');
  });

  it('缺整塊且連切分 metadata 都沒有（舊／不完整 artifact）⇒ 回 null，呼叫端不渲染', () => {
    expect(splitUnifyView(undefined)).toBeNull();
    expect(splitUnifyView(null)).toBeNull();
    expect(splitUnifyView(undefined, { hasSplitMetadata: false })).toBeNull();
  });

  it('🔴 已知的全域 run（有切分 metadata、沒有 split_unify）⇒ 明說「不適用」', () => {
    const v = splitUnifyView(undefined, { hasSplitMetadata: true })!;
    expect(v.notApplicable).toBe(true);
    expect(v.countText).toBe('不適用');
    expect(v.countText).not.toBe('0');
    expect(v.hasCount).toBe(false);
    // 出生理由（CODEX-R1-P2-04）：直接不渲染會讓使用者分不出「這頁本來就沒這個數字」與「後端漏了」
  });
});
