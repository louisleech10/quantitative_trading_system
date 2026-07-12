# P2DEBT T5 Golden Provenance — Codex adversarial
task-id: t5-adv-codex | date: 2026-07-12 | scope: read-only review; no freeze executed

## Verdict: BLOCK
1. **重凍而非 revert：方向成立，但 R1 理由不誠實。** `854d444` 的雙 RCA 證明舊 baseline 把
   feature epoch index 與 label RangeIndex 做 rolling join，得到 0 列/50 個 summary 全 None；對齊修正不可 revert。
   然而新 fd932a/35e15c 還包含 flag-off/on 顯式化；應分別記「修 rolling oracle」與「補記原隱形 override」，
   不可把 float64 寫進理由：RCA 後 float64 強轉已被修掉，這不是現 baseline 的重凍理由。
2. **可證偽反例：現 reuse 會接受髒 cache。** 將 inputs 複本中的 H5 任一 feature 值改 1 byte/改 row index，
   保留檔名與 meta `baseline_subset.selected_features`；現 `_materialize_deterministic_subset()` 仍直接 return，分析會
   靜默消費被污染資料，產出不同 baseline 或錯誤統計。它不驗 H5 SHA、row count/index、symbol/tf/config_hash、
   selected_features 是否等於當前 registry 的 sorted top-N；meta 本身甚至沒有可綁定 H5 的 SHA。
3. **R1 guard 驗收不足。** 只比 meta `config_hash/選特徵/參數` 仍抓不到「同 meta、髒 H5」。需 manifest
   綁定 H5 SHA256 + meta SHA256，並驗 H5 內 symbol/tf/schema/row-index/feature order；不符應 raise，不能自動
   覆寫 canonical inputs。mutation 必含「只改 H5、meta 不改」以及「meta 選欄與 registry top-N 分歧」。
4. **`unlock_*` 不是既有制度。** `rg -n 'unlock_' tests/golden handoffs --glob '*.json' --glob '*.md'` 只命中
   R1 自己；另一 golden `ic_phase1_contract/baseline_meta.json` 也無此欄。故不能列為既有必填 schema。
   若要建立制度，SPEC 必先定精確欄名/語義/authority/source receipt；否則用 append-only provenance events 較可稽核。
5. **獨立重放定義自相矛盾。** 「乾淨環境」與「reuse guard 生效」不能同時證明 source→input 可重建；reuse
   只證明固定 materialized input→output。應拆兩 gate：(A) pinned input SHA 重放 output byte SHA；(B) 移除 inputs
   後由 canonical registry 重建，驗 input SHA。JSON 含 task_id/generated_at 時，整檔 byte SHA 天生不穩；需明定
   canonical projection/exempt fields，現有 regen receipt 已只對排除 `generated_at` 後的 normalized SHA 比較。
6. **可行性/時間：DELEGATED。** 腳本 timeout 已由 1200 提到 1800 秒，兩家族各跑一次最壞 60 分鐘；本審
   未在髒工作樹執行。應用獨立 worktree/複製 golden+inputs 至 `/tmp`、redirect persist，且先後快照 data_cache。

REQUIRED_RECONCILE: 修正重凍理由；定義 content-addressed input manifest；拆 A/B replay；定 canonical SHA；
移除未制度化 unlock 必填或先建 schema。完成前不得把現工作樹 golden 宣告 provenance closed。
