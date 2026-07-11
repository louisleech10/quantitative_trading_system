# P2DEBT-T2 TODO R1 adversarial review — grok — 2026-07-11

Task-id: `p2debt-t2`  
待審: `handoffs/P2DEBT-T2-TODO-DRAFT-R1.md`  
凍結 SPEC: `handoffs/P2DEBT-T2-SPEC-DRAFT-R4.md`  
對照 MINOR: `handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-grok.md` NEW-R4-1..4  
Scope: repo **read-only**（僅本檔 + 本輪 handoff）；**未**讀 codex TODO review；**未**跑 polluting pytest body；**未**寫 `data_cache/`；**未** git checkout/restore。

---

## Meta / 過時標註（先記）

| 項 | 證據 | 判定 |
|----|------|------|
| Header L4「composer 待戳」 | `handoffs/P2DEBT-T2-SPEC-REVERIFY-R4-composer.md` L192：`RECONCILE-STAMP APPROVED (p2debt-t2 SPEC R4, composer, 2026-07-11)`；同檔 grok stamp 已在 | **STALE 行**（非 oracle 弱化；TODO R2 須改為「雙戳已齊：grok+composer」） |
| 基線 dirty 行數 | TODO 稱 pre-dirty **22**；本輪 `git status --porcelain \| awk … \| sort -u \| wc -l` → **23**（HEAD 仍 `241ab910…`） | **MINOR 基線漂移**（實作前必須重存 pre-dirty；不得釘死 22） |

---

## FACT-RECEIPT（本輪唯讀實跑）

### R1 — 16-caller

```text
命令: rg -l '\.(analyze|start_analysis|refilter)\(' tests/ --glob '*.py' | sort | wc -l
結果: 16
```

### R2 — V1 collect-only（無 body）

```text
命令: venv/bin/python -m pytest \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_fallback_insufficient_data_marks_applied_false \
  tests/momentum/Analysis/test_ic_1a_cut1_oos.py::test_oos_applied_true_when_sufficient \
  tests/momentum/test_ic_e2e.py \
  tests/momentum/test_ic_feature_filter.py::test_analyze_applies_feature_filter_metadata_and_summary_limit \
  tests/momentum/Analysis/test_ic_1a_cut1_golden.py \
  --collect-only -q
結果: 10 tests collected
EXIT=0
（與 TODO/SPEC V1 collect=10 一致；9p+1s 為 body 契約，本輪未跑 body）
```

### R3 — V2 collect-only

```text
命令: venv/bin/python -m pytest \
  tests/api/test_ic_analysis_service.py::test_analyze_real_run_split_validation_passes_with_real_axis \
  tests/api/test_ic_analysis_service.py::test_resolve_run_path_contains_config_hash \
  --collect-only -q
結果: 2 tests collected
```

### R4 — V7 六檔 collect-only

```text
命令: venv/bin/python -m pytest \
  tests/test_feature_factory_e2e.py \
  tests/momentum/Analysis/test_lightgbm_analyzer.py \
  tests/momentum/Analysis/test_lightgbm_edge_cases.py \
  tests/momentum/Analysis/test_xgboost_protocol_methods.py \
  tests/momentum/test_lightgbm_analyzer_phase3.py \
  tests/momentum/test_xgboost_protocol_methods_phase3.py \
  --collect-only -q
結果: 141 tests collected
```

### R5 — V6 API 三檔 + 解耦 + I1 nodeids + 原型

```text
V6 collect: 32 tests collected
grep -r "from api\." momentum/ | wc -l → 0
I1 三 nodeid collect: 3 tests collected
cd /tmp/p2debt-t2-proto && python3 -m pytest -q → 8 passed
HEAD: 241ab91030dcc0cc87876e517f98213130dd5f90
dirty unique paths: 23
e2e create_feature_factory(: 7 處（含 multi_tf L78）
export_task 直接 h5py.File: tests/api/test_export_api.py L125–137（與 TODO S9 行號一致）
GEN-01..04 四檔皆存在
scripts/run_ic_persist_hermetic.sh: 尚未存在（預期）
tests/momentum/conftest.py: 尚未存在（預期新建）
tests/conftest.py: 已存在（條件 scope 追加 pytest_plugins 可行）
```

### R6 — 命令極性 / ticket-1 機械掃描（TODO 正文）

