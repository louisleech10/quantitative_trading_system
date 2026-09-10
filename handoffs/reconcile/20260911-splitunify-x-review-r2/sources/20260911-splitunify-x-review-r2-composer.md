# SPLITUNIFY — SPEC/TODO v2 Adversarial Review R2（composer）

task-id: `20260911-SPLITUNIFY-X-REVIEW-R2`  
family: `COMPOSER`  
findings-round: `R2`  
審查對象: `docs/SPLITUNIFY_SPEC.md`（sha256 `84ab732b021b…`）、`docs/SPLITUNIFY_TODO.md`（sha256 `7d6d4f0c4e90…`）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| 「無 universe ⇒ event-study-only 不會讓 `event_forward_return_table` 失去 OOS 意義」 | **assumed（brief 自標）** | **否證**：`tables.py:211-238` 在 `event_split_plan=None` 時仍對**全 manifest 事件**算報酬；僅 `ci=="unavailable"`（`:251`）與 `formal_pooled_inference_allowed=False`（`:138`），**無 test 段過濾**——與 `binary_discrimination_table`（`:305` 只取 test）不一致。v2 Task 3.3 未寫此揭露義務。 |
| 「Task 1.3 紅清單 B1→B3 不會變」 | **assumed（brief 自標）** | **未跑 REDSWEEP**；v2 Task 1.3 邊界②已承認變綠會紅，但**未指定**誰在 B2 期間更新清單 ⇒ 施工風險成立。 |
| 「`holdout_boundary` 之 ms 邊界不算第二份算術」 | **fact-verified** | Task 2.1 明寫包 `holdout_split_point`＋`holdout_test_row_index`；ms 為 `feature_index[row]` 投影，非重算切點。`M-SU-11` 可擋「不呼叫既有兩支」。 |
| 「R1 C1–C13 已全部落入 v2」 | **fact-verified（逐條）** | 見必答 7；殘留一處 SPEC/TODO 驗收不一致（C7 釘選測試）。 |

## 必答 1–8（明確立場）

**1. C-0 落點與事件掃描端是否永遠 event-study-only？**  
**是（現況＋v2 設計皆指向此結論）。** 碼證：`case_import_service.py:1610` 只呼叫 `run_with_params`（不帶 `feature_config`）；`pipeline.py:654-657` `_materialize` 在 `feature_config is None` 回 `None`；`run_with_params`（`:512-516`）不暴露 universe 參數。**v2 已寫清** C-0 決議③與 Task 3.3。  
**但 v2 未寫清下游表語意**：`event_forward_return_table`（`tables.py:157-281`）在 `split_plan=None` 時對**全樣本**算均值報酬（`:211-238`），**不是** OOS test 段；`binary_discrimination_table`（`:305`）才只取 test。Task 3.3 只禁 `summary` 的 `n_test` 鍵，**未要求**表級 `capability`／`oos_scope` 揭露 ⇒ 使用者仍可能把全樣本報酬當驗證段。見 `COMPOSER-R2-P1-01`。

**2. Task 2.1 `holdout_boundary` 是否引入第二份算術？**  
**否（在現行 Task 2.1 契約下可接受）。** ms 邊界是既有 row index 在 `feature_index` 上的**投影**，切點仍由 `holdout_split_point`／`holdout_test_row_index` 唯一決定（SPEC Task 2.1 要點 1-2；`split_preview.py:19-46`）。`M-SU-11`（「不呼叫既有兩支」）能擋自寫公式，**不能**擋「多回傳 ms」——但 ms 與 row index 同源，不算第二套切分邏輯。建議 Task 2.1 docstring 明寫 `train_end_ms = feature_index[split_point-1]` 之投影關係（非 blocking）。

**3. C-5 `degraded.single_symbol` 在投影路徑是否誤導？**  
**否（在 Task 3.2 fail-closed 前提下語意自洽）。** Task 3.2 令多 symbol 批 raise，投影成功路徑 `n_symbols` 恆 ≤1 ⇒ `single_symbol` 恆亮是**正確揭露**（exploratory、禁 formal pooled inference），與 `_degraded_flags`（`event_split.py:21-30`）設計一致。多 symbol 批拿不到 plan，不會產出誤導 summary。

