# IC 1e+1b — B2 實作派工(Task 2.1-2.5:縱向主路徑接線)

**執行端**:Grok 4.5(B1 已乾淨過,階梯續派)
**SPEC**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md`(v2.2 凍結;重點 §A D-C/D-D/D-E/D-F/D-G+§C consumer map)　**TODO**:`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 2(Task 2.1-2.5 逐條要點=**唯一真相,全文照做**)
**基底**:B1 已合入 main(c0b29ac):`compute_hac_ic_statistics`/`apply_fdr` 可用。

## Scope(五件一氣,完成後 stage5 消費 HAC q,舊 pooled 路徑退出 p-value 鏈)
1. **Task 2.1** stage5 接新 kernel:horizon 取 split_context["effective_horizon"] 或 `_resolve_effective_label_horizon(config, None)`,禁硬編;舊 `compute_ic_statistics` 改名 `compute_pooled_ic_statistics_deprecated`(唯一 caller=語意遷移測試;生產 import→M-H 結構測試紅)。
2. **Task 2.2** q 進閘+α 政策:apply_fdr 對**全 evaluated 集合**先於任何門檻;alpha_effective 三檔(sufficient/marginal→p_value_max;low_confidence→max(p_value_max,0.10));`alpha_source`+`selection_mode` 標記;`_apply_thresholds` p 閘消費 `p_value_adj`(fdr on)/`p_value`(off);threshold_log 增 alpha_effective/n_tests/fdr_enabled。
3. **Task 2.3** SelectionScope 接線:契約 split_label 擴 "full"(明示變更非放寬);evaluated 嚴格=finite p 子集;n_tests==len(evaluated) 違反=raise;入 report metadata。
4. **Task 2.4** reporter 導出:summary 增 t_stat/p_value_adj;JSON metadata canonical `significance.*` 節(D-F 同形,禁別名;fdr_assumption_note=固定一行 PRDS 披露);既有欄名/順序 byte 不變。
5. **Task 2.5** 刪 `apply_significance_filter`(不留 stub);其測試遷移入 T-2.2c α 政策測試。

## 測試(TODO 各 Task 驗證欄全做)
T-2.1a/b/c(M-F 雙腿+M-H 結構斷言)、T-2.2a(M-B **雙場景**:獨立 null+相關 null ρ≈0.7,n_tests 縮水 mutation 轉紅,允收帶入碼)、T-2.2b(M-D)、T-2.2c(α 六格含欄位值)、T-2.2d、T-2.3a/b(mutation:n_tests+1→契約 raise)、T-2.4(舊欄 byte 不變 golden 小樣本)、T-2.5(grep 0 殘留)。每條附實跑 receipt;mutation 轉紅附真紅輸出(非綠測試包裝)。

## 禁止事項(違反=退件)
- 禁對通過前置閘的子集算 FDR;禁保留舊 i.i.d. p 欄;禁 adjusted_p_threshold 舊語意(直接覆蓋 p_value_max)。
- 不動 rolling_ic/icir/ic_decay/grouped_ic 計算與輸出(G-1 byte 不變腿,B5 會驗);不動 cross_sectional 路徑(B3)。
- HAC 無生產開關;fdr.enabled 預設 true;OFF 態唯一真相=canonical `significance.fdr.enabled=false`。
- 既有測試斷言不放寬不刪(語意遷移逐條列帳寫入 RESULT);`handoffs/ic1eb_baseline/` 唯讀;data_cache 唯讀;禁 git checkout/stash tracked 檔。
- `tests/golden/l65/test_inventory.txt` 為 conftest 自動衍生,若被子集 pytest 覆寫,結束前 `git restore` 該單一檔(唯一允許的 restore)。
- 膨脹信號(碰 factories.py/protocols.py/新 caller 超出 SPEC §C map)→停手回報。

## 驗收命令(全綠才交)(VERIFY-EXEMPT:doc-example:dispatch-prompt-future-commands)
```bash
source venv/bin/activate
pytest tests/momentum/ -q
grep -rn "from api\." momentum/ | wc -l   # 0
grep -rn "apply_significance_filter" momentum/ tests/ | wc -l  # 0(僅 git 歷史)
```

## 交付
`handoffs/IC1EB-B2-IMPL-RESULT.md`:改檔清單/每條 T-2.x receipt/mutation 真紅輸出/語意遷移列帳/邊界結果。兩輪解不了→BLOCKED 停手(斷路器)。
