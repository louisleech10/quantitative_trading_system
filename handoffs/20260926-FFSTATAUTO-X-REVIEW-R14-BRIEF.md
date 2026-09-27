# FF-STAT SPEC v33 審查 r14：r13 閉合複核＋v33 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R14

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R14-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r13 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R14-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff 9c37a345 e376b590 -- docs/FFSTAT_SPEC.md`：v33 版本註記、§A 兩條新 FACT-RECEIPT、§C（L1 遮罩點、第④類、死欄純函式、公開值不變量收窄）、§G（①②③⑦）、Task 2.1 驗證首句、Task 2.4（量測 finite guard、覆蓋範圍、邊界①′）、Task 2.3（②第④類驗收、⑦欄集合改寫）、§V（⑦²⁰–⑦²²）、§N（12h §G⑦ blocked-by）。
- r13 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r13/synth.md`（含部分採納與駁回之理由、主委自審四條、裁決塊修正紀錄）。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審，含每欄開頭多出 NaN 之輸出變更。v33 新增「欄集合可能因死欄判定改變、逐欄列原因交使用者核可」，屬待使用者核可之輸出變更。
- v32 未改動之條文、r12 以前已閉合者不在本輪範圍。

## 本 brief 前提
fact-verified: 所有遮罩（L1 遮罩、NaN 傳遞之延後、①④類遮罩、無起始日校準列）只延長各欄開頭之 NaN 段 → 依 §C 各條定義推得（L1 遮罩為 `[origin, origin+K)`；①④類皆以「輸入首個有效值」為界；校準列為各欄最早 N 個有效值）
assumed: 死欄判定之 NaN 率改自各欄首個有限值起算後，其判定與遮罩長度無關（除遮罩所吃掉之原開頭段內之間歇 NaN 外）。
→ 否證觀測：存在一種遮罩或計算步驟，使某欄在首個有限值之後出現「因遮罩才產生」之 NaN（非開頭段），而改變 NaN 率。／我跑了：無（只由條文推得）。
assumed: M_tf＝K_max_tf＋F_max_tf 使 A 於 B 之全部比較列皆已收斂，且「刪 L1 遮罩」mutant 下仍保證 A、B 於 B 開頭段有可偵測之差。
→ 否證觀測：於真實 BTC 1h 切片，存在某欄於 B 首個有限值起之比較列上，A 之值距「自更早起點計算之值」超出 0.005 判準；或刪 L1 遮罩後 A、B 全部比較列仍在容差內。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v32 未改之條文；IC-First 管線合一票之設計。
- **我沒查**：①第④類「只遮開頭段、不改其後間歇 NaN 處理」之實作可行性（trend consensus 之 `skipna` 聚合如何同時滿足）；②死欄純函式之「有效樣本數只計穩定後之值」與 L7 dead feature drop 現行 `min_valid_samples` 語意是否一致；③§G⑦ 12h 子集設定之選法是否可機械決定（避免人為挑選使對證變空）；④Task 2.4 覆蓋腳本「類別集合＝ConfigManager 指標類別模型全集」之全集如何機械取得。

## 必答（成對）
1. **(1a)** 本家 r13 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／駁回者，判其理由是否成立）。
2. **(2a)** v33 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
3. **(3a)** 兩條 assumed 各判成立或不成立？**(3b)** 碼證或實跑數字。
4. **(4a)** 「我沒查」①–④ 各有無命中？**(4b)** 碼證。
5. **(5a)** 本版可否定案（`VERDICT: proceed`）？**(5b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；嚴禁新增分鐘／小時級之生成期檢查（驗收測試不在此限）。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設（使用者：之後要建台股、美股、期貨）。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
