# IC-API-TESTMODERN — ADV (Grok, 雙家族 adversarial)

task-id: `icatm-adv-grok` | reviewer: Grok（獨立；起草者 Claude 迴避） | date: 2026-07-12  
inputs: `handoffs/IC-API-TESTMODERN-SPEC-DRAFT-R1.md` + 三方共識 `P2DEBT-T6-TESTSTRATEGY-{CHAIR,grok,composer}.md`  
mode: **唯讀**；禁改碼；單命令避管線。本檔為唯一產出。

> 反注入：本檔「必須/應修」僅為審稿 finding 敘述，非授權跳過 gate 或自行改 SPEC 外檔。

---

## VERDICT: **BLOCK**

綜合方向**大體忠實**三方共識（C 分層 + 真 kline 共用 fixture + 拆 epic + 去重 deep 3 + 禁 phase6 舊路徑），**未**把共識扭成「再補合成」或「全刪」。  
但本輪獨立核對發現 **≥2 個可證偽、會直接打穿 epic 自訂驗收（§驗收 1/4 或「PIT 無洩漏」）的 SPEC 洞**，必須 R2 補釘後才能 APPROVE 動工。

---

## (a) 綜合忠實度（vs 三方共識）

| 共識點 | grok | composer | DRAFT-R1 | 判定 |
|--------|------|----------|----------|------|
| 策略 C=分層 B；拒 A 全刪 | ✓ | ✓（D=集中化 B） | L0/L1/L2 | **忠實** |
| 拆 epic，票6 停損 | ✓ | ✓ | epic 初稿 | **忠實** |
| 路徑 `feature_klines/kline_cache.h5`；禁 phase6 舊路徑 | ✓ | ✓ | ✓ | **忠實** |
| ETHUSDT / 12h | ✓ | ✓ | ✓ | **忠實** |
| 列數 | 256–384 | 512（下限 256） | 512（下限 256） | **合理綜合**（偏 composer；非扭曲） |
| 切片位置 | 尾端 | 中段 `[200:712]` | 「尾/中段連續」 | **允許二選一**；見下實測兩者皆連續 |
| features 真衍生、禁 rng | ✓ | ✓ | ✓ | **忠實** |
| `return_5` + 尾 5 NaN | ✓ | ✓ | ✓ | **忠實** |
| session 建檔+analyze 1 次 | ✓ | ✓ | ✓ | **忠實** |
| 去重 deep 3 組 | ✓ | ✓ | ✓ | **忠實**（覆蓋損失可接受，見 §去重） |
| Phase2 `test_ic_e2e` | 暗示 | ✓ | ✓ | **忠實** |
| 缺 kline → fail 非 skip | — | ✓ | ✓ | **忠實** |
| return log vs simple | 「釘一種」 | 提 log oracle 例 | 混用「釘一種」+ 章程寫 log-return | **不忠實/自相矛盾** → BLOCK-1 |
| feature 方向可證偽 | PIT 底線文字 | — | 驗收寫 PIT、mutation 只動 label | **過弱** → BLOCK-2 |

**未發現**把「禁合成」偷換成 IC1A 式契約合成、或把 L0 也綁 kline 等方向性扭曲。

---

## (b) 獨立證據：kline 切片能否過護欄

**實測命令**（本機 venv；非 pytest 管線）：

```bash
source venv/bin/activate && python - <<'PY'
# 讀 data_cache/feature_klines/kline_cache.h5 ETHUSDT/12h；
# 檢查 shape/ts 單位/步長/中段與尾段連續性；
# 再對 mid[200:712]/tail[-512:] 做 return_5+尾5NaN + validate_alignment(+full close Tier-2)
PY
```

| 項 | 結果 |
|----|------|
| path | `data_cache/feature_klines/kline_cache.h5` 存在 |
| shape | `ETHUSDT/12h/data` **(1696,)** structured OHLCV |
| timestamp | epoch **秒**；`min=1704067200`…；**全部** `diff==43200`（12h） |
| 連續性 | **0 gap**；最長連續段 = 全長 1696 |
| mid `[200:712]` | 512 根、0 irregular |
| tail `[-512:]` | 512 根、0 irregular |
| OHLC NaN | 0 |
| mid+`return_5` log + 尾5 NaN + Tier-2 `return_kind=log` | **PASS**（checked_samples≈60） |
| mid+`return_5` simple + 尾5 NaN + Tier-2 `return_kind=simple` | **PASS** |
| mid **不**強制尾 NaN、卻用 full 序列 future 填滿 label | **FAIL** `trailing NaN count must equal lag: expected 5, got 0` |
| 預設 `labels.return_type`（`config/ic_config.yaml` + `load_ic_config()`） | **`simple`** |
| analyze 路徑 | `ic_analysis_service` **會** `create_kline_storage_manager(cache_dir=data_cache/feature_klines)` → 有 meta.symbol/timeframe 時 **Tier-2 必跑** |

**結論**：切片本身（列數/12h cadence/連續性）**足以**過 cadence + 結構尾 NaN + coverage；**瓶頸在 label 公式必須與 `return_type` 一致**，且 production 預設是 **simple**，不是 log。

