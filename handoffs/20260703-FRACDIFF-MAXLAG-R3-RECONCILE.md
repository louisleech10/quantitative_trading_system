# R3 reconcile — 尾擾 MR codec 處置 + 控制探針重設計（Claude 編）

> 2026-07-03 | 兩腿：R3-{CODEX,COMPOSER}.md（皆核 D1(a)/D2/D3/D4）+ Claude 票
> 證據鏈：receipt 054245Z vs 094044Z 差分 + codec 選型實碼（feature_storage.py:2554-2588 兩腿皆實讀確認）

## 收斂裁決（全數一致，無仲裁）

1. **D1=(a)**：`test_fracdiff_tail_perturbation_invariant` 掛 xfail(strict)，reason 必須誠實載明：
   「**真實護面（尾擾值級因果比對）暫停**——pre-existing storage codec（per-column float16/32 依全窗值域選型）使跨 run 儲存精度不可比（證據=094044Z dtype dump 2^-7 量化差）；非 max_lag/conv 問題；storage epic 修 codec 決定論後轉綠」。**禁止**寫成「噪音/預期漂移」（Codex 約束）。
2. **D2**：`test_mutation_fracdiff_calibration_perturb_fails` 重設計為**顯式單邊擾動契約**：僅 full 跑的 calibration 段擾動、trunc 保持乾淨（受控不對稱）→ 觸發必須**經由 d\* gate**。驗收 gate（Codex 加嚴）：receipt 必須顯示失敗來自 d\* 不變量斷言（match d\* gate 訊息），泛值差觸發不算過。
3. **D3**：值守恆簽核文件必含：①B1+尾擾 codec 家族=pre-existing、已確認根因、storage epic 立案；②**更正 MRFAIL-RECONCILE 裁決案 2 的預測**：「conv 修後尾擾 MR 轉綠」已被 094044Z 推翻（尾擾 MR 改掛誠實 xfail）；③max_lag 面殘留護網=d\* gate＋3 mutation＋full_fit 控制＋（D2 修後）calibration 控制。
4. **D4**：ROADMAP storage epic 立案文字升級為**已確認根因**：per-column float16/32 codec 依全窗值域選型 → 窗長/尾值洩入儲存精度（症狀=NaN 翻面 idx508 + ULP 級 2^-7 值差）。
5. **epic 目標語意更正（使用者可見）**：原定「2 個 strict-xfail 轉綠」結果為——max_lag 缺陷已修並經 golden 等價鏈+mutation 探針證明；但兩 MR 因**另一顆 pre-existing storage bug** 維持誠實 xfail（reason 已從 max_lag 換成 codec），轉綠時點=storage epic 完成後。

## 戳記區（委員 append，勿改上文）
RECONCILE-STAMP: codex APPROVED 2026-07-03 sha256:8b0260a9a51aa031aff9b5c2ac5ff35744e509a03d56e8d21e97d579a633ebee task:fracdiff-maxlag-r3-stamp-codex-20260703
RECONCILE-STAMP: composer APPROVED 2026-07-03 sha256:8b0260a9a51aa031aff9b5c2ac5ff35744e509a03d56e8d21e97d579a633ebee task:fracdiff-maxlag-r3-stamp-composer-20260703
