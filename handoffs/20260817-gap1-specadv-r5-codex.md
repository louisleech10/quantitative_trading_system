# GAP-1 SPEC R5 複審 — CODEX

task-id: `20260817-GAP1-X-REVIEW-R5` ｜ family: `CODEX` ｜ target: `docs/GAP1_STRATEGY_OVERFIT_SPEC.md`
本輪審查 SPEC R4；目前 SPEC sha256 前 12 碼＝`f7321c906af7`。未修改 SPEC、程式、測試、golden、data_cache 或根 `HANDOFF.md`。

## Closure table（本家 R3 8 條）

| R3 finding | verdict | closure evidence |
|---|---|---|
| CODEX-R3-P0-01 | PARTIAL / OPEN | `SPEC:439-467` 已補必填 `n_obs`／`n_candidates`、四步選冠軍/排名、平均排名與 tie-break；但 finite 候選在 path 內 `std=0` 時 metric=NaN，仍無選擇/排名/狀態規則，見 `CODEX-R4-P0-01`。|
| CODEX-R3-P1-01 | CLOSED | `SPEC:106-111` 改唯一推導式並要求測試重算；`venv/bin/python -c ...` 實跑 `abs_diff=5.421010862427522e-20`、`within_atol_1e-18=True`。|
| CODEX-R3-P1-02 | PARTIAL / OPEN | `SPEC:255-259` 新增型別/必填、`additional_properties: false`、`reason_conditions` 要求；但 13-key 結構未放置 `reason_conditions`，ledger row/n_fields 型別仍未定義，且非法列要求記 reason 卻無對應 enum，見 `CODEX-R4-P1-01`。|
| CODEX-R3-P1-03 | PARTIAL / OPEN | `SPEC:345-364` 已改 typed `LedgerReadResult` 並禁止另傳 `n_trials`；但 Task 2.2 未定義 DSR 使用哪個 N 欄位、未要求 snapshot/hash 聚合欄位，驗證仍寫已移除的 `cross_trial_sr_values`，見 `CODEX-R4-P1-02`。|
| CODEX-R3-P1-04 | PARTIAL / OPEN | `SPEC:477-494` 已拒絕 `external_declared`；但 `full_grid`/`ledger_all_candidates` 沒有可信 candidate ID 集合或獨立 expected hash 可供簽名內重算，top-K 仍可自標 full_grid，見 `CODEX-R4-P1-03`。|
| CODEX-R3-P1-05 | CLOSED | `SPEC:197-208` 明列 objective `evaluate()` 傳 `timeframe`，並以 `result.annualization["periods_per_year"]` 建構 metrics；新增 ②b 同時驗 engine 直呼與 `None` 分叉。|
| CODEX-R3-P2-01 | CLOSED | `SPEC:145-153` 已明定 `value_per_period`、`value_annualized`、`sr_estimator_variance` 皆 NaN，且測試同時斷言雙欄。|
| CODEX-R3-P2-02 | CLOSED | `SPEC:343` 標題已改為「跨 trial 變異數來源二態」，`SPEC:244-245` 移除 `analytic`。|

## 必答 2/3

可否進 TODO 生成：**不可**。真正阻擋者為 `CODEX-R4-P0-01`、`CODEX-R4-P1-01`、`CODEX-R4-P1-02`、`CODEX-R4-P1-03`；它們分別可令 PBO 未定義、contract 自洽假綠、DSR 統計物件錯綁、top-K 宇宙污染通關。

具名殘留判斷：上述四項均 **no**，不能帶進 TODO 而宣稱不損 B1–B4 正確性。§N 所列未接生產者/API/前端、adaptive-search 的 `n_independence="unverified"` 等，若維持純統計核心的 fail-closed/明示 unavailable，可作具名殘留；它們與本四項不同。

## CODEX-R4-P0-01

**斷言**: PBO 逐 path 的 `sharpe` metric 對 finite 但局部 `std==0` 的候選會回 NaN，而 SPEC 沒有定義 champion、OOS rank、path 排除或 fail-closed reason；因此 F1 的四步演算法仍不足以讓獨立實作得到相同結果。

