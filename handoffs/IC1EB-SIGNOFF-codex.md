# IC 1e+1b 全 epic 數據正確性最終簽核（Codex 獨立腿）
日期：2026-07-11；範圍：`f277caf..cfcf08e` B1–B5；判定不採用其他委員 verdict，只以 frozen SPEC、現碼、凍結產物及本輪實跑為據。

## 簽核依據逐項
1. 前置：SPEC/TODO v2.2 已全文核對；reconcile body hash 實算 `b77932d8…043`，Codex/Composer 雙 APPROVED stamp 同 hash。
2. 生成/對齊/split：label horizon 沿既有 resolver；longitudinal preprocessing 只以 train fit，stage4/5/6 消費 test mask，purge=effective horizon；refilter 保留 split_context；scope 缺真 symbol 會 raise，未見跨 symbol 或 future-row 接線。
3. HAC kernel：逐 feature pairwise 對齊、rank-product、Bartlett NW、`L=max(auto_bw,h-1)`、Student-t(df=n-1)；樣本不足/常數/全 NaN 均 NaN，無 i.i.d. production fallback；oracle/邊界/bootstrap 非 slow 測試 17 passed。
4. FDR/門檻：正常 `fdr_bh` 路徑在全 finite evaluated universe、任何前置門檻前算 q；n_tests 與 SelectionScope 同源；ON 用 q、OFF 用 raw HAC p；六格 alpha 與 low-confidence 披露接線一致。
5. **阻塞反例（本輪新縫）**：`SignificanceFdrSchema.method` 是任意 `str`；未知值由 `_resolve_fdr_method` 原樣送入 `adjust_multiple_comparisons`，後者只 warning 後回傳 raw p。實跑 `enabled=true, method=typo, p={.01,.04}` 得 q 原樣 `{.01,.04}`，schema 仍接受並報 `method=typo`；stage5 隨後把它寫成 `p_value_adj` 且 ON 門檻照 q 消費。這是「宣告 FDR enabled、實際裸 p」的可達 fail-open，違反 D-G/資料正確性。
6. xsec：labels_path 與 in-frame `return_N` 都在改名以前解析；未知 horizon 令 t/p/q NaN；已知 horizon 用 period-IC HAC、全欄 BH、仍按 ICIR 排序且不新增淘汰。B3 11 passed。
7. 報告/API/前端：canonical `significance.fdr.*`、SelectionScope、raw p/q/t/null 可達 stage7；前端三 preset ON、toggle 可達後端、只顯示後端 t/p/q，無 `1.96`/i.i.d. 推導；B4 11 passed，`npm run build` 成功（4 個既存 hook warnings）。
8. G-1：快顆重放與五 hash/feature order/series invariant 測試 exit 0；13-run manifest coverage 與 inputs integrity 由測試 fixture 驗；未改 data_cache。
9. G-2：machine diff 6488 列；273/273 old-only 均 `p_hac>p_iid_old`、均 `reason=removed:p_value`、0 new-only；全可比列 5160/5482（94.1262%）p 上升。event BTC 12h 的 45/45 old-only `window_63` lag-1 >0.8（min 0.873411、median 0.980688；95.56% >0.9），故「高自相關假顯著轉紅」方向有真資料支撐；但未把全 273 列自相關逐列凍結，不能擴張成全體皆已量測。
10. G-2/G-3 完整性：newpath manifest/per-feature SHA 實算吻合 `0aa54b2…ab2`/`eb15070…f86`；12h NaN-p 比例 0–0.002008，非爆炸性失效；G-3 把三類 NaN 接到真 p 閘並驗 SelectionScope raise/缺 receipt fail，targeted 命令 exit 0。
11. 防假綠/不變性：舊 pooled 測試只改名保留；已刪 ghost filter 的 low-confidence/NaN 語意由 alpha 六格與 G-3 真閘覆蓋；未見 IC/ICIR/rolling/decay/grouped/coverage/turnover 生產數值被顯著性欄覆寫。

## 受檢環節清單
生成與真實凍結 inputs → label 對齊/horizon → train/test purge/embargo → preprocessing fit scope → bar-level HAC → BH universe/SelectionScope → alpha/p 閘 → redundancy → reporter/metadata → API config/preset/toggle → frontend t/p/q/null → xsec period-IC → G-1/G-2/G-3/hash/fail-closed。

ASSUMPTIONS_VERIFIED: reconcile hash；HAC/BH 正常路徑；test-scope/refilter；xsec horizon；report/UI；G-2 方向、抽樣自相關及 freeze SHA；未知 method 可達性。
TESTS_RUN: B1 non-slow `17 passed`；B2 wiring exit 0；B3 `11 passed`；B4 `11 passed`；B5 G1-fast+G3 selection exit 0；frontend build PASS；另有 schema/apply_fdr 反例 PASS（成功證偽 fail-closed）。
FAILURES_SEEN: stage5 完整 typo-method probe 50 秒無輸出後依規棄跑；較小 schema→apply_fdr probe 已直接重現 raw-p fallback，讀碼閉合至 stage5 q 閘。
SCOPE_CHANGES: 僅新增本檔；l65 inventory 未變，無 restore；其他既有 dirty/untracked 檔未動。
NUMERIC_OR_SCHEMA_IMPACT: 本輪無修改；受審實作新增 HAC p/t、BH q、significance/SelectionScope schema 與預期 passed-set 變更。
DATA-CORRECT: FAIL（FDR method 未限域且未知值 fail-open 回裸 p，仍以 enabled=true/p_value_adj 對外報告並進門檻）
