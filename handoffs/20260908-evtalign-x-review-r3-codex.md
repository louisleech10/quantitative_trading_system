# EVTALIGN B1 code review R3 — codex

brief-kind: review  
task-id: `20260908-EVTALIGN-X-REVIEW-R3`  
family: `codex`  
findings-round: `R3`  
target: `efb16e4c` (B1; B0=`097dae40`)

# 被當成事實的未驗證假設（§0）

- 新測試 14 條、0 skip：**fact-verified**；指定 pytest → `14 passed in 3.59s`, `rc=0`。
- B1 mutation：**fact-verified in clean target clone**；`bash scripts/evtalign_phase_gate.sh 1` → `GATE PASS: phase=1`；mutation `8/8`, `UNCOVERED=0`。
- 共享工作樹直接跑 phase gate：**environment failure**；既有 dirty orchestrator 使 mutate 先 `REFUSE rc=3`，不是 target code 斷言失敗。target clone 重跑已排除該干擾。
- split golden：**fact-verified**；probe `rc=0`、`組合數=9（ok=8、skipped=1、error=0）`、`與既有 golden 相同？ True`。
- stage0 oracle probe：**fact-verified**；`rc=0`、`逐鍵相同 = True`。
- baseline sha：**fact-verified**；`shasum -a 256 -c handoffs/20260908-evtalign-r3-baseline.sha` → `rc=0`、全 OK。
- tz-aware event key：**fact-verified**；`validate_event_given` 對 UTC `DatetimeIndex` → `checked_samples=3`。
- 真實 API service 五階段端到端：**blocked-by / not-run**；直接 orchestrator e2e test 通過，但本輪未啟動後端走 `event_batch → _run_event_label_stages → analyze → _assert_event_triple_bound`。
- 最後指定 pytest：**既有環境漂移**；`13 passed, 1 failed`，唯一失敗為 `test_ichc_p2_golden.py::TestTG1Golden::test_feature_set_and_config_exact` 的 config hash `9fcdd0cb…` vs frozen `c1616bdf…`；target diff 未碰該設定。

# R2 closure 與必答 verdict

| R2 群集 | 裁定 | 重跑／碼證摘要 |
|---|---|---|
| D1 `label_kind` 可偽造 | **CLOSED** | `derive_label_kind` 只接受 producer `label_source`；缺席/未知 raise；D2 mutation 與 `test_label_kind_missing_source_raises` 均紅/綠正確。 |
| D2 `bars_after_target_end` 可偽造 | **CLOSED** | 參數已不存在；`_coterminalize_close` 由 normalized `feature_index[-1]` 推導；B1 mutation 使截短測試紅。 |
| D3 close 污染使 oracle 自洽 | **CLOSED（EA-RESID-4 保留）** | B1 沒有新增 caller-supplied close 判準；守衛 sha256 釘住。R2 Case H 仍是 `PASSES_SELF_FAILS_TRUE`，屬原始 K 線品質邊界，非本批新洞。 |
| D4 event label rotation / event_id mismatch | **CLOSED（本批契約範圍）** | producer value 逐筆比對、owners 缺失/重複 raise、service value 回綁；`test_event_values_shifted_by_one_row_raise`、owner tests、D1/D3 mutation 均驗證。 |
| D5 覆寫前仍驗 forward-return 鷹架 | **OPEN** | R2 Case J 重跑仍印 `MISBLOCK_DISCARDED_SCAFFOLD`；target stage2 仍在 stage3 覆寫前呼叫 `validate_alignment`。詳見 `CODEX-R3-P1-01`。 |
| D6 Task 0.2 baseline 不足 | **CLOSED** | golden v2 已含 `split_row_fingerprint`、`retained_event_ids`、preload cases；split probe 逐鍵對證。 |
| D7 `excess` / `risk_adjusted` oracle | **CLOSED（EA-RESID-5 保留）** | B1 未新增 oracle raise；非 oracle 型別仍依既有契約處理。事件鷹架因此造成的擋死歸 D5，不重複列 finding。 |
| D9 mutation ID collision | **CLOSED** | clean target clone 中 7 條 mutation `rc=1` 真斷言紅、C0 `rc=0`，`UNCOVERED=0`。 |

同一份 R2 grok counterexample script 實跑 `rc=0`；其 G/I/J/H 輸出仍是紙上舊設計的旗標（分別 `LEAK_BYPASS`、`WRONG_JOIN_PASSES`、`MISBLOCK_DISCARDED_SCAFFOLD`、`PASSES_SELF_FAILS_TRUE`）。新碼對 G/I 的對應實作測試與 mutation 已補驗；J 仍成立，H 為已登記 residual。

## 必答 1b：各 closure 是否製造新誤擋

