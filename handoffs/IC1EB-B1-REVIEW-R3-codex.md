# IC 1e+1b B1 終驗 R3（Codex）

日期：2026-07-10；範圍：只讀審計 Claude gate transcript、Codex R2、Composer R1 receipt，另抽跑一個短單測；未改受審碼或 data_cache。

## Transcript 內部一致性
- Reconcile 前置：`bash scripts/reconcile_body_hash.sh handoffs/IC1EB-RECONCILE.md` → `b77932d811a9011faf7aeba7b64e2667b5134277c969d971aa6529e9f1a36043`，與 Codex/Composer APPROVED 雙章一致。
- SHA 鏈閉合：receipt L3-L5 前置三檔 SHA，經 `shasum -a 256` 對現況重算皆逐字相同；mutation 只改 production 檔，而 L20/L28 還原 SHA `917c1971…ce08` 與 L3 前置值相同。
- 還原證據：`rg -F TEMP-MUTANT` 於三個受測檔無輸出；`rg 't_stat = float\(mean_z / se\)' momentum/Analysis/statistical_validator.py` → L142 原式，無 production `*2` 殘留。
- 完整 gate：同一 receipt 在 mutation 前 L10 記 `78 passed in 3.66s`，還原後 L23 記 `78 passed in 3.55s`，形成雙綠夾紅。
- FAILED 證據：L14-L15 明列主同判測試 `FAILED` 與 `1 failed`；L16 的 exit 0 與失敗表面矛盾，但 L24 明載原因是 pipeline 吃掉 exit，補跑不接管線後 L25 為 direct exit code 1，矛盾已在同一 transcript 內被可稽核地補正。
- L26 `FAILED lines: 2` 與 pytest 同時在進度列、short summary 各列一次 FAILED 相容；未見計數矛盾。L27-L28 再次確認無殘留且 SHA 回原值。
- 非阻塞證據限制：receipt 未記 mutant 狀態的 SHA，故不能單靠 hash 證明 mutant 的精確字節；但這是完整性限制，不是內部不一致。特定測試紅、direct exit=1、前後雙綠與原 SHA 還原，加上另一非作者的獨立 mutation receipt，足以交叉閉合。

## 短單測交叉驗證
- `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 venv/bin/pytest tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel -q` → `1 passed in 1.79s`；確認 transcript 還原後的現碼主同判測試為綠。

## R2 STILL-OPEN 裁定
- R2 已 CLOSED 的五項維持 CLOSED：paired rerank、兩個 T-1.3 邊界、statsmodels oracle、50-seed M-A 抽驗、source clean；本輪未見反證。Composer R1 的 75-gate/oracle/M-A/mutation 是較早版本的獨立佐證，不冒充 FIX1 後 78-gate。
- 「完整 78 gate」改判 CLOSED：Claude（非作者）在相同前置／還原 production SHA 下取得 mutation 前後各 78 passed；本輪現況 SHA 全吻合且 targeted test 再綠。
- 「真紅 receipt」改判 CLOSED：Claude transcript 保存主同判測試 FAILED、`1 failed`、direct exit 1、還原清潔與 78 passed 複跑；Composer（非作者）另有 `t×2` 破壞 agreement 的獨立數值 receipt。
- 未發現具體偽造疑點；可觀察的 exit-code 表面衝突已有明示原因與 direct 非管線補跑修正，時間順序、SHA 與測試狀態互相吻合。

ASSUMPTIONS_VERIFIED: reconcile 雙章 hash、三檔現況 SHA、production 還原式、無 TEMP-MUTANT、targeted 現碼綠、R2/Composer receipt 的證據邊界。
TESTS_RUN: 上述 targeted pytest → 1 passed in 1.79s；另跑 reconcile body hash、shasum、rg 靜態探針，結果如上。
FAILURES_SEEN: transcript 原 L16 pipeline exit 0；由同檔 L24-L25 direct exit 1 補正，非未解矛盾。
SCOPE_CHANGES: 僅新增本 review 檔；無其他檔案變更。
NUMERIC_OR_SCHEMA_IMPACT: none（終驗只讀；未改 production/test 數值或 schema）。
VERDICT: PASS
