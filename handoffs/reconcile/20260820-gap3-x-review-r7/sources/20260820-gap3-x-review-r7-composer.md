# GAP-3 TODO 對抗審 R7 — COMPOSER

task-id: `20260820-GAP3-X-REVIEW-R7`  
審查標的: `docs/GAP3_EVENT_TODO.md`（DRAFT v0.1）vs `docs/GAP3_EVENT_SPEC.md`（FROZEN 2026-08-20）  
brief: `handoffs/20260820-gap3-todo-adv-r1-brief.md`  
追溯基準: `handoffs/20260820-gap3-todo-stage1-index.md`

## 被當成事實的未驗證假設（§0）

| 前提 | 標注 | R7 複核結論 |
|---|---|---|
| §V M1–M12 TODO 與 SPEC byte-identical | fact-verified（brief） | **成立** — RECHECK 空 diff（見下） |
| `survivor_contract.py`／`strategy_validation/{pbo,min_btl}.py`／`ichc_run.run_analyze()`／`tests/golden/la0/inputs/` 存在 | fact-verified（brief） | **成立** — `test -f`／`rg` 探針全命中 |
| `doc_format_precheck.sh` TODO rc=0 | fact-verified（brief） | **成立** — 本輪重跑 rc=0 |
| B2 批內〔§G 凍結〕步驟＋B2.4 升版前禁寫 v2 payload | assumed（brief） | **攻後成立** — 與 SPEC §G「B2.3 動工前凍結」＋B2.4 `additional_properties:false` 一致；為合法施工序細化，非越權 |
| §G-1 import `gap2_canonical_sha`、不另立 scrub | assumed（brief） | **攻後成立** — scrub ①②③⑤ 與 `scripts/gap2_freeze_golden.py:43-63` 字面對齊 |
| `ic_feed.py`／`generator.py`／`pipeline.py`／`types.py`／`create_event_sample_pipeline()` 屬 V13 細化 | assumed（brief） | **攻後成立** — SPEC §RISK 末行授權 B5 一個 factory 出口；B2.3「event_samples 餵入層」未禁檔名；V13「繼承並細化到批次層」 |

## 20 Task 抄寫漂移比對（逐 Task 全欄）

| Task | 目標 | 檔案/改法 | 驗證 | 邊界/不可做/存活至/覆蓋風險 | 漂移 |
|---|---|---|---|---|---|
| B1.0 | 無 | 無（契約 JSON＋`import_contract.py`；欄位 pointer 契約檔） | 無（五斷言＋M3/M12） | 無 | **無** |
| B1.1 | 無 | 無（`align_events`＋兩層 `AlignmentReceipts`；D2 三段鏈） | 無（§G-2 手算＋mutation ASSERT） | 無 | **無** |
| B1.2 | 無 | 无（UTC duration gap；C⇒cluster_first／A/B⇒uniqueness） | 无 | 无 | **无** |
| B1.3 | 无 | 无（per-symbol ms 切分；`cluster_weight=1/n`；macro/micro） | 无（`atol=1e-12` 權重和） | 无 | **无** |
| B1.4 | 无 | 无（吃 B1.6；`N_perm=1000` 三道硬檢） | 微：SPEC「落 CI 內」→TODO「落帶內」；與同 Task 改法「permutation quantile 帶」一致，非數值/命令漂移 | 无 | **无**（用語對齊改法，可執行） |
| B1.5 | 无 | 无（四門檻 0.05/0.0/0.01/0.05；公式 R2 Y2） | 无 | 无 | **无** |
| B1.6 | 无 | 无（全史物化＋as-of 取列；`feature_manifest_hash`） | 无（`atol=1e-12`） | 无 | **无** |
| B2.1 | 无 | 无（`event_forward_return_table`；D1-6 entry） | 无 | 无 | **无** |
| B2.2 | 无 | 无（擴 B1.4 核心；`counterexample_kind_effective` 分層） | 无 | 无 | **无** |
| B2.3 | 无 | 細化：`ic_feed.py`＋`gap3_freeze_golden.py`（SPEC 授權之餵入層／§G 凍結） | 无（conditional_ic＋§G-1 `--check`） | 无（v2 payload 時序＝SPEC B2.4 升版約束） | **无** |
| B2.4 | 无 | 无（v1→2；`survivor_contract.py` 全路徑） | 无 | 无 | **无** |
| B2.5 | 无 | 无（D4 manifest；`missing_prevalence_disclosure`） | 无（分母手算＋mutation ASSERT） | 无 | **无** |
| B3.1 | 无 | 无（D3 角色隔離；`ConditionSpec` digest） | 无（role ASSERT） | 无 | **无** |
| B3.2 | 无 | 細化：`generator.py`（SPEC 未禁檔名；G1–G6 逐項保留） | 无 | 无 | **无** |
| B3.3 | 无 | 无（`state_counters.py` 五算子） | 无 | 无 | **无** |
| B4.1 | 无 | 无（`pattern_bridge.py` 消費側；AR-3 共同約束） | 无 | 无 | **无** |
| B4.2 | 无 | 无（ledger＋`pbo.py`/`min_btl.py`；AUC 禁餵 DSR） | 无（metric ASSERT） | 无 | **无** |
| B5.1 | 无 | 細化：`pipeline.py`＋`create_event_sample_pipeline()`（§RISK 授權） | 无 | 无 | **无** |
| B5.2 | 无 | 无（三頁升級；兩表僅事件模式） | 无 | 无 | **无** |
| B5.3 | 无 | 无（UAT 三命令＋registry 殘留） | 无 | 无 | **无** |

