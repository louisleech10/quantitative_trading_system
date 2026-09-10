# SPLITUNIFY — SPEC v3 ＋ TODO v3 adversarial 審（R3，收斂輪）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R3
findings-round: R3

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0（挑戰前提）與 canonical finding
四欄格式**全文照做**；findings 用 `## <FAMILY>-R3-P<0-3>-<NN>`，結尾附 **Verdict**。
審查對象＝`docs/SPLITUNIFY_SPEC.md`（sha256 `d851e56dc1bf…`）與
`docs/SPLITUNIFY_TODO.md`（sha256 `a9ec9e1559a8…`），commit `7f040c93`。
**禁改碼**；碼證以檔案:行號指名。

## 這是什麼——本輪是**收斂輪**

R1 收斂 13 群集、R2 收斂 11 群集（含三個 P0），**全部採納並已改進 v3**。
本輪的問題不是「還有沒有可以更好的地方」，而是——

> **v3 有沒有還沒閉合的 P0／P1？如果沒有，就放行 B1。**

⇒ 請優先判定「可否進 B1」。P2／P3 等級的建議請照列，但**明確標為不擋 B1**。
主委依 `feedback_95_percent_then_record`：95% 解法就收，殘留具名記錄，不當阻擋。

## R2 → v3 的實質變更（逐條，供你核對是否真的閉合）

| R2 群集 | 嚴重度 | v3 落點 |
|---|---|---|
| D1 C-0 未閉合（codex P0） | P0 | C-0 決議②改寫：pipeline **接受（選填）** boundary；**裁定事件掃描端恆走 event-study-only**，不新增 universe 供給路徑 ⇒ 殘留 `R-5` |
| D2 Task 3.3 自相矛盾（grok P0） | P0 | C-0 決議③(a)＋Task 3.3 要點 2：**刪除** `pipeline.py:728-734` 之三鍵；L3 與新 reason 共用新形狀；兩條 reason 皆加回歸 |
| D3 G-5 空殼（composer P0＋codex／grok／主委） | P0 | §G G-5 補四項逐一 oracle（fingerprint 指名首個 mismatch position／獨立 oracle 集合＋diff 輸出／兩端 endpoint 完整覆蓋／注入後必進 purged 且 mutation rc=1） |
| D4 study-only 無「非 OOS」標籤 | P1 | C-0 決議③(b)＋Task 3.3 要點 3：`estimand_scope="full_sample_not_oos"` |
| D5 前端不渲染 capability | P1 | C-0 決議③(c)＋Task 3.3 要點 4：必顯 `capability.split`／`reason`；`unavailable` 時禁顯示計數列；兩 reason 各一 vitest |
| D6 ms 導出未定義 | P1 | Task 2.1 要點 2 寫死導出式；新增 `-k ms_same_source`；`M-SU-11` 擴為 rows＋ms 同源 |
| D7 normalizer 拒收 ms | P1 | C-4 明寫「本票時鐘一律 epoch **毫秒**，**禁**呼叫 `_normalize_ic_time_index`」 |
| D8 raise 欄位不在簽名上 | P1 | C-5：檢查移到呼叫端；C-4 簽名補 `bucket_ms` |
| D9 既有紅清單協議 | P1 | Task 1.3 補 pipefail／`pytest_rc` 捕獲＋維護協議；Task 3.1 驗收 (B) 由集合相等改**方向性（只准變短）** |
| D10 SPEC↔TODO 不一致 | P2 | SPEC Task 3.1 驗收補 (D) 呼叫點釘 0 |
| D11 `single_symbol` 恆亮 | P2 | Task 2.2 要點 6 聲明為預期、禁清空 `degraded` |
| codex Q8 批次 | — | B2 拆為 B2a／B2b／B2c，各自 gate 與 review |

## 🔴 必答（每題給明確立場＋碼證）

