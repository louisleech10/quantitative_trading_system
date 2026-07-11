# IC1EB-SIGNFIX3 交接

- **正在做/已完成**: R3 殘縫修復——`_resolve_fdr_method` 顯式 `method=None` vs 缺鍵分離
- **待辦**: Claude 重跑 Codex R3 簽核；R3 PASS 後與 signfix 一起 commit
- **阻塞**: none
- **本次決策**: dict 缺 `method` 鍵→schema 預設 `fdr_bh`（合法）；顯式 `method=None`→`ValueError`；矩陣測試 None 格改 raise、新增缺鍵格 default
- **踩坑提醒**: object 路徑須用 `hasattr` 區分缺屬性與顯式 `None`；勿再把兩況寫進同一 `default` 測試分支
