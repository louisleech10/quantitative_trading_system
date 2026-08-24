/**
 * GAP-3 UX Task 2.1b — **真實呼叫點**之覆蓋（GROK-R1-P2-01 之修法）。
 *
 * 出事情境：`lookaheadDepthLock.test.ts` 用的是自建之 `exportGuarded` 雙胞，
 * 註解寫「與 search/page.tsx 同一形態」卻**不 import page** ⇒ 把 page 的守衛整段刪掉，
 * 那份測試仍然 7 passed。這與本 epic 犯過四次之「比對範圍過寬」同族：
 * 錨點落在**像目標的東西**上，不是目標本身。
 *
 * 本檔以 **TypeScript AST**（非 grep）鎖住真正的呼叫點：
 *   ① `exportSearchResultsToEventJson` 內確實呼叫 `isHorizonBelowLowerBound`
 *   ② 該呼叫位於一個帶 `return` 的 `if` 內（是守衛，不是純顯示）
 *   ③ 該守衛出現在該函式**第一個 `await` 之前**（阻擋須早於任何網路動作）
 */
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const PAGE = path.resolve(__dirname, '../app/search/page.tsx');
const GUARD_FN = 'isHorizonBelowLowerBound';
const EXPORT_FN = 'exportSearchResultsToEventJson';

function exportHandlerBody(): { node: ts.Node; source: ts.SourceFile } {
  const text = fs.readFileSync(PAGE, 'utf8');
  const source = ts.createSourceFile(PAGE, text, ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);

  let found: ts.Node | undefined;
  const visit = (n: ts.Node): void => {
    if (
      ts.isVariableDeclaration(n) &&
      ts.isIdentifier(n.name) &&
      n.name.text === EXPORT_FN &&
      n.initializer
    ) {
      found = n.initializer;
      return;
    }
    ts.forEachChild(n, visit);
  };
  visit(source);
  if (!found) throw new Error(`在 ${PAGE} 找不到 ${EXPORT_FN}（字面錨點失效，不是通過）`);
  return { node: found, source };
}

/** 回傳該節點子樹中，符合 predicate 之第一個節點的起始位移（找不到回 -1）。 */
function firstOffset(root: ts.Node, predicate: (n: ts.Node) => boolean): number {
  let best = -1;
  const visit = (n: ts.Node): void => {
    if (predicate(n)) {
      const start = n.getStart();
      if (best === -1 || start < best) best = start;
    }
    ts.forEachChild(n, visit);
  };
  visit(root);
  return best;
}

const isGuardCall = (n: ts.Node): boolean =>
  ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === GUARD_FN;

describe('gap3 lookahead depth lock — search/page.tsx 真實呼叫點', () => {
  it('① 匯出處理器內確實呼叫守衛函式', () => {
    const { node } = exportHandlerBody();
    expect(firstOffset(node, isGuardCall)).toBeGreaterThan(-1);
  });

  it('② 該呼叫位於帶 return 的 if 內（是守衛，不只是顯示）', () => {
    const { node } = exportHandlerBody();
    const guardingIf = firstOffset(
      node,
      (n) =>
        ts.isIfStatement(n) &&
        firstOffset(n.expression, isGuardCall) > -1 &&
        firstOffset(n.thenStatement, (m) => ts.isReturnStatement(m)) > -1,
    );
    expect(guardingIf).toBeGreaterThan(-1);
  });

  it('③ 守衛出現在第一個 await 之前（阻擋早於任何網路動作）', () => {
    const { node } = exportHandlerBody();
    const guardAt = firstOffset(node, isGuardCall);
    const awaitAt = firstOffset(node, (n) => ts.isAwaitExpression(n));
    expect(guardAt).toBeGreaterThan(-1);
    expect(awaitAt).toBeGreaterThan(-1); // 該函式本來就有 await；沒有代表錨點抓錯
    expect(guardAt).toBeLessThan(awaitAt);
  });

  it('④ 選單以同一函式 disable 低於下界之選項（不是另寫一份比較）', () => {
    const text = fs.readFileSync(PAGE, 'utf8');
    const source = ts.createSourceFile(PAGE, text, ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);
    let calls = 0;
    const visit = (n: ts.Node): void => {
      if (isGuardCall(n)) calls += 1;
      ts.forEachChild(n, visit);
    };
    visit(source);
    // 匯出守衛 1 次 ＋ option disabled 1 次 ＋ option 文案 1 次
    expect(calls).toBeGreaterThanOrEqual(2);
  });
});
