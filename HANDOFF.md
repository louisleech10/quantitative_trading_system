# Handoff
**Agent**: Claude(Opus 4.8) | **Time**: 2026-07-15 | **Branch**: main | **狀態**: 乾淨,可新 session 起

## ✅ 上個 session 完成(兩票全入版 push)
1. **1c Net IC 量綱正確化**:治理(SPEC 五輪+TODO 六輪三家 adversarial)+實作 B0-B3 四批(f1d85c5/2133c77/04ac6fb/77af3d3)。B-strict=禁 IC 減報酬率/`net_ic` 鍵全樹禁絕/成本去 ×2/成本前端輸入 fail-closed(5bps 寫死三處拔除)/per-rebalance 語意註記。docs/IC1C_NETIC_{SPEC,TODO}.md。
2. **1c-FR-STOPGAP(錯位因子報酬輸出止血)**:四方委員會揭「無消費者」前提不成立(錯位 ls_returns 預設 enabled+活在 reporter/UI)→使用者裁定立即止血。實作 B0-B2 三批(8be3056/41c26e0/81724c7)+缺口補提(4481c53:phase29 quarantine 漏 git add)。default-off 三態契約+統一收斂 sanitizer(codex 三輪實證揪 save_report/cache-hit/cache force-merge 三洩漏路徑)+AST consumer guard+前端兩圖三態下架。docs/IC1CFR_STOPGAP_{SPEC,TODO}.md。

## ▶ 下一步:④ 1d attribution 正名+NaN fail-closed(中/大)
- **模組**:`momentum/Analysis/factor_exposure_analyzer.py::calculate_factor_attribution`(:104-146)。做迴歸把因子報酬拆成各因子貢獻(y_pred/residual/ss_res/attribution dict)。
- **兩個已知問題**(ROADMAP 列為正確性紅線):①**正名**——模組名/輸出欄與實際計算不符,須釐清它真正算的是什麼;②**NaN fail-closed**——`factor_attribution NaN 繞過`:NaN 被靜默處理(如 fillna(0.0),見 :101),可能產出誤導性歸因,須改 fail-closed。
- **範圍界定**:**真 residual IC(移除已知因子貢獻後的預測力)歸 Phase 2B**,1d 不做;1d 只做正名+NaN 硬閘。
- **流程**:中/大任務→完整管線(SPEC 起草→三家 adversarial→凍結→TODO→Grok 實作/Codex+Composer 審);開工前先偵察讀碼確認 scope。

## 之後排序
⑤ **1c-FR-FULL**(canonical timestamp-aligned factor-portfolio return series 重建;修 ls_returns reset_index 錯位+模組資料通道+breakeven/profitable 實值)——使用者定=1d 之後近期排入。
⑥ 1f 空圖 schema flatten→實測→AI Agent。

## 📌 慣例/環境
- Grok 審查/實作一律 `--sandbox workspace` 直接寫檔;grok 家族入 `reconcile_stamps_check.sh` 第二參數。
- pytest collect 副作用 `tests/golden/l65/test_inventory.txt` 每次 revert(勿 commit)。
- `docs/API_SPECIFICATION.md` 有 1 行尾空白未 commit(session 前既存,非本工作;小債另清)。
- 全套件 baseline nodeids=77(1cfr B0 凍結),止血後 current=44;`scripts/ic1cfr_stopgap_freeze.py --check-nodeids` 為 fail-closed 機械 gate。
- 全套件既有紅(~數十)非近期引入;`--before`/`--check-nodeids` 跑全套件約 >10 分鐘(本機易逾時,可交委員代驗)。
- 派工三家 code review 一律另一方(實作者不自審);兩輪解不了交委員會/斷路器換手。

## ⚠️ 未 commit
docs/API_SPECIFICATION.md(session 前既存尾空白,非本工作)。其餘全入版。
