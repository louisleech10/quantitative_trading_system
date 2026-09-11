# VERDICTGATE TODO v2 閉合確認（R10）

brief-kind: review
task-id: 20260911-VERDICTGATE-X-REVIEW-R10
findings-round: R10

🔴 **這是審查（review），不是實作。AGENTS.md Rule 12 只約束「動工」，對審查任務不適用。禁改碼、禁動 tracked 檔（含 git checkout／stash）。**

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0 與 canonical finding 四欄格式；findings 用 `## <FAMILY>-R10-P<0-3>-<NN>`。產出**末段**必含機械裁決塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>        （blocked 時必填；只列你自己的 P0/P1）
CLOSED: <ID,ID>            （你在 R9 提過、TODO v2 已閉合者；只列你自己重驗過的）
```

## 審查對象
`docs/VERDICTGATE_TODO.md` **v2** 對照 `docs/VERDICTGATE_SPEC.md` v9。R9 收斂 `handoffs/reconcile/20260911-verdictgate-x-review-r9/synth.md`（Q1–Q5 全採納；新殘留 E-7）。

## 🔴 必答
1. 你 R9 的每一條在 v2 是否閉合？逐條重驗（Q1 簽名是否真的「冷啟動可寫」；Q2 §B 依賴；Q3 §0 commit 規則；Q4 hook 寫入時子集；Q5 E-3／E-5／E-6 研究問題）。
2. **E-7**（治理腳本 commit 不受 Phase 3 保護，本票自身即實例）：理由類別寫 user-ruling（SPEC 停輪裁定）——成立嗎？若你認為這是本票的**核心目標漏洞**（「不論誰實作皆觸發」對治理票不觸發），請明說並給立場：擴 scope 到 `scripts/` 的代價（每個治理小修都要領票）是否可接受？主委立場：不重開 SPEC，留給下一張治理票。
3. **Q4 hook 寫入時子集**：對非佔位列驗 quote20——主委填 synth 時常先寫群集列、後補引用；「非佔位列即驗」會不會讓每次中途存檔都紅？給立場：是否該以「該列含處置 token」作為「該列已完成」的判準再驗 quote20？
4. **可否 FROZEN**？

## 停輪條件
①必答 1–4 皆有立場；②禁以「三家零 finding」當停輪；③P0/P1 須說明「不改會怎麼在實作批具體失敗」；④`CLOSED:` 只列重驗過的。

## 前提
fact-verified: `bash scripts/template_check.sh todo docs/VERDICTGATE_TODO.md` rc=0（v2，主委 2026-09-11）。
fact-verified: `spec_xref_check.sh --synth` R9 synth vs TODO v2 PASS（主委實跑；R9 synth 首版之簡寫簽名被 hook 當場擋下，改成與 TODO 逐字一致）。
fact-verified: SPEC v9 三家 R1–R8 全部 ID 已 `CLOSED:`（codex R8 四條於 R9 閉合）。
assumed: 「非佔位列即驗 quote20」不會造成填寫中誤擋 ⇒ 否證觀測：主委本輪填 R9 synth 是一次寫完整列，沒有中途存檔樣本。／我跑了：**沒跑**。請必答 3 正面打。

## ⚠️ 前置
禁改碼；禁跑 `tests/governance` 全套；禁與其他委員平行跑重測試。收尾清 /tmp workdir（保留 claude-501）。
