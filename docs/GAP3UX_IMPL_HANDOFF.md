# GAP-3 事件型 UAT 缺口修補 — **實作交接**（更新於 2026-08-26，B7 收斂態）

> **給下一個 session 的完整交接。** `HANDOFF.md` 只放指標，細節全在本檔。
> 讀完本檔即可開工，不必回頭問。

---

## §0 一句話狀態

**SPEC 🔒 凍結、TODO 🔒 凍結 v1.0；第一批到第九批皆已結案；`D-004` 三家 APPROVED。下一批＝B10（Phase 7 全棧接線，**9 個 Task**）。**

🔴 **接手第一件事：照 §1 跑開工前稽核**（期望值已更新為第九批結案後之實測值），再讀 §2E（B10 是什麼）。

🔴 **B8 新增兩條鐵律，開工前先讀（§3 之第 9、10 條）**：
① **派 review 前先 commit**；② **mutation runner 必須同時有 `IsolatedWorktree` 與備份閘**。
兩者都是 B8 付了代價才知道的：B8 四輪 review 全程未 commit，加上 runner 缺隔離，
導致一個檔的實作在委員並行複驗期間回到 HEAD、整段消失。

| 文件 | 路徑 | 狀態 | commit |
|---|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 🔒 FROZEN，3,547 行／42 Task | `4ce3d6d9` |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 🔒 FROZEN v1.0，1,618 行／42 Task | `afa70967` |
| TODO 延伸檔 D-001（**須並讀**） | `docs/GAP3_EVENT_UX_TODO.D-001.md` | ✅ 三家 APPROVED | `81cbe7ab` |
| TODO 延伸檔 D-002（**須並讀**，A-002..A-015） | `docs/GAP3_EVENT_UX_TODO.D-002.md` | ✅ 三家 APPROVED | `51f1a65e` |
| TODO 延伸檔 D-003（**須並讀**，A-016..A-019） | `docs/GAP3_EVENT_UX_TODO.D-003.md` | ⬜ **尚未過戳記輪**（見 §5） | `09884811` |
| TODO 延伸檔 D-004（**須並讀**，A-020..A-022） | `docs/GAP3_EVENT_UX_TODO.D-004.md` | ✅ 三家 APPROVED（戳記歷三輪，見 §2B.0） | 本批 |
| 施工看板（給使用者看） | `白話說明/GAP-3施工看板.md` | 24 ✅／0 🔧／18 ⬜ | 每批收尾更新 |

🔴 **層級**：**操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）；
讀 TODO 必須並讀 D-001／D-002／D-003／D-004**（凍結後修訂只走延伸檔，不就地改 TODO）。
🔴 **驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**；TODO 只給可執行命令＋條目下限＋SPEC 行號。
**不得把 SPEC 斷言字面抄成第二份副本**——本 epic 之自傷絕大多數出自副本漂移。

### 各批已交付什麼（可直接用）

| Task | 產出 | 可直接 import 的東西 |
|---|---|---|
| 1.1 | typed namespace-aware `receipt_schema` | `import_contract.py`：`flatten_receipt_schema()`／`receipt_type_ok()`（含 `Mapping[str,str]`）／`validate_receipt_namespace()`／`capability_unavailable_reason()` |
| 1.10 | `contracts/future_column_lookahead.json`（**37 個 future 欄，全部以 `future` 開頭**） | `lookahead_registry.py`：`load_lookahead_registry()`／`resolve_lookahead_bars()`／`registry_resolvable_columns()`／`requires_declaration()`／`unregistered_future_columns()` |
| 2.1b | **唯一** exported 深度函式 | `lookahead_depth.py::depth_by_timeframe()`；前端守衛已於 B7 改名為 `lookaheadDepthLock.ts::withExportLowerBoundGuard()` |
| 4.2（僅 §G S-9） | canonical bytes 參考實作 | `canonical_serialize.py`：`canonical_event_table_bytes()`／`canonical_event_table_sha256()`／`canonical_source_bytes()` |
| 1.2／1.3／1.4／1.8 | CSV 對映端點、`event_id` 之 D-2 唯一定義、t0 單位偵測、異質列拒收 | `case.py::import_events_csv`；`EventImportService.csv_records_from_mapping()`／`file_columns()`；`import_contract.canonical_event_id()`／`detect_t0_unit_ms()` |
| 1.11／1.12／1.9 | L2 強制宣告、L3 閘與 event-study-only executor、答案窗宣告 | `lookahead_gate.py`／`lookahead_declaration.py`；前端 `lookaheadDeclaration.ts`＋`LookaheadDeclarationFields.tsx` |
| **1.5／1.6／1.7**（B4） | CSV 對映 UI、對映 provenance、可疑欄警示 | `EventCsvMappingForm.tsx`；`csvPreview.ts`（`parseCsvText`／`countDeclaredLabels`）／`suspiciousBinaryColumns.ts`／`eventIdNormalization.ts`；契約新增 `receipt_schema.mapping_provenance`（七欄） |
| **2.1／2.2／2.3**（B5） | 匯出前篩選、條件寫入 `filters`、即時筆數 | `exportFilter.ts`（`applyExportFilters`／`buildExportFilterSpec`／`nextLowerBoundState`／`computeExportCounts`）；契約新增 `label_definition.fields.filters.wire_shape`。🔴 `exportAllowedUnderBound`／`horizonOptions` 已於 B7 刪除，改為 `exportAllowedByLowerBoundState`／`depthMapCoversTimeframes` |
| **3.1／3.2／3.3**（B6） | 事件批次刪除 | `case_import_service.py::batch_paths()`／`payload_path()`；`EventBatchDeleteDialog.tsx`；`eventBatchReferences.ts` |
| **4.1／4.1b／4.1c／4.2／4.3**（B7） | 匯出端報酬欄與揭露 | `eventExport.ts`（`ATTACHED_HORIZONS`／`windowHorizonBarsFor`／`EVENT_EXPORT_SCENARIO`／`EVENT_EXPORT_CONTROL_KIND`）／`exportFilter.ts::depthMapCoversTimeframes`／`lookaheadDepthLock.ts::withExportLowerBoundGuard`／`eventContractDocs.ts`（**契約 doc 鏡像＋逐字比對測試之範本**）／`EventTablesPanel.tsx::sanitizeHorizons`；`import_contract.py::_is_finite_num`＋`_ALWAYS_HOMOGENEOUS_DIMENSIONS` |

### `EventSamplePipeline` 之 R3 出口清單（api 層只能經這些取用 momentum）

`import_contract()`／`canonical_event_id()`／`event_id_template()`／`mapping_failure_reasons()`／
`normalize_t0_units()`／`canonical_source_payload()`／`condition_engine_contract()`／
`bars_from_kline_cache()`／`validate()`／`run()`／`run_with_params()`／`analyze_tables()`／
`requires_lookahead_declaration()`／`lookahead_declaration_defaults()`／`resolve_lookahead_declaration()`／
`apply_lookahead_horizon_projection()`／`lookahead_split_blocked()`／`split_blocked_capability_reason()`／
`run_event_study_only_with_params()`／**B4 新增** `validate_receipt_values()`／**B5 新增** `lookahead_depth()`
（見 `momentum/Analysis/event_samples/pipeline.py` 之 `@staticmethod` 區）。
🔴 **若要讓 api 層用到其他 momentum 內部函式，必須在此加出口**——直接
`from momentum...import` 會被 `scripts/check_decoupling_imports.py`（R3）在 PostToolUse 當場擋掉。
🔴 **出口一律回純資料**（dict／bool／str），例外型別不跨界。

---

## §1 開工前稽核（逐條跑，全部要對；不對先修再開工）

