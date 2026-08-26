/**
 * GAP-3 UX Task 3.2 —— 前端刪除鈕與二次確認（vitest selector：`eventBatchDeleteConfirm`）。
 *
 * 邊界①：未確認時 `fetch` call count `== 0`。
 * 邊界②：只在批列表提供（其他頁面無入口）。
 * 另釘：確認框顯示之筆數與匯入時間 `==` 批列表之值；不得以 `window.confirm` 帶過。
 *
 * 🔴 一律**執行期**證據（§6.2）：
 *  - 真的 render page、真的按鈕；不看原始碼長相。
 *  - **不 mock `@/lib/api`**——B4 R1 之假綠正是「mock 掉 api helper 後只數 `global.fetch`」。
 *    這裡數的是**真實 `fetch`** 上 method `=== 'DELETE'` 的呼叫，走的是真的 helper。
 *  - 確認鍵**刻意保持可按**（B4 教訓），故「未確認 ⇒ 0 次」不是靠 `disabled` 得來的。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DataPreparationPage from '@/app/data-preparation/page';
import type { EventImportSummary } from '@/lib/types';

const BATCH: EventImportSummary = {
  import_id: '20260826T000000Z-aaaaaaaa',
  source_name: 'unit.csv',
  upload_sha256: 'a'.repeat(64),
  imported_at: '2026-08-26T00:00:00Z',
  n_events: 7,
  symbols: ['ETHUSDT'],
  timeframes: ['1h'],
  direction: 'long',
  scenario: 'C',
};

/** 記錄每一次 fetch 的 (url, method)，供逐條斷言。 */
let calls: Array<{ url: string; method: string }>;

function deleteCalls() {
  return calls.filter((c) => c.method === 'DELETE');
}

