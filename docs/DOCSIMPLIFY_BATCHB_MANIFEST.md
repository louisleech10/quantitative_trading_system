# 文檔簡化批次 B — B00 Disposition Manifest

> Baseline：既有 DEV/ARCH 唯讀；唯一 block 座標為 TARGETVIEW/ARCHVIEW。content hash 由 `scripts/check_doc_manifest_b.py` 的 normalization 與 parser 產生。

## Disposition Inventory

| ID | 原 heading | content-hash@line-span | 分類 | 承載 | 理由 | 文件 |
|---|---|---|---|---|---|---|
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 | First Principle思考和Ultra Think三步驟流程 | 9483f757fa93e3ece5e2874138ec5ab3ba2c68a297a72a6f2e5b0171b826d359@L67-L68 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-01 先驗證假設 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 概述::heading1 | 概述 | c16d67b4d98c8dd451b7a6090f4baec67cfc2510066fa6658acf083f8cfd0db1@L69-L72 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 概述::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-01 先驗證假設 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟1：初始生成::heading1 | 步驟1：初始生成 | f8a8f6e239fe8df6121925d0094f24c9660e8bdeabc64eec7553113475b9f03c@L73-L90 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟1：初始生成::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-02 初始生成 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟2：自我審查::heading1 | 步驟2：自我審查 | 744184eccf9176cd7ba63aee180528a2efacce2a5aa0629162fe76e3770c94fe@L91-L117 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟2：自我審查::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-03 自我審查 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟3：優化重構::heading1 | 步驟3：優化重構 | 809f1d02788faec66e988c338a41d3d6cbe8dfbeca256c7fc1c807b214596334@L118-L135 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟3：優化重構::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-04 優化重構 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::heading1 | 實際應用示例 | 7d71d5486d2eea0f831bf0bdd5f04cd1175d085a911b4af639f027537320cc78@L136-L236 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::heading1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-05 最小可證偽示例 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 | 代碼質量規範 | 74088832600f3984b8785d140af28a8784d9c5528b355031030b546a4ba5d081@L374-L375 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-01 DRY | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > DRY原則（Don't Repeat Yourself）::heading1 | DRY原則（Don't Repeat Yourself） | 2b3fb059b4657fd5cd55b5953619412966a8db4fd7be35d4862f41df6557fdd2@L376-L404 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > DRY原則（Don't Repeat Yourself）::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-01 DRY | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > KISS原則（Keep It Simple, Stupid）::heading1 | KISS原則（Keep It Simple, Stupid） | 85334935356e462f21de6d827acb2f516dd4967fc87a49c4d323dc0f7582b88b@L405-L439 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > KISS原則（Keep It Simple, Stupid）::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-02 KISS | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 函數設計原則::heading1 | 函數設計原則 | 6c162c8de0ee9ba9db35e57ec6961f58e030998a0d5477b8c7fcf09fe1963dc5@L440-L489 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 函數設計原則::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-03 函數單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 變量命名規範::heading1 | 變量命名規範 | b867d884f38e7cc9c9fddbcf5a6baabcef3ca9229c314800783954d627bbd418@L490-L512 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 變量命名規範::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-04 命名表意 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 避免深層嵌套::heading1 | 避免深層嵌套 | e0aee7b8a26bcfc211791cf7977a8a05fd955e72335edabed486057afded2dfc@L513-L546 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 避免深層嵌套::heading1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-05 降低巢狀深度 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範::heading1 | 日誌規範 | 35f5432d806c7a8e467a752a7531384a5320cc5f712a1da912ef1f264aac72b2@L547-L548 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-01 記錄決策邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 何時記錄Log::heading1 | 何時記錄Log | eb6b95d8b74a91e9ba13b4d6064c6be158c5de10ff5756482d6acd5ace446409@L549-L584 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 何時記錄Log::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-01 記錄決策邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > Log等級使用::heading1 | Log等級使用 | 267ccae192400f7e579d5333f9d96d4e1d1cdfa8d7748b465caf9f2728015f85@L585-L613 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > Log等級使用::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-02 INFO與ERROR分級 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > Log格式規範::heading1 | Log格式規範 | e55cc43224620969184f40b88123747aedf4a86d66c3051585c4d534405f3fdb@L614-L651 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > Log格式規範::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-03 結構化上下文 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 錯誤Log範例::heading1 | 錯誤Log範例 | e55f1ce614dd6503bc2ac02509d800857bebc63c62db8f05073d691509604226@L652-L684 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 錯誤Log範例::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-04 ERROR附exc_info | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 性能敏感的Log::heading1 | 性能敏感的Log | 281048826fb7a20677ca6bffbcf2e4ad0617e7409a9b89177c4c783922c57008@L685-L708 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 性能敏感的Log::heading1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-05 循環內大量log | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 | 錯誤處理規範 | 8268e1a33f3590ca86e4a2c4bd3835d5299a3bac6ca9270ef267def19fc6be27@L709-L710 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-01 fail closed | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 基本原則::heading1 | 基本原則 | d22546dd06333d8ba7a26466881edc02edd920b10c824c4fcf5d4c3f010647b1@L711-L720 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 基本原則::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-01 fail closed | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > Try-Catch使用::heading1 | Try-Catch使用 | 1dd304788ba80107436d32809df62bf8216244fa3de08987b6d5bfe5766b5c9f@L721-L758 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > Try-Catch使用::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-02 只捕獲可處理例外 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤重試機制::heading1 | 錯誤重試機制 | 2992cbd99a28a34c196e538421e281cd0bae1ba97e11189947e51e046274f90f@L759-L806 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤重試機制::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-03 可重試與不可重試 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 用戶友好的錯誤提示::heading1 | 用戶友好的錯誤提示 | d6b8cc43e1df465aa16f4578e3526fb230324f9add6efbf6b2eb0f286dd6c3bc@L807-L849 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 用戶友好的錯誤提示::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-04 對外錯誤可行動 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤傳播::heading1 | 錯誤傳播 | eaf7f82329d8aa1b6a13f34f11e92a1401ab982b14647b04272d630aeaf33de5@L850-L877 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤傳播::heading1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-05 保留錯誤因果 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 | LLM Coding規範 | 85a8320c996f1f9d22a2093ed415da951c5b664f146368f5bb932ebef81c4dea@L878-L879 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-01 需求含驗收邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的需求描述規範::heading1 | 給Claude Code的需求描述規範 | ead91666a6063f4b4e1e6f839c479f6236c0ea3eb9f07cd4b15dd0cad98c0126@L880-L926 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的需求描述規範::heading1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-01 需求含驗收邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 驗證生成代碼的Checklist::heading1 | 驗證生成代碼的Checklist | a9003f02214eab0f28a2ad53fd4a8fb1c842003992ce6fdfa4a9692494878387@L927-L973 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 驗證生成代碼的Checklist::heading1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-02 生成結果必驗證 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > Claude Code常見問題::heading1 | Claude Code常見問題 | 135346c46df46502b697591279b5c122058407dd937be223f9bf6ffb9bcf6312@L974-L1009 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > Claude Code常見問題::heading1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-03 禁止幻覺介面 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的提示範例::heading1 | 給Claude Code的提示範例 | 40273e294d045a51d1e7d99f410b5ae8c8d94aead59d8fa1e715294a16af2313@L1010-L1045 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的提示範例::heading1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-04 提示附真實上下文 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範::heading1 | 性能優化規範 | 5e5342c1eaa2a61ff8e279ba03b9c8a8e37c930678cc67c8ea7f2e5979781713@L1046-L1047 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-01 正確性優先 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 核心原則::heading1 | 核心原則 | 855e74c25656d929b423f6365a1c736de103181e72686979da116e465dc028ed@L1048-L1066 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 核心原則::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-01 正確性優先 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > M1優化策略::heading1 | M1優化策略 | bb657d6a782feec55e8ee5e270b2e81c98bd5de8fad7561fa0fcf0ede884a985@L1067-L1129 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > M1優化策略::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-02 硬體自適應 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 避免重複計算::heading1 | 避免重複計算 | 8bb59908925d41de9abcd714fe804300ea6df42f493bedd29a46504a2be50d95@L1130-L1160 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 避免重複計算::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-03 避免重複計算 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 使用緩存::heading1 | 使用緩存 | 23f0154c94cb6ce4d66f76b2305b8b3efdba07c20e653f53a7c5182f95a01fd7@L1161-L1186 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 使用緩存::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-04 cache key完整隔離 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 避免不必要的數據拷貝::heading1 | 避免不必要的數據拷貝 | 6fbde13c39408c493feab478e97fcc45acae2b048c6e01c9d3b7b22b7d983396@L1187-L1207 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 避免不必要的數據拷貝::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-05 避免不必要拷貝 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 性能分析工具::heading1 | 性能分析工具 | 539baf2534bd63468a903d14e44fcaafe8ff73c4f2f987e26706a60e04934b79@L1208-L1245 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 性能分析工具::heading1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-06 benchmark後優化 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範::heading1 | Python開發規範 | c0053215e59add993b7f2528ff8ef4f7add52020a7bb036168646b09d405278b@L1348-L1349 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-01 PEP 8 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > PEP 8風格指南::heading1 | PEP 8風格指南 | fe8a0fbee1770ee01a49738c51c4e67bf0b42b2e84bb616ac6bc5da488fe89b7@L1350-L1385 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > PEP 8風格指南::heading1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-01 PEP 8 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > 類型提示::heading1 | 類型提示 | 6e1e60243c61f512fbe631f602e12221aa519540deb4674cd94e46a35fd62a63@L1386-L1438 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > 類型提示::heading1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-02 完整type hints | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > Docstring規範::heading1 | Docstring規範 | 3ed82bd9d2de5835bbdf8fc4979454ab8a26b1db905873451d9ebb72b05cb04c@L1439-L1483 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > Docstring規範::heading1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-03 中文docstring | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > 異常處理::heading1 | 異常處理 | 8b99b343a2754930c4e05f6cee624a829c32010c507f1eb909d4ac88db71b9a3@L1484-L1518 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > 異常處理::heading1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-04 明確例外邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範::heading1 | 前端開發規範 | dff6578af208c1942fb44d0772eb5836a6d9a3943c8a2188f059dcb2d66f3e82@L1519-L1520 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-01 API與state完整型別 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > TypeScript規範::heading1 | TypeScript規範 | 2d8328a17e5bc3fd3bd3bd7ffb1d44d5e9cf8d03165a5871940d5b55d5b7430a@L1521-L1579 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > TypeScript規範::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-01 API與state完整型別 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > React組件規範::heading1 | React組件規範 | d52ee4d27347e7e18c2f1dbd7d3ee14425330e3f8ad44850778e71f52d7a8c76@L1580-L1659 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > React組件規範::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-02 元件單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > 狀態管理規範（Zustand）::heading1 | 狀態管理規範（Zustand） | 698f0193c92ac6ff3f38f3a780ea1fdf54dbb9e11976fa0bbce9261631777d25@L1660-L1711 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > 狀態管理規範（Zustand）::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-03 Zustand管理共享狀態 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > 性能優化（React）::heading1 | 性能優化（React） | 0c01bdc889ae20c7673130e6ee729fc41b31c82dfdd364b0e83c0b86a04f8b74@L1712-L1764 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > 性能優化（React）::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-02 元件單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > API調用規範::heading1 | API調用規範 | 0af7ffa9093ae35844e73681f1843d78747f3d6c29c04e6a66e56cefbffb5518@L1765-L1829 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > API調用規範::heading1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-05 loading empty error三態 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範::heading1 | 註釋規範 | 5fa24c7d9ca71e9feae05d092370025b785f87be1b3bd2cdc5f03c6c3f068dc8@L1830-L1831 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範::heading1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-01 解釋why與契約 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 何時需要註釋::heading1 | 何時需要註釋 | 1b1eccc81f5994eb8db77c5c697ceefce90d3120ece81b576de7562ee5315373@L1832-L1884 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 何時需要註釋::heading1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-01 解釋why與契約 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 何時不需要註釋::heading1 | 何時不需要註釋 | 9fa8dddeaed294dadae2558b08bb6ff461608a6c780ec36c56f85e3f646e8497@L1885-L1913 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 何時不需要註釋::heading1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-02 不重述程式碼 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 好的註釋範例::heading1 | 好的註釋範例 | 1b1a91a1589be86829a0ae845ee7ce23e3300fd64b7b2929c7fcb480e7e676d0@L1914-L1950 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 好的註釋範例::heading1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-03 註釋保持可驗證 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟1：初始生成::fence1 | 步驟1：初始生成 | 76bb4975b0ba790673fd26198b6f09fdd249aeb6c987e4341e9288baeb2283e4@L74-L89 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟1：初始生成::fence1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-02 初始生成 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟2：自我審查::fence1 | 步驟2：自我審查 | 523783dbd331da05ff9b125bc880ebae8234235b958995c66349f6d64643e51e@L92-L116 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟2：自我審查::fence1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-03 自我審查 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟3：優化重構::fence1 | 步驟3：優化重構 | 7dbc34b66f96c01cd41ade60f20c6860c09b31ac0c2d51ccde0aecbaec2fc9e0@L119-L134 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 步驟3：優化重構::fence1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-04 優化重構 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence1 | 實際應用示例 | 967914605751d8ca6a264d17d4a9bf26af77abcd4c9358d210e2d4ec31e5fa48@L139-L148 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence1 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-05 最小可證偽示例 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence2 | 實際應用示例 | 9f453fa90632a5ac2644774b4fd3c3d3fc752840d40b0aea6c5b71331eff9dcb@L153-L166 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence2 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-05 最小可證偽示例 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence3 | 實際應用示例 | 3c18c201108303b18fa188e8bd4ed02c77b55e35e26c73f099a263d18eb76576@L169-L176 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence3 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-05 最小可證偽示例 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence4 | 實際應用示例 | f1b85a11819a3bd9d4cd65a5e603f38d9bceb7862626580a669de492b2581716@L179-L233 | 壓縮留 | DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程 > 實際應用示例::fence4 → DEVELOPMENT_GUIDE.md::First Principle思考和Ultra Think三步驟流程::heading1 → INV-B-FP-05 最小可證偽示例 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > DRY原則（Don't Repeat Yourself）::fence1 | DRY原則（Don't Repeat Yourself） | ca266ddcbf770d7bf9b52792b9a77b33b3ff7d25a3b377601d09e2cec10eba01@L378-L403 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > DRY原則（Don't Repeat Yourself）::fence1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-01 DRY | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > KISS原則（Keep It Simple, Stupid）::fence1 | KISS原則（Keep It Simple, Stupid） | befe51e3f9ee38fee26fd9faf311f1a64af9b1912f1f6990cbf087beaee7fe4e@L407-L438 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > KISS原則（Keep It Simple, Stupid）::fence1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-02 KISS | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 函數設計原則::fence1 | 函數設計原則 | 0217bea386bf85571cfdf19f637a9bd05f734cd94affdae14f956da5ce70ee33@L442-L488 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 函數設計原則::fence1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-03 函數單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 變量命名規範::fence1 | 變量命名規範 | e5897012cc1cc10c0b35aa4f1b6f3313c116f353d1d2ac4068e457e7b05c42f0@L492-L511 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 變量命名規範::fence1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-04 命名表意 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::代碼質量規範 > 避免深層嵌套::fence1 | 避免深層嵌套 | 9ede2543815deb9408fa9b0abafdd5e155fe6fa17c3a043167e41399a09f1ae7@L515-L543 | 壓縮留 | DEVELOPMENT_GUIDE.md::代碼質量規範 > 避免深層嵌套::fence1 → DEVELOPMENT_GUIDE.md::代碼質量規範::heading1 → INV-B-CQ-05 降低巢狀深度 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 何時記錄Log::fence1 | 何時記錄Log | 86a340e5cb030b6fb2b72104cbe62d2169b0a3f334935b7eb7b174bbec4f1e2d@L551-L583 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 何時記錄Log::fence1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-01 記錄決策邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > Log等級使用::fence1 | Log等級使用 | 764211fc8bb8b4abde437d11633bb341ad01df6f23fafb14f0d9cd5d02250a01@L587-L612 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > Log等級使用::fence1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-02 INFO與ERROR分級 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > Log格式規範::fence1 | Log格式規範 | 05a2b2005d0b544dc5918d9158e762bec502e9f218de6da9edef3dbe5f01794a@L616-L650 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > Log格式規範::fence1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-03 結構化上下文 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 錯誤Log範例::fence1 | 錯誤Log範例 | 2fd8b549cc9eb7fe9f024f1322e5cc7416fc287c69742b60d3755e93bf246dbe@L654-L683 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 錯誤Log範例::fence1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-04 ERROR附exc_info | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::日誌規範 > 性能敏感的Log::fence1 | 性能敏感的Log | 623f9ab863757a59dad52912ab6c3cdc5dcd7f60460217de4fe7eca8cc16a93a@L687-L705 | 壓縮留 | DEVELOPMENT_GUIDE.md::日誌規範 > 性能敏感的Log::fence1 → DEVELOPMENT_GUIDE.md::日誌規範::heading1 → INV-B-LOG-05 循環內大量log | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 基本原則::fence1 | 基本原則 | de9c09602923ce4fcaa4b3a68d4ed1d45bcf98d4f4aa2422e383d64dc88fdd52@L713-L719 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 基本原則::fence1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-01 fail closed | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > Try-Catch使用::fence1 | Try-Catch使用 | f5269f3c5b849ad9160444e816e0540fa3335e09e7ad86cf89585c715b68f964@L723-L757 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > Try-Catch使用::fence1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-02 只捕獲可處理例外 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤重試機制::fence1 | 錯誤重試機制 | 047d3f95d7446d73febe8535363ef760cf6da28bff30db85f034a53e1cae921a@L761-L805 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤重試機制::fence1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-03 可重試與不可重試 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 用戶友好的錯誤提示::fence1 | 用戶友好的錯誤提示 | 906fea948c05d49c1177fd354b294a8f64612e7e756cdbbea2826201aadca576@L809-L848 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 用戶友好的錯誤提示::fence1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-04 對外錯誤可行動 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤傳播::fence1 | 錯誤傳播 | f934def21dd07e26eeed7e716df6cfb89ab8d26d251cb9c3ca411257aa44c429@L852-L874 | 壓縮留 | DEVELOPMENT_GUIDE.md::錯誤處理規範 > 錯誤傳播::fence1 → DEVELOPMENT_GUIDE.md::錯誤處理規範::heading1 → INV-B-ERR-05 保留錯誤因果 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的需求描述規範::fence1 | 給Claude Code的需求描述規範 | 7b1886c9f99359a6e90d62ad769efa6725e02d61660f60592b1b45e338e3106a@L882-L925 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的需求描述規範::fence1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-01 需求含驗收邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 驗證生成代碼的Checklist::fence1 | 驗證生成代碼的Checklist | 3f2812dad3bfaf691553b8f31531f80037cf2c16ec7e827b5191e0f085df090e@L929-L972 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 驗證生成代碼的Checklist::fence1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-02 生成結果必驗證 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > Claude Code常見問題::fence1 | Claude Code常見問題 | f9d7d61c9862e6639b8fa316a8a7d904ee73ed0247d6787e95889352eae43c0e@L976-L1008 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > Claude Code常見問題::fence1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-03 禁止幻覺介面 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的提示範例::fence1 | 給Claude Code的提示範例 | 828e8eaf7f989ef71d19bb5dacafd3ed0005a5c3e033821ded108ec2c9da76ae@L1012-L1042 | 壓縮留 | DEVELOPMENT_GUIDE.md::LLM Coding規範 > 給Claude Code的提示範例::fence1 → DEVELOPMENT_GUIDE.md::LLM Coding規範::heading1 → INV-B-LLM-04 提示附真實上下文 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 核心原則::fence1 | 核心原則 | edaa73fa25fdeaae4cbc8b50cb0376857fb3887dc72a50bd11a2817496a8acb5@L1050-L1065 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 核心原則::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-01 正確性優先 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > M1優化策略::fence1 | M1優化策略 | a307a35b265e37845459bd89c4f9815e0455d879bdbae39000f6bd5e33251d08@L1069-L1128 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > M1優化策略::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-02 硬體自適應 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 避免重複計算::fence1 | 避免重複計算 | 25a6bf9d4cdfad62f29cf5b716960f7de01522532f247281f34467fb288dc633@L1132-L1159 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 避免重複計算::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-03 避免重複計算 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 使用緩存::fence1 | 使用緩存 | e6345d346eccd4f718a792eab72ac211aded761257f7788584e0fc3ea03bb7c7@L1163-L1185 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 使用緩存::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-04 cache key完整隔離 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 避免不必要的數據拷貝::fence1 | 避免不必要的數據拷貝 | 4ddab57ad094f28074bbb5f0b59d3c675477ab45f2b22467d88fef9646b4ccb5@L1189-L1206 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 避免不必要的數據拷貝::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-05 避免不必要拷貝 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::性能優化規範 > 性能分析工具::fence1 | 性能分析工具 | 3807aec880198609675cc39cfa8d41573f695a02a948a3f9fc54467884e850fb@L1210-L1244 | 壓縮留 | DEVELOPMENT_GUIDE.md::性能優化規範 > 性能分析工具::fence1 → DEVELOPMENT_GUIDE.md::性能優化規範::heading1 → INV-B-PERF-06 benchmark後優化 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > PEP 8風格指南::fence1 | PEP 8風格指南 | 8c77b88410b2b532619830a801d1ac7fa20e32661f1daeb9d6ae777dc92c4435@L1352-L1384 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > PEP 8風格指南::fence1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-01 PEP 8 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > 類型提示::fence1 | 類型提示 | 89348d601152f6a5baf3e208004496c6baad6cebeac33b65d015c2c40cc6146e@L1388-L1437 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > 類型提示::fence1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-02 完整type hints | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > Docstring規範::fence1 | Docstring規範 | 9ce1eda63ba424ed310e082823980e1aa733cacae387676557a68e1db3e67024@L1441-L1482 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > Docstring規範::fence1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-03 中文docstring | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::Python開發規範 > 異常處理::fence1 | 異常處理 | 12c4c826c432bf814d4997c2cb719d973b9b3608280f9f962cdc66a9d1f398ad@L1486-L1515 | 壓縮留 | DEVELOPMENT_GUIDE.md::Python開發規範 > 異常處理::fence1 → DEVELOPMENT_GUIDE.md::Python開發規範::heading1 → INV-B-PY-04 明確例外邊界 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > TypeScript規範::fence1 | TypeScript規範 | 789d813a5e45546b11789e98829a15e0d00382efe0a51085f126c168304de741@L1523-L1578 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > TypeScript規範::fence1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-01 API與state完整型別 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > React組件規範::fence1 | React組件規範 | 6b4cf8f52273bbf50af936c0660a5b975230011c97ffcd6e78227436952b7e3e@L1582-L1658 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > React組件規範::fence1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-02 元件單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > 狀態管理規範（Zustand）::fence1 | 狀態管理規範（Zustand） | af38c77ff2f2d6408306df9ba8166a37356fe88a696b96f12e94c5cca1b9cd6c@L1662-L1710 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > 狀態管理規範（Zustand）::fence1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-03 Zustand管理共享狀態 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > 性能優化（React）::fence1 | 性能優化（React） | 002d211a4c030ac44361440eecddba5134ef83ccd0e627bf5ec63a6b4a283d78@L1714-L1763 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > 性能優化（React）::fence1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-02 元件單一職責 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::前端開發規範 > API調用規範::fence1 | API調用規範 | c9d203a26588e6857829d488e2cc7ada9d9639dee608089237d9f480fed07098@L1767-L1826 | 壓縮留 | DEVELOPMENT_GUIDE.md::前端開發規範 > API調用規範::fence1 → DEVELOPMENT_GUIDE.md::前端開發規範::heading1 → INV-B-FE-05 loading empty error三態 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 何時需要註釋::fence1 | 何時需要註釋 | 7e83e68f513df475cb43704ea3f430d497a0c19476b9feafcd389b31ade42106@L1834-L1883 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 何時需要註釋::fence1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-01 解釋why與契約 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 何時不需要註釋::fence1 | 何時不需要註釋 | 418b89d1ea993580ef9b15c12bca7039557f19b324324f68fb467a7420fbc0ac@L1887-L1912 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 何時不需要註釋::fence1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-02 不重述程式碼 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| DEVELOPMENT_GUIDE.md::註釋規範 > 好的註釋範例::fence1 | 好的註釋範例 | 645a6a14af5bf9b2e3d0c9f8568e9979e168a79cfc5762e0a219e1ee9e876053@L1916-L1947 | 壓縮留 | DEVELOPMENT_GUIDE.md::註釋規範 > 好的註釋範例::fence1 → DEVELOPMENT_GUIDE.md::註釋規範::heading1 → INV-B-COM-03 註釋保持可驗證 | 專案 invariant 收斂至章級條列；保留至多一組正反例 | DEV |
| ARCHITECTURE.md::解耦架構原則::heading1 | 解耦架構原則 | 7d14981118839bd48daef92818d897cf0bbdae17882d318fd8e7304066def54e@L1-L5 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 架構規則(canonical,與 CLAUDE.md 同步)::heading1 | 架構規則(canonical,與 CLAUDE.md 同步) | b106493e6138414b84dfd56f93ded418b833291121075190ad4991860baf8069@L6-L26 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::heading1 | Protocol 注入機制 | 8f2f2b6aa20fd5fea8adf7dc5b7b6efed3f8c4b15a6afa66dfdd05d5e1d31f93@L27-L71 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::heading1 → ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::heading1 → INV-B-ARCH-01 Protocol權威指向protocols.py | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Factory 模式::heading1 | Factory 模式 | 18df6dafb19af7aecfa0398ed7a5c02427628f51f28b9ba8d02ca5b57057902c@L72-L198 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > Factory 模式::heading1 → ARCHITECTURE.md::解耦架構原則 > Factory 模式::heading1 → INV-B-ARCH-02 Factory權威指向factories.py | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 呼叫流程::heading1 | 呼叫流程 | ae45159461addbf6fc4171600153a68df48cb9a59b68ba85486ee7072c7caa85@L199-L215 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Artifact Contract Table::heading1 | Artifact Contract Table | 4070e1a737438e19f4219116cd2edc0ff9e052540fffa801456a27f85645c14f@L216-L229 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求::heading1 | 持續解耦要求 | 94aa105551045cbbd880e62ac95dd67688041b29f36cf608fb0981dfb1c2ea8e@L230-L233 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求::heading1 → INV-B-ARCH-09 持續解耦指向PRODUCT_VISION | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 為何需要持續解耦？::heading1 | 為何需要持續解耦？ | 050d37911a08c079f0d91766fa977974a065107c1b025d0fede7ec2758cf9f01@L234-L247 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::heading1 | 解耦規則適用範圍 | fa99cf2d24e4eafd34829115c6dea21f67e28353a6fd172d1eae8725cd4c4bce@L248-L259 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::heading1 → INV-B-ARCH-03 解耦規則適用所有版本 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 新模組開發檢查清單::heading1 | 新模組開發檢查清單 | 33a0f710e55d328832e97ad99a00144e0a6d3fe5bf30fd816b914c84f81fecec@L260-L289 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 新模組開發檢查清單::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 新模組開發檢查清單::heading1 → INV-B-ARCH-04 新模組依canonical checklist | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 | 常見違規案例 | aa0c0dec2131b883ef1bedcfa75e33dfcc37be34788b043560fd2d8ee17182d1@L290-L356 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::heading1 | 解耦驗證工具 | 06b6eb9c90bffe2e389b45ccdcb324c78965df3caacfd473e51bdbaf9141169e@L357-L380 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::heading1 → INV-B-ARCH-06 scanner命令可重生 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 文檔同步要求::heading1 | 文檔同步要求 | 740ead04c36921d48b3ac130470abc0bd7952abf715dd0c849dc701b42994242@L381-L388 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 文檔同步要求::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 文檔同步要求::heading1 → INV-B-ARCH-07 架構變更同步canonical | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 實例：Task 1 (FeatureFactory) 解耦設計::heading1 | 實例：Task 1 (FeatureFactory) 解耦設計 | 56d42697cbbf06cfbe98cca6bec51483d1c0ed7cb59cd2725adffef08a3d4f9f@L389-L401 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 實例：Task 1 (FeatureFactory) 解耦設計::heading1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 實例：Task 1 (FeatureFactory) 解耦設計::heading1 → INV-B-ARCH-08 FeatureFactory案例指向專節 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 架構規則(canonical,與 CLAUDE.md 同步)::table1 | 架構規則(canonical,與 CLAUDE.md 同步) | 36b5d94815db28b4c3f3027a6e39a1ae414f5223c84296ecc5211153b5e6cbd5@L8-L16 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 架構規則(canonical,與 CLAUDE.md 同步)::table2 | 架構規則(canonical,與 CLAUDE.md 同步) | 792321bd6dd2e509287801c8fdd64758bd2f317f67c56a1865c83b6b67ec35ef@L20-L23 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::fence1 | Protocol 注入機制 | f88e003525369bfeee68fb0fa468998afda853cfdcc2fba9fa0264ae16cbd76f@L31-L70 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::fence1 → ARCHITECTURE.md::解耦架構原則 > Protocol 注入機制::heading1 → INV-B-ARCH-01 Protocol權威指向protocols.py | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Factory 模式::fence1 | Factory 模式 | 142bb624368e64c54712bc272270cff67adc3abf5074c6f4b71bb0a789fc1877@L76-L197 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > Factory 模式::fence1 → ARCHITECTURE.md::解耦架構原則 > Factory 模式::heading1 → INV-B-ARCH-02 Factory權威指向factories.py | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 呼叫流程::fence1 | 呼叫流程 | 20fa8d542446071f32ac372fb50dc8d696ef3c0bad2c0bc85ee0ad0327354a40@L201-L214 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > Artifact Contract Table::table1 | Artifact Contract Table | df0e9bbe82e4755658ab068ca6f8c1acc55ef0b0a6d3e1e0bcb3588da5ddb186@L218-L228 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 為何需要持續解耦？::fence1 | 為何需要持續解耦？ | 7a5864c5a2bf338c5bea0facd0375eaaa60c9e6bbc5587165a58381de8e3463c@L237-L241 | 原樣留 | N/A（hash 凍結） | 點名必留 contract／why／誠實現況 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::table1 | 解耦規則適用範圍 | ede2b22a3a189c0139d920bb34c9e7eb4287cd86773e8ab9341fabb04325cc8a@L250-L258 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::table1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦規則適用範圍::heading1 → INV-B-ARCH-03 解耦規則適用所有版本 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence1 | 常見違規案例 | 457d101fa542bb624419463b49140c68e0a73487579a4da3a954ec36fafe7037@L293-L300 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence2 | 常見違規案例 | c42efd2bb08fb5bac1d45d3945d7769459b2d93eb606a6ceb5e3d54fb4897a27@L303-L315 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence2 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence3 | 常見違規案例 | 08ab013fe6cc92dd2a2a851607dff1a3c09a1615925516fc1267e78dac80c805@L318-L323 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence3 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence4 | 常見違規案例 | d6033f7459238891f11c3c032f30ad77419414d34f003149cf058c1dd7d56fd8@L326-L331 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence4 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence5 | 常見違規案例 | 9aa5e09d4dadf6a47e52643631fc3d1a22eab34ed5dc00f8518ff23b77eee4f9@L334-L341 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence5 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence6 | 常見違規案例 | 76f80642deac8495b43db8674be21cdb2ddfd3e1ada211822ac8c1db0f121bb4@L344-L355 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::fence6 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 常見違規案例::heading1 → INV-B-ARCH-05 違規案例保留一組 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::fence1 | 解耦驗證工具 | 3966a03e0dae1b04a1c4e1f12856d1dc0a2d0d543c2cd57b7c02d8c139a73847@L360-L372 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::fence1 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::heading1 → INV-B-ARCH-06 scanner命令可重生 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |
| ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::fence2 | 解耦驗證工具 | 384f00149568728c60386d50830ebc2f6188d65c4b819d45fc0c7122187be85c@L375-L379 | 壓縮留 | ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::fence2 → ARCHITECTURE.md::解耦架構原則 > 持續解耦要求 > 解耦驗證工具::heading1 → INV-B-ARCH-06 scanner命令可重生 | 長枚舉收斂為 canonical pointer 或單一示例 | ARCH |

