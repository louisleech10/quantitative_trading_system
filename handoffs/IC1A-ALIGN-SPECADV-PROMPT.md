# Adversarial Review 派工:1-align SPEC+TODO(task-id: ic1a-align-specadv)

你是 adversarial reviewer——目標是**弄壞這份 SPEC**,不是確認它。用 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` 的紀律獨立審:

- SPEC=docs/IC_PHASE1_1A_ALIGN_SPEC.md
- TODO=docs/IC_PHASE1_1A_ALIGN_TODO.md
- FOCUS=靜默錯位面完整性(consumer-map 有無漏)+ gate 語義誤殺率 + mutation 可證偽性
- 背景偵察(receipt 已 register):handoffs/IC1A-CUTS-ORDER-{claude,codex,composer}.md

## 特別挑戰(至少各給結論,附你自己實跑/實讀 receipt)
1. **consumer-map 完整性**:SPEC §C 列的 5 個下游,是不是全部?grep 所有對 label/features reindex/merge/iloc 的點——第一刀事故=漏 consumer。特查 `_stage3_event_filter`、`analyze_full`、xgboost/ML 服務有無繞過 gate 的 label 消費。
2. **gate 誤殺率**:Tier-1 freq 檢查對真實資料的孔(缺 K 棒)會不會誤殺?`pd.infer_freq` 在有 gap 序列上回 None——SPEC 的「相鄰差中位數」夠嗎?研究型資料 gap 率多高(實測 `data_cache/features/` 真資料)?
3. **Tier-2 oracle 語義**:`lag_offset=spec.lag×to_offset(spec.freq)` 對「第 t+lag 根 K 棒」vs「t+lag×freq 時刻」兩種語義,遇缺棒時結果不同——SPEC 選哪個?錯選會怎樣?
4. **長度巧合面(Task 2.3)**:`_slice_by_mask` 改 fail-closed 後,現行哪些真實路徑會被擋(V1 舊檔/RangeIndex 場景)?會不會弄斷既有綠測試(git stash 驗)?
5. **mutation M1-M6 可證偽性**:每條真的能轉紅?M5 meta-test 設計是否自洽(gate 關掉後測試「須漏」怎麼斷言)?有無廉價綠燈?
6. **Phase 依賴/返工**:Phase 3(cut2 oracle 收斂)會不會反而增加 cut2 回歸風險?defer 是否更優?
7. **與第二刀(1e HAC+1b FDR)的接縫**:本刀 gate 輸出/例外契約,下一刀會不會要改(返工預兆)?

## 產出格式
`handoffs/IC1A-ALIGN-SPECADV-<你的名字 codex|composer>.md`:
- 每 finding:`ID / BLOCKING|NON-BLOCKING / 挑戰點 / 你的 receipt(檔案:行號或實跑輸出) / 建議修法`
- 結尾 `VERDICT: APPROVE|REJECT(有 BLOCKING 即 REJECT)`
- 只讀+寫你自己的輸出檔;不改生產 code/測試;不 git checkout tracked 檔。