| 檢查 | 結果 |
|------|------|
| `comm -13` post∖pre + 禁 `comm -23` | 有；Final §7 正確 |
| `rc=$?; echo $rc; exit $rc` | B3 Gate / V4 / Final 有；禁 bare `echo $?` 有寫 |
| V8 `grep … \| wc -l` 預期 0 | **正向計數**（非 inverted `! grep`） |
| xdist / 平行 | 明文禁止 |
| `run_guard` digest mismatch → return 1 + `set -euo pipefail` | 與 SPEC 同構；pytest 失敗在 set -e 下不會被後續 echo 蓋掉 |
| 裸 polluting 當最終驗收 | 明文禁止；正式=`--set all` |

**命令機械面（exit masking / inverted grep / comm -23）: 無 ticket-1 級回歸。**  
另見 Findings 的 **可執行 gate 錯誤預期**（非 masking，是錯期望）。

---

## (1) 100% 覆蓋追溯矩陣

| SPEC 塊 | 列數宣稱 | TODO 映射 | 本輪判定 |
|---------|----------|-----------|----------|
| §SEAM S1–S11 | 11 | 追溯表 → 2.1 / 2.3 / 2.4 / 2.5；unit 1.3 | **結構有列**；S9/S11 **Phase 序矛盾**見 B1 |
| §COVERAGE 污染 31 | IC12+API7+ML6+FF2+GEN4=31（展開核對） | Task 2.2–2.5 / 3.3 / 4.1 | **PASS**（分組列，展開齊） |
| 16-caller #1–#16 | 16 | 各有分類+TODO | **PASS**；rg 實跑 16 |
| §G A/B/C | 3 | Task 3.2 | **列齊**；normalize 細節缺 → M2 |
| I1–I3 | 3 | Task 3.3；I1 nodeid 與 SPEC 字面一致 | **PASS**（collect 3 nodeid OK） |
| V1–V7 + V3b + V8–V9 | 11 | 3.1–3.4 + Final | **列齊**；V7 命令未內嵌六檔路徑 → M3 |
| Mutation | 1 | 1.4 + 3.4 | **列齊**；1.4.1 雙模表述 → M4 |
| R4 必驗 1–6 | 6 | 追溯表 | **PASS** |
| NEW-R4-1 multi_tf | — | §0 硬性 + 2.5 全部 7 factory + I3 | **ABSORBED**（且強於 SPEC 原文「六個 generate」） |
| NEW-R4-2 spy hook | — | §0 + 1.1.4 rewrite 決策點 | **ABSORBED** |
| NEW-R4-3 abs prefix | — | §0 + 1.1.3 `repo_root/data_cache.resolve()` | **ABSORBED** |
| NEW-R4-4 wrapper 文案 | — | §0 + 1.3.2/1.3.3 分案 | **ABSORBED** |
| 總追溯 89 | 11+31+16+3+3+11+1+6+3+4 | 表頭自洽 | 算術 **PASS** |

附錄 B 四 MINOR 對照表與 §0 硬性句一致 → **吸收宣稱屬實**（不因此放行 B1）。

---

## (2)(3)(4) Findings

### B1 — [BLOCKING] Phase 1 Gate 要求 S1–S11 全 resolve/probe，但 S9/S11 helper（及 S10 installer 正文）延到 Phase 2 — 冷啟動 Phase 1 **不可執行**  
**信心度: High**

**證據:**
- Task 1.3.1：`test_seam_probe_redirect_only[S1..S11]` → **11 passed**；Phase 1 Gate：unit 全 passed。
- Task 1.1 修改檔**僅** `tests/fixtures/ic_persist_redirect.py`；B1 prompt：**禁止 REDIRECT wiring**。
- SPEC/TODO S9 target = `tests.api.test_export_api._export_fixture_filtered_path`（現況**不存在**，本輪 rg 僅見 L125 字面 `Path("data_cache/features")`）。
- S11 target = `tests.test_feature_factory_e2e._create_e2e_factory`（現況不存在）；helper 在 Task **2.5**。
- Task **2.1** 明文：`_build_manifest()` **註冊 8 seams（S1–S8）** — 與 `REQUIRED_SEAM_IDS` 11 元及 Phase 1 11-probe 衝突。
- Task **2.3** 對 S10 只有五檔 `pytestmark` + models probe，**無** `_resolve_model_path` installer 精確變更表（S10 生產符號雖已存在，TODO 仍未派工實作句）。

**會怎麼失敗:** 冷啟動執行端做 B1 → `resolve_all` import S9/S11 缺 attr → `RedirectCompletenessError` / 無法 `install_once` → 與「11 passed」Gate 互斥；或為過 Gate 而削弱 completeness（假綠）。

