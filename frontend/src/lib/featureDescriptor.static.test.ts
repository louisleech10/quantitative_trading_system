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
  };
};
const FE = CONTRACT.frontend;
const PATTERNS = FE.static_forbidden.map((p) => ({ id: p.id, re: new RegExp(p.regex) }));

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

  it('mutation ⑪：恢復 split(\'_\') 或 ms_ 特判之原始碼即被偵測', () => {
    const regressed = "const parts = name.split('_');\nconst picks = all.filter((n) => n.startsWith('ms_'));\nconst ind = parts[3];";
    const hits = scanSource(regressed);
    expect(hits.some((h) => h.startsWith('split_underscore_sq'))).toBe(true);
    expect(hits.some((h) => h.startsWith('prefix_special_case'))).toBe(true);
    expect(hits.some((h) => h.startsWith('parts_index_3'))).toBe(true);
    expect(scanSource("const label = name; // 原樣顯示\nconst hit = name.includes(query);")).toEqual([]);
  });
});
