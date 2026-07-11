# 20260711-IC1EB-SIGNFIX2

- **正在做/已完成**: R2 三層 FDR method exact-whitelist 一致化（apply_fdr / schema / _resolve_fdr_method）
- **待辦**: Claude 驗收 + Codex 重簽（R2 縫閉合後）
- **阻塞**: none
- **本次決策**: 刪 strip/lower；禁 raw-or-default；None/缺鍵 consumer→schema 預設；其餘顯式非 exact "fdr_bh" 三層 raise；參數化 6×3 矩陣
- **踩坑提醒**: consumer None≠apply_fdr None（前者 default、後者 raise）須在矩陣逐格寫死；接受集合字面仍恆等 {"fdr_bh"}
- **VERIFY**: `OPENBLAS_NUM_THREADS=1 venv/bin/python -m pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py tests/momentum/test_ic_1eb_b3_xsec.py -q` → 63 passed/42.18s；詳 `handoffs/IC1EB-SIGNFIX2-RESULT.md`