1. **可否進 B1**：直接回「可以」或「不可以＋還沒閉合的那一條 ID」。**不得只列改進建議。**
2. **D1 的裁定是否可接受**：事件掃描端恆走 event-study-only、`R-5` 具名殘留。
   這是「95% 解法就收」還是「把主目標偷偷降級」？請正面打。
   （使用者的主目標是「不要在同一次 UAT 看到兩個互相矛盾的驗證段數字」——
   裁定後使用者只會在 IC 報告看到「驗證段」，事件掃描端明講「未執行切分」。夠不夠？）
3. **D2 的刪三鍵會不會打破既有測試或前端**：`pipeline.py:728-734`、
   `EventTablesPanel.tsx:352`、`tests/momentum/event_samples/test_gap3_split_blocked.py`。
   請指名會紅的既有測試，並說明 v3 有沒有把它們列進修改範圍。
4. **G-5 四項 oracle 現在夠不夠可執行**：逐項回「夠／不夠＋缺什麼」。
5. **v3 有沒有引入新的自相矛盾**（R2 抓到兩條：D7 normalizer、D8 簽名）。
   請以同樣的方式掃一遍 v3 的**介面可執行性**：每個「須 raise」的檢查，
   它要檢查的東西是不是真的在該函式的簽名上？每個「復用既有函式」，
   那個函式是不是真的接受我們要餵的輸入？
6. **批次拆分後的依賴鏈是否正確**：B2a→B2b→B2c→B3，B2b 需要 B2a 的什麼？
   B2c 需要 B2b 的什麼？有沒有 Task 被放錯批？
7. **殘留清單是否誠實**：`R-1`～`R-5` 與 `SU-RESID-1` 六條，理由類別只准
   blocked-by／user-ruling／needs-research。有沒有哪一條其實是「偷懶」？

## 停輪條件

① 必答 1 有明確二值立場；② 必答 3／5 有具體檔案:行號；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭），主委依較嚴版本收斂並具名殘留。
④ 禁以「三家零 finding」當停輪理由——零 finding 須走 sentinel 契約。
⑤ 🔴 **本輪不接受「還可以更好」型的 P0/P1**——標 P0/P1 者須說明
「不改會怎麼在 B1–B4 具體失敗」，否則請標 P2/P3。

## 本 brief 之前提（逐條標）

fact-verified: R2 三家 verdict 一致「不可直接進 B1」，17 條全數採納 → `handoffs/reconcile/20260911-splitunify-x-review-r2/synth.md`。

fact-verified: `_normalize_ic_time_index` 拒收毫秒 → `momentum/Analysis/ic_filter_orchestrator.py:269-271` 明文 raise「looks like milliseconds, expected epoch seconds」（主委實跑複驗）。

fact-verified: `run_event_study_only` 目前寫死三鍵為 0 → `momentum/Analysis/event_samples/pipeline.py:728-734`。

assumed: 本輪之後不需要 R4——收斂趨勢（13 → 11 → ?）足以在 R3 收束
← 否證觀測：R3 又出現三個以上互相獨立的 P0。／我跑了：**沒跑**，這是判斷不是事實。
若你認為需要 R4，請在 Verdict 明說並給理由。

assumed: 刪除 `n_train`／`n_test`／`n_purged` 三鍵不會打破 `test_gap3_split_blocked.py`
← 否證觀測：該測試斷言 summary 含這三鍵。／我跑了：**沒跑**。請正面打（必答 3）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 是否有其他 caller 讀 `summary["n_test"]`（事件掃描路徑） | 刪鍵後該 caller KeyError | cost |
| `EventTablesPanel.test.tsx` 是否已存在 | Task 3.3 之 vitest nodeid 不存在 | cost |
| `tables.py:598-599` 之 `estimand_note` 模式是否適用於 `common` 區塊 | `estimand_scope` 放錯層級 | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth。
- 不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」（`tests/momentum/Analysis` 20 條，非本票造成）。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（第一句必須是「可進 B1」或「不可進 B1：<ID>」）。
