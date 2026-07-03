# Golden G2 pin 失效 — 委員會事實檔 + 待裁決（Claude 編，斷路器觸發）

> 2026-07-03 | epic: fracdiff max_lag（SPEC=docs/FRACDIFF_MAXLAG_SPEC.md）
> 背景：Task 0.1 Golden 凍結三輪失敗（①streaming 不回傳 features_df→改讀 L7 raw，已修；②read_d_star_json 誤用→直讀 JSON，已修；③本輪=G2 pin 未生效），依宏觀斷路器開委員會。

## 實測事實（全部有出處，非推論）

1. 三跑（G1-run1/G1-run2/G2-run1，BTC+ETH×1h，窗 2081 bars，各自獨立空 d\* cache）全部完成；
   G1 兩跑 digest 全同（穩定性 PASS）；**G1 vs G2 全部 225,784 欄（含 5,626 fracdiff 欄）digest 全同**
   （出處：/tmp/golden_freeze_stdout3.log 尾段 RuntimeError dump）。
2. 三跑 d\* payload 皆 `max_lag=208`、`fracdiff_hash=84c11cce8bef...` 全同——**G2 的 `max_lag=50` override 沒抵達 preprocessor**（出處：三個 artifacts d_star json 實讀）。
3. `208 = 2081//10`：len(df) 耦合活體實證（窗 2081 bars，非 SPEC 敘事假設的 600→60）。
4. override 寫法：`config["preprocessing"]["fractional_differencing"]["max_lag"] = 50`（freeze script `_config_for`），
   路徑存在（`_fracdiff_mr_config_payload()` 有該節點）。
5. `FractionalDifferencingConfig`（feature_config.py:183-191）**無 max_lag 欄位**；
   preprocessor 讀 `self._config.get("fractional_differencing", {})`（feature_preprocessor.py:144）再 `.get("max_lag", 0)`（:3198）。
6. 假設（待委員驗證）：config_override 進 factory 後經 pydantic `FeatureFactoryConfig` 解析，未知鍵被丟棄
   → preprocessor 拿到的 fracdiff dict 無 max_lag → 永遠 auto。若成立：**現行 HEAD 任何 config 路徑都 pin 不了 max_lag**；
   2026-06-29 「pin=50 d\* 全同」實驗能成立，是因直接餵 dict 給 FeaturePreprocessor（繞過 pydantic）。
7. 附帶：SPEC §G 條件 1 的語意是「證明修後變更純由窗寬造成」——G2 必須是「現行計算行為 + 唯一差異 max_lag=50」。

## 待裁決（G2 在未修碼的 HEAD 上怎麼產）

- **選項 A**：G2 改用 monkeypatch/wrapper 在 freeze script 內 patch（如 subclass/patch `FeaturePreprocessor.__init__` 後把 `fracdiff_config["max_lag"]=50` 注入，或 patch :3198 讀值點）。優點：仍是 HEAD 計算行為；缺點：非純 config 路徑，需論證等價。
- **選項 B**：調序——先實作 Task 1.2（schema 加欄位）為獨立 commit，G2 用「HEAD+僅 1.2」跑（1.2 不動數值路徑，僅 schema）。優點：走真 config 路徑；缺點：G2 不再是嚴格 pre-fix HEAD，需論證 1.2 零數值影響。
- **選項 C**：放棄 G2，改「修後 fresh 跑 vs G1」+「修後把 config 顯式 50 vs 修後 auto」雙對照重定義 §G 條件 1。
- 另裁：事實 6 的 pydantic 丟棄假設請至少一腿實碼驗證（config_override 解析鏈）；若證實，Task 1.2 的必要性升級（現行連逃生口都是幽靈）,SPEC §A 補此事實。

## Claude 腿（獨立版，供挑戰）

**選 A**，patch 點=dict 層非邏輯層：G2 run 在 factory 建好後、generate 前，把 preprocessor 的
`fracdiff_config["max_lag"]=50` 注入（或 patch `FeaturePreprocessor.__init__` wrapper 做同事）。
理由：production 讀值點是 `self.fracdiff_config.get("max_lag", 0)`（:3198）——dict 注入與「config 路徑若通會交付的東西」**在讀值點 byte 級等價**，等價論證閉合在單一 read site，無計算行為差異。
B 的缺點：G2 混入新 commit，「pre-fix baseline」語意被汙染，三方簽核多一層「1.2 零數值影響」的證明負擔。
C 的缺點：丟掉「變更純由窗寬造成」的直接證明，§G 條件 1 弱化。
風險自認：A 的注入若打錯層（如 patch 到 copy 而非實例用的 dict）會靜默無效——**防呆斷言必加**：run 後驗 d\* payload `max_lag==50` 且 `fracdiff_hash != G1`，不同才算 pin 生效（本輪失敗正是缺這道斷言才燒掉一輪 40 分鐘）。
事實 6 我未實碼驗證解析鏈（只驗了兩端），留給兩腿。

## 要求
兩腿各自：驗事實 6、選 A/B/C/D 附理由與風險、挑戰 Claude 腿、指出 §G 文字需怎麼改。結論寫回各自檔。
