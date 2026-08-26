# GAP-3 事件型 UAT 缺口修補 — **實作交接**（更新於 2026-08-26，B6／B7 開工態）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0；B1–B5 皆已收斂並蓋章；下一步＝B6（Phase 3 刪除）＋ B7（Phase 4 匯出端報酬欄）。**

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 D-001（**須並讀**） | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ✅ 三家 APPROVED | `81cbe7ab` |
| TODO 延伸檔 D-002（**須並讀**，A-002..A-015） | `docs/GAP3_EVENT_UX_TODO.D-002.md` | ✅ 三家 APPROVED | `51f1a65e` |
| TODO 延伸檔 D-003（**須並讀**，A-016..A-019） | `docs/GAP3_EVENT_UX_TODO.D-003.md` | ⬜ **尚未過戳記輪**（見 §5） | `09884811` |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 16 ✅／1 🔧／25 ⬜ | 每批收尾更新 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001／D-002／D-003**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 之自傷絕大多數出自副本漂移。

### 前五批已交付什麼（B6／B7 可以直接用）

| Task | 產出 | 可直接 import 的東西 |
|---|---|---|
| 1.1 | typed namespace-aware `receipt_schema` | `import_contract.py`：`flatten_receipt_schema()`／`receipt_type_ok()`（含 `Mapping[str,str]`）／`validate_receipt_namespace()`／`capability_unavailable_reason()` |
| 1.10 | `contracts/future_column_lookahead.json`（**37 個 future 欄，全部以 `future` 開頭**） | `lookahead_registry.py`：`load_lookahead_registry()`／`resolve_lookahead_bars()`／`registry_resolvable_columns()`／`requires_declaration()`／`unregistered_future_columns()` |
| 2.1b | **唯一** exported 深度函式 | `lookahead_depth.py::depth_by_timeframe()`；前端 `lookaheadDepthLock.ts::withHorizonLowerBoundGuard()` |
| 4.2（僅 §G S-9） | canonical bytes 參考實作 | `canonical_serialize.py`：`canonical_event_table_bytes()`／`canonical_event_table_sha256()`／`canonical_source_bytes()` |
| 1.2／1.3／1.4／1.8 | CSV 對映端點、`event_id` 之 D-2 唯一定義、t0 單位偵測、異質列拒收 | `case.py::import_events_csv`；`EventImportService.csv_records_from_mapping()`／`file_columns()`；`import_contract.canonical_event_id()`／`detect_t0_unit_ms()` |
| 1.11／1.12／1.9 | L2 強制宣告、L3 閘與 event-study-only executor、答案窗宣告 | `lookahead_gate.py`／`lookahead_declaration.py`；前端 `lookaheadDeclaration.ts`＋`LookaheadDeclarationFields.tsx` |
| **1.5／1.6／1.7**（B4） | CSV 對映 UI、對映 provenance、可疑欄警示 | `EventCsvMappingForm.tsx`；`csvPreview.ts`（`parseCsvText`／`countDeclaredLabels`）／`suspiciousBinaryColumns.ts`／`eventIdNormalization.ts`；契約新增 `receipt_schema.mapping_provenance`（七欄） |
| **2.1／2.2／2.3**（B5） | 匯出前篩選、條件寫入 `filters`、即時筆數 | `exportFilter.ts`（`applyExportFilters`／`buildExportFilterSpec`／`nextLowerBoundState`／`exportAllowedUnderBound`／`horizonOptions`）／`exportCounts.ts::computeExportCounts`；契約新增 `label_definition.fields.filters.wire_shape` |

### `EventSamplePipeline` 之 R3 出口清單（api 層只能經這些取用 momentum）

