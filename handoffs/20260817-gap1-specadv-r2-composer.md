# GAP-1 SPEC Adversarial Review — COMPOSER (R2 closure)

**task-id**: `20260817-GAP1-X-REVIEW-R2` | **family**: composer | **brief**: `handoffs/20260817-gap1-specadv-r2-BRIEF.md`  
**審查標的**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（R2，commit `4f59a010`）｜**R1 產出**：`handoffs/20260817-gap1-specadv-composer.md`  
**R1 收斂**：`handoffs/reconcile/20260817-gap1-x-review-r1/synth.md`（D1–D7）

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS` rc=0
- `shasum -a 256 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `03e6832ae4ae`
- 逐條 closure 重跑 R1 反例（grep／python 重算／讀 Task 段落，見下表）
- §A／§G 數值重算（python/scipy，見必答 3）

---

## Verdict：可進 TODO

R1 之 **7 條 COMPOSER finding 均已實質關閉**（非僅 ID 引用）：Task 1.4 補齊 canonical／T 語意、§A inline receipt、B4 去假依賴、C5 產品 oracle、§V mutation 9/10、命名區隔、contract resolver 皆具可證偽驗收。§A 七條 FACT-RECEIPT 與 §G 解析等式本輪重算成立。R2 修補未引入新的 BLOCKING 缺陷。**BLOCKING 清單：無。**

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 判定 | 碼證 |
|---|---|---|
| fact-verified: 23 ID grep ≥1 | **fact**（非 closure 充分條件） | 本輪抽樣 `grep -c COMPOSER-R1-P0-01 docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 1；其餘 6 條 composer ID 皆命中 |
| fact-verified: template_check PASS | **fact** | 本輪 rc=0 |
| assumed: D1–D7 逐條完整回應 23 findings | **成立（composer 7/7）** | 下表逐條重跑 R1 反例；每條皆有對應 Task／§V／§N 義務，非空引 ID |
| assumed: Task 1.4＋13 鍵關閉 C2 T 語意 | **成立** | Task 1.4:137-158 三語意＋DSR 拒 `bar_count`；Task 2.1:192-206 `t_semantics_values` 等 5 枚舉鍵 |
| assumed: V[SR] 三態解矛盾 | **成立** | Task 3.2:299-302 `explicit`／`analytic`／`ledger_cross_trial`；§G:93-94 解析式；N=1 退化 PSR 驗收 Task 3.2:304 |
| assumed: §C 三處白名單使 Task 1.3 可實作 | **成立** | §C:65-70 允許 `timeframe`＋`annualization` dict；Task 1.3:167-177 數值分叉斷言 `sqrt(8760/730)` |

---

## 必答 1：closure 表（COMPOSER R1 → R2）

| ID | R1 反例（摘要） | 狀態 | R2 重跑證據（義務落地，非僅 ID） |
|---|---|---|---|
| COMPOSER-R1-P0-01 | `t_semantics` 無定義／無 canonical Task | **CLOSED** | **Task 1.4**（:137-158）定義 `bar_count`／`nonzero_return_bars`／`trade_level` 與 DSR 允許集合；**Task 2.1** `t_semantics_values`（:202）；**Task 3.2** 拒收 `bar_count`（:307-308,314）；**§V mutation 9**（:410-411）錯 T 語意須轉紅。RECHECK：`grep -n "Task 1.4\|t_semantics_values\|t_semantics_inflates" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` |
| COMPOSER-R1-P1-01 | `scratchpad/nmax.py` 不存在 | **CLOSED** | §A:27-28 改 **inline** `venv/bin/python -c "import math;T=20352/8760;print([math.floor(...)])"` → `[3,13,104,1422]`；`grep scratchpad docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 僅修正說明、無可執行路徑。RECHECK：`ls scratchpad/nmax.py 2>&1` → 仍不存在，但 receipt 不再引用 |
| COMPOSER-R1-P1-02 | B4 假依賴 B3 Task 3.1 | **CLOSED** | Phase B4（:338）「依賴 B1 1.1/1.2/1.4、B2 2.1；**不依賴 B3**」；§R:427-428 同步。Task 4.x 參數仍無 MinBTL。RECHECK：`grep -n "不依賴 B3\|B3 Task 3.1" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` |
| COMPOSER-R1-P1-03 | 缺 C5 產品 oracle | **CLOSED** | Task 3.1 驗收 ⑤（:279-280）`assess_eligibility(2.3232876712328765,100,1.0).eligible is False` 且 `trials_used > trials_budget`。本輪：`min_btl(100,1.0)=9.21>T`，`budget=3`，`100>3` → 斷言可證偽。RECHECK：見必答 3 C5 小節 |
| COMPOSER-R1-P1-04 | §V 缺 default_730 mutation | **CLOSED** | §V mutation **9**（:410-411）接受 `default_730` 或 `bar_count` ⇒ Task 1.4 ②③＋Task 3.2 ④ 轉紅（10 條清單，非 R1 之 7 條）。RECHECK：`grep -n "mutation 9\|default_730" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` |
| COMPOSER-R1-P2-01 | 未區隔 `overfitting_score` | **CLOSED** | Task 3.3 不可做（:336）明文不得複用 `overfitting_score`／`OverfittingCheckChart`。RECHECK：`grep overfitting_score docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → 1 命中（禁止條款） |
| COMPOSER-R1-P2-02 | `capability_status_ref` 無 resolver | **CLOSED** | Task 2.1（:189-215）`load_strategy_validation_contract()` 須 dereference；驗收 ① IC 逐值相等、③ drift tmp fixture raise。RECHECK：讀 Task 2.1 驗收段 :210-215 |

---

## 必答 2：R2 修補是否引入新缺陷

| 檢查項 | 結論 | 碼證 |
|---|---|---|
| Task 1.4 與 B2/B3 依賴 | **無新阻塞** | B3 依賴「B1 全部」含 1.4；1.4 語意在本 Task 定義，枚舉在 2.1——順序可實作 |
| 13 鍵契約過度？ | **可接受** | 鍵集合對應 R1 缺口（t/n/selection/universe/variance）；`validate_against_contract` 機械驗證 |
| lazy iterator＋20000 vs §G S=16 | **無衝突** | `C(16,8)=12870 < 20000`（本輪 `math.comb`）；S=20 之 184756 由 Task 4.1 ⑤ `CscvBudgetExceeded` 守衛 |
| 24 案例笛卡兒 | **可實作** | Task 3.3:326-330 明定 3×2³=24、允許唯一 `display_downgrade=False` 條件與 allowlist 差集 |

**新 finding**：本輪逐項核對後無實質新缺陷（見 sentinel `COMPOSER-R2-P3-00`）。

---

## 必答 3：數值複核（§A FACT-RECEIPT ＋ §G）

| 項目 | SPEC 宣稱 | 本輪重算 | 結論 |
|---|---|---|---|
| floor 預算 1.0/1.5/2.0/2.5 SR | 3／13／104／1422 | `[3,13,104,1422]` | **成立** |
| `min_btl(13)≤T < min_btl(14)` @ SR=1.5 | True／False | `2.280≤2.323`，`2.346>T` | **成立** |
| `E[max SR]` N=10/100/1000 | 1.5746/2.5306/3.2551 | 1.5746/2.5306/3.2551 | **成立**（atol<1e-4） |
| `C(S,S/2)` S=12/14/16 | 924/3432/12870 | 924/3432/12870 | **成立** |
| 預算不變式 20 組 | `ub(N)≤T<ub(N+1)` | 20/20 通過 | **成立** |
| 解析 V[SR] 手算樣本 | §G:93-94 公式 | 與公式一致 | **成立** |
| C5 oracle | ineligible @ n=100,T≈2.323,SR=1.0 | `min_btl=9.21>T`，`budget=3` | **成立** |
| §A receipt #1–2,#4–7 | grep／ls 命令 | 與 R1 一致（0 行／兩呼叫點／F-ST 登記） | **成立** |
| §A receipt #3 h5 路徑 | `1h/data (20352,)` | 檔內實際為 `SYMBOL/1h/data`；`BTCUSDT/1h/data` shape `(20352,)` | **數值成立**；receipt 路徑為簡寫，不阻 TODO |

---

## 必答 4：是否可進 TODO

**是。** R1 BLOCKING（P0-01）與 MAJOR/MINOR 均已轉為可驗收 Task／§V mutation；無殘留 OPEN／PARTIAL。**BLOCKING 清單：無。**

---

## COMPOSER-R2-P3-00

**斷言**: 本輪在優先完成 7 條 R1 closure 複驗與 §A／§G 數值重算後，未發現需以 `COMPOSER-R2-P0/P1/P2` 立項之新缺陷；R2 修補（Task 1.4、13 鍵契約、V[SR] 三態、§C 三處白名單、lazy CSCV 守衛、24 案例笛卡兒）與既有 Task 依賴一致且可證偽。

**碼證**: ① closure 表 7/7 為 CLOSED（上表逐條 RECHECK）② `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS ③ python 重算：預算 3/13/104/1422、`min_btl(13)≤T`、`E[max SR]` 三點、`C(16,8)=12870<20000`、C5 oracle ④ 新缺陷四項（1.4 依賴、13 鍵、20000 上限、24 案例）逐項無 BLOCKING。RECHECK：重跑 closure 表 RECHECK 列＋本節 python 區塊。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[NON-BLOCKING] 信心度=High。依據＝R1 原反例重跑均不再失敗；未為湊數捏造實質 finding。

---

## §1 必查（R2 增量；無新 finding 者標「無」）

| # | 類別 | 結果 |
|---|---|---|
| 1 | 矛盾/互斥 | 無（B4 假依賴已除；floor 預算與 §G 不變式一致） |
| 2 | 漏項/端到端 | 無（C2 T 語意、命名區隔已補） |
| 3 | 不可測驗收 | 無（C5 oracle、mutation 9/10、24 笛卡兒已寫死） |
| 4 | quant 假設 | 無新項（`bar_count` fail-closed 已鎖） |
| 5–11 | 其餘 | 無新項 |

## §2 範本錨點

§RISK/§A/§C/§G/§P/§V/§R/§N 齊備；§G 含數值 token 與 sha256 要求；RISK-HIT a,d ⇒ §G 非 N/A。R2 未見空殼 Task。

---

ASSUMPTIONS_VERIFIED: template_check PASS；7/7 closure 重跑；§A/§G 數值重算；scratchpad 仍不存在但 receipt 已 inline；B4 無 B3 依賴  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS rc=0；python/scipy 數值重算（本輪）；`bash scripts/completeness_check.sh --single handoffs/20260817-gap1-specadv-r2-composer.md --family composer`（見下）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（只讀審查）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC）

STATUS: DONE
