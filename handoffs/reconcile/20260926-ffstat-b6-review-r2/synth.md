# Reconcile — 20260926-ffstat-b6-review-r2

**來源** 20260926-ffstat-b6-review-r2-codex.md, 20260926-ffstat-b6-review-r2-composer.md, 20260926-ffstat-b6-review-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/FFSTAT_SPEC.md

三家各一條 P1、同一缺陷（主委於派出後亦自查得之）：`_expect_causal_gate_failure` 以訊息前綴判定，誤拒三個因果 gate 之真實失敗——warmup NaN mask（訊息為 `warmup <檔>::<欄> ...`）、fracdiff atol 值 gate（numpy `Not equal to tolerance`）、metadata gate（裸 assert）。codex 以原 gate 對小 parquet 重現三例 REJECT。修法（v60 同版修正）：改以 traceback 之函式名對封閉集合判定（`_CAUSAL_GATE_FUNCS`；尾擾動 fracdiff／校準擾動／全量 d\* 三控制為 `_FRACDIFF_PRE_VALUES_GATES`＝strict 欄集合與 d\*），路徑經 `_assert_mutation_layer_coverage` 或訊息含覆蓋守衛字樣者拒；不改任何 gate 之判準與訊息（codex 所提「於 gate 補診斷標籤」不採，因函式名判定為封閉可導出集合、不需改既有 gate）。新增秒級測試 `tests/feature_engineering/test_ff_truncation_capture_boundary.py` 9 項以真實 gate 函式驗收／拒正反例（9 passed）。r1 閉合：codex CLOSED 本家三條（真實 K 線 lags 334／333、前史擾動 17,010 列公開域 0 列、缺 L4 傳出），composer CLOSED 本家 P2。codex 另指 assumed ②（全量 d\* 必使 d\* 不同）未驗——該控制只收 strict 欄集合／d\*，若兩者皆同將紅而非假綠，交全跑收據判定。

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 | 類別 |
|---|---|---|---|---|
| 捕獲誤拒：`_expect_causal_gate | P1 | CODEX-R2-P1-01 | 採納（改函式名封閉集合判定；不改 gate 訊息；新增秒級邊界測試） | code-contract |
| 捕獲誤拒：`_CAUSAL_GATE_PREFIX | P1 | COMPOSER-R2-P1-01 | 採納（同上） | code-contract |
| 捕獲誤拒：`_CAUSAL_GATE_PREFIX | P1 | GROK-R2-P1-01 | 採納（同上） | code-contract |

Verdict: 需修補後合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01

**斷言**: `_expect_causal_gate_failure` 拒收三種實際因果 gate 失敗（warmup mask、fracdiff atol values、metadata），因此正確抓到 mutant 的控制仍可被判紅；brief assumed ③ 不成立。

**碼證**: helpers:903-908／931-936 傳入 `context=f"warmup {fname}::{col}"`，實際為 `warmup 1h_L3.parquet::close_fracdiff NaN mask mismatch`，不是白名單的 `warmup NaN mask`；helpers:1036-1042 使用 `np.testing.assert_allclose(..., err_msg="fracdiff values ...")`，實際訊息先是換行＋`Not equal to tolerance rtol=0, atol=1e-08`，lstrip 後仍不是 `fracdiff `；helpers:1061-1093 的 metadata assertions 多數無訊息，其他以 `present_timeframes missing`／`config_used.timeframes.training missing` 開頭，均不是 `metadata gate`。複本命令 `PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/ffstat_b6_r2_check/probe.py --collect` rc=0：呼叫原 gate 取得三個 AssertionError，再餵原捕獲器，三者均 `REJECT`；主 values 與 d_star 正例 `ACCEPT`；準備／coverage 反例 `REJECT`。
CODE-ANCHOR: tests/feature_engineering/ff_truncation_mr_helpers.py:1520
MUTATION: 在隔離複本建立 full parquet `close_fracdiff=[0,1,2]`、trunc parquet `[NaN,1,3]`，直接呼叫 `_assert_warmup_nan_masks_equal(...,warmup=1,n_trunc=3)` 與 `_assert_values_gate(...,warmup=1,n_trunc=3,atol=1e-8)`；另以 manifest symbol A／B 呼叫 `_assert_metadata_gate`；將各原生 AssertionError 訊息交給 `_expect_causal_gate_failure`（秒級探針只略過其準備步驟，以單獨測捕獲邊界），三者皆被當成非因果 gate 拒收。

**來源摘要**: tests/feature_engineering/ff_truncation_mr_helpers.py#9c98ca5e8002

**類別**: code-contract

影響：serial／parallel 長度耦合截斷控制允許 fracdiff values 失敗，卻不能收下原 atol gate 之真實訊息；其他控制若先在 warmup mask 或 metadata 抓到差異，同樣假紅。這是可重現的捕獲契約缺陷，不代表某一生成型 node 已實跑失敗，也不是假綠。尾擾動 fracdiff 控制仍須拒收 values，不受本修法放寬。

修法：在既有 gate 補一致的因果診斷標籤，保留原斷言與數值容差；warmup 白名單與原 `warmup <file>::<column>` context 對齊；atol gate 捕獲其 `np.testing.assert_allclose` 的 AssertionError 後以 `fracdiff values gate failed: ...` 重拋；metadata 每個 assert 補 `metadata gate failed: ...`。這需要明示擴大「既有 helpers gate 不改」的 scope 到診斷訊息，不增加機制、不改 gate 判準、不把 numpy 的通用 `Not equal to tolerance` 廣泛加入白名單。

修法可行性：同命令 rc=0，僅於 `/tmp` 探針將 metadata 函式 AST 的 assert message 補標籤、用 wrapper 為原 numpy AssertionError 補 fracdiff 標籤、warmup allowed prefixes 改為 `warmup `；同三個失敗皆輸出 `FIX_FEASIBILITY ACCEPT warmup/atol/metadata`。原 gate 仍因相同輸入拋 AssertionError，容差與比較內容完全保留。此為秒級診斷修法證據，不是完整生成驗收。準備檢查在捕獲區外之結構維持，sampling／coverage 反例仍不可作 mutant 成功。

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
