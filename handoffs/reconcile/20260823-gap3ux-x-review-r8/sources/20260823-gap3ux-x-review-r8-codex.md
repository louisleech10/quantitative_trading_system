# GAP-3 事件型 UAT 缺口修補 SPEC — R8 CODEX review

## Verdict：需修訂後定版

議題一的產品分層方向成立：事件批次是 t0 事實，答案窗可屬 IC 分析參數；但現行 SPEC 與 code 沒有把它接成可執行、可驗證的分析時計算路徑。故本輪有 P0，不能 FROZEN。

## CODEX-R8-P0-01

**斷言**: 把答案窗移出 `/search` 後，現行契約與 IC 分析呼叫鏈沒有分析時計算 `label_value` 的端到端 producer；新批次會落入 `missing_label_value`，而不是在 IC 頁依條件／答案窗重算。

**碼證**: `frontend/src/lib/eventExport.ts:81-105` 仍在匯出時讀 `future_${horizon}bar_return` 並寫 `label_value`；`EventImportPicker.tsx:45-52` 只回傳 import ID＋t0 timestamps；`useICAnalysis.ts:269-287` 只送 `event_timestamps`；`api/services/ic_analysis_service.py:229-238` 只傳 `event_timestamps`，`rg -n 'build_event_ic_inputs' api/services api/routes` 無 service caller；`ic_feed.py:44-46` 對缺值直接回 `unavailable:missing_label_value`；`import_contract.py:152-168` 仍要求 `label_definition.window.horizon_bars`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; frontend/src/lib/eventExport.ts#b2024ac8970f; frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456; frontend/src/hooks/useICAnalysis.ts#e05507ee38ed; api/services/ic_analysis_service.py#c3459aa2e6a6; momentum/Analysis/event_samples/ic_feed.py#5710f3436654; momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e

[BLOCKING] 信心度=High。R8 的方向不是被碼證推翻，而是尚未成為閉合架構：IC 頁現有 `horizons` 是報告 horizon 集合，`event_query` 也只是 feature filter，不是 label condition。須明訂事件事實層、分析 label spec、批次契約版本／legacy 行為、IC request/response、後端 bars producer、`ic_feed` 呼叫點與 provenance；不得只把 Task 7.0b 的 `/search` cases API 改名。

## CODEX-R8-P0-02

**斷言**: 即使新增分析時計算 label，現行 IC split/purge 仍在事件 label 注入前依 labels/default horizon 建立；IC 頁選較長答案窗時可能 purge 小於實際 label window，違反 §C0 的 leakage gate。

**碼證**: `api/models/ic_models.py:133-165` 沒有 analysis-time label/horizon 欄位；`ic_filter_orchestrator.py:920-949` 先以 `_resolve_effective_label_horizon(config, labels_df)` 建 holdout split；`ic_filter_orchestrator.py:2728-2774` 無 labels 時從 config default 產生 `return_{horizon}`；`ic_filter_orchestrator.py:360-378` 以該 horizon 建 purge；`EventAnalyzeRequest.horizons` (`api/models/event_import_models.py:83-91`) 只控制事件報酬表，不是 IC label window。RECHECK：上述 `nl -ba` 命令可重跑。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; api/models/ic_models.py#fbc974fb7fa4; api/models/event_import_models.py#919507b8ad19; momentum/Analysis/ic_filter_orchestrator.py#935fb860c6b1; momentum/Analysis/event_samples/pipeline.py#db3d29667082

[BLOCKING] 信心度=High。h=7 若仍依 labels/default h=1 或 h=5 建 split，train 尾端答案窗可跨入 test；這是數值正確性缺口，不可列殘留。修法須讓本次 `event_label_spec.horizon_bars` 在 split 建立前成為唯一 purge 下界，並以 h=1/7、尾端不足、真實 kline golden＋mutation 驗證「改 h 但不改 purge」必紅。

## CODEX-R8-P0-03

**斷言**: `decision_offset_bars > 0` 時，IC picker 目前把 t0 當成 feature timestamp，沒有映射到 `decision_at`／`last_bar_open_ms`；因此特徵截止與事件 label 對不到同一決策時點。

