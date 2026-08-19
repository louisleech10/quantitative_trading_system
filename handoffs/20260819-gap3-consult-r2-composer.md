# GAP-3 事件型 consult R2 / composer | task-id=20260819-GAP3-X-CONSULT-R2

brief-kind=consult；家族=COMPOSER；輪次=R2；read-only；審查標的=`白話說明/GAP-3事件型討論.md` v6（sha256 前 12＝`685405d0daf9`）。

## Verdict：可進 SPEC 起草（decision-gated）；無全域 BLOCKING

討論檔在 A／B／C 三情境＋case-control 配套＋完整版產生器（U6）上已可支撐 decision-gated SPEC。R1 已成立項（六時間欄 receipt、ms 單位、per-symbol 時間切、二元／條件 IC 分開、分批骨架）**引用不重證**（`handoffs/reconcile/20260819-gap3-x-consult-r1/synth.md` C1–C6）。

本輪須寫進 SPEC 的 R2 增量（非使用者重議 U1–U11）：

1. A／B 的 **label 價格語意**（open 進場）不可沿用序列型預設 close-to-close `return_N` 而不改契約（`COMPOSER-R2-P0-01`）。
2. 多 TF 對齊 receipt 須 **per-TF `feature_cutoff_ms`**，非單一「t₀ 換算成一個 1h 戳」（`COMPOSER-R2-P1-01`）。
3. 連續觸發「兩種都跑」改為 **主預設＋敏感度附錄**，C 與 A／B 預設策略不同（`COMPOSER-R2-P1-02`；K3 定案）。
4. pooled 最小版必含 **跨標的同時刻 time-cluster 權重**，否則 n 灌水（`COMPOSER-R2-P1-03`）。
5. 產生器／`event_filter` 共用引擎須 **欄位相位**（PIT-safe vs outcome／future）分離（`COMPOSER-R2-P1-04`）。

---

## §0 被當成事實的未驗證假設（挑戰 brief `assumed:`）

| # | 前提 | 判定 | 摘要 |
|---|---|---|---|
| A1 | A／B case-control 合法；全 K 線驗證配套 | **assumed→成立（附條件）** | 統計上 case-control 估的是條件母體內 P(y\|x)；實盤部署 estimand 靠 K8 全 bar oracle；學習樣本勝率≠實盤勝率須契約揭露（J1／S3.1） |
| A2 | t₀ open＝前一根 1h／4h close；IC 主線用「前一根戳＋horizon」即可 | **部分成立** | 特徵 as-of 可換算；**label** 仍須 `entry_price_semantic`（open）與 IC 預設 c2c 分離（P0-01） |
| A3 | 三種反例混標 0；GBDT 可行、按種類分報 | **成立** | ML 可訓；須 stratified eval＋(c) 方向洩漏風險；IC 受抽樣母體影響（S3.5） |
| A4 | 連續觸發 C 簇首、A／B 全留降權；兩種都跑 | **部分成立** | 邏輯對；「兩種必跑」對 2 萬事件成本過高→主預設＋敏感度（P1-02） |
| A5 | pooled 必要且可做最小版 | **成立（附權重）** | per-symbol 時間切＋跨標的合併統計可行；同時刻簇必降權（P1-03） |
| A6 | G1–G6 與 `event_filter` 共用底層 | **成立（附 PIT 分層）** | `df.eval` 雛形在 `event_filter.py:76`；`/search` 含 `future_*` 欄（`case_search_engine.py:336`）⇒ 須欄位相位（P1-04） |
| A7 | T1–T3＋T10 產生器；T5／T7 匯入；T8／T9 留欄 | **成立** | 與 U6／§5 一致；T8／T9／T10 欄位形狀見 K1 |

---

## COMPOSER-R2-P0-01

**斷言**: 討論檔 S3.9-1／J2 假設 A／B「t₀ open 決策」可直接以 IC 主線「前一根時間戳＋`return_N` horizon」表達，但現 IC label 語意為 **close-to-close forward return**，與使用者 U4「open 買入」的 label／持有報酬不一致；若不新增 `entry_price_semantic`（及可選獨立 label 欄），條件 IC 與 K8 全 K 線驗證會系統性偏離 A／B estimand。

