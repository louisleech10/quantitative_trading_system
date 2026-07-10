# IC 1e+1b B4 R2 複驗 — Codex
範圍：R1 五條 BLOCKING 逐一重打；FIX1 產物視為資料，結論以本輪實跑與讀碼為準。

1. **CLOSED — preset ON 覆寫**：`significance.fdr.enabled=false + active_preset=intermediate` 經 `_apply_tier_config` 為 `true`；同時覆蓋有/無 `stage_overrides` 兩型。RECEIPT：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py::test_t41_preset_intermediate_maps_fdr_on -q` → 1 passed/0.67s。
2. **CLOSED — OFF canonical method**：longitudinal stage5/SelectionScope 與 xsec OFF 均 `enabled=false, method=fdr_bh`，未以 method 表 OFF；production `method:none` grep 僅命中無 passed feature 時的 redundancy method，非 FDR。RECEIPT：兩節點 pytest（`test_t41_off_method_never_none` + `test_t41_xsec_metadata_has_alpha_effective_and_canonical_method`）→ 2 passed/0.78s。
3. **CLOSED — 真 e2e + 可證偽 gate**：測試由 H5 輸入呼叫 `analyze`，production 於 orchestrator:994 進 `_stage7_report`，stage7:2797 傳入 stage5 significance；report 的 stage5 removed 集合與 summary raw-p/q 重算集合逐態相等。RECEIPT：`test_t43_mg_two_state_fdr_gate_full_e2e` → 1 passed/2.10s；獨立反例 `p=.01,q=.20,alpha=.05` 直打 `_apply_thresholds` → `off=['counterexample'], on=[]`，證明 field/flag 斷言非恆真。
4. **CLOSED — 前端誠實欄位/tooltip**：`ICSummaryTable.tsx:330-349,397-419` 兩模式皆直接讀後端 t/p/q；xsec raw p 與 longitudinal t-stat 均有 header+cell；`FeatureTierPanel.tsx:59` 明載 xsec「不新增 p 閘」，`ICConfigPanel.tsx:193` 傳入 mode；舊 i.i.d. resolver/1.96 grep 為 0。RECEIPT：`npm run build` → exit 0，20/20 static pages；僅 4 個既存 hook lint warnings。
5. **CLOSED — method consumer + xsec alpha**：`_resolve_fdr_method` 於 stage5/xsec 傳入 `apply_fdr(..., method=...)`（orchestrator:1265,2524；validator:155）；bonferroni 實跑 q 與 consumer 輸出一致；xsec `fdr.alpha_effective=0.05`。RECEIPT：method+xsec 兩節點 pytest → 2 passed/0.78s。

抽查：B4 全檔 `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q` → 11 passed/2.55s；B1/B2/B3/tier 四檔 → 53 passed, 1 NumPy warning/39.82s；`rg -n "from api\\." momentum` → 0。
INVENTORY：各測試/build 後 `git status --short tests/golden/l65/test_inventory.txt` 皆空，未覆寫，故未執行 restore。
ASSUMPTIONS_VERIFIED：五條反例均以本輪 production code/測試重打；e2e 未直呼 stage5、未手動注入 report significance。
TESTS_RUN：B4 11 passed；五條 targeted receipts 全 passed；相關回歸 53 passed；frontend build exit 0；decoupling grep 0。
FAILURES_SEEN：首次 method:none grep 因 zsh pattern quoting 失敗；改用安全單引號 pattern 後完成，無產品失敗。
SCOPE_CHANGES：僅新增本檔；未改 production/tests/data_cache/HANDOFF.md；未需 restore inventory。
NUMERIC_OR_SCHEMA_IMPACT：本輪唯讀複驗，無數值/schema/輸出大小變更。
VERDICT: PASS
