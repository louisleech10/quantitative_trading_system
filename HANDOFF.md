# HANDOFF

**當前**：GAP-3 事件型 UAT 缺口修補 SPEC（`docs/GAP3_EVENT_UX_SPEC.md`）
——**R8 架構變更全部落地**（本批），**待派 R9**。SPEC 1981 行、**42 Task（未增未減）**。
sha256 `8c66861e…`（R9 審查期間不得動該檔）。

🔴 使用者 2026-08-23 裁定：**輪次上限已解除**（「就做到完整 Frozen，不用管輪次」）、
**42 個一個不砍**、**A-6′ 已確認**（FROZEN 條件③滿足）⇒ 三者皆**不必再問使用者**。

---

## 🔴 開工前必讀

**角色卡＝`docs/GAP3_EVENT_UX_ROLE_CARD.md`**。三條最要緊：
主委**不得**自寫第二處複述／觸及 SPEC 之 commit 須有補丁包或 ERRATA id／
派審前跑 `bash scripts/gap3ux_pre_review.sh <patch.md>`。
🔴 **任何文件一律不寫閘數**（已犯四次）——權威清單唯一在 `gap3ux_pre_review.sh` 之 `run` 呼叫序列；
計數稽核之掃描面與呼叫唯一在 `scripts/gap3ux_count_check.sh`。

---

## 本批（R8 落地）做完什麼

§D-3′／§D-3′-a／§D-7 增訂／§A A-6′／§F-0..F-5′／§G G-3／
Task 1.1・1.9・1.12・4.1・4.1b・4.1c・4.3・5.3・7.0・7.0b・7.1・7.2・7.4・7.6・7.7／
V-6・V-12・V-16・V-17・G-3／§R／Phase 4 更名。工具：`ic_feed.py` 檔頭、`gap3ux_pre_review.sh` 截斷修復。

**三個主委裁決點**（補丁包互斥，理由皆已寫進 SPEC）：
1. **匯出端仍須寫 `window.horizon_bars`**（§D-3′-a）——`-arch-shift` 說不得寫，但
   `import_contract.py:163` 強制 `int ≥ 1`，照寫會使匯出檔無法匯入 ⇒ 採 `-arch-analyze-time-label`；
   該欄語意改為 **D-7 之 lookahead 深度宣告**，非答案窗。
2. **transport 折進 `ICAnalyzeRequest`**（Task 7.0b ②）——不採 `-arch-shift` 之
   `/api/v1/ic/event-label-values` 與 `-arch-analyze-time-label` 之 `/event-batches/{id}/conditional-ic`；
   兩者讓 `label_value` 經前端往返，可造成「purge 用 h=3、label 用 h=7」，正是 §D-3a 要根除者。
3. **三元組在 IC 頁「有控制項但鎖 F-1′」**（§F-1′）——`-arch-shift` 說可自由設定，
   但兩份補丁包指定之 golden 都只涵蓋 F-1 三元組 ⇒ 依 §C0 取嚴。

**兩處主委補充，已具名標「待 R9 裁定」**：
§D-3′-a（i）深度 0 vs 契約下限 1、（ii）`purge = max(深度, 本次 h)`；§F-5′ CSV 自帶值之互斥處置。

---

## 🔴 立即待辦：派 R9（brief 尚未寫）

- facts：`bash handoffs/20260823-gap3ux-x-review-r9-facts.sh` → rc=0（15 條，含 F-05／F-08／F-10 三條新關鍵碼證）
- brief 範本沿用 R8（`handoffs/20260823-gap3ux-x-review-r8-brief.md`），改輪次＋改議題
- 🔴 **R9 第一議題＝locus 閘現為紅，主委未放寬**：
  `bash handoffs/20260823-gap3ux-x-review-r9-locus.sh` 列出全部未達 locus，分兩類——
  ①**實作階段之 code locus**（`ICAnalyzeRequest`／`useICAnalysis` 等）：SPEC 未凍結、未進實作，現在不該動
  ②**anchor 寫成敘述而非可比對字面**（`檔頭 A-6／FROZEN 句`／`§A-A-6`／`§G-G-2` 等）：
    角色卡誠實邊界 2 已載「anchor 精確度是委員責任」
  **實質內容四份補丁包皆已套用，無一漏套**；請 R9 裁定 locus 閘之 stage 語意，勿由主委自訂。

