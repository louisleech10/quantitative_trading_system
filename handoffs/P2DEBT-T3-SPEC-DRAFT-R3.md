# P2 債票 3 — frontend feature-factory 測試檔 TypeScript 錯誤清零 — SPEC 初稿 R3

> 來源：HANDOFF 票 3 + `templates/SPEC_TEMPLATE.md`  
> 日期：2026-07-11　|　起草：Composer　|　task-id：`p2debt-t3`  
> 狀態：**初稿 R3**（R2 Gate C 假 FAIL 修正；待 Grok + Codex 雙家族 adversarial 審後正式化；起草人不得自審）

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
- **diff gate（scope）**：派工前擷取 pre-dirty（`git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t3-pre-dirty.txt`）；完工後取 post-dirty 同法；以 `comm -13 /tmp/p2debt-t3-pre-dirty.txt /tmp/p2debt-t3-post-dirty.txt | sort -u` 得 **delta**（post 相對 pre 新增/變更路徑）；delta 與五檔 whitelist 比對時**兩邊皆須 `sort -u`**，且須精確相等（見 §V scope gate）；**不得**用未扣 pre-dirty baseline 的全域 `git diff --name-only` 當驗收（壞基線實跑 7 行外檔，見 §V receipt）。

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
  2. `cd frontend && npm test -- --run src/components/feature-factory/__tests__/run_lifecycle.test.tsx src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx src/hooks/useFeatureFactory.batchDate.test.ts src/lib/runExplorer.test.ts src/store/featureFactoryStore.test.ts` → **31 passed, 0 failed**（與基線一致；**31 = vitest 測試數**，非 `expect()` 站點數）。
  3. **scope gate（pre-dirty delta vs 五檔 whitelist；可執行）** — 對齊 `docs/P2DEBT_T1_GOVFIX_TODO.md` Final Acceptance §2：
     ```bash
     # 派工前（一次，實作開始前）：
     git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t3-pre-dirty.txt
     # Composer 實跑 2026-07-11：pre-dirty 15 行（含 .claude/*、handoffs/*×8、tests/golden/*×5；HEAD=47ac7b3ae6c62c998aee7c534dd2eba4dad18dca）
     # 壞基線說明：全域 git diff --name-only 現有 7 行外檔（.claude/*×2、tests/golden/*×5），故 R1 之「僅含五測試檔」驗收不可執行。
     #
     # 完工後比對（五檔 whitelist oracle；delta = post dirty MINUS pre dirty）：
     git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t3-post-dirty.txt
     comm -13 /tmp/p2debt-t3-pre-dirty.txt /tmp/p2debt-t3-post-dirty.txt | sort -u > /tmp/p2debt-t3-delta-dirty.txt
     printf '%s\n' \
       frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
       frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
       frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
       frontend/src/lib/runExplorer.test.ts \
       frontend/src/store/featureFactoryStore.test.ts | sort -u > /tmp/p2debt-t3-whitelist.txt
     sort -u /tmp/p2debt-t3-whitelist.txt > /tmp/p2debt-t3-whitelist-sorted.txt
     sort -u /tmp/p2debt-t3-delta-dirty.txt > /tmp/p2debt-t3-delta-dirty-sorted.txt
     diff -u /tmp/p2debt-t3-whitelist-sorted.txt /tmp/p2debt-t3-delta-dirty-sorted.txt
     # 壞基線（無實作變更）誠實預期：post=pre，delta-dirty 0 行；diff 顯示 whitelist 五檔全缺；exit 1。
     # Composer 實跑 2026-07-11 壞基線：wc -l /tmp/p2debt-t3-bad-delta.txt → 0；diff rc=1。
     # R2 synthetic simulation（pre + 五檔 → sim-post；全在 /tmp）：
     #   cat /tmp/p2debt-t3-pre-dirty.txt /tmp/p2debt-t3-whitelist.txt | sort -u > /tmp/p2debt-t3-sim-post-dirty.txt
     #   comm -13 /tmp/p2debt-t3-pre-dirty.txt /tmp/p2debt-t3-sim-post-dirty.txt | sort -u > /tmp/p2debt-t3-sim-delta.txt
     #   diff -u /tmp/p2debt-t3-whitelist-sorted.txt /tmp/p2debt-t3-sim-delta.txt → rc=0；wc -l /tmp/p2debt-t3-sim-delta.txt → 5
     # 真實完工驗收預期：delta-dirty 精確 5 行（= whitelist）；排序後 diff 無輸出（exit 0）
     ```
