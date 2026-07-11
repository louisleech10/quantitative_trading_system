# P2 債票 3 — frontend feature-factory 測試檔 TypeScript 錯誤清零 — TODO(正式版)

> 定稿來源:handoffs/P2DEBT-T3-TODO-DRAFT-R3.md(R1 Composer→codex 2 finding→R2 Composer→codex BLOCK→斷路器換手 Grok R3)
> RECONCILE-STAMP:codex(R3 追認)=handoffs/P2DEBT-T3-TODO-REVERIFY-R3-RATIFY-codex.md;composer(2nd repro)=handoffs/P2DEBT-T3-R3-2ND-REPRO-composer.md;chair receipt=handoffs/P2DEBT-T3-R3-CHAIR-DELEGATED-RECEIPT.md
> task-id:p2debt-t3 | 正式化:2026-07-11 | 內容=R3 凍結稿,除本頭注外零改動

---

## 階段 1 — SPEC 索引與 100% 覆蓋追溯

| 類別 | ID / 項 | SPEC 原文節錄（≤30 字） | TODO 對應 |
|------|---------|------------------------|-----------|
| Task | 1.1 | `FeatureTask` / `CompletionQueueItem` fixture（2 檔、3 處） | Phase 1 → Task 1.1 + Task 1.2 |
| Task | 1.2 | 本地 `response()` helper 簽名（2 檔、4 處 call site） | Phase 1 → Task 1.3 + Task 1.4 |
| Task | 1.3 | `fetch` mock 簽名（1 檔、2 測試） | Phase 1 → Task 1.5 |
| 錯誤 | #1–#2 | `run_lifecycle.test.tsx:42,88` TS2741 | Task 1.1 |
| 錯誤 | #3–#4 | `RunManagerPanel.batchDeleteWhole.test.tsx:102,170` TS2345 | Task 1.3 |
| 錯誤 | #5–#8 | `useFeatureFactory.batchDate.test.ts:55,75` TS2493/TS2339 | Task 1.5 |
| 錯誤 | #9 | `runExplorer.test.ts:51` TS2352 | Task 1.2 |
| 錯誤 | #10–#11 | `featureFactoryStore.test.ts:429,539` TS2345 | Task 1.4 |
| 驗收 | §V 主驗收 ① | `npx tsc --noEmit` → 0 `error TS` | Final Acceptance §1 |
| 驗收 | §V 主驗收 ② | vitest 五檔 → 31 passed | Final Acceptance §2 |
| 驗收 | §V scope gate | `comm -13` delta vs 五檔 whitelist | Task 3.1 |
| Gate | Gate A | `rg_rc` 三極性（1=PASS） | Task 2.1 |
| Gate | Gate B | 合計 87 `expect(` 站點 | Task 2.2 |
| Gate | Gate C Leg1 | per-file `rg -c expect` pre/post diff rc=0 | Task 2.3 |
| Gate | Gate C Leg2 | `rg -N expect` assertion body diff（審查者） | Task 2.3 |
| RISK | RISK-HIT: none | 小任務；僅測試檔 | §0 |
| 禁止 | §C | 禁 `@ts-ignore`/`types.ts`/非測試 `src/` | §0 |
| **合計** | Task×3 + 錯誤×11 + Gate×3 + 驗收×3 | — | 全覆蓋 |

**基線 receipt（2026-07-11 Composer 實跑）**

- `cd frontend && npx tsc --noEmit 2>&1 | grep -c "error TS"` → `11`
- `cd frontend && npm test -- --run src/components/feature-factory/__tests__/run_lifecycle.test.tsx src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx src/hooks/useFeatureFactory.batchDate.test.ts src/lib/runExplorer.test.ts src/store/featureFactoryStore.test.ts` → `Test Files 5 passed (5)`、`Tests 31 passed (31)`
- Gate B 合計：`rg -c '\bexpect\('` 五檔 → `87`
- Gate C per-file：`run_lifecycle.test.tsx:20`、`RunManagerPanel.batchDeleteWhole.test.tsx:10`、`useFeatureFactory.batchDate.test.ts:4`、`runExplorer.test.ts:9`、`featureFactoryStore.test.ts:44`
- Gate A：`rg_rc=1` → `gate_a_exit=0`（現樹五檔無禁則 token）
- scope 壞基線：`wc -l /tmp/p2debt-t3-bad-delta-composer.txt` → `0`；`diff` whitelist vs bad-delta → `bad_diff_rc=1`
- scope synthetic good：`wc -l /tmp/p2debt-t3-sim-delta-composer.txt` → `5`；`sim_diff_rc=0`

---

## §0 全域規則與約束（執行端讀完即可遵守）

- **scope（硬邊界）**：僅允許修改下列 5 檔（SPEC §C 白名單）：
  1. `frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx`
  2. `frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx`
  3. `frontend/src/hooks/useFeatureFactory.batchDate.test.ts`
  4. `frontend/src/lib/runExplorer.test.ts`
  5. `frontend/src/store/featureFactoryStore.test.ts`
- **禁止**：`frontend/src/lib/types.ts`；一切非 `*.test.{ts,tsx}` 的 `frontend/src/**`；`momentum/`、`api/`、`data_cache/`、`scripts/`。
- **防假綠（§C + §V）**：
  1. 禁止 `@ts-ignore`、`@ts-expect-error`、`as any`、`as unknown as` 靜默繞過（Gate A 負向掃描）。
  2. 禁止刪弱/移除既有 `expect(...)` 斷言（Gate B 合計 87；Gate C per-file 計數須不變）。
  3. 僅補齊型別正確的 fixture / mock 簽名 / helper 簽名；**不得**改斷言期望值或測試行為。
  4. scope 驗收 = 派工前擷取 pre-dirty；完工後 `comm -13` 得 delta；delta 與五檔 whitelist **排序後精確相等**（見 Task 3.1）；**不得**用未扣 pre-dirty 的全域 `git diff --name-only`。
