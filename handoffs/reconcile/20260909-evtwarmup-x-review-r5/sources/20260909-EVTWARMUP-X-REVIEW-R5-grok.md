# EVTWARMUP 第二批 TFWINDOW Task 3.1 實作 code review R5（grok）

brief-kind: review
task-id: 20260909-EVTWARMUP-X-REVIEW-R5
family: grok
findings-round: R5
標的 commit: `a17b57e7`（審查範圍 `git diff 7a1dd8f0..HEAD`）
SCOPE: review-only；禁改 production／test／docs／frontend
ENGINE-DIGEST: momentum/Analysis/ic_engine.py#66a2fa1b696c
ORCH-DIGEST: momentum/Analysis/ic_filter_orchestrator.py#4cbc810e28cb
SPEC-DIGEST: docs/TFWINDOW_SPEC.md#e51179a38d97
TODO-DIGEST: docs/EVTWARMUP_TODO.md#3bbfe57cca40
MUTATE-DIGEST: handoffs/20260908-evtwarmup-mutate.py#ba28bc5c39a3
TFTEST-DIGEST: tests/api/test_tfwindow.py#9c9e9c80b485
GOLDEN1H-DIGEST: tests/golden/tfwindow/rolling_keys_1h.json#6e538a5f756f
BASELINE: `shasum -a 256 -c handoffs/20260909-evtwarmup-r5-baseline.sha` → 2208 OK／1 FAILED＝`docs/site/現在做到哪.html`（與本票無關之站點 HTML 漂移；production 碼 hash＝HEAD）

---

## Verdict：可合併

Task 3.1 與 SPEC §G／§V／落地註記一致；必答 1–5 雙向有碼證；clean-clone mutation phase 3＝T1／T2 紅＋C1 綠、`UNCOVERED=0`；無新 P0／P1。本輪無實質 finding → sentinel `GROK-R5-P3-00`。

邊界③④：裁定**改 SPEC／TODO 措辭**（不另做 analyze 層揭露）；意圖「不靜默換算」已被 split-on 之既有 `ValueError`＋引擎層 `not_applied:*` 覆蓋。`test_flag_toggles_path`：**須登記殘留**（三值理由見必答 7；非本票接線缺陷）。

---

## 驗收命令實跑

| 命令 | 結果 |
|---|---|
| `venv/bin/python -m pytest tests/api/test_tfwindow.py tests/api/test_evtwarmup.py tests/momentum/Analysis/test_gap2_golden.py -q -rs -k 'not budget_bench'` | **23 passed, 1 deselected, 0 skip**, pytest rc=0（~436s）。`budget_bench` 另跑（見下／交接）；首跑含 bench 曾卡死於並發負載後以 SIGTERM 清掉 |
| `venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` | **1 failed／12 passed**；唯一紅＝`test_flag_toggles_path`（`applied is True` 失敗；預檢 `min_test_rows=1517`、`test_rows=31`） |
| `venv/bin/python handoffs/20260909-probe-tfwindow-refreeze.py` | 腳本印 `DIFF_ONLY_DISCLOSURE=NO`／rc=1——因 `gap2_golden_pre.json` 已重凍為含 disclosure 之新 sha（`363ae1ce…`），剝鍵後無法再等於「新 pre」。**獨立覆核**：live==pre=`363ae1ceebb6`；`live_minus_disclosure`=`163c4cecb100`＝寫入時舊投影（receipt `tfwindow_refreeze_probe.log` 之 YES 證據仍成立） |
| clean clone `@HEAD`＋symlink `data_cache`／`venv`／`tests/golden/la0/inputs`：`handoffs/20260908-evtwarmup-mutate.py --phase 3` | **MUTATE_RC=0**；T1 rc=1／T2 rc=1／C1 rc=0；`UNCOVERED=0`；共用樹 `ic_engine`／`orchestrator` hash＝HEAD |
| `shasum -a 256 -c handoffs/20260909-evtwarmup-r5-baseline.sha` | 2208 OK；1 FAILED＝`docs/site/現在做到哪.html`（非審查標的） |

### Mutation 紅集合（closure=CLOSED；紅因＝pytest rc=1 斷言）

| ID | 觀測 |
|---|---|
| T1-timeframe-injection-removed | `rc=1` PASS（期望紅；假 `applied` 未注入 ⇒ 1h 鍵仍未 ×12） |
| T2-missing-timeframe-fake-applied | `rc=1` PASS（期望紅；缺 tf 假換算 ⇒ 引擎層揭露斷言紅） |
| C1-comment-only-control-phase3 | `rc=0` PASS（期望綠；首兩輪 clone 缺 la0 h5 symlink → 假紅，補 symlink 後綠） |

---

## 必答（成對；逐條有碼證）

### 1a. 注入時序：所有讀 rolling／warmup 門檻的 call-site 是否皆在 `set_timeframe` 之後？