**修法（TODO R2，不改 SPEC 契約）:**  
任選並寫死其一：(a) Phase 1 允許**最小 stub helper** 落地（export_api / e2e / 或 fixture 側可 import probe 接點）並把 S9–S11 installer 列入 Task 1.1/1.x 精確表；或 (b) Phase 1 Gate 明確 **S1–S8(+S10) only**，S9/S11 probe 移 B2 Gate，且 B1 不得宣稱 S1–S11 全綠；**禁止**默許「邊 wiring 邊裝 seam」破壞 atomic resolve。

**RECHECK:** 讀 Task 1.3.1 / 2.1 / 2.4 / 2.5 修改檔列表與 Phase 1 Gate 一句是否仍互斥。

---

### B2 — [BLOCKING] Task 2.5 驗收 `create_feature_factory(` 完工後預期 **0** — 與同檔 helper 內必留 **1** 次呼叫矛盾（錯期望 gate）  
**信心度: High**

**證據 (TODO L369–373):**
```text
rg -c "create_feature_factory\(" …  # 預期：7（…後應為 0 直接呼叫）
rg -c "_create_e2e_factory\(" …     # 預期：7
```
本輪基線：`create_feature_factory(` = **7**。完工後 `_create_e2e_factory` 本體若仍呼叫 `create_feature_factory()`，全檔 `rg -c` **至少 1**，不是 0。

**會怎麼失敗:** 執行端為湊 0 而刪 helper 內工廠呼叫、改為無法建構 factory，或把 gate 當失敗硬改測試；I3「出現次數與 helper 覆蓋一致」亦被錯誤基線帶偏。

**修法:** 完工契約改為例如：`_create_e2e_factory(` == 7（或 call-site 數）；`create_feature_factory(` == 1 且**僅**出現在 `_create_e2e_factory` 定義內；測試函式 body 0 直接呼叫。分 pre/post 兩段期望，禁止混寫。

**RECHECK:** 對修訂後兩條 `rg -c` 期望做靜態推演是否可同時成立。

---

### M1 — [MAJOR] §G `normalize(result)` 豁免集合未落入 Task 3.2（冷啟動缺 oracle 細節；有弱化風險）  
**信心度: High**

**證據:** SPEC §G 要求 `json.dumps(..., sort_keys=True, default=str)`，**只**豁免 path/mtime 類欄位，**不得**豁免數值/NaN/feature count/selection/schema。TODO Task 3.2 僅 `hash_a`/`hash_b==hash_a`/`hash_off==hash_a`，**全文無 normalize 句**（`rg normalize|豁免` 於 TODO → 無）。Header 卻稱「不必回讀 SPEC」。

**會怎麼失敗:** 實作者自行擴大豁免 → ON/OFF 假相等；或未豁免 path → 假紅後再放寬斷言（假綠路徑）。

**修法:** Task 3.2 內嵌 SPEC normalize 規則全文（或可複製的 bullet），並加「禁止新增豁免欄位」否決句。

---

### M2 — [MAJOR] V7 skip **nodeid/reason 白名單 fail-closed** 未寫進 harness 演算法（oracle 轉移不完整）  
**信心度: High**

**證據:** SPEC §V：「report 中任何其他 nodeid/reason skip 皆 FAIL；不得用 `passed == collected - arbitrary skips`」。TODO Task 3.1 V7 僅「skip 僅 FF `_require_data` missing kline」作**期望敘述**；`run_guard` 草稿只做 digest，**無** skip 解析/白名單 exit 1。禁止事項有「V7 非白名單 skip」口號但無命令。

**會怎麼失敗:** harness 只看 0 failed + digest → 任意 skip 仍可綠。

**修法:** Task 3.1 為 V7（與 V1 perf skip）寫明：解析 pytest 報告/JSON report，非白名單 skip → `exit 1`；白名單字面列出。

---

### M3 — [MINOR] Task 3.1 V7 內層命令寫「六檔 ML+FF（SPEC §V 清單）」— 違反自身冷啟動「不必回讀 SPEC」  
**信心度: High**

附錄 A / Task 2.3+2.5 可拼回六路徑，但 harness 表應**內嵌**六絕對相對路徑（與 SPEC L410–417 同文）。非 BLOCK（可還原），屬冷啟動摩擦。

---

### M4 — [MINOR] Task 1.4.1 驗證「DISABLE → FAILED；正常 → PASSED」雙模易被做成「常駐紅燈」測  
**信心度: Medium**

3.4 `test_mutation_redirect_disabled_caught` **PASSED + MUTATION_CANARY** 才是套件內 canary 正模。1.4.1 應改成：測試**內** monkeypatch DISABLE 後 assert 路徑落 production/sacrificial 且**用例本身 PASSED**；另列可選 PROTO 對照（外層 env 令既有 opt-in 測紅）並**排除**於 Phase 1 Gate 收集。

