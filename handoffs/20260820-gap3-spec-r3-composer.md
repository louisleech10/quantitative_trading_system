# GAP-3 事件型 SPEC adversarial review R3 — COMPOSER（sentinel 確認）

task-id: `20260820-GAP3-X-REVIEW-R3`  
審查標的: `docs/GAP3_EVENT_SPEC.md` @ `c7ac693e`（sha256 `377c9a39b01e23b804fe7ea6fc88c9390abd1e992d6d2b47d9167d9abd521c07`）  
R2 收斂權威: `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md`（Y1–Y6＋sentinel 節）  
brief: `handoffs/20260820-gap3-spec-r3-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 前提 | 標注 | R3 複核結論 |
|---|---|---|
| R2 reconcile completeness PASS（8/8 heading） | fact-verified（brief） | 未重跑 `--lock`；本輪只驗 Y1–Y6 寫回與新錯掃描 |
| R2 修訂版 `template_check spec` PASS | fact-verified | 本輪重跑 `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0 |
| Y1–Y6 寫回無語意漂移 | **assumed → 攻後成立** | 六群集逐條對讀 synth 處置 vs `git diff 21135434..c7ac693e`；0 掉項、0 反向裁決 |
| Y2 預設值忠實於使用者 §2-4 原例 | **assumed → 攻後成立** | 白話 §2 第 4 點：a＝漲≥5%後續不漲、b＝震盪上下 1%、c＝跌 x%；SPEC B1.5 預設 0.05/0.0/0.01/0.05 與公式語意對齊 |
| Y6 accepted 集與 §N-7 全文一致 | **assumed → 攻後成立** | B1.0 validator 三值 accepted＋`platform_random_bars` 恆拒；§N-7 仍列 needs-research 殘留且註記 X13 拆分——無矛盾 |

## Y1–Y6 synth 處置 vs SPEC 寫回忠實度

| 群集 | synth 處置要點 | SPEC 落點 | 漂移？ |
|---|---|---|---|
| Y1 | D1-6 映射表＋receipt `entry_at_ms`/`entry_price_source`＋B2.1/§G-2 | D1-6 L27；D2-1 六欄含 `entry_at`；B2.1 L210；§G L107 | 無 |
| Y2 | direction-aware 公式＋四門檻預設＋boundary fixtures | B1.5 L184–185（公式/預設/驗證三點） | 無 |
| Y3 | 匯入欄三值 vs derived `counterexample_kind_effective`＋分層消費 derived | B1.0 L126；B1.5 L184；B2.2 L221 | 無（見下註） |
| Y4 | §V 統一命令＋fixture 身分＋誠實邊界 digest | §V L359–371（M1–M12 共 12 條） | 無 |
| Y5 | permutation quantile oracle `N_perm=1000` | B1.4 L173；§V M8 L367 | 無 |
| Y6 | validator accepted 三值；`platform_random_bars` 恆拒；B3.2 同一 validator | B1.0 L123；B3.2 L278–279；§N-7 L396 | 無 |

**註（非 finding）**：D4-2 L43 仍寫 `counterexample_kind` 分層字樣，但 B1.0 L126 已寫全局規則「分層報表一律消費 derived 欄」且 B2.2 已改 `counterexample_kind_effective`；Y3 synth 處置範圍僅 B1.0/B1.5/B2.2，屬 R1 遺留措辭、由全局規則覆蓋，不構成 R3 新引入 BLOCKING/MAJOR。

## 專項攻擊面（brief 指定）

| 攻擊面 | 探針 | 結果 |
|---|---|---|
| D1-6 映射表 vs D2 六欄不變式 | D1-6 `decision_at ≤ entry_at`；D2-1 `…≤ decision_at ≤ entry_at ≤ label_start…`；五種 semantic 均可滿足（含 `next_open` k>0） | 內部一致 |
| Y2 公式 vs 使用者 §2-4 | 讀 `白話說明/GAP-3事件型討論.md` §2 第 4 點；B1.5 `R0`/`Rw` signed return＋a/b/c 門檻與原例 5%/1%/跌 x%（x 預設 5%） | 忠實 |
| Y3 兩值集 vs JSON SoT | §C L91 單一契約檔；B1.0 L126 兩值集「字面入契約檔」、derived 住 manifest | 符合 SoT 原則 |
| Y6 accepted 集 vs §N-7 | `rg control_kind\|platform_random` → B1.0 三值 accepted＋恆拒 reason；§N-7 殘留＋X13 註記 `platform_same_trigger_rule` 非殘留 | 一致 |
| X1–X13 寫回是否被 Y1–Y6 衝突 | 對照 R2 composer X1–X13 表；Y 寫回為增量修補（D1-6、B1.5 公式、B2.2 derived、§V、B1.0 validator），未反向 X 裁決 | 無衝突 |

## R2 sentinel 結論保留確認

R2 synth sentinel 節引用 COMPOSER-R2-P3-00：X1–X13 寫回忠實、R1 己方 findings CLOSED、殘餘 sweep 無新錯。R3 修訂僅追加 Y1–Y6（diff 98 行），未改動 X 群集正文；本輪重掃 M1–M12（`rg -c "^  - M"` → 12）、B1 批內順序、B3 依賴 B2.5、§N-7/8——**R2 sentinel 結論仍成立**。

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾 | 無 |
| 2 漏項 | 無 |
| 3 不可測 | 無 |
| 4 quant 假設 | 無新疑 |
| 5 過度工程 | 無 |
| 6 OOM | 無 |
| 7 Cache | 無 |
| 8 API/型別 | 無 |
| 9 測試品質 | 無 |
| 10 Agent 可執行性 | 無 |
| 11 短命工 | 無 |

## 必答

1. **Y1–Y6 忠實度＋新錯掃描**：六群集全數字面落地；專項四攻擊面無 BLOCKING/MAJOR；X1–X13 無碼證衝突。
2. **可否進三家 RECONCILE-STAMP＋使用者白話閘？**：**可以**——Y1–Y6 閉合寫回可證偽；無實質 finding 須再修 SPEC。

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；Y1–Y6 寫回忠實於 R2 synth 處置，與 X1–X13 無碼證衝突，專項四攻擊面（D1-6↔D2、Y2↔§2-4、Y3↔JSON SoT、Y6↔§N-7）未見新錯。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `377c9a39…` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md` → 98 行、涵蓋 Y1–Y6 全部落點；`rg -n "D1-6|counterexample_kind_effective|permutation quantile|test_mutation_guard|platform_random_bars.*恆拒"` → 命中 D1-6/B1.0/B1.4/§V/B1.0；`rg -c "^  - M"` → 12；對照 `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md` Y1–Y6 處置原文與 `白話說明/GAP-3事件型討論.md` §2 第 4 點反例三類原例。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md

sentinel：0 findings（實質）；上列為 R3 Y1–Y6 忠實度＋X1–X13 衝突掃描＋四專項攻擊面之機械複驗摘要。

## Verdict：可派工

Y1–Y6 已可證偽落地；可進 **三家 RECONCILE-STAMP＋使用者白話閘**。無 BLOCKING/MAJOR 須再修 SPEC。

---

ASSUMPTIONS_VERIFIED: SPEC sha256 `377c9a39…`＝brief；template_check PASS；Y1–Y6 六群集對 synth 0 漂移；Y2 預設對 §2-4 原例；Y6 與 §N-7 一致；X1–X13 無衝突；M1–M12 共 12 條  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → 377c9a39…；`bash scripts/completeness_check.sh --single handoffs/20260820-gap3-spec-r3-composer.md --family composer` → 見下行  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r3-composer.md`

STATUS: DONE
