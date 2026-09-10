# SPLITUNIFY consult synth 戳記輪（修正後重審；序列化，每家一次派工）

brief-kind: stamp
task-id: 20260911-SPLITUNIFY-X-STAMP-R4
findings-round: R4
stamp-target: handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md

（序列化：composer＝`-STAMP-R2`、grok＝`-STAMP-R3`、codex 重審＝`-STAMP-R4`；
戳記行之 `task:` 寫**你被派的 task-id**。）

## 為什麼有這一輪，以及 synth 已經被改過什麼

第一輪（`20260911-SPLITUNIFY-X-STAMP-R1`）codex **REJECTED**，理由：synth 的處置段把
`CODEX-R1-P1-02` 明確反駁過的說法（「時間 purge／embargo 比事件緩衝強」）寫成「三家共同理由」
與「三家未反駁」。**該 finding 成立，主委採納並已改。**

主委據此回頭把 6 條 codex consult findings 逐條核對，**又自行發現三處收斂失誤**：
- `CODEX-R1-P1-04`（接線缺口）被誤併進 D4 而實質丟失 ⇒ 補為新增之 **D6**。
- `CODEX-R1-P1-03`／`CODEX-R1-P1-05` **完全未被任何群集引用** ⇒ 補為 **D7**／**D8**。
- `CODEX-R1-P2-06` 原被誤列在 D5 ⇒ 移正至 D4。

⇒ synth 的**本體已改**（決議項由 5 個增為 8 個），body-hash 已變。
第一輪那行 REJECTED 帶的是舊 hash，**刻意保留為稽核軌跡**，其下有一段說明註記。
**你這一輪要蓋的是新的 body-hash**，自己算，不要抄任何文件裡出現過的雜湊。

## 🔴 交件形態（缺這段整輪會銷不了帳）

無論結論為何，**交件檔內必須至少有一個 canonical heading**：
- 有問題 → `## <FAMILY>-R<輪次>-P<0-3>-<NN>`，含 `**斷言**`／`**碼證**`／`**來源摘要**`（P0/P1 須 12 位雜湊）。
- 無問題 → 照 `templates/COMMITTEE_FINDING_TEMPLATE.md` 的**零 findings sentinel** 形態，不得只寫散文。
戳記本身 append 到 stamp-target 的 `## 戳記` 區，**不算**交件檔的 heading。

## 你要做的事（只有這件）

1. 讀 `handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` 全文，核對它是否**忠實**
   收斂了你自己那一輪的 consult 產出（`handoffs/20260910-splitunify-x-consult-r1-<你的家族>.md`）：
   你的每一條 finding 是否被某個決議項（D1–D8）**實質引用**（不是只在附錄出現過）、
   你的立場有沒有被改寫或降級。**特別盯 Claude 自己寫的處置段**（ORCH「Claude 自身不享特權」）。
   🔴 主委已自承掉了三條 codex findings——**請假設同樣的事也可能發生在你的條目上**，逐條核。
2. 在 stamp-target 的 `## 戳記` 標題之下 append **一行**：
   ```
   RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<hash> task:<task-id>
   ```
   `<hash>` ＝ `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md`
   之輸出（**自己算**，不得抄本 brief 或檔內任何既有雜湊）。
   若不核可 ⇒ `RECONCILE-STAMP: <family> REJECTED <date> sha256:<hash> task:<task-id> — <一句理由>`，
   並在你的交件檔寫 canonical finding。
3. 交件檔（`--output` 指定路徑）：寫出你算到的 body-hash、你 append 的那一行、逐條核對結果。

## ⚠️ 紅線

- **只 append 戳記行，不改 synth 其他任何位元組**（append 前後 `reconcile_body_hash.sh` 須不變）。
- **禁改碼、禁改 `docs/SPLITUNIFY_*.md`**。不得跑 `pytest tests/governance`（小時級）。
- 本輪**序列化**：你是唯一在寫這個檔的委員；完成後主委才派下一家。
- 本輪**不是**重審 SPEC/TODO——那已由 `20260911-SPLITUNIFY-X-REVIEW-R1` 做完（13 群集）。
  本輪只問「synth 是否忠實記錄了 consult 共識」。

## 本 brief 之前提（逐條標）

fact-verified: 第一輪 codex REJECTED 與其理由 → `handoffs/20260911-splitunify-x-stamp-r1-codex.md` 之 `CODEX-R1-P1-07`。

fact-verified: 主委之三處收斂失誤 → `handoffs/reconcile/20260911-splitunify-x-stamp-r1/synth.md` 群集段逐條列出；synth 內亦有「修訂紀錄」段自承。

assumed: `reconcile_cluster_attribution_check.sh` 對本檔回 rc=0 並不代表沒有掉項
← 否證觀測：該腳本能抓出「ID 只出現在附錄、未被任何決議項實質引用」的情形。
／我跑了：**跑了**，rc=0，但 `CODEX-R1-P1-03`／`P1-05` 當時確實只在附錄 ⇒ 該腳本擋不住這型掉項。
這條已登記為殘留 `SU-RESID-1`。請正面打：你的條目有沒有同型掉項？

## 驗收命令

```
bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md
bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md
```

## 產出

交件檔＋synth 一行戳記。收尾清 /tmp workdir（保留 claude-501）。