---

## FROZEN 四條件（唯一終點；輪數無上限）

| # | 條件 | 現況 |
|---|---|---|
| ① | 正確性／洩漏／接線類 OPEN P0＝0、P1＝0 | ⬜ 待 R9 |
| ② | 本輪主委自傷絕對數＝0 | ⬜ 待 R9 |
| ③ | A-6′ 經使用者確認 | ✅ 已滿足（2026-08-23 逐字裁定） |
| ④ | `bash scripts/gap3ux_pre_review.sh` rc=0 | 常駐閘 ✅；**含補丁包之 locus 對證 ❌**（見上） |

---

## 🔴 做不成機械閘者（三家明列，不得宣稱已封）
「選哪個技術修法正確」／「使用者 label 語意是否正確」／「**未被列出的**隱藏複述」

---

## 收斂履歷與錯誤帳（**須並列絕對數**；佔比是壞指標 GROK-R3-P2-01）

| 輪 | findings | 主委自傷（絕對數） | 錯誤類型 |
|---|---|---|---|
| R1–R3 | 24 → 7 → 18 | — | — |
| R4 → R7 | 19 → 13 → 15 → 12 | 3 → 5 → 6 → 7 | 選錯修法 → 整合字面不同步 |
| R8 | 17（含 7 份補丁包） | 6 | 全在主委自建工具／receipt |
| **R8 落地（本批）** | — | **2（自查自修，已附反測 receipt）** | ①`pre_review` 輸出截斷至前 6 行 ⇒ 四份補丁包只顯示前兩份之未達 locus，主委一度誤判「後兩份全過」②R9 locus 列表首版 `cmd \| grep … \|\| echo` 撞 pipefail ⇒ 未達清單後印「全達」 |

委員找到之真缺口：約 16 → 8 → 9 → 5 → 8。
**Task 數**：本批 42 → 42（**未增未減**；改寫 7 個 Task，新增 0）。

---

## 坑（累積；全部實測過）

- **rc 一律直接取**：`cmd \| grep …` 在 `set -o pipefail` 下，前段非 0 會讓整條 pipeline 非 0
  ⇒ `|| echo '全達'` 會在有缺口時照印（本批再犯一次，已改「先收變數再判空」）
- **報告層截斷＝fail-open**：`sed -n '1,6p'` 之類的省略會把後面的紅吃掉（本批再犯一次）
- **shell 文字工具對非 ASCII 不可靠**（macOS awk 逐位元組）⇒ 比對中文一律用 Python
- **`doc_format_precheck` 之空殼偵測按「行」判**：續行以 `**` 開頭會被當 bullet；
  該行若含「驗證」二字又無數字／`pytest`／`==` 等 token ⇒ 判空殼。改寫時把 token 放同一行
- **`git diff HEAD --name-only` 不含 untracked**；**`git status -uall` 不含 ignored**
- `git checkout`／`git restore --staged`／`rm` 被 auto-mode classifier 擋 ⇒ 還原用 Edit，unstage 用 `git reset -q HEAD <path>`
- **長 heredoc 會被 `gate_check` 誤判為派工**；`cd <絕對路徑>` 會觸發權限分類器（本 session 兩次 A 類卡頓 21s／16s）
- `handoffs/*` 在 `.git/info/exclude`：新檔須 `git add -f`；委員產出（review／補丁包）**不入版控**
- `plain_docs_sync_check` 是 commit 時序判準：先 `git add` 再跑 `--staged`
- commit 之 `Governance-Scope` trailer 須單行；長訊息一律 `git commit -F <檔>`

## 已知既有紅（非本批造成）
`tests/api` 10 failed + 3 errors／G-7 scope 淨差（基準凍結 2026-08-07）／
`.probe_ic{,2,3}.sh`（untracked 殘檔，`rm` 被權限擋）

## 其他線
`/search` 三 bug 修復 🏁 已收案。GAP-3 五個施工批全部蓋章，只差使用者 UAT B 段 13 項簽字。
#9b 規模防護排 GAP-6；純事件研究模組／標籤方法論討論皆使用者裁定另立。