- **解耦**：零觸後端；`grep -r "from api\." momentum/ | wc -l` 須仍為 `0`。
- **升級訊號**：若實作期發現需改 `types.ts` / store / hook 生產碼 → **立即 BLOCK**，另立票。
- **FACT-RECEIPT 格式**（本檔基線）：`FACT-RECEIPT: <命令> → 印出 <stdout 摘要>（Composer 實跑 2026-07-11）`

---

## §B 批次執行策略（依賴拓撲 → 最少批次）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|-------|---------|------|----------|------|
| **B1** | 1.1 + 1.2 + 1.3 + 1.4 + 1.5 | 無 | 五檔互不 import；單 commit 可 revert；錯誤清單 11 處全在本批 | **小** |
| **B2** | 2.1 + 2.2 + 2.3 + 3.1 + Final | B1 完工 | 防假綠 gate + scope + 主驗收須在型別修復後跑 | **小** |

**Batch Gate（B1 完工後必跑）**

> **R3**（在 R2 `run_step` 累積之上）：每步 **self-contained**（禁 `bash -c` 讀未 export 的 parent 變數；對齊 T2 Final §8 每步獨立契約）；tsc 計數用 `rg -c` + **rc=1 → count 0**（禁 `grep -c … || echo 0` 雙行非整數）；禁鏈式二次 `cd frontend`；vitest 斷言 `package.json` `"test": "vitest run"` 契約。

```bash
set +e
set -o pipefail
fail=0
run_step() {
  local name="$1"; shift
  "$@"
  local rc=$?
  echo "STEP_RC[$name]=$rc"
  if [ "$rc" -ne 0 ]; then fail=1; fi
  return 0
}

# § tsc：compiler rc 與 zero-count 各一步；計數在 child 內完成（R3 self-contained）
run_step tsc bash -c 'cd frontend && npx tsc --noEmit 2>&1 | tee /tmp/p2debt-t3-batch-tsc.log; exit ${PIPESTATUS[0]}'
run_step tsc_zero bash -c '
  c=$(rg -c "error TS" /tmp/p2debt-t3-batch-tsc.log 2>/dev/null)
  rc=$?
  if [ "$rc" -eq 1 ]; then c=0
  elif [ "$rc" -ne 0 ]; then echo "TSC_COUNT_RG_RC=$rc"; exit 2
  fi
  echo "TSC_ERROR_COUNT=$c"
  test "$c" -eq 0
'
# 壞基線（Grok 實跑 2026-07-11）：STEP_RC[tsc]=1；TSC_ERROR_COUNT=11；STEP_RC[tsc_zero]=1

run_step vitest bash -c 'cd frontend && npm test -- \
  src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  src/hooks/useFeatureFactory.batchDate.test.ts \
  src/lib/runExplorer.test.ts \
  src/store/featureFactoryStore.test.ts 2>&1 | tee /tmp/p2debt-t3-batch-vitest.log; exit ${PIPESTATUS[0]}'
run_step vitest_files bash -c 'grep -q "Test Files  5 passed (5)" /tmp/p2debt-t3-batch-vitest.log'
run_step vitest_tests bash -c 'grep -q "Tests  31 passed (31)" /tmp/p2debt-t3-batch-vitest.log'
# package.json `"test": "vitest run"` → 上式等價 `vitest run <五檔>`；完工預期 Test Files 5 passed、Tests 31 passed
# 壞基線：STEP_RC[vitest]=0；vitest_files/tests=0；ANY_FAIL=1（因 tsc）

echo "ANY_FAIL=$fail"
exit "$fail"
# 完工預期：ANY_FAIL=0
```

**派工 prompt（B1，可直接複製）**

```
task-id: p2debt-t3
讀 handoffs/P2DEBT-T3-TODO-DRAFT-R3.md §0 + Phase 1 Task 1.1–1.5。
完成全部 checklist 項；scope 僅五個測試檔。
禁改 types.ts / 非測試 src/；禁 @ts-ignore / as any；禁刪弱 expect。
驗收：cd frontend && npx tsc --noEmit → 0 error TS；vitest 五檔 → 31 passed。
```

---

## Phase 1 — 測試型別對齊（目標：11 顆 tsc 錯誤 → 0；vitest 31 仍全綠）

### Task 1.1 — `run_lifecycle.test.tsx`（錯誤 #1–#2）

- **SPEC ref**：§P Task 1.1　|　**目標檔**：`frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx`
- **輸入**：生產型別 `FeatureTask.error: string | null`（`types.ts:576`）、`CompletionQueueItem.source: CompletionSource`（`types.ts:595`）
- **輸出**：L42 `FeatureTask` 字面量合法；L88 `completionQueue` 元素含 `source`

#### 有序實作清單

| # | 位置 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.1.1** | L42 `const task: FeatureTask` | 補 `error: null` | `cd frontend && npx tsc --noEmit 2>&1 \| rg "run_lifecycle.test.tsx\(42"` → 0 行（基線 1 行 TS2741） |
| **1.1.2** | L88 `completionQueue: [run]` | 改 `completionQueue: [{ ...run, source: 'single' as const }]` | `cd frontend && npx tsc --noEmit 2>&1 \| rg "run_lifecycle.test.tsx\(88"` → 0 行（基線 1 行 TS2741） |

- **實作要點**：
  1. `error` 須顯式 `null`，不可省略（必填欄）。
  2. `source` 須字面量 `'single' as const`，對齊 store `enqueueCompletion` 預設。
  3. 不改 `expect(...)` 行；L70/L83 已預期 `{ ...run, source: 'single' }`，與 L88 對齊後行為一致。
