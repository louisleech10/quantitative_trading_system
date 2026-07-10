# IC Phase1 1e+1b 顯著性正確化 — SPEC/TODO Reconcile(R1→R2→嚴謹度委員會→v2.2)

**Task 鏈**:ic1eb-recon-{claude,codex,composer}(三方偵察)→ ic1eb-specadv-{codex,composer}(R1 雙 REJECT)→ ic1eb-specadv-r2-{codex,composer}(Composer APPROVE 13/13;Codex 8/9+1 STILL-OPEN→v2.1 修)→ ic1eb-rigor-{claude,codex,composer}(使用者質疑觸發之嚴謹度委員會,三腿 FREEZE-OK/AMEND-最小→v2.2 聯集收編)
**凍結對象**:docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md v2.2 + docs/IC_PHASE1_1E1B_SIGNIF_TODO.md v2.2
**日期**:2026-07-09

## 裁決總表(全文見 SPEC §ADV-RESOLUTION 與 v2.1/v2.2 changelog)
- R1 Codex 2 BLOCKING+6 MAJOR/NB:v2 全 ACCEPT(auto_bw/use_t/p 分布寫死+M-I;xsec `_label` horizon 丟失修法+M-J;α 顯性標記;canonical significance.fdr.*;nullability;G-1 五 hash;baseline 禁 git 操作;統計測試預算)→R2 8/9 CLOSED,STILL-OPEN(fdr:disabled 第四命名)→v2.1 D-G 統一 canonical。
- R1 Composer 2 BLOCKING+6 MAJOR+5 NB:v2 全 ACCEPT(p 分布單一定義;統計假設子節;ic_mean/檢定量雙軌披露;resolveConfidenceInterval 入刪除清單;樣本下限標註;六格 α;preset 現況標註;method 參數刪除)→R2 **APPROVE**(13/13 CLOSED;NEW-ISSUE 1/2/3 NB 文案→v2.1 修;4/5 已排除)。
- 嚴謹度委員會(三腿獨立):HAC+BH=feature 級 IC 篩選的標準且足夠工具,default 不變;聯集增補→v2.2:①M-B 相關 null 場景(PRDS 實測化)②fdr_assumption_note 披露③§N 登記 fdr_by/romano_wolf 選項、描述性指標正名、monotonicity ttest_ind P2、策略層 data-snooping epic。
- 閉合方法:原提出方重跑同一反例(statsmodels maxlags=None 慣例/use_t p 分叉 seed sweep/rank-product 標度/xsec 現碼 :965-968/auto_bw=0 邊界探針),非憑條文信任。
- 實作註記(NON-BLOCKING,入實作派工):threshold_log.fdr_enabled 僅鏡像 canonical(T-4.3/T-4.1 斷言兩者恆等);G-2 附 fraction_nan_p;統計性質測試掛 slow_stat marker。

## 過程檔(全部已 gate register-output)
- 偵察:handoffs/IC1EB-RECON-{claude,codex,composer}.md
- R1:handoffs/IC1EB-SPECADV-{codex,composer}.md
- R2:handoffs/IC1EB-SPECADV-R2-{codex,composer}.md
- 嚴謹度:handoffs/IC1EB-RIGOR-{claude,codex,composer}.md

## 戳記
(委員 append:`RECONCILE-STAMP: <codex|composer> APPROVED YYYY-MM-DD sha256:<body_hash> task:<task-id>`;body_hash 用 `bash scripts/reconcile_body_hash.sh handoffs/IC1EB-RECONCILE.md` 取得;任一方不滿意改 append REJECTED+理由)
RECONCILE-STAMP: codex APPROVED 2026-07-09 sha256:b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043 task:ic1eb-r3-stamp-codex
RECONCILE-STAMP: composer APPROVED 2026-07-09 sha256:b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043 task:ic1eb-stamp-composer

Verdict: APPROVE(雙家族閉合;出處=IC1EB-SPECADV-R2-composer.md「Verdict: APPROVE」13/13+IC1EB-R3-codex.md「Verdict: APPROVE」;本行位於戳記區後,不入 body hash)
