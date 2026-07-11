# IC 1e+1b 全 epic 數據正確性簽核 R3（Codex）
日期：2026-07-11；範圍：R2 三層 FDR method 契約分叉之 SIGNFIX2 複驗；其餘全 epic 證據沿用 R2 並跑 targeted regression。

## Receipt：R2 六值邊界矩陣逐格重打
前置：`bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS，sha256=`b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043`。

| 顯式 method | direct `apply_fdr` | schema | bypass-consumer `_resolve_fdr_method` |
|---|---|---|---|
| `"fdr_bh"` | OK，q=`{a:0.02,b:0.04}` | OK | OK |
| `"FDR_BH"` | ValueError | ValidationError | ValueError |
| `" fdr_bh "` | ValueError | ValidationError | ValueError |
| `None` | ValueError | ValidationError | **OK，靜默 default=`"fdr_bh"`** |
| `""` | ValueError | ValidationError | ValueError |
| `"banana"` | ValueError | ValidationError | ValueError |

實跑：`OPENBLAS_NUM_THREADS=1 venv/bin/python - <<'PY' ...` 對三層×六值逐格列印 outcome；18 格中唯一違約為 bypass-consumer×顯式 `None`。
實跑：`OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py tests/momentum/test_ic_1eb_b3_xsec.py -q --tb=short -o log_cli=false` → 63 passed、1 warning、43.04s。
l65 inventory：測試前後 `shasum -a 256 tests/golden/l65/test_inventory.txt` 均為 `6f46bbbd3068ad9a5d6157434f9cb2b47558a21bbb627c4b2d5da71b8fa92f2b`，`git status/diff` 為空，未執行 restore。

## Docstring 與判定
`apply_fdr` docstring 與行為一致（僅 exact 值）；schema docstring 宣稱三層接受集合恆等且 `None` 被拒，但 consumer docstring/行為明訂顯式 `None` default，故跨層文件與行為仍矛盾。新增矩陣測試亦把 consumer×`None` 預期寫成 `default`，所以 63 綠未覆蓋派工要求「唯 exact 過、其餘全拒」。缺鍵採 schema default 可合法；顯式 `method=None` 必須與缺鍵區分並 raise。

全 epic 判定：**FAIL**。R2 的 casing／空白／空字串／banana 分叉已閉合，合法 BH regression 全綠；但顯式 `None` 仍由 consumer 靜默補預設，三層 exact-whitelist 契約未閉合，不得簽數據正確。〔REF:handoffs/IC1EB-SIGNOFF-R4-codex.md〕 〔SUPERSEDED:該輪 FAIL/紅燈紀錄已由後續修復輪與 ic1eb-epic-final-gate 綠收據取代;審計軌跡保留〕

ASSUMPTIONS_VERIFIED: 雙 reconcile stamp；三層×六值 18 格獨立 probe；三處 docstring/實碼/參數化測試交叉核對；63 targeted regression；l65 inventory 未變。
TESTS_RUN: 上述 reconcile、18 格 Python probe、63-test targeted suite、inventory 前後 hash/diff，均附實跑摘要。
FAILURES_SEEN: bypass-consumer 對顯式 None 回傳 fdr_bh；現有測試將此違約固化為 default，因此假綠於本次契約。
SCOPE_CHANGES: 僅新增 `handoffs/IC1EB-SIGNOFF-R3-codex.md`；未改 production/test/data_cache/HANDOFF。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無修改；現碼合法 canonical 數值路徑不變，顯式 None 的 consumer fail-open 契約縫仍在。
DATA-CORRECT: FAIL
