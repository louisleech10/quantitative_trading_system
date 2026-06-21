# B6 v2 warmup-then-trim — Adversarial Review (Composer 2.5)
SPEC=`docs/B6_WARMUP_TRIM_SPEC.md` TODO=`docs/B6_WARMUP_TRIM_TODO.md` | 2026-06-22 | read-only | 對照 v1=`handoffs/20260622-b6-adv-composer.md`+設計委員會=`handoffs/20260622-b6-opt1-composer.md`

## Verdict：需修補後派工（窄範圍）
v2 已閉合 v1 全部 BLOCKING 設計缺口（放棄 byte parity、排除表、max_warmup 全源、per-TF ingest、四 persist trim、PIT/labels metadata）。剩餘為**主驗收可執行性**與 **API/flag 契約**未寫死；非重作。

## v1 findings 閉合逐項
| # | v1 議題 | v2 狀態 |
|---|---|---|
| ① | cumulative burn_in 未實作 | **閉合**：§A 實測 yaml 未消費；run-relative+`cumulative_anchor`；§C/TODO 排除 parity 且不納 max_warmup |
| ② | ADF 位置相依 | **閉合**：§C/§0 排除表含 ADF order；§V③ 校準 slice 上界<start 後段 |
| ③ | max_warmup 漏 L4/L2/rank-zscore/native-tf | **閉合**：Task1.1 明列 L2/L4/L6.5(rank/zscore/ADF/fracdiff)/native-tf/validator fallback；post-IC 正確排除子集 B 非估算 |
| ④ | 多TF+CGSA trim | **大部分閉合**：Task2.1 次 TF 反推 source 跨度；Task2.2 四路徑+CGSA L3 中間可暫含→L7 finalize 裁 manifest+browse/checkpoint；§C⑧ resume 禁偽裝。殘留：compact-native idx_map 未單列測試 token |
| ⑤ | 驗證契約 | **部分閉合**：§V A/B 有 δ=0.05·真實 kline·NaN mask·輔助 allclose。**缺口**：`POSITION_INDEPENDENT` 無判定式（僅指排除表）→實作者可能量錯欄假綠 |
| ⑥ | labels 尾 NaN | **閉合**：Task2.3 `label_tail_nan_bars`/`label_valid_through`；ingest 不延 end（opt1③） |
| ⑦ | PIT | **閉合**：§C③+§V C ingest<start+校準取自 ingest 前段；end 側 label NaN 已文件化非 parity |

## 新/殘留 Findings（修補即可派工）
1. **[MAJOR|High]** §V① 主驗收依 `POSITION_INDEPENDENT` 但未定義欄集合算法。修法：SPEC 補「L7 pre-IC 持久化欄 − 排除表(prefix/regex: OBV/AD/ADOSC/VWAP、fracdiff_*、adf_diff_order、label_*、post_ic_*)」+fixture 列舉。
2. **[MINOR|Medium]** §R flag 無 env 名與 config_hash 納入規則（v1#9/Codex#7）。修法：仿 B3 寫 `FFACT_WARMUP_TRIM=0` 預設+hash 不含 flag。
3. **[MINOR|Medium]** Task3.1 `warmup_insufficient` 無 Pydantic 欄位名（needed/available/affected_bars）。修法：contracts 凍結欄位+vitest selector。
4. **[NON-BLOCKING]** CGSA stream-resume 中間 shard 仍可能含 warmup（§C⑧ 允禁）；IC-first 選特結構差異不再追 parity，品質增益測試應限 non-IC-first 或 mock IC。

## §1 速查
矛盾:無｜漏項:#1｜不可測:#1｜quant:①②已解｜Agent:#2-3

ASSUMPTIONS_VERIFIED: warmup_lookup:67 cumulative 載入未消費;feature_preprocessor:180-182/3334 ADF 用 calibration;label_generator:17-21 horizons max=21;multi_tf_generator:162-165 per-TF _layer0
TESTS_RUN: read-only static(grep/Read), no pytest
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: review only
HANDOFF_NOT_UPDATED: read-only 任務

STATUS: DONE
