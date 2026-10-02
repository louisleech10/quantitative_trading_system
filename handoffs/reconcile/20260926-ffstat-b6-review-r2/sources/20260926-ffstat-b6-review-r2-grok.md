# FF-STAT 第 6 批 審查 r2 — grok

task-id: 20260926-FFSTAT-B6-REVIEW-R2
family: grok
findings-round: R2
brief-kind: review
brief: handoffs/20261002-FFSTAT-B6-REVIEW-R2-BRIEF.md
template: templates/COMMITTEE_FINDING_TEMPLATE.md
commit: d3c8d339
round-id: 970ff20a-be5c-43ea-826b-5d47a255e52a

本輪唯讀。未改碼、未改文檔、未 git 寫入。未跑生成型 node。秒級探針在 `/tmp/ffstat_b6_r2_work`，先呼叫 `isolate()`／`isolate_dstar_cache()`。指令列與暫存路徑無家族名。

## 前提

fact-verified: 主委事實 1–3（縮小 C2-1 綠 506s；分母尺度 mutant DID NOT RAISE 已撤；fracdiff 截斷基線 XPASS→一般測試；尾擾動 fracdiff 仍 XFAIL；collect-only 41 node；三 smoke 綠；校準經 `AdapterRegistry.fetch_aligned`，full 側 perturb 同時作用於校準域與公開域預熱）。
assumed: brief ①②③。
→ 否證觀測：①擾動前史使校準前置關卡拋 `CalibrationError` 或 full 側生成失敗；②全量 d* 下兩 run d* 相同；③某 gate 失敗訊息不以表列前綴開頭而被誤拒，或非因果訊息以表列前綴開頭而被誤收。／本輪：③以 helpers 原碼 raise 實例＋`lstrip().startswith(_CAUSAL_GATE_PREFIXES)` 秒級探針否證；①②未跑生成，第二層未否證。

---

## 必答（成對）

### (1a) r1 之放行判斷在 v60 下是否仍成立

不成立。本家 r1 sentinel `GROK-R1-P3-00` 之 proceed（「不阻擋主委獨占實跑」）已被收斂檔部分採納且 proceed 不採；v60 已落地三缺陷改正之本體，但捕獲區前綴表未從各 gate 實際 raise 字面取出，長度耦合（無尾擾）在 d*／欄集合不變時會把 numpy atol 值失敗誤拒，6.5h 全跑會在該控制上紅。

### (1b) 碼證或秒級探針輸出

- 收斂 `handoffs/reconcile/20260926-ffstat-b6-review-r1/synth.md` 群集表：GROK-R1-P3-00 處置「部分採納（proceed 不採：codex 三條 P1 有實證反例）」。
- v60 三改正在 helpers 檔尾：捕獲區外 `_assert_mr_preparation`（`:1493-1503`）＋`pytest.raises` 只包 `check()`（`:1515-1516`）；長度耦合 `lag = max(2, len(df) // 10)` 無 252 上限（`:1712-1713`）且 `assert len(lags) >= 2`（`:1734`）；校準 `patch_fetch_full_only=_patch` 走 `_patch_kline_pre_start_ohlcv`（`:1749-1766`）。
- 前綴否證見 GROK-R2-P1-01：atol 路徑訊息 `lstrip()` 後為 `Not equal to tolerance rtol=0, atol=1e-08`，`accepted=false`。
- `venv/bin/python -m pytest --collect-only -p no:cacheprovider tests/feature_engineering/test_ff_fullchain_truncation_mr.py tests/feature_engineering/test_ff_fullchain_truncation_small_mr.py tests/feature_engineering/test_ff_multitf_truncation_mr.py tests/feature_engineering/test_ff_multitf_truncation_small_mr.py -q` → `41 tests collected in 0.05s` rc=0。
- 三 smoke：`test_b2_sampling_helper_smoke`／`test_multitf_sampling_helper_smoke`／`test_align_lookahead_oracle_smoke` → `3 passed in 0.24s` rc=0。

