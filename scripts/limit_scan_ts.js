#!/usr/bin/env node
// 上限盤點掃描器之 TS／TSX 子程序（ICPERF SPEC v5.85 Task 0.6 (b)）：以 TypeScript 編譯器 API 語法解析，
// 輸出數字字面量候選。用法：node scripts/limit_scan_ts.js <檔>...；stdout 為 JSON {"rows": [...], "errors": [...]}。
// 只列上限語境之數字（切片引數、JSX 上下界屬性、名稱帶上限語意之屬性／變數／參數／解構預設、以呼叫包裝之具名初值
// 〔useState(10)〕、比較式、Math.min／max）；檔內數字常數於上述語境之使用處追一層（`const N=50; xs.slice(0,N)`）；
// 行內無數字而一側帶上限語意名稱之比較式與切片引數列為具名候選（value 為 null）。
// 樣式與一般運算之數字不列。0 一律不列；1、-1 不列，但切片引數列入（含 ±1）。
"use strict";
const path = require("path");
const fs = require("fs");

const tsPath = path.join(__dirname, "..", "frontend", "node_modules", "typescript");
const ts = require(tsPath);
const SLICE_CALLS = new Set(["slice", "substring", "splice", "substr"]);
const JSX_BOUND_ATTRS = new Set(["max", "min", "step", "maxLength", "minLength"]);
// 上限語意名稱（不分大小寫）：與 Python／YAML／JSON 掃描共用同一字面（scripts/limit_scan.py LIMIT_NAME_PATTERN）。
const LIMIT_NAME = new RegExp(process.env.LIMIT_NAME_PATTERN
  || "(limit|max|min|top|cap|budget|timeout|window|period|horizon|lag|sample|threshold|depth|paths|perm|bootstrap|"
   + "count|rows|cols|batch|chunk|worker|retr|ttl|quantile|bins|alpha|pct|ratio|frac|size|len|n_)", "i");
const COMPARE_OPS = new Set([ts.SyntaxKind.LessThanToken, ts.SyntaxKind.LessThanEqualsToken,
  ts.SyntaxKind.GreaterThanToken, ts.SyntaxKind.GreaterThanEqualsToken]);

function numericValue(node) {
  return Number(node.text.replace(/_/g, ""));
}

function scanFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const kind = file.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, kind);
  if (sf.parseDiagnostics && sf.parseDiagnostics.length > 0) {
    const d = sf.parseDiagnostics[0];
    return { rows: [], error: ts.flattenDiagnosticMessageText(d.messageText, "\n") };
  }
  const lines = text.split(/\r?\n/);
  const rows = [];
  function emit(node, value, kindName) {
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    rows.push({ file, line, kind: kindName, value, code: (lines[line - 1] || "").trim().slice(0, 200) });
  }
  function inSliceCall(node) {
    const p = node.parent;
    const call = p && ts.isPrefixUnaryExpression(p) ? p.parent : p;
    return call && ts.isCallExpression(call) && ts.isPropertyAccessExpression(call.expression)
      && SLICE_CALLS.has(call.expression.name.text);
  }
  function contextKind(node) {
    // 回候選語境（不屬上限語境者回 null）：切片引數、JSX 上下界屬性、名稱帶上限語意之屬性／變數、比較式、Math.min／max。
    if (inSliceCall(node)) return "ts_slice";
    let cur = node.parent;
    if (cur && ts.isPrefixUnaryExpression(cur)) cur = cur.parent;
    if (!cur) return null;
    if (ts.isJsxExpression(cur) && cur.parent && ts.isJsxAttribute(cur.parent)) {
      const name = cur.parent.name.getText(sf);
      return JSX_BOUND_ATTRS.has(name) || LIMIT_NAME.test(name) ? "ts_jsx_attr" : null;
    }
    if ((ts.isPropertyAssignment(cur) || ts.isVariableDeclaration(cur) || ts.isPropertyDeclaration(cur)
         || ts.isParameter(cur) || ts.isBindingElement(cur)) && cur.name && LIMIT_NAME.test(cur.name.getText(sf))) {
      return "ts_named";
    }
    // 名稱帶上限語意之綁定以呼叫包裝初值（`const [maxIterations, set…] = useState(10)`）
    if (ts.isCallExpression(cur) && cur.parent && ts.isVariableDeclaration(cur.parent) && cur.parent.initializer === cur
        && LIMIT_NAME.test(cur.parent.name.getText(sf))) {
      return "ts_named_call";
    }
    if (ts.isBinaryExpression(cur) && COMPARE_OPS.has(cur.operatorToken.kind)) return "ts_compare";
    if (ts.isCallExpression(cur) && ts.isPropertyAccessExpression(cur.expression)
        && cur.expression.expression.getText(sf) === "Math"
        && ["min", "max"].includes(cur.expression.name.text)) return "ts_minmax";
    return null;
  }
  // 檔內數字常數表（符號常數追一層）：`const N = 50` 之名稱 → 值；同名異值者視為不定、不解析。
  const consts = new Map();
  const ambiguous = new Set();
  function collect(node) {
    if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.initializer) {
      let init = node.initializer;
      let sign = 1;
      if (ts.isPrefixUnaryExpression(init) && init.operator === ts.SyntaxKind.MinusToken) { sign = -1; init = init.operand; }
      if (ts.isNumericLiteral(init)) {
        const name = node.name.text;
        const v = sign * numericValue(init);
        if (consts.has(name) && consts.get(name) !== v) ambiguous.add(name);
        consts.set(name, v);
      }
    }
    ts.forEachChild(node, collect);
  }
  collect(sf);
  function constOf(node) {
    return ts.isIdentifier(node) && consts.has(node.text) && !ambiguous.has(node.text) ? consts.get(node.text) : null;
  }
  function limitNameOf(node) {
    if (ts.isIdentifier(node) && !consts.has(node.text) && LIMIT_NAME.test(node.text)) return node.text;
    if (ts.isPropertyAccessExpression(node) && LIMIT_NAME.test(node.name.text)) return node.name.text;
    return null;
  }
  function emitNamed(node, name, kindName) {
    const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
    rows.push({ file, line, kind: kindName, value: null, name, code: (lines[line - 1] || "").trim().slice(0, 200) });
  }
  function isDeclName(node) {
    const p = node.parent;
    return p && (ts.isVariableDeclaration(p) || ts.isParameter(p) || ts.isBindingElement(p) || ts.isPropertyAssignment(p)
      || ts.isPropertyDeclaration(p) || ts.isFunctionDeclaration(p)) && p.name === node;
  }
  function visit(node) {
    if (ts.isNumericLiteral(node)) {
      let value = numericValue(node);
      const p = node.parent;
      if (p && ts.isPrefixUnaryExpression(p) && p.operator === ts.SyntaxKind.MinusToken) value = -value;
      const kindName = contextKind(node);
      if (kindName && value !== 0 && (kindName === "ts_slice" || !(value === 1 || value === -1))) {
        emit(node, value, kindName);
      }
    } else if (ts.isIdentifier(node) && !isDeclName(node) && constOf(node) !== null) {
      // 使用處之符號常數：同數字字面量之語境判定，值取常數宣告（`xs.slice(0, N)`、`<input max={N}/>`）
      const value = constOf(node);
      const kindName = contextKind(node);
      if (kindName && value !== 0
          && (kindName === "ts_slice" || !(value === 1 || value === -1))) {
        emit(node, value, kindName);
      }
    }
    if (ts.isBinaryExpression(node) && COMPARE_OPS.has(node.operatorToken.kind)) {
      // 行內無數字之上限判定點（`if (total > maxRows)`）
      const sides = [node.left, node.right];
      const numeric = (s) => ts.isNumericLiteral(s) || (ts.isPrefixUnaryExpression(s) && ts.isNumericLiteral(s.operand))
        || constOf(s) !== null;
      if (!sides.some(numeric)) {
        for (const s of sides) {
          const name = limitNameOf(s);
          if (name) emitNamed(s, name, "ts_named_compare");
        }
      }
    }
    if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)
        && SLICE_CALLS.has(node.expression.name.text)) {
      for (const a of node.arguments) {
        const name = constOf(a) === null ? limitNameOf(a) : null;
        if (name) emitNamed(a, name, "ts_named_slice");
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(sf);
  return { rows, error: null };
}

const out = { rows: [], errors: [] };
for (const file of process.argv.slice(2)) {
  try {
    const r = scanFile(file);
    if (r.error) out.errors.push({ file, error: r.error });
    else out.rows.push(...r.rows);
  } catch (e) {
    out.errors.push({ file, error: String(e && e.message || e) });
  }
}
process.stdout.write(JSON.stringify(out));
