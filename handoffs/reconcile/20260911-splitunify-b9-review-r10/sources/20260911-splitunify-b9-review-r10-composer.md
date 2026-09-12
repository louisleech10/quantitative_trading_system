# SPLITUNIFY D-002 閉合輪 R10 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R10  
family: composer  
findings-round: R10  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第十次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R9 二十一條歸十一群 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r9/synth.md` |
| brief fact-verified: golden fixture 全部 `decision==cutoff` | **fact-verified** | `sed -n '117p' scripts/freeze_splitunify_golden.py` |
| brief fact-verified: mutation 表列 31、ID 連續 | **fact-verified** | `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → **31** |
| brief fact-verified: obligation／format rc=0 | **fact-verified** | `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → **rc=0** |
| brief assumed: 第十次修訂十一項皆落在該落點 | **assumption，部分否證** | L7／L8 仍「Task 有、§V／義務塊無」——見必答 2／P1-01／P1-02 |
| brief assumed: (G-4e) 三份判準不會三份同錯 | **assumption，部分否證** | 探針：三份皆 cutoff 錯時 `g3b=True g4e=True`（必答 3） |
| brief assumed: baseline 雙量後下游不混用 | **assumption，部分否證** | `D-002-C6`(6.2) 仍寫恆等、§V 無雙量 ASSERT（必答 4） |
| brief assumed: Step 0 後三段式互斥窮盡 | **assumption，SPEC 層成立** | 步驟 0 ＋ `train_last_ms < test_start_ms` 不變量 ⇒ 邏輯 MECE（必答 4） |

## 必答 1–5（成對立場）

**1. 本家 R9 finding 是否閉合**

| ID | R9 斷言 | 第十次修訂落點 | 判定 | 確認方式 |
|----|---------|----------------|------|----------|
| COMPOSER-R9-P1-01 | G-4c 不擋兩邊同錯 | (G-4e) §G L129、§V #3、M-28 | **CLOSED** | 對讀 §G／§V；探針見必答 3 |
| COMPOSER-R9-P1-02 | G-4d 未進 §V | §V L224-229 五條、M-27–29 | **CLOSED** | `sed -n '224,230p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R9-P1-03 | L127 一刀切互斥 | L127 v10 允許集合除外 | **CLOSED** | `sed -n '127p' docs/SPLITUNIFY_SPEC.D-002.md` |
| COMPOSER-R9-P1-04 | K4 二擇一未決 | L151 鎖三層、刪逃逸句（沿革外無「若成本超出」） | **CLOSED** | `rg '若成本超出' docs/SPLITUNIFY_SPEC.D-002.md` 僅命中沿革 |
| COMPOSER-R9-P2-01 | K3 引錯 brief 範本 | §N L281 改引 `SPEC_TEMPLATE.md:107-112`＋`為何現在不做:` | **CLOSED** | 對讀 §N；`rg BRIEF_REVIEW_TEMPLATE` 僅沿革 |
| COMPOSER-R9-P2-02 | L137 仍要終端可見 | L138 改交付 producer 層 | **CLOSED** | `rg '終端使用者看得到' docs/SPLITUNIFY_SPEC.D-002.md` → 0（正文） |
| COMPOSER-R9-P2-03 | SU-RESID 無 owner | `docs/SPLITUNIFY_TODO.md` §E L471 登記＋recheck | **CLOSED** | 對讀 TODO §E |
| COMPOSER-R9-P2-04 | §V 缺 early／late | §V L228-229 兩條 ASSERT | **CLOSED** | `sed -n '228,229p' docs/SPLITUNIFY_SPEC.D-002.md` |

**2. 檢驗主委自證步驟（十一群逐項）**

| 群 | 宣稱落點 | 複驗 | 主委漏掉 |
|----|----------|------|----------|
| L1 (G-4e) | §G L129、§V #3、M-28 | **落在** | — |
| L2 (G-4d)＋L11 | §V L224-229、M-27–29 | **落在** | — |
| L3 目標句 | L138 | **落在** | — |
| L4 K3 | §N L281 `SPEC_TEMPLATE`＋強制欄 | **落在** | — |
| L5 三層 | L151 鎖三層 | **落在** | — |
| L6 L127 | L127 | **落在** | — |
| L7 handoff | Task 9.1 L150 整鏈 | **Task 有、§V 無** | §V L220 仍分層斷言，無 producer→summary→metadata 整鏈（→P1-02） |
| L8 baseline 雙量 | Task 9.4 L211、M-31 | **Task 有、義務塊／§V 矛盾或缺失** | `D-002-C6`(6.2) L92 仍寫恆等（→P1-01）；§V 無 Task 9.4 斷言（→P2-01） |
| L9 Step 0 pair | Task 9.2b L184、§V L230 | **落在** | — |
| L10 TODO §E | `SPLITUNIFY_TODO.md` L471 | **落在** | — |
| mutation 31 條 | 表列 31、正文宣稱 31 | **落在** | — |

