/**
 * GAP-3 UX Task 3.3 —— 已被引用批次之警語（vitest selector：`eventBatchDeleteWarning`）。
 *
 * 邊界①：被引用批次之確認框 `toContain('引用它的分析結果將無法重現')`。
 * 邊界②：未被引用者**不顯示**該警語（防恆顯示而失去鑑別力）。
 *
 * 🔴 警語字面在本檔**硬寫**，不從元件 import 常數——import 的話兩邊會一起動，
 *    mutation 改壞字面時本檔照樣綠（§6.1 之第 4 種假綠）。
 * 🔴 判準之**資料來源**（`@/lib/eventBatchReferences`）為 PENDING-RULING；本檔驗的是
 *    「有引用 ⇒ 顯示／無引用 ⇒ 不顯示」這個對應關係本身，來源若經三家改裁，本檔不必動。
 * 🔴 三件套 RECHECK：①page runtime（真的 render page）②malformed 輸入 probe
 *    ③逐批之值不得塌平（兩批共存時，只有被引用的那一批顯示）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import DataPreparationPage from '@/app/data-preparation/page';
import { referencedImportIds } from '@/lib/eventBatchReferences';
import type { EventImportSummary } from '@/lib/types';

const WARNING = '引用它的分析結果將無法重現';
const STORAGE_KEY = 'gap3.eventBatchReferences.v1';

function batch(id: string, n: number): EventImportSummary {
  return {
    import_id: id,
    source_name: `${id}.csv`,
    upload_sha256: 'a'.repeat(64),
    imported_at: '2026-08-26T00:00:00Z',
    n_events: n,
    symbols: ['ETHUSDT'],
    timeframes: ['1h'],
    direction: 'long',
    scenario: 'C',
  };
}

const REFERENCED = batch('20260826T000000Z-referenc', 3);
const FRESH = batch('20260826T000000Z-freshbat', 5);

let deleteCount: number;

function installFetch(imports: EventImportSummary[]) {
  deleteCount = 0;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      if (method === 'DELETE') {
        deleteCount += 1;
        return new Response(null, { status: 204 });
      }
      if (url.includes('/case/events')) {
        return new Response(JSON.stringify({ total: imports.length, imports }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ total: 0 }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }),
  );
}

/** 種下引用紀錄。刻意直接寫 storage 而非呼叫 `recordImportReference`，以免與被測來源自我配對。 */
function seedReferences(ids: string[]) {
  globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

async function openDialogFor(b: EventImportSummary) {
  const opener = await screen.findByTestId(`event-batch-delete-open-${b.import_id}`);
  fireEvent.click(opener);
  return screen.findByTestId('event-batch-delete-dialog');
}

beforeEach(() => {
  globalThis.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('GAP-3 Task 3.3 已被引用批次之警語', () => {
  it('① 被引用之批 ⇒ 確認框含警語字面', async () => {
    seedReferences([REFERENCED.import_id]);
    installFetch([REFERENCED]);
    render(<DataPreparationPage />);

    const dialog = await openDialogFor(REFERENCED);
    expect(dialog.textContent).toContain(WARNING);
  });

  it('② 未被引用之批 ⇒ **不顯示**該警語（鑑別力）', async () => {
    installFetch([FRESH]);
    render(<DataPreparationPage />);

    const dialog = await openDialogFor(FRESH);
    expect(dialog.textContent).not.toContain(WARNING);
    expect(screen.queryByTestId('event-batch-delete-referenced-warning')).toBeNull();
  });

  it('③ 🔴 逐批不得塌平：兩批共存時，只有被引用的那一批顯示警語', async () => {
    seedReferences([REFERENCED.import_id]);
    installFetch([REFERENCED, FRESH]);
    render(<DataPreparationPage />);

    const refDialog = await openDialogFor(REFERENCED);
    expect(refDialog.textContent).toContain(WARNING);

    fireEvent.click(screen.getByTestId('event-batch-delete-cancel'));
    await waitFor(() => expect(screen.queryByTestId('event-batch-delete-dialog')).toBeNull());

    const freshDialog = await openDialogFor(FRESH);
    expect(freshDialog.textContent).not.toContain(WARNING);
  });

  it('④ 有警語時**仍可刪**——警語不改動確認流程之控制流', async () => {
    seedReferences([REFERENCED.import_id]);
    installFetch([REFERENCED]);
    render(<DataPreparationPage />);

    const dialog = await openDialogFor(REFERENCED);
    expect(dialog.textContent).toContain(WARNING);
    // 3.2 邊界①之回歸：警語在場時，未確認仍然 0 次
    expect(deleteCount).toBe(0);

    fireEvent.click(screen.getByTestId('event-batch-delete-confirm'));
    await waitFor(() => expect(deleteCount).toBe(1));
  });

  it('⑤ malformed 引用紀錄 probe：畸形形狀／型別冒充 ⇒ 一律當作未被引用，不崩、不誤顯示', async () => {
    const malformed = ['not json at all', '{"not":"an array"}', '42', '[123, null, {"import_id":"x"}]', '[]'];
    for (const raw of malformed) {
      globalThis.localStorage.setItem(STORAGE_KEY, raw);
      installFetch([FRESH]);
      render(<DataPreparationPage />);
      const dialog = await openDialogFor(FRESH);
      expect(dialog.textContent, `malformed=${raw}`).not.toContain(WARNING);
      cleanup();
    }
  });

  it('⑤b 型別冒充之單元層斷言：讀出之集合只含字串，非字串項一律被濾掉', () => {
    // 🔴 為何另加這條：⑤ 只驗「畫面沒被誤導」，而「整包信任」在那個路徑上**不可觀測**
    //    （Set 之 has() 為嚴格比較，塞進去的整數／物件不會讓字串 id 命中）⇒ 錄到空紅集合。
    //    型別過濾之實際作用在**讀出之集合本身**，故在此直接下斷言。
    globalThis.localStorage.setItem(STORAGE_KEY, JSON.stringify(['ok-id', 123, null, { import_id: 'x' }, '']));
    const ids = referencedImportIds();
    expect([...ids]).toEqual(['ok-id']);
    expect(ids.size).toBe(1);
  });

  it('⑥ 引用紀錄含其他批之 id ⇒ 本批不得因此顯示警語（不是「有任何紀錄就顯示」）', async () => {
    seedReferences([REFERENCED.import_id, 'some-other-batch']);
    installFetch([FRESH]);
    render(<DataPreparationPage />);

    const dialog = await openDialogFor(FRESH);
    expect(dialog.textContent).not.toContain(WARNING);
  });
});
