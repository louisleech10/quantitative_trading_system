# Handoff
**Agent**: Claude | **Time**: 2026-06-13 | **Branch**: main

## 結案:第 1 批 follow-up 小修包(升級為大型管線後完成,6 commits 9f207fc..4d5656f,未 push)
- N4 resource/N6 stream nan_ratio(all-NaN=total_nan)/N3 winsor per-call+共用 resolver/N7 冪等 canonicalizer 三套用點/T5 present_timeframes(含 scripts 2 消費者)。
- 管線:V1→V3 三輪雙家族 adversarial(Codex r1 16→r2 5B→r3 PASS;Composer r1 1B→r2 PASS)→Codex 實作→Composer code review **APPROVE**(3 MINOR 備註見 handoffs/20260613-*codereview*)。
- 驗收:新測試 20/20(含真 kline gate)+回歸 bundle **78 passed**+grep gate 乾淨+postflight ✅;golden baseline 先行凍結(9f207fc)。
- 文件:docs/BATCH1_FOLLOWUP_{SPEC,TODO,MANIFEST,DECISION}.md(V3);交接 handoffs/20260612-batch1-followup.md。

## ⚠️ 待使用者決策
- **d* cache/fracdiff(原第1批項,已抽出)**:實測推翻 HANDOFF 舊前提——非 CGSA path fracdiff 因欄名 regex 整體靜默失效(非 missing_context),修復=改數值輸出命中(a)(b)(d)。三選項 A 修復對齊/B 顯式化現狀/C 棄用非 CGSA,見 docs/DSTAR_FRACDIFF_NONCGSA_FINDING.md §5(建議 A,可排第2/3批後)。
- 6 commits 未 push,要 push 說一聲。
- templates/optimization_report.html 還原案(前輪遺留)。

## 下一步 backlog(順序使用者已拍板)
- 第 2 批:Run 生命週期 UX(中型,api+frontend+storage registry,不碰數值)。
- 第 3 批:既有測試紅 triage(~44 紅,先分類半天)。
- 16/24/32GB tier ADF/d* 並行度 profile(第1批後一次)——注意:d* cache 在非 CGSA 的前提已變,profile 應以 CGSA 主路徑為準。
- MINOR 備註(下輪順手):真 kline 測試 glob→rglob;SPEC :185 錨點勘誤;_apply_failed_timeframe_metadata 共用 helper。

## 鐵律教訓(本輪新增)
- codex sandbox 無 .git 寫權限→執行端只寫檔,commit 由 Claude 按 Phase 接手(已實證可行)。
- Codex quota 耗盡(00:16 重置)中斷在收尾報告;實作其實已完;驗檔案落盤而非信 log 再次奏效。
- tests/conftest.py 在 `--collect-only` 會重寫 tests/golden/l65/test_inventory.txt——跑 --co 後必查 git status 還原。
- 派工進度查看改 10 分鐘節奏(使用者 2026-06-12 指示,已入 memory)。
