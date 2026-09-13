# SPLITUNIFY b9 — D-002 v18 重簽（進 Task 9.2 之前置）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`（見 `templates/COMMITTEE_FINDING_TEMPLATE.md`）。

## 本輪只做一件事
`CODEX-R19-P1-01` 之修補使 SPEC body 變更 ⇒ v17 之三家 APPROVED 戳記失效。請審該 diff 並**重簽**。

- **新 body sha256**（實跑 `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`）：
  `76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433`
- 逐字格式：`RECONCILE-STAMP: <family> APPROVED 2026-09-14 sha256:76006a764a8c1d12437cc71c8ed38bbdaddbc65637a523cd52792d2ee3ef9433 task:20260911-SPLITUNIFY-B9-STAMP-R4`
- 🔴 舊戳記行請**保留**。

## 修補內容（`§P Task 9.1` 兩處）
| # | 原字面（已作廢） | 現字面 | 依據 |
|---|---|---|---|
| ① | 「producer → summary → `metadata.split_unify` **三層**完整記帳」 | 「producer → `EventSplitPlan.summary` **兩層**」；`metadata` 層與終端可見性同歸 §N 之 `SU-RESID-9A-UI` | v13 之 O1 已把 metadata 移入殘留、§V 已同步，**只有 §P 沒改** |
| ② | 「多 symbol 時**逐 symbol 相加**」 | 「多 symbol 時**原樣傳遞、不得相加**」 | R18 三家撞題並實跑證實照字面相加會按 symbol 放大；TODO／實作／測試皆已定案 |

## 審查標的（🔴 輸入邊界）
- **本輪 diff**：`git show 8327d60c -- docs/SPLITUNIFY_SPEC.D-002.md`
- **current block**：`docs/SPLITUNIFY_SPEC.D-002.md` 之 `§P Task 9.1` 前三個 bullet（目標／返回形狀／跨邊界傳遞）
- 🔴 **不在審查範圍**：`HISTORY-BEGIN..END`、「## 沿革與追溯索引」節；`Task 9.2`–`9.5` 之設計；register 之 mutation 欄對應。
- 🔴 **不得重開**：r17 共識決、r18／r19 已閉合之十三條。

## 本 brief 前提（逐條標；請優先攻 assumed）

fact-verified: 兩處舊字面已無殘留 → `grep -n "逐 symbol 相加\|三層完整記帳" docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 排除「原寫／原文／v18」註記行後**零命中**。派工後預期值: 不變（唯讀審查）。
fact-verified: 格式閘過 → `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0。
fact-verified: r18 十三條全閉合 → r19 三家交件之 `CLOSED:` 欄合計十三個 ID，逐一對應 r18 附錄。
fact-verified: mutation 表與 register 未動 → 本輪 diff 只觸及 `§P Task 9.1` 三個 bullet 與沿革段。

assumed: `§P` 與 `§V` 現在**完全一致**，不再有第三處互斥。**我的否證觀測（已先跑）**：對兩處舊字面做 grep 已零命中。**我沒查**：`§P Task 9.1` 與 `§V Task 9.1` **逐句對讀**——除 metadata 與相加兩點外，是否還有別的語意差（例如「返回形狀」之描述、`{}` vs `None` 之措辭）。← **請直接攻這條**，逐句對讀後給結論。

assumed: 此修補**不影響** `Task 9.2`–`9.5` 之任何條文。**我的否證觀測（已先跑）**：diff 只在 `§P Task 9.1` 範圍內。**我沒查**：`Task 9.2` 之條文是否曾以「承 9.1 之三層」之類措辭**引用**被改掉的字面。← **請直接攻這條**。

## 必答（逐條 verdict；成對，不得只答一半）
1. **(1a)** 對 body `76006a76…`：`APPROVED` 還是 `REJECTED`？
   **(1b)** 若 `REJECTED`，逐條列阻擋項且每條須能在**一次修訂**內關閉。
2. **(2a)** `§P Task 9.1` 與 `§V Task 9.1` 逐句對讀，是否還有第三處互斥？
   **(2b)** 若有，逐處列出並給可直接貼入的修正字面；若無，貼出你逐句對讀的方式。
3. **(3a)** `Task 9.2`–`9.5` 是否有條文引用了被改掉的舊字面？
   **(3b)** 若有，逐處列出；若無，說明你掃了哪些範圍。
4. **(4a)** 可以進 `Task 9.2`（批次 `B9B`＝`9.2`＋`9.2a`）了嗎？
   **(4b)** 若可以，說明你檢查了什麼；若不可以，列**最小**閉合集合。

## 🔴 本輪格式硬約束
1. **P0／P1 之 `**碼證**` 欄必含兩行 token**：`CODE-ANCHOR: <path>:<line>` 與 `MUTATION: <可執行的破壞>`。
2. **anchor 不得落在 `HISTORY-BEGIN..END` 或「## 沿革與追溯索引」區**。
3. **欄位內容必須與標籤同一行**（逐行判）。
4. **零 findings 時**須用零 findings sentinel 形態，且含**斷言**與**碼證**。
5. 收尾行：`VERDICT: proceed|blocked`；`CLOSED:` **空值或 finding ID 清單**，🔴 **不得填日期**，🔴 **只准填本家自己提出過的 ID**。

## 產出
canonical 四欄 findings + **Verdict** ＋ 戳記（append 到 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `## 戳記` 區）。
**禁改碼、禁改 SPEC 正文、禁改 TODO**（戳記 append 除外）。收尾清 /tmp workdir（保留 claude-501）。
