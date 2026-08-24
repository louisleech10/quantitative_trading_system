/**
 * GAP-3 UX Task 2.1b — page 之**接線**檢查（不是行為檢查）。
 *
 * 分工（R3 重寫後）：
 *  - **行為**由 `lookaheadDepthLock.test.ts` 驗——它測 page 實際呼叫的
 *    `withHorizonLowerBoundGuard`，用 `proceed` 呼叫次數證明「未達下界 ⇒ 網路動作不發生」。
 *  - **本檔只驗一件事**：`page.tsx` 真的把整段匯出**委派**給那個守衛，而不是自己另寫一份。
 *
 * 🔴 為什麼上一版不夠（R3 三條）：舊版用「第一個命中之位移」與「子樹裡任一個 return」當判準
 *    ⇒ 誘餌守衛（`if (isHorizonBelowLowerBound(999,1)) return;` 放開頭）、
 *      巢狀 `(() => { return; })()`、把真守衛移到 `await` 之後、
 *      把 `disabled` 綁到別的 `<select>` 之 `<option>`——四種壞法都能讓它全綠。
 *    現版改為**結構包含關係**：整段匯出被包進 `proceed`，
 *    所以「阻擋早於網路動作」不再靠先後位移判斷，而是靠「所有 await 都在 proceed 之內」。
 */
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const PAGE = path.resolve(__dirname, '../app/search/page.tsx');
const GUARD_FN = 'withHorizonLowerBoundGuard';
const PREDICATE_FN = 'isHorizonBelowLowerBound';
const EXPORT_FN = 'exportSearchResultsToEventJson';
const HORIZON_SELECT_TESTID = 'export-gap3-horizon';

function parsePage(): ts.SourceFile {
  const text = fs.readFileSync(PAGE, 'utf8');
  return ts.createSourceFile(PAGE, text, ts.ScriptTarget.ESNext, true, ts.ScriptKind.TSX);
}

function findNode(root: ts.Node, predicate: (n: ts.Node) => boolean): ts.Node | undefined {
  let found: ts.Node | undefined;
  const visit = (n: ts.Node): void => {
    if (found) return;
    if (predicate(n)) {
      found = n;
      return;
    }
    ts.forEachChild(n, visit);
  };
  visit(root);
  return found;
}

function collect(root: ts.Node, predicate: (n: ts.Node) => boolean): ts.Node[] {
  const out: ts.Node[] = [];
  const visit = (n: ts.Node): void => {
    if (predicate(n)) out.push(n);
    ts.forEachChild(n, visit);
  };
  visit(root);
  return out;
}

function exportHandler(source: ts.SourceFile): ts.Node {
  const decl = findNode(
    source,
    (n) =>
      ts.isVariableDeclaration(n) &&
      ts.isIdentifier(n.name) &&
      n.name.text === EXPORT_FN &&
      !!n.initializer,
  ) as ts.VariableDeclaration | undefined;
  if (!decl?.initializer) throw new Error(`找不到 ${EXPORT_FN}（字面錨點失效，不是通過）`);
  return decl.initializer;
}

const isGuardCall = (n: ts.Node): n is ts.CallExpression =>
  ts.isCallExpression(n) && ts.isIdentifier(n.expression) && n.expression.text === GUARD_FN;

/** 取 guard 呼叫之第三引數（deps 物件字面）中 `proceed` 的值節點。 */
function proceedArg(call: ts.CallExpression): ts.Node {
  const deps = call.arguments[2];
  if (!deps || !ts.isObjectLiteralExpression(deps)) throw new Error('guard 之第三引數不是物件字面');
  const prop = deps.properties.find(
    (p) => ts.isPropertyAssignment(p) && p.name.getText() === 'proceed',
  ) as ts.PropertyAssignment | undefined;
  if (!prop) throw new Error('deps 缺 proceed');
  return prop.initializer;
}

