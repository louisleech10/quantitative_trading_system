# VERIFY_GATE_SPEC v2 — BLOCK 閉合再驗證（Composer 2.5 adversarial 提出方）

**審查對象**：`docs/VERIFY_GATE_SPEC.md` v2  
**對照**：`handoffs/20260701-VERIFYGATE-SPEC-ADV-COMPOSER.md`（v1 BLOCK/必修）、`handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md`（四方定案 + 五條件）、`handoffs/20260701-VERIFYGATE-DELIB-COMPOSER.md` §五  
**方法**：逐條對 v1 每個 `[BLOCK]` 與 APPROVED-WITH-CONDITIONS 五條件做「可實作、可測、不腦補」閉合檢查；不認同式放行。

---

## 總評

v2 相對 v1 是實質大改：claim-object 取代詞表+同段、B-FORGE 審計事件、三層 enforcement（含 PreToolUse + CI）、runtime_class 推導、#6 衝突-only、§V 擴到 V16。**多數 v1 BLOCK 在設計層已閉合**。

但仍有 **4 項 SPEC 級定義缺口**（實作者必須腦補 → 高概率實作分裂或假綠）與 **3 項 reconcile 追溯缺口**（五條件字面未完全落地）。這些不足以「直接派實作」；應先補 SPEC 再派。

**VERDICT: CHANGES-REQUESTED** — 方向可執行，殘留見末節「必修再派工前」。

---

## A. 五條件（APPROVED-WITH-CONDITIONS）閉合表

| # | 條件 | v2 錨點 | 閉合？ | 殘留／攻擊面 |
|---|------|---------|--------|----------------|
| 1 | claim-object 測試誤報=0 **先於** PreToolUse | §RISK L11、§V L76、§R L98 | **部分** | 順序與降級路徑寫清；但 P3-1「operational result 區塊」**無偵測算法** → PreToolUse 範圍實作者自選 → 撞牆或漏攔風險仍在 |
| 2 | EXEMPT 窄化 + **HANDOFF/commit/RESULT 零豁免** | V8、reconcile §定案項 5 | **部分** | 禁區寫清；**VERIFY-EXEMPT 類別白名單整段缺失**（reconcile 聯集 `typo\|doc-example\|migration-note\|template-drift\|tooling-blocked\|spec-ambiguity` 未進 P2-1）→ 實作不知 handoffs 內合法 EXEMPT 邊界 |
| 3 | #6 v1 **僅衝突檢查**，全文索引 phase 2 | P5-2、§N L102 | **是** | 與 DELIB 一致；殘餘風險（過期綠 claim 未衝突）已在 §N 誠實登記 |
| 4 | 結構化 `SIGNOFF:<family>:<task-id>:<scope-hash>`，禁裸「已驗」 | P2-1 L51 | **是** | 格式與「不得支撐 runtime/慢測」明確；`scope-hash` 算法未寫（實作需補，但低於 BLOCK） |
| 5 | **W2/W3/W4 P0** 與 B-FORGE 同批 | P1-2 B-FORGE、P4-2 W3、P4-3 W2 | **部分** | B-FORGE/W2/W3 有；**W4 未在 SPEC Phase 出現**（reconcile P0「pass-fail 自述無 receipt」僅被 P2 隱含，無可追溯交付項） |

---

## B. v1 各 `[BLOCK]` 逐條閉合

### ① Claim checker 繞過

