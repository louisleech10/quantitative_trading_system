
# 諮詢：`audit.log` 如何在不破壞任何消費者的前提下瘦身

brief-kind: consult

## 委員範本（**全文照做**）

`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` — **請完整讀取並照做**，
包含 canonical finding heading 格式（`^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$`，本輪用 `R13`）、
§0 挑戰前提、Verdict 段。本 brief 只**收斂本輪範圍**，不取代該範本的任何格式要求。
若結論為零 findings，請明寫一行 `FINDINGS_COUNT: 0`。

## 背景與已發生的事故

`audit.log` 已 **34,479 行**，`gate_check.sh` 每次都要讀 ⇒
`test_gate_check_latency_under_100ms` 紅（冷啟約 287ms／門檻 100ms）。
🔴 **非任何一批實作造成**——pre-Phase2 snapshot 同環境亦約 203ms。

**主委已犯的錯（請以此為前車之鑑）**：
主委寫了 `scripts/audit_archive_legacy.sh`，把「非 debt 白名單」的 33,716 行整批封存，
只留 763 行。三項自檢（行數守恆／`debt_ledger` 可跑／round 數不變）**全過**，latency 也轉綠。

**但下一次派工立刻失敗**：

```
RECONCILE-STAMP FAIL: … 未獲全數委員核可:
  · codex/composer/grok: provenance 不符 —
    ERROR: 戳記 task:GOVB0-R9-STAMP 無 committee_dispatch 審計事件（非 legacy allowlist 須有派工留痕）
```

根因：戳記 provenance 檢查需要 `committee_dispatch` 事件，
而它**不在** debt 白名單（白名單只有 `committee_round_open`／`committee_family_result`／
`debt_abandon`／`committee_debt_clear`），因此被封存掉。

⇒ **主委只驗了 `debt_ledger` 一個消費者就宣稱安全**，屬「驗了 A 就當作 B 也成立」的推論失誤。
**已還原**（`audit.log` 回到 34,479 行，自備份 `audit.log.bak-20260805T111750Z`）。

## §0 前提宣告

**已查證**（主委實跑）：

- fact-verified: `audit.log` 現為 **34,479 行**；已自備份還原，與封存前一致。
- fact-verified: 讀 `audit.log` 的程式共 **20 個**（`grep -rln` 於 `scripts/`），
  含 `verify_task_provenance.py`／`verification_claim_check.py`／`verify_audit_chain.py`／
  `gate.sh`／`gate_check.sh`／`reconcile_build.sh`／`run_with_receipt.py`／`_debt_ledger_core.py` 等。
- fact-verified: 系統**已有** `cutoff_ts` 機制（`scripts/audit_events.json` 現值 `2026-07-23T00:00:00Z`，
  語意為「cutoff 之前的事件視為 legacy」），但它只改變 **debt 語意判定**，**不減少讀檔量**。
- fact-verified: debt 白名單事件的 `sequence` 為自身獨立編號（實測 1,2,3,4,5…），
  故封存非白名單行**不會**造成 debt 缺號——這部分主委的判斷是對的，錯在沒查其他消費者。

**假設**（請攻）：

- assumed: latency 門檻 100ms 本身合理、不該放寬。**主委未查該門檻的出處與理由。**
- assumed: 20 個消費者中，多數只在**特定 task_id／receipt_id／round_id** 上做點查詢，
  而非需要全量歷史。**未逐一確認。**

## 你要回答的

| # | 問題 |
|---|---|
| 1 | **窮舉** 20 個消費者各自需要 `audit.log` 的**哪些事件型別**與**多久的歷史**。哪些只做點查詢？哪些需要全量？ |
| 2 | 在不破壞任何消費者的前提下，**可行的瘦身方案有哪些**？請比較：(a) 依事件型別分流 (b) 依時間分流＋消費者改讀「現役＋封存」兩檔 (c) 建索引，檔案不動 (d) 只讓 `gate_check.sh` 熱路徑改為不讀全檔 (e) 你提的其他 |
| 3 | 各方案的**風險**與**是否需要改動消費者**。主委傾向「改動愈少愈好」，但**不接受靠紀律維持**（例如「以後記得別讀全檔」）。 |
| 4 | 使用者已定死「**修正只考慮以後，不溯及既往；不管舊文件與舊資料格式，除非那些檔案真的有必要未來使用**」。⇒ 依此原則，**哪些歷史事件是「未來仍必須被機器讀」的**？請具名。 |
| 5 | 是否有**現在就能做、風險最低**的一步（讓 B3 推得上去），與**完整解**（線 C）分開？ |

## 🔴 不受理範圍

1. **放寬 latency 門檻**——使用者定死禁用統計手法充當達標；除非你能證明 100ms 這個值本身無依據。
2. 重開第 0 批 SPEC／TODO 的設計裁決。
3. 線 C 完整版的設計細節（本輪只問「怎麼安全瘦身」與「先做哪一步」）。

## 硬性要求

1. **禁改碼**。只交分析與建議。
2. **rc 一律直接取，禁經 pipe**。
3. 禁 `git checkout`／`git restore`／`git clean`；不要 commit、不要 push；**禁碰 `data_cache/`**。
4. 每個結論須附**實跑命令與輸出**，不得只憑讀碼推論。

## 產出

第 1 題的完整消費者對照表（程式 → 需要的事件型別 → 需要的歷史範圍 → 是點查詢或全量）、
第 2–5 題的逐題回答、以及你**建議的下一步**（含理由與風險）。
收尾清 /tmp workdir（保留 claude-501）。