describe('gap3 lookahead depth lock — search/page.tsx 接線', () => {
  it('① 匯出處理器把工作委派給守衛，且**恰一處**（誘餌會被這條抓到）', () => {
    const handler = exportHandler(parsePage());
    const calls = collect(handler, isGuardCall) as ts.CallExpression[];
    expect(calls.length).toBe(1);
  });

  it('② 守衛之引數逐字為 (eventHorizonBars, lookaheadLowerBound, {notify, proceed})', () => {
    const handler = exportHandler(parsePage());
    const call = (collect(handler, isGuardCall) as ts.CallExpression[])[0];
    expect(call.arguments.slice(0, 2).map((a) => a.getText())).toEqual([
      'eventHorizonBars',
      'lookaheadLowerBound',
    ]);
    const deps = call.arguments[2] as ts.ObjectLiteralExpression;
    expect(deps.properties.map((p) => p.name?.getText()).sort()).toEqual(['notify', 'proceed']);
  });

  it('③ 該函式內**每一個** await 都落在 proceed 之內（阻擋早於網路動作＝結構保證）', () => {
    const handler = exportHandler(parsePage());
    const call = (collect(handler, isGuardCall) as ts.CallExpression[])[0];
    const proceed = proceedArg(call);
    const [pStart, pEnd] = [proceed.getStart(), proceed.getEnd()];

    const awaits = collect(handler, (n) => ts.isAwaitExpression(n));
    expect(awaits.length).toBeGreaterThan(0); // 該函式本來就有 await；沒有代表錨點抓錯
    for (const a of awaits) {
      expect(a.getStart()).toBeGreaterThanOrEqual(pStart);
      expect(a.getEnd()).toBeLessThanOrEqual(pEnd);
    }
  });

  it('④ 答案窗那個 <select> 之 <option disabled> 由同一判定函式綁定（錨定到該 select，不是任一 select）', () => {
    // 🔴 CODEX-R3-P2-01：舊版掃全檔之 <option>，把同形綁定搬到別的選單也會綠。
    // 🔴 GROK-R4-P2-01：舊版用 `getText().includes(testid)` ＋ `findNode` 第一命中
    //    ⇒ 在真 select **之前**插一個 testid **含該子字串**的誘餌 select（綁定正確），
    //      再把真 select 的綁定改壞，四條仍全綠。子字串＋第一命中＝兩個代理物疊在一起。
    //    改為 **exact 比對 testid**，且斷言符合者**恰一個**（誘餌會被這條抓到）。
    const source = parsePage();
    const selects = collect(source, (n) => {
      if (!ts.isJsxOpeningElement(n) && !ts.isJsxSelfClosingElement(n)) return false;
      if ((n as ts.JsxOpeningElement).tagName.getText() !== 'select') return false;
      return (n as ts.JsxOpeningElement).attributes.properties.some((attr) => {
        if (!ts.isJsxAttribute(attr) || attr.name.getText() !== 'data-testid') return false;
        const init = attr.initializer;
        if (!init || !ts.isStringLiteral(init)) return false;
        return init.text === HORIZON_SELECT_TESTID; // exact，不是 includes
      });
    });
    expect(
      selects.length,
      `data-testid 恰等於 ${HORIZON_SELECT_TESTID} 之 select 須恰一個`,
    ).toBe(1);

    // 該 select 元素（含子樹）＝其 JsxElement 父節點
    const element = selects[0].parent;
    const bindings = collect(element, (n) => {
      if (!ts.isJsxAttribute(n) || n.name.getText() !== 'disabled') return false;
      const owner = n.parent.parent;
      const tag =
        ts.isJsxOpeningElement(owner) || ts.isJsxSelfClosingElement(owner)
          ? owner.tagName.getText()
          : '';
      if (tag !== 'option') return false;
      return (
        !!n.initializer &&
        ts.isJsxExpression(n.initializer) &&
        !!n.initializer.expression &&
        ts.isCallExpression(n.initializer.expression) &&
        ts.isIdentifier(n.initializer.expression.expression) &&
        n.initializer.expression.expression.text === PREDICATE_FN
      );
    }) as ts.JsxAttribute[];

    expect(bindings.length).toBe(1);
    const call = (bindings[0].initializer as ts.JsxExpression).expression as ts.CallExpression;
    expect(call.arguments.map((a) => a.getText())).toEqual(['h', 'lookaheadLowerBound']);
  });
});
