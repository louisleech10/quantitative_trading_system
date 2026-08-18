# Reconcile — 20260818-gap1-b4-review-r18

**來源** 20260818-gap1-b4-review-codex.md, 20260818-gap1-b4-review-composer.md, 20260818-gap1-b4-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；B4 實作 code review → B4 修補 commit ＋延伸檔 A1-24）

三家共 **13 條** canonical ID（codex 6／composer 2／grok 5）；下列 **六群集 N1–N6 引用全部 13 條，0 掉項**。
三家 Verdict **一致＝「需修補後收工」**（無 P0）。分歧：N2（名次母體）codex P1「改回 TODO／原典全 N 母體」vs grok P2「保留 oos_valid、改寫字面」
⇒ **看碼證取較嚴＝守 Frozen 字面**（見 N2）。A1-23 之 #3／#4／#5 三家皆可接受（#5 過程債入帳）；#1／#2／#6／#7 相關者本輪修。
🔴 主委 brief 四條 assumed：①向量化等價鎖足夠 **部分推翻**（近常數欄兩邊皆非 NaN 但值不同）②W3 passthrough 無洞 **推翻**（codex／grok 各給反例：
`reason=obj.payload`／`reason=data["x"]`／`.get` 首參數不驗／區域遮蔽）③OOS 名次母體不改定義 **推翻**（codex 引原典 Algorithm 2.3 全 N；grok 認為可保留但需改字面）
④雙冠由間接覆蓋 **推翻**（三家皆判無鑑別力斷言）。

### N1 — W3 passthrough 謂詞過寬＋W2 死枚舉判定過寬（wiring 閘可繞過）
**引用**: CODEX-R18-P1-03, GROK-R18-P1-01, CODEX-R18-P2-06

grok 實跑：`reason=data["x"]`（`data={"x":"invented_v"}`）與 `reason=o.reason`（執行期自創）皆 rc=0；codex 另指 `.get` 不核對首參數、同檔頂層常數替換忽略區域遮蔽；
W2 把任意字串 Constant 當「已接線」——`UNUSED="new_reason"`／docstring 即可騙過「死枚舉即紅」。兩家 MAJOR。
**處置（修）**：① passthrough **白名單收窄**：`Attribute` 僅 `attr=="reason"`；`Subscript` 僅 slice 為 Constant `"reason"`；`.get(<Const "reason">, <合規>)`；
`IfExp` 兩支皆合規；`Name` 改為**同函式作用域**解析（函式內 Assign／AnnAssign 來源皆合規，或為該函式參數；模組級名稱只認頂層 str 常數，且函式內同名指派**遮蔽**模組常數）；
其餘一律 `[unresolved]` rc=1。② W2 改為「契約每個 reason 須出現於 **reason 位置**（三形，經同檔常數解析）或為**被引用**之模組級 str 常數之值」——
只在 docstring／未使用常數出現 ⇒ 死枚舉 rc=1。③ 新增 wiring mutation：`reason=data["not_reason"]`、`reason=obj.other`、`reason=x.get("other","n_unknown")`、
區域 f-string 遮蔽同名頂層常數、`UNUSED="ghost_reason"`（配契約多一 reason）皆 rc=1。延伸檔 A1-24 具名白名單（覆寫 A1-23 #2）。

### N2 — PBO 名次母體與分母偏離 Frozen TODO 字面（`len(valid_cols)+1`）與原典 Algorithm 2.3
**引用**: CODEX-R18-P1-02, GROK-R18-P2-03

主委實作以「OOS 亦有限之候選」為母體（A1-23 #6 自揭）；codex 引原典 pp.10-11「OOS rank 為 N strategies、`N+1`」判 P1；grok 判 P2 建議保留並改字面。
**裁決（看碼證）**：Frozen TODO 字面＝`oos_metrics` 對 `valid_cols`（path 有效候選）取名次、`r=rank/(len(valid_cols)+1)`；`rankdata` 對 NaN 不可用是**實作困難非語意依據**，
且母體縮小會**系統性改變 r**（分母變小）⇒ 改變 PBO 定義。⇒ **守字面**：名次母體與分母恆為 `path_valid`（IS 有限之候選）；
**任一** path 有效候選之 OOS metric 非有限 ⇒ 該 path **跳過**（`n_paths_skipped += 1`；含 A1-15 之 champion 情形），**不**在縮小母體上取名次。
golden 三案例 excl=0 不受影響；新增單測：某非 champion 候選 OOS 常數 ⇒ path skip、分母不變（手算）。A1-24 覆寫 A1-23 #6。

