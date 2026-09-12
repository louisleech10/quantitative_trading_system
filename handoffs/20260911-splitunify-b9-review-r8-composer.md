# SPLITUNIFY D-002 閉合輪 R8 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R8  
family: composer  
findings-round: R8  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第八次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R7 十五條歸八群、全部採納 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md` 群集表 |
| brief fact-verified: golden `gap1`／`gap2` 在 `purged` | **fact-verified** | `venv/bin/python` 讀 `splitunify_golden.json` → `purged` 含 `gap1`,`gap2`,`tr_leak` |
| brief fact-verified: `alignment.py:87-93` 允許 `cutoff < decision` | **fact-verified** | `sed -n '87,93p' momentum/Analysis/event_samples/alignment.py` |
| brief fact-verified: `api/` 對 `EventSamplePipeline.run` 零呼叫點 | **fact-verified** | `rg 'EventSamplePipeline\(\)\.run' api momentum --glob '*.py'` 非測試 0 命中 |
| brief fact-verified: 第八次修訂 obligation／format rc=0 | **fact-verified** | `obligation_block_check.sh` rc=0；`doc_format_precheck.sh` rc=0 |
| brief assumed: §G (G-4a)「僅允許因換錨而改側」可機械驗證 | **assumption，本輪否證** | 見必答 2：無雙路徑 oracle／allowlist 閘 |
| brief assumed: `Task 9.1` 具名殘留不讓 9A 名存實亡 | **assumption，本輪否證** | 見必答 3：L135 仍要求終端可見；`metadata.split_unify` 生產寫入點無 `discarded` 來源 |
| brief assumed: 七條反向 mutation 能真的紅 | **assumption，本輪否證** | 見必答 4：`rg` 無 `誤改為複合鍵`／`byEventId` 防誤改測試；多數應紅測試尚未存在 |
| brief assumed: `dedupe` 廣播不改 `w=1/n` | **assumption，未實跑** | 規格 L195 要求新測試；repo 無「兩 TF 皆存活而簇仍一列」案例 |

## 必答 1–5（成對立場）

**1. 本家 R7 finding 是否閉合**

| ID | R7 斷言 | 第八次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R7-P1-01 | 9A IC 主線無 `discarded` 生產路徑 | L145–147 改為具名殘留＋只交 producer 三層 | **規格已改寫、問題未解** | `rg discarded_rows_by_feature_tf` 全 repo 0 命中；決策本身見 R8-P1-02／P1-03 |
| COMPOSER-R7-P1-02 | `Task 9.3` 與 (5.1) 甲類互斥 | L193 四處改「維持事件級 `.loc[eid]`」 | **CLOSED（規格）** | `sed -n '193p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R7-P1-03 | `dedupe` 保留集改複合鍵互斥 | L195 事件級保留＋`event_id` 廣播 | **CLOSED（規格）** | `sed -n '195p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R7-P2-01 | 9.2b 位置映射未定義 | L178–182 改時間域四段式 | **CLOSED（規格）** | `sed -n '178,182p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R7-P2-02 | `M-SU-D2-11` 與排除遷移互斥 | L237 改反向 mutation | **CLOSED（規格）** | mutation 表 `M-SU-D2-11` 行 |
| COMPOSER-R7-P2-03 | §V 9.1 仍指作廢三層 | L214 改 producer／summary／`metadata.split_unify` | **部分閉合** | §V 已改，但 `M-SU-D2-02`／`03` 仍指已延後的 API／前端（見 R8-P2-03） |

**2. 攻 §G (G-4a)**

**立場**：(G-4a) 在語意上正確（cutoff 判側才是缺陷），但「重凍一次、僅允許因換錨而改側」**不可機械驗證**，且會讓單 TF golden 對「改側」類缺陷失去鑑別力。

**碼證（換錨必改側）**：`venv/bin/python -c 'test_start=1000; decision=1000; cutoff=900; print({\"old\":\"train\",\"new\":\"test\"})'` → `old=train, new=test`（與 SPEC L128 一致）。

**碼證（無區分閘）**：§G L128 只要求「重凍前後差異須逐筆列出並在 commit 訊息說明」——這是**人工流程**，`freeze_splitunify_golden.py`／§V 無「允許差異 allowlist」或雙實作 diff 腳本。實作 bug 若把非邊界事件改側，與換錨改側在 `g1_membership` 輸出上**同型**（都是 `split_label` 變了），單次重凍後無第二條 oracle。

**具體反例**：假設 Task 9.2b 實作者誤把 `decision_at_ms <= train_last_ms` 寫成 `<`（少含等號）。事件 `e` 滿足 `decision_at_ms == train_last_ms == feature_cutoff_ms`（非 `decision != cutoff` 邊界 fixture 覆蓋不到）⇒ 舊路徑 train、新路徑 purged／test。重凍後 golden 只記錄新值，**無法**與「合法換錨」區分，除非保留舊 cutoff 路徑平行跑。

**替代（具體）**：① 重凍前用腳本對單 TF fixture **雙跑** cutoff 判側 vs decision 判側，產出 `allowed_side_diff_events.json`（僅 `decision_at_ms != feature_cutoff_ms` 且差異符合公式者）；CI 比對新實作只允許該集合改側。② 或保留 `g1_membership_cutoff_anchor` 平行鍵一個 Phase，新鍵為 decision-anchor，兩鍵 diff 必須等於 allowlist。③ 不採「重凍後單向 exact」作為唯一閘。

**3. 攻 `Task 9.1` 具名殘留**

**立場**：把終端可見性延後 + 理由類別 `blocked-by` **不成立**；Phase 9A「消除靜默丟棄之誠實性缺陷」對終端使用者**名存實亡**；且第三交付層 `metadata.split_unify` 在生產路徑上**走不通**。

**碼證（目標未收回）**：L135 仍寫「必須讓**終端使用者**看得到」，與 L145–147 殘留**同檔並存**。

**碼證（零生產接線）**：`rg 'EventSamplePipeline\(\)\.run' api momentum --glob '*.py'` 非測試 0；`discarded_rows_by_feature_tf` 全 repo **0 實作**。

**碼證（`metadata.split_unify` 第三層矛盾）**：L146 要求擴充 `metadata.split_unify`；生產唯一寫入點 `ic_filter_orchestrator.py:1530-1534` 呼叫 `build_split_unify_disclosure(n_test=...)`，該函式 `split_projection.py:175-177` 回傳鍵僅 `n_test`／`split_authority`／`boundary_hash`／`per_symbol_counts`／`reason`，**無** `discarded` 欄位，且上游未呼叫 `build_event_keys`。⇒ §V L214 之 `ASSERT metadata.split_unify 帶該鍵` 在生產 IC 路徑**不可達**；實作者只能寫 unit test 對 `build_split_unify_disclosure` 手塞鍵，與「資料流契約」不符。

**`blocked-by` 是否正確**：**否**。`blocked-by` 須指名**已登記之阻塞票**（類比 §N `R-4` 屬 GAP-3）。L147 碼證僅「零呼叫點」＝**能力缺口**／**未接線**，不是被另一張已存在票擋住；較接近 `needs-research`（生產投影接線設計未定）或應開獨立「projection wiring」Task。且 L147 寫「登記於 §N」，但 §N L258–265 **無**終端可見性殘留條目——殘留未入權威登記處。

**4. 七條反向 mutation 是否真能紅**

| ID | 誤改內容 | SPEC 應紅測試 | 現有測試面 | 能否紅 |
|----|----------|---------------|------------|--------|
| `M-SU-D2-04` | 物化改每 TF 一列 | Task 9.3 多 TF 合併一列＋`:138-140` 記帳 | `test_return_table_by_label.py` 等為單事件／未覆蓋多 TF 合併值 | **實作測試前不紅**；加多 TF fixture 後可紅（`AssertionError` 於 `:138-140`） |
| `M-SU-D2-06` | `tables` 改複合鍵 lookup | 事件級 lookup 值斷言 | `test_return_table_by_label.py` 走 `event_forward_return_table` 但未斷言「誤改複合鍵」 | **不紅**（無專項） |
| `M-SU-D2-07` | `ic_feed` 改複合鍵 `set_index` | 逐列值斷言 | `test_gap3_attached_columns_contract.py` 驗欄位洩漏，非索引形狀 | **不紅** |
| `M-SU-D2-08` | `counterexample_classifier` 改複合鍵 | 分類結果綁定 | `test_mutation_guard.py` 測 offset，非複合鍵 | **不紅** |
| `M-SU-D2-09` | `candidate_ledger` 改複合鍵 | 帳本列綁定 | `test_candidate_ledger.py` 測 return series，非 `.loc[eid]` | **不紅** |
| `M-SU-D2-10` | `dedupe` 保留集改複合鍵 | 兩 TF 存活簇仍一列 | `test_dedupe.py` 僅事件級 `cluster_first` | **不紅**（廣播測試未寫） |
| `M-SU-D2-11` | `byEventId` 改複合鍵 | 匯出 extras 值 | `tests/frontend` 中 `rg byEventId\|composite` → **0 檔** | **不紅** |

**結論**：七條反向 mutation 在 SPEC 層已對齊，但 **6/7 條現行測試面抓不到**；僅 `M-SU-D2-04` 在補齊多 TF 物化測試後**有明確紅路徑**（記帳 `AssertionError`）。Task 9.3 L193 寫「加防誤改回歸測試」但 §V L221 僅泛稱「逐處各一條」，**未派工到檔名** ⇒ Agent 可跳過仍過 mutation 表形式檢查。

**5. J1–J8 修訂引入的新問題**

| 群 | 複驗 | 新問題 |
|----|------|--------|
| J1 Task 9.3 同步 | L192–197 已對位 (5.1) | 無 |
| J2 dedupe 廣播 | L195 已寫 | 廣播後 `w=1/n` 未派測試（brief assumed 未驗） |
| J3 Task 9.1 殘留 | L145–147 | 9A 目標／§N 登記／`metadata` 路徑三重矛盾（R8-P1-02／P1-03） |
| J4 時間域映射 | L178–182 | 無 |
| J5 §G (G-4) | L128 (G-4a) | 機械不可驗（R8-P1-01） |
| J6 baseline `n_test` | L205 改事件數 | 與 `D-002-C6` (6.2) L92「baseline 為樣本數」**未同步改寫**（R8-P2-02） |
| J7 `M-SU-D2-11` 反向 | L237 | 無應紅測試（必答 4） |
| J8 §V 9.1 | L214 | `M-SU-D2-02`／`03` 孤兒（R8-P2-03） |

與 D-001／golden：**無新 schema 衝突**；G-4a 重凍將改 `g1_membership` 邊界事件側別（預期內）。

## §1 必查摘要（11 類）

1. **矛盾**：Task 9.1 L135 vs L145–147；C6 L92 vs Task 9.4 L205；§V L214 vs `build_split_unify_disclosure` 實際鍵集——**有**
2. **漏項**：§N 未登記 9.1 終端殘留；Task 9.3 防誤改測試無檔名派工——**有**
3. **不可測**：G-4a 僅人工列差異；七反向 mutation 多數無測試——**有**
4. **quant 假設**：G-4a 重凍後邊界改側缺陷與換錨不可分——**有**
5–11. 其餘——**無新增**（除上述）

## COMPOSER-R8-P1-01

**斷言**: §G (G-4a) 要求單 TF golden 於 Task 9.2b 後重凍且「僅允許因換錨而改側」，但規格未提供機械 allowlist／雙路徑 diff，重凍後**無法區分**合法換錨與實作寫錯导致的改側，回歸錨對改側類缺陷失效。

**碼證**: SPEC L127–128 (G-4a)；`alignment.py:87-93`；PROBE `test_start=1000, decision=1000, cutoff=900` → old train／new test；`freeze_splitunify_golden.py` 無 side-diff allowlist 輸出。RECHECK: 雙跑 cutoff vs decision 判側，比對 diff 集合是否等於 `{e | decision_at_ms != feature_cutoff_ms}` 之理論集合。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/alignment.py#0da3c48b2668;scripts/freeze_splitunify_golden.py#e331623163d2

[BLOCKING] 信心度=High。Task 9.2b 實作後若邊界公式 off-by-one，重凍會把錯側**固化進 golden**；後續 mutation 22（判側改回 cutoff）也可能被「已重凍」掩蓋。**修法**：採必答 2 替代①或②——CI 必備 `allowed_side_diff_events.json` 或 cutoff-anchor 平行鍵；§G 刪「僅允許一種差異」之空稱，改為可執行斷言。

## COMPOSER-R8-P1-02

**斷言**: `Task 9.1` v8 具名殘留使 Phase 9A 對終端使用者**零揭露**，且第三交付層「`metadata.split_unify` 承載 `discarded_rows_by_feature_tf`」在生產 IC 路徑上**不可達**——與 L135 目標及 §V L214 互斥。

**碼證**: L135「終端使用者看得到」；L145–147 殘留；`ic_filter_orchestrator.py:1530-1534` 僅 `build_split_unify_disclosure(n_test=...)`；`split_projection.py:175-177` 回傳無 discarded；`rg discarded_rows_by_feature_tf` → 0。RECHECK: 對讀 L135／L146／L214 與上述三處。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/ic_filter_orchestrator.py#9a3e94399293;momentum/Analysis/event_samples/split_projection.py#55ca7327764f

[BLOCKING] 信心度=High。9A 交付後使用者仍完全看不到丟棄列；實作者對 `metadata.split_unify` 寫契約測試卻無生產資料流 ⇒ 假綠。**修法**：① 收回 L135「終端可見」或降級 Phase 9A 為「producer-only」並改 Phase 名；② 刪 §V 對 `metadata.split_unify` 之 discarded 斷言，改為僅 `EventSplitPlan.summary`；③ 或先開「projection wiring」Task 再接 9A 終端層。

## COMPOSER-R8-P1-03

**斷言**: `Task 9.1` 將終端可見性標為 `blocked-by` 並稱「登記於 §N」，但 §N **無對應殘留條目**，且零 `EventSamplePipeline.run` 呼叫點屬能力缺口而非被具名票阻塞——殘留分類與治理登記皆不成立。

**碼證**: L147「理由類別 `blocked-by`…登記於 §N」；§N L258–265 僅列 `SU-RESID-2`／`D1`／`R-3`／`R-4` 等，**無** 9.1 終端揭露；`api/` 無 `.run(` 生產呼叫（`case_import_service.py:1605` 僅註解提及）。RECHECK: `sed -n '147p;258,265p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;api/services/case_import_service.py#55ca7327764f

[BLOCKING] 信心度=High。治理模板 §2 要求殘留須在 §N 具名且理由成立；缺失會讓 R-5／D1 與本殘留混淆，後續無觸發條件可追。**修法**：§N 新增條目（例 `SU-RESID-9A-UI`，`blocked-by: <projection-wiring Task ID>` 或改 `needs-research`）；若堅持 `blocked-by` 須指名阻塞票號而非「零 grep」。

## COMPOSER-R8-P2-01

**斷言**: `M-SU-D2-04`／`06`–`11` 七條反向 mutation 中，**六條**在現行測試面下誤改為複合鍵**不會紅**——Task 9.3 只寫「加防誤改回歸測試」未派工到具名檔案，mutation 目錄形同空殼。

**碼證**: mutation 表 L230–237；`rg '誤改為複合鍵|byEventId.*composite' tests/` → 0；`test_dedupe.py` 無廣播案例；`tests/frontend` 無 `byEventId` 複合鍵匯出測試。RECHECK: 對七 ID 逐條 grep 應紅測試名稱。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c

[MAJOR] 信心度=High。實作者照 (5.1) 甲類維持 event-level，mutation 06–11 永不觸發 ⇒ mutation 自證失敗或被迫假綠。**修法**：§V Task 9.3 增具名 pytest 路徑（例 `tests/momentum/event_samples/test_splitunify_event_level_guards.py`）覆蓋七條；或暫標 `needs-research` 直至測試存在。

## COMPOSER-R8-P2-02

**斷言**: J6 將 `baseline` 之 `n_test` 更正為事件數（L205），但 `D-002-C6` (6.2) L92 仍寫 baseline 之 `n_test` 為「實際模型輸入樣本數（複合鍵列數）」——同檔兩處量詞**未同步**，實作者不知以哪條為準。

**碼證**: L92 vs L205；`baseline.py:118-121` `n_test = len(idx)` 隨 `features_at_decision` 索引（事件級物化下 `len(idx)`＝事件數）。RECHECK: `sed -n '92p;205p' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[MAJOR] 信心度=High。Task 9.4 驗收與 C6 義務衝突時，Agent 可能改 `n_test` 語意卻通過錯誤斷言。**修法**：修 (6.2) L92——在事件級物化前提下 baseline 樣本數＝事件數，刪除「複合鍵列數」例外句；或保留例外但明寫「僅適用 per-TF adapter 未來票」。

## COMPOSER-R8-P2-03

**斷言**: `M-SU-D2-02`／`03` 仍要求 API 回應／前端揭露契約測試，但 v8 已將終端可見性具名殘留且 §V L214 作廢該兩層——mutation 與殘留決策**互斥**，實作者無合法應紅測試可寫。

**碼證**: mutation L228–229；§V L214「v7 之 API 回應／前端型別兩層作廢」；L147 終端殘留。RECHECK: 對讀三處。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#a2ac7731fd7c

[MAJOR] 信心度=High。mutation 自證時 02／03 永遠灰態（寫測試違殘留、不寫測試違 mutation）。**修法**：刪除或改為 `DEGRADE` 直至接線；或將應紅測試改指 `EventSplitPlan.summary` 鍵（與 01 合併）。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -o 'M-SU-D2-[0-9]{2}' docs/SPLITUNIFY_SPEC.D-002.md \| sort -u \| wc -l` | **26** |
| `rg 'EventSamplePipeline\(\)\.run' api momentum --glob '*.py' \| rg -v test` | **0** |
| `rg 'discarded_rows_by_feature_tf' .` | **0** |
| golden purged keys | **gap1, gap2, tr_leak** |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R8-P1-01,COMPOSER-R8-P1-02,COMPOSER-R8-P1-03
CLOSED: COMPOSER-R7-P1-02,COMPOSER-R7-P1-03,COMPOSER-R7-P2-01,COMPOSER-R7-P2-02

ASSUMPTIONS_VERIFIED: R7 八群落點逐條對讀第八次修訂；G-4 探針；零 run 呼叫點；golden gap；build_split_unify_disclosure 鍵集；七 mutation 測試面 grep  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r8-composer.md --family composer`（交件前自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
