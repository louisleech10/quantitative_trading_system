# SPLITUNIFY B1＋B2a code review R1（composer）

task-id: `20260911-SPLITUNIFY-B1-REVIEW-R1`  
family: `COMPOSER`  
findings-round: `R1`  
審查對象: B1 commit `9607430d`（`split_unify.json`、契約測試、Task 1.3 基準、D-002、GAP3 索引行）；B2a commit `a58754d6`（`holdout_boundary`／`_as_ms`、`test_splitunify_boundary.py`）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| `holdout_boundary` 目前無生產 caller | **fact-verified** | `grep -rn holdout_boundary momentum api` → 僅 `split_preview.py:61,99` 與 `tests/momentum/core/test_splitunify_boundary.py` |
| 19 vs 20 之差為測試間污染 | **fact-verified → 否；正確解釋是 receipt 過濾** | receipt 摘要 `19 failed`；`^FAILED ` 共 30 行、`grep '::'` 後 19 行真 nodeid（`SPLITUNIFY_SPEC.md:392-394` 已文件化進度條殘片） |
| `_as_ms` 對 tz-aware index 未驗 | **fact-verified（UTC）** | 探針：`holdout_boundary(pd.date_range(..., tz='UTC'))` 與 `tz=None` 同組 `train_end_ms`／`test_start_ms`；非 UTC tz 仍列 brief「我沒查的」，不擋 B2b |
| `tests/baselines/` 被 pytest 收集 | **fact-verified → 否** | `pytest --collect-only tests/baselines/` → 0 items |

## 必答 1–7（明確立場）

### 1. B2a `holdout_boundary` 有無第二份算術？`_as_ms` 三型別／時區？

**無第二份切分算術。** `holdout_boundary`（`split_preview.py:101-111`）之 `split_point` 只經 `holdout_split_point`（`:44-46`）；`test_rows` 只經 `holdout_test_row_index`（`:19-41`）；`train_rows = arange(0, split_point)` 與前者共用同一 `split_point` 變數，非重算公式。`train_end_ms`／`test_start_ms` 僅為 `_as_ms(index, train_rows[-1])`／`_as_ms(index, test_rows[0])`（`:110-111`），與 orchestrator 既有的「由 rows＋index 物化」模式（`ic_filter_orchestrator.py:553-558` `_time_bounds_for_rows`）同類，但**不引入第二套 split 公式**。

**`_as_ms` 行為**（`:49-58`）：`pd.Timestamp`／`np.datetime64` → `int(pd.Timestamp(value).value // 10**6)`；其餘（含 int64 epoch ms index）→ `int(value)`。`test_ms_same_source_accepts_int64_ms_index`（`test_splitunify_boundary.py:91-96`）證 DatetimeIndex 與 int64 ms index 同組 ms。時區：UTC tz-aware 與 naive 同牆鐘 ms 一致（本輪探針）；**刻意不复用** `_normalize_ic_time_index`（`ic_filter_orchestrator.py:269-271` 拒毫秒）符合 SPEC C-4。

**生產路徑**：`holdout_boundary` 尚無 caller（B3 才接線）⇒ 本批不可能改變既有數值。

### 2. `test_rows` 空時 `test_start_ms=None` 下游會踩嗎？分工對嗎？

**現無下游消費**（grep 僅 builder 測試）。**分工正確**：builder 層回 `None`、不 raise（`split_preview.py:111`；測試 `:114-119`），避免 `-1`／`0` 被當 1970 或有值；投影層（B2b）須在取用 ms **之前**先檢查 `test_plan.row_index.size == 0` 並 `raise ValueError("missing_test_plan: …")`（`SPLITUNIFY_SPEC.md:197-198`、D-002 §D2-2 `:44-45`）——**禁與 None 比較**。空段之 fail-closed／event-study-only 由 caller／投影負責，不由 builder raise。

### 3. B1 契約測試算「兩端對證」嗎？

**B1 版弱對證、但非自證迴圈，可接受。** 第二來源為獨立撰寫的 `docs/SPLITUNIFY_SPEC.md` 字面（`test_every_reason_appears_verbatim_in_spec`，`test_splitunify_contract.py:96-109`），外加 `event_import_contract.json` 之 purge reason 交叉（`:89-94`）。測試檔頭已明言 B1 不動生產碼故無 `split_projection.py`（`:3-7`）；B2b 應再加 `test_python_constants_equal_json`（`:112-115` TODO）。判準：JSON↔SPEC 能擋「只改 JSON 不改 SPEC」；不能擋「SPEC 與 JSON 一起錯」——那是 B2b Python 常數對證的職責，符合 Task 1.2 分階設計。

### 4. Task 1.3 基準 19 條可信嗎？與 HANDOFF 20 條差異要處理嗎？

**可信；本批不需再處理。** 碼證：receipt 尾行 `==== 19 failed, 1103 passed …`＋`pytest_rc=1`；`tests/baselines/analysis_known_failures.nodeids` 恰 19 行；`awk '/^FAILED /'` 30 行、`grep '::'` 19 行（SPEC Task 1.3 `:392-394` 解釋 `-q` 進度條殘片）。HANDOFF `:50` 之「20 failed」是 session 盤點敘事（含污染／未過濾），**不是** B1 凍結清單的權威數字；B3 驗收以 nodeid 清單「只准變短」為準，不依賴聚合計數。建議主委順手把 HANDOFF 敘事改「19 條凍結＋進度條過濾」以免再誤導，**不擋 B2b**。

