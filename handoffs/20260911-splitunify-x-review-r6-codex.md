# SPLITUNIFY SPEC 延伸 D-001 對抗審 R6（codex）
## CODEX-R6-P1-01
**斷言**: D-001-C2 要求 `row_index` 是各 symbol 的 post-trim `feature_index` 內 positional ordinal，但 Task 8.2 點名的兩個 producer 目前仍輸出全框 position；若直接按新契約投影，交錯 symbol 會把 row 對到錯時刻或越界。
**碼證**: D-001 §C2 lines 58-61、Task 8.2 lines 83-90；`contracts.py:657-661,665-677` 與 `ic_split_adapter.py:230-236` 都以 `positions[local]` 寫入 `row_index`。VERIFY: `rg -n -e 'positions\[.*train_local' -e 'positions\[.*test_local' -e 'row_index=train_rows' momentum/core/contracts.py momentum/Analysis/ic_split_adapter.py` → stdout 命中上述兩 producer；RECHECK: 交錯 A/B fixture 應同時驗證 local/global ordinal 不可混用。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73；momentum/core/contracts.py#642aecf26b32；momentum/Analysis/ic_split_adapter.py#c2dd93482826；momentum/Analysis/event_samples/split_projection.py#98ee62905643
[P1] 信心度=High。這是 producer/consumer identity contract 的實質缺口，不是單純實作偏好。修訂須明定所有 named producer 轉成 symbol-local ordinal，並同步修正 full-frame validation、holdout/既有 golden 期待；或明定唯一、可驗證的無損轉換層與其測試。否則 b8 的 per-symbol path 無法在資料交錯時同時滿足 C2 與現有 producer 語意。
## CODEX-R6-P1-02
**斷言**: 導入 D-001 新 mapping/fingerprint 入口後，現有 golden 與 wiring 綠徑不能由列出的驗證命令涵蓋：golden script 仍呼叫舊 scalar API 且建 plan 不帶 fingerprint，wiring test 仍傳舊 singular pipeline 參數且建 plan 不帶 fingerprint；這些檔案未列入 Task 8.1/8.2 的更新範圍。
**碼證**: D-001 Task 8.1 lines 68-78、Task 8.2 lines 83-97 的檔案/驗證清單未列 script、`test_splitunify_golden.py` 或 wiring test；`freeze_splitunify_golden.py:68-71,145-147,224-225,240-241` 保留舊呼叫；`test_splitunify_golden.py:40-49` 執行該 script；`test_splitunify_wiring.py:68-80` 建立無 fingerprint 的 plan 並傳 singular kwargs。VERIFY: `rg -n -e 'derive_event_split_from_plans\(' -e 'fingerprint_rows' scripts/freeze_splitunify_golden.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py momentum/Analysis/event_samples/split_projection.py` → stdout 命中 script 舊呼叫與 projection 唯一入口；RECHECK: 新簽名後應納入並執行 golden script、golden pytest、wiring pytest，且獨立 oracle 逐值比對 plan fingerprint。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-001.md#9bb033a39a73；scripts/freeze_splitunify_golden.py#6fb0c7361dad；tests/momentum/Analysis/test_splitunify_golden.py#006b7bd2d41e；tests/momentum/event_samples/test_splitunify_wiring.py#0b24aed23fe3；momentum/Analysis/event_samples/pipeline.py#55ca7327764f
[P1] 信心度=High。這會讓 b8 驗收在新 API/欄位落地時於未涵蓋的既有測試面失效，且現行獨立 oracle 只計算 fixture fingerprint，未被要求拿 producer-attested 欄位逐值對證。修訂須把上述 script/test/wiring surface 與更新後命令納入 scope，否則「pytest -k fingerprint/per_symbol」不能證明整條 frozen/golden/wiring 綠徑。
Q1（自身 R5 findings）: `CODEX-R5-P0-01` 關閉；R5 synth 判定為程序性阻塞且拒絕，理由是 Rule 12 的「動工前」限於 implementation；本輪 recheck 兩份 synth stamp 均 rc=1（缺 `## 戳記`），但不改變其 read-only review 性質。
Q2（八項實質裁決）: ①D-vs-R＝D，Task 3.2 明示改寫且未推翻既有設計；②touch set＝覆寫 C-2/Task 3.2/C-4/§N、依賴 §V/§G，C-0/C-1 no-touch，錨點格式檢查通過；③hash＝接受同 symbol train/test 相等、cross-symbol 可共享 joint hash、symbol triangle 對證；④fingerprint＝欄位/型別/empty/duplicate/NaT/normalizer 規則已寫，但 producer local identity 與可執行 oracle scope 未閉合（P1-01/02）；⑤golden＝要求改前/改後逐值重凍及獨立 oracle，但現行 script/test 未納入（P1-02）；⑥ASSERT＝多數可 falsify，惟 non-empty 不等於 digest 正確，需補逐值 oracle；⑦mutation＝M-SU-D1-01..07 已列且 D1-07 命中跨 symbol index 混用；⑧scope＝D1/R5/SU-RESID-2 排除後 single-TF 中間狀態自洽，SU-RESID-2 仍 fail-closed。
Q3（程序性 block）: Reject。AGENTS Rule 12 的精確限制詞是「動工前」；其語義是開始 implementation，不是 read-only review。R5 synth 亦記錄前三輪曾在未 stamped upstream synth 下完成審查，且 consult synth 非 frozen consensus；本輪不要求繞過 stamp，只將它作為程序證據。
Q4（C-4 wrapper）: 可接受的唯一入口是 `derive_event_split_from_plans(plans, event_keys, feature_index_by_symbol, manifest=..., bucket_ms=..., tier_min_test_events=...)`；single-symbol 舊 API 只能由薄 wrapper 包成單鍵 Mapping 後 call-through，多 symbol pipeline 直接傳 Mapping，wrapper 不得複製投影邏輯或保留第二條 scalar logic path。
Q5（是否可進 implementation）: 不可；P1-01 與 P1-02 尚未關閉，先補 producer row identity、完整驗證 surface 與 oracle 後再 proceed。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、D-001、R5/consult synth、amendment procedure；D-001 `doc_format_precheck.sh` rc=0，`template_check.sh dext` rc=0；producer/consumer 靜態證據與 pipeline 舊呼叫已核對。
TESTS_RUN: `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-001.md` rc=0；`bash scripts/template_check.sh dext docs/SPLITUNIFY_SPEC.D-001.md` rc=0；兩次 `reconcile_stamps_check.sh` rc=1（均缺 `## 戳記`，作為 Q1/Q3 證據）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-x-review-r6-codex.md --family codex` rc=0（2 個 canonical ID）。
FAILURES_SEEN: 上游 R5/consult stamp checker 均報缺 `## 戳記`；未執行 full pytest/governance，未修改測試斷言。
SCOPE_CHANGES: none；未改 tracked code/data，產出檔=`handoffs/20260911-splitunify-x-review-r6-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無數值、schema、golden 或輸出檔變更；僅指出 D-001 新增 `row_time_fingerprint` 的落地與 refreeze 風險。
VERDICT: blocked
BLOCKED-BY: CODEX-R6-P1-01,CODEX-R6-P1-02
CLOSED: CODEX-R5-P0-01
STATUS: DONE