**3. 攻 (G-4e)：三份判準如何避免三份同錯？**

**立場**：**(G-4e) 相對 (G-4c) 有效，但非數學上不可攻破**——第三份判準若與投影／oracle **同一次改動 copy-paste 同一錯誤語意**，三者仍全綠。

**碼證（獨立實作時可抓）**：`decision=250,cutoff=200,train_last=200,test_start=300`；正解 `purged`。投影／oracle 皆 cutoff 判側 ⇒ `train`；若 `expected_side` **正確**用 decision-anchor ⇒ `g3b_pass=True` 且 `g4e_pass=False`（`python3` 探針 stdout：`proj=train oracle=train expected=purged g3b_pass=True g4e_pass=False`）。

**碼證（三份同錯）**：`expected_side` 亦 copy cutoff 邏輯 ⇒ `g3b_pass=True g4e_pass=True`（stdout：`triple_same_error: proj=train oracle=train expected=train g3b=True g4e=True correct=purged`）。

**誠實標註建議**：§G (G-4e) 應明寫——第三份判準須**獨立**依 `Task 9.2b` 三段式（decision-anchor）實作，**禁止**與 `_oracle_membership` 共用實作或同 PR 機械複製；並以 (G-4d)③ 之 `decision!=cutoff` fixture 提供手算期望向量（目前 §V L225-226 已標空心風險，但未把「三份同錯」列為殘餘誠實邊界）。

**4. 攻 L8／L9 修法**

**L8 baseline 雙量**：Task 9.4 L211 要求 `n_test_events`＋`n_test_samples` 足夠區分物化失敗，**但** `D-002-C6`(6.2) L92 仍宣稱 baseline `n_test`「樣本數＝事件數…**等價**」，與 L211 **同檔互斥**（→P1-01）。§V **無** Task 9.4 斷言，`M-SU-D2-31` 指向不存在的 §V 項（→P2-01）。下游：`baseline.py:120` 現只寫 `n_test=len(idx)`（樣本）；`metadata.split_unify.n_test`（`split_projection`／前端 `splitAuthority.ts`）語意為**事件數**——雙量未落地前，實作者可依 (6.2) 宣稱恆等而跳過 `n_test_events`，IC 端仍可能用錯粒度。

**L9 Step 0＋三段式**：在步驟 0（界外 raise ＋ pair 完整性）與 `train_last_ms < test_start_ms` 不變量（Task 9.2b L184⑤）下，規則 1–3 **邏輯上互斥且窮盡**；`decision=50`／`450` 重疊問題已由步驟 0 封堵（§V L228-229）。碼證：`split_projection.py` derive 路徑**仍未**呼叫 `validate_split_pair_integrity`（`rg` 0 命中）——屬預期施工前狀態，不構成 SPEC 邏輯洞，但 Task 9.2b 落地時須實作否則 pair 前置成空文。

**5. L1–L11 修訂引入的新問題**

| 衝突 | 說明 |
|------|------|
| L8 vs `D-002-C6`(6.2) | v10 在 Task 9.4 否定恆等，義務塊未同步（P1-01） |
| L7 vs §V | 整鏈驗收只在 Task 散文（P1-02） |
| L8 vs §V／mutation | M-31 應紅測試無 §V 母斷言（P2-01） |
| (G-4e) 誠實邊界 | 三份同錯仍可能，SPEC 未標殘餘（必答 3） |
| D-001／golden | 無新衝突；`decision==cutoff` fixture 仍使 (G-4d)② 空心（§V L225 已誠實標註） |
| TODO §E | `SU-RESID-9A-UI` 已登記，與 §N 一致 |

## §1 必查摘要（11 類）

1. **矛盾**：`D-002-C6`(6.2) vs Task 9.4 L211 — **有**（P1-01）
2. **漏項**：§V 缺整鏈／Task 9.4 — **有**（P1-02、P2-01）
3. **不可測**：M-31 應紅測試缺 §V 母斷言 — **有**
4. **quant 假設**：(G-4e) 三份同錯殘餘 — **有**（必答 3）
5–11. 其餘 — **無新增 BLOCKING**

