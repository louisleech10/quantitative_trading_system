# IC1C-TODOREV R2 — Grok 閉合重驗

- **Reviewer**: Grok (r1 原委員, family ≠ author)
- **Date**: 2026-07-14
- **Inputs**: r1 `handoffs/20260714-IC1C-TODOREV-grok.md`(3B+6MAJOR+3MINOR); TODO r2 `docs/IC1C_NETIC_TODO.md`; 裁決 `handoffs/20260714-IC1C-TODOREV-RECONCILE.md` T-F1~T-F16
- **Scope**: 僅本檔(+若 APPROVE 則 RECONCILE 戳記);未改 SPEC/TODO/code
- **Discipline**: 逐 finding 反例重判 CLOSED/STILL-OPEN;掃 r2 新洞;查 RECONCILE 曲解

## Verdict

**TODO-REVIEW-R2: REJECT(1 BLOCKING)**

r1 三項 BLOCKING 與六 MAJOR/三 MINOR **全數 CLOSED**(對應 T-F 落點可對上)。  
但 r2 新引入 **Task 0.1 skipped 注入寫死 `obv`/`ad`**,與真-kline fixture `FEATURE_NAMES` **零交集**→B0 冷啟動必炸或造假 feature,構成 **1 新 BLOCKING**。  
另見 2 新 MAJOR(T-F7 任務體與 §0 互斥;RECONCILE 漏裁 CODEX-1/`max(0.0,turnover)` 發明式公式)。  
**不 APPROVE、不蓋戳記。**

---

## r1 Findings 逐條重判

### ADV-GROK-1 [原 BLOCKING] → **CLOSED** (T-F1)

| 項 | 內容 |
|----|------|
| r2 落點 | 新 Task 1.4:ic_reporter :150/:209/:631-634/:773 + `test_export_formats.py`;B1 Gate 含 export;覆蓋表列 §C #4/#16 |
| 反例是否仍成立 | **否**。Agent 嚴格 scope 必改 reporter/export;red-on-break 寫明改回舊鍵→紅 |
| RECHECK | `rg ic_reporter docs/IC1C_NETIC_TODO.md`≥1;`rg export_formats`≥1;B1 pytest 字串含 `test_export_formats.py` |
| VERIFY | 現行 repo 仍殘 `"net_ic"`(預期,未開工);TODO 已列改法與驗收 grep |

### ADV-GROK-2 [原 BLOCKING] → **CLOSED** (T-F2)

| 項 | 內容 |
|----|------|
| r2 落點 | §B B1/B2 Gate 皆 `mutation_probe_check.sh <test_path...>` 具名檔 |
| 反例是否仍成立 | **否**。無參呼叫已不在 TODO 字面 |
| RECHECK | 命令含 `tests/momentum/Analysis/test_net_ic_analyzer.py` 等 |
| VERIFY | `bash scripts/mutation_probe_check.sh` 仍 usage exit(腳本未變);r2 已帶參,簽名可執行 |

### ADV-GROK-3 [原 BLOCKING] → **CLOSED** (T-F5)

| 項 | 內容 |
|----|------|
| r2 落點 | `--baseline new2`+路徑 `g_new2.{json,sha256}`;API TestClient 入參 vs G-NEW config 直開 10bps feature dict sha256;不等 exit 1 |
| 反例是否仍成立 | **否**(原「無路徑/無命令/無 failure oracle」)。殘留:未釘 deep-analysis **完整 URL/body/fixture 掛載**(見 NEW MINOR) |
| RECHECK | TODO 含 `g_new2`+`python scripts/ic1c_freeze_baseline.py --baseline new2` |

### ADV-GROK-4 [原 MAJOR] → **CLOSED** (T-F3)

| 項 | 內容 |
|----|------|
| r2 落點 | Task 1.2 驗證=T1b `test_run_net_ic_orchestrator_direct`(B1 內);e2e 歸 2.1/B2;B1 Gate 跑 T1 檔含 T1b |
| 反例是否仍成立 | **否**。B1 可證 orchestrator 兩參/unavailable,不再依賴未建 API 契約的 T2 |

