brief-kind: review
task-id: 20260909-EVTWARMUP-X-REVIEW-R5
family: composer
findings-round: R5
標的 commit: `a17b57e7`（`git diff 7a1dd8f0..HEAD`）

## 被當成事實的未驗證假設（§0）

| 前提 | 裁定 | 覆核摘要 |
|---|---|---|
| `pytest tests/api/test_tfwindow.py`＋`test_evtwarmup.py`＋`test_gap2_golden` 0 skip | **fact-verified** | `test_tfwindow`＋`test_evtwarmup` → **19 passed**, 0 skip；`test_g1_golden_unchanged` → **1 passed**, rc=0 |
| `test_ic_1a_cut1_oos` 唯一紅＝`test_flag_toggles_path` | **fact-verified** | `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` → **1 failed, 12 passed**（`:413` `applied is True`） |
| `test_flag_toggles_path` HEAD~1 亦紅 | **fact-verified** | `git worktree add /tmp/tfwindow-review-parent 7a1dd8f0` 後同測 → **FAILED :413**（非本票新引入） |
| `handoffs/20260909-probe-tfwindow-refreeze.py` → `DIFF_ONLY_DISCLOSURE=YES` | **fact-verified 反例** | 本輪實跑 → `live_minus_disclosure=163c4cec…` vs `pre=363ae1ce…` ⇒ **DIFF_ONLY_DISCLOSURE=NO**, rc=1 |
| `evtwarmup-mutate.py --phase 3` T1/T2 紅、C1 綠 | **fact-verified** | `venv/bin/python handoffs/20260908-evtwarmup-mutate.py --phase 3` → **pass=3/3**, MUTATE_RC=0 |
| `set_timeframe` 早於所有 `_adjust_rolling_windows` 消費 | **fact-verified（讀碼）** | 注入 `:1087`；預檢 `:1160`→`:3276`；stage4 `:3605`、`:3638`→`ic_engine:312`；slice `:4256`；fallback 重入 `:1437` 再 `analyze` |
| scan_cube 格內直呼 stage4  bypass 注入 | **fact-verified（讀碼）** | `ic_analysis_service._run_scan_cell` → `analyzer.analyze(...)`（`:1298`），每格新 orchestrator |
| `ic_window_disclosure` sanitizer 不炸 | **assumed** | `_sanitize_metadata_for_json` 只做 significance 清理（`:958-978`），list/int 原样透传；`test_serialization_entries_have_no_nan_literal` 未本輪重跑 |
| baseline sha lock 全 OK | **fact-verified 反例** | `shasum -a 256 -c handoffs/20260909-evtwarmup-r5-baseline.sha` → **2 FAILED**（`ic_filter_orchestrator.py`、`docs/site/現在做到哪.html`）；其餘 OK |

---

## 必答（成對）

### 1a. 注入時序（rolling／warmup call-site）

| 順序 | 位置 | 說明 |
|---|---|---|
| 0 | `ic_filter_orchestrator.analyze` `:1087` | `set_timeframe(metadata.timeframe)` — **唯一注入點** |
| 1 | 同上 `:1094` | `ic_window_disclosure.adjusted_windows` ← `_adjust_rolling_windows` |
| 2 | `:1100`→`:1160` | 切分後 `_precheck_rolling_warmup` → `_rolling_warmup_min_rows` `:3276` |
| 3 | `_stage4_ic_calculation` `:3605`、`:3638` | warmup 安全網＋`compute_rolling_ic`（引擎內 `:312` 再換算） |
| 4 | `_slice_rolling_ic_to_test` `:4256` | OOS rolling 切片鍵 |
| 5 | `_run_full_sample_fallback` `:1437` | 重入 `analyze` ⇒ 再執行 0 |
| 6 | `refilter` `:2131+` | **不重算 stage4**；沿用首跑 cache 與同一 `self._ic_engine._timeframe` |
| 7 | `ic_analysis_service._run_scan_cell` `:1298` | 每格 `analyzer_factory()` → `analyze` ⇒ 走 0 |

### 1b. 反向：注入前快取？

**無。** `ICEngine._timeframe` 初始 `None`；`_adjust_rolling_windows` 每次現算（`ic_engine:1349-1361`），無 adjusted 視窗快取。config 中 `rolling_windows` 保持 [21,63,126] 原值；換算只在讀取時套用。

### 2a. 假換算（`applied` 但鍵未 ×／反之）

**生產 `analyze` 路徑不可構造。** disclosure 的 `adjusted_windows` 與 stage4 共用同一 `_ic_engine._adjust_rolling_windows`（`:1094` 與 `compute_rolling_ic:312`）。T2 mutation 僅在**引擎層**假 `applied`（缺 tf），被 `test_engine_set_timeframe_*` 抓；analyze 層缺／非法 tf 於 `:1100` `_resolve_expected_freq` 先 `ValueError`，到不了 stage4。若有人手改 `metadata["ic_window_disclosure"]` 而不經引擎 — 非生產路徑。

### 2b. 合法 12h run 除 disclosure 外不變

**是（重凍時已證）。** `handoffs/run_receipts/tfwindow_refreeze_probe.log`（寫入前）`live_minus_disclosure=163c4cec…` == 舊 pre；`test_g1_golden_unchanged` 對新 pre `363ae1ce…` 全等。刪 `ic_window_disclosure` 後與改前 canonical 一致。

### 3a. 邊界③④：analyze fail-closed vs SPEC「不變＋揭露」

