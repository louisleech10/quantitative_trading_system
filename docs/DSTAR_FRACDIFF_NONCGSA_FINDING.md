# 發現報告：非 CGSA path fracdiff 整體失效（d* cache 接線項喊停，待使用者決策）

> 日期：2026-06-12 | 作者：Claude | 狀態：**待使用者決策**
> 背景：HANDOFF 第 1 批含「非 CGSA d* cache 接線（missing_context 致大記憶體 tier 全寬 L6.5 ADF 30+分）」。
> 動工前實測（鐵律：實測 > 假設）推翻了此前提，且真實問題命中高風險原則 (a)(b)(d)，按任務分派規則
> 升級為「大」，**不得按中型靜默開工**，故抽出本批、留此文檔。

## 1. 實測設定（真實路徑，非合成 fixture）

```python
os.environ["FFACT_USE_CGSA"] = "0"   # 非 CGSA frame path
factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
res = factory.generate_features("BTCUSDT", "12h",
        config_override={"preprocessing": {"enabled": True, "fractional_differencing": {"enabled": True}}},
        persist=False, start_date="2024-06-01", end_date="2024-12-01")
```

實際輸出（log：/tmp/dstar_repro.log）：
- `ELAPSED 113.1s, feature_count=165268`，`factory._current_symbol/timeframe = BTCUSDT / 12h`（context 完整）。
- **204 次** `[L6.5] Layer parse failed for FracDiff filter: unparsed_columns=2000/2000 allowed=['L1','L2'] ... treating unparsed columns as non-target`。
- `[d_star_cache]` 字樣 **0 次**（含 missing_context warning 0 次）。
- `data_cache/feature_preprocessing/` **沒有**新增任何 BTCUSDT d_star 檔（既有檔為 ETHUSDT CGSA run 與 SYNTHETIC 測試殘留）。

## 2. 根因（與 HANDOFF 描述不同）

- 非 CGSA frame path 的欄名是**裸特徵名**（如 `close_trend_EMA_5`），而 fracdiff 目標過濾
  `_FRACDIFF_LAYER_RE = re.compile(r"^(L\d+)_")`（`preprocessing/feature_preprocessor.py:65`）
  要求 `L<digit>_` 前綴 → **全部 unparsed → 全列 non-target → fracdiff/ADF/d* cache 整段不執行**。
- CGSA path 正常，因為走 registry 的 `source_layer` 分支（`_filter_fracdiff_target_columns` 的
  `if source_layer:` 路徑），不靠欄名 regex。
- `missing_context`（symbol/timeframe=unknown 時 disable cache）是**另一個**條件，本次實測未觸發。
  HANDOFF 寫的「missing_context 致 30+分 ADF」與實測不符：fracdiff 根本沒跑，何來 cache miss。
- 「全寬 L6.5 ADF 30+分」的既有觀察推測來自**測試**：synthetic fixture 欄名常帶 `L1_` 前綴
  → regex 可解析 → fracdiff/ADF 全跑（慢）；生產裸名 → 靜默 no-op（快但功能失效）。
  與既往「fixture 與真實路徑不符」事故同型。（此句為推測，未逐一驗證各測試欄名。）

## 3. 影響評估

- `FFACT_USE_CGSA` 預設 `"1"`（`feature_factory.py:873`）→ 生產主路徑是 CGSA，**不受影響**。
- 受影響的是非 CGSA frame path（legacy / 測試 / 顯式關 CGSA 的場景）：
  fractional differencing 在該 path **從未生效**（靜默），輸出與 CGSA path 數值行為分歧。
- 原第 1 批的「修接線享受 cache」**無從談起**：要先讓 fracdiff 在 frame path 能選中目標欄，
  才有 d*/ADF 可 cache。

## 4. 為何升級為「大」

修法需要 factory 把「layer → 欄名集合」歸屬傳給 preprocessor（或欄名帶層標記），動
`feature_factory.py` / `feature_preprocessor.py` 共用路徑；修好後非 CGSA 輸出將**新增 fracdiff
數值行為**（原本沒有→有）。命中：
- (a) 數值正確性/資料品質、(b) 跨模組共用路徑、(d) ML 訓練/回測正確性（fracdiff 影響特徵平穩性）。

## 5. 待使用者決策（三選一）

| 選項 | 內容 | 代價/風險 |
|---|---|---|
| A. 修復對齊 | frame path 傳入 layer 歸屬，使 fracdiff 與 CGSA 行為一致；d* cache 隨之生效 | 大任務管線（Codex 實作+Composer review+雙家族 adversarial+Golden）；非 CGSA 輸出改變 |
| B. 顯式化現狀 | 文檔+log 升級為明確「frame path 不支援 fracdiff」，config 開了就 warn/raise；不修 cache | 最小工程；接受兩 path 永久行為分歧 |
| C. 棄用非 CGSA path | 評估直接 deprecate frame path（生產已走 CGSA） | 需盤點測試與 legacy caller，另立批次 |

建議：**A**（功能本意如此，且第 3 批測試 triage 也會撞到這裡），但排程上可放在第 2/3 批之後。

## 6. 連帶修正

- HANDOFF 第 1 批該項描述（missing_context 根因）需更正為本文檔結論。
- 第 1 批其餘 5 個 follow-up 小修不受影響，照拍板中型管線進行（見 `docs/BATCH1_FOLLOWUP_SPEC.md`）。
