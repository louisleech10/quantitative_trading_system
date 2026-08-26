/**
 * GAP-3 UX Task 1.3 之前端驗收（`npx vitest run canonicalSourceCoverage`）。
 *
 * SPEC L1495–1497 之 ①②③ ＋ ④(a)(b)(c)。判準字面之唯一來源＝SPEC Task 1.3「驗證」欄。
 *
 * 🔴 golden（`__fixtures__/canonicalSourceGolden.json`）由**後端** §G S-9 參考實作生成
 *    （`tests/api/test_gap3_source_digest.py`）。後端序列化被改壞（例：改回五欄子集）時
 *    golden 之四個 variant digest 會塌陷 ⇒ 本檔 ①②③ 同時轉紅。
 * 🔴 本檔之 selector 為 `canonicalSourceCoverage`，不得與 Task 1.9 之 `gap3_horizon_declaration` 混用。
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import ts from 'typescript';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import golden from './__fixtures__/canonicalSourceGolden.json';
import cryptoExportsGolden from './__fixtures__/node_crypto_exports.golden.json';
import cryptoReviewManifest from './__fixtures__/node_crypto_review_manifest.json';
import { buildEventContractRecords } from './eventExport';
import { EVENT_ID_TEMPLATE, canonicalEventId } from './eventId';
import { hashEntryCalls, resetHashEntryCalls } from '../test/hashEntrySpy';
import type { CaseData } from './types';

// ④(a) node:crypto 側之封閉枚舉：createHash／hash／Hash／webcrypto 皆包成計數 passthrough。
// （ESM 命名空間唯讀 ⇒ 必須用 hoisted vi.mock，不能在 setupFiles 就地改寫。）
vi.mock('node:crypto', async (importOriginal) => {
  const m = await importOriginal<typeof import('node:crypto')>();
  const record = (entry: string) => {
    (globalThis as { __hashEntryCalls?: { entry: string; input: string }[] }).__hashEntryCalls ??= [];
    (globalThis as { __hashEntryCalls: { entry: string; input: string }[] }).__hashEntryCalls.push({ entry, input: '' });
  };
  return {
    ...m,
    createHash: (...a: Parameters<typeof m.createHash>) => { record('node:crypto.createHash'); return m.createHash(...a); },
    hash: (...a: Parameters<typeof m.hash>) => { record('node:crypto.hash'); return m.hash(...a); },
    Hash: new Proxy(m.Hash, { construct: (t, a: unknown[]) => { record('node:crypto.Hash'); return Reflect.construct(t, a); } }),
    webcrypto: m.webcrypto,
  };
});

const RULE_CONDITIONS = [{ parameter: 'price_change', operator: '>=', value: 0.05 }];
const SRC_ROOT = path.resolve(__dirname, '..');

type Variant = { cases: Record<string, unknown>[]; source_file_text: string; source_file_digest: string };
const variants = golden.variants as unknown as Record<string, Variant>;

async function exportOf(name: string) {
  const v = variants[name];
  return buildEventContractRecords(v.cases as unknown as CaseData[], {
    timeframe: '12h',
    conditions: RULE_CONDITIONS,
    priceChangeMethod: 'close_to_close',
    // Task 4.1 ③／R1 `CODEX-R1-P1-02`：深度宣告 map 為必填（缺該列 tf 之鍵會拋錯）
    lookaheadBarsDeclared: { '12h': 0 },
    sourceFileText: v.source_file_text,
    sourceFileDigest: v.source_file_digest,
  });
}

beforeEach(() => resetHashEntryCalls());

describe('canonicalSourceCoverage — digest 綁完整 CaseData 列', () => {
  it('① 刪除一個 future_* 欄 ⇒ digest 改變（且匯出檔帶的就是後端那一個）', async () => {
    const base = await exportOf('base');
    const deleted = await exportOf('deleted');
    expect(deleted.source_file_digest).not.toBe(base.source_file_digest);
    expect(base.source_file_digest).toBe(variants.base.source_file_digest);
    expect(deleted.source_file_digest).toBe(variants.deleted.source_file_digest);
    expect(base.records.every((r) => r.source_file_digest === variants.base.source_file_digest)).toBe(true);
  });

  it('② 改名一個 future_* 欄 ⇒ digest 改變', async () => {
    const base = await exportOf('base');
    const renamed = await exportOf('renamed');
    expect(renamed.source_file_digest).not.toBe(base.source_file_digest);
    expect(renamed.source_file_digest).toBe(variants.renamed.source_file_digest);
  });

  it('③ 改值一個 future_* 欄之數值 ⇒ digest 改變', async () => {
    const base = await exportOf('base');
    const changed = await exportOf('changed');
    expect(changed.source_file_digest).not.toBe(base.source_file_digest);
    expect(changed.source_file_digest).toBe(variants.changed.source_file_digest);
  });

  it('①②③ 之前提：四個 variant 之 digest 兩兩相異（塌陷即代表覆蓋面不完整）', () => {
    const ds = ['base', 'deleted', 'renamed', 'changed'].map((k) => variants[k].source_file_digest);
    expect(new Set(ds).size).toBe(ds.length);
  });
});

describe('canonicalSourceCoverage — ④(a) 前端不得自算 digest（執行期）', () => {
  it('跑完整匯出流程後，與 source_file_digest 相關之雜湊呼叫數 == 0（rule_digest 另計）', async () => {
    const out = await exportOf('base');
    const calls = hashEntryCalls();
    const ruleSummary = JSON.stringify({ conditions: RULE_CONDITIONS, price_change_method: 'close_to_close', timeframe: '12h' });
    // 唯一被雜湊的輸入就是規則摘要；來源文字一次都沒進過任何雜湊入口。
    expect(calls.map((c) => c.input)).toEqual([ruleSummary]);
    expect(calls.filter((c) => c.input !== ruleSummary)).toHaveLength(0);
    expect(calls.filter((c) => c.input === out.source_file_text)).toHaveLength(0);
    expect(out.records[0].label_definition.canonical_digest).toHaveLength(64);
  });

  it('後端未提供 digest ⇒ fail-closed 拋錯，不退回前端自算', async () => {
    const v = variants.base;
    await expect(buildEventContractRecords(v.cases as unknown as CaseData[], {
      timeframe: '12h', conditions: [], priceChangeMethod: 'x', sourceFileText: '', sourceFileDigest: '',
      lookaheadBarsDeclared: { '12h': 0 },
    })).rejects.toThrow(/後端/);
    expect(hashEntryCalls().filter((c) => c.input === v.source_file_text)).toHaveLength(0);
  });
});

describe('canonicalSourceCoverage — ④(b) 前端不得自算 digest（AST 靜態）', () => {
  const HASH_MODULES = new Set(['crypto', 'node:crypto']);
  const HASH_MEMBERS = new Set(['createHash', 'createHmac', 'webcrypto']);

  function walkFiles(dir: string, out: string[] = []): string[] {
    for (const name of readdirSync(dir)) {
      const p = path.join(dir, name);
      if (statSync(p).isDirectory()) walkFiles(p, out);
      else if (/\.(ts|tsx)$/.test(name)) out.push(p);
    }
    return out;
  }

  function analyse(file: string) {
    const sf = ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
    let hashEntry = false;
    let writesSourceFileDigest = false;
    const visit = (node: ts.Node) => {
      if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)
          && HASH_MODULES.has(node.moduleSpecifier.text)) hashEntry = true;
      if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword
          && node.arguments[0] && ts.isStringLiteral(node.arguments[0])
          && HASH_MODULES.has(node.arguments[0].text)) hashEntry = true;
      if (ts.isPropertyAccessExpression(node)) {
        const name = node.name.text;
        if (HASH_MEMBERS.has(name)) hashEntry = true;
        if (name === 'digest' && ts.isPropertyAccessExpression(node.expression)
            && node.expression.name.text === 'subtle') hashEntry = true;
        if (name === 'subtle') hashEntry = true;
      }
      // 「寫入」＝以 source_file_digest 為鍵建物件，或指派到 .source_file_digest
      if ((ts.isPropertyAssignment(node) || ts.isShorthandPropertyAssignment(node))
          && node.name && ts.isIdentifier(node.name) && node.name.text === 'source_file_digest') writesSourceFileDigest = true;
      if (ts.isBinaryExpression(node) && node.operatorToken.kind === ts.SyntaxKind.EqualsToken
          && ts.isPropertyAccessExpression(node.left) && node.left.name.text === 'source_file_digest') writesSourceFileDigest = true;
      ts.forEachChild(node, visit);
    };
    visit(sf);
    return { hashEntry, writesSourceFileDigest };
  }

  it('frontend/src/** 中無任何模組同時碰雜湊入口且寫入 source_file_digest', () => {
    const offenders = walkFiles(SRC_ROOT)
      .map((f) => ({ f, ...analyse(f) }))
      .filter((r) => r.hashEntry && r.writesSourceFileDigest)
      .map((r) => path.relative(SRC_ROOT, r.f));
    expect(offenders).toEqual([]);
  });

  it('本閘有鑑別力：eventExport 寫 digest 但不碰雜湊入口；ruleDigest 碰雜湊入口但不寫 digest', () => {
    const ev = analyse(path.join(SRC_ROOT, 'lib', 'eventExport.ts'));
    const rd = analyse(path.join(SRC_ROOT, 'lib', 'ruleDigest.ts'));
    expect(ev).toEqual({ hashEntry: false, writesSourceFileDigest: true });
    expect(rd).toEqual({ hashEntry: true, writesSourceFileDigest: false });
  });
});

describe('canonicalSourceCoverage — (b)(c) 位元組相等與浮點邊界', () => {
  it('(b) 匯出取得之 source_file_text 之 sha256 逐位元組等於後端 digest', async () => {
    const out = await exportOf('base');
    expect(out.source_file_text).toBe(variants.base.source_file_text);
    expect(createHash('sha256').update(out.source_file_text, 'utf8').digest('hex')).toBe(out.source_file_digest);
    expect(out.source_file_text.endsWith('\n')).toBe(false);
  });

  it('(c) 含 -0.0／極大極小浮點之 fixture ⇒ (b) 仍成立', async () => {
    const out = await exportOf('floats');
    expect(out.source_file_text).toContain('-0.0');
    expect(out.source_file_text).toContain('5e-324');
    expect(createHash('sha256').update(out.source_file_text, 'utf8').digest('hex')).toBe(variants.floats.source_file_digest);
  });

  it('(b) 之獨立 oracle：收到的 text 本身須符合 §G S-9 之可觀察規則（不是只跟自己對得起來）', async () => {
    // 🔴 前端不准自算 digest ⇒ 它沒有第二個實作可以比。唯一能獨立檢查的，
    //    是「後端給的這串 bytes 是否還長得像 S-9」。少了本條，後端換成
    //    `json.dumps` 預設參數時前端完全看不見（mutation 1.3-M3b 實跑抓到）。
    const out = await exportOf('floats');
    expect(out.source_file_text).toContain('多頭é');                 // ensure_ascii=False：非 ASCII 字面輸出
    expect(out.source_file_text).not.toMatch(/\\u[0-9a-fA-F]{4}/);   // 不得 \u 脫逃
    expect(out.source_file_text).not.toContain('", "');              // separators=(',',':')：無空白
    expect(out.source_file_text).not.toContain('": "');
    expect(out.source_file_text.endsWith('\n')).toBe(false);          // S-9 第 5 條：禁尾端 newline
    expect(out.source_file_text).not.toContain('NaN');                // allow_nan=False：非有限值一律 null
  });
});

describe('canonicalSourceCoverage — D-2 event_id 之唯一定義來源（CODEX-R1-P1-01）', () => {
  const CONTRACT = path.resolve(SRC_ROOT, '../../momentum/Analysis/contracts/event_import_contract.json');

  it('前端模板與契約 `event_id_template` **逐字**相等（改任一側即紅）', () => {
    const contract = JSON.parse(readFileSync(CONTRACT, 'utf8'));
    expect(EVENT_ID_TEMPLATE).toBe(contract.event_id_template);
  });

  it('匯出之 event_id 由共用定義來源產生，且不在 eventExport.ts 內手寫第二份公式', async () => {
    const out = await exportOf('base');
    const v = variants.base;
    out.records.forEach((r, i) => {
      const c = v.cases[i] as { symbol: string; timeframe: string };
      expect(r.event_id).toBe(canonicalEventId(c.symbol, c.timeframe, r.t0));
    });
    // 錨點落在「有沒有第二份公式」這件事本身：模板字面不得出現在呼叫端模組
    const exportSrc = readFileSync(path.join(SRC_ROOT, 'lib', 'eventExport.ts'), 'utf8');
    expect(exportSrc).not.toMatch(/`\$\{[^`]*\}:\$\{[^`]*\}:\$\{[^`]*\}`/);
    expect(exportSrc).toContain('canonicalEventId(');
  });
});

describe('canonicalSourceCoverage — ④(a) ii：node:crypto 匯出面之 golden × 複審 manifest', () => {
  it('ii-a 現行匯出面逐字等於 golden（Node 雜湊面變動時有人會看到）', async () => {
    const m = await vi.importActual<typeof import('node:crypto')>('node:crypto');
    expect(Object.getOwnPropertyNames(m).sort()).toEqual(cryptoExportsGolden.exports);
  });

  it('ii-b golden 與複審 manifest 雙向封閉集合相等（缺 receipt 即紅）', () => {
    const reconstructed = new Set<string>();
    for (const e of cryptoReviewManifest.entries) {
      for (const n of e.added) reconstructed.add(n);
      for (const n of e.removed) reconstructed.delete(n);
    }
    const goldenSet = new Set(cryptoExportsGolden.exports);
    const inGoldenNotManifest = [...goldenSet].filter((n) => !reconstructed.has(n)).sort();
    const inManifestNotGolden = [...reconstructed].filter((n) => !goldenSet.has(n)).sort();
    expect({ inGoldenNotManifest, inManifestNotGolden }).toEqual({ inGoldenNotManifest: [], inManifestNotGolden: [] });
    expect(cryptoReviewManifest.entries.every((e) => e.reviewer && e.reviewed_at && e.commit_context)).toBe(true);
  });

  it('ii-c stub 清單維持顯式枚舉，且**不自稱窮舉**（純 JS 手刻 sha256 為具名殘留）', () => {
    const enumerated = ['crypto.subtle.digest', 'node:crypto.createHash', 'node:crypto.hash', 'node:crypto.Hash', 'node:crypto.webcrypto'];
    expect(new Set(enumerated).size).toBe(5);
    const spy = readFileSync(path.join(SRC_ROOT, 'test', 'hashEntrySpy.ts'), 'utf8');
    expect(spy).toContain('不得宣稱已解決');
  });
});
