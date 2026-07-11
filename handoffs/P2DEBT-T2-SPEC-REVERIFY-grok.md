# P2 債票 2 SPEC R2 複驗 — grok（xAI）

Task-id: `p2debt-t2` | Date: 2026-07-11 | Role: §B8 原審查者 re-verify  
待審: `handoffs/P2DEBT-T2-SPEC-DRAFT-R2.md`  
對照: `handoffs/P2DEBT-T2-SPEC-REVIEW-R1-grok.md`（本輪**不**讀 codex re-verify）  
方法: 重跑 R1 同源 greps/讀碼/collect-only + path+size 假綠 vs digest 對照；**未**跑 polluting pytest body；repo 唯讀（僅本檔寫出）。

---

## FACT-RECEIPT（本輪實跑）

1. **analyze/start_analysis/refilter 檔數**  
   `rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l` → **16**（與 R2 §A 一致）。

2. **HTTP POST `/api/v1/ic/analyze`（R1 B-1 同源）**  
   `rg -n 'client\.post.*/api/v1/ic/analyze' tests/ --glob '*.py'` →  
   - `tests/api/test_ic_analysis_api.py:107`  
   - `tests/api/test_export_api.py:102`  
   - `tests/api/test_ic_deep_analysis.py:144`  
   三檔皆入 R2 §COVERAGE API-01..07。

3. **export 直接 h5py（R1 B-2 反例）**  
   `rg -n 'h5py.File\(filtered_path|features_dir = Path' tests/api/test_export_api.py` → L125 `Path("data_cache/features")`、L135 `h5py.File(...,"w")`。R2 → **S9**。

4. **transforms / materialize / meta / export-csv 生產字面量**  
   - `_apply_transforms_sync`: `api/services/ic_analysis_service.py:976–979` `data_cache/reports/post_ic_transforms_*.h5` → R2 **S6**  
   - materialize/meta: L1260 / L1321 `ic_ingest_cache` → **S4/S5**  
   - route export-csv: `api/routes/ic_analysis.py:405` → **S8**  
   - route `_resolve_filtered_path`: L454 → **S7**  
   - orchestrator `_persist_outputs` reports 字面量 L3182/3188 → **S2**；features via `_resolve_filtered_path` L3207 → **S1**

5. **path+size 假綠仍成立；digest 擊破**  
   ```text
   path_size_oracle_false_green= True  # AAAA→BBBB, size=4
   digest_detects_overwrite= True      # sha256 before≠after
   ```

6. **postflight / b6 弱點未變（R2 已降級非主證明）**  
   `scripts/agent_postflight.sh:8–32` 只 FAIL 縮減；`test_b6_warmup_trim._assert_data_cache_unchanged` 只 diff 新 features 路徑。

7. **conftest 現況（實作前）**  
   `tests/momentum/conftest.py` **不存在**；`tests/api/conftest.py` **存在**；`tests/momentum/Analysis/conftest.py` **存在**（僅 synthetic fixtures，無 redirect）。R2 規劃新建/ re-export — 文件層可對；見 B-5 可執行性。

8. **API fixture scope（掛載可執行性關鍵）**  
   - `test_ic_analysis_api.py:69` `ic_analysis_task` → **`scope="session"`**  
   - `test_export_api.py:65` `export_task` → **`scope="session"`**  
   - `test_ic_deep_analysis.py:124` `completed_ic_task` → **`scope="module"`**  
   pytest：`tmp_path` / `monkeypatch` 為 **function** scope → session/module fixture **不可**依賴 function fixture（ScopeMismatch）；且 session setup **先於** function-scoped usefixtures。

9. **API meta 符號（對照 R2 路徑列）**  
   三檔 meta：`TESTUSDT` / `12h`；case_id=`ic_api_test` | `ic_export_test` | `ic_deep_api_test` — 與 R2 API 表一致。

10. **Collect-only（無 body）**  
    - V1 路徑集合：**10 tests collected**  
    - V2：**2 collected**  
    - V6 三 API 檔：**32 collected**（R2 `≥30 passed` 量級合理）  
    - e2e：`test_performance_800_features` 有 `skipif(not RUN_IC_E2E_PERF)`（預設 skip）

