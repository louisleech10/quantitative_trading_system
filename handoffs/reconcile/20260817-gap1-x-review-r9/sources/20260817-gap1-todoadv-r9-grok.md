# GAP-1 TODO R2 受限複驗（R9）— GROK

**task-id**: `20260817-GAP1-X-REVIEW-R9` | **family**: grok | **brief**: `handoffs/20260817-gap1-todoadv-r9-BRIEF.md`
**審查標的**（本輪 `shasum -a 256` 前 12）：
- TODO R2：`docs/GAP1_STRATEGY_OVERFIT_TODO.md` @ `e6d673841704`
- 延伸檔 A1：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md` @ `44556a29f5c1`
- 母 SPEC R8：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md` @ `502c93cae402`（衝突以延伸檔為準）
- r8 收斂：`handoffs/reconcile/20260817-gap1-x-review-r8/synth.md` @ `32271ad1ccab`
- Registry：`docs/IC_QUANT_GAP_REGISTRY.md` @ `5dc19777a196`
- 前輪本家族：`handoffs/20260817-gap1-todoadv-r8-grok.md` @ `94cf0b524648`

**本輪 finding 輪次**：R9（session＝`review-r9`）
**禁改碼／禁改 SPEC／TODO／延伸檔／禁蓋戳記**；只產本檔。

