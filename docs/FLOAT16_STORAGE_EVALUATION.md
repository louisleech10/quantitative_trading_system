# L7_raw float16 儲存評估（2026-06-16，委員會三方）

> 起因：#2 d* 調查意外發現 CGSA L7_raw 將特徵存 float16（frame path float32），max abs diff ~0.0009。問「是否該改 float32」。
> 報告：handoffs/20260616-float16-eval-{codex,composer}.md。

## 三方裁定：維持 float16 儲存，本批不動
- **float16 冷存可接受**：現行條件式 float16 + float32 fallback（feature_storage.py float16 gate）；1e-3 roundtrip gate 合理，~0.0009 屬預期量化誤差。
- **不全面改 float32**：(1) L7 體積 ~2×（8GB tier disk/RAM 吃緊、OOM 風險）；(2) 只消除量化差，**不解決 T4 其他結構差異**（index dtype int64/datetime、L6.5 拓撲、dead-drop）；(3) 改輸出大小需 SPEC+tier 驗證+使用者批准（不可靜默）。
- **精度風險為消費端特定且未證實**：Spearman IC rank / XGB/LGBM 樹模型 中低風險（依排序/分裂）；Pearson IC 邊界 / 線性 / NN / threshold-like 較敏感。無 A/B 證據前不應據直覺全改。

## 可選後續 ticket（非本批，需要才做）
1. **strict/training 讀取升 float32**：FeatureReader strict/training 路徑回傳 float32（小改、不改儲存、無體積代價）——避免 float16 dtype 進模型運算，但無法復原已落盤量化資訊。
2. **float16 vs float32 A/B 驗證**：同 symbol/tf/config 寫兩份，量 Spearman/Pearson IC top-k overlap、IC threshold flip count、XGB/LGBM AUC/importance drift、proba drift、backtest metric drift。**唯有 A/B 顯示 IC/ML 邊界翻轉實質**才考慮敏感 feature family（ratio/normalized/low-variance）強制 float32。
3. **manifest 顯性化**：raw parquet storage policy 註明允許 `rtol<=1e-3` lossy quantization，value-exact parity 不適用（解釋 #2 T4 為何 out-of-scope）。

## 結論
維持現狀 float16 儲存；無立即動作。若未來下游精度疑慮，先做 strict-read 升 float32（低成本）+ A/B，再決定是否敏感欄改儲存 dtype。
