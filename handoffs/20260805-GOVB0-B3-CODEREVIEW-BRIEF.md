
# 第 0 批 B3 code review（雙家族）— Phase 2 首批

brief-kind: review

**受審 commit**：`18cfdd2`（B3 本體＋解阻塞）
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
- fact-verified: **主委親跑全套** `pytest tests/governance -q` → **751 passed** rc=0（264s）。
  ⚠️ 比實作者回報的 `750` 多 **1**，差異來源主委未查——**請一併確認此差值是什麼**。
- fact-verified: `.claude/gate/audit.log` 現為 **34,504 行完整未截斷**；
  `test_gate_check_latency_under_100ms` 在此完整檔上主委獨立連跑 3 次全 PASS。

🔴 **本輪範圍變更（務必看）**：brief 前一版曾把 `c2a351f`（audit 封存）列為受審對象並設為攻擊標的 2。
**該封存已於 `fd6dc77` 全數撤回**——`audit.log` 還原完整、封存檔與 `audit_archive_legacy.sh` 皆刪除。
撤回原因：latency 紅只出現一次（287ms），主委未重跑就斷定根因是檔案過大，**整套診斷不成立**。
⇒ **audit 封存不在本輪範圍**，勿花時間稽核；`OUT-OF-SCOPE` 第 5 條。

**假設**（請優先攻）：

- assumed: **排除清單的抽取邏輯真的窮舉了 TODO 的所有轉向敘述**。
  主委只驗了「抽取腳本存在且測試會比對」，**未逐條核對 TODO 中每個轉向都被抽到**。
- assumed: **契約 11 項在語料 B 各有 TP/TN**。主委未逐項核對。

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

### 2. 精準化是否換來 fail-open（**取代原標的 2**）

B3 是 8 批中**第一批真的改變判定結果**的（B0–B2 全為 invariance）。
改動方向是讓 `gate_check.sh` **少誤判**（票 B-15：唯讀查詢被當成派工，本 session 咬 13 次）。

🔴 **這個方向天生的風險是反向的**：把誤報壓下去的同時，
**是否讓某些真正該擋的派工變成放行**？fail-open 比 fail-closed 嚴重得多。

**請查**：
| # | 問題 | 通過條件 |
|---|---|---|
| 2a | 針對契約 11 項各自**構造一個真派工**（該擋），確認新判定仍擋得住 | 逐項附實跑命令與 rc |
| 2b | 引號感知（2.1）剝掉引號後，**引號內的真派工指令**是否因此逃脫？ | 構造反例；能逃脫＝BLOCKING |
| 2c | 詞法契約（2.0）的 tokenize 對**畸形輸入**（未閉合引號、跳脫、巢狀）如何處置？ | 須 fail-closed；靜默放行＝BLOCKING |

**判定基準**：任何「舊版擋、新版放行」且該指令確為真派工者，一律 **BLOCKING**，不接受「機率很低」。

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
3. 線 C 完整版（`audit.log` 持續輪替規則）——排第 0.5 批。
4. 措辭／命名／可讀性。
5. **`audit.log` 的大小、封存、latency**——封存已於 `fd6dc77` 全數撤回，
   完整檔上 latency 實測通過。本輪勿再稽核此主題。

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
