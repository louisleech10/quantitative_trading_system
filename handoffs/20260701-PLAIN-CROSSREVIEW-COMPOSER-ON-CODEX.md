# 白話版互審 — Composer 2.5 審 Codex 版

**任務**：對照 `docs/VERIFY_GATE_SPEC.md`（v2.1 原文）與 `docs/VERIFY_GATE_SPEC_PLAIN_CODEX.md`（Codex 白話版），核對忠實度、關鍵風險/trade-off 是否遺漏、非技術讀者友善度。  
**審閱者**：Composer 2.5 | **日期**：2026-07-01

---

## 總評

Codex 白話版**整體品質高**：事故動機、五 Phase 主線、三層防線 rationale、誠實邊界（§C 三點中的 ①②③）、§N 殘餘風險多數、§RISK 硬性順序（誤報=0 才接 PreToolUse）均有覆蓋，文風對非技術讀者友善，術語表（§1）有助入門。

但有 **6 處實質遺漏或弱化**，其中 2 處會讓讀者誤解 v2.1 的 enforcement 範圍或實作前提；建議修正後再當對外白話定稿。

---

## 逐項對照

### 原文核心原則（開頭段）

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| 語意分類器=router，provenance=judge | ✅ §1、§5.3 | 清楚 |
| commit/交接 fail-closed；討論/引用/supersede fail-open | ⚠️ 隱含 | 未在開頭或獨立小節**成對**點出；非技術讀者不易抓住「哪裡硬擋、哪裡放行」 |
| careless-proof + tamper-evident，非防惡意偽造 | ✅ §1、§5.1 | 忠實 |

### §RISK 風險分級與硬性順序

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| high 因 (b) 跨流程共用路徑，非 (a)/(d) | ✅ §3 開頭 | 忠實 |
| 雙家族 adversarial + TODO + Composer 實作 + Codex review | ✅ §3 | 忠實 |
| v2 須重審 adversarial | ❌ 未提 | 原文 §RISK「v2 須重審」；白話只說流程要求，未標 v2 重審狀態 |
| **硬性順序：claim-object 測試誤報=0 → 才接 PreToolUse** | ✅ §3 Phase 3、§4、§6 | **忠實且重複強調**，符合不可違 |
| 未達標 → commit-hook + CI + receipt，不上 PreToolUse 全攔 | ✅ §3、§4、§6 | 忠實 |
| 執行者標註「Composer,不可違」 | ⚠️ 弱化 | 寫成「SPEC 硬性順序」即可，但實作派工讀者可能不知道這是**實作順序**而非僅政策建議 |

### §A 已確認現況

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| gate_check 只攔 Task/Bash/Write，不掃 HANDOFF/commit-msg | ✅ §3 | 忠實 |
| jq 缺失 fail-open | ❌ 未提 | 與 Phase 3「CI 不能 fail-open」對照可幫讀者理解為何要新 CI |
| 無自訂 git hook | ✅ §3 | 忠實 |
| CI workflow 存在 | ✅ §3 | 忠實 |
| reconcile_stamps 只 grep、不驗來源 | ✅ §3、§4 | 忠實 |
| mutation_probe 無 receipt | ✅ §3、§4 | 忠實 |

### §C 約束與誠實邊界

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| ① 只證有跑+範圍對+provenance，不證人類詮釋正確 | ✅ §5.2 | 忠實 |
| ② 同可寫主體 → careless-proof+tamper-evident | ✅ §1、§5.1 | 忠實 |
| ③ 分類器只 router，法官=receipt/task/stamp/ledger | ✅ §5.3 | 忠實 |
| bash 3.2 / venv/bin/python / 標準庫優先 | ❌ 未提 | §C 技術約束；白話可一句帶過「實作須相容 macOS 內建 bash、用專案 venv」 |
| 不弱化 gate_check；本閘並存新通道 | ❌ 未提 | 讀者可能以為取代既有 gate |
| 不做：regex 判詮釋正確；全量掃 docs/；v1 完整 render 索引 | ⚠️ 部分 | render 索引在 §5.7/§6；**掃描範圍僅 HANDOFF/handoffs/commit** 未明寫 |
| 僅衝突檢查、不做完整 render | ✅ §5.7、§6 | 忠實 |