### (2a) assumed ①②③ 與「我沒查」1–4 是否成立

- ①第二層成立、生成層未驗：真實 kline 1h 20352 列、fracdiff 窗 3342、起始 `2025-12-09 18:00:00`；`_pre_start_rows(..., bars=len(df))` 得 17010 列；`_patch_kline_pre_start_ohlcv` 對那 17010 列 `+1e6` 本身不拋。`CalibrationError` 須生成才現，本輪禁生成型 node。只承認 `_FRACDIFF_PRE_VALUES_PREFIXES`（欄集合／d*），公開域預熱被改不影響判定契約。
- ②未否證：`_resolve_fracdiff_precision` 預設 0.02；trunc 少 10 根。無生成收據證明兩 run d* 必異。若 d* 同且欄集合同，全量 d* 控制走 `_FRACDIFF_PRE_VALUES_PREFIXES`，`pytest.raises` 會 DID NOT RAISE（fail-closed）。
- ③不成立：見 GROK-R2-P1-01。`_assert_values_gate` atol 版、`_assert_warmup_nan_masks_equal`、`_assert_metadata_gate` 三處實際訊息皆不以表列前綴開頭。值 mismatch 自訂字面、columns、d*、fracdiff NaN mask、align oracle 無 mismatch 被收；coverage／sampling 字樣被拒（此五類與主委秒級例一致）。
- 「我沒查」1：對 helpers 原碼逐函式 raise，見 P1-01。
- 「我沒查」2：既有兩檔負控制改呼叫同一 `run_control_*`，只差 `MRScope`（`FULL_SCOPE`／`FULL_MULTITF_SCOPE` vs `SMALL_*`）。除 r1 三改正外，seam 計數改在捕獲區外 `assert calls[0] > 0`（更嚴、fail-closed）；尾擾動／校準／全量 d* 之 fracdiff 控制改只收欄集合與 d*。`FULL_MULTITF_SCOPE.fracdiff_payload` 填 `_multitf_config_payload`（values 設定）；多週期四檔無 `run_control_fracdiff_*` 呼叫、`_build_scope_pair(..., fracdiff=True)` 在 multitf 路徑無呼叫點，現況無誤用。helpers 仍留 `run_control_denominator_scale_full_column`，四測試檔皆未呼叫（與 v60 撤除一致）。
- 「我沒查」3：去上限 `max_lag` 334／333。權重寬度於 d≤0.72 時 334 vs 333 綁定（n0>333）；d≥0.73 自然長度 <333，兩邊同為自然長度、mutant 的 `len(lags)>=2` 仍可因 `len(df)//10` 不同而過，權重長度相同。`_frac_diff_ffd(..., max_lag=334)` 於 n=500 剩 167 finite、n=3342 剩 3009 finite，不拋。超過權重／序列限制而拋錯之路徑第二層未現。
- 「我沒查」4：`_build_scope_pair` 預設 `window_date_fn or _bar_window_dates`（`:1558`）；對齊控制顯式 `_bar_window_dates_at_12h_boundary`（`:1681`）。本 cache 最後一根落 12h 邊界，預設日期與 12h 邊界日期重合。與既有「基線用 `_bar_window_dates`、對齊用 12h 邊界」一致。

### (2b) 依據

