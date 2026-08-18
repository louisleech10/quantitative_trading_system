brief-kind: review

# GAP-2a／2b TODO adversarial 審查 R9 — COMPOSER

**task-id**: `20260818-GAP2-X-REVIEW-R9`  
**family**: `composer`  
**brief**: `handoffs/20260818-gap2-todoadv-r9-BRIEF.md`  
**標的**: `docs/GAP2_MARGINAL_IC_TODO.md`（**DRAFT R3**）｜義務：`docs/GAP2_MARGINAL_IC_SPEC.md`（R7 FROZEN）＋`docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-1..A1-4）｜收斂：`handoffs/reconcile/20260818-gap2-x-review-r8/synth.md`（U1–U10）  
**date**: 2026-08-18

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標記 | R9 結論 |
|---|---|---|
| `template_check todo` PASS | fact-verified | **成立** — `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → `TEMPLATE PASS` |
| `todo_spec_crosscheck` SMOKE PASS | fact-verified | **成立** — `bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → `CROSSCHECK SMOKE PASS` |
| U6 駁回：`grep -F '非獨立 OOS 驗證'` → 0 | fact-verified | **成立** — 同命令 rc=1（0 命中）；L256 為「…非獨立驗證」 |
| Task 4.1 `_inject_root_oos` 兩插入點覆蓋 root 重註 | assumed→verified | **成立** — `_annotate_root_status_and_pass_class` 三呼叫點（`:1130` fallback wrapper、`:1542` xsec、`:3424` `_stage7_report`）；xsec 節 `not_applicable` 不需注入；TODO L202／L220 明列 `_stage7_report`＋fallback wrapper 重注入 |
| Task 4.1 xsec＋reporter 透傳不破 10 處 reporter 測試 | assumed→verified | **成立** — TODO L201「缺鍵省略、不補裸 `{}`」；現 `ic_reporter.generate_json_report` 未硬編 marginal_ic 鍵（`:327-347`） |
| Task 1.2／4.3 `monkeypatch.setattr(marginal_ic,"fit_projection",…)` 可攔內部呼叫 | assumed→verified | **成立** — Task 1.2 步驟 4 同模組直呼 `fit_projection(...)`；模組級 setattr 可攔（禁 top-level `from … import fit_projection` 綁定——TODO 未禁但實作要點已明示同檔呼叫） |
| A1-4 三檔足 B5、不需碰其他前端既有檔 | assumed→**推翻** | **不成立** — 見 COMPOSER-R9-P1-01 |
| 各批 gate `mutation_probe_check.sh` 路徑對映 | assumed→mostly verified | §B L32–35 已明列；Phase B1 測試 L110 殘句見 P2-01 |

---

## COMPOSER-R9-P1-01

**斷言**: Task 5.1 要求「接入 IC 結果頁 deep 區塊」（必改 `frontend/src/app/ic-analysis/page.tsx` import＋渲染 `<MarginalICTable>`），但 §0／A1-4 白名單未含該檔，執行端無法同時完成 B5 表格落地與「白名單外一律不碰」。

**碼證**: VERIFY `grep -n '接入 IC 結果頁 deep' docs/GAP2_MARGINAL_IC_TODO.md` → L257；Task 5.1 L258「修改檔案」僅列 A1-4 三檔＋新 `MarginalICTable.tsx`；§0 L12「唯此七處」無 `page.tsx`。`grep -n MarginalICTable frontend/src/app/ic-analysis/page.tsx` → 0 命中（現況未接入）。SPEC Task 5.1 L236 同義務「接入現有 IC 結果頁 deep 區塊之後」。RECHECK: 比對 §0⑥／A1-4 與 Task 5.1 步驟 3／修改檔案清單是否含 `frontend/src/app/ic-analysis/page.tsx`（或等價容器）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；frontend/src/app/ic-analysis/page.tsx#77341721b6f0

[MAJOR] 信心度=High；**SPEC 義務側**（母 SPEC L236 ＋ TODO L257 義務已寫，scope 未同步）。失敗：agent 守 §0 則表格永不顯示；越權改 `page.tsx` 則違反派工白名單。修法：延伸檔 A1-5（或 A1-4 增列）把 `frontend/src/app/ic-analysis/page.tsx` 納入 §C#6 既有檔（僅 import＋`<MarginalICTable report={report?.marginal_ic} …/>` 插入 deep `TabsContent`）；同步 TODO §0⑥ 與 Task 5.1 修改檔案清單。

---

## COMPOSER-R9-P2-01

**斷言**: Phase B1 測試段 L110 仍寫「`bash scripts/mutation_probe_check.sh` 對新檔綠」未帶路徑，與 §B L32／§0 L19（無參數 rc=1）及 U9 寫回不一致，執行端若跟 L110 會 gate 硬失敗。

**碼證**: VERIFY `grep -n 'mutation_probe_check.sh' docs/GAP2_MARGINAL_IC_TODO.md` → L110 無 test path；§B L32 已為 `… test_survivor_contract.py tests/momentum/Analysis/test_marginal_ic.py`。RECHECK: `bash scripts/mutation_probe_check.sh` → rc=1（用法提示）。

**來源摘要**: docs/GAP2_MARGINAL_IC_TODO.md#96facb832358

[MINOR] 信心度=High。不阻 B1 若跟 §B 表；阻 agent 只讀 Phase 小節。修法：L110 與 §B L32 逐字對齊。

---

## R9 必核 U1–U10（逐條 verdict；引 TODO 行號）

| 群集 | verdict | 依據 |
|---|---|---|
| **U1** A1-4 三檔／§0⑥／SPEC 母檔未改 | **PASS** | §0 L12 ⑥ 列 `types.ts`＋`icAnalysisStore.ts`＋`FeatureTierPanel.tsx`；A1-4 L17–19；`git diff docs/GAP2_MARGINAL_IC_SPEC.md` 空 |
| **U2** 刪 fit_scope→pass_class；`_inject_root_oos`；root oracle | **PASS** | L201–202 無推導殘句；L202 `_inject_root_oos`；L211 驗證①③③′＋`test_mutation_fit_scope_derived_oos_breaks_root_oracle` |
| **U3** pre `case_id`＋`report_ref` | **PASS** | L187 `--write` schema 含 `case_id`；L234 A1-2 斷言 |
| **U4** 4.2 顯式 kwargs＋三 caller＋`_ic_cache` 承接 | **PASS** | L202 persist kwargs；L220 三 caller (a)(b)(c)＋`event_identity=event_identity`；L226 驗證⑧＋`test_mutation_persist_reads_ic_cache_breaks_cold_call` |
| **U5** `persist_suppressed` 五鍵分欄 | **PASS** | L220 完整 object；L226 驗證⓪ 第四形狀 |
| **U6** 駁回碼證 | **PASS（駁回成立）** | `grep -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0 命中；L256 警語無禁子字串 |
| **U7** `fit_projection` spy | **PASS** | L90 ⑮；L236 bench spy；L242 `test_mutation_counter_without_fit_call_breaks_spy` |
| **U8** xsec N/A＋reporter 透傳＋⑯ | **PASS** | L201 xsec `dict(_xsec_na)`；reporter 條件透傳；L211 ⑯ |
| **U9** gate 探針路徑＋`test_mutation_*` | **PASS（L110 除外→P2-01）** | §B L32–35 各路徑；Task 1.0–4.3 驗證欄具名 `test_mutation_*` |
| **U10** 「四處」殘留 | **PASS** | `grep -n '四處' docs/GAP2_MARGINAL_IC_TODO.md` → 僅 L3 歷史敘述 |

