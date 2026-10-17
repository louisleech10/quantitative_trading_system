/**
 * FF-NAME Task 3.3 — 前端語意解析之靜態封閉檢查（docs/FFNAME_SPEC.md Task 3.3；TODO docs/manifests/FFNAME.json）。
 *
 * 「語意解析」＝由欄名字串拆段推導 source／category／indicator／params／ops 或 layer；僅原樣顯示或子字串搜尋欄名不屬之。
 * `frontend/src`（測試檔除外）內 `featureNameParser`、`parseFeatureNameSegments`、對欄名之 `split('_')`／`split("_")`／
 * `split(/_/)`、`startsWith('ms_'|'ent_'|'tr_'|'cs_'|'meta_')`、`parts[3]` 命中 == 0（新增即紅）；
 * `featureNameParser.ts` 與 worker 刪除；顯示或篩選特徵欄名之元件一律經同一 hook 查描述 map。
 * 樣式與元件清單之單一落點：`tests/_golden/ffname/contract.json`（frontend 段）。
 * §V mutation ⑪：前端恢復自行解析欄名語意（`split('_')` 或 `ms_` 特判）⇒ 本檔必紅。
 */
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const REPO = resolve(__dirname, '../../..');
const CONTRACT = JSON.parse(readFileSync(join(REPO, 'tests/_golden/ffname/contract.json'), 'utf8')) as {
  frontend: {
    hook_module: string;
    hook_name: string;
    consumers: string[];
    deleted_files: string[];
    static_scan_root: string;
    static_forbidden: { id: string; regex: string }[];
    semantic_scan: {
      roots: string[];
      receiver_regex: string;
      string_methods: string[];
      ambiguous_methods: string[];
      collection_suffix_regex: string;
      forbid_new_regexp: boolean;
    };
  };
};
const FE = CONTRACT.frontend;
const PATTERNS = FE.static_forbidden.map((p) => ({ id: p.id, re: new RegExp(p.regex) }));
const SEM = FE.semantic_scan;
const RECEIVER_RE = new RegExp(SEM.receiver_regex, 'i');
const COLLECTION_RE = new RegExp(SEM.collection_suffix_regex);
const METHODS = [...SEM.string_methods, ...SEM.ambiguous_methods];
const CALL_RE = new RegExp(`([A-Za-z_$][\\w$]*(?:\\s*\\.\\s*[A-Za-z_$][\\w$]*)*)\\s*\\.\\s*(${METHODS.join('|')})\\s*\\(`, 'g');

const ALIAS_DECL_RE = /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*([^;\n]+)/g;
const IDENT_RE = /[A-Za-z_$][\w$]*/g;

/** 同檔單步別名（審查 r13 CODEX-R13-P1-04）：`const|let|var X = <含名稱類識別字之表達式>` ⇒ X 視同名稱類識別字。
 * 更深之資料流（跨函式、多步、經中介函式）不追蹤，列 manifest not_executable 由審碼把關。 */
export function nameAliases(source: string): Set<string> {
  const aliases = new Set<string>();
  for (const m of source.matchAll(ALIAS_DECL_RE)) {
    const rhsIdents = m[2].match(IDENT_RE) ?? [];
    if (rhsIdents.some((id) => RECEIVER_RE.test(id))) aliases.add(m[1]);
  }
  return aliases;
}

/** 名稱類識別字（含同檔單步別名）之字串解析呼叫（審查 r12 CODEX-R12-P1-06、r13 P1-04）；回傳 `id@行號`。 */
export function scanSemantic(source: string): string[] {
  const hits: string[] = [];
  const aliases = nameAliases(source);
  source.split('\n').forEach((line, idx) => {
    if (SEM.forbid_new_regexp && /new\s+RegExp\s*\(/.test(line)) hits.push(`new_regexp@${idx + 1}`);
    for (const m of line.matchAll(CALL_RE)) {
      const receiver = m[1].split('.').map((s) => s.trim()).pop() ?? '';
      const method = m[2];
      if (!RECEIVER_RE.test(receiver) && !aliases.has(receiver)) continue;
      if (SEM.ambiguous_methods.includes(method) && COLLECTION_RE.test(receiver)) continue;
      hits.push(`${method}:${receiver}@${idx + 1}`);
    }
  });
  return hits;
}

function walk(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      if (entry === 'node_modules') continue;
      out.push(...walk(full));
    } else if (/\.(ts|tsx)$/.test(entry) && !/\.test\.(ts|tsx)$/.test(entry)) {
      out.push(full);
    }
  }
  return out;
}

