# P2 債票 3 — frontend feature-factory 測試檔 TypeScript 錯誤清零 — SPEC 初稿 R1

> 來源：HANDOFF 票 3 + `templates/SPEC_TEMPLATE.md`  
> 日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t3`  
> 狀態：**初稿**（待 Grok + Codex 雙家族 adversarial 審後正式化；起草人不得自審）

---

## §RISK 風險分級

- **大小**：**小** — 僅 5 個測試檔、11 處 `tsc` 診斷；不動 `src/` 生產程式、不動 `types.ts`。
- **命中高風險原則**：**none** — 不碰數值/ML/回測、不碰 API 契約執行路徑、無 schema/輸出大小變更。
- **RISK-HIT 宣告**：`RISK-HIT: none`
- **升級訊號（偵察結論）**：**無 production type 變更需求**。全部 11 錯誤根因為測試 fixture/helper 未對齊既有 `src/lib/types.ts`（`FeatureTask.error`、`CompletionQueueItem.source` 必填；本地 `response()` 簽名過窄；`vi.fn` 零參數推斷）。若實作期發現需改 `types.ts` / store / hook 生產碼 → **立即 BLOCK**，另立票，本票不得擴 scope。

## §A 假設與待使用者確認

- **FACT-RECEIPT 格式**：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（<who> 實跑 <date>）`

### 實跑 receipt（2026-07-11 Composer 實跑）

**基線 TypeScript**

- **已確認**：FACT-RECEIPT: `cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"` → 印出 `11`（Composer 實跑 2026-07-11）
- **已確認**：FACT-RECEIPT: `cd frontend && npx tsc --noEmit 2>&1` → 僅 5 個檔案報錯、合計 11 條 `error TS`；`frontend/src/components/feature-factory/__tests__/` 其餘 10 個 `.test.tsx` **零** tsc 錯誤（Composer 實跑 2026-07-11）

**完整錯誤清單（file:line — 根因類別 — test-only?）**

| # | file:line | TS | 根因類別 | 對齊的生產型別 | 修法域 |
|---|-----------|-----|----------|----------------|--------|
| 1 | `run_lifecycle.test.tsx:42` | TS2741 | `FeatureTask` 字面量缺必填 `error` | `FeatureTask.error: string \| null`（`types.ts:576`） | test-only |
| 2 | `run_lifecycle.test.tsx:88` | TS2741 | `completionQueue` 元素缺必填 `source` | `CompletionQueueItem.source: CompletionSource`（`types.ts:595`） | test-only |
| 3 | `RunManagerPanel.batchDeleteWhole.test.tsx:102` | TS2345 | `RunInfo[]` 傳入 `response(payload: Record<string, unknown>)` | GET `/runs` 實際 JSON 為陣列（store `as RunInfo[]`，`featureFactoryStore.ts:569`） | test-only（放寬本地 helper） |
| 4 | `RunManagerPanel.batchDeleteWhole.test.tsx:170` | TS2345 | 同上 | 同上 | test-only |
| 5–6 | `useFeatureFactory.batchDate.test.ts:55` | TS2493 + TS2339 | `vi.fn(async () => …)` 零參數 → `mock.calls[0][1]` 推斷為空 tuple / `never` | 真實 `fetch(url, init)` 第二參為 `RequestInit` | test-only（補 mock 簽名） |
| 7–8 | `useFeatureFactory.batchDate.test.ts:75` | TS2493 + TS2339 | 同上 | 同上 | test-only |
| 9 | `runExplorer.test.ts:51` | TS2352 | `as FeatureTask` 斷言；物件缺 `error`，與 `FeatureTask` 重疊不足 | `FeatureTask`（`types.ts:570-587`） | test-only（補欄位 + 移除不安全 cast） |
| 10 | `featureFactoryStore.test.ts:429` | TS2345 | `[]`（`never[]`）傳入 `response(…, Record<string, unknown>)` | GET `/runs` 回傳 `RunInfo[]` | test-only |
| 11 | `featureFactoryStore.test.ts:539` | TS2345 | 同上 | 同上 | test-only |

