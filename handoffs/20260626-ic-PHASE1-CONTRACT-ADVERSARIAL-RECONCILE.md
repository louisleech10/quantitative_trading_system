# IC Phase 1 1-contract — 雙家族 adversarial Reconcile（Claude 綜合）

> 兩家獨立 review：CODEX(GPT-5.5) / CURSOR(Composer 2.5)。兩家 Verdict 皆「需修補後派工」。
> Claude 已自驗關鍵指控（非盲信 reviewer）。

## 雙家收斂（兩家都點，最高優先，必修）

| # | 收斂 finding | 等級 | Claude 自驗 |
|---|---|---|---|
| R1 | **per-symbol 只解跨 symbol；單 symbol 內 positional purge 遇 gap/缺bar/重複/未排序 timestamp 仍洩漏**（purge_gap=5 是 5 列非 5 bar/5h）。(d) 紅線。 | BLOCKING | ✅ 真（CPCV `mask[purge_start:purge_end]` 連續切片） |
| R2 | **「只加 surface、byte 不變」與 Task 3.1/3.2 觸碰 result path 矛盾**；需把 flag-off byte-for-byte 寫成可測契約。 | BLOCKING | ✅ 真（`get_result`→`_to_json_compatible` 共用路徑） |
| R3 | **CPCV 既有會自動降 embargo(silent relaxation)**，adapter 不改 CPCV 就繼承 → 與 fail-closed 衝突。 | BLOCKING/MAJOR | ✅ 真（`combinatorial_purged_cv.py:75-79` 實見） |
| R4 | **HDF5 預設可疑**；應傾向 Parquet（檔案大小/篩選/8GB tier/業界慣例）。 | MAJOR | ✅ composer 加碼證據：`feature_reader.py` V7 Parquet-only、Phase 3 串流亦 parquet → HDF5=二次遷移 |
| R5 | **API negotiation/flag-off byte equality 未定**；v1/v2 schema、TS 對照、flag config 位置缺。 | MAJOR | ✅ `api/core/config.py` 無 `ic_response_v2` key |
| R6 | **舊 JSON 共存無 SSOT / 雙寫一致性**；artifact vs memory JSON 兩套數值風險。 | MAJOR | ✅ |
| R7 | **§G Golden 不足**：單 BTC/1h、抽樣 hash；config_hash 外推 TODO 不可凍結。應拆三 golden(v1 byte / artifact 全表非抽樣 / 多symbol+gap 反例)。 | MAJOR | ✅ |
| R8 | **[C-8] artifact schema 欄位空殼 + [C-10] 讀端點空殼**（無欄名/route/型別）。 | MAJOR | ✅ |
| R9 | **SplitPlan/RowMaskPlan 缺 canonical row identity**（mask 相對誰？index 是 positional/timestamp/row_id？）。 | MAJOR/MINOR | ✅ |

## 單家獨有（仍須處理）

- **[CURSOR 獨有 BLOCKING] §A 事實錯誤：WalkForwardValidator 無 `def split()`**（僅 CPCV 有）。我 §A 把「兩工具皆有 split()」當已驗證 = fact-as-assumption 違規。**✅ Claude grep 自驗:WF def split=0。** codex 未抓到(接受了我的錯前提)→ 雙家族價值印證。
- [CURSOR] §A「30 測試證 purge 正確」過度陳述:全 synthetic、無真實 kline/gap → 不可代替 [C-3] 測試。✅ 真。
- [CODEX] eval_status 預設 EVALUATED 掩蓋未遷移路徑 → 用 UNKNOWN_LEGACY 邊界狀態。
- [CURSOR] cross_sectional 模式未進 [C-3] 範圍 → §N 登記本刀不涵蓋。

## 分歧（一處）

- **HDF5 vs Parquet**：codex=「別在 SPEC 寫死,先補 decision record 比較」；composer=「直接建議 Parquet,附 codebase 證據」。
  - **Claude 裁決:採 Parquet**。理由:composer 證據強(feature_reader V7 已 Parquet-only、Phase 3 串流亦 parquet,選 HDF5 必二次遷移),且 codex 不反對 parquet 只要求論證——composer 已提供論證。仍在 §P 附權衡表(檔案大小/cold read 延遲 10K/100K/430K/8GB peak RSS)滿足 codex 要求。**此為技術決策,依委員會收斂採納,對使用者透明不另問**(改寫我先前給使用者的 HDF5 預設)。

## 結論
SPEC 現稿**不可派工**,雙家共識。Claude 據上修 SPEC（R1-R9 + 單家項 + 採 Parquet）。修完重跑機檢 → 生 TODO → 對 TODO 再跑必要 review → gate → 派實作。