### ADV-GROK-5 [原 MAJOR] → **CLOSED**(主因),殘差升級為 **NEW BLOCKING R2-1**

| 項 | 內容 |
|----|------|
| r2 落點 | Task 0.1 偽碼:fixture→summary+turnover→`batch_analyze`(禁 full deep);確定性/lineage/獨立 validator |
| 原反例 | 「fixture 直接當 orchestrator」—**已解** |
| 新反例 | 見 ADV-GROK-R2-1:寫死 feature 名不在 fixture |

### ADV-GROK-6 [原 MAJOR] → **CLOSED** (T-F9)

| 項 | 內容 |
|----|------|
| r2 落點 | §0 JSON strict+batch 邊界非有限 capacity→null;T1 `test_finite_invariants` 含 capacity 子樹;函式本體不動 |
| 反例是否仍成立 | **否**。G-NEW dump 路徑有明確 null 規則,非 agent 私自分叉 |

### ADV-GROK-7 [原 MAJOR] → **CLOSED** (T-F11)

| 項 | 內容 |
|----|------|
| r2 落點 | Task 1.3 明列 `:60-66`+`test_net_ic_proxy_nan_turnover(:92-96)`;完成=`grep net_ic_proxy`==0 |
| VERIFY | repo 仍兩測(預期未開工):`test_net_ic_proxy`/:92-96 |

### ADV-GROK-8 [原 MAJOR] → **CLOSED** (T-F12)

| 項 | 內容 |
|----|------|
| r2 落點 | §0+Task 2.1 雙入口 422;merge typed 最後;G-NEW2 節 T2 矩陣「雙 override」 |
| 殘差 | 具名測試字串仍單一名 `test_config_override_net_ic_rejected`(未強制兩 path 分測)—**MINOR**,不升級 |

### ADV-GROK-9 [原 MAJOR] → **CLOSED** (T-F13)

| 項 | 內容 |
|----|------|
| r2 落點 | §0 R1–R7 一行 checklist+本票適用 |

### ADV-GROK-10 [原 MINOR] → **CLOSED** (T-F6)

| 項 | 內容 |
|----|------|
| r2 落點 | 專檔 `tests/momentum/Analysis/test_net_ic_schema_profiles.py::SCHEMA_*`,禁複製 |

### ADV-GROK-11 [原 MINOR] → **CLOSED** (T-F15)

| 項 | 內容 |
|----|------|
| r2 落點 | Task 2.1 fenced JSON+註 request `net_ic` vs 模組鍵 `net_ic_analysis` |

### ADV-GROK-12 [原 MINOR] → **CLOSED** (T-F8)

| 項 | 內容 |
|----|------|
| r2 落點 | grep 改 `useState\(5\)|turnover \?\? 0\.1|\|\| ?0\.1`;註 step/min 0.1 合法;RTL 行為守衛 |

---

## 覆蓋表機械勾稽(r2)

| SPEC 錨點 | r2 TODO | 判定 |
|-----------|---------|------|
| Task 0.1–3.1(7) | 同名+**1.4** | 7/7+consumer Task |
| M1–M10 | Phase1/2+§B(M10 分層 B1/B2) | 10/10 名目成立 |
| G-OLD/NEW/NEW2 | 三模式腳本+validator(G-OLD)+compare(G-NEW2) | 3/3 程序有字面 |
| §U SCHEMA | 專檔+§0 | 對齊 Frozen |
| §C #4/#16 | Task 1.4 | 已補 |
| 覆蓋行「獨立 validator」G-NEW2 | G-NEW2 實為 vs G-NEW 等值,非獨立內容 validator | **措辭過滿**(MINOR 過聲稱,非空殼) |

---

## r2 新洞

### ADV-GROK-R2-1 [BLOCKING] 信心度 High — Task 0.1 寫死 feature 名不存在於真-kline fixture

- **證據 (TODO Task 0.1 ④)**:`turnover_data.pop("obv")`+`summary["ad"]["ic_mean"]=float("nan")`,「兩 feature 名寫死」。
- **證據 (repo, VERIFY 2026-07-14)**:
  ```text
  FEATURE_NAMES = ['log_return_1','log_return_3','rvol_20','zscore_20',
                   'hl_range','oc_return','close_sma_ratio_20']
  'obv' in FEATURE_NAMES → False
  'ad'  in FEATURE_NAMES → False
  ```
