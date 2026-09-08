# Reconcile — 20260909-evtwarmup-x-review-r5

**來源** 20260909-EVTWARMUP-X-REVIEW-R5-codex.md, 20260909-EVTWARMUP-X-REVIEW-R5-composer.md, 20260909-EVTWARMUP-X-REVIEW-R5-grok.md　|　**roster** codex,composer,grok


## 群集 / 處置

grok「可合併」（sentinel `GROK-R5-P3-00`，clean-clone mutation＋獨立 gap2 對照皆實跑）；composer「可合併（附 P2 修 probe／brief）」；codex「需修補後派工」：2 P1＋2 P2，四條皆附實跑反例、皆成立，**皆已修**（皆為主委自造缺陷，依 `feedback_self_inflicted_bugs_dont_ask` 直接修不問）。

### Z1 — P1 refreeze 探針對照已被 `--write` 覆蓋的 PRE_PATH（`CODEX-R5-P1-01`＋`COMPOSER-R5-P2-01`）
**處置**：探針改對照不可變 `tests/golden/tfwindow/gap2_pre_disclosure.sha`（`7a1dd8f0` 投影 digest `163c4cec…`），並同時要求 live == 現行 PRE_PATH；兩者皆真才 `DIFF_ONLY_DISCLOSURE=YES`。receipt `handoffs/run_receipts/tfwindow_refreeze_probe_r5.log`。

### Z2 — P1 語意非法 timeframe（`0h`／`-1h`／`infh`／`nanh`）被當 applied（`CODEX-R5-P1-02`）
**處置**：`ICEngine._is_valid_timeframe_hours`（可解析且有限正數）套用於 `set_timeframe` 與 `_adjust_rolling_windows`；非法 reference 回第四值 `not_applied:invalid_reference_tf`；測試 `test_engine_rejects_semantic_invalid_timeframes`；mutation T3；SPEC 邊界⑤。

### Z3 — P2 `config_override` 改 `reference_tf` 未同步進引擎，揭露≠實際（`CODEX-R5-P2-03`）
**處置**：`set_timeframe(tf, reference_tf=)` 由 analyze 以 effective config 傳入；測試 `test_config_override_reference_tf_reaches_engine`（override 1h／run 12h ⇒ `[2,5,10]`——126/12=10.5 半偶捨入，codex 反例寫 11 為其期望值非實跑——且 rolling 鍵一致）；mutation T4；SPEC 邊界⑥。

### Z4 — P2 1h golden 未鎖 fallback 狀態／原因／列數／特徵名；SPEC 邊界③④與 `atol` 措辭落差（`CODEX-R5-P2-04`＋`COMPOSER-R5-P2-02`＋GROK 建議）
**處置**：golden payload 加 `features`／`n_features`／`analysis_status`／`oos_downgrade_reason`／`split_details`／`ic_window_disclosure`，測試 `test_1h_golden_locks_fallback_and_features`；SPEC Task 3.1 邊界③④改寫（analyze 層 fail-closed、引擎層才 `not_applied:*`，不放寬切分——三家一致）；`atol`→pinned-sha 契約登記 `TW-RESID-2`（needs-research）。

### Z5 — 必答 7：`test_flag_toggles_path` 既有紅
**處置**：composer／grok 裁「登記既有殘留」、codex 裁「非新回歸不須登記」；採較嚴版登記 `TW-RESID-3`（blocked-by：ICHC 測試面，三家一致非本票缺陷）。

