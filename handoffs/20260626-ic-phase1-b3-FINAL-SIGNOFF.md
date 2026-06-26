# IC Phase 1 B3 — 三方數據正確性簽核：PASS（最終）

> 鐵律(2026-06-09)：split/leakage 正確性須 Claude+Codex+Composer 三方獨立簽「資料正確」,真實 kline,不靠使用者驗收。

## 三方齊簽 PASS
- **Claude ✅**：全程獨立自驗,自打反例驗 L1/L2/L3/L4 + allowlist(每輪重打確認 raise/正例不誤殺)。
- **Composer ✅**：round-2 15 probe + round-3 32 adversarial probe,L1-L6 PASS,無等嚴重度新洞。
- **Codex ✅**：實作者兼 adversarial 多輪自挑戰(抓 6+2 真 LEAK 驅動修補),最終「L4 疑消解,B3 可 PASS」。

## 收斂軌跡（adversarial 抓到 confirm-review 漏的洞 → 修 → 再挑戰）
- R1: Codex 自挑戰抓 6 LEAK(Claude+Composer confirm-review 皆漏)→ 教訓 [[feedback_adversarial_beats_signoff]]。
- R2: 修 6;Codex 再挑戰 L2(交錯多 symbol 全域 position 漏)/L4(字串 sentinel)殘留。
- R3: 修 L2 根因(per-symbol local ordinal)+ L4 strip+sentinel。Codex 再找 '<NA>'/'nil'。
- R4: L4 改**有原則 allowlist 權威防線**(allowed_symbols)打破 blocklist whack-a-mole + 補 '<NA>'。
- 最終: Codex 確認 allowlist 消解 L4 疑。

## 已關閉的洩漏向量
- L1 rows-purge 必須 expected_freq(None→raise)。
- L2 train/test pair-level purge/embargo,**per-symbol local ordinal**(非全域 position),交錯多 symbol 不漏。
- L3 空 row_index 不繞過 symbol 檢查;空 train/test pair fail-closed。
- L4 symbol normalize(strip+sentinel blocklist)+ **allowed_symbols allowlist 權威防線**。
- L5 WF 跨 fold embargo 生效。
- L6 CPCV expected test boundaries 獨立重建(非信 returned)。

## 殘留（必須在後續落實，已記錄）
- **R-L4-allowlist**：`allowed_symbols=None` 時 L4 僅 blocklist best-effort(exotic sentinel 如 'nil' 無 allowlist 時可能漏)。**B5/B6 接線 ICSplitAdapter 時必須傳入真實 symbol universe(allowed_symbols)** 才 airtight。
- **R-expected_freq**：`create_ic_split_adapter` 預設 expected_freq=None → gap fail-closed 不生效;B5/B6 接線須從 timeframe 推導傳入。
- **R-split_per_symbol G3**：B6 G3 補 split_per_symbol integration golden。
- **R-opt-in**：契約尚未接 IC 主 pipeline;正確性紅線在接線(1a)前僅保護經 adapter/validate 的路徑(Phase 1 contract-first 範圍)。

## 驗收
33 測試 PASS;解耦 grep=0;wf/cpcv 既有碼零改動;真實 kline_cache.h5。**B3 通過,可進 B4。**
