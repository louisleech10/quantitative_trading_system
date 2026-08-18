# GAP-2 B1 code review｜task-id=20260818-GAP2-B1-REVIEW-R12｜family=codex

Review target: commit `022650ff`; 只審查 B1 新增檔，未改 code／SPEC／TODO／commit／push。
Verdict：需修補後進 B2；無 P0；6 個 P1、2 個 P2。

## 段 A — 契約符合度

Task 1.0：loader 缺檔／壞 JSON／多鍵／少鍵／`allowed != [false]` 皆 fail-closed；`_doc` 的 (a)(b)(c)、24 個 TODO 頂層鍵、`survivor_file_keys` 24 鍵與物件層 `additional_properties:false` 均核對通過。另見 P1-01/P1-02 與 P2-08。
Task 1.1：normal scores、空 basis、共線 basis、NaN gate、欄數 gate 與 Python 3.9 相容性通過。
Task 1.2：主計算、fit-on-train、退化 gate、排序、預算與結果鍵集通過；section／label-degenerate 語意見 P1-04/P1-05；契約 SoT literal 見 P1-02。
Task 1.3：十條唯一對映與鎖／備份／還原流程通過；probe 實跑見段 C。

## 段 B — 實作期決定複核

① 空 removed 視角以 `ok` 表示可接受的暫定封閉方案，但 section parent gate 必須保留；所有候選均不可算時目前仍回 `ok`，見 P1-04。
② `views` 缺子 schema，B3 前需補 A1-7，見 P1-03。③ `conditioning_set` 是審計必要欄，保留。④ train 借用 `min_test_rows` 符合 Frozen TODO，無 finding。
⑤ 常數 label 會產生 `status=ok` 加全 null 指標，需修正或新增契約 reason，見 P1-05。⑥ block_len 截 n、全非有限回 null、n_bootstrap<1 raise 均可接受。
⑦ Params defaults 與 B4 顯式 config／FAST fixture 相容。⑧ full_sample 的 None masks 是顯式 fit_scope 下的省略值，不是由 masks 猜測。
⑨ `with_root` 只作測試 helper；production root 仍由 orchestrator 注入，未另列 finding。⑩ Task 3.1 權利欄位均有 pointer，唯 views 子物件 schema 缺口見 P1-03。

## 段 C — 測試品質

`bash scripts/gap2_mutation_probe.sh --batch B1` rc=0：baseline/post-restore 各 39 passed，V-1/V-2/V-3/V-4/V-5/V-6/V-17a/V-18/V-21/V-22a 均 `RED rc=1 FAILED=1` 且 `RESTORED GREEN`；`mutation_probe_check` rc=0（3 probes）。V-5 fixture 真區分：order=`['s','f','w']`，train abs IC `w=.0203213,s=.4940813,f=.4712512`，test abs IC `w=.515189,f=.499590`。
O7 test-fit seam 能抓錯擬合，但依 shape 注入，敘述與證據保留於測試內；O7 reference 未 import production primitives。O1b 實際走非退化／閾值分支（`ok`, marginal=`0.000184867546`）。V-3 與 bootstrap 測試缺口見 P1-06/P2-07。

## 段 D — 數值正確性

`O2 marginal=.385256601314`、`gross=.391081651770`、Δ=`-.005825050456`；O7 marginal=`-.513101585196`、獨立 train reference exact、test-fit=`-.010112438520`，差=`.502989146675`；train-insample 與 test 差=`.508079488838`。負 gross ratio、normal scores、r2、moving-block paired index 均通過核對。

## 段 E — registry 殘留觸發

本 commit 僅新增 B1 契約／純函式／測試／探針；未改 ML bridge、forward-stepwise policy、xsec #4 或 holdout/nested 主線，因此 G2-R1/R2/R3/R5 觸發條件均未成立。

## CODEX-R12-P1-01

**斷言**: `load_survivor_contract()` 回傳可被 caller 原地改寫的 mutable global singleton，後續呼叫會直接看到被竄改的契約。

**碼證**: `survivor_contract.py:56,70-71,102-104` 使用 `_contract_cache` 並原樣回傳；實跑 `venv/bin/python -c '... c["version"]=999; print(...)'` → `original 1 subsequent 999 same_object True`。修法：移除 cache，或使用 mtime/version key 並對 cache 與回傳值 deep-copy；既有 `strategy_validation/contract.py:54-56,100-117` 已採此防護模式。

**來源摘要**: momentum/Analysis/survivor_contract.py#5d885dbaf7f8

