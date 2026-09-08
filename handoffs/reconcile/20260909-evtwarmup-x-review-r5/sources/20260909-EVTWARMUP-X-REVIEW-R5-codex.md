## Verdict：需修補後派工（2×P1、2×P2；無 P0）
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
