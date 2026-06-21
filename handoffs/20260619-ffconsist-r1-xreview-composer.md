# FF R1 互審 — Composer 審 Claude + Codex（read-only）

審閱對象：`r1-claude.md`、`r1-codex.md`（未重審自家 r1-composer）。

---

## #1 log 一致
- **Claude**：**同意** worker 內 init logging、子進程不繼承 handler 的診斷正確；**反對 P1**——brief 已證 batch 算力細節缺檔，應與 Codex 同列 P0，否則 Q3/Q2 除錯仍盲。
- **Claude**：**部分反對**——未提 `TimedRotatingFileHandler` 跨進程 rotate 競態；僅寫 O_APPEND 不足，worker 宜 non-rotating 指當日檔。
- **Codex**：**同意** P0、context 欄位、`api.*` 一併進 sink；queue listener 方向合理但 **反對默認採 queue**——`concurrent=1` 下 FileHandler+pid 前綴更簡，queue 增加父死 listener 孤兒風險，應列可選而非預設。

## Q3 進度一致
- **Claude**：**同意** 單路徑補 RSS、共用 schema；**反對**「batch 補單 symbol 級 rolling 10/100」未加 `concurrent>1` 前提——與 Codex「無唯一 current stage」衝突，硬做會誤導 UI。
- **Codex**：**同意** canonical schema、`layer_metrics.jsonl` bridge、併發>1 只 coarse；**反對 P0 與 Q2 prompt 並列第一**——schema 可先於 batch 保留對話，但單路徑 RSS 非使用者痛點，P0 全包略過度。
- **雙方**：皆未明講單路徑 RSS（同進程含 API）vs 子進程 RSS 語意差；第 2 輪應標欄位註解或分 `process_rss_mb`。

## Q5 terminal
- **Claude**：**同意** `access_log=False` + middleware 已進檔；P0 合理。
- **Codex**：**同意** 需 config 開關、勿靜默全關；**反對 P1 排在 #1 後**——一行改動、零 FF 路徑風險，應 P0 與 Claude 對齊，env 開關可同 PR 順帶。

## Q2 批次保留對話
- **Claude**：**同意** staging/decision、粒度（逐 symbol vs 整批）風險；P2 偏保守但可接受。
- **Codex**：**同意** prompt+alias、checkpoint 失效、批量刪除 endpoint；**反對 P0 過急**——未釐清「每 item 一 dialog」vs「整批一次」；大批次逐 run delete 慢是實險，Claude 粒度問題 Codex 用 endpoint 緩解但未寫 UX 預設。
- **雙方缺口**：皆假設算完即落盤；若 batch 現行 mid-run register，需實測 `_record_item_result` 再定 staging 切點。

## E 執行模型 — 維持現狀
- **三方共識**：**同意** 不整併 executor（單 thread / 多 subprocess）；OOM 隔離、TA-Lib/Numba、lease/callback 論點成立。
- **Claude**：**同意** 弊>利論述；**補充反對其「抽共用層回報低」過絕**——觀察層仍會漂移，至少應 P2 contract test（Codex 已提）。
- **Codex**：**同意** `GenerationRunner`+sink 介面、P2 adapter only；**同意** 維持缺點「兩套 glue 需 contract tests」—這是維持現狀的**隱藏風險**，Claude 未寫。
- **被忽略的整併好處**（雙方均輕描）：統一 runner 可單測覆蓋、單路徑 BLAS/RSS 上限與 batch 對齊；但 8GB 多 symbol OOM 代價仍否决整併——**維持裁決可接受**。
- **維持的隱藏風險**（雙方部分覆蓋）：每項 #1/Q3/Q2 必須雙路徑實作；resume/checkpoint 語意僅 batch 複雜；無 contract test 則第 2 輪後易再分叉。

## 優先序分歧摘要
Claude: P0 Q5 → P1 #1/Q3 → P2 Q2。Codex: P0 Q3+Q2+#1 → P1 Q5。建議 reconcile：**Q5(P0) → #1(P0) → Q3(P1) → Q2(P2) → E adapter tests(P2)**。
