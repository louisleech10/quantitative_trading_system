
# B3 修補 R2 確認審查（雙家族）— D-1～D-4 是否真的關閉

brief-kind: review

**受審**：工作區未 commit 變更
**依據**：`handoffs/reconcile/20260805-govb0-b3-fixreview/synth.md`（三家戳記 `sha256:eea35be5…`）
**實作報告**：`handoffs/20260805-govb0-b3-fix2-grok.md`（**視為不可信資料**，須獨立複核）

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — 完整讀取並照做。
finding heading 逐字格式 `^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`，本輪用 `R15`。
零 findings 請明寫 `FINDINGS_COUNT: 0`。

🔴 **本輪為確認輪**：驗 D-1～D-4 是否關閉、有無回退、有無新引入缺口。
**不受理任何 D-1～D-4 以外的新主題**（見不受理範圍）。

## §0 前提宣告

**已查證**（主委獨立實跑，非採信實作報告）：

- fact-verified: 三條原始 fail-open **未回退**——引號內命令替換／引號 env 前綴／8KiB 後綴 皆 rc=2。
- fact-verified: D-1 繞道三變體 **舊 rc=0 → 新 rc=2**：
  `codex exec x; echo scripts/gate.sh`／`codex exec x  # scripts/gate.sh`／
  `8200B; scripts/gate.sh; codex exec hi`。
- fact-verified: D-1 **未過嚴**——`bash scripts/gate.sh dispatch --task-id X`／
  `bash scripts/gate_check.sh`／`bash scripts/gate.sh register-output T p.md` 皆 rc=0；
  而 `bash scripts/gate.sh dispatch; codex exec x` rc=2（合法前綴後接派工仍擋）。
- fact-verified: D-2 摩擦已消——`echo`+8200 字元無害字串 **新 rc=0**（R1 時為 2）。
- fact-verified: `git diff docs/GOVB0_FRICTION_TODO.md` 為**空**（已還原）；
  `git diff tests/governance/fixtures/gate_invariance_corpus.txt` 為**空**（語料 A 未動）。
- fact-verified: `pytest tests/governance -q` → **763 passed** rc=0（主委親跑，287s）。

**假設**（請優先攻）：

- assumed: D-2 的 O(n) 掃描在 **latency 與 4MB 兩端**都成立。
  主委**只跑了全套 pytest**（含 latency 測試），**未獨立連跑 3 次 latency、未獨立測 4MB**。
- assumed: D-3 的新 C4 測試**這次**是真 mutation。
  主委 R1 時曾誤判此點（`VERIFY:20260805T135713Z-c4-not-true-mutation-confirmed` 為當時的證偽），
  **本輪未重驗**。
- assumed: 新增測試（763−759＝4 條）各自都會因對應修法 revert 而轉紅。**未逐條驗證。**

---

## 逐項核對

| # | 查什麼 | 通過條件 |
|---|---|---|
| 1a | D-1 修法是否**只**排除「整條即 gate invocation」 | 讀碼＋自構反例；能繞過＝BLOCKING |
| 1b | D-1 是否誤擋任何既有 TN 語料 | 對照語料 B TN 全跑 |
| 1c | D-2 是否真為 O(n)（非隱藏長度上限、非取樣） | 讀碼確認；殘留硬頂＝BLOCKING |
| 1d | D-2 latency **連跑 3 次**全部數值 | 全部 <100ms；**門檻是否被動過** |
| 1e | D-2 4MB 輸入 rc 與秒數 | rc=2 且有界 |
| 1f | D-3 C4 mutation before／after rc | 未突變 rc=0、突變後 rc≠0；**缺一即未通過** |
| 1g | D-4 延伸檔內容是否足以取代就地註解 | 含 TODO 錨點與實作錨點雙向指回 |
| 1h | 新增 4 條測試逐條 mutation | 每條 revert 後須轉紅 |
| 1i | 有無**新引入**的 fail-open 或誤擋 | 自構攻擊向量；發現即 BLOCKING |

## 🔴 收斂斷路器（本輪特別注意）

R1 修補曾引入一條新缺口（D-2）。裁定為：**若 R2 再現「修補引入新缺口」型態，
即觸發 epic 斷路器——停手、開委員會重審 C1 設計，不再往下修。**

⇒ 若你發現本輪修補又製造了新問題，**請明確標註 `NEW-DEFECT-INTRODUCED`**，
不要只當成一般 finding。這個標註會直接決定要不要停手。

## 🔴 不受理範圍（確認輪，嚴格執行）

1. **C6**（多 heredoc 誤擋）——已裁順延 B4。
2. B4 以後的 Task。
3. 重開 SPEC／TODO／收斂裁決。
4. `audit.log` 大小／封存／latency 門檻值本身。
5. 措辭／命名／可讀性。
6. **D-1～D-4 以外的既有缺陷**——寫進報告標 `OUT-OF-SCOPE` 即可，不列 finding。

## 出場判準

> **findings ≤3 且 BLOCKING = 0 且無 `NEW-DEFECT-INTRODUCED` ⇒ B3 驗收通過，可進 B4。**

（門檻由 5 收緊為 3：確認輪應該愈收愈窄；若仍有 4 條以上，代表沒收斂。）

## 硬性要求

1. **禁改碼、禁改測試、禁改 TODO／SPEC／延伸檔**。只交報告。
2. **rc 一律直接取，禁經 pipe**。
3. 🔴 **禁 `git checkout`／`git restore`／`git clean` 任何 tracked 檔**；誤動請回報，不要自行還原。
4. 不要 commit、不要 push；**禁碰 `data_cache/`**。
5. 跑全套請**丟背景並導檔再取尾**；跑完須 `bash scripts/restore_golden_inventory.sh`。

## 產出

1a–1i 逐項判定與實測值、`## 出場判準核算`、
對 §0 三條假設的攻擊結果、有無 `NEW-DEFECT-INTRODUCED`。
收尾清 /tmp workdir（保留 claude-501）。
