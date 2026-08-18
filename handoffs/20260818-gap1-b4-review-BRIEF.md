# GAP-1 B4 實作 code review（三家全員；實作者＝Claude 主委，不自審）

VERIFY-EXEMPT:doc-example:gap1-b4-review-brief-questions

> 本檔為**派給委員的提問清單**：段 A–D 是「請你查證的項目與我的待攻假設」，非主委結論；
> 結論在你們的產出與收斂檔。檔頭 `fact-verified:` 附主委實跑命令。

brief-kind: review

## 審查標的（commit `763b9d56`；`git show 763b9d56 --stat`）
- 程式：`momentum/Analysis/strategy_validation/{cscv,pbo}.py`、`scripts/strategy_wiring_check.{py,sh}`、`ledger.py`（一行：reason 取值改靜態字面）
- 測試：`tests/momentum/Analysis/strategy_validation/test_{cscv,pbo,pbo_universe_guard,wiring_check}.py`；golden `tests/momentum/Analysis/golden/gap1_reference_cases.json`
- 契約來源：TODO **FROZEN R3** Task 4.1／4.2／4.3／2.4 ＋延伸檔 **A1-1..A1-23**（重點 A1-1／2／3／4／11／15／17；**A1-23 為主委自揭之七項偏離／解讀，待你們裁定**）
- 🔴 B1–B3 之教訓：前三批我 brief 的自我描述各有一條以上被實跑推翻。本批 A1-23 就是我先自己列出來的「可能不忠於字面」清單，請**逐項裁定可接受／須改回字面**，並找我沒列的。
- 🔴 自建探針**一律加 timeout**；產出檔尾最後一行 `STATUS: DONE`。探針（20 條）**只由 codex 跑**（互斥鎖），另兩家讀 receipt。

## 本輪任務（四段皆必答）
**段 A — 契約符合度（逐 Task）**
- 4.1：`cscv_path_count`／`iter_cscv_splits`／`CscvBudgetExceeded` 簽名與語意；預算在 generator 建立前 raise？塊邊界餘數規則？驗收①–⑥逐字？`inspect.isgenerator` 真？
- 4.2：`probability_of_backtest_overfitting` 簽名；`PBOResult` 12 欄；守衛先跑（非 ok 即回、`universe_scope=None`）；champion 平手取最小原始欄索引；A1-15 之 `pos` 映射與 champion OOS 退化 ⇒ 跳過不重選；PBO 分母＝`n_paths_used`；驗收①–⑨逐字（golden 三案例、轉置、平手、④b/④c/④d、NaN 候選、有效 1、常數切片、全退化、universe_scope）。
- 4.3：`UniverseProvenance` `__post_init__` 型別驗證；`check_universe_provenance` 三項全符才 ok；`full_grid`／`external_declared` 無例外 unverifiable；不提供 `force`、不接受自備 hash；驗收①–⑤d 逐字。
- 2.4：AST（非 regex）；W1／W4 只認 `build_validation_section` 函式頂層無條件組裝（`If`／`For`／`While`／`Try`／`With` 內不計）；W2 死枚舉；W3 三形＋`[unresolved]` rc=1；rc 0/1/2 語意；六條 wiring mutation 各 rc=1；`--contract`／`--pkg` 旗標（禁 env）。

**段 B — 🔴 攻我的實作決定（本輪重點；對應 A1-23 七項＋兩項）**
1. **向量化 sharpe**（A1-23 #1）：Task 4.2 字面「`sharpe`→`compute_sharpe(col[idx], periods_per_year=1).value_per_period`」；我為效能（30s→0.2s／案例）改 `_metrics_columns()` 向量化 `mean/std(ddof=1)`，等價鎖 `test_vectorized_sharpe_matches_compute_sharpe`（atol 1e-15，含 std=0／NaN／n<2）。
   請攻：等價鎖是否夠強（例如**近常數欄**：`compute_sharpe` 之 `std == 0.0` 精確比對 vs 向量化——我實測 `sub[:,3]=0.01` 之常數欄兩者皆算出 ~1e15 之 SR（std 非精確 0），**兩邊都不 NaN 但值不同**；我改測試用 0.5 使 std 恰 0。這暴露 `compute_sharpe` 對「浮點上非精確常數」序列**不視為退化**——這是 B1 之既有行為，本批未動；請判定是否為真 bug 應另立修補（會影響 PBO 之 path 級退化判定）。
