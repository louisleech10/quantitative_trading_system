# IC1EB baseline capture 設計審查 — 三方 findings reconcile(編排端裁決)

**輸入**:`IC1EB-BASELINE-REVIEW-{grok,composer,codex}.md`(三家獨立、全 BLOCK)
**裁決者**:Claude(編排端);每項裁決附碼證 receipt;BLOCKING findings 修復後由**原提出方**複驗(Finding 閉合鐵律)。
**產物**:`scripts/capture_ic1eb_baseline.py` v2 重寫+重跑;v1 全寬 capture 已終止,其產物不採用。

## 裁決表

| # | Finding(提出方) | 裁決 | 落地 |
|---|---|---|---|
| F1 | xsec 不消費 feature_filter/max_features(3家 BLOCK) | **ACCEPT**(Claude 親驗:`_apply_feature_filter` 僅 :828 縱向鏈;xsec :921+ 零引用) | 全矩陣改**預物化 inputs 架構**(1a cut1 先例同構):capture 以 `feature_library.load(feature_columns=…)` 物化 500 欄子集 h5+meta 落 `handoffs/ic1eb_baseline/inputs/`,縱向走 `features_path/meta_path`;xsec 由 capture 複刻 service 前置(`load_multi(feature_columns=…, config_hashes=顯式全hash)`→`_append_cross_sectional_labels`→`analyze_cross_sectional`),程序寫死於腳本供 B5 同構重放 |
| F2 | xsec `symbols` 分支 config_hashes=None→吃 latest,標籤不真(codex BLOCK) | **ACCEPT**(service:129-136 親讀屬實) | xsec 一律顯式 per-symbol 全長 config_hash;capture assert 載入欄數=500 且 manifest config 相符 |
| F3 | `passed_features` 非 report 頂層 key→passed_set 假快照(codex BLOCK) | **ACCEPT**(Claude 實跑:`'passed_features' in report`→False) | passed set=summary 集合−union(`filter_log.stage5_thresholds.removed_features.*`),assert 數量==`output_features`;removed mapping 另出 canonical hash(G-2 reason 完整性) |
| F4 | sort_index 掩蔽輸出順序,D-H「ICIR 排序不變」漏檢(codex BLOCK) | **ACCEPT** | 五 hash 保持 canonical(排序後);另增 `summary_feature_order_sha256`(raw 順序)per run;ordering mutation 必轉紅 |
| F5 | `to_numeric(coerce)` 吞 corruption→不同壞值同 hash(codex BLOCK) | **ACCEPT** | G1 欄僅允許 numeric/None/NaN;其他型別 raise(嚴格 gate,不 coerce) |
| F6 | data_cache 寫入違反 §G 唯讀紅線(codex BLOCK) | **ACCEPT**(親讀 `_persist_outputs` 寫死 `data_cache/reports`;`_materialize_features_for_ic` 寫 ingest_cache) | premat+features_path 繞過 ingest cache;capture 內 patch `ICFilterOrchestrator._persist_outputs`→no-op(report 走記憶體;patch 明文入 manifest,B5 同 patch);capture 前後 data_cache tree hash 斷言零 diff 入 manifest |
| F7 | provenance 不足(HEAD 不含 dirty/script/env)+非 atomic 發布(codex BLOCK;grok MAJOR) | **ACCEPT** | staging dir→全驗→atomic rename;manifest 記:HEAD+`git status --porcelain` 全文+capture script sha256+numpy/pandas/scipy/statsmodels 版本+每 report byte sha256/size+完整 effective request |
| F8 | dtypes 未 canonical→None/NaN 假紅(grok MAJOR;composer 低) | **ACCEPT** | 五 hash 對 canonical 化(float64)後 frame 計 dtypes;政策明文:缺值=NaN、dtype=float64 |
| F9 | rolling_ic_series/ic_decay/grouped_ic 未入不變腿(composer MAJOR;grok MINOR) | **ACCEPT** | per run 增 `rolling_ic_series_sha256`/`ic_decay_sha256`/`grouped_ic_sha256`(canonical JSON sort_keys);report byte sha 兜底 |
| F10 | 欄名字典序 500 偏同族(codex CHALLENGE;grok G-2 降權) | **ACCEPT(改制)** | 選欄改 `sorted(names, key=sha256(name))[:500]`(確定性+family 均勻);完整選欄清單入 manifest;family 分布直方入 manifest 供 G-2 解讀 |
| F11 | 雙產生器/雙產物並存(3家) | **ACCEPT** | N=50 產物隔離至 `handoffs/ic1eb_baseline_n50_superseded/`(不刪,審計留痕);canonical=`scripts/capture_ic1eb_baseline.py`+`baseline_manifest.json`,B5 消費端硬編此對 |
| F12 | 補 full(split off)真資料 run(codex;grok/composer 原判排除成立) | **ACCEPT**(升覆蓋從嚴) | +1 顆 BTC 12h e53e2290 `ic_train_test_split=False`,assert scope=full |
| F13 | 補 event 真路徑 run:event filter_base=真 kline,可由分位值導 query 非合成(codex;grok/composer 原判排除成立) | **ACCEPT**(codex 碼證推翻「無真實事件源」前提:orchestrator:1982-1995) | +1 顆 BTC 12h e53e2290 event run,query=真 kline 分位值導出(寫死於腳本),樣本落 marginal 帶則記 tier |
| F14 | 補 labels_path return_5 xsec run(D-H 核心修點)(codex) | **ACCEPT** | +1 顆 xsec labels_path run:由真 kline_cache 計 per-symbol `return_5` 落 MultiIndex labels h5(inputs/;derived-from-real,非合成),B3 後 assert maxlags≥4 用同一顆 |
| F15 | manifest 頂層 mode 誤導/缺 generated_at/8字hash 碰撞(grok/composer MINOR) | **ACCEPT** | 刪頂層 mode;增 generated_at_utc;短 hash 解析 exactly-one 否則 raise |
| F16 | 跨環境重產風險(grok MINOR) | **ACCEPT(政策)** | manifest 記環境版本;G-1 比對限同 venv/同機;禁跨環境重產 baseline |
| F17 | 12h passed=0→pass diff 無資訊(grok G-2 降權;codex 假快照關聯) | **PARTIAL**:pass 集合仍如實凍結(F3 修真值);G-2 簽核說明必須標註 p 閘層診斷為主 | 設計檔+manifest 註記 |