**生產型別錨點（唯讀核對）**

- **已確認**：FACT-RECEIPT: `rg -n "export interface FeatureTask|export interface CompletionQueueItem|export type CompletionSource" frontend/src/lib/types.ts` → `FeatureTask` L570、`CompletionSource` L592、`CompletionQueueItem` L594（Composer 實跑 2026-07-11）
- **已確認**：`FeatureTask` 必填欄：`task_id`, `status`, `progress`, `current_stage`, `completed_stages`, **`error`**；`CompletionQueueItem` 繼承 `RunIdentity` 並必填 **`source: 'single' \| 'batch'`**。

**基線測試（型別錯誤存在時仍綠）**

- **已確認**：FACT-RECEIPT: `cd frontend && npm test -- --run src/components/feature-factory/__tests__/run_lifecycle.test.tsx src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx src/hooks/useFeatureFactory.batchDate.test.ts src/lib/runExplorer.test.ts src/store/featureFactoryStore.test.ts` → 印出 `Test Files 5 passed (5)`、`Tests 31 passed (31)`（Composer 實跑 2026-07-11）——**tsc 紅與 vitest 綠可並存**；驗收須兩者皆過。

**測試 runner**

- **已確認**：FACT-RECEIPT: `rg '"test"' frontend/package.json` → `"test": "vitest run"`（Composer 實跑 2026-07-11）
- **已確認**：FACT-RECEIPT: `rg "include" frontend/vitest.config.ts` → `include: ['src/**/*.test.{ts,tsx}']`（Composer 實跑 2026-07-11）

- **待確認：無**
- **已確認結果**：2026-07-11 HANDOFF 票 3 — 修法=測試檔對齊既有生產型別；禁 `@ts-ignore` / `@ts-expect-error` / `as any` 靜默；禁改 `src/lib/types.ts` 與非測試 `src/`。

## §C 約束

- **硬邊界（允許改）**：僅下列 5 檔（本票 tsc 錯誤全集）：
  1. `frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx`
  2. `frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx`
  3. `frontend/src/hooks/useFeatureFactory.batchDate.test.ts`
  4. `frontend/src/lib/runExplorer.test.ts`
  5. `frontend/src/store/featureFactoryStore.test.ts`
- **禁止改**：`frontend/src/lib/types.ts`、一切非 `*.test.{ts,tsx}` 的 `frontend/src/**`、`momentum/`、`api/`、`data_cache/`、`scripts/`。
- 解耦 7 條：本票零觸後端。
- **防假綠**：
  - 禁止 `@ts-ignore`、`@ts-expect-error`、`as any`、雙重 `as unknown as T` 僅為過關。
  - 禁止刪弱/移除既有 `expect` 斷言以換綠燈。 VERIFY-EXEMPT:draft-superseded:p2debt-t3
  - 測試**行為**不變：僅補齊型別正確的 fixture / mock 簽名 / helper 簽名；不得改斷言期望值。
- **diff gate**：`git diff --name-only` 不得出現上述 5 檔以外之 `frontend/src/` 路徑（`package-lock` 等亦禁止）。

## §G Golden / Baseline

N/A — 見 §N（前端測試型別修復，無數值/feature golden）。

## §P Phase 與依賴

### Phase 1 — 測試型別對齊（依賴：無）

**Task 1.1 — `FeatureTask` / `CompletionQueueItem` fixture（2 檔、3 處）**  
檔案：`run_lifecycle.test.tsx`、`runExplorer.test.ts`

| 位置 | 改法 |
|------|------|
| `run_lifecycle.test.tsx:42` `const task: FeatureTask` | 補 `error: null`（與生產型別一致；`GenerationProgress` 接受完整 `FeatureTask`） |
| `run_lifecycle.test.tsx:88` `completionQueue: [run]` | 改為 `[{ ...run, source: 'single' as const }]`（對齊 store `enqueueCompletion` 預設 `source='single'`） |
| `runExplorer.test.ts:51-58` `currentTask` | 物件補 `error: null`；改 `const currentTask: FeatureTask = { … }` **移除** `as FeatureTask` |

