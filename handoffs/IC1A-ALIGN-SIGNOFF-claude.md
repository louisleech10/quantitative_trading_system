# 1-align 數據正確性簽核 — Claude 腿

**Task-id**: ic1a-align-signoff　**Date**: 2026-07-09　**對象 commit**: fd5866f/854d444/78c85bb/e47933d(SPEC v3 Frozen)

## 獨立探針(真資料,非既有測試,本 session 實跑)
- 資料:golden BTC 1h top50 特徵軸(20352 列)+ 真 `data_cache/feature_klines/kline_cache.h5` close;label 由 `create_label_generator().generate_returns_by_type(close,1,"log")` 生成。
- **G-2 正確必放**:`validate_alignment` PASS,gap_count=0,checked_samples=62。
- **G-1a 平移必抓**:`np.roll(label,1)`(保尾端結構 NaN)→ `AlignmentViolationError: label mismatch at 2024-01-01 01:00:00`(首列即抓)。
- **G-3 fail-closed**:RangeIndex label → `AlignmentViolationError: target_data index must carry timestamps`。
- **G-1b 邊界記錄**:20352 列中段任意單點 +0.01 值腐化未被 64 抽樣命中(敏感區=top-16 突變+gap 邊界,0.01 於 BTC 1h 波動排不進 top-16)。**判定=SPEC 內預期**:Tier-2 為對齊抽樣 oracle,保證抓系統性錯位(平移/錯軸/錯 tf 任一抽樣即中);任意單點值腐化非對齊類故障,全值稽核由 golden byte 級(cut1 golden 逐欄深比對)承擔。
- 回歸:全套 momentum 986 passed,殘 2 紅=pre-existing FF(pre-B1+真資料實證,另案)。golden 2 passed。

## 過程正確性佐證(本管線內)
- B2 RCA 破案:cut1 舊 baseline 凍到 rolling IC join 0 列壞行為;MIXED 裁定後 dtype 保留使 grouped/turnover 與舊 baseline **完全相等**(Codex 探針 maxdiff=0)=index 修正零數值副作用的直接證據。
- M5 雙腿/M6 sha 相等/M2/M4/M7 mutation 全有轉紅 receipt(B1/B2 fix-round+Composer 閉合複驗)。

## 結論
SIGNOFF:claude:DATA-CORRECT
(附帶邊界聲明:Tier-2 抽樣不承諾任意單點值腐化偵測;此類故障由 golden 全值比對層承擔——已記入 HANDOFF 殘留節。)
