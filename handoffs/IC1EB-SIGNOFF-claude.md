# IC 1e+1b 全 epic 數據正確性簽核 — Claude(編排端,獨立腿)

**範圍**:B1-B5(f277caf→cfcf08e)——HAC 顯著性 kernel/FDR 應用層/縱向主路徑/xsec 最小面/全棧接通/Golden 三腿。
**方法**:非採信任何執行端自報;以下每條有本人實跑 receipt 或親讀碼證。

## 簽核依據(逐項)
1. **統計正確性**:kernel se/t/p 對 statsmodels HAC(use_t)oracle allclose rtol=1e-8(本人 pytest 實跑+composer 顯式重跑至 1e-17 級+codex 單執行緒獨立腳本 5 組);BH q 對 multipletests 恆等;假陽率示範 舊 0.43→新 0.06(binomial 帶內,雙委員重跑)。
2. **不變性(G-1)**:13 顆真資料 baseline 重放,非顯著性欄位五 hash+raw 順序+rolling/decay/grouped 序列 hash 全等(本人三次獨立抽驗 ALL MATCH:B2 前/B2 FIX1 後/B4 後;B5 測試常駐+mutation 轉紅驗證)。
3. **變更可解釋(G-2)**:per-feature 對照顯示 pass 遷移方向=高自相關假顯著轉紅,與病灶診斷(lag-1 自相關≈0.98 之 rolling 串接)一致;fraction_nan_p 記錄 12h 短窗 fail-closed 比例;數字程式生成(codex 抽樣復算)。
4. **fail-closed(G-3)**:樣本不足/全NaN/std=0→p=NaN→p 閘 fail(接真 stage5 閘斷言);SelectionScope 違約 raise;xsec labels 單軸 raise 與 baseline receipt 同型;golden receipt 缺件=紅非 skip。
5. **無洩漏/scope 誠實**:refilter 保 split_context(OOS 不漂全樣本,codex 反例閉合);scope symbol 缺值 raise 禁虛構;n_tests=len(evaluated) 契約 mutation 轉紅。
6. **全棧一致**:fdr toggle 從 UI(custom+具名 preset 雙分支)→schema→stage5→report metadata 同 key 鏈;OFF 唯一表述=canonical enabled=false;前端零統計推導(grep=0),值全出自後端。
7. **adversarial 腿充足**(鐵律):B1-B5 由 codex 執行 explicit adversarial 共 4+6+1+5+3 條 BLOCKING 反例,全部實跑轉正閉合;composer 兩次漏抓由雙家族互補抓回(記分)。
8. **殘留誠實披露**:BH PRDS 假設 note 已入 canonical metadata;500 欄 sha 抽樣之 G-2 解讀降權註記在案;legacy 測試寫 data_cache=既有債(P2);suite 時長 10:43(golden 重放)。

## 結論
**DATA-CORRECT: PASS**(2026-07-11,Claude)

## Delta 附記(2026-07-11 簽核輪後)
簽核輪 Codex 三輪抓出 FDR method 契約縫(fail-open→三層分叉→顯式 None),經 Grok signfix/signfix2+Composer signfix3(斷路器換手)修復;本人逐輪反例親驗(banana/六值矩陣/顯式 None vs 缺鍵)全部 fail-closed。維持 **DATA-CORRECT: PASS**,含上述修復。