- **修改檔案**：`run_lifecycle.test.tsx`（頂層 `task` 常數；`it('renders completion queue and retains item on 422')` 內 `setState`）
- **不可做**：改 `GenerationProgress` / `RunRetentionDialog` 生產元件；改 `types.ts` 將 `error` optional；用 `as FeatureTask` 跳過檢查。
- **邊界**：
  1. `error: null` vs 省略 — TypeScript 要求顯式 `null`；執行期行為不變。
  2. 422 retention 測試：`completionQueue` 長度仍須為 1（`expect(...).toHaveLength(1)` 不變）。
- **風險緩解**：⊘（RISK-HIT: none）
- **驗證（Task 閉合）**：`cd frontend && npx tsc --noEmit 2>&1 | rg -c "run_lifecycle"` → `0`（基線 `2`）；`cd frontend && npm test -- --run src/components/feature-factory/__tests__/run_lifecycle.test.tsx` → `Tests` 行含 `passed` 且 `failed` 為 0

---

### Task 1.2 — `runExplorer.test.ts`（錯誤 #9）

- **SPEC ref**：§P Task 1.1（`runExplorer` 分檔）　|　**目標檔**：`frontend/src/lib/runExplorer.test.ts`
- **輸入**：`pickDefaultRun(runs, currentTask, null)` 需完整 `FeatureTask`
- **輸出**：L51–58 物件補 `error: null`；改 `const currentTask: FeatureTask = { … }`；**移除** `as FeatureTask`

#### 有序實作清單

| # | 位置 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.2.1** | L51–58 `currentTask` | 補 `error: null`；移除尾端 `as FeatureTask`；改為 `const currentTask: FeatureTask = { … }` | `cd frontend && npx tsc --noEmit 2>&1 \| rg "runExplorer.test.ts\(51"` → 0 行（基線 1 行 TS2352） |

- **實作要點**：
  1. 保留 `run_identity` 等既有欄位；只補 `error` 與型別註解方式。
  2. 同檔 L67 `batchTask as BatchTaskStatus` **不在本票 scope**（無 tsc 錯誤，勿動）。
  3. `expect(pickDefaultRun(...).config_hash).toBe('cfg_new')` 不變。
- **修改檔案**：`runExplorer.test.ts`（`it('pickDefaultRun prefers completed current task identity…')` 內 `currentTask`）
- **不可做**：`as unknown as FeatureTask`；改 `pickDefaultRun` 生產函式；改 `types.ts`。
- **邊界**：
  1. `error: null` 對 completed task 語意正確（無錯誤狀態）。
  2. 移除 cast 後須滿足 structural typing，不可再觸發 TS2352。
- **風險緩解**：⊘
- **驗證（Task 閉合）**：`cd frontend && npx tsc --noEmit 2>&1 | rg -c "runExplorer"` → `0`（基線 `1`）；`cd frontend && npm test -- --run src/lib/runExplorer.test.ts` → 全 `passed`

---

### Task 1.3 — `RunManagerPanel.batchDeleteWhole.test.tsx`（錯誤 #3–#4）

- **SPEC ref**：§P Task 1.2　|　**目標檔**：`frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx`
- **輸入**：本地 `response(status, payload: Record<string, unknown>)` 過窄
- **輸出**：`payload: unknown`；L102、L170 call site 不變

#### 有序實作清單

| # | 位置 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.3.1** | L22 `function response` | `payload: Record<string, unknown>` → `payload: unknown`；`json: async () => payload` 不變 | `cd frontend && npx tsc --noEmit 2>&1 \| rg "batchDeleteWhole.test.tsx"` → 0 行（基線 2 行 TS2345） |

- **實作要點**：
  1. 僅改 helper 簽名一行；`return { ok, status, json: async () => payload }` 形狀不變。
  2. L102 `response(200, allRuns)`、L170 `response(200, activeOnly)` 自動滿足（`RunInfo[]`）。
  3. bulk-delete `response(200, { deleted, failed, skipped })` 物件 payload 仍合法。
- **修改檔案**：`RunManagerPanel.batchDeleteWhole.test.tsx`（頂層 `response()`；call site 在兩個 `it` 的 `fetchMock`）
- **不可做**：改 `response` 回傳形狀；改 `RunManagerPanel` 生產元件；改 bulk-delete 斷言期望值。
- **邊界**：
  1. `RunInfo[]` 陣列 mock 須仍觸發 `runsUrl()` 分支。
  2. `response(404, {})` 空物件 payload 仍須型別合法。
- **風險緩解**：⊘
- **驗證（Task 閉合）**：`cd frontend && npx tsc --noEmit 2>&1 | rg -c "batchDeleteWhole"` → `0`（基線 `2`）；`cd frontend && npm test -- --run src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx` → 全 `passed`

---

### Task 1.4 — `featureFactoryStore.test.ts`（錯誤 #10–#11）

- **SPEC ref**：§P Task 1.2（store 分檔）　|　**目標檔**：`frontend/src/store/featureFactoryStore.test.ts`
- **輸入**：同上 `response()` 簽名過窄；L429、L539 `response(200, [])`
- **輸出**：`payload: unknown`；兩處 `[]` mock 合法

#### 有序實作清單

| # | 位置 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.4.1** | L19 `function response` | `payload: Record<string, unknown>` → `payload: unknown` | `cd frontend && npx tsc --noEmit 2>&1 \| rg "featureFactoryStore.test.ts\(429\|featureFactoryStore.test.ts\(539"` → 0 行（基線 2 行 TS2345） |

