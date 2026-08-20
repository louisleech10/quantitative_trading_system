# GAP-3 B1 批 code review R3 — codex

TASK_ID: 20260821-GAP3-B1-REVIEW-R3
SCOPE: `git diff e0cecf7c..HEAD -- momentum/ tests/`；review-only；未改碼。

## Verdict

Verdict: NOT READY FOR B2；三條指定 R2 反例均已閉合，但修補宣稱的 `feature_manifest_hash` 64-hex fail-closed 契約仍有一條 P2 finding。
R2_CLOSURE: `CODEX-R2-P1-01` CLOSED（uint64 降序拒收）；`CODEX-R2-P2-01` CLOSED（one-class＋NaN loud 拒收）；`CODEX-R2-P2-02` 的省略 hash 行為 CLOSED（未傳參數 fail-closed），但採納處置所列 64-hex 格式要求未完全落地，見 `CODEX-R3-P2-01`。
B2_STAMP: withheld；目前不可蓋 APPROVED 進 B2。

## CODEX-R3-P2-01

**斷言**：`feature_manifest_hash` 的修補只驗 `str` 與長度 64，沒有驗十六進位字元；長度正確但非 hash 的 provenance 仍可產生 baseline receipt。

**碼證**：`momentum/Analysis/event_samples/baseline.py:98-100` 只有 `len(feature_manifest_hash) != 64`，未有 hex-pattern 檢查；`venv/bin/python -c 'from tests.momentum.event_samples.test_baseline_oracle import synth,OC; from momentum.Analysis.event_samples.baseline import single_feature_binary_baseline as f; X,y,p=synth(); r=f(X,y,p,oracle_config=OC,feature_manifest_hash="g"*64); print("nonhex_manifest_hash_accepted",r["receipts"]["feature_manifest_hash"]); raise SystemExit(0)'` → `nonhex_manifest_hash_accepted ggg...`，rc=0。相對地省略參數 probe → `TypeError`、rc=0（由 `pytest.raises` 捕獲）。

**來源摘要**：`momentum/Analysis/event_samples/baseline.py#026cc7bca318`

P2；信心度=10/10；採納處置明列 `feature_manifest_hash` 為 64-hex 且格式錯須 fail-closed，但目前只保證長度，會讓 malformed provenance 進入 receipt。修法：以既定 sha256 hex 契約做完整 `[0-9a-f]{64}` 驗證，並補 64 字元非 hex 的回歸負例；不改本輪產品碼。
## 驗證摘要

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、R3 brief、FROZEN GAP3 SPEC/TODO、GAP3 TODO D-001、R2 synth；`e0cecf7c..HEAD` 目標 diff 為 5 files、56 insertions/24 deletions；合法 uint64（值不超 int64 max）ascending validator probe 回傳空字串，行為未改變。
TESTS_RUN: `venv/bin/python -c '<uint64 descending probe>'` → `unsorted_bar`，rc=0；`venv/bin/python -c '<one-class＋NaN probe>'` → `ValueError loud`，rc=0；`venv/bin/python -c '<omitted hash probe>'` → `TypeError fail-closed`，rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 100 passed in 10.58s，rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k 'M1 or M2 or M3 or M5 or M8 or M9 or M10 or M12'` → 8 passed in 0.83s，rc=0；non-hex probe → accepted，rc=0。
FAILURES_SEEN: 初次把兩個例外 probe 壓成單行 `try` 造成 Python SyntaxError；改用 `pytest.raises` 後通過。`bash scripts/restore_golden_inventory.sh` → rc=128，因 sandbox 拒絕建立 `.git/index.lock`；未繞過權限，未改 `.git`。
SCOPE_CHANGES: review-only；未改 implementation/tests/SPEC/TODO，未碰 data_cache，僅新增本交件檔；`/tmp` 與 TMPDIR 未找到本任務 workdir，`/private/tmp/claude-501` 保留。
NUMERIC_OR_SCHEMA_IMPACT: 未改產品輸出；指出 provenance hash 格式驗證缺口。
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b1-review-r3-codex.md`
STAMP_STATUS: withheld；因 `CODEX-R3-P2-01` 尚未閉合，未宣稱 APPROVED。
STATUS: DONE