- 驗證：`cd frontend && npx tsc --noEmit 2>&1 | rg "run_lifecycle|runExplorer"` → 0 行。
- 邊界：① `error: null` vs 省略 — 須顯式 `null`（必填欄）；② `source` 須為字面量 `'single'`，非任意字串。

**Task 1.2 — 本地 `response()` helper 簽名（2 檔、4 處 call site）**  
檔案：`RunManagerPanel.batchDeleteWhole.test.tsx`、`featureFactoryStore.test.ts`

| 現狀 | 改法 |
|------|------|
| `function response(status, payload: Record<string, unknown>)` | 改為 `payload: unknown`（`json: async () => payload` 不變）；準確反映 GET `/runs` 回傳陣列與物件 payload |
| L102、L170 `response(200, allRuns\|activeOnly)` | call site 不變（型別自動滿足） |
| L429、L539 `response(200, [])` | call site 不變；`[]` 作為 `RunInfo[]` mock 合法 |

- 驗證：`cd frontend && npx tsc --noEmit 2>&1 | rg "batchDeleteWhole|featureFactoryStore.test"` → 0 行。
- 邊界：① 物件 payload（bulk-delete、orphans）仍須通過；② 勿改 `response` 回傳形狀（避免改變測試行為）。

**Task 1.3 — `fetch` mock 簽名（1 檔、2 測試）**  
檔案：`useFeatureFactory.batchDate.test.ts`

| 現狀 | 改法 |
|------|------|
| `vi.fn(async () => response(200, …))` | 改 `vi.fn(async (_url: string, init?: RequestInit) => …)`（兩個 `it` 各一處） |
| `fetchMock.mock.calls[0]?.[1]?.body` | 簽名修正後 tuple 推斷正確；**保留**既有 `JSON.parse(String(…body))` 與 `start_date`/`end_date` 斷言 |

- 驗證：`cd frontend && npx tsc --noEmit 2>&1 | rg "batchDate"` → 0 行。
- 邊界：① mock 可不使用 `_url`；② 不得改 `startBatchGeneration` 呼叫參數或斷言邏輯。

- 不可做：改 `useFeatureFactory.ts` 生產 hook；改 `types.ts` 將 `error`/`source` 改 optional。

## §V 驗證策略與邊界測試目錄

- **mutation 條件**：N/A — 見 §N（型別對齊，不宣稱數值正確性）。
- **主驗收（可證偽）**：
  1. `cd frontend && npx tsc --noEmit` → exit 0；`grep -c "error TS"` = **0**（不得硬編碼「11」；以實跑為準）。
  2. `cd frontend && npm test -- --run src/components/feature-factory/__tests__/run_lifecycle.test.tsx src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx src/hooks/useFeatureFactory.batchDate.test.ts src/lib/runExplorer.test.ts src/store/featureFactoryStore.test.ts` → **31 passed, 0 failed**（與基線一致）。
  3. `git diff --name-only` 僅含上述 5 個測試檔（+ 本 SPEC/handoff 若 commit）。
- **防假綠**：實作後 diff 不得含 `@ts-ignore`/`@ts-expect-error`/`as any`；既有 31 條斷言須全保留（允許同檔非斷言之型別補欄）。
- **邊界目錄**（本任務適用）：  
  - [ ] 空陣列 mock `response(200, [])` 仍觸發 `fetchRuns` 路徑（store 測試已覆蓋）  
  - [ ] `completionQueue` 帶 `source` 後 422 retention 測試仍保留 queue 長度 1  
  - [ ] batch date 測試：有日期 / 無日期兩路徑 body 斷言不變  

## §R 回退

- 單一 commit（`fix:` 或 `test:` 前綴）可 `git revert` 還原；無 feature flag。
- tsc 或 vitest 任一 FAIL → 不 merge。

## §N N/A 登記

- **§G**：N/A — 本任務不碰數值/ML/feature 計算（僅 TS 測試 fixture）。
- **mutation**：N/A — 不宣稱演算法/資料正確性，僅型別與既有斷言保持。
