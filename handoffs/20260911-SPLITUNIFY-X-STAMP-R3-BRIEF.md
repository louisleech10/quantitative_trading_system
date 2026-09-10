# SPLITUNIFY consult synth 戳記輪（序列化；每家一次派工）

brief-kind: stamp
task-id: 20260911-SPLITUNIFY-X-STAMP-R3
findings-round: R3
stamp-target: handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md

（序列化三家：codex＝`-STAMP-R1`、composer＝`-STAMP-R2`、grok＝`-STAMP-R3`；
戳記行之 `task:` 寫**你被派的 task-id**。）

## 為什麼有這一輪

`CODEX-R1-P0-01`（`handoffs/20260911-splitunify-x-review-r1-codex.md`）實跑
`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
得 rc=1（缺 `## 戳記` 區段），據 `AGENTS.md` Rule 12 判 STAMP-BLOCKED。
**該 finding 成立，主委採納**：consult 共識未經委員核可就被寫進 SPEC，正是這條閘要擋的形態。
主委已補上 `## 戳記` 區段標題（**只加標題段，本體一位元組未動**），本輪補齊三家戳記。

## 🔴 交件形態（缺這段整輪會銷不了帳）

無論結論為何，**交件檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。

## 你要做的事（只有這件）

1. 讀 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` 全文，核對它是否**忠實**
   收斂了你自己那一輪的 consult 產出（`handoffs/20260910-splitunify-x-consult-r1-<你的家族>.md`）：
   你的立場有沒有被改寫、被降級、被靜默丟掉。**特別盯 Claude 自己寫的處置段**
   （ORCH「Claude 自身不享特權」）。
2. 在 stamp-target 的 `## 戳記` 標題之下 append **一行**：
   ```
   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<hash> task:<task-id>
   ```
   `<hash>` ＝ `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
   之輸出（**自己算**，不得抄本 brief）。
   若不核可 ⇒ `RECONCILE-STAMP: <family> REJECTED <date> sha256:<hash> task:<task-id> — <一句理由>`，
   並在你的交件檔寫 canonical finding。
3. 交件檔（`--output` 指定路徑）：寫出你算到的 body-hash、你 append 的那一行、核對結果。

## ⚠️ 紅線

- **只 append 戳記行，不改 synth 其他任何位元組**（append 前後 `reconcile_body_hash.sh` 須不變）。
- **禁改碼、禁改 `docs/SPLITUNIFY_*.md`**。不得跑 `pytest tests/governance`（小時級）。
- 本輪**序列化**：你是唯一在寫這個檔的委員；完成後主委才派下一家。
- 本輪**不是**重審 SPEC/TODO——那是 `20260911-SPLITUNIFY-X-REVIEW-*` 的事。本輪只問
  「synth 是否忠實記錄了 consult 共識」。

## 本 brief 之前提（逐條標）

fact-verified: stamp gate 實跑為紅 → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` rc=1（主委自跑，與 codex 同輸出）。

fact-verified: 主委只在 synth 末尾 append `## 戳記` 標題段，本體未動 → 該檔 `## 戳記` 之前的內容與 commit `9f75e4a7` 相同。

assumed: 三家 consult 產出（`handoffs/20260910-splitunify-x-consult-r1-*.md`）仍在原路徑且未被改動
← 否證觀測：`git status` 顯示該三檔為 modified。／我跑了：**沒跑**。請自行複驗再蓋章。

## 驗收命令

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md
bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md
```

## 產出

交件檔＋synth 一行戳記。收尾清 /tmp workdir（保留 claude-501）。
