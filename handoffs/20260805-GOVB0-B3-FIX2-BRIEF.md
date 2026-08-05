
# B3 修補 R2（**確認輪，禁新增 scope**）— 關閉 D-1～D-4

brief-kind: impl

**依據**：`handoffs/reconcile/20260805-govb0-b3-fixreview/synth.md`（三家戳記
`sha256:eea35be5…`；composer 逐條同意主委裁定 A1–A3，grok 確認 D-2 修法可行）

🔴 **本輪為確認輪**：只做 D-1～D-4，**不得擴散**。
R1 修補曾引入一條新缺口（D-2），若 R2 再現同型態即觸發 epic 斷路器、停手重審設計。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: `pytest tests/governance -q` → **759 passed** rc=0（主委親跑，255s）。
- fact-verified: D-1 探針新舊 rc 同（`codex exec x; echo scripts/gate.sh` 皆 rc=0）⇒ **非 B3 引入**。
- fact-verified: D-2 探針 `echo`+8200 字元 舊 rc=0、新 rc=**2** ⇒ **本批引入的誤擋**。

**假設**（請攻）：

- assumed: D-2 改 O(n) 流式掃描後，latency 仍可 <100ms 且 4MB 有界。
  **grok 於戳記輪宣稱可行但未實作**；本輪須以實測證明，做不到就停手回報。

---

## D-1 — `gate_check.sh` 自我排除為子字串比對【BLOCKING】

**現況**：`gate_check.sh:211-216` 判定為 dispatch 後執行
`grep -Eq 'scripts/gate(_check)?\.sh'` 於**整條 cmd**，命中即 `exit 0`。
⇒ 任意位置嵌入該字串即整條放行。

| payload | 現行 rc | 期望 rc |
|---|---|---|
| `codex exec x; echo scripts/gate.sh` | 0 | **2** |
| `codex exec x  # scripts/gate.sh` | 0 | **2** |
| 8200B + `; scripts/gate.sh; codex exec hi` | 0 | **2** |
| `bash scripts/gate.sh dispatch --task-id X`（正當自呼叫） | 0 | **0**（不得誤擋） |
| `bash scripts/gate_check.sh`（正當勘查） | 0 | **0**（不得誤擋） |

**要求**：收斂為「僅當 gate 腳本位於**命令位置**、且該條命令本身即 gate invocation 時才排除」。
🔴 **對照既有 TN 語料**，確認不誤擋合法自呼叫（composer 已具名此風險）。

---

## D-2 — `>8192 一律 fail-closed` 誤擋無害超長指令【BLOCKING】

**現況**：`_gate_lex.sh:355-366` 超過 8192 字元即 `_GATE_LEX_OVERSIZE=1; return 0`（BLOCK）。

**要求**：採 **O(n) 流式／分塊掃描全 cmd**，移除字元長硬頂。

🔴 **禁止**以子字串型逃生口規避——會與 D-1 疊加成新繞道（三家一致具名此風險）。

| # | 待驗項目 | 期望值 |
|---|---|---|
| D-2a | `echo` + 8200 字元無害字串 | rc=**0**（不得誤擋） |
| D-2b | 8200B 前綴 + `; codex exec hi` | rc=**2**（fail-open 不得復活） |
| D-2c | `test_gate_check_latency_under_100ms` | rc=**0**（門檻 100ms **不得放寬**） |
| D-2d | 4MB 級輸入 | 有界時間內回覆且**不 fail-open**；貼實測秒數 |
| D-2e | 8200B 前綴 + `; scripts/gate.sh; codex exec hi` | rc=**2**（與 D-1 疊加後仍須擋） |

⚠️ **latency 測試有冷啟抖動**（codex 實測首次 108.8ms、次次 72.8ms）。
判定請**連跑 3 次取全部**，勿以單次結果下結論；**不得為此放寬門檻**。

---

## D-3 — C4 測試非真 mutation【MAJOR】

**現況**（`VERIFY:20260805T135713Z-c4-not-true-mutation-confirmed`，主委獨立實跑證實
`CODEX-R14-P2-03`）：`test_gate_deny_fields.py:590-654` 僅於測試內建 `poisoned` list
並 `pytest.raises`，**未複製並執行 altered subject**。
主委把注入斷言段自**副本**移除後重跑：原檔 rc=0、副本仍 rc=0
⇒ 該段無鑑別力，測試非真 mutation。

**要求**：改為**隔離副本**移除 C4 修法後實跑同一驗收測試。
**驗收**：貼出 before／after 兩次 rc——未突變 rc=0、突變後 rc≠0。**缺一不算通過。**
（可參考同批 `test_01_c5_absolute_state_recurse_in_flips` 的寫法，該條確為真突變。）

---

## D-4 — C5 決策就地寫入 Internal Frozen TODO【MAJOR】

**現況**：`docs/GOVB0_FRICTION_TODO.md:338` 新增 HTML 註解。

**要求**：
1. **還原 TODO 為未改狀態**（`git diff docs/GOVB0_FRICTION_TODO.md` 須為空）。
   ⚠️ 用編輯工具刪除該行，**禁 `git checkout`／`git restore`**。
2. 決策改記於延伸檔（新建 `docs/GOVB0_FRICTION_TODO_AMENDMENTS.md`，
   含 C5 選 (a) 的理由與指回 TODO 的錨點）。
3. 確認 `python3 scripts/extract_phase2_expected_flips.py --check` 仍 rc=0。

---

## 每條共同要求

1. **每個修法都要有語料 B 條目（TP／TN）＋ mutation**：revert 修法後該測試須**轉紅**。
2. **禁改檢查器讓測試變綠**、**禁恆真斷言**、**禁弱化既有斷言**。
3. **禁改語料 A**（`gate_invariance_corpus.txt`）任何一行。
4. 全套 `pytest tests/governance -q` 須維持 **≥759 passed**、rc=0。**丟背景並導檔再取尾。**
5. 跑完須 `bash scripts/restore_golden_inventory.sh`。

## 🔴 不受理範圍（確認輪，嚴格執行）

1. **C6**（多 heredoc 誤擋）——順延 B4。
2. B4 以後的 Task。
3. 重開 SPEC／TODO 設計裁決。
4. `audit.log` 大小／封存／latency 主題。
5. 措辭／命名／可讀性重構。
6. 🔴 **任何 D-1～D-4 以外的改動**——本輪為確認輪。
   若途中發現新問題，**寫進報告但不要動手**。

## 硬性要求

1. **rc 一律直接取，禁經 pipe**。
2. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**（D-4 還原亦然）。
   誤動請回報，不要自行還原。
3. 不要 commit、不要 push；**禁碰 `data_cache/`**。
4. **兩輪解不了任何一條 ⇒ 停手回報**。
5. **禁 `python3 -c` 做檔案字串取代**。

## 產出

逐條（D-1～D-4）：改了什麼（貼 diff）、新增語料／測試、**mutation 前後兩次 rc**、
D-1 五樁與 D-2 五樁的實測 rc、latency **連跑 3 次**的全部數值、4MB 秒數、
全套 pytest 尾段與 rc、`git diff docs/GOVB0_FRICTION_TODO.md` 為空的證明。
收尾清 /tmp workdir（保留 claude-501）。
