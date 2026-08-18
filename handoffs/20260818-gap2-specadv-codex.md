# GAP-2a／2b SPEC adversarial 審查 R1（CODEX）
## CODEX-R1-P0-01
**斷言**: §G O8 與 Task 1.2-⑨ 要求的等式在 SPEC 允許的負 IC／非空條件集案例中為假，正確實作會被驗收打紅。
**碼證**: docs/GAP2_MARGINAL_IC_SPEC.md:50,85,109-110；venv/bin/python -c ... → gross_ic=-1.0 train_ic=-1.0 composite_ic=1.0；另一反例 gross_ic=1.000000000000 marginal_ic=-0.960533020035。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[BLOCKING] 修正 O8 為 sign-adjusted gross 或明確 raw gross，且將 |S|=1 改為 S=∅／附獨立條件；新增非空 S 參考 oracle。
## CODEX-R1-P1-02
**斷言**: O4 的 [0.85,1.15] 並非由所述 y=Σρ_i f_i+ε 模型保證，且 O1/O2/O4/O7 未固定可重現的係數、噪聲、label、seed 與 mask。
**碼證**: docs/GAP2_MARGINAL_IC_SPEC.md:77-84,248；允許係數 [1,.1,.1,.1]、noise=1 的獨立 Spearman probe → sum_sq_ratio=2.497437336413（非 [0.85,1.15]）。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[MAJOR] 固定完整資料生成器／seed／ρ／噪聲／label 與 mask，或把容差依限定參數推導；「seed 寫在測試」不足以使 SPEC 驗收唯一。
## CODEX-R1-P1-03
**斷言**: D3 的 no-holdout 與 full-sample fallback 在宣告的 compute_marginal_ic／_stage6b_marginal_ic 介面中沒有可傳遞的 fit_scope／root-status 來源，無法依規格同時 fail-closed 地區分 no_holdout_split 與 full_sample。
**碼證**: SPEC :107,109,179-182 的簽名無 fit_scope；實際 fallback ic_train_test_split=False 並注入 preprocessing.fit_mode=full_sample（ic_filter_orchestrator.py:1096-1101），一般 no-holdout 同樣沒有 split_context（:889-920）。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；[MAJOR] 將 root status/fit scope 變成明確 typed input 或唯一 context，並為兩條路徑各設 fail-closed oracle。
## CODEX-R1-P1-04
**斷言**: 2b survivor 契約目前不能讓消費端重建／驗證 exact event rows，且 oos_guarantees=true＋independent_oos_validation=false 仍可被既有消費語意讀成 OOS；C4 要求的 symbol/timeframe/case_id 也未落入列舉。
**碼證**: event_filter.py:66-105 只暫存 timestamps，orchestrator :2773-2776 明確 pop timestamps 只留計數；SPEC :155-158,193 只留 definition hash/counts、test index hash，且 ic_reporter.py:581-611 以 oos_guarantees 推 pass_class=oos；收斂 C4 synth.md:42-44 明列 symbol/timeframe/case_id。
**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c；momentum/Analysis/ic_filter_orchestrator.py#e4268dc1970c；docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；[MAJOR] 保存 event mask/timestamps hash（或可重建 row identity）及 symbol/timeframe/case_id；consumer validator 必須把 independent flag 與 root OOS 語意聯結，不能只驗 oos_guarantees。
## CODEX-R1-P1-05
**斷言**: B3 的「契約 SoT／批次可獨立驗收」與自身規則矛盾：Task 1.2 先用 file-local key constants，Task 3.1 又列同一欄位；且 B3 加 report_sections.marginal_ic 即會使既有 R6 sync 在 B4 前因 marginal_ic 不在 orchestrator 而失敗。
**碼證**: SPEC :68,107,110,155-158；test_ichc_contract_sync.py:59-61 對契約每個 report section 查 orchestrator，當前 rg -n marginal_ic momentum/Analysis/ic_filter_orchestrator.py ... 無輸出；SPEC :156 只預見新 reason 的紅，漏掉新 section 的同一斷言。
**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc；tests/momentum/Analysis/test_ichc_contract_sync.py#c2eb517dd24a；[MAJOR] 先定 schema 再讓 B1/B2 import，或將 B3+B4 設為同一 atomic gate；刪除 prose/temporary key duplication。
## Verdict
必答1=BLOCKING（定義方向正確但 O8/⑨ 假紅）；2=需修補（D3′ 揭露 selection=test 正確，但 root oos_guarantees 不能單獨代表獨立 OOS）；3=BLOCKING（§V 有 train/rank/sign/fail-closed mutation，但漏上述反例、ratio 公式、event identity/OOS consumer gate）；4=有 forward dependency（名義 B1→B2→B3→B4 無循環，但 file-local keys 與 B3→B4 sync 使 B3 不可獨立綠）；5=C1 D3′、C2 D1、C3 D4/D5+R2、C5 D7、C6 Task4.3/B5、C7 §G/§V 有對應，C4 有 exact-row 與 symbol/timeframe/case_id 遺漏；6=ref/additionalProperties/RowMaskPlan sync 方向可行，唯 SoT 重複與 event/OOS 欄位需修；7=白名單及 refilter/fallback/cache-hit/suppress/xsec 大致點名，B3 sync 與前端 build/type 仍不能視為已閉合；8=R1 user-ruling、R2 needs-research、R3 blocked-by #4、R4 預設納入可否決、R5 blocked-by holdout 理由成立；9=不可進 TODO，先修 P0/P1。
ASSUMPTIONS_VERIFIED: bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md → TEMPLATE PASS rc=0；O4/O8/|S|=1 獨立 probe 已實跑；stage/fallback/event/SOT/sync 證據已重查。
TESTS_RUN: venv/bin/pytest tests/momentum/Analysis/test_ichc_contract_sync.py -q → 5 passed rc=0；venv/bin/python scripts/ic_wiring_check.py → R1a(24)/R1b(16)/R2(11)/R3(5) 全綠 rc=0；數值 probe 輸出見 findings。
FAILURES_SEEN: 指定的 bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-codex.md --family codex 未進入腳本，PreToolUse 以 open_debt 阻擋；bash scripts/gate.sh dispatch 同因 rc=1（round 638a557a-f201-4c64-b5c3-3e8d60c13de8 OPEN）。
SCOPE_CHANGES: 僅新增本 review 檔；未改程式、測試、SPEC、TODO、data_cache 或根 HANDOFF。
NUMERIC_OR_SCHEMA_IMPACT: 未修改；本 review 指出 O4/O8/⑨ oracle 與 2b provenance/OOS schema 缺陷。
OUTPUT: handoffs/20260818-gap2-specadv-codex.md；/tmp workdir 清理檢查未發現可刪 matching 目錄，亦未發現 claude-501；未執行刪除。
STATUS: BLOCKED — completeness check 被現有 OPEN review round 的 PreToolUse gate 阻擋，尚無 rc=0 可確認。