- **實作要點**：
  1. 僅改 L19 helper 簽名；其餘 `response(200, bulkResponse)` 等物件 call site 不變。
  2. L429、L539 `response(200, [])` 作為 `RunInfo[]` 空陣列 mock 須通過。
  3. Gate B：本檔 `expect(` 計數須仍為 **44**。
- **修改檔案**：`featureFactoryStore.test.ts`（頂層 `response(): Response`）
- **不可做**：改 `featureFactoryStore` 生產 store；刪弱 orphans/bulk-delete 斷言。
- **邊界**：
  1. 空陣列 `[]` mock 仍須觸發 `fetchRuns` / `runsUrl()` 路徑。
  2. `response(200, scanPayload)` 等非陣列 payload 不受影響。
- **風險緩解**：⊘
- **驗證（Task 閉合）**：`cd frontend && npx tsc --noEmit 2>&1 | rg -c "featureFactoryStore.test"` → `0`（基線 `2`）；`cd frontend && npm test -- --run src/store/featureFactoryStore.test.ts` → 全 `passed`

---

### Task 1.5 — `useFeatureFactory.batchDate.test.ts`（錯誤 #5–#8）

- **SPEC ref**：§P Task 1.3　|　**目標檔**：`frontend/src/hooks/useFeatureFactory.batchDate.test.ts`
- **輸入**：`vi.fn(async () => …)` 零參數 → `mock.calls[0][1]` 推斷為 `never`
- **輸出**：兩個 `it` 各改 mock 為 `vi.fn(async (_url: string, init?: RequestInit) => …)`

#### 有序實作清單

| # | 位置 | 精確變更 | 驗證命令 + 預期輸出 |
|---|------|----------|---------------------|
| **1.5.1** | L39–41（有日期 `it`） | `vi.fn(async () => response(200, …))` → `vi.fn(async (_url: string, init?: RequestInit) => response(200, …))` | `cd frontend && npx tsc --noEmit 2>&1 \| rg "batchDate.test.ts\(55"` → 0 行（基線 2 行 TS2493/TS2339） |
| **1.5.2** | L61–63（無日期 `it`） | 同上簽名 | `cd frontend && npx tsc --noEmit 2>&1 \| rg "batchDate.test.ts\(75"` → 0 行（基線 2 行） |

- **實作要點**：
  1. `_url` 可不使用；`init` 可選，對齊真實 `fetch(url, init)`。
  2. **保留** `JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body))` 與 `start_date`/`end_date` 斷言。
  3. 不改 `startBatchGeneration` 呼叫參數。
- **修改檔案**：`useFeatureFactory.batchDate.test.ts`（`it('sends start_date and end_date…')`、`it('omits undefined dates…')` 內 `fetchMock`）
- **不可做**：改 `useFeatureFactory.ts` 生產 hook；改 `response()` 回傳形狀（本檔 L8 helper 可維持 `Record<string, unknown>`，無 tsc 錯誤）。
- **邊界**：
  1. 有日期路徑：`body.start_date`/`end_date` 仍為 `'2025-01-01'`/`'2025-06-21'`。
  2. 無日期路徑：`body.start_date`/`end_date` 仍為 `undefined`。
- **風險緩解**：⊘
- **驗證（Task 閉合）**：`cd frontend && npx tsc --noEmit 2>&1 | rg -c "batchDate"` → `0`（基線 `4`）；`cd frontend && npm test -- --run src/hooks/useFeatureFactory.batchDate.test.ts` → 全 `passed`

---

### Phase 1 測試 + Phase Gate

| 層級 | 內容 | 命令 + 預期 |
|------|------|-------------|
| 型別 | 全專案 tsc | `cd frontend && npx tsc --noEmit 2>&1 \| grep -c "error TS"` → `0`（基線 `11`） |
| 單元 | 五檔 vitest | 見 §B Batch Gate → `31 passed` |
| per-file | 五檔零 tsc | 各檔 `rg -c` 見 Task 1.1–1.5 → 皆 `0` |

---

## Phase 2 — 防假綠 Gate（B2；須 Phase 1 完工後）

### Task 2.1 — Gate A：禁靜默型別繞過（`rg_rc` 三極性）

- **SPEC ref**：§V Gate A　|　**目標**：五檔無 `@ts-ignore`/`@ts-expect-error`/`as any`/`as unknown as`
- **輸入**：五檔 existence + `rg` 負向掃描
- **輸出**：`rg_rc=1` → gate exit 0

- **實作要點**：
  1. **禁止** `rg … | wc -l`（rg rc=2 時 pipe 假 PASS）。
  2. 先 `test -f` 五檔；缺檔 `exit 2`。
  3. 直接讀 `rg_rc`：`1`=PASS（無命中）、`0`=FAIL（印命中行）、`2`=FAIL（rg 錯誤）。
- **修改檔案**：無（驗收腳本 only）
- **不可做**：在修復中引入任何 Gate A 禁則 token；用 `wc -l` 代替 `rg_rc`。
- **邊界**：
  1. **Polarity 1（現樹）**：五檔存在；`rg_rc=1` → `gate_a_exit=0`。
  2. **Polarity 2（合成命中）**：`/tmp/p2debt-t3-gate-a-synth.ts` 含 `// @ts-ignore` → `rg_rc=0`（FAIL）。
  3. **Polarity 3（bogus path）**：`rg` 指向不存在路徑 → `rg_rc=2`（FAIL）。
- **風險緩解**：⊘
- **驗證（Task 閉合）**（`rg_rc=1` → `test` exit 0；Composer 實跑 2026-07-11）：