- 前綴探針 `/tmp/ffstat_b6_r2_work/probe_gates.json`（isolate 後直接呼叫 helpers 閘）：`numpy_fracdiff_values.accepted=false`；`warmup_nan_helper.accepted=false`（msg=`warmup f.parquet::col NaN mask mismatch`）；`metadata_rowcount.accepted=false`（msg 空字串）；`metadata_tf_missing.accepted=false`（`present_timeframes missing '4h'`）；`values_mismatch_helper.accepted=true`；`columns_strict_real.accepted=true`；`d_star.accepted=true`；`fracdiff_nan_mask.accepted=true`；`coverage_design`／`coverage_guard`／`sampling_guard` 含非因果 marker、`accepted=false`。
- 修法可行性探針：自訂 `fracdiff values f.parquet::col values mismatch...` → accepted true；`warmup NaN mask f.parquet::col mismatch` → true；`metadata gate: present_timeframes missing '4h'` → true。numpy 頭 `Not equal to tolerance rtol=0, atol=1e-08` → false。
- kline／窗：1h 20352；fracdiff 窗 3342 start `2025-12-09 18:00:00`；pre_start_all=17010；small_values 窗 3594；small_multitf 窗 12786。
- 權重：d=0.72 n0=339 故 334≠333 綁定；d=0.73 n0=323 兩邊皆 323。

### (3a) 可否據此全跑（約 6.5 小時，串行、獨占）

不可。長度耦合截斷／並行控制（`allowed=_CAUSAL_GATE_PREFIXES`）在欄集合與 d* 不變時，預期靠 fracdiff 值閘抓 mutant；該閘 atol 分支丟出的 numpy 訊息會被前綴表誤拒，測試紅在「失敗不屬因果 gate」，6.5h 會在此停下。屬 fail-closed（不是漏測假綠），仍會消耗獨占時段後得到不可用收據。

### (3b) 擋之 P0／P1

GROK-R2-P1-01

---

## GROK-R2-P1-01

**斷言**: `_CAUSAL_GATE_PREFIXES` 未覆蓋 `_assert_values_gate` atol 分支、`_assert_warmup_nan_masks_equal`、`_assert_metadata_gate` 三處實際 AssertionError 字面；長度耦合（無尾擾）在 d*／欄集合不變時會把 numpy atol 值失敗誤拒為非因果，負控制紅在前綴檢查而非收據中的因果 gate。

**碼證**: 隔離後直接呼叫 helpers 閘：`np.testing.assert_allclose` atol=1e-8 訊息 lstrip 後為 `Not equal to tolerance rtol=0, atol=1e-08`，`startswith(_CAUSAL_GATE_PREFIXES)` false；warmup 實際 `warmup {file}::{col} NaN mask mismatch` 不以 `warmup NaN mask` 開頭；metadata `assert trunc_rows < full_rows` 訊息為空字串、`present_timeframes missing` 不以 `metadata gate` 開頭。值自訂字面／columns／d*／fracdiff NaN mask 被收；coverage／sampling 被拒。collect-only 41 node 0.05s；三 smoke 3 passed 0.24s。
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:1040
MUTATION: 隔離複本內對 `_assert_values_gate` 的 atol 分支餵入相差 0.1 的兩段 finite 陣列（`np.testing.assert_allclose([1.,2.],[1.,2.1],atol=1e-8,rtol=0,err_msg="fracdiff values 1h_L65.parquet::col")`）；將捕獲訊息經 `message.lstrip().startswith(_CAUSAL_GATE_PREFIXES)`（helpers:1520）得到 False。把該分支改呼叫既有 `_assert_arrays_values_close(..., context="fracdiff values 1h_L65.parquet::col")` 後，同輸入之自訂字面 `fracdiff values ... values mismatch...` 判定 True。warmup 將 context 改為以 `warmup NaN mask` 開頭、metadata 將失敗包成 `metadata gate: ...` 後同判定 True。禁止把前綴放寬成 `Not equal to tolerance`（會誤收無關 numpy 失敗）。

**類別**: code-contract

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#9c98ca5e8002; docs/FFSTAT_SPEC.md#ed060ae4ef80; handoffs/reconcile/20260926-ffstat-b6-review-r1/synth.md#062ca5d18b00; handoffs/20261002-FFSTAT-B6-REVIEW-R2-BRIEF.md#7206d0429f24