**小結**：20/20 Task 無 BLOCKING 抄寫漂移；3 處為 V13 合法細化（`ic_feed`／`generator`／`pipeline`）；1 處驗證用語與同 Task 改法對齊（B1.4 帶 vs CI）。

## §V M1–M12 RECHECK

```bash
diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) \
     <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)
# 空輸出 → rc=0
```

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾/互斥 | 无 — 批內順序 B1/B2/B3 依賴與 SPEC §P 一致 |
| 2 漏項/端到端 | 无 — 20 Task＋§B Gate＋§G 六項已落地 |
| 3 不可測驗收 | 无 — 各 Task 驗證欄含 pytest 命令＋ASSERT |
| 4 可疑 quant 假設 | 无 — D1/D2/D3/D4 鐵三角 §0-13 pointer ＋ Task 內三段鏈/固定分母保留 |
| 5 過度工程 | 无 |
| 6 OOM/並行 | 无 — B5.1 萬級牆鐘列邊界② |
| 7 Cache 正確性 | 无 |
| 8 API/型別/相容 | 无 — R7 DTO 殼 vs momentum 純函式分離明確 |
| 9 測試品質 | 无 — mutation M1–M12＋§G 四類 oracle |
| 10 Agent 可執行性 | 无 — 各 Task 含檔案/函式/偽碼/驗證/不可做；§2 獵空殼未見標題-only |
| 11 必要性/短命工 | 无 — `存活至`／`覆蓋風險` 全 20 Task 已填且與 SPEC 一致 |

## §2 範本錨點＋獵空殼

- §0 解耦/不可違反原則：13 條＋白名單六項 — **實填**
- §B 批次/Gate：五批＋五 Gate — **實填**
- §V mutation：12 條 — **逐字一致**（RECHECK 空）
- §N：pointer registry（8 殘留不屬 TODO scope）— **符合 brief 不受理範圍**
- 獵空殼：20 Task 皆有函式簽名或偽碼＋可執行驗證命令；未見「確認正確」式空話

## SPEC-AMENDMENT 提案（不計入 TODO BLOCKING）

| 項 | 說明 |
|---|---|
| B3.3 驗證路徑 | SPEC 與 TODO 皆寫 `tests/momentum/feature_engineering/`；repo 實際為 `tests/feature_engineering/`（兩檔一致，非 TODO 獨有漂移）— 若實作前未修正，B3 Gate 命令會 miss collection |

## 必答

1. **20 Task 抄寫漂移**：上表 — 全 **無** BLOCKING 漂移。
2. **§V M1–M12 逐字一致？**：**是** — RECHECK diff 空輸出。
3. **TODO 相對 SPEC 新增＝合法細化還是越權？**：**合法細化** — B2 §G 施工序、`gap3_freeze_golden.py` import 復用、新模組檔名/factory 簽名均落在 SPEC §G/§RISK/V13 授權範圍。
4. **V13 深度紅線與錨點？**：**通過** — `doc_format_precheck.sh` rc=0；各 Task 驗證/token 非空。
5. **冷啟動可執行性？**：**可** — 單 Task 含輸入/輸出/檔案/函式/偽碼/驗證/邊界/不可做；契約字面 pointer `event_import_contract.json`。
6. **可凍結？**：**可凍結（Internal Frozen → 三家 reconcile＋戳記後 TODO FROZEN）** — 無 BLOCKING 須先修。

## COMPOSER-R7-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的實質 finding；20 Task 抄寫漂移比對、§V RECHECK、brief 三條 assumed 攻擊、§1/§2 掃描均未見 BLOCKING/MAJOR。

**碼證**: `diff <(sed -n '370,382p' docs/GAP3_EVENT_SPEC.md) <(awk '/^- \*\*mutation 條件\*\*/,/^  - M12/' docs/GAP3_EVENT_TODO.md)` → 空輸出 rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`rg -c '^### Task '` TODO=20 SPEC=20；`rg -c '^  - M'` TODO=12；`shasum -a 256 docs/GAP3_EVENT_{SPEC,TODO}.md` → `544c2922ef2e`／`511c3f1b3b84`；路徑探針 `survivor_contract.py`/`pbo.py`/`min_btl.py`/`ichc_run.py:30`/`tests/golden/la0/inputs/` 皆存在；`gap2_freeze_golden.py` scrub ①②③⑤ 與 TODO §B B2 前言一致。

**來源摘要**: docs/GAP3_EVENT_TODO.md#511c3f1b3b84; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

## Verdict：可派工（可進 TODO 三家 reconcile＋戳記）

無 BLOCKING/MAJOR。建議 reconcile 時帶上 SPEC-AMENDMENT 列之 B3.3 pytest 路徑（兩檔同源，非本輪 composer finding）。

---

ASSUMPTIONS_VERIFIED: §V diff 空；doc_format_precheck rc=0；20 Task 計數對齊；M1–M12=12；關鍵路徑 ls/rg 探針；gap2 scrub 對照  
TESTS_RUN: `diff … mutation …` → rc=0；`bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_TODO.md` → rc=0；`bash scripts/completeness_check.sh --single handoffs/20260820-gap3-x-review-r7-composer.md --family composer` → COMPLETENESS PASS rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-x-review-r7-composer.md`

STATUS: DONE