`import_contract()`／`canonical_event_id()`／`event_id_template()`／`mapping_failure_reasons()`／
`normalize_t0_units()`／`canonical_source_payload()`／`condition_engine_contract()`／
`bars_from_kline_cache()`／`validate()`／`run()`／`run_with_params()`／`analyze_tables()`／
`requires_lookahead_declaration()`／`lookahead_declaration_defaults()`／`resolve_lookahead_declaration()`／
`apply_lookahead_horizon_projection()`／`lookahead_split_blocked()`／`split_blocked_capability_reason()`／
`run_event_study_only_with_params()`／**B4 新增** `validate_receipt_values()`／**B5 新增** `lookahead_depth()`
（見 `momentum/Analysis/event_samples/pipeline.py` 之 `@staticmethod` 區）。
🔴 **B6／B7 若要讓 api 層用到其他 momentum 內部函式，必須在此加出口**——直接
`from momentum...import` 會被 `scripts/check_decoupling_imports.py`（R3）在 PostToolUse 當場擋掉。
🔴 **出口一律回純資料**（dict／bool／str），例外型別不跨界。

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
git log --oneline -5                            # 期望最新為 B5 收斂之 docs commit
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-003.md  # 期望 rc=0
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
python3 scripts/gap3_freeze_golden.py --check   # 期望 rc=0，canonical_sha=163c4cec…（本條約 15 秒）
venv/bin/python -m pytest tests/momentum/event_samples/ -q            # 期望 279 passed
venv/bin/python -m pytest tests/api -q -k "gap3_csv or gap3_export_filter or lookahead_declaration or gap3_horizon or gap3_import or gap3_t0_unit or gap3_heterogeneous or gap3_source_digest or gap3_contract_reason or gap3_lookahead"   # 期望 164 passed
npm --prefix frontend test -- --run             # 期望 45 files／269 passed
npm --prefix frontend run build                 # 期望 rc=0
```

B1–B5 之 mutation receipt 為 `handoffs/run_receipts/gap3ux-b{1,2,3,4,5}-all-mutations.receipt.json`
（32／14／13／15／19 條），皆 `closure: CLOSED`。**不需重跑**，除非你改了那幾批的產出。

🔴 **B7 會讓上表第 6 條（golden）之期望值合法改變**——見 §2B.3。

---

## §2 B6 是什麼（Phase 3 全部，三個 Task）

**B6 ＝ 事件批次刪除 ＝ Task 3.1（DELETE 端點）、3.2（前端刪除鈕與二次確認）、3.3（已被引用之警語）。**
依 §B 拓撲，B6 **無前置依賴**。

> **一句話**：讓使用者刪掉一批匯入的事件，**不留孤兒檔**，並在刪之前告訴他
> 「引用它的分析結果將無法重現」。

### 2.1 🔴 偵察結論（2026-08-26 主委實跑，下個 session **不必重查**）

| 事實 | 位置 | 對 B6 的意義 |
|---|---|---|
| **一批匯入只落一個檔** | `EventImportService.import_records()`：`<storage_dir>/<import_id>.json`（預設 `data_cache/events/`） | 3.1 之刪除範圍**就是那一個檔**——Phase 1 之 receipt（`mapping_provenance`／`lookahead_declaration`）與 Phase 2 之 `filters` 都住在**同一個 payload 內**，不是獨立檔 ⇒ TODO 所說「刪除範圍須隨 Phase 1／2 同步擴張」在現況下**已自動滿足**，但**要在測試裡釘住**（日後有人把 receipt 拆出去就會破） |
| `analyze` **不落任何檔** | `EventImportService.analyze()` 回 `EventAnalyzeResponse`，全程不寫磁碟 | 3.1 不需處理分析產物；邊界②（殘留檔數 == 0）可直接以 `storage_dir.glob("*.json")` 驗 |
| 既有讀取端點 | `api/routes/case.py::get_event_import`（`GET /case/events/{import_id}`）、`list_event_imports`（`GET /case/events`） | 3.1 之 `delete_event_import` 緊鄰它們放；`get_import()` 已有 path traversal 防護（`".." in import_id` ⇒ None），**刪除方法要沿用同一條防護，不要另寫** |
| 批列表 UI 落點 | `frontend/src/app/data-preparation/page.tsx` 之 `data-testid="event-imports-list"` 區塊（用 `listEventImports()`；每列已有 `import_id`／`n_events`／`imported_at`） | 3.2 之刪除鈕落在此；**確認框要顯示的「筆數與匯入時間」該列已經有了**，不必另查（TODO 實作要點 1 明寫） |
| 🔴 **「被引用」沒有現成紀錄** | `ic_survivors_{case_id}.json` 以 **case_id** 為鍵；repo 內查不到任何把 `import_id` 寫進分析產物的地方 | 3.3 之「該批是否被引用」**目前無資料來源**。⇒ **必須在 brief 具名請三家裁**判準（例如：以 IC 分析頁選過該批之本地紀錄／或改為「一律顯示但措辭為條件句」）。**不裁就做，會做出一個永遠顯示或永遠不顯示的警語，邊界②（未被引用者不顯示）直接失去鑑別力** |
| 前端測試檔名 selector | `eventBatchDeleteConfirm`（3.2）／`eventBatchDeleteWarning`（3.3） | 🔴 vitest selector 靠**檔名**匹配，現有檔名都不匹配，須新建 |

### 2.2 B6 三個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **3.1** DELETE 端點 | `717` | `1894–1907` | `api/routes/case.py`＋`case_import_service.py` | `pytest tests/api -q -k gap3_event_delete` **≥4 條**；mutation 1 條 |
| **3.2** 刪除鈕與二次確認 | `740` | `1908–1918` | `frontend/src/app/data-preparation/` 之批列表 | `npm --prefix frontend test -- --run eventBatchDeleteConfirm` **≥2 條**；mutation 1 條 |
| **3.3** 已被引用之警語 | `761` | `1919–1929` | Task 3.2 之**同一個**確認框元件 | `npm --prefix frontend test -- --run eventBatchDeleteWarning` **≥2 條**；mutation 1 條 |

### 2.3 B6 之陷阱（TODO／SPEC 已明列，逐條抄在這裡免得漏）

1. **3.1**：不得提供「刪除全部」端點；不存在之 id ⇒ **404 非 500**；
   不連帶刪 kline 快取或 Feature Library。
   🔴 邊界②要驗的是**磁碟殘留檔數 == 0**——只驗 `GET` 回 404 偵測不到「端點回 404 但檔還在」。
2. **3.2**：🔴 **不得以 `window.confirm` 帶過**（須為可測之元件）；
   未確認 ⇒ `fetch` call count `== 0`——**用執行期計數，不要斷言按鈕有沒有 `disabled`**（§6.2）。
   🔴 B4 之教訓直接適用：**送出鍵要保持可按**，否則 `fireEvent.click` 什麼都沒觸發、測試恆綠；
   且**不要 mock 掉 api helper 後只數 `global.fetch`**（B4 R1 之 P0 就是這樣假綠的）。
3. **3.3**：於 3.2 之**同一確認框**疊加警語，不另建元件；**仍可刪**；
   邊界②＝未被引用者**不顯示**該警語（防恆顯示而失去鑑別力）。
   🔴 3.1 與 3.3 **須同批驗收**——警語之正確性依賴刪除範圍確實涵蓋該批全部產物。

---

## §2B B7 是什麼（Phase 4 全部，五個 Task；4.2 之 S-9 已於 B1 完成）

**B7 ＝ 匯出端之報酬欄與揭露 ＝ Task 4.1、4.1b、4.1c、4.2、4.3。**
依 §B 拓撲，B7 之前置為 **B1 ＋ Task 2.1b**——皆已完成。

> **一句話**：匯出檔改成可攜帶多個 `future_*` 欄供 Excel 分析；匯出端**不再**寫 `label_value`、
> **不再**有「主答案窗」（依 §D-3′ 移到 IC 分析層），並把四件使用者從未被告知的事實顯示出來。

### 2B.1 🔴 偵察結論（2026-08-26 主委實跑，**不必重查**）

| 事實 | 位置 | 對 B7 的意義 |
|---|---|---|
| 🔴 **Task 4.1 與 B5 直接相撞** | B5 把下界守衛整套綁在匯出面板之 `eventHorizonBars`（`exportAllowedUnderBound`／`withHorizonLowerBoundGuard`／`horizonOptions`／`export-gap3-horizon` select） | **4.1 要移除的正是那個「主答案窗」單選**。移除後 `window.horizon_bars` ＝ `max(1, lookahead_bars_declared[該列 tf])`＝**由深度導出**而非使用者選 ⇒「使用者選太小」這個風險消失，**B5 守衛的存在理由必須重新裁定**。🔴 **在 brief 具名請三家裁**：不得默默刪掉（那會讓 `D-002 A-004` 之解除失效），也不得留一個守不住任何東西的死碼 |
| `label_value` 現況寫在三處 | `eventExport.ts`：`:112` 寫入欄位、`:139` `n_missing_label_value`、`:140` `label_value_source`、`:141` `note` | 4.1「不得以任何形式寫入 `label_value`」⇒ 這四處要一起清；`skipped` 之 `missing_*_label_value_omitted` reason 亦然 |
| `analyze_tables` 之 horizons 預設 | `pipeline.py:282`：`horizons: Tuple[int, ...] = (1, 2, 4)` | 4.2 改由呼叫端傳入；**只改要算哪些 horizon，不改每個 horizon 之計算式** |
| 🔴 **G-2 golden 會合法改變** | `scripts/gap3_freeze_golden.py`（現行 `canonical_sha=163c4cec…`；`--check` 比 canonical_sha exact＋summary_table 逐列 abs≤1e-12） | 4.2 改列數 ⇒ golden **必然不符**。這是 **D-4 所稱之受管變更**：須以 `_write()` 重凍、**並在 commit message 說明**，且重凍**須以 §G S-9 參考實作重算**（`canonical_serialize.py`，B1 已交付）。🔴 **不得靜默重凍**；也不要以為是自己弄壞了 |
| 附帶欄之來源 | `CaseData` 之 `future_{1..12}bar_return`（`types.ts:49-60`）；registry 之 37 個 future 欄全部以 `future` 開頭 | 4.1 之多選預設**全選 1..12**；🔴 **附帶欄不得納入深度 `max`**（SPEC Task 2.1b 覆蓋風險：過度 purge 會吃掉訓練樣本）。B5 之 `referencedColumnsOf()` 只回條件引用欄，**維持該分界即可**，不要把附帶欄混進去 |
| `control_kind` 現為寫死 | `eventExport.ts` 之 `control_kind: 'user_labeled_same_trigger'` | 4.1b 第 5 段要揭露它；邊界②＝顯示值 `==` 匯出檔實際值（防寫死漂移） |
| `R-A005-1` **不觸發** | 該殘留之觸發條件＝動到 `CaseSearchEngine` 之**未來欄計算段** | B7 只**消費** future 欄、不改 producer ⇒ 不觸發。**在 brief 寫明這個判斷**，免得誤以為要一併做 |

### 2B.2 B7 五個 Task 之關鍵座標

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **4.1** 附帶欄／移除 `label_value` 與主答案窗 | `798` | `1940–1978` | `eventExport.ts`＋`search/page.tsx` | `npm --prefix frontend test -- --run eventExportHorizonColumns` **≥6 條**；**mutation 4 條**（SPEC L1973–1976） |
| **4.1b** 匯出時揭露四件事 | `833` | `1979–2005` | `search/page.tsx` 揭露區塊（文案取自契約 `_doc`） | `npm --prefix frontend test -- --run eventExportDisclosureLegacy` **≥2 條**；mutation 1 條 |
| **4.1c** 明文標示不提供 IC decay | `865` | `2006–2023` | `search/page.tsx` 說明段 | `grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md >= 1` ＋ vitest 邊界①② |
| **4.2** 報酬表完整曲線 | `886` | `2024–2036` | `pipeline.py:282`／`tables.py`（S-9 已完成） | `pytest tests/momentum/event_samples/ -q -k horizon_curve` **≥3 條**（S-9 之 **≥7 條**見 D-002 A-002）；mutation 1 條 |
| **4.3** 缺欄確認框逐 horizon | `910` | `2037–2049` | `search/page.tsx` 缺欄確認框 | `npm --prefix frontend test -- --run exportMissingColumnDialog` **≥2 條**；mutation 1 條 |

### 2B.3 B7 之陷阱

1. **4.1**：
   - 🔴 `window.horizon_bars` 與 `lookahead_bars_declared` **刻意可不相等**（深度 0 時前者為 1、後者為 0）
     ——前者有 serialization floor。邊界②就是釘這件事，**不要「順手」把它們對齊**。
   - 🔴 匯出端**不得以任何形式**寫 `label_value`（含寫 `null`／`0`／另立 `label_value_status` 新欄
     ——新欄須先改契約，D-6）。
   - 邊界①＝附帶欄選擇改變 ⇒ `lookahead_bars_declared` 與 `window.horizon_bars` **皆不變**。
   - ②之逐列斷言：`'label_value' in records[i] === false` 須**逐列**驗，非只第一列。
   - ④須**呼叫同一 exported 深度函式比對，非寫死數字**。
2. **4.1b**：四段**皆由實際設定導出，禁寫死**；深度顯示須取 `lookahead_bars_declared`，
   🔴 **不得**顯示 `window.horizon_bars`（有 floor，深度 0 會顯示成 1）；批內多 TF ⇒ **逐 tf 各一行**
   （B5 R1 群集 B 之教訓：**不得塌成單一 scalar**）。
3. **4.1c**：文案中**不得**出現「重新匯出」作為換 h 之手段（斷言該字串不出現）。
4. **4.2**：golden 重凍見 2B.1；**不得因列數變多而改變 `n_eff` 之定義**。
5. **4.3**：訊息**不得**含「主答案窗」字樣；不得因缺欄而阻擋匯出。

### 2.4 之後的批次（不在本批，僅供排序）

| 批 | Task | 依賴 |
|---|---|---|
| B8 訊息與表頭 | Phase 5 全部 | Task 5.0 |
| B9 IC 止血閘 | Phase 6 全部 | Task 6.0 |
| B10 全棧接線 | Phase 7 全部 | B1–B9 |

---

## §3 派工管線（**大任務**，不得跳步）

命中高風險 (a) 數值/資料品質 ＋ (b) 跨模組 ⇒ **大任務**。SPEC／TODO 皆已凍結、已過 adversarial
⇒ **實作階段之管線為**：

1. **實作＝Claude 主委自任**（`docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行；
   機器版 SoT＝`scripts/governance_roles.json`：`implementer=claude`、`reviewers=[codex,composer,grok]`）。
   🔴 **派工前必先重讀該行＋該 JSON**——選層是動態的。
