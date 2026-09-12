# SPLITUNIFY-B9 REVIEW R9 — CODEX

task-id: `20260911-SPLITUNIFY-B9-REVIEW-R9`；審查為唯讀，未修改 SPEC、TODO、程式碼或 data_cache。

R8 關閉重驗：`CODEX-R8-P1-01` 未閉合，以下以 `CODEX-R9-P1-02` 重開；`CODEX-R8-P1-02` 未閉合，以下以 `CODEX-R9-P1-01` 重開。`CODEX-R8-P1-03` 的「五處 exact-key 同步面已列出」原宣稱已閉合，但實際 producer→metadata 資料流另成 `CODEX-R9-P1-06`；`CODEX-R8-P1-04` 的「界外先置前置條件」已列入 §9.2b，但其餘 split pair 完整性另成 `CODEX-R9-P1-08`。

## CODEX-R9-P1-01
**斷言**：Task 9.1 的目標仍要求「必須讓終端使用者看得到」，同一份 SPEC 卻把 API/前端可見性列為 `SU-RESID-9A-UI`、明載本延伸交付後使用者仍看不到；這使「9A 已消除誠實性缺陷」與「只做到 producer」兩種驗收解讀同時存在。失敗面是完成判定可在未達終端目標時被宣稱通過。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '136,150p;262,270p'` 顯示 L137 的終端目標、L142/L147/L150 的 producer-only/殘留決策與 L267 的不可見誠實邊界；`rg -n 'EventSamplePipeline|EventSamplePipeline\(\)|\.run\(' api --glob '*.py'` 未找到投影路徑之生產 `EventSamplePipeline.run` 呼叫點。修復：將 Task 9.1 目標改成「producer 層完整記帳」，並明確指向 `SU-RESID-9A-UI`，待投影生產接線後再驗終端可見性；這不會偽造 API 完成。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/pipeline.py#55ca7327764f`

## CODEX-R9-P1-02
**斷言**：G-4c 的「同步逐行重寫獨立 oracle」不是足以區分換錨改側與兩份共同錯誤的機械閘。具體反例：`index=[100,200,300,400]`、`train_last_ms=200`、`test_start_ms=300`、`decision_at_ms=250`、`feature_cutoff_ms=200`；正確 decision-anchor 結果是 `purged`，若被測投影與 oracle 都誤用 cutoff，兩者都得 `train`，G-3b 仍相等而綠燈。
**碼證**：`nl -ba scripts/freeze_splitunify_golden.py | sed -n '132,155p;340,352p'` 顯示 `_oracle_membership` 目前逐列以 `feature_cutoff_ms` 判側，`main()` 只比較 `g1_membership == g3b_oracle`；同檔 `:112-123` 又把 fixture 的 `decision_at_ms` 直接設成 cutoff，現有資料沒有暴露反例。修復：保留不 import 投影的 oracle，但在 fixture 明列 decision/cutoff 與預期 side，至少加入上述 gap 反例及事件級 expected-membership 斷言；再以 G-3b 做第二份推導對證。可行性證據：現有 `_build_actual()`/`main()` 已是單一擴充入口，無需新增 allowlist 檔。信心：高。
**來源摘要**: `scripts/freeze_splitunify_golden.py#e331623163d2`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-03
**斷言**：G-4d 的三個硬條件只寫在 §G，未成為 §V 的可執行驗收或 mutation：保留 v8 baseline、不覆寫、`decision==cutoff` 零位移、`decision!=cutoff` 單 TF 邊界 fixture。現有 golden 命令雖通過，不能證明這三件事；重凍或 fixture 維持等值都可能把缺口遮住。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '124,130p;216,226p;227,256p'` 顯示 G-4d 在 L129，但 §V 只有多 TF 反例與舊值斷言，mutation 表沒有 G-4d 專屬項；`nl -ba scripts/freeze_splitunify_golden.py | sed -n '112,123p;346,352p;373,377p'` 顯示 fixture 令 decision 等於 cutoff，且 `--write` 可直接寫 golden。實跑 `venv/bin/python scripts/freeze_splitunify_golden.py` rc=0 僅輸出 G-3b/G-5/golden OK。修復：新增命名的 G-4d test/mutation，保留不可覆寫的 v8 鍵、對等值事件做零位移斷言、對非等值事件做單 TF 邊界 expected-side 斷言；讓 `--write` 另寫新鍵。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `scripts/freeze_splitunify_golden.py#e331623163d2`