```bash
bash scripts/debt_ledger.sh --has-open          # 期望 rc=0（無未清委員會債）
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md        # 期望 rc=0
bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-003.md  # 期望 rc=0
grep -c '^### Task ' docs/GAP3_EVENT_UX_TODO.md # 期望 42
venv/bin/python scripts/gap3_freeze_golden.py --check   # 期望 rc=0，canonical_sha=163c4cec…（約 15 秒）
venv/bin/python -m pytest tests/momentum/event_samples/ -q            # 期望 332 passed（🔴 B10 之 7.0b 起；含 -k analysis_label_producer 19）
venv/bin/python -m pytest tests/api -q -k "gap3_csv or gap3_export_filter or lookahead_declaration or gap3_horizon or gap3_import or gap3_t0_unit or gap3_heterogeneous or gap3_source_digest or gap3_contract_reason or gap3_lookahead or gap3_event_delete or source_json_hint"   # 期望 189 passed（🔴 B8 起 -k 多了 source_json_hint）
venv/bin/python -m pytest tests/api -q -k "feature_coverage_gate or event_analysis_horizon_purge"   # 期望 44 passed（🔴 B10 之 7.0b／7.7 新增，21＋23）
venv/bin/python -m pytest tests/api -q -k "gap3_matrix or ic_feature_cap or ic_stop_gate_alive or ic_progress_fields"   # 期望 39 passed（🔴 B9 之止血閘＋雙向形狀矩陣）
npm --prefix frontend test -- --run             # 期望 61 files／351 passed（🔴 B10 之 7.0／7.0b／7.7 收案後之實測）
npm --prefix frontend run build                 # 期望 rc=0
npx --prefix frontend tsc --noEmit -p frontend/tsconfig.json   # 期望：GAP-3 相關檔 0 錯（另有 **8 行**既有債，見 §7.3）
```

🔴 **golden 一律用 `venv/bin/python`**——系統 `python3` 缺 `numba`，codex 於 B7 R1 踩過。
🔴 **`npm run build` 不涵蓋測試檔**（B7 R2 `CODEX-R2-P2-03`）⇒ 型別關卡要靠上列最後一條。

B1–B8 之 mutation receipt 為 `handoffs/run_receipts/gap3ux-b{1..8}-all-mutations.receipt.json`
（32／14／13／15／19／23／22／**19** 條），皆 `closure: CLOSED`。**不需重跑**，除非你改了那幾批的產出。
🔴 **跑之前先查 `grep -o '"closure": "[A-Z]*"' <receipt>`**——委員複驗會覆寫它（見 §6.4）。
🔴 **B8 起 runner 會在開跑前先 `unlink` 目標 receipt**：中止就沒有檔、下游 `jq` 必定 fail-loud，
不再可能讀到上一輪的舊 receipt（B8 主委差點就這樣宣稱通過，見 §6.4）。

🔴 **上表之 golden 期望值 `163c4cec…` 不因 B7 改變**——原交接宣稱「4.2 會讓它合法改變」已於
2026-08-26 實測推翻，定案見 `D-004` 之 A-022（**不重凍**；同型誤植在本檔曾有兩處，皆已更正）。

---

## §2 B6 是什麼（Phase 3 全部，三個 Task）—— 🔴 **已收斂（2026-08-26，commit `b2055ac8`），本節保留供追溯**

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

## §2B.0 🔴 B7 之收斂結果（2026-08-26；**Phase 4 已完成，本節保留供追溯**）

**Task 4.1／4.1b／4.1c／4.2／4.3 皆 ✅。** `D-004`（A-020／A-021／A-022）三家 APPROVED 後才動契約。

### 收斂軌跡

| 輪 | findings | 誰抓到 |
|---|---|---|
| `D-004` 戳記 R1 | codex REJECTED（另兩家 APPROVED）——**且他是對的** | `RULING-3(c)` 實為 2 vs 1，主委誤採少數版並標「三家一致」 |
| `D-004` 戳記 R2 | codex REJECTED（另兩家 APPROVED）——**又是對的** | A-020 漏記**三家一致**之三項限制；🔴 該輪另兩家標「一致」時**也沒回讀自己的 consult 原文** |
| `D-004` 戳記 R3 | 三家 APPROVED（sha `12a8fc74…`／`befd04f7…`） | — |
| code review R1 | **7** 條 → 4 群集 | 三家（群集 A 為**三家一致**） |
| code review R2 | **3** 條 → 2 群集 | 只有 codex（另兩家零 finding 判可收） |
| code review R3 | **0** 條 | 三家一致可收，皆附實跑證據 |

### 🔴 本批之五次自傷（全部由委員實跑抓出，逐條記在收斂檔）

1. **D-004 R1**：未逐家交叉核對即宣稱「三家一致」，採了少數且較弱的版本。
2. **D-004 R2**：三家一致講過的三項限制在摘要時整條掉了，卻仍標「三家一致」。
3. **review R1（三家同時抓到）**：主委在 brief 宣稱「深度拿不到就擋」，
   實作只擋了「有條件」那一半 ⇒ 無條件批次在 API in-flight 期間可匯出空宣告之檔。
4. **review R2 群集 E**：**R1 修法自身開的破口**，且**正是主委寫進 brief 請委員攻、卻沒先自己打過的嫌疑點**。
   ⇒ 已入 `HANDOFF.md` 鐵律：**列出嫌疑點 ≠ 驗過嫌疑點**。
5. **收尾**：`verify_pretooluse.sh` 擋下一次指向 `closure: OPEN` receipt 卻宣稱全通過的寫入
   （根因＝委員複驗覆寫 repo 內 receipt，見 §6.4）。

### 落地內容（判準字面全文在 `D-004` 之 A-020／A-021，本節不複述）

- **契約**：`lookahead_bars_declared` 移出 `derived_fields` 入 `optional_fields`
  （doc 含「對齊後複製至 `receipt_schema.batch`」）；`receipt_schema.batch` 同名鍵**保留**（第三處）；
  `future_{1..12}bar_return` 逐欄列舉（doc 含「不進 `ic_feed`」）。
- **validator**：`Mapping[str,int>=0]` 型別（共用 `receipt_type_ok`）＋**批內一致性**
  （值一致＋**全有全無**，後者由 R2 補上）；附帶欄用 `_is_finite_num`（**拒 NaN／±Inf**）。
- **前端**：附帶欄多選（預設全選）／移除主答案窗與 `label_value`／逐列 `window.horizon_bars`／
  四段揭露逐 tf 一行／缺欄確認框逐 horizon／`EventTablesPanel` 真的送 `{horizons}`。
- **守衛改形**：`withExportLowerBoundGuard(state, {notify, proceed})`——保留 `proceed` 結構保證、
  職責改 readiness fail-closed；`exportAllowedByLowerBoundState` 刪 scalar 比較；
  `inexpressible` 改為可匯出；刪 `horizonOptions`。深度回傳以 `depthMapCoversTimeframes()` 驗覆蓋性，
  不通過即 `error`；`windowHorizonBarsFor` 缺鍵**拋錯**（不再 floor 成 1 冒充深度 0）。

### 🔴 一條被推翻的 D-004 字面（實跑證據在 `R2-M3`／`A021-M3`）

`D-004 A-021` 寫「拆包裹 ⇒ 驗收⑤須仍能抓到」。**實跑推翻**：真的把 page 之 `proceed` 包裹
拆成裸 `if (…) return;` 後，**⑤維持綠**，轉紅的是 AST 側之 `lookaheadDepthLock.page.test.ts` ①②③。
原因是執行期計數**在原理上**分不出「包在 `proceed` 裡」與「正確寫的裸 `if…return`」——兩者行為相同。
⇒ 正確分工＝**③擋形狀退化、⑤擋行為退化**（守衛被搬到 `await` 之後），缺一不可。三家 R3 皆接受此結論。

---

## §2B B7 是什麼（Phase 4 全部）—— 🔴 **已收斂，本節保留供追溯**

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
| ~~G-2 golden 會合法改變~~ 🔴 **本列原為錯誤宣稱，2026-08-26 實測推翻** | `scripts/gap3_freeze_golden.py` 之 `_run` 來自 `scripts/gap2_freeze_golden.py`，跑的是 `tests.momentum.helpers.ichc_run.run_analyze`（**IC 分析**管線，`ic_gatekeeper` case） | 它**不呼叫** `analyze_tables`／`event_forward_return_table`，而 4.2 動的正是後者 ⇒ **4.2 不會讓 golden 改變**。實測：加完 4 條 `-k horizon_curve` 後 `--check` rc=0、`canonical_sha=163c4cec…` **未變**；三家 consult 一致複驗成立。🔴 **不重凍、commit message 不得寫「已重凍」**。定案見 `docs/GAP3_EVENT_UX_TODO.D-004.md` 之 **A-022**（SPEC Task 4.2 之該句亦判為誤植） |
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

### 2.4 之後的批次

