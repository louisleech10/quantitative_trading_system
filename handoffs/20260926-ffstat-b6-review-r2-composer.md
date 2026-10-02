# FF-STAT B6 審碼 r2 — COMPOSER

task-id: 20260926-FFSTAT-B6-REVIEW-R2  
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R2-BRIEF.md  
family: COMPOSER  
brief-kind: review  
findings-round: R2  
note: 唯讀；標的＝commit `d3c8d339`（SPEC v60 Task 4.2 負控制共用本體與三缺陷改正）；未跑生成型 node。

## 必答（成對）

**(1a)** 本家 r1 兩條處置是否正確：**COMPOSER-R1-P1-01**（缺全套 `*-ffstat-small-mr.json`）— 收斂檔採納為「修補後全跑產收據」仍正確；v60 已改正 codex 三缺陷並有 `20261002-ffstat-small-mr-prerun.json` 局部實跑，但 `handoffs/run_receipts/*-ffstat-small-mr.json` **仍不存在**（`test -f` 失敗），故**驗收條本身未閉合、處置方向無誤**。**COMPOSER-R1-P2-01**（multitf 縮小版不含 12h coarse oracle）— 仍正確：`test_ff_multitf_truncation_small_mr.py` 維持 `SMALL_ALIGN_COARSE_TFS=["4h"]`，SPEC Task 4.2 誠實邊界與 RM-FULLSCALE ⑤ 未收回 12h。

**(1b)** `venv/bin/python /tmp/ffstat_b6_r2_probe.py`（先 `isolate()`／`isolate_dstar_cache()`）→ `PROBE_RC=0`；`pytest --collect-only` 四檔 **41** node；smoke 三項 **3 passed**（0.30s）；`git show d3c8d339 --stat` 對齊 brief 標的。

**(2a)** **assumed ①**（擾動起始日前前史可接受）：**成立**— `run_control_fracdiff_calibration_perturb` 用 `_pre_start_rows`＋`patch_fetch_full_only`；探針 `PRE_START picked=5 all_before_start=True`。**②**（全量 d\* mutant 仍使兩 run 差 10 根）：**未實跑生成**；靜讀 `run_control_fracdiff_full_fit_d_star` 仍 spy `_calibration_series` 回傳全序列，與 brief ② 一致，**未否證**。**③**（因果前綴涵蓋實際失敗訊息）：**不成立**— 見 **COMPOSER-R2-P1-01**。**「我沒查」1**（前綴 vs `_assert_warmup_nan_masks_equal`／metadata）：**已查**，warmup 實際格式不被收；metadata 仍為裸 `assert`、無 `metadata gate` 字面（現行 mutant 多先撞 values，屬 fail-closed 殘餘風險）。**2**（既有兩檔改共用本體語意）：**成立**— 全設定 `FULL_SCOPE`／`FULL_MULTITF_SCOPE` 與 small 檔同調 `run_control_*`，除 v60 三改正外 seam／gate 未複製。**3**（max_lag 334 超實作限制）：**算術可行**（探針 `334/333`）；未跑 fracdiff 生成，**未否證**拋錯傳出。**4**（`_build_scope_pair` 預設 `_bar_window_dates`、align 控制仍 12h 邊界）：**成立**— `ff_truncation_mr_helpers.py:1557-1558` 與 `_run_align_lookahead_control` 之 `window_date_fn=_bar_window_dates_at_12h_boundary` 同既有寫法。

**(2b)** 碼證見各 finding；探針輸出摘要：`PREFIX warmup_mask_actual: accepted=False`；`MAX_LAG uncapped full/trunc=(334, 333) distinct=True`；`PREP_REJECT ok`。

