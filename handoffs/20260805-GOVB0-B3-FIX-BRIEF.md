
# B3 修補 — 關閉 3 條 fail-open ＋ 2 條測試品質缺口

brief-kind: impl

**依據**：`handoffs/reconcile/20260805-govb0-b3-review/synth.md`（雙家族 review 收斂，三家戳記）
**受影響檔**：`scripts/_gate_lex.sh`／`scripts/gate_check.sh`／
`tests/governance/test_gate_lexical_contract.py`／`tests/governance/test_gate_deny_fields.py`／
`scripts/extract_phase2_expected_flips.py`／語料 `tests/governance/fixtures/gate_decision_corpus.txt`

## §0 前提宣告

**已查證**（主委實跑，`VERIFY:20260805T124806Z-b3-failopen-independent-repro`）：

- fact-verified: 對照 `tests/governance/fixtures/gate_check_pre_phase2.sh.snapshot`，
  `FOO="bar" codex exec x` 舊 rc=2 → 新 rc=0；8KiB 後綴 payload 舊 rc=2 → 新 rc=0。
- fact-verified: `echo "$(codex exec x)"` 舊 rc=0、新 rc=0（**非 B3 回歸**，但仍為真漏洞）。
  composer 獨立補跑反引號形式，舊版同樣 rc=0。
- fact-verified: `pytest tests/governance -q` → 751 passed rc=0（主委親跑，264s）。

**假設**（請攻）：

- assumed: C1 取消 8KiB 上限後，`_gate_lex_preprocess` 的 awk 實作**不會**在 MB 級輸入上退化。
  `_gate_lex.sh:291-292` 註解宣稱「awk 字串拼接 O(n²) 會卡死（4MB audit 邊界測）」，
  **主委未獨立複現該效能宣稱**，你必須實測後再決定修法。

---

## C1 — 8KiB 截斷造成尾端真派工放行【BLOCKING】

**現況**：`_gate_lex.sh:293,301-303` 以 `_max_lex=8192` 截斷後才送 `_gate_lex_preprocess`，
超長指令的尾端不進入判定 ⇒ 前 8KiB 填無害內容、尾端放 `; codex exec …` 即可繞過 PreToolUse。

**要求**：

1. **禁止靜默放行**。無論採何修法，超過上限的輸入**不得**以「只掃前綴」結案。
2. 修法自選，但須同時滿足下列三條驗收（互為約束，不得只顧其一）：

| # | 待驗項目 | 期望值 |
|---|---|---|
| C1-a | 8200 byte 前綴 + `; codex exec hi` | rc=**2**（BLOCK） |
| C1-b | `pytest tests/governance/test_debt_gate.py::test_gate_check_latency_under_100ms` | rc=**0**（門檻 100ms 不得放寬） |
| C1-c | 4MB 級輸入 | **有界時間內回覆且不 fail-open**；請貼實測秒數 |

3. **若選擇保留長度上限**：超限必須 `return 0`（BLOCK，fail-closed），
   並在 audit 記錄可辨識的 reason，**不得**與一般命中混淆。
4. 🔴 **禁止**以放寬 C1-b 門檻換取 C1-a（使用者定死：禁統計手法充當達標）。

---

## C2 — 引號 env 賦值前綴造成放行【BLOCKING】

**現況**：`gate_check.sh:167-169` 的剝除字元類 `[A-Za-z0-9_./:@%+=,-]+` 不含引號，
故 `FOO="bar" codex exec x` 不被剝除；其後 executor 比對只認「命令位置」，
`codex` 前方為 `FOO="bar" ` 而非分隔符 ⇒ 判為非命令位置 ⇒ ALLOW。

**要求**：剝除邏輯改為 quote-aware assignment-word 處理，接受**引號括起的值**。

🔴 **不得回歸 E-3**：該處註解（`gate_check.sh:166`）明載此字元類是為避免
`out=$(codex exec x)` 被誤剝成 `exec x)`。修法必須同時保住：

| # | payload | 期望 rc |
|---|---|---|
| C2-a | `FOO="bar" codex exec x` | **2** |
| C2-b | `FOO='bar baz' codex exec x` | **2** |
| C2-c | `out=$(codex exec x)`（E-3 回歸樁） | **2** |
| C2-d | `FOO="bar" echo hi` | **0**（不得誤擋） |

---

## C3 — 雙引號內 `$()`／反引號命令替換放行【既有缺陷，本批一併修】

**歸屬**：**非 B3 回歸**（舊版同樣放行，三家已獨立實跑確認）。
**仍本批修的理由**：正落在 Task 2.1「引號感知」主題內——
雙引號內的 `$()`／反引號**會執行**，不是字面字串，B3 的剝引號規則依其自身設計意圖即應處理。