- **防假綠（可執行 gate；區分測試數 vs expect 站點）**：
  - **基線計數（派工前一次擷取）**：`rg -c '\bexpect\('` 五檔合計 **87** 站點（非 31）；per-file：`run_lifecycle.test.tsx:20`、`RunManagerPanel.batchDeleteWhole.test.tsx:10`、`useFeatureFactory.batchDate.test.ts:4`、`runExplorer.test.ts:9`、`featureFactoryStore.test.ts:44`。
  - **FACT-RECEIPT: chair-run 2026-07-11, Gate A=0 Gate B=87 (codex sandbox hang, delegated)**
  - **Gate A — 禁靜默型別繞過（負向掃描，預期 0 命中）**：
    ```bash
    rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' \
      frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
      frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
      frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
      frontend/src/lib/runExplorer.test.ts \
      frontend/src/store/featureFactoryStore.test.ts | wc -l
    # Composer 實跑 2026-07-11 壞基線：0（rc=0）
    # 完工驗收：須仍為 0；任何新增命中 → FAIL
    ```
  - **Gate B — expect 站點數不變（預期 87）**：
    ```bash
    rg -c '\bexpect\(' \
      frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
      frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
      frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
      frontend/src/lib/runExplorer.test.ts \
      frontend/src/store/featureFactoryStore.test.ts | awk -F: '{s+=$2} END {print s}'
    # Composer 實跑 2026-07-11 壞基線：87
    # 完工驗收：須仍為 87（刪弱斷言會降低此數）
    ```
  - **Gate C — expect 斷言行為不變（雙腿：機械 per-file 計數 + 審查者 assertion body diff）**  
    **R2 缺陷（Codex BLOCK）**：pre/post `rg -n expect` raw diff 對**合法型別補行**（line-number shift、非 expect 行插入）產生假 FAIL，即使各 `expect(...)` 文本與行為未變。  
    **SPEC amendment 規則**：任何**合意**的 per-file `expect()` 計數變更（新增/刪除斷言）**必須**在本 SPEC §A 或 PR 描述加 **SPEC amendment note**，列明新 per-file baseline；未修訂 SPEC 而計數變動 → mechanical gate **FAIL**（視為刪弱或未授權改動）。
    - **Leg 1 — Mechanical gate（自動 PASS/FAIL）**：per-file 計數 pre vs post 全等 ⇒ PASS。
      ```bash
      # 派工前（與實作同一 shell session 或存檔至 /tmp）：
      rg -c '\bexpect\(' \
        frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
        frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
        frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
        frontend/src/lib/runExplorer.test.ts \
        frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-pre-expect-counts.txt
      # Composer 實跑 2026-07-11 壞基線 pre-expect-counts.txt：
      # frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx:10
      # frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx:20
      # frontend/src/hooks/useFeatureFactory.batchDate.test.ts:4
      # frontend/src/lib/runExplorer.test.ts:9
      # frontend/src/store/featureFactoryStore.test.ts:44
      #
      # 完工後：
      rg -c '\bexpect\(' \
        frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
        frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
        frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
        frontend/src/lib/runExplorer.test.ts \
        frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-post-expect-counts.txt
      diff -u /tmp/p2debt-t3-pre-expect-counts.txt /tmp/p2debt-t3-post-expect-counts.txt
      # Composer 實跑 2026-07-11（pre=post 壞基線）：rc=0、無 diff 輸出
      # 完工驗收：rc=0；任一 per-file 計數變動且無 SPEC amendment note → FAIL
      ```
    - **Leg 2 — Reviewer leg（人工/adversarial 審查；非單獨 auto-block）**：assertion **body** diff（`rg -N` 不含行號，僅 `file:expect(...)` 文本）；審查者須確認 diff 非空時是否為刪弱/改期望值。
      ```bash
      # 派工前：
      rg -N '\bexpect\(' \
        frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
        frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
        frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
        frontend/src/lib/runExplorer.test.ts \
        frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-pre-expect-bodies.txt
      # Composer 實跑 2026-07-11：wc -l /tmp/p2debt-t3-pre-expect-bodies.txt → 87
      #
      # 完工後：
      rg -N '\bexpect\(' \
        frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
        frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
        frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
        frontend/src/lib/runExplorer.test.ts \
        frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-post-expect-bodies.txt
      diff -u /tmp/p2debt-t3-pre-expect-bodies.txt /tmp/p2debt-t3-post-expect-bodies.txt
      # Composer 實跑 2026-07-11（pre=post 壞基線）：rc=0、無 diff 輸出
      # 合法型別-only 變更（fixture/helper 補行、expect 行文本不變）：預期 rc=0
      # expect 文本變更：diff 非空 → adversarial 審查者須簽核或 BLOCK
      ```
  - 允許同檔**非** `expect` 行之型別補欄（fixture/helper/mock 簽名）；**禁止**改動 `expect(...)` 行本身（Leg 2 diff 須為空，或審查者明示核准）。
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

---

R2-CLOSURE: BLOCKER-1→§V 防假綠：區分 31 vitest tests vs 87 `expect()` 站點；新增 Gate A（禁 `@ts-ignore`/`@ts-expect-error`/`as any`/`as unknown as` 負向掃描，預期 0）、Gate B（合計 87）、Gate C（pre/post `rg -n expect` diff rc=0）；移除 R1「31 條斷言」錯稱
R2-CLOSURE: BLOCKER-2→§C diff gate + §V item 3：改 pre-dirty snapshot + `comm -13` delta vs 五檔 whitelist（對齊 P2DEBT_T1 Final Acceptance §2）；附壞基線（delta 0、diff rc=1）與 synthetic good（delta 5、diff rc=0）實跑 receipt；廢止全域 `git diff --name-only` 當 scope 驗收
R3-CLOSURE: Gate C 重設計——廢止 R2 `rg -n expect` raw diff（line-number shift 假 FAIL）；改 Leg1 機械 gate = per-file `rg -c expect` pre/post diff rc=0 + 合意計數變更須 SPEC amendment note；Leg2 審查者 gate = `rg -N expect` assertion body diff（合法型別-only 變更預期 rc=0）；嵌入 chair FACT-RECEIPT Gate A=0 Gate B=87