function installFetch(deleteStatus = 204) {
  calls = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      calls.push({ url, method });
      if (method === 'DELETE') {
        return new Response(null, { status: deleteStatus });
      }
      if (url.includes('/case/events')) {
        return new Response(JSON.stringify({ total: 1, imports: [BATCH] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      // /case/list 之案例數
      return new Response(JSON.stringify({ total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }),
  );
}

beforeEach(() => {
  globalThis.localStorage?.clear();
  installFetch();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderWithBatch() {
  render(<DataPreparationPage />);
  await screen.findByTestId(`event-batch-delete-open-${BATCH.import_id}`);
}

describe('GAP-3 Task 3.2 事件批刪除之二次確認', () => {
  it('① 未確認 ⇒ DELETE 之 fetch call count == 0（開了確認框、按了取消，都不得發出請求）', async () => {
    await renderWithBatch();

    // 尚未開確認框
    expect(deleteCalls()).toHaveLength(0);

    // 開了確認框 —— 仍不得發請求
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    expect(await screen.findByTestId('event-batch-delete-dialog')).toBeTruthy();
    expect(deleteCalls()).toHaveLength(0);

    // 按取消 —— 確認框關閉，仍不得發請求
    fireEvent.click(screen.getByTestId('event-batch-delete-cancel'));
    await waitFor(() => expect(screen.queryByTestId('event-batch-delete-dialog')).toBeNull());
    expect(deleteCalls()).toHaveLength(0);
  });

  it('② 確認框顯示之筆數與匯入時間 == 批列表之值', async () => {
    await renderWithBatch();
    const row = screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`).closest('li');
    expect(row).not.toBeNull();
    const rowText = row!.textContent ?? '';
    // 前置：列上確實帶著這兩個值（否則本斷言退化為「兩邊都空」）
    expect(rowText).toContain(String(BATCH.n_events));
    expect(rowText).toContain(BATCH.imported_at);

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');

    expect(screen.getByTestId('event-batch-delete-n-events').textContent).toBe(String(BATCH.n_events));
    expect(screen.getByTestId('event-batch-delete-imported-at').textContent).toBe(BATCH.imported_at);
    expect(screen.getByTestId('event-batch-delete-import-id').textContent).toBe(BATCH.import_id);
  });

  it('③ 確認 ⇒ 發出且只發出一次 DELETE，URL 指向該批', async () => {
    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');

    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));

    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    expect(deleteCalls()[0].url).toContain(`/case/events/${BATCH.import_id}`);
    // 刪除全部之形狀不得出現
    expect(deleteCalls()[0].url.endsWith('/case/events')).toBe(false);
  });

  it('④ 不得以 window.confirm 帶過：確認框為可測元件，且全程未呼叫 window.confirm', async () => {
    const confirmSpy = vi.fn(() => true);
    vi.stubGlobal('confirm', confirmSpy);
    installFetch();

    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));

    expect(confirmSpy).not.toHaveBeenCalled();
  });

  it('⑤ 🔴 確認鍵刻意保持可按（非 disabled）——否則 ①「0 次」會是恆真的假綠', async () => {
    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    const confirmBtn = (await screen.findByTestId('event-batch-delete-confirm')) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(false);
  });

  it('⑦ 🔴 R1 群集 B：連點兩次確認 ⇒ 仍只發出一次 DELETE（防重入）', async () => {
    // `CODEX-R1-P1-02`：確認鍵刻意保持可按（B4 教訓），因此重入必須由 handler 自己擋。
    // 用**延遲**的 DELETE 回應把「在途」這段時間拉開，再於同一 tick 內連點兩次。
    let release: (() => void) | null = null;
    const gate = new Promise<void>((r) => { release = () => r(); });
    calls = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? 'GET').toUpperCase();
        calls.push({ url, method });
        if (method === 'DELETE') {
          await gate;
          return new Response(null, { status: 204 });
        }
        if (url.includes('/case/events')) {
          return new Response(JSON.stringify({ total: 1, imports: [BATCH] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ total: 0 }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    const confirmBtn = (await screen.findByTestId('event-batch-delete-confirm')) as HTMLButtonElement;

    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn);

    // 確認鍵**仍然可按**——防重入不得靠 disabled（否則 ①「0 次」會變恆真的假綠）
    expect(confirmBtn.disabled).toBe(false);
    expect(deleteCalls()).toHaveLength(1);

    release!();
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
  });

  it('⑧ 🔴 同一 tick 內連續兩次點擊（不經 act flush）⇒ 仍只發出一次 DELETE', async () => {
    // 為什麼要這條：⑦ 用 `fireEvent`，而 testing-library 會把每次事件包進 `act()` 並**立即 flush**
    // state ⇒ 第二次點擊時 `deleteBusy` 已是 true，**用 state 守也會過**。
    // 也就是說 ⑦ 分不出「ref 守」和「state 守」。主委原本宣稱「state 守不住」，
    // 而 mutation `R1B-M2` 錄到**空紅集合**，正是那個宣稱在 ⑦ 之下不成立的證據。
    // 本條改用原生 `.click()`（不經 act flush）製造真正的同一 tick 重入，
    // 這才是 ref 與 state 會分岔的地方。
    let release: (() => void) | null = null;
    const gate = new Promise<void>((r) => { release = () => r(); });
    calls = [];
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        const method = (init?.method ?? 'GET').toUpperCase();
        calls.push({ url, method });
        if (method === 'DELETE') {
          await gate;
          return new Response(null, { status: 204 });
        }
        if (url.includes('/case/events')) {
          return new Response(JSON.stringify({ total: 1, imports: [BATCH] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ total: 0 }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    const confirmBtn = (await screen.findByTestId('event-batch-delete-confirm')) as HTMLButtonElement;

    // 🔴 同一同步區塊、不經 act：兩次點擊之間**沒有** re-render，state 仍是舊值
    confirmBtn.click();
    confirmBtn.click();

    expect(deleteCalls()).toHaveLength(1);

    release!();
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
  });

  it('⑥ 刪除失敗 ⇒ 確認框留著並顯示錯誤，不假成功', async () => {
    installFetch(404);
    await renderWithBatch();
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));

    await screen.findByTestId('event-batch-delete-error');
    expect(screen.getByTestId('event-batch-delete-dialog')).toBeTruthy();
  });
});
