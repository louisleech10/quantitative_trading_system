# B6 日期選擇 warmup-then-trim TODO
> 版本：DRAFT｜基於 SPEC：docs/B6_WARMUP_TRIM_SPEC.md｜日期：2026-06-22

## 階段 1：SPEC ID 覆蓋
| 類別 | ID | 節錄 | 落點 |
|---|---|---|---|
| Task | 1.1 | max_warmup_bars 全來源估算 | Phase1 |
| Task | 2.1 | _layer0 載 [start-warmup, end] | Phase2 |
| Task | 2.2 | 輸出 trim 到 [start, end] | Phase2 |
| Task | 2.3 | warmup 不足偵測+回報 | Phase2 |
| Task | 3.1 | 不足警示穿 API+UI | Phase3 |
| 不變量 | PARITY | 非 fracdiff date-windowed vs 全範圍 byte 一致 | §V |
| 不變量 | FRACEXC | fracdiff d* byte-parity 例外(Option A) | §V |
| 不變量 | FLAGOFF | flag 關=strict-window 不變 | §G/§V |
| 不變量 | PIT | warmup index<start 無 look-ahead | §V |
| 風險 | (b)(d) | 共享 ingestion+warmup 正確性 | §RISK |
| flag | 預設關=B5 strict-window | 護欄 | §R |
- 合計：Task=5、不變量=4、風險=1、flag=1。

## §0 全域規則
- **非 fracdiff byte 一致(核心)**:date-windowed(warmup 足)輸出 == 全範圍同日期(allclose≤1e-6)。
- **fracdiff d* 例外(Option A,三方定)**:d* 用序列前500,date-windowed≠全範圍 byte 一致;文件標明,非洩漏/污染。
- **flag 預設關=今日 strict-window(B5)**:flag 關 golden 不變。
- **warmup 不靜默**:不足→後端回報 needed/available/受影響前段 + 前端警示。
- **PIT**:warmup 區全在 start 之前(過去),無 look-ahead。
- **不改數值**:只改「載多少+輸出trim」,不碰特徵公式/NaN gate。
- **max_warmup 涵蓋全來源**(L1/L3/L6.5/fracdiff/native-tf),勿低估。
- **真實 kline 驗證**(kline_cache.h5)非合成。

## §B 批次
| Batch | Task | 依賴 | 規模 |
|---|---|---|---|
| B6a | 1.1 | 無 | 中(warmup 估算 helper) |
| B6b | 2.1+2.2+2.3 | B6a | 中-大(ingest+trim+不足回報,核心 parity) |
| B6c | 3.1 | B6b | 中(API+前端警示) |
- Gate:B6a 估算=各源最大;B6b 非fracdiff parity allclose+trim列數+flag關golden+PIT;B6c npm build+vitest 警示。

## Phase 1
### Task 1.1 — max_warmup_bars 全來源
- SPEC ref：1.1　目標:max(L1 get_max_warmup_bars/L3窗/L6.5窗/fracdiff calibration_bars/native-tf放大窗)。
- 實作要點:新 helper 重用 warmup_lookup;native-tf 用 scale_window_for_native 換算次要窗。
- 修改檔案:feature_factory.py/preprocessing helper。不可做:不漏來源。
- 邊界:無 fracdiff/native-tf 不計該源。
- 驗證:已知 config→等各源最大(含 native-tf 放大窗);`pytest tests/ -k warmup_bars_estimate`。

## Phase 2
### Task 2.1 — _layer0 載 warmup
- SPEC ref：2.1　目標:flag 開+有 start→mask 保留 start-max_warmup 起;flag 關=strict。
- 實作要點:feature_factory.py:738-749 start_mask 改 `index>=(start_ts-warmup_span)`。
- 修改檔案:feature_factory.py。不可做:flag 關須完全今日行為。
- 邊界:前史不足→載最早+記不足;flag 關 strict。
- 驗證:flag 開起點≤start-warmup;`pytest tests/ -k warmup_ingest_range`。
### Task 2.2 — 輸出 trim
- SPEC ref：2.2　目標:算完輸出前 trim 到 [start,end](warmup 不輸出)。
- 實作要點:L7 前依 index 取 [start,end] 子集;各層/TF 對齊後 trim。
- 修改檔案:feature_factory.py 輸出階段。不可做:不改特徵值。
- 邊界:輸出列數=strict [start,end];native-tf 對齊後對。
- 驗證:**非 fracdiff date-windowed vs 全範圍同日期 allclose≤1e-6**;fracdiff 例外;`pytest tests/ -k warmup_trim_parity`。
### Task 2.3 — warmup 不足回報
- SPEC ref：2.3　目標:needed vs available 不足→結構化回報。
- 實作要點:算 start 前實得 bar 數 vs max_warmup_bars;不足寫 metadata(needed/available/受影響前段)。
- 修改檔案:feature_factory.py + contracts。不可做:不靜默降級。
- 邊界:足夠不報;無前史 needed/available=0。
- 驗證:模擬 start 近開頭→回報正確;`pytest tests/ -k warmup_insufficient_report`。

## Phase 3
### Task 3.1 — 警示穿 API+UI
- SPEC ref：3.1　目標:不足 metadata 穿 Pydantic+WS/REST→前端警示。
- 實作要點:api/models+ws/routes+frontend types/元件;警示文案含 needed/available/前 N 根降級。
- 修改檔案:api/models、feature_factory_ws/routes、frontend。不可做:足夠不顯/flag 關不顯。
- 邊界:足夠不顯;flag 關不顯。
- 驗證:`npm run build`+**vitest 2 案例**(不足顯/足夠不顯);`pytest tests/api/ -k warmup_warning`。

### Phase 測試 + Gate
- flag 關:`build_l65_golden_baseline.py --check` PASS。
- 非 fracdiff parity allclose + fracdiff 例外 + trim 列數 + PIT(warmup index<start) + 不足回報。

## 階段 4：Frozen 前 handoff
`SPEC=docs/B6_WARMUP_TRIM_SPEC.md TODO=docs/B6_WARMUP_TRIM_TODO.md FOCUS=非fracdiff byte parity/fracdiff d*例外OptionA/flag關strict/warmup不足不靜默/PIT/真實kline`
→ **雙家族 adversarial(大,(d),Codex+Composer)** reconcile → Composer 實作(Phase1→3) + Codex review。