P1，信心度=10/10。長駐 process 中任一 consumer 可污染所有後續計算的 SoT、枚舉與 reason；這也新增違反 CLAUDE Rule 8 的 mutable global singleton。

## CODEX-R12-P1-02

**斷言**: reason 字面仍複列於 `marginal_ic.py`，`_reason()` 只驗 caller literal membership，並未從契約取得該語意對應的 value。

**碼證**: `marginal_ic.py:372,394,416,420,425,473,494` 實際命中 `no_holdout_split`、`no_survivors`、`candidate_budget_exceeded`、`insufficient_*`、`residual_degenerate`、`insufficient_rows`；重跑 `git show 022650ff:momentum/Analysis/marginal_ic.py | rg -n '"(no_holdout_split|insufficient_test_rows|insufficient_train_rows|no_survivors|candidate_budget_exceeded|insufficient_rows|residual_degenerate)"'` 得 7 命中。契約 reason 改名／重排時，程式會 KeyError 或不再遵循 SoT。修法：以契約 resolver 的結構化 pointer／索引取值，避免在此檔複列輸出 literal。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

P1，信心度=10/10。這直接違反 brief 要求的 reason grep=0 與 TODO §0 JSON SoT，B2/B3 擴增 reason 後會形成漂移風險。

## CODEX-R12-P1-03

**斷言**: `marginal_ic_section_keys.views` 只有 `type=object`，沒有描述 `{status, reason}` 子物件的 `views_keys`；B3 遞迴 validator 無法依契約 fail-closed 驗證 view entry 的鍵集。

**碼證**: `ic_survivor_contract.json:171-195` 的 `section_keys.views` 只有 object 宣告，整檔沒有 `views_keys`；`test_marginal_ic.py:336-353` 只驗 `set(d["views"].keys()) == view_values`，不驗每個 view entry 的 exact keys。修法：A1-7 增 `views_keys`（至少 `status`／`reason` 及其 nullable/type），再讓 B3 validator 套用 additional-properties gate。

**來源摘要**: momentum/Analysis/contracts/ic_survivor_contract.json#ed2872020c6e；tests/momentum/Analysis/test_marginal_ic.py#60860d0762d5

P1，信心度=10/10。若 B3 以現有契約遞迴，`views.loo.typo` 等未知欄無 schema 可拒；若 B3 另寫欄表，則再次違反 JSON SoT。

## CODEX-R12-P1-04

**斷言**: 所有候選都不可計算時，section 仍為 `status="ok", reason=null`，B4 依 section status 會把無任何可用 IC 的結果當成可畫表結果。

**碼證**: `marginal_ic.py:531-558` 先把未超 budget 的 view 無條件標 `ok`，`any_ok` 只檢 view status，不檢 view 內 candidate status；反例 `venv/bin/python -c '... df["c"]=1.0; r=_run(...,["c"])'` → `section ok None`、三 view 均 `ok`、`per_feature.c.status=not_computed reason=residual_degenerate`。修法：section/view status 應反映至少一筆真正 computed result，或新增明確 no-computable reason 並在 B4 消費端處理。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

P1，信心度=10/10。這是 brief 段 B-1 指定的前端語意邊界，現行 parent status 無法區分「view 執行成功但零資料」與「至少有一筆 IC」。

## CODEX-R12-P1-05

**斷言**: test label 為常數時，`_spearman()` 回 NaN 會被轉成 null，但 `_one()` 仍回 `status="ok", reason=null`，所有 IC 欄位可同時為 null。

**碼證**: `marginal_ic.py:261-265` 對常數 label 回 NaN，`253-259` `_finite_or_none` 轉 None，`510-523` 固定回 status ok；反例 `venv/bin/python -c '... y[:]=1.0; ...'` → section `ok None`，`f.status=ok`、`marginal_ic/gross_ic/ratio/train_insample/ci95` 全為 null。修法：在契約增 label-degenerate reason，或將此候選／section fail-closed 為 not_computed。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792；momentum/Analysis/contracts/ic_survivor_contract.json#ed2872020c6e

P1，信心度=10/10。下游看到 `status=ok` 會把不可定義的 IC 當成成功計算，而既有三個 feature reason 沒有說明原因。

## CODEX-R12-P1-06

**斷言**: V-3 的 mutation oracle 不能證明 marginal IC 使用 Spearman；全域替換 `_spearman` 為 Pearson 後，O6 的 marginal invariance 仍成立，探針主要由 raw `gross_ic`／ratio 變化而轉紅。

