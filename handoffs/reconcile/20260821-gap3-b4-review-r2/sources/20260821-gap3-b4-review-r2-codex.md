# GAP-3 B4 code review R2 — codex
TASK_ID: 20260821-GAP3-B4-REVIEW-R2; FAMILY: codex; SCOPE: R1 修補 diff e9e0257c..HEAD -- momentum/ tests/；review-only，未改碼。
## Verdict
需修補後再審；B4 focused/full tests 綠，但兩個 P1 未閉合，不能進 stamp。
R1_CLOSURE: CODEX-R1-P1-01 CLOSED、P1-02 CLOSED、P1-03 CLOSED、P1-04 CLOSED；`pytest ... -k 'manifest_required or unlogged_candidate or pbo_observation_axis or requires_command_and_expected'` → 4 passed/23 deselected/rc=0。
PATCH_CHECK: manifest required 未見 repo 內既有 production caller；attrs gate、candidate-set exact 與五種 entry semantic 均有綠測，未發現 brief 所列相容性破壞；但下列兩個 R1 漏抓成立。
## CODEX-R2-P1-01
**斷言**: ledger append 成功而 provenance sidecar 失敗時，`record_candidate` 雖 raise，仍留下 1 筆無 sidecar 的 ledger；`run_dsr_pbo` 只讀 ledger，之後仍回 `capability_status=ok`/DSR `ok`，故 provenance 完整性不是 fail-closed。
**碼證**: `candidate_ledger.py:229-244` 先 append ledger、後寫 sidecar；`:286-310` 不檢查 sidecar。暫時 probe `PYTHONPATH=. venv/bin/python review_tmp/gap3_b4_r2_probe.py` → `record_rc=raised OSError sidecar write unavailable; ledger_rows=1; sidecar_exists=False; run_capability_status=ok; run_ledger_status=ok; run_dsr_status=ok`。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626; docs/GAP3_EVENT_TODO.md#df04bdabf37d; handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057
[P1] 信心度=High；這推翻「sidecar 失敗 raise 即可接受」前提：後續 consumer 看不到失敗，且相同 evaluation_id 的 retry 會撞 duplicate。修法需使 sidecar 缺失的 evaluation 在 DSR/PBO 變 unavailable，並提供可驗證的 orphan/reconcile 路徑。
## CODEX-R2-P1-02
**斷言**: 收據 attrs 閘只驗欄位形狀與 hash 為 64 hex，未驗 hash 對應目前 values；普通 `Series.copy()` 後原地改值會帶著舊 hash 通過 `_assert_return_series`，可把改過的報酬寫入 ledger。
**碼證**: `candidate_ledger.py:68-99` 無 digest 重算；`:178-181` producer digest 包含 values。真實 kline probe `venv/bin/python -c '...to_return_series(...); mutated=s.copy(); mutated.iloc[0]+=0.123; _assert_return_series(...)...'` → `accepted=True; attrs_hash_matches_values=False`（原 hash `0688e34f...`，重算 `09d1e6f0...`）。
**來源摘要**: momentum/Analysis/event_samples/candidate_ledger.py#a825e470d626; tests/momentum/event_samples/test_candidate_ledger.py#79411209968d; handoffs/20260821-gap3-b4-review-r2-brief.md#839fc031c057
[P1] 信心度=High；這不是蓄意偽造 attrs，而是 pandas 普通 copy/mutation 的 stale receipt，會讓 GAP-1 snapshot membership 綁到錯誤資料。修法需在 consumer 重算並比對 canonical digest，或使 return payload/receipt 不可變且只能由 `to_return_series` 建立。
## §0/§1/§3 核對
fact-verified：R1 四條重跑；sidecar half-write 與 mutable-copy stale-hash 反例均實跑；§1 矛盾/漏項/不可測/quant/OOM/cache/API/測試/agent/短命工均無另新增 finding；§3 數據品質與不假最佳化要求與上述兩 finding 衝突。
B4_GATE: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k 'pattern_bridge or candidate_ledger'` → 27 passed/195 deselected/rc=0；完整 event_samples → 222 passed/rc=0；strategy_validation → 272 passed/rc=0；W8 五語意＋AUC assertion → 6 passed/11 deselected/rc=0。
TESTS_RUN: `git diff --check e9e0257c..HEAD -- momentum/ tests/` → rc=0；`rg extract_event_patterns` 僅 definition＋tests；未重跑 golden（brief 禁止）。
FAILURES_SEEN: `restore_golden_inventory.sh` rc=128（sandbox 無法建立 `.git/index.lock`），但 inventory 無 dirty diff；sidecar probe 首次缺 `PYTHONPATH`，補 `PYTHONPATH=.` 後上述輸出成立；未改以放寬測試掩蓋。
SCOPE_CHANGES: none；未改產品碼、測試、SPEC/TODO、根 HANDOFF 或 data_cache；/tmp 無 workdir target，claude-501 保留。
NUMERIC_OR_SCHEMA_IMPACT: 未改輸出；finding 涉 provenance transaction/integrity，不改數值定義。
OUTPUT: handoffs/20260821-gap3-b4-review-r2-codex.md
STATUS: DONE
