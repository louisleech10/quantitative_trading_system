# ICPOSTLEAK 實作第 1 批 審碼 r2（r1 修補閉合＋§N 殘留觸發之處置）

brief-kind: review
task-id: 20261001-ICPOSTLEAK-B1-REVIEW-R2

## 範本
照 `templates/COMMITTEE_FINDING_TEMPLATE.md`：canonical 四欄、heading `## <FAMILY>-R2-P<0-3>-<NN>`、零 finding 用 `## <FAMILY>-R2-P3-00`；每條 `**類別**:`；P0／P1 之碼證含 `CODE-ANCHOR: <repo-relative-path>:<line>` 與 `MUTATION: <可執行破壞>`；末段 `VERDICT`／`BLOCKED-BY`／`CLOSED`（`CLOSED:` 只列本家族前綴之 r1 ID）。每家**全面**審（不分角度）。
🔴 **本輪唯讀**：禁改碼、禁改文檔、禁 git 寫入；實跑一律在 `/tmp` 複本，指令列與暫存路徑不得含委員家族名稱；FF 探針須先呼叫 `handoffs/run_receipts/ffstat_probes/_isolate.py` 之 `isolate()` 與 `isolate_dstar_cache()`。本期委員為 codex、composer、grok 三家。
🔴 **磁碟與時長**：本機 8 GB、8 核；重測試一律單組串行、不得與他家並行；以 node id 選跑；暫存結束前刪除。
🔴 **使用者指示（逐字）**：「嚴謹度和分析模組是必要的，只能多但不能少」；「測試和驗證是必要，但是我不想整個流程再消耗時間在不是必要的測試上」。使用者離線，授權「有問題你跟委員討論共識」。**不得侷限加密貨幣**；**嚴禁慢閘**。殘留之「為何現在不做」只准 `blocked-by`／`user-ruling`／`needs-research` 三值，不得是「之後再說」。

## 審查標的
- r1 收斂檔 `handoffs/reconcile/20261001-icpostleak-b1-review-r1/synth.md`（CODEX-R1-P2-01 NaT 漏擋、CODEX-R1-P2-02 量級收據缺）。
- 修補 commit `40f863d4`（`git show 40f863d4`）：`momentum/FeatureEngineering/preprocessing/time_order.py`、`tests/feature_engineering/test_icpostleak.py`（`nat_after_valid`、`nat_first`）、`handoffs/run_receipts/icpostleak_probes/probe_change_report.py`（`branchdiff`）、`handoffs/run_receipts/icpostleak_probes/probe_branch_diff_locate.py`、收據 `handoffs/run_receipts/20261002-icpostleak-branch-diff.json`、`handoffs/run_receipts/20261002-icpostleak-branch-diff-locate.json`、盤點收據更正。
- 前批 commit `95487b67`、`47ba1d3e` 已於 r1 三家 proceed。

## 主委事實
1. ICPOSTLEAK 兩測試檔 124 passed；以改前 `np.diff(values) <= 0` 寫法為 mutant，`nat_after_valid`、`nat_first` 兩例紅、其餘時間序例綠。
2. branch-diff（改後 npz 由主樹 HEAD 程式碼 dump，49 例；42 對各分支對同組合 legacy）：optimized 七組合全 0 格差異；最大相對差 58.8（registry 系 rank+zscore，該格 legacy 值近 0）；最大絕對差 0.0975（polars rank+zscore）；NaN 位置不一致 0 對 ⇒ SPEC §N 殘留「各分支 zscore 數值核心不一致」之觸發條件（最大相對差 > 1e-3）成立。
3. 主委定位（locate 收據＋scratchpad 對照）：
   - rank 單步：polars／registry 與 legacy 各 2 格差 0.001984（＝1/504，窗 252 之半階），位於 `close_trend_EMA_21` 第 1053 列；polars／registry 之輸入為 float32、legacy 為 float64 ⇒ float32 下兩值同值而取平均名次。
   - rank+zscore：上述 rank 差經 zscore 放大（該窗 rank 之 std 0.018）⇒ 0.095；與 float64 精確 z（-3.009236）相比 legacy 吻合、分支偏離。
   - registry 單步 zscore：最大 0.038、p99 0.009（`close_trend_EMA_21` 第 2202 列，窗均值 70168、std 276）；float64 精確 z＝legacy 值 ⇒ registry 之 float32 累積式核心對價位級輸入之精度損失。polars 單步 zscore 最大 4.7e-5。
   - 改前（HEAD `d31c170e` 之 before.npz）對同一 legacy 參照：registry 單步 zscore 與 rank 單步差異**逐格相同**（非本批引入）；含 gaussian 之 registry 組合改前 3.4–73574（漏 gaussian／順序錯），改後 ≤ 0.0275。