| v1 BLOCK/MAJOR | v2 對應 | 閉合？ | 說明 |
|----------------|---------|--------|------|
| 詞表不全／同義詞 | claim-object + normalize + 強/弱極性 + 未知→WARN | **部分** | 架構正確（router 非法官）；但強極性仍 regex 閉集。`也正確紅`、`STATUS: DONE`（裸）**不在** P2-1 強極性表（V11 測 DONE 僅 pending 語境）。未知同義詞 **WARN 不 FAIL** → reconcile 接受的 P2 殘餘，**可派工但須寫進 §N**；`7e71fd1`/`9f9839d`/`METAFIX` L6 **無 byte 級 §V fixture**（v1 必修 #7 未閉） |
| 同段未定義 | 空行分段 + 列表/表格/commit subject 獨立 + 同段多 claim(V10) | **是** | v1 拆段攻擊（文末 VERIFY）應 FAIL |
| VERIFY-EXEMPT 濫用 | V8 + discussion 僅 fenced/quote | **部分** | 濫用場景有測；類別白名單缺失（見條件 2） |
| VERIFY 與 CLAIM 語義脫鉤 | operational 須 VERIFY；scope 交集；class 防冒充(V4) | **是** | 快測撐慢測核心洞已機械化 |
| 偽造 receipt（無審計） | P1-2 + V6 | **是** | B-FORGE 閉合 v1 BLOCK；§C 誠實邊界（同主體 tamper-evident）合理 |
| commit 自製 receipt 進歷史 | — | **殘餘** | v1 要求 `run_receipts` gitignore + staged 拒偽；v2 **未要求 gitignore**（W12「staged+hash 對 claim」亦未寫）。有審計的空殼 run 仍可進 git → 靠 class 推導擋，非歷史防污染 |

### ② runtime_class

| v1 BLOCK/MAJOR | v2 | 閉合？ |
|----------------|-----|--------|
| 完全自宣告 | argv 推導 authoritative + V9 | **是** |
| 耗時僅 WARN 冒充 kline | helper_smoke/static 不得支撐 runtime/mutation/kline claim | **是**（機制改為 FAIL 非 WARN） |
| pytest 解析失敗跳過範圍 | 需 node 範圍 claim → fail-closed | **是** |

### ③ Pending ledger

| v1 BLOCK/MAJOR | v2 | 閉合？ |
|----------------|-----|--------|
| 偵測空殼 | schema + 僅 run_with_receipt/RESULT parser 產事件 + P5-1 枚舉 | **部分** | schema 有；**`claim_fingerprint` 算法未定義**（P2-2、P5-2 皆依賴）→ close/衝突檢查無法一致實作 |
| 完全繞過 ledger | operational 須 VERIFY+審計（與 ledger 正交） | **是** | 惡意省略 pending 仍不能無 receipt 宣稱 operational |
| TOCTOU / 無鎖 | — | **殘餘** | v2 未提；reconcile 未強制 → MAJOR 殘留，非派工 blocker |
| task_id 綁定未定 | pending 含 task_id | **部分** | 欄位有；**task_id 抽取規則**（檔名？手寫？）未寫 → 錯 slug 仍可不匹配 |

### ④ Hook／旁路（事故核心）

| v1 BLOCK | v2 | 閉合？ |
|----------|-----|--------|
| opt-in hook 靜默缺席 | P3-4 health + preflight/CI；P3-3 CI fail-closed | **是** |
| `--no-verify` | CI range checker + V13 | **是** |
| 不 commit 污染 HANDOFF | P3-1 PreToolUse | **部分** | 路徑對；**operational block 算法缺失**（條件 1） |
| #6 根 HANDOFF 索引 | P5-2 衝突-only | **是**（條件 3） |
| #7 RESULT 硬欄位 | P5-1 + template_check | **是** |

### ⑤ §V 測試

| v1 BLOCK | v2 | 閉合？ |
|----------|-----|--------|
| mutation 覆蓋過窄 | V1–V16 | **大部分** | 缺：**事故 commit byte regression**、pending TOCTOU mutation、**W12 staged-hash**、hook 未裝備僅 V14 health（未測「未 install 仍 merge 被 CI 擋」端到端） |
| V7 誤報=0 | V7 測 SPEC/DELIB fenced | **是**（撞牆） | 與 v1「7e71fd1/9f9839d」不同 fixture，但 V7 目的（不擋討論引用）已覆蓋 |

---

## C. reconcile 定案項（B-*）抽查

| 定案項 | v2 | 閉合？ |
|--------|-----|--------|
| B-FORGE 審計事件 | P1-2 | **是** |
| B-HOOK 三層 | P3-1/2/3 | **是** |
| B-CLASS 推導 | P1 + P2-1 | **是** |
| B-EXEMPT 窄豁免 | 討論結構 + V8 禁區 | **部分**（類別表缺失） |
| B-LEDGER 狀態機 | P2-2 | **部分**（fingerprint 未定） |
| B-SCOPE #7 | P5-1 | **是** |
| B-SCOPE #6 衝突-only | P5-2 | **是** |
| W10 jq fail-open | P3-3/P3-4 | **是**（verify 側）；`gate_check.sh` 仍 fail-open 屬並存舊閘，§C 已聲明不弱化 |
| W12 staged+hash | — | **否** |
| W13 commit subject/body | P3-2 commit-msg + V13 | **是** |