D1、D2、D3、D6、D9：合法 known source、合法截短、同尾與 baseline 均通過，未見新誤擋。D4：合法 dense event label、owners 缺席/重複的 fail-closed 邊界與 tz-aware key 均有直接測試。D7 的合法 `risk_adjusted`/`excess` 事件情境若被 stage2 鷹架擋住，屬 D5 OPEN 的同一擋死，不另重複計數。

## 必答 2a/2b：B 的漏與誤擋

2a：stage2 生成路徑的「K 線尾長於 feature」主病灶已封；裁切發生在 `generate_returns_by_type` 前，截短與同尾 labels 逐值相同。非單調或重複 close 會在 `_normalize_frame_time_index` 的 monotonic/unique guard 先 raise。中段 gap 的只讀 probe 實跑：`accepted gap labels; interior_nan=1 tail_nan=5`；這表示 B 不提供 close 原始品質/固定 cadence 的新保證，仍屬 `EA-RESID-4` 既有邊界，不是 B 新增的 caller-spoof P0。stage0 預載 label 的 parity 測試缺口另列 `P1-02`。

2b：未見 B 新誤擋。feature 空 index 依設計 raise；K 線尾早於 feature 尾時 helper no-op，實跑 `_stage2_label_generation(... _Reader(140) ...)` → `AlignmentViolationError target trailing NaN count must equal lag: expected 5, got 22`，由既有 guard 照舊擋。

## 必答 3a/3b：D 的漏與誤擋

3a：在 producer maps 保持正確的前提下，timestamp 對 value、owner 對 event id、service `event_id→value` 三段皆有檢查；整批 value rotation、未知 id、缺 owner、重複 owner 都會 raise。未構造出同時通過新契約與 service 回綁的實質 consumer-side bypass。D 的誠實邊界是它不能證明 producer 自己計算的 raw event cutoff/value 是真實市場語義，這不在本批。

3b：dense same-tail event labels、UTC tz-aware index、fallback `mainline_return_N` 與 real la0 orchestrator e2e 均通過；未見新合法事件 run 被 D 誤擋。service 真實五階段端到端未啟動，保留 blocked-by，不宣稱已驗。

## 必答 4a/4b：保留 stage2 鷹架驗證是否成立

4a：安全理由只**部分成立**。同一 K 線的 global/mainline label 需要 forward-return guard；但 TODO Task 2.1 明文規定 `event_label_value` 覆寫前不驗，而 target 仍在 stage2 先驗，故 implementation 與 TODO 有可機械對證的矛盾。

4b：會產生「驗了就丟」。只讀反例：設定 `return_type="risk_adjusted"`、截短/合法 feature run、同時提供合法 event labels 時，stage2 仍先跑鷹架；實跑輸出 `AlignmentViolationError target coverage too low: actual=0.8344, required>=0.9585`。`excess` 路徑則實跑 `ValueError benchmark_close is required for excess`。事件 label 尚未被消費前即被丟棄的 scaffold 擋住。最小修法需在 B2 前取得裁定：若遵守 TODO，僅對確定會被 event label 覆寫且不被消費的 scaffold 降為診斷/跳過，覆寫後仍走 `event_given`；若要保留鷹架 gate，則同步把 TODO 明文改成此 user-ruling 並接受該擋死。

## 必答 5a/5b：mutation 充分性與紅因

5a：8 條全綠的缺陷是「stage0 預載 labels 在截短 K 線下的 producer parity 漂移」：測試只對 stage2 生成路徑做截短/同尾逐值對照；stage0 只驗 oracle report，mutation 清單也沒有改動/污染預載 label payload 的 mutation。故列 `CODEX-R3-P1-02`（needs-research，不宣稱已證實 production leak）。另一個未覆蓋邊界是 direct orchestrator caller 不帶 owners，但 service product path 已 fail-closed，未列為本輪 finding。

5b：clean target clone 中 B1/B2/B3/D1/D2/D3/A4 全為 `pytest rc=1` 的預期斷言失敗；C0 comment-only 為 `rc=0`；無 import/語法假紅。phase gate 同 clone `GATE PASS: phase=1`。

## 必答 6：複雜度

沒有 ≥10× 不必要複雜或慢速 finding。`event_label_owners` 是 timestamp→event_id 的逐列綁定，`event_label_by_id` 是 service 端 event_id→producer value 的回比來源，語意不同且同一 producer loop 建立；合併成 nested dict 只省表面欄位，不提高可讀性或正確性。

## 必答 7：是否可進 B2

**可進 B2，無新 P0。** D5 需在 B2 前取得 `user-ruling`（或同步 TODO/實作契約）；P1-02 以 `needs-research` 進 B2 增 stage0 preload parity/mutation，均不構成本輪 merge-blocking。

## CODEX-R3-P1-01

