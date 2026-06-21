# B6 日期選擇 warmup-then-trim（選項 1）TODO v2
> 版本：v2(Option 1 三方設計委員會定案)｜基於 SPEC：docs/B6_WARMUP_TRIM_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | max_warmup_bars 全來源 + OutputWindow | Phase1 |
| Task | 2.1 | _layer0 per-TF 載 [ingest_start,end] | Phase2 |
| Task | 2.2 | 單 trim choke 貫穿 4 persist 路徑 | Phase2 |
| Task | 2.3 | warmup 不足偵測 + metadata | Phase2 |
| Task | 3.1 | warmup_insufficient 穿 API+UI | Phase3 |
| 不變量 | QGAIN | 品質增益 flag-on valid_frac≥off+δ(主驗收) | §V |
| 不變量 | NOLEAK | warmup 列不外露(逐 persist) | §V |
| 不變量 | CAUSAL | ingest_index<start + 校準<start 後 | §V |
| 不變量 | FLAGOFF | flag 關=strict-window 不變 | §G/§V |
| 風險 | (b)(d) | 共享 ingestion 多persist+warmup正確性 | §RISK |
| flag | 預設關=B5 strict | 護欄 | §R |
- 合計：Task=5、不變量=4、風險=1、flag=1。
- **雙家族 v2 確認 reconcile(v2.1,兩家判 Option1 框架 sound 只需窄補)**:① max_warmup 補 **L5 cross-sectional**(compute_beta rolling+reference BTC,feature_factory.py:1812)+**L1 advanced atomic 獨立窗**(microstructure/entropy/tail_risk/hurst/perm/mdd);② **POSITION_INDEPENDENT 判定式**=L7 pre-IC 欄−排除 regex(OBV/AD/ADOSC/VWAP/fracdiff_*/adf_*/label_*/post_ic_*)+fixture,品質增益限 non-IC-first/mock IC;③ flag `FFACT_WARMUP_TRIM`=0 不納 hash;④ warmup_insufficient 凍結欄位 needed/available/affected_bars。詳 SPEC v2.1。

## §0 全域規則
- **不承諾 byte parity**(明示);成功=品質增益+因果+不外露。
- **排除 parity 表**(位置相依,文件標+allclose 排除):cumulative(OBV/AD/ADOSC/VWAP)、fracdiff d*、ADF、post-IC rank/zscore、labels horizon。
- **warmup 列絕不外露**(features/labels/HDF5/CGSA raw manifest/registry row_count/browse/checkpoint 全從 start)。
- **因果**:ingest index<start;校準列取 ingest 前段非 start 後。
- **flag 預設關=今日 strict-window(B5)**:golden 不變。
- **warmup 不靜默**:不足→回報+UI;labels 尾 NaN 標 label_tail_nan_bars。
- **不改數值**:只改載入範圍+輸出 trim;不弱化 NaN/inf gate。
- **真實 kline 驗證**(kline_cache.h5)。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B6a | 1.1 | 無 | 中(warmup 估算+OutputWindow) |
| B6b | 2.1+2.2+2.3 | B6a | 中-大(per-TF 載入+trim choke+不足) |
| B6c | 3.1 | B6b | 中(API+UI) |
- Gate:B6a max_warmup=各源最大;B6b 品質增益+不外露逐路徑+因果+flag關golden;B6c npm build+vitest。

## Phase 1
### Task 1.1 — max_warmup + OutputWindow
- SPEC ref：1.1　目標:generate 入口算 OutputWindow + max_warmup_bars(§SPEC 完整清單)。
- 實作要點:新 helper 重用 warmup_lookup;**含 L5 cross-sectional(compute_beta rolling+reference BTC 同 warmup)+L1 advanced atomic 獨立窗(microstructure/entropy/tail_risk/hurst/perm/mdd config 逐列)+L6/meta 顯式窗**;native-tf 各次 TF scale_window_for_native 取 max;排除 cumulative/fracdiff d*/ADF/post-IC/labels。
- 修改檔案:feature_factory.py/preprocessing helper。不可做:不漏源、cumulative 不納。
- 邊界:無 fracdiff/native-tf 不計該源。
- 驗證:max_warmup=各源最大(含 native-tf 放大);`pytest tests/ -k warmup_bars_estimate`。

## Phase 2
### Task 2.1 — per-TF 載 warmup
- SPEC ref：2.1　目標:flag 開各 TF 載 [ingest_start,end];次 TF 用 primary ingest_start 反推 source 跨度;flag 關 strict。
- 實作要點:feature_factory.py:738-749 + multi_tf_generator per-TF。不可做:次 TF 不可共用 primary bar 數。
- 邊界:前史不足→載最早+記;flag 關 strict。
- 驗證:各 TF ingest 起點≤對應 warmup 起;`pytest tests/ -k warmup_ingest_range_multitf`。
### Task 2.2 — 單 trim choke 4 路徑
- SPEC ref：2.2　目標:`_trim_to_output_window` 每公開輸出前套(features/labels/manifest row_count/time_range/sidecar)。
- 實作要點:單 helper;路徑 normal L7/CGSA _layer7_raw·_validate/multi-TF primary_raw/IC-first raw+processed;CGSA L3 stream 中間可暫含 warmup→L7 finalize 裁 manifest。
- 修改檔案:feature_factory.py、feature_storage。不可做:不改特徵值。
- 邊界:多TF對齊後 trim;native-tf 對齊後對。
- 驗證:**不外露**逐路徑首列=start、row_count=|[start,end]|;`pytest tests/ -k warmup_trim_no_leak`。
### Task 2.3 — warmup 不足 metadata
- SPEC ref：2.3　目標:needed vs available 不足→warmup_insufficient;labels label_tail_nan_bars;cumulative cumulative_anchor。
- 實作要點:算 ingest_start 前實得 bar vs max_warmup;寫 metadata。
- 修改檔案:feature_factory.py+contracts。不可做:不靜默降級。
- 邊界:足夠不報;無前史 available=0。
- 驗證:模擬 start 近開頭→回報正確;`pytest tests/ -k warmup_insufficient_report`。

## Phase 3
### Task 3.1 — API+UI 警示
- SPEC ref：3.1　目標:不足 metadata 穿 Pydantic(明定欄)+WS/REST+checkpoint→前端警示。
- 實作要點:api/models+ws/routes+frontend types/元件;文案 needed/available/前N根降級。
- 修改檔案:api/models、ws/routes、frontend。不可做:足夠/flag關不顯。
- 邊界:足夠不顯;flag 關不顯。
- 驗證:`npm run build`+**vitest 2 案例**(不足顯/足夠不顯);`pytest tests/api/ -k warmup_warning`。

### Phase 測試 + Gate
- flag 關:`build_l65_golden_baseline.py --check` PASS。
- 品質增益(主)+子集 allclose(輔)+因果+不外露+PIT。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B6_WARMUP_TRIM_SPEC.md TODO=docs/B6_WARMUP_TRIM_TODO.md FOCUS=不承諾parity/品質增益主驗收/排除表/warmup不外露/因果/flag關strict/真實kline`
→ **雙家族 adversarial 確認 v2(大,(d),Codex+Composer)** reconcile → Composer 實作(Phase1→3) + Codex review。