| 批 | Task | 依賴 | 狀態 |
|---|---|---|---|
| **B8 訊息與表頭** | Phase 5 全部（5.0／5.1／5.2／5.3） | Task 5.0 | ✅ **已收斂**（`ebd77b87`；五輪 5→1→4→2→0） |
| **B9 IC 止血閘** | Phase 6 全部（6.0／6.1／6.2／6.3／6.4） | Task 6.0 | ✅ **已結案**（`01870c1a`→`fbf2f643`；五輪 10→3→4→5→3＋兩輪 consult；mutation 29 條 CLOSED） |
| **B10 全棧接線** | Phase 7 全部（7.0／7.0b／7.1／7.2／7.3／7.4／7.5／7.6／7.7） | B1–B9 | ⬜ **下一批，見 §2E** |

---

## §2C B8 是什麼（Phase 5 全部，四個 Task）—— 🔴 **已收斂（2026-08-27，commit `ebd77b87`），本節保留供追溯**

### 2C.0 B8 之收斂結果

**Task 5.0／5.1／5.2／5.3 皆 ✅。** 五輪 code review：**5 → 1 → 4 → 2 → 0**（三家全員）。
mutation **19 條**全 PASS、`closure: CLOSED`（隔離環境下重跑）。

🔴 **本批之九條自傷，全部同一種病：glossary 的 definition 在重述公式，而我是讀碼推論寫出來的。**
`n_eff`（micro 區其實等權、恆等於 n）／`prevalence_full`（分母是 n_labeled 不是 n_total）／
`n_eligible`＋`n_unknown`（漏 warmup 與 grid 連續、且「重複」永遠不會出現在 n_unknown）／
`horizon`（自**進場**根起算，非事件錨定根）／`macro_mean`（是保留集 × uniqueness 加權）／
`n_test`（三者交集；**前後改了三次**）。
⇒ 修法不只改字：每條被指出的定義都補上**把它釘在真實算式上**的測試，算式一改先紅。

🔴 **三家對病根的修正（我原本只講對一半）**：codex／composer 皆指出「定義重述公式」只是一半，
另一半是**審查方法本身沒跑不對稱反例探針**——R3 那輪 codex／grok 判可收，正是因為只對
`formula_ref` 路徑讀碼。⇒ 定案＝**收窄定義 ＋ 保留算式綁定 ＋ 審查必跑不對稱探針**，三者缺一。

🔴 **另有一次工作區事故**：`import_contract.py` 之未 commit 實作整段回到 HEAD
（由 composer 複驗時發現）。**機制未判定**——可觀察事實只有「內容回到 HEAD」；
主委初判「執行端違約 `git checkout`」已**撤回**（過度宣稱），grok 提出至少同樣合理的機制＝
**B8 runner 缺 `IsolatedWorktree`、三家在共用樹並行跑 mutation**，那是主委自己的缺陷。
兩條 assumed（災損只有一檔／重打逐字相同）三家**明標無法 post-hoc 證明**，列具名殘留。

### 2C.1 原始偵察與座標（保留供追溯）

**B8 ＝ 錯誤訊息與表頭說明。** 依 §B 拓撲，**內部依賴＝ Task 5.0 必須先做**（5.2 讀它）。

> **一句話**：讓使用者看得懂表頭在講什麼、把誤傳檔案的訊息直接給正解、
> 匯出前主動說清楚每個附帶 horizon 有幾筆算得出來。

### 2C.1 🔴 偵察結論（2026-08-26 主委實跑，**不必重查**）

| 事實 | 位置 | 對 B8 的意義 |
|---|---|---|
| **glossary 檔不存在** | `momentum/Analysis/contracts/` 現有六檔：`condition_engine_contract`／`event_import_contract`／`future_column_lookahead`／`ic_report_contract`／`ic_survivor_contract`／`strategy_validation_contract` | 5.0 是**新建** `event_metrics_glossary.json`，不是改既有檔 |
| **表頭字面現況** | `EventTablesPanel.tsx:67-68` 之 `macro mean`／`micro mean`；`:46` 之 `HorizonRow` 型別＝`{mean, median, win_rate, n, n_effective, ci}`；`:57` 註解記載後端鍵形狀 | 5.2 之 tooltip 掛在**這些 `<th>`**；glossary 的鍵要對得上這裡實際用到的指標 |
| **SPEC 要求的八鍵** | `macro_mean`／`micro_mean`／`n_eff`／`lift_threshold`／`prevalence_full`／`prevalence_learn`／`signal_frequency`／`tail_excluded` | 後四鍵來自 `all_bars_evaluation` 那張表（同檔 `overall`／`counts` 區），**不要只做報酬表那張** |
| **訊息組裝唯一點** | `api/routes/case.py::_rejected()`（`:134`；TODO 定案為 `:132`，B4–B7 改動後位移兩行——**用字面錨點，別用行號**） | 5.1 就改這裡；它同時服務 JSON 與 CSV 兩條路徑 ⇒ SPEC「須同步」那條（CSV 端點也要給同一則正解）自動滿足，但**要在測試裡釘住** |
| 🔴 **5.3 與已完成的 4.3 是同一個訊息區塊** | `search/page.tsx` 之 `missingRows` 段（B7 落地） | 5.3 ＝**擴寫**該訊息：現在只列「缺幾筆」，5.3 要改成「N/M 筆可算、K 筆因尾端不足而缺」。**不得另建第二個確認框** |
| 前端測試檔名 selector | `eventTableTooltips`（5.2）／`exportHorizonCoverageDialog`（5.3） | 🔴 vitest selector 靠**檔名**匹配，兩個都要新建 |

### 2C.2 B8 四個 Task 之關鍵座標（詳細內容一律回讀 TODO 該 Task 全文）

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **5.0** glossary SoT | `941` | `2052–2067` | 新增 `momentum/Analysis/contracts/event_metrics_glossary.json` | SPEC L2059 之 `python3 -c` 一行 rc=0（八鍵 `>=`）；mutation 1 條 |
| **5.1** `.source.json` 誤傳正解 | `970` | `2068–2080` | `api/routes/case.py::_rejected()` | `pytest tests/api -q -k source_json_hint`；400 且訊息含 `source_file`；mutation 1 條 |
| **5.2** 兩表 tooltip | `992` | `2081–2091` | `EventTablesPanel.tsx` 之表頭 | `npm --prefix frontend test -- --run eventTableTooltips` **≥2 條**；mutation 1 條 |
| **5.3** 缺欄覆蓋率確認框 | `1014` | `2092–2105` | **Task 4.3 之同一訊息組裝處** | `npm --prefix frontend test -- --run exportHorizonCoverageDialog` **≥2 條**；mutation 1 條 |

### 2C.3 B8 之陷阱

1. **5.0**：只放文案與公式指標，**不放數值**；**不得**把定義同時寫在前端（5.2 以 `==` 斷言防漂移）。
   🔴 驗收是 `set(g) >= {八鍵}`（**成員資格非等值**）——Task 7.5 之後還會加鍵。
2. **5.1**：只**追加**提示；`legacy_schema_detected` 之 reason 字面**不變**（下游依 reason 判斷）。
   🔴 **不得**因判別為 source.json 就自動改走 `source_file` 流程（靜默轉換＝契約禁止）。
3. **5.2**：glossary 缺該鍵 ⇒ 顯示 **fail-closed 佔位**而非空字串（驗收②）。
   🔴 前端**不得另寫一份定義**——本 epic 之 `eventContractDocs.ts`（B7）是同型作法之範本：
   鏡像常數 ＋ vitest 讀契約檔逐字 `toBe` 比對。
4. **5.3**：與 4.3 **合併實作**（4.3 已完成 ⇒ 直接擴寫）；訊息**不得**含「主答案窗」字樣；
   **不得阻擋匯出**。數字要**精確比對**（`含 3`，不是「含某個數字」）。

---

## §2E B10 是什麼（Phase 7 全部，**九個** Task）

**B10 ＝ 全棧接線**，TODO 標籤皆為 `票 #3-全棧`。這是 GAP-3 的最後一批。