## CODEX-R9-P1-04
**斷言**：K3 對「`blocked-by` 必須是票號」的反駁方向正確，但採用的權威文件錯了，且 §N 殘留缺少模板要求的 literal `為何現在不做:` 欄；因此目前不能宣稱 `SU-RESID-9A-UI` 治理格式合規。BRIEF 的四值 `reason_code` 是「我沒查的」表格欄，不是 SPEC §N 殘留欄位。
**碼證**：`nl -ba templates/BRIEF_REVIEW_TEMPLATE.md | sed -n '62,72p;167,174p'` 顯示四值只屬 brief 表；`nl -ba templates/SPEC_TEMPLATE.md | sed -n '107,113p'` 與 `nl -ba templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md | sed -n '47,50p'` 明定 §N 必須寫 `為何現在不做:`，且只允許 `blocked-by:<具體依賴（檔/層/前置票）>`、`user-ruling:`、`needs-research:`。`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '262,270p'` 顯示 L267 只有裸 `blocked-by`。修復：保留「不必是票號」的結論，但改引 SPEC_TEMPLATE，並寫成 `為何現在不做: blocked-by:投影路徑無 EventSamplePipeline.run 生產接線（api/呼叫點=0）`，同時補權威登記處與觸發條件。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `templates/BRIEF_REVIEW_TEMPLATE.md#82dfcbd10f3`; `templates/SPEC_TEMPLATE.md#0b2f68f0c38a`; `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa`

## CODEX-R9-P1-05
**斷言**：K4 的「成本過高時只交前兩層」仍是未裁決的二選一，與同一段已指定 `metadata.split_unify` 欄位、§V 三層斷言、`M-SU-D2-03` 應紅測試互相衝突；實作者可合法選擇兩層或三層，造成半套契約或驗收分叉。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '148,151p;218,225p;231,234p'` 同時顯示三層交付、metadata 斷言與「成本高則前兩層」條件。修復選擇：現在鎖定三層（producer 回傳、`EventSplitPlan.summary`、`metadata.split_unify`），刪除成本條件；理由是 SPEC 已列出 exact-key 契約、欄位型別與既有 mutation/測試落點，縮成兩層反而要同步改寫 §V、mutation、殘留和契約。可行性證據：現有 metadata 只有一個 builder/caller，可在一個資料流內定義 handoff（詳 `CODEX-R9-P1-06`），不需要新增 API。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/split_projection.py#99bfddace904`

## CODEX-R9-P1-06
**斷言**：三層方案沒有定義 producer 的 `discarded` 如何到達實際 `metadata.split_unify`；目前 metadata 產生器只接受 `n_test`/timestamps/counts/reason，唯一現行 caller 也沒有 `EventSplitPlan` 或 `discarded`。因此可寫一個孤立的欄位單測並通過，卻仍讓真實 producer 計數在 metadata 邊界遺失。
**碼證**：`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '123,181p'` 顯示 `build_split_unify_disclosure` signature 無 `discarded` 且固定回五鍵；`nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '1525,1534p'` 顯示唯一 caller 只傳 `n_test`、timestamps、per-symbol counts；`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '138,149p;218,219p'` 卻要求 summary 值再進 metadata。修復：在鎖定三層後指定一個 producer-result/context handoff，讓同一個 `discarded_rows_by_feature_tf` 明確流入 metadata，並以 producer→summary→metadata 整鏈測試驗值與 exact-key；或若架構不能接，收回三層承諾而不是留孤立欄位。可行性證據：`rg` 已盤定唯一 builder caller，變更面是封閉的。信心：高。
**來源摘要**: `momentum/Analysis/event_samples/split_projection.py#99bfddace904`; `momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-07
**斷言**：C6 的「事件級物化前提下 baseline 的 `n_test` 等於樣本數也等於事件數」不是一般不變式；物化允許事件進 failure table 而不進 features，baseline 又只對 features index 與 test IDs 取交集，故一個 assigned test event 可能使 baseline `n_test` 少一個。
**碼證**：`nl -ba momentum/Analysis/event_samples/feature_materialization.py | sed -n '100,140p'` 顯示 warmup/非有限值會寫入 `failures`、不寫 `features`，但只保證 input = features + failures；`nl -ba momentum/Analysis/event_samples/baseline.py | sed -n '105,121p'` 顯示 `idx = features_at_decision.index.intersection(test_ids)` 後以 `len(idx)` 寫 `n_test`。這直接構成反例：test assignment 有 `e1`，materialization failure 也有 `e1`，features 無 `e1`，baseline `n_test=0` 而 test event count=1。修復：明定 baseline 同時輸出 `n_test_events=unique(test_ids)` 與 `n_test_samples=len(idx)`，或在 baseline 前要求完整物化並對缺失事件 fail-closed；補一個 failure fixture，不能靠「事件級」語意推導兩數永遠相等。信心：高。
**來源摘要**: `momentum/Analysis/event_samples/feature_materialization.py#3403d81fa8f2`; `momentum/Analysis/event_samples/baseline.py#38c7ec473653`; `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`