### §G / §N

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| §G Golden N/A（治理基建、無數值 golden） | ⚠️ 隱含 | §6 列延後項，未明說「**不改交易/ML/回測數值，故無 golden baseline**」 |
| 完整 render 索引 N/A + 殘餘：過期 claim 靠衝突+人工 supersede | ✅ §5.7 | 忠實 |
| 防惡意密碼學偽造 N/A + repo 外密鑰殘餘 | ✅ §5.1、§6 | 忠實 |
| 殘餘① 未知同義詞 WARN→週期升 FAIL | ✅ §5.8、§6 | 忠實 |
| 殘餘② ledger 無 file lock / TOCTOU | ✅ §5.6、§6 | 忠實 |
| 殘餘③ run_receipts 完整索引與自動 render phase 2 | ✅ §6 | 忠實 |
| 「經四方 reconcile 接受為 v1 殘餘」 | ❌ 未提 | 治理語境；可一句帶過增加可信度 |

### Phase 1（Receipt）

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| runtime_class 由 argv 推導，requested_class 僅稽核 | ✅ §3 Phase 1 | 忠實 |
| checker 重算 hash 比對審計事件 | ✅ §3 Phase 1 | 忠實 |
| **W12：gitignore `*.log` 衝突，receipt/audit 須可 track** | ❌ 未提 | **實質遺漏**；§5.5 只講 untracked backing，未講「被 ignore 規則擋住也無法進 git」 |
| pytest 解析失敗 → 需 node 範圍的 claim fail-closed | ❌ 未提 | 邊界行為；可白話一句 |

### Phase 2（Claim checker）

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| claim-object 五維結構 | ✅ §3 Phase 2 | 忠實 |
| 強/弱極性詞 + 語境觸發 | ⚠️ 簡化 | 列了關鍵字，未區分「弱詞僅在 operational/commit/HANDOFF 語境才觸發」 |
| V7 排除：`42 passed` 反引號、passed through、通過層 6.5 | ⚠️ 泛化 | §5.3 只說「事故檢討、引用」；**未給具體排除例**，非技術讀者難理解「誤報=0」怎麼測 |
| W4 P0：operational 測試自述無 VERIFY → fail-closed | ⚠️ 合併 | §2 有列情境，未點名 W4/本事故核心規則名 |
| claim_fingerprint 公式（#6 + pending 一致） | ❌ 未提 | 可白話：「同一宣稱會算固定指紋，用來抓紅綠衝突」 |
| VERIFY-EXEMPT 六類 + 零豁免區 | ✅ §5.4 | 忠實 |
| 未知近似詞 → WARN | ✅ §5.8 | 忠實 |
| 同段多 claim / runtime 防冒充 | ✅ §2、§3 | 忠實 |
| readonly_signoff 限制 | ✅ §3 Phase 2 | 忠實 |

### Phase 3（三層 enforcement）

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| PreToolUse 攔 Edit\|Write → HANDOFF/handoffs | ⚠️ 簡化 | 寫「改交接文件」即可，未限定 Edit/Write（避免讀者以為所有工具都攔） |
| operational block 機械規則（標題清單） | ⚠️ 簡化 | 「正式結果區塊」未列 `## 正在做|待辦|已完成|STATUS|RESULT` |
| 只看本次 diff 新增/修改 | ✅ §3 Phase 3 | 忠實 |
| git hook 範圍 + commit-msg 含 docs: | ✅ §3 | 忠實 |
| CI fail-closed | ✅ §3 | 忠實 |
| health check 入 preflight/postflight | ⚠️ 簡化 | 有 health check，未提 agent pre/postflight 掛鉤 |

### Phase 4–5

| 原文要點 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| mutation_probe 行為不變 | ✅ §4 | 忠實 |
| W2/W3 provenance | ✅ §4 | 忠實 |
| verify_audit_chain 輔助、非機器 fail-closed | ✅ §4 | 忠實 |
| RESULT 結構化欄位 | ✅ §5 | 忠實 |
| #6 衝突檢查 | ✅ §5 | 忠實 |
| **W1 / P5-3：§A「已確認」須 FACT-RECEIPT** | ❌ **未提** | **實質遺漏**；防 SPEC 自己寫假「已確認」的 P1 級規則 |

### §V 驗證策略（白話不必逐條 V1–V19）

| 原文主軸 | Codex 覆蓋 | 備註 |
|----------|-----------|------|
| 誤報=0 是 PreToolUse 前置 | ✅ 多處 | 忠實 |
| 假擋/真放/冒充擋/誤報不擋 | ✅ §2、§5 | 忠實 |
| V17 事故 byte fixture（babu8o07p 原文必擋） | ⚠️ 泛化 | §2 描述事故，未說「會用當初 HANDOFF/commit 原文當回歸測試」 |
| 三層可分别停用 / 回退獨立 script | ❌ 未提 | 運維與 rollback；可 §6 加一句 |

---

## 白話友善度

**優點**