| Task | 標題 | **真實**依賴（偵察後更正；**不是** TODO 的「—」） |
|---|---|---|
| 7.0 | 前置：擴 `EventExportOptions` 補齊五維度 | 無（唯一可先動的） |
| 7.0b | 分析時 `label_value` producer 與其 wiring | 無，但**範圍遠大於 TODO 清單**（見 2E.1 群集 D） |
| 7.1 | 五維度全部接出前端 | **7.0** |
| 7.2 | 機械閘：`selectable(path,dim)` ＋ 選值真的傳到落檔 | **7.0／7.1** |
| 7.3 | 動態揭露本批設定 | 🔴 **7.6**（formatter registry 由 7.6 定義）＋ 4.1c 抽常數 |
| 7.4 | 條件 IC decay 之邊界揭露 | 🔴 **4.1c 抽成 exported 常數**（現為 JSX 行內字串） |
| 7.5 | 事件後報酬表正／反／全體三組 | 4.2（已完成）＋ **5.0 glossary 先登記**＋ 2.3 筆數守恆 |
| 7.6 | IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定 | 🔴 **7.1**（`EVENT_DIM_PATH_EXCLUSIONS`） |
| 7.7 | Feature run `time_range` 與事件期之對證 | 🔴 **7.0b**（同一 `timeframe_seconds` 物件之 `is` 比對） |

**定案實作順序**：
`7.0 → 7.0b → 7.1 → 7.2 → [抽 formatter registry ＋ 4.1c 常數] → 7.6 → 7.3 → 7.4 → 7.5 → 7.7`

### 2E.1 ✅ 座標偵察**已做**（2026-08-28，Claude ＋ 三委員平行；`49f98ed2`）

收斂檔＝`handoffs/reconcile/20260828-gap3ux-b10-consult-r1/synth.md`
（三家 **17 條 findings 全部成立**，主委逐條實跑複驗，**無一條被推翻**；八個群集 A–H）。
主委獨立版＝該檔之群集敘述；委員原文在 `sources/`。

🔴 **主委原本猜錯的兩件事（先記自己錯的）**：
① 猜「`_run_analysis` 已有事件分支、只是 `timeframe_seconds` 可能多處建構」——**連分支都沒有**（三家一致）；
② 猜「`event_forward_return_table` 尚無 `strata` 頂層鍵」——**已存在**（兩家獨立打穿）。
照錯誤基準開工會新建第九頂層鍵，直接違反 Task 7.5 要點 1。

#### 五題之答案

1. **`EventExportOptions`**（`frontend/src/lib/eventExport.ts:25-67`）現有 **11 欄**。五個批次維度中
   `scenario?`／`entryPriceSemantic?` 已是可選參數，**缺** `controlKind`／`labelReturnMode`／`decisionOffsetBars`。
   落檔寫死於 **`:216`**（`decision_offset_bars: 0`）／**`:229`**（`label_return_mode`，**巢狀**）／
   **`:234`**（`control_kind`）＋ **`:217`**（`entry_price_semantic` 預設 `trigger_open`，§F-3′ 要改 `trigger_close`）
   ⇒ **實際要動四處，不是 TODO 說的三處**。生產 caller 唯一，在 `search/page.tsx:645-654`，五維度**一個都沒傳**。
   🔴 **TODO 的行號 `:9-17`／`:92`／`:102`／`:104`／`:522-525` 全數過時**（群集 H）——
   實作與 review 一律引用**符號名 ＋ 本表行號**，不引用 TODO 行號；**不就地改 FROZEN TODO**。
2. **`label_value`**：producer **只有** `event_samples/generator.py:212`（合成產生器）；
   consumer＝`ic_feed.py:66-80`（缺 ⇒ `missing_label_value`）→ `ic_filter_orchestrator.py:2877-2906`；
   validator＝`import_contract.py:583`（走 `_is_num`，仍收 NaN＝`R-B7-1`）；匯出端已不寫（`eventExport.ts:197-198`）。
   🔴 ⇒ **真實使用者路徑目前沒有任何 producer**：從 `/search` 匯出的批次不含 `label_value`，
   CSV 不自帶就永遠 `missing_label_value` ⇒ **條件 IC 對真實批次現在是不可用的**。7.0b 是**補洞，不是搬家**。
3. **glossary**（`event_metrics_glossary.json`）實有 **21 條** definition ＋ `_doc`／`_version`，
   **無** `positive`／`negative`／`all` 分組標籤、**無**兩個 `not_computed` 文字
   ⇒ 7.5「須同步 (c)」**不是空操作**，`R-B8-1` 的觸發點確實在此。
   `ic_report_contract.json` 之 `report_sections` 現有 7 鍵，**無 `event_return_table`** ⇒ 7.5 要點 3 為真實新增。
4. **`analysis_rejected`**：B9 已預先用**成員資格**斷言（`tests/api/test_gap3_ic_feature_cap.py:26-27`，
   檔頭第 6–7 行明寫為 7.7 預留）⇒ **7.7 不必改既有斷言**。
   🔴 但本節原文說「再加**兩個** reason」**是錯的**——SPEC L3337-3338 定死最終集合為**五個**：
   `feature_count_exceeds_cap`／`feature_coverage_insufficient`／`feature_coverage_unknown_legacy_run`／
   `feature_coverage_unknown_timeframe`／`feature_coverage_unknown_timestamp_format`（＝**加四個**）。
5. **`selectable(path,dim)`**：兩側皆可導出——契約側 `accepted(dim)`＝`accepted` 鍵或 `enum` 全集
   （實測：`scenario` enum4 無 accepted；`control_kind` enum4／accepted3／`rejected_with_reason`；
   `entry_price_semantic` enum5；`label_return_mode` enum3 **住 `required_fields.label_definition.fields`**；
   `decision_offset_bars` 為 `int, min 0`，**非 enum**）；排除側＝單一具名常數 `EVENT_DIM_PATH_EXCLUSIONS`
   （SPEC L2854-2860 五列封閉）。🔴 **難點在 UI 側**：「可操作選項集合」須由 **render 後的 DOM 查詢**導出
   （`getAllByRole('option')` 濾 `disabled`），**不得**在測試裡另寫期望清單（TODO 7.2「不可做」明禁）。

#### 逐 Task 座標（主委＋三家實跑；**詳細內容一律回讀 TODO／SPEC 該 Task 全文**）

| Task | 落點（**實查行號**） | 現況 | 與 TODO 之落差 |
|---|---|---|---|
| **7.0** | `eventExport.ts:25-67`（型別）／`:216`,`:217`,`:229`,`:234`（落檔）／caller `search/page.tsx:645-654` | 兩維度已參數化、三處寫死 | 行號全過時；實動**四處** |
| **7.0b** | **新建** `event_samples/label_value_from_case.py`＋**SPEC L2487 指名之新檔** `event_samples/keys.py`；`alignment.py:21-27`（`_EVENT_COLS` **無 `symbol`／`timeframe`**）；`ic_analysis_service.py:225`（`_run_analysis`）；`event_split.py`；`ic_feed.py`；**`api/models/ic_models.py`**（加 `event_import_id`＋`event_label_spec`，SPEC L2609）；**`useICAnalysis.ts`／`lib/api.ts`**（停送 `event_timestamps`，SPEC L3364-3387） | 🔴 **事件分支不存在**：全檔 `timeframe_seconds`／`prepare_analysis_windows`／`check_feature_run_coverage` 字面數皆 **0**；`mode` 僅 `longitudinal｜cross_sectional`；`event_import_id` 在 `api/`／`momentum/` **完全不存在** | TODO「修改檔案」清單**漏 4 類檔**（見群集 D）；另有**第二條旁路** `_run_full_analysis:1001` 亦傳 raw `event_timestamps` |
| **7.1** | **新建** `frontend/src/lib/eventDimensions.ts`；`search/page.tsx`／`/data-preparation` | `selectable`／`EVENT_DIM_PATH_EXCLUSIONS` 皆不存在 | 無 |
| **7.2** | **新建** `frontend/src/lib/__tests__/contractEnumWiring.test.ts` | 不存在 | TODO 只列 under 向；**over 向缺**（見 2E.3） |
| **7.3** | `search/page.tsx:1853-1888`（4.1b 揭露區，六個 testid） | **已有半套**：`-scenario`／`-depth`／`-depth-pending`／`-depth-{tf}`／`-purge-{tf}`／`-control-kind` | TODO 要點 2 說「原清單漏掉 `control_kind`」——對**現況不成立**（`:1884` 已有）；缺的是進場價／報酬算法／決策位移三項＋ registry 化 |
| **7.4** | `search/page.tsx:1889-1893`（4.1c 文案） | **JSX 行內字串，非 exported 常數** | 「同一參考」斷言**須先抽常數** |
| **7.5** | `tables.py:193-208`（`strata` **已存在**，四子鍵）／`dedupe.py:114-115`（`ctx_cols` **無 `control_kind`**）／`ic_report_contract.json`／`EventTablesPanel.tsx:72-73`（**只讀 `sensitivity_micro`，完全不讀 `strata`**） | 頂層恰 8 鍵✓；無 `by_label` | 7.5 ＝**擴充既有 `strata`**，不是新建 |
| **7.6** | `case.py:364-368`（route 只轉呼）／**`case_import_service.py:1280-1285`（真正 producer）**／**`event_import_models.py:80-99`（`EventImportSummary` 只有 `direction`／`scenario`，缺六鍵）**／`ic-analysis/page.tsx`（957 行，**完全無**批次揭露區，只有 `:600` 一行 `EventTablesPanel`） | 全缺 | TODO 只列 route ⇒ 只改 route 必被 `response_model` **靜默濾欄** |
| **7.7** | `feature_factory_models.py:116-133`（`RunInfo` 19 欄，**無 `time_range`**）／`feature_factory_service.py:811-836`（`list_runs`）＋`:764-800`（`_browse_metadata_for_run`）／`routes/feature_factory.py:60-62`／`frontend/src/lib/types.ts`／`ic_analysis_service.py`（新建 gate） | 全鏈零實作 | 🔴 **manifest 前提不完整**：實掃 14 份，**12 份**有 `time_range`（epoch **秒**字串），**2 份缺鍵**（`BTCUSDT/1h/cfg_batch_ret`、`ETHUSDT/1h/cfg_batch_ret`）——SPEC L3310-3312 只裁定 `{None,None}`，**未裁缺鍵** |

