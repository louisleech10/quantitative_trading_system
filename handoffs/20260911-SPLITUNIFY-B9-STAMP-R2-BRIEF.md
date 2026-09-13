# SPLITUNIFY b9 — codex 之 X1／X2 閉合再驗證＋對 D-002 同一 body 重簽

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 🔴 本輪為何只派你一家、範圍為何這麼窄（先讀）
- r17 之共識決已定：**`PROCEED`**（composer／grok `PROCEED`、你 `FIX-FIRST`）。收斂依據**不是數人頭**——你在 r17 必答 1b 寫下的退讓條件逐字為「**若本立場不採，至少保留 `SU-RESID-C5-TARGETS` 並把這 15 個 ID 具名化**」，該條件已於同輪**全額滿足**（見下 fact-verified）。
- 你在 r17 對 `docs/SPLITUNIFY_SPEC.D-002.md` 之 body `d42b3f14…` 判 **REJECTED**，`BLOCKED-BY: CODEX-R17-P1-01, CODEX-R17-P1-02`。**那兩條已修**。
- composer 與 grok 已對**同一個 body** `d42b3f14…` 簽 APPROVED 且 provenance 已補齊 ⇒ **本檔現在只差你一枚戳記**。
- 🔴 **SPEC body 一字未動**（你的兩條 blocker 都落在 `docs/SPLITUNIFY_TODO.md`，修補也都在 TODO）⇒ 本輪要重簽的是**與你上輪拒簽時完全相同**的 body hash。

## 本輪要做兩件事

### (A) 逐條重跑你在 r17 提出的反例
| finding | 你的斷言要旨 | 修補摘要 |
|---|---|---|
| `CODEX-R17-P1-01` | `Task 9.3` 之 fallback basename 對證在 15 列無任何檔名副檔名，故那 15 列不可執行核對（`C5-01`..`C5-12`、`C5-20`、`C5-22`、`C5-24`） | 驗收第 5 點改**三段式、29 列互斥窮盡**：(甲) 有 `path:line` 之 10 列走精確 keyed；(乙) 有檔名無行號之 4 列走 basename；**(丙) 那 15 列明文排除於碼證對證之外**、逐列具名、該欄填封閉字面 `NO-ANCHOR`。排除**不含**分類欄——15 列之重掃結論仍須逐列寫入 receipt 且分類欄照常對證 SPEC 現況 |
| `CODEX-R17-P1-02` | `SU-RESID-C5-TARGETS` 之觸發句無判定人、時點、輸入、比較命令 ⇒ 可無限期不觸發 | 改為**兩條客觀事件、任一成立即升級**：①以 `awk` 掃 register 無檔名列數，輸出 **≠ 15** 即代表 (丙) 組成員變動、排除清單過期；②`Task 9.3` 重掃**實際發現** (丙) 15 列中任一列分類需改動 ⇒ 須在同一次變更補 `TARGETS:`。並明定 **owner ＝ SPLITUNIFY epic 主委**、判定時機＝`Task 9.3` 驗收當下，另附誠實邊界句 |

### (B) 對 `docs/SPLITUNIFY_SPEC.D-002.md` 重簽
- body sha256（與你上輪拒簽時**相同**）：`d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`
- 逐字格式：`RECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0 task:20260911-SPLITUNIFY-B9-STAMP-R2`
- 🔴 舊戳記行（含你上輪那枚 REJECTED）請**保留**。

