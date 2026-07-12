# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-13 | **Branch**: main

## ✅ 本 session 完成(全 push)
1. **D1+D2 doc 漂移治理(b3f67bf)**:解耦規則定 CLAUDE.md canonical 唯一權威;假綠據實化;競爭權威 doc 降級;測試分層。codex+composer 雙審 BLOCK→修→閉合。
2. **簡化研究三家收斂+reconcile(5ff380d/27de27f)**:Claude 自產+codex+composer+grok;定案兩批次。
3. **批次 A SPEC v2 委員核可(7bac9a2)**:Claude 起草 v1→三家 adversarial 全 BLOCK(15 項)→改寫 v2→三家閉合重驗全 VERDICT PASS+RECONCILE-STAMP APPROVED。template PASS。

## 🔴 既存問題入帳(各自票,ROADMAP P2)
- **解耦 R2/R3/R4 全紅 18 筆**(phase4 半套 scanner 誤報綠):triage 債票。
- **TGF 觸發器既存斷鏈**:納入簡化 epic 批次 A(SPEC A0.2 修)。

## ▶ 下一步:實作批次 A(docs/DOCSIMPLIFY_BATCHA_SPEC.md v2,已委員核可)
**方法論=inventory-first/manifest-gated/mapping-verified/先建後刪**。拓撲 A00→A0.1→A0.2→A1;A2 序列化於 A1 後。
- **A00(先,只讀 review-lock)**:產 disposition manifest(§1000-1852+§636-999 每子塊 ID/hash/分類{刪|外移|留}/重生命令/目的 anchor)+route→API H2 mapping+目的地契約驗真。點名必留:d_star fingerprint/native-tf/force_regenerate/IC 8階段 config precedence/§21-23。
- **A0**:建 ARCH `## Feature Factory 架構` H2+DEV `## 長時間任務與 API 生命週期`(rename 現節+改 inbound)+修 TGF 三列穩定 anchor。
- **A1**:已實現→能力索引表(依 manifest,清假綠狀態欄)。**A2**:目錄→~80+README 假行數。
- **交付物**:新增 `scripts/check_doc_anchors.sh`(GitHub slug+fixtures+changed-files baseline/delta)。
- **驗收硬 gate(非行數)**:manifest disposition 覆蓋(刪除塊⊆{刪,外移}、留塊不消失)+anchor checker exit 0+舊觸發字串 templates/TODO_GENERATION_PROMPT.md==0+phase4 exit 0。
- **待辦儀式**:正式 body-hash RECONCILE-STAMP(reconcile_stamps_check.sh 格式)才發實作 token;審查鏈=handoffs/DOCSIMPLIFY-A-SPECREVIEW-{codex,composer,grok}{,-closure}.md(未 commit,pre-commit claim hook 擋 VERDICT 文字;本地+task log 留審計)。
- **批次 B** 另立 SPEC(DEV 8 通用章→300-450+解耦枚舉→pointer+修 §1277 損壞 markdown)。

## 其他剩餘
1c Net IC 量綱(大,正確性紅線,net_ic_analyzer.py:34)→1d/1f→實測→AI Agent。