## B0 可重放施工圖

| Step | Baseline 行 | 行級編輯 | Oracle |
|---|---|---|---|
| 1 | DEV L1259-L1323；另 L1384（後續隨 Step 3 刪除） | L1259 Python fence 於呼叫結束後補裸 fence；9 個 selector 命中拆為語言 fence與首行，並在各 code 片段末補裸 fence | selector=0；長任務內容保留 |
| 2 | DEV L2373-L2387 | L2376 Python fence 在錯誤例後閉合；L2379 拆為 Python fence與 `workers = get_optimal_workers()`，隨後閉合 | 硬體章 fence-balanced |
| 3 | DEV L1326-L1405 | 整段刪除（含錯置 meta 指示、假 API H2、4 個未閉 language fence） | `^## GET /api`=0 |
| 4 | DEV L1259 起長任務末段 | Step 1/3 後複驗；若仍 unclosed 才於該節末補裸 fence。本 target 結果無額外補線 | unclosed=0、nested=0 |

## Fence / heading oracle

- Raw baseline parser receipt：`unclosed=2, nested=27, fence-aware H2=11`。
- Target parser receipt：`unclosed=0, nested=0, fence-aware H2=22`。
- `authorized_raw ∩ pre_fence_aware = ∅`（L1326-L1405 四個 raw heading 全在 baseline 未閉 fence 內）。
- 被吞 heading 重現集（target FA headings − raw baseline FA headings，已扣授權刪除區）：
  - `## Python開發規範`
  - `### PEP 8風格指南`
  - `### 類型提示`
  - `### Docstring規範`
  - `### 異常處理`
  - `## 前端開發規範`
  - `### TypeScript規範`
  - `### React組件規範`
  - `### 狀態管理規範（Zustand）`
  - `### 性能優化（React）`
  - `### API調用規範`
  - `## 註釋規範`
  - `### 何時需要註釋`
  - `### 何時不需要註釋`
  - `### 好的註釋範例`
  - `## 測試規範`
  - `### 單元測試`
  - `### 集成測試`
  - `### 測試覆蓋率`
  - `## Git工作流程`
  - `### 提交訊息規範`
  - `### 分支策略`
  - `## 代碼審查Checklist`
  - `### 人工審查Claude Code生成的代碼`
  - `## 安全性規範`
  - `### API密鑰管理`
  - `### 日誌中的敏感信息`
  - `### 輸入驗證`
  - `## 開發環境配置`
  - `### Python環境`
  - `### 前端環境`
  - `## 硬體自適應開發規範`
  - `### 禁止硬編碼資源數量`
  - `## 持續改進`
  - `### 定期審查`
  - `## 總結`

