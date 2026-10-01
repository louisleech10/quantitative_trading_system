# ICPOSTLEAK 實作第 1 批 審碼 r3（SPEC v5 §N 改寫閉合；收批確認）

brief-kind: review
task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R3

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R3-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R3-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只列本家族前綴之 r2 ID）。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；本輪標的為文件一條，**不需重跑數值探針**；如需核對數字，只讀收據 JSON。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」。殘留之「為何現在不做」只准 `blocked-by`／`user-ruling`／`needs-research` 三值。

## 審查標的
- r2 收斂檔 `handoffs/reconcile/20261001-icpostleak-b1-review-r2/synth.md`（處置：殘留維持 needs-research、理由附數字與具名待研究項、列入全票細項排序諮詢；主委原立場撤回；blocked-by 不採之理由）。
- commit `4733b743`（`git show 4733b743 -- docs/ICPOSTLEAK_SPEC.md`）：SPEC v5 版本頭＋§N 殘留第一條。

## 主委事實
1. §N 該條所引數字逐一取自 `handoffs/run_receipts/20261002-icpostleak-branch-diff.json`、`handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json` 與 r2 三家交件（codex 10 倍／3 倍、grok 8.8 倍／3.3 倍）。
2. 生產程式碼自 `40f863d4` 起未再改動。

## 本 brief 前提
fact-verified: 主委事實 1、2。
assumed: §N 改寫後之文字未遺漏 r2 三家任一碼證所示之可達差異（特別是 Polars 臂 rank+zscore 絕對差 0.0975 於 float64 輸入、同 float32 輸入時 1.5e-5）。
→ 否證觀測：r2 任一家交件列出之生產可達差異未出現在 §N 該條或其待研究項之涵蓋內。／我跑了：逐家交件對讀，未機械比對。

## 攻擊面
- **已排除**：生產碼與測試（r1、r2 已閉合，`40f863d4` 後未改）。
- **我沒查**：§N 該條「rank 同值差屬 float32 輸入量化，不列缺陷」對未來非 float32 落盤之市場資料（台股、美股、期貨）是否仍成立。

## 必答（成對）
1. **(1a)** grok：GROK-R2-P2-01 是否閉合？codex、composer：§N 改寫是否忠實反映 r2 碼證？**(1b)** 逐句對照（引收據欄位）。
2. **(2a)** assumed 與「我沒查」是否成立？**(2b)** 依據。
3. **(3a)** 可否收第 1 批並收 ICPOSTLEAK 票（殘留兩條皆具名、皆有觸發與登記處）？**(3b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
3. `CLOSED:` 只准列**本家族前綴**之 ID。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend tests templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