#### 陷阱（逐條是本輪實跑抓到的）

1. 🔴 **7.0b／7.7 的事件編排是 net-new**。掛 gate 時**只在 `request.event_import_id` 存在時進入**，
   否則會誤擋 cross-sectional（`:262-304`）與純特徵 longitudinal（`:306-369`）。
   另**必須同時處理** `_run_full_analysis:1001` 這條旁路，否則可繞過 receipt-derived `decision_at`。
2. 🔴 **`api/` 不得直接 import 新模組**：R3 只認 `momentum.factories.create_event_sample_pipeline()`
   之 `@staticmethod` 出口（現有 20 個，**無**這兩個新函式）⇒ **7.0b 須先加 R3 出口**，TODO 未提此步。
3. 🔴 **7.6 只改 route 會靜默失效**：`EventImportSummary` 沒宣告的鍵會被 `response_model` 濾掉（§4.2 形態 5）。
4. 🔴 **7.5 邊界② 是真實風險**：`EventTablesPanel` **從未讀過 `strata`**，後端全綠仍可能前端只顯示舊單表。
5. 🔴 **7.7 之 `_browse_metadata_for_run:790-793`** 只在 `feature_count`／`row_count`／`quality_status`
   任一為空時才讀 manifest ⇒ 把 `time_range` 掛在該分支內會**間歇性拿不到值**；須另行無條件讀取。
6. 🔴 **7.0b 邊界② 會假紅**：`h=3` vs `h=7` 之 `label_values` 「不相同」在 flat-close 序列下兩者同為 `0.0`
   ⇒ fixture 須顯式非平坦且手算 expected（`CODEX-R1-P2-06`）。
7. **7.0 之 `entry_price_semantic` 預設改動**屬 D-4 合法變更，**須在 commit message 說明**；
   同批要驗「其餘四維度維持預設 ⇒ G-2 golden byte 級不變」，否則假綠。

#### 本輪之主委裁定（**非 SPEC 字面**，批末 review 須請三家攻）

- **裁定 1（群集 F）**：manifest **缺 `time_range` 鍵**與 `{"start":None,"end":None}` **同等處置**，
  同用 reason `feature_coverage_unknown_legacy_run`。理由：兩者資訊量相同（都拿不到區間），
  分兩個 reason 只讓前端多一種字面；且 §C0 只能更嚴，缺鍵放行才是弱化。
- **裁定 2（群集 D）**：TODO 7.0b／7.6 之「修改檔案」清單不足以落地 SPEC 所定交付，
  **不開 D-005 延伸檔**——缺的是操作清單、不是判準修訂（判準字面 SPEC L2487／L2593／L2609／L3364 皆已有），
  而開延伸檔要再付一輪戳記，B10 已欠 D-003 戳記。改為在本表逐檔列出並於 commit message 引用 SPEC 行號。
  **若批末 review 三家認為不足，再升 D-005。**

### 2E.2 B10 之收案判準（沿用 B9 之改寫，**不要退回舊判準**）

🔴 **禁用「三家零 finding」當停輪條件**（`20260828-gap3ux-b9-consult-r1` 三家一致廢止）。
改用可列完的判準：
① **雙向矩陣**——每種輸入形態都有 under（該擋擋住）與 over（**不該擋沒被擋**）各一條可重跑測試；
② mutation `closure=CLOSED` 且紅集合**逐一等於**；
③ 具名殘留皆有三值理由；
④ 上輪 P0／P1 原反例 CLOSED **且**本輪對矩陣雙向探針無新 P0／P1。

🔴 **B9 五輪的病根**：我只測「該擋的有沒有擋住」，從沒測「不該擋的有沒有被誤擋」——
前五輪的缺陷**全部藏在只有單向對照的格子裡**。B10 的 7.2 是機械閘，同一個坑會再出現。

### 2E.3 🔴 本批之雙向矩陣缺口（偵察輪確立；**實作時逐格補 over 條**）

TODO／SPEC 對下列格子**只寫了 under 向**。收案判準①要求每格兩向各一條可重跑測試 ⇒ over 條由本批補。

| Task | under（TODO 已有） | **over（TODO 缺，本批須補）** |
|---|---|---|
| 7.2 ③ | `decision_offset_bars = -1` ⇒ fail-closed | `k = 0` 與正整數 ⇒ 須成功且落檔 `=== k` |
| 7.2 ① | 契約加第 5 個 `scenario` 值而未改 UI ⇒ 須紅 | `/data-preparation` 之 `scenario` **四值全部可操作**（不得被 `/search` 之排除誤及） |
| 7.7 | run 不涵蓋事件期 ⇒ fail-closed | 現存 12/14 之 **epoch 秒字串 run 須放行**（SPEC 驗證⑩已有此條）；缺鍵 2/14 之處置見裁定 1 |
| 7.0b | h 與匯入宣告不同 ⇒ 拒絕 | **非退化** fixture 下 `h=3`／`h=7` 皆成功且值不同（`CODEX-R1-P2-06`） |
| 7.6 | 批次事實欄無可輸入控制項 | 分析參數區**必須**有可輸入控制項 |
| 7.0b 編排 | 事件批走五階段 | cross-sectional／純特徵 longitudinal **不得**被誤擋 |
| 7.5 | `control_kind` 混批 ⇒ `not_computed` | `positive`／`negative` 兩組在三種 `control_kind` 下 byte 級相同（TODO 邊界①已有）✓ |

## §2D B9 是什麼（Phase 6 全部，五個 Task）

**B9 ＝ IC 分析止血閘。** 依 §B 拓撲，**內部依賴＝ Task 6.0 必須先做**（6.1 讀它取 reason 字面）。

> **一句話**：218,369 個特徵的 run 拿去跑 IC 分析會把記憶體吃爆；
> 這批在**啟動任務之前**擋下來，並且用**可重跑的量測**決定上限值，不是拍腦袋填。

### 2D.1 🔴 偵察結論（2026-08-26 主委實跑，**不必重查**）

