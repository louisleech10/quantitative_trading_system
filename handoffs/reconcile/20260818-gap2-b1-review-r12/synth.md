# Reconcile — 20260818-gap2-b1-review-r12

**來源** 20260818-gap2-b1-review-codex.md, 20260818-gap2-b1-review-composer.md, 20260818-gap2-b1-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18）

三家共 **11 條**（codex 8：6 P1／2 P2；grok 2：1 MAJOR／1 MINOR；composer sentinel「可進 B2」），下列八個群集**引用全部 11 條，0 掉項**。Verdict：codex／grok「需修補後進 B2」、composer「可進 B2」⇒ 依較嚴：**需修補後進 B2**。**9 條接受**（K1／K3／K4／K5／K6 全接受；K2 部分接受）、**1 條駁回附碼證**（K7）、**1 條 sentinel 記錄**（K8）。修補走 B1 修補 commit＋延伸檔 A1-7（契約 `marginal_ic_section_keys` 增子 schema `view_status_keys`＋`reasons` 三個增值；頂層鍵集**不變**）；戳記輪 r13 兼修補驗收。

Verdict：需修補後進 B2——修補 commit 落地後派 stamp r13（含各群集反例重跑判準）；APPROVED ⇒ B1 CLOSED → B2。

### K1 — `load_survivor_contract()` 回傳可變 cache singleton（Rule 8）
**引用**: CODEX-R12-P1-01
**處置＝接受**：cache 保留（內部），回傳 `copy.deepcopy`；測試加「回傳物件改寫不影響下一次呼叫」斷言。

### K2 — reason 字面以名稱出現於 `marginal_ic.py`（`_reason(literals, group, "no_survivors")`）
**引用**: CODEX-R12-P1-02
**處置＝部分接受**：reason 之**選擇**必須有語意名（契約為陣列、無語意鍵→字面之對照層；改契約為 mapping 亦只是把同一名字寫兩次），故「零命中」不可達；本票 TODO Task 4.1 ⑫ 已認可 orchestrator 側「字串常數 ⊆ 契約（AST）」為標準。**接受之部分**：(a) 加測試 `test_reason_literals_in_marginal_ic_subset_of_contract`（AST 掃 `marginal_ic.py` 內所有傳給 `_reason()` 之字串常數 ⊆ `load_survivor_contract()["reasons"]` 對應組；改名／刪值 ⇒ 紅）；(b) `_reason()` 維持成員檢查 fail-closed（改名 ⇒ KeyError 而非漂移）；(c) A1-7 明文：reason 選擇以名稱＋成員檢查＋AST 子集測試為本票之 SoT 遵循方式。**駁回之部分**：不改契約結構、不引入 pointer／索引取值（索引更脆弱：重排即錯值而不報錯）。

### K3 — `views` 無子 schema，B3 遞迴 validator 無法 fail-closed
**引用**: CODEX-R12-P1-03
**處置＝接受**：A1-7 於 `marginal_ic_section_keys` 增子鍵 `view_status_keys={additional_properties:false, keys:{status, reason(nullable)}}`（**頂層鍵集不變**）；測試 ⑪ 加每 view entry 鍵集 == `view_status_keys.keys`。

### K4 — 節級／視角級 status 語意：全部候選不可算仍 `ok`；loo 超預算＋removed 非空 ⇒ 節 `ok` 且 `per_feature={}`；label 常數 ⇒ `ok` 全 null
**引用**: CODEX-R12-P1-04, GROK-R12-P1-01, CODEX-R12-P1-05
**處置＝接受**（規則寫死於 A1-7）：(a) 視角 `ok` **僅當**該視角至少一候選 `status=="ok"`；否則 `not_computed`，reason＝預算超限 ⇒ `candidate_budget_exceeded`、無可算候選 ⇒ **新增** `no_computable_candidates`；removed 視角於 `extra=[]` ⇒ `not_applicable`＋**新增** `no_removed_candidates`；(b) 節級 `status`／`reason` ＝ `views["loo"]` 之 status／reason（removed 成功**不**抬升節 status；grok 修法 (a)）；(c) `_one` 於列數 gate 後加 label 退化 gate：`ptp(y_te)==0` 或 `ptp(y_tr)==0` ⇒ 候選 `not_computed`＋**新增** feature reason `label_degenerate`（三個 reason 皆只增值不改鍵集）；(d) 測試：常數因子全退化 ⇒ 節 `not_computed:no_computable_candidates`；grok 反例（loo 超限＋removed 非空）⇒ 節 `not_computed:candidate_budget_exceeded`、`views.removed_candidates.status=="ok"`；label 常數 ⇒ `label_degenerate`。