## run 矩陣 v2(13 顆)
9 縱向(3sym×[1h/4a8a0b37,12h/e53e2290,12h/f754aad4])+1 xsec(3sym×12h/e53e2290,顯式hash)+1 full(F12)+1 event(F13)+1 xsec labels_path return_5(F14)。全部走 premat 500 欄 inputs。

## 複驗約定
重跑完成後,三家各對本 reconcile+v2 產物複驗自家 BLOCKING findings(同反例重打),全綠才進 B1 派工;任何一家維持 BLOCK→再修。VERIFY:handoffs/IC1EB-BASELINE-REVERIFY-{grok,composer}.md(PASS)+IC1EB-BASELINE-REVERIFY-R4-codex.md(R4 全 CLOSED PASS)

## R2 複驗結果與裁決(2026-07-10)
- Grok:4/4 CLOSED,VERDICT PASS。Composer:VERDICT PASS。Codex:8 條 STILL-OPEN,VERDICT BLOCK——**全數裁 ACCEPT 修復**(v3):
  - F4b 綱要盲區:G1 欄整欄消失不轉紅 → v3 增 `summary_keys_union_sha256`+`summary_row_key_order_sha256`+G1 缺欄即 raise。
  - F5b ±inf 可入 Golden → v3 finite-or-NaN gate(inf raise)。
  - F8b NaN bit payload 差異假紅 → v3 canonical quiet-NaN 統一位元。
  - F6b 指紋不含內容(mtime 保留型改寫假綠) → v3 全內容 sha256(29GB 實測可承受)。
  - F7b inputs 無防偽章+request 混 harness 鍵 → v3 `inputs_integrity`(逐檔 sha)+request 剝離 expect_*。
  - F10b 裁決走樣(選欄清單/家族分布未落 manifest) → v3 落實 `selected_names(+sha)`/`family_distribution`。
  - F13b q75 落 sufficient 帶,未命中 low-confidence α 變更面 → v3 追加 q95 事件顆(≈85 事件,30-99 帶)。
  - **F14b 裁決文字修正**:原 F14 承諾 per-symbol MultiIndex labels——**結構上不可能**(Claude 親驗 `_load_labels_hdf5`:2798-2814 僅產單軸 DataFrame → xsec 必 raise :951-954,任何內容皆然)。故舊路徑真相=expected-raise receipt(維持);**旗標給 B3 實作者**:SPEC T-3.1b「labels_path return_5→maxlags≥4」的可達性需在 B3 定義(單軸支援不在本刀 scope,勿擅自擴)。
- 附註:event 模式舊路徑無 train/test split(report scope 鍵不存在)→ manifest note 記錄,G-2 解讀時計入。
- v2 產物移 `handoffs/ic1eb_baseline_v2_superseded/`;v3 重跑後由 Codex 複驗(R3),Grok/Composer 收 delta 通知。
