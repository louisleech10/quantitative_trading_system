# FF-STAT SPEC v35 審查 r16：r15 閉合複核＋v35 改動

brief-kind: review
task-id: 20260926-FFSTATAUTO-X-REVIEW-R16

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading **只准** `## <FAMILY>-R16-P<0-3>-<NN>`（ID 後不得附標題文字）；每條 `**類別**:`；P0／P1 之碼證含兩行封閉字面 `CODE-ANCHOR: <repo-relative-path>:<line>`（路徑不得加反引號）與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只准列本家族前綴之 r15 ID，逐一列出經你複核確認閉合者；不得寫 `none` 等非 ID 字面）。零 finding 用 `## <FAMILY>-R16-P3-00` sentinel。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱。
🔴 **PreToolUse hook 擋下你的指令時，停下並於 FAILURES_SEEN 記錄，不得改寫指令形式（如換直譯器路徑）繞過**。
🔴 **磁碟與記憶體**：本機 8 GB；不跑全設定 FF run；探針用真實 `data_cache/feature_klines/kline_cache.h5` 之小切片（禁合成 fixture）；暫存結束前刪除（被環境拒絕時照實記錄，不得換寫法）。

## 審查標的
- `git diff f12e842e bf591b73 -- docs/FFSTAT_SPEC.md`：v35 版本註記、Task 2.3 ⑦（欄集合與 delta 之逐位元組框架、核可紀錄之誠實邊界、置換不變負例）、§G⑦（12h 選擇器實例語法、每步移除全部最大 K 實例、無 recursive 殘留即 blocked）。
- r15 收斂：`handoffs/reconcile/20260926-ffstatauto-x-review-r15/synth.md`（CODEX-R14-P1-01 維持「SPEC 定案後、實作派工前同步 manifest」，兩家 r15 已判理由成立，本輪不再議）。
- **使用者裁定（不重議）**：同 r13 brief 之 R1–R7（`handoffs/20260927-ffstat-b4-redesign-rulings.md`）；使用者已同意 v32 送審。
- v34 以前已閉合、且 v35 未改動之條文不在本輪範圍。
## 本 brief 前提
fact-verified: L7 `find_dead_columns` 以 `notna().sum() < min_valid_samples` 與 `nunique(dropna=True) < 2` 判定、不計 NaN 率 → `sed -n 44,90p momentum/FeatureEngineering/utils/dead_feature_filter.py`
assumed: §G⑦ 12h 固定選擇器必終止，且終止時子集非空（至少保留一個 recursive 指標，使「係數改 1.0」mutant 在 12h 子集上仍可偵測）。
→ 否證觀測：以真實 12h 1,696 根與預設全設定執行選擇器規則，移除至只剩非 recursive 指標或空集才滿足容量條件。／我跑了：無。
assumed: v35 之逐位元組框架使語意相同之 delta 必得相同 sha256，且不同 delta 不會因框架而碰撞（欄名含非 ASCII 或 `,`、`:`、`"` 時亦然）。
→ 否證觀測：兩個語意相同之 delta 依 v35 規則序列化後位元組不同；或兩個不同 delta 序列化後位元組相同。／我跑了：無。

## 攻擊面
- **已排除**：使用者裁定 R1–R7 本身；v34 以前已閉合且 v35 未改之條文；IC-First 管線合一票之設計；CODEX-R14-P1-01 之延後理由（r15 兩家已判成立）。
- **我沒查**：①選擇器「每步 A run 實測 F_max_tf」之總步數上限與耗時（12h 1,696 根、預設全設定）；②多參數組合實例之「最大週期」取法對 MACD 以外之組合型指標（STOCH、ADOSC 等）是否一義；③`reasons` 值集合是否封閉於 `nan_rate_rule`｜`stable_samples_below_min`（出現第三種原因時之處置）。

## 必答（成對）
1. **(1a)** 本家 r15 各條是否閉合？**(1b)** 逐條以原反例重跑或對條文逐字核對之結果（部分採納／延後者，判其理由是否成立）。
2. **(2a)** v35 有無新缺陷？**(2b)** 可重現反例（真實 kline 切片之輸入或操作序列）。
3. **(3a)** 兩條 assumed 各判成立或不成立？**(3b)** 碼證或實跑數字。
4. **(4a)** 「我沒查」①–③ 各有無命中？**(4b)** 碼證。
5. **(5a)** 本版可否定案（`VERDICT: proceed`）？**(5b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 使用者定死「任何每次都會跑的檢查，單次必須秒級」；嚴禁新增分鐘／小時級之生成期檢查（驗收測試不在此限）。
2. 威脅模型＝**意外漂移**；每條 P0／P1 須附可重現之輸入或操作序列。
3. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由。
4. 研究設計不得寫死 24h／UTC／加密貨幣特有假設（使用者：之後要建台股、美股、期貨）。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api scripts tests docs templates config` 與開跑前相同。完成訊號逐字 `STATUS: DONE`。