---

### M5 — [MINOR] FF-02 追溯到 I3「回歸 canary」，但 I3 正文只做 REDIRECT inventory / helper / 16-caller — 無 `feature_engineering/**` 執行 canary  
**信心度: Medium**

不過度升 BLOCK：SPEC 對 FF-02 是保留既有隔離。TODO 應改標「分類-only / 不新增 canary」或真加一條不碰 repo cache 的回歸命令。

---

### M6 — [MINOR] 基線 dirty=22 過時；現 23。Header composer 待戳過時（見 Meta）

---

## (3) SPEC oracle 弱化檢查（摘要）

| Oracle | 弱化？ |
|--------|--------|
| digest 主證明；path+size 不可取代 | **無**（§0 + run_guard） |
| V1 9p1s / 唯一 perf skip | **無**（命令+期望齊；collect 10 已核） |
| V2 2p | **無** |
| V5 3p + ab_hash + Run C chdir(work)+雙 digest | **無弱化句**；normalize 缺詳 → M1 |
| V6 ≥30；collect 32 已核 | **無** |
| V7 141 + skip 白名單 | 期望在；**執法算法缺** → M2 |
| Mutation 拔 redirect 必可證偽 | 3.4 清楚；1.4 表述險 → M4 |
| 禁改 production 簽名/schema/NaN gate | **無** |
| NEW-R4-1..4 | **加強或等價吸收，未削弱** |

未發現「放寬斷言 / skip polluter / 拿掉 digest set」類主動弱化。殘留是**轉移不全**與**Phase 序**，不是改小門檻。

---

## (4) 冷啟動可執行性總評

| 區段 | 可執行？ |
|------|----------|
| §0 邊界 / scope gate / 防假綠 | 是 |
| B1 / Phase 1 Gate | **否** — B1 |
| Phase 2 wiring 任務表 | 大致是；S10 installer 句弱；2.5 rg 期望錯 — B2 |
| Phase 3 harness | 骨架是；V7 路徑與 skip 執法不全 — M2/M3 |
| Final Acceptance | 出口契約與 comm -13 正確；依賴 B1–B3 先可跑 |

---

## 10 類速檢（ADV template）

1. 矛盾/互斥：**有** — B1（11 seam vs 8 註冊 vs Phase 2 helper）  
2. 漏項：**有** — S10 installer 精確步、normalize、V7 skip 算法  
3. 不可測驗收：**部分** — 多數 Gate 可跑；B1/B2 期望不可同時真  
4. quant 假設：無（本票測試隔離）  
5. 過度工程：無（對準 SPEC process-global）  
6. OOM/並行：禁 xdist 有  
7. cache：digest 三目錄有；spy+abs prefix 有  
8. API 相容：禁改生產簽名有  
9. 測試品質：mutation/isolation/golden 有；skip 白名單執法弱  
10. Agent 可執行性：**B1 擋住冷啟動 Phase 1**

---

## 結構化收尾

```
ASSUMPTIONS_VERIFIED: TODO 追溯表展開 31 污染列；16-caller rg=16；V1 collect=10；V2=2；V6=32；V7=141；I1 三 nodeid collect=3；解耦 grep=0；e2e create_feature_factory=7 含 multi_tf；export_task h5py L125-137；GEN 四檔在；原型 8 passed；composer SPEC R4 stamp 已存在（header 待戳為過時）；NEW-R4-1..4 在 TODO §0/Tasks 有對應硬性句
TESTS_RUN: collect-only 如上 R2–R5（0 polluting body）；/tmp/p2debt-t2-proto pytest -q → 8 passed；靜態 rg/grep/git 如上
FAILURES_SEEN: none unexpected
SCOPE_CHANGES: none（僅本 review 產物）
NUMERIC_OR_SCHEMA_IMPACT: none
```

**產出:** `handoffs/P2DEBT-T2-TODO-REVIEW-grok.md`

---

## Verdict

**Verdict: BLOCK — Phase 1 與 S9/S11（及 S10 installer 派工）不可同時滿足 cold-start（B1）；Task 2.5 完工 rg 期望 create_feature_factory=0 為錯 gate（B2）。**

不附 `RECONCILE-STAMP APPROVED`。  
TODO R2 至少閉合 B1+B2；建議同輪吸收 M1+M2（normalize 全文 + V7 skip 執法）與 stale header（composer 已戳、dirty 重測）。  
MINOR M3–M6 不單獨阻 stamp，但 R2 一併修可減少下一輪摩擦。

STATUS: DONE