### K5 — V-3 探針之 O6 oracle 只由 raw `gross_ic` 轉紅，未證 `marginal_ic` 用秩相關
**引用**: CODEX-R12-P1-06, GROK-R12-P2-01
**處置＝接受**：新增 `test_marginal_uses_spearman_not_pearson`（重尾 label：`y = 0.5·s + t(df=2) 噪聲`，秩常態殘差對 y 之 Spearman 與 Pearson 差 >0.05；斷言 `marginal_ic` 與獨立 `stats.spearmanr(r_te,y_te)` 參考 `atol=1e-12` 且與 Pearson 參考差 >0.05）；探針 V-3 對映改為此測試（O6 保留為輔測）；TODO 1.3 對映表註記走 A1-7。

### K6 — O9 未驗 resampling 本身（點估 mutant 可通過）
**引用**: CODEX-R12-P2-07
**處置＝接受**：O9 加斷言 `ci95[1]-ci95[0] > 0` 且換 seed 至少一特徵 CI 不同（點估 mutant ⇒ 寬度 0 ⇒ 紅）；`block_bootstrap_ci` 單元：固定小陣列＋seed 之 CI 與「不重抽」點估不同。

### K7 — 頂層鍵表於 loader 常數與測試 ① 各列一份，判違反 JSON SoT
**引用**: CODEX-R12-P2-08
**處置＝駁回（碼證）**：TODO（FROZEN）Task 1.0 步驟 4 明文「`load_survivor_contract()`：頂層鍵集 `==` 上列集合否則 `ContractValidationError`」、驗證①「頂層鍵集 `==`」、風險緩解「契約鍵集由測試 ① 鎖死，B4 增鍵須改測試（可見）」——loader allowlist 與測試 ① 之逐字鍵集**皆為 TODO 指定之 fail-closed 守衛**，非欄位表複列；JSON SoT 條款（§0）之對象是「新欄位名／枚舉／reason 字面」（`*_keys` 內容與值集），頂層 allowlist 是契約檔自身之結構守衛。digest 方案（codex 建議）會失去「多了哪個鍵／少了哪個鍵」之可讀錯誤且仍需一處鎖 digest。A1-7 明文此豁免；不改。

### K8 — 收斂 sentinel（composer）：可進 B2
**引用**: COMPOSER-R12-P3-00
**處置＝接受（記錄）**：composer 段 B 十問獨立重判皆「可接受」、探針／oracle 本機重跑通過；與 K1–K6 修補不衝突（皆為收緊）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R12-P3-00

