# SPLITUNIFY b9 — review-r15 V1-V5 閉合再驗證 ＋ D-002 v16 重簽（停輪判準生效輪）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 🔴 本輪的停輪判準（r15 三家給、主委逐字採；本輪即其生效輪）
逐字取自 `handoffs/reconcile/20260911-splitunify-b9-review-r15/synth.md` 之收斂段（composer 版）：
- **若本輪再出現「register 錯配」或「mutation 條數不一致」** ⇒ 判**未收斂**，**停輪並回報使用者**，不再自行加輪。
- **若只剩 P2 級字面問題** ⇒ 允許進 `Task 9.1` 實作，並於 `Task 9.3` 驗收時補洞。
🔴 **請在你的交件中明確回答本輪落在哪一邊**（必答 5）。這不是修辭題——它決定本票是繼續派輪還是停下來。

## ⚠️ 前置說明（勿誤 block）
- 🔴 **本輪不重審 SPEC 既有內容**。R12 停輪判準已觸發；R13／R14／R15 三輪皆一致判「不為三條 ASSERT 重開 §V」。
- 🔴 **`C5-01`..`C5-29` 的逐列 mutation 對應已於 R14 窮舉完成、R15 零復發**。本輪請**只複驗 r15 那五條修補**，不要重跑整表——除非你能給出「R14 窮舉本身有洞」的碼證。

## 本輪要做兩件事

### (A) 逐條重跑你自己在 review-r15 提出的反例
| finding | 提出方 | 修補摘要 |
|---|---|---|
| `CODEX-R15-P1-01` ／ `COMPOSER-R15-P2-01` | codex／composer | receipt 碼證改為**逐列 keyed 對證**：第 `C5-NN` 列之碼證檔路徑須與 SPEC register 同一列所載落點檔相同、行號須落在該列範圍內 |
| `CODEX-R15-P1-02` | codex | `M-SU-D2-38` 改寫為**可達 seam**＝`event_context_from_windows` 本身（餵入含重複 `event_id` ⇒ 雜湊漂移），測試改為直接呼叫該函式驗不變性 |
| `CODEX-R15-P1-03` | codex | `M-SU-D2-39` 之具名測試補 `summary["per_symbol_n"]`／`per_symbol_test_n` 之去重計數斷言 |
| `CODEX-R15-P1-04` | codex | `M-SU-D2-40` 改為「移除 `tables.py:372` 之顯式去重 reducer」，並要求**成對**測試（同值去重成功／衝突值 fail-closed） |
| `GROK-R15-P2-01` | grok | receipt 閘語義殘留，併入上列 keyed 對證處置 |