11. **ML 實路徑**  
    - 存在：`tests/momentum/Analysis/test_lightgbm_{analyzer,edge_cases}.py`、`test_xgboost_protocol_methods.py`  
    - 存在：`tests/momentum/test_lightgbm_analyzer_phase3.py`、`tests/momentum/test_xgboost_protocol_methods_phase3.py`  
    - **不**存在：`tests/momentum/Analysis/test_*_phase3.py`  
    - V7 命令**未**含 edge_cases / 兩個 phase3 檔

---

## 原 findings 逐條

| ID | R1 要旨 | R2 閉合位置（claimed） | 複驗 | 判定 |
|----|---------|------------------------|------|------|
| **BLOCKING-1** | 漏 3 API 真路徑 polluters | §COVERAGE API-01..07；Phase2；V6 | greps 三檔=HTTP 全集；表列 fixture/h5py/export-csv/deep；V6 覆蓋三檔 | **CLOSED** |
| **BLOCKING-2** | wrap persist 攔不住 h5py/transforms/meta/models | §SEAM S1–S11；S9 h5py；S6 transforms | 生產寫點皆有具名 seam；S9 測側改 path | **CLOSED** |
| **BLOCKING-3** | hermetic/V5 假綠（b6 新檔、postflight 縮減、path+size） | §V `digest_data_cache` sha256；禁 path+size/mtime/b6/postflight 主證；V5→V9 輔助 | 同尺寸覆寫 digest 必 diff；主證明改 harness before==after | **CLOSED** |
| **BLOCKING-4** | mutation 預設不跑 / 寫真 cache / xfail 不可機檢 | 三態 + fake_prod + 禁真 cache + 預設 CI + exit `1 passed` | (a)(b)(c) 原缺陷已關；fake_prod 重綁機制略簡（見殘留）但不回退三原罪 | **CLOSED**（殘留見下） |
| **BLOCKING-5** | fixture 只掛 momentum 覆蓋不到 api | 三 conftest + plugin + usefixtures + session 顯式參數 | **跨樹註冊**有寫；**session/module + function redirect 不可執行**，且與「setup 前已 redirect」主張衝突 | **STILL-OPEN** |
| MINOR-1 | 大小應為大 | §RISK **大** + 白話 + 雙家族條款 | 已改 | **CLOSED** |
| MINOR-2 | RISK (b) 過窄 | (b) 擴 API/FF/models + 全集表 | 已改 | **CLOSED** |
| MINOR-3 | 票 5 劃界 | §G A/B hash oracle；V5 `2 passed`+`ab_hash=` | 條件式劃界+可機檢 oracle | **CLOSED** |
| MINOR-4 | opt-in 無強制 | §ISOLATION I3 inventory FAIL | 有靜態回歸 | **CLOSED** |
| MINOR-5 | models 延期不得宣稱全零 | ML-* 入 REDIRECT；撤 Phase4 defer | 表內有；但 V7 未蓋全 ML（見 NEW） | **CLOSED**（驗收缺口見 NEW-2） |

### BLOCKING-5 詳證（STILL-OPEN）

R2 §SEAM 寫：

> Session/module fixture 檔…參數 **顯式** `ic_persist_redirect: RedirectContext`，確保 setup 前已 redirect。

與 R2 `install_ic_persist_redirect(monkeypatch, tmp_path, ...)` / 預設 function fixture **不相容**：

1. **ScopeMismatch**：session/module fixture 不能 request function-scoped `tmp_path`/`monkeypatch` 型 redirect。  
2. **時序**：即使改用 `pytestmark=usefixtures("ic_persist_redirect")` 掛在**測試函式**，`ic_analysis_task` / `export_task` 仍在 **session setup** 先跑 `POST /analyze`（+ export 的 h5py 寫 features），redirect **尚未**安裝 → 仍污染 `data_cache/`。  
3. 此三 fixture 正是 R1 B-1 漏網主體；掛載「寫在紙上」但**依現行 pytest 規則無法如文兌現**。

**最低閉合（給 R3，擇一寫死）**：

- A) 將 `ic_analysis_task` / `export_task` / `completed_ic_task` **降為 function（或 module+session-safe redirect）**，且 redirect fixture scope ≥ polluter fixture scope；或  
- B) 提供 **session/module-scoped** `ic_persist_redirect`（`tmp_path_factory` + 手動 patch/restore，不用 function `monkeypatch`），並規定 polluter fixture **必須** depend on 它且 setup 順序先 redirect 後 analyze；或  
- C) 廢 session 污染 fixture，改 per-test analyze + redirect。

