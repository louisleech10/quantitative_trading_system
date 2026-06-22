# d* Option A 實證量化 — 三方 reconcile（Claude+Codex+Composer）

**日期** 2026-06-22｜**結論：Option A（fracdiff d* 前500列校準）非二階；根源=校準窗;有乾淨修法（固定參考 d*）但屬大改 + (d) 權衡。**

## 三方獨立證據（皆 hermetic，data_cache diff empty）
| 家族 | 設計 | Option A 不穩 | 固定參考修法 |
|---|---|---|---|
| Claude | log-price/EMA 衍生,4 sym,值相關 | d* 一差 corr→~0(ETH 0.00008/SOL 0.039/LINK 0.004) | **corr→1.0 全 sym** |
| Codex | 真實L1/L2 手工20欄,BTC 1h,IC+trim | d*Δ mean0.37/max0.69;Pearson0.51;sel Jaccard(IC≥.01)**0.20** | —(未測) |
| Composer | factory L1+衍L2,ETH/SOL/LINK/ADA | d*Δ mean0.206;Pearson0.52;sel Jaccard mean0.43(SOL**0.0**) | Pearson**0.9999**/ΔIC0.0009/Jaccard**1.0** |

## 收斂事實
1. **非二階**：跨家族/多 symbol 確認。date-windowed vs full-range 的 fracdiff 特徵 decorrelate（Pearson~0.5）、**IC selection 隨窗變**（Jaccard 0.20–0.43，SOL 完全分歧）。
2. **根源**=per-run「前 500 列」regime-specific 校準 → d* 隨窗漂（極端 LINK SMA_55 1.0↔0.055）。**非 fracdiff 本體壞**。
3. **修法可行**=d* 改**固定參考**（每 symbol 全可得歷史校準一次→快取→所有窗共用）→ 重疊段特徵/IC/selection 完全穩定（corr/Jaccard→1.0）。

## (d) 權衡（須使用者/委員會定）
- **現況 first-500**：d* 取窗內最前段=**無 look-ahead**(in-sample)，但 cross-window **不可重現**（IC/selection 含校準 artifact，不可跨窗比較）。
- **固定參考(全史)**：可重現/可比，但短窗 run 用含未來/遠古 regime 的 d*=**輕微超參數 look-ahead**（d* 是平穩化常數非預測訊號，量化界常單次全序列校準）。
- **Option C 中間**：校準用「整個選定窗」而非前500 → 仍 in-sample 無 look-ahead、更穩(更多資料)，但仍窗依賴（部分改善非全解）。

## 與舊決策 reconcile
- [[project_dstar_walkforward_rejected]]（2026-06-17）否決的是「WF in-run d* 漂無 OOS 下游價值」+ d_min floor。**本案不同問題**=cross-window 可重現性;固定參考是**消除漂移**（與舊「反 drift」立場一致，非重議 WF）。舊記憶「勿重議除非真實 L1/L2 配對證據」→ **現已有該證據**。

## 建議（Claude 自產）
- finding 真實且影響研究可重現性，**但修法=改共用預處理 d* 校準路徑→大任務 + 命中 (d)**，不宜今日急改。
- **今日收尾**：記錄 finding + 限制（Option A run 自洽但 cross-window 非 parity，勿跨窗比 IC/selection）、更新 memory；**固定參考 d* 修法立為未來 epic**（走完整管線:SPEC/TODO/雙家族 adversarial/實作/review）。
