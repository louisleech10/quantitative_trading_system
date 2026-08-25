/**
 * GAP-3 UX Task 1.5 驗收（`npm --prefix frontend test -- --run gap3_csv`）。
 *
 * 判準字面之唯一來源＝SPEC L1578–1587 之「驗證」欄：≥5 條；斷言**未勾確認時 `fetch` call count == 0**。
 * 另含 TODO 之兩條邊界（①未勾確認、②欄名重複之 CSV）與具名殘留 `R-B2-1`（秒級 t0 之 ID 摩擦）。
 *
 * 🔴 邊界①一律以**執行期呼叫次數**斷言，不看按鈕有沒有 `disabled`（§6.2：原始碼形狀證明不了執行期性質）
 *    ——送出鍵刻意**保持可按**，否則 `fireEvent.click` 什麼都沒觸發，測試會恆綠。
 */
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import EventCsvMappingForm, { MAPPABLE_CONTRACT_FIELDS } from '@/components/case/EventCsvMappingForm';
import { EVENT_ID_TEMPLATE, MS_MAGNITUDE_MIN, canonicalEventId } from '@/lib/eventId';

const CONTRACT_PATH = path.resolve(__dirname, '../../../../momentum/Analysis/contracts/event_import_contract.json');
const CONTRACT = JSON.parse(readFileSync(CONTRACT_PATH, 'utf8'));

const uploadMock = vi.fn();
const previewMock = vi.fn();
vi.mock('@/lib/api', async (orig) => {
  const actual = await orig<typeof import('@/lib/api')>();
  return {
    ...actual,
    uploadEventCsvMapping: (...a: unknown[]) => uploadMock(...a),
    fetchLookaheadDeclarationPreview: (...a: unknown[]) => previewMock(...a),
  };
});

const T0_MS = 1704067200000;
const T0_SEC = 1704067200;

/** 7 列資料（用來證明預覽只顯示前 5 列）；`is_up` 與 `flag` 都是二元欄。 */
function csvText({ seconds = false, duplicateHeader = false } = {}): string {
  const head = duplicateHeader
    ? ['我的編號', '幣種', 'K線週期', '毫秒時間', '是不是正例', '是不是正例']
    : ['我的編號', '幣種', 'K線週期', '毫秒時間', '是不是正例', 'flag'];
  const lines = [head.join(',')];
  for (let i = 0; i < 7; i += 1) {
    const t0ms = T0_MS + i * 43200000;
    const t0 = seconds ? String(T0_SEC + i * 43200) : String(t0ms);
    lines.push([canonicalEventId('ETHUSDT', '12h', seconds ? Number(t0) : t0ms), 'ETHUSDT', '12h',
                t0, String(i % 2), String((i + 1) % 2)].join(','));
  }
  return `${lines.join('\n')}\n`;
}

/** 只有**一個**二元欄的檔——用來證明「只有一個也不自動選」（A-4′）。 */
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

/** 依「契約欄名 → CSV 欄序」設定下拉。 */
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

beforeEach(() => {
  previewMock.mockRejectedValue(new Error('preview off in this test'));
  vi.stubGlobal('fetch', vi.fn());
});

afterEach(() => {
  cleanup();
  uploadMock.mockReset();
  previewMock.mockReset();
  vi.unstubAllGlobals();
});

describe('GAP-3 Task 1.5 CSV 對映 UI', () => {
  it('① 選檔後顯示前 5 列預覽與全部欄名；所有對映下拉初始值皆為「未選」（A-4′）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());

    expect(screen.getAllByTestId('csv-preview-header').map((n) => n.textContent))
      .toEqual(['我的編號', '幣種', 'K線週期', '毫秒時間', '是不是正例', 'flag']);
    expect(screen.getAllByTestId('csv-preview-row').length).toBe(5);   // 7 列資料只顯示前 5 列

    for (const field of MAPPABLE_CONTRACT_FIELDS) {
      expect((screen.getByTestId(`csv-mapping-${field}`) as HTMLSelectElement).value).toBe('');
    }
  });

  it('①b 只有一個二元欄時，label 下拉仍是「未選」（不得因為只有一個就自動選它）', async () => {
    render(<EventCsvMappingForm />);
    await pick(singleBinaryCsv());
    expect((screen.getByTestId('csv-mapping-label') as HTMLSelectElement).value).toBe('');
  });

  it('② 未勾確認 ⇒ 送出時 upload 與 fetch 之呼叫次數皆為 0；勾了才送出一次', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    mapAll();

    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(screen.getByTestId('csv-mapping-problems')).toBeTruthy());
    expect(uploadMock).toHaveBeenCalledTimes(0);
    expect(global.fetch).toHaveBeenCalledTimes(0);

    uploadMock.mockResolvedValueOnce({ accepted: true, import_id: 'imp-1', n_rows: 7, n_valid: 7,
      failures: [], warnings: [], upload_sha256: null, source_digest_verified: false,
      contract_version: '1', stored_path: null });
    fireEvent.click(screen.getByTestId('csv-confirm'));
    fireEvent.click(screen.getByTestId('csv-mapping-submit'));
    await waitFor(() => expect(uploadMock).toHaveBeenCalledTimes(1));

    const [, submission] = uploadMock.mock.calls[0];
    expect(submission.columnMapping).toEqual({
      event_id: '我的編號', symbol: '幣種', timeframe: 'K線週期', t0: '毫秒時間', label: '是不是正例',
    });
    expect(typeof submission.confirmedAt).toBe('string');
    expect(Number.isNaN(Date.parse(submission.confirmedAt))).toBe(false);
  });

  it('③ 聲明筆數即該欄之 0/1 實際筆數（不是估算）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    // 7 列，label 依序 0,1,0,1,0,1,0 ⇒ 正例 3、反例 4
    expect(screen.getByTestId('csv-positive-count').textContent).toBe('3');
    expect(screen.getByTestId('csv-negative-count').textContent).toBe('4');
  });

  it('④ 欄名重複之 CSV ⇒ 下拉各自可辨；選到重複欄名時擋下且不送出', async () => {
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
    expect(uploadMock).toHaveBeenCalledTimes(0);
  });

  it('⑤ 文案：禁用「label 正確」字樣，改說「你聲明」（D-1）', async () => {
    const { container } = render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    const text = container.textContent ?? '';
    expect(text).not.toContain('label 正確');
    expect(text).toContain('你聲明');
  });

  it('⑥ 殘留 R-B2-1：秒級 t0 ⇒ 預先算出契約要求的毫秒版 event_id（逐字相等）', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText({ seconds: true }));
    mapAll();

    const block = await screen.findByTestId('csv-event-id-expected');
    const expected = canonicalEventId('ETHUSDT', '12h', T0_MS);
    expect(block.textContent).toContain(expected);
    expect(block.textContent).toContain(canonicalEventId('ETHUSDT', '12h', T0_SEC));   // 使用者原本寫的秒版
    // ms 級檔案不得出現本警示（避免「恆亮型」提示）
    cleanup();
    render(<EventCsvMappingForm />);
    await pick(csvText());
    mapAll();
    expect(screen.queryByTestId('csv-event-id-normalization')).toBeNull();
  });

  it('⑦ Task 1.7 接線：可疑欄警示列出使用者所選以外之二元欄', async () => {
    render(<EventCsvMappingForm />);
    await pick(csvText());
    map('label', 4);
    const warn = screen.getByTestId('csv-suspicious-binary');
    expect(warn.textContent).toContain('flag');
    expect(warn.textContent).not.toContain('是不是正例');
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
