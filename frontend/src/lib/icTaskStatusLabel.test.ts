/**
 * GAP-3 UX Task 6.3 前端半之驗收（`--run icTaskStatusLabel`）。
 *
 * SPEC L2148–2159 邊界②：**兩種狀態之顯示字串 `!==`**。
 * 🔴 階段字串為可擴充集合 ⇒ 本檔**不得**以固定 enum 窮舉相等斷言鎖死
 *（GAP-6 會細分更多階段；改測試是掩蓋行為變更的常見路徑）。
 */
import { describe, expect, it } from 'vitest';
import {
  IC_LABEL_IDLE,
  IC_LABEL_NO_RESPONSE,
  IC_LABEL_RUNNING,
  icFeatureCountLabel,
  icTaskStatusLabel,
} from './icTaskStatusLabel';

describe('Task 6.3 — 前端區分「後端無回應」與「任務執行中」', () => {
  it('① 兩種狀態之顯示字串不相同（SPEC 邊界②）', () => {
    const running = icTaskStatusLabel({ status: 'running', pollFailed: false });
    const noResponse = icTaskStatusLabel({ status: 'running', pollFailed: true });
    expect(running).not.toBe(noResponse);
    expect(running).toBe(IC_LABEL_RUNNING);
    expect(noResponse).toBe(IC_LABEL_NO_RESPONSE);
  });

  it('② 🔴 後端無回應時**不得**沿用過期的 status 顯示成執行中', () => {
    // 手上那個 status 是上一次成功輪詢的快照；後端已無回應時它是過期的
    expect(icTaskStatusLabel({ status: 'running', pollFailed: true })).toBe(IC_LABEL_NO_RESPONSE);
    expect(icTaskStatusLabel({ status: 'pending', pollFailed: true })).toBe(IC_LABEL_NO_RESPONSE);
  });

  it('③ 尚未開始 ⇒ 第三種字串，與前兩者皆不同', () => {
    const idle = icTaskStatusLabel({ status: null });
    expect(idle).toBe(IC_LABEL_IDLE);
    expect(new Set([idle, IC_LABEL_RUNNING, IC_LABEL_NO_RESPONSE]).size).toBe(3);
  });

  it('④ 階段為可擴充集合：未知階段原樣附上，不映射成「其他」', () => {
    const label = icTaskStatusLabel({ status: 'running', currentStage: 'gap6_chunked_stage_42' });
    expect(label).toContain(IC_LABEL_RUNNING);
    expect(label).toContain('gap6_chunked_stage_42');
    // 終態原樣顯示，不另造詞
    expect(icTaskStatusLabel({ status: 'completed' })).toBe('completed');
  });

  it('⑤ 特徵數未知時明說不知道，**不填假數字**', () => {
    expect(icFeatureCountLabel(218369)).toContain('218369');
    expect(icFeatureCountLabel(null)).toBe('特徵數未知');
    expect(icFeatureCountLabel(undefined)).toBe('特徵數未知');
    // 🔴 0 是合法的特徵數，不得被當成「未知」
    expect(icFeatureCountLabel(0)).toContain('0');
  });
});
