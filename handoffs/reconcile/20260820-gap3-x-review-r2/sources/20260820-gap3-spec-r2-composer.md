# GAP-3 事件型 SPEC adversarial review R2 — COMPOSER

task-id: `20260820-GAP3-X-REVIEW-R2`  
審查標的: `docs/GAP3_EVENT_SPEC.md` @ `21135434`（sha256 `9f63e290e89a1dde96b44c217866d01d0113b0dc47f19b5acd0a7e356459f5bf`）  
R1 收斂權威: `handoffs/reconcile/20260820-gap3-x-review-r1/synth.md`（X1–X13＋AR-1..AR-6）  
brief: `handoffs/20260820-gap3-spec-r2-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 前提 | 標注 | R2 複核結論 |
|---|---|---|
| R1 reconcile completeness PASS（15/15） | fact-verified（brief） | 未重跑 `--lock`；本輪只驗 SPEC 寫回，不質疑 R1 union |
| 修訂版 `template_check spec` PASS | fact-verified | 本輪重跑 `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0 |
| 主委 X1–X13 寫回無語意漂移 | **assumed → 攻後成立** | 十三群集逐條 grep/對讀；未見掉項或反向裁決；見下表 |
| AR 裁決與 R1 原意相容 | **assumed → 攻後成立** | `decision_offset_bars` int≥0（非 R1 composer 負號版）、`unclassifiable` 不猜（非 R1 composer precedence）、`cluster_weight=1/n_events_in_time_cluster`（X9 收斂）均已字面落地 |

## R1 findings 閉合驗證（§B8）

| ID | R1 斷言摘要 | 重跑探針 | 判定 |
|---|---|---|---|
| COMPOSER-R1-P1-01 | `cluster_weight` 公式缺失、estimand 分裂 | `rg -n "cluster_weight\|1/n_events_in_time_cluster" docs/GAP3_EVENT_SPEC.md` → B1.3 L160 字面公式＋契約檔唯一；M5 L363 綁 mutation；B1.3 驗證 L161 手算權重和＝1 | **CLOSED** |
| COMPOSER-R1-P1-02 | B3 依賴缺 B2.5（G6） | `rg -n "Phase B3\|B2\.5\|evaluate_all_bars\|禁平行實作" docs/GAP3_EVENT_SPEC.md` → B3 L260 `依賴：**B1＋B2.5**`；B3.2 L277 G6 呼叫 B2.5、禁平行實作；B3.2 驗證 L278 G6 整合測試 | **CLOSED** |

## X1–X13 synth 處置 vs SPEC 寫回忠實度

| 群集 | synth 處置要點 | SPEC 落點 | 漂移？ |
|---|---|---|---|
| X1 | `t0`＋`decision_offset_bars` int≥0；衍生 `decision_at_ms`；§G-2 k=0/k>0 oracle | D2-2；B1.0 L122；§G L106；M9 L367 | 無 |
| X2 | label 錨＝t₀ close；禁 `return_N[decision_at]` join | D1-5；B2.3 L233 | 無 |
| X3 | `conditional_ic` 缺 `label_value` ⇒ `missing_label_value`；v1 不重算；§N-8 殘留 | D1-3；B1.0；§N-8 L396 | 無 |
| X4 | `counterexample_classifier_config`；user 優先；多類 ⇒ `unclassifiable` | B1.0 L125；B1.5 L183–185；M10 L368 | 無（composer R1 precedence 不採＝synth 已定） |
| X5 | T8/T9/T10 條件必填 | B1.0 L124；M12 L370 | 無 |
| X6 | `event_split_plan` 必需輸入；macro/micro；`degraded:single_symbol` | §A AR-3 L72；B2 共同約束 L203；B4.1 L303；M11 L369 | 無 |
| X7 | 新增 B1.6 特徵物化；B1.4 改吃 B1.6；B3.3 `state_counters.py` 寫死 | B1 批內順序 L115；B1.6 L190–199；B3.3 L286 | 無 |
| X8 | M1–M12 逐條 baseline/mutation/rc | §V L358–370（12 條） | 無 |
| X9 | `cluster_weight = 1/n_events_in_time_cluster` | B1.3 L160；M5 L363 | 無 |
| X10 | B3 依賴 B1＋B2.5；G6 禁平行實作 | B3 L260；B3.2 L277–278 | 無 |
| X11 | `entry_price_semantic` 頂層化 | D1-1 L22；B1.0 L122 | 無 |
| X12 | K6 落批 C9 腳註；G1–G6 六條驗收 | B4 L297；B3.2 驗證 L278 | 无 |
| X13 | `platform_same_trigger_rule` 收回 B3.2；`platform_random_bars` needs-research | B1.0 L122；B3.2 L277–278；§N-7 L395 | 无 |

