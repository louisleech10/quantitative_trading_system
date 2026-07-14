# IC1C SPEC Adversarial 審查任務書(task-id: IC1C-SPECREV)

**角色**:你是獨立 adversarial 審查委員。目標=獵洞,不是背書。確認式 review 無效;每個 finding 須附可證偽反例或具體攻擊路徑。

**標的**:`docs/IC1C_NETIC_SPEC.md`(1c Net IC 量綱正確化,RISK-HIT: a,b,d)

**必審面向(全量看,禁分角度)**:
1. **量綱修法二案裁決**:§A 案 A(IC 同單位化)vs 案 B(拆報告+損益平衡點,Claude 推薦)。你必須自己讀 `momentum/Analysis/net_ic_analyzer.py` 全檔+`ic_filter_orchestrator.py:1942-1956`,獨立判斷哪案正確、Claude 推薦理由是否站得住、有無第三案。
2. **consumer-map 完整性**:§C 列的下游(ic_reporter :631/:150/:209/:570/:773、ic_analysis_service:1140、api/models/ic_models.py:28、frontend NetICChart/DeepAnalysisConfigPanel/store/types)有無漏。自己 grep 驗證,勿信 SPEC。
3. **§G golden 設計**:行為變更型「選擇性等值」是否可證偽?能否抓到「改了不該改的」?
4. **Task 1.2 factor_returns 來源存在性**:SPEC 聲稱「來源=既有 factor return 計算模組」——實際存在嗎?找出具體模組/函式,不存在=BLOCKING。
5. **fail-closed 語意**:cost_enabled+缺 cost_bps→422;breakeven 無因子報酬→NaN+reason。有無繞過路徑(舊 request/預設值殘留 5.0 bps)?
6. **§V mutation M1-M4** 是否真能證偽;既有測試(tests/phase25、tests/momentum/Analysis、tests/api)哪些斷言會紅、SPEC 有無漏列。
7. **timeframe 情境掃描**(Phase 3)語意是否足夠(使用者:持倉 1h~1w 不定,禁單一 timeframe 假設)。

**產出**:寫到 `handoffs/20260714-IC1C-SPECREV-<你的名字 codex|composer|grok>.md`。格式:每 finding 一節,`ID: <NAME>-<n>` + 嚴重度(BLOCKING/NON-BLOCKING/NIT)+ 證據(檔:行)+ 可證偽反例 + 建議修法。最後一行 verdict:`SPEC-REVIEW: APPROVE|REJECT(n BLOCKING)`。另須對修法二案明確表態:`RULING: A|B|第三案<描述>`。

**約束**:唯讀審查,除產出檔外不得改任何檔;不得跑會寫 data_cache 的命令;兩輪內解不了的疑問記為 finding 而非硬猜。
