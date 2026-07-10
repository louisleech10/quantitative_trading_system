# IC 1e+1b B4 Code Review — Codex（非實作者）
範圍：未 commit B4 diff；依 TODO Phase 4 全文與 SPEC D-F/D-G；未採信實作者自報。

1. **FINDING（BLOCKING）T-4.1 每跳鏈**：custom 的 `store JSON→FeatureTierRequest→_build_config_override→_apply_tier_config→stage5→report` 可通，但三個非 custom preset 在 store `getEffectiveConfig` 不送 `fdr_correction`（store:315-325），backend preset 分支也不映射它（orchestrator:3305-3325），UI 的 preset=true 可靜默丟失。
   可證偽反例：以 `significance.fdr.enabled=false + active_preset=intermediate` 實跑 `_apply_tier_config`，輸出仍 `false`；若鏈完整應被 UI preset ON 覆成 true。B4 test 的 `_tier_payload` 是手刻且永遠 `active_preset=custom`，不能抓此事故。
2. **FINDING（BLOCKING）禁第四命名／OFF 唯一真相**：longitudinal report、SelectionScope、xsec report 在 OFF 另寫 `method="none"`（orchestrator:1319,2547,2565），違反 D-G「唯一表述=canonical enabled=false；禁其他 off marker」。
   可證偽反例：真 custom OFF stage5 收據=`enabled:false, method:none, scope_method:none`；xsec 收據同為 `enabled:false, method:none`。正確反例應保持 canonical `method=fdr_bh`，只由 enabled 表態。
3. **FINDING（BLOCKING）兩態 e2e**：7 tests 確實不 mock `_apply_tier_config`，且 `threshold_log.fdr_enabled === significance.fdr.enabled`；但直接呼叫 private `_stage5_statistical_validation`，report 腿再手動把 `result["significance"]` 注入 `_build_report_metadata`，不是真 `analyze→stage7→report` 端到端。
   可證偽反例：若 production `_stage7_report` 丟掉 significance，現測仍會綠；`_gate_features` 選了 field 卻不使用計算結果，末尾 `len(on)<=len(off) or on!=off` 在前文已證集合不同後恆真。
4. **FINDING（BLOCKING）前端誠實顯示**：null 型別、finite formatter、q 欄、CI 固定 `--`、刪 i.i.d. 推導均 PASS；但 xsec 缺 raw p 欄，longitudinal 缺 t-stat 欄，未達 TODO「t-stat/p/q 三欄直接讀後端」。
   可證偽反例：有效 xsec `p_value=0.0123` 在表格無任何 cell；有效 longitudinal `t_stat=4.2` 同樣不可見。另 FeatureTierPanel 無 mode prop，xsec 仍顯示「關閉時用 raw p 閘」，但 SPEC D-H 明定 xsec 無門檻行為，tooltip 不誠實。
5. **PASS ic_config_schema 既有預設**：`git diff -U0` 僅新增兩個 significance schema 與 ICConfig 欄，其他欄預設零修改；舊 JSON 無 significance 實跑預設 ON。
   可證偽反例：任何既有 schema 行出現在 `-U0` 修改 hunk 即轉 FINDING；本次沒有。
6. **FINDING（BLOCKING）xsec schema 消費不完整**：真 xsec 路徑會消費 tier-mapped `enabled` 與 `significance.maxlags`（收據 false/6），但 repo 無 production 讀取 `significance.fdr.method`，兩路皆硬編 fdr_bh/none；xsec metadata 也缺 canonical `fdr.alpha_effective`。
   可證偽反例：全 production grep `significance.fdr.method|.fdr.method` 為 0；把 schema method 改成其他值不會影響 consumer，證明欄位是幽靈 config。

RECEIPTS：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b4_fullstack.py -q`→7 passed/1.79s；iid grep→0；別名 grep 僅允許 UI `fdr_correction`、internal mirror `fdr_enabled`，另抓到上述 `method:none`。〔REF:handoffs/IC1EB-B4-IMPL-RESULT-FIX1.md〕
TYPECHECK：`frontend/npx tsc --noEmit` fail，10 個既存 feature-factory test typing errors，未指向本批檔；編排端自報 build 綠僅列為外部 receipt，不冒稱本委員實跑。
INVENTORY：pytest 前後 `git status --short tests/golden/l65/test_inventory.txt` 皆空，未需 restore。
ASSUMPTIONS_VERIFIED：custom 真映射；preset 反例；stage5/xsec enabled+maxlags；OFF method；前端欄位與 formatter均由實碼/實跑核對。
FAILURES_SEEN：tsc 既存 10 errors；B4 tests 全綠但未攔上述反例。
SCOPE_CHANGES：僅新增本檔；未改 production/tests/data_cache/HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT：審查未改數值/schema；受審 diff 新增 schema，且 OFF metadata 命名不合規。
VERDICT: BLOCK