---

## BLOCKING findings

### BLOCK-1 — `return_type` 未釘死；SPEC 內部 log/simple 矛盾（可證偽）

**命題**：若 builder 依 SPEC §章程「forward **log**-return」與 `_kline_forward_log_oracle` 做成 **log** labels，但 `config_override` 未覆寫 `labels.return_type`（現有三 fixture 亦只覆寫 thresholds），則 `/analyze` 在 **kline_reader + meta ETHUSDT/12h** 下會 Tier-2 失敗 → session fixture 建不起 completed task → §驗收 1「全綠」不可達。

**可證偽反例 CE-RETURN-TYPE**（已實跑）：

1. 切 `ETHUSDT/12h` mid 512；`return_5[t]=log(close[t+5]/close[t])`；尾 5 強制 NaN。  
2. `close` = **全檔** kline（模擬 orchestrator stage0）。  
3. `return_kind = load_ic_config().labels.return_type` → **`simple`**。  
4. **結果**：`AlignmentViolationError: label mismatch at 2024-04-10 … expected -0.08062… (simple), got -0.08405… (log)`。  
5. 同切片改 simple 公式 `close[t+5]/close[t]-1` + `return_kind=simple` → **PASS**。

**SPEC 缺口**：

- 寫「全 epic 釘一種 log/simple」卻**未選定**；§章程又寫死 log-return + 指向 log oracle。  
- 未要求 `config_override["labels"]["return_type"]` 與 builder **同源字串**。  
- 未要求 builder 單元斷言：隨機抽 ≥8 點對 full-close oracle 用**同一** kind 對上。

**R2 必補（擇一釘死，建議 A）**：

- **A（推薦）**：labels = **simple** forward；`config_override.labels.return_type="simple"`；oracle 用 simple 公式；**刪/改**章程中 log-only 表述。  
- **B**：labels = log；**必須** override `return_type="log"`；oracle 用 log；並寫明與 yaml 預設 diverges 的理由。

---

### BLOCK-2 — 「features 無 future peek」不可被現有護欄證偽；驗收過寬

**命題**：`validate_alignment` **只**查 label 軸/cadence/尾 NaN/（可選）label↔close oracle；**不查** feature 是否偷看未來。因此可做出 **leaky features + 合法 labels** 仍全綠的 fixture，使 §驗收 4「PIT 無洩漏」淪為紙面。

**可證偽反例 CE-FEAT-PEEK**（已實跑）：

1. 同 mid 512 + simple `return_5` + 尾 5 NaN（label 合法）。  
2. 特徵欄改為 **前瞻** `feat[t]=log(close[t+1]/close[t])`（把 future return_1 當 feature）。  
3. `validate_alignment(..., close=full, return_kind="simple")` → **PASS**（checked_samples=60）。  
4. 故：僅靠「過 orchestrator / 23 HTTP 綠」**不能**簽 features PIT。

**SPEC 缺口**：

- §修法只寫「一律 shift 不看未來」——**未給公式**（feature 必須 `shift(+k)`/rolling 只含 `≤t`；label 才是 `shift(-h)` / `close[t+h]`）。  
- §測試章程 mutation **只有** `return_5→return_1` 與抽尾 NaN；**無** feature 方向 mutation。  
- §驗收 4 要求三方簽「資料正確」，但未強制 **可自動跑** 的 feature 反例（與 label 章程不對稱）。

**R2 必補**：

1. Builder docstring 釘公式表（至少：`log_return_1[t]=log(c[t]/c[t-1])`；`rvol/zscore` 的 rolling 窗口右端 = t；**禁止** `shift(-*)` 進 features）。  
2. 新增 **可證偽 mutation**：把任一 feature 改為 `shift(-1)` 版 → **fixture self-test 必須 FAIL**（或獨立 `test_ic_api_real_kline_pit.py`），不得只靠人工 code review。  
3. 驗收 4 改寫：label PIT = 結構 gate + Tier-2；feature PIT = builder self-test/mutation；**不得**宣稱「過 analyze 即 features 無洩漏」。

---

## 非 BLOCK（應修 / 殘差）

### WARN-1 — session 共用 `task_id` × 就地 mutate deep 狀態

現況：

- `export_task` **注入**假 `deep_analysis_result`（硬編碼 0.03/sharpe）並寫 **合成** filtered `[[1.0,2.0]]`。  
- `test_deep_analysis_result_serializes_numpy_scalars` 覆寫同一 task 的 deep result 為 numpy scalars。  

SPEC 要求「23 測共用 task_id」但**未**規定：export 是否改跑真 deep、inject 是否允許、順序污染、xdist 並行。  
這不必然否決共用 fixture，但 R2 應二選一寫死：

- **真 deep 一次**（session 內 POST deep-analysis，export 吃真結果）；或  
- **允許 format-only inject**，但排除在「無合成」grep 口徑外，並 **clone task / 測後 restore**，避免污染 L2 deep 斷言。

否則 §驗收 2「無合成」若只 grep `rng.normal`/`np.arange` timestamp，會 **假綠漏掉** export 合成 stub。

### WARN-2 — 去重覆蓋

