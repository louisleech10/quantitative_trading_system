# GAP-2a／2b SPEC adversarial 審查 R1 — GROK

**task-id**: `20260818-GAP2-X-REVIEW-R1`｜**family**: grok｜**輪次**: R1  
**brief**: `handoffs/20260818-gap2-specadv-BRIEF.md`  
**審查標的**: `docs/GAP2_MARGINAL_IC_SPEC.md`＃`1912db84ebfc`  
**上游收斂**: `handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md`＃`7c72c0aa258d`  
**本家偵察**: `handoffs/20260818-gap2-recon-grok.md`＃`a5e28b535edf`  
**禁改碼／禁改 SPEC**（只產本檔）

**VERIFY（本輪實跑）**:
- `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → `TEMPLATE PASS (spec)`
- `shasum -a 256 docs/GAP2_MARGINAL_IC_SPEC.md` → `1912db84ebfc…`
- `shasum -a 256 handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md` → `7c72c0aa258d…`
- `shasum -a 256 tests/momentum/Analysis/test_ichc_contract_sync.py` → `c2eb517dd24a…`
- B3 模擬：契約加 `report_sections.marginal_ic` 後，依 `test_r6` 迴圈 ⇒ `fails ['marginal_ic']`
- O1 探針 n=5000／`tanh(2s)`：`max|zf-zs|=0`、`var_r≈7.8e-31`、未先 degenerate 之 `spearman(r,y)≈-0.69`；`1e-10` 門檻會觸發；raw 殘差 Spearman≈0.104
- O4 探針 n=20000／k=4：`Σ marg² / composite² ≈ 1.055` ∈ `[0.85,1.15]`

---

## Verdict：需修補後派工

統計主幹（D1 semi-partial 秩 IC、D3′ 揭露、O4 容差、§G／§V 多數 mutation）可支撐 TODO 骨架，但 **B3 批切與 `test_r6` 實核衝突**屬可獨立重現的批次存活性缺陷，須先改 SPEC（或把 `report_sections.marginal_ic` 明確延到 B4 與 orch 同 commit）才能按五批切法落地。另 C4 聯集之 `symbol`／`timeframe` 未進 Task 3.1、`ic_retained_ratio` 公式未釘——列 MAJOR，建議同輪補進 SPEC，勿留待實作「自行判斷」。

**BLOCKING 清單（進 TODO 前須改 SPEC）**
1. `GROK-R1-P0-01` — B3 加 `report_sections.marginal_ic` 會令 `test_r6_wider_contract_nodes_consistent` 紅；SPEC 對 reasons 的緩解敘述與實碼不符

**MAJOR（建議同輪修，可爭辯是否殘留 TODO 但本家傾向先修）**
2. `GROK-R1-P1-01` — C4 要求的 `symbol`／`timeframe` 未出現在 Task 3.1  
3. `GROK-R1-P1-02` — `ic_retained_ratio` 只寫 null 條件、未定義比值公式  
4. `GROK-R1-P1-03` — O1 在精確單調冗餘下 `|marg|≤0.02`  alone 不可用；必須先 `residual_degenerate`

---

## 挑戰 brief assumed（§0）

| assumed | 本輪 verdict | 證據 |
|---|---|---|
| vdW 投影空間最合適；O1 0.02／O4 [0.85,1.15] 夠嚴不假紅 | **O4 成立；O1 容差 alone 不成立** | O4 ratio≈1.055；O1 精確單調時 `spearman(noise,y)≈-0.69`，靠 `degenerate_threshold` 才過 → `GROK-R1-P1-03` |
| 五批無 forward dependency；1.2→2.1 bootstrap 搬移非白工 | **1.2→2.1 成立；B3→B4 不成立** | bootstrap 為同票刻意合併；但 B3 加 `report_sections` 鍵依賴 B4 orch 字串 → `GROK-R1-P0-01` |
| `enabled=True` 不弄壞既有測試（§G-1 只比既有鍵） | **大致成立（攻後仍立）** | §G-1 去除 `marginal_ic`／`survivor_output`；未找到既有測試鎖死 `ICConfig` 頂層鍵集。風險在 B4 契約＋orch 必須同 commit（與 P0-01 同源） |
| §N R1–R5 三值理由皆成立 | **成立** | 見必答 8；未找到「現在就能做且不擴 scope」之反證 |
| Task 3.1 欄位集對 ML 重建 exact rows＋防 stale 足夠 | **不成立** | C4 聯集含 symbol／tf；Task 3.1 語意段與 `build_survivor_output` 簽名皆無 → `GROK-R1-P1-01` |
| `deny_factor_in_ok_oos` 不誤傷新節；`test_r6` 以 B3 只加鍵／B4 加值可過 | **deny 成立；test_r6 緩解不成立** | deny 只拒 `module∈{orthogonalization,exposure}`；`test_r6` 對 **全部** `report_sections` 鍵查 orch 字串，reasons 新值**不被**迴圈檢查 |

---

## Findings

## GROK-R1-P0-01

**斷言**: Task 3.1（B3）指示同步把 `report_sections.marginal_ic` 寫入 `ic_report_contract.json`，但既有 `test_r6_wider_contract_nodes_consistent` 會對契約內每一個 `report_sections` 鍵要求 orchestrator 原始碼出現 `"{section}"`（僅豁免 `net_ic_analysis`）；B3 單獨落地必紅。SPEC 宣稱的緩解（B3 只加契約鍵不加 reason 值）打在錯誤攻擊面——現測對新 reason 值根本不做消費點掃描。

**碼證**: SPEC L155 加 `report_sections.marginal_ic`；L156 緩解只談 reason 值延到 B4。`test_ichc_contract_sync.py:56-61` 對 reasons 只查兩常數 `insufficient_events`／`turnover_disabled`，但對 `contract["report_sections"]` 全鍵要求 `"{section}" in orch_src`（豁免僅 `net_ic_analysis`）。VERIFY 模擬：契約臨時加 `marginal_ic` ⇒ `fails ['marginal_ic']`；填滿 `reasons.marginal_ic` 新值不會使該測因新值而紅。RECHECK: `sed -n '43,61p' tests/momentum/Analysis/test_ichc_contract_sync.py`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[BLOCKING] 信心度=High。會怎麼失敗：B3 commit 後 `pytest …test_ichc_contract_sync.py` 紅，五批「B3 可獨立綠」敘事崩解；或實作者為過測提前改 orch／放寬測試＝假綠或越界。  
修法（擇一寫進 SPEC）：(a) B3 不加 `report_sections.marginal_ic`，該鍵與 reason 值皆於 B4 與 `_stage6b`／組裝字串同 commit；(b) 明示 B3+B4 對契約該鍵不可拆 commit；(c) 測試豁免清單加 `marginal_ic`（最弱，需另證不會幽靈節）。

---

## GROK-R1-P1-01

**斷言**: 收斂檔 C4 欄位聯集（codex 最嚴版，已採納）明列 `symbol`／`timeframe`，但 SPEC Task 3.1 的契約頂層鍵清單、`provenance`／`split` 語意段、與 `build_survivor_output(...)` 簽名皆未出現這兩欄；依 brief「對未來 ML 消費端重建 exact rows＋防 stale 足夠」之 assumed，契約集合不足。

**碼證**: synth C4 明列 symbol／timeframe；SPEC L155–157 之 `survivor_file_keys`／`provenance`／`split`／`build_survivor_output(...)` 簽名無此兩欄。本輪掃描 Task 3.1 段 L153–162：`symbol: NO`、`timeframe: NO`（`labels_content_hash`／`row_identity`／`feature_set_hash` 有）。僅靠 `features_path` 或 row hash 不能機器強制跨 symbol 隔離。RECHECK: `grep -n 'symbol\|timeframe' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MAJOR] 信心度=High。會怎麼失敗：事件型／多標的消費端無法 fail-closed 驗「此倖存者檔屬於哪顆 symbol/tf」；stale 或錯掛 features 時只靠 path 慣例。  
修法：Task 3.1 契約必填 `symbol`／`timeframe`（頂層或 `sample_scope`／`provenance` 擇一釘死）；`build_survivor_output` 簽名加入並加驗證⑫類 hash／相等斷言；同步 §V 一條 mutation（錯 symbol ⇒ raise）。

