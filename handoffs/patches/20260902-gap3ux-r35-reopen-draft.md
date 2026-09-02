# PATCH cluster gap3ux-r35-reopen-draft
AUTHORITY: docs/GAP3_EVENT_UX_SPEC.md §D **D-8**（R 重開裁定本體；使用者 2026-09-02 原話）＋ 檔頭「D-001…D-005 逐節落點表」；程序權威＝docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md §2.1
family: claude
round: R35
target: docs/GAP3_EVENT_UX_SPEC.md、docs/GAP3_EVENT_UX_TODO.md、docs/GAP3_EVENT_UX_TODO.D-001.md…D-005.md（主委落地之 R 重開修訂稿；本包供 patch_locus_check 對證，非委員補丁）
SYNC-LOCI:
- docs/GAP3_EVENT_UX_SPEC.md#R 重開
- docs/GAP3_EVENT_UX_SPEC.md#逐節落點表
- docs/GAP3_EVENT_UX_SPEC.md#A-1′
- docs/GAP3_EVENT_UX_SPEC.md#D-8
- docs/GAP3_EVENT_UX_SPEC.md#declared_window_bars[tf]
- docs/GAP3_EVENT_UX_SPEC.md#Task 1.9′
- docs/GAP3_EVENT_UX_SPEC.md#withExportDeclarationGuard
- docs/GAP3_EVENT_UX_SPEC.md#⛔ RETIRED
- docs/GAP3_EVENT_UX_SPEC.md#宣告 validator 一致性
- docs/GAP3_EVENT_UX_SPEC.md#V-12
- docs/GAP3_EVENT_UX_TODO.md#R 重開
- docs/GAP3_EVENT_UX_TODO.md#Task 1.9′
- docs/GAP3_EVENT_UX_TODO.md#⛔ RETIRED
- docs/GAP3_EVENT_UX_TODO.md#depth_by_timeframe
- docs/GAP3_EVENT_UX_TODO.D-001.md#SUPERSEDED-BY-R
- docs/GAP3_EVENT_UX_TODO.D-002.md#SUPERSEDED-BY-R
- docs/GAP3_EVENT_UX_TODO.D-003.md#SUPERSEDED-BY-R
- docs/GAP3_EVENT_UX_TODO.D-004.md#SUPERSEDED-BY-R
- docs/GAP3_EVENT_UX_TODO.D-005.md#SUPERSEDED-BY-R
BEFORE/AFTER: 見 `git diff 003d4846..HEAD -- docs/GAP3_EVENT_UX_SPEC.md docs/GAP3_EVENT_UX_TODO.md docs/GAP3_EVENT_UX_TODO.D-00*.md`（就地修訂，非替換片段；摘要如下）
- SPEC 檔頭：新增「R 重開」blockquote（為何是 R／效力／六項變更／D-001…D-005 逐節落點表）；版本行保留 `R34-landing` 收據形式並註明 R35-R 疊加
- SPEC §A：`A-1` ⛔ 作廢、新增 `A-1′`（使用者原話）
- SPEC §D：新增 `D-8`；§D-3′-a 六處「Task 2.1b」引用改寫為宣告來源（公式本體不動）
- SPEC Phase 2：⛔ RETIRED（附退役／保留清單；`depth_by_timeframe()` 本體保留為匯入端投影）；新增 Task 1.9′；Task 1.9／1.10／1.11／4.1③④／4.1b／7.3／§V V-12 同步
- TODO：檔頭 R 區塊；§B B3／B5／B7／`depth_by_timeframe` 列；Task 1.9／1.10／1.11／4.1／4.1b／7.3；Phase 2 ⛔ RETIRED；新增 Task 1.9′
- D-001…D-005：檔頭 `SUPERSEDED-BY-R` 與逐條處置
VERIFY:
- bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_SPEC.md
- bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.md
- bash scripts/spec_ruling_task_sync.sh docs/GAP3_EVENT_UX_SPEC.md
- python3 scripts/patch_locus_check.py handoffs/patches/20260902-gap3ux-r35-reopen-draft.md --diff-base 003d4846
- grep -nE "2\.1b|匯出前篩選|引用之欄位清單" docs/GAP3_EVENT_UX_SPEC.md docs/GAP3_EVENT_UX_TODO.md | grep -vE "RETIRED|退役|R 重開|D-8|~~|歷史|原"
