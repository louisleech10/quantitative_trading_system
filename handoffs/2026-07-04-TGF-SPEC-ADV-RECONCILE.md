# TGF SPEC Adversarial RECONCILE（2026-07-04）

對象：docs/TEMPLATE_GATE_FIX_SPEC.md（v2，已依兩家 adversarial 修訂）＋ docs/TEMPLATE_GATE_FIX_MANIFEST.md（29 ID）。
兩家 findings 全數 ACCEPTED，無 REJECTED、無降級。機檢：SPEC v2 過 template_check（exit 0）＋ coverage 29/29（exit 0）。

## 對映表（[Finding ID] → [修補位置] → [SPEC 階段 RECHECK]；實作階段 RECHECK 依各 finding 原命令列入驗收）

| Finding ID | 級別 | 修補位置 | SPEC 階段 RECHECK（可立即重跑） |
|---|---|---|---|
| ADV-CODEX-1（原 ADV-C1） | BLOCKING | Task 2.1 改法改「§A 段級狀態機」；Task 1.1 增 `spec_heading_verified_bypass.md` fixture | `grep -c "段級狀態機" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1；`grep -c "spec_heading_verified_bypass" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥2 |
| ADV-CODEX-2（原 ADV-C2） | MAJOR | Task 2.2 ②：a/d 之 §G 限 `atol|rtol|sha256`，明文「exit/== 不算」；manifest [A-3] 同步 | `grep -c "exit.*不算" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-CODEX-3（原 ADV-C3） | MAJOR | Task 6.1 定死 `gate.sh dispatch --reconcile <path>` CLI 契約＋4 fixture 驗收（拒/拒/拒/發） | `grep -c -- "--reconcile <path>" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-CODEX-4（原 ADV-C4） | MINOR | Task 4.1 ID 格式定 family-scoped `ADV-CODEX-<n>`／`ADV-COMPOSER-<n>`；Task 6.1 gate regex 同步 | `grep -c "ADV-CODEX-<n>" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-COMPOSER-1（原 ADV-P1） | BLOCKING | §A 事實更正 6→7 處（附誤計事故註記）；Task 6.2 檔案清單/驗收基準改 7 | `grep -c "共 7 處" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1；`grep -n "§1.0\|§1\.4" CLAUDE.md scripts/gate.sh docs/MULTI_AGENT_ORCHESTRATION.md \| wc -l` = 7 |
| ADV-COMPOSER-2（原 ADV-P2） | MAJOR | Task 2.1 觸發域=整個 fact-scope 子段（標題進入/離開）；Task 1.1 增 `spec_ic_phase0_style.md`；§A 補 IC_PHASE0 exit 0 事實 | `grep -c "spec_ic_phase0_style" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥2 |
| ADV-COMPOSER-3（原 ADV-P3) | BLOCKING | Task 6.2 定案策略(a)：7 處全改寫為不含舊錨點字面、語意文字保留；驗收=0 不再與邊界互斥 | `grep -c "不含 .§1.0./.§1.4. 字面\|不留可 grep 的舊錨點字面" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-COMPOSER-4（原 ADV-P4） | BLOCKING | Task 2.2 棄 NLP grep，改 `RISK-HIT:` 結構化宣告制（缺行 fail-closed）；Task 1.1 增 `spec_risk_false_positive.md`；Task 3.1 範本教學；本 SPEC §RISK 自帶宣告 | `grep -c "RISK-HIT" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥5 |
| ADV-COMPOSER-5（原 ADV-P5） | MAJOR | Task 1.1 增 3 個 result fixture；Task 1.2 支援 result kind；Task 2.4 驗證改引用固化 fixture | `grep -c "result_pass_empty_receipts" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥2 |
| ADV-COMPOSER-6（原 ADV-P6） | MAJOR | §V mutation 擴至全 A-* 規則（MUTATION.txt 登記，分列 Task 2.1–2.4 驗收） | `grep -c "MUTATION.txt" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥2 |
| ADV-COMPOSER-7（原 ADV-P7） | MAJOR | 同 ADV-CODEX-3（Task 6.1 --reconcile） | 同上 |
| ADV-COMPOSER-8（原 ADV-P8） | MAJOR | Task 5.2 併入 Task 4.1（prompt 檔單一改動點）；§P 依賴註記更新 | `grep -c "已併入 Task 4.1" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-COMPOSER-9（原 ADV-P9） | MINOR | Task 6.2 GRANDFATHER 明列 docs/IC_PHASE0_SPEC.md；spec_ic_phase0_style 探針另涵蓋 | `grep -c "IC_PHASE0_SPEC" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥2 |
| ADV-COMPOSER-10（原 ADV-P10） | MINOR | Task 5.1 驗證改全機械 grep 斷言（無條件讀行不得含三大檔名） | `grep -c "全機械斷言" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-COMPOSER-11（原 ADV-P11） | MINOR | manifest 新增 [D-5]＋Task 6.2 RESULT 映射一行（收窄版 C-6，全域統一列二期） | `grep -c "D-5" docs/TEMPLATE_GATE_FIX_MANIFEST.md` ≥1 |

