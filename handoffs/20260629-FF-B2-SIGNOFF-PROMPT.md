# 三方數據簽核:FF 因果可用於量化? + B2 測試設計(委員獨立腿)

使用者無法自判,全權委派委員會(三方數據簽核鐵律)。讀 Claude 腿 `handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-CLAUDE.md`(含完整證據)。

## ⚠️ 重要:勿重跑全鏈
generate_features 全開 ~14分/次,反覆 timeout。**從 Claude 腿的證據 + 讀碼判斷**;只在必要時做小範圍 targeted 實驗(如比幾個欄、讀某層 rolling/lag/preprocess 是否用未來)。

## 你的兩個獨立判斷(各給結論+理由)
### A. FF 因果性:可用於量化?
- 證據:截斷尾 bar → 暖機後前綴特徵「值」相同(僅差 float16 儲存精度 0.1% + 列數依賴 NaN/dead 處理);mutation 注入 look-ahead 會造成數量級差異(測試抓得到)。
- **讀碼複核**:抽查 L2 衍生 / L3 rolling(`operators/numba_rolling.py`)/ L4 lag / L6.5 preprocess(`preprocessing/`)有沒有哪層在算「過去某列」時用到「未來某列」(真 look-ahead)?Claude 判沒有,你獨立查證/反駁。
- 兩個 caveat(float16 可重現性、特徵集列數依賴=stateful-param-audit epic)同意?
- **SIGN-OFF: FF-CAUSAL PASS / HOLD**(任一方 HOLD→不通過,說明哪層可疑)。

### B. B2 測試設計怎麼收
- Claude 提:common-valid-region(交集欄、both-non-NaN 位置)值在 2× float16 容差(rtol 2e-3)內一致;columns drop 差異記錄(設上限門檻防大量掉欄掩蓋);NaN mask 良性化;mutation 探針保留必紅;fracdiff 專屬 MR 保留。
- 挑戰:這樣會不會放走真 look-ahead?(look-ahead 是否一定在「值」上現形,還是可能只在 NaN mask?)columns drop 上限該設多少?NaN mask 退讓到哪仍可證偽?
- **B2-DESIGN: 同意 / 修正**(具體)。

## 輸出
寫 `handoffs/20260629-FF-B2-SIGNOFF-<你>.md`:A 簽核 + B 設計結論。只寫你的檔。完成 STATUS: DONE。
