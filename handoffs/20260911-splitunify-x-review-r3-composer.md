# SPLITUNIFY — SPEC/TODO v3 Adversarial Review R3（composer）

task-id: `20260911-SPLITUNIFY-X-REVIEW-R3`  
family: `COMPOSER`  
findings-round: `R3`（收斂輪）  
審查對象: `docs/SPLITUNIFY_SPEC.md`（sha256 `d851e56dc1bf…`）、`docs/SPLITUNIFY_TODO.md`（sha256 `a9ec9e1559a8…`），commit `7f040c93`

## 被當成事實的未驗證假設（§0）

| 宣稱 | 類型 | 核對結果 |
|---|---|---|
| R2 之 D1–D11 已全部落入 v3 | **fact-verified** | 逐條對照 brief 變更表與 v3 章節（見必答 1–7）；11 群集均有對應落點 |
| 刪 `n_train`/`n_test`/`n_purged` 會紅 `test_gap3_split_blocked.py` | **assumed（brief 自標）→ 否證** | 該檔 7 條測試**未斷言** summary 三鍵（`:72-79` 只查 `execution_mode`／`split_plan is None`／表產出） |
| `EventTablesPanel.test.tsx` 已存在 | **fact-verified 不存在** | `glob **/EventTablesPanel.test.tsx` → 0；v3 Task 3.3 驗收要求**新建**並跑 vitest——屬 B3 施工項，非 v3 自相矛盾 |
| `tables.py:598-599` 有 `estimand_note` 模式 | **否證** | `tables.py` 僅 372 行；`estimand_note` 實際在 `pipeline.py:598-599`（`evaluate_all_bars` 表）。v3 要加的是 `event_forward_return_table["common"]["estimand_scope"]`（新欄），引用行號錯但意圖與落點（`_common_constraint_block`）明確——**P3 文檔筆誤，不擋 B1** |
| 事件掃描 analyze 端仍走 `run_with_params` | **fact-verified（現碼）** | `case_import_service.py:1596-1613` 非 blocked 時仍 `run_with_params`；v3 C-0:77-80／TODO §0:37-38／Task 3.3:305 明寫**恆走** event-study-only，B3 須改 else 分支——規格已閉合，施工在 B3 |

## 必答 1–7（明確立場）

**1. 可否進 B1**  
**可以。** R2 三家一致「不可直接進 B1」之三個 P0（D1 未閉合、D2 Task 3.3 自相矛盾、D3 G-5 空殼）與八個 P1 均已落入 v3（brief 變更表逐條可對）。B1 僅文件／枚舉／紅基準（SPEC §P:270），不動生產碼；無未閉合之 P0/P1 阻擋本批。

**2. D1 裁定是否可接受（event-study-only + R-5）**  
**可接受，屬「95% 解法」而非偷偷降級。** 使用者主目標＝「同一次 UAT 不要看到兩個互相矛盾的驗證段數字」。裁定後：IC 端暴露 canonical `n_test`（C-6）；事件掃描端**不傳** universe（C-0:77-80）⇒ `capability.split=="unavailable"` + `reason`（Task 3.3），**刪除**假 `n_train/n_test/n_purged` 三鍵（C-0:86-88），表級 `estimand_scope="full_sample_not_oos"`（C-0:89-92）。使用者只會在 IC 報告看到「驗證段」；事件端明講「未執行切分」——符合離線授權之委員會定案。`R-5` 誠實標記跨棧 `features_run_id` 為 needs-research，非偷懶。

**3. D2 刪三鍵會不會打破既有測試／前端**  
**既有測試：不會紅 `test_gap3_split_blocked.py`。** 碼證：該檔未讀 `summary["n_test"]` 等鍵（`:72-79`）。**會需改的前端**：`EventTablesPanel.tsx:352` 今日硬渲 `s.n_train`/`s.n_test`/`s.n_purged`——v3 Task 3.3 要點 4 已列為修改檔並要求 vitest。**其他 caller**：`scripts/gap3_import_scale.py:97` 讀三鍵，但該腳本走 `pipeline.run()`（`:60` 有 `split_events`），非 `run_event_study_only`，刪鍵範圍僅 study-only 路徑，不影響此腳本。v3 已把 `test_splitunify_event_study_only.py` 兩 reason 回歸與前端 vitest 列入 Task 3.3 驗收。

**4. G-5 四項 oracle 夠不夠可執行**  
逐項：**夠。**  
① row fingerprint：SPEC §G:248-250 定義 canonical 序列化 + 首個 mismatch position；TODO Task 2.3:228-230 同型。  
② assignments/purged IDs：SPEC §G:251-254 獨立 oracle 集合 + diff event_id；TODO:231-233。  
③ answer-window：`label_start_ms`/`label_end_ms` 在 `label_value_from_case.py:155-156` 等處存在；SPEC §G:255-257 定義 endpoint 覆蓋 + purge 輸出 event_id。  
④ leakage negative：SPEC §G:258-260 合成 fixture + mutation rc=1；TODO:237-238。  
每項均有 nodeid 或 freeze 子模式要求（SPEC §G:261-262）。

