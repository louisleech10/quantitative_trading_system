# VERDICTGATE TODO 收斂戳記輪（序列化，每家一次派工）

brief-kind: stamp
task-id: 20260911-VERDICTGATE-X-STAMP-R13
findings-round: R13
stamp-target: handoffs/reconcile/20260911-verdictgate-x-review-r10/synth.md

（序列化：codex＝`-STAMP-R11`、composer＝`-STAMP-R12`、grok＝`-STAMP-R13`；戳記行之 `task:` 寫**你被派的 task-id**。）

## 你在核可什麼

`docs/VERDICTGATE_TODO.md` **v3** 是否可 FROZEN 進實作。依據鏈：SPEC v9（R1–R8，三家全部 ID 已 `CLOSED:`）→ TODO v1（R9 三家 8 條，Q1–Q5 全採納）→ TODO v2（R10：composer／grok `proceed`；codex 3 條精確度修正 P1–P3 全採納）→ TODO v3。stamp-target 為 **R10 收斂檔**，其群集段記錄 P1–P3 之處置與 E-7 三家立場。

🔴 **grok**：你 R10 已 `proceed`；本輪只核 synth 忠實性。codex（R11）與 composer（R12）已 APPROVED（檔內既有兩行戳記保留，勿抄其雜湊）。

## 🔴 交件形態（缺這段整輪會銷不了帳）

無論結論為何，**交件檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R13-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
末段必含機械塊：
```
VERDICT: proceed|blocked
BLOCKED-BY: <ID,ID>
CLOSED: <ID,ID>
```
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。

## 你要做的事（只有這件）

1. 讀 `handoffs/reconcile/20260911-verdictgate-x-review-r10/synth.md` 全文，核對它是否**忠實**收斂了你自己 R10 的產出（`handoffs/20260911-verdictgate-x-review-r10-<你的家族>.md`）：你的每一條 finding 是否被某群集**實質引用**、立場有沒有被改寫或降級；並抽驗 TODO v3 對應段落是否真的照處置改了（主委已用 `spec_xref_check --synth` 機械對證「處置欄概念皆見於 TODO」——那只驗存在，**語意由你驗**）。
2. 在 stamp-target 的 `## 戳記` 標題之下 append **一行**：
   ```
   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<hash> task:<task-id>
   ```
   `<hash>` ＝ `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-verdictgate-x-review-r10/synth.md` 之輸出（**自己算**，不得抄本 brief 或檔內任何既有雜湊）。
   若不核可 ⇒ `RECONCILE-STAMP: <family> REJECTED <date> sha256:<hash> task:<task-id> — <一句理由>`，並在交件檔寫 canonical finding。
3. 交件檔（`--output` 指定路徑）：寫出你算到的 body-hash、你 append 的那一行、逐條核對結果。

## ⚠️ 紅線

- **只 append 戳記行，不改 synth 其他任何位元組**（append 前後 `reconcile_body_hash.sh` 須不變）。
- **禁改碼、禁改 `docs/VERDICTGATE_*.md`**。不得跑 `pytest tests/governance`（小時級）。
- 本輪**序列化**：你是唯一在寫這個檔的委員；完成後主委才派下一家。
- 本輪**不是**重審 TODO——那已由 R9／R10 做完。本輪只問「synth 是否忠實記錄了收斂」＋（codex）R10 三條是否閉合。

## 本 brief 之前提（逐條標）

fact-verified: `bash scripts/template_check.sh todo docs/VERDICTGATE_TODO.md` rc=0（v3，主委 2026-09-11）。
fact-verified: `spec_xref_check.sh --synth` R10 synth vs TODO v3 → PASS（處置欄 8 個概念皆見於 TODO；主委實跑）。
fact-verified: R10 round `8e12917e` 已 `debt_clear`；`## 戳記` 區為主委於清債後 append（body-hash 不含該區）。
assumed: TODO v3 對 P1–P3 之修法與 codex 原意一致 ← 否證觀測：codex 在 R10 對 Q4 給的立場是「以有效 disposition token 判定列已完成後才驗 quote20」，v3 已逐字採用；若 codex 認為 `strict_defer` 參數化仍不足，蓋 REJECTED。／我跑了：**沒跑**（語意須原提出方驗）。

## 驗收命令

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260911-verdictgate-x-review-r10/synth.md
bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260911-verdictgate-x-review-r10/synth.md
```

## 產出

交件檔＋synth 一行戳記。收尾清 /tmp workdir（保留 claude-501）。
