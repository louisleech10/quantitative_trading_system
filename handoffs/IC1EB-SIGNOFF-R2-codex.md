# IC 1e+1b 全 epic 數據正確性簽核 R2（Codex）
日期：2026-07-11；範圍：R1 唯一 blocker「FDR method fail-open」修復複驗；R1 其餘全 epic 證據沿用並以本輪 regression 查回歸。

## 複驗 receipt
1. 前置：`bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS，body sha256=`b77932d8…043`。
2. 原反例 direct：`OPENBLAS_NUM_THREADS=1 venv/bin/python -c '...apply_fdr(...,method="banana")'` → exit 1，`ValueError: Unsupported FDR method='banana'`；不再回 raw p。
3. 原反例 config 鏈：`ICConfig.model_validate({significance:{fdr:{enabled:true,method:"banana"}}})` → exit 0 probe，捕獲 `ValidationError`，位置 `significance.fdr.method`、`literal_error`。
4. 邊界矩陣 probe（direct/schema/繞過 schema consumer）：canonical `fdr_bh` 三層接受且 q=`{a:0.02,b:0.04}`；schema 對 `FDR_BH`、` fdr_bh `、`None`、`""` 全部 `ValidationError`。
5. **新縫**：direct `apply_fdr` 對 `FDR_BH` 與 ` fdr_bh ` 會 `.strip().lower()` 後接受（`statistical_validator.py:179`）；繞過 schema 的 `_resolve_fdr_method` 同樣接受大小寫/空白，且把 `None`/`""` 以 `raw or default` 靜默改成 `fdr_bh`（`ic_filter_orchestrator.py:2689`），沒有依修復宣告「白名單以外一律 raise」。
6. 此縫目前仍執行 BH、未重現 raw-p fail-open；但三層對同一 canonical 欄位的接受集合不同，且 consumer 的 fail-closed docstring/修復 receipt 與實際行為矛盾，無法簽「修復無新縫」。
7. `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py -q` → 46 passed、1 warning、41.30s；現有 tests 未覆蓋上述矩陣。
8. `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_ic_1eb_b3_xsec.py -q` → 11 passed、1.95s；xsec 無回歸。
9. diff 核對：schema 已是 `Literal["fdr_bh"]`；`adjust_multiple_comparisons` 本體未動；合法 method 的 HAC/BH、SelectionScope、ON/OFF、xsec 與 R1 G-1/G-2/G-3 簽核依據未見新反證。
10. l65 inventory：測試前後 `git status --short -- tests/golden/l65/test_inventory.txt` 均空，未覆寫，故未執行 restore；除本檔外未改檔。

## 全 epic 判定〔REF:handoffs/IC1EB-SIGNOFF-R4-codex.md〕 〔SUPERSEDED:該輪 FAIL/紅燈紀錄已由後續修復輪與 ic1eb-epic-final-gate 綠收據取代;審計軌跡保留〕
R1 唯一 raw-p fail-open 主反例已閉合，合法 canonical 路徑 regression 全綠；但本輪明示必驗的 method 大小寫／空白／`None`／空字串暴露跨層契約分叉。需讓 `apply_fdr` 與 `_resolve_fdr_method` 對所有非精確 `"fdr_bh"` 值一致 raise，並補 direct+schema+consumer 參數化回歸後再重簽。

ASSUMPTIONS_VERIFIED: reconcile 雙章；banana direct/config 反例閉合；三層 edge matrix；合法 BH、B2/B4、xsec regression；共用 util 未動；l65 inventory 未變。
TESTS_RUN: 上述 reconcile、兩個 Python probe、46-test targeted suite、11-test xsec suite，均附實跑結果。
FAILURES_SEEN: 驗收反例成功證偽 exact-whitelist 一致性；測試套件本身無失敗。
SCOPE_CHANGES: 僅新增 `handoffs/IC1EB-SIGNOFF-R2-codex.md`；無 production/test/data_cache/HANDOFF 修改。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無修改；現碼非法 casing/空白仍算 BH，None/空字串 consumer 仍預設 BH，與 schema Literal 拒絕語意分叉。
DATA-CORRECT: FAIL（原 raw-p fail-open 已閉合，但 method 大小寫/空白及 consumer None/空字串未依 exact whitelist fail-closed，三層契約仍有新縫）
