# 20260711-IC1EB-SIGNFIX

- **正在做/已完成**: FDR method fail-closed（codex 簽核 FAIL 洞）
- **待辦**: Claude 驗收 + 可重跑全 epic 簽核
- **阻塞**: none
- **本次決策**: apply_fdr 白名單 `fdr_bh` only raise；schema `Literal["fdr_bh"]`；`_resolve_fdr_method` 同步 raise；**不動** `adjust_multiple_comparisons` 本體
- **踩坑提醒**: 原 B4 用 bonferroni 證 method 非幽靈——限域後改以 fdr_bh 消費+typo schema/resolve raise 證 fail-closed；共用 util 仍 fail-open 屬刻意隔離
- **VERIFY**: `pytest tests/momentum/test_statistical_validator.py tests/momentum/test_ic_1eb_b2_wiring.py tests/momentum/test_ic_1eb_b4_fullstack.py -q` → 46 passed/40.42s；b3 11 passed；詳 `handoffs/IC1EB-SIGNFIX-RESULT.md`
