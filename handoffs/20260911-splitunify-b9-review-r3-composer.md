# SPLITUNIFY D-002 閉合輪 R3 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R3  
family: composer  
findings-round: R3  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第三次修訂 @ `3930b032710e`）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R2 九群 11 條全部採納零駁回 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md` 群集表，11 ID 皆「採納」 |
| brief fact-verified: 第三次修訂後三道閘 rc=0 | **fact-verified（本輪重跑 1/3）** | `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → `OBLIGATION_RC=0`；`doc_format_precheck`／`spec_xref_check --synth` 依 brief 背書未重跑 |
| brief assumed: `(3.1)` 可比時點前提已足以避免同側誤殺 | **assumption，本輪否證未成功** | §V L178 與 `split_projection.py:530-553` 之 operational 定義＝各列 `feature_cutoff_ms` 對 `train_ms`／`test_ms` 落側；同事件混側屬 OOS 洩漏形態（必答 2） |
| brief assumed: clusters 維持事件級不會讓權重失真 | **fact-verified（碼證）** | `event_split.py:66-74` 僅 manifest 事件列算 `w=1/n`；Task 9.2a 定案 clusters 不加欄（必答 3） |
| brief assumed: 20 條 mutation 已覆蓋 producer／survivor 等 | **fact-verified（表對照）** | `rg 'M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` → 20 列；含 `M-SU-D2-19`／`M-SU-D2-20` |
| brief assumed: `(6.2)` 逐消費者不會退化成各處自判 | **fact-verified（列舉完整）** | (6.2) 明列 summary／前端／wiring＝事件數、`baseline.n_test`＝樣本數；`Task 9.4` 派工（必答 5） |

## 必答 1–5（成對立場）

**1. 本家 R2 finding 是否閉合**

本家 R2 僅 `COMPOSER-R2-P3-00` sentinel（`proceed`），無 P0／P1 待閉。R1 三條已於 R2 判定 `CLOSED`，本輪對九群修訂落點逐段複驗：

| 群 | 修訂落點 | 判定 | 確認方式 |
|----|----------|------|----------|
| 同側約束 | `(3.1)` 可比時點前提 | **閉合** | L46 禁止未定義前判定異側；§V L178-179 成對 ASSERT |
| 混側 purge 字面 | `(3.2)` 沿用 `interval_crosses_split_boundary` | **閉合** | L48 指名真相源、不新增值集 |
| 三量一刀切 | `(6.2)` 逐消費者 | **閉合** | L92 明列 baseline 樣本數 vs summary 事件數 |
| producer 單選 | `Task 9.2`＋`M-SU-D2-20` | **閉合** | L145-149 標核心；mutation 表 L205 |
| clusters 粒度 | `Task 9.2a` 維持事件級 | **閉合** | L154 定案不加 `feature_timeframe` |
| mutation 目錄 | 表格 20 條 | **閉合** | L184-205 完整 ID＋應紅測試 |
| timeframe 命名 | `(0.6)`＋`discarded_rows_by_feature_tf` | **閉合** | L38-39、L138；`rg '\btimeframe\b'` 僅引用／規則 |
| 觸及面／義務閘 | C0／C3／C4／C5／C6 | **閉合** | L17-18；`obligation_block_check.sh` rc=0 |
| sentinel | — | **N/A** | 本家 R2 已 sentinel |

**2. 可比時點（`(3.1)`）——能否構造合法事件被誤 purge**

**構造不出合法誤 purge 情境。** 嘗試：同 `event_id` 兩列 `per_tf`（1h／4h），各自 `feature_cutoff_ms` 分別 ∈ `train_ms`／`test_ms`（對照 `alignment.py:197-213` 各 TF 獨立 as-of cutoff；投影落側邏輯 `split_projection.py:530-553`）。此時混側正是 `D-002-C3` (3.3) 所述非法 OOS：`feature_materialization.py:93-130` 之 `groupby("event_id")+row_vals.update` 會把多 TF 折成事件級一行，train 特徵配 test 標籤。第三次修訂 (3.1) 要求先確立落側映射（§V L178 即 per-TF cutoff→split 集合）再套整事件 purge——與現行投影順序一致。**誠實邊界**：(3.1) 未用獨立小節 prose 定義「可比時點」三字，但 §V＋投影碼提供可操作的 operational 定義；若實作者另選 decision_at 錨定，須同步改 §V ASSERT（本輪未構造出需阻擋之衝突）。

**3. clusters 維持事件級——`w=1/n` 與 `n_events_effective`**

**仍正確。** 碼證：`build_time_clusters`（`event_split.py:66-74`）僅讀 `manifest.table`（一事件一列），`cluster_weight = 1.0 / counts` 其中 `counts` 為 `time_cluster_id` 之**事件**計數（非 assignment 列數）。Task 9.2a L154 定案 clusters 不加 `feature_timeframe`、同事件多 TF **共用同一簇列** ⇒ 9B 後 assignments 可 1 event×2 TF＝2 列，但 join `clusters` on `event_id` 仍得同一 `cluster_weight`（權重語意＝每事件一份，非每 TF 列一份）。`n_events_effective` 取自 manifest.summary 之事件列數（`split_projection.py:680`、`event_split.py:184`），與 feature TF 展開無關。**反例嘗試失敗**：若把 clusters 複製成 per-TF 列，`w=1/n` 分母會按列膨脹、破壞「同簇權重和＝1」——正是 R2 採納不修之路徑。