## 請兩位委員做的事（閉合鐵律：原提出方重驗）
1. 重讀 docs/TEMPLATE_GATE_FIX_SPEC.md（v2）與本對映表，逐條重跑**你自己提出**的 finding 之 SPEC 階段 RECHECK。
2. 全部確認關閉 → 在本檔末 append 一行：`RECONCILE-STAMP: <CODEX|COMPOSER> APPROVED 2026-07-04`；任何一條未真關閉 → append `RECONCILE-STAMP: <family> REJECTED — <ID>+理由`。
3. 不重開已定案項；發現 v2 修訂**新引入**的問題可另列（格式同 adversarial，family-scoped ID 續號）。

---
（委員戳記 append 於下）

## Composer 2.5 閉合輪重驗（2026-07-04）

| Finding | RECHECK 結果 | 判定 |
|---------|-------------|------|
| ADV-COMPOSER-1 | `共 7 處`=1；live grep wc -l=7 | **關閉** |
| ADV-COMPOSER-2 | `spec_ic_phase0_style`=2 | **關閉** |
| ADV-COMPOSER-3 | 策略(a)字面=2（含「不留可 grep 的舊錨點字面」） | **關閉** |
| ADV-COMPOSER-4 | `RISK-HIT`=11 | **關閉** |
| ADV-COMPOSER-5 | `result_pass_empty_receipts`=2 | **關閉** |
| ADV-COMPOSER-6 | `MUTATION.txt`=3 | **關閉** |
| ADV-COMPOSER-7 | `--reconcile <path>`=1 | **關閉** |
| ADV-COMPOSER-8 | `已併入 Task 4.1`=1 | **關閉** |
| ADV-COMPOSER-9 | `IC_PHASE0_SPEC`=3 | **關閉** |
| ADV-COMPOSER-10 | `全機械斷言`=1 | **關閉** |
| ADV-COMPOSER-11 | manifest `D-5`=1 | **關閉** |

輔助：`template_check.sh spec` exit 0；`coverage_check.sh` 29/29 exit 0。

### v2 新引入（不阻擋原 11 條閉合）

**ID:ADV-COMPOSER-12 [MAJOR] 信心度:High** — §G 通過條件仍寫「3 繞過探針 exit 0→1」，§A FACT-RECEIPT 仍寫「三個繞過探針」，但 Task 1.1／manifest [F-1] 已擴至 **7** 個繞過探針；執行端手填 EXPECTED.txt 時可能漏列 4 探針 → 假綠。  
證據：§G L32、§A L17 vs Task 1.1 L38／[F-1] L42。  
修法：§G／§A 計數改 7，或改為「F-1 所列全部繞過探針」不寫死數字。  
RECHECK: `grep -c "3 繞過\|三個繞過" docs/TEMPLATE_GATE_FIX_SPEC.md` = 0 且 §G 與 F-1 探針清單一致。

**ID:ADV-COMPOSER-13 [MINOR] 信心度:High** — manifest [D-3] 檔名 typo `MULTI_AGent_ORCHESTRATION.md`（Agent 大小寫錯），SPEC Task 6.2 用正確路徑；copy-paste 風險。  
修法：manifest L31 改為 `MULTI_AGENT_ORCHESTRATION.md`。  
RECHECK: `grep -c "MULTI_AGent" docs/TEMPLATE_GATE_FIX_MANIFEST.md` = 0。

RECONCILE-STAMP: COMPOSER APPROVED 2026-07-04
RECONCILE-STAMP: CODEX APPROVED 2026-07-04