正文：v60 捕獲區只收「因果 gate 前綴」之 AssertionError，SPEC 列了欄集合、值、NaN mask、metadata、d*、fracdiff 值、對齊 oracle。前綴表（`:1457-1465`）為 `"columns gate failed"`／`"values "`／`"warmup NaN mask"`／`"metadata gate"`／`"d_star mismatch"`／`"fracdiff "`／`"align lookahead oracle: no coarse column mismatch"`。`_expect_causal_gate_failure`（`:1518-1520`）對 `str(excinfo.value).lstrip()` 做 `startswith`。

實際 raise 與表不一致的三處：

1. `_assert_values_gate` atol 分支（`:1034-1046`，`FRACDIFF_ATOL=1e-8`）走 `np.testing.assert_allclose(..., err_msg=f"fracdiff values {fname}::{col}")`。numpy 把 err_msg 放在「Not equal to tolerance…」之後；`lstrip()` 去掉前導換行後開頭是 `Not equal to tolerance`，對不上 `"values "` 也對不上 `"fracdiff "`。同一函式無 atol 時走 `_assert_arrays_values_close`，context=`values {fname}::{col}`，開頭 `"values "`，被收。fracdiff NaN mask 字面 `fracdiff NaN mask {fname}::{col}` 對上 `"fracdiff "`，被收。
2. `_assert_warmup_nan_masks_equal`（`:899-903`、`:920-923`）context=`warmup {fname}::{col}`，失敗為 `warmup {fname}::{col} NaN mask mismatch` 或 `warmup {fname}::{col} values mismatch...`，對不上 `"warmup NaN mask"`。
3. `_assert_metadata_gate`（`:1060-1086`）裸 `assert`：列數比較失敗訊息為空；缺 tf 為 `present_timeframes missing {tf!r}`。皆對不上 `"metadata gate"`。

操作序列（長度耦合截斷／並行，無尾擾）：`run_control_fracdiff_maxlag_len_coupling`（`:1704-1738`）`allowed=_CAUSAL_GATE_PREFIXES`，`check=_assert_fracdiff_truncation_invariants`。閘順序：strict 欄集合 → d* → atol 值 → warmup → metadata。主委已改截斷基線為一般測試（值閘在正常路徑應綠）。mutant 注入 334 vs 333；若 d* 與欄集合不變（precision 0.02、差 10 根），預期抓手是 fracdiff 值差異。值閘一響，numpy 訊息被 `:1520` 再 assert 成「失敗不屬因果 gate」，測試紅，收據拿不到因果字面。尾擾動長度耦合／校準／全量 d* 只用 `_FRACDIFF_PRE_VALUES_PREFIXES`（欄集合／d*），值閘本就不算抓到，不走本條操作序列。L3／縮尾／L4／對齊走 `_values_check` → `_assert_values_gate_main` 自訂 `"values "` 字面，主路徑被收；warmup／metadata 只在值閘已過、這兩閘先失敗時才誤拒。

威脅模型：此條是誤拒（fail-closed），不是把 coverage／sampling 當抓到的假綠。假綠路徑未在本探針出現。獨占 6.5h 若在長度耦合值差異上紅，收據不可用。

修法（不新增機制、不放寬容差、不改前綴去吃 numpy 頭）：atol 分支改呼叫既有 `_assert_arrays_values_close(..., context=f"fracdiff values {fname}::{col}")`，字面開頭 `"fracdiff "`。warmup 的 context 改為以 `"warmup NaN mask"` 開頭（或把表列前綴改成實際的 `"warmup "`，只動字面對齊）。metadata 各失敗改 `raise AssertionError(f"metadata gate: ...")`，對上已有前綴。可行性：同輸入自訂字面探針 accepted true；numpy 頭 accepted false。不把 `"Not equal to tolerance"` 加進前綴表。

影響：單週期既有檔與縮小檔之 `test_*mutation_fracdiff_maxlag_len_coupling_truncation_fails` 與 `*_parallel_fails`（四 node）。多週期無 fracdiff 控制。基線與 L3／縮尾／L4／對齊主路徑不受 numpy 頭影響。

VERDICT: blocked
BLOCKED-BY: GROK-R2-P1-01
CLOSED:
