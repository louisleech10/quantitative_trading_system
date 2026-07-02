# align 探針 oracle 輸入修正 — 事實檔（兩輪斷路器開委員會）

## 兩輪失敗史（為何開委員會）
- v1(PROBE-FIX):不對稱注入+oracle,但兩探針包在寬 `pytest.raises(AssertionError)` → oracle「no mismatch」的 AssertionError 也算過=無牙假綠(Codex review 抓 BLOCKING)。
- v2(PROBE-FIX2):shape 修對(oracle 正向斷言移出 raises)→ **真跑 2:21:43 兩 align 探針紅**(receipt 20260702T071634Z),但**非注入偵測不到**,是 oracle setup 錯:
  `AssertionError: align oracle: missing timestamps.parquet in .../features/BTCUSDT/1h/<hash>/raw`
- 根因:oracle(`ff_truncation_mr_helpers.py:1211`)讀 `pair.trunc.raw_dir/timestamps.parquet`——**真實管線不產這檔**。v2 的 synthetic smoke 過=fixture 自己造了該檔(合成 fixture 掩蓋真實路徑差異,驗證保真度鐵律再現)。

## 已驗事實(實跑印出)
- 真實 raw dir 內容(pytest-397 殘留實測):`12h_L1_amihud_illiq.parquet`、`12h_L1_apen_100.parquet`、`1h_*.parquet`…**每特徵一檔**,無 timestamps.parquet、無合併大表。
- center/winsor/lag 3 探針同輪 3 passed(它們不依賴該 oracle)。
- 探針結構(v2 shape,保留):先 build 注入 pair → oracle 正向斷言(偵測到 coarse 欄 mismatch)→ 只包 `_assert_truncation_invariants` 於 raises。

## 委員會任務
1. **讀真實工件結構**設計 oracle 輸入:時間戳/邊界 index 從哪拿(候選:任一特徵 parquet 的 index;`pair.*` GenerationArtifacts 有哪些欄位可用——讀 helpers 定義);coarse(4h/12h)欄值從對應 `12h_*/4h_*` parquet 讀。
2. oracle 邏輯不變:在已知 12h 邊界 index 比 full vs trunc 的 coarse 欄值,注入 +1 forward 偏置後必須出現 mismatch(正向斷言)。
3. **禁止**:讓管線多產 timestamps.parquet(不動 production);synthetic fixture 當驗收;放寬 shape。
4. 驗證策略(省時):修完先單跑 `test_mutation_align_lookahead_fails` 一個(~30-40分)確認 oracle 讀得到+注入偵測到,再跑全 5 探針 receipt 版。
