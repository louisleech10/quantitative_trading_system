# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ 本 session 完成(全 push,工作樹乾淨除既有 settings/audit)
**D1+D2 doc 漂移治理(commit b3f67bf)**:解耦規則定 CLAUDE.md 為 canonical 唯一權威;假綠全據實化;兩競爭權威 doc(PRODUCT_VISION/全系統解耦Prompt)降級;測試分層修正。codex+composer 雙審 BLOCK→修→codex 閉合全 CLOSED。
**簡化研究三家收斂 + reconcile(commit 5ff380d)**:Claude 自產 + codex+composer+grok 三家互審;定案兩批次。

## 🔴 揪出的既存問題(已入帳,待各自票)
1. **解耦 R2/R3/R4 全紅(18 筆)**:phase4 是半套 scanner 誤報綠;真狀態 R2=5/R3=12/R4=1(FeatureEngineering 共用工具直接 import)。ROADMAP P2 triage 債票(架構判斷:真違規 vs 該豁免)。
2. **TGF 觸發器既存斷鏈**:模板指「Feature Factory 章/API 節」但無對應穩定 H2。已定案納入簡化 epic 批次 A 修。

## ▶ 下一步:文檔簡化 epic(使用者定案兩批都做,TGF 納入)
中型文件治理,走完整管線。**下一步 = Claude 起草批次 A SPEC**(每段刪/外移/留分類 + 先建後刪 anchor + 驗收腳本)→ 雙家族 adversarial 審 → reconcile 戳 → 實作 → 另一方 review。
- **批次 A**(應做):修 TGF 斷鏈 + 建 ARCH `## Feature Factory 架構` 穩定 H2 + 刀1(已實現 853→能力索引+修假綠狀態欄)+ 刀3 目錄 364→~80 + 修 README 假行數。預期 ARCH ~1150-1350。
- **批次 B**(後排):刀2(DEV 8 通用章→300-450)+ 解耦枚舉→pointer(留 Artifact Contract/V2V3 why)+ 修 §1277+ 損壞 markdown+錯置 API 區塊。預期全檔 ~2200-2500(−44〜−51%)。
- 鐵律:驗收看資訊類型非硬行數;抽 contract 非整批上移;單檔 A/B/C 不拆 appendix。
- 研究鏈:handoffs/DOCDRIFT-SIMPLIFY-{STUDY-claude/codex/composer/grok,RECONCILE}.md。

## 其他剩餘(doc 後)
1c Net IC 量綱(大,正確性紅線,net_ic_analyzer.py:34)→1d/1f→實測→AI Agent。