**是（生產 `analyze` 路徑）。** Call-site 清單：

| Call-site | 讀什麼 | 相對注入 |
|---|---|---|
| `analyze` `:1087` `set_timeframe` | 寫入 `_timeframe` | 注入點本身（period_alignment 後、切分前） |
| `analyze` `:1094` disclosure `adjusted_windows` | `_adjust_rolling_windows` | 直後 |
| `_precheck_rolling_warmup` → `_rolling_warmup_min_rows` `:3276` | 同上 | 切分後、預處理前；同一次 analyze 已注入 |
| `_stage4_ic_calculation` warmup `:3605`＋`compute_rolling_ic`（引擎內 `:312` 再調 `_adjust_rolling_windows`） | 門檻＋實際視窗 | stage4；已注入 |
| `_slice_rolling_ic_to_test` `:4256` | 調整後窗切 test | stage4 內 |
| `_run_full_sample_fallback` → 再入 `analyze` `:1437` | 全路徑重跑 | 重跑開頭再次 `set_timeframe` |
| `refilter` | **不重算** rolling；吃 `_ic_cache` | 首跑已注入之結果 |
| scan cube 格 | `ic_analysis_service` 每格 `analyzer.analyze(...)` `:1298` | 每格各自注入；`build_cube` 只存報告 |

引擎層直呼 `_stage4_ic_calculation`（`test_oos_ic_rolling_warmup`）**故意**不經注入＝SPEC 保留之回歸。

### 1b. 反向：有無注入前就把視窗算進快取／閾值？

**未證實。** `ICEngine.__init__` 存 `_rolling_windows` 原值，但 `compute_rolling_ic`／warmup **從不讀該快取做換算**——一律呼叫時 `_adjust_rolling_windows(windows)`。無「注入前快取已換算視窗」路徑。

### 2a. 假換算：能否讓 `timeframe_adjustment=="applied"` 但 rolling 鍵未 ×因子（或反之）？

**可構造、已被 T1 抓住。** T1 把注入改成 `_tf_adjust = "applied"` 且不呼叫 `set_timeframe` ⇒ disclosure 寫 applied＋`adjusted_windows` 仍為未換算（因 `_timeframe is None`），實際 rolling 鍵仍 `window_21/63/126` ⇒ `-k window_keys` 紅。反向（真注入但揭露寫 not_applied）無現成 mutation；合法 1h／12h 行為測綠。

### 2b. 合法 12h run 數值／鍵是否只多 `ic_window_disclosure`？

**是。** 獨立覆核：`live` sha＝`363ae1ceebb6`＝現行 pre；剝 `metadata.ic_window_disclosure` 後＝`163c4cecb100`（寫入時舊投影）。disclosure＝`applied`／`adjusted_windows=[21,63,126]`／`icir_role=threshold`。

### 3a. 邊界③④落差：analyze 缺／非法 tf 先 `ValueError`——是否滿足「不靜默換算不揭露」？

**滿足意圖；裁定改 SPEC／TODO 措辭，不補 analyze 層揭露。**

- split-on：`_resolve_expected_freq` 本就要求 timeframe ∈ `EXPECTED_FREQ_BY_TIMEFRAME`（`:161-165`）⇒ 缺／非法在切分 fail-closed，永遠到不了視窗換算（`test_missing_timeframe_fails_closed_before_stage4`／`test_invalid_timeframe_fails_closed_before_stage4`）。
- split-off／引擎單獨：`set_timeframe` 回 `not_applied:*`、視窗不變（`test_engine_set_timeframe_adjusts_windows_and_discloses`）。
- SPEC Task 3.1 邊界③④／TODO 驗證句仍寫「不變＋揭露」＝**過時**；落地註記已描述實況。建議把邊界改成：「split-on ⇒ ValueError（既有切分守衛）；引擎／split-off ⇒ `not_applied:*` 揭露」。

### 3b. 引擎單獨使用時 `not_applied:*` 的消費者；有無靜默路徑？

**消費者＝引擎單測＋任何直呼 `ICEngine` 而未經 analyze 的呼叫端。** 生產主路徑必經 analyze 注入。靜默假換算路徑：缺 tf 時 `_adjust_rolling_windows` 回原窗（不 × reference）——fail-loud 靠回傳值／warning，不靜默套 reference（T2 守住）。

### 4a. 1h golden：值序列 canonical-JSON sha 取代 `atol=1e-12` 是否可接受？

**可接受（決定性 run 下等價；與落地註記一致）。**

- 假紅：跨平台 JSON float 字串化差異、非決定性特徵序、fixture／config 漂移。
- 假綠：只改非 rolling 欄（status／reason）而 golden 未鎖者；或 NaN↔字串經 `default=str` 偶合相同（低機率）。
- 若日後出現浮點漂移 → 改 `np.allclose(atol=1e-12)`（TODO 落地註記已預留 needs-research）。