Verdict: 需修補後合併——Z1–Z5 已修並加測試／mutation；修補由三家於下一輪（R6，收案前 stamp）以同一反例（probe rc、`0h`／`infh` 注入、override `reference_tf=1h`）複驗。
## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P1-01
**斷言**: refreeze probe 比對已被 `--write` 更新的 PRE_PATH，故目前驗收命令會把正確的「只差 disclosure」判成失敗。
**碼證**: `venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py` → `pre=363ae1ceebb6 live=363ae1ceebb6 live_minus_disclosure=163c4cecb100`, `DIFF_ONLY_DISCLOSURE=NO`, rc=1；probe:26-39 比對 current PRE_PATH，git 7a1dd8f0 舊 canonical 是 `163c4cec…`。
**來源摘要**: handoffs/20260909-probe-tfwindow-refreeze.py#22d4069c8e9f；handoffs/run_receipts/gap2_golden_pre.json#5aded8ea7be8；[BLOCKING] 信心度 High；保留不可變的舊 projection digest／sidecar 後再 `--write`，現有 YES receipt 已過時。
## CODEX-R5-P1-02
**斷言**: `set_timeframe` 將 `0h`、`-1h`、`infh`、`nanh` 視為 `applied`，可靜默錯算、全變 1 或拋例外。
**碼證**: `momentum/Analysis/ic_engine.py:86-94,1353-1360` 只檢查 parser 非 None；實跑輸出 `0h applied [21,63,126]`; `-1h applied [1,1,1]`; `infh applied [1,1,1]`; `nanh applied ValueError cannot convert float NaN to integer`。
**來源摘要**: momentum/Analysis/ic_engine.py#66a2fa1b696c；[MAJOR] 信心度 High；current/reference 均應 finite 且 >0，否則回 `not_applied:invalid_timeframe` 並加 edge tests；`bad` reference 也目前回 base windows。
## CODEX-R5-P2-03
**斷言**: `analyze(config_override=...)` 的 disclosure 可使用 effective `reference_tf`，但 engine 仍使用建構時 reference，導致揭露與實際換算不一致。
**碼證**: orchestrator:985-988 建 engine、1050 套 override、1092-1094 用 effective config；實跑 override `reference_tf=1h`、run `12h` → `effective_reference=1h engine_reference=12h disclosed_adjusted=[21,63,126]`（依 1h/12h 應為 `[2,5,11]`）。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#4cbc810e28cb；momentum/Analysis/ic_engine.py#66a2fa1b696c；[MAJOR] 信心度 Medium；同步 engine reference 或由同一 effective config 計算，服務 factory 同步建構不應掩蓋 direct orchestrator contract。
## CODEX-R5-P2-04
**斷言**: 1h golden 未鎖定 fallback 狀態／原因／計數，且 SPEC 的缺 tf「揭露」措辭與 analyze 實際 fail-closed、以及 `atol=1e-12` 與 canonical sha 並不相同。
**碼證**: `tests/api/test_tfwindow.py:67-83` 只比 keys/lengths/value sha，:72-74 只允許兩種 reason；`_golden_payload` 的 `n_features` 未斷言；SPEC:33-43 要求 atol、缺/非法揭露，而 orchestrator:1098-1104 後以 `_resolve_expected_freq` raise。 [MINOR] 信心度 High；固定 deterministic fixture 時 sha 可用但較 atol 嚴格、跨平台易假紅，且可對空 feature/status 變更假綠；建議鎖 `analysis_status`, exact `oos_downgrade.reason`, details/counts、finite/NaN mask，或改 SPEC 為 pinned sha contract。
### 必答裁定
1a/1b：讀點為 `compute_rolling_ic→_adjust` (engine:312)、`_rolling_warmup_min_rows` 由 precheck:3313 與 stage4:3605 呼叫、`_slice_rolling_ic_to_test:4256`；皆在 analyze:1087 注入後。fallback:1437 重新進 analyze；scan cube 每格 service:1286,1298 亦進 analyze；refilter 不重算 rolling，cross-sectional 用獨立 `window_cross_sectional`；只有 direct stage4/unit-engine caller 是刻意 bypass，沒有 production cache/threshold 在注入前計算。
2a/2b：`timeframe=0h` 且不走 split 時即有 `applied`＋實際 `[21,63,126]` 反例；合法 12h 實跑刪 disclosure 得 `163c4cecb100`，與 git 7a1dd8f0 舊 golden 相同，故數值/鍵未見漂移，但 current probe 因 stale PRE_PATH 仍失敗。
3a/3b：fail-closed 避免靜默錯算，意圖正確但不滿足「analyze 回報揭露」字面；裁定修改 SPEC/TODO 明確寫 analyze reject、engine direct 才回 `not_applied:*`，不要為揭露而放寬切分。該狀態在 production report 無 missing/invalid consumer；analyze local 寫 metadata，direct engine caller 若忽略 return 則是既有 silent legacy path。
4a/4b：sha 僅在固定 interpreter/data 可接受，非 `atol=1e-12` 等價；會因浮點/JSON formatting/BLAS 漂移假紅，未納 feature name、n_features/status 可假綠。是，fixture 應鎖 `degraded_full_sample`、`rolling_warmup_insufficient`、`train_rows=1600/test_rows=395/min_test_rows=1517`（receipt 實測），若這些是契約。
5a/5b：`0h` semantic-invalid accepted 的 mutation 可使 T1/T2/C1＋M1–M13 全綠；T1/T2 紅是 assertion 行為、C1 綠，非 import/syntax。6：無 ≥10× 不必要複雜。7：不可合併；`test_flag_toggles_path` 在 HEAD~1 已同樣失敗、非本票新回歸、且本 diff 未改其 path，故三值判定為「不須登記新殘留」。
§1/§2：矛盾= P2-04；端到端=1a/3b；不可測= P2-04；quant/OOM/cache/必要性/agent=無；§0 未驗證假設為「canonical sha 跨環境等價」與「1h 短歷史 fallback 只需任一 reason」，均未當作 fact。
ASSUMPTIONS_VERIFIED: call-site grep、invalid-timeframe/config-override probes、12h projection digest、mutation receipt 均實跑；無 P0。
TESTS_RUN: exact group1 → 24 passed, 4 warnings, 0 skip, rc=0；exact group2 → 1 failed (`test_flag_toggles_path`), 12 passed, rc=1；exact refreeze probe → `DIFF_ONLY_DISCLOSURE=NO`, rc=1；phase3 receipt → pass=3/fail=0/skip=0。
FAILURES_SEEN: group2 pre-existing flag test；refreeze stale oracle；invalid semantic timeframe probe；均已納入本報告，未改碼。
SCOPE_CHANGES: 只新增本交件檔；未改 production/test/docs/frontend，未動 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未改任何輸出；審查指出 disclosure/golden/fallback contract 與非法 timeframe 的數值風險。
STATUS: DONE
## COMPOSER-R5-P2-01