2. **W3 passthrough 形態**（A1-23 #2）：TODO 字面「非 Constant（f-string／變數／跨檔常數別名）⇒ unresolved rc=1」；我對 `x.reason`／`x["reason"]`／`.get("reason", <Const>)`／`IfExp`／`Name`（同檔指派來源皆合規或為參數）放行。理由：`reason=eligibility.reason` 之契約傳遞若一律 unresolved 則 gate 不可達。
   請攻：①這個放行是否留下可繞過之洞（例：`Name` 之來源在**別的函式**被指派為 f-string——我只追同檔 Assign 不分作用域，是否會把跨函式同名變數誤判為合規？請給反例）②`Attribute` 一律放行是否過寬（`obj.reason` 若 obj 是自造物件？）③是否應改為「TODO 字面＋延伸檔明列白名單形態」。
3. **`ledger.py` reason 靜態化**（A1-23 #3）：`reasons_seen[0]` → `_REASON_ROW_INVALID if _REASON_ROW_INVALID in reasons_seen else ""`。B2 已蓋章之碼被改一行——行為今日等價；請確認 `test_ledger.py` 是否真鎖住等價（25 passed）且未來多 reason 時會 fail-closed（不是靜默取第一個）。
4. **`len(candidate_ids)!=n_candidates` 不可達**（A1-23 #4）：守衛先跑使該 ValueError 分支死碼。應刪除該分支、或改守衛順序（先驗形狀再守衛）？TODO 字面順序是守衛先。
5. **golden 檔**（A1-23 #5）：§G 要求「Task 3.1 動工前建立」，我在 B4 才建；`sha256` 常數住 `test_pbo.py`；`alpha_undetectable` 之 mu 字面須為完整 double。請攻：sha256 只在 `test_pbo.py` 檢一次是否夠（B3 之常數測試沒讀 golden）；provenance 欄是否合 §G「文獻條目或解析推導出處」。
6. **PBO 名次母體**（A1-23 #6）：TODO「`r = rank/(len(valid_cols)+1)`」；我以「OOS 亦有限之候選」為母體（`rankdata` 對 NaN 全體 NaN），其他候選 OOS 非有限 ⇒ 剔除並計 `n_path_exclusions`。golden 三案例 excl=0 故不影響；請攻是否改變 PBO 定義（Bailey 2015 Algorithm 2.3 之名次母體為何）。
7. **§V-14 首版未轉紅**（A1-23 #7）：我原④d 測試在「原始索引＝壓縮位置」下對 mutation 無感；探針抓到後補 `test_rank_uses_compressed_position_not_original_index`。請確認新測試確實使 `[champ]` 索引壓縮陣列 ⇒ 紅，且 ④d 本身仍測 A1-15 之「OOS 退化跳過不重選」。
8. **雙冠測試**（④b）：`test_double_champion_takes_smallest_index_and_denominators` 之雙冠斷言我寫得**弱**（只斷言 `n_paths_used==2`，未直接證明取了最小索引）。請判定是否為廉價綠燈並給可證偽寫法（我承認這條可疑）。
9. **`n_path_exclusions` 計數語意**：我在 IS 剔除、OOS 剔除他人、champion OOS 退化各 +1（champion 情形 +1 再 +skip）。TODO 只寫「非有限 ⇒ 該候選該 path 剔除，`n_path_exclusions += 1`」。是否重複計數／語意漂移？