2. **每批收尾必派 code review**：三家全員，**實作者不自審**。
3. **開門**：先跑 `bash scripts/gate.sh dispatch --task-id … --risk … --intent … --facts-asked … --review-role … --template …`
   🔴 **必須先開 token，`committee_run.sh` 本身也會被 PreToolUse 擋**。
   🔴 **`--task-id` 必須是 session 名之全大寫形式**。
4. **派工指令**（B2–B5 實測可用，逐字照抄改 session 名即可）：
   ```bash
   bash scripts/committee_run.sh --session <session> <brief> <out-prefix> codex,composer,grok \
     -- --intent "…" --risk low --facts-asked "…" --review-role "reviewer（…）" \
     --template "n/a: 用 brief" --task-id "<SESSION 大寫>"
   ```
   丟背景跑；三家平行，**約 3–8 分鐘**（B4／B5 實測）。
5. **收集**：`bash scripts/reconcile_build.sh <session> --mode review <三個 -family.md>`
   → 手填 `synth.md` 之「群集／處置」＋ `**Verdict**:` 行 →
   `bash scripts/reconcile_cluster_attribution_check.sh <synth.md>`（rc=0）→
   🔴 `bash scripts/completeness_check.sh --lock <session>/sources.lock`
   （**只給 lock 路徑，不得再帶 synth.md**）。
