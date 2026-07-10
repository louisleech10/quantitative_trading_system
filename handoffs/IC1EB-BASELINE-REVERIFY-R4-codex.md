# IC 1e+1b Golden baseline v4 — Codex R4 複驗

**前置 — CLOSED**：`bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS，body sha256=`b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043`；baseline/`data_cache` 全程唯讀。
**F10b 選欄 receipt — CLOSED**：Python 全量重算 manifest `subsets=10`（9 longitudinal + xsec），每組 `selected_names` 皆 500 個且唯一，十組 list sha/family histogram 全自洽；9/9 input meta 與 manifest 完全一致。xsec report 500 個 `feature_name` 與 manifest xsec 清單集合相等，`selected_names_sha256=e6e01c4cd96f48460aee9c3c57405672bf64a8eeddcee5591995daace422f03f`、family 數=10；R3「xsec receipt 不可查」反例已失效。
**F4c 非首列 missing-vs-null — CLOSED**：R3 同一兩列 mutation 重打：舊 union hash、首列 order hash、G1 five-hash 均仍相等；新 `summary_row_keysets_sha256` 分離，explicit-null=`877db12a8827afb836f5433e9b788006f079614b0bb8a5afe0683d20ec7e0118`、第 2 列缺 `coverage`=`6bb15474deac964c7c9045b7c3aff2d84c2c4ffa50ffc29ccf393b6bacd0c4c0`；同缺欄送入 `record_run` → `AssertionError: ... row 1: ['coverage']`。
**F4b 綱要/順序 — CLOSED（抽查）**：xsec artifact 重算 union/逐列 keysets/feature-order/G1 five-hash 均 match；反轉 raw 首列 key insertion order 使 `summary_row_key_order_sha256` 轉紅。提醒：report 以 `sort_keys=True` 發布，故 raw key-order hash不能由發布 JSON 重建；逐列 keyset 與 feature-row order receipts 可重建且成立，不影響 R3 原反例 closure。
**F5b ±inf — CLOSED（抽查）**：`_strict_numeric(coverage)` 對 `+inf/-inf` 均實際 raise `TypeError`。
**F6b content 指紋 — CLOSED（抽查）**：tmp 同 path/size/mtime 的 `AAAA→BBBB` 使指紋 `ba9313d2…991a→da7594e2…7ba5`；另實跑 29GB `data_cache_fingerprint()`（函式內計時 24.2s）=`a7a043c0f7d3a6e8c3b3cd10ea3b14708211d32534bdc6c81fa3d9f301fc7046`，等於 manifest after，且 before=after/unchanged=true。
**F7b 完整性/淨化 — CLOSED（抽查）**：逐檔重算 inputs `19/19 bad=[]`、reports `13/13 bad=[]`；13 個 request 均無 `name/expect_scope/expect_rows`。capture script 實檔 sha=`1bb23a74673b31af8b647680dd59e4de6d1ceb4d294ab612d0a26c2111cb6e9e`，等於 manifest generator sha。
**F8b NaN 位元 — CLOSED（抽查）**：payload `0x7ff8000000000001` vs `0x7ff8000000000002` 重打，`values_sha256` 與 `nanmask_sha256` 均相等；values sha=`74999fd28ab18ccca2bee199f260d19764603a3c78353d773d16d215eebe8e19`。
**F13b low-confidence 顆 — CLOSED（抽查）**：真 `kline_cache` BTCUSDT/12h 重算 q95=`33498.7109375`、事件數=85；manifest request 精確為 `volume >= 33498.7109375`，report `metadata.event_filter` 精確為 `n_events=85/tier=low_confidence/adjusted_p_threshold=0.1`。
**實跑命令**：`source venv/bin/activate && python -u -`（F4/F5/F6 mutation/F7/F8/F10/F13 replay harness）→ 上述全部成立；`source venv/bin/activate && python -u -`（獨立真 cache 全內容 fingerprint）→ actual=manifest；baseline reports 共 805MB、`data_cache` 29GB。
ASSUMPTIONS_VERIFIED: v4 manifest 不是只新增空欄；十組 receipt 與 meta/report 實體一致；F4c 缺欄與 null 可區分且 fail-closed；六條 R3 closure 原反例仍轉紅
TESTS_RUN: stamps PASS；Python 原反例/逐檔 sha/真 kline replay/29GB content fingerprint 全 PASS
FAILURES_SEEN: 首次合併式全內容命令因長時間無回傳而中止；拆分後同檢查完整通過；另 raw key-order hash 因 JSON sort_keys 不可由 report 重建，已以 raw mutation 及可重建 receipts 交叉確認
SCOPE_CHANGES: none；唯一產出 `handoffs/IC1EB-BASELINE-REVERIFY-R4-codex.md`
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀複驗；未改 baseline/data_cache/code/schema）
VERDICT: PASS