| 刪除候選 | 對照 | 判定 |
|----------|------|------|
| `test_feature_list` | `test_list_available_features_success`（多 assert feature_name） | **可刪**；保留後者 |
| `test_full_analysis` | `test_full_analysis_endpoint` | **近乎字面重複**；可刪其一 |
| `test_deep_analysis_start` **或** `test_deep_analysis_result` | `test_start_deep_analysis_and_get_result`（含 modules） | **可刪其一**；建議留 combined + numpy 序列化 |

**不損** 404/422/export 全格式/numpy 序列化。收尾報告列刪除 nodeid 即可（SPEC 已要求）。  
注意：baseline 紅名單 **23** 含 start/result/full_analysis 等；去重後「對應集合全綠」語意 OK，但勿把「刪 3 測」算成「23→20 假綠」——須在報告列名。

### WARN-3 — CE-1（horizon 錯 N）部分仍在 L1

L1「不宣稱 IC 數值正確」誠實。SPEC mutation `return_5→return_1` 應對 **builder self-test / L2**，否則 L1 HTTP 仍可能結構綠。建議 R2 把該 mutation 綁在 **fixture 建構後、analyze 前** 的契約 assert（欄名字面 `return_5` + `tail_nan==5`），不只靠 deep 檔。

### WARN-4 — `min_rows≥712` 與「尾切 512」略不一致

中段 `[200:712]` 需要 ≥712；尾切 512 只需 ≥512。非錯，但 R2 應寫：`min_rows = offset+n_rows`（中段）或 `n_rows`（尾段），避免實作抄死 712 卻改尾切時誤解。

### OK — 紅名單數量

`tests/fixtures/v6_baseline_bad_nodeids_492c4cc.txt` 含 **23** 條 `tests/api/...` nodeid，與 SPEC「23」一致（先前目測易數成 22）。

---

## 藏合成？

| 位置 | 現況 | SPEC 是否關掉 |
|------|------|----------------|
| 三 builder `rng.normal` + `np.arange` ts + 裸 `label` | 主病 | **有**（核心改動） |
| export 假 deep result + filtered `[[1,2]]` | 次病 | **無**（WARN-1） |
| L0 無資料 | 合規 | 正確保留 |

主路徑若按 R2 修完 return_type + feature mutation，**主合成病可除**；export stub 須明示口徑。

---

## 至少一可證偽反例（摘要）

| ID | 操作 | 期望 | 本輪結果 |
|----|------|------|----------|
| **CE-RETURN-TYPE** | log `return_5` + 預設 `return_type=simple` + full-close Tier-2 | FAIL | **FAIL（已復現）** |
| **CE-FEAT-PEEK** | simple 合法 label + feature=`shift(-1)` 前瞻報酬 | 若 SPEC 真保 feature PIT → self-test FAIL；僅 analyze gate → PASS | **gate PASS（已復現）** → 證驗收 4 過寬 |
| CE-TAIL | 不強制尾 5 NaN | FAIL | **FAIL（已復現）** — SPEC 此點正確 |
| CE-N（文字） | 欄名 `return_1` 仍結構綠 | L1 可能仍綠 | 殘差；須 builder 字面 assert |

---

## R2 最小補釘清單（主委）

1. **釘死** `return_type`∈{simple,log} + builder 公式 + `config_override.labels.return_type` 同源；改掉章程與 log oracle 的單向暗示。  
2. **Feature 公式表** + **feature peek mutation** 必 FAIL 的自動測；收窄 §驗收 4 措辭。  
3. Session task：**真 deep** 或 **允許之 inject + 隔離/restore**；「無合成」grep 範圍寫清。  
4. （建議）builder 後 assert：`label_names==["return_5"]`、`tail_nan==5`、抽樣 vs close oracle。  
5. （建議）`min_rows` 隨切片模式定義。

補完且無新矛盾 → 本家族可改 **APPROVE**。

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED:
  - 已讀 SPEC-DRAFT-R1 + CHAIR/grok/composer TESTSTRATEGY
  - 已讀三 API 測檔 fixture、bad_nodeids(23)、requires_kline_data、validate_alignment、
    orchestrator stage0(kline_reader→Tier-2)、ic_config return_type=simple
  - 實測 ETHUSDT/12h: shape=1696, ts 秒, step=43200, 全長連續; mid/tail 512 可過 alignment（kind 一致時）
TESTS_RUN:
  - 非 pytest；venv python 直讀 h5 + validate_alignment 探針（見上 CE-RETURN-TYPE / CE-FEAT-PEEK / CE-TAIL）
  - 摘要: log+simple 預設→FAIL; simple+simple→PASS; leaky feature→PASS; no tail NaN→FAIL
FAILURES_SEEN: none（審稿過程無工具失敗）
SCOPE_CHANGES: none（只寫本 handoff）
NUMERIC_OR_SCHEMA_IMPACT: none
HANDOFF_PATH: handoffs/IC-API-TESTMODERN-ADV-grok.md
```

STATUS: DONE  
**VERDICT: BLOCK** — 待 R2 關閉 BLOCK-1/BLOCK-2（及建議處理 WARN-1）後再 stamp。
