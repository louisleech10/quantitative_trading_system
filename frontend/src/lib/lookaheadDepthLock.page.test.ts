/**
 * GAP-3 UX Task 2.1b — page 之**接線**檢查（不是行為檢查）。
 *
 * 分工（R3 重寫、B7 改形後）：
 *  - **行為**由 `lookaheadDepthLock.test.ts` 驗——它測 page 實際呼叫的
 *    `withExportLowerBoundGuard`，用 `proceed` 呼叫次數證明「未就緒 ⇒ 網路動作不發生」。
 *  - **執行期**由 `eventExportGuardRuntime.test.tsx` 驗（`A-021` 驗收⑤）——真的 render `/search`、
 *    真的按匯出鍵，數 `buildEventContractRecords` 的呼叫次數。
 *  - **本檔只驗一件事**：`page.tsx` 真的把整段匯出**委派**給那個守衛，而不是自己另寫一份。
 *
 * 🔴 為什麼上一版不夠（R3 三條）：舊版用「第一個命中之位移」與「子樹裡任一個 return」當判準
 *    ⇒ 誘餌守衛放開頭、巢狀 `(() => { return; })()`、把真守衛移到 `await` 之後、
 *      把 `disabled` 綁到別的 `<select>` 之 `<option>`——四種壞法都能讓它全綠。
 *    現版改為**結構包含關係**：整段匯出被包進 `proceed`，
 *    所以「阻擋早於網路動作」不再靠先後位移判斷，而是靠「所有 await 都在 proceed 之內」。
 */
import fs from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { describe, expect, it } from 'vitest';

const PAGE = path.resolve(__dirname, '../app/search/page.tsx');
const GUARD_FN = 'withExportLowerBoundGuard';
const EXPORT_FN = 'exportSearchResultsToEventJson';

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

/** 取 guard 呼叫之**第二**引數（deps 物件字面）中 `proceed` 的值節點（`A-021(c)` 改簽章後）。 */
function proceedArg(call: ts.CallExpression): ts.Node {
  const deps = call.arguments[1];
  if (!deps || !ts.isObjectLiteralExpression(deps)) throw new Error('guard 之第二引數不是物件字面');
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

  it('② 守衛之引數逐字為 (lowerBoundState, {notify, proceed})——`A-021(c)` 之新簽章', () => {
    const handler = exportHandler(parsePage());
    const call = (collect(handler, isGuardCall) as ts.CallExpression[])[0];
    // 🔴 恰兩個引數：舊簽章之 `selectedBars` 已刪（4.1 後那個比較恆真＝死碼）。
    //    只驗第一個引數的話，多傳一個殘留參數也會綠。
    expect(call.arguments.length).toBe(2);
    expect(call.arguments[0].getText()).toBe('lowerBoundState');
    const deps = call.arguments[1] as ts.ObjectLiteralExpression;
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

  it('④ 主答案窗之 <select> 已不存在（Task 4.1 ②：匯出端不再讓使用者選 h）', () => {
    // 🔴 改形前這裡驗的是「該 select 之 <option disabled> 綁對判定函式」。4.1 移除主答案窗後
    //    那個 select 本身不該存在 ⇒ 判準改為**不存在**（SPEC Task 4.1 驗收③之 AST 側）。
    //    執行期側（真的 render、真的按）由 A-021 驗收⑤之 page runtime 測試承擔。
    const source = parsePage();
    const selects = collect(source, (n) => {
      if (!ts.isJsxOpeningElement(n) && !ts.isJsxSelfClosingElement(n)) return false;
      return (n as ts.JsxOpeningElement).attributes.properties.some((attr) => {
        if (!ts.isJsxAttribute(attr) || attr.name.getText() !== 'data-testid') return false;
        const init = attr.initializer;
        return !!init && ts.isStringLiteral(init) && init.text === 'export-gap3-horizon';
      });
    });
    expect(selects.length, '主答案窗 select 應已移除').toBe(0);
  });
});