### (B) 對 `docs/SPLITUNIFY_SPEC.D-002.md` **重簽**
- 新 body sha256（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`）：
  `8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0`
- 逐字格式：`RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:8607f2b770fb39f967c7c75686a90f4c1bc39a7d1536cc70bca1909e838021a0 task:20260911-SPLITUNIFY-B9-REVIEW-R16`
- 🔴 舊戳記行請**保留**。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `M-SU-D2-38`／`39`／`40` 三列；`docs/SPLITUNIFY_TODO.md` 之 `Task 9.3`（含其表之 `tables`／`ic_feed` 兩列）與 `Task 9.4`。
- **本輪 diff**：`git show 79b66dd1 -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`
- 🔴 **不在審查範圍**：`HISTORY-BEGIN`～`HISTORY-END` 與「## 沿革與追溯索引」節。**anchor 落在歷史段者不受理**。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: `M-SU-D2-38` 之新 seam 可達 → 主委實讀 `momentum/Analysis/event_samples/ic_feed.py`：`event_context_from_windows` 是模組級公開函式、只吃 `windows`／`label_definition`／`control_kind`，可直接以含重複 `event_id` 之 windows 呼叫。派工後預期值: 不變（唯讀審查）。
fact-verified: `M-SU-D2-40` 之新描述與 pandas 實際行為相符 → 主委實跑 `set_index("event_id")["symbol"].reindex(...)` 於重複索引得 `ValueError: cannot reindex on an axis with duplicate labels`（非靜默取值）。
fact-verified: mutation 40 列、ID 01–40 連續、§C-9 認領 40/40、register 29 列、條數字面一處 → 五項逐一實跑 `grep`／`awk` 確認。
fact-verified: 兩檔格式閘 rc=0 → `bash scripts/doc_format_precheck.sh` 對兩檔皆 rc=0。

assumed: keyed 碼證對證**已無可行繞過**。**我的否證觀測（已先跑）**：它把 receipt 每列綁到 register 同列的落點檔，「全填同一真實行」因此失效。**我沒查**：register 有些列的落點欄本身就寫了**多個**檔或只寫模組名而無 `path:line`（例如 `C5-25` 寫「`ic_feed` survivor **餵入端**」沒有行號）⇒ 那幾列的 keyed 對證**無從執行**。← **請直接攻這條**，逐列指出哪幾列的 register 落點欄不足以支撐 keyed 對證，並給最小修補。

assumed: `M-SU-D2-38` 改寫後，`C5-25` 之處置「先去重再算雜湊」與該 mutation **語意一致**。**我的否證觀測（已先跑）**：兩者都指向 `event_context_from_windows` 之餵入去重。**我沒查**：`C5-25` 原文寫的是「survivor **餵入端**」，而 `M-SU-D2-38` 現在指的是該函式**內部**的 `rows` 組裝——若正確實作是在**呼叫端**去重，那 mutation 的破壞點與 register 的施工點可能是**不同的兩行碼**。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| r15 四條之修補 | 逐條改寫並實讀／實跑佐證（上列 fact-verified 前兩條） | 修補後是否引入**新的**不可達或不一致（請對每條各給一次可執行檢查） |
| keyed 碼證對證 | 「全填同一真實行」已失效 | 🔴 register 落點欄本身不足以支撐 keyed 對證的列（見 assumed 1） |
| `M-SU-D2-38` 之施工點 vs 破壞點 | 兩者皆在 `event_context_from_windows` 一帶 | 是否實為不同兩行碼（見 assumed 2） |
| 40 條之「應紅之測試」維度 | R15 grok 判「預先未寫成之具名測試屬 Task 未開工可接受狀態」 | 是否仍有**已存在但不會因該破壞而紅**的測試（此為 R15 未完全排除之維度） |
| 停輪判準之適用 | 判準字面已錄於 r15 收斂段 | 本輪 findings 落在「register 錯配／條數不一致」還是「P2 級字面」——**請明確歸類**（必答 5） |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 逐條重跑你在 review-r15 提出的反例，給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出你重跑的命令與觀測到的輸出特徵。
2. **(2a)** register 有哪幾列的落點欄**不足以**支撐 keyed 碼證對證（無 `path:line`、或寫了多個檔）？逐列列出。
   **(2b)** 對這幾列給**最小**修補——是補行號、還是把 keyed 對證放寬為「檔集合包含」？給出可直接貼進 TODO 的字面。
3. **(3a)** `M-SU-D2-38` 的破壞點與 `C5-25` 的施工點是否為同一行碼？
   **(3b)** 若不是，給出正確的 seam 與對應修補字面。
4. **(4a)** 40 條中是否還有「應紅之測試**已存在**但**不會**因該破壞而紅」者？逐條列出。
   **(4b)** 若答「零條」，貼出你用來核對的可執行命令；「逐項核對後無問題」不受理。
5. 🔴 **(5a)** 依 r15 已定之停輪判準，本輪 findings 屬於「register 錯配／條數不一致」還是「P2 級字面」？**明確歸類**。
   **(5b)** 依你的歸類，本票該**停輪回報使用者**還是**進 `Task 9.1` 實作**？給一句話結論。
6. **(6a)** 對新 body sha256 `8607f2b7…`：`APPROVED` 還是 `REJECTED`？
   **(6b)** 若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
