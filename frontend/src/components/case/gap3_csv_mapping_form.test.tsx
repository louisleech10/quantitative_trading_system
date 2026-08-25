/**
 * GAP-3 UX Task 1.5 驗收（`npm --prefix frontend test -- --run gap3_csv`）。
 *
 * 判準字面之唯一來源＝SPEC L1578–1587 之「驗證」欄：≥5 條；斷言**未勾確認時 `fetch` call count == 0**。
 * 另含 TODO 之兩條邊界（①未勾確認、②欄名重複之 CSV）與具名殘留 `R-B2-1`（秒級 t0 之 ID 摩擦）。
 *
 * 🔴 邊界①一律以**執行期呼叫次數**斷言，不看按鈕有沒有 `disabled`（§6.2：原始碼形狀證明不了執行期性質）
 *    ——送出鍵刻意**保持可按**，否則 `fireEvent.click` 什麼都沒觸發，測試會恆綠。
 * 🔴 **邊界①之計數對象是真 `fetch`**（R1 `COMPOSER-R1-P0-01`）：本檔**不 mock**
 *    `fetchLookaheadDeclarationPreview`／`uploadEventCsvMapping`，只 stub `global.fetch`
 *    ——把 api helper mock 掉，答案窗預填那次真實網路動作就會從計數裡消失（那正是 R1 抓到的假綠）。
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import EventCsvMappingForm, { MAPPABLE_CONTRACT_FIELDS } from '@/components/case/EventCsvMappingForm';
import { EVENT_ID_TEMPLATE, MS_MAGNITUDE_MIN, canonicalEventId } from '@/lib/eventId';

const CONTRACT_PATH = path.resolve(__dirname, '../../../../momentum/Analysis/contracts/event_import_contract.json');
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, 'utf8'));

const T0_MS = 1704067200000;
const T0_SEC = 1704067200;
const HEADER = ['我的編號', '幣種', 'K線週期', '毫秒時間', '是不是正例', 'flag'];

/** 一次真實 fetch 之最小回應（`response.ok` 為真時 caller 會 `.json()`）。 */
function jsonResponse(body: unknown) {
  return { ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body) };
}

function fetchSpy(body: unknown = { timeframes: [], data_columns: [], default_window_bars: {}, requires_declaration: false, referenced_columns: [] }) {
  return vi.fn(async () => jsonResponse(body));
}

/** 7 列資料（用來證明預覽只顯示前 5 列）；`是不是正例` 與 `flag` 都是二元欄。 */
function csvText({ seconds = false, duplicateHeader = false, ragged = false } = {}): string {
  const head = duplicateHeader
    ? ['我的編號', '幣種', 'K線週期', '毫秒時間', '是不是正例', '是不是正例']
    : HEADER;
  const lines = [head.join(',')];
  for (let i = 0; i < 7; i += 1) {
    const t0ms = T0_MS + i * 43200000;
    const t0 = seconds ? String(T0_SEC + i * 43200) : String(t0ms);
    const cells = [canonicalEventId('ETHUSDT', '12h', seconds ? Number(t0) : t0ms), 'ETHUSDT', '12h',
                   t0, String(i % 2), String((i + 1) % 2)];
    lines.push((ragged ? [...cells, 'EXTRA'] : cells).join(','));
  }
  return `${lines.join('\n')}\n`;
}

function singleBinaryCsv(): string {
  return ['symbol,is_up,price', 'ETHUSDT,1,3200', 'ETHUSDT,0,3210'].join('\n');
}

async function pick(text: string, name = 'mine.csv') {
  const input = screen.getByTestId('csv-mapping-file') as HTMLInputElement;
  const file = new File([text], name, { type: 'text/csv' });
  fireEvent.change(input, { target: { files: [file] } });
  await waitFor(() => expect(screen.getByTestId('csv-preview')).toBeTruthy());
  return file;
}

function map(field: string, columnIndex: number) {
  fireEvent.change(screen.getByTestId(`csv-mapping-${field}`), { target: { value: String(columnIndex) } });
}

function mapAll() {
  map('event_id', 0);
  map('symbol', 1);
  map('timeframe', 2);
  map('t0', 3);
  map('label', 4);
}

