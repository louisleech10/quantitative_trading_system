# SPLITUNIFY b9 — review-r14 U1-U3 閉合再驗證 ＋ D-002 v15 重簽

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## ⚠️ 前置說明（勿誤 block）
- `handoffs/reconcile/*/synth.md` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK。
- 🔴 **本輪不重審 SPEC 既有內容**。R12 停輪判準已觸發；R13／R14 三家亦一致判「不為三條 ASSERT 重開 §V」。本輪標的**只有** v14→v15 的 diff。
- 🔴 **`C5-01`..`C5-29` 的逐列 mutation 對應已於 R14 窮舉完成**（三家獨立確認 `C5-01`..`23` 與 `C5-26` 無誤）。本輪請**複驗那五列的修補**，不必重跑整張表——除非你認為 R14 的窮舉本身有洞，那請直接說並給碼證。

## 本輪要做兩件事

### (A) 逐條重跑你自己在 review-r14 提出的反例
| finding | 提出方 | 修補摘要 |
|---|---|---|
| `CODEX-R14-P1-01` ／ `GROK-R14-P2-03` | codex／grok | `M-SU-D2-35`／`36` 應紅欄改為：先斷言欄位存在、再做複合鍵唯一性；**刪欄**與 **`in df.columns` 軟包**兩種破壞皆須 FAIL；fixture 須多 feature TF。SPEC 兩列與 TODO `Task 9.2a` 同步 |
| `CODEX-R14-P1-02` ／ `COMPOSER-R14-P2-02` ／ `GROK-R14-P2-04` | 三家 | `Task 9.3` receipt 閘加兩條內容對證：①改前分類須逐列等於 SPEC register 現況第三欄 ②碼證 `path:line` 須指向真實存在的檔與不超範圍的行；並把 `COMMIT:` 改為須等於 audit 之 round-start HEAD |
| `CODEX-R14-P1-03` ／ `COMPOSER-R14-P2-01` ／ `GROK-R14-P1-01` ／ `GROK-R14-P1-02` | 三家 | `C5-24` 改掛 `M-SU-D2-05`／`M-SU-D2-37` 兩條；`C5-25`→`M-SU-D2-38`；`C5-27`→`M-SU-D2-39`；`C5-29`→`M-SU-D2-40`；`C5-28` 之 `—` 具名為刻意（`blocked-by`）。條數 36→40 |
| `CODEX-R14-P2-04` | codex | **部分採納**：判定成立但本輪不改判準（量測進行中由被量測者單方調整不正當，且其 SSOT 已蓋章）⇒ 改為同時報兩個數字。請判此處置是否可接受 |

### (B) 對 `docs/SPLITUNIFY_SPEC.D-002.md` **重簽**
- v14 之戳記（composer APPROVED、codex／grok REJECTED）因本次修訂而失效。新 body sha256（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`）：
  `c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0`
- 審完 append 到該檔 `## 戳記` 區，逐字格式：
  `RECONCILE-STAMP: <family> APPROVED 2026-09-13 sha256:c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0 task:20260911-SPLITUNIFY-B9-REVIEW-R15`
- 🔴 舊戳記行請**保留**（追溯用）。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：
  - `docs/SPLITUNIFY_SPEC.D-002.md`：`C5-24`／`25`／`27`／`28`／`29` 五列、`M-SU-D2-35`..`M-SU-D2-40` 六列、mutation 目錄標題行
  - `docs/SPLITUNIFY_TODO.md`：`§C-9` 之 `Task 9.2a` 與 `Task 9.3`（含其表之 `tables`／`ic_feed`／`pattern_bridge` 三列）與 `Task 9.4`
- **本輪 diff**：`git show 0de1a17f -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md`
- 🔴 **不在審查範圍**：`HISTORY-BEGIN`～`HISTORY-END` 與「## 沿革與追溯索引」節。**finding 之 source anchor 落在歷史段者不受理**。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: mutation 表 40 列、ID 01–40 連續 → `grep -cE '^\| .M-SU-D2-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` ＝ 40，逐號無缺。派工後預期值: 不變（唯讀審查）。
fact-verified: §C-9 對 40 條全數認領 → `awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` ＝ 40。
fact-verified: register 仍 29 列 → `grep -cE '^\| .C5-[0-9]+.' docs/SPLITUNIFY_SPEC.D-002.md` ＝ 29。
fact-verified: 條數字面只一處 → `grep -c '共 \*\*40\*\* 條' docs/SPLITUNIFY_SPEC.D-002.md` ＝ 1。
fact-verified: 兩檔格式閘 rc=0 → `bash scripts/doc_format_precheck.sh` 對兩檔皆 rc=0。