未寫死 A/B/C 前，不得稱 mount wiring concrete。

### BLOCKING-4 殘留（不單獨升級 BLOCK）

三態 + 禁真 `data_cache` + CI 預設 + `1 passed` 已關 R1 三洞。  
「Remove redirect → `fake_prod` digest 非空」仍須 **production 字面量重綁到 fake_prod**（非僅 spy raise）；R2 命名有 fake_prod，patch 步驟略隱。TODO 應寫死：mutation 全程 hardcode 根 = fake_prod，redirect 再指到 redirect_root。不阻本 finding CLOSED。

---

## NEW problems（R2 引入 / 新發現）

### NEW-1 — V1 exit contract 自相矛盾（MINOR）

R2 V1：`10 passed, 0 skipped, 0 failed`，同格又允許 e2e perf **`1 skipped`**。  
Receipt：V1 集合 collect=**10**；其中 `test_performance_800_features` 預設 **skip** → 實跑應為 **`9 passed, 1 skipped`**（未設 `RUN_IC_E2E_PERF`）。  
機掃「10 passed 且 0 skipped」與「允許 1 skipped」互斥 → 假紅或假綠風險。  
**修法**：改精確為 `9 passed, 1 skipped, 0 failed`（skip nodeid 鎖 perf）或分兩命令。

### NEW-2 — ML REDIRECT 表 vs V7 驗收漏掛（MINOR）

- ML-03 `test_lightgbm_edge_cases.py` 在表內，**不在** V7 命令。  
- ML-05/06 實體在 `tests/momentum/test_*_phase3.py`，**不在** `Analysis/`；V7 亦未列。  
→ Phase2「ML-01..06 全掛」可被 V7 部分綠掩蓋。  
**修法**：V7 顯式列入 edge_cases + 兩個 phase3 路徑（或 collect 白名單 = ML 表）。

### NEW-3 — API-06 case_id 報告名可更準（cosmetic）

export meta `case_id=ic_export_test`；表著重 features 強制覆寫已夠。非阻擋。

---

## 五軸複驗（派工原文）

| 軸 | 結果 |
|----|------|
| API polluters 已枚舉 vs §COVERAGE | **PASS** — 3 HTTP 檔 + h5py + export-csv 皆在 API-01..07 |
| h5py/export/transforms 有 §SEAM | **PASS** — S6/S8/S9（+ S1–S5/S7） |
| digest 擊敗同尺寸覆寫 | **PASS** — sha256 before≠after（AAAA→BBBB） |
| mutation 三態可證偽 | **PASS**（殘留：fake_prod 重綁步驟應再釘死） |
| mount wiring 具體可執行 | **FAIL** — session/module polluter fixture vs function redirect |

---

## 總表

| 類 | CLOSED | STILL-OPEN |
|----|--------|------------|
| BLOCKING 1–4 | 4 | 0 |
| BLOCKING-5 | — | **1** |
| MINOR 1–5 | 5 | 0 |
| NEW | — | NEW-1/2 建議 R3 順手修（非本輪唯一 BLOCK 因） |

---

ASSUMPTIONS_VERIFIED: HTTP analyze 僅 3 檔；export L125–135 直接 h5py；transforms/meta/export-csv 字面量與 R2 seams 對得上；path+size 假綠、digest 擊破；session/module fixture scopes；V1 collect=10 含 perf skipif；phase3 ML 在 tests/momentum/ 非 Analysis/  
TESTS_RUN: rg/sed/ls/python3 digest probe；pytest --collect-only V1=10 / V2=2 / V6=32；**0** polluting body  
FAILURES_SEEN: none（審查）  
SCOPE_CHANGES: none（僅本檔）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_ROOT_NOT_TOUCHED: 1  

**產出檔**：`handoffs/P2DEBT-T2-SPEC-REVERIFY-grok.md`

Verdict: BLOCK — BLOCKING-5 STILL-OPEN: session/module API polluter fixtures cannot take function-scoped redirect; R2 "explicit param before setup" is not executable under pytest scope rules
