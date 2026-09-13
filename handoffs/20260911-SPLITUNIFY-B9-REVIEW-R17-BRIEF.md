# SPLITUNIFY b9 — 停輪歸類分歧之共識決（使用者裁定交委員會）＋ D-002 v17 重簽

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 🔴 本輪為何存在（先讀這段，它決定你該怎麼答）

r16 三家對**停輪判準的歸類**分裂：
- **codex**：「屬 register 錯配／落點不足」⇒ 停輪回報使用者、不可進 `Task 9.1`。
- **composer**／**grok**：「屬 P2 級字面——非 mutation 欄 ID 指錯、非條數不一致」⇒ 進 `Task 9.1`，於 `Task 9.3` 驗收補洞。

主委已依該判準之停輪分支回報使用者。**使用者 2026-09-13 逐字回覆：「技術問題, 你們委員會共識決。我無法給出答案」**
⇒ 本輪即該共識決。**請直接給出可執行的單一結論，不要再把球踢回使用者。**

🔴 **三家在 r16 都沒有拿到的一份既有裁定**（主委疏失，現在補上，請把它納入判斷）：
> `HANDOFF.md:32` 逐字：「🔴 **不再擴建治理工具**（2026-09-12 定）；同型缺陷降級為具名殘留。」
> 其脈絡（同檔歷史）：使用者當時的理由是「主目標已被治理擠掉三次」。

請明確說明：這條裁定是否適用於「為 `Task 9.3` 的驗收收據閘再補 20 列 `TARGETS:` 錨點」這件事；若適用，它是否已足以解消 r16 的分歧。

## 爭點的事實基礎（三家在 r16 對事實**無分歧**，僅列供複驗）
- `docs/SPLITUNIFY_SPEC.D-002.md` 之 `D-002-C5` register 共 **29** 列；主委實測以「消費面欄是否含檔名加副檔名再加行號」掃描，**19 列無錨**（r16 修 `C5-25` 後由 20 降為 19）。
- 主委 v16 所寫之「逐列 keyed 碼證對證」因此在多數列**不可執行**（＝假閘）。
- r17（本版）之現行處置：**收窄**——9 個有錨列走精確 keyed 對證；其餘列走「碼證 basename 須出現在該列消費面文字中」之封閉判準；補齊 `TARGETS:` 之精確版**降級為具名殘留 `SU-RESID-C5-TARGETS`**（`blocked-by`），codex 於 `CODEX-R16-P1-01` 之逐字修法已原樣錄入該殘留。