**4. `Task 9.2` 是否補上核心——`SU-RESID-2` 丟棄是否消失**

**規格面已補齊；實作尚未動（預期）。** 碼證：現行 `build_event_keys` 仍在 L279 過濾 `selected_timeframe`、L291 `validate="1:1"`（`split_projection.py:256-303`）；`pytest -k build_event_keys_picks_selected_timeframe_only` → **1 passed**（確認現況仍單選）。第三次修訂：`Task 9.2` L145-149 明定移除預設單選、輸出全量 keyed rows；`M-SU-D2-20` 綁 producer 保留單選應紅。`Task 9.1` 之 `discarded_rows_by_feature_tf`（L138）覆蓋**可選** caller 過濾之揭露路徑。**仍缺**：無（規格層）；實作層待 Task 9.1→9.2 落地。

**5. 修訂引入新問題（(0.6)／(3.1)／Task 9.2／9.2a／20 mutation）**

**未發現彼此或與 D-001 衝突。** (0.6) 解決 R2 裸 `timeframe` 新鍵矛盾；`(3.1)`+(3.2) 與 D-001 封閉 purge 值集一致；Task 9.2 與 9.2a 分工（producer 全量 vs schema 加欄、clusters 例外）無互斥；20 mutation 含 producer（20）與 survivor（19）補 R2 缺口。`D-002-C4` (4.4) 保留 D-001 其餘義務。主動攻擊：(3.1) prose 未獨立定義「可比時點」——§V 已給 operational 定義，不足以開 P1；(6.2) 與 `Task 9.4` 已逐處派工，不會退化成各處自判。

## R2 九群修訂複驗（brief 對照表）

逐段讀第三次修訂 SPEC L38-39、L46-52、L90-94、L133-168、L176-205 與沿革 L225；交叉對照現行程式 `split_projection.py`、`event_split.py`、`baseline.py:120`、`pipeline.py:760-762`、`test_splitunify_disclosure.py:282-300`。九群落點均已落地，與 brief 表一致。

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding——R2 本家已 `proceed`（sentinel），第三次修訂九群修訂落點均已對位，且對 (3.1) 誤 purge、(6.2) 粒度、Task 9.2 核心、clusters 權重、20 mutation 完整性之主動攻擊未構造出需阻擋實作之 P0／P1。

**碼證**: ①九群表逐段對照（上節＋必答 1）②(3.1) 混側反例 `alignment.py:197-213`＋`split_projection.py:530-553`＋`feature_materialization.py:93-130` ③clusters `event_split.py:33-36,66-74`＋Task 9.2a L154 ④Task 9.2 `split_projection.py:279-303` vs SPEC L145-149＋`M-SU-D2-20` ⑤(6.2) `baseline.py:120` vs `test_splitunify_disclosure.py:282-300` ⑥`obligation_block_check.sh` rc=0 ⑦mutation 20 列 `rg 'M-SU-D2-'`。RECHECK: 重讀上述行號＋重跑 obligation 閘＋`pytest -k build_event_keys_picks_selected_timeframe_only`。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#3930b032710e;momentum/Analysis/event_samples/split_projection.py#99bfddace904;momentum/Analysis/event_samples/event_split.py#943d0721b059

P3 sentinel；信心度=High。誠實邊界：IC 端到端真實 run 未跑；(3.1)「可比時點」三字未獨立 prose 定義，但 §V L178 與投影落側邏輯已給 operational 定義——不足以另開 blocking。

## 主動攻擊面（停輪②③）

1. **九群修訂落點**：逐段對照 SPEC ⇒ 均已落地（必答 1 表）。
2. **(3.1) 合法誤 purge**：同事件多 TF 混側＝OOS，非合法樣本（必答 2）。
3. **clusters 權重**：event-level `w=1/n` 不受 assignments 多列影響（必答 3）。
4. **Task 9.2 核心**：SPEC＋M-SU-D2-20 已覆蓋；現碼仍單選屬未實作（必答 4）。
5. **新修訂互斥**：(0.6)／(3.1)／9.2／9.2a／20 mutation 交叉讀 ⇒ 無 D-001 衝突（必答 5）。
6. **§N 殘留**：L218 `api/services/` 未逐檔讀已在誠實邊界具名；不另開洞。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **OBLIGATION_RC=0** |
| `rg 'M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md \| wc -l` | **20** |
| `rg '\btimeframe\b' docs/SPLITUNIFY_SPEC.D-002.md` | 8 行，皆引用／規則／沿革 |
| `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k build_event_keys_picks_selected_timeframe_only` | **1 passed, 77 deselected** |
| 讀 `event_split.py:66-74` | clusters 事件級 `w=1/n` |
| 讀 `pipeline.py:760-762` | 現行仍列數求和；Task 9.4 已派工修正 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: 九群修訂逐段對照；混側/OOS 反例；clusters 權重碼證；Task 9.2 規格＋現碼對照；(6.2) 消費者列舉；obligation 閘 rc=0  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r3-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