**斷言**: `handoffs/20260909-probe-tfwindow-refreeze.py` 在 gap2 pre 已 `--write` 重凍後，仍用 `pre["canonical_sha"]`（含 disclosure 之新 sha）對照「刪 disclosure 後 live」，導致 `DIFF_ONLY_DISCLOSURE` 恒為 NO、rc=1，與 brief 驗收命令矛盾。

**碼證**: 探針 `:35` `same = stripped_sha == pre["canonical_sha"]`；實跑 `venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py` → `pre=363ae1ceebb6 live=363ae1ceebb6 live_minus_disclosure=163c4cecb100` / `DIFF_ONLY_DISCLOSURE=NO` rc=1；寫入前 log `handoffs/run_receipts/tfwindow_refreeze_probe.log` 同命令 → YES（pre 當時仍為 `163c4cec…`）。

**來源摘要**: handoffs/20260909-probe-tfwindow-refreeze.py#22d4069c8e9f

[MAJOR] 信心度=High。重凍後 CI／R5 驗收第三條必紅，與實作品質無關但會假擋收案。修法：pre 檔保留 `canonical_sha_pre_disclosure`（或 probe 改比 `canonical_sha_legacy`／明確欄位），或 brief 將此探針標為**一次性寫前 gate**、收案改靠 `test_g1_golden_unchanged`＋`jq del(.metadata.ic_window_disclosure)` 手動對照。

---

## COMPOSER-R5-P2-02

**斷言**: `docs/TFWINDOW_SPEC.md` Task 3.1 邊界③④「視窗不變＋揭露」與實作（analyze 切分前 `ValueError`、報告無 `not_applied` 鍵）措辭不一致，易誤導審查與 UAT。

**碼證**: SPEC `:43` 邊界③④；實作 `ic_filter_orchestrator:160-164` fail-closed；`tests/api/test_tfwindow.py:99-109` 註解與測試釘 analyze 層行為。

**來源摘要**: docs/TFWINDOW_SPEC.md#e51179a38d97

[MINOR] 信心度=High。不影響數值；建議 SPEC／TODO 改寫對齊實作（見必答 3a），避免下一輪委員按字面要求 analyze 層仍產出 `not_applied` 報告。

---

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding——Task 3.1 之 `set_timeframe` 注入、全路徑 `ic_window_disclosure`、gap2 只多該鍵、1h 鍵集 ×12 與 mutation T1／T2／C1 在碼證＋驗收命令下與 SPEC §G／§V／落地註記一致，無新 P0／P1。

**碼證**: `pytest … -k 'not budget_bench'` → 23 passed 0 skip rc=0；`test_ic_1a_cut1_oos` → 唯一紅 `test_flag_toggles_path`（既有 fixture 債）；獨立 gap2：`live==pre=363ae1ceebb6`、`stripped=163c4cecb100`；clean-clone `evtwarmup-mutate.py --phase 3` → T1／T2 紅＋C1 綠、UNCOVERED=0；production hash＝HEAD；必答 1a–5b 雙向見上。

**來源摘要**: momentum/Analysis/ic_engine.py#66a2fa1b696c；momentum/Analysis/ic_filter_orchestrator.py#4cbc810e28cb；docs/TFWINDOW_SPEC.md#e51179a38d97；handoffs/20260908-evtwarmup-mutate.py#ba28bc5c39a3

[MINOR] 信心度=High。哨兵非實質缺陷；合併判定見 Verdict。建議後續（非本輪 finding）：SPEC／TODO 改寫邊界③④；登記 `test_flag_toggles_path` 殘留；可選鎖 1h golden 之 `oos_downgrade.reason`。

---

ASSUMPTIONS_VERIFIED: 注入在所有 analyze 路徑 rolling／warmup 讀取之前；fallback／scan cube 經 analyze 重注；12h 除 disclosure 外 sha 不變；T1／T2／C1 mutation 紅綠集合＝oracle；1h 鍵 ×12＋TW-RESID-1 degraded；邊界③④意圖以 fail-closed＋引擎揭露滿足
TESTS_RUN: pytest tfwindow+evtwarmup+gap2(-k not budget_bench) 23 passed 0 skip rc=0；ic_1a_cut1_oos 1 failed(flag_toggles)/12 passed；probe 獨立 DIFF 成立（腳本 YES 因 pre 已重凍而 NO）；mutate phase3 clean-clone UNCOVERED=0 rc=0；baseline 2208 OK／1 unrelated FAILED
FAILURES_SEEN: clone 缺 la0 h5 symlink → C1 假紅（補 symlink 後綠）；含 budget_bench 之全檔 pytest 並發卡死後改 scoped＋另跑 bench
SCOPE_CHANGES: none（唯讀；/tmp clone 僅供 mutation）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；產品已落地之全域 disclosure 鍵與 1h×12 如 brief）
產出檔: handoffs/20260909-EVTWARMUP-X-REVIEW-R5-grok.md

STATUS: DONE