**碼證**: mutation mapping `gap2_mutation_probe.sh:48` 將 `_spearman` 全域替成 `pearsonr`；`test_o6_rank_invariance:236-248` 同時斷言 marginal、gross、ratio。隔離 in-memory mutant 實跑顯示 Pearson 下 transform 前後 marginal delta 對 `s1/s2/f` 均 `0.0`，但 `s1` gross delta=`-0.06748018535006645`、ratio delta=`0.28798489153934725`。修法：新增非線性 association fixture，直接以獨立 `stats.spearmanr(r_te,y_te)` 對 line 495 的 marginal oracle，或只 mutate marginal call site。

**來源摘要**: scripts/gap2_mutation_probe.sh#3d6173c29ad6；tests/momentum/Analysis/test_marginal_ic.py#60860d0762d5

P1，信心度=10/10。現行 receipt 的 V-3 RED 不能支持「秩相關實作被保護」這個品質 claim，屬高風險數值測試的 false coverage。

## CODEX-R12-P2-07

**斷言**: O9 bootstrap 測試允許完全不重抽資料的 point-estimate mutant 通過，因此未驗 moving-block resampling 本身。

**碼證**: `test_marginal_ic.py:286-298` 只驗 CI 含點估、同 seed exact、`block_len=0` raise；in-memory mutant `block_bootstrap_ci -> (stat_fn(*arrays), stat_fn(*arrays))`（仍保留非法參數 raise）實跑 → `point-estimate bootstrap mutant: test_o9_bootstrap_seed_determinism PASS`。修法：加入固定 seed 的非平凡 resample golden／至少斷言 block index 改變會改變 statistic，並保留 paired-index oracle。

**來源摘要**: tests/momentum/Analysis/test_marginal_ic.py#60860d0762d5；momentum/Analysis/marginal_ic.py#a5de8252b792

P2，信心度=10/10。現行 V-6 只驗 seed 是否被忽略，不能封鎖「seed 有讀但永遠回原樣本」的 bootstrap 假實作。

## CODEX-R12-P2-08

**斷言**: loader 與 test 各自複列完整 top-level key table，與 TODO §0「欄位名只在 JSON SoT、其他處只准 pointer」不一致。

**碼證**: `survivor_contract.py:27-53` 的 `SURVIVOR_CONTRACT_TOP_KEYS` 逐字列 24 鍵；`test_survivor_contract.py:41-50` 再列一份同樣 24 鍵，且 JSON 本身為第三份來源。修法：以不重複欄名的版本化 canonical key-set digest／專用 schema pointer 實作 exact drift gate，並讓測試只驗該 gate；若委員會裁定 top-level allowlist 是必要例外，需在 A1-7 明文豁免，否則目前是 SoT 違規。

**來源摘要**: momentum/Analysis/survivor_contract.py#5d885dbaf7f8；tests/momentum/Analysis/test_survivor_contract.py#70d48152b033；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

P2，信心度=9/10。這不改現有數值，但會讓 B4 增鍵必須同步修改多處非 JSON 表，違反本批要求的單一來源可演進性。

ASSUMPTIONS_VERIFIED: 目標 commit／SPEC R7／AMENDMENTS A1／TODO Frozen 已讀；Python 3.9.6；R1 import grep=0；V-5 train/test 排序可區分；O7 reference 獨立；O1b 走 threshold branch；G2-R1/R2/R3/R5 觸發均未成立。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` = 10 passed/1 deselected；`venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` = 28 passed；`bash scripts/gap2_mutation_probe.sh --batch B1` = rc=0、10/10 RED+RESTORED GREEN、baseline/post 39 passed；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py` = PASS；`bash -n scripts/gap2_mutation_probe.sh` = rc=0。
FAILURES_SEEN: 初始發現 stale probe lock（owner pid 5387 已不存在）；未修改 code，重跑 probe 最終 rc=0 且 lock absent。
SCOPE_CHANGES: 只新增本 review 產出與本次 probe receipt；未改 code／測試／SPEC／TODO／data_cache／git history，未 commit／push。
NUMERIC_OR_SCHEMA_IMPACT: 審查未修改數值或 schema；P1-03/P1-04/P1-05 與 P2-08 為 schema/status SoT 風險，P1-06/P2-07 為 oracle coverage 風險。
TMP_CLEANUP: `/tmp/workdir` 與 `/private/tmp/workdir` 均不存在；`/private/tmp/claude-501` 保留。
HANDOFF_OUTPUT: `handoffs/20260818-gap2-b1-review-codex.md`
STATUS: DONE