- 開頭術語對照表降低門檻。
- 用 P0-FF-3 事故敘事串起「為什麼要做」，比 SPEC 更易讀。
- §5「已知會失效的地方」結構清楚，對應 §C/§N 的誠實邊界，非技術讀者能懂「能保證什麼、不能保證什麼」。
- 三層防線 rationale（§4）解釋 trade-off，不只有功能列表。

**可改進**

- 缺少「兩種模式」一圖或兩句話：**硬擋區**（HANDOFF 操作結果、commit、RESULT）vs **放行區**（討論、引用、supersede）。
- 部分仍偏長（§3 Phase 2）；可拆「機器怎麼看一句話」+「人要寫 VERIFY: 才過」。
- 未連到 §V 的「誤報=0 怎麼驗」：建議加一句「會用本專案既有文件原文當測試，確保討論裡的『已驗』不會被誤擋」。

---

## 具體修正建議清單

### P0 — 建議必補（失真或漏關鍵 enforcement）

1. **補 W1 / FACT-RECEIPT（P5-3）**  
   在 Phase 5 或 §5 新增一小段：SPEC 裡寫「已確認」且涉及資料結構、命令輸出的事實，必須附 `FACT-RECEIPT:` 收據；純設計假設不能寫「已確認」。白話：「規格文件也不能空口說已實測。」

2. **補 W12 gitignore 可追蹤性（P1-3）**  
   在 §5.5 或 Phase 1 補：收據與審計 log 必須能進 git（需排除 `*.log` 誤傷），否則 CI/他人看不到證據。與「untracked backing 不過」並列為兩種「證據不可見」情形。

3. **開頭或 §2 後增「硬擋 vs 放行」對照**  
   一句話：交接/commit/RESULT 的新驗收宣稱 **fail-closed**；討論、引用、標 SUPERSEDED **fail-open**。對應原文核心原則第二條。

### P1 — 建議補強（風險/trade-off 完整性）

4. **§6 或 §3 開頭明寫 §G N/A**  
   「本 epic 不動交易數值、模型、回測，沒有數值 golden；驗收靠行為測試（假擋、真放、誤報=0）。」

5. **§5.3 或 Phase 2 加 V7 排除白話例**  
   例如：pytest 輸出 `` `42 passed` ``、英文片語 passed through、架構用語「通過層 6.5」不當成驗收宣稱。

6. **Phase 2 一句話解釋 claim_fingerprint**  
   「同一宣稱會算固定指紋，用來發現『後來變紅但舊文件還寫綠』的衝突。」

7. **§3 現況段補 jq fail-open**  
   「現有 gate 在缺少 jq 時會放行；新 CI 設計為缺工具就 FAIL。」

8. **§C 並存約束一句**  
   「不取代、不弱化既有 `gate_check.sh`；驗收防偽閘是並行新通道。」

### P2 — 可選 polish

9. PreToolUse 限定 **Edit/Write** 改 HANDOFF/handoffs；operational 區塊標題列舉（正在做/待辦/已完成/STATUS/RESULT）。  
10. §RISK 補「v2 adversarial 須重審」或註明「已完成 gate-ready」。  
11. §6 加 rollback：三層可分别關閉；新 script 可 revert 不動核心引擎。  
12. §6 或 §5 末句：「上述殘餘風險經四方 reconcile 接受為 v1 取捨。」  
13. 硬性順序標註對象：「實作時須先完成誤報=0 測試套件，再接 PreToolUse（Composer 派工不可跳步）。」

---

## 結論

Codex 版在**事故動機、五 Phase、三層 rationale、§C 三點誠實邊界、§N 三項殘餘、§RISK PreToolUse 硬性順序**上整體忠實，白話品質適合非技術讀者。主要缺口是 **W1 FACT-RECEIPT** 與 **W12 gitignore 可追蹤** 兩條會改變「什麼算有證據」的規則，以及 **fail-closed/fail-open 成對原則**未在顯眼處點名。

---

**VERDICT: NEEDS-FIX**

需修正項目（對應上文編號）：

- **必補（P0）**：#1 W1/FACT-RECEIPT、#2 W12 gitignore 可追蹤、#3 fail-closed vs fail-open 對照  
- **建議補強（P1，至少 #4–#8 中任 3 項）**：優先 #4 §G N/A、#5 V7 排除例、#7 jq fail-open 對照  

完成 P0 三項後可升級為 **ACCURATE**；P1 補強後可作對外定稿。

---

```
ASSUMPTIONS_VERIFIED: 已全文對讀 VERIFY_GATE_SPEC.md(v2.1) 與 VERIFY_GATE_SPEC_PLAIN_CODEX.md
TESTS_RUN: none（文件互審）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅新增 handoffs/20260701-PLAIN-CROSSREVIEW-COMPOSER-ON-CODEX.md）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**STATUS: DONE**
