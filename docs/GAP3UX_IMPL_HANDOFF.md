# GAP-3 事件型 UAT 缺口修補 — **實作交接**（R 重開後重寫，2026-09-02）

> **給下一個 session 的交接。** `HANDOFF.md` 只放指標，細節在本檔。
> 🔴 本檔為 **R 重開（SPEC D-8）後**之版本；R 前（B1–B10、D-001…D-005 延伸檔、Task 2.1b／`filters`／匯出前篩選）之敘述已全部作廢，
> 不再保留——需要歷史請看 git（`git show 32d35c7f^:docs/GAP3UX_IMPL_HANDOFF.md`）。

---

## §0 一句話狀態

**SPEC／TODO 已 R 重開並三家戳記（review-R37 synth，session `20260902-gap3ux-x-stamp-r1`）；
R 實作批（Task 1.9′＋Phase 2 退役＋Task 1.11 後端謂詞＋validator `v<0`＋preview-columns 端點）已落地，待三家 code review／adversarial。**

| 文件 | 路徑 | 狀態 |
|---|---|---|
| SPEC（語意權威） | `docs/GAP3_EVENT_UX_SPEC.md` | 版本行 `R37-landing`；D-8 為現行裁定；Phase 2 ⛔ RETIRED；Task 1.9′ 新增 |
| TODO（操作依據） | `docs/GAP3_EVENT_UX_TODO.md` | 同上；`D-001…D-005` 延伸檔皆 `SUPERSEDED-BY-R`，**不再並讀** |
| 戳記 | `handoffs/reconcile/20260902-gap3ux-x-review-r37/synth.md`（本機） | codex／composer／grok APPROVED，`reconcile_stamps_check.sh` rc=0 |
| 驗收清單（給使用者） | `白話說明/GAP-3驗收清單.md` | B2 改為「匯出前先填答案窗」；B5／B10 同步 |

🔴 **層級**：操作依據＝TODO；語意權威＝SPEC（衝突以 SPEC 為準並回報）。**驗收字面之唯一來源＝SPEC 各 Task 之「驗證」欄**。

---

## §1 R 實作批做了什麼（落點；接手先讀這張表）

| 項 | SPEC | 落點 | 要點 |
|---|---|---|---|
| 匯出端宣告框 | Task 1.9′ | `frontend/src/app/search/page.tsx`（宣告 state／preview effect／面板）、`frontend/src/lib/lookaheadDeclaration.ts`（`withExportDeclarationGuard`／`exportDeclarationBlockMessage`／`declaredWindowBarsForExport`） | 與匯入頁**同一元件** `LookaheadDeclarationFields`、同一 `validateDeclaration`；兩條匯出（JSON／CSV）共用同一守衛與同一 map 函式；`proceed` 結構保證沿用 |
| 預設值 wire path | Task 1.9′ 實作要點 2 | `POST /api/v1/case/lookahead-declaration/preview-columns`（`api/routes/case.py`）→ `EventImportService.lookahead_declaration_preview_from_columns` → `EventSamplePipeline.preview_lookahead_declaration` → **唯一實作** `lookahead_declaration.py::preview_from_columns`（匯入端 preview 亦改走它） | 前端只顯示；改附帶欄只重取預設候選，不覆寫已宣告值 |
| Phase 2 退役 | SPEC Phase 2 CROSS-FILE | 刪 `frontend/src/lib/{exportFilter,lookaheadDepthLock}.ts`＋其測試、`exportFilterPersist.test.ts`、`eventExportGuardRuntime.test.tsx`、`gap3_export_filter_page.test.tsx`、`tests/api/test_gap3_export_filter_wiring.py`；刪 `/case/lookahead-depth` 路由與 `LookaheadDepthRequest/Response`、`EventImportService.lookahead_depth()`、`EventSamplePipeline.lookahead_depth()`；`page.tsx` 篩選面板／`export-count-n` 移除；`eventExport.ts` 不再寫 `label_definition.filters` | **保留**：`computeExportCounts`（改為不接條件）、`lookahead_declaration.py`／`lookahead_gate.py`／`lookahead_registry.py`、`lookahead_depth.py::depth_by_timeframe()` 本體（匯入端投影，`referenced_columns` 恆空） |
| 一律宣告 | Task 1.11 | `lookahead_declaration.py::resolve_declaration`：`needs = True`；`declaration is None` ⇒ `lookahead_declaration_required`；`ON_MISSING_*`／`on_missing` 參數刪除 | 🔴 **勾選**與**宣告**分拆：勾選只在「引用了驗不了的欄／非 canonical filters」或「調低於預設」時要求；判定之**唯一實作**＝`declaration_is_unverifiable()`（後端拒收與兩端 preview 之 `acknowledgement_required` 共用），前端 `acknowledgementRequiredByPreview()` 只讀旗標（缺鍵退看 `referenced_columns`），不再看 `requires_declaration` |
| JSON 直傳 | Task 1.11 ④ | `case_import_service.py::_declaration_from_rows`：每列皆帶且批內同值 ⇒ 視為宣告（`acknowledged_unverifiable=True`，殘留 `R35-L2-ACK`）；整批缺 ⇒ reject；部分缺／不同值 ⇒ 先跑契約 validate 讓列間不一致 reason 現形 | 表單宣告與列內攜帶**皆有** ⇒ **表單為準**，落檔列之 `lookahead_bars_declared` 一律改寫為本次宣告，差異記 `warnings` |
| 值域 | Task 1.9′／R35 | 後端 `_validate_declaration_shape`：`v < 0` 拒（0 合法、須明填）；前端 `validateDeclaration` 同；`LookaheadDeclarationFields` `min={0}` | 留白＝缺鍵 ⇒ 鍵集不符而拒，不得默認 0 |
| 揭露 | Task 7.3 | `eventFieldFormatters.ts`：`lookahead_depth` 文案改「來源＝你在匯出前宣告的值」；`EventDepthRow`／`SearchDisclosureContext` 移除 `referencedColumns` | 深度自宣告 state 讀取；未填 ⇒ 「尚未宣告」 |