**小結**：十三群集 0 掉項、0 反向裁決、0 主委抄寫漂移可阻擋收斂。

## 殘餘 sweep（修訂是否引入新錯）

| 攻擊面 | 探針 | 結果 |
|---|---|---|
| D1-5 label 錨 vs D2-2 offset | D1-5 明訂 `decision_offset_bars>0` 不改錨；D2-2 特徵跟 `decision_at`、label 跟 t₀ close | 内部一致 |
| B1 批內順序（B1.6 插入） | L115 `B1.0→…→B1.3→B1.6→B1.4→B1.5`；B1.4 L170 輸入＝B1.6 | 一致 |
| X6 共同約束 vs 各 Task | B2 區塊 L203「各 Task 驗證含此共同約束斷言」；B4.1 L303 重複必需輸入 | 可執行（phase 級約束＋B4.1 明示足夠） |
| M1–M12 可證偽性 | `rg -c "^  - M" docs/GAP3_EVENT_SPEC.md` → 12；每條含 baseline/mutation/預期 rc | 无空殼 |
| §N-7/8 三值理由 | §N L389–396：§N-7 `needs-research`＋X13 拆分註記；§N-8 `needs-research`＋D1-3 配套 | 成立 |

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾 | 无 |
| 2 漏项 | 无 |
| 3 不可测 | 无 |
| 4 quant 假设 | 无新疑（D1/D2 锚点已闭合） |
| 5 过度工程 | 无 |
| 6 OOM | 无 |
| 7 Cache | 无 |
| 8 API/型別 | 无 |
| 9 测试品质 | 无 |
| 10 Agent 可执行性 | 无 |
| 11 短命工 | 无 |

## 必答

1. **R1 闭合规**：COMPOSER-R1-P1-01、P1-02 均 **CLOSED**（上表）。
2. **X1–X13 忠实？**：是；漂移 0 处。
3. **新引入错误？**：未发现 BLOCKING/MAJOR。
4. **可否进三家 RECONCILE-STAMP＋使用者白话闸？**：**可以**——R1 处置已可证伪落地；无残余 BLOCKING/MAJOR 须再修 SPEC。

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的實質 finding；R1 兩條 MAJOR 均已 CLOSED，X1–X13 寫回忠實，殘餘 sweep 五面未見新錯。

**碼證**: `sha256sum docs/GAP3_EVENT_SPEC.md` → `9f63e290…` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`rg -n "cluster_weight = 1/n_events_in_time_cluster|依賴：\*\*B1＋B2\.5|禁平行實作|unclassifiable|B1\.6"` → 命中 B1.3/B3/B1.5/B1 批內順序；`git diff e0af4a3d..21135434 -- docs/GAP3_EVENT_SPEC.md` → 224 行修訂對齊 synth 十三群集。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a; handoffs/reconcile/20260820-gap3-x-review-r1/synth.md

sentinel：0 findings（實質）；上列為 R2 閉合＋synth 忠實度＋殘餘 sweep 之機械複驗摘要。

## Verdict：可派工

R1 reconcile 寫回已閉合；可進 **三家 RECONCILE-STAMP＋使用者白話閘**。無 BLOCKING/MAJOR 須再修 SPEC。

---

ASSUMPTIONS_VERIFIED: SPEC sha256 `9f63e290…`＝brief；template_check PASS；COMPOSER-R1-P1-01/02 重跑探针 CLOSED；X1–X13 逐条对照 synth 无漂移；M1–M12 共 12 条  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；`sha256sum docs/GAP3_EVENT_SPEC.md` → 9f63e290…；`rg` 闭合规探针见上表  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r2-composer.md`

STATUS: DONE
