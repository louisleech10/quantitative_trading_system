# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ 上一 session 完成(全 push,工作樹乾淨)
- P2 債五票全清(票1 d0d0ebf/票2 e6825d9/票3 492c4cc/票4 669c6fa/票5 27fdb00)+ IC-API epic 三 Phase(56a9566/a39dc6c)。
- 流程圖 docs/workflow_diagram.html(32a5e9e/1405473)+ PNG(docs/workflow_diagram.png,untracked 分享用)。
- SSD 清理:handoffs/ 4.3G→445M(刪 untracked 廢棄 baseline 快照);data_cache 未碰。
- handoffs 歸檔=**跳過**(24 處 gate 機制引用會斷、檔小、auto-load 只讀 HANDOFF.md,實益<風險)。

## ▶ 新 session 要做:doc 漂移修正(D1 先→D2 後→簡化研究)
**研究已完成**(三家收斂,鏈=handoffs/DOCDRIFT-{MAP-CHAIR,STUDY-grok/codex/composer,RECONCILE}.md)。
**核心解耦本體是綠的**(momentum→api=0;check_decoupling_phase4 135 passed)——問題是**文件吹過頭+規則兩套說法**,非程式壞。

### D1(先做,大;純文件治理,禁改程式邏輯)
1. canonical 7 解耦規則**定 CLAUDE.md 版**(Rule5=Config single source、Rule6=Tests without run_api;證據:CLAUDE 宣告權威+ARCH 後段§349 也這版+check_decoupling_phase4 R6=pytest tests/momentum/Strategy 135 passed)。
2. 修 ARCHITECTURE.md §150 錯的 5/6 表;singleton/callback **降獨立 Rule 8/9**(不頂替 5/6);兩 check 腳本編號 deconflict。
3. 大文件(ARCH/DEV_GUIDE)移除重述規則→pointer 指 CLAUDE.md。
4. **全 agent 可讀(使用者定)**:AGENTS.md/.cursorrules/派工 prompt 都要指向或掛載 canonical 規則,避免 Codex/Grok/Cursor 矇著做。建議規則留 CLAUDE.md+各入口加 pointer+摘要。

### D2(D1 完成後,大;修假宣稱/過時)
1. ARCHITECTURE:改「已修復/已驗證」假綠(singleton/callback 程式裡仍在:chart_signal_service.py:57、signal_analysis_service.py:47、data_source_registry.py:69…,據實記+Rule8/9 追蹤)、更新 factory map(factories.py 79 個 create_,清單缺一堆)、修狀態漂移(§60「2026 Q1」、FF UI §1499 vs §1804 矛盾)。
2. DEV_GUIDE:錯誤「絕對禁 random/硬編碼數值測試」→**分層**(對齊 docs/IC_API_TEST_LAYERING.md:production truth/regression/synthetic unit)、刪自相矛盾(§237 vs §308/§327)、更新§54「人工驗證」舊工作流為多 agent。

### 文檔簡化研究(接 D1/D2 後,使用者提)
4400 行 ARCH+DEV_GUIDE 被讀時貴(非每 session,只 on-demand;但漂移時讀了更糟)。D1/D2 會讓它們變瘦;委員研究「還要再砍多少/怎麼精簡成 lean reference」。

## 流程:走完整管線(D1/D2 各自)
Claude 起草 SPEC→grok+codex+composer 多家 adversarial→reconcile 戳→實作→驗收(check_decoupling 仍綠+pointer CI 可檢)。D1 定案草案已在 DOCDRIFT-RECONCILE.md。

## 其他剩餘(doc 後)
1c Net IC 量綱(大,正確性紅線,net_ic_analyzer.py:34 相關係數減報酬率量綱錯)→1d/1f→實測→AI Agent。
