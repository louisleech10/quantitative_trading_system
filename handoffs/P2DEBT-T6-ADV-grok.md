# P2DEBT-T6 ADV — Grok（雙家族 adversarial）

> task-id: `p2debt-t6` | reviewer: Grok（獨立，非起草者） | date: 2026-07-12  
> inputs: `handoffs/P2DEBT-T6-{SPEC,TODO}-DRAFT-R1.md` + `P2DEBT-T6-CHAIR-ROOTCAUSE.md`  
> scope: 只審草稿；**禁改碼**（本檔為唯一產出）

## VERDICT: **APPROVE**

A1–A3 改 fixture `["label"]` → `["return_5"]`、禁動生產 resolver — **可合規閉合 API 既有紅**。  
下列為必讀殘差與 B1 裁示（**非**擋 rename 本體）。

---

## 可證偽反例（至少 1）

### CE-1（殘差，不擋 APPROVE）— `return_1` 仍會「綠且結構斷言過」但 horizon 語意錯

**命題（可推翻）**：API 三檔在 rename 後若誤用 `return_1`（或任意合法 `return_N`，N≠5），pytest 仍可全綠，因斷言無 horizon/purge oracle。

**證據**：

1. Label 值 = `rng.normal` 合成噪音（三檔 fixture 同型），無「5-bar return」真值。
2. 斷言僅 HTTP/結構：`status_code==200`、`summary_table` / export content-type 等；**三檔無任何 assert 含 label 欄名或 effective_horizon**。
3. 欄名解析為權威：`_resolve_label_horizon_from_column("return_N")→N`；`_resolve_effective_label_horizon` 在單欄 `return_1` 時 **回 1，不強制 default=5**（本輪 Python 實測）。
4. stage0 把欄名解析出的 horizon 餵給 `_alignment_spec(..., lag=horizon)`（`ic_filter_orchestrator.py:2042–2059`）；錯 N → lag 錯，**測試不查 gap/lag**。
5. `test_ic_analysis_api` 另設 `ic_train_test_split: False` → 更難從 split purge 暴露錯 N。

**對策（草稿已大致對）**：A1–A3 **必須** `return_5`（對齊 `default_horizon`，見下），不得「任意合法 N」。  
**收斂語意**：本票驗收 = **契約命名對齊 + 紅轉綠**；**≠** 證明 purge/horizon 數值正確。後者需另開有 oracle 的測（非本票 scope）。

---

## 獵點 (1) 有效 horizon 真的是 5 嗎？

| 來源 | 實測 |
|------|------|
| `config/ic_config.yaml` | `global.default_horizon: 5`；`labels.horizons: [1,2,3,5,8,13,21]` |
| `load_ic_config()` | `default_horizon == 5` |
| A1 `test_ic_deep_analysis` | `config_override` 僅 thresholds/redundancy；**無** `default_horizon` / `labels.horizons`；`full-analysis` 路徑甚至常無 override |
| A2 `test_ic_analysis_api` | override：`ic_train_test_split: False` + thresholds/redundancy；**無 horizon** |
| A3 `test_export_api` | 同 A1 型 thresholds/redundancy；**無 horizon** |
| `ICAnalyzeRequest` | **無** request 級 `horizon` 欄（`horizon: int = 5` 在 `ICTopFeaturesRequest`，與 analyze fixture 無關） |

**結論**：A1–A3 有效配置 horizon = **5**；目標欄名 **`return_5` 正確**。  
（註：一旦寫入 `return_N`，stage0 以**欄名 N** 為準；故仍須釘 5，不能只靠 yaml default。）

---

## 獵點 (2) `return_5` 是「綠且斷言正確」還是「只是綠」？

| 維度 | 判定 |
|------|------|
| 修根因訊息 | **是** — 裸 `label` → `InvalidInputError: label horizon cannot be resolved from column: label`（pytest 已重現） |
| 對齊生產落盤契約 | **是** — stage2 寫 `return_{horizon}`；resolver 只認 `return_(\d+)` |
| 斷言驗證 horizon 語意 | **否** — 見 CE-1 |
| 錯 N 靜默 alignment/purge | **可能** — lag=N 來自欄名；結構測不抓 |

**一句話**：`return_5` = 契約對齊 + 可預期轉綠；**不是** horizon 正確性的充分證明。

---

## 獵點 (3) B1（`test_ic_analysis_service.py:123`）

