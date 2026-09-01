/**
 * 🔴 **dev 與 build 必須走同一個打包器**（2026-09-01 使用者 UAT B12 實測踩到）。
 *
 * 出生事故：`package.json` 之 `dev` 原本是 `next dev --turbopack`、`build` 是 `next build`（webpack）。
 * 兩者對「專案根目錄**之外**的 import」判準不同——
 * `eventMetricsGlossary.ts` 依 Task 5.0 之裁定必須 build-time import
 * `momentum/Analysis/contracts/event_metrics_glossary.json`（在 repo 根、frontend 之外），
 * webpack 解得開、**turbopack 直接 `Module not found`**
 * ⇒ `npm run build` 全綠、而使用者 `npm run dev` 打開 `/ic-analysis` 是整頁 Build Error。
 *
 * 🔴 **我為什麼沒抓到**：我從頭到尾只跑 `npm run build`，從沒跑過 `npm run dev`——
 * 而驗收清單叫使用者跑的正是 `dev`。「我驗的那條路」與「使用者走的那條路」不是同一條。
 *
 * 🔴 Next 15.3.4 之 turbopack **沒有** root 選項（`turbopack.root` 與
 * `experimental.turbo.root` 兩處實跑皆得 `Unrecognized key(s) in object: 'root'`）
 * ⇒ 解法是拿掉 `--turbopack`，不是設定 root。
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const PKG = resolve(__dirname, '../../package.json');

describe('dev／build 打包器一致性', () => {
  const pkg = JSON.parse(readFileSync(PKG, 'utf8')) as { scripts: Record<string, string> };

  it('🔴 `dev` 不得用 turbopack——它解不開 frontend 之外的 import', () => {
    expect(pkg.scripts.dev).toBeDefined();
    expect(pkg.scripts.dev).not.toContain('--turbopack');
  });

  it('`dev` 與 `build` 走同一個打包器（兩者皆為預設 webpack）', () => {
    for (const key of ['dev', 'build'] as const) {
      expect(pkg.scripts[key], `${key} script`).not.toContain('--turbopack');
    }
  });

  it('正向對照：真的讀到了 scripts（打錯路徑時上面兩條會空洞地通過）', () => {
    expect(Object.keys(pkg.scripts)).toEqual(expect.arrayContaining(['dev', 'build', 'test']));
  });
});