4. 生產可達性（讀碼）：registry 入口兩個呼叫者——`feature_factory.py` `_run_layer6_5_preprocessor`（pre-IC 經 `_layer6_5_pre_ic` 強制關 rank／zscore／gaussian；post-IC `_layer6_5_post_ic` 之呼叫者待核）與 `feature_storage.py` `write_raw_from_registry_stream`（設定來自 `_build_l7_raw_preprocessing_config`，同樣強制關三項）。IC 頁與 `run_ic_first` 之 post-IC 經 `transform_selected` → `transform`（預設 Polars 臂）。

## 本 brief 前提
fact-verified: 主委事實 1–3。
assumed: ① registry 帶 rank／zscore／gaussian 之組合經生產分派不可達（主委事實 4）。② 生產輸入（特徵 h5）以 float32 落盤，故 legacy 臂讀入後之同值集合與 float32 臂相同，rank 同值差異只出現在 float64 測試輸入。
→ 否證觀測：①任一生產呼叫鏈（含 `multi_tf_generator.py:1432` 傳入之 `_layer6_5_preprocessing`、post-IC）以 registry 入口跑 rank／zscore／gaussian；②IC 頁讀入之特徵欄為 float64。／我跑了：①只讀碼（pre-IC 與 L7 raw 兩處強制關閉）；`_layer6_5_post_ic` 與 registry 並存之時序未查；②未查。

## 主委立場（供共識；可推翻）
殘留之觸發已成立，依「第一性原理·現在修」：**registry 之 zscore 步改用與 legacy 相同之 float64 數值核心（`_rolling_zscore_2d`），結果回存 float32**，使 registry 對 legacy 之差異降至 float32 回存精度；rank 同值差異屬 float32 輸入量化（非核心缺陷），收據記錄、不改。此改需 SPEC v5（殘留第一條改為已處理、Task 1.1 數值基準補「registry zscore 與 legacy 同核心」）並經 r3 審。替代方案：維持殘留，但「為何現在不做」須改寫為三值之一並附本收據數字。

## 攻擊面
- **已排除**：r1 已閉合之面（Phase 1／2 主體、前端、ratio-unsafe、append、sharded 可達性）。
- **我沒查**：
  1. `_layer6_5_post_ic` 是否可能於 `_cgsa_registry` 非空時被呼叫而走 registry 帶 zscore。
  2. 改 registry zscore 為 float64 核心之記憶體／耗時（registry 路徑原為大資料設計）。
  3. polars 單步 zscore 4.7e-5 是否已足（float32 回存之相對精度約 6e-8，但累加式 rolling 本有誤差）。
  4. 收據 `branchdiff` 之相對差定義（分母＝|legacy|，近零放大）是否恰當作 §N 觸發依據；是否應改以「相對於該窗 std」量測。

## 必答（成對）
1. **(1a)** codex：本家 r1 兩條以原反例重跑是否閉合？composer、grok：修法是否正確、無副作用？**(1b)** 實跑輸出。
2. **(2a)** assumed ①② 與「我沒查」1–4 是否成立？**(2b)** 碼證或輕量實跑。
3. **(3a)** §N 殘留第一條之處置：採主委立場（本批改 registry zscore 核心＋SPEC v5）或維持殘留（附三值理由）？**(3b)** 依據（含是否屬資料品質、生產可達性、成本），並指出主委立場之錯處（如有）。
4. **(4a)** 可否收第 1 批（依 (3a) 之結論）？**(4b)** 若否，只列擋之 P0／P1。

## 🔴 停輪紀律
1. 威脅模型＝**意外漂移與未來洩漏**；每條 P0／P1 須附可重現之輸入或操作序列。
2. **不得以「再加一層機制」為修法**；禁以「無 finding」當停輪理由；不得以放寬容差或移出分母掩蓋問題。
3. `CLOSED:` 只准列**本家族前綴**之 ID。

## 產出
canonical 四欄 findings＋**Verdict**。**禁改碼、禁改 `templates/`、禁改 `CLAUDE.md`、禁改 SPEC 與 manifest**。結束前確認 `git status --short -- momentum api frontend tests templates config` 與開跑前相同（主委於本輪期間可能同步 `docs/`、`scripts/fact_keys.json` 之進度文字，不在比較範圍）。完成訊號逐字 `STATUS: DONE`。