**4. Task 3.3 reason 與 `lookahead_split_blocked` 前端能否區分？**  
**v2 寫得不足。** SPEC Task 3.3 邊界①承認兩條 unavailable 並存、reason 不同；`split_unify.json` 會列 `canonical_feature_universe_unavailable`。但 Task 4.1／前端驗收只測 IC 端 `split_authority`，**未要求**事件掃描頁對兩種 reason 做可區分文案；`types.ts:3190` 僅 `reason?: string`。見 `COMPOSER-R2-P1-02`。

**5. Task 1.3 B1 凍結、B3 驗收集合相等——時序陷阱？**  
**是會卡住施工的 fail-closed 特性，但缺操作判準。** v2 Task 1.3 邊界②已寫「變綠必移出」，卻未指定：① B2 期間若 `REDSWEEP` 修好一條，誰在何時更新 `analysis_known_failures.nodeids`；② B3 gate 紅時是停批還是允許「先更新清單再過 gate」。**判準建議**：B3 驗收 B 紅 ⇒ 必須在同一 commit 更新 nodeid 清單（只准變短）並附 receipt diff；B2 期間禁止無人負責的靜默修紅。見 `COMPOSER-R2-P1-03`。

**6. §G G-5 四項是否可執行？**  
**否——目前為空殼。** 四項僅列名（SPEC `:218-219`、Task 2.3 `:190-191`），無逐項 oracle／輸入／通過條件。建議具體化（見 `COMPOSER-R2-P0-01` 正文）。

**7. R1 C1–C13 是否漏項或降級？**  
**基本全數採納；一處 SPEC↔TODO 驗收漂移（C7）。**

| 群集 | v2 落點 | 狀態 |
|---|---|---|
| C1 戳記 | consult D1–D8 戳記 rc=0（brief fact-verified） | ✅ |
| C2 簽名 feature_index | C-4、Task 2.2 | ✅ |
| C3 紅清單 deselect | Task 1.3、Task 3.1 驗收 A/B | ✅ |
| C4 未匹配⇒purged | C-4、Task 2.2 邊界② | ✅ |
| C5 clusters/summary | C-5、Task 2.2、`build_time_clusters` | ✅ |
| C6 G-3a/G-3b | §G、Task 2.3 | ✅ |
| C7 消費者／split_events 退出 | Task 3.1 要點 3；**TODO 有釘選測試、SPEC 驗收段缺** | ⚠️ 見 `COMPOSER-R2-P2-01` |
| C8 mutation 12 條 | §D / TODO §D | ✅ |
| C9 D-002 post-trim | Task 1.1 | ✅ |
| C10 C-0 boundary builder | C-0、Task 2.1/3.3 | ✅ |
| C11 三態兩容器 | C-3、Task 1.2 禁 assignment_states | ✅ |
| C12 embargo None | C-5、Task 2.2 要點 7 | ✅ |
| C13 §A2 兩 endpoint | §A2 | ✅ |
| consult D8 數值必變 | C-9 | ✅ |

**8. B2 三 Task 是否應拆批？**  
**不拆。** 2.1→2.2→2.3 為同一因果鏈（boundary→投影→golden／G-3b oracle 依前兩者）；拆出 2.3 會讓 golden 在無投影函式時無法凍結。規模「大」合理；依賴 B1 完成後**整批 B2 一次 review** 即可。若資源緊，可並行寫測試 stub，但**驗收 gate 不應拆成兩個綠燈**。

---

## COMPOSER-R2-P0-01

**斷言**: §G G-5「containment 四項 golden」與 Task 2.3 實作要點僅列四個名稱，未給任一項的獨立 oracle、fixture 來源或可執行比對命令，屬 §2 獵空殼之 BLOCKING 空殼；C-1 附帶約束②要求 §G golden 四項，但 G-5 目前不可證偽。