/** 目前為止所有 fetch 之 URL（含答案窗預填那一次）。 */
function fetchUrls(): string[] {
  return (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls.map((c) => String(c[0]));
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchSpy());
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('GAP-3 Task 1.5 CSV 對映 UI', () => {
  it('① 選檔後顯示前 5 列預覽（逐格內容相符）與全部欄名；所有對映下拉初始值皆為「未選」（A-4′）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());

    expect(screen.getAllByTestId('csv-preview-header').map((n) => n.textContent)).toEqual(HEADER);

    const rows = screen.getAllByTestId('csv-preview-row');
    expect(rows.length).toBe(5);                       // 7 列資料只顯示前 5 列
    // 🔴 逐格比對（R1 `CODEX-R1-P2-06`）：只數列數的話，把 previewRows 換成同長度空列也會綠
    rows.forEach((row, i) => {
      const t0 = String(T0_MS + i * 43200000);
      expect([...row.querySelectorAll('td')].map((td) => td.textContent)).toEqual([
        canonicalEventId('ETHUSDT', '12h', T0_MS + i * 43200000), 'ETHUSDT', '12h',
        t0, String(i % 2), String((i + 1) % 2),
      ]);
    });

    for (const field of MAPPABLE_CONTRACT_FIELDS) {
      expect((screen.getByTestId(`csv-mapping-${field}`) as HTMLSelectElement).value).toBe('');
    }
  });

  it('①b 只有一個二元欄時，label 下拉仍是「未選」（不得因為只有一個就自動選它）', async () => {
    render(<EventCsvMappingForm />);
    await pick(singleBinaryCsv());
    expect((screen.getByTestId('csv-mapping-label') as HTMLSelectElement).value).toBe('');
  });

  it('② 未勾確認 ⇒ 真 fetch 呼叫次數為 0（含答案窗預填）；勾了才發生網路動作', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    mapAll();

    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(screen.getByTestId('csv-mapping-problems')).toBeTruthy());
    // 🔴 本檔沒有 mock 任何 api helper ⇒ 這個 0 是真的「一次網路動作都沒有」
    expect(global.fetch).toHaveBeenCalledTimes(0);

    fireEvent.click(screen.getByTestId('csv-confirm'));
    await waitFor(() => expect(fetchUrls().some((u) => u.includes('lookahead-declaration'))).toBe(true));

    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(fetchUrls().some((u) => u.includes('import-events/csv'))).toBe(true));
  });

  it('②b 送出之 multipart 內容：對映逐鍵相符、確認時間＝**勾選當下**（非送出當下）、URL 命中對映端點', async () => {
    // 🔴 勾選與送出在測試裡只差幾毫秒 ⇒ 「時間差 < 5 秒」這種斷言對「改記送出時間」**沒有鑑別力**
    //    （`--record` 錄到空紅集合＝假綠信號）。用假時鐘把兩者拉開五分鐘，才驗得出記的是哪一個。
    const TICK_AT = '2026-08-25T10:00:00.000Z';
    const SUBMIT_AT = '2026-08-25T10:05:00.000Z';
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      vi.setSystemTime(new Date(TICK_AT));
      render(<EventCsvMappingForm />);
      await pick(csvText());
      mapAll();
      fireEvent.click(screen.getByTestId('csv-confirm'));
      await waitFor(() => expect(fetchUrls().some((u) => u.includes('lookahead-declaration'))).toBe(true));

      vi.setSystemTime(new Date(SUBMIT_AT));
      fireEvent.click(screen.getByTestId('csv-mapping-submit'));
      await waitFor(() => expect(fetchUrls().some((u) => u.includes('import-events/csv'))).toBe(true));

      const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls;
      const submit = calls.find((c) => String(c[0]).includes('import-events/csv'))!;
      expect(String(submit[0])).toContain('validate_only=false');
      const body = (submit[1] as { body: FormData }).body;
      expect(JSON.parse(String(body.get('column_mapping')))).toEqual({
        event_id: '我的編號', symbol: '幣種', timeframe: 'K線週期', t0: '毫秒時間', label: '是不是正例',
      });
      // 勾選與送出相距 5 分鐘；記到的必須落在勾選那一刻附近（`shouldAdvanceTime` 會走幾十毫秒）
      const recorded = Date.parse(String(body.get('mapping_confirmed_at')));
      expect(recorded - Date.parse(TICK_AT)).toBeLessThan(60_000);
      expect(Date.parse(SUBMIT_AT) - recorded).toBeGreaterThan(240_000);
      expect(body.get('derive_event_id')).toBe(null);                   // 預設不推斷（A-4′）
    } finally {
      vi.useRealTimers();
    }
  });

  it('③ 聲明筆數即該欄之 0/1 實際筆數（不是估算）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    // 7 列，label 依序 0,1,0,1,0,1,0 ⇒ 正例 3、反例 4
    expect(screen.getByTestId('csv-positive-count').textContent).toBe('3');
    expect(screen.getByTestId('csv-negative-count').textContent).toBe('4');
  });

  it('④ 欄名重複之 CSV ⇒ 下拉各自可辨；選到重複欄名時擋下且不發生任何網路動作', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText({ duplicateHeader: true }));

    const options = within(screen.getByTestId('csv-mapping-label')).getAllByRole('option')
      .map((o) => o.textContent);
    expect(new Set(options).size).toBe(options.length);          // 逐項可辨，沒有兩個一樣的字樣
    expect(options).toContain('是不是正例（第 5 欄）');
    expect(options).toContain('是不是正例（第 6 欄）');

    mapAll();
    fireEvent.click(screen.getByTestId('csv-confirm'));
    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(screen.getByTestId('csv-mapping-problems')).toBeTruthy());
    expect(screen.getByTestId('csv-mapping-problems').textContent).toContain('重複欄名');
    expect(fetchUrls().some((u) => u.includes('import-events/csv'))).toBe(false);
  });

  it('④b 欄數不齊之 CSV ⇒ 預覽即紅字擋下，不得送出（後端會整批拒收）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText({ ragged: true }));
    expect(screen.getByTestId('csv-ragged-rows').textContent).toContain('欄數與標頭');

    mapAll();
    fireEvent.click(screen.getByTestId('csv-confirm'));
    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(screen.getByTestId('csv-mapping-problems')).toBeTruthy());
    expect(screen.getByTestId('csv-mapping-problems').textContent).toContain('欄數與標頭');
    expect(fetchUrls().some((u) => u.includes('import-events/csv'))).toBe(false);
  });

  it('⑤ 文案：禁用「label 正確」字樣，改說「你聲明」（D-1）', async () => {
    const { container } = render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    const text = container.textContent ?? '';
    expect(text).not.toContain('label 正確');
    expect(text).toContain('你聲明');
  });

  it('⑥ 殘留 R-B2-1：秒級 t0 ⇒ 逐列列出契約毫秒版 event_id（逐字相等），並提供由後端產生之選項', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText({ seconds: true }));
    mapAll();

    const block = await screen.findByTestId('csv-event-id-expected');
    // 🔴 逐列 exact 比對（R1 `CODEX-R1-P2-06`：`toContain` 對「期望值後面多接垃圾」無鑑別力）
    expect([...block.querySelectorAll('li')].map((li) => li.textContent)).toEqual(
      [0, 1, 2, 3, 4].map((i) => {
        const given = canonicalEventId('ETHUSDT', '12h', T0_SEC + i * 43200);
        const expected = canonicalEventId('ETHUSDT', '12h', T0_MS + i * 43200000);
        return `第 ${i + 1} 列：${given} → ${expected}`;
      }),
    );

    // 勾「由系統產生」⇒ 送出時帶 derive_event_id（後端在 t0 正規化後依契約模板產生）
    fireEvent.click(screen.getByTestId('csv-derive-event-id'));
    fireEvent.click(screen.getByTestId('csv-confirm'));
    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(fetchUrls().some((u) => u.includes('import-events/csv'))).toBe(true));
    const calls = (global.fetch as unknown as { mock: { calls: unknown[][] } }).mock.calls;
    const submit = calls.find((c) => String(c[0]).includes('import-events/csv'))!;
    expect((submit[1] as { body: FormData }).body.get('derive_event_id')).toBe('true');
  });

  it('⑥b ms 級檔案不得出現 ID 警示（避免恆亮型提示）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    mapAll();
    expect(screen.queryByTestId('csv-event-id-normalization')).toBeNull();
  });

  it('⑦ Task 1.7 接線：可疑欄警示之集合等於「所選以外之二元欄」', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    const warn = screen.getByTestId('csv-suspicious-binary');
    const listed = (warn.querySelector('span.font-mono')?.textContent ?? '').trim();
    expect(listed).toBe('flag');                       // 集合相等，不是 toContain
  });

  it('⑧ 防漂移：可對映欄清單／ID 模板／單位門檻逐字等於契約檔', () => {
    const derived = Object.entries(CONTRACT.required_fields as Record<string, { type: string }>)
      .filter(([, spec]) => spec.type !== 'object')
      .map(([name]) => name);
    expect([...MAPPABLE_CONTRACT_FIELDS]).toEqual(derived);
    expect(EVENT_ID_TEMPLATE).toBe(CONTRACT.event_id_template);
    expect(MS_MAGNITUDE_MIN).toBe(CONTRACT.ms_magnitude_min);
  });
});
