# EVTLABEL 戳記輪（序列化；每家一次派工）

brief-kind: stamp
task-id: 20260910-EVTLABEL-X-STAMP-R3
findings-round: R3
stamp-target: handoffs/reconcile/20260910-evtlabel-x-review-r3/synth.md
（批次戳記（ORCH「批次戳記」節）：主標的＝R3 synth；同輪亦對 R1／R2 synth 各 append 一行，路徑見下方「標的」；本 brief 供三家序列化使用：codex＝`-STAMP-R1`、composer＝`-STAMP-R2`、grok＝`-STAMP-R3`；派工時以各自 task-id 為準，戳記行之 `task:` 寫你被派的 task-id）

## 🔴 交件形態（缺這段整輪會銷不了帳）
無論結論為何，**交件檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。

標的：`docs/EVTLABEL_SPEC.md`＋`docs/EVTLABEL_TODO.md` **v4**（commit `24e011dc`）＋三份 reconcile：
- `handoffs/reconcile/20260910-evtlabel-x-review-r1/synth.md`（C1–C14）
- `handoffs/reconcile/20260910-evtlabel-x-review-r2/synth.md`（D1–D8）
- `handoffs/reconcile/20260910-evtlabel-x-review-r3/synth.md`（E1–E5）

## 你要做的事（只有這件）
1. 讀 v4 SPEC/TODO 與三份 synth。核對：R3 之 E1–E5 是否已落入 v4（`git diff fe53734f..24e011dc -- docs/EVTLABEL_SPEC.md docs/EVTLABEL_TODO.md`）；三份 synth 之處置是否與 v4 一致；**特別盯 Claude 自己寫的處置段**（ORCH「Claude 自身不享特權」）。
2. 每份 synth 各 append **一行**（放在該檔 `## 戳記` 標題之下，逐檔一行）：
   ```
   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<hash> task:<task-id>
   ```
   `<hash>`＝`bash scripts/reconcile_body_hash.sh <該 synth 路徑>` 之輸出（**自己算**，三檔各自不同）。
   若不核可 ⇒ `RECONCILE-STAMP: <family> REJECTED <date> sha256:<hash> task:<task-id> — <一句理由>`，並在你的交件檔寫 canonical finding。
3. 交件檔（`--output` 指定路徑）：列出三檔各自 body-hash、你 append 的三行、核對結果；若 REJECTED 附 `## <FAMILY>-STAMP-P<n>-<NN>` finding。

## ⚠️ 紅線
- **只 append 戳記行，不改三份 synth 其他任何位元組**（append 前後用 `reconcile_body_hash.sh` 對證 body-hash 不變）。
- **禁改碼、禁改 SPEC/TODO**。不得跑 `pytest tests/governance`。
- 本輪**序列化**：你是唯一在寫這三個檔的委員；完成後主委才派下一家。
- 附錄式 verdict 已於 R3 交件：composer「可派工」、grok「修兩殘句後可凍結」、codex「修 P1-01/02/04 後可凍結」——v4 即該修補。若你認為 v4 未修到位，REJECTED 並具名。

## 驗收命令
```
bash scripts/template_check.sh spec docs/EVTLABEL_SPEC.md
bash scripts/template_check.sh todo docs/EVTLABEL_TODO.md
for s in r1 r2 r3; do bash scripts/completeness_check.sh --lock handoffs/reconcile/20260910-evtlabel-x-review-$s/sources.lock; done
for s in r1 r2 r3; do bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-evtlabel-x-review-$s/synth.md; done
```

## 產出
交件檔＋三份 synth 各一行戳記。收尾清 /tmp workdir（保留 claude-501）。