**斷言**: 本輪對 commit `022650ff` 段 A–E 與段 B 十項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -k load -q` → 10 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py -q` → 28 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B1` → rc=0 十條 RED+GREEN；O2 Δ=0.005825、O7 diff=0.508、O1b 走 ok 分支 marginal=0.000185；`marginal_ic.py` L493–495 退化先於 Spearman、`grep` 無硬編碼 statistic 字面。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792；momentum/Analysis/contracts/ic_survivor_contract.json#ed2872020c6e；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c

本輪核對依據：契約符合度對照 TODO Task 1.0–1.3 實作要點／不可做／邊界／驗證；段 B 十問獨立重判；mutation 探針與 §G oracle 本機重跑；數值重算與 SPEC 附值交叉驗證。未發現需修補後才能進 B2 之項。

---

## GROK-R12-P1-01

**斷言**: `compute_marginal_ic` 在 `loo`／`sequential` 因 `max_survivors_for_loo` 整體 `not_computed`、但 `removed_candidates` 視角仍標 `ok`（removed 非空）時，節級 `status` 會成為 `"ok"` 且 `per_feature={}`；此與 B5「節 `status!="ok"` 才不畫 survivor 表」的消費語意衝突，且作者只特殊處理了 removed **空集合** 情況。

**碼證**: `momentum/Analysis/marginal_ic.py` L551–558（`any_ok`；僅當 `not (loo_budget_ok or removed_names)` 才把空 removed ok 打回）。VERIFY：`MarginalICParams(max_survivors_for_loo=2)`、survivors=`[s1,s2,f]`、extra=`[z]`（O2 資料加與 y 弱相關之 z）→ `status=="ok"`、`reason is None`、`views.loo.status=="not_computed"`、`per_feature=={}`、`removed_candidates["z"]["status"]=="ok"`、`n_regressions==1`。對照空 removed 同預算：`status=="not_computed"`（`test_budget_survivors_whole_not_computed`）。RECHECK: 重跑上列構造。SPEC Task 5.1：節 `status!="ok"` ⇒ 不畫表。

**來源摘要**: momentum/Analysis/marginal_ic.py#a5de8252b792

[MAJOR] 信心度=High。會怎麼失敗：B5／報告消費端只讀節 status → 顯示「ok」空表，誤以為 loo 已算。  
修法（擇一寫死）：(a) 節 `ok` **僅當** `views["loo"]` 或 `views["sequential"]` 為 `ok`（removed 成功不抬升節 status；超預算理由仍可留在 views）；(b) 維持現狀但 B5／契約 `_doc` 明定消費端必須閘 `views.loo.status`（並加測試鎖死「loo 超限＋removed 非空 ⇒ 節 not_computed 或前端不畫」）。建議 (a) 在 B1 熱修，成本低於前端分叉。

---

## GROK-R12-P2-01

**斷言**: B1 mutation V-3（`_spearman` 內 `spearmanr→pearsonr`）對映之 `test_o6_rank_invariance` 在突變下轉紅，**唯一**逾 1e-12 的鍵是 raw 路徑的 `s1.gross_ic`／派生 `ic_retained_ratio`；所有特徵的 `marginal_ic`（與 `marginal_ic_train_insample`）在 base vs `f×c`／`s1³` 變換下差值仍為 0——因此該探針**不能**證明「`marginal_ic` 使用秩相關」。

**碼證**: `scripts/gap2_mutation_probe.sh` L42（V-3）；`tests/.../test_marginal_ic.py` L236–248（O6 斷言含 `marginal_ic` 與 `gross_ic`）。VERIFY：monkeypatch `mic._spearman`→`pearsonr` 後重跑 O2 O6 變換對，失敗鍵僅 `[('s1','gross_ic',≈0.067),('s1','ic_retained_ratio',≈0.288)]`；`*.marginal_ic` 全 0。原因：投影後已是秩常態殘差，Pearson≈Spearman，單調變換不破 `marginal_ic` 不變性。RECHECK: 同上 monkeypatch 實驗。

**來源摘要**: tests/momentum/Analysis/test_marginal_ic.py#60860d0762d5

[MINOR] 信心度=High。會怎麼失敗：日後有人把殘差改回 raw／在殘差路徑改用 pearson，V-3／O6 仍可能綠（假陰性於 marginal 路徑）。  
修法：收窄 oracle——例如構造「秩常態殘差上 Spearman≠Pearson」之合成（重尾／非單調 tie 結構），只斷言 `marginal_ic`；或另增 mutation 目標專打 `_one` 內 `marginal_ic = _spearman(r_te, y_te)` 一行並以該窄測對映。V-3 現況仍能證 raw gross 路徑，可保留作輔測。

---