**5. v3 有沒有引入新的自相矛盾（介面可執行性）**  
**R2 之 D7/D8 已閉合，未見新的 P0/P1 級矛盾。**  
- D7：`C-4:166-173` 明文禁 `_normalize_ic_time_index`（`ic_filter_orchestrator.py:269-271` 拒 ms）；改為 `pd.to_datetime(unit="ms")` 或 `asi8//10**6`。  
- D8：`bucket_ms` 已進 C-4 簽名（`:155`）；`EventSplitConfig.embargo_ms` 檢查移呼叫端（C-5:199-201）。  
- 殘留 P3：`tables.py:598-599` 行號引用錯（實為 `pipeline.py:598-599`）；Task 3.1 正文未重複列 embargo 檢查，但 C-5 + TODO Task 2.2:195-197 已指定落點——實作端讀全 SPEC 可執行。

**6. 批次拆分依賴鏈**  
**正確。** B2a（Task 2.1）產 `holdout_boundary` → B2b（Task 2.2）需其 row/ms 做投影 `derive_event_split_from_plans` + `build_time_clusters` → B2c（Task 2.3）需投影函式凍 G-1/G-3b/G-5 golden → B3（3.1–3.3）接線。Task 未放錯批；B3 三 Task 同批合理（brief：分開會有一段邊界不唯一）。

**7. 殘留清單是否誠實**  
**是。** `R-1`～`R-5` + `SU-RESID-1` 六條理由類別均為 blocked-by／user-ruling／needs-research（SPEC §N:589-606；TODO §E:382-391），且與現碼一致：`R-4`（`pattern_bridge` 無 caller）、`R-5`（`case_import_service` 不碰 FF run，`1588-1613`）、`SU-RESID-1`（attribution checker 只驗 ID 字串）。無「現在就能做卻標殘留」之偷懶項。

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對 R2 之 D1–D11 在 v3 的閉合情況、七道必答與 §1 十一類必查後，無未閉合之 P0/P1 finding；v3 可放行 B1。

**碼證**: `sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md` → `d851e56dc1bf…`／`a9ec9e1559a8…`；R2 P0 閉合點——D1 `SPEC.md:71-81`+`§N R-5`、D2 `SPEC.md:86-88`+Task 3.3:498-501、D3 `SPEC.md:246-262`+TODO:227-238；介面——`ic_filter_orchestrator.py:269-271`（ms 拒收）、C-4:149-157（`bucket_ms` 簽名）、C-5:199-201（embargo 呼叫端）；必答 3——`test_gap3_split_blocked.py` 無三鍵斷言、`EventTablesPanel.tsx:352` 已列 Task 3.3 修改範圍。RECHECK: `rg -n '恆走|event-study-only|estimand_scope|G-5|ms_same_source|split_events_production_call_count' docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md`

**來源摘要**: docs/SPLITUNIFY_SPEC.md#d851e56dc1bf, docs/SPLITUNIFY_TODO.md#a9ec9e1559a8

[NON-BLOCKING] 信心度=High。核對依據＝brief R2→v3 變更表 11 行逐條 grep＋必答 3/5 所列生產檔案:行號實讀；未發現會在 B1–B4 具體失敗且 v3 未覆蓋之缺口。殘留 P3：`tables.py:598-599` 行號筆誤（應指 `pipeline.py:598-599`），建議 v3.1 順手改正，**不擋 B1**。

---

## §1 必查摘要（無問題標「無」）

1. 矛盾/互斥：無（R2 D7/D8/D10 已修；`tables.py:598` 為行號筆誤 P3）。  
2. 漏項/端到端：無未閉合 P0/P1（event-study 揭露、前端 capability、紅清單協議均已寫入 Task 3.3／1.3）。  
3. 不可測驗收：G-5 已由空殼補為四項可執行 oracle（§G:246-262）。  
4. 可疑 quant 假設：D1 裁定已用 `estimand_scope` + 刪假鍵處理全樣本誤讀風險。  
5–11. 過度工程／OOM／cache／API／測試品質／Agent 可執行性／短命工：無新增 blocking。

## Verdict：可進 B1

v3 已閉合 R2 全部 P0/P1（D1–D9）；P2（D10/D11）亦已落入。B1（Task 1.1–1.3，不動生產碼）可開工；B2 前無需 R4。P3 殘留（`tables.py` 行號引用）建議隨 B1 文件批順手修正，不阻擋派工。

---

```
ASSUMPTIONS_VERIFIED: sha256 SPEC/TODO 與 brief 一致；`_normalize_ic_time_index` 拒 ms（ic_filter_orchestrator.py:269-271）；`run_event_study_only` 仍寫三鍵 0（pipeline.py:728-734）；`test_gap3_split_blocked.py` 不斷言三鍵；`EventTablesPanel.tsx:352` 仍渲三鍵；`case_import_service.py:1596-1613` 非 blocked 仍 `run_with_params`（B3 待改）
TESTS_RUN: sha256sum docs/SPLITUNIFY_SPEC.md docs/SPLITUNIFY_TODO.md → d851e56dc1bf…/a9ec9e1559a8…；glob EventTablesPanel.test.tsx → 0；rg 碼證見各必答；未跑 pytest 全套
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼）
NUMERIC_OR_SCHEMA_IMPACT: none（review only）
```

STATUS: DONE