assumed: R14 的逐列窮舉**已把存量錯配清乾淨**，`C5-01`..`23`／`C5-26` 確實無誤。**我的否證觀測（已先跑）**：三家在 R14 各自獨立做了逐列核對，codex 明列「`C5-01..23`、`C5-26` 可對應」，grok 獨立命中的兩列（`C5-25`／`C5-29`）都在 codex 的五列之內 ⇒ 兩家交集無新增。**我沒查**：那五列以外，是否有「mutation 存在且對應正確，但其**應紅之測試**欄指向不存在或不會紅的測試」——這是**另一個維度**，R14 只查了對應關係。← **請直接攻這條**。

assumed: `Task 9.3` 之 receipt 閘加了「改前分類對證 SPEC 第三欄」與「碼證 path:line 須存在」兩條後**已無可行繞過**。**我的否證觀測（已先跑）**：這兩條分別殺掉 R14 三家實證的「全填同值」與「占位路徑」。**我沒查**：實作者可以照抄 SPEC 第三欄、並把碼證全指向同一個真實存在的檔的第 1 行（例如 `docs/SPLITUNIFY_SPEC.D-002.md:1`）——這樣兩條都過，但仍未真正重掃。← **請直接攻這條**，若成立請給**最小**加強字面。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| register 逐列 mutation 對應 | R14 三家窮舉，五列已修（上列 fact-verified 與 assumed 1） | 🔴 **應紅之測試欄**這個維度（見 assumed 1） |
| `M-SU-D2-35`..`40` 六條新編號本身 | 條數、ID 連續、§C-9 認領皆已驗 | 六條各自的「應紅之測試」是否**真的存在或可被建立**；`M-SU-D2-37`／`38`／`40` 指向的具名測試目前皆**不存在**（Task 9.3 未開工）——請判這是否為可接受狀態，還是該在 TODO 標更明確的建立責任。VERIFY-EXEMPT:doc-example:brief-attack-surface |
| receipt 閘 | 已堵「全填同值」與「占位路徑」 | 見 assumed 2 之「全指同一真實行」繞過 |
| `C5-28` 之 `—` | 已具名 `blocked-by` 且交付面確在殘留內 | 該殘留之**觸發條件**是否可執行（`SU-RESID-9A-UI` 之 recheck 命令） |
| DOCROT 判準之處置 | 本輪不改判準、同時報兩個數字 | 此處置是否可接受；若不可接受，你認為誰有權改、何時改 |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** 逐條重跑你在 review-r14 提出的反例，給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出你重跑的命令與觀測到的輸出特徵。
2. **(2a)** `M-SU-D2-01`..`40` 中，有哪幾條的「**應紅之測試**」欄指向不存在、或存在但**不會**因該破壞而紅的測試？逐條列出。
   **(2b)** 若你答「零條」，貼出你用來核對的可執行命令或逐條對照表；「逐項核對後無問題」不受理。
3. **(3a)** `Task 9.3` 之 receipt 閘還能被繞過嗎？（特別是「分類照抄 SPEC ＋ 碼證全指同一真實行」）
   **(3b)** 若能，給**最小**加強字面；若不能，說明你試了哪幾種構造。
4. **(4a)** `CODEX-R14-P2-04` 之處置（判定成立、本輪不改判準、同時報兩個數字）可接受嗎？
   **(4b)** 若不可接受，說明誰有權改該判準、以及在量測未結束時改它為何不算被量測者自己放寬標準。
5. **(5a)** 對新 body sha256 `c674086e…`：`APPROVED` 還是 `REJECTED`？
   **(5b)** 若 `APPROVED`，指出 v15 裡最可能在 `Task 9.1` 實作當下變紅的條文（具名）；若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。
6. **(6a)** 現在可以領 impl token 進 `Task 9.1` 了嗎？
   **(6b)** 若可以，說明你檢查了什麼；若不可以，列**最小**閉合集合。
   🔴 **另請一併判**：本票已連跑 r13／r14 兩輪、每輪都在同一類問題上找到新東西。你認為**還在收斂**，還是**已進入窮舉遞減報酬**？給判準，不要給感覺。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