**碼證**: `SPEC:446-455` 只把整個候選含 NaN/inf 視為 invalid，未處理 path slice 的退化；`SPEC:145-146` 又明定 `std==0` 的 Sharpe 為 NaN。實跑 `venv/bin/python -c 'import numpy as np; ...'` → `global finite [True, True]`、`candidate0 IS std 0.0 sharpe nan per Task 1.2`、`candidate1 ... sharpe finite 2.1213203435596424`；同一規則下 `max`/rank 遇 NaN 未定義。RECHECK：重跑該命令，或以 `s_blocks=2` 使 IS/OOS 各只有一筆，直接觸發 `n_obs<2`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；這不是「函式尚不存在」問題，而是已寫死的輸入邊界與 PBO 演算法互相留下未定義分支。修法：明定 path-level metric 退化的拒絕/剔除與分母、全 path 不可算時的 status/reason，並以包含局部常數 slice 的 reference oracle 驗證；不能默默讓 Python/NumPy NaN 排序決定結果。

## CODEX-R4-P1-01

**斷言**: Task 2.1 的機器 contract 仍不可唯一實作：它要求「僅 13 個頂層鍵」卻另要求 `reason_conditions`，未說明其巢狀位置；`ledger_record_keys`/`n_fields` 仍只有名稱而無 row 型別/required 規則；非法 ledger row 要記 reason，但 9 值 enum 沒有對應非法列 reason。

**碼證**: `SPEC:230-233` 寫 JSON 含且僅含 13 個頂層鍵；`SPEC:251-259` 才另要求 `reason_conditions`、型別/必填與額外鍵；若 `reason_conditions` 放頂層即違反 13-key，放巢狀則 schema 未定義。`SPEC:235-238` 僅列 ledger/n_fields 名稱，`SPEC:278-289` 要求非法列「記 reason」；`SPEC:251-254` 的 reasons 沒有 `invalid_ledger_record` 或等價字面。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '230,259p;274,289p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；Agent 可自行選 schema 形狀、任意 ledger 型別或把非法列折疊成錯誤 reason，24 案例仍可能與同一份不完整 contract 自洽通過，正中 F3 要防的自洽假綠。修法：在唯一 JSON SoT 明定 `reason_conditions` 的實際層級與 schema，補 ledger row/n_fields 的 type/required/additional-properties，並為每個要求記錄的非 ok 路徑提供唯一 reason。

## CODEX-R4-P1-02

**斷言**: typed `LedgerReadResult` 的加入尚未完成 DSR snapshot binding：Task 2.2 沒有規定五個 N 欄位中哪一個是 DSR 的 N，也沒有規定如何保留/聚合 `input_artifact_hash` 供與 `period_returns` 比對；Task 3.2 驗收仍引用已從 signature 移除的 `cross_trial_sr_values`。

**碼證**: `SPEC:278-283` 的 LedgerReadResult 只明列五個 `n_fields`、`n_semantics`、`valid_sharpe_values`、status/reason，未選定 `n_candidates_considered`／`n_evaluated`／`n_valid_metrics`；`SPEC:345-364` 要求 DSR 驗 `input_artifact_hash` 一致，但 `PeriodReturns` 與 LedgerReadResult 的定義沒有可比較的 hash/snapshot identity；`SPEC:369-377` 仍寫 `len(cross_trial_sr_values)`，而 signature `SPEC:345` 已無此參數。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '274,289p;343,377p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；呼叫方仍可在同一 typed 物件內用錯 N 欄位，或無法證明 `valid_sharpe_values` 與被檢驗報酬是同一 snapshot，導致 SR0 deflation 與跨 trial variance 不屬同一統計物件；測試還沒有可直接呼叫的參數契約。修法：在 `LedgerReadResult` 寫死 `n_for_dsr`、canonical snapshot identity/hash 及 values 的 provenance/一致性規則，並把驗收改用 `ledger_result`，不用已刪除的參數名。