6. **清債**：`bash scripts/debt_clear.sh --round-id <id> --session <name> --lock <sources.lock>`。
   `round_id` 由 `committee_run.sh` 輸出；🔴 **若 `/tmp` 之 log 已被委員清掉，改用
   `bash scripts/debt_ledger.sh --list | tail -1` 取 OPEN 那一筆**（B4／B5 都遇到過）。
   🔴 **債未清會擋掉下一輪派工**。
7. **前後**：`bash scripts/agent_preflight.sh` → 派工 → `bash scripts/agent_postflight.sh`。
8. **兩輪斷路器**：任何問題自己弄 ≤2 輪仍失敗 ⇒ 立即開委員會，禁 solo 硬幹。

**B1–B5 之實績供校準**：B1 五輪 3→2→10→7→0；B2 兩輪 2→1；B3 三輪 6→3→0；
**B4 六輪 7→4→4→1→1→0**；**B5 四輪 6→3→1→0**。

### 🔴 B4／B5 學到的六件事（B6／B7 直接沿用，別重踩）

1. **「兩家零 finding」不構成放行理由，可重跑的反例才是。**
   B5 R1：composer／grok 都判「可收」，而 codex 五條 P1 主委逐條實跑**全部成立**。
2. **每輪修完都要問一次「這個修法本身有沒有違反別的條文／開新破口」。**
   B4／B5 共十輪裡有**五輪**的 finding 是上一輪修法自己引入的相鄰缺陷。