**斷言**: event label 會被 stage3 覆寫且不被消費，但 stage2 仍先對 forward-return scaffold 跑 `validate_alignment`；`return_type` 為 `risk_adjusted` 或 `excess` 的合法事件 run 可在 scaffold 階段 fail-closed，形成「驗了就丟」。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2939-2957` 先生成並驗 scaffold；`momentum/Analysis/ic_filter_orchestrator.py:3059-3093` 才覆寫並驗 consumed label；`docs/GAP3_EVENT_ALIGNMENT_TODO.md:165-170` 明定 event producer 應覆寫前不驗。只讀命令 `venv/bin/python -c ... return_type=risk_adjusted ...` → `AlignmentViolationError target coverage too low: actual=0.8344, required>=0.9585`；同類 `excess` → `ValueError benchmark_close is required for excess`；R2 grok Case J → `MISBLOCK_DISCARDED_SCAFFOLD`。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#47c9ffb0ba23; docs/GAP3_EVENT_ALIGNMENT_TODO.md#c0961bbf2267; handoffs/20260907-evtalign-r2-grok-counterexamples.py#aae975eec9d1

[MAJOR] 信心度=High；這是 TODO/實作契約矛盾與可重現的誤擋，不是新 look-ahead P0。未直接改碼的理由=`user-ruling`：brief 明確要求裁定是否刻意保留 scaffold gate；最小修法見必答 4b。未取得裁定前，P1-01 不應被誤標 CLOSED。

## CODEX-R3-P1-02

**斷言**: B 的逐值截短→同尾證據只覆蓋 stage2 重新生成 labels；stage0 預載 labels 只裁 oracle `close`、不重生或保存 label producer parity，因此相同缺陷可讓 8 條 mutation 全綠且目前沒有 byte-level preload 對照。

**碼證**: `momentum/Analysis/ic_filter_orchestrator.py:2788-2821` 讀入既有 `labels_df` 後只在有 reader 時裁 `close`，再直接以既有 `label_series` 驗證；`tests/momentum/test_close_coterminalize.py:80-97` 的逐值測試只呼叫 `_stage2_label_generation`；`handoffs/20260907-evtalign-mutate.py` 的 8 條 mutation 無 stage0 preload payload mutation。指定 stage0 oracle probe 只輸出 `逐鍵相同 = True`（alignment report），不等價於 label payload parity。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#47c9ffb0ba23; tests/momentum/test_close_coterminalize.py#e51721648f7; handoffs/20260907-evtalign-mutate.py#4528ba20e650

[MAJOR] 信心度=Medium；目前是測試/證據缺口，未由本輪 probe 證明實際 production label 漂移。未修理由=`needs-research`：需先確認產品允許「長 K 線離線預載 label＋短 feature run」的組合，再補 stage0 byte-level parity 與 mutation；不應在本輪捏造 production finding。

## Verdict: 可合併——R2 六 P0 形態已消除；無新 P0。D5 保持 OPEN，需 user-ruling 或同步 TODO/實作契約；P1-02 可帶入 B2 做證據補強。

# VERIFY

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/momentum/test_close_coterminalize.py tests/api/test_event_label_alignment.py -q -rs` | `14 passed, 0 skipped, rc=0` |
| `bash scripts/evtalign_phase_gate.sh 1`（shared worktree） | `rc=1`：mutation 先因 dirty target `REFUSE rc=3`；非 production assertion failure |
| `bash scripts/evtalign_phase_gate.sh 1`（clean target clone + required fixture links） | `GATE PASS: phase=1`, `rc=0` |
| `venv/bin/python handoffs/20260907-probe-split-baseline.py` | `rc=0`, 9 cases, golden `True` |
| `venv/bin/python handoffs/20260908-probe-stage0-trim-oracle.py` | `rc=0`, `逐鍵相同 = True` |
| `venv/bin/python handoffs/20260907-evtalign-r2-grok-counterexamples.py` | `rc=0`; G/I/J/H flags as recorded above |
| `shasum -a 256 -c handoffs/20260908-evtalign-r3-baseline.sha` | `rc=0`, all OK |
| `venv/bin/python -m pytest tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/Analysis/test_ichc_p2_golden.py -q` | `13 passed, 1 failed`; pre-existing config-hash golden drift |

ASSUMPTIONS_VERIFIED: R2 closure matrix、B/D required pairs、mutation 8/8 in clean target clone、golden/probe outputs、tz-aware key、risk_adjusted/excess scaffold counterexamples。
TESTS_RUN: Commands and exact summaries are listed in VERIFY; `pytest tests/governance` 未執行。
FAILURES_SEEN: shared-worktree phase gate dirty refusal（clean clone rc=0）；`test_ichc_p2_golden::test_feature_set_and_config_exact` config hash drift（非本票）；D5 scaffold counterexamples reproduced（finding）。
SCOPE_CHANGES: only this review artifact; no production/test/docs/data_cache changes; shared pre-existing dirty files preserved。
NUMERIC_OR_SCHEMA_IMPACT: no production numeric/schema/output change; review only。
HANDOFF_OUTPUT: `handoffs/20260908-evtalign-x-review-r3-codex.md`
STATUS: DONE