export function scanSource(source: string): string[] {
  const hits: string[] = [];
  source.split('\n').forEach((line, idx) => {
    for (const p of PATTERNS) {
      if (p.re.test(line)) hits.push(`${p.id}@${idx + 1}`);
    }
  });
  return hits;
}

describe('FF-NAME 前端語意解析靜態封閉', () => {
  it('契約已讀到（防路徑錯而空洞通過）', () => {
    expect(PATTERNS.length).toBeGreaterThanOrEqual(7);
    expect(FE.consumers.length).toBe(5);
  });

  it('frontend/src（測試檔除外）禁用樣式命中 == 0', () => {
    const root = join(REPO, FE.static_scan_root);
    const files = walk(root);
    expect(files.length).toBeGreaterThan(50);
    const hits: string[] = [];
    for (const file of files) {
      for (const h of scanSource(readFileSync(file, 'utf8'))) hits.push(`${relative(REPO, file)}:${h}`);
    }
    expect(hits).toEqual([]);
  });

  it('前端 parser 與 worker 已刪除', () => {
    for (const rel of FE.deleted_files) expect(existsSync(join(REPO, rel)), rel).toBe(false);
  });

  it('顯示或篩選特徵欄名之元件一律經同一 hook', () => {
    for (const rel of FE.consumers) {
      const src = readFileSync(join(REPO, rel), 'utf8');
      expect(src, rel).toContain(FE.hook_name);
      expect(src, rel).toContain(FE.hook_module);
    }
  });

  it('feature-factory 元件、store、hooks 內名稱類識別字之字串解析命中 == 0', () => {
    const hits: string[] = [];
    for (const rootRel of SEM.roots) {
      for (const file of walk(join(REPO, rootRel))) {
        for (const h of scanSemantic(readFileSync(file, 'utf8'))) hits.push(`${relative(REPO, file)}:${h}`);
      }
    }
    expect(hits).toEqual([]);
  });

  it('mutation（審查 r12）：name.split(\'-\')、featureName.slice、new RegExp 被偵測；陣列操作與 includes 不誤判', () => {
    const regressed = [
      "const indicator = name.split('-')[0];",
      'const head = featureName.slice(0, 3);',
      'const m = row.column.match(/x/);',
      'const re = new RegExp(pattern);',
    ].join('\n');
    const hits = scanSemantic(regressed);
    expect(hits.some((h) => h.startsWith('split:name'))).toBe(true);
    expect(hits.some((h) => h.startsWith('slice:featureName'))).toBe(true);
    expect(hits.some((h) => h.startsWith('match:column'))).toBe(true);
    expect(hits.some((h) => h.startsWith('new_regexp'))).toBe(true);
    const allowed = [
      'const preview = features.slice(0, 20);',
      'const idx = filteredFeatureOptions.indexOf(feature);',
      'const hit = name.includes(query);',
      'const label = name;',
    ].join('\n');
    expect(scanSemantic(allowed)).toEqual([]);
  });

  it('mutation（審查 r13）：同檔單步別名後之字串解析被偵測；非名稱來源之別名與集合別名不誤判', () => {
    const aliased = [
      'const token = featureName;',
      "const indicator = token.split('-')[0];",
      'const key = row.column;',
      'key.match(/trend/);',
      'let label: string = displayName;',
      "label.replace('_', ' ');",
    ].join('\n');
    const hits = scanSemantic(aliased);
    expect(hits.some((h) => h.startsWith('split:token'))).toBe(true);
    expect(hits.some((h) => h.startsWith('match:key'))).toBe(true);
    expect(hits.some((h) => h.startsWith('replace:label'))).toBe(true);
    const clean = [
      'const total = items.length;',
      "const text = total.toString().split('.');",
      'const previewItems = features.slice(0, 20);',
      'const tail = previewItems.slice(1);',
      'const hit = name.includes(query);',
    ].join('\n');
    expect(scanSemantic(clean)).toEqual([]);
  });

  it('mutation ⑪：恢復 split(\'_\') 或 ms_ 特判之原始碼即被偵測', () => {
    const regressed = "const parts = name.split('_');\nconst picks = all.filter((n) => n.startsWith('ms_'));\nconst ind = parts[3];";
    const hits = scanSource(regressed);
    expect(hits.some((h) => h.startsWith('split_underscore_sq'))).toBe(true);
    expect(hits.some((h) => h.startsWith('prefix_special_case'))).toBe(true);
    expect(hits.some((h) => h.startsWith('parts_index_3'))).toBe(true);
    expect(scanSource("const label = name; // 原樣顯示\nconst hit = name.includes(query);")).toEqual([]);
  });
});