---

## GROK-R1-P1-02

**斷言**: Task 1.2 輸出 `ic_retained_ratio` 但 SPEC 只規定 `|gross|<1e-12 ⇒ null`，未釘比值定義（`marginal/gross` vs `|marginal|/|gross|` vs 符號對齊後），兩實作可自洽綠燈而前端「retained」欄語意相反。

**碼證**: SPEC L109：`ic_retained_ratio`（`|gross|<1e-12` ⇒ null）— 無等式。B5 L213 表格要顯示 `retained`。D1／§G 無 O-numeric 定義該比值。  
RECHECK: `grep -n 'ic_retained_ratio\|retained' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。會怎麼失敗：`train_ic<0` 或 marginal 與 gross 異號時，signed vs abs 比值差到變號；B5 與契約消費者解讀分裂。  
修法：釘死 `ic_retained_ratio = marginal_ic / gross_ic`（保留符號； `|gross|<1e-12 ⇒ null`），並加一條單元斷言（構造 gross<0、marginal≈gross ⇒ ratio≈1）。

---

## GROK-R1-P1-03

**斷言**: §G O1 寫 `|marginal_ic|≤0.02` 或 `residual_degenerate` 二擇一；但對嚴格單調冗餘（`tanh(2s)`／`x³`），vdW 分數與基底分數逐點相等，殘差數值噪聲之 Spearman 可達 `|ρ|≈0.7`（n=5000），絕對值容差分支 alone 必然假紅；正確性完全依賴「先 `var(r)≤degenerate_threshold` 再算 IC」的求值順序，而 Task 1.2 改法未把該順序寫成硬約束。

**碼證**: SPEC L78 O1；L109 敘事有先後但未列入不可做／驗證必須先 gate。VERIFY n=5000／`tanh(2s)`：`max|zf-zs|=0`、`var_r≈7.8e-31≤1e-10`、未 gate 之 `spearman(r,y)≈-0.693`；raw 殘差≈0.104>0.10。RECHECK: 重跑文首 O1 探針。

**來源摘要**: docs/GAP2_MARGINAL_IC_SPEC.md#1912db84ebfc

[MAJOR] 信心度=High。會怎麼失敗：實作先算 Spearman 再看 abs≤0.02 → O1 假紅；或放寬 0.02／關掉 raw>0.10 反向斷言換綠＝削弱 D1 防退回 raw。  
修法：O1／Task 1.2 明定必須先 degenerate gate；`|·|≤0.02` 僅適用近單調／非精確共線；加 mutation：刪除 gate 先後 ⇒ O1 紅。

---

## GROK-R1-P2-01

**斷言**: 收斂 C7 要求 mutation 覆蓋含 hash mismatch／shuffle-S；§V 17 條有 feature_set_hash 的**測試斷言**（Task 3.1 ⑫）但無對應 §V mutation 編號，shuffle-S（條件集列洗牌應不變）亦缺，抗回歸網比 C7 窄一截。

**碼證**: synth C7「hash mismatch」；§V L225–242 列 V-1..V-17——無「打亂 S 欄序仍 exact」「`feature_set_hash` 篡改必紅」之 mutation 條（⑫ 是測試斷言非 probe 腳本 case）。  
RECHECK: `grep -n 'shuffle\|hash mismatch\|feature_set_hash' docs/GAP2_MARGINAL_IC_SPEC.md`。

**來源摘要**: handoffs/reconcile/20260818-gap2-x-consult-r1/synth.md#7c72c0aa258d

[MINOR] 信心度=Medium。不阻 TODO 生成；建議 §V 加 V-18／V-19 或於 Task 1.3／3.2 probe 具名納入。不列 BLOCKING。

---

## 必答 1–9

### 1. 統計定義正確性
**Verdict: 主幹正確，附 2 個須釘死點（P1-02／P1-03）。**  
D1 semi-partial 秩 IC（vdW → train OLS → test 殘差 → Spearman(y)）與「非 raw／非 partial／非 Δcomposite」一致；`normal_scores` 各自 mask 轉換與 train-β／test-apply 相容（漸近同分位）。`sequential` 依 `|train_ic|` 合理。`ic_retained_ratio` **公式缺失**（P1-02）。O1 之 0.02 非精確單調之可靠門（P1-03）；O2／O3／O6／O7／O8 可證偽；O4 本輪 ratio≈1.055，容差帶合理；O5／O9 設計足夠。未發現 D1 選擇 vdW 相對 raw 的數學錯誤（raw 假陽已有反向斷言）。

### 2. OOS 與揭露誠實度
**Verdict: 足夠且偏嚴。**  
D3／D3′：`oos_guarantees` 沿用 root＋強制 `independent_oos_validation=false`＋`selection_sample="test"`＋train 並列統計＋禁文案，正確對應 C1。一律 `oos_guarantees=False` 更「看起來嚴」但與 root 契約／`ok_oos` 語意矛盾（preprocessing 未在 test 擬合卻整節否認），SPEC 選擇較優。`marginal_ic_train_insample` 名含 insample，誤讀為 OOS 風險低；建議前端／`_doc` 再強調（非 BLOCKING）。

### 3. 可證偽驗收
**Verdict: 大致足夠；缺 hash／shuffle mutation 與 retained 公式。**  
各 Task 驗證含命令與數值；§V 17 條覆蓋 train-only fit／秩空間／符號權重／契約 fail-closed／既有鍵。缺：retained 公式斷言、O1 gate 順序 mutation、C7 hash／shuffle（P2-01）。

### 4. forward dependency 與存活性
**Verdict: 1.2→2.1 非白工；B3→B4 有硬依賴（P0-01）。**  
Task 1.2 鍵集對 3.1 契約有「先常數後改讀」過渡，可接受。B3 加 `report_sections.marginal_ic` 不可在無 orch 字串時單獨綠。

### 5. 義務覆蓋 C1–C7
| 群集 | SPEC 對應 | 遺漏／弱化 |
|---|---|---|
| C1 | D3′＋契約欄＋§N R5 | 無實質弱化 |
| C2 | D1／D2 | 無 |
| C3 | D4／D5＋§N R2 | 無 |
| C4 | Task 3.1 | **缺 symbol／timeframe（P1-01）**；其餘聯集大多在語意段 |
| C5 | D7＋Task 4.1 | 無 |
| C6 | Task 4.3＋B5 | 無（但 B3 同步節鍵時序錯） |
| C7 | §G／§V | mutation 略窄（P2-01） |

### 6. 契約設計（2b）
**Verdict: 架構可行；欄位完備性與批切有洞。**  
ref 機制、`sample_scope` 結構、`additional_properties:false`、與 `RowMaskPlan.source` AST sync——可行，無明顯載入循環。Task 3.1「語意描述」已構成**實質第二處鍵名列舉**（與 §C「只在契約檔出現一次」緊張），且列舉仍漏 C4 欄——危險的是「看似完整的長列表」。建議語意段改 pointer＋「完整鍵以契約檔／C4 checklist 核對表」避免漂移。

### 7. 接線影響面
**Verdict: 白名單 7 處完整；路徑行為大致明定。**  
`analyze`／`refilter`／`analyze_full`／fallback／xsec／`_suppress_persist`／cache-hit refilter 邊界有寫。`REPORT_SECTIONS` 改讀契約後 R3 語意從「五節硬編碼」變「契約全鍵」——正確修復漂移，但使 P0-01 更硬（新節必須有組裝字面）。B5：`vitest`／`npm run build`／`tsc` 有驗收；風險可控。`deny_factor_in_ok_oos` 不誤傷新節（無 module 鎖）。

### 8. 殘留誠實度 R1–R5
| 殘留 | Verdict |
|---|---|
| R1 橋本體 user-ruling | **成立**（成熟度地圖；現接會隨 ML 殼作廢） |
| R2 stepwise needs-research | **成立**（能做≠有認可之多重比較政策；D4 已禁選擇） |
| R3 xsec blocked-by #4 | **成立** |
| R4 前端預設納入、白話閘可否決 | **合規** |
| R5 nested blocked-by holdout-only | **成立**（本票內加 frozen test ＝改主線切分，超 scope） |

### 9. 可以進 TODO 生成嗎？
**Verdict: 否 — 須先消 P0-01（並強烈建議同輪消 P1-01..03）。**  
修補後可進 TODO；P2-01 可殘留 TODO。

---

## §1 必查 11 類

1. **矛盾/互斥**：有 — B3 同步 `report_sections` vs `test_r6`／緩解敘述（P0-01）；§C 單次列舉 vs Task 3.1 長表。  
2. **漏項/端到端**：有 — symbol／tf（P1-01）。  
3. **不可測驗收**：有 — `ic_retained_ratio`（P1-02）。  
4. **可疑 quant 假設**：有條件 — O1 容差 alone（P1-03）；vdW 主幹可接受；O4 容差本輪實測 OK。  
5. **過度工程**：無。  
6. **OOM/並行**：無（§V 具名不測 OOM 合理）。  
7. **Cache 正確性**：邊際 — survivor 缺 symbol/tf 弱化跨標的隔離（併 P1-01）；`_ic_cache stage6b_results` 有寫。  
8. **API/型別/相容**：無重大；B5 在 ICHC 段外加型別正確。  
9. **測試品質**：大致強；缺 gate 順序／hash／shuffle mutation。  
10. **Agent 可執行性**：高，但 P0-01 會讓 Agent 在 B3 卡死或自行改測。  
11. **必要性/短命工**：1.2 內部 bootstrap→2.1 搬移＝刻意合併、非跨 Phase 白工；**無**其它短命刪除項。B3 若按錯誤時序加節鍵則屬「必返工」而非短命。

---

## 被當成事實的未驗證假設（§0 匯總）

| SPEC／brief 陳述 | fact / assumed | 本輪 |
|---|---|---|
| D1 vdW semi-partial 為正確統計量 | assumed（有探針／文獻） | 攻後**主幹成立**；O1 容差 alone 不成立 |
| D3′ 較嚴版足以防「獨立 OOS」誤稱 | fact-aligned C1 | **成立** |
| B3 reason 緩解使 test_r6 可過 | assumed | **不成立**（P0-01） |
| Task 3.1 欄位＝C4 聯集 | 呈述為已覆蓋 | **不成立**（缺 symbol/tf） |
| `enabled=True` 無害既有鍵黃金 | assumed | **大致成立**（§G-1） |
| §N R1–R5 不能現做 | assumed | **成立** |

---

ASSUMPTIONS_VERIFIED: template PASS；SPEC/synth/test_ichc_contract_sync sha12；test_r6 源碼行為＋B3 模擬 fails=['marginal_ic']；deny_factor_in_ok_oos 只鎖 orth/exposure；O1 degenerate 探針；O4 ratio∈帶；C4 vs Task 3.1 symbol/tf 缺席；ic_retained_ratio 無公式
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP2_MARGINAL_IC_SPEC.md` → PASS；python B3/O1/O4 探針（見文首）；交件前 `bash scripts/completeness_check.sh --single handoffs/20260818-gap2-specadv-grok.md --family grok`（見下）
FAILURES_SEEN: none（唯讀審查）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none（未改 SPEC／碼）；建議影響＝B3 契約時序、survivor 加 symbol/tf、retained 公式、O1 gate 順序
OUTPUT_ARTIFACT: handoffs/20260818-gap2-specadv-grok.md

STATUS: DONE