3. **同型錯會跨批重犯——靠記得沒用。**
   B5 R1 群集 B（逐 tf map 被 `Math.max` 塌成 scalar）是主委在 **B3 R2 才親手修過**的同一條禁令。
   有效的對策是**把規則寫成兩端共用的單一實作**（B4 之行尾判準）或**把禁令做成 mutation**（B5 之 `R1-M2`）。
4. **🔴 三件套 RECHECK（composer 於 B5 R2 自陳漏抓成因後自提，主委採為常設條款）**：
   安全面之複驗固定包含 ①**page runtime**（`endpoint 綠 ≠ page effect／guard 綠`）
   ②**malformed 輸入 probe**（畸形形狀／型別冒充／多餘鍵藏東西）
   ③**逐 scope 之值不得塌平**。**寫進每份 review brief**。
5. **重複守衛會使 mutation 失明。**
   兩層守衛涵蓋同一批輸入時，只拆其中一層必然錄到**空紅集合**。
   解法：拆主層與兩層一起拆各一條，**兩者紅集合之差就是後備層的作用範圍**（B4 之 `1.2-M5`／`1.2-M6`）。
6. **「宣稱大於實作」是本 epic 最常見的自傷。**
   B4 A-016c 宣稱「一律 fail-closed」而當時只涵蓋一種；B5 註解宣稱「四個顯示點共用」而只有兩個。
   ⇒ **寫下宣稱前先數一遍實際 caller**。

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
＋ `docs/ROADMAP.md` ＋ `HANDOFF.md` ＋ commit ＋ **背景 push**。

### 4.1 怎麼寫 mutation runner（已隔離，可平行）

**現成範本（直接複製改）**：`handoffs/gap3ux_b5_mutations.py`（19 條，最新；含 **page runtime
selector** 之寫法，B6 之刪除確認框與 B7 之匯出面板都會用到）＋ `gap3ux_b5_expected.json`
（每條都有 `_<id>_why`）。另有 `gap3ux_b4_mutations.py`（15 條，含 vitest selector 與後端 CSV 變異）。

- **工作流**：先 `--record` 跑一次取得實際紅集合 → **逐條人工對證語意** → 寫進
  `<epic>_expected.json`（含 `_<id>_why`）→ 不帶 `--record` 跑正式 receipt。
- 官方單條 CLI：`bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>`。
- 🔴 `<檔>` 須為 **repo 相對路徑且不含 `..`**。
- 🔴 **parametrize 的 test id 不得含空白**（pytest node id 以空白切）。
- ⚠️ `handoffs/*.py` 與 `handoffs/*.json` 由 `.git/info/exclude` 排除 ⇒ **runner 不入版控**；
  入版控的只有 `scripts/mutation_worktree.py`、官方 CLI、與 `handoffs/run_receipts/*.json`。

### 4.2 🔴 mutation 抓假綠之實例（B2–B5 實際發生，B6／B7 照著防）