### N3 — `n_path_exclusions` 對 champion 重複計數
**引用**: CODEX-R18-P1-01, GROK-R18-P2-02

grok 實跑 ④d fixture：`n_path_exclusions=3`（champion 雙計）。**處置（修）**：計數語意固定為「每候選每 path 至多 +1」：IS 非有限 +1；OOS 非有限（含 champion）+1；
path skip 不再額外 +1。④d 測試改為精確斷言 `n_path_exclusions` 手算值（IS 排除欄 2 於 path 2：+1；OOS 欄 2 非有限於 path 1：+1 ⇒ 2）。

### N4 — ④b 雙冠測試為無鑑別力斷言
**引用**: CODEX-R18-P2-04, COMPOSER-R18-P2-01, GROK-R18-P2-01

三家一致（composer／grok 各手算：正確 champion 欄 1 ⇒ ω≈−0.405，誤取欄 3 ⇒ ω≈+1.386，現行測試兩者皆綠）。主委 brief 段 B8 自承。
**處置（修）**：重寫 fixture 為手算可證偽矩陣（`mean_return`、S=2、4 候選）：path 0 IS 平手欄 1／3 ⇒ champion 欄 1、OOS 名次 2/4 ⇒ ω=ln(2/3)；
path 1 IS champion 欄 3、OOS 與欄 1 平手名次 3.5 ⇒ ω=ln(0.7/0.3)；斷言 `sorted(logits)==[ln(2/3), ln(7/3)]`（atol 1e-12）；④c 改為兩次真實 PBO 呼叫比較 5 vs 3 有效候選之分母。

### N5 — 向量化 Sharpe 等價鎖未覆蓋近常數欄（且暴露 `compute_sharpe` 對浮點非精確常數不視為退化）
**引用**: CODEX-R18-P2-05, COMPOSER-R18-P2-02

composer 實跑：`sub[:,3]=0.01` ⇒ vec≈1.909e15、ref≈5.728e15（`std≈1.75e-18`），皆非 NaN、值不同（2-D axis 縮減與 1-D 縮減順序不同）。
**處置（修）**：`_metrics_columns` 之 `sharpe` 改為**逐欄呼叫同一 1-D 縮減**（`col.mean()/col.std(ddof=1)`＋同 `compute_sharpe` 之退化判定），
與 `compute_sharpe` **逐位相同**（`==`）；等價測試加入 `0.01` 近常數欄與 `1e-9` 微擾欄，斷言逐位相等（實測仍秒級）。
`compute_sharpe` 對「浮點非精確常數」不視為退化 ⇒ 屬 B1 已蓋章之語意，本批**不動**；登記殘留 **G1-R11**（`為何現在不做: needs-research: 「常數」之相對容差定義
無公認判準（相對於 |mean|？|max|？），且改動會使 Task 1.2 退化語意變更需另輪三家審`；觸發＝任何真實回測序列命中「近常數且 SR>1e6」或使用者裁定容差）。

### N6 — golden 檔時序債與 sha256 單點
**引用**: GROK-R18-P2-04

grok 判 MINOR、不擋收工。**處置（修，低成本）**：抽 `tests/momentum/Analysis/strategy_validation/_golden.py`（sha256 常數＋loader 唯一定義處）；
`test_min_btl.py`／`test_deflated_sharpe.py` 之手算常數改為同時對照 golden（三檔皆驗 sha）；時序債（§G「Task 3.1 前建立」）具名記於 A1-24。