### 5. D-002 覆寫兩條是否對應原檔真實條文？

**對應成立。**

- **B1.3 邊界來源**：D-002 `:12`／§D2-1 之「每 symbol 各自按時間切＋緩衝 ≥ 答案窗」逐字對齊 `docs/GAP3_EVENT_SPEC.md:172`（Task B1.3 改法）；SPLITUNIFY §A2 表（`SPLITUNIFY_SPEC.md:46-49`）亦描述現行 `split_events` 行為。覆寫的是**事件規格鏈**之 B1.3 語意，非 UX 原檔內某 heading 字面——D 延伸慣例允許跨檔指向。
- **事件掃描報告三鍵**：D-002 §D2-5 對 `pipeline.py:728-734`（`run_event_study_only` 寫死 `n_train`／`n_test`／`n_purged` 為 0）與 `EventTablesPanel.tsx:352`（顯示 train 0／test 0）之碼證正確；目標形態與 SPLITUNIFY C-0 決議③（`SPLITUNIFY_SPEC.md:94-100`）一致。

`bash scripts/template_check.sh dext docs/GAP3_EVENT_UX_SPEC.D-002.md` → PASS（本輪複驗）。

### 6. `GAP3_EVENT_UX_SPEC.md` 只動索引行是否合規？

**合規。** `git diff 9607430d^..9607430d -- docs/GAP3_EVENT_UX_SPEC.md` 僅改第 3 行延伸索引，追加 `D-002 docs/GAP3_EVENT_UX_SPEC.D-002.md`；符合 `FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.3「D 延伸對原檔唯一允許改動＝索引行」。

### 7. 可否進 B2b？

**可以。** 判準：B1 契約＋基準＋D-002 無 P0/P1 缺口；B2a boundary builder 同源、M-SU-11 雙向 mutation 守衛就位、無生產接線副作用。

---

## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–7、B1/B2a 審查對象與主委驗收項後無 P0/P1/P2 finding；可進 B2b（投影純函式）。

**碼證**: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/core/test_splitunify_boundary.py` → 17 passed, rc=0；`pytest --collect-only` 19 baseline nodeids → 19 collected, rc=0；receipt `splitunify-analysis-baseline.stdout` 尾 `19 failed`＋`pytest_rc=1`；`grep -rn holdout_boundary momentum api` 無生產 caller；`holdout_boundary` 算術鏈 `split_preview.py:44-111`；mutation 守衛 `-k ms_same_source` → 3 passed；`git diff 9607430d^..9607430d -- docs/GAP3_EVENT_UX_SPEC.md` 僅索引行。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#1bf699fbde5b;docs/GAP3_EVENT_UX_SPEC.D-002.md#92cd70b1f366;momentum/Analysis/contracts/split_unify.json#5ff16a66f2ca;momentum/core/split_preview.py#58a4ef2c7033

[NON-BLOCKING] 信心度=High。核對依據＝必答 1（算術同源＋caller grep）與必答 4（receipt 19／nodeid 19／SPEC 過濾說明）之碼證；B1 JSON↔SPEC 為分階弱對證（必答 3）；D-002 覆寫兩條對 GAP3_EVENT_SPEC B1.3 與 pipeline 現碼。殘差：HANDOFF「20 failed」敘事過期（必答 4）、非 UTC tz-aware 未實測（brief 成本項）——均不擋 B2b。

---

## Verdict：可進 B2b

B1 契約 JSON、SPEC 字面對證、Task 1.3 十九條 nodeid 基準與 D-002 延伸檔均與 SPEC v5 一致；B2a `holdout_boundary` 無第二份算術、M-SU-11 ms/rows 同源測試可證偽。B2b 開工時須補 `split_projection.py` 常數↔JSON 對證，並在投影內實作 `test_plan` 空段之 `missing_test_plan` raise（不得假設 `test_start_ms` 永遠非 None）。

---

ASSUMPTIONS_VERIFIED: contract+boundary pytest 17/17；baseline 19 nodeids collect-only rc=0；receipt 19 failed+pytest_rc=1；holdout_boundary 無生產 caller；D-002 template_check PASS；GAP3 原檔僅索引 diff；UTC tz-aware _as_ms 探針與 naive 一致  
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_contract.py tests/momentum/core/test_splitunify_boundary.py` → 17 passed rc=0；`venv/bin/python -m pytest -q tests/momentum/core/test_splitunify_boundary.py -k ms_same_source` → 3 passed rc=0；`venv/bin/python -m pytest --collect-only -q $(cat tests/baselines/analysis_known_failures.nodeids | tr '\n' ' ')` → 19 collected rc=0；`bash scripts/template_check.sh dext docs/GAP3_EVENT_UX_SPEC.D-002.md` → PASS rc=0；`bash scripts/restore_golden_inventory.sh` → restored  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 review）  
NUMERIC_OR_SCHEMA_IMPACT: none  
TEMP_CLEANUP: `/tmp/workdir` 不存在；`claude-501` 保留  
HANDOFF_OUTPUT: handoffs/20260911-splitunify-b1-review-r1-composer.md

STATUS: DONE