---

## D. 仍可攻破的路徑（誠實列殘，非否定整體）

1. **同義詞 WARN 通道**：operational 語意但未命中強/弱極性 → 不進 operational → 無 VERIFY 要求（直到 WARN 升級）。reconcile 已接受為 P2 殘餘，但 **§N 應明示**，避免實作誤以為「WARN=安全」。
2. **PreToolUse 增量區塊未定義**：可能實作成「全檔掃」撞牆，或「只掃 subject 行」漏攔——違反條件 1 精神。
3. **`claim_fingerprint` 自由解讀**：#6 衝突與 pending close 一致性無法驗收。
4. **惡意模型內 forgery**：同一可寫主體跑 `run_with_receipt.py` + 空殼 cmd → 有審計的「真」receipt；v2 §C 誠實邊界已涵蓋，非 v1 目標（疏忽模型）。

---

## E. 必修（再派實作前 SPEC 補丁）

1. **P3-1**：定義 `operational result block` 機械規則（建議：git diff hunks 內 `## 正在做|## 待辦|STATUS:` 區段 + 非 fenced 新增行；或 diff 全文過 checker 但 V7 保誤報=0）。  
2. **P2-2 / P5-2**：定義 `claim_fingerprint = hash(normalize(scope + runtime_expectation + task_id + source_line_text))` 或等價可測公式。  
3. **P2-1 或 §N**：補 VERIFY-EXEMPT 窄類別表（reconcile 聯集）**或** 明示 v2 廢除 VERIFY-EXEMPT、僅留 discussion context。  
4. **Phase 4**：增 **P4-0/W4** 可追溯項——「operational pass-fail 自述須 VERIFY receipt；無 receipt 的 PASS/FAIL/已驗敘述 fail-closed」（與 P2 重述即可，但須命名 P0）。  
5. **§V**：增 **V17**（或擴 V7）：`7e71fd1` HANDOFF 片段、`9f9839d` commit body、`METAFIX` L6 `也正確紅` 原文 fixture。  
6. **（建議 MAJOR）**：補 W12「claim 引用 receipt 須與 staged 檔 hash 一致」或寫入 §N 為 phase 2。

---

## F. 可接受殘餘（不阻派工，但須進 §N/TODO）

- 未知同義詞 WARN→週期升 FAIL（reconcile P2）  
- ledger TOCTOU 無 file lock  
- #6 完整 render 索引 phase 2  
- `run_receipts/` 未 gitignore（B-FORGE 已降風險）  
- `scope-hash` / `task_id` 抽取細節可放 TODO 若附最小範例  

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: v2 SPEC 已讀全文；v1 COMPOSER adversarial 9 BLOCK + 8 必修已逐條對照；DELIB reconcile 五條件與 B-* 已對照；run_receipts 仍不在 .gitignore（grep 確認）
TESTS_RUN: 讀碼靜態（VERIFY_GATE_SPEC.md v2、DELIB-RECONCILE、SPEC-ADV-COMPOSER v1）；未跑 pytest（本任務為 SPEC 閉合審查）
FAILURES_SEEN: none
SCOPE_CHANGES: none（僅審查產物）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**VERDICT: CHANGES-REQUESTED** — v2 已閉合多數 v1 BLOCK 與五條件中的 #3/#4；**#1/#2/#5 仍部分閉合**，且 **`claim_fingerprint`、operational block、W4 追溯、事故 byte fixture、W12** 須先補 SPEC 再派實作。補完後可重跑本閉合審查預期 **APPROVED 可派實作**。

HANDOFF_NOT_UPDATED: 執行合約 — 審查任務不覆寫根 HANDOFF.md；未 APPROVED 故不 append DELIB RECONCILE-STAMP。