**碼證**: `docs/SPLITUNIFY_SPEC.md:218-219`（「逐 row test fingerprint、逐 event assignments/purged IDs、answer-window 完整性、leakage negative case」——無算法）；`docs/SPLITUNIFY_SPEC.md:340-355` Task 2.3 要點 4 同樣只複述名稱；`docs/SPLITUNIFY_TODO.md:190-191` 同型。RECHECK: `rg -n 'G-5|test fingerprint|leakage negative' docs/SPLITUNIFY_SPEC.md` → 僅標題級提及，無 `freeze_splitunify_golden.py` 子命令或 pytest nodeid。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[BLOCKING] 信心度=High。Agent 實作 Task 2.3 時只能自創 oracle，與 C-1「containment 未證明」目標背離。修法（逐項補進 Task 2.3，示例）：  
① **row test fingerprint**：`sha256(json.dumps(sorted(feature_index[test_plan.row_index].asi8//10**6)))` 與 IC orchestrator 同批輸出逐值相等；  
② **event assignments/purged IDs**：`set(assignments.event_id)`／`set(purged.event_id)` 與 G-3b oracle 集合相等（整數集合 `==`）；  
③ **answer-window 完整性**：對每個 test 事件 assert `label_end_ms <= train_end_ms` 或 purged reason=`interval_crosses_split_boundary`（沿用 `event_split.py:114-115` 語意）；  
④ **leakage negative case**：合成 fixture 一筆 train 事件其 `label_end_ms` 跨入 test 區 ⇒ 必進 `purged`，不得留在 `assignments`。每項須有對應 `tests/momentum/Analysis/test_splitunify_golden.py -k <name>` 或 freeze 腳本子模式。

---

## COMPOSER-R2-P1-01

**斷言**: v2 雖在 C-0／Task 3.3 禁止事件掃描端宣稱 OOS，但未規定 `event_forward_return_table` 在 `split_plan=None`（event-study-only）時的全樣本語意與必要揭露，與 brief 所質疑之「全樣本被誤讀為 OOS」風險仍成立。

**碼證**: `momentum/Analysis/event_samples/tables.py:166-172`（`split_plan=None` 合法）；`:211-238` 迴圈**全 manifest 事件**、無 `split_label=="test"` 過濾；`:251` 僅 `ci="unavailable"`；對照 `binary_discrimination_table:305` 只取 test。`pipeline.py:728-733` `run_event_study_only` 仍寫 `n_test:0`（v2 Task 3.3 要求移除這些鍵）。`case_import_service.py:1614-1615` 現況仍走 `run_with_params`（有切分）而非 Task 3.3 目標路徑。RECHECK: `rg -n 'event_forward_return|oos_only|formal_pooled' docs/SPLITUNIFY_SPEC.md` → 無 Task 3.3 表級契約。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MAJOR] 信心度=High。失敗模式：B3 後 summary 無 `n_test`，但 `tables.event_forward_return_table` 仍展示全批報酬均值，前端無「非 OOS」標籤（`test_gap3_split_blocked.py:101-107` 只驗「表能產出」）。修法：Task 3.3 增④——`event_forward_return_table` 須含 `common.estimand_scope="full_sample_not_oos"`（或 `capability.split=="unavailable"` 鏡像）；`test_splitunify_event_study_only.py` 斷言該欄位；可選在表 title 沿用 `tables.py:598-599` 之 `estimand_note` 模式。

---

## COMPOSER-R2-P1-02

**斷言**: Task 3.3 新增 `canonical_feature_universe_unavailable` 與既有 `lookahead_split_blocked`（`case_import_service.py:1591-1594`）並存，但 v2 未要求前端對兩種 `capability.reason` 做可區分揭露，實作端只能共用「split unavailable」泛稱。

**碼證**: `case_import_service.py:1618-1620` capability 形態；`pipeline.py:204-208` `split_blocked_capability_reason()` 與 Task 3.3 新 reason 字面不同；`frontend/src/lib/types.ts:3189-3190` `reason?: string` 無枚舉；Task 4.1 驗收（SPEC `:446-448`）未含事件掃描頁 reason 分支；`EventBatchDisclosurePanel.tsx:668-670` 僅顯示 `scanResult.reason` 原文。RECHECK: `rg 'canonical_feature_universe' frontend/` → 0。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=Medium。失敗模式：使用者見「切分不可用」無法分辨「深度宣告封鎖」vs「缺 feature universe（本票新路徑）」——支援與 UAT 難以對症。修法：Task 3.3 增前端驗收——`vitest` 對兩種 reason mock payload 斷言不同文案；或 D-002 增 UX 對照表映射 `split_unify.json` fail_closed_reasons。

