# GAP-3 事件型 UAT 缺口修補 — **實作交接**（更新於 2026-08-25，B4／B5 開工態）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0；B1／B2／B3 皆已收斂並蓋章；下一步＝B4（Task 1.5／1.6／1.7）＋ B5（Phase 2）。**

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 D-001（**須並讀**） | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ✅ 三家 APPROVED | `81cbe7ab` |
| TODO 延伸檔 D-002（**須並讀**，A-002..A-015 共 14 條） | `docs/GAP3_EVENT_UX_TODO.D-002.md` | ✅ 三家 APPROVED | `51f1a65e` |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 10 ✅／1 🔧／31 ⬜ | 每批收尾更新 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001 與 D-002**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 三十四輪之自傷絕大多數出自副本漂移。

### 前三批已交付什麼（B4／B5 可以直接用）

| Task | 產出 | 可直接 import 的東西 |
|---|---|---|
| 1.1 | `event_import_contract.json` typed namespace-aware `receipt_schema` | `import_contract.py`：`flatten_receipt_schema()`／`receipt_type_ok()`／`validate_receipt_namespace()`／**B3 新增** `capability_unavailable_reason(binding_key)` |
| 1.10 | `contracts/future_column_lookahead.json`（37 個 future 欄） | `event_samples/lookahead_registry.py`：`load_lookahead_registry()`／`lookahead_columns()`／`normalize_future_column()`／`hours_to_bars()`／`resolve_lookahead_bars()`／`lookahead_resolution()`／`unregistered_future_columns()`／**B3 新增** `registry_resolvable_columns()`／`declaration_required_columns()`／`requires_declaration()` |
| 2.1b | **唯一** exported 深度函式 | `event_samples/lookahead_depth.py::depth_by_timeframe(referenced_columns, declared_window_bars, timeframes, registry=None) -> Dict[str,int]`；前端 `frontend/src/lib/lookaheadDepthLock.ts::withHorizonLowerBoundGuard()` |
| 4.2（僅 §G S-9） | canonical bytes 參考實作 | `event_samples/canonical_serialize.py`：`normalize_for_canonical()`／`canonical_event_table_bytes()`／`canonical_event_table_sha256()`／`canonical_source_bytes()`／`canonical_source_digest()` |
| 1.2 | CSV 欄名對映端點 | `api/routes/case.py::import_events_csv`；`EventImportService.csv_records_from_mapping()`／**B3 新增** `file_columns()` |
| 1.3 | `event_id` 之 D-2 唯一定義來源 | `import_contract.py`：`event_id_template()`／`canonical_event_id()`／`verify_source_digest()`；前端 `frontend/src/lib/eventId.ts` |
| 1.4 | t0 單位偵測 | `import_contract.py`：`detect_t0_unit_ms()`／`normalize_t0_units()`／`T0UnitUndetectedError` |
| 1.8 | 異質列拒收 | `validate_event_import(..., enforce_batch_homogeneity=True)` |
| **1.11**（B3） | L2 強制宣告 | `lookahead_registry.requires_declaration(columns, timeframe, *, provenance, registry)` |
| **1.12**（B3） | L3 閘與 event-study-only executor | `event_samples/lookahead_gate.py`：`LookaheadGate`／`SplitBlockedError`／`assert_split_allowed()`／`capability_unavailable_block()`／`split_blocked_reason()`；`pipeline.run_event_study_only()`／`run_event_study_only_with_params()` |
| **1.9**（B3） | 答案窗宣告解析與投影 | `event_samples/lookahead_declaration.py`：`resolve_declaration()`／`batch_referenced_columns()`／`batch_has_filters()`／`default_window_bars_by_timeframe()`／`apply_horizon_projection()`／`embargo_ms_by_symbol()`／`gate_from_receipt()`；前端 `frontend/src/lib/lookaheadDeclaration.ts` ＋ `components/case/LookaheadDeclarationFields.tsx` |

### `EventSamplePipeline` 之 R3 出口清單（api 層只能經這些取用 momentum）

