/**
 * GAP-3 UX **Task 7.7** 之前端欄（`--run runInfoTimeRange`；SPEC「backend 全綠不算完成」）。
 *
 * 🔴 為什麼一定要有這兩條：Task 7.7 的失敗形態是**靜默的**——
 * 只改 `types.ts` 的型別宣告，`npm run build` 會過、vitest 也會過（vitest 是 transpile-only），
 * 但 `time_range` 根本沒被後端帶出來，前端拿到的永遠是 `undefined`。
 * 型別宣告不會讓任何東西在執行期出現。所以第二條**必須**驗真的解析過的回應。
 */
import { describe, expect, it } from 'vitest';
import type { RunInfo } from './types';

describe('Task 7.7 — RunInfo.time_range', () => {
  it('① 型別含 `time_range`，形狀為 `{start: string|null, end: string|null}`', () => {
    // 型別層：能賦值即代表宣告存在且形狀相符（型別錯會在 `tsc --noEmit` 紅）。
    const run: Pick<RunInfo, 'time_range'> = {
      time_range: { start: '1704067200', end: '1777330800' },
    };
    expect(run.time_range?.start).toBe('1704067200');
    expect(run.time_range?.end).toBe('1777330800');

    // 🔴 值為**字串**不是數字：現存 manifest 皆為 epoch **秒之數字字串**。
    // 前端不得自行轉型別或比大小——涵蓋判定一律由後端 gate 做。
    expect(typeof run.time_range?.start).toBe('string');

    // legacy run：兩端皆 null（後端判 feature_coverage_unknown_legacy_run）
    const legacy: Pick<RunInfo, 'time_range'> = { time_range: { start: null, end: null } };
    expect(legacy.time_range?.start).toBeNull();

    // 缺鍵之 legacy run（實掃 14 份 manifest 有 2 份如此）
    const absent: Pick<RunInfo, 'time_range'> = {};
    expect(absent.time_range).toBeUndefined();
  });

  it('② `/features/runs` 之回應經前端解析後 `runs[0].time_range` **不為 undefined**（證明鍵真的傳到前端）', async () => {
    // 🔴 這條測的是**接線**不是型別：模擬後端實際回應（含 time_range），
    //    經與生產路徑相同的 `res.json()` 解析後，該鍵必須還在。
    //    若哪天有人在 `RunInfo` 之 pydantic model 拿掉該欄，後端會**靜默濾掉**它，
    //    此處解析出來就會是 undefined ⇒ 本條紅。
    const payload = [{
      symbol: 'ETHUSDT',
      timeframe: '1h',
      config_hash: 'abc123',
      active: true,
      browse_task_id: 'browse_ETHUSDT_1h_abc123',
      browse_ready: true,
      time_range: { start: '1704067200', end: '1777330800' },
    }];
    const res = new Response(JSON.stringify(payload), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    });
    const runs = (await res.json()) as RunInfo[];

    expect(runs[0].time_range).not.toBeUndefined();
    expect(runs[0].time_range).toEqual({ start: '1704067200', end: '1777330800' });
  });

  it('③ **over 向對照**：後端回 legacy 形時前端不得當成「沒有這個欄位」', async () => {
    // 🔴 `{start: null, end: null}` 與「鍵不存在」在後端是**同一種處置**，
    //    但在前端是兩個不同的值——把前者誤讀成後者，畫面就會顯示「未知」而不是「舊 run」。
    const res = new Response(JSON.stringify([{ time_range: { start: null, end: null } }]), {
      status: 200, headers: { 'content-type': 'application/json' },
    });
    const runs = (await res.json()) as Partial<RunInfo>[];
    expect(runs[0].time_range).not.toBeUndefined();
    expect(runs[0].time_range).toEqual({ start: null, end: null });
  });
});
