# IC 1e+1b 全 epic 數據正確性簽核 R4（Codex）
日期：2026-07-11；範圍：R3 唯一殘縫「consumer 對顯式 method=None 靜默補預設」之 SIGNFIX3 終驗；其餘全 epic 證據沿用 R3/R2，並重跑 targeted regression。

## Receipt
1. `bash scripts/reconcile_stamps_check.sh handoffs/IC1EB-RECONCILE.md codex,composer` → PASS；body sha256=`b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043`。
2. 獨立實跑 `OPENBLAS_NUM_THREADS=1 venv/bin/python - <<'PY' ...` 六值×三層 18 格 probe：`"fdr_bh"` direct/schema/consumer 全 OK，q=`{a:0.02,b:0.04}`、n_tests=2。
3. 同 probe：`"FDR_BH"`、`" fdr_bh "`、`None`、`""`、`"banana"` 的 direct/schema/consumer 逐格皆為 ValueError/ValidationError/ValueError；`MATRIX_ASSERTIONS: PASS (18/18)`。
4. 缺鍵獨立格：`apply_fdr` 參數缺省、schema 缺 method、consumer raw dict 缺 method 均得 `"fdr_bh"`；`MISSING_KEY_DEFAULT: PASS`，與顯式 None 已分離。
5. `OPENBLAS_NUM_THREADS=1 venv/bin/python - <<'PY' ... inspect.getdoc ...` → apply_fdr / SignificanceFdrSchema / `_resolve_fdr_method` 三處皆含 exact-whitelist、顯式 None 拒絕、缺省/缺鍵合法預設的相容語意；`DOCSTRING_CONSISTENCY_ASSERTIONS: PASS`。
6. 實碼核對：consumer 已移除 `str(raw or default).strip().lower()`；只有缺 method 鍵/屬性才 default，鍵存在且非精確值即 raise；矩陣測試將 None 格改為 raise，另列 missing-key default。
7. `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py tests/momentum/test_ic_1eb_b3_xsec.py -q --tb=short -o log_cli=false` → 64 passed、1 warning、43.65s。
8. l65 inventory 測試前後 `shasum -a 256 tests/golden/l65/test_inventory.txt` 均=`6f46bbbd3068ad9a5d6157434f9cb2b47558a21bbb627c4b2d5da71b8fa92f2b`；scoped `git status/diff` 空，故未執行 restore。

## 判定
R3 唯一殘縫已閉合：顯式 `None` 不再與缺鍵混同，三層接受集合均為精確 `{"fdr_bh"}`，非法值 fail-closed；合法 BH、B2/B4、xsec regression 全綠，且未出現反證推翻 R3 所沿用之全 epic G-1/G-2/G-3 與數據正確性證據。全 epic 判定：**PASS**。

ASSUMPTIONS_VERIFIED: 雙 reconcile stamp；獨立 18 格矩陣；缺鍵三層預設；三處 docstring/實碼/參數化測試一致；64 targeted regression；l65 inventory 未變。
TESTS_RUN: 上述 reconcile、兩段獨立 Python probe、64-test targeted suite、inventory 前後 hash/status/diff；結果均列於 Receipt。
FAILURES_SEEN: none。
SCOPE_CHANGES: 僅新增 `handoffs/IC1EB-SIGNOFF-R4-codex.md`；未改 production/test/data_cache/HANDOFF；inventory 未需 restore。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無修改；SIGNFIX3 保持 canonical BH 與缺鍵預設數值路徑，僅令顯式 None fail-closed。
STATUS: DONE
DATA-CORRECT: PASS
