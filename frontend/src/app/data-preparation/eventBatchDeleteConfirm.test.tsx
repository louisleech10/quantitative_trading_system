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

  it('⑨ 🔴 R2 群集 G：確認 A 後取消、改開 B ⇒ A 的回應不得關掉 B 的確認框', async () => {
    // `CODEX-R2-P2-02`：`handleDeleteConfirmed` 捕獲了 importId，但 settle 時無條件
    // `setPendingDelete(null)` ⇒ A 的成功回應會把使用者正在看的 B 關掉；錯誤同理會寫進 B 的框。
    // 修法＝settle 前比對 `openBatchIdRef`。本條同時釘住「取消 A 之後仍可刪 B」（守衛以批為單位）。
    const BATCH_B: EventImportSummary = { ...BATCH, import_id: '20260826T000000Z-bbbbbbbb', n_events: 4 };
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
          if (url.includes(BATCH.import_id)) await gate;   // A 卡住
          return new Response(null, { status: 204 });
        }
        if (url.includes('/case/events')) {
          return new Response(JSON.stringify({ total: 2, imports: [BATCH, BATCH_B] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ total: 0 }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    render(<DataPreparationPage />);
    await screen.findByTestId(`event-batch-delete-open-${BATCH.import_id}`);

    // 確認 A（在途）→ 取消 → 開 B
    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    fireEvent.click(screen.getByTestId('event-batch-delete-cancel'));
    await waitFor(() => expect(screen.queryByTestId('event-batch-delete-dialog')).toBeNull());

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH_B.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    expect(screen.getByTestId('event-batch-delete-import-id').textContent).toBe(BATCH_B.import_id);

    // A 這時才回來——不得動到 B 的框
    release!();
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    expect(screen.getByTestId('event-batch-delete-dialog')).toBeTruthy();
    expect(screen.getByTestId('event-batch-delete-import-id').textContent).toBe(BATCH_B.import_id);

    // 且 B 仍刪得掉（守衛以批為單位，不是全域一把鎖）
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCalls()).toHaveLength(2));
    expect(deleteCalls()[1].url).toContain(BATCH_B.import_id);
  });

  it('⑩ 🔴 R3 群集 H：A 在途時開 B ⇒ B 的確認鍵不得顯示「刪除中…」', async () => {
    // `GROK-R3-P3-01`：`deleteBusy` 是單一布林，而在途的批可以有多個。
    // `closeDeleteDialog()` 不清 busy、`finally` 只在「開著的仍是這批」時清 ⇒ 取消後 busy 會殘留 true；
    // 產品碼靠 `openDeleteDialog()` 的 `setDeleteBusy(Set.has(id))` 同步修正，
    // 但**官方測試沒有任何一條斷言那行**——grok 實跑證明：拿掉它，confirm 套件仍全綠（廉價綠燈）。
    // 本條就是那行的回歸鎖：busy 必須是「**開著的那批**是否在途」的投影，不是殘值。
    const BATCH_B: EventImportSummary = { ...BATCH, import_id: '20260826T000000Z-cccccccc', n_events: 6 };
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
          if (url.includes(BATCH.import_id)) await gate;
          return new Response(null, { status: 204 });
        }
        if (url.includes('/case/events')) {
          return new Response(JSON.stringify({ total: 2, imports: [BATCH, BATCH_B] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ total: 0 }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    render(<DataPreparationPage />);
    await screen.findByTestId(`event-batch-delete-open-${BATCH.import_id}`);

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    // A 在途中：A 自己的確認鍵**應該**顯示刪除中（前置，確保下面的斷言不是恆真）
    expect(screen.getByTestId('event-batch-delete-confirm').textContent).toContain('刪除中');

    fireEvent.click(screen.getByTestId('event-batch-delete-cancel'));
    await waitFor(() => expect(screen.queryByTestId('event-batch-delete-dialog')).toBeNull());

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH_B.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    // 🔴 B 沒有在途 ⇒ 不得沿用 A 留下的 busy
    expect(screen.getByTestId('event-batch-delete-confirm').textContent).not.toContain('刪除中');

    release!();
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    expect(screen.getByTestId('event-batch-delete-confirm').textContent).not.toContain('刪除中');
  });

  it('⑪ 🔴 R4 群集 J：A 刪除失敗在途 → 取消 → 開 B ⇒ A 的錯誤不得畫進 B 的確認框', async () => {
    // `COMPOSER-R4-P3-01`／`GROK-R4-P3-01`（兩家**獨立**得出同一結論，各自實跑）：
    // R2 之 settle 修法在 `catch` 也加了 `openBatchIdRef === importId` 閘，但**沒有任何官方
    // 測試斷言那個閘**——拿掉後 confirm+warning 18 條仍全綠（與群集 H 同型的廉價綠燈）。
    // 🔴 這正是主委在 R4 brief 必答 3 自問的「errorMessage 是不是下一個 deleteBusy」：答案是是。
    // ⑥ 只驗**同批**失敗會顯示錯誤，涵蓋不到跨批的 settle 序列。
    const BATCH_B: EventImportSummary = { ...BATCH, import_id: '20260826T000000Z-dddddddd', n_events: 2 };
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
          if (url.includes(BATCH.import_id)) {
            await gate;
            return new Response(null, { status: 404 });   // A 在途、且**失敗**
          }
          return new Response(null, { status: 204 });
        }
        if (url.includes('/case/events')) {
          return new Response(JSON.stringify({ total: 2, imports: [BATCH, BATCH_B] }), {
            status: 200, headers: { 'Content-Type': 'application/json' },
          });
        }
        return new Response(JSON.stringify({ total: 0 }), {
          status: 200, headers: { 'Content-Type': 'application/json' },
        });
      }),
    );

    render(<DataPreparationPage />);
    await screen.findByTestId(`event-batch-delete-open-${BATCH.import_id}`);

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));

    fireEvent.click(screen.getByTestId('event-batch-delete-cancel'));
    await waitFor(() => expect(screen.queryByTestId('event-batch-delete-dialog')).toBeNull());

    fireEvent.click(screen.getByTestId(`event-batch-delete-open-${BATCH_B.import_id}`));
    await screen.findByTestId('event-batch-delete-dialog');
    expect(screen.queryByTestId('event-batch-delete-error')).toBeNull();

    // A 這時才失敗回來——錯誤不得落在 B 身上
    release!();
    await waitFor(() => expect(deleteCalls()).toHaveLength(1));
    expect(screen.getByTestId('event-batch-delete-import-id').textContent).toBe(BATCH_B.import_id);
    expect(screen.queryByTestId('event-batch-delete-error')).toBeNull();
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
