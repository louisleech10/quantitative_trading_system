# IC 1e+1b Golden baseline v3 — Codex R3 複驗

**前置**：`bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS，body sha256=`b77932d8…`; baseline/`data_cache` 全程唯讀。
**F4b 綱要 — CLOSED（R2 原反例）**：`venv/bin/python -c '<raw key-order/missing-column mutation>'` → 反轉單列 keys 使 `summary_row_key_order_sha256` 改變；單列刪 `coverage` 得 missing=`['coverage']`，`record_run` 同判據必 raise。
**F5b ±inf — CLOSED**：`venv/bin/python -c '<five_hash coverage=+inf/-inf>'` → 兩者均 `TypeError`；finite-or-NaN gate 已成立。
**F6b content 指紋 — CLOSED**：tmp 原反例（同 path/size/mtime，`AAAA→BBBB`）→ fingerprint 改變；再跑 29GB `data_cache_fingerprint()`（24.3s）=`a7a043c0…7046`，等於 manifest after，before=after/unchanged=true。
**F7b inputs 完整性/request 淨化 — CLOSED**：逐檔重算 → inputs `19/19 bad=[] extra=[]`、reports `13/13 bad=[]`；13 run 的 `request` 無 `name/expect_*`，4 組 harness asserts 已隔離至 `capture_asserts`。
**F8b NaN 位元 — CLOSED**：payload `0x7ff8000000000001` vs `…0002` 重打 → `values_sha256 equal=True`、`nanmask_sha256 equal=True`。
**F10b 選欄清單/家族分布 — STILL-OPEN (MAJOR)**：9 份 input meta 的 `selected_names` 各 500、hash/hist 自洽，12 顆 longitudinal report 亦繼承；但 R2 原 `manifest` 反例仍成立：manifest top/run 無 `selected_names(+sha)/family_distribution`，xsec report `metadata.baseline_subset=null`。xsec summary 可另算 list sha=`f0bced11…9c77` 與 10-family histogram，但產物未存該 receipt，違反 reconcile「入 manifest」。
**F13b low-confidence 顆 — CLOSED**：真 `kline_cache` BTC/12h 重算 q95=`33498.7109375`、`n_events=85`；report 精確為 query 同值、tier=`low_confidence`、`adjusted_p_threshold=0.1`。
**F14b 裁決文字 — CLOSED/同意編排端**：實跑真 labels artifact 重算 `return_5_equal=True`（1696 rows/1691 finite）；`_load_labels_hdf5` 回 `Index(name=timestamp)`、shape `(1696,1)`、無 symbol 維度，receipt=`InvalidInputError` 與 manifest 完全一致。
**F14b 碼證**：`ic_filter_orchestrator.py:2798-2814` 無論 H5 內容只取 first group 後建立單軸 DataFrame；`:367-372` 因非 MultiIndex 必回 false；`:951-954` 因而必 raise。故舊路徑 expected-raise 是 baseline 真相，3sym MultiIndex 承諾撤回合理；T-3.1b 可達性留 B3 定義，不在 baseline 刀擴 scope。
**新增發現 F4c — STILL-OPEN (BLOCKING)**：兩列 mutation 中只把第 2 列 `coverage:null` 改為缺 key，第 1 列保持完整；實跑 `summary_keys_union_sha256`、`summary_row_key_order_sha256`（只看首列）、feature-order 與 G1 five-hash **全相等**。因此 v3 仍把非首列 missing 與 explicit null 混同；需 per-row key-order/schema hash 或逐列 schema assert。
**其餘新問題抽驗**：generator sha/current HEAD 均 match，13 reports+1 expected raise、generated_at/env/content receipts 齊；除 F4c/F10b 外未見新 artifact integrity 問題。
ASSUMPTIONS_VERIFIED: 原 R2 mutations 逐項實跑；F14 結構性不可達由真 artifact loader+碼證驗，不採信裁決文字
TESTS_RUN: stamps PASS；Python F4/F5/F6/F7/F8/F10/F13/F14 mutations/replay；29GB content fingerprint match；13 report+19 input sha/size 全 match
FAILURES_SEEN: create_ic_analyzer 完整初始化複驗逾時後中止，改以同 production `_load_labels_hdf5`+symbol-dimension guard 直接實跑；不影響結構性結論
SCOPE_CHANGES: none；唯一產出 `handoffs/IC1EB-BASELINE-REVERIFY-R3-codex.md`
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀複驗；未改 baseline/data_cache/code/schema）
VERDICT: BLOCK(F10b manifest/xsec 選欄 receipt 仍缺；F4c 非首列 missing-vs-null 仍可假綠)