```bash
for f in \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts; do
  test -f "$f" || exit 2
done
rg -n '@ts-ignore|@ts-expect-error|\bas any\b|as unknown as' \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts
rg_rc=$?
test "$rg_rc" -eq 1
# Composer 實跑 2026-07-11：rg_rc=1；gate exit 0
```

---

### Task 2.2 — Gate B：`expect(` 站點合計不變（預期 87）

- **SPEC ref**：§V Gate B　|　**目標**：刪弱斷言會降低合計數
- **輸入**：五檔 `rg -c '\bexpect\('`
- **輸出**：合計 **87**；per-file 見 Task 2.3

- **實作要點**：
  1. 用 `awk -F: '{s+=$2} END {print s}'` 加總 per-file 計數。
  2. 基線 per-file：`20+10+4+9+44=87`。
  3. 與 vitest **31 tests** 區分（31 ≠ expect 站點數）。
- **修改檔案**：無
- **不可做**：為過 tsc 而刪除 `expect(...)` 行。
- **邊界**：
  1. 合法型別補行（非 expect 行）不影響 Gate B。
  2. 任一合計 ≠ 87 → FAIL，視為刪弱或未授權改動。
- **風險緩解**：⊘
- **驗證（Task 閉合）**（合計 `87`；`awk` 加總 per-file `rg -c expect`）：

```bash
rg -c '\bexpect\(' \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts | awk -F: '{s+=$2} END {print s}'
# Composer 實跑 2026-07-11：87
# 完工驗收：須仍為 87
```

---

### Task 2.3 — Gate C：per-file `expect` 計數 + assertion body diff

- **SPEC ref**：§V Gate C Leg1 + Leg2　|　**目標**：機械 gate + 審查者 leg
- **輸入**：派工前擷取 pre-expect-counts；完工後 post-expect-counts
- **輸出**：Leg1 `diff` rc=0；Leg2 `rg -N` body diff rc=0（或審查者簽核）

- **實作要點**：
  1. **Leg1**：`rg -c '\bexpect\('` per-file，`sort` 後 `diff -u` pre vs post → rc=0。
  2. **Leg2**：`rg -N '\bexpect\('`（無行號）body diff；合法型別-only 變更預期 rc=0。
  3. 合意 per-file 計數變更須 SPEC amendment note（本票預期無變更）。
- **修改檔案**：無
- **不可做**：用 `rg -n expect` raw diff 當機械 gate（line-number shift 假 FAIL）。
- **邊界**：
  1. 壞基線 pre=post：`diff` rc=0（Composer 實跑 2026-07-11）。
  2. fixture 補行導致 expect 行號變但文本不變：Leg2 須 rc=0。
- **風險緩解**：⊘
- **驗證（Task 閉合）**（Leg1 `diff` rc=0；Leg2 `wc -l` → `87` expect bodies）：

```bash
# Leg1 — 派工前（實作開始前一次）：
rg -c '\bexpect\(' \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-pre-expect-counts.txt
# Composer 實跑 2026-07-11 pre-expect-counts.txt 五行；per-file 20/10/4/9/44

# Leg1 — 完工後：
rg -c '\bexpect\(' \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-post-expect-counts.txt
diff -u /tmp/p2debt-t3-pre-expect-counts.txt /tmp/p2debt-t3-post-expect-counts.txt
# 壞基線：rc=0；完工：rc=0 且 per-file 計數不變

# Leg2 — assertion body（審查者）：
rg -N '\bexpect\(' \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-pre-expect-bodies.txt
# Composer 實跑 2026-07-11：wc -l → 87
# 完工後 diff pre vs post bodies → rc=0（expect 文本不變）
```

---

## Phase 3 — scope + Final Acceptance

### Task 3.1 — scope gate（pre-dirty `comm -13` vs 五檔 whitelist）

- **SPEC ref**：§V item 3 + §C diff gate　|　**目標**：delta 精確等於五檔 whitelist
- **輸入**：派工前 pre-dirty snapshot
- **輸出**：`diff -u` whitelist vs delta-dirty → rc=0

- **實作要點**：
  1. 派工前一次：`git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t3-pre-dirty.txt`。
  2. 完工後 post-dirty 同法；`comm -13 pre post | sort -u` 得 delta。
  3. whitelist 五檔 `sort -u` 後與 delta `diff -u`。
- **修改檔案**：無
- **不可做**：用全域 `git diff --name-only` 當 scope 驗收（壞基線含外檔）。
- **邊界**：
  1. **壞基線**（無實作）：post=pre，delta 0 行，`diff` vs whitelist → **rc=1**（Composer 實跑：`bad_diff_rc=1`）。
  2. **Synthetic good**：pre + 五檔 → sim-post；delta 5 行，`diff` → **rc=0**（Composer 實跑：`sim_diff_rc=0`）。
- **風險緩解**：⊘
- **驗證（Task 閉合）**（`comm -13` delta 5 行 vs whitelist → `diff` rc=0）：

```bash
# 派工前（一次）：
git status --porcelain | awk '{print $NF}' | sort -u > /tmp/p2debt-t3-pre-dirty.txt
# Composer 實跑 2026-07-11：wc -l → 30

# 完工後：
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
# 真實完工預期：delta 精確 5 行；diff rc=0
```

---

## Final Acceptance（閉合條件）

> **R3**（在 R2 `run_step` 累積之上）：七個 leg 皆 **self-contained**（變數計算 + 斷言同在一個 `bash -c` / 同一步；對齊 T2 Final §8）；禁 parent-only 變數餵 `bash -c 'test "$var"'`；計數禁 `grep -c … || echo 0`；Gate B 用 per-file `rg -c` + 算術加總（rc=1 → 0）；禁 `producer | consumer` 掩蓋 producer rc；§3–§7 不得僅註解指向他處。

