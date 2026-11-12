/**
 * ICPERF SPEC Task 0.6 (h) ⑦ 牆鐘中止＋③ 分頁（L1c；委員會 r169 G3）：SymbolCoverageMatrix 之前端驗收。
 * L0 機讀表（git 物件 1eeef821）落點寫在 describe 名稱之 [rows:…]（`檔:L0 行:code_sha256 前 12 碼`），
 * 由 tests/momentum/Analysis/test_icperf_limit_l1_coverage.py 自 vitest 實際執行之測試名稱取用：
 * - :125／:163 請求本體帶逾時秒數 30 ⇒ 移除；POST 只回 task_id，前端輪詢 `GET /feature-browser/tasks/{id}`
 *   至終態（completed／failed／cancelled／interrupted），**不設次數或時間上限**，顯示 progress，提供取消鈕
 *   （`POST /feature-browser/tasks/{id}/cancel`）；completed 後取 `GET /feature-browser/tasks/{id}/result`。
 * - :24 clampTopN 上界 500、:208 輸入 max={500} ⇒ 下鑽改「每頁筆數」（≥1、無上界），結果以
 *   `GET .../result?offset=&limit=` 分頁讀取，顯示 total，上一頁／下一頁以 offset 遍歷全量。
 * 輪詢間隔由元件決定；本檔以 vi 假時鐘推進（非牆鐘），推進直到條件成立。
 */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SymbolCoverageMatrix from '@/components/feature-factory/SymbolCoverageMatrix';
import type { FeatureRegistryEntry } from '@/lib/types';

const SYMS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'];
const entries: FeatureRegistryEntry[] = SYMS.map((symbol, i) => ({
  symbol,
  timeframe: '12h',
  config_hash: `cfg_${i}`,
  feature_count: 135,
  row_count: 1600,
  created_at: 1_900_000_000,
  hdf5_relative_path: '',
}));

const groupResult = {
  groups: ['group_sma', 'group_ret'],
  symbols: SYMS,
  matrix: {
    group_sma: { BTCUSDT: 0.95, ETHUSDT: 0.93, SOLUSDT: 0.9 },
    group_ret: { BTCUSDT: 0.998, ETHUSDT: 0.997, SOLUSDT: 0.996 },
  },
  divergence: { group_sma: 0.05, group_ret: 0.002 },
  summary: { avg_coverage: 0.96, worst_symbol: 'SOLUSDT', worst_group: 'group_sma', missing_symbols: [] },
};

const DRILL_TOTAL = 1234;
function drillPage(offset: number, limit: number) {
  const names: string[] = [];
  for (let i = offset; i < Math.min(offset + limit, DRILL_TOTAL); i += 1) names.push(`feat_${i}`);
  const matrix: Record<string, Record<string, number>> = {};
  const divergence: Record<string, number> = {};
  for (const n of names) {
    matrix[n] = { BTCUSDT: 0.9, ETHUSDT: 0.8, SOLUSDT: 0.7 };
    divergence[n] = 0.2;
  }
  return { group_name: 'group_sma', total: DRILL_TOTAL, offset, limit, features: names, symbols: SYMS, matrix, divergence,
    row_counts: { BTCUSDT: 1600, ETHUSDT: 1000, SOLUSDT: 700 } };
}

interface Call { url: string; method: string; body: Record<string, unknown> | undefined }
let calls: Call[] = [];
/** handler 回此值 ⇒ fetch 以網路錯誤拒絕（模擬斷線；NOCAP Task 5.3：網路錯誤依退避重試、不丟棄進行中任務）。 */
const NETWORK_ERROR = Symbol('network-error');

function stubFetch(handler: (url: string, method: string) => unknown) {
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? 'GET').toUpperCase();
    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined;
    calls.push({ url, method, body });
    const payload = await handler(url, method); // handler 可回 Promise（延遲回應，驗晚到回應之世代防護）
    if (payload === NETWORK_ERROR) throw new TypeError('Failed to fetch');
    return { ok: true, status: 200, statusText: 'OK', json: async () => payload } as unknown as Response;
  }));
}

