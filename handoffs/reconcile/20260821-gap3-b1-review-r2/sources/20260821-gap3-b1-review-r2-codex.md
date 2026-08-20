# GAP-3 B1 批 code review R2 — codex
TASK_ID: 20260821-GAP3-B1-REVIEW-R2
SCOPE: `git diff df45bc82..e0cecf7c -- momentum/ tests/`；review-only；未改碼。

## Verdict
Verdict: NOT READY FOR B2；CODEX-R2-P1-01、CODEX-R2-P2-01、CODEX-R2-P2-02 尚未閉合，故不蓋 APPROVED stamp。
R1_CLOSURE: CODEX P1-01 CLOSED、P1-02 CLOSED、P1-03 CLOSED、P1-04 NOT-CLOSED→P1-01、P1-05 CLOSED、P1-06 NOT-CLOSED→P2-01、P2-07 NOT-CLOSED→P2-02。
COMPOSER_CLOSURE: COMPOSER-R1-P1-01 CLOSED；union-find 反例與本輪 `test_transitive_overlap_union_find_composer_counterexample` 均通過。
X1/X6: X1 probe 得 i:c0、j:k:c1，符合 gap_i=事件 i duration 對所有 j>i；X6 的「任一非有限值 loud 拒」被 one-class 路徑反例推翻。
STAMP_STATUS: withheld；未輸出 RECONCILE-STAMP，避免把未閉合 finding 宣稱 APPROVED。

## CODEX-R2-P1-01
**斷言**：R1 P1-04 的 close-time ordering guard 對 `uint64` timestamp 仍可繞過；`np.diff(uint64)` 下降時下溢，PIT 可能在未排序 bars 上繼續。
**碼證**：`alignment.py:42-50` 接受 dtype kind `u` 且直接做 `np.diff`; `venv/bin/python -c 'import numpy as np,pandas as pd;from momentum.Analysis.event_samples.alignment import _validate_bar_table as v;t=np.uint64(1704067200000);b=pd.DataFrame({"open_time_ms":np.array([t+86400000,t],dtype=np.uint64),"close_time_ms":np.array([t+172800000,t+86400000],dtype=np.uint64),"open":[1.,1.],"close":[1.1,1.1]});print("uint64_descending_validator_result",repr(v(b)))'` → `''`，rc=0。
**來源摘要**：`momentum/Analysis/event_samples/alignment.py:42-50`#0e7591c6b591；嚴重度=P1；修補=先轉有號/安全差分或拒 unsigned timestamp，再驗排序。

## CODEX-R2-P2-01
**斷言**：R1 P1-06 修補只在 test labels ≥2 類時檢查非有限值；one-class branch 先於 finite gate return，NaN 可被誤報為 `one_class_test_segment`。
**碼證**：`baseline.py:114-123`; `venv/bin/python -c 'import numpy as np;from tests.momentum.event_samples.test_baseline_oracle import synth,OC;from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f;X,y,p=synth();X.iloc[120,0]=np.nan;y.iloc[120:]=1;r=f(X,y,p,oracle_config=OC);print("one_class_nonfinite_result",r["capability_status"],r["reason"],"raises",False)'` → `unavailable one_class_test_segment raises False`；混合類 targeted test 2 passed，不覆蓋此分支。
**來源摘要**：`momentum/Analysis/event_samples/baseline.py:114-123`#63e6be0a20ec；嚴重度=P2；修補=將 finite gate 前移，或在 unavailable receipt 明列 nonfinite failure。
## CODEX-R2-P2-02
**斷言**：R1 P2-07 仍可省略 provenance；`feature_manifest_hash` 是 Optional，呼叫者不傳時 baseline 正常產報且 receipt hash 為 `None`。
**碼證**：`baseline.py:88,109-112`; `venv/bin/python -c 'from tests.momentum.event_samples.test_baseline_oracle import synth,OC;from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f;X,y,p=synth();print("omitted_manifest_hash_receipt",repr(f(X,y,p,oracle_config=OC)["receipts"]["feature_manifest_hash"]))'` → `None`，rc=0；僅提供 hash 的 regression test 2 selected passed。
**來源摘要**：`momentum/Analysis/event_samples/baseline.py:88-112`#63e6be0a20ec；嚴重度=P2；修補=要求非空 hash 或 typed materialization result，缺 hash fail-closed。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF/CLAUDE/brief/SPEC/TODO/D-001；X1 gap probe、R2 seam/反例 probes 與 code line 對證完成；truncated_mode 壞 row_id 被接受但仍以 timestamp `ms[pos]==target` 定位，符合 D-001 明示語意，非 finding。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 98 passed in 11.15s；mutation M1/M2/M3/M5/M8/M9/M10/M12 → 8 passed；dedupe/alignment/import/row_id/baseline targeted → 2+1+5+1+2 passed；`bash scripts/completeness_check.sh --single handoffs/20260821-gap3-b1-review-r2-codex.md --family codex` → rc=0（scratchpad 執行；直接入口先被 debt gate 擋）。
FAILURES_SEEN: uint64 ordering、one-class nonfinite、omitted hash probes 分別產生上述 findings；未改碼、未修改 SPEC/TODO；data_cache 僅作真實 kline/FF 輸入，未納入交件，未 commit。
SCOPE_CHANGES: review-only；HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r2-codex.md`；NUMERIC_OR_SCHEMA_IMPACT: 未改產品輸出，報告指出 PIT guard、nonfinite gate、provenance receipt 風險。
STATUS: DONE