```bash
set +e
set -o pipefail
fail=0
run_step() {
  local name="$1"; shift
  "$@"
  local rc=$?
  echo "STEP_RC[$name]=$rc"
  if [ "$rc" -ne 0 ]; then fail=1; fi
  return 0
}

# §1 — TypeScript 零錯誤（compiler rc 與 count 各 self-contained；禁 parent $tsc_count + 禁 grep -c||echo 0）
run_step tsc bash -c 'cd frontend && npx tsc --noEmit 2>&1 | tee /tmp/p2debt-t3-final-tsc.log; exit ${PIPESTATUS[0]}'
run_step tsc_count bash -c '
  c=$(rg -c "error TS" /tmp/p2debt-t3-final-tsc.log 2>/dev/null)
  rc=$?
  if [ "$rc" -eq 1 ]; then c=0
  elif [ "$rc" -ne 0 ]; then echo "TSC_COUNT_RG_RC=$rc"; exit 2
  fi
  echo "TSC_ERROR_COUNT=$c"
  test "$c" -eq 0
'
# Grok 實跑壞基線 2026-07-11：STEP_RC[tsc]=1；TSC_ERROR_COUNT=11；STEP_RC[tsc_count]=1

# §2 — vitest 五檔（package.json `"test": "vitest run"` → `npm test -- <五檔>`）
run_step vitest bash -c 'cd frontend && npm test -- \
  src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  src/hooks/useFeatureFactory.batchDate.test.ts \
  src/lib/runExplorer.test.ts \
  src/store/featureFactoryStore.test.ts 2>&1 | tee /tmp/p2debt-t3-final-vitest.log; exit ${PIPESTATUS[0]}'
run_step vitest_files bash -c 'grep -q "Test Files  5 passed (5)" /tmp/p2debt-t3-final-vitest.log'
run_step vitest_tests bash -c 'grep -q "Tests  31 passed (31)" /tmp/p2debt-t3-final-vitest.log'
# Grok 實跑：STEP_RC[vitest]=0；Test Files 5 passed；Tests 31 passed

# §3 — Gate A（rg 三極性：1=PASS；rg_rc 在同一 bash -c 內）
run_step gate_a_files bash -c 'for f in \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts; do test -f "$f" || exit 2; done'
run_step gate_a_rg bash -c 'rg -n "@ts-ignore|@ts-expect-error|\\bas any\\b|as unknown as" \
  frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
  frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
  frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
  frontend/src/lib/runExplorer.test.ts \
  frontend/src/store/featureFactoryStore.test.ts; rg_rc=$?; test "$rg_rc" -eq 1'
# Grok 實跑：rg_rc=1 → STEP_RC[gate_a_rg]=0

# §4 — Gate B（per-file rg -c + 算術加總；rc=1 no-match → c=0；禁 parent $gate_b_sum）
run_step gate_b bash -c '
  sum=0
  for f in \
    frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
    frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
    frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
    frontend/src/lib/runExplorer.test.ts \
    frontend/src/store/featureFactoryStore.test.ts; do
    c=$(rg -c "\bexpect\(" "$f" 2>/dev/null)
    rc=$?
    if [ "$rc" -eq 1 ]; then c=0
    elif [ "$rc" -ne 0 ]; then echo "GATE_B_RG_RC=$rc file=$f"; exit 2
    fi
    echo "$f:$c"
    sum=$((sum + c))
  done
  echo "GATE_B_SUM=$sum"
  test "$sum" -eq 87
'
# Grok 實跑：GATE_B_SUM=87；STEP_RC[gate_b]=0

# §5 — Gate C Leg1（pre/post 在同一步；派工前須已存 /tmp/p2debt-t3-pre-expect-counts.txt）
run_step gate_c bash -c '
  rg -c "\bexpect\(" \
    frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
    frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
    frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
    frontend/src/lib/runExplorer.test.ts \
    frontend/src/store/featureFactoryStore.test.ts | sort > /tmp/p2debt-t3-post-expect-counts.txt
  gate_c_rg_rc=$?
  echo "GATE_C_RG_RC=$gate_c_rg_rc"
  test "$gate_c_rg_rc" -eq 0 || exit 1
  diff -u /tmp/p2debt-t3-pre-expect-counts.txt /tmp/p2debt-t3-post-expect-counts.txt
  gate_c_diff_rc=$?
  echo "GATE_C_DIFF_RC=$gate_c_diff_rc"
  test "$gate_c_diff_rc" -eq 0
'
# 壞基線 pre=post：GATE_C_DIFF_RC=0；STEP_RC[gate_c]=0

# §6 — scope gate（pre-dirty comm -13 全在同一步；禁 parent $scope_diff_rc）
run_step scope bash -c '
  git status --porcelain | awk "{print \$NF}" | sort -u > /tmp/p2debt-t3-post-dirty.txt
  scope_git_rc=$?
  echo "SCOPE_GIT_RC=$scope_git_rc"
  test "$scope_git_rc" -eq 0 || exit 1
  comm -13 /tmp/p2debt-t3-pre-dirty.txt /tmp/p2debt-t3-post-dirty.txt | sort -u > /tmp/p2debt-t3-delta-dirty.txt
  printf "%s\n" \
    frontend/src/components/feature-factory/__tests__/run_lifecycle.test.tsx \
    frontend/src/components/feature-factory/__tests__/RunManagerPanel.batchDeleteWhole.test.tsx \
    frontend/src/hooks/useFeatureFactory.batchDate.test.ts \
    frontend/src/lib/runExplorer.test.ts \
    frontend/src/store/featureFactoryStore.test.ts | sort -u > /tmp/p2debt-t3-whitelist-sorted.txt
  sort -u /tmp/p2debt-t3-delta-dirty.txt > /tmp/p2debt-t3-delta-dirty-sorted.txt
  dl=$(wc -l < /tmp/p2debt-t3-delta-dirty-sorted.txt)
  dl=${dl// /}
  echo "DELTA_LINES=$dl"
  diff -u /tmp/p2debt-t3-whitelist-sorted.txt /tmp/p2debt-t3-delta-dirty-sorted.txt
  scope_diff_rc=$?
  echo "SCOPE_DIFF_RC=$scope_diff_rc"
  test "$scope_diff_rc" -eq 0
'
# 壞基線（無實作）：DELTA_LINES=0；SCOPE_DIFF_RC=1；STEP_RC[scope]=1

# §7 — 解耦回歸（計數 + test 同一步；grep rc=1 no-match → n=0）
run_step decouple bash -c '
  n=0
  if out=$(grep -r "from api\." momentum/ 2>/dev/null); then
    n=$(printf "%s\n" "$out" | wc -l)
    n=${n// /}
  else
    greprc=$?
    if [ "$greprc" -eq 1 ]; then n=0
    else echo "DECOUPLE_GREP_RC=$greprc"; exit 2
    fi
  fi
  echo "DECOUPLE_N=$n"
  test "$n" -eq 0
'
# Grok 實跑：DECOUPLE_N=0；STEP_RC[decouple]=0

echo "ANY_FAIL=$fail"
exit "$fail"
# 完工預期：ANY_FAIL=0；TSC_ERROR_COUNT=0；GATE_B_SUM=87；SCOPE_DIFF_RC=0；DECOUPLE_N=0
# 壞基線實跑：ANY_FAIL=1（tsc + tsc_count + scope）
```

