# IC 1e+1b — B5 實作派工(Task 5.1:Golden 三腿+選型 diff 收尾)

**執行端**:Grok 4.5(階梯;B1-B4 已入版至 49ef0ac)
**SPEC**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §G(v2 全文)　**TODO**:Phase 5 Task 5.1
**Baseline(唯讀,禁重產)**:`handoffs/ic1eb_baseline/`(v4;baseline_manifest.json=真相源;13 report+inputs/+expected_raise_runs;五 hash 程序=`scripts/capture_ic1eb_baseline.py` 之 `five_hash/summary_to_g1_frame`,重放須同 `patch_persist_outputs` patch;比對限同 venv/同機)

## Scope
1. **G-1 不變腿測試**:新 golden 測試檔(tests/momentum/Analysis/ 下):對 baseline manifest 的縱向 9 顆+full+event 顆(xsec 顆亦含)——以 inputs/ 預物化檔重放新路徑,斷言**非顯著性欄位結構化五 hash 相等**(復用 capture 的 five_hash/summary_to_g1_frame 程序;import scripts.capture_ic1eb_baseline 或抽共用 helper 皆可,擇一說明);另斷言 `summary_feature_order_sha256`(xsec ICIR 排序不變)與 `series_sha256`(rolling/decay/grouped)不變。重放成本高的顆掛 `slow_stat` marker+預算;至少 BTC-12h-f754(最快顆)不掛 marker 常跑。
2. **G-2 變更腿**:產 `handoffs/IC1EB-GOLDEN-DIFF.md`——per-feature 對照表(p_iid_old(自 baseline report)/p_hac/q/pass_old(自 manifest passed_set 重建)/pass_new/淘汰原因),涵蓋 13 顆;**新路徑 baseline 凍結**(名稱集合 sha256+每 feature p/q 值 hash)落 `handoffs/ic1eb_newpath_freeze/`(manifest 格式仿 baseline);**`fraction_nan_p` 統計**(12h 短窗 fail-closed 比例)入 diff 檔;變化方向摘要(預期:高自相關假顯著轉紅)供三方簽核審。
3. **G-3 fail-closed 腿**:測試斷言:樣本不足(n_valid<max(8,2L))/全 NaN/std=0→p=NaN→p 閘 fail;SelectionScope 違約→raise;xsec labels_path 單軸→仍 raise(比對 baseline expected_raise_runs receipt 之 exception_type)。
4. **1a baseline 重生**(quarantine README 義務):於 pre-B2 commit `c0b29ac` 開 **git worktree**(新目錄,絕不動主工作樹)重跑 1a 凍結程序(tests/golden/ic_phase1_1a_cut1/ 原程序;找 freeze 腳本或依 test 之 _run_baseline 重建),與 `baseline_meta.json`/`baseline_new_meta.json` 宣告雜湊比對——**一致才放回** tests/golden/ic_phase1_1a_cut1/;不一致→停手記 BLOCKED-1A 交回(禁湊合)。之後 1a golden 兩測試對新代碼**預期紅**(行為變更)→依 1a 原 §G 程序以新路徑重凍 baseline_new(old 保留舊凍結),重生後兩測試須綠。worktree 用畢刪除。
5. 全套收尾:`venv/bin/python -m pytest tests/momentum/ -q` 全綠(1a 兩測試回歸綠)。

## 禁止事項
- `handoffs/ic1eb_baseline/` 唯讀(manifest 有 inputs_integrity+report sha 防偽,任何改動必被抓);data_cache 唯讀;主工作樹禁 git checkout/stash(1a 重生限 worktree 內)。
- G-2 對照表數字全部由程式生成(腳本入 repo scripts/),禁手填。
- 既有斷言不放寬;receipt 紀律(run_with_receipt+VERIFY:<claim-id>;mutation 紅燈行加 SUPERSEDED 註記)。

## 驗收命令(全綠才交)(VERIFY-EXEMPT:doc-example:dispatch-prompt-future-commands)
```bash
source venv/bin/activate
venv/bin/python -m pytest tests/momentum/ -q
venv/bin/python -m pytest tests/momentum/Analysis/test_ic_1a_cut1_golden.py -q  # 重生後 2 passed
```

## 交付
`handoffs/IC1EB-B5-IMPL-RESULT.md`:G-1/G-2/G-3 各腿 receipt/1a 重生比對記錄/fraction_nan_p 數字/G-2 diff 方向摘要。兩輪解不了→BLOCKED 停手。