## 審查標的（🔴 輸入邊界：只餵 current block ＋ 本輪 diff）
- **current block**：`docs/SPLITUNIFY_TODO.md` 之 `Task 9.3` 驗收第 5 點全段（三段式判準 ＋ `SU-RESID-C5-TARGETS` 殘留段）。
- **本輪 diff**：`git show b27002f3 -- docs/SPLITUNIFY_TODO.md`
- 🔴 **不在審查範圍**：`docs/SPLITUNIFY_SPEC.D-002.md` 正文（本輪一字未動）、`HISTORY-BEGIN`～`HISTORY-END`、「## 沿革與追溯索引」節。**anchor 落在歷史段者不受理**。
- 🔴 **不得重開**：r17 之共識決方向（`PROCEED`）、`C5-01`..`C5-29` 之 mutation 欄對應、mutation 條數與 ID 連續性（40、01–40）。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 你的退讓條件已全額滿足 → `Task 9.3` 驗收第 5 點 (丙) 段逐字列出 15 個 ID（`C5-01`／`C5-02`／`C5-03`／`C5-04`／`C5-05`／`C5-06`／`C5-07`／`C5-08`／`C5-09`／`C5-10`／`C5-11`／`C5-12`／`C5-20`／`C5-22`／`C5-24`），且 `SU-RESID-C5-TARGETS` 殘留保留並補上兩條可執行觸發。派工後預期值: 不變（唯讀審查）。
fact-verified: SPEC body 未動 → 本輪 diff 不含 `docs/SPLITUNIFY_SPEC.D-002.md`；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` 仍為 `d42b3f14c4e33f51ca4fb04e66526db245b7f2cb080198afcd989c0d9c3730a0`。
fact-verified: 另兩家已簽同一 body → `grep '^RECONCILE-STAMP' docs/SPLITUNIFY_SPEC.D-002.md | tail -3` 顯示 composer 與 grok 對 `d42b3f14…` 皆 APPROVED；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` 之未過原因**只剩你一家**。
fact-verified: 15 之數字為機械得出 → `awk -F'|' '/^\| \`C5-[0-9]+\`/ { if ($3 !~ /[A-Za-z0-9_]+\.(py|ts|tsx|json)/) n++ } END {print n}' docs/SPLITUNIFY_SPEC.D-002.md` 輸出 15，與你 r17 所列清單逐字一致。

assumed: 「(丙) 15 列明文排除碼證對證、但分類欄仍對證」這個折衷**在你的 P1-01 語意下足以閉合**。**我的否證觀測（已先跑）**：你的斷言是「那 15 列無法被執行性核對」——明文排除使該檢查對它們**不再宣稱存在**，因此不會有「寫了跑不動」的假閘。**我沒查**：你是否認為「排除」本身就是不可接受的降級（即你要的是補錨而非排除）。← **請直接攻這條**；若你堅持排除不可接受，請說明在 `PROCEED` 已定的前提下，最小可接受替代是什麼。

assumed: 兩條新觸發條件**真的可執行**。**我的否證觀測（已先跑）**：第 1 條是一行 `awk`，輸出為整數可直接比對；第 2 條綁在 `Task 9.3` 重掃的實際結果上，有明確判定人與時機。**我沒查**：第 2 條的「分類需改動」是否可能**永遠不發生**（若 15 列全都維持現狀），使該觸發等同不存在。← **請直接攻這條**。

## 攻擊面（兩欄；我沒查的請你查）
| 面向 | 已排除（附查法） | 我沒查 |
|---|---|---|
| 15 列清單正確性 | 機械 `awk` 與你 r17 清單逐字一致 | 該 `awk` 之樣式是否會漏判（例如消費面寫了檔名但無副檔名、或寫成反引號包住的模組路徑） |
| 三段式是否互斥窮盡 | 10 ＋ 4 ＋ 15 ＝ 29 | (乙) 那 4 列的實際 ID 未在條文中逐列具名（只寫「29 − 10 − 15」）——請判是否該具名 |
| 殘留觸發條件 | 兩條皆有命令／owner／時機 | 見 assumed 2 之「可能永不發生」 |
| SPEC body | 本輪未動、另兩家已簽 | — |

## 必答（逐條 verdict；成對，不得只答一半）

1. **(1a)** `CODEX-R17-P1-01` 與 `CODEX-R17-P1-02`：逐條給 `CLOSED` 或 `STILL-OPEN`。
   **(1b)** 判 `CLOSED` 者，寫出你重跑的命令與觀測到的輸出特徵。
2. **(2a)** (乙) 那 4 列是否該在條文中逐列具名（而非只寫算式）？
   **(2b)** 若該具名，請直接給出那 4 個 ID（你算得出來就給，不要只說「應該具名」）。
3. **(3a)** 殘留觸發條件第 2 條是否可能永不發生而使殘留等同不存在？
   **(3b)** 若可能，給**最小**補強字面；若不可能，說明理由。
4. **(4a)** 對 body `d42b3f14…`：`APPROVED` 還是 `REJECTED`？
   **(4b)** 若仍 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉；並說明在 r17 共識決已定 `PROCEED` 的前提下，該阻擋項為何仍屬**必須先修**而非具名殘留。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填你自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
