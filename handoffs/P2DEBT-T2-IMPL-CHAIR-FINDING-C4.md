# 票 2 實作主委驗收 finding C-4(V6 紅=main 既有,非票 2 引入)
Task-id: p2debt-t2 | Chair: Claude(Fable 5) | Date: 2026-07-11

## 現象
V5(C-3 修後)PASS(grok receipt);全套跑到 V6:`3 failed, 9 passed, 20 errors`,
根因全同=`InvalidInputError: label horizon cannot be resolved from column: label`
(momentum 端 label 欄名解析,fixture 造的 labels 欄叫 `label` 無 horizon 後綴)。

## 判別鏈(三重對照,receipt 齊)
1. grok sandbox 跑(nohup 繼承 sandbox):V6 紅 → 疑 sandbox 假紅(/tmp/t2-all-grok.log)。
2. codex 對照跑:**同樣紅** → 排除 sandbox 因素(handoffs/P2DEBT-T2-V6-CODEX-RUN.md,/tmp/t2-v6-codex.log)。
3. **主委 HEAD 對照**(git worktree @492c4cc,無票 2 任何改動,直接 pytest):
   - test_ic_deep_analysis.py:`3 failed, 7 passed, 4 errors`——同 3 個 FAILED、同 label horizon 錯誤。
   - test_ic_analysis_api.py+test_export_api.py+test_ic_analysis_service.py:`3 failed, 8 passed, 2 skipped, 16 errors`——同 error 家族。
   → V6 全部紅點在 HEAD 原樣重現;票 2 diff(只加 redirect marks/fixture 包裝)未引入任何新紅。
4. 兩輪 V6 皆 `DIGEST_DIFF_EMPTY[V6]=1`:redirect 守衛未破,data_cache 無洩漏。

## 主委裁決提案(請委員 STAMP 或 BLOCK)
- **P-1** V6 驗收準則偏差(VERIFY-EXEMPT:doc-example:p2debt-t2-c4;裁決敘述,證據見已入版 C4-REVIEW+final7 receipt):凍結 SPEC 要求 V6 綠,但 main 基線本身紅;票 2 驗收改為
  「**無新增紅**:V6 失敗 nodeid 集合 ⊆ HEAD 基線失敗集合(逐 nodeid 比對)+DIGEST_DIFF_EMPTY[V6]=1」。
  基線集合=本檔 §判別鏈 3 兩次 HEAD 實跑的 FAILED/ERROR nodeid(receipt 可重放)。
- **P-2** label horizon 既有紅=**另立新票**(P2 債票 6 候補):api IC full analysis 測試家族在 main 上壞,
  疑 fixture label 欄名 vs 生產解析器不相容;涉 a(數值/資料品質)須完整管線,不塞進票 2 scope。
- **P-3** V7+全套 receipt:依 P-1 準則重跑全套(V6 用 nodeid 比對),出 final5 receipt 後進實作雙審。

## 委員請驗
- 驗 §判別鏈 3 可重放:`git worktree add /tmp/chk HEAD && cd /tmp/chk && <venv pytest 同組檔案>`。
- 驗票 2 diff 無 label 相關語意變更:`git diff tests/api/`。
- 對 P-1/P-2/P-3 各給 STAMP APPROVED 或 BLOCK+理由。
