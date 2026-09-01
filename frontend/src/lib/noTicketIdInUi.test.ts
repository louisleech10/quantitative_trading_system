/**
 * 🔴 **施工票號不得出現在使用者看得到的地方**（`--run noTicketIdInUi`）。
 *
 * 出生事故（2026-09-02 使用者 UAT）：匯出檔名叫 `gap3_events_2026-09-01.csv`、
 * 區塊標題寫「已匯入事件批（GAP-3）」、後端拒收訊息寫「偵測到 GAP-3 新 schema」。
 * 使用者原話：「以後使用者哪知道什麼是 GAP3？」——`GAP-3` 是**我們的施工票號**，
 * 不是產品概念；它出現在畫面上就是把內部流程洩漏給使用者。
 *
 * **本閘只管使用者看得到的層**：JSX 文字、字串字面（含檔名／title／訊息）。
 * 程式碼**註解**裡的票號是刻意保留的施工追溯（`// GAP-3 UX Task 7.1：…`），
 * 它讓人查得出「這行為什麼長這樣」，且使用者永遠不會讀到 ⇒ 不在本閘範圍。
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const SRC = join(process.cwd(), 'src');

/**
 * 票號樣式：`GAP-3`／`GAP3`（**大寫**）與檔名前綴 `gap3_`。
 * 🔴 **不得加 `i` flag**：Tailwind 的 `gap-4`／`gap-2` 會全部被誤抓
 * （第一版就是這樣，掃出 25 個排版 class）。票號在本 repo 一律大寫。
 */
const TICKET = /\bGAP[-_]?\d\b|\bgap\d_/;

/**
 * 豁免——**每一條都要說得出為什麼**，不是「暫時放過」。
 * `pendingFeatures.ts`：那一頁列的就是「還沒做的開發項目」，票號是它的內容
 * （每筆另有 `registryAnchor` 指回 registry），拿掉反而查不到對應。
 */
const ALLOW = new Set(['lib/pendingFeatures.ts']);

function walk(dir: string, out: string[] = []): string[] {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) { walk(p, out); continue; }
    if (!/\.(ts|tsx)$/.test(name)) continue;
    if (/\.test\.tsx?$/.test(name)) continue;           // 測試檔不是使用者介面
    if (p.includes('__fixtures__')) continue;           // golden 基線是資料
    out.push(p);
  }
  return out;
}

/**
 * 逐行判斷「這行是不是註解」。跨行區塊註解以 `*` 起始行涵蓋（本 repo 一律如此排版）；
 * `{/* … *\/}` 是 JSX 內的註解，同樣不會被瀏覽器渲染。
 */
function isCommentLine(line: string): boolean {
  const t = line.trim();
  return t.startsWith('//') || t.startsWith('*') || t.startsWith('/*') || t.startsWith('{/*');
}

/**
 * 剝掉**行尾註解**（`x: number;   // GAP-3 UX Task 6.3`）。
 * 🔴 不能只看整行開頭：那會把行尾註解裡的票號誤報成 UI 文字。
 * 這裡刻意用最保守的判準——`//` 前若有奇數個引號就不剝（可能是字串裡的 `//`，如網址）。
 */
function stripTrailingComment(line: string): string {
  const i = line.indexOf('//');
  if (i < 0) return line;
  const before = line.slice(0, i);
  const quotes = (before.match(/['"`]/g) ?? []).length;
  return quotes % 2 === 0 ? before : line;
}

describe('使用者可見層不得出現施工票號', () => {
  it('🔴 掃 frontend/src：非註解行不得含 GAP-N', () => {
    const hits: string[] = [];
    for (const file of walk(SRC)) {
      const rel = relative(SRC, file);
      if (ALLOW.has(rel)) continue;
      const lines = readFileSync(file, 'utf8').split('\n');
      lines.forEach((line, i) => {
        if (isCommentLine(line)) return;
        if (line.includes('data-testid')) return;       // DOM 測試識別字，使用者看不到
        if (TICKET.test(stripTrailingComment(line))) hits.push(`${rel}:${i + 1}  ${line.trim().slice(0, 100)}`);
      });
    }
    expect(hits, `這些行會讓使用者看到施工票號：\n${hits.join('\n')}`).toEqual([]);
  });

  it('🔴 本閘可證偽：對一段帶票號的假 JSX 必須抓得到', () => {
    // 若把偵測寫壞（例如 regex 打錯），上一條會永遠綠 ⇒ 這條在此當對照組。
    const fake = '      <h4>已匯入事件批（GAP-3）</h4>';
    expect(isCommentLine(fake)).toBe(false);
    expect(TICKET.test(fake)).toBe(true);
    // 而註解行不得被誤抓（否則會逼人刪掉有用的施工追溯）
    expect(isCommentLine('  // GAP-3 UX Task 7.1：五個批次維度可見可改')).toBe(true);
  });
});
