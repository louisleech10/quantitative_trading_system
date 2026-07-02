# O3 REDO — 內容級 forensic 豁免（Composer）

## 背景
Codex review（`handoffs/20260702-O3-REVIEW-CODEX.md`）3 BLOCKING：路徑級 `_GOVERNANCE_FORENSIC_GLOBS` 預設繞過，使 REVIEW/REDTEAM 等檔案內**散文**真 VERIFY、operational 段、裸極性宣稱可 exit 0。

## 修法（`scripts/verification_claim_check.py`）

1. **移除路徑級預設繞過**：刪除 `_GOVERNANCE_FORENSIC_GLOBS`、`_is_governance_forensic_path`、`_forensic_*`、`_is_forensic_example_or_discussion`；`_detect_source_context` 不再因 forensic 路徑設 `forensic_discussion`。
2. **內容級 discussion 豁免**（`_is_content_discussion_exempt` + `_has_claim_signals_outside_exempt_regions`）：
   - `in_fenced` / `in_quote`（blockquote）整段豁免；
   - inline-code（单反引号）內字串剝除後，若無 VERIFY/REF/SIGNOFF/強極性/DONE 信號 → 豁免。
3. **非範例散文仍驗**：`classify_mode` 對非 exempt 單位——假歸屬（R6）、裸強極性無 backing、VERIFY/REF citation、operational 段——照常 FAIL；`docs_spec` 仍 discussion。
4. **治理 meta 敘述**（內容模式 `GATE_META_DISCUSSION_RE`，非路徑）：規格/紅隊文件中描述 gate 行為的 token 列舉（如 `已驗/真紅`、`operational claim`、`pytest tests/governance`）仍走 citation/discussion，避免 V7/既有 REDTEAM 誤擋。
5. **VERIFY-EXEMPT 檔案級傳播**（`_file_verify_exempt_allowed`）：標頭含 VERIFY-EXEMPT 的 discussion 檔全檔豁免；HANDOFF/commit/RESULT 零豁免不變。
6. **零豁免不變**：`HANDOFF.md`、commit-msg、`*RESULT*` 路徑邏輯未改。

## 測試（`tests/governance/test_verify_gate_o3.py`）

| 測試 | 意圖 |
|------|------|
| `test_o3_redteam_attack_examples_allowed` | fenced / blockquote / inline-code 攻擊範例 → exit 0 |
| `test_o3_review_real_verify_still_blocked` | Codex-① REVIEW 散文 `VERIFY:no-such-receipt` → exit 1 |
| `test_o3_review_operational_section_still_blocked` | Codex-② `## 已完成` operational 無 backing → exit 1 |
| `test_o3_review_bare_polarity_still_blocked` | Codex-③ 裸極性 → exit 1 |
| 既有 HANDOFF/commit/R6/FIX-PROMPT/V7/REDTEAM repo 回歸 | 不回歸 |

ASSUMPTIONS_VERIFIED: 逐條跑 Codex 反例 fixture（REVIEW 真 VERIFY / operational / 裸極性 → rc=1；fenced 範例 → rc=0）；`grep _GOVERNANCE_FORENSIC` 在 checker 中為 0。
TESTS_RUN: `pytest tests/governance/ -q` → 105 passed
FAILURES_SEEN: 初版裸極性/REDTEAM 誤擋 → 調整 classify 順序 + GATE_META + 檔案級 EXEMPT 後全綠
SCOPE_CHANGES: none（僅 `scripts/verification_claim_check.py` + `tests/governance/test_verify_gate_o3.py`）
NUMERIC_OR_SCHEMA_IMPACT: none

HANDOFF_NOT_UPDATED: 執行合約 append-only 至本檔，不重寫根 HANDOFF.md

STATUS: DONE
