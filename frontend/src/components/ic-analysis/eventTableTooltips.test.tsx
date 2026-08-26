/**
 * GAP-3 UX Task 5.2 驗收（`--run eventTableTooltips`）——邊界①與防漂移。
 *
 * 邊界①：**每個表頭**之 tooltip 文字 `==` glossary 對應 `definition`。
 * 🔴 比對對象＝**render 出來的 DOM 之 `title` 屬性**（執行期），不是讀原始碼有沒有那個字串；
 *    右邊那個值**逐字讀自 `event_metrics_glossary.json`**，不在本檔另寫一份定義。
 *
 * 邊界②（缺鍵 ⇒ fail-closed 佔位）在 `eventTableTooltips.failclosed.test.tsx`，
 * 那條要換掉定義表，混在同一檔會讓本檔的①改為走替身。
 */
import { readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import EventTablesPanel from '@/components/ic-analysis/EventTablesPanel';
import { EVENT_METRIC_DEFINITIONS } from '@/lib/eventMetricsGlossary';
import type { EventAnalyzeResponse } from '@/lib/types';

const GLOSSARY_PATH = resolve(
  __dirname, '../../../../momentum/Analysis/contracts/event_metrics_glossary.json',
);
const GLOSSARY = JSON.parse(readFileSync(GLOSSARY_PATH, 'utf8')) as Record<string, { definition?: string }>;

/** 三張表全部 `ok`，讓每個表頭都真的被 render 出來（少 render 一張＝該表之表頭沒被驗到）。 */
const RESP = {
  import_id: 'imp-tooltip',
  summary: { n_input: 2, n_aligned: 2, n_align_failures: 0, n_train: 1, n_test: 1, n_purged: 0 },
  align_failures: [],
  tables: {
    event_forward_return_table: {
      capability_status: 'ok',
      horizons: [1, 2],
      primary_macro: { '1': { mean: 0.1, n_symbols: 2 }, '2': { mean: 0.2, n_symbols: 2 } },
      sensitivity_micro: {
        '1': { mean: 0.11, median: 0.1, win_rate: 0.6, n: 10, n_effective: 7.5 },
        '2': { mean: 0.21, median: 0.2, win_rate: 0.55, n: 10, n_effective: 7.5 },
      },
      // 🔴 `uniqueness_weighted` 之 n_effective **刻意與 micro 不同**：`n_eff` 之 definition 宣稱
      //    畫面這一欄是等權、降權值另存在這裡且未顯示。兩者相同的話，⑥ 分不出 UI 讀了哪一個。
      uniqueness_weighted: {
        '1': { mean: 0.11, median: 0.1, win_rate: 0.6, n: 10, n_effective: 3 },
        '2': { mean: 0.21, median: 0.2, win_rate: 0.55, n: 10, n_effective: 3 },
      },
    },
    binary_discrimination_table: {
      capability_status: 'ok',
      overall: { auc: 0.62, pr_auc: 0.41, n: 10, auc_in_band: false },
    },
    all_bars_evaluation: {
      capability_status: 'ok',
      counts: { n_total: 1000, n_eligible: 900, n_labeled: 880, n_tail_excluded: 60, n_unknown: 40 },
      overall: {
        capability_status: 'ok', prevalence_full: 0.05, prevalence_learn: 0.5,
        lift_threshold: 1.8, precision: 0.09, signal_frequency: 0.02,
      },
      manifest: {},
      signal_mapping: {},
    },
  },
  event_timestamps: [],
  event_timestamps_ic_seconds: [],
} as unknown as EventAnalyzeResponse;

/** 三張表在畫面上實際掛 tooltip 的表頭鍵（此清單改變＝版面改變，須連同 Task 5.2 一起審） */
const RENDERED_KEYS = [
  'horizon', 'macro_mean', 'micro_mean', 'median', 'win_rate', 'n', 'n_eff',
  'auc', 'pr_auc', 'n_test', 'auc_in_band',
  'n_total', 'n_eligible', 'n_labeled', 'tail_excluded', 'n_unknown',
  'prevalence_full', 'prevalence_learn', 'lift_threshold', 'precision', 'signal_frequency',
];

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('Task 5.2 — 事件型表格表頭 tooltip 取自 glossary', () => {
  it('① 逐表頭之 tooltip 文字逐字等於 glossary 之 definition', () => {
    render(<EventTablesPanel importId="imp-tooltip" data={RESP} />);
    for (const key of RENDERED_KEYS) {
      const fromGlossary = GLOSSARY[key]?.definition;
      // 正向對照：glossary 真的有這個鍵（打錯鍵時 undefined === undefined 不得被當成通過）
      expect(typeof fromGlossary, `glossary 缺鍵 ${key}`).toBe('string');
      const el = screen.getByTestId(`event-metric-${key}`);
      expect(el.getAttribute('title'), `${key} 之 tooltip`).toBe(fromGlossary);
    }
  });

  it('② 三張表之表頭都掛上了 tooltip（漏掛一個表頭＝本條紅）', () => {
    render(<EventTablesPanel importId="imp-tooltip" data={RESP} />);
    const rendered = screen.getAllByTestId(/^event-metric-/).map((e) => e.getAttribute('data-testid'));
    expect(new Set(rendered)).toEqual(new Set(RENDERED_KEYS.map((k) => `event-metric-${k}`)));
  });

  /**
   * 🔴 R1（`CODEX-R1-P1-01`）之後本條換了守衛對象。
   * 舊版守的是「鏡像常數逐字等於 glossary」；現在 `EVENT_METRIC_DEFINITIONS` 是**由 JSON 當場導出**，
   * 那個比對已成同義反覆。真正還需要守的是 Task 5.0 之「不可做：不得把定義同時寫在前端」——
   * 只要有人把某段 definition 複製進前端原始碼，唯一來源就破了，而本條會紅。
   */
  it('③ 前端原始碼不得出現任何 definition 副本（唯一來源＝glossary JSON）', () => {
    const definitions = Object.entries(GLOSSARY)
      .filter(([key]) => !key.startsWith('_'))
      .map(([key, entry]) => [key, entry.definition as string] as const);
    expect(definitions.length).toBeGreaterThan(0);        // 正向對照：真的讀到東西

    const srcRoot = resolve(__dirname, '../..');
    const files: string[] = [];
    const walk = (dir: string) => {
      for (const item of readdirSync(dir, { withFileTypes: true })) {
        const full = resolve(dir, item.name);
        if (item.isDirectory()) walk(full);
        else if (/\.tsx?$/.test(item.name)) files.push(full);
      }
    };
    walk(srcRoot);
    expect(files.length).toBeGreaterThan(0);

    const offenders: string[] = [];
    for (const file of files) {
      const text = readFileSync(file, 'utf8');
      for (const [key, definition] of definitions) {
        if (text.includes(definition)) offenders.push(`${file} 複列了 ${key}`);
      }
    }
    expect(offenders).toEqual([]);
  });

  it('④ 導出之鍵集恰為 glossary 之指標鍵（後設欄不混入、指標鍵不漏）', () => {
    const metricKeys = Object.keys(GLOSSARY).filter((k) => !k.startsWith('_'));
    expect(new Set(Object.keys(EVENT_METRIC_DEFINITIONS))).toEqual(new Set(metricKeys));
    expect(Object.keys(EVENT_METRIC_DEFINITIONS)).not.toContain('_doc');
    expect(Object.keys(EVENT_METRIC_DEFINITIONS)).not.toContain('_version');
  });

  /**
   * 🔴 R1 修補後**主委自打**新增：R1 群集 A 加的算式綁定測試守的是「micro 區是不是等權」，
   * **沒有**守「畫面的 n_eff 讀的是哪一個欄」。有人把它改讀 `uniqueness_weighted` 時，
   * 算式沒變（測試全綠），但 `n_eff` 之 definition 宣稱的「本欄恆等於 n」就又變成錯的。
   * 這條把 definition 的另一半（欄位綁定）也釘住。
   */
  it('⑥ n_eff 欄顯示的是等權之 micro 值，不是降權後的 uniqueness_weighted', () => {
    render(<EventTablesPanel importId="imp-tooltip" data={RESP} />);
    const row = screen.getByTestId('event-fwd-row-1').textContent ?? '';
    expect(row).toContain('7.50');       // sensitivity_micro.n_effective
    expect(row).not.toContain('3.00');   // uniqueness_weighted.n_effective（definition 說它沒顯示）
  });

  it('⑦ 每個 definition 都夠長，前端副本掃描不會誤命中（③ 之前置）', () => {
    // ③ 是「原始碼含該字串就算複列」。definition 若短到會偶然出現在別處（例如 'n'），
    // ③ 會開始亂紅。現況最短 27 字元；本條讓未來加入過短定義時**先在這裡紅**，而不是讓 ③ 變得不可信。
    const tooShort = Object.entries(GLOSSARY)
      .filter(([key]) => !key.startsWith('_'))
      .filter(([, entry]) => (entry.definition ?? '').length < 20)
      .map(([key]) => key);
    expect(tooShort).toEqual([]);
  });

  it('⑤ 標籤字面未被改動（Task 5.2 邊界：只加 tooltip，不改版面）', () => {
    render(<EventTablesPanel importId="imp-tooltip" data={RESP} />);
    expect(screen.getByTestId('event-metric-macro_mean').textContent).toBe('macro mean');
    expect(screen.getByTestId('event-metric-n_eff').textContent).toBe('n_eff');
    expect(screen.getByTestId('event-metric-n_test').textContent).toBe('n（test）');
  });
});