const isStatus = (url: string, id: string) => new URL(url).pathname.endsWith(`/feature-browser/tasks/${id}`);
const isResult = (url: string, id: string) => new URL(url).pathname.endsWith(`/feature-browser/tasks/${id}/result`);
const isCancel = (url: string, id: string) => new URL(url).pathname.endsWith(`/feature-browser/tasks/${id}/cancel`);
const isPost = (url: string, ep: string) => new URL(url).pathname.endsWith(`/feature-browser/${ep}`);
const count = (pred: (c: Call) => boolean) => calls.filter(pred).length;
const bodyText = () => document.body.textContent ?? '';
const REMOVED_TIME_FIELD = 'timeout_seconds';

/** 以假時鐘推進直到條件成立（每步 1 秒假時間；步數只為避免測試本身無窮迴圈，與元件之輪詢無上限無關）。 */
async function advanceUntil(pred: () => boolean, maxSteps = 3000) {
  for (let i = 0; i < maxSteps && !pred(); i += 1) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
  }
  expect(pred()).toBe(true);
}

/** 手動放行之延遲回應。 */
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function statusBody(id: string, state: string, processed = 3, total = 10) {
  return { task_id: id, kind: 'group_coverage', state, error: null, created_at: '2026-11-11T00:00:00+00:00',
    progress: { phase: 'manifest', processed, total, updated_at: '2026-11-11T00:00:01+00:00' } };
}