- **反例 / 會怎麼失敗**:
  1. 依偽碼從 fixture 建 summary/turnover 後 `pop("obv")`→**KeyError**,B0 Gate 紅;或
  2. Agent 為過 validator「必含兩 skipped」**硬插** obv/ad 合成列→違 §0「禁新合成 fixture / 真-kline」;或
  3. 靜默略過寫死名改用真名但未改 TODO→審核/重跑不可復現。
- **與 ADV-GROK-5 關係**:原「orchestrator 空殼」已修;本項是 r2 修補引入的**可證偽假名**。
- **修法**:改寫死為 fixture 實名(例 `hl_range` turnover_missing + `rvol_20` gross_ic NaN),或 `FEATURE_NAMES[i]` 索引+validator 對同一 pair;禁虛構 indicator 名。
- **RECHECK**:`python -c "from tests.fixtures.ic_api_real_kline import FEATURE_NAMES; ..."` 與 TODO 寫死名集合⊆FEATURE_NAMES。

### ADV-GROK-R2-2 [MAJOR] 信心度 High — T-F7「落地聲明」與 Task 1.1/2.1 實作句互斥

- **證據 (§0)**:「域驗證與 enabled 無關——`cost_bps` 非 None 一律驗域」;T-F7 例 `{cost_enabled:False, cost_bps:NaN}` 三層拒絕。
- **證據 (Task 1.1 ④)**:`cost_enabled and (cost_bps is None or not isfinite or not 0<…)` 才 raise——**disabled 時不驗**。
- **證據 (Task 2.1 ①)**:`@model_validator`: **enabled 且** (None/非有限/域)→raise——同殘。
- **證據 (Phase2 G-NEW2 段)**:T2 矩陣要求 `{cost_enabled:false, cost_bps:NaN}`→422。
- **反例**:執行端照 1.1/2.1 ① 實作→T2 矩陣失敗;或刪/弱化該用例假綠→M10「三層」名存實亡;analyzer 直呼 `NetICAnalyzer({cost_enabled:False,cost_bps:nan})` 放行。
- **修法**:1.1/2.1 改寫為「`cost_bps is not None`→一律域檢;enabled→另要求非 None」與 §0/T-F7 同構;T1/T5 具名含 disabled+NaN。
- **RECHECK**:三處(§0/1.1/2.1)無 `enabled and` 域檢短路。

### ADV-GROK-R2-3 [MAJOR] 信心度 High — `max(0.0,turnover)` / 負 turnover clamp 仍屬 SPEC 外發明;且 RECONCILE 漏列 CODEX-1

- **證據 (Frozen SPEC §T)**:`cost_drag_return = (cost_bps/10000) × turnover`——**無 max/clamp 負值**。非有限 turnover→SKIPPED(§U)。
- **證據 (TODO 1.1/1.3)**:`compute_cost_drag=…*max(0.0,turnover)`;邊界「負 turnover clamp」。
- **證據 (RECONCILE)**:T-F1~T-F16 **無** CODEX-1(負 turnover/`max`)主題,卻標「全 ACCEPT」。
- **反例**:上游污染 turnover=-0.2→成本拖累被靜默改 0,像合法;與「不得發明量化假設」鐵律衝突;委員裁決帳不完整。
- **修法**:RECONCILE 補裁(SKIPPED reason=`non_positive_turnover` **或** raise **或** SPEC 正式修訂後允許 clamp);TODO 刪 `max` 直到有 stamp 的 SPEC 依據。
- **RECHECK**:`rg 'max\\(0\\.0,turnover\\)' docs/IC1C_NETIC_TODO.md` 在有 SPEC 依據前應為 0。

### ADV-GROK-R2-4 [MINOR] 信心度 Medium — G-NEW2 API 路徑仍缺 copy-paste 級入口細節

- 有 `--baseline new2` 與 10bps 等值規則;缺 route path、完整 multipart/JSON body(symbol/TF/modules)、features dict 於 response 的 JSON pointer。
- 失敗模式:agent 自造 endpoint→G-NEW2 測錯層。建議附 5–10 行 TestClient 偽碼(可對 2.1 JSON 擴充)。