**碼證**: `frontend/src/lib/api.ts:1042-1048` 的 `eventT0MsToIcTimestamps` 直接取每列 `t0/1000`；`EventImportPicker.tsx:51-52` 將該結果送給 `onPick`；`ic_feed.py:51-58` 的合法事件 label map key 卻來自 receipt `last_bar_open_ms`；`ic_filter_orchestrator.py:2895-2904` 以 feature index 的 epoch ms 查該 map；SPEC Task 7.7 雖要求 `max_close_ms <= decision_at`，Task 7.6 只要求揭露五維度，沒有這條實際 picker→analyze wiring。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5; frontend/src/lib/api.ts#a70a519560b7; frontend/src/components/ic-analysis/EventImportPicker.tsx#1cb1e1562456; momentum/Analysis/event_samples/ic_feed.py#5710f3436654; momentum/Analysis/ic_filter_orchestrator.py#935fb860c6b1

[BLOCKING] 信心度=High。Task 7.2 明確允許輸入非零 k，不能以目前 default 0 當作安全假設。修法須由後端 receipt 產生 per-event decision timestamp／feature row mapping，前端不可自行由 t0 推導；k=3、混 TF、重複 feature row 與未知 TF 均需 fail-closed receipt。

## CODEX-R8-P1-04

**斷言**: A-6 不能因議題一而默認作廢；現行 §A、Phase 4、V-6 仍把舊的「主答案窗在匯出層」當權威，卻沒有新的使用者白話閘或取代裁定。

**碼證**: SPEC `:241-258` 將 A-6 定義為附帶 horizon 不改 `label_value` 且確認前不得 FROZEN；`:841-850` 的 Task 4.1 驗收 `window.horizon_bars==4` 且 `label_value==future_4bar_return`；`:1541` 的 V-6 重述同一行為。R8 brief 要求回答 A-6 是否作廢，但沒有 user-visible confirmation receipt。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#01cf2468573ff5

[MAJOR] 信心度=High。正確處置是「舊 A-6（D-3(a)）作廢，新增 A-6′：分析時計算之答案窗／label_value，仍待使用者白話確認」，並同步 §A、檔頭 FROZEN 句、D-3/D-7、Task 4.1/4.1b/4.1c、Task 7.0b/7.4/7.6、V-6 與白話勾選表；未確認前不能宣稱架構已接受。

## CODEX-R8-P1-05

**斷言**: R8 facts receipt 與派審前入口目前能把失敗機械閘報成成功：F-14 用最後一個 `echo` 蓋掉 count-audit rc，且 `gap3ux_pre_review.sh` 仍掃 R7 facts，不掃 R8 facts。

