# VERIFYGATE B2 執行交接（Composer / cursor-agent）

## 完成項
- `scripts/verification_claim_check.py`：claim-object 偵測、normalize、段切分、模式判定、citation/operational、check_backing（receipt+audit+sha256+極性+runtime_class+scope）、claim_fingerprint、VERIFY-EXEMPT 窄類、未知詞 WARN、list-open 子指令。
- `handoffs/pending_verifications.jsonl`：空 ledger 檔（append-only reducer 讀寫）。
- `tests/governance/test_verify_gate.py`：追加 V2–V11、V17 + 2 mutation 探針；測試隔離用 `VERIFY_GATE_RECEIPTS_DIR` / `VERIFY_GATE_AUDIT_LOG` / `VERIFY_GATE_PENDING_LEDGER`。

## 驗證
- `venv/bin/python -m pytest tests/governance/test_verify_gate.py -q` → 20 passed
- V7 專項 exit 0（WARN 2 條為預期 stderr，非 fail）
- 測試後 `handoffs/run_receipts/`、`.claude/gate/verify_audit.log` 無改動；`pending_verifications.jsonl` 為本批新增 untracked 交付物

## 決策
- `docs_spec` / fenced / 引號內容 fail-open；HANDOFF/commit/RESULT operational fail-closed。
- 測試隔離模式下跳過 W12 git tracked 檢查（receipt 在 tmp 目錄即視為可引用）。
- 同段多 claim 以 `;` 切分；pending 關閉後純 DONE/ready 狀態宣稱放行。

## 未做（B3 範圍）
- PreToolUse / git hook / CI / health

---

## B2-FIX（2026-07-01，Codex review 5 BLOCKING 閉合）

### 修正
1. **B2-CODEX-1**：`正確紅`/`探針紅`/`搞定` 加入 STRONG_POLARITY_RE；從 unknown WARN 清單移除前兩者。
2. **B2-CODEX-2**：`claim-context: discussion` 僅在 fenced/blockquote 生效；自 SUPERSEDED_RE 拆出。
3. **B2-CODEX-3**：移除檔名（FORENSICS/DELIB 等）單獨免責；新增 `_is_citation()`（引號內極性 / 歸屬否定 / fenced-quote）。
4. **B2-CODEX-4**：node-id scope 須全等或 test 函式後綴一致；不再以共用檔路徑 substring 放行。
5. **B2-CODEX-5**：`reduce_events()` close 須驗 fingerprint/scope/runtime + receipt 存在且有 audit。
6. **附帶**：`真紅` 極性改為 success（非 failure）；先前與 `紅燈` 混判會讓 scope 測試誤報。

### 測試
- 新增 5 組 B2 回歸（同義詞 / inline discussion / FORENSICS operational / node-id scope / 偽 close）。
- `test_v11` close 改用具 audit 的真 receipt。

### 驗證原文
- pytest：`27 passed in 6.77s`
- V7：`exit 0`（WARN 驗證通過×2，預期）
- 真實路徑零污染：pending/audit/receipts 測試前後皆 0