**禁止事項（驗收時逐條否決）**：改 `types.ts` 或非測試 `src/`；`@ts-ignore`/`as any`；刪弱 `expect`；未扣 pre-dirty 的 scope 驗收；vitest 或 tsc 任一 FAIL。

**建議 commit message**：`test: p2debt-t3 align feature-factory test fixtures to production types`

---

## 附錄 — 11 錯誤修法速查（對齊 SPEC §A 表）

| # | 檔案:line | TS | Task |
|---|-----------|-----|------|
| 1 | `run_lifecycle.test.tsx:42` | TS2741 | 1.1.1 |
| 2 | `run_lifecycle.test.tsx:88` | TS2741 | 1.1.2 |
| 3 | `RunManagerPanel.batchDeleteWhole.test.tsx:102` | TS2345 | 1.3.1 |
| 4 | `RunManagerPanel.batchDeleteWhole.test.tsx:170` | TS2345 | 1.3.1 |
| 5–6 | `useFeatureFactory.batchDate.test.ts:55` | TS2493/TS2339 | 1.5.1 |
| 7–8 | `useFeatureFactory.batchDate.test.ts:75` | TS2493/TS2339 | 1.5.2 |
| 9 | `runExplorer.test.ts:51` | TS2352 | 1.2.1 |
| 10 | `featureFactoryStore.test.ts:429` | TS2345 | 1.4.1 |
| 11 | `featureFactoryStore.test.ts:539` | TS2345 | 1.4.1 |

---

SPEC=handoffs/P2DEBT-T3-SPEC-DRAFT-R4.md TODO=handoffs/P2DEBT-T3-TODO-DRAFT-R3.md FOCUS=11-error test-only tsc fix + Gate A/B/C + pre-dirty scope gate；用 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 獨立審查；Blocking 修補後才 Frozen。

---

## R2 FACT-RECEIPT（Composer 唯讀實跑 2026-07-11；零 repo body 污染）

### R2-P1 — finding (1) chained `cd`/exit 掩蓋

```text
命令: bash -c 'false; true; rc=$?; echo rc=$rc'; echo exit=$?
結果: rc=0 exit=0  ← 前步 false 被掩蓋

命令: run_step 累積（見 §B Batch Gate / Final Acceptance）；壞基線 tsc fail + vitest pass
結果: STEP_RC[tsc]=1 STEP_RC[vitest]=0 STEP_RC[vitest_files]=0 STEP_RC[vitest_tests]=0 ANY_FAIL=1 exit=1
```

### R2-P2 — finding (2) vitest 可跳過 / 無斷言

```text
命令: cd frontend && npm test -- <五檔>（package.json test=vitest run）
結果: STEP_RC[vitest]=0；stdout 含 Test Files  5 passed (5)；Tests  31 passed (31)
斷言: grep -q "Test Files  5 passed (5)" → rc=0；grep -q "Tests  31 passed (31)" → rc=0
```

### R2-P3 — finding (3) Task 1.5.1 行號錯

```text
命令: npx tsc --noEmit 2>&1 | rg batchDate
結果: 診斷錨點 L55/L75 正確；mock 實際位於 L39–41（有日期 it）、L61–63（無日期 it）；R1 誤標 L43–45
```

---

## R2-CLOSURE — codex R1 review finding → fix

R2-CLOSURE: acceptance commands mask failures via chained `cd frontend`/last-rc-only → `set +e` + `set -o pipefail` + `run_step` 累積 `fail`；tsc 先 `PIPESTATUS[0]` 再 `grep -c`；`exit "$fail"`；反例 `false;true;rc=$?`→0 vs 壞基線 tsc fail→ANY_FAIL=1  
R2-CLOSURE: vitest leg skippable / no exit contract → 獨立 `run_step vitest`（`npm test -- <五檔>` = `vitest run`）；`grep -q "Test Files  5 passed (5)"` + `grep -q "Tests  31 passed (31)"` 斷言  
R2-CLOSURE: Task 1.5.1 false line L43–45 → 更正為 L39–41；診斷錨點 L55/L75 不變（tsc 實跑確認）