**碼證**: `python3 scripts/spec_count_audit.py --check docs/GAP3_EVENT_UX_SPEC.md handoffs/20260823-gap3ux-x-review-r8-facts.sh --baseline handoffs/run_receipts/gap3ux-spec-count-baseline.txt` → `COUNT_DIRECT_RC=2`（R8 字面未進 baseline）；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` → F-14 `count_audit=2` 但 `FACTS_WRAPPER_RC=0`；`bash scripts/gap3ux_pre_review.sh` → `PRE_REVIEW_RC=0`；`scripts/gap3ux_pre_review.sh:20` 仍為 `FACTS=...review-r7-facts.sh`。

**來源摘要**: handoffs/20260823-gap3ux-x-review-r8-facts.sh#a3d9fdfb26af; scripts/gap3ux_pre_review.sh#e489b7908fdb; scripts/spec_count_audit.py#27b09e0ffb52; handoffs/run_receipts/gap3ux-spec-count-baseline.txt#4fa233d48b9a

[MAJOR] 信心度=High。這直接使 brief 的「fact 全可重跑」與 FROZEN 六閘條件不可信。修法：F-14 以 fail-propagating compound command 執行五閘、pre-review 改用 R8 facts、重產 baseline，再以直接命令和 wrapper rc 同時驗證；不得只看最後 echo。

## CODEX-R8-P1-06

**斷言**: `patch_locus_check.py` 的實作只以 dirty worktree 的檔名集合判定 locus，且沒有檢查 anchor 或 diff hunk；同檔無關修改／既有 dirty 檔即可被誤算為補丁已套用。

**碼證**: `scripts/patch_locus_check.py:87-111` 以 `git diff --name-only` 加 `git status --porcelain -uall` 建 `changed_files`；`:144-155` 只檢查 `f in touched`，讀到的 `anchor` 未參與判定。當前 `git status --porcelain -uall` 已有既存 `.claude/gate/audit.log`、`.probe_ic*.sh` 與 receipt 檔，證明工作樹並非本補丁專屬。

**來源摘要**: scripts/patch_locus_check.py#010a10e9e16d; docs/GAP3_EVENT_UX_ROLE_CARD.md#（角色卡文件未變更；其誠實邊界與本碼證對照）

[MAJOR] 信心度=High。這會錯誤歸責「已列 locus 而主委未改齊」與「補丁已套用」，正好繞過 R3 新流程的目的。修法須以指定 base/snapshot 的實際 diff hunk 驗 anchor，並加同檔無關行、既存 dirty 檔、缺 anchor 三個反測；檔名集合只能作輔助，不得作通過條件。

### R7 十二條修訂複審

R7 群集 A、B、C、D、F、G：CLOSED（現行 SPEC 已含五閘 receipt、§F-2 純引用、Task 7.7 epoch 秒格式、`control_kind`、registry 內容正確性、§G S-9 浮點/跨環境 digest）；群集 E：R7 原 finding 的 `/case/label-values` API 形狀已補入 SPEC，**但在 R8 新架構下重新 OPEN 為 IC service wiring 缺口**，已由 P0-01 覆蓋。未把 R7 已修正文字重複計為 finding。

### 全棧三欄與必查類別

後端 code：P0-01/P0-02；前端 UI：P0-01/P1-04；wiring：P0-01/P0-03。矛盾/漏項/不可測：P0-01、P1-04；quant/PIT/leakage：P0-02/P0-03；API/型別/相容：P0-01；測試 golden：P0-02/P0-03；cache/OOM/過度工程/必要性短命工：本輪無新增 finding。C0 已讀且未主張放寬；但新架構的分析 label golden 尚未存在，不能以既有事件 G-2 代替。

### 被當成事實的未驗證假設（§0）

- 「把答案窗移到 IC 頁後，既有 `decision_time_rule`／`feature_cutoff_rule` 自動足以保證 PIT」：未驗證；split horizon 與 decision timestamp wiring 尚未接通。
- 「A-6 隨架構調整自然作廢」：未經使用者白話確認；只能提出 A-6′ 取代裁定。
- 「R8 六閘已全綠」：被直接 count-audit rc=2 與 F-14 wrapper 假綠反駁。
- 「patch locus 已由檔名集合充分封閉」：與腳本未使用 anchor/diff hunk 的實作不符。

ASSUMPTIONS_VERIFIED: 標的 sha256=01cf2468573ff5、1580 行；R8 facts 14 條命令輸出可重跑但 F-14 compound masks count-audit；IC service/前端/`ic_feed` 呼叫鏈以 `rg`/`nl` 逐項核對；R7 A-G 修訂文字逐項抽驗。
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md; wc -l docs/GAP3_EVENT_UX_SPEC.md` → sha/1580；`bash handoffs/20260823-gap3ux-x-review-r8-facts.sh` → wrapper rc=0 但 F-14 count_audit=2；直接 `spec_count_audit.py --check ...r8-facts.sh` → rc=2；`bash scripts/gap3ux_pre_review.sh` → rc=0；未修改 code/SPEC，未跑完整 pytest。
FAILURES_SEEN: R8 F-14 direct count-audit rc=2 被 facts wrapper 遮蔽；此為 finding，未自行修改。
SCOPE_CHANGES: none；只新增本輪 review 與補丁包，未改 code、SPEC、data_cache、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值/schema；指出分析 label producer、purge、timestamp mapping 與契約分層之待修影響。
HANDOFF_OUTPUT: handoffs/20260823-gap3ux-x-review-r8-codex.md
PATCH_OUTPUTS: handoffs/patches/20260823-gap3ux-r8-codex-analysis-label.md; handoffs/patches/20260823-gap3ux-r8-codex-pit-wiring.md; handoffs/patches/20260823-gap3ux-r8-codex-gate-locus.md
STATUS: DONE
