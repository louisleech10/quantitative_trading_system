# GAP-3 B5 Review R4 — codex
TASK_ID: 20260822-GAP3-B5-REVIEW-R4
SCOPE: 依 brief 審查 013aa69f 的 R3 修補；review-only，禁改產品碼、測試、data_cache、root HANDOFF.md。
VERDICT: NOT READY FOR RECONCILE-STAMP／USER UAT；機械 Gate 全綠，但 same-file verify 相容假設仍有一條 P1 finding。
R3_CLOSURE: CODEX-R2-P1-03 CLOSED（companion 200／缺 source_file 400／竄改 422）；CODEX-R3-P1-01 CLOSED（plain_docs rc0）；CODEX-R3-P1-02 CLOSED（vitest 22 passed）；CODEX-R3-P2-03 CLOSED（decision-bar 1 passed＋mutation 使斷言失敗）。GROK-R3-P0-01、COMPOSER-R3-P2-01：複核同意 CLOSED（plain_docs rc0）。
Q2_REVIEW: ①file-only 且 verify=false 的既有路徑仍 200；verify=true 未附 source_file 明示 400；但同一檔同時放 file/source_file 仍 mismatch（下列 finding）。②分開的 /search companion 可成功。③連續兩次 link.click 可能被瀏覽器擋，僅 UX 建議不列 finding。④預設 2 同時傳入 future_2bar_return 與 label_definition.window.horizon_bars，語意一致。
B5_GATE: `pytest tests/api/ -q -k gap3_import` 15 passed rc0；`npm run build` rc0；`npx vitest run gap3` 3 files/18 passed rc0；`pytest tests/momentum/event_samples/ -q` 230 passed rc0；`bash scripts/plain_docs_sync_check.sh` rc0；scale receipt 三欄齊，UAT checklist 簽字仍空白。
REVIEW_COVERAGE: 11 類逐項核對；矛盾／端到端／可測／quant／過度工程／OOM／cache／測試／必要性均無新增 finding；API 相容性問題列下方 P1；agent 可執行性不適用本輪。

## CODEX-R4-P1-01

**斷言**: brief 所稱「上傳檔即來源檔」可把同一檔同時放入 `file` 與 `source_file` 並通過 verify 不成立；事件檔含 `source_file_digest` 時，完整檔案位元組的 SHA-256 不可能自洽，該路徑仍拒收。

**碼證**: `api/routes/case.py:153-165` 將 `source_file` 完整 bytes 傳入 validator；`momentum/Analysis/event_samples/import_contract.py:108,182-184` 對完整 `source_bytes` 取 SHA-256 並逐列比 `source_file_digest`。實跑 `venv/bin/python -c '<EventImportService same file/file probe>'` → `same_file_status=reject kind=contract_violation reasons=['digest_mismatch']`；分開 companion 的 `venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"` → 3 passed rc0。RECHECK: 若保留 same-file 相容性，需改定不含內嵌 digest 的 canonical source bytes（或明確只接受 distinct companion）並新增 same-file 成功測試。

**來源摘要**: api/routes/case.py#c481747e887b；momentum/Analysis/event_samples/import_contract.py#58c331ca3d5d；tests/api/test_gap3_import.py#51774859bf14；handoffs/20260822-gap3-b5-review-r4-brief.md#00a885cee1ca

正文：[P1] 信心度=High。分開 companion 的 R3 修法可用，但目前說明把「同檔相容」與「companion 相容」混為一談；在修法或文件裁決前阻擋 stamp/UAT。
ASSUMPTIONS_VERIFIED: R3 四條己方 finding 與兩條他家 finding 均依實跑命令閉合；horizon 2 接線一致；same-file 假設被 service-level probe 反例推翻；scale receipt `n_events=10000`、`wall_clock_s`、`peak_rss_mb` 存在。
TESTS_RUN: `venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"`→3 passed；`venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar`→1 passed；in-memory `vals[i-k]→vals[i]` mutation→target assertion failed；`npx vitest run gap3 pendingFeatures`→4 files/22 passed；`npm run build`→rc0；`venv/bin/python -m pytest tests/api/ -q -k gap3_import`→15 passed；`venv/bin/python -m pytest tests/momentum/event_samples/ -q`→230 passed；`bash scripts/plain_docs_sync_check.sh`→rc0。
FAILURES_SEEN: 初次 in-memory mutation harness 因雙 staticmethod 包裝 TypeError，修正 harness 後得到預期決策根斷言失敗；直接 TestClient probe 受 Binance DNS startup 影響，改用相同 service/validator 路徑完成反例；`restore_golden_inventory.sh` 因 sandbox 禁寫 `.git/index.lock` 未執行，既有 golden dirty 狀態未變。
SCOPE_CHANGES: none；未改產品碼、測試、data_cache、root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未修改輸出；指出 verify provenance 語意與 same-file 路徑不一致。
HANDOFF_OUTPUT: handoffs/20260822-gap3-b5-review-r4-codex.md
HANDOFF_NOT_UPDATED: root HANDOFF.md 由 Claude 維護；本檔為本任務唯一產出。
STATUS: DONE