## COMPOSER-R10-P1-01

**斷言**: L8 第十次修訂在 `Task 9.4` L211 否定 baseline「樣本數＝事件數」恆等並要求雙量輸出，但 `D-002-C6`(6.2) L92 **仍逐字宣稱兩者等價**，同檔義務互斥，實作者可依義務塊跳過 `n_test_events`。

**碼證**: `sed -n '92p;211p' docs/SPLITUNIFY_SPEC.D-002.md`；`baseline.py:105-120` 現僅 `n_test=int(len(idx))`。RECHECK: 對讀 (6.2) 與 Task 9.4；`rg '樣本數＝事件數' docs/SPLITUNIFY_SPEC.D-002.md`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/baseline.py#38c7ec473653

[BLOCKING] 信心度=High。Task 9.4 實作者讀 (6.2) 可合法只改 `n_test` 而不拆雙量，物化失敗反例再次靜默。**修法**：(6.2) 改為「baseline 須輸出 `n_test_events`／`n_test_samples`，不得宣稱恆等；既有 `n_test` 語意明定為樣本數或 deprecate」；§V 增 Task 9.4 物化失敗 fixture 斷言。

## COMPOSER-R10-P1-02

**斷言**: L7 採納之 producer→metadata **整鏈**驗收只寫在 `Task 9.1` L150，§V L220 仍只有 summary／metadata **分層**鍵斷言——與 R9「寫了要做卻沒進 §V」同型，孤立 builder 單測仍可假綠。

**碼證**: L150「驗收須為 producer→summary→metadata 整鏈測試」；§V L220 五條 ASSERT **無**整鏈字樣；`build_split_unify_disclosure`（`split_projection.py:123-180`）仍無 `discarded` 參數。RECHECK: 對讀 L150 vs L220；`rg '整鏈' docs/SPLITUNIFY_SPEC.D-002.md` 僅 Task 段。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。真實 IC 路徑計數可在 orchestrator 邊界遺失而分層測試全綠。**修法**：§V `Task 9.1` 增 `ASSERT 經 EventSamplePipeline.run（或等價 derive 路徑）之 discarded_rows_by_feature_tf 與 metadata.split_unify 同值`。

## COMPOSER-R10-P2-01

**斷言**: `M-SU-D2-31` 應紅測試指向「`Task 9.4` 物化失敗 fixture」，但 §V **無任何 `Task 9.4` 斷言列**——mutation 表與驗收目錄脫鉤（主委自證只驗 mutation 條數，未驗應紅測試是否有母斷言）。

**碼證**: mutation 表 L268 `M-SU-D2-31`；`rg '^- \`Task 9\.4' docs/SPLITUNIFY_SPEC.D-002.md` → **0**（§V 區段）。RECHECK: 對讀 L268 vs §V L218-235。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#2c5a584645ab

[MAJOR] 信心度=High。實作者可無測試依據實作 M-31 或宣稱已覆蓋。**修法**：§V 增 `Task 9.4`：`ASSERT WHEN test 含 e1 且物化 failures 含 e1 THEN n_test_events=1 AND n_test_samples=0`。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `rg -c '^\| \`M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` | **31** |
| `rg '終端使用者看得到' docs/SPLITUNIFY_SPEC.D-002.md`（正文） | **0** |
| `rg 'EventSamplePipeline\(\)\.run' api --glob '*.py'` | **0** |
| G-4e 探針（獨立 expected） | **g4e_pass=False** |
| G-4e 探針（三份同錯） | **g4e_pass=True** |
| `rg 'validate_split_pair_integrity' momentum/Analysis/event_samples/split_projection.py` | **0**（施工前預期） |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R10-P1-01,COMPOSER-R10-P1-02
CLOSED: COMPOSER-R9-P1-01,COMPOSER-R9-P1-02,COMPOSER-R9-P1-03,COMPOSER-R9-P1-04,COMPOSER-R9-P2-01,COMPOSER-R9-P2-02,COMPOSER-R9-P2-03,COMPOSER-R9-P2-04

ASSUMPTIONS_VERIFIED: R9 八條逐條對讀第十次修訂；十一群 grep 落點；G-4e 雙探針；obligation rc=0；mutation 計數 31  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r10-composer.md --family composer`（交件自跑）  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
