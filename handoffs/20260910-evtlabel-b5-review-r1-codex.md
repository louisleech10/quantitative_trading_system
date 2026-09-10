## CODEX-R1-P1-01
**斷言**：無 `label_origin` 的舊 scenario-C/legacy records 會被 target staging 當成來源字面 `"0"/"1"`，造成倖存者 provenance 假揭露（P1，信心 10/10）。
**碼證**：`api/services/ic_analysis_service.py:1015-1023` 使用 `rec.get("label_origin", rec.get("label"))`；`event_import_models.py` 明示舊 scenario C 可缺欄；實檔掃描 20260901 批為 60/60 無 `label_origin`。
**來源摘要**：契約允許 optional provenance，不能以答案值代填；最小修法只收非 null `label_origin`（缺席即空 list），或明示 binary 拒絕無 provenance 批。source_digest: 12c334f0aa1f
## CODEX-R1-P1-02
**斷言**：`event_label_mode != auto` 且 `event_import_id=""` 時 target model 只檢查 `is None`，route/service 的 truthy guard 會跳過五階段，靜默跑成一般分析而非 fail-closed（P1，信心 10/10）。
**碼證**：`api/models/ic_models.py:282-285`、`api/routes/ic_analysis.py:122-123`、`api/services/ic_analysis_service.py:1876,1960`；target hook 亦以 truthy ID 選事件分支。
**來源摘要**：Task 3.2 要求非 auto 必有批；最小修法在 request boundary 以 `not self.event_import_id` 擋 blank，並加空字串回歸測試。source_digest: 12c334f0aa1f
## CODEX-R1-P1-03
**斷言**：倖存者落檔先處理 `negative_control_failed`、後驗證 symbol/timeframe；兩者同時缺失時會把結構性 `identity_missing` 誤報成統計性負對照失敗（P1，信心 9/10）。
**碼證**：`momentum/Analysis/ic_filter_orchestrator.py:5552-5583`；既有 target tests 只分別覆蓋 `identity_missing` 與 negative-control，沒有 combined case。
**來源摘要**：identity 是輸出身分前置條件；最小修法把 identity validation 移到 suppression early return 前，保留合法身分的 suppression 行為。source_digest: 12c334f0aa1f
## CODEX-R1-P1-04
**斷言**：前端固定請求 `view=light`，但 target metadata 白名單漏 `label_mode` 與 `event_label_rule`，故頁面讀取的模式 banner／規則揭露在正常 light response 中消失（P1，信心 10/10）。
**碼證**：`ic_result_paging_contract.json:17-24` 無兩鍵；`api/services/ic_result_projection.py:241-243` 僅保留白名單；`useICAnalysis.ts:132` 請求 light，`page.tsx:710-713` 讀兩鍵。
**來源摘要**：最小修法把兩個已由 backend 寫出的 metadata key 加入 allowlist，並增 projection→page integration assertion；不改數值計算。source_digest: 12c334f0aa1f
## Verdict
1a/1b：不是所有實批都有 `label_origin`；舊 scenario C/legacy 可缺，新契約批應有；target 對缺席批的 fallback 是 P1-01。
2a/2b：合法 binary 必須有非空 `import_id`；`event_timestamps` legacy 不供 binary map，stage3 檢查本身正確但 blank-ID bypass 是 P1-02，應在 request boundary fail-closed 且不產 survivor。
3a/3b/4a/4b：目前 suppression 優先序不對，採 identity 先（P1-03）；`unavailable`+`negative_control_failed` 符合封閉 capability enum，優於新增 `suppressed`，無 4b finding。
5a/5b：target `_merge_binary_statistics` 對每列（含 unavailable）寫 `rank_biserial`，首列風險目前未成立；報告級 effective-mode metadata 是較穩定的未來準則。
6a/6b：最嚴重 banner 優先足以阻止 ML，但不足以保留所有診斷；P1-04 修好後應 danger first、其餘 warning/info 以次要列呈現（建議，非另列 finding）。
7：未見 >=10x 不必要複雜度；可在四個 P1 修正、真實 kline E2E/ML consumer 驗證完成後進 B6，當前 R1 不應直接放行。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF/CLAUDE/brief；3-family RECONCILE-STAMP=APPROVED；1a 真實 data_cache records 驗證；target diff static receipts。
TESTS_RUN: `git diff --check a98b3a84..12c334f0 -- momentum api tests frontend` rc=0；target `git show`/`rg` receipts；real records jq scan；completeness exact command rc=0。
FAILURES_SEEN: completeness 首跑缺 4 個 P1 source_digest；補上 target commit digest 後同命令 rc=0；brief 所載 backend/frontend/build/decoupling 未重跑。
SCOPE_CHANGES: review-only，未改程式、測試、契約或 HANDOFF；產出 `handoffs/20260910-evtlabel-b5-review-r1-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT: 本次無修改；P1-04 修法只暴露既有 metadata，會擴充 light response 欄位，無數值計算變更。
STATUS: DONE
