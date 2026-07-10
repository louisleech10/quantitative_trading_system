# IC 1e+1b — B4 實作派工(Task 4.1-4.3:config+API+前端全棧接通)

**執行端**:Grok 4.5(階梯續派;B1-B3 已過)
**SPEC**:`docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md` §A D-F/D-G+§C consumer map 第9項　**TODO**:`docs/IC_PHASE1_1E1B_SIGNIF_TODO.md` Phase 4(Task 4.1/4.2/4.3 逐條要點=唯一真相,全文照做)
**基底**:main 546f50a(B1-B3 已閉)。

## Scope
1. **Task 4.1 後端 config**:`ic_config_schema.py` 增 canonical `SignificanceSchema`(`significance.fdr.{enabled=True,method="fdr_bh"}`+`significance.maxlags`);`_apply_tier_config` 增 `fdr_correction→significance.fdr.enabled` 映射(UI 邊界唯一轉名點);stage5/xsec 消費 schema;禁第四種 fdr 命名;舊 config 無 significance 節→預設 ON。
2. **Task 4.2 前端**:三 preset `fdr_correction: true`;`getEffectiveConfig` 送出該欄;types.ts nullability(`p_value/p_value_adj/t_stat` 皆 `?: number|null`);**刪 ICSummaryTable `resolveTStat`+`resolveConfidenceInterval` 全部 i.i.d. 推導**,直讀後端欄+共用 finite formatter('--');表頭增 q 欄;CI 無後端值→'--';FeatureTierPanel tip 更新;ic_mean tooltip 註「描述性 rolling 均值,非檢定量」。前端禁任何統計推導(含 1.96·SE)。
3. **Task 4.3 e2e 兩態**(M-G):pytest 真小樣本走 `_apply_tier_config` 真路徑(禁 mock 映射鏈):false→raw p 閘;true→q 閘;兩態 passed 可分離;off 態唯一判據=report metadata `significance.fdr.enabled=false`,threshold_log.fdr_enabled 僅鏡像且斷言恆等。

## 測試/驗收(全綠才交)(VERIFY-EXEMPT:doc-example:dispatch-prompt-future-commands)
```bash
source venv/bin/activate
venv/bin/python -m pytest tests/momentum/ -q          # 全綠
grep -rn "from api\." momentum/ | wc -l                # 0
grep -nE "resolveTStat|resolveConfidenceInterval|1\.96" frontend/src/components/**/ICSummaryTable.tsx | wc -l  # 0
cd frontend && npm run build                           # 綠
```
T-4.1 每跳接點斷言(store JSON→API model→_apply_tier_config→stage5→report metadata 同 key 鏈);T-4.2 build+grep;T-4.3 兩態 receipt。mutation/receipt 紀律同前批(run_with_receipt,RESULT 掛 VERIFY:<claim-id>;mutation 紅燈行加 SUPERSEDED 註記)。

## 禁止事項
- 不動其他 schema 欄預設/其他 toggle 語意;顯式 maxlags 仍受 h-1 下限。
- 既有斷言不放寬;`handoffs/ic1eb_baseline/` 唯讀;data_cache 唯讀;l65 inventory 被覆寫→git restore 該單一檔(唯一允許)。
- 前端只增列不改既有欄名/順序。

## 交付
`handoffs/IC1EB-B4-IMPL-RESULT.md`。兩輪解不了→BLOCKED 停手。