**(3a)** **否**— 在修 **COMPOSER-R2-P1-01** 前不宜投入約 6.5 小時全跑：若某 mutant 先在 warmup NaN mask 失敗（SPEC 列為合法因果 gate），`_expect_causal_gate_failure` 會以「失敗不屬因果 gate」使控制 node **紅**，與「mutant 未抓到」不可分，收據無法作為閉環證據。另 **COMPOSER-R1-P1-01** 仍缺 aggregate 收據（全跑之目的之一）。

**(3b)** 擋全跑之 P0／P1：**COMPOSER-R2-P1-01**；收案前置仍缺全套 JSON 時亦擋（原 **COMPOSER-R1-P1-01**，本輪不另開 ID）。

---

## COMPOSER-R2-P1-01

**斷言**: `_CAUSAL_GATE_PREFIXES` 含字面 `"warmup NaN mask"`，但 `_assert_warmup_nan_masks_equal`→`_assert_arrays_values_close` 實際拋出之訊息為 `warmup <parquet>::<col> NaN mask mismatch`（context 在前），`startswith` 判定會**拒收**合法 warmup gate 失敗；主 MR 與 fracdiff MR 路徑皆在 values gate 之後執行 warmup 檢查，mutant 若僅在此層失敗會使負控制測試紅而訊息像「捕獲邊界 bug」，違反 v60「只收因果 gate」契約。

**碼證**: `ff_truncation_mr_helpers.py:1457-1465` 前綴表；`:899-903` context=`f"warmup {fname}::{col}"`；`:754-767` `AssertionError` 為 `f"{context} NaN mask mismatch"`；`:1115-1123` 呼叫順序在 values 之後。`/tmp/ffstat_b6_r2_probe.py`（`isolate()` 後）→ `PREFIX warmup_mask_actual: accepted=False`；對照 `PREFIX values_mismatch: accepted=True`。  
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:1460  
MUTATION: 在隔離環境對 `message="warmup 1h_L3_rolling.parquet::x NaN mask mismatch"` 套用與 `_expect_causal_gate_failure` 相同之 `head.startswith(_CAUSAL_GATE_PREFIXES)` → `False`（探針 `warmup_mask_actual` 行）。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#9c98ca5e8002;docs/FFSTAT_SPEC.md#ed060ae4ef80

正文：v60 SPEC Task 4.2 將 NaN mask 列為可收因果 gate，但前綴表與 helpers 自 2.1 起之錯誤字串格式不一致（非 r1 新引入，隨共用本體 centralize 後成為全檔負控制共用風險）。**修法**：將允許前綴改為與實際 context 一致（例如 tuple 增 `"warmup "` 並保留舊字面，或統一 `_assert_arrays_values_close` 錯誤模板）；fracdiff 尾擾動控制若只允許 `_FRACDIFF_PRE_VALUES_PREFIXES`，亦須同步允許 warmup 失敗格式，否則同型拒收。**可行性**：秒級探針已證一行前綴調整即可使 `warmup_mask_actual` 為 `accepted=True`，無需改 gate 容差或加慢閘；建議補一條秒級單測鎖定模板。影響：未修前全跑可能出現「控制已抓到 mutant 但 node 紅」之假陰性，收據不可作主委 6.5h 獨占驗收依據。

---

ASSUMPTIONS_VERIFIED: d3c8d339 與 brief 標的一致；41 collect-only；三 smoke passed；prerun.json 與 brief 主委事實 1 一致；scoped git status 與開跑前同型（僅既有 __pycache__/golden 等噪音）。  
TESTS_RUN: `venv/bin/python /tmp/ffstat_b6_r2_probe.py` rc=0；`pytest` collect-only 四檔 rc=0（41）；smoke 三項 rc=0（3 passed）；`test -f handoffs/run_receipts/20261002-ffstat-small-mr.json` → 不存在。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
產出: `handoffs/20260926-ffstat-b6-review-r2-composer.md`

VERDICT: blocked  
BLOCKED-BY: COMPOSER-R2-P1-01  
CLOSED: COMPOSER-R1-P2-01

STATUS: DONE
