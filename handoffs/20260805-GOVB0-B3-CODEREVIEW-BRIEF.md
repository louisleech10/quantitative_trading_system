
# 第 0 批 B3 code review（雙家族）— Phase 2 首批

brief-kind: review

**受審 commit**：`18cfdd2`（B3 本體＋解阻塞）／`c2a351f`（audit 封存）
**依據**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）Phase 2 / Task 2.0 ＋ Task 2.1

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。

## 🔴 finding heading 格式

`scripts/completeness_check.sh:153` 逐字為 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`。
本輪合法範例：`CODEX-R12-P1-01`。
**唯一允許的 `##` 標題**：`## Verdict`／`## §0 前提宣告`／`## 逐項核對表`／`## 出場判準核算`
＋ canonical finding heading。零 findings 請明寫 `FINDINGS_COUNT: 0`。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: 語料 A 條數 **30**，未因 B3 減少（`grep -c '^{'`）。
- fact-verified: `pytest tests/governance/test_gate_deny_fields.py` → **24 passed** rc=0（主委親跑）。
- fact-verified: 排除機制 mutation `test_01_invariance_exclude_nonflip_mutation` → **1 passed** rc=0（主委親跑）。
- fact-verified: audit 封存後三項守恆——行數 34,479 = 763 + 33,716；round 數 199→199；`has_open` 0→0。
- fact-verified: `test_gate_check_latency_under_100ms` 封存後 **PASSED**（主委親跑）。

**假設**（請優先攻）：

- assumed: **`750 passed` 為實作者回報，主委未親跑全套**（僅親跑上述子集）。
- assumed: **排除清單的抽取邏輯真的窮舉了 TODO 的所有轉向敘述**。
  主委只驗了「抽取腳本存在且測試會比對」，**未逐條核對 TODO 中每個轉向都被抽到**。
- assumed: **契約 11 項在語料 B 各有 TP/TN**。主委未逐項核對。
- assumed: audit 封存**不影響任何既有機制**。主委只驗了 `debt_ledger` 三項與 latency，
  **未窮舉其他讀 audit.log 的消費者**。

---

## 🔴 本輪首要攻擊標的

### 1. 排除機制是否被濫用（**最高優先**）

B3 引入「預期翻轉清單」機制：INVARIANCE 比對時排除 TODO 明文標示會翻轉的條目。

**設計意圖**：主委原本把「TODO 要求要改」的條目放進「判定不得改變」的語料，是設計矛盾。
**風險**：這個機制若被濫用，等於「發現哪條紅就把哪條加進清單」。

**請查**：
| # | 問題 | 通過條件 |
|---|---|---|
| 1a | 清單是否真的**只**來自 TODO 的機械抽取？有無任何條目是手加的？ | 逐條比對 fixture 與 TODO 原文 |
| 1b | 抽取腳本是否**遺漏** TODO 中某些轉向敘述？（漏抽 ⇒ 該條仍在 A 中比對 ⇒ 會紅；但若漏抽又剛好沒紅，代表覆蓋不足） | 自行重跑抽取並與 TODO 全文對照 |
| 1c | 兩條反向斷言是否真的可證偽？ | 各自構造反例驗證 |

### 2. audit 封存的副作用（**新增，主委未窮舉**）

`c2a351f` 把 `audit.log` 由 34,479 行縮為 763 行，其餘移入 `.claude/gate/archive/`。

**請查**：**還有哪些程式讀 `audit.log`？** 逐一判定封存是否影響其正確性。
主委只驗了 `debt_ledger`（三項）與 latency 測試，**未窮舉其他消費者**
（例如 `verification_claim_check.py` 的 `_load_audit_events`、`gate.sh`、`verify_audit_chain.py` 等）。

🔴 **若發現任何消費者因封存而行為改變，屬 BLOCKING。**

### 3. Task 2.0／2.1 本體

| # | 查什麼 | 判定 | 依據 |
|---|---|---|---|
| 3a | 契約 11 項是否各有 TP＋TN 進語料 B（≥22 條） | | |
| 3b | 原型③ 26 條的新舊判定是否逐條相同（差異須具名） | | |
| 3c | 契約 1b 剝引號是否真的**跨行有狀態**（非行內替換、非正規化為單行） | | |
| 3d | heredoc ⑥⑦ 是否**互補不重疊**（無「⑥接受但⑦要拒絕」的區間） | | |
| 3e | `test_debt_gate.py`／`test_family_registry.py` 的改動是否為**必要的最小同步** | | |
| 3f | 測試品質：依範本 §1 第 9 類逐條舉證 | | |

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`）

1. 重開 SPEC／TODO 的設計裁決。**例外**：導致本實作有實質缺陷。
2. B4 以後的 Task（`2.2`／`2.3`／`2.4`／`2.5`／`3.*`）。
3. 線 C 完整版（持續輪替規則）——本次僅一次性封存，完整版排第 0.5 批。
4. 措辭／命名／可讀性。

## 出場判準

> **findings ≤5 且 BLOCKING = 0 ⇒ B3 驗收通過，可進 B4。**

## 硬性要求

1. **禁改碼、禁改測試、禁改 TODO／SPEC**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`／`git clean`；不要 commit、不要 push；**禁碰 `data_cache/`**。
4. 每條 finding 附**可執行修法**與**重現命令**。
5. 跑全套 `pytest tests/governance -q` 請**丟背景並導檔再取尾**。

## 產出

三大標的的逐項判定、findings（若有）、`## 出場判準核算`、
對 §0 四條假設的攻擊結果。收尾清 /tmp workdir（保留 claude-501）。
