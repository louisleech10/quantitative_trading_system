/**
 * FF-NAME Task 3.3 — 前端只消費 API 描述（docs/FFNAME_SPEC.md Task 3.3；TODO docs/manifests/FFNAME.json）。
 *
 * 以 API `detail_level=names` 與 `table` 兩種回應樣本（含不在 Task 1.2 向量內之合法 `cross-sectional`、`tail-risk`、
 * 連字號 source 名）建共享描述 map；查詢一律經 map（不解析欄名字串），map 查無或未知版本／未知 kind 顯示 unsupported。
 * 邊界：描述版本不符或未知 kind ⇒ unsupported，不 fallback other。
 * 介面名（hook／resolver／map builder）與描述鍵取自 `tests/_golden/ffname/contract.json`。
 * 元件只經 hook 讀描述之靜態封閉見 featureDescriptor.static.test.ts。
 */
import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { beforeAll, describe, expect, it } from 'vitest';

const REPO = resolve(__dirname, '../../..');
const CONTRACT = JSON.parse(readFileSync(join(REPO, 'tests/_golden/ffname/contract.json'), 'utf8')) as {
  naming_version: number;
  kinds: string[];
  descriptor: { row_key: string; keys: string[]; unsupported_marker: string };
  frontend: { hook_name: string; resolver_name: string; map_builder_name: string };
};
const ROW_KEY = CONTRACT.descriptor.row_key;
const UNSUPPORTED = CONTRACT.descriptor.unsupported_marker;
// 模組路徑以變數動態載入：實作前模組不存在時只使本檔紅，不使 `npm run build` 之型別檢查失敗
const MODULE_PATH = '@/lib/featureDescriptor';
type Fn = (...args: unknown[]) => unknown;
let mod: Record<string, Fn> = {};
let build: Fn = () => { throw new Error('module not loaded'); };
let resolveDesc: Fn = () => { throw new Error('module not loaded'); };

beforeAll(async () => {
  mod = (await import(/* @vite-ignore */ MODULE_PATH)) as Record<string, Fn>;
  build = mod[CONTRACT.frontend.map_builder_name];
  resolveDesc = mod[CONTRACT.frontend.resolver_name];
});

type Desc = Record<string, unknown>;

function desc(name: string, kind: string, source: string, tf: string, category: string, indicator: string,
              params = '', ops: string[] = [], version = CONTRACT.naming_version): Desc {
  return { version, kind, source, tf, category, indicator, params, ops, display: name };
}

const SAMPLE: Record<string, Desc> = {
  'xsec_1h_cross-sectional_beta': desc('xsec_1h_cross-sectional_beta', 'cross-sectional', 'xsec', '1h', 'cross-sectional', 'beta'),
  'close_1h_tail-risk_cvar_1pct-21': desc('close_1h_tail-risk_cvar_1pct-21', 'atomic', 'close', '1h', 'tail-risk', 'cvar', '1pct-21'),
  'taker-ratio_12h_momentum_CMO_13': desc('taker-ratio_12h_momentum_CMO_13', 'atomic', 'taker-ratio', '12h', 'momentum', 'CMO', '13'),
  // 描述之 category 故意與欄名字面不同：證明查詢走 map 而非解析欄名
  'close_1h_trend_EMA_8': desc('close_1h_trend_EMA_8', 'atomic', 'close', '1h', 'momentum', 'EMA', '8'),
};

const NAMES_RESPONSE = { features: Object.entries(SAMPLE).map(([name, d]) => ({ name, [ROW_KEY]: d })) };
const TABLE_RESPONSE = {
  features: Object.entries(SAMPLE).map(([name, d]) => ({ name, category: 'x', nan_ratio: 0.1, [ROW_KEY]: d })),
};

function isUnsupported(result: unknown): boolean {
  const r = result as Record<string, unknown> | null;
  return !!r && (r.status === UNSUPPORTED || r[UNSUPPORTED] === true);
}

function descriptorOf(result: unknown): Desc {
  const r = result as Record<string, unknown>;
  return (r.descriptor ?? r) as Desc;
}

describe('FF-NAME 前端描述 map', () => {
  it('模組匯出 hook／resolver／map builder', () => {
    expect(typeof mod[CONTRACT.frontend.hook_name]).toBe('function');
    expect(typeof build).toBe('function');
    expect(typeof resolveDesc).toBe('function');
  });

  it('names 與 table 兩種回應建出之 map 逐欄相等', () => {
    const a = build(NAMES_RESPONSE.features) as Map<string, Desc>;
    const b = build(TABLE_RESPONSE.features) as Map<string, Desc>;
    expect([...a.keys()].sort()).toEqual(Object.keys(SAMPLE).sort());
    for (const name of Object.keys(SAMPLE)) expect(b.get(name)).toEqual(a.get(name));
  });

  it('合法之 cross-sectional、tail-risk、連字號 source 名經 map 取描述（不解析欄名）', () => {
    const map = build(NAMES_RESPONSE.features);
    for (const [name, d] of Object.entries(SAMPLE)) {
      const result = resolveDesc(map, name);
      expect(isUnsupported(result), name).toBe(false);
      expect(descriptorOf(result).category).toBe(d.category);
    }
    expect(descriptorOf(resolveDesc(map, 'close_1h_trend_EMA_8')).category).toBe('momentum');
  });

  it('map 查無 ⇒ unsupported（不 fallback 字串解析）', () => {
    const map = build(NAMES_RESPONSE.features);
    const result = resolveDesc(map, 'close_1h_volatility_ATR_14');
    expect(isUnsupported(result)).toBe(true);
    expect(JSON.stringify(result)).not.toContain('"volatility"');
  });

  it('邊界：描述版本不符或未知 kind ⇒ unsupported，不 fallback other', () => {
    const name = 'close_1h_trend_EMA_21';
    const oldVersion = build([{ name, [ROW_KEY]: desc(name, 'atomic', 'close', '1h', 'trend', 'EMA', '21', [], CONTRACT.naming_version - 1) }]);
    const unknownKind = build([{ name, [ROW_KEY]: desc(name, 'bogus-kind', 'close', '1h', 'trend', 'EMA', '21') }]);
    for (const map of [oldVersion, unknownKind]) {
      const result = resolveDesc(map, name);
      expect(isUnsupported(result)).toBe(true);
      expect(JSON.stringify(result)).not.toContain('"other"');
    }
    expect(CONTRACT.kinds).not.toContain('bogus-kind');
  });

  it('mutation：resolver 改為「查無即回空描述」會被 unsupported 斷言抓到', () => {
    const lenient = (map: Map<string, Desc>, name: string) => map.get(name) ?? { category: 'other' };
    const map = build(NAMES_RESPONSE.features) as Map<string, Desc>;
    expect(isUnsupported(lenient(map, 'not-in-map'))).toBe(false);
    expect(isUnsupported(resolveDesc(map, 'not-in-map'))).toBe(true);
  });
});