1. **比對對象錯層**：用**原始列**比對而非正規化後之列。
2. **golden 生成順序**：斷言寫在寫檔**前** ⇒ 後端被改壞時前端假綠。
3. **測到 fixture 而非生產接線**：autouse fixture 已 monkeypatch 掉單例。
4. **fixture 使被測輸入恆為空**：引用欄永遠是空集合 ⇒ 變異算出同值。
5. **response_model 靜默濾欄**：後端加鍵但 pydantic 沒宣告 ⇒ 前端永遠看不到。
6. **（B4）錨點放在無測試涵蓋之處**：`A004-M1` 原本錨在 page 的 `catch`，那段沒有任何測試 ⇒ 空紅集合。
   修法＝**把決策抽成純函式**，決策本體才測得到。
7. **（B4）斷言分不出兩個時間**：「勾選當下 vs 送出當下」在測試裡只差幾毫秒 ⇒ 用**假時鐘**拉開。
8. **（B4／B5）重複守衛**：兩層涵蓋同一批輸入 ⇒ 只拆一層錄到空紅集合（見 §3 之第 5 條）。
9. **（B5）fixture 沒有覆蓋該邊界**：R2 之 page fixture 兩列皆有 label ⇒ 沒抓到「缺標記列」之口徑差。

**共同形狀＝「錄到空紅集合」就是假綠的信號**。`--record` 出現 `紅=[]` 一律先查根因。
🔴 **另一個訊號＝runner 之字面錨點 fail-loud**（`mutation 錨點找不到`）：那是你改了碼卻沒同步
mutation，**要重錨、不是繞過**（B4／B5 各發生一次）。

---

## §5 未辦事項（開工前／收 epic 前要處理）