| 命題 | 判定 |
|------|------|
| 現況紅？ | **否** — 本輪 `test_run_analysis_does_not_block_event_loop` **PASSED** |
| stub 是否走 orchestrator？ | **否** — `_SleepingAnalyzer.analyze/_cross_sectional` 僅 `sleep(0.2)` + 空 `summary_table`；`_run_analysis` 把 stub 當 analyzer 呼叫 |
| frame 欄 `"label"` 是否進 resolver？ | **現路徑不** — xsec 分支有 `labels_path="labels.h5"` → **不**呼叫 `_append_cross_sectional_labels`；stub 亦不讀 frame/label |
| 若將來真 analyzer + in-frame | 優先序 `label > return_N > ...`；`_resolve_cross_sectional_label_horizon("label")→None` → `structural_horizon=1`（**不 raise**，與 longitudinal stage0 fail-closed **不同**） |
| 建議 `return_1`？ | 僅對「無 labels_path、in-frame、且真 analyzer」的**預防性**命名有意義；對 **B1 現測不必要** |
| append 三測 #24–26 | 已用 `return_1`；本輪 **3 passed**；**非**裸 `label` 根因 |

**裁示**：B1 **移出本票必改**；TODO Task 2.4 預設 **skip 改碼**（僅 receipt）。勿把 B1 算進「同根因 26 紅」。

---

## 獵點 (4) 有無「生產應接受裸 label」真契約？

- 失敗鏈均為 fixture 裸 `label` → stage0 fail-closed；**無** assert / docstring 要求 accept bare `label`。
- 生產：`re.fullmatch(r"return_(\d+)", name)`；落盤 `return_{horizon}`。
- append/xsec oracle 測斷言的是 **`return_1` 值**，不是 bare label 相容。

**反證「純殘留」失敗** → 主委假設成立：**測試殘留命名**，非 API 應接受 `label` 的契約測。

---

## 庫存校正（NON-BLOCKING）

| 項目 | 主委/草稿 | 本輪 |
|------|-----------|------|
| V6 baseline API | 23 nodeid | 檔內 23 行 nodeid（+1 註解）一致 |
| service 3 | 曾列紅 | **已綠**（return_1 已齊） |
| B1 L123 | 點名 | **綠**、stub、非 26 必改 |

驗收表述建議改為：**API 23 轉綠 + service 檔不新紅**；「26 全綠」在 service 已綠時仍成立，但 **rename 作用面 = A1–A3 三點**。

---

## FACT-RECEIPT（獨立實跑）

```text
命令:
  source venv/bin/activate && pytest \
    tests/api/test_ic_deep_analysis.py::test_full_analysis_endpoint \
    tests/api/test_ic_analysis_api.py::test_ic_task_status \
    tests/api/test_export_api.py::test_export_csv_summary_200 \
    tests/api/test_ic_analysis_service.py::test_run_analysis_does_not_block_event_loop \
    tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_real_3sym_oracle \
    tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_kline_hole_becomes_nan_not_raise \
    tests/api/test_ic_analysis_service.py::test_append_cross_sectional_labels_mutation_rangeindex_regresses \
    -v --tb=line

摘要:
  FAILED  test_full_analysis_endpoint — label horizon cannot be resolved from column: label
  ERROR   test_ic_task_status (setup) — 同上
  ERROR   test_export_csv_summary_200 (setup) — 同上
  PASSED  test_run_analysis_does_not_block_event_loop (B1)
  PASSED  append 三測 (return_1)
  → 1 failed, 4 passed, 2 errors

Python 抽樣:
  default_horizon=5; resolve(label)→InvalidInputError;
  resolve(return_5)→5; effective(return_1)→1 (欄名優先於 default)
  三 API 測檔無 horizon 字樣於 config_override
```

---

## 對草稿的凍結建議（reconcile 用）

1. **APPROVE 實作面**：A1/A2/A3 → `["return_5"]` only；`momentum/**` `api/**` 零 diff；resolver 正則不變。  
2. **B1 / Task 2.4**：預設 **不動**；不得寫進「26 紅同修」敘事。  
3. **CE-1 殘差**：收尾報告不得宣稱「已驗證 purge/horizon 數值正確」；僅可稱 fixture 命名對齊 + nodeid 轉綠。  
4. **票 2 baseline**：閉合後由 Claude 縮 V6 23 列表（impl 預設只提案）— 與草稿一致。

---

## STAMP

| 欄位 | 值 |
|------|-----|
| Grok adversarial | **APPROVE** |
| 反例 | CE-1（錯 N 仍結構綠；要求釘 `return_5`） |
| BLOCK 項 | **none** |

```
ASSUMPTIONS_VERIFIED: default_horizon=5; A1-A3 無 horizon override; bare label 非契約 assert; B1 stub 不走 orchestrator 且 PASS; append×3 PASS return_1
TESTS_RUN: 見 FACT-RECEIPT（7 nodeid 單命令）
FAILURES_SEEN: 預期 — 3 API fixture 裸 label
SCOPE_CHANGES: 建議 B1 正式 out-of-scope（非擴大實作）
NUMERIC_OR_SCHEMA_IMPACT: none（審稿 only）
產出: handoffs/P2DEBT-T6-ADV-grok.md
```

STATUS: DONE
