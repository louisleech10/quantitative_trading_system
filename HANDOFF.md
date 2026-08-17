# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。
> 使用者 2026-08-14：「這是交接要做的事情，有需要寫這幾百行流水帳？
> 而且後面上百行治理 epic 相關的，為何還寫在裡面？」
> ⇒ 治理 epic 之敘事／殘留清單／操作紀律全部移入 `docs/ROADMAP_DETAIL.md`。

---

## ✔ IC 健檢 epic 已收工（2026-08-17）——接手第一件事＝開缺口票 GAP-1

epic 全鏈路完結：偵察（四方）→SPEC/TODO（凍結＋戳記）→六批實作（逐批 A/B Gate 零新增紅、
逐批 push）→M1–M7 mutation 全紅過→三家 code review（8 findings：5 修 2 具名殘留 1 契約回應）
→原提出方複驗全 CLOSED→三家 RECONCILE-STAMP（`handoffs/reconcile/20260817-ichc-x-review-r6/`）
→債全清。中途一次斷路器委員裁決（R5 事件×fallback＝A′ 案）。
**→ 下一步＝`docs/IC_QUANT_GAP_REGISTRY.md` 六票排程，首位 GAP-1（DSR/PBO/MinBTL）**，
開工走完整管線（Claude 起草 SPEC→三家審）。
具名殘留：治理段5 有 4 條 f50f9d0f 遺留紅（舊 pre-push 契約測試，屬治理線不擴建，未修）；
產品套件 14 條既有紅（A/B 隔離證明非 ICHC 引入）；wiring 規則二為窄版（registry #6 升級路徑）。
待手動清：`handoffs/reconcile/*.stale-*` 兩目錄＋`handoffs/run_receipts/20260817T000000Z-*.log`
＋`scripts/ichc_t{2,3}_*.py` 三支臨時診斷腳本（rm 被沙箱擋）。

治理＝**留現狀、不再擴建**。已掛的機制繼續運作，不需要動。

## 回主線後的測試紀律（使用者定「邊走邊建立」）

新測試優先選這三類——它們的紅綠**使用者可在不讀程式碼的前提下採信**：
**性質檢驗**（`t` 不得依賴 `t+1`、跨 symbol 換料不變、合併前後守恆）／
**真實 kline**／**與第三方實作對照**（`scipy`／`statsmodels`）。

⚠️ **凍結 golden 比對能不用就不用**：基準與測試兩側皆由本 agent 產出，互相量測是循環論證。
既有失效基準與疑似孤兒**一律不大清**，碰到才處理（`scripts/golden_staleness_check.sh`
的歸屬判定已實測有兩個 bug，其輸出**不得用於刪檔**）。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l` |
| 治理票狀態 | `docs/GOV_TICKET_SOT.md`（唯一來源） |
| 哪些檢查真的掛著 | `docs/GOV_ACTIVE_MECHANISMS.md` §二（機械生成） |
| 治理 epic 的一切 | `docs/ROADMAP_DETAIL.md` |

**髒檔應為 5 個且全為規則禁止提交項或待處置**：`.claude/gate/*.log`×2、
`scripts/governance_families.json`（`R-15`）、`docs/GOVB0_FRICTION_AMENDMENTS.md`、
`handoffs/run_receipts/20260814T095050Z-fracdiff-maxlag-postfix-compare.log`（未追蹤 receipt，待處置）。

🔴 **push 需使用者明示**。`pre-push` 已改秒級快閘 `gov_check --fast`（2026-08-14 使用者裁定，
commit f50f9d0f）；全套治理 pytest 改為手動關卡——動過 `scripts/`／`tests/governance/` 者
收 epic 前自跑 `bash scripts/gov_check.sh --no-probe`（丟背景）。

## ⚠ 對任何工作都適用的操作紀律

> 完整地雷清單在 `CLAUDE.md` 的 Gotchas 節，**本檔不重述**。只列最常咬人的：

- 🔴 **`git add` 一律逐檔列出**，禁目錄形式、禁 `$(...)` 展開（曾兩次掃進明令不得提交的檔）
- 🔴 **rc 禁經 pipe**：`cmd | tail` 讀到的是 `tail` 的 rc。一律 `cmd > file; rc=$?`
- 🔴 **commit 訊息用 `-F` 寫檔**，檔放 `.claude/tmp/`（放專案外每次多 12–17 秒）；
  訊息中的 operational claim 需 `VERIFY:<receipt>` 背書，**commit 零豁免**
- 🔴 **改檔用 Edit／Write**，禁 `sed -i`／heredoc／`printf >> 檔`
- 🔴 **說明檔同步是工作項目的最後一個 commit**（同一 commit 既動 `scripts/` 又動
  `白話說明/` 必判過期）
- 🔴 **`scripts/fact_keys.json` 一律用 Edit 改**，`jq` 只准拿來讀（會整檔重排）；
  改完跑 `bash scripts/regen_factkey_fixtures.sh`