| 事實 | 位置 | 對 B9 的意義 |
|---|---|---|
| **IC 側契約現有三類 reason** | `ic_report_contract.json` 之 `reasons`：`net_ic_unavailable`／`event_fallback`／`xsec_not_applicable`（實跑確認 `len==3`） | 6.0 加第四類 `analysis_rejected` ⇒ 驗收之 `len(r)==4` 成立；🔴 **不是**加到 `event_import_contract`（那是匯入契約） |
| **analyze 端點落點** | `api/routes/ic_analysis.py:34` 之 `start_ic_analysis`，body 只有一行 `await ic_analysis_service.start_analysis(request)` | 6.1 之前置檢查要插在**呼叫 service 之前**；TODO 定案落點為此檔（**不是** `api/routes/ic.py`，SPEC L2119 之 mutation 敘述寫的是舊檔名） |
| **6.4 之取樣時點綁 6.1 之檢查位置** | SPEC L2160–2171 | 🔴 **兩者須同批實作**並以同一測試釘住先後——6.1 若被移到任務啟動之後，6.4 會量到已載入大矩陣的 footprint 而失去意義 |
| **量測工具已定死** | macOS `sample <pid>` 之 **Physical footprint** 欄 | 🔴 **禁用 `ps rss`**：UAT 實測 RSS 96–400MB vs footprint 7.1GB（macOS 壓縮頁面使 RSS 失真） |

### 2D.2 B9 五個 Task 之關鍵座標

| Task | TODO 行 | SPEC 行 | 主要落點 | 驗收命令（條目下限） |
|---|---|---|---|---|
| **6.0** reason 登記處 | `1047` | `2108–2122` | `momentum/Analysis/contracts/ic_report_contract.json` | ①`python3 -c` 一行含 `len(r)==4`；②硬編碼掃描 `== 0`；mutation 1 條 |
| **6.1** analyze 前置特徵數檢查 | `1073` | `2123–2133` | `api/routes/ic_analysis.py` | `pytest tests/api -q -k ic_feature_cap` **≥3 條**；mutation 1 條 |
| **6.2** 上限值之量測協定 | `1096` | `2134–2147` | 新增 `scripts/measure_ic_footprint.sh` | receipt **≥3 個量測點**、每點六欄齊全、重跑 2 次 peak 差 `< 20%`；mutation 2 條 |
| **6.3** 進度回報與狀態區分 | `1125` | `2148–2159` | `api/routes/ic_analysis.py`（progress response）＋前端 | `pytest tests/api -q -k ic_progress_fields` ＋ vitest 兩狀態字串 `!==`；mutation 1 條 |
| **6.4** 止血閘之存活驗證 | `1148` | `2160–2171` | `tests/api/`；復用 6.2 之腳本 | `pytest tests/api -q -k ic_stop_gate_alive`，條目數 `>=` V-8 所列；mutation 1 條 |

### 2D.3 B9 之陷阱

1. **6.0**：程式與前端一律**由契約檔取字面**；驗收②之硬編碼掃描 `== 0`。
   🔴 斷言用**成員資格**（`in`）而非等值——Task 7.7 會往同一類再加兩個 reason，
   寫成 `== ['feature_count_exceeds_cap']` 會在 7.7 上線時假紅。
2. **6.1**：碼內須註明本 Task 為**過渡止血**，GAP-6 之分塊計算上線後取代。
   🔴 驗收要斷言**任務未被建立**（task store 筆數不變），**不是只驗 HTTP 400**——
   只驗狀態碼的話，「先建任務再回 400」也會綠，而那正是要防的事。
   🔴 **不得**提供「強制略過上限」之開關。
3. **6.2**：🔴 **禁拍腦袋填數字**；無 receipt 不得寫入設定值。
   上限＝最小超標點之 `feature_count` **再乘安全係數 0.5**。
4. **6.3**：階段字串須設計為**可擴充集合**，測試**不得**以固定 enum 窮舉相等斷言鎖死
   （GAP-6 會細分更多階段；改測試是掩蓋行為變更的常見路徑）。
   🔴 **不得**以固定假進度值填充（UAT 已證實 `progress==0.12` 卡 15 分鐘之誤導性）。
5. **6.4**：🔴 **不得在 cap 檢查之前採樣就宣稱通過**（SPEC R1 明列此假綠形態）。

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

**B1–B7 之實績供校準**：B1 五輪 3→2→10→7→0；B2 兩輪 2→1；B3 三輪 6→3→0；
**B4 六輪 7→4→4→1→1→0**；**B5 四輪 6→3→1→0**；**B6 六輪 5→2→2→1→兩家零→0**；
**B7 三輪 7→3→0**（另加 `D-004` 戳記三輪，R1／R2 皆 codex 一家 REJECTED 且兩次都對）；
**B8 五輪 5→1→4→2→0**（🔴 **非單調**：R3 跳回 4 是因為主委首次請三家**獨立重掃全部 21 條 definition**
＝新開的攻擊面，不是修法退步；R4 之 2 條是工作區事故及其下游）。
🔴 **B8 之角色反轉值得記**：R1／R3 是另兩家判可收而 **codex** 抓到真缺陷；R4 反過來是 codex／grok
零 finding 而 **composer 抓到一條 P0**。⇒ `兩家零 finding 不構成放行理由` 對**任何一家**都成立，
不是針對特定家族——三家都當過那個唯一發現問題的人。
⇒ **抓一個估**：三到六輪、findings 個位數、**幾乎每批都有一輪是「另兩家判可收而 codex 抓到真缺陷」**。

### 🔴 B4–B7 學到的八件事（下一批直接沿用，別重踩）

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
6. **「宣稱大於實作」是本 epic 最常見的自傷（累計七次）。**
   B4 A-016c 宣稱「一律 fail-closed」而當時只涵蓋一種；B5 註解宣稱「四個顯示點共用」而只有兩個；
   **B7 三次**：D-004 R1 未逐家核對即宣稱「三家一致」而採少數版、
   D-004 R2 三家一致講過的限制在摘要時整條掉了、
   review R1 之 brief 宣稱「深度拿不到就擋」而只擋了「有條件」那一半（**三家同時抓到**）。
   ⇒ **寫下宣稱前先數一遍實際 caller**；**寫「三家一致」前逐家開原文核對那一格**。
7. 🔴 **列出嫌疑點 ≠ 驗過嫌疑點（B7 新增）。**
   B7 review R2 之群集 E ＝ R1 修法自身開的破口，而它**正是主委寫進 brief 請委員攻、
   卻沒先自己打過的嫌疑點**。⇒ 寫進 brief 的攻擊面，自己也要先打一遍再送出去。
8. 🔴 **型別關卡不能只靠 `npm run build`（B7 新增）。**
   它**不涵蓋測試檔** ⇒ vitest 是 transpile-only、型別錯照樣全綠。
   前端收案前固定加跑 `npx --prefix frontend tsc --noEmit -p frontend/tsconfig.json`。
9. 🔴 **派 review 前先 commit（B8 新增，付過代價）。**
   B8 從 R1 到 R4 跑了**四輪 review 全程未 commit**，期間 `import_contract.py` 之整段實作
   回到 HEAD、憑空消失（composer 複驗時才發現）。委員合約本就禁對 tracked 檔 `git checkout`，
   但**合約擋不住已經發生的事**；先 commit 是把「可還原的基準」從髒工作區換成不可變物件
   ——那是主控端唯一能自己控制的一半。
10. 🔴 **mutation runner 必須同時具備 `IsolatedWorktree` 與備份閘（B8 新增）。**
   B1–B6 之 runner 皆有隔離；**B7 之範本已經掉了隔離而交接沒記**，B8 照抄 ⇒ 缺陷延續兩批。
   缺隔離的後果：三家並行複驗時在共用工作樹上互相污染（實測到同一個檔同時殘留兩個變異標記、
   假 `closure=OPEN`、baseline 殘紅）。**複製範本前先 `grep IsolatedWorktree`。**
