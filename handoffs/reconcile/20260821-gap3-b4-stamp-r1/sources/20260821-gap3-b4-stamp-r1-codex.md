# GAP-3 B4 stamp handoff

## CODEX-R1-P3-00
**斷言**: r4 synth 群集/處置與三家 P3-00 sentinel 一致；R1=8、R2 新增=2、R3 新增=1、R4 新增=0，終版 commit `90ff53f7` 可合併。
**碼證**: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260821-gap3-b4-review-r4/synth.md` 於 append 前後均回 `dfc4250e28fa11fec14198484bd15ad6e33c99ca9b26e62bd3c444227ee66723`；stamp 行計數為 3。
**碼證**: `git show --no-patch 90ff53f7` 對應終版；r4 三家來源均含 canonical `*-R4-P3-00` 且無新增 finding。

ASSUMPTIONS_VERIFIED: 主委 hash 與自行重算值一致；r4 closure 與三家 sentinel、收斂履歷及 receipt 內容一致。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "pattern_bridge or candidate_ledger"` → 29 passed, 195 deselected, rc=0。
TESTS_RUN: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260821-gap3-b4-review-r4/synth.md` → hash 如上，rc=0。
FAILURES_SEEN: 初次 `rm -rf` 被環境安全策略拒絕且未刪除；改用精確 workdir 路徑的 `find -delete` 後清理完成。
SCOPE_CHANGES: 僅對 stamp-target 的 `## 戳記` 區單次 append codex APPROVED stamp，新增本交件檔；未改程式、SPEC、TODO、HANDOFF.md；scratchpad 已移除。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_ARTIFACT: `handoffs/20260821-gap3-b4-stamp-r1-codex.md`。
STAMP: `RECONCILE-STAMP: codex APPROVED 2026-08-21 sha256:dfc4250e28fa11fec14198484bd15ad6e33c99ca9b26e62bd3c444227ee66723 task:20260821-GAP3-B4-STAMP-R1`
STATUS: DONE