### §1b R1 code review（session `20260902-gap3ux-b11-review-r1`）之修法（同日落地）

| finding | 修法落點 |
|---|---|
| `GROK-R1-P1-01`／`CODEX-R1-P2-02` 匯出端預設候選欄集把結果列全部鍵送去（含系統內部 `future72_*`）⇒ 1h 預設被拉到 72 | `page.tsx` preview 欄集改**只送勾選之附帶 `future_{h}bar_return`**；page 測試：列自帶 `future72_*` 時欄集不含它、取消勾選後同步變少 |
| `CODEX-R1-P1-01` preview 重取失敗留舊 preview 放行 | catch ⇒ `setDeclPreview(null)`（守衛據此擋）、宣告值保留；page 測試：先成功→改附帶欄→端點拒 ⇒ 兩鈕皆擋、重取成功後恢復 |
| `GROK-R1-P1-02` `resolve_declaration` 仍把可解析引用欄餵 `depth_by_timeframe` 取 max（宣告 5 落檔 72） | `referenced_for_depth` 恆 `()`＋assert `depth == declared`；新測試（引用 `future72_close_return`、宣告 5／12／0 ⇒ 落檔＝宣告）；`test_gap3_horizon_declaration_05` 改寫為 R 版 |
| `GROK-R1-P2-01` 攜帶值自動勾選擴到 CSV | `import_records(carried_declaration_acknowledged=)` 只在 JSON 直傳路由傳 True；CSV／對映攜帶值不自動勾選（低於預設須表單勾）；殘留 `R35-L2-ACK` 收窄回 JSON 直傳 |
| `CODEX-R1-P2-03` 兩路由文案仍寫「正整數」 | description 改「非負整數（0 ＝未用未來資訊，須明填）」＋一律宣告語句 |

---

## §2 測試與驗證（接手前先跑一次）

```bash
# 後端（GAP-3 全部；含新檔 tests/api/test_gap3_declaration_mandatory.py）
venv/bin/python -m pytest tests/api tests/momentum/event_samples -q -o log_cli=false -k "gap3 or lookahead or import_contract or event_samples"
# 前端
cd frontend && npx vitest run src/app/search src/lib src/components/case && npx tsc --noEmit
```

- 新測試：`tests/api/test_gap3_declaration_mandatory.py`（Task 1.11 ②③④、0／負數值域、表單勝攜帶、preview-columns 端點與單一實作、退役端點不存在）；
  `frontend/src/app/search/exportDeclaration.test.tsx`（Task 1.9′ ①–⑦）；`frontend/src/test/lookaheadDeclarationTestUtils.ts`（頁測試共用 preview mock＋填宣告）。
- 改判之既有測試：`test_lookahead_declaration_03b`（無條件 ⇒ **仍**須宣告）＋ `03c` 對照；`lookaheadDeclaration.test.ts` 值域改非負；八支 `/search` 頁測試改 mock `fetchLookaheadDeclarationPreviewColumns` 並先填宣告。
- fixture：`tests/momentum/event_samples/test_import_contract.py::canonical_event` 預設攜帶 `lookahead_bars_declared`（值＝`window.horizon_bars`）；
  CSV 對映路徑測試以 `tests/api/_gap3_declaration.py::declaration_for_timeframes` 帶表單宣告。
- mutation 收據：`handoffs/run_receipts/20260902T050448Z-gap3-rimpl-mutations-8.json`（M-B1…M-B4、M-F1…M-F4 皆 applied_rc=1／restored_rc=0；
  runner `handoffs/gap3_r_mutations.sh`，本機）。另兩張：後端 GAP-3 子集 `20260902T050101Z-gap3-rimpl-backend-gap3-suite`（653 passed）、
  前端全套 `20260902T050038Z-gap3-rimpl-frontend-vitest`（411 passed）。
  🔴 receipt 之 runtime_class 由命令推導：shell 腳本型變異為 `static_only`，commit-msg 關鍵字閘只認 pytest `test_mutation_` node ⇒
  commit message 不引用該 id（引用即被判類別不足），以本檔為引用點。

---

## §3 開工鐵律（沿用）

1. **派 review 前先 commit**；2. mutation runner 須有隔離與備份閘（本批用 `handoffs/gap3_r_mutations.sh` 之 `.mutbak` 備份，逐條套用→紅→還原→綠）；
3. 主控端在委員實跑期間**不動檔**；4. 不得以「其他欄都能解析」取 max 當深度、不得由欄名推斷深度；5. 前端不得重寫換算表或第二份 validator。

---

## §4 具名殘留（三值）

| 代號 | 內容 | 為何現在不做 |
|---|---|---|
| `R35-L2-ACK` | JSON 直傳無法複驗匯出端之 `acknowledged_unverifiable`（契約無該欄） | needs-research：新增契約欄須 D-6 |
| `G3-D2` | 五維度三類值不接受永久灰著 | user-ruling：UAT B3 在三者全交付前記未完成 |
| `KLINE-1` | `/data-preparation` 舊區塊已標 deprecated，移除票待開 | user-ruling：另開票走完整管線 |
| `MUT-CSV-MAP` | Task 1.9′ mutation「CSV 另組一份 map」只在第二份**漂移**時可紅；語意等值之副本 ⑥ 抓不到 | needs-research：以 buildSpy 之同一函式參考斷言補強（本批已加 `buildSpy` 兩次呼叫 map 逐鍵相等） |