**意圖已滿足；SPEC 措辭應改。** 缺／非法 tf：`set_timeframe` 回 `not_applied:*`（`:1087-1096` 寫入 metadata），隨即 `_resolve_expected_freq` `:163-164` `ValueError` — **比「不換算＋揭露」更 loud**。測試 `test_missing_timeframe_fails_closed_before_stage4` 明文化。建議 SPEC Task 3.1 邊界③④ 改為：「analyze 層切分前 fail-closed；`not_applied:*` 引擎單測可觀測」。

### 3b. 引擎單獨使用 `not_applied:*` 消費者

**僅單測／探針**（`test_tfwindow.test_engine_set_timeframe_*`、`20260908-probe-evtwarmup-baseline.py`）。生產一律經 `analyze`；無靜默換算路徑（缺 tf 直接 exception）。

### 4a. 1h golden：sha256 取代 `atol=1e-12`

**可接受。** 固定 fixture＋決定性 `json.dumps(sort_keys=True, default=str)` 哈希（`test_tfwindow._golden_payload`）。**假綠**：序列化格式／`default=str` 變更而數值不變。**假紅**：非決定性浮點（本 fixture 路徑為 list 輸出，風險低）。與 §G「值級」意圖一致。

### 4b. `degraded_full_sample` 下是否鎖 `oos_downgrade.reason`

**不必。** TW-RESID-1 已文件化；`test_1h_fixture_window_keys_scaled_by_12` 在 `analysis_status != ok_oos` 時斷言 reason ∈ `{rolling_warmup_insufficient, insufficient_data}`。golden 鎖 rolling 鍵／長度／值 sha 已足；再加 reason 與 status 重複且易受文案微調假紅。

### 5a. mutation 漏網缺陷？

**低風險：** 只改 `adjusted_windows` 列表字面而保留 `set_timeframe`（T1/T2 不紅）。或 disclosure `timeframe_adjustment` 硬寫 `"applied"` 而 `_timeframe` None — 無專項 mutation。不影響 rolling 實算（stage4 仍看引擎狀態）。不修不擋合併。

### 5b. 紅因＝斷言？

**是。** T1→`-k window_keys`；T2→`-k engine_set_timeframe`；C1→全檔 pytest；M8 重定義為 `icir_role=diagnostic` 全域斷言紅。無 import／語法假紅。

### 6. ≥10× 不必要複雜？

**無。** 一個 `set_timeframe`、一塊 disclosure 寫入、測試／探針／mutation 三件套；無新 framework。

### 7. 可合併？`test_flag_toggles_path` 殘留？

**可合併（附 P2 修 probe／brief）。** `test_flag_toggles_path`：**應登記為既有殘留、非本票新紅** — 理由：① `7a1dd8f0` worktree 同測同敗 `:413`（ICHC 小 fixture＋1h meta，與 TFWINDOW 無關或早於本 commit）；② `blocked-by:` 修復屬 ICHC／測試面，超出 Task 3.1 scope；③ `user-ruling:` 本票驗收已允許唯一紅＝此測（brief 狀態斷言）。建議標 `ICHC-RESID-1` 或併入既有 EW 登記處，不阻 merge。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | SPEC ③④ 措辭 vs analyze fail-closed（見 3a／P2-02） |
| 2 | 漏項 | probe 驗收命令重凍後失效（P2-01） |
| 3 | 不可測 | 主路徑 pytest＋mutation＋gap2 可證偽 |
| 4 | quant | 1h ×12 換算與 warmup 1517 一致；TW-RESID-1 已揭露 |
| 5–11 | 其餘 | 無過度工程；無 cache 污染；API 型別 OK；測試非 smoke；無短命白工 |

---

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

## Verdict：可合併（修補 probe／brief 驗收後更佳）

Task 3.1 接線正確：`set_timeframe` 時序覆蓋 analyze／fallback／scan cube；precheck 與 stage4 共用 `_rolling_warmup_min_rows`；12h 除 disclosure 外 byte-stable（gap2 新 pre 已鎖）；1h golden／mutation phase 3 對位。無 P0／P1。P2-01 為驗收 oracle 漂移，應在收案前修 probe 或 brief 第三條驗收；P2-02 為 SPEC 措辭。`test_flag_toggles_path` 登記既有殘留，不阻本票。

---

## VERIFY（本輪實跑）

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_tfwindow.py tests/api/test_evtwarmup.py -q -rs` | 19 passed, 0 skip |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_gap2_golden.py::test_g1_golden_unchanged -q` | 1 passed, rc=0 |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` | 1 failed (`test_flag_toggles_path`), 12 passed |
| `venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py` | DIFF_ONLY_DISCLOSURE=NO, rc=1 |
| `venv/bin/python handoffs/20260908-evtwarmup-mutate.py --phase 3` | pass=3/3, rc=0 |
| `shasum -a 256 -c handoffs/20260909-evtwarmup-r5-baseline.sha` | 2 checksum mismatch（見 §0） |

---

ASSUMPTIONS_VERIFIED: 注入時序讀碼；probe／pytest／mutation 實跑；HEAD~1 worktree 對照 test_flag_toggles_path
TESTS_RUN: 見 VERIFY 表
FAILURES_SEEN: probe DIFF_ONLY_DISCLOSURE=NO（預期寫後漂移）；baseline sha 2 檔 mismatch
SCOPE_CHANGES: none（review-only）
NUMERIC_OR_SCHEMA_IMPACT: none（審查未改碼）
產出檔: handoffs/20260909-EVTWARMUP-X-REVIEW-R5-composer.md

STATUS: DONE