11. 🔴 **讀執行結果不要 `tail` 掉失敗訊號（B8 新增）。**
    B8 有一次 runner 在第 5 條 crash（錨點失效），receipt 未被覆寫，而主委只讀 `tail -6`
    ⇒ 看到的是**上一輪的舊 receipt**，差點據此宣稱全數通過。
    固定顯式檢查三個訊號：`runner_rc`、`grep -c Traceback`、`n_mutations == len(MUTATIONS)`。

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
| 2 | 動過 `scripts/` ⇒ 收 epic 前跑 `bash scripts/gov_check.sh --no-probe`（丟背景，十分鐘級） | 收 epic 前 | ✅ 2026-08-25 已跑；**B2–B8 皆未動 `scripts/`**（B8 只動 `handoffs/` 之 runner，未入版控）。若 B9 動了需重跑 |
| 3 | **GAP-3 之 UAT B 段簽字**仍在使用者手上（`docs/GAP3_UAT_CHECKLIST.md`） | 使用者 | ⬜ **未簽字不收案** |
| 4 | 根目錄 `.probe_ic{,2,3}.sh` 三個 untracked 檔為更早批次殘留 | 隨時 | ⬜ 要清可直接刪 |
| 5 | `handoffs/run_receipts/gap3ux-b{3,4,5,6}-record*.json` 為 `--record` 之暫存 receipt | 隨時 | ⬜ untracked，可刪 |
| 6 | 根目錄檔名為 `--only` 之檔（內容為某委員誤寫之 mutation receipt） | 隨時 | ⬜ untracked、無害，可刪 |
| 7 | ~~`D-004` 之戳記輪~~ | — | ✅ 歷 R1／R2／R3，**R3 三家 APPROVED**（見 §2B.0） |
| 8 | `handoffs/gap3ux_b7_*.py`／`*.json`（runner 與預期檔）為 untracked，**勿清** | 隨時 | ⬜ 下一批之 runner 直接複製它（含**備份閘**） |

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
- 🔴 **`handoffs/run_receipts/*.receipt.json` 會被委員覆寫**（2026-08-26 實際踩到）：
  B7 R3 之 codex 為複驗而跑了主委的 mutation runner，把 repo 內那份 receipt 蓋成
  `closure: OPEN`（他自陳「首次 combined receipt 出現暫時 restore timing 殘留」）。
  主委寫 `HANDOFF.md` 之 `VERIFY:` 時被 `verify_pretooluse.sh` 以「REF 檔案無 backing」擋下才發現
  ——**否則就會 commit 一個指向 `OPEN` receipt 卻宣稱全數通過的訊息**。
  ⇒ ①收尾前**必查** `grep -o '"closure": "[A-Z]*"' <receipt>`；
  ②review brief 要寫明「複驗請輸出到你自己的 workdir，勿寫 repo 內 receipt 路徑」。
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
| **`R-B7-1`** | `label_value` 仍走 `_is_num` ⇒ **仍收 NaN**（附帶欄已改用 `_is_finite_num` 拒之）。**屬既有行為、非 B7 弱化**——改它會動到 B7 範圍外之既有 caller | `blocked-by` Task 7.0b（label producer 於分析時重寫） | 主委；7.0b 落地時一併收 |
| **`R-B7-2`** | 前端既有型別錯 **8 行**：`FactorReturnChart.test.tsx`（4）／`useFeatureFactory.batchDate.test.ts`（**4**，兩行各兩個錯）。`npx tsc --noEmit` 可見，`npm run build` 看不見。⚠️ 本欄原記「6 條」為**計數誤植**，2026-08-27 實測更正（三家 R2／R4 皆回報 8） | `user-ruling`（面向未來不溯及既往） | 主委；不排工。🔴 **新寫的檔不得再增加此數** |
| **`R-B8-1`** | Task 5.0 之 21 條 definition **應收窄**為白話語意＋判讀陷阱，計算細節交 `formula_ref`；並保留算式綁定、審查必跑不對稱探針。三家 R4 表態 codex(B)／grok(B)／composer(C)，實質共識如前述 | `blocked-by` Task 7.5（該 Task 本就會動 glossary，一併改成本最低） | 主委；三家皆明示**不阻擋 B8 收斂** |
| **`R-B8-2`** | glossary 之後設欄（`_doc`／`_version`／`formula_ref`）隨 build-time import 進 client bundle（`page-*.js`，`_doc` ≈540 字元）。無機密 | `user-ruling`（R2 三家一致：拆檔會破壞「SoT 單檔」，代價 > 幾百字元） | 主委；不排工 |
| **`R-B8-3`** | 工作區 revert 事故之兩條**無法 post-hoc 證明**的假設：①「災損只有 `import_contract.py` 一個檔」——post-commit 後無法重播「還原後又被編輯覆蓋」之中間態；②「主委由對話紀錄重打之內容與事故前**逐字**相同」——無備份可比對，只有行為等價（19 條 mutation ＋ 型別 probe）佐證 | `needs-research` | 主委；**觸發＝日後在 Task 5.1 相關碼發現與定義不符之行為時，回頭查此條** |
| **`R-B3-3`** | 逐 symbol 之 purge 下界（`EventSplitConfig.embargo_ms_by_symbol`）未實作 ⇒ 各 symbol 宣告下界**不一致**之批次一律拒絕分析（fail-closed，不取全批 max——SPEC §D-3′-a(ii) 明令禁止）。使用者當前解法＝依 timeframe 拆批 | `blocked-by` Task 7.0b | 主委；7.0b 落地時解除 |
| **`R-B4-1`** | **CSV 方言之殘餘前後端差異**：支援之行尾＝**LF／CRLF**；引號內 CR 當資料保留；裸 CR（含舊式 Mac）兩端一致不支援。其他方言／編碼／writer 癖好之殘餘差異**不再逐一開輪**。兜底＝後端永遠是契約權威；前端只做預覽且**不得產出看似合理的假欄名**（由 mutation `1.5-M5` 鎖住）。R6 由 codex 以 **9,331 個字串窮舉**比對兩端 predicate，`mismatch_count=0` | `user-ruling` | 主委；**觸發＝出現具體且可重跑之使用者實例才重開** |
| **`R-B9-5`** | 閘門與 loader 之等價性**靠 `_plan_cross_sectional_load` 這一個共用點 ＋ 雙向形狀矩陣測試**維持，**不是**由型別或呼叫關係強制。新增 IC 請求欄位／新增分析入口時若未同步，仍可能出現第六種不一致。三家 consult 之耐久解法＝`LoadPlan`（一次解析、把同一 plan 帶進 task），**明列為 GAP-6 或 D-00N 之工作**，不在 B9 做 | `user-ruling`（B9 存活至 GAP-6 即整條刪除；codex 實查 `plan_load` 下沉會動 **7 個 production caller**（cross-symbol training／model task／feature browser／XGBoost／IC）且其測試基線本就有 2 條紅 ⇒ 為一個即將刪除的閘做跨模組手術，ROI 為負） | 主委；**觸發＝新增 IC 分析入口或 `ICAnalyzeRequest` 新欄位時，須同步擴充形狀矩陣** |
| **`R-B9-1`** | IC 止血閘之上限 **80,515 綁本機 8GB**（＝最小超標點 161,031 × 0.5，導出自 `handoffs/run_receipts/gap3ux-b9-footprint.receipt.json`）。換機器須覆寫 `IC_ANALYSIS_MAX_FEATURES` 並重跑量測 | `user-ruling`（過渡止血，GAP-6 分塊計算上線即整條刪除） | 主委；不排工 |
| **`R-B9-2`** | 量測之安全閥在 peak > RAM×0.5 時 `kill -TERM`，故 receipt 記的是「多快撞到 4GB」而非真實最終 peak（UAT 觀測為 7.1GB）；3 秒採樣對 1–2 秒之小 run 解析度不足 | `blocked-by` 本機 8GB 實體限制 | 主委；換大記憶體機器時重跑 |
| **`MEASURE-CANCEL-1`** | IC 分析**無取消任務端點** ⇒ 量測腳本之安全閥只能 `kill` 整個後端行程，無法只停該任務 | `blocked-by`（端點不存在，屬 IC-Analysis 主線範圍） | 主委；IC-Analysis 主線補端點時解除 |
| **`R-B9-3`** | 閘門之**最後一個具名破口**：呼叫端硬塞一個 registry 查不到、HDF5 header 也讀不出的 `features_path` 指向大 run。R3 之後其餘路徑（顯式 hash／`cross_sectional_runs`／識別字串／隱式 latest ×2）皆已覆蓋 | `user-ruling`（過渡止血；該路徑非使用者介面之路徑，擋住它會弄壞 golden replay 這個既有消費端） | 主委；不排工 |
| **`R-B9-4`** | Task 6.3 之接線回歸證據為**原始碼層斷言**（`page.tsx` 兩處 call-site 走 `icPollFailed`），不是 render 整頁的 runtime 測試。`CODEX-R3-P2-03` 要求後者 | `needs-research`（render 整個 ic-analysis 頁需先評估其 store／chart 依賴之 mock 成本與 flakiness） | 主委；**觸發＝下次動 ic-analysis 頁面時一併評估** |
| **`D-001/D-002/D-003` provenance** | `gate.sh register-output` 只收 `handoffs/` 或 `stampable_artifacts.txt` 明列者 ⇒ 對 `docs/*.D-00N.md` 跑 `reconcile_stamps_check.sh` 會報 provenance pending（**非戳記造假**） | `user-ruling` | 主委 |

