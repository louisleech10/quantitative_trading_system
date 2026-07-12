# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-12 | **Branch**: main

## ✅ P2 債已閉合入版
- 票 1 governance 9 紅(d0d0ebf, 151 passed)。
- 票 3 tsc 11→0(492c4cc, vitest 31 綠, grok+composer 雙審)。
- 票 2 data_cache redirect(**e6825d9, 已 push**):process-global patch+S1-S11 seam manifest+逐檔 digest oracle;final7 V1 9p/V2 2p/V5 3p/V7 133p+V6 no-new-red,scripts/run_ic_persist_hermetic.sh --set all exit0 VERIFY:20260712T011428Z-p2debt-t2-impl-final7;finding 鏈 C-1~C-5+雙家族審 CE8 全閉合;C-5 digest 抓到真洩漏證守衛可證偽。

## ▶ P2 債剩餘
- **票 4** codex 沙箱卡死蒐證:handoffs/P2DEBT-T4-CODEX-SANDBOX-EVIDENCE.md;A/B 案(ORCH 繞法 vs 報 OpenAI)委員會裁決待開。
- **票 5** 1a cut1 golden provenance:與票 2 相鄰;**票 2 已留 4 個 freeze 腳本的票5 hunk 於 working tree**
  (h5 快取/config_override 854d444)+baseline_*.json+l65/test_inventory.txt 未 commit,票5 收。
- **票 6(新,C-4/P-2 裁決)**:label horizon 既有紅(api IC full analysis 23 nodeid+service cross-sectional 3);
  fixture `label` 欄名 vs 生產 `_resolve_label_horizon_from_column` 只認 `return_(\d+)`;涉 a 類完整管線。

## 未 commit 殘留(刻意)
- .claude/settings.json(本機)。
- handoffs/*.md 票2 審計鏈(~40 檔 provenance):claim checker 擋 7 檔草稿/prose,未入 e6825d9;
  在 working tree,可另開 provenance commit 或下 session 處理(run_receipts json/log 已入版)。
- 票 5 golden hunk(見上)。

## 教訓(SCAR 素材,待彙整入 SCAR_LEDGER)
- chdir 型 hermetic 測試落地前必附 cwd 依賴盤點(C-2/C-3 三連環:config/kline/git rev-parse)。
- 驗收解析 CLI 輸出附真實樣本 fixture(C-1 skip 行格式);禁 `| tail` 遮 rc。
- digest oracle 抓到真洩漏=守衛可證偽非廉價綠(C-5);接縫完整性須 per-seam arity fail-closed(CE8)。
- 分工:實作 Codex/代跑 Grok/主委只讀 receipt 不自跑;codex 不可自報「grok 跑過」(provenance)。

## 下一步(使用者排程 project_session_plan)
P2 債剩餘(票4/5/6)→ 1c Net IC 量綱(大,獨立 session)→ 1d/1f → 實測 → AI Agent 地基 → V2。
