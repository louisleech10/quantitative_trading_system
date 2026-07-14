# IC1CFR-STOPGAP TODO r3 adversarial review — Codex
task-id: `IC1CFR-STOPGAP-TODO` | date: 2026-07-14 | basis: SPEC v1.0 Frozen + TODO r3 + RECONCILE T-S9~T-S12

結論: APPROVE。r2 的 4 個 BLOCKING 全數關閉；r3 新洞掃描未發現 BLOCKING。

1. **B1 CLOSED（T-S9）**：sanitizer 新檔已定死為 `momentum/Analysis/factor_return_sanitizer.py`，且禁 import api。七類掛點各有可定位具名測試：cache hit、raw JSON、task storage/get round-trip、CSV、AI JSON、Markdown、export_all；另有 idempotent 測試。
2. **B2 CLOSED（T-S10）**：B2 gate 已定為 `python scripts/ic1cfr_stopgap_freeze.py --check-nodeids`；腳本自跑與 B0 相同的 `tests/momentum/ tests/api/ tests/phase26/ -q`，解析 failed+collection-error，與 frozen baseline 做差集，新增失敗非空即列出並 exit 1，無人工豁免。
3. **B3 CLOSED（T-S11）**：direct constructor allowlist 已明列 `momentum/factories.py:454`，並保留 orchestrator direct runner 與 phase24 analyzer tests；factory caller 與 direct constructor 分類未混用，B0 artifact/test 共用 scanner 正規化規則。
4. **B4 CLOSED（T-S12）**：三個 Vitest 路徑為獨立 CLI 參數。實跑完整命令 rc=0，現況選中既有 `NetICChart.test.tsx`（1 file/8 tests passed）；只傳尚不存在的 FactorReturn/FactorEquity 兩檔時 rc=1，Vitest 明列兩個獨立 filters，證明命令語法正確，實作後可選中新增檔。

新洞掃描：sanitizer 的 dict 契約可在 cache-hit 對 `DeepAnalysisReport.results` 套用後回填，不要求 momentum→api 依賴；現有七類出口、factory/direct caller、前端檔名與 package script 均可按 TODO 落地。未發現 scope、數值品質或 gate 自相矛盾。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、Frozen SPEC、TODO r3、RECONCILE、Codex r2 review；以現碼核對 DeepAnalysisReport/cache/API serializer/reporter/caller 與前端測試檔實況。
TESTS_RUN: `npm --prefix frontend run test -- src/components/ic-analysis/FactorReturnChart.test.tsx src/components/ic-analysis/FactorEquityCurveChart.test.tsx src/components/ic-analysis/NetICChart.test.tsx` → PASS, 1 file/8 tests, rc=0；同命令移除 NetIC 路徑 → expected no test files, rc=1，輸出列兩個獨立 filters；`rg` caller 掃描確認 factories.py:454/orchestrator/phase24/tmp 命中。
FAILURES_SEEN: 兩個尚未建立的前端測試檔單獨 filter 時 rc=1（預期且用於語法驗證）；無未解決失敗。
SCOPE_CHANGES: 僅新增本 review 檔；APPROVE 後僅在指定 RECONCILE 的 `## 戳記` 後追加一行；未改 HANDOFF.md、docs、runtime、tests、data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none（文件唯讀審查）。
TODO-REVIEW-R3: APPROVE