---

## COMPOSER-R2-P1-03

**斷言**: Task 1.3 之「B1 凍結、B3 集合相等」在 B2 期間若既有紅被 `REDSWEEP` 修復會必然紅 gate，但 v2 未給「誰、何時、如何」更新 nodeid 清單的操作判準，會卡住施工而非僅提醒。

**碼證**: `docs/SPLITUNIFY_SPEC.md:279-280` 邊界②「變綠必移出」；Task 3.1 驗收 B（`:377-387`）集合不等即 rc=1；`HANDOFF.md:45-48` 建議 `REDSWEEP` 另票。無「B2 期間紅清單變動」流程。RECHECK: `rg 'REDSWEEP|主動移出' docs/SPLITUNIFY_TODO.md`。

**來源摘要**: docs/SPLITUNIFY_TODO.md#7d6d4f0c4e90

[MAJOR] 信心度=High。這是**刻意的 fail-closed**（優於聚合假綠），但缺 procedure = Agent 不知該停批還是順手改清單。修法：Task 1.3 增「維護協議」——B3 驗收 B 紅時允許同一 PR 更新 `analysis_known_failures.nodeids`（只准變短）+ `splitunify-analysis-baseline.stdout`；B2 內 `REDSWEEP` 修紅須在 commit message 標 `splitunify-baseline-sync` 並重跑 Task 1.3 命令。

---

## COMPOSER-R2-P2-01

**斷言**: R1 C7 要求生產路徑對 `split_events` 呼叫次數釘 0，TODO Task 3.1 驗收已寫「釘選測試」，但 SPEC Task 3.1 驗收三條命令未包含該斷言，SPEC↔TODO 不一致會讓實作端只跟 SPEC 而漏釘。

**碼證**: `docs/SPLITUNIFY_TODO.md:225`「另加：釘選測試斷言…呼叫次數 == 0」；`docs/SPLITUNIFY_SPEC.md:376-389` 驗收 (A)(B)(C) 無此項；R1 synth C7 採納「測試釘呼叫點＝0」。RECHECK: `diff` 兩檔 Task 3.1 驗收段。

**來源摘要**: docs/SPLITUNIFY_SPEC.md#84ab732b021b

[MINOR] 信心度=High。修法：SPEC Task 3.1 驗收增 (D) `pytest -k split_events_production_call_count`（或 spy 測試 nodeid）rc=0，與 TODO 對齊。

---

## §1 必查摘要（無問題標「無」）

1. 矛盾/互斥：SPEC↔TODO Task 3.1 驗收（見 P2-01）；其餘無。  
2. 漏項/端到端：event-study 表語意（P1-01）、前端 reason（P1-02）。  
3. 不可測驗收：G-5 空殼（P0-01）。  
4. 可疑 quant 假設：全樣本報酬當 OOS（P1-01）。  
5–11. 過度工程／OOM／cache／API／測試品質／Agent 可執行性／短命工：無新增 blocking（B2 規模已評估，見必答 8）。

## Verdict：需修補後派工

v2 已落實 R1 十三群集與 consult D6–D8 之主體；**B1 可進**（文件／枚舉／紅基準，不動生產碼）。**B2 開工前**須補 G-5 四項 oracle（P0-01）與 Task 3.3 表級非 OOS 揭露（P1-01）；P1-02／P1-03／P2-01 建議同批合入 v2.1 以免施工摩擦。

---

```
ASSUMPTIONS_VERIFIED: holdout_boundary 包既有兩函式（split_preview.py:19-46）；事件端無 universe（pipeline.py:654-657, case_import_service.py:1610）；event_forward_return_table 全樣本路徑（tables.py:211-238）；sha256 SPEC/TODO 與 brief 一致
TESTS_RUN: sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md → 84ab732b…/7d6d4f0c…；rg 碼證見各 finding；未跑 pytest 全套
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼）
NUMERIC_OR_SCHEMA_IMPACT: none（review only）；建議修補將影響 Task 2.3 golden schema 與 Task 3.3 API 揭露欄位
```

STATUS: DONE