**VERIFY（本輪實跑）**：
- `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → `TEMPLATE PASS (todo)` rc=0
- `shasum -a 256` 五檔前 12 如上
- PBO 探針：`venv/bin/python handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.py` → noise 0.6483／0.6158／0.5357；alpha(μ=1.068e-4) 0.5411／0.6201／0.5487；`sr_pp=0.15` ⇒ 0.0000（default_rng）／0.0054（legacy）
- 等價 A1 生成式＋§V-4 mutation 自跑（見段 B 表）
- MinBTL：`venv/bin/python handoffs/run_receipts/20260817T150000Z-gap1-minbtl-conservatism-probe.py` → mean=0.843077 max=1.216377 analytic=0.833943
- AST 死分支／`ValueError` 吞例外之可執行片段（見段 C／findings）

---

## Verdict：需修補後 Frozen

段 A：本家族 R8 七條 finding **全 CLOSED**（拓撲／簽名／reporter／殘留理由／W3 邊界皆已落到 TODO R2＋A1／registry）。  
段 B：J1 三條數值 golden ＋ §V-4 新 mutation ＋ 驗收⑨ **全部本輪實跑重現**，與主委 receipt 一致。  
段 C：新機制大體可執行且 fail-closed 取向正確；但 **A1-8 之 `ValueError` 捕獲過寬** 會把 `assess_eligibility` 參數驗證（程式／呼叫方 bug）吞成 `reporter_failed`（2xx），屬新增例外政策之可執行缺陷。另兩條 MINOR（AST 死分支假綠風險、§R 未隨 B4→B3 依賴改寫）。

**不**判「有根本缺陷需重作」：B1–B4 純統計核心與 J1 oracle 已可 Frozen 級重現；修 A1-8 例外集合（或自訂例外階層）＋（建議）A1 補 §R 一句即可。

**BLOCKING**：無。  
**MAJOR**：`GROK-R9-P1-01`（1）。  
**MINOR**：`GROK-R9-P2-01`、`GROK-R9-P2-02`（2）。

---

## 段 A — 本家族 R8 closure（7/7）

| R8 ID | 原 severity | 處置落點 | 本輪重跑／對證 | 狀態 | 仍 OPEN 可否殘留 |
|---|---|---|---|---|---|
| GROK-R8-P0-01 | BLOCKING | TODO §B：2.4→B4 末；B2→B3／B3 去 wiring rc=0；B4 依賴 B3 3.3；A1-11 | 讀 TODO:42-58、420-451：批內 4.1→4.2→4.3→2.4；B4 唯一 wiring 關 | **CLOSED** | — |
| GROK-R8-P1-01 | MAJOR | A1-5：`ledger_result`；刪 `budget_capped`／`10**18`；`x>700` raise | TODO:235-245 與 A1-5 一致；無 `budget_capped` | **CLOSED** | — |
| GROK-R8-P1-02 | MAJOR | A1-8／TODO 3.4：三 optional；禁 `trial:{n}`；缺參不呼叫 assess | TODO:309-318 | **CLOSED** | — |
| GROK-R8-P1-03 | MAJOR | A1-10／registry G1-R3 → `user-ruling:…不含 frontend` | registry:46 逐字 | **CLOSED** | — |
| GROK-R8-P1-04 | MAJOR | A1-9 驗收⑨部分收回；G1-R7 觸發改 `GAP-1-R7-MC` | registry:50；TODO:246-250；本輪 mean 重現 | **CLOSED** | — |
| GROK-R8-P2-01 | MINOR | A1-11／TODO 2.4：W3 AST 三形＋`[unresolved]` rc=1；誠實邊界具名 | TODO:431-448 | **CLOSED** | — |
| GROK-R8-P2-02 | MINOR | A1-8：例外分類＋`exc_info`＋文字不進 reason | TODO:319-324；**剩餘寬度見 R9-P1-01**（新攻擊，不重開本 ID） | **CLOSED** | — |

**他家族（僅異議時）**：無異議。`CODEX-R8-P0-02` 之 `rankdata` 反例本輪重跑仍 IndexError；TODO:376-381 之 `pos[champion]`＋champion 非有限 skip path **關閉該反例**。`CODEX-R8-P0-01` 轉 G1-R9＋`universe_scope` 為主委裁定，本輪不重審範圍 A。

---

## 段 B — J1 數值可重現性（本輪實跑）

生成式（A1-2 逐字）：`rng=np.random.default_rng(20260817)`；`M=rng.standard_normal((1200,50))*0.01`；`S=12`。

| # | 斷言 | 本輪實跑 | 主委 receipt | 判定 |
|---|---|---|---|---|
| B1 | `alpha_detectable`：`mu=0.01*0.15` ⇒ PBO `<0.30` | **0.0000**（default_rng） | 0.0000／legacy 0.0054 | **PASS** |
| B2 | 全噪音 PBO ∈ `[0.30,0.70]` | **0.6483** | 0.6483（同生成式） | **PASS** |
| B2b | band 放寬理由（924 path 相關） | 三變體 0.6483／0.6158／0.5357，極差 0.1126＞√(0.25/924)≈0.016 | 同 | **成立**（單 seed band 合理；多 seed 平均可作未來收緊，**非**本輪必改） |
| B3 | `alpha_undetectable`：`mu=0.01/√8760` ⇒ PBO `>0.40` | **0.5411**（default_rng） | 0.5411／0.6201／0.5487 | **PASS** |
| B4 | §V-4：champion 改 OOS 選 ⇒ noise 或 alpha_det 至少一條轉紅 | mutation 後 noise **0.0000**（出 band）；alpha_det 仍 0.0000 | A1-3 宣稱趨近 0 | **PASS**（至少 noise 轉紅）；舊 IS/OOS 對調仍 0.6483＝原值（證舊 mutation 不可證偽） |
| B5 | 驗收⑨：`mean(max ann SR)≤1.0` 且 vs `0.833943` `rtol<0.05` | mean=**0.843077**；rtol=**0.0110**；max=1.216377（逐 seed 上界不成立） | 同 | **PASS**（只可下在 20-seed 平均） |

---

## 段 C — 新增機制攻擊面（五項）

### C1 AST wiring（A1-11／Task 2.4）
- **Helper／`**dict`／迴圈／`dict(**kwargs)`／`setattr`**：在 TODO 所寫「只收 `ast.Constant` 鍵」下，這些路徑**拿不到鍵** → 傾向 **rc=1 假紅（fail-closed）**，不是假綠。與誠實邊界「不追跨檔別名／f-string ⇒ unresolved」一致。
- **可執行假綠**：若實作對函式 body **無 CFG** 地收集所有 `ast.Dict` 的 Constant 鍵，則死分支可餵滿契約節名而 runtime 回殘缺 dict（本輪 AST 探針：`if False: out={五節…}` ⇒ `contract ⊆ collected` 為 True）。mutation ④只鎖註解／docstring，**未**鎖死分支。見 `GROK-R9-P2-01`。
- `return dict(eligibility=…)` 形：純 `ast.Dict` 掃描會假紅；實作須一併收 `Call(func=Name('dict'))` 之 keyword——TODO 未明寫，屬實作註記，不另開 finding（假紅非假綠）。

### C2 `universe_scope`（A1-4）
- 以可觀測欄＋Task 3.3 強制 `display_downgrade=True` 取代「一律非 ok」：**足夠誠實**且不使 PBO 永不可用（符合範圍 A）。G1-R9 正確登記生產者側證明。
- **繞過路徑**：呼叫方只讀 `pbo.value`／`eligibility.eligible` 而忽略 `display_downgrade`／`universe_scope`——**存在**，但是使用者裁決「降級不硬擋」的已知面；機器證明在 flag／欄位，不在 HTTP 4xx。較嚴版（若未來要）：route 在 `universe_scope==ledger_recorded_only` 時仍 2xx，但 **禁止** 任何「promote／建 pipeline 成功文案」鍵（本票 API 已只投影三鍵，無推薦鍵）——**不**要求本輪改為硬擋。
- 今日 `universe_scope_values` 僅一值 ⇒ 真實算完之 PBO 路徑上 `display_downgrade` 實務上恆 True；測試①之 `False` 僅在 `universe_scope=None` 合成態——可接受（為測 step 2 邏輯）。

### C3 例外分類（A1-8）
- `(OSError, json.JSONDecodeError, ContractViolation, ValueError)` 對 I/O／契約／JSON **恰當**。
- **`ValueError` 過寬**：`assess_eligibility`／`max_trials_budget` 參數驗證亦 `raise ValueError` ⇒ 呼叫方傳錯（`t_years<=0` 等）被吞成 `reporter_failed` 2xx，與「程式 bug 往上拋」目標衝突。本輪可執行：`except (…, ValueError)` 捕獲 `assess_eligibility(t_years=-1,…)` → `reporter_failed`。見 `GROK-R9-P1-01`。
- 修法（擇一）：① 參數驗證改自訂 `StrategyValidationParamError(Exception)`（**不**進捕獲元組）；② 捕獲集合收窄為 `(OSError, json.JSONDecodeError, ContractViolation)`，參數錯誤在 reporter 入口先轉 typed `unavailable` 而不 raise；③ `ValueError` 只包一層 ledger 解析並具名，assess 之 ValueError 重拋。

### C4 `n_rows_rejected`（A1-7）
- 六欄自洽：`n_evaluated = n_valid_metrics + n_failed_or_pruned` 由構造成立；`n_rows_rejected` 只計 schema-invalid 且**不**進 `n_evaluated`；`n_candidates_considered` 只對 schema-valid 去重——與「非法列不是候選」一致。
- 與 `n_is_lower_bound≡True`：**無衝突**。後者語意＝「ledger 可能沒寫完真實嘗試過的候選」（G1-R9 面），不是「拒收列應算進 N」。
- Conformance「合法寫入口 ⇒ `n_rows_rejected==0`」可證偽：繞過 `append_trial_attempt` 手寫非法 JSONL 行即可使 `n_rows_rejected>0`；測試②／②b 可紅。

### C5 Task 2.4 → B4 末 vs §R
- **失效**：母 SPEC §R:653-654「B4 不依賴 B3 ⇒ B3／B4 可獨立 revert」在 R2 拓撲下**不再成立**（B4 的 2.4 硬依賴 B3 之 `report.py`）。Revert B3 後 B4 wiring 必 rc=2。
- A1-11 已改 B4 依賴與 gate，**但未改寫 §R 條文**；冷啟動雖以 TODO 為準，審查／回退仍可能讀到母 SPEC 舊句。
- **處置**：延伸檔增 A1-x 改 §R 為「B4 依賴 B3 3.3；可單獨 revert B4；revert B3 須連 B4 之 2.4 或接受 wiring 紅」。見 `GROK-R9-P2-02`。**不**建議改回 2.4 落點（會重開 P0-01）。

---

## Findings（canonical）

## GROK-R9-P1-01

**斷言**: A1-8／Task 3.4 將 `ValueError` 列入 reporter 捕獲集合，會使 `assess_eligibility`（及 `max_trials_budget`）的參數驗證 raise 被映射為 `reason=reporter_failed` 的 2xx 降級，而非可觀測的程式／呼叫錯誤。

**碼證**: A1-8 第 4 點與 TODO:319-324 捕獲 `(OSError, json.JSONDecodeError, ContractViolation, ValueError)`；TODO:237 參數驗證 `t_years<=0`／`n_trials<1`／`target_sharpe<=0` ⇒ `ValueError`；TODO:238 `x>700` ⇒ `ValueError`。本輪：`assess_eligibility(t_years=-1.0, …)` 落入 `except ValueError` → `("reporter_failed", "ValueError")`。RECHECK：對讀 A1-8 與 TODO 3.1／3.4；用最小 try/except 重跑上式。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md#44556a29f5c1

[MAJOR] 信心度=High。會怎麼失敗：G1-R1 接上後 route 傳錯 `t_years`／錯誤組裝 optional 時，API 測試仍 2xx＋`reporter_failed`，與驗收⑤「`TypeError`⇒5xx」的 fail-closed 精神不一致，且掩蓋 bug。修法：自訂非 `ValueError` 之 param 例外並排除於捕獲元組；或入口把非法參轉 typed `unavailable` 而讓真正的 `ValueError` 來自非預期路徑時改記 metric 後重拋。不影響 B1–B4 純函式數值路徑。

---

## GROK-R9-P2-01

**斷言**: Task 2.4 W1 若對 `build_validation_section` body 做無控制流之 Constant 鍵收集，死分支內的完整 `ast.Dict` 可使契約節名集合被視為已組裝，造成 wiring rc=0 假綠。

**碼證**: TODO:425-428 寫 Return 之 Dict 鍵＋「body 內對該回傳 dict 之 Constant 鍵指派」，未要求 CFG／可達性分析；mutation ④只覆蓋註解／docstring。本輪 AST 探針：`out={"only_runtime":1}; if False: out={五節…}; return out` → 收集鍵 ⊇ `{eligibility,min_btl,dsr,pbo,provenance}`。RECHECK：對 `ast.parse` 該片段 walk `ast.Dict` 的 `Constant` 鍵。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_TODO.md#e6d673841704

[MINOR] 信心度=Medium-High（取決於實作是否做 name→dict 資料流而無 CFG）。運行時 `validate_against_contract`（Task 3.3）仍是第二道防線，故不升 MAJOR。修法：W1 只接受**無條件**組裝路徑，或新增 mutation ⑥「`if False:` 內寫滿節名 ⇒ rc=1」；文件誠實邊界加「不保證排除死分支」。

---

## GROK-R9-P2-02

**斷言**: A1-11 使 B4 依賴 B3 Task 3.3 後，母 SPEC §R「B3／B4 可獨立 revert」已失效，但延伸檔未具名改寫 §R，留下回退敘事漂移。

**碼證**: 母 SPEC:653-654「B4 依賴 B1+B2，不依賴 B3 ⇒ B3 與 B4 可獨立 revert」；A1-11 第 1–2 點與 TODO:49、51-53 改為 B4 依賴 B3 3.3；A1 全文無 §R 條目。RECHECK：`grep -n '獨立 revert\|不依賴 B3' docs/GAP1_STRATEGY_OVERFIT_{SPEC,AMENDMENTS,TODO}.md`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#502c93cae402

[MINOR] 信心度=High。不造成 B1–B4 數值錯；冷啟動以 TODO 為準可避開。修法：A1 增一條改 §R（可單獨 revert B4；revert B3 須連動 2.4／接受 wiring 紅）。**勿**把 2.4 移回 B2。

---

## §0 被當成事實的未驗證假設

| 來源 | 宣稱 | 本輪判定 |
|---|---|---|
| brief fact | `template_check todo` PASS | **成立**（本輪重跑 PASS） |
| brief fact | r8 completeness 22/22 | **未重跑** completeness 全量（accepted）；synth 附錄 22 標題在場 |
| brief fact | J1 三值＋MinBTL receipt | **成立**（本輪重跑一致） |
| brief assumed | 22 條處置皆真關閉 | **本家族 7/7 CLOSED**；他家族抽樣 P0-02 關閉；未逐字重跑全部 22 反例 |
| brief assumed | A1↔TODO R2 無抄寫漂移 | **抽樣成立**（16 鍵／6 n_fields／12 reasons／2.4 落點／3.4 簽名／驗收⑨）；未逐字 diff 全檔 |
| A1-2 | band 放寬因 path 相關 | **成立**（三變體極差 0.11） |

---

## §1 十一類速查（R9 範圍內）

| # | 類 | 結論 |
|---|---|---|
| 1 | 矛盾／互斥 | **有** P2-02（§R vs A1-11 拓撲）；P1-01（例外政策自相矛盾於 fail-closed） |
| 2 | 漏項 | AST 死分支 mutation 未列（P2-01）；其餘 J1–J6 落點齊 |
| 3 | 不可測 | J1／⑨ 可測且已重現；§V-4 可證偽 |
| 4 | 可疑 quant | 無新假 oracle；band 誠實放寬＋雙 alpha 承接鑑別力 |
| 5 | 過度工程 | 無 |
| 6 | OOM | 4.1 預算仍在 |
| 7 | Cache | 無新 cache 面 |
| 8 | API／相容 | 三鍵投影 OK；ValueError 政策見 P1-01 |
| 9 | 測試品質 | ⑨ 禁逐 seed；wiring mutation 缺死分支 |
| 10 | Agent 可執行 | B1 可開工；Frozen 前建議修 P1-01 |
| 11 | 短命工 | 無；2.4 跨批依賴已具名 |

---

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF、R9 brief、V13、TODO R2、A1、母 SPEC §R、r8 synth J1–J6、registry G1-R3/R7/R8/R9、r8 grok 七條；template_check PASS；五檔 sha 前 12；PBO／MinBTL／§V-4／AST／ValueError 探針實跑。
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS rc=0；`venv/bin/python handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.py` → noise 0.6483/0.6158/0.5357 alpha 0.5411/0.6201/0.5487 sr_pp0.15→0.0000；等價 A1 生成式 alpha_det=0.0000 undet=0.5411 mutation OOS-champ noise=0.0000；`…-minbtl-conservatism-probe.py` → mean=0.843077 rtol≈0.011；AST/ValueError 片段如上。
FAILURES_SEEN: none
SCOPE_CHANGES: none（只讀審查；僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC/TODO/碼）；建議 A1-8 例外集合收窄屬契約敘事修補，不動三關數值
OUTPUT_ARTIFACT: `handoffs/20260817-gap1-todoadv-r9-grok.md`
STATUS: DONE