---

## §1 必查 11 類（摘要）

1. **矛盾/互斥**：P1-01（B5 接入 vs 白名單）；其餘 U1–U10 已收斂。  
2. **漏項/端到端**：P1-01 前端 mount 漏 scope。  
3. **不可測驗收**：無新增（各 Task 驗證含 rc／atol／spy）。  
4. **可疑 quant 假設**：無。  
5. **過度工程**：無。  
6. **OOM/並行**：無（bench 觀測＋spy 上界 L236）。  
7. **Cache 正確性**：U4 顯式 kwargs 已寫回。  
8. **API/型別/相容**：reporter 缺鍵省略策略已寫（L201）。  
9. **測試品質**：無新增缺口。  
10. **Agent 可執行性**：P1-01 B5 卡住；P2-01 L110 歧義。  
11. **必要性/短命工**：無（各 Task「存活至」合理）。

---

## 必答 1 — Agent 可執行性

| Task | 判定 | 備註 |
|---|---|---|
| 1.0–4.3 | 可執行 | R8 寫回已逐條可落地 |
| 5.1 | **需擴 scope** | P1-01：`page.tsx` 接入不在白名單 |
| B1 Gate | 跟 §B 可；跟 L110 不可 | P2-01 |

---

## 必答 2 — 義務覆蓋