## 本輪另一件事：對 `docs/SPLITUNIFY_SPEC.D-002.md` **重簽**
- 新 body sha256（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`）：
  `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`
- 逐字格式：`RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0 task:20260911-SPLITUNIFY-B9-REVIEW-R17`
- 🔴 舊戳記行請**保留**。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`docs/SPLITUNIFY_TODO.md` 之 `Task 9.3` 驗收第 5 點（收窄後之兩段式判準與 `SU-RESID-C5-TARGETS` 殘留段）；`docs/SPLITUNIFY_SPEC.D-002.md` 之 `C5-25` 一列。
- **本輪 diff**：`git show 0908ffad -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`
- 🔴 **不在審查範圍**：`HISTORY-BEGIN`～`HISTORY-END` 與「## 沿革與追溯索引」節。**anchor 落在歷史段者不受理**。
- 🔴 **不得重開**：`C5-01`..`C5-29` 之 mutation 欄對應（R14 窮舉、R15／R16 零復發）；mutation 條數與 ID 連續性（40、01–40）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 無錨列為 19 → 主委以 `awk` 對 register 29 列逐列掃「檔名加副檔名加行號」樣式，得 19 列無錨。派工後預期值: 不變（唯讀審查）。
fact-verified: mutation 40 列、ID 01–40 連續、§C-9 認領 40/40、register 29 列 → 四項逐一實跑確認。
fact-verified: 使用者已將本爭點交回委員會 → 2026-09-13 逐字「技術問題, 你們委員會共識決。我無法給出答案」。
fact-verified: 兩檔格式閘 rc=0 → `bash scripts/doc_format_precheck.sh` 對兩檔皆 rc=0。

assumed: `HANDOFF.md:32` 那條使用者裁定**適用**於本爭點，且足以解消分歧（因為「補 20 列 TARGETS 讓驗收閘更嚴」正是「擴建治理工具」，而「降級為具名殘留」正是該裁定指定的處置）。**我的否證觀測（已先跑）**：該裁定字面只說「不再擴建治理工具」，**沒有**定義何謂「治理工具」——若「補既有 register 的落點欄」被視為**補完既有規格**而非**擴建工具**，則該裁定不適用。**我沒查**：repo 內是否有更早的定義或先例把「補 SPEC 欄位」與「擴建治理工具」劃清界線。← **請直接攻這條**。

assumed: 收窄後的 basename 判準**仍是封閉且有鑑別力**的。**我的否證觀測（已先跑）**：它禁止任意真實路徑，要求 basename 出現在該列消費面文字中。**我沒查**：有幾列的消費面文字**完全沒有任何檔名**（只有模組名或中文敘述）⇒ 那幾列連 basename 判準也無從執行，等於又是一個較小的假閘。← **請直接攻這條，逐列給數字**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| register 之 mutation 欄對應 | R14 窮舉、R15／R16 零復發 | — |
| 收窄後之 basename 判準 | 禁任意真實路徑 | 🔴 **有幾列連 basename 都沒有**（見 assumed 2）——請逐列給數字與清單 |
| `SU-RESID-C5-TARGETS` 之殘留品質 | 已帶理由類別 `blocked-by` ＋ codex 逐字修法 ＋ 觸發條件 | 該觸發條件（「`Task 9.3` 開工時 basename 判準出現誤判」）是否**可執行**——誰在什麼時候用什麼命令判定「誤判」？若判不出來，這條殘留就是無限期擱置 |
| 使用者裁定之適用範圍 | 已把逐字原文餵給你 | 它與 r15 停輪判準孰先孰後、是否存在先例 |
| v17 之 `C5-25` 修補 | 已具名 seam `ic_feed.py:56-65` 與呼叫端 | 該 seam 之行號是否正確（請實讀複驗） |

## 必答（逐條 verdict；成對，不得只答一半）

1. 🔴 **(1a)** 依 `HANDOFF.md:32` 之使用者裁定與 r15 停輪判準，本票現在應該**進 `Task 9.1` 實作**還是**先補齊 20 列 `TARGETS:`**？給**單一**字面結論：`PROCEED` 或 `FIX-FIRST`。
   **(1b)** 你這個結論若是錯的，會以什麼形式在後面爆掉？給一個**可執行的觀測**（命令 ＋ 期望輸出特徵）。
2. **(2a)** `HANDOFF.md:32` 那條裁定是否適用於本爭點？（見 assumed 1 之否證觀測）
   **(2b)** 若你認為**不**適用，請指出「補既有 SPEC 欄位」與「擴建治理工具」的分界線在哪，並給可機械套用的判準。
3. **(3a)** 收窄後之 basename 判準：有幾列的消費面文字**完全沒有任何檔名**？逐列列出。
   **(3b)** 對那幾列給**最小**處置（是補檔名、還是明文把那幾列排除在 receipt 對證之外並具名）。
4. **(4a)** `SU-RESID-C5-TARGETS` 之觸發條件是否可執行？誰、何時、用什麼命令判定「basename 判準出現誤判」？
   **(4b)** 若不可執行，給**可直接貼進 TODO** 的替代觸發條件字面。
5. **(5a)** 對新 body sha256 `d42b3f14…`：`APPROVED` 還是 `REJECTED`？
   **(5b)** 若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。

## 🔴 共識決之程序規則（三家請遵守）
- 使用者已明示交由委員會共識決 ⇒ **不得**在 (1a) 答「交使用者裁定」。
- 若三家在 (1a) 仍不一致，主委將依既有規則「**看碼證不數人頭；不決則採較嚴版並具名殘留**」處理，並把分歧原文完整保留於收斂檔。**請在你的 (1b) 裡預先說明：若你的立場最後未被採用，你認為最該被保留成具名殘留的是哪一條。**

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**（r16 有一家填了他家 ID 被 `verdict_parse` 拒收，整輪卡住）。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