## 五個代表塊 calibration

| 代表塊 | disposition | 校準理由 |
|---|---|---|
| ARCH 架構規則 table1 | 原樣留 | R1-R7 誠實現況與兩個 `0 violation` scanner pointer 不可改寫 |
| ARCH 呼叫流程 fence1 | 原樣留 | Route→Service→Factory 責任鏈為點名必留 |
| ARCH Artifact Contract table1 | 原樣留 | 跨域 artifact schema/path contract 不可壓掉 |
| DEV 日誌／性能敏感 heading | 壓縮留 | 承載 `INV-B-LOG-05 循環內大量log` 永久 needle |
| DEV 錯誤／重試 heading | 壓縮留 | 承載 `INV-B-ERR-03 可重試與不可重試` 分類語意 |

## 點名必留 disposition 稽核

- 數據真實性 L0/L1/L2、真實 kline、禁 sanitized：不在 D1 壓縮範圍，既有 doc 唯讀且未入表。
- retryable/non-retryable 與 hot-loop log：分別綁定 INV-B-ERR-03、INV-B-LOG-05，非「刪」。
- 硬體自適應章、DEV 權威 banner、長時間任務節：不在 D1 壓縮範圍，target view 只執行 B0 結構修復。
- ARCH R2/R3/R4 誠實表、R8 殘留與 scanner 編號語意：架構規則 heading/table 原樣留。
- V2/V3 why、Artifact Contract、呼叫流程：對應 heading 與 fence/table 全為原樣留。
- ARCH Feature Factory 章位於 ARCHVIEW 外，既有 ARCH 全程唯讀。