### ADV-GROK-R2-5 [MINOR] 信心度 Low — 覆蓋追溯「G-NEW2…獨立 validator」措辭過滿

- G-OLD 有 `ic1c_validate_baseline.py`;G-NEW2 是 vs G-NEW 等值(合理),非獨立內容 validator。改措辭即可。

---

## RECONCILE 曲解檢查

| 主題 | 判定 | 說明 |
|------|------|------|
| T-F1~T-F4,T-F6,T-F8~T-F16 對我方 finding | **無曲解** | 落點與原修法方向一致,未降級 BLOCKING 意圖 |
| T-F5 bps 數值 | **輕微漂移** | RECONCILE 寫「API 7bps vs config 7bps」;r2 TODO G-NEW/G-NEW2 用 **10bps**(前端 wiring 另用 7)。精神(傳導等值)保留,數字不一致——r2 以 TODO 為準即可,建議 RECONCILE 勘誤 10 |
| T-F5 G-NEW2 | **未削弱** | 可執行命令+exit oracle 已落;細節見 R2-4 |
| T-F7 | **半落地/內部打架** | §0+測試矩陣 ACCEPT 到位;Task 1.1/2.1 ① 仍舊 enabled 短路→**執行句未跟上裁決**(R2-2) |
| T-F10 | **意圖保留+引入新錯** | 偽碼/validator 好;feature 名寫死錯誤(R2-1) |
| **CODEX-1(max/負 turnover)** | **曲解=漏裁** | 原 BLOCKING 未入 T-F 表,TODO 仍保留發明式 `max`→帳面「16 主題全 ACCEPT」不完整(R2-3) |
| 無靜默 REJECT/降我方 3B | **OK** | 我方 3B 皆有對應 T-F 且 r2 已閉 |

---

## 建議 r3 最小補丁(不重寫全文)

1. **必做(BLOCKING)**:Task 0.1 ④ feature 名⊆`FEATURE_NAMES`;validator 同步。  
2. **必做(MAJOR)**:Task 1.1 ④ / Task 2.1 ① 域檢與 §0 T-F7 同構(非 None 一律驗)。  
3. **必做(MAJOR/帳本)**:RECONCILE 補 CODEX-1 裁決行+TODO 刪或合法化 `max(0.0,turnover)`。  
4. 可選:G-NEW2 TestClient 偽碼;覆蓋表 G-NEW2 validator 措辭;RECONCILE 7→10bps 勘誤;override 雙 path 分測名。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - r1 ADV-GROK-1..12: 3B+6MAJOR+3MINOR 在 r2 字面均可 CLOSED(對 T-F1..15 等)
  - FEATURE_NAMES 無 obv/ad (python import fixture, 2026-07-14)
  - mutation_probe_check.sh 仍要求 >=1 test_path; r2 Gate 已帶參
  - RECONCILE 無 CODEX-1/max 主題列
  - Task 1.1/2.1 仍 "enabled and" 域檢; §0 要求非 None 一律驗
TESTS_RUN:
  - python: from tests.fixtures.ic_api_real_kline import FEATURE_NAMES → 7 names, no obv/ad
  - bash scripts/mutation_probe_check.sh → usage exit (unchanged script)
  - rg/read: TODO r2, RECONCILE, ic_reporter :773, turnover proxy tests, _to_json_compatible NaN→None
FAILURES_SEEN: none (review-only)
SCOPE_CHANGES: none — output only handoffs/20260714-IC1C-TODOREV-R2-grok.md
NUMERIC_OR_SCHEMA_IMPACT: none
RECONCILE_DISTORTIONS:
  - T-F5 bps 7 vs TODO 10 (minor)
  - CODEX-1 omitted from T-F table while max() remains in TODO (major ledger gap)
  - T-F7 §0 accepted but Task 1.1/2.1 body still enabled-gated (partial land)
STAMP: NOT APPENDED (REJECT)
```

STATUS: DONE

TODO-REVIEW-R2: REJECT(1 BLOCKING)