**現況**：`_gate_lex.sh:143-166,196-203,305-311` 對整個 quote span 將空白改為 US，
使 span 內的 `codex exec x` 無法命中命令位置比對。

**要求**：雙引號狀態下遇 `$(` 或反引號，其內容須視為**命令上下文**並遞迴判定
（沿用契約 8 的 `_GATE_LEX_MAX_DEPTH` 上限與逾限 fail-closed）。

| # | payload | 期望 rc |
|---|---|---|
| C3-a | `echo "$(codex exec x)"` | **2** |
| C3-b | 反引號形式同義 payload | **2** |
| C3-c | `echo "codex exec x"`（純字面，契約 1） | **0**（不得誤擋） |
| C3-d | `git commit -m "x; codex closure review"` | **0**（不得誤擋） |

---

## C4 — 排除機制 reverse-1 mutation 為恆真斷言【MAJOR】

**現況**：`test_gate_deny_fields.py:530-557` 的
`test_01_invariance_exclude_nonflip_mutation` 只對非 flip victim 再呼叫
`_flip_matches_command` 並斷言 `hit is None`——**未改動判定主體、未執行 altered `excluded` trace**，
故該測試僅證明 helper 行為，不證明排除機制本身。

**要求**：改為真實注入 victim（使一個**不該被排除**的條目進入排除路徑），
要求該 mutation 下測試**轉紅**。

**驗收**：貼出 mutation 前後兩次 rc——未注入時 rc=0、注入後 rc≠0。**兩者缺一不算通過。**

---

## C5 — 抽取器未涵蓋 TODO 絕對態敘述【MAJOR】

**現況**：`extract_phase2_expected_flips.py:128-131` 僅辨識「由 X 轉 Y／維持 Z」方向標記，
無標記即 `continue`。TODO 中 `TEST-2.1-RECURSE`（「六條皆 BLOCK」）、
`TEST-2.2-REGRESS`（「兩條須 BLOCK」）等絕對態寫法**不會**進排除清單。

**現況不紅**：語料 A 目前無這些條目。**但**削弱「清單窮舉 TODO 轉向」前提，
B4+ 擴充語料 A 時會再次撞上同一設計矛盾。

**要求**（二擇一，選定後在 TODO 註記所選）：
(a) 抽取器增第三類「絕對態＋命令列舉」；或
(b) 要求 TODO 一律用「由 X 轉 Y」格式，並加機檢強制。

**驗收**：加測試——RECURSE 六條若模擬進語料 A，必須出現在 flips 或明確標 `maintain`；
該測試在修法 revert 後須轉紅。

---

## 每條共同要求

1. **每個修法都要有語料 B 條目（TP／TN）＋ mutation**：把修法 revert 後該測試須**轉紅**。
   只有「加了測試且通過」不算——**必須證明它抓得到**。
2. **禁改檢查器讓測試變綠**、**禁恆真斷言**、**禁弱化既有斷言**。
3. **禁改語料 A**（`gate_invariance_corpus.txt`）任何一行。
4. 全套 `pytest tests/governance -q` 須維持 **≥751 passed**、rc=0。**丟背景並導檔再取尾。**
5. 跑完測試須 `bash scripts/restore_golden_inventory.sh`。

## 🔴 不受理範圍（標 `OUT-OF-SCOPE`，不得擴散）

1. **C6**（多 heredoc 第二 body 誤擋，MINOR）——已裁定順延 B4，**本批不做**。
2. B4 以後的 Task（`2.2`／`2.3`／`2.4`／`2.5`／`3.*`）。
3. 重開 SPEC／TODO 設計裁決。**例外**：C5 若選修法 (b) 須改 TODO 格式規定。
4. `audit.log` 大小／封存／latency 主題（封存已於 `fd6dc77` 撤回）。
5. 措辭／命名／可讀性重構。

## 硬性要求

1. **rc 一律直接取，禁經 pipe**（`cmd | tail; echo rc=$?` 讀到的是 `tail` 的 rc）。
2. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**。
   誤動檔案**請回報，不要自行還原**——本 epic 前一位委員違反此條已具名記錄。
3. 不要 commit、不要 push；**禁碰 `data_cache/`**。
4. **兩輪解不了任何一條 ⇒ 停手回報**，不得硬幹。
5. **禁 `python3 -c` 做檔案字串取代**；改檔用編輯工具或寫成腳本檔執行。

## 產出

逐條（C1–C5）：改了什麼（貼 diff）、新增哪些語料／測試、
**mutation 前後兩次 rc**、C1 的三項驗收實測值（含 4MB 秒數）、
全套 pytest 尾段與 rc。收尾清 /tmp workdir（保留 claude-501）。