## D2 錯置 search-task 欄位 mapping

錯置 JSON 實列欄位數：**9**（DEV baseline L1355-L1367；只計 `progress` 內具名欄位，不計容器 `progress`）。公開 endpoint truth chain：`api/main.py:203-206` → `api/routes/case_search.py:28,31,132-148` → `api/models/responses.py:35-41,43-51`。

| 錯置欄位 | API_SPEC receipt | 公開 endpoint runtime receipt | 判定／保全 |
|---|---|---|---|
| `current_step` | `docs/API_SPECIFICATION.md:159` | `api/models/responses.py:37` 僅 `current` | drift：命名裁決後才可補契約 |
| `total_steps` | `docs/API_SPECIFICATION.md:160` | `api/models/responses.py:38` 僅 `total` | drift：命名裁決後才可補契約 |
| `percentage` | `docs/API_SPECIFICATION.md:161` | `api/models/responses.py:39` | 兩邊皆有 |
| `step_description` | endpoint 章無；全檔 `rg -n step_description`=0 | truth chain 三檔 `rg -n step_description`=0 | 兩邊皆無，錯置草稿虛構 |
| `current_symbol` | `docs/API_SPECIFICATION.md:162` | `api/models/responses.py:40` | 兩邊皆有 |
| `processed_symbols` | endpoint 章無；全檔 `rg -n processed_symbols`=0 | truth chain 三檔 `rg -n processed_symbols`=0 | 兩邊皆無，錯置草稿虛構 |
| `estimated_remaining_seconds` | endpoint 章無；全檔 `rg -n estimated_remaining_seconds`=0 | `api/models/responses.py:41` | API 缺口；逐字保全如下 |
| `errors` | `docs/API_SPECIFICATION.md:250`（他 endpoint，非 search-task） | `api/models/responses.py:176` 為 `ParameterValidationReport`，非本 endpoint `TaskProgress` | 兩邊皆無本 endpoint 欄位，錯置草稿虛構 |
| `warnings` | endpoint 章無；`docs/API_SPECIFICATION.md:1963` 僅前端 `sample_warnings` | `api/models/responses.py:175,202` 分屬 `ParameterValidationReport`／`SamplingQuality`，非本 endpoint `TaskProgress` | 兩邊皆無本 endpoint 欄位，錯置草稿虛構 |

### 缺口欄位逐字保全

以下內容逐字復刻自 DEV baseline L1365（不把草稿自動升格為正式契約）：

```json
    "estimated_remaining_seconds": 1200,  // 預估剩餘時間（秒）
```

### BLOCKED-scope 申請清單（供後續裁決，B00 不改 API_SPEC）

- `estimated_remaining_seconds`：runtime 公開 response model 已有而 API_SPEC search-task schema 缺漏；需另票核准修改 `docs/API_SPECIFICATION.md`。
- `current/total`（runtime）對 `current_step/total_steps`（API_SPEC/錯置草稿）：需先裁決 canonical 命名與向後相容策略，B00 不推定答案。
- `step_description/processed_symbols/errors/warnings`：公開 endpoint schema 與 API_SPEC endpoint 皆無，不列補約候選。