## CODEX-R9-P1-08
**斷言**：R8 新增的 Step 0 只處理 `decision_at_ms` 在 feature index 首尾之外；它沒有使 train/test plans 本身互斥、有序且非空，因此「三段規則互斥且窮盡」仍未成立。若 `train_last_ms == test_start_ms`，decision 同時命中 train 與 test；若 train 為空，SPEC 要求取 `train_rows[-1]` 而現行程式明許極端切分可空，會先遇到未定義邊界。
**碼證**：`nl -ba docs/SPLITUNIFY_SPEC.D-002.md | sed -n '180,187p'` 的 Step 0 僅驗 index 首尾；`nl -ba momentum/Analysis/event_samples/split_projection.py | sed -n '498,527p'` 顯示只對 test 空 fail-closed、train 空則 `continue`，並直接建立 `train_ms/test_ms`；`nl -ba momentum/core/contracts.py | sed -n '404,415p;676,712p'` 顯示 `SplitPlan.__post_init__` 無 pair 關係檢查，雖有 `validate_split_pair_integrity`（含非空/洩漏檢查）但該 derive 路徑未呼叫。修復：Step 0 一併要求 train/test 非空、`train_last_ms < test_start_ms`、row sets 不重疊且 pair integrity 通過，或明定空 train 的 fail-closed 訊息；在任何 side rule 前執行既有 pair validator。可行性證據：validator 與所需 row/time 資料已存在，無需改數值語意。信心：高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `momentum/Analysis/event_samples/split_projection.py#99bfddace904`; `momentum/core/contracts.py#1471cef968a3`

## CODEX-R9-P2-09
**斷言**：`SU-RESID-9A-UI` 的 trigger 雖可由 grep 觀察，卻沒有 owner、權威登記列或 gate/task 使它在後續輪次自動收斂；目前它只出現在 SPEC §N，TODO 仍是五鍵 metadata 舊形狀。這是治理追蹤缺口，不是把尚未接線誤宣稱為已接線。
**碼證**：`rg -n 'SU-RESID-9A-UI|EventSamplePipeline\.run|production.*run' scripts tests api momentum docs --glob '*.py' --glob '*.sh' --glob '*.md'` 只命中 SPEC/brief/handoff 類文字，未命中專門 gate；`rg -n -C 3 'SU-RESID-9A-UI|metadata\.split_unify' docs/SPLITUNIFY_TODO.md` 只見舊 Task 4.1 五鍵契約。修復：在 epic authority/TODO 登記該 residual 的 `為何現在不做`、owner、recheck command 和觸發後續票，並讓完成檢查固定重跑生產 caller 掃描；若不建立 gate，至少把 manual recheck 命令與責任人寫入權威登記。信心：中高。
**來源摘要**: `docs/SPLITUNIFY_SPEC.D-002.md#e3ebec32d870`; `docs/SPLITUNIFY_TODO.md#e44da6448b01`

K1-K8 / D-001 / golden / residual trigger 的新衝突集中在上述 finding：K1 的 G-4c 仍是共同錯誤可綠；K2 的 Task 9.1 目標與 residual 互斥；K3 引錯 brief 模板；K4 三層方案未決且無 handoff；K5 Step 0 未覆蓋 pair 完整性；K6 baseline 計數前提不成立；K7/K8 的具名測試與 mutation 清單本輪未另發現缺檔或漏號，但它們仍不能補足 G-4d 與 producer→metadata wiring。

ASSUMPTIONS_VERIFIED: 已實跑 golden、obligation block、doc format 與 caller/template/source grep；G-4c、Step 0 exhaustiveness、C6 baseline equality、UI trigger 均有反證或未閉合證據。
TESTS_RUN: `venv/bin/python scripts/freeze_splitunify_golden.py` rc=0（G-3b/G-5/GOLDEN OK）；`bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；其餘 `rg`/`nl` 為唯讀證據命令。
FAILURES_SEEN: none（未修改實作以消除任何測試失敗）。
SCOPE_CHANGES: none；只新增本交件檔，未改 SPEC/TODO/程式碼/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 無實際輸出變更；finding P1-05/P1-06 指出計畫中的 `metadata.split_unify` 新欄位與資料流仍需裁決/施工。
TMP_CLEANUP: 已檢查並清理本 task 可辨識的 `/tmp` workdir；未觸碰並保留 `/tmp/claude-501`。
VERDICT: blocked
BLOCKED-BY: CODEX-R9-P1-01,CODEX-R9-P1-02,CODEX-R9-P1-03,CODEX-R9-P1-04,CODEX-R9-P1-05,CODEX-R9-P1-06,CODEX-R9-P1-07,CODEX-R9-P1-08
CLOSED: CODEX-R8-P1-03,CODEX-R8-P1-04
STATUS: DONE