| # | 事項 | 何時 | 狀態 |
|---|---|---|---|
| 1 | **延伸檔 D-003 之戳記輪**（A-016..A-019 四條修訂，含 SPEC L1427 digest 語意之 doc drift 裁定） | 收 epic 前 | ⬜ **未過戳記**；不擋 B6／B7，但收 epic 前須補（比照 D-002 之作法） |
| 2 | 動過 `scripts/` ⇒ 收 epic 前跑 `bash scripts/gov_check.sh --no-probe`（丟背景，十分鐘級） | 收 epic 前 | ✅ 2026-08-25 已跑；**B2–B5 皆未動 `scripts/`**。若 B6／B7 動了需重跑 |
| 3 | **GAP-3 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`） | 使用者 | ⬜ **未簽字不收案** |
| 4 | 根目錄 `.probe_ic{,2,3}.sh` 三個 untracked 檔為更早批次殘留 | 隨時 | ⬜ 要清可直接刪 |
| 5 | `handoffs/run_receipts/gap3ux-b{3,4,5}-record*.json` 為 `--record` 之暫存 receipt | 隨時 | ⬜ untracked，可刪 |

---

## §6 地雷（本 epic 專屬，逐條是實際踩過的）

### 6.1 🔴 「比對範圍過寬／失真」——主委在本 epic 犯了**七次**，形狀完全相同

| # | 形態 | 後果 |
|---|---|---|
| 1 | Phase Gate 之測試層標籤與 Task 欄位**同字面** | 機械閘分不出來 |
| 2 | 以**行號**注入修補，行號取自修補**前**之掃描輸出 | 三處落到**錯的 Task** |
| 3 | 判斷 Task 有無 mutation 時掃**整個區塊** | 被區塊尾端別人的字樣騙過 |
| 4 | 同步斷言只驗**子字串存在**，散文卻宣稱「逐字相等」 | **假綠**，改參數名照樣過 |
| 5 | 驗 gitignore 時問**目錄** | 隔離副本缺 fixture、全紅 |
| 6 | 驗「兩件事不共用序列化路徑」時掃**整段原始碼文字** | 自己 docstring 裡的字樣讓斷言誤紅 |
| 7 | parametrize label 含空白 ⇒ node id 被截斷 | 「逐一相等」比的是**半截字串** |

🔴 **對策**：①錨點落在**真正要判斷的那個東西**上 ②**一律字面錨點，禁行號**
③檢查寫完要用**已知會紅的輸入**試一次，只看綠不算驗過。

### 6.2 🔴 **不要用原始碼形狀證明執行期性質**（B1→B2→B3→B4→B5，同一病五度出現）

- **B1 R3**：改設計讓它變成結構保證（整段匯出包進 `withHorizonLowerBoundGuard(…, {proceed})`）。
- **B2 R1／R2**：AST oracle 被 assignment／subclass／factory-return 逐一繞過 ⇒ 改**執行期**錨點。
- **B3**：monkeypatch 計數 `== 0` ＋ **同時斷言表產得出來**（只斷言「沒呼叫」的話，raise 在最前面也綠）。
- **B4**：送出鍵**刻意保持可按**——設成 `disabled` 的話 `fireEvent.click` 什麼都沒觸發、測試恆綠。
- **B5**：`endpoint 綠 ≠ page effect／guard 綠` ⇒ 必須 render page、真的按鈕。

### 6.3 產出端閘會擋你，而且多半擋對了

- `doc_format_precheck.sh`：驗證欄須**逐行**含可證偽 token（`pytest`／`==`／數字／`.py`…）。
- commit message：`VERIFY:<path>` **冒號後不能有空格**，且該檔須含 `CLOSED`／`APPROVED` 等閉合判詞。
- 🔴 **`Governance-Scope: out-of-epic <理由>` trailer**：staged 含 epic scope 外路徑時**必加**，
  且**必須在 commit 訊息之最後一段**。B1–B5 之全部 commit 都加了，可直接複製措辭。
- 🔴 **api 層不得複列契約 reason 字面**（`tests/api/test_gap3_import.py` 之機械閘會擋）
  ——**連 docstring 裡出現都算**（B4 實際踩到：`missing_required_field` 寫在註解裡就紅）。
- 🔴 **`factkey_write_guard.sh`（PostToolUse）會擋「識別碼緊接狀態」之句型**：
  在 `HANDOFF.md` 寫「B5 已落地」會 fail-closed。改寫成不含批次代號的句子即過。
- 計數字面稽核：說明文字裡的「一支」「一筆」也會被當計數字面 ⇒ 改措辭。
- 🔴 **改過 `白話說明/*.md` 必須跑 `bash scripts/plain_docs_render.sh` 並把 `docs/site/` 一起 staged**。
- 🔴 **R3 解耦閘掛在 `PostToolUse`**：api 層直接 `from momentum.Analysis...import` 會**當場被擋**。
- **artifact gate**：新增 `docs/*{SPEC,TODO,PLAN}*.md`（含延伸檔 `*.D-00N.md`）須先跑
  `bash scripts/gate.sh artifact --file … --template-opened … --sections …`。

### 6.4 工具與環境

- **本機 bash 3.2.57** ⇒ **無 `declare -A`**；`sed` 為 BSD ⇒ 一律用 `sed -E`。
- 🔴 **絕不寫 `cd <專案路徑>` 前綴**；前端指令一律 `npm --prefix frontend …`。
- 🔴 **改檔一律用 Edit／Write 工具**，不要用 Bash 包 `python3 - <<'PY'` 做字串取代
  （會觸發權限分類器，且找不到目標時**靜默無動作**）。
- `pytest tests/api tests/momentum/event_samples` 全量約 **6 分鐘** ⇒ 丟背景。
- mutation receipt（19 條含 vitest）約 **3–10 分鐘** ⇒ 丟背景。
- 委員會清 `/tmp` ⇒ 自己導到 `/tmp/x.log` 的檔**可能被刪**；重要輸出看 harness task output 檔。
- 跑完測試須 `bash scripts/restore_golden_inventory.sh`。
- `handoffs/` **未入版控**（勿清）。

### 6.5 🔴 治理現況（**皆既有債，不要以為是自己弄的**）

`pytest tests/api tests/momentum/event_samples` 之 **3 條長期紅**：
`test_batch_alias.py::test_patch_batch_alias_deleting_returns_409`、
`test_progress_rss_fields.py::test_parity_batch_rest_worker_rss_and_schema_version`、
`test_progress_rss_fields.py::test_parity_concurrent_gt_one_no_fake_stage`。
（B4／B5 全程每次全量跑皆**逐字相同**這三條。）
另 `gov_check.sh` 段 4 之 G-7 scope 淨差長期 FAIL、`pytest tests/governance` 6 條長期紅
——皆已登記為 `R-GOV7-1`／`R-GOV7-2`，三值理由 `user-ruling`，**不排工**。

---

## §7 🔴 不要碰的東西

### 7.1 治理（使用者 2026-08-24 定死）

逐字：「當初就是發現你做治理是無解才不做」「你這樣岔題去問委員，永遠沒完沒了」。
⇒ **遇治理工具壞掉：繞過並具名記錄，不修、不開票。要動須使用者明示。**
⇒ **治理／工具問題不得寫進派工單**，那是迴圈的燃料。

### 7.2 已具名封存之殘留（**不排工、不另立票**）

- **SPEC 末節 F-1..F-4**、**TODO（R3 reconcile）四條**——全文見 SPEC／TODO 末節。

### 7.3 具名殘留全文（**本節為全文；`HANDOFF.md` 只指回這裡**）

| 代號 | 內容 | 三值理由 | owner／觸發 |
|---|---|---|---|
| `R-GOV7-1` | G-7 scope 淨差長期紅（383 條）。判準要求 trailer 落在**該 commit 自身** ⇒ 前向修不掉 | `user-ruling` | 主委 |
| `R-GOV7-2` | 治理 pytest 6 條長期紅 | `user-ruling` | 主委 |
| `R-B1-1` | 全量跑之測試順序污染（`test_feature_export`／`test_run_lifecycle_api` 之 error 時有時無）。歸因**未實跑證明** | `needs-research` | 主委 |
| `R-A005-1` | `lookahead_registry` 之 `_PRODUCER_SEMANTICS` 表為人工稽核非執跑探針 | `needs-research` | 主委；**觸發＝下次動到 `CaseSearchEngine` 未來欄計算段時一併做。🔴 B7 不觸發**（只消費、不改 producer） |
| `R-B2-2` | 執行期 oracle 之 factory-body 繞法：新斷言綁 `get_event_import_service()` 之回傳；若日後另立第二個工廠且 route 改呼叫它，本閘看不見 | `needs-research` | 主委；屬 **B10 全棧接線** |
| **純 JS 手刻 sha256** | 不經 `crypto.subtle`／`node:crypto` 入口之手刻實作，前端封閉枚舉看不見 | `needs-research` | 主委 |
| **`R-B3-3`** | 逐 symbol 之 purge 下界（`EventSplitConfig.embargo_ms_by_symbol`）未實作 ⇒ 各 symbol 宣告下界**不一致**之批次一律拒絕分析（fail-closed，不取全批 max——SPEC §D-3′-a(ii) 明令禁止）。使用者當前解法＝依 timeframe 拆批 | `blocked-by` Task 7.0b | 主委；7.0b 落地時解除 |
| **`R-B4-1`** | **CSV 方言之殘餘前後端差異**：支援之行尾＝**LF／CRLF**；引號內 CR 當資料保留；裸 CR（含舊式 Mac）兩端一致不支援。其他方言／編碼／writer 癖好之殘餘差異**不再逐一開輪**。兜底＝後端永遠是契約權威；前端只做預覽且**不得產出看似合理的假欄名**（由 mutation `1.5-M5` 鎖住）。R6 由 codex 以 **9,331 個字串窮舉**比對兩端 predicate，`mismatch_count=0` | `user-ruling` | 主委；**觸發＝出現具體且可重跑之使用者實例才重開** |
| **`D-001/D-002/D-003` provenance** | `gate.sh register-output` 只收 `handoffs/` 或 `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報 provenance pending（**非戳記造假**） | `user-ruling` | 主委 |

**已解除（不要再當殘留看）**：`R-B2-1`（B4）／`D-002 A-004`、`R-B3-1`、`R-B3-2`（B5）。

---

## §8 檔案地圖（B6／B7 會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組 | `momentum/Analysis/event_samples/`：`pipeline.py`／`tables.py`／`event_split.py`／`lookahead_registry.py`／`lookahead_depth.py`／`lookahead_gate.py`／`lookahead_declaration.py`／`import_contract.py`／`canonical_serialize.py`／`condition_engine.py` |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`、`future_column_lookahead.json`、`condition_engine.json` |
| case 端點 | `api/routes/case.py`：`import_events_file`／`import_events_json`／`import_events_csv`／`lookahead_declaration_preview`／`lookahead_depth`／`list_event_imports`／`get_event_import`（**3.1 之鄰居**）／`analyze_event_import` |
| 匯入服務 | `api/services/case_import_service.py::EventImportService`：`parse_upload`／`file_columns`／`csv_records_from_mapping`／`import_records`（落檔唯一點）／`list_imports`／`get_import`／`analyze` |
| 前端（B6） | `frontend/src/app/data-preparation/page.tsx`（批列表 `event-imports-list`）／`lib/api.ts::listEventImports` |
| 前端（B7） | `frontend/src/app/search/page.tsx`（匯出面板；`export-gap3-horizon`／`export-gap3-events`／篩選面板）／`lib/eventExport.ts`（`label_value` 與 `horizon_bars` 之落點）／`lib/exportFilter.ts`／`lib/exportCounts.ts` |
| API 模型 | `api/models/event_import_models.py`（🔴 加 response 鍵必須同步改這裡，否則被 `response_model` 靜默濾掉） |
| golden | `scripts/gap3_freeze_golden.py`（🔴 B7 之 4.2 會讓它合法改變，須 `_write()` 重凍並在 commit message 說明） |
| mutation receipt | `handoffs/run_receipts/gap3ux-b{1,2,3,4,5}-all-mutations.receipt.json`（32／14／13／15／19 條） |
| mutation runner 範本（**未入版控**） | `handoffs/gap3ux_b5_mutations.py` ＋ `gap3ux_b5_expected.json`（最新，含 page runtime selector）；`gap3ux_b4_mutations.py` |
| reconcile 收斂檔 | `handoffs/reconcile/20260825-gap3ux-b4-review-r{1,2}/`、`20260826-gap3ux-b4-review-r{3,4,5,6}/`、`20260826-gap3ux-b5-review-r{1,2,3,4}/synth.md` |
| 過程與教訓（給使用者） | `白話說明/GAP-3施工看板.md`（進度）、`白話說明/GAP-3施工進度.md`（歷史）、`白話說明/流程摩擦記錄.md` |