**碼證**: IC 主線 `_resolve_effective_label_horizon` 從 `labels_df` 欄名 `return_(\d+)` 解析（`ic_filter_orchestrator.py:255-287`）；stage3 後統計仍對連續 `return_N`（`ic_engine.py` 路徑，經 orch `:2776+`）。使用者 A／B：決策＝t₀ **open**、進場價＝open（討論檔 §2-2、U4）。舊 ML 殼同根取值風險 R1 已證（`xgboost_batch_service.py:617-628`）。RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '255,287p'`；對照討論檔 §3.9-1 與 §2-2。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[BLOCKING for SPEC estimand 章] 信心度=High。修法：契約必填 `entry_price_semantic∈{trigger_open,trigger_close,next_open}`＋`label_return_mode∈{open_to_close,open_to_horizon_close,c2c}`；對齊 receipt 寫入實際 `entry_at`／`label_start` 價格來源；條件 IC 在 A／B 預設用 `label_value`（使用者已附實際漲幅，U2）或重算 open-based return，**禁止**靜默沿用序列型 c2c `return_N` 當 A／B 主 label。

---

## COMPOSER-R2-P1-01

**斷言**: J2「12h t₀ 的 open 與 1h／4h 邊界對得整齊」在 **特徵 as-of** 層大致成立，但單一「把 t₀ 換成一根 1h 戳」不足以表達多 TF 特徵截止；對齊失敗清單若只有一個 `feature_row_ts` 會在 12h 觸發＋1h＋4h 並用時漏報半數 TF 越界。

**碼證**: 討論檔 §2-3、J2 宣稱 UTC 00:00／12:00 邊界對齊；Feature Factory 多 TF 獨立計算（`batch_download_service` 支援多 TF `case_models.py:131-134`）。現對齊無 per-TF receipt（R1 C1）。RECHECK: 讀 `api/models/case_models.py:114-135`；grep `feature_cutoff` momentum/ → 0 命中（本輪）。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=High。K2 定案：receipt 內 `feature_cutoffs: {tf: {last_bar_open_ms, last_bar_close_ms, row_id}}`；失敗枚舉增 `missing_tf_bar`／`tf_boundary_ambiguous`／`warmup_insufficient_<tf>`。12h t₀ open 時 1h／4h 各自取 `max(close_ms) < decision_at_ms` 的最後一根。

---

## COMPOSER-R2-P1-02

**斷言**: S3.7 要求簇首與全留降權「**兩種都跑一次**」在 1–2 萬事件規模會使下游 ML／統計計算量近似翻倍，且 A／B（預測型）與 C（確認型）的最優預設不同；寫成硬性雙跑會拖慢 B2/B3 驗收節奏。

**碼證**: 討論檔 §3.7 L103「兩種設定都跑一次」；規模 §3.8 L104–110（150–200 標的、1–2 萬案例）。R1 C3 已要求 `dedupe_policy` 枚舉與 overlap 報告。RECHECK: 討論檔 §3.7–3.8。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=Medium。K3 定案（見 B）：**主報告**用情境預設（C=`cluster` 簇首；A／B=`all_with_uniqueness` AFML 權重）；**敏感度附錄**才跑另一政策；報告必寫 `dedupe_policy_primary`／`sensitivity_policy`／`conclusion_flips_under_alt_policy: bool`。非禁用雙跑，但降為驗收選項而非 B1 硬門檻。

---

## COMPOSER-R2-P1-03

**斷言**: J6／S3.8 將 GAP-4「多標的合併估 IC」併入 GAP-3 最小版正確，但若 pooled 統計不強制 **同 UTC 時刻跨標的簇**（market-wide shock）降權，會把「BTC+ETH+SOL 同刻大漲」算成 3 個獨立樣本，顯著性與 IC 標準誤膨脹。

**碼證**: 討論檔 §3.3 L67–68、§3.8 L108–109 已文字要求「同一時刻一起大漲是一件事」；registry #4 邊界＝事件型先做「per-symbol 切＋pooled 描述統計」，完整 panel IC 可 degraded。無現成 `cross_symbol_time_cluster` 實作（grep → 0）。RECHECK: 討論檔 §3.8；`docs/IC_QUANT_GAP_REGISTRY.md` #4。

**來源摘要**: 白話說明/GAP-3事件型討論.md#685405d0daf9

[MAJOR] 信心度=High。K4 最小版：`time_cluster_id = floor(decision_at_ms / cluster_bucket_ms)`（預設 bucket＝觸發 TF 一根）＋`cluster_weight=1/sqrt(n_symbols_in_cluster)` 或用 bootstrap over clusters；報告欄 `n_events_raw`／`n_time_clusters`／`avg_cluster_size`；未做 cluster 調整時 `capability_status=degraded`、禁宣稱 formal pooled inference。

---

## COMPOSER-R2-P1-04

**斷言**: J10「產生器與 IC `event_filter` 共用底層條件引擎」可行，但 `/search` 進階條件含 `future_max_drawdown` 等 **結果欄**（`case_search_engine.py:333-340`），而 ML 特徵欄不得越過 `feature_cutoff`；若共用引擎不區分 `column_phase`，實作會把 future 欄誤用進 PIT 特徵或阻擋合法觸發條件。

**碼證**: `EventFilter.apply_filter` 對任意欄 `df.eval`（`event_filter.py:76-77`）；`_add_calculated_columns` 計算 `future_*`（`case_search_engine.py:1193+`）；篩選只允許 `price_change`（`requests.py:50`）。RECHECK: `nl -ba momentum/Analysis/event_filter.py | sed -n '55,85p'`；`nl -ba momentum/DataExtraction/case_search_engine.py | sed -n '333,341p'`。

**來源摘要**: momentum/Analysis/event_filter.py#e2c89cb3ad7c

[MAJOR] 信心度=High。K9：引擎落點 `momentum/Analysis/event_condition_engine.py`（純函式）；欄位登記 `phase∈{pit_feature, trigger_outcome, future_outcome}`；query 編譯時對 `pit_feature` 自動注入 `index<=feature_cutoff`；觸發可用 `future_outcome`；匯出 ML 特徵表時 assert 無 `future_*` 列。

---

## A. 逐項對應表

| ID | 表態 | 一句理由 | 建議（若有） | 證據 |
|---|---|---|---|---|
| U2-1 | 技術可行（有風險） | 流程對；舊對齊「精確相等＋靜默跳過」必換 | B1 新契約＋legacy adapter | `case_import_service.py:36`；`xgboost_batch_service.py:618-622` |
| U2-2 | 技術可行 | A／B 預測型與 PIT 可形式化 | `decision_time_rule=trigger_bar_open`＋receipt | 討論檔 §2-2；R1 C1 |
| U2-3 | 技術可行（有風險） | 多 TF 可行但 receipt 須 per-TF | 見 K2 | P1-01 |
| U2-4 | 技術可行（有風險） | 混標 0 可訓練；須分種類評估 | `control_subtype∈{a,b,c}` 必填 | §3.5；S3.5 |
| U2-5 | 技術可行 | 事件後報酬表＝描述統計，無需反例 | K5-(i) | §2-5、§6⑦-i |
| U2-6 | 技術可行（有風險） | 2 萬×多 TF FF 重但可分段抓取 | `/data-preparation` 按案例切片 | §3.8；`case_models.py:122-134` |
| U2-7 | 技術可行 | 出場／連續觸發可延後為參數＋K3 | 時間出場＝答案窗 | §3.6–3.7 |
| U2-8 | 技術可行 | 文檔先行策略正確 | — | U3 |
| S3.1 | 同意 | case-control＋全 K 線驗證＝正確 estimand 分層 | 報告強制兩套基率 | §3.1 |
| S3.2 | 同意 | 三情境契約維度清晰 | `scenario∈{AB_predict,C_confirm,two_stage}` | §3.2 |
| S3.3 | 同意 | 切分／末端／運氣陷阱完整 | interval purge≥答案窗 | §3.3 |
| S3.4 | 同意 | 不切固定窗、變化類特徵主路徑正確 | 補 K7 算子 | §3.4；`rolling_aggregator.py` slope |
| S3.5 | 部分同意 | 混標 0 可行但 (c) 易學方向 | 訓練可選 balance；評估必分種類 | §3.5；P0-01 無關 |
| S3.6 | 同意 | 時間出場第一版誠實 | triple-barrier 列 §N | §3.6 |
| S3.7 | 部分同意 | 政策對但「雙跑」過重 | 見 K3／P1-02 | §3.7 |
| S3.8 | 部分同意 | pooled 必要但須 time-cluster | 見 K4／P1-03 | §3.8 |
| S3.9 | 部分同意 | IC 圖表九成可复用；對齊與 label 語意要補 | `entry_price_semantic` | §3.9；P0-01 |
| S3.10 | 同意 | IC→ML→全 bar 驗證接力正確 | — | §3.10 |
| S3.11 | 同意 | 前端落點合理 | `/pending-features` 占位 | §3.11；U10 |
| T1 | 同意 | 價量觸發＝產生器核心 | G1–G3 | §5① |
| T2 | 同意 | 指標事件可條件化；形態靠標註 | 形態不內建 | §5② |
| T3 | 同意 | 狀態／波動可表達 | 用窗內摘要特徵 | §5③ |
| T4 | 不適用 | 外部源本輪不接 | 登記待資料 | §5④ |
| T5 | 同意 | 日曆＝匯入時間戳 | `event_source=calendar` | §5⑤ |
| T6 | 不適用 | 同 T4 | 登記 | §5⑥ |
| T7 | 同意 | 人工標定＝現 CSV 通道升級 | 新契約 | §5⑦ |
| T8 | 部分同意 | 分析可後排但契約欄位現就要 | `ref_symbol` 等 K1 | §5⑧ |
| T9 | 部分同意 | meta-labeling 合理；須溯源模型 run | `signal_provenance` K1 | §5⑨ |
| T10 | 部分同意 | 區間型須 `event_shape=interval` | start/end ms | §5⑩ |
| P0 | 同意 | 產生器升級路徑 | `/search` | §6⓪ |
| P1 | 同意 | 匯入契約為 SoT | K1 | §6① |
| P2 | 同意 | 批次 K 線概念保留 | 多 TF list | §6② |
| P3 | 同意 | 對齊＋receipt 核心 | K2 | §6③ |
| P4 | 同意 | FF 取決策列 | K7 | §6④ |
| P5 | 同意 | 去重／簇／權重 | K3 | §6⑤ |
| P6 | 同意 | per-symbol 切＋pooled | K4 | §6⑥ |
| P7 | 同意 | 三表分開 | K5 | §6⑦ |
| P8 | 同意 | ML 在學習段 | 成熟度地圖 | §6⑧ |
| P9 | 同意 | 全 K 線驗證＋oracle | K8 | §6⑨ |
| P10 | 同意 | 前端占位 | UAT 後 | §6⑩ |
| G1 | 同意 | 擴條件至 FF 特徵 | 欄位相位 P1-04 | §6末-1 |
| G2 | 同意 | 多組條件→多標籤 | 一次匯出 wide CSV | §6末-2 |
| G3 | 同意 | 方向／情境／答案窗／規則摘要 | K1 | §6末-3 |
| G4 | 同意 | 產生期去重 | 與 K3 同參數 | §6末-4 |
| G5 | 同意 | 合規事件檔直進 import | validator 同一套 | §6末-5 |
| G6 | 部分同意 | 全 bar 重算標籤＝引擎第二輸出模式 | `mode=audit_all_bars` | §6末-6；P1-04 |
| J1 | 同意 | 配套硬正確 | 揭露 sample vs population 基率 | §7 J1 |
| J2 | 部分同意 | 方向對；多 TF receipt 不足 | P1-01 | §7 J2 |
| J3 | 同意 | 不切固定窗＋窗內摘要 | K7 | §7 J3 |
| J4 | 同意 | 反例種類欄＋分報 | K5-(ii) | §7 J4 |
| J5 | 同意 | 時間出場 v1 | — | §7 J5 |
| J6 | 部分同意 | 併 #4 最小版對；須 cluster 權重 | P1-03 | §7 J6 |
| J7 | 同意 | IC 九成复用 | stage3 timestamps | §7 J7；`ic_models.py:150-154` |
| J8 | 同意 | IC 不取代 ML | — | §7 J8 |
| J9 | 同意 | 情境＞類型標籤 | 正交欄位 R1 C6 | §7 J9 |
| J10 | 部分同意 | 共用引擎對；須 PIT 分層 | P1-04 | §7 J10 |

---

## B. K1–K10 技術定案提案

### K1 匯入契約欄位

**提案**（SoT：`momentum/Analysis/contracts/event_import_contract.json` v1）：

| 欄位 | 必填 | 說明 |
|---|---|---|
| `event_id` | ✓ | 全域唯一 |
| `symbol` | ✓ | 標的 |
| `timeframe` | ✓ | 觸發根 TF（如 `12h`） |
| `t0_ms` | ✓ | 觸發根 **open** epoch ms UTC |
| `label` | ✓ | `0`／`1` |
| `label_value` | 建議 | 連續實際報酬（使用者 U2） |
| `direction` | ✓ | `long`｜`short`（單次匯入單向，U4） |
| `scenario` | ✓ | `A`｜`B`｜`C`｜`two_stage` |
| `decision_time_rule` | ✓ | `trigger_bar_open`｜`trigger_bar_close`｜`next_bar_open` |
| `entry_price_semantic` | ✓ | `trigger_open`｜`trigger_close`｜`next_open` |
| `label_window` | ✓ | `{horizons_bars[]}` 或 `{end_ms}`；單位與觸發 TF 綁定 |
| `label_definition` | ✓ | `{rule_id, canonical_digest, agg}` |
| `control_kind` | ✓ | `user_labeled`（v1 實作） |
| `control_subtype` | 反例必填 | `a`｜`b`｜`c` |
| `rule_snapshot` | ✓ | `/search` 條件 JSON＋sha256 |
| `data_snapshot_digest` | ✓ | kline/feature 版本 |
| `event_type_tag` | 選填 | T1–T10 自由標籤 |
| `ref_symbol` | T8 選填 | 參照標的 |
| `ref_timeframe` | T8 選填 | 參照 TF |
| `signal_run_id` | T9 選填 | 模型／IC run id |
| `signal_model_id` | T9 選填 | 產生訊號的模型 |
| `interval_start_ms`／`interval_end_ms` | T10 選填 | 區間型 |
| `event_shape` | ✓ | `instant`｜`interval` |

**六時間點 receipt**（validator 推導寫入，非 CSV 必填）：`observed_through_ms`／`decision_at_ms`／`feature_cutoffs{tf}`／`entry_at_ms`／`label_start_ms`／`label_end_ms`。

**理由**：R1 C2 聯集＋本輪 A／B open label 語意（P0-01）。

**證據**：`case_models.py:16-30` 現欄不足；R1 synth C2。

**可證偽驗收**：`pytest tests/momentum/Analysis/test_event_import_contract.py`（待 SPEC）— 缺 `control_subtype` 之反例列⇒422；`t0_ms` 秒量級⇒`timestamp_unit_reject`。

---

### K2 對齊收據格式

**提案**：

- 輸入：`t0_ms`＋`timeframe`＋`decision_time_rule`＋`feature_tfs[]`。
- A／B `trigger_bar_open`：`decision_at_ms = t0_ms`；每 TF 取 `last_bar.close_ms < decision_at_ms`（含剛收盤那根 iff `close_ms==decision_at_ms`）。
- 餵 IC timestamps：**`feature_row_ms = feature_cutoffs[primary_tf].last_bar_close_ms`**（非 t0）；horizon 用 1h bar 數。
- 失敗枚舉：`no_bar_before_decision`｜`missing_tf_bar`｜`warmup_insufficient`｜`label_window_past_data_end`｜`alignment_gap_ms>tolerance`｜`pit_violation_feature_after_decision`。

**理由**：P1-01；討論檔 §3.9-1。

**證據**：`ic_filter_orchestrator.py:2797-2807` ms/s 判別；`xgboost_batch_service.py:618` 反例。

**驗收**：golden CSV 10 事件；receipt JSON schema validate；故意越界⇒`pit_violation`。

---

### K3 連續觸發預設

| 情境 | 主預設 `dedupe_policy` | 簇間隔 G 預設 | 降權 |
|---|---|---|---|
| C 確認型 | `cluster`（簇首） | 答案窗／觸發 TF 換算 bar 數（48h@12h→4） | 無（代表事件） |
| A／B 預測型 | `all_with_uniqueness` | 同左 | AFML 唯一性 `w=1/|overlap_cluster|` |

**兩種都跑**：改為 **敏感度**（`sensitivity_dedupe_policy`）；主報告只出一種，附錄標 `flip_risk`。

**報告欄**：`n_raw`／`n_effective`／`overlap_fraction`／`mean_cluster_size`／`dedupe_policy_primary`。

**理由**：§3.7；P1-02；R1 C3。

**驗收**：合成 5 連續觸發；簇首 n=1；全留權重和≈1。

---

### K4 切分與 pooled

- **切分**：per-symbol 時間序 70/30（可配置）；`purge_embargo_bars >= max(label_horizon)`；事件 manifest interval-aware purge（R1 C3）。
- **pooled 最小版**：各 symbol 先 OOS，再合併 **cluster-weighted** 均值／CI；欄位 `n_time_clusters`。
- **同時刻簇**：`time_cluster_id=hash(floor(decision_at_ms/bucket))`；權重 `1/n_in_cluster`。
- **registry #4 邊界**：GAP-3 做 pooled **事件統計**；正式 panel IC／cross-sectional 全功能＝GAP-4，未做則 `capability_status=degraded`。

**驗收**：3 symbol 同刻事件⇒effective n&lt;3；無權重⇒報告 degraded。

---

### K5 三張統計表

| 表 | 計算 | 揭露欄 | capability |
|---|---|---|---|
| (i) 事件後報酬 | 每事件多 horizon 報酬；均值／中位／勝率／n／bootstrap CI | `horizons[]`｜`by_symbol` optional | 不需反例；C／finlab |
| (ii) 正反例辨別 | OOS AUC／PR-AUC／Mann-Whitney；按 `control_subtype` 分層；兩段式各一份 | `statistic_kind=binary_discrimination` | 缺反例類⇒`unavailable` |
| (iii) 條件 IC | 事件 mask＋stage4/5；label＝`label_value` 或 open-based return | `statistic_kind=conditional_ic`；A′ fallback 保留 | 複用 `ic_filter_orchestrator` |

**與既有枚舉**：`capability_status∈{available,degraded,unavailable}`；reason 增 `insufficient_events`｜`single_class`｜`pooled_without_cluster_weight`。

**驗證**：置亂 label⇒(ii)≈chance；(iii) IC≈0。

---

### K6 防運氣

- **B1 必做**：label 置亂 oracle；PIT 後移（`label_start < feature_cutoff`）⇒ validator **raise**；單特徵二元 baseline 作 permutation 載體（R1 C5）。
- **B3 接點**：規則→持倉序列→return series→candidate ledger→`min_btl.py`／`pbo.py`（吃 SR／returns matrix，**非** AUC）。
- **不做 B1**：DSR/PBO 全量掃描。

**證據**：`min_btl.py`／`pbo.py` 介面；R1 C5。

---

### K7 變化類特徵補充

| 特徵 | 落點 | 狀態 |
|---|---|---|
| 窗內斜率 | `rolling_aggregator.py` `_compute_slope` | 已有 |
| 差分／變化率 | `feature_factory.py` `_diff` 路徑 | 已有 |
| `ts_argmax`／`ts_argmin` | `derived_operators.py:435-441` | 已有 |
| **bars_since_cross** | 新算子 `momentum/FeatureEngineering/operators/state_counters.py` | **要補** |
| **consecutive_up/down N** | 同上 | **要補** |
| 窗內 max ratio（量／波） | `rolling_aggregator` 擴展 | **要補** |

**IC 共用**：`pit_stats` expanding 原語（`ic_engine.py:17` import）；新算子須 PIT-safe（只用 `<=t`）。

**驗證**：grep `bars_since` → 0（本輪 VERIFY）；補後單測單調性。

---

### K8 全部 K 線驗證輸出

**提案（一次建完整，呼應 U11）**：

1. **混淆矩陣要素**：precision／recall／F1／support（threshold 可選 Youden 或固定 0.5，須揭露）。
2. **PR 曲線**＋AUPRC；**lift** vs 全樣本基率。
3. **訊號頻率**：`n_signals / n_bars` per symbol。
4. **簡單持有報酬**：open@t → close@t+horizon（與 `entry_price_semantic` 一致）；均值／中位／勝率。
5. **分層**：by symbol；by 時間分段（年／季）穩定性。
6. **與序列 IC 並排**：同特徵集「全 bar IC」vs「事件條件 IC」vs「ML 全 bar 掃描」三欄。

**不碰回測層**：倉位 sizing、手續費、滑價模型、複利資金曲線、組合層 long-short（U1 殘留）。

**驗收**：置亂模型分數⇒precision≈基率；持有報酬分佈與標籤窗一致。

---

### K9 完整版事件產生器 G1–G6

- **落點**：`momentum/Analysis/event_condition_engine.py`（純函式）；`api/services/search_task_service.py` 薄包殼；與 `EventFilter` 共用 query 編譯器。
- **語法**：`df.eval` 安全子集＋欄位相位（P1-04）；禁止 `__`／import（沿用 `event_filter.py:39-49`）。
- **多組條件**：OR 合併正例；AND 分組反例 a/b/c；輸出 long 表。
- **PIT**：觸發允許 `future_*`；特徵匯出列禁止。
- **與 `/search`**：升級 `_add_calculated_columns` 登記欄位相位；保留 `price_change` 路徑（U7）。
- **T1–T10**：①–③⑩ 產生器；⑤⑦ import；⑧⑨ 契約欄位；④⑥ 不實作。

**驗收**：同一 query 在 IC stage3 與產生器產生相同 timestamp set（hash 比對）。

---

### K10 分批

| 批 | 內容 | 單獨價值 | 依賴 |
|---|---|---|---|
| **B1** | K1 契約＋K2 對齊＋K3 去重＋K4 切分＋K6 oracle | 資料正確性閘 | — |
| **B2** | K5 三表之 (i)(ii)(iii)＋survivor v2 擴欄 | 統計回答「有沒有訊號」 | B1 |
| **B3** | K7 變化特徵＋K8 全 K 線驗證＋ML 餵料 | 實盤 estimand | B1 |
| **B4** | K9 產生器 G1–G6 | 減少手工作業 | B1 契約 |
| **B5** | API 持久化＋前端占位（U10） | UAT | B2–B4 |

**第一批最小可交付＝B1**（與 R1 一致）。

---

## §1 必查摘要（R2 增量）

1. 矛盾：A／B open 進場 vs IC c2c label — 見 P0-01。
2. 漏項：per-TF receipt、time-cluster pooled、欄位相位 — P1-01/03/04。
3. 不可測：各 K 均附驗收句；數值門檻不寫死。
4. Quant：case-control 基率、混標反例、同刻灌水 — §0 A1/A3、P1-03。
5. 過度工程：完整產生器放 B4；雙 dedupe 降敏感度。
6–11. OOM／cache／API／測試／agent／短命工：R1 結論仍適用；本輪未新增 BLOCKING。

---

STATUS: DONE
