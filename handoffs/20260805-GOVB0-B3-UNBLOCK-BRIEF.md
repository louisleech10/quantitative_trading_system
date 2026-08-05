
# B3 解阻塞 — 修主委的語料 A 設計矛盾

brief-kind: impl

**唯一權威來源**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）
**前置**：B3 實作已完成但標 **BLOCKED**，等待本輪解阻塞後方可標 DONE。

## 🔴 阻塞根因：**主委的設計自相矛盾，非實作者失誤**

| 事實 | 出處 |
|---|---|
| 語料 A 含 `pgrep -fl 'codex exec\|cursor-agent\|grok '` | `tests/governance/fixtures/gate_invariance_corpus.txt:58` |
| TODO **明文要求同一條由 BLOCK 轉 ALLOW** | `docs/GOVB0_FRICTION_TODO.md:331-332`（`TEST-2.1-FP`） |

⇒ 主委把「TODO 明文要求要改變」的條目，放進了「判定不得改變」的語料。
**實作者停下回報、未自行調整語料，處置完全正確**（brief 明文禁止「為了讓語料 A 變綠而修改語料 A」）。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: 上述兩個檔案／行號的內容如上表（主委逐行讀檔確認）。
- fact-verified: `test_gate_check_latency_under_100ms` 失敗**非 B3 回歸**——
  實作者實測 snapshot（pre-Phase2）在同環境亦 ~203ms，同樣 >100ms；根因為 `audit.log` 34k 行。

**假設**（你若發現不成立，**停下來回報**）：

- assumed: TODO 中「應翻轉」的條目**可由文件機械抽取**（各 `TEST-*` 的「由 X 轉 Y」敘述）。
  若某條翻轉只寫在散文而無機械可辨的樣式，**明說是哪一條**，不要手挑。

---

## 修法：**排除清單必須自 TODO 機械導出，禁手挑**

🔴 **這是本輪唯一的正確性關鍵。** 若排除清單用手挑，
就等於「發現哪條紅就把哪條移出去」——即主委原本禁止的行為，只是換個位置。

### 1. 建立「Phase 2 預期翻轉清單」

- 自 `docs/GOVB0_FRICTION_TODO.md` **機械抽取**所有明文標示轉向的條目
  （樣式如「**由 BLOCK 轉 ALLOW**」「**由 ALLOW 轉 BLOCK**」「維持 BLOCK」「維持 ALLOW」）。
- 產出資料檔（例 `tests/governance/fixtures/phase2_expected_flips.txt`）＋ 其 `.sha256` sidecar。
- **禁硬編於測試碼**；抽取邏輯須可重跑。

### 2. `TEST-0.1-INVARIANCE` 改為「排除預期翻轉後仍逐項相等」

- 比對前先自語料 A 排除「在預期翻轉清單內」的條目。
- 🔴 **加兩條反向斷言**：
  - **每個被排除的條目，必須能在預期翻轉清單中找到對應**（禁靜默排除）；
  - **預期翻轉清單中的每一條，必須在語料 B 有對應條目並確實翻轉**
    （否則「排除」等於白白刪掉覆蓋）。
- **mutation**：把某條**不在**預期清單的條目也排除 ⇒ 第一條反向斷言**必須轉紅**。

### 3. 語料 A 本身**不得刪除任何條目**

- `pgrep` 那條**留在語料 A**，只是在 INVARIANCE 比對時被「預期翻轉」規則排除。
- 理由：它仍是 Phase 0 記錄的真實案例，刪掉會失去出處與可追溯性。

### 4. 兩個既有失敗的處置

- `test_gate_check_latency_under_100ms`：**非本批回歸**（snapshot 同環境亦超標）。
  🔴 **不得為此放寬門檻**。請在產出中具名記錄：根因＝`audit.log` 體積，
  對應 **P1-6 線 C（第 0.5 批）**，本批不修。
- `test_no_unpinned_family_list_line`：你回報已修（釘 `_gate_lex.sh`），請貼修後實跑 rc。

---

## 🔴 硬性禁令

1. **禁碰 `data_cache/`**。
2. **禁 `git checkout`／`git restore`／`git clean`**；不要 commit、不要 push。
3. **禁刪除語料 A 任何條目**；**禁手挑排除清單**；**禁放寬 latency 門檻**。
4. **禁修改既有測試斷言**（`test_debt_gate.py`／`test_family_registry.py` 的既有斷言除外——
   你回報已為 `_gate_lex.sh` 做最小同步，請在產出中逐行說明改了什麼、為何是必要的最小改動）。
5. **不做 B4 以後的任何 Task**。
6. **bash 3.2 相容**；**`rc` 一律直接取，禁經 pipe**。
7. 中文路徑比對必須 `git -c core.quotepath=false`。

## 收尾必做

1. `pytest tests/governance -q`（**丟背景導檔再取尾**）——貼總數與 rc，
   並**逐條說明每個非綠項**（是否為本批造成）。
2. `bash scripts/restore_golden_inventory.sh` 後貼 `git status --short tests/golden/`（須為空）。
3. 每個 mutation **貼實跑 rc**。
4. 清 /tmp workdir（**保留 `/private/tmp/claude-501`**）。

## 產出

1. 預期翻轉清單的**抽取邏輯**與產出檔（含 `.sha256`）
2. `TEST-0.1-INVARIANCE` 改後的實跑結果 ＋ 兩條反向斷言的實跑
3. 排除清單的 mutation 實跑 rc
4. 語料 A 條數**未減少**的證明
5. 兩個既有失敗的逐條說明
6. `test_debt_gate.py`／`test_family_registry.py` 的改動逐行說明
7. `git diff --stat`、`pytest` 總數、`git status --short tests/golden/`

🔴 **若你認為排除機制仍有漏洞（例如某條翻轉無法機械辨識），明說**，不要自行決定手挑。