**段 C — 測試品質（禁廉價綠燈）**
- 探針 **20 條**（`bash scripts/gap1_b1_mutation_probe.sh`；🔴 只由 codex 跑；receipt `handoffs/run_receipts/20260818T100000Z-gap1-b4-mutation.log`）：§V-4／6／14 之 mutant 是否對應 TODO／A1-3／A1-15 字面；有無假紅。
- wiring 六條 mutation（`test_wiring_check.py`）是否各自真的只被對應規則抓到（W1／W3／W1／W3-unresolved／W1+W4）；⑤b（變數持 f-string）是否為有效補強或多餘。
- golden 三案例之 band 斷言（`0.30<=noise<=0.70`、`alpha_detectable<0.30`、`alpha_undetectable>0.40`）與 `abs=5e-5` 對 0.6483 之精確對照——後者是否過度綁定實作（RNG 形狀已寫死，應可重現）。

**段 D — 數值／契約正確性**
- 請自行重算：`C(12,6)=924`／`C(14,7)=3432`／`C(16,8)=12870`；`n_obs=1205,S=12` 塊長 `[101]*5+[100]*7`；`S=16,n_obs=2000` ⇒ 25.7M > 20M raise；golden noise 0.6483／alpha_detectable 0.0000／alpha_undetectable 0.5411（default_rng (T,N)）。
- `候選 0 mu = 0.01/sqrt(8760)` 之 double 為 `0.00010684346079267205`（`1.068434607926721e-04` 差 5.4e-20）。
- ω 公式 `ln(r/(1-r))`、`r=rank/(n+1)`；全平手 ⇒ ω=0；4 有效候選 ⇒ ω ∈ {ln(k/5/(1-k/5))}。

## 範本
`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13 之 §0／§1／§3 與 canonical 四欄。
ID＝`## <FAMILY>-R18-P<0-3>-<NN>`，**本輪輪次=R18**。零 findings 用 sentinel `## <FAMILY>-R18-P3-00`。

## ⚠️ 前置說明
- **禁改碼／SPEC／TODO／延伸檔；禁 commit／push**；只產你自己的 review 檔。
- 可自由跑測試；跑完貼 rc。探針有鎖，只由 codex 跑；若見 `.claude/gate/gap1_mutation_probe.lock` 存在請等鎖消失再跑測試，勿把探針期間之紅列 finding。
- 既有紅 2 條（`test_model_hyperparam_enhanced`）與本 epic 無關，勿列為 finding。
- 🔴 主委本輪**不動工作區**。`scripts/governance_families.json` 有既有 no-op dirty，非本輪。

## 本 brief 前提（逐條標）
fact-verified: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **269 passed**
fact-verified: `bash scripts/gap1_b1_mutation_probe.sh` → rc=0、20 條皆 rc=1、baseline／post-restore 266 passed（receipt 見段 C）
fact-verified: `bash scripts/strategy_wiring_check.sh` → rc=0 `✓ W1..W4`；`python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → BASELINE OK；`bash scripts/gov_check.sh --fast` → ✅
fact-verified: golden 三案例實跑 0.6483／0.0000／0.5411（與 2026-08-17 receipt 逐位一致；`standard_normal*0.01 == normal(0,0.01)` 已驗 True）
assumed: 向量化 sharpe 等價鎖足以取代字面「呼叫 compute_sharpe」← 請攻
assumed: W3 passthrough 封閉形態無繞過洞 ← 請攻（要反例）
assumed: OOS 名次母體「OOS 亦有限之候選」不改變 PBO 定義 ← 請攻
assumed: 雙冠斷言雖弱但由 ④d′／golden 間接覆蓋 ← 請攻

## Time-box
優先序＝段 B（我的決定）＞ 段 D（數值）＞ 段 C（測試品質）＞ 段 A（條文符合）。
**不受理**：使用者裁決、已 Frozen 之 TODO 契約本身（要改請走延伸檔提案）、前端、治理機制、B1–B3 已蓋章之範圍（除本批動到的一行 `ledger.py`）。

## 產出
Verdict（可收工／需修補後收工／有根本缺陷需重作）＋段 A–D 結論＋canonical findings。檔尾最後一行 `STATUS: DONE`。收尾清 /tmp workdir（保留 claude-501）。