---

## R3 FACT-RECEIPT（Grok 唯讀實跑 2026-07-11；零 repo body 污染；僅寫本檔）

### R3-P1 — codex finding (1) unexported parent vars in `run_step` child

```text
# 舊契約反例（R2 等價：parent 設值 + bash -c 'test "$var"'）
tsc_count=11
bash -c 'echo child_sees=[${tsc_count-<unset>}]; test "$tsc_count" -eq 0; echo test_rc=$?'
結果: child_sees=[<unset>]；test: integer expression expected；test_rc=2
# export 後 child 可見，但仍受 finding (2) multi-line 污染（見 R3-P2）

# 新契約：計數+斷言同在 bash -c（Batch Gate tsc_zero / Final tsc_count）
run_step tsc_count bash -c 'c=$(rg -c "error TS" LOG); rc=$?; if [ "$rc" -eq 1 ]; then c=0; elif [ "$rc" -ne 0 ]; then exit 2; fi; echo TSC_ERROR_COUNT=$c; test "$c" -eq 0'
壞基線 LOG=/tmp/p2debt-t3-final-tsc.log:
  TSC_ERROR_COUNT=11；STEP_RC[tsc_count]=1
sim-pass LOG（無 error TS 行）:
  TSC_ERROR_COUNT=0；STEP_RC[tsc_count_sim_pass]=0
```

### R3-P2 — codex finding (2) zero-match `grep -c … || echo 0` multi-line non-integer

```text
echo "no errors" > /tmp/p2debt-t3-sim-zero-tsc.log
tsc_count=$(grep -c "error TS" /tmp/p2debt-t3-sim-zero-tsc.log 2>/dev/null || echo 0)
printf '%s' "$tsc_count" | od -An -c
結果: 0 \n 0   （兩行）；OLD_lines=2；test "$tsc_count" -eq 0 → integer expression expected rc=2

# multi-file grep -c zero:
grep -c THIS_NEVER file1 file2 || echo 0
結果: file1:0\nfile2:0\n0  （三行非整數）

# 新契約 per-file rg -c + rc=1→0 算術加總（Gate B zero-match 極性）:
sum over 2 files pattern THIS_NEVER_MATCHES_XYZ_R3 → GATE_B_SUM=0；test -eq 87 → STEP_RC=1；test -eq 0 → STEP_RC=0
```

### R3-P3 — Batch Gate 全段壞基線（R3 腳本原文）

```text
STEP_RC[tsc]=1
TSC_ERROR_COUNT=11
STEP_RC[tsc_zero]=1
STEP_RC[vitest]=0
STEP_RC[vitest_files]=0
STEP_RC[vitest_tests]=0
ANY_FAIL=1
# （vitest stdout: Test Files  5 passed (5)；Tests  31 passed (31)）
```

### R3-P4 — Final Acceptance 全段壞基線（R3 腳本原文）

```text
STEP_RC[tsc]=1
TSC_ERROR_COUNT=11
STEP_RC[tsc_count]=1
STEP_RC[vitest]=0
STEP_RC[vitest_files]=0
STEP_RC[vitest_tests]=0
STEP_RC[gate_a_files]=0
STEP_RC[gate_a_rg]=0
GATE_B_SUM=87
STEP_RC[gate_b]=0
GATE_C_RG_RC=0
GATE_C_DIFF_RC=0
STEP_RC[gate_c]=0
SCOPE_GIT_RC=0
DELTA_LINES=0
SCOPE_DIFF_RC=1
STEP_RC[scope]=1
DECOUPLE_N=0
STEP_RC[decouple]=0
ANY_FAIL=1
```

### R3-P5 — scope synthetic good（sim post = pre ∪ whitelist）

```text
SIM_DELTA_LINES=5
SCOPE_DIFF_RC=0
STEP_RC[scope_sim]=0
```

### R3-P6 — template_check

```text
命令: bash scripts/template_check.sh todo handoffs/P2DEBT-T3-TODO-DRAFT-R3.md
結果: TEMPLATE PASS (todo): handoffs/P2DEBT-T3-TODO-DRAFT-R3.md 含全部必填錨點，且無明顯空殼。
EXIT=0
```

---

## R3-CLOSURE — codex R2 re-verify finding → fix

R3-CLOSURE: run_step assertions read unexported parent variables (`tsc_count`, `gate_b_rg_rc`, `gate_b_sum`, `gate_c_rg_rc`, `gate_c_diff_rc`, `scope_git_rc`, `scope_diff_rc`, `decouple_n`) → each leg self-contained: compute + assert inside the same `bash -c` (T2 Final §8 pattern); parent-only `bash -c 'test "$var"'` removed from §B Batch Gate + Final Acceptance  
R3-CLOSURE: zero-match `grep -c … || echo 0` yields multi-line non-integer (`0\n0`) → `rg -c` with explicit `rc=1 → c=0` (else `rc≠0 → exit 2`); Gate B uses per-file loop + arithmetic `sum=$((sum+c))`; tsc count same pattern on log file  
R3-CLOSURE: R2-CLOSURE (run_step fail accumulation / vitest exit contract / Task 1.5.1 L39–41) → **intact**；本輪 diff 僅 acceptance shell + header/refs + R3 FACT-RECEIPT/CLOSURE；Task 1.1–1.5 實作清單零改  
R3-CLOSURE: polarity receipts — bad-baseline ANY_FAIL=1 (TSC_ERROR_COUNT=11 integer + scope delta 0); tsc sim-pass count=0 rc=0; scope sim-good SIM_DELTA_LINES=5 rc=0; gate_b zero-match sum=0; template_check todo PASS