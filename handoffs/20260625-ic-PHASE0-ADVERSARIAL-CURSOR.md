# IC Phase 0 SPEC — Adversarial Review（Composer 2.5 / Cursor）

> 審查者：獨立 adversarial（雙家族之一）｜日期：2026-06-25  
> 輸入：`docs/IC_PHASE0_SPEC.md`、`handoffs/20260625-ic-PHASE0-MANIFEST.md`、`handoffs/20260625-ic-PHASE0-BRIEF.md`、`handoffs/20260624-ic-grouped-crash-perf-ANALYSIS.md`、`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` V13  
> 程式對照：已讀 `ic_engine.py`、`ic_filter_orchestrator.py`、`ic_config_schema.py`、`ic_analysis_service.py`、`ic_models.py`、`kline_storage.py`、`useICAnalysis.ts`、`icAnalysisStore.ts`；並實跑 `read_klines('BTCUSDT','1h')` + `_get_time_index` / `_iter_time_groups`。

---

## Verdict：需修補後派工

SPEC 根因與 Phase 切分大致正確，§A 多數項有碼證；但 **IC-TIMEAXIS 漏報第二個真實路徑崩潰點**、**IC-BYVOL fail-closed 未綁定 schema 預設**、**feature_filter / max_features 語義與 F-6 矛盾**、**§G golden 在現況下部分不可捕獲**，且 **Task 2.3 仍待收斂才能鎖驗收**。修補上述 SPEC 條目（不需重寫整份）後可派工。

---

## Findings

### §0 挑戰前提（置頂）

1. **[BLOCKING|High]** §A#2 寫「bug 在真實路徑必觸發」但只描述 1970 錯軸，**漏掉 `_iter_time_groups` 在真實 kline 路徑會直接 AttributeError**。  
   **證據**：§A#2「落 numeric 分支 → unit=ms → 年份全錯成 1970」；`ic_engine.py:1011` `time_index.to_series().groupby(time_index.year)`；實跑 `read_klines` → `RangeIndex` + `timestamp[0]=1704067200`（秒）→ `_get_time_index` 回傳 `Series`（1970 日期）→ `_iter_time_groups` → `AttributeError: 'Series' object has no attribute 'to_series'`。  
   **會怎麼失敗**：修完 C-1（model_dump）後，grouped 路徑在 by_year/by_quarter **先崩潰**，T-3 若只斷言 by_year=1970 鍵會永遠達不到；實作者只修 unit 仍回傳 Series 則依舊崩潰。  
   **修法**：Task 2.1 明寫 `_get_time_index` numeric 分支須 `return pd.DatetimeIndex(pd.to_datetime(...))`（或等價），並加單測：RangeIndex + 秒級 `timestamp` 欄可走完 `_iter_time_groups('year')` 不拋錯。

2. **[MAJOR|High]** §A 標「六項皆附實際跑了什麼」——#1/#3/#4/#5 主要是 grep/讀碼；#6 自承「委員會來源，實作端須先讀碼確認」。  
   **證據**：§A 表頭「皆附實際跑了什麼、印出什麼」；#6「此項為委員會來源」。  
   **會怎麼失敗**：gate/M-2 把未實跑項當 fact-verified，下游 golden 假設已碰真實路徑。  
   **修法**：§A 每項加標籤 `fact-verified` / `code-verified` / `assumed`；#2 補上本次實跑的 Series/crash 輸出。

3. **[MAJOR|High]** §A#2「唯一真實路徑」推論鏈**核心成立**但**結論過窄**：`read_klines` 確實 `RangeIndex`+秒級 `timestamp`（實跑 20352 rows，`1704067200`→2024-01-01）；**現有 grouped 單測全用 `DatetimeIndex` 當 `raw_data.index`**，從未覆蓋 kline 形狀。  
   **證據**：`kline_storage.py:1107-1109`；`tests/momentum/test_ic_engine.py:105-109` `index=pd.date_range(...)`；`test_ic_filter_orchestrator.py:530-533` DummyReader 同樣 DatetimeIndex。  
   **會怎麼失敗**：C-3/T-3 若沿用 DatetimeIndex fixture → 秒/毫秒 bug **假綠**。  
   **修法**：T-3/C-3 fixture **禁止** DatetimeIndex index；必須 `reset_index` + 秒級 `timestamp` 欄，與 `read_klines` 一致。

### §1 十類失敗模式

**1. 矛盾/互斥**

4. **[BLOCKING|High]** F-2 要讓 `max_features` **真截斷**，F-6 要改名 `preview_limit` 並暗示「非正式 universe」；前端預設仍 `max_features: 30`（`icAnalysisStore.ts:187`），與 §C「不靜默截斷、不改 universe 語義」張力未解。  
   **證據**：Task 3.2「max_features 截斷」；Task 3.4「preview_limit 改名」；§C「不靜默截斷特徵」。  
   **會怎麼失敗**：落地後使用者仍以為 30 是「預覽」卻進 IC 管線改 universe；或 F-6 只做 alias 但 orchestrator 仍當正式篩選。  
   **修法**：SPEC 明訂：**預設行為改為不截斷（全量）**；`max_features`/`preview_limit` 僅在 UI 明示「預覽模式」時生效；metadata 必須 `truncation_mode: preview|none`。

5. **[MAJOR|Med]** Task 2.3「委員會收斂後定」與 §A「不問使用者」並存，但 **B-1/B-2 驗收仍雙分支**，派工 agent 無法寫死 pytest。  
   **證據**：Task 2.3「改法：待雙家族 adversarial 收斂 (a)/(b)」。  
   **會怎麼失敗**：實作選 (a) 或 (b) 與另一家族結論衝突，驗收標準分裂。  
   **修法**：雙家族 review 合併後把 Task 2.3 改成單一路徑（見下方 IC-BYVOL 建議）。

**2. 漏項/端到端**

6. **[MAJOR|High]** U-4「HTTP poll fallback」有 `fetchTaskStatus`/`fetchResult`（`useICAnalysis.ts:194-212`）但 **onclose 無限重連未接 poll**；SPEC 未寫觸發條件、輪詢間隔、completed/failed 時如何停輪詢。  
   **證據**：Task 4.4「WS 不可用 → HTTP poll fallback」；`useICAnalysis.ts:110-117` 無限 `setTimeout(connectProgress, 3000)`。  
   **會怎麼失敗**：Agent 各寫一半，WS 斷了仍重連不 poll，或 poll 與 WS 雙寫狀態。  
   **修法**：補狀態機：retry≤3 → poll `/task/{id}` 直到 terminal → `fetchResult`；失敗時 `setError(status.error)`。

7. **[MINOR|Med]** Phase 0 §N 排除 resume/retry；IC 長 run 失敗仍全量重算——可接受，但應在 §N 註明 **不阻 Phase 0 派工**（避免 agent 自行加 checkpoint）。  
   **證據**：§N「串流/train-test/case-control…不做」。  
   **修法**：§N 加一句「IC task resume/retry 留後 Phase，本 Phase 不實作」。

8. **[MINOR|Low]** F-1 加 `ICConfig.feature_filter` 後，**yaml 預設檔無 migration**——Pydantic 可 `None` 向後相容；但 `load_ic_config(api_override)` 目前 **靜默丟棄** `feature_filter`（實跑 `has feature_filter False`）。Task 3.1 驗收須覆蓋此路徑，SPEC 已暗示但未寫成 fail 條件。  
   **修法**：Task 3.1 驗證加：`api_override` 含 `feature_filter` 時不得被 `model_validate` 丟棄。

**3. 不可測驗收**

9. **[MAJOR|Med]** C-3/T-3「未修時 fail、修後 pass」在 **單一 CI 快照無法同時成立**；需 TDD 兩 commit 或文檔化「先紅後綠」。  
   **證據**：§V「C-3/T-3 測試須未修時 fail、修後 pass」。  
   **會怎麼失敗**：Agent 為綠燈寫條件過弱測試，或跳過紅階段。  
   **修法**：§V 明寫「同一 PR 內須可展示：僅加測試 commit 紅 → 修 code commit 綠」；或接受「回歸測試只保證修後行為 + 註明 bug 重現腳本在 `tests/fixtures/`」。

10. **[MAJOR|Med]** U-1「event loop 不被阻塞、WS heartbeat 不斷」**無具體 pytest 命令/門檻**（多少 ms 內須收到 ping）。  
    **證據**：Task 4.3 驗證「整合測試 assert to_thread 包裹後 analyze 期間 event loop 不被阻塞」。  
    **修法**：改為可測：`asyncio.wait_for` 在 analyze 背景跑時主 loop 仍能 `await asyncio.sleep(0)` 完成 N 次；或 mock 慢 analyze + assert heartbeat callback 被調度。

**4. 可疑 quant 假設**

11. **[MAJOR|High]** F-3「按 `features_df` 既有欄位順序取前 N」——**確定性足夠、語義不正**。欄位順序來自 HDF5/materialization，**非經濟意義排序**；`max_features=30` 會改 feature universe（命中 (d)），僅 metadata 不足以稱「未改語義」。  
    **證據**：Task 3.2「按 features_df 既有欄位順序取前 N」；§C「不改 IC 數值計算語義」vs feature 子集。  
    **會怎麼失敗**：兩次 materialization 欄位順序變 → 同一「前 30」不同特徵；研究結論不可比。  
    **修法**：截斷排序改 **穩定可移植規則**（建議：`sorted(remaining_columns)` 在 include/exclude 之後）；metadata 記 `truncation_order: sorted_column_name`；與 F-6 `preview_limit` 聯動，禁止暗示品質排序。

12. **[MINOR|Med]** T-2 量級啟發式 `>1e12` 視 ms——邊界可接受（秒級 crypto ~1.7e9；毫秒 ~1.7e12），但 **微秒/纳秒未列**；異常應靠 fail-closed 年份檢查兜底，SPEC 已部分覆蓋。  
    **修法**：Task 2.1 邊界加一條「1e15+ 非法 → raise」，避免靜默選錯單位。

**5. 過度工程**：無（Phase 0 範圍克制，§N 排除向量化/串流合理）。

**6. OOM/並行**：**[MINOR|Med]** F-5 大 run 僅 `logger.warning`，45k 特徵仍可能 OOM；Phase 0 可接受，但 **F-2 落地後預設 30 可緩解**——與 Findings #4 綁定。  
**修法**：F-5 閾值寫死（如 5000）並在 SPEC 註明「不阻擋，僅警示」。

**7. Cache 正確性**：無（本 Phase 不動 cache key）。

**8. API/型別/相容**

13. **[MAJOR|High]** 若 IC-BYVOL 選 (b) fail-closed 且 **不動 schema 預設 `by_volatility: True`**（`ic_config_schema.py:80`），預設 grouped 分析 **必 raise**，比現況「靜默忽略」更糟。  
    **證據**：GroupedConfig `by_volatility: bool = True`；Task 2.3(b)「schema 開但不支援 → raise」。  
    **會怎麼失敗**：修 B 後預設 config 無法跑 regime/grouped。  
    **修法**：(b) 必須同 Task 綁定 **`by_volatility` 預設改 `False`** + migration note；或 `compute_grouped_ic` 開頭對不支援欄位 **warn+skip 僅限 deprecated 欄位**（與 fail-closed 矛盾，故推薦改預設）。

**9. 測試品質**

14. **[BLOCKING|High]** 現有 `test_stage4_ic_calculation_with_kline_reader` 用 **SimpleNamespace + dict `grouped_analysis`**，**不會重現 C-1 pydantic AttributeError**；與 C-3 目標一致但 SPEC 須點名刪/換。  
    **證據**：`test_ic_filter_orchestrator.py:535-549` dict；orchestrator 真路徑傳 `GroupedConfig`。  
    **修法**：C-3 明列取代此測試或新增平行測試用真 `ICConfig`。

15. **[MAJOR|Med]** `test_time_index_parsing_and_alignment` 用 `open_time: [0,1000,2000]` + 現行 ms 假設——**不覆蓋秒級真實值**；T-3 新增後應標記舊測試意圖或更新。  
    **證據**：`test_ic_engine.py:260`。

**10. Agent 可執行性**

16. **[MINOR|Med]** Task 3.4 preview_limit「改名」**未指定新欄位名、alias 規則、TS 型別檔**（僅 handoffs 提及）。  
    **修法**：SPEC 寫死：`FeatureFilterConfig.preview_limit` + `max_features` deprecated alias；`frontend/src/lib/types.ts` 同步。

17. **[MINOR|Med]** §G baseline「動工前用 BTCUSDT 1h 跑 baseline」——**現況 grouped 在 C 修後仍可能 T 崩潰**，baseline 捕獲順序須寫死：C → 可選捕獲錯誤基準 → T → 正確基準。  
    **證據**：§G「baseline = 修 C 後、修 T 前的 by_year 鍵（1970）」——實際可能 crash 無鍵。  
    **修法**：§G 分階段 artifact：`baseline_grouped_post_crash_fix_pre_timeaxis.json`（若可達）+ `baseline_grouped_post_timeaxis.json`。

### §2 範本錨點 + 獵空殼