### B10 新增之三條具名殘留（皆出自 R1 三家 review）

| 代號 | 內容 | 三值理由 | owner／觸發 |
|---|---|---|---|
| **`R-B10-1`** | **各 symbol 之 purge 下界不一致時，事件分析 fail-closed 拒絕**（不取 max、不取 min）。根因是單位與粒度都對不上：IC 切分器用的是**列數之全域 scalar** embargo（`ic_filter_orchestrator._split_rows` 之 `purge_gap`／`embargo`），而 §D-3′-a(ii) 算出來的是**毫秒之 per-symbol** 下界。取 max 折成 scalar 正是該節**明令禁止**之 per-scope 冒充（本 epic 在 B3／B5 各犯過一次）⇒ 採 B3 之既有先例「能表達就套用、不能表達就拒絕」。**使用者當前解法＝依 timeframe 拆批**（與已解除之 `R-B3-3` 同一解法） | `blocked-by`：IC 切分器之 embargo 為全域列數 scalar；要支援 per-symbol 須改 `ic_filter_orchestrator` 之切分模型，屬 **IC-Analysis 主線**範圍 | 主委；**觸發＝IC 切分器支援 per-symbol embargo 時** |
| **`R-B10-2`** | SPEC ⑭(a)(b)(d)（真剔除列後之 manifest／split 配對、空 allowed ⇒ loud unavailable）在 **live 路徑上不可證偽**：3a（`check_feature_run_coverage`）是**批次級 pass/fail**、不產生 event-id 子集 ⇒ `_run_event_label_stages` 恆傳全集給 `apply_event_coverage`。本批之驗收是對 `apply_event_coverage` **直接驗語意**（`test_..._14abd_coverage_filter_semantics`），**不等於** live 路徑有守到。R1 由 composer／grok **兩家獨立**指出 | `blocked-by` GAP-6：分塊計算上線後 3a 才會產生 event-id 子集，屆時 live 路徑才有剔除可驗 | 主委；**觸發＝任何讓 3a 產生子集之機制上線時** |
| **`R-B10-3`** | TODO 7.0b 之「修改檔案」列了 `ic_feed.py（只吃 prepared1）`，**本批未改該檔**。IC 分析鏈**根本不經過它**（`_run_event_label_stages` 直接由 `prepared1.windows`＋`per_tf` 組出餵給 analyzer，因為 SPEC ⑩(ii″) 之 `is prepared1` 身分比對禁不起「拆回 DataFrame 再組回來」）。🔴 **R2 更正（`CODEX-R2-P1-01` 之 3a）**：本欄原寫「它現存的唯一 consumer 是匯入端之 `EventImportService.analyze`」——**該敘述不成立**。實查 `rg 'build_event_ic_inputs\('` 只命中**定義與 tests**，**production caller 為 0** ⇒ 本檔目前是**沒有生產消費者的碼**。這使殘留理由改變：不是「改了會弄壞表格鏈」，而是「改一個沒人呼叫的東西沒有收益，且會讓既有測試失去對照」 | `blocked-by`：需先決定該模組是**接上分析時 producer** 還是**刪除**；兩者都超出 B10 範圍 | 主委；**觸發＝決定 `ic_feed` 之去留時**（建議併入 GAP-6 一起裁） |

**已解除（不要再當殘留看）**：`R-B2-1`（B4）／`D-002 A-004`、`R-B3-1`、`R-B3-2`（B5）／
🔴 **`R-B3-3`（B10：`EventSplitConfig.embargo_ms_by_symbol` 已實作，per-symbol 下界可表達）**
——但**新的邊界移到了 `R-B10-1`**：可表達不等於 IC 切分器吃得下。

---

## §8 檔案地圖（B6／B7 會碰到的）

| 用途 | 路徑 |
|---|---|
| 事件樣本模組 | `momentum/Analysis/event_samples/`：`pipeline.py`／`tables.py`／`event_split.py`／`lookahead_registry.py`／`lookahead_depth.py`／`lookahead_gate.py`／`lookahead_declaration.py`／`import_contract.py`／`canonical_serialize.py`／`condition_engine.py` |
| 契約（欄位／枚舉／reason 之 SoT） | `momentum/Analysis/contracts/event_import_contract.json`、`future_column_lookahead.json`、`condition_engine.json`、`ic_report_contract.json`（IC 側；**B9 之 6.0 加 reason 在這裡，不是匯入契約**）；🔴 **B8 之 5.0 要新建** `event_metrics_glossary.json` |
| case 端點 | `api/routes/case.py`：`import_events_file`／`import_events_json`／`import_events_csv`／`lookahead_declaration_preview`／`lookahead_depth`／`list_event_imports`／`get_event_import`（**3.1 之鄰居**）／`analyze_event_import` |
| 匯入服務 | `api/services/case_import_service.py::EventImportService`：`parse_upload`／`file_columns`／`csv_records_from_mapping`／`import_records`（落檔唯一點）／`list_imports`／`get_import`／`analyze` |
| 前端（B6） | `frontend/src/app/data-preparation/page.tsx`（批列表 `event-imports-list`）／`lib/api.ts::listEventImports` |
| 前端（B7） | `frontend/src/app/search/page.tsx`（匯出面板；`export-gap3-events`／`export-attached-h{1..12}`／`export-disclosure-*`／`export-no-ic-decay`）／`lib/eventExport.ts`／`lib/exportFilter.ts`／`lib/lookaheadDepthLock.ts`／`lib/eventContractDocs.ts` |
| **前端（B8 會碰）** | `frontend/src/components/ic-analysis/EventTablesPanel.tsx`（**兩表表頭在此**：`:67-68` macro／micro mean、`:46` `HorizonRow` 型別）；5.3 併入 `search/page.tsx` 之 `missingRows` 段（**Task 4.3 同一處**） |
| **後端（B9 會碰）** | `api/routes/ic_analysis.py`（`:34` `start_ic_analysis`＝6.1 之前置檢查落點；progress response＝6.3）；`momentum/Analysis/contracts/ic_report_contract.json`（`reasons` 現有三類＝6.0 加第四類） |
| API 模型 | `api/models/event_import_models.py`（🔴 加 response 鍵必須同步改這裡，否則被 `response_model` 靜默濾掉） |
| golden | `scripts/gap3_freeze_golden.py`（🔴 **不重凍**：它跑 IC 管線、不碰 `analyze_tables`，4.2 動不到它——實測 `--check` rc=0、`canonical_sha` 未變。定案見 `D-004` 之 **A-022**；commit message **不得**寫「已重凍」。本列原寫「4.2 會讓它合法改變，須 `_write()` 重凍」，為同型誤植，2026-08-26 由 `GROK-R1-P3-02` 抓出後更正） |
| mutation receipt | `handoffs/run_receipts/gap3ux-b{1,2,3,4,5,6,7}-all-mutations.receipt.json`（32／14／13／15／19／23／22 條）。🔴 **用前先查 `closure` 欄**（見 §6.4） |
| mutation runner 範本（**未入版控**） | 🔴 **最新＝`handoffs/gap3ux_b8_mutations.py` ＋ `gap3ux_b8_expected.json`**——它是目前**唯一同時具備三件**者：`IsolatedWorktree` 隔離、備份閘、開跑前 `unlink` receipt。⚠️ **`gap3ux_b7_mutations.py` 缺隔離**（本欄舊版曾把它標為「最新範本」而沒記這件事，B8 照抄 ⇒ 缺陷延續兩批）；`gap3ux_b{1..6}` 有隔離但無後兩者。**複製任何範本前先 `grep -c "IsolatedWorktree\|_BACKED_UP\|out_path.unlink"`，三者缺一就補。** |
| reconcile 收斂檔 | `handoffs/reconcile/20260826-gap3ux-b{6-review-r{1..6},7-review-r{1,2,3}}/synth.md`；`20260826-gap3uxtodod004-x-stamp/synth.md`（D-004 戳記，三輪） |
| 過程與教訓（給使用者） | `白話說明/GAP-3施工看板.md`（進度）、`白話說明/GAP-3施工進度.md`（歷史）、`白話說明/流程摩擦記錄.md` |