beforeEach(() => {
  calls = [];
  vi.useFakeTimers();
});
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('SymbolCoverageMatrix 任務制與分頁 [rows:frontend/src/components/feature-factory/SymbolCoverageMatrix.tsx:24:bec607c7198d,frontend/src/components/feature-factory/SymbolCoverageMatrix.tsx:125:014ba6bc49c5,frontend/src/components/feature-factory/SymbolCoverageMatrix.tsx:163:014ba6bc49c5,frontend/src/components/feature-factory/SymbolCoverageMatrix.tsx:208:343dd1a589c8]', () => {
  it('Group Coverage 請求本體無逾時秒數欄', async () => {
    stubFetch((url) => (isPost(url, 'group-coverage') ? { task_id: 'g1' } : statusBody('g1', 'running')));
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => count((c) => isPost(c.url, 'group-coverage')) === 1);
    const post = calls.find((c) => isPost(c.url, 'group-coverage'))!;
    expect(post.method).toBe('POST');
    expect(post.body).toBeDefined();
    expect(Object.keys(post.body!)).not.toContain(REMOVED_TIME_FIELD);
    expect(post.body!.symbols).toEqual(SYMS);
    expect(post.body!.timeframe).toBe('12h');
  });

  it('POST 後輪詢任務狀態至 completed（逾 200 次 running 仍續輪詢、無次數上限），執行中顯示進度，完成後取結果並顯示', async () => {
    const RUNNING_POLLS = 200;
    let polls = 0;
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isResult(url, 'g1')) return groupResult;
      if (isStatus(url, 'g1')) {
        polls += 1;
        return polls <= RUNNING_POLLS ? statusBody('g1', 'running') : statusBody('g1', 'completed', 10, 10);
      }
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => polls >= 1);
    expect(bodyText()).toMatch(/3\s*\/\s*10/);
    await advanceUntil(() => count((c) => isResult(c.url, 'g1')) >= 1 && screen.queryByText('group_ret') !== null);
    expect(polls).toBe(RUNNING_POLLS + 1);
    expect(screen.getByText('group_sma')).toBeTruthy();
    expect(calls.every((c) => !c.body || !(REMOVED_TIME_FIELD in c.body))).toBe(true);
  });

  it('執行中可取消：取消鈕呼叫 cancel 端點，進入終態 cancelled 後停止輪詢', async () => {
    let cancelled = false;
    let terminalReplies = 0;
    stubFetch((url, method) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isCancel(url, 'g1') && method === 'POST') {
        cancelled = true;
        return { task_id: 'g1', cancel: 'cancelling' };
      }
      if (isStatus(url, 'g1')) {
        if (cancelled) terminalReplies += 1;
        return statusBody('g1', cancelled ? 'cancelled' : 'running');
      }
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => count((c) => isStatus(c.url, 'g1')) >= 1);
    fireEvent.click(screen.getByRole('button', { name: /取消/ }));
    await advanceUntil(() => count((c) => isCancel(c.url, 'g1') && c.method === 'POST') === 1);
    await advanceUntil(() => terminalReplies >= 1);
    await act(async () => {}); // 讓終態回應處理完畢
    // 收到終態後再推進 60 秒假時間：不得再輪詢、不取結果
    const afterTerminal = count((c) => isStatus(c.url, 'g1'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(count((c) => isStatus(c.url, 'g1'))).toBe(afterTerminal);
    expect(count((c) => isResult(c.url, 'g1'))).toBe(0);
  });

  it.each([
    ['failed', 'group not found: group_x'],
    ['interrupted', 'service restarted before completion'],
  ])('running → %s：停止輪詢、結束 loading、顯示終態原因、不取結果（interrupted 附重送）', async (state, reason) => {
    let polls = 0;
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isStatus(url, 'g1')) {
        polls += 1;
        return polls <= 3 ? statusBody('g1', 'running') : { ...statusBody('g1', state), error: reason };
      }
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => bodyText().includes(reason));
    await act(async () => {});
    const afterTerminal = count((c) => isStatus(c.url, 'g1'));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(count((c) => isStatus(c.url, 'g1'))).toBe(afterTerminal);
    expect(count((c) => isResult(c.url, 'g1'))).toBe(0);
    expect((screen.getByRole('button', { name: /計算 Group Coverage/ }) as HTMLButtonElement).disabled).toBe(false);
    expect(screen.queryByRole('button', { name: /重送/ }) !== null).toBe(state === 'interrupted');
  });

  it('輪詢遇一次網路錯誤 ⇒ 退避後重試（假時鐘前進後才重試）、不丟棄任務，仍輪詢至 completed 並取結果', async () => {
    let polls = 0;
    const pollAt: number[] = []; // 各次 status 呼叫之假時鐘時間（vi 假時鐘同時接管 Date.now）
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isResult(url, 'g1')) return groupResult;
      if (isStatus(url, 'g1')) {
        polls += 1;
        pollAt.push(Date.now());
        if (polls === 2) return NETWORK_ERROR;
        return polls <= 4 ? statusBody('g1', 'running') : statusBody('g1', 'completed', 10, 10);
      }
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => polls >= 2);
    // 拒絕後只清微任務、不前進假時鐘 ⇒ 不得立即重試
    await act(async () => {});
    expect(polls).toBe(2);
    await advanceUntil(() => screen.queryByText('group_ret') !== null);
    expect(pollAt[2]).toBeGreaterThan(pollAt[1]);
    expect(polls).toBeGreaterThanOrEqual(5);
    expect(count((c) => isPost(c.url, 'group-coverage'))).toBe(1);
  });

  it('執行中顯示進度之 updated_at', async () => {
    stubFetch((url) => (isPost(url, 'group-coverage') ? { task_id: 'g1' } : statusBody('g1', 'running')));
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => count((c) => isStatus(c.url, 'g1')) >= 1 && bodyText().includes('2026-11-11T00:00:01'));
  });

  it('下鑽 A、B 先後送出而 A 之 POST 晚到：現行任務仍為 B，下一頁讀 B 之快照（審碼 r178）', async () => {
    const postA = deferred<unknown>();
    let drillPosts = 0;
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isStatus(url, 'g1')) return statusBody('g1', 'completed', 10, 10);
      if (isResult(url, 'g1')) return groupResult;
      if (isPost(url, 'group-feature-coverage')) {
        drillPosts += 1;
        return drillPosts === 1 ? postA.promise : { task_id: 'dB' };
      }
      if (isStatus(url, 'dB')) return statusBody('dB', 'completed', 30, 30);
      if (isStatus(url, 'dA')) return statusBody('dA', 'completed', 30, 30);
      for (const id of ['dA', 'dB']) {
        if (isResult(url, id)) {
          const q = new URL(url).searchParams;
          return drillPage(Number(q.get('offset')), Number(q.get('limit')));
        }
      }
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => screen.queryByText('group_sma') !== null);
    fireEvent.click(screen.getByText('group_sma')); // A（POST 延遲）
    await advanceUntil(() => drillPosts === 1);
    fireEvent.click(screen.getByText('group_ret')); // B
    await advanceUntil(() => screen.queryByText('feat_0') !== null);
    postA.resolve({ task_id: 'dA' }); // A 之 POST 晚到
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    fireEvent.click(screen.getByRole('button', { name: /下一頁/ }));
    await advanceUntil(() => screen.queryByText('feat_100') !== null);
    const pageCalls = calls.filter((c) => isResult(c.url, 'dA') || isResult(c.url, 'dB'));
    expect(pageCalls.every((c) => isResult(c.url, 'dB'))).toBe(true);
    expect(count((c) => isStatus(c.url, 'dA'))).toBe(0);
  });

  it('主表重算使舊下鑽失效：舊下鑽晚到之完成不取結果、不寫回已清空之下鑽區（審碼 r178）', async () => {
    let groupPosts = 0;
    let drillDone = false;
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) {
        groupPosts += 1;
        return { task_id: `g${groupPosts}` };
      }
      if (isStatus(url, 'g1') || isStatus(url, 'g2')) return statusBody('gx', 'completed', 10, 10);
      if (isResult(url, 'g1') || isResult(url, 'g2')) return groupResult;
      if (isPost(url, 'group-feature-coverage')) return { task_id: 'd1' };
      if (isStatus(url, 'd1')) return statusBody('d1', drillDone ? 'completed' : 'running', 30, 30);
      if (isResult(url, 'd1')) return drillPage(0, 100);
      throw new Error(`unexpected ${url}`);
    });
    render(<SymbolCoverageMatrix entries={entries} />);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => screen.queryByText('group_sma') !== null);
    fireEvent.click(screen.getByText('group_sma'));
    await advanceUntil(() => count((c) => isStatus(c.url, 'd1')) >= 1);
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ })); // 主表重算
    drillDone = true;
    await advanceUntil(() => groupPosts === 2 && count((c) => isResult(c.url, 'g2')) >= 1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(count((c) => isResult(c.url, 'd1'))).toBe(0);
    expect(screen.queryByText('feat_0')).toBeNull();
    expect(screen.queryByText(/下鑽 Group/)).toBeNull();
  });

  it('兩次讀頁回應反序：只採用最後一次讀頁之結果（審碼 r178）', async () => {
    const slow = deferred<unknown>();
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isPost(url, 'group-feature-coverage')) return { task_id: 'd1' };
      if (isStatus(url, 'g1')) return statusBody('g1', 'completed', 10, 10);
      if (isStatus(url, 'd1')) return statusBody('d1', 'completed', 30, 30);
      if (isResult(url, 'g1')) return groupResult;
      if (isResult(url, 'd1')) {
        const q = new URL(url).searchParams;
        const page = drillPage(Number(q.get('offset')), Number(q.get('limit')));
        return Number(q.get('offset')) === 501 ? slow.promise.then(() => page) : page;
      }
      throw new Error(`unexpected ${url}`);
    });
    const { container } = render(<SymbolCoverageMatrix entries={entries} />);
    const input = container.querySelector('input[type="number"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '501' } });
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => screen.queryByText('group_sma') !== null);
    fireEvent.click(screen.getByText('group_sma'));
    await advanceUntil(() => screen.queryByText('feat_0') !== null);
    fireEvent.click(screen.getByRole('button', { name: /下一頁/ })); // offset 501（延遲）
    fireEvent.change(input, { target: { value: '100' } });
    fireEvent.click(screen.getByRole('button', { name: /下一頁/ })); // offset 100（先回）
    await advanceUntil(() => screen.queryByText('feat_100') !== null);
    slow.resolve(undefined); // 舊讀頁晚到
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(screen.queryByText('feat_100')).not.toBeNull();
    expect(screen.queryByText('feat_501')).toBeNull();
  });

  it('下鑽每頁筆數輸入無 max、接受越舊界之 501（不 clamp 至 500）', () => {
    stubFetch(() => ({}));
    const { container } = render(<SymbolCoverageMatrix entries={entries} />);
    const input = container.querySelector('input[type="number"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.hasAttribute('max')).toBe(false);
    fireEvent.change(input, { target: { value: '501' } });
    expect(input.value).toBe('501');
    expect(input.validity.rangeOverflow).toBe(false);
  });

  it('下鑽：請求本體無逾時秒數欄與 top_n；結果以 offset／limit 分頁讀取、顯示 total、下一頁／上一頁帶 offset', async () => {
    stubFetch((url) => {
      if (isPost(url, 'group-coverage')) return { task_id: 'g1' };
      if (isPost(url, 'group-feature-coverage')) return { task_id: 'd1' };
      if (isStatus(url, 'g1')) return statusBody('g1', 'completed', 10, 10);
      if (isStatus(url, 'd1')) return statusBody('d1', 'completed', 30, 30);
      if (isResult(url, 'g1')) return groupResult;
      if (isResult(url, 'd1')) {
        const q = new URL(url).searchParams;
        return drillPage(Number(q.get('offset')), Number(q.get('limit')));
      }
      throw new Error(`unexpected ${url}`);
    });
    const { container } = render(<SymbolCoverageMatrix entries={entries} />);
    const input = container.querySelector('input[type="number"]') as HTMLInputElement;
    fireEvent.change(input, { target: { value: '501' } });
    fireEvent.click(screen.getByRole('button', { name: /計算 Group Coverage/ }));
    await advanceUntil(() => screen.queryByText('group_sma') !== null);
    fireEvent.click(screen.getByText('group_sma'));
    await advanceUntil(() => count((c) => isPost(c.url, 'group-feature-coverage')) === 1);
    const post = calls.find((c) => isPost(c.url, 'group-feature-coverage'))!;
    expect(post.body!.group_name).toBe('group_sma');
    expect(Object.keys(post.body!)).not.toContain(REMOVED_TIME_FIELD);
    expect(Object.keys(post.body!)).not.toContain('top_n');

    const pageReqs = () => calls.filter((c) => isResult(c.url, 'd1')).map((c) => new URL(c.url).searchParams);
    await advanceUntil(() => pageReqs().length >= 1 && screen.queryByText('feat_0') !== null);
    expect([pageReqs()[0].get('offset'), pageReqs()[0].get('limit')]).toEqual(['0', '501']);
    expect(bodyText()).toContain(String(DRILL_TOTAL));
    expect(screen.queryByText('feat_501')).toBeNull();

    fireEvent.click(screen.getByRole('button', { name: /下一頁/ }));
    await advanceUntil(() => screen.queryByText('feat_501') !== null);
    const second = pageReqs()[pageReqs().length - 1];
    expect([second.get('offset'), second.get('limit')]).toEqual(['501', '501']);

    fireEvent.click(screen.getByRole('button', { name: /上一頁/ }));
    await advanceUntil(() => screen.queryByText('feat_0') !== null);
    const back = pageReqs()[pageReqs().length - 1];
    expect([back.get('offset'), back.get('limit')]).toEqual(['0', '501']);
    // 讀頁只呼叫結果端點，不重送計算請求
    expect(count((c) => isPost(c.url, 'group-feature-coverage'))).toBe(1);
  });
});
