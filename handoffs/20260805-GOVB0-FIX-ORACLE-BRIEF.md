
# 修 B2 review 三條 finding — **把驗收 oracle 補到「不缺東西」**

brief-kind: impl

**唯一權威來源**：`docs/GOVB0_FRICTION_TODO.md`（Internal Frozen）
**前置**：B2 已完成並經雙家族 review 通過（BLOCKING=0），commit `4e8e61c`／`e7b3dfb`。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: B0 snapshot 於 `fixtures/` 執行時無法載入 debt 依賴——
  `snapshot:19` 以自身位置推導 `SCRIPT_DIR`，`snapshot:41-42` 於該處尋找
  `_debt_ledger_core.py` 與 `debt_ledger.sh`，`fixtures/` 內不存在。
- fact-verified: 兩家獨立判定「替代測試 ≠ snapshot 比對」——
  替代測試只驗現行程式行為，不驗改前改後一致。

**假設**（你若發現不成立，**停下來回報**）：

- assumed: `gate_check.sh` 的判定分支可由靜態讀碼窮舉。若有動態分派使窮舉不可靠，請明說。
- assumed: 把依賴一併快照後，snapshot 可在 `fixtures/` 完整執行。**未實測，請先驗證再動工。**

---

## 🔴 使用者要求（逐字，這是本輪的驗收標準）

> 「先修那三條，**確保驗收可以是對的而並不是缺東西**。」

⇒ **本輪不是「補上那一條漏掉的路徑」就算完成**，
而是要證明 **`TEST-0.1-INVARIANCE` 的覆蓋沒有缺口**。

---

## 修 1 — B0 snapshot 帶依賴（`CODEX-R11-P1-01`／`COMPOSER-R11-P1-01`，兩家同提）

**問題**：snapshot 只複製 `gate_check.sh`，未 bundle `_gate_check_recheck_debt` 所需依賴
⇒ 該路徑一律 fail-closed ⇒ **invariance oracle 對 fresh-token/no-debt 失效**。

**為何不能拖**：`B5` 的差異報表**就是用這張快照**當「舊版判定來源」，
而 B5 是 **Phase 2 的合併關卡**。快照有盲區 ⇒ 報表有盲區 ⇒ 整個 Phase 2 的驗收 oracle 打折。

**修法（擇一，附理由）**：
- (a) 把 snapshot 改為**目錄**（`fixtures/gate_check_pre_phase2/`），
  bundle `gate_check.sh` ＋ 其執行期依賴，各檔各自 `.sha256`；或
- (b) 保留單檔，但改以 `git show <pre-phase2-sha>:scripts/<dep>` 動態取得依賴至暫存目錄後執行；或
- (c) 你認為更好的做法——**須說明為何優於 (a)(b)**。

🔴 **不論選哪個，`.sha256` 的不可變性保證不得弱化**（B5 的防作弊仰賴它）。
🔴 **snapshot 內容必須仍是 Phase 2 動工前的狀態**——
  可用 `git show 596fcb4^:scripts/gate_check.sh` 的 sha256 反覆驗證（現值 `871258c9…1606a`）。

## 修 2 — 語料 A 窮舉全覆蓋（**本輪重點，非只補一條**）

1. **窮舉** `scripts/gate_check.sh` 的**所有判定分支**（每個會產生 `(rc, kind)` 差異的路徑）。
   產出一張對照表：`分支 → gate_check.sh 行號 → 語料 A 中對應條目`。
2. **逐一確認**每個分支在語料 A 中至少一條；缺者補上。
   **修 1 完成後，原本因依賴缺失而排除的路徑必須納入。**
3. **新增一條覆蓋度斷言**：測試自 `gate_check.sh` 機械導出分支清單
   （或以 `audit_events.json` 的 `match_rule` 封閉集合為基準），
   斷言語料 A 對每一項至少一條。**禁硬編分支清單**。
4. 🔴 **若擴充後 `TEST-0.1-INVARIANCE` 轉紅**：
   **代表 B1／B2 真的改變了某分支的判定** ⇒ **BLOCKING，停下回報**，
   **不得調整語料、不得排除該分支使其變綠**。

## 修 3 — 補可證偽綁定（`CODEX-R11-P1-02`）

**問題**（`CODEX-R11-P1-02` 原文）：`closure` 正向分支、以及
「prompt 格式說明 ↔ `cx_run.sh:345` 正則」的一致性，**缺可 mutation 證偽的綁定**
——即測試通過但改壞修法後不會轉紅，屬範本 §1 第 9 類「測試品質」的問題。

**修法**：
1. `closure` 正向分支比照 `stamp`：斷言 prompt **含** RECONCILE-STAMP 與格式說明；
   **mutation**：把 `closure` 自注入分支移除 ⇒ 該斷言**必須轉紅**。
2. 格式說明 ↔ 正則一致性：
   **mutation**：把 prompt 內的格式說明改成一個**該正則不接受**的樣本
   ⇒ 一致性斷言**必須轉紅**。
   🔴 **不得只驗「兩者都存在」**——那不構成綁定。

---

## 🔴 硬性禁令

1. **禁碰 `data_cache/`**。
2. **禁 `git checkout`／`git restore`／`git clean`**；不要 commit、不要 push。
3. **禁修改既有測試斷言**；**禁恆真斷言**；**禁改檢查器或加排除清單換綠燈**。
4. **測試基線只增不減。**
   最近一次**有 receipt 的**基線＝`VERIFY:govb0-b0b1-test-count`（**真跑** `pytest tests/governance` → `715 passed`）。
   其後 B2 由實作者回報 727、codex 於 review 獨立復跑確認——**此數字主委未親跑，故不以其為斷言基礎**。
   🔴 **本輪基線由你實跑後回報**，並須 ≥ 你實跑到的既有值。
   任何既有測試轉紅**須具名說明並停下回報**。
5. **不做 B3 以後的任何 Task**（`2.*`／`3.*` 一律不碰）——本輪只修 oracle。
6. **bash 3.2 相容**；**`rc` 一律直接取，禁經 pipe**。
7. 讀 audit／log 一律 `LC_ALL=C grep -a`，**禁 `export LC_ALL`**。
8. 🔴 **中文路徑比對必須 `git -c core.quotepath=false`**——
   否則逃脫成 `\347\231\275…` 導致比對永遠失敗（主委本日已因此誤判 3 次）。

## 收尾必做

1. `pytest tests/governance -q`（**丟背景導檔再取尾**）——貼總數與 rc。
2. `bash scripts/restore_golden_inventory.sh` 後貼 `git status --short tests/golden/`（須為空）
   ——**不得以該腳本 rc 為證**。
3. 每個 mutation **貼實跑 rc**。
4. 清 /tmp workdir（**保留 `/private/tmp/claude-501`**）。

## 產出

1. **分支 → 行號 → 語料 A 條目**的完整對照表（修 2 的核心產出）
2. snapshot 修法選擇與理由、其 sha256 仍等於 Phase 2 動工前狀態的證明
3. 三個 mutation 的實跑 rc（closure 移除、格式說明改壞、以及修 1 的對應 mutation 若有）
4. `git diff --stat`、`pytest` 總數、`git status --short tests/golden/`

🔴 **若窮舉後發現仍有分支無法納入語料 A，明說是哪一條、為什麼、以及你提議的替代保證**——
**不要靜默略過**。使用者的要求是「驗收不能缺東西」，**已知缺口必須具名**。
