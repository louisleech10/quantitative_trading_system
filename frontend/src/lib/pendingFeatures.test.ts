/**
 * 前端占位頁 ↔ registry 防漂移（不做第二份真相源）：
 * 每個 registryId 須存在於 docs/IC_QUANT_GAP_REGISTRY.md，且其列之「為何現在不做」三值與本檔 kind 一致；
 * GAP-3 章節以標題存在為準。殘留收掉／改理由而本檔沒改 ⇒ 紅。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { PENDING_FEATURES, findPendingFeature } from '@/lib/pendingFeatures';

const REGISTRY = readFileSync(resolve(__dirname, '../../../docs/IC_QUANT_GAP_REGISTRY.md'), 'utf-8');

describe('pendingFeatures ↔ registry', () => {
  it('每個 registryId 存在於 registry（表列或章節標題）', () => {
    for (const f of PENDING_FEATURES) {
      const rowRe = new RegExp(`^\\| ${f.registryId.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')} \\|`, 'm');
      const headingRe = new RegExp(`^## ${f.registryId.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&')}`, 'm');
      expect(rowRe.test(REGISTRY) || headingRe.test(REGISTRY), `${f.registryId} 不在 registry`).toBe(true);
    }
  });

  it('三值理由與 registry 該列一致（表列者）', () => {
    for (const f of PENDING_FEATURES) {
      const line = REGISTRY.split('\n').find((l) => l.startsWith(`| ${f.registryId} |`));
      if (!line) continue; // 章節型（GAP-3）無列
      const cells = line.split('|').map((c) => c.trim());
      const why = cells[3] ?? '';
      expect(why.includes(f.kind), `${f.registryId} 三值不一致：registry=「${why.slice(0, 40)}…」 page=${f.kind}`).toBe(true);
    }
  });

  it('無重複 ID；findPendingFeature 對未知 ID 回 undefined', () => {
    const ids = PENDING_FEATURES.map((f) => f.registryId);
    expect(new Set(ids).size).toBe(ids.length);
    expect(findPendingFeature('NOPE-R0')).toBeUndefined();
    expect(findPendingFeature('G1-R3')?.kind).toBe('user-ruling');
  });

  it('殼放置點：優化結果頁掛 G1-R3、XGBoost 頁掛 G2-R1', () => {
    const opt = readFileSync(resolve(__dirname, '../app/optimization-execution/result/[taskId]/page.tsx'), 'utf-8');
    const xgb = readFileSync(resolve(__dirname, '../app/patterns/xgboost-analysis/page.tsx'), 'utf-8');
    expect(opt).toContain('<PendingFeatureCard registryId="G1-R3" />');
    expect(xgb).toContain('<PendingFeatureCard registryId="G2-R1" />');
    const nav = readFileSync(resolve(__dirname, '../components/layout/MainLayout.tsx'), 'utf-8');
    expect(nav).toContain("href: '/pending-features'");
  });
});