### 4b. 1h 落 `degraded_full_sample` 時 golden 是否還該鎖 `oos_downgrade.reason`？

**建議鎖（非阻擋合併）。** 現行 golden 含 `analysis_status`／disclosure，測試主斷言只比 keys／lengths／values_sha256；`test_1h_fixture_window_keys_scaled_by_12` 已對 reason ∈ `{rolling_warmup_insufficient, insufficient_data}` 做行為斷言。補強 golden 可防「錯 reason 仍綠」，屬 P3 測試強化，非產品洞。

### 5a. mutation 充分性：一種讓 T1／T2／C1＋M1–M13 全綠的缺陷？

**例：** 把 `set_timeframe` **移到 precheck 之後、stage4 之前**——中等長度 1h run 可能預檢用未換算門檻（131）放行、stage4 才用 1517 降級；1h fixture（極短或極長）與 12h（因子 1）仍綠；T1（整段刪注入）／T2（引擎缺 tf）／C1 不抓「時序錯位」。現行碼注入在 precheck **前**（`:1087`→`:1160`），此為突變缺口敘事，非已證 prod 洞。

### 5b. 紅因＝斷言而非 import／語法？

**是。** 補齊 la0 symlink 後：T1／T2＝`rc=1`；C1＝`rc=0`；無 rc=5／UNCOVERED。

### 6. ≥10× 不必要複雜？

**無。** 一個 `set_timeframe`＋analyze 一處寫 disclosure＋事件路徑只覆寫 `icir_role`；換算邏輯沿用既有 `_adjust_rolling_windows`。

### 7. 可合併嗎？`test_flag_toggles_path` 是否須登記新殘留？

**可合併。** `test_flag_toggles_path`：**須登記殘留**（建議 `TW-RESID-2` 或併入既有 IC1A 殘留表）：

| 欄 | 值 |
|---|---|
| 現象 | `_real_btc_frame()` 預設 180 根 ⇒ 測試段 ~31 ＜ warmup；斷言 `applied is True` 紅 |
| HEAD 實測 | 注入後 `min_test_rows=1517`（1h×12）；fallback `rolling_warmup_insufficient` |
| HEAD~1 | brief 稱亦紅；根因＝fixture 相對**未換算**門檻 131 已不足（31＜131），非本票獨有 |
| 為何現在不做 | `blocked-by: fixture limit=180 對 warmup 先天不足；產品「充足」路徑已由 test_oos_applied_true_when_sufficient（8500 根）覆蓋；修法＝放大 fixture 或 stub precheck，屬測試債` |

---

## §1 必查摘要（11 類；標的＝已實作碼 vs TFWINDOW SPEC Task 3.1／§G／§V）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | SPEC／TODO 邊界③④措辭 vs 實作 fail-closed——裁定改文件（見 3a）；碼與落地註記一致 |
| 2 | 漏項 | 無阻合併漏項；scan cube／sanitizer 見下表 NOT_RUN 覆核摘要 |
| 3 | 不可測 | 驗收＋mutation＋1h／gap2 golden 可證偽 |
| 4 | quant | 1h 視窗×12＝正確化；TW-RESID-1 短史 fallback 已揭露 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 無 |
| 7 | Cache | N/A（refilter 不重算 rolling） |
| 8 | API／相容 | 全域新增 `ic_window_disclosure`（§G 已重凍）；事件路徑只覆寫 `icir_role` |
| 9 | 測試 | tfwindow 6 條＋mutate T1／T2／C1；`test_flag_toggles_path` 既有紅須登記 |
| 10 | Agent 可執行 | 已實作；gate phase 3 PASS（receipt） |
| 11 | 短命工 | 無 |

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| 注入後 precheck 與 stage4 讀同一組換算視窗 | **fact-verified** | 兩者皆 `_rolling_warmup_min_rows`→`_adjust_rolling_windows`；1h 診斷 `min=1517` |
| scan cube 每格經 `analyze` 注入 | **fact-verified** | `ic_analysis_service` 格內 `analyzer.analyze`；`build_cube` 不建引擎 |
| `ic_window_disclosure` 進 sanitizer 不炸 | **fact-verified（讀碼）** | `_sanitize_metadata_for_json` 只動 significance scalar；list／int 原樣通過。`test_survivor_contract` 本輪 **NOT_RUN**（cost） |
| 12h 除 disclosure 外 bit-identical | **fact-verified** | stripped sha＝`163c4cec…`；live＝pre＝`363ae1ce…` |
| 使用者實機 1h／39k 門檻 1517 | **unverified** | brief blocked-by UAT B33 |
| mutation oracle T1／T2／C1 | **fact-verified** | clean clone＋la0 symlink，UNCOVERED=0 |

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
