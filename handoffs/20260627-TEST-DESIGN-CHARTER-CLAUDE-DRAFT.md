# 測試設計 & 驗證審查章程（Claude 獨立草稿 v0，待雙家族委員會補全）

> 目的:回答「這個 ML 量化交易專案 + 這些 code,該做哪些類別的測試與驗證審查」。
> 使用者(非專業)委派委員會定義完整地圖。Claude 先自產一版([[feedback_claude_own_version]]),交 Codex+Composer 用專業挑戰/補缺,reconcile 成可重用章程,往後每 SPEC 引用。
> 連動記憶:[[feedback_test_design_rigor_reviewed]](測試設計受審 + 可證偽硬門檻)。

## §A 測試類別地圖(每類:測什麼 / 過關條件 / 何時必做)
> 「✦核心」=本專案高風險區(資料正確/防洩漏/數值)必做;其餘按 Task 性質選。

1. **✦資料正確性/完整性**:無假資料、無跨 symbol 污染、schema/dtype/單位正確、來源真實(真 kline 非合成)。過:真實資料跑 + 值守恆。
2. **✦防洩漏/前瞻/PIT**:train/test 切分、purge≥horizon、fit-on-train、OOS 口徑、look-ahead、survivorship。過:**擾動「不該影響」的資料→目標指標不變**(不變量,必可證偽)。
3. **✦數值正確性/golden**:byte/容差 golden、NaN/inf gate、float reduction 穩定、決定性(易變欄如 timestamp 須豁免且白名單寫死)。過:`==`或 atol/rtol 分尺度 + sha256 全表(非抽樣)。
4. **量化/統計嚴謹**:樣本量充足、顯著性檢定、多重比較校正(FDR/PBO/DSR)、IC/ICIR 統計效力、門檻數值有依據(非拍腦袋)。過:統計檢定通過 + 門檻來源可溯。
5. **不變量/性質測試**:守恆律、單調性、對稱性、冪等。過:性質在隨機/真實輸入皆成立。
6. **邊界/退化**:空、全NaN、單值、單列、gap/重複/亂序 ts、極端值、零變異。過:各有明確預期(raise 或 graceful)。
7. **行為不變型重構**:改前==改後(byte/值/數量/輸出大小)。過:deep-equal(易變欄豁免)。
8. **✦整合/真實管線**(G-NEW 教訓):不只 unit fixture,要走真實全 run 路徑(materialized service)。過:真實全量 run 成功 + 結果正確(小 fixture 會漏整合 bug)。
9. **跨 tier / 多 symbol / OOM / resume**:8/16/24/32GB 可重複、多 symbol 隔離、中斷續跑、無孤兒。過:各 tier 跑通 + 隔離不污染。
10. **效能/回歸**:有 baseline、規模化、無「優化改了語義」。過:不慢於 baseline 且輸出不變。
11. **契約/解耦**:`from api.` grep=0、DTO 邊界、factory。過:腳本 exit 0。
12. **API/型別/相容**:Pydantic↔TS 一致、flag-off 回舊行為、新參數有預設+migration。過:契約測試 + 相容矩陣。
13. **冪等/重現性**:同輸入同輸出(扣易變欄)、config_hash 決定性。過:兩次 run 一致。

## §B 測試設計的審查紀律(後設:怎麼確保測試本身嚴謹)
1. **可證偽硬門檻(mutation)**:凡聲稱「驗正確性」的測試,**必須證明把實作改壞它會 FAIL**(反例/mutation)。做不到→標 smoke,不計入正確性保證。廉價綠燈(查欄位/算數字)明確分級,不混入正確性份量。
2. **測真實路徑**:不得用會掩蓋真實差異的 sanitized fixture;要嘛真實 ingestion,要嘛 byte-faithful 重現(含 index 型別與單位)。
3. **防假綠**:不得放寬/刪除既有斷言換綠;diff 既有 assert。
4. **覆蓋追溯**:每個正確性性質→至少一條可證偽測試;缺口明列。
5. **測試章程受審**:測試設計(本表的選類 + 每條性質 + 門檻依據)在 SPEC 階段先產,**交雙家族 adversarial 專門攻擊測試套件本身**(非只審實作)。

## §C 流程接入點(這套何時跑)
- **SPEC 階段**:依 Task 性質從 §A 勾選必做類別 + 寫每條性質的過關條件(可證偽) → 產「測試章程」。
- **SPEC/TODO adversarial**:雙家族除審實作,**另專審測試章程**(§B 紀律)。
- **接回驗收**:Claude 對正確性測試抽查 mutation(改壞會否 FAIL);diff 防假綠。
- **三方數據簽核**:資料正確/洩漏類(§A 1-3)三方獨立 adversarial,真實 kline。

## §D 待委員會補(我可能漏的)
- 我非測試工程/量化專家,本表必有漏類或門檻設定不專業處。請 Codex+Composer:① 補缺類別(如 property-based/hypothesis、metamorphic testing、fuzzing、CI flaky 隔離、test data 版本化…);② 修正各類「過關條件」到專業標準;③ 針對**本專案 code 的具體高風險**(Feature Factory/IC/回測/cache)指名該做哪些;④ 量化/統計類的具體檢定清單。
