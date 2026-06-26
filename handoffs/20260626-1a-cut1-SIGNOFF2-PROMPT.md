# 1a 第一刀 — 三方簽核 R2（修補後重簽，聚焦 2 LEAK 是否真關閉）

R1 抓到 2 真 LEAK（見 `handoffs/20260626-1a-cut1-SIGNOFF-RECONCILE.md`），已修。**本輪重簽**：用 adversarial 確認 LEAK 真關閉（不是表面綠燈）。working tree 已含修補。

## 先讀
- 修補 reconcile：`handoffs/20260626-1a-cut1-SIGNOFF-RECONCILE.md`
- 修補 diff：`git diff momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/data_preprocessor.py`
- 新測試：`tests/momentum/Analysis/test_ic_1a_cut1_oos.py`（`test_purge_label_mutation_*`、`test_winsorize_type_branch_*`、`test_holdout_embargo_*`）

## 必驗（adversarial，真實 kline `data_cache/feature_klines/kline_cache.h5`）
1. **LEAK-1 關閉？**：**重跑你 R1 的反例**——只擾動 purge rows 的 label，test rolling IC/ICIR **必須不變**（R1 時會變）。自己手構，不只信測試。確認 rolling 輸入已排除 purge hole（`~train & ~test`）。
2. **LEAK-2 關閉？**：只改 test 段 type-like 值，winsorize 的 skip/winsorize 分支與 train 輸出 **必須不變**（R1 時會變）。
3. **embargo**：embargo>0 test 起點推遲 embargo 列。
4. **新測試可證偽？**：確認 `test_purge_label_mutation_*`/`test_winsorize_type_branch_*` 是真不變量斷言（若把修補還原會 FAIL），非 smoke。
5. **無新洩漏/回歸**：flag-off G-OLD deep-equal 仍 PASS；解耦 0。

## 輸出（寫你的 SIGNOFF2 檔）
```
## R2 簽核結論：{資料正確,簽 PASS / 仍有疑,列向量}
## LEAK-1 重驗（反例 + 結果:變/不變）
## LEAK-2 重驗（反例 + 結果）
## 殘留 Findings（無則「無」）
STATUS: DONE
```
任一 LEAK 未真關閉 → 不簽。