## CODEX-R4-P1-03

**斷言**: `candidate_set_hash` 重算目前仍不是可信 universe provenance：PBO signature 沒有 candidate ID 集合或 `LedgerReadResult`，而 `full_grid` 沒有獨立 expected hash/source；因此先做 top-K 再把同一 50 個 ID 自算 hash、宣稱 `source="full_grid"` 仍可通關。

**碼證**: `SPEC:439-441` 的 PBO signature 只有 `returns_matrix`、N/S、metric、`universe_provenance`；`SPEC:477-486` 的 dataclass 僅列 `selection_free`、`source`、`candidate_set_hash`、`candidate_count`，卻要求由「候選識別集合」重算 hash，該集合不在輸入。`ledger_all_candidates` 只在文字中指向 LedgerReadResult，但 signature 沒有該 result；hash 演算法/ canonical ordering 也未定義。RECHECK：`nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '437,486p'`，並構造 top-K ID list 自算同 hash 後代入四欄即可滿足現行書面條件。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#f7321c906af7

[BLOCKING] 信心度=High；這直接保留 F4 要關閉的污染路徑，PBO 可在被挑過的 universe 上給出看似合格的結果。修法：讓 guard 收到可信、不可變且可重算的 candidate ID artifact（或 ledger snapshot），以 canonical hash 演算法與獨立 expected universe identity 比對；只有 count/hash 自洽不足以證明 selection-free。

## 被當成事實的未驗證假設（§0）

- F1 四步演算法已足夠：**未成立**，局部退化 metric 未定義。
- F3 `reason_conditions`＋`additional_properties:false` 已完整封閉 contract：**未成立**，結構位置、ledger 型別及 reason coverage 仍缺。
- F4 candidate hash 重算已封閉自我宣告：**未成立**，缺 trusted candidate set/expected hash。
- 其餘 §N 殘留可否帶入 TODO：純統計核心之生產接線/API/前端與 adaptive-search 已有明示 unavailable/降級語意，**可**具名帶入；以上四項則不可。

## Verdict：需修補後派工，不可進 TODO

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、brief、review template、SPEC R4、R3 Codex review、R4 synth；SPEC sha256=`f7321c906af7`；template_check 實跑 PASS；μ 重算差值與 atol 實跑；局部 constant-slice probe 實跑；未把「函式尚不存在」當 finding。
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`，rc=0；`venv/bin/python -c '...mu...'` → `within_atol_1e-18=True`，rc=0；`venv/bin/python -c '...constant slice...'` → `global finite [True, True]` 且 `candidate0 IS std 0.0`，rc=0；未跑產品 pytest（本輪只審 SPEC，brief 禁改碼）。
FAILURES_SEEN: completeness command was intercepted before script execution by the existing OPEN-debt PreToolUse gate; no format failure was emitted.
SCOPE_CHANGES: 僅新增 `handoffs/20260817-gap1-specadv-r5-codex.md`；無越界，未改 SPEC、程式、測試、golden、data_cache 或根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: 未修改數值或輸出；指出 PBO path-degenerate 分支、contract schema、DSR snapshot 與 universe provenance 的規格缺口。
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-specadv-r5-codex.md`
HANDOFF_NOT_UPDATED: 根 `HANDOFF.md` 由 Claude 維護；本輪按 brief 只寫指定 review artifact。
TMP_CLEANUP: final check found `/tmp/workdir` absent and `/tmp/claude-501` present (`Directory drwx------`); no deletion performed, protected entry preserved。
COMPLETENESS_ATTEMPT: exact command `bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r5-codex.md --family codex` attempted; PreToolUse blocked before script execution with `OPEN 債或帳本不可信`，故沒有 script rc。`bash scripts/gate.sh dispatch` → rc=1，列出 `20260817-gap1-x-review-r5` state=OPEN；未使用 env/命令形狀旁路，亦無格式錯誤輸出可就地修正。
STATUS: BLOCKED — completeness_check 被既有 OPEN 委員會債務 gate 在執行前攔截，無法確認 rc=0