18. **[MAJOR|Med]** §G decay「**byte 級一致**」與同節 grouped「`abs≤1e-6`」**精度標準不一致**；float JSON 序列化跨平台可能假 FAIL。  
    **證據**：§G decay「byte 級一致」vs grouped「abs≤1e-6 或 rel≤1e-4」。  
    **會怎麼失敗**：D-1 只動 log 卻因 dump 順序/浮點字串 fail；或漏掉 r2 微漂移。  
    **修法**：decay golden 改 **結構化 float 比對**（同 grouped 容差）+ 鍵集合相等；禁止純 `json.dumps` byte compare。

19. **[MAJOR|High]** §G grouped「各組 IC 值集合 = 正確秒級分組重算」——**可證偽但 SPEC 未給參考實作位置**（測試內獨立 groupby 還是 golden json）。  
    **會怎麼失敗**：Agent 用錯對齊 index 的假參考仍綠燈。  
    **修法**：§G 指定：測試內用 `pd.to_datetime(timestamp, unit='s').year` 獨立分組後 `np.isclose` 比對 per-group IC mean。

20. **獵空殼**：Task 2.3 改法欄為「待收斂」→ **邏輯空殼**（機械 gate 可能過，實作不可執行）。見 Finding #5。

### §3 不可違反原則

21. **[MAJOR|High]** F-3 按欄位順序截斷 **違反「不假設截斷無語義影響」精神**（§C 只要求 metadata，未消除 universe 改變）。  
    **修法**：見 #11；不得建議「為過測試放寬 max_features 門檻」或刪除篩選 assert。

---

## IC-BYVOL 建議：**(b) fail-closed** + **schema 預設 `by_volatility=False`**

**理由（獨立判斷）**：

1. **Phase 0 定位**：止血 + 硬閘，不擴功能；波動度分組需定義 lookback、percentile、label 對齊、可能滾動波動率計算，命中 (d) 且無現成分支可抄（`by_regime` 的 high_vol/low_vol 是 regime 子邏輯，非 `by_volatility` 契約）。
2. **契約一致性**：schema 預設 `True` 卻靜默忽略是 **契約謊言**；fail-closed 誠實，但 **預設 True + fail-closed = 預設壞掉**，必須改預設或分組預設關閉 `by_volatility`。
3. **實作風險**：(a) 在 Phase 0 做等於新 epic，需獨立 golden；與 §N「不擴 grouped 向量化」精神一致應延後。
4. **驗收清晰**：(b) 單測 `by_volatility=True` → `ValueError` 訊息含契約不支援；(a) 需定義輸出 schema，SPEC 未給。

**派工前 SPEC 必補**：Task 2.3 刪除雙分支，寫死 (b) + `GroupedConfig.by_volatility` 預設 `False` + 錯誤訊息格式。

---

## 被當成事實的未驗證假設

| # | 假設 | 實際 |
|---|------|------|
| 1 | §A#2 真實路徑只產生錯誤 1970 分組 | **部分假**：還會 `_iter_time_groups` AttributeError（Series 無 `to_series`） |
| 2 | §A 六項皆「實跑驗證」 | #1/#3/#4/#5 多為 code/grep；#6 委員會推論 |
| 3 | §G 修 C 後可穩定拿到「1970 by_year 鍵」baseline | **假**：可能 crash 無 grouped 輸出 |
| 4 | 現有 orchestrator grouped 測試覆蓋 C-1 | **假**：SimpleNamespace+dict 繞過 pydantic |
| 5 | `feature_filter` override 已進 IC 管線 | **假**：`load_ic_config` 目前丟棄未知頂層鍵（已實跑） |
| 6 | F-3 欄位順序截斷不改「研究語義」 | **假**：改 universe，僅確定性 |
| 7 | decay golden byte 級可攔浮點重排 | **偏弱**：byte compare 對 log-only 變更過嚴/過鬆皆可能 |

---

## §1 類別無問題摘要

- **矛盾**：除 #4/#5 外無大型 Phase 順序衝突（Phase 3 平行合理）。
- **過度工程 / Cache**：無。
- **Resume/retry**：刻意不做，見 #7。

---

```
ASSUMPTIONS_VERIFIED: read_klines→RangeIndex+秒級timestamp；_get_time_index(ms)→1970 Series；_iter_time_groups→AttributeError；orchestrator:1139傳GroupedConfig；compute_grouped_ic僅dict API；feature_filter override被ICConfig丟棄；主analyze:209同步無to_thread；WS onclose無限重連
TESTS_RUN: 本地 python 實跑 read_klines+_get_time_index+_iter_time_groups；load_ic_config(feature_filter) 靜默丟棄
FAILURES_SEEN: none（審查任務）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 審查建議涉及 schema by_volatility 預設、FeatureFilterConfig 命名；未改程式
```

STATUS: DONE
