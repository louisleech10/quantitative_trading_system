# Handoff
**Agent**: Claude | **Time**: 2026-07-09 | **Branch**: main

## ✅ 剛完成:1e+1b「顯著性正確化」SPEC v2.2+TODO v2.2 雙戳記凍結(本次 commit)
- **B-1 文檔債已閉**(57e9ac8):1-align SPEC v3.1 D-5 return_kind+雙家族重戳機檢 PASS。
- **管線全走**:三方偵察(IC1EB-RECON-{claude,codex,composer},Claude 全量自產版在列)→SPEC/TODO v1→R1 雙家族 adversarial 雙 REJECT(4 BLOCKING:auto_bw/p 分布不確定、xsec `_label` 改名丟 horizon(codex 抓,Claude 親驗 :966/:359)、fdr 第四命名)→v2/v2.1 逐項 ACCEPT→R2(Composer 13/13 CLOSED APPROVE;Codex 8/9→v2.1 修)→R3 Codex APPROVE→**雙 RECONCILE-STAMP 機檢 PASS(sha256:b77932d8,task:ic1eb-r3-stamp-codex/ic1eb-stamp-composer)**。
- **使用者質疑觸發嚴謹度委員會**(ic1eb-rigor-*,三腿):HAC+BH=feature 級篩選標準工具,三方 FREEZE-OK;聯集收編 v2.2=M-B 增相關 null 場景(PRDS 實測化)+fdr_assumption_note+§N 登記(fdr_by/romano_wolf/描述性正名/策略層 snooping epic→ROADMAP P2 新節)。
- **SPEC 核心**:kernel=bar-level Spearman 貢獻序列+NW(auto_bw=int(4*(n/100)^(2/9)),L=max(auto,h-1),p=t 分布,oracle=statsmodels use_t=True);BH-FDR 對全 evaluated 集合先算 q 再進閘;SelectionScope 接線;canonical `significance.fdr.*`;前端刪 resolveTStat/resolveConfidenceInterval i.i.d. 推導;xsec horizon 改名前解析;Golden=G-1 五 hash 不變腿+G-2 selection-diff+G-3 fail-closed;M-A~M-J mutation。
- 委員產出全部 register-output;過程檔見 handoffs/IC1EB-*。

## ★下一站(使用者指示:freeze commit 後停下討論)
1. **與使用者討論後才動**:預產 Golden baseline 快照(`handoffs/ic1eb_baseline/`,舊路徑 report+五 hash,SPEC §G 程序)→ B1-B5 批次派工(Codex 實作+Composer review,依 TODO §B)→ 三方數據正確性簽核。
2. 後續刀:③1c Net IC 量綱→④1d attribution→⑤1f 空圖+grouped schema。

## 鐵律(慢測試/執行)
- 「已驗/passed」須帶 VERIFY receipt。委員審查派工 `gate.sh dispatch --risk low --template "n/a:"`;實作派工 --risk high 附 --spec/--todo/--adversarial(過戳記機檢的 handoffs/IC1EB-RECONCILE.md)/--reconcile;codex exec 必接 `< /dev/null`;產出 register-output。
- 執行端產物不可信;接回只讀 diff+測試+摘要;執行端不得 git checkout/stash tracked 檔(Golden baseline 唯讀消費預產快照)。