`import_contract()`／`canonical_event_id()`／`event_id_template()`／`mapping_failure_reasons()`／
`normalize_t0_units()`／`canonical_source_payload()`／`condition_engine_contract()`／
`bars_from_kline_cache()`／`validate()`／`run()`／`run_with_params()`／`analyze_tables()`／
**B3 新增**：`requires_lookahead_declaration()`／`lookahead_declaration_defaults()`／
`resolve_lookahead_declaration()`／`apply_lookahead_horizon_projection()`／
`lookahead_split_blocked()`／`split_blocked_capability_reason()`／`run_event_study_only_with_params()`
（見 `momentum/Analysis/event_samples/pipeline.py` 之 `@staticmethod` 區）。
🔴 **B4／B5 若要讓 api 層用到其他 momentum 內部函式，必須在此加出口**
——直接 `from momentum...import` 會被 `scripts/check_decoupling_imports.py`（R3）在 PostToolUse 當場擋掉。
🔴 **出口一律回純資料**（dict／bool／str），例外型別不跨界——B3 之 `resolve_lookahead_declaration()`
回 `{"ok": bool, ...}` 就是為此（api 層不得 `catch` momentum 的例外型別）。

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
git log --oneline -5                            # 期望最新為 B3 收斂之 docs commit
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-001.md  # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-002.md  # 期望 rc=0
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
python3 scripts/gap3_freeze_golden.py --check   # 期望 rc=0（canonical_sha 全程不變；本條約 15 秒）
venv/bin/python -m pytest tests/momentum/event_samples/ -q            # 期望 279 passed
venv/bin/python -m pytest tests/api -q -k "gap3_csv_import or gap3_source_digest or gap3_t0_unit_detect or gap3_heterogeneous_rows or lookahead_declaration or gap3_horizon_declaration"   # 期望 64 passed
npm --prefix frontend test -- --run             # 期望 38 files／208 passed
```

B1／B2／B3 之 mutation receipt 為 `handoffs/run_receipts/gap3ux-b{1,2,3}-all-mutations.receipt.json`
（32／14／13 條），皆 `closure: CLOSED`。**不需重跑**，除非你改了那幾批的產出。

---

## §2 B4 是什麼（三個 Task）

**B4 ＝ 匯入前端 ＝ Task 1.5（上傳／預覽／對映 UI）、1.6（對映 provenance 落檔）、1.7（可疑欄警示）。**
依 §B 拓撲，B4 之前置為 **B2**——已完成。

> **一句話**：B2 做了 CSV 對映**端點**，B4 做它的**使用者介面**，
> 並把「這批的正反例是依哪一欄、哪個檔宣告的」寫進 receipt 以便日後追溯。

### 2.1 🔴 偵察結論（2026-08-25 主委實跑，下個 session **不必重查**）

| 事實 | 位置 | 對 B4 的意義 |
|---|---|---|
| 事件匯入頁＝`/data-preparation` | `frontend/src/app/data-preparation/page.tsx`（246 行，內嵌 `EventImportForm`） | 1.5 之新 UI 落在此頁；**不是** `/search` |
| 現有 `EventImportForm` 打的是 `/case/import-events`（**非**對映端點） | `frontend/src/components/case/EventImportForm.tsx` | 1.5 要接的是 `POST /api/v1/case/import-events/csv`（B2 交付），需**新增**上傳／預覽／對映元件；B3 已在此表單接上答案窗宣告區塊，**新 UI 須沿用同一組宣告元件**，不得另寫一份 |
| 對映端點之三個 Form 欄 | `api/routes/case.py::import_events_csv`：`column_mapping`／`batch_defaults`／`lookahead_declaration` | 1.5 之 multipart 請求即這三欄＋`file`；`column_mapping` **無預設**（A-4′），缺 ⇒ `column_mapping_missing` |
| 預覽所需之欄名來源 | `EventImportService.file_columns(content, filename)`（B3 新增，只讀首列、不做契約檢核） | 1.5／1.7 之「全部欄名」可經此取得；**前 5 列預覽**目前**無端點**，需新增或於前端解析 |
| 宣告預填端點已存在 | `POST /api/v1/case/import-events/lookahead-declaration`（B3 新增，只讀不落檔） | 1.5 選檔後可直接呼叫取得逐 tf 預設值與 `requires_declaration` |
| **receipt_schema.batch 目前只有兩欄** | `event_import_contract.json`：`lookahead_bars_declared`／`analysis_alignment_receipt_hash` | 🔴 **1.6 要寫的四項（`column_mapping`／來源檔名／`source_file_digest`／確認時間）尚未登記** ⇒ 依 D-6「新欄位必須先進契約」，**1.6 第一步是改契約** |
| 契約成長之機械約束 | `tests/api/test_gap3_contract_reason_registry.py:126-129`（⑧a） | 斷言 `now_names[:len(pre_names)] == pre_names` 且 `len(now) > len(pre)` ⇒ **新欄只要加在 `receipt_schema` 尾端就仍通過**；插在中間會紅 |
| B3 之宣告 receipt 落點 | `import_records()` 之 `payload["lookahead_declaration"]`（**頂層**，非 `receipt_schema.batch`） | 1.6 須決定 provenance 放哪；建議與宣告 receipt 同層（頂層 `payload`）或正式登記進 `receipt_schema.batch`——**兩者擇一並在 brief 具名**，不要兩處都寫 |
| 落檔函式 | `EventImportService.import_records()` 之 `payload = {...}` 區塊 | 1.6 之唯一落點 |
| 現有 vitest 檔名 | `frontend/src/lib/*.test.ts`＋`components/case/gap3_event_import_form.test.tsx` | 🔴 selector 靠**檔名**匹配：1.5 需檔名含 `gap3_csv`、1.7 需含 `suspiciousBinaryColumns`，現有檔名**都不匹配**，須新建 |
| 前端測試指令 | `npm --prefix frontend test -- --run <pattern>` | 🔴 **禁用** `cd frontend && npx vitest`（`cd` 前綴會讓每個指令走權限分類器，見 §6.4） |

### 2.2 B4 三個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **1.5** 上傳／預覽／對映 UI | `294` | `1578–1587` | `frontend/src/app/data-preparation/`＋新元件；型別入 `frontend/src/lib/types.ts` | `npm --prefix frontend test -- --run gap3_csv` **≥5 條**；`npm --prefix frontend run build` rc=0；mutation 1 條 |
| **1.6** 對映 provenance 落檔 | `315` | `1588–1601` | `momentum/Analysis/contracts/event_import_contract.json`（先改契約）＋`api/services/case_import_service.py::import_records` | `pytest tests/api -q -k gap3_csv_provenance` **≥2 條**；mutation 1 條 |
| **1.7** 可疑欄警示 | `337` | `1602–1613` | `frontend/src/`（`detectBinaryColumns()`，純函式） | `npm --prefix frontend test -- --run suspiciousBinaryColumns` **≥2 條**；mutation 1 條 |

### 2.3 B4 之陷阱（TODO／SPEC 已明列，逐條抄在這裡免得漏）

1. **1.5**：
   - 🔴 **不得預設任何欄位對映**（A-4′）——下拉初始值必須是「未選」。
   - 🔴 文案**禁用「label 正確」字樣**（D-1：語意正確性不可機械證明，只能說「**你聲明**」）。
   - 🔴 邊界①＝**未勾確認 ⇒ `fetch` call count `== 0`**。這是執行期計數，
     **不要**用「原始碼裡有沒有 `disabled`」那種形狀斷言（§6.2 之教訓）。
   - 邊界②＝欄名重複之 CSV ⇒ 下拉須各自可辨，不得靜默取第一個同名欄。
2. **1.6**：
   - 🔴 **先改契約再寫程式**（D-6）；四項**只記錄、不參與任何計算**。
   - 邊界①＝未帶 `source_file_digest` ⇒ fail-closed；邊界②＝receipt 已存在時**不覆寫**既有欄。
   - 🔴 **須同步**（TODO 明列）：Task 7.1 讓五維度可選之後，本 receipt 須一併記錄五維度實際選值。
3. **1.7**：
   - 🔴 **不得因為只有一個二元欄就自動選它**（A-4′）——這正是 mutation 要打的點。
   - 🔴 **不得**與 Phase 2 之篩選合併為同一實作：系統內搜尋結果的旗標欄值域多半落在 `{0,1}`，
     合併後警示會失去鑑別力（「`len == 2`」會鬆脫）。
   - 只警示**不阻擋**；不持久化。

---

## §2B B5 是什麼（三個 Task ＋ 一條殘留接線）

**B5 ＝ 匯出前篩選 ＝ Task 2.1（篩選面板）、2.2（條件寫入 `filters`）、2.3（即時筆數）。**
（Phase 2 之 Task 2.1b 已於 B1 完成。）依 §B 拓撲，B5 之前置為 **B1**——已完成。

> **一句話**：Phase 2 不是方便功能——它是**唯一**能把「答案窗宣告」從不可驗的使用者聲明
> 變成**機器可證事實**的路徑（系統內篩選時，系統確知使用者引用了哪些 `future_N` 欄）。

### 2B.1 🔴 偵察結論（2026-08-25 主委實跑，**不必重查**）

| 事實 | 位置 | 對 B5 的意義 |
|---|---|---|
| `/search` 頁 1,617 行，匯出流程在 `exportSearchResultsToEventJson()` | `frontend/src/app/search/page.tsx:507` | 2.1 面板與 2.3 筆數區塊落在此頁；匯出整段已包在 `withHorizonLowerBoundGuard(..., {proceed})` 內（B1 之結構保證，**勿拆開**） |
| 🔴 **`label_definition` 實際是在「前端」組的** | `frontend/src/lib/eventExport.ts:103` 之 `label_definition: {...}` | **TODO Task 2.2「修改檔案」寫的是後端 `case_import_service` 之序列化函式——那是 doc drift**（與 B2 之 Task 1.3 同型）。後端只驗證與落檔，不組 `label_definition`。⇒ 2.2 之落點應為 `eventExport.ts`；**須在 brief 具名回報並請三家裁**，收 epic 前走延伸檔 D-003 更正 |
| 🔴 **`lookaheadLowerBound` 恆為 `null` 且明確標記未接線** | `frontend/src/app/search/page.tsx:59-60`：`useState<number\|null>(null)` ＋ `void setLookaheadLowerBound;` | 這就是 **D-002 之 `A-004` 殘留**（`blocked-by` Task 2.1）。B5 必須把它接上——條件物件 →（Task 2.1b 之 `depth_by_timeframe`）→ 下界 → `setLookaheadLowerBound`。**接上之前，B1 交付的下界鎖定在生產上等於沒作用** |
| 深度函式已存在且**不得再寫第二份** | `momentum/Analysis/event_samples/lookahead_depth.py::depth_by_timeframe` | 2.1b 已交付；B5 只呼叫。B3 的 `1.9-M4`／`1.9-M5` mutation 就是在守這條 |
| 條件引擎契約已存在 | `momentum/Analysis/event_samples/condition_engine.py`＋`contracts/condition_engine.json`；`ConditionSpec.column_roles` 給引用欄 | 2.1 之條件物件若要走後端驗證，經 `EventSamplePipeline.condition_engine_contract()` 出口 |
| `filters` 之 wire shape **尚未凍結** | `event_import_contract.json` 之 `label_definition.fields.filters` 只寫 `{"type": "object"}` | 🔴 這是 B3 之具名殘留 **`R-B3-2`**：B3 的 L2 目前對「有 `filters` 但抽不出欄名」一律強制宣告。**Task 2.2 定案 wire shape 時必須同批把 `lookahead_declaration.filters_referenced_columns()` 改為精確抽取**，否則帶條件的 CSV 會一直多要一次宣告 |
| 匯出筆數目前無單一計算函式 | `search/page.tsx` 內散在各處 | 2.3 要抽 `computeExportCounts(rows, filters) -> {N, M, X, Y}`，並成為 1.5／2.1／4.1b／7.3 **四個顯示點之唯一來源** |

### 2B.2 B5 三個 Task 之關鍵座標

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **2.1** 篩選面板 | `582` | `1799–1810` | `frontend/src/app/search/page.tsx`；型別入 `types.ts` | `npm --prefix frontend test -- --run exportFilter` **≥6 條**（含「篩選後筆數 == 手算筆數」數值斷言）；mutation 1 條 |
| **2.2** 條件寫入 `filters` | `655` | `1865–1879` | 🔴 實際落點見 2B.1（`eventExport.ts`，與 TODO 字面不同，須回報） | `npm --prefix frontend test -- --run exportFilterPersist` **≥2 條** ＋ 契約防漂移之 `python3 -c ...` rc=0；mutation 1 條 |
| **2.3** 即時筆數 | `679` | `1880–1891` | `frontend/src/lib/`（新增 `computeExportCounts`）＋`search/page.tsx` | `npm --prefix frontend test -- --run exportCounts` **≥2 條**；mutation 1 條 |

### 2B.3 B5 之陷阱

1. **2.1**：只篩**數值**欄（字串欄不得出現在可選清單）；條件為空 ⇒ 匯出筆數 `==` 原筆數
   （不得因面板存在而改變預設行為）；面板**不改任何原始欄位值**。
2. **2.2**：🔴 **不得把篩選條件納入 `event_id` 之輸入**（違反 D-2；mutation 就是打這條——
   納入後 Task 1.3 之 `event_id` 集合相等斷言須紅）。序列化**一律引用 §G S-1..S-9**，不自訂。
3. **2.3**：🔴 **不得以估算值**；`N + 被濾掉數 == M`、`X + Y == N` 兩條守恆是驗收本體。
   四個顯示點**共用同一函式**——否則同一畫面會出現互相矛盾的筆數（RISK-(b)）。
4. **A-004 接線**：這是 B5 的**隱性必辦**，TODO 沒把它列成獨立 Task，但 D-002 明寫
   `blocked-by` Task 2.1。做完 2.1 若沒接上，B1 的下界鎖定仍是死碼。

### 2.4 之後的批次（不在本批，僅供排序）

| 批 | Task | 依賴 |
|---|---|---|
| B6 刪除 | Phase 3 全部 | 無 |
| B7 匯出端報酬欄 | Phase 4 全部（4.2 之 S-9 已於 B1 完成） | B1、Task 2.1b |
| B8 訊息與表頭 | Phase 5 全部 | Task 5.0 |
| B9 IC 止血閘 | Phase 6 全部 | Task 6.0 |
| B10 全棧接線 | Phase 7 全部 | B1–B9 |

---

## §3 派工管線（**大任務**，不得跳步）

命中高風險 (a) 數值/資料品質 ＋ (b) 跨模組 ⇒ **大任務**。SPEC／TODO 皆已凍結、已過 adversarial
⇒ **實作階段之管線為**：

1. **實作＝Claude 主委自任**（`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行；
   機器版 SoT＝`scripts/governance_roles.json`：`implementer=claude`、`reviewers=[codex,composer,grok]`）。
   🔴 **派工前必先重讀該行＋該 JSON**——選層是動態的，以使用者當下指示為準。
2. **每批收尾必派 code review**：三家全員，**實作者不自審**。
3. **開門**：先跑 `bash scripts/gate.sh dispatch --task-id … --risk … --intent … --facts-asked … --review-role … --template …`
   🔴 **必須先開 token，`committee_run.sh` 本身也會被 PreToolUse 擋**（B3 第一次派工就撞到）。
   🔴 **`--task-id` 必須是 session 名之全大寫形式**（session `20260826-gap3ux-b4-review-r1`
   ⇒ task-id `20260826-GAP3UX-B4-REVIEW-R1`）。
4. **派工指令**（B2／B3 實測可用，逐字照抄改 session 名即可）：
   ```bash
   bash scripts/committee_run.sh --session <session> <brief> <out-prefix> codex,composer,grok \
     -- --intent "…" --risk low --facts-asked "…" --review-role "reviewer（…）" \
     --template "n/a: 用 brief" --task-id "<SESSION 大寫>"
   ```
   丟背景跑；三家平行，B3 之 R1 約 12 分鐘、R2／R3 各約 10 分鐘。
5. **收集**：`bash scripts/reconcile_build.sh <session> --mode review <三個 -family.md>`
   → 手填 `synth.md` 之「群集／處置」＋ `**Verdict**:` 行 →
   `bash scripts/reconcile_cluster_attribution_check.sh <synth.md>`（rc=0）→
   🔴 `bash scripts/completeness_check.sh --lock <session>/sources.lock`
   （**只給 lock 路徑，不得再帶 synth.md**——多一個參數就 fail）。
6. **清債**：`bash scripts/debt_clear.sh --round-id <id> --session <name> --lock <sources.lock>`。
   `round_id` 由 `committee_run.sh` 輸出（`grep -oE "round_id=[a-f0-9-]+"`）。
   🔴 **債未清會擋掉下一輪派工**。
7. **前後**：`bash scripts/agent_preflight.sh` → 派工 → `bash scripts/agent_postflight.sh`，PASS 才驗收。
8. **兩輪斷路器**：任何問題自己弄 ≤2 輪仍失敗 ⇒ 立即開委員會，禁 solo 硬幹。

**B1／B2／B3 之實績供校準**：
- B1：五輪，findings **3 → 2 → 10 → 7 → 0**。
- B2：兩輪，findings **2 → 1**；P0／P1 全程 0。
- B3：三輪，findings **6 → 3 → 0**；三家 Verdict 於 R1／R2 **不一致**，R3 首次一致。

### 🔴 B3 學到的三件事（B4／B5 直接沿用，別重踩）

1. **三家不一致時，去查 SPEC 原文，不要數人頭。**
   R2 時 codex 判 BLOCKING、另兩家判可進；主委逐字調出 SPEC §D-3′-a(ii) 的「明令禁止」段，
   確認 codex 引用成立 ⇒ 採嚴格版。**引用可查證的一家 > 兩家的印象**。
2. **修一輪的 finding 可能生出新的**：R1 修「embargo 沒接進 split」時，
   主委寫的 `max(values)` 正好命中 SPEC 明令禁止的「以單一 batch scalar 冒充 per-scope 下界」。
   ⇒ **每輪修完都要問一次「這個修法本身有沒有違反別的條文」**，並把它寫成 brief 的必答題。
3. **對「主委宣稱已補」型的前提要逐欄實查**（r2 synth 群集 K）：
   composer 連兩輪把主委的宣稱當事實而漏抓；R3 改用
   `model_fields`／`grep -A20`／`grep -n` 逐欄對證後，三家結論首次一致。
   ⇒ **建議寫進每份 review brief 的常設條款。**

---

## §4 「完成」的判準（不得放寬）

一個 Task 標 ✅ 的條件：
1. 該 Task「驗證」欄之命令**全部 rc=0**，且條目數 ≥ TODO 所列下限；
2. **該 Task 之 mutation 已實跑**——故意改壞 ⇒ 對應斷言**轉紅**；還原 ⇒ 轉綠；
3. **receipt 路徑寫進 commit message**（`VERIFY:<path>`，冒號後不得有空格）。

🔴 **只有測試綠、沒有 mutation receipt ⇒ 仍是 🔧，不是 ✅。**
🔴 **mutation 判準＝轉紅之 test 集合逐一等於預期**（多紅少紅皆 FAIL）。

**批次間 Gate**：上一批全部 mutation 轉紅並還原轉綠、receipt 入 commit，才可開下一批。

**每批收尾固定動作**：更新 `白話說明/GAP-3施工看板.md`（每完成一個 Task 改一列、更新「一眼看完」三個數字）
＋ `白話說明/GAP-3施工進度.md`（歷史敘事）＋ `bash scripts/plain_docs_render.sh`（生成 HTML，同 commit）
＋ `docs/ROADMAP.md` ＋ `HANDOFF.md` ＋ commit ＋ **背景 push**（使用者在外看進度）。

### 4.1 怎麼寫 mutation runner（已隔離，可平行）

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from mutation_worktree import IsolatedWorktree, venv_python   # noqa: E402

with IsolatedWorktree(prefix="b4mut_") as wt:
    ...   # 所有改檔與 pytest 都在 wt 底下；主 repo 一個位元組都不動
```

- **現成範本（強烈建議直接複製改）**：`handoffs/gap3ux_b3_mutations.py`（13 條，最新、含
  `--record` 模式與外置預期集合 `handoffs/gap3ux_b3_expected.json`，每條都有 `_<id>_why` 語意說明）。
  另有 `gap3ux_b2_mutations.py`（14 條，含 **vitest selector** 之寫法——B4／B5 前端條目會用到）
  與 `gap3ux_b1_mutations.py`（32 條）。
- **工作流**：先 `--record` 跑一次取得實際紅集合 → **逐條人工對證語意**（不是抄輸出了事）→
  寫進 `<epic>_expected.json`（含 `_<id>_why`）→ 不帶 `--record` 跑正式 receipt。
  合併工具：`venv/bin/python handoffs/b3_merge_expected.py <mutation_id>`（只搬已寫 `_why` 的條目）。
- 官方單條 CLI：`bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>`。
- 🔴 `<檔>` 須為 **repo 相對路徑且不含 `..`**，否則 rc=2 拒收。
- 🔴 **parametrize 的 test id 不得含空白**——runner 以空白切 node id，
  帶空白的 label 會讓紀錄下來的 id 被截斷、「逐一相等」比的是半截字串（B3 實際踩到）。
- ⚠️ `handoffs/*.py` 與 `handoffs/*.json` 由 **`.git/info/exclude:21`** 排除
  ⇒ **runner 本身不入版控，換機器就沒有**；入版控的只有 `scripts/mutation_worktree.py`、
  官方 CLI、與 `handoffs/run_receipts/*.json`。

### 4.2 🔴 mutation 抓假綠之實例（B2／B3 實際發生，B4／B5 照著防）

1. **比對對象錯層**：Task 1.8 用**原始列**比對，把「預設值未寫出」誤判成異質 ⇒ 改比對**正規化後**的列。
2. **golden 生成順序**：斷言寫在寫檔**前** ⇒ 後端被改壞時 golden 不重生、前端**假綠**
   （`1.3-M1b` 錄到**空紅集合**才抓出來）⇒ 改成**先寫檔再斷言**。
3. **測到 fixture 而非生產接線**：新斷言直接呼叫工廠，但該檔 autouse fixture 已 monkeypatch 掉單例
   ⇒ 驗到的是 fixture 注入物件（`1.2-M4` 空紅集合）⇒ 測試內先把單例清成 `None`。
4. **（B3 新增）fixture 使被測輸入恆為空**：Task 1.9 ⑤ 的 fixture 讓引用欄永遠是空集合
   ⇒ codex 的「把 `referenced_for_depth` 改成 `()`」變異算出**同值**、探針仍被呼叫一次
   ⇒ 兩條斷言都綠。修法＝fixture 改為引用可解析欄，並加「**餵進去的是什麼**」的斷言。
5. **（B3 新增）response_model 靜默濾欄**：後端加了鍵但 `EventAnalyzeResponse` 沒宣告
   ⇒ FastAPI **靜默丟掉**，前端永遠看不到。加 response 鍵時**必須同步改 pydantic 模型與 `types.ts`**。

**共同形狀＝「錄到空紅集合」就是假綠的信號**。`--record` 出現 `紅=[]` 一律當作
「這條測試沒有在測它宣稱在測的東西」，先查根因再往下走。

---

## §5 未辦事項（開工前／收 epic 前要處理）

| # | 事項 | 何時 | 狀態 |
|---|---|---|---|
| 1 | **延伸檔 D-003**：更正兩處 doc drift——①TODO Task 1.3「修改檔案」行之 `api/routes/case.py` 字面；②**TODO Task 2.2「修改檔案」行之後端序列化函式字面**（實際在 `frontend/src/lib/eventExport.ts`，見 §2B.1） | 收 epic 前 | ⬜ **不擋 B4／B5，但 B5 動到 2.2 時應一併處理** |
| 2 | 動過 `scripts/` ⇒ 收 epic 前跑 `bash scripts/gov_check.sh --no-probe`（丟背景，十分鐘級） | 收 epic 前 | ✅ 2026-08-25 已跑；**B2／B3 皆未動 `scripts/`**。若 B4／B5 動了需重跑 |
| 3 | **GAP-3 B5 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`） | 使用者 | ⬜ **未簽字不收案** |
| 4 | 根目錄 `.probe_ic{,2,3}.sh` 三個 untracked 檔為更早批次殘留 | 隨時 | ⬜ 未納入任何 commit；要清可直接刪 |

---

## §6 地雷（本 epic 專屬，逐條是實際踩過的）

### 6.1 🔴 「比對範圍過寬／失真」——主委在本 epic 犯了**七次**，形狀完全相同

| # | 形態 | 後果 |
|---|---|---|
| 1 | Phase Gate 之測試層標籤與 Task 欄位**同字面** | 機械閘分不出來 |
| 2 | 以**行號**注入修補，行號取自修補**前**之掃描輸出 | 三處落到**錯的 Task** |
| 3 | 判斷 Task 有無 mutation 時掃**整個區塊** | 被區塊尾端別人的字樣騙過（假跳過） |
| 4 | 同步斷言只驗**子字串存在**，散文卻宣稱「參數名序列逐字相等」 | **假綠**，改參數名照樣過 |
| 5 | 驗 gitignore 時問**目錄** | `.gitignore` 之 `*.h5` 沒被看見 ⇒ 隔離副本缺 fixture、全紅 |
| 6 | 驗「兩件事不共用序列化路徑」時掃**整段原始碼文字** | 自己 docstring 裡的字樣讓斷言誤紅 ⇒ 改用 AST 只看**實際呼叫了什麼** |
| 7 | **（B3 新增）** parametrize label 含空白 ⇒ mutation runner 記錄的 node id 被截斷 | 「逐一相等」比的是**半截字串** |

**共同形狀＝拿比目標更大／更小的範圍去比對，然後把命中當成目標命中。**
🔴 **對策（照做）**：①錨點落在**真正要判斷的那個東西**上——不是它的段落、不是行號、不是附近的字
②**一律字面錨點，禁行號** ③檢查寫完要用**已知會紅的輸入**試一次，只看綠不算驗過。

### 6.2 🔴 **不要用原始碼形狀證明執行期性質**（B1 R3 → B2 R1 → B2 R2 → B3，同一病四度出現）

- **B1 R3**：用原始碼形狀證明「阻擋早於網路動作」⇒ 修法是**改設計讓它變成結構保證**
  （整段匯出包進 `withHorizonLowerBoundGuard(…, {proceed})`）。
- **B2 R1／R2**：V-3 之 AST oracle 被 assignment／subclass／factory-return 逐一繞過
  ⇒ 最終改採**執行期**錨點（工廠回來那個物件之 `import_records` **就是**共用那一個 function object）。
- **B3**：1.12 驗收①用 **monkeypatch 計數 `== 0`** ＋ **同時斷言表產得出來**
  （只斷言「沒呼叫」的話，一條 raise 在最前面的實作也會綠）；
  1.9 ⑤用**函式物件同一性 ＋ 呼叫探針 ＋ 餵入內容**三重（前兩重仍被 codex 找到假綠反例）。

**B4／B5 之高風險面**：
- **1.5 邊界①「未勾確認 ⇒ `fetch` call count == 0」**——用 `vi.fn()` 計數，
  **不要**斷言按鈕有 `disabled` 屬性（那是形狀，且可被繞過）。
- **2.3「四個顯示點共用同一函式」**——用**函式物件同一性＋呼叫探針**（照 B3 之 1.9 ⑤ 寫法），
  不要斷言「原始碼裡都有出現 `computeExportCounts` 字樣」。

### 6.3 產出端閘會擋你，而且多半擋對了

- `doc_format_precheck.sh`：驗證欄須**逐行**含可證偽 token（`pytest`／`==`／數字／`.py`…）。
- commit message：`VERIFY:<path>` **冒號後不能有空格**，且該檔須含 `CLOSED`／`APPROVED` 等閉合判詞
  （🔴 由 runner 直接寫 `closure` 欄，**不要**事後手補）。
- 🔴 **`Governance-Scope: out-of-epic <理由>` trailer**：staged 含 epic scope 外路徑時**必加**，
  且**必須在 commit 訊息之最後一段**（git 只解析最末段；與 `Co-Authored-By` 同段即可）。
  B1／B2／B3 之六個 commit 都加了，可直接複製措辭。
- 🔴 **`factkey_write_guard.sh`（PostToolUse）會擋「識別碼緊接狀態」之句型**：
  在 `HANDOFF.md` 寫「B3 已落地」「B2 已完成」會 fail-closed。
  改寫成不含批次代號的句子（例如「Task 1.11／1.12／1.9 之程式碼已寫入 repo」）即過。
- 計數字面稽核：說明文字裡的「一支」「一筆」也會被當計數字面 ⇒ 改措辭。
- 白話狀態檔（`README.md`／`接下來要做什麼.md`）**禁純檔尾追加**，須改寫現況段。
- `plain_docs_sync_check.sh`：改過 `scripts/`／`docs/GOV*`／`tests/governance/` 才會要求同步治理白話檔。
- 🔴 **改過 `白話說明/*.md` 必須跑 `bash scripts/plain_docs_render.sh` 並把 `docs/site/` 一起 staged**
  ——pre-commit 會檢查 22 檔與來源一致。
- 🔴 **R3 解耦閘掛在 `PostToolUse`**：api 層直接 `from momentum.Analysis...import` 會**當場被擋**。
  改走 `EventSamplePipeline` 之 `@staticmethod` 出口（見 §0 出口清單）。

### 6.4 工具與環境

- **本機 bash 3.2.57** ⇒ **無 `declare -A`**；`sed` 為 BSD ⇒ 一律用 `sed -E`。
- 🔴 **絕不寫 `cd <專案路徑>` 前綴**——會讓每個指令走權限分類器（2.3s 起跳，~7% 機率變 600s）。
  **前端指令一律用** `npm --prefix frontend test -- --run` ／ `npm --prefix frontend run build`。
- 瑣事別用 `python3 -c`；改檔一律用 Edit／Write 工具。
- `pytest tests/api tests/momentum/event_samples` 全量約 **6.5 分鐘** ⇒ 丟背景。
- `pytest tests/governance` 與 `govb1_final_gate.sh` 全跑皆**十分鐘級** ⇒ 一律丟背景。
- 委員會清 `/tmp` ⇒ 自己導到 `/tmp/x.log` 的檔可能被刪；重要輸出看 harness task output 檔。
- `handoffs/` **未入版控**（勿清）。
- 跑完測試須 `bash scripts/restore_golden_inventory.sh` 還原 golden inventory 副作用。

### 6.5 🔴 治理現況（2026-08-25 實測，**皆既有債，不要以為是自己弄的**）

| 檢查 | 結果 | 歸屬證據 |
|---|---|---|
| `gov_check.sh --no-probe` 段 4 **G-7 scope 淨差** | FAIL，**383 條**「未宣告即修改」 | 於 `HEAD~2` 隔離 worktree 跑同一條閘**亦 FAIL 且路徑集合逐一相同** |
| `pytest tests/governance -q` | **1743 passed / 6 failed** | 於 `HEAD~3` 隔離 worktree 實跑同這 6 條，**同樣 6 failed** |
| `pytest tests/api tests/momentum/event_samples` | **887 passed / 3 failed** | 以 `git stash` 實跑證實改動前後**逐字相同** |

**那 3 條 failed 之名單**（B4／B5 若看到同樣這幾條，**不是你弄的**）：
`test_batch_alias.py::test_patch_batch_alias_deleting_returns_409`、
`test_progress_rss_fields.py::test_parity_batch_rest_worker_rss_and_schema_version`、
`test_progress_rss_fields.py::test_parity_concurrent_gt_one_no_fake_stage`。
⚠️ 交接舊版另列 3 個 **error**（`test_feature_export` ×2、`test_run_lifecycle_api` ×1），
**B3 兩次全量跑皆未重現**＝順序相依，歸屬 `R-B1-1`。

- 🔴 **連帶效果**：`gov_check` 段 4 FAIL 後**不再往下跑第 5／6 段** ⇒ 全套 pytest 從未經由 gov_check 執行。
- 兩條治理債已登記為 `R-GOV7-1`／`R-GOV7-2`，三值理由 `user-ruling`，**不排工**。

---

## §7 🔴 不要碰的東西

### 7.1 治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
⇒ **遇治理工具壞掉：繞過並具名記錄，不修、不開票。要動須使用者明示。**
⇒ **落地出錯就抄仔細**，不要「做一支工具來量自己」。
⇒ **治理／工具問題不得寫進派工單**，那是迴圈的燃料。

🔴 **唯一已獲明示授權之例外（2026-08-25，已完成）**：mutation 併發隔離
`scripts/mutation_worktree.py` ＋ `scripts/verify_mutation.sh`。用法見 §4.1。

### 7.2 已具名封存之殘留（**不排工、不另立票**）

- **SPEC 末節 F-1..F-4**：同輪重派死鎖／補丁包檔名碰撞／編排草圖含 illustrative 佔位／
  `gap3ux_apply_patch.py` 包側 VERIFY 缺陷。
- **TODO（R3 reconcile）四條**：前端 directory-only 路徑 10 處／Task 5.0 驗證 defer SPEC／
  五 Task（1.10／3.3／4.3／7.3／7.5）之 mutation 全文 defer SPEC／B1 須並讀 FROZEN SPEC。

### 7.3 具名殘留全文（**本節為全文；`HANDOFF.md` 只指回這裡**）

| 代號 | 內容 | 三值理由 | owner／觸發 |
|---|---|---|---|
| `R-GOV7-1` | G-7 scope 淨差長期紅（383 條）。判準要求 trailer 落在**該 commit 自身** ⇒ 前向修不掉 | `user-ruling` | 主委 |
| `R-GOV7-2` | 治理 pytest 6 條長期紅；其中 2 條之斷言比 2026-08-14 之使用者裁定舊 | `user-ruling` | 主委 |
| `R-B1-1` | 全量跑之測試順序污染（`test_progress_rss_fields` 兩條、`test_feature_export`／`test_run_lifecycle_api` 之 error 時有時無）。歸因**未實跑證明** | `needs-research` | 主委 |
| `R-A005-1` | `lookahead_registry` 之 `_PRODUCER_SEMANTICS` 表為人工稽核非執跑探針；與 producer 漂移時本閘看不見 | `needs-research` | 主委；**觸發＝下次動到 `CaseSearchEngine` 未來欄計算段時一併做** |
| `D-002 A-004` | 前端下界**值來源**未接上（`lookaheadLowerBound` 恆 `null`，`search/page.tsx:59-60` 有 `void` 佔位） | `blocked-by` Task 2.1（B5） | 主委；**B5 必辦** |
| `D-001/D-002 provenance` | `gate.sh register-output` 只收 `handoffs/` 或 `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報 provenance pending（**非戳記造假**） | `user-ruling` | 主委 |
| **`R-B4-1`** | **CSV 方言之殘餘前後端差異**：支援之行尾＝**LF／CRLF**；引號內 CR 當資料保留；裸 CR（含舊式 Mac）兩端一致不支援。其他方言／編碼／writer 癖好之殘餘差異**不再逐一開輪**。兜底＝後端永遠是契約權威；前端只做預覽且**不得產出看似合理的假欄名**（該不變式由 mutation `1.5-M5` 鎖住）。R6 由 codex 以 **9,331 個字串窮舉**比對兩端 predicate，`mismatch_count=0` | `user-ruling`（95% 解法就收；三家 R5／R6 一致裁定） | 主委；**觸發＝出現具體且可重跑之使用者實例才重開，不預先開票** |
| ~~`R-B2-1`~~（B4 已解除） | **秒級 t0 之 `event_id` 摩擦**：使用者上傳秒級 `t0` 的 CSV 時，`event_id` 仍須寫 **ms 版**（否則 fail-closed 拒收並列出期望值）。三家一致判**屬 Task 1.5** | `blocked-by` Task 1.5（B4） | 主委；**B4 必辦** |
| `R-B2-2` | **執行期 oracle 之 factory-body 繞法**：新斷言綁 `get_event_import_service()` 之回傳；若日後另立第二個工廠且 route 改呼叫它，本閘看不見 | `needs-research`（正解為 route 層之執行期 wiring 探針） | 主委；屬 **B10 全棧接線** |
| **純 JS 手刻 sha256** | 不經 `crypto.subtle`／`node:crypto` 入口之手刻實作，前端 ④(a) 之封閉枚舉看不見 | `needs-research` | 主委 |
| **`R-B3-1`** | Task 1.9 ⑤ 之「系統內篩選路徑」**端到端**對證缺席——該 production caller 尚不存在，本批以「函式物件同一性 ＋ 餵入之 `referenced_columns` 非空且相等」鎖住 | `blocked-by` Task 2.1（B5）／Task 4.1（B7） | 主委；**B5 落地時補端到端** |
| **`R-B3-2`** | `label_definition.filters` 之 wire shape 未凍結 ⇒ 引用欄採「抽不出即強制宣告」之 fail-closed 止血；在 Task 2.2 定案前，帶 `filters` 而抽不出欄名之 CSV 會多要一次宣告 | `blocked-by` Task 2.2（B5） | 主委；**B5 收斂時改為精確抽取** |
| **`R-B3-3`** | 逐 symbol 之 purge 下界（`EventSplitConfig.embargo_ms_by_symbol`）未實作 ⇒ 各 symbol 宣告下界**不一致**之批次一律拒絕分析（fail-closed，不取全批 max——SPEC §D-3′-a(ii) 明令禁止「以單一 batch scalar 冒充 per-scope 下界」）。使用者當前解法＝依 timeframe 拆批 | `blocked-by` Task 7.0b（SPEC 已把該 API 之唯一實作與驗收 ⑨ 鎖在該 Task） | 主委；7.0b 落地時解除 |

🔴 **B4 必辦 `R-B2-1`、B5 必辦 `D-002 A-004` 與 `R-B3-1`／`R-B3-2`**——這四條的 `blocked-by`
指的正是這兩批，做完該 Task 卻沒解除殘留＝殘留變偷懶（使用者 2026-08-17 定死）。

---

## §8 檔案地圖（B4／B5 會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組 | `momentum/Analysis/event_samples/`：`pipeline.py`／`tables.py`／`event_split.py`／`ic_feed.py`／`lookahead_registry.py`／`lookahead_depth.py`／**`lookahead_gate.py`**（B3）／**`lookahead_declaration.py`**（B3）／`import_contract.py`／`canonical_serialize.py`／`condition_engine.py`／`alignment.py`／`dedupe.py`／`types.py` |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`（**1.6 要在此加 receipt 欄**）、`future_column_lookahead.json`、`condition_engine.json`、`ic_report_contract.json` |
| case 端點 | `api/routes/case.py`：`import_events_file` ／`import_events_json`／`import_events_csv`（**1.5 之目標端點**）／`lookahead_declaration_preview`（B3 新增）／`analyze_event_import` |
| 匯入服務 | `api/services/case_import_service.py::EventImportService`：`parse_upload`／`file_columns`（B3）／`csv_records_from_mapping`／`import_records`（**1.6 落點**）／`_assert_scope_embargo_expressible`（B3）／`analyze` |
| 搜尋結果端點 | `api/routes/case_search.py::get_task_result` ＋ `_attach_canonical_source()` |
| 前端（B4） | `frontend/src/app/data-preparation/page.tsx`（匯入頁）／`components/case/EventImportForm.tsx`／`components/case/LookaheadDeclarationFields.tsx`（B3，**新 UI 須沿用**）／`lib/lookaheadDeclaration.ts` |
| 前端（B5） | `frontend/src/app/search/page.tsx`（1,617 行；匯出在 `exportSearchResultsToEventJson()` `:507`；`lookaheadLowerBound` `:59-60`）／`lib/eventExport.ts`（**2.2 實際落點**，`label_definition` 在 `:103`）／`lib/lookaheadDepthLock.ts`／`lib/types.ts` |
| API 模型 | `api/models/event_import_models.py`：`EventImportResponse`／`EventImportRejected`／`EventAnalyzeResponse`（🔴 加 response 鍵必須同步改這裡，否則被靜默濾掉） |
| mutation receipt | `handoffs/run_receipts/gap3ux-b{1,2,3}-all-mutations.receipt.json`（32／14／13 條） |
| mutation runner 範本（**未入版控**） | `handoffs/gap3ux_b3_mutations.py` ＋ `gap3ux_b3_expected.json` ＋ `b3_merge_expected.py`；vitest selector 寫法見 `gap3ux_b2_mutations.py` |
| reconcile 收斂檔 | `handoffs/reconcile/20260824-gap3uxtodo-x-review-r{1,2,3}/synth.md`（TODO）／`20260825-gap3ux-b2-review-r{1,2}/synth.md`／`20260825-gap3ux-b3-review-r{1,2,3}/synth.md` |
| 過程與教訓（給使用者） | `白話說明/GAP-3施工看板.md`（進度）、`白話說明/GAP-3施工進度.md`（歷史）、`白話說明/流程摩擦記錄.md` |
