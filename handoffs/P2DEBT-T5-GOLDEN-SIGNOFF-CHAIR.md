# 票5 三方 golden 資料正確性簽核 — 主委獨立版
Task-id: p2debt-t5 | Chair: Claude(Opus 4.8) | Date: 2026-07-12

## 簽核標的
1a cut1 golden baseline 重凍(963ba4f2→fd932a6e / new 對應)+ provenance 閉合。golden 是 IC 正確性 oracle,觸鐵律 a → 三方獨立簽。

## 主委實測簽核(receipt)
1. **新 golden 值正確(B2 對齊修)**:舊 baseline 963ba4f2 把 feature-epoch-index vs label-RangeIndex 做 rolling join→0 列全 None(壞行為);
   新 fd932a6e 修軸後 50/50 有 rolling、7 特徵首落 icir(RCA handoffs/IC1A-ALIGN-B2-GOLDEN-RCA-{codex,composer};grok adversarial 覆核)。舊值本身是 bug,不可保留。
2. **flag-off 語意正確**:config_override ic_train_test_split=false 顯式化;golden 測試自始顯式 split_on=False(test_ic_1a_cut1_golden.py:56)。
3. **語意 replay 通過**:pytest test_ic_1a_cut1_golden.py 2 passed(service 路徑+顯式 flag,新 baseline deep-equal,exempt generated_at)。主委實跑 10 passed 含此。
4. **值守恆意義**:票5 未再 freeze,fd932a6e 為前 session 重凍值;票5 只復原稽核+加守衛,未再動值。
5. **無 look-ahead**:flag-off=無 train/test split=用全樣本 IC(非前瞻);B2 修的是 index-join 非引入未來資料。
6. **provenance 誠實完整**:三事由分述(B2/flag-off/post-B2 drift)、移除錯誤 float64、append-only events、禁刪史;reuse guard content-addressed fail-closed(6 mutation raise)。

## 主委簽核
**GOLDEN DATA-CORRECT: PASS**(新 baseline 修真 bug〔B2〕、flag-off 語意正確無前瞻、語意 replay 通過、provenance 誠實、reuse guard 守衛整合性)。

## 交三方(grok+composer 各獨立簽,codex=實作者迴避)
獨立驗:(1) 新 fd932a6e 是否真修 B2 bug(舊值壞)非引入錯;(2) flag-off 無前瞻、值守恆;(3) 語意 replay 自跑證;
(4) provenance 三事由誠實對應 diff、reuse guard 3 mutation 真 raise。輸出 handoffs/P2DEBT-T5-GOLDEN-{grok,composer}.md,一行 GOLDEN DATA-CORRECT: PASS 或 FAIL+反例。任一疑→不通過。