**Verdict**: 需修補後合併 → 修補於 B4 修補 commit ＋延伸檔 A1-24；三家戳記後收工。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R18-P1-01
**斷言**：champion OOS 非有限時，同一候選被 `n_path_exclusions` 重複計數，審計欄位與 TODO「每候選每 path 一次」不符。 **碼證**：`pbo.py:213-218` 先以 `len(path_valid)-len(oos_valid)` 計入，再因 `not math.isfinite(oos_all[pos[champ]])` 額外 `n_excl += 1`；`test_pbo.py:190-206` 只斷言 `>=1`。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`docs/GAP1_STRATEGY_OVERFIT_TODO.md#1b5b3d3609caa876648e52399b15fa27491431f7`。
## CODEX-R18-P1-02
**斷言**：實作把 OOS 非有限的其他候選從 rank 母體刪除並用 `len(oos_valid)+1`，改變 Frozen TODO 的 `len(valid_cols)+1` 及 Algorithm 2.3 的全 N 母體，會改變 PBO。 **碼證**：`pbo.py:213-224` 建 `oos_valid`、`oos_vals` 後以 `len(oos_valid)+1` 計 `r`；TODO `:398-406` 要求 `oos_metrics` 對 `valid_cols` 且 `r=rank/(len(valid_cols)+1)`，原典 Algorithm 2.3 PDF pp.10-11 明定 OOS rank 為 N strategies 且 `N+1`。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`docs/GAP1_STRATEGY_OVERFIT_TODO.md#1b5b3d3609caa876648e52399b15fa27491431f7`；[Bailey et al. Algorithm 2.3](https://www.carmamaths.org/resources/jon/backtest2.pdf)#4b0d8f9e3d7a。
## CODEX-R18-P1-03
**斷言**：W3 的 passthrough 判定可被非 reason 欄位/變數繞過 fail-closed gate，且同檔頂層常數替換忽略區域遮蔽。 **碼證**：`strategy_wiring_check.py:123-139` 對任意 `Attribute` 放行、對任意字串 `Subscript` 放行、`.get` 不核對第一參數；`:199-214` 將頂層常數套用到所有 scope。反例形態 `reason=obj.payload`、`reason=obj["dynamic_key"]`、局部 f-string 變數遮蔽同名頂層常數均不會列 `[unresolved]`；現有六 mutation 未覆蓋。 **來源摘要**：`scripts/strategy_wiring_check.py#517578808275821cc6bc59b7ee41f90137a49127`；`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#56cde5ed7a83ca32fc9e1ceb2871ff59513e0077`。
## CODEX-R18-P2-04
**斷言**：④b 雙冠測試沒有證明取最小原始索引，是廉價綠燈。 **碼證**：`test_pbo.py:170-187` 只斷言 `got.n_paths_used==2`；兩個 `rankdata` 斷言作用於獨立常數陣列，沒有讀 `got.logits_*`，錯取欄 3 仍可全綠。 **來源摘要**：`tests/momentum/Analysis/strategy_validation/test_pbo.py#4211eb848533efcff9313afeb0cc2bed01609c64`；TODO `:417` 的 ④b。
## CODEX-R18-P2-05
**斷言**：向量化 Sharpe 等價鎖不足以支持替代字面 `compute_sharpe`，近常數欄的 reduction/精確 std 差異可能改變 champion 或退化判定。 **碼證**：`pbo.py:136-153` 用 `sub.mean(axis=0)/sub.std(axis=0)`，參考 `_metric` `:129-133` 走 `compute_sharpe`；`test_pbo.py:126-140` 只測隨機欄、精確常數 `0.5`、NaN、n<2，沒有 A1-23 指出的近常數 case。 **來源摘要**：`momentum/Analysis/strategy_validation/pbo.py#4b8fae455bda8a7324c9fb9403f9f4b7a6bc1c0f`；`tests/momentum/Analysis/strategy_validation/test_pbo.py#4211eb848533efcff9313afeb0cc2bed01609c64`。
## CODEX-R18-P2-06
**斷言**：W2 將任意字串 `ast.Constant` 當作 reason 已接線，未阻擋只存在於 docstring/未使用常數的死枚舉。 **碼證**：`strategy_wiring_check.py:187-188` 收集所有字串常數，`:280-282` 只檢查每個契約 reason 是否在集合；可新增 `UNUSED="new_reason"` 或 docstring 後仍 rc=0，現有 `test_dead_enum_reason_is_red` 只測完全不存在。 **來源摘要**：`scripts/strategy_wiring_check.py#517578808275821cc6bc59b7ee41f90137a49127`；TODO `:445-457` 要求「死枚舉即紅」。
ASSUMPTIONS_VERIFIED: `git show 763b9d56 --stat` matches B4 target; `bash scripts/gap1_b1_mutation_probe.sh` baseline/post-restore 266 passed and 20/20 mutants rc=1 with FAILED>=1; `bash -n scripts/strategy_wiring_check.sh` rc=0; `bash scripts/strategy_wiring_check.sh` rc=0 with W1..W4; target files `git diff --quiet` rc=0; `mu`/golden values and numeric counts checked from target tests/golden and brief receipt.
TESTS_RUN: `bash scripts/gap1_b1_mutation_probe.sh` = rc=0; `bash -n scripts/strategy_wiring_check.sh` = rc=0; `bash scripts/strategy_wiring_check.sh` = rc=0; brief fact-verified `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` = 269 passed.
FAILURES_SEEN: ad hoc direct Python counterexample was blocked by the repository PreToolUse debt gate; no source mutation remained; no finding depends on that unrun probe.
SCOPE_CHANGES: only `handoffs/20260818-gap1-b4-review-codex.md` added; no code/SPEC/TODO/data_cache change, no commit/push; pre-existing dirty files preserved.
NUMERIC_OR_SCHEMA_IMPACT: reviewer made no changes; findings P1-01/P1-02 concern PBO audit counter and rank denominator semantics; no output file/schema was changed.
HANDOFF_OUTPUT: `handoffs/20260818-gap1-b4-review-codex.md`
STATUS: DONE
## COMPOSER-R18-P2-01

**斷言**: `test_double_champion_takes_smallest_index_and_denominators` 僅斷言 `n_paths_used==2`，未直接證明 IS 平手時 champion 取最小原始欄索引；誤取較大索引之 mutant 仍可全綠。

**碼證**: `test_pbo.py:170-182` 註解承認「只斷言至少一條 path 之 ω 非最大名次值」但實際僅 `assert got.n_paths_used == 2`；④c 分母公式在測試內手算 `rankdata` 與雙冠無關。本輪雙冠 fixture 手算：正 champion 欄 1 ⇒ ω≈−0.405；誤取欄 3 ⇒ ω≈+1.386；實跑 logits `[−1.386, 0.0]` 與正實作一致但測試未斷言。RECHECK：跑現有測試通過；補 `assert got.logits_max == pytest.approx(0.0)` 與 `assert got.logits_min < 0` 或比對 champion 欄索引。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_pbo.py#e8b4f5b90d86

[MINOR] 信心度=High。平手取最小索引為 Task 4.2 驗收④b 字面；現行斷言為廉價綠燈。修法：在雙冠 fixture 上斷言 `logits_max==0.0`（欄 1 champion 非最高 OOS 名次）或 spy 內部 champion 索引；④d′ 不覆蓋平手語意。

---

## COMPOSER-R18-P2-02

**斷言**: `test_vectorized_sharpe_matches_compute_sharpe` 未覆蓋「浮點上非精確常數」欄（如全欄 `0.01`），該區間內 `_metrics_columns` 與 `compute_sharpe` 給出不同巨大有限 SR、皆非 NaN，等價鎖不足以證明逐位一致。

**碼證**: `pbo.py:136-153` 向量化 `std!=0.0` 精確比對；`test_pbo.py:130` 用 `0.5` 使 `std` 恰 0。RECHECK：`sub[:,3]=0.01`（80 行）⇒ vec≈1.909e15、ref≈5.728e15、`std≈1.75e-18`，皆非 NaN。`compute_sharpe` 觸發 scipy moment Precision loss 警告。

**來源摘要**: momentum/Analysis/strategy_validation/pbo.py#c1f466553416

[MINOR] 信心度=High。PBO 僅走向量化路徑故生產內部自洽；但近常數欄可能被當高 SR 影響 IS champion／path 退化語意，且與 TODO 字面「呼叫 compute_sharpe」偏離。修法：擴等價測試涵蓋 `0.01` 欄並決策是否統一退化為 NaN（可能需另票動 sharpe）；或文件化「PBO 以向量化為準、近常數非退化」。

---

STATUS: DONE
## GROK-R18-P1-01

**斷言**: W3 passthrough 謂詞過寬——任意 `Attribute`、任意字串鍵 `Subscript`／`get`、以及檔內無 Assign 之 `Name` 皆放行，可使自創 reason 經屬性／字典查找繞過 wiring 閘而 rc=0。

**碼證**: `scripts/strategy_wiring_check.py` `_is_passthrough`（Attribute 無條件 True；Subscript 只驗 slice 為 str；Name 無來源⇒True）。RECHECK：tmpdir 複製 `strategy_validation` 後寫 `reason=data["x"]`（`data={"x":"invented_v"}`）⇒ `strategy_wiring_check.py --pkg …` **rc=0**；`reason=o.reason`（執行期自創字串）⇒ **rc=0**；對照 `reason=f"x_{i}"`／`tmp=f"..."; reason=tmp` ⇒ rc=1。

**來源摘要**: scripts/strategy_wiring_check.py#4d8c4fe6e979

[MAJOR] 信心度=High。修法：白名單收窄為 `x.reason`／`x["reason"]`／`x.get("reason", …)`／合規 IfExp／同**函式**作用域 Name；其餘維持 unresolved。並加 mutation：`reason=data["not_reason"]` 與 `reason=obj.other` 必須 rc=1。延伸檔具名白名單（對應 A1-23 #2 裁定「改字面＋白名單」）。

## GROK-R18-P2-01

**斷言**: `test_double_champion_takes_smallest_index_and_denominators` 未直接證明「平手取最小原始索引」——只斷言 `n_paths_used==2`，且 ④c 未呼叫 PBO。

**碼證**: `tests/momentum/Analysis/strategy_validation/test_pbo.py` 該測末段；本輪構造 S=2／IS 平手／OOS 名次分離矩陣 ⇒ 正確實作 `logits` 含 `ln(1/3)≈-1.0986`，誤取大索引則得 `ln(3)`——**現行測試兩者皆能綠**。

**來源摘要**: tests/momentum/Analysis/strategy_validation/test_pbo.py#e8b4f5b90d86

[MINOR] 信心度=High。修法：assert 至少一條 path 之 ω 等於最小索引 champion 之手算值（或 mock／spy champion 索引）；④c 改為兩次真實 PBO 呼叫比較不同 `n` 有效候選下之 ω。

## GROK-R18-P2-02

**斷言**: champion OOS 退化時 `n_path_exclusions` 對同一候選重複 +1（一般 OOS 剔除一次＋skip 分支再一次）。

**碼證**: `pbo.py` 約 L213–218：`n_excl += len(path_valid)-len(oos_valid)` 後，`if not finite(champ) or len(oos_valid)<2: n_excl += 1`。RECHECK：④d fixture ⇒ `n_paths_skipped=1, n_paths_used=1, n_path_exclusions=3`（champion 雙計）。

**來源摘要**: momentum/Analysis/strategy_validation/pbo.py#c1f466553416

[MINOR] 信心度=High。修法：skip 時若 champ 已在 OOS 剔除集合則不再 +1；或具名「path-skip 附加計數」並改測試期望。同步延伸檔／TODO 一句話消歧。

## GROK-R18-P2-03

**斷言**: 實作以「OOS 亦有限候選」為名次母體，與 TODO 字面 `r=rank/(len(valid_cols)+1)` 在 `n_path_exclusions>0` 時不等價；golden 三案例 excl=0 蓋不住此差。

**碼證**: TODO Task 4.2 步驟 2 vs `pbo.py` L220–223 `r = rank/(len(oos_valid)+1)`；A1-23 #6 自揭。Bailey／CSCV 敘事支持對有定義 OOS 指標者排名（`rankdata`+NaN 不可用）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e559a616f00a

[MINOR] 信心度=High。修法：**保留** `oos_valid` 母體；延伸檔改寫 TODO 字面並加 excl>0 之單測（手算分母）。不要求改回 `valid_cols`（會強迫 NaN 進 `rankdata` 或需另造填充規則）。

## GROK-R18-P2-04

**斷言**: golden 檔未在 Task 3.1 前建立（§G 時序），且 sha256 防篡只掛在 `test_pbo.py`——B3 內嵌解析常數測試不讀該檔，存在雙源漂移窗口。

**碼證**: A1-23 #5；`_GOLDEN_SHA256` 僅 `test_pbo.py`；`gap1_reference_cases.json` provenance 欄完整。B4 補建後 PBO／cscv／min_btl 對照已進 `test_golden_file_sha256_and_analytic_constants`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#3a32678eeed8

[MINOR] 信心度=Medium。修法：過程債入帳即可；可選讓 B3 常數測改讀 golden，或在 CI／gate 加「golden sha256 單點」。不擋 B4 演算法收工。

---


## 戳記
