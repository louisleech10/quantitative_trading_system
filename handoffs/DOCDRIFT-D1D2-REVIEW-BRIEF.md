# DOCDRIFT D1+D2 施工 code review brief(委員審查標的)

Task-id: docdrift-review | Date: 2026-07-12 | Chair/實作: Claude(Opus 4.8)
**性質**:純文件治理,**未改任何程式邏輯**(scanner 只加註解頭、grep 邏輯零改)。canonical 決策鏈已三家 adversarial 收斂(handoffs/DOCDRIFT-{MAP-CHAIR,STUDY-grok/codex/composer,RECONCILE}.md);本 review 審**實作 diff 是否忠實落地 + 有無殘留假宣稱/自相矛盾/pointer 不穩**。

## 審查對象
`git diff`(未 commit)。**範圍檔**:CLAUDE.md / docs/ARCHITECTURE.md / docs/DEVELOPMENT_GUIDE.md / docs/ROADMAP.md / AGENTS.md / .cursorrules / scripts/check_decoupling.sh / scripts/check_decoupling_phase4.sh。
**排除**(非本次):`.claude/settings.json`(session 起始既有改動,非本任務)、`HANDOFF.md`(交接)。

## 落地決策(對照 diff 檢查是否忠實)
1. **canonical 7 條 = CLAUDE.md 版**:R5=Config single source、R6=Tests without run_api.py。ARCHITECTURE §162 舊錯表(R5/R6=singleton/callback+假✅已修復)已改正。
2. **singleton/callback 降 named invariant Rule 8/9**:Rule 8(singleton)**誠實記「仍有殘留」**(chart_signal_service/signal_analysis_service/data_source_registry `_instance`),不得再宣稱已修復;Rule 9(callback bypass)由 check_decoupling.sh lambda 檢查強制。
3. **兩 scanner 編號語意對照**:check_decoupling.sh 內部「Rule 6」=callback bypass(=Rule 9),phase4「Rule 6」=獨立 pytest(=canonical R6);scanner 只加註解頭,grep 未動。
4. **全 agent 可讀**:AGENTS.md/.cursorrules/DEV_GUIDE 頂各加 canonical 規則 pointer 指 CLAUDE.md。
5. **D2 假宣稱/過時**:factory map 補漏+標「示意非完整,權威=factories.py 78 個」;§60「2026 Q1」→里程碑+校對日;FF UI 待開發標「部分已建」;DEV_GUIDE §237 blanket-ban「絕對禁 random」→分層(對齊 docs/IC_API_TEST_LAYERING.md);§327 測試數據分層;§54 工作流→多 agent。
6. **Rule 4 既存違規據實入檔**:feature_factory_batch_adapters.py:9 service→service,ARCHITECTURE 標「1 已知違規」,ROADMAP 立 P2 債票(code 本次不動,使用者裁定)。

## 請重點挑戰(adversarial)
- 有無**殘留假綠**:diff 後是否還有任一處把 singleton/callback 或 Rule 4 宣稱為「已修復/0 violation/通過」?(grep 全庫)
- 有無**新引入的自相矛盾**:改後 canonical R5/R6 是否與 §367 演進表、§502/504、DEV_GUIDE 分層說法一致?
- **DEV_GUIDE 分層**是否與 docs/IC_API_TEST_LAYERING.md 判準真對齊(沒把合法合成誤禁、也沒把數據正確性測試放水)?
- **pointer 穩定性**:各 pointer 指向的錨點(§名)是否存在、可被 CI/grep 檢查?有無指向已淘汰檔(如 copilot-instructions)?
- scanner 註解對照是否正確描述 grep 實際行為(勿誤述)?

## 驗收事實(供對照)
- phase4 canonical R1/2/3/6 = 135 passed PASSED;check_decoupling.sh 僅 Rule 4 紅(既存)。

## 回覆格式
`handoffs/DOCDRIFT-D1D2-REVIEW-{codex,composer}.md`:逐點 AGREE/CHALLENGE(附證據與可證偽建議)+結論行 `VERDICT: PASS` 或 `VERDICT: BLOCK(原因)`。
**read-only 審查**:勿改任何檔;發現須修處寫進回覆檔由 Claude 落地。