§A D1–D7／§G 1–4／§V 24／§C（含 A1-4）／§N 四殘留 — TODO 追溯表 L271–298 全對應。**漂移**：SPEC Task 5.1「接入結果頁」義務 vs §C 白名單缺 `page.tsx`（P1-01，SPEC 義務側 scope 未跟）。

---

## 必答 3 — 批次獨立性

B1–B4 獨立綠；B5 依 B4 `STAGE_OVERRIDE_PATHS`；Task 4.0 為 B4 首件；4.2 `persist_suppressed` 走 A1-1 無義務漂移。無 forward dependency 新問題。

---

## 必答 4 — 取巧面

| 區域 | 風險 |
|---|---|
| bench `n_regressions` | 低 — spy 對證 L236 |
| B5 vitest 只測元件 | 中 — 未測 page mount（P1-01 修 scope 後需 page 級 smoke 或文件化） |
| mutation 探针 | 低 — §B 路徑已明列 |

---

## 必答 5 — 測試設計

`test_mutation_*` 與 `--batch Bn` 對映完整（L55–242）；V-19 三欄參數化為刻意例外。無 falsification 缺口。

---

## 必答 6 — 可 Frozen？

**需修補後 Frozen**（一處 MAJOR scope 缺口阻 B5 端到端）。

**BLOCKING 清單**：
1. **COMPOSER-R9-P1-01** — B5 須把 `frontend/src/app/ic-analysis/page.tsx` 納入核准白名單並同步 TODO Task 5.1 修改檔案清單。

**非阻 Frozen（建議同步修）**：COMPOSER-R9-P2-01（L110 gate 字面）。

---

## Verdict：需修補後派工

R8 十群集 U1–U10 寫回 DRAFT R3 已逐條核對成立（U6 駁回碼證可重現）。本輪新增 1 MAJOR：B5 表格接入與 §0 白名單互斥（P1-01）。修 A1-4／TODO scope 後可 Frozen → B1。

---

ASSUMPTIONS_VERIFIED: template_check PASS；todo_spec_crosscheck SMOKE PASS；U6 grep 0 命中；U10 grep 四處 僅 L3；`_persist_outputs` 兩呼叫點 `:1142`／`:3432`；`_annotate_root_status_and_pass_class` 三呼叫點；page.tsx 無 MarginalICTable  
TESTS_RUN: `bash scripts/template_check.sh todo docs/GAP2_MARGINAL_IC_TODO.md` → PASS；`bash scripts/todo_spec_crosscheck.sh docs/GAP2_MARGINAL_IC_SPEC.md docs/GAP2_MARGINAL_IC_TODO.md` → SMOKE PASS；`grep -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` → 0（rc=1）；`grep -n '四處' docs/GAP2_MARGINAL_IC_TODO.md` → L3 only；`bash scripts/mutation_probe_check.sh` → rc=1（無參數）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（審查只讀）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: `handoffs/20260818-gap2-todoadv-r9-composer.md`  
TMP_CLEANUP: 已嘗清 `/private/tmp/agent_dc_snapshot.txt`、`/private/tmp/sessions`；`/private/tmp/claude-501` 保留  
STATUS: DONE
