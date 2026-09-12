# SPLITUNIFY D-002 閉合輪 R2 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R2  
family: composer  
findings-round: R2  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（R1 七群修訂版 @ `708a6bafded5`）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: 七群 15 條全部採納零駁回 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md` 群集表，15 ID 皆「採納」 |
| brief fact-verified: 修訂版 `doc_format_precheck`／`spec_xref_check --synth` rc=0 | **未本輪重跑**（依 brief 背書） | 本輪只讀 SPEC＋碼證對照，未重跑 gate 腳本 |
| brief assumed: `D-002-C3` 異側 purge 不會誤殺合法樣本 | **assumption，本輪否證未成功** | 構造同事件 1h cutoff∈train_ms、4h cutoff∈test_ms（見必答 2）；此情境會被 C3 整事件 purge，但屬洩漏形態而非合法分析 |
| brief assumed: `D-002-C6` 三量定為事件數 | **fact-verified（消費者對照）** | `tests/api/test_splitunify_disclosure.py:282-300` 明定 `n_test`=事件數、`test_rows`=K 線列數；`baseline.py:120` 之 `n_test` 為不同報告欄位（見必答 3） |
| brief assumed: 18 條 mutation 覆蓋 16 處＋9A 三層 | **fact-verified（表對照）** | §V L173-181 列 18 條；`12`/`13` 對位記帳鏈與 wiring；`01`-`03` 對位 9A 三層 |
| brief assumed: 分名後全檔無裸 `timeframe` 歧義 | **fact-verified（行號掃描）** | `rg '\btimeframe\b' docs/SPLITUNIFY_SPEC.D-002.md` → 僅 L28/30/32/36/107/201；皆為歷史欄位引用或外部 API 引數名（見必答 4） |

## 必答 1–5（成對立場）

**1. 本家 R1 finding 是否閉合**

| R1 ID | 判定 | 確認方式 |
|-------|------|----------|
| `COMPOSER-R1-P1-01` | **CLOSED** | `D-002-C5` (5.5) 增第四層記帳鏈（`pipeline`／`EventTablesPanel`／`wiring:103-104`）；`D-002-C6` (6.2) 定義三量為事件數；`Task 9.4` 指派修改；§V L170 `n_train+n_test+n_purged == n_events` |
| `COMPOSER-R1-P1-02` | **CLOSED** | §V mutation 由 6→18：`12` wiring `dict(zip)`、`13` `n_train` 取列數、`07` `ic_feed` lookup；`Task 9.3` L171 要求靜默面逐處值斷言。`ic_feed` survivor hash（`ic_feed.py:142-145`）對 event-level manifest 逐事件一行，9B 後 manifest 粒度不變（`Task 9.3` L154），故不需獨立 mutation |
| `COMPOSER-R1-P2-01` | **CLOSED** | `Task 9.1` L133-137 明定返回形狀、跨邊界傳遞、**API 與前端三層揭露**（缺任一層即 9A 未完成）；§V L167 三層 ASSERT；mutation `01`-`03` |

**2. 同側約束（`D-002-C3`）** — **構造不出合法異側情境**。嘗試：同 `event_id` 兩列 `per_tf`（1h／4h），`feature_cutoff_ms` 分別落在 `train_ms`／`test_ms`（對照現行 `split_projection.py:530-553` 逐列判定邏輯）。此時 1h→train、4h→test 正是 `D-002-C3` (3.3) 所述非法 OOS（`feature_materialization` `groupby("event_id")+update` 仍折成事件級一行）。若改 `decision_at_ms` 企圖「誠實」分側，與 `event_level` 一事件一列矛盾。結論：C3 整事件 purge 為保守正確，非過嚴。

**3. 量詞分離（`D-002-C6`）** — **既有消費者不需要把 `n_train`/`n_test`/`n_purged` 當列數**。碼證：`pipeline.py:760-762` 現行對 assignment **列數**求和（9B 後會膨脹）——正是 R1 所指缺陷，修訂版以 (6.2)＋`Task 9.4` 改為事件數並新增 `n_event_tf_rows_*`；`tests/api/test_splitunify_disclosure.py:282-300` 已把 `n_test`（事件）與 `test_rows`（K 線列）分開並斷言 `0 < n_test <= test_rows`；`baseline.py:120` 之 `"n_test": int(len(idx))` 屬 `binary_discrimination` 報告內「測試段交集列數」，與 summary 的 `n_test` 不同命名空間。`ic_feed.py:115` `n_events=len(keep)` 為 manifest 事件行數，9B 後 manifest 仍 event-level（`Task 9.3` L154）。

**4. 術語分名（`D-002-C0`）** — **修訂版無新增裸 `timeframe` 歧義句**。`rg` 命中 L28（說明歷史雙語意）、L30（`canonical_event_id` 外部 API 引數名）、L32（既有 `per_tf.timeframe`／`selected_timeframe`，(0.5) 禁**新**欄名）、L36（規則本身）、L107（FACT-RECEIPT 引 `eventId.ts`）、L201（沿革）。殘留：`discarded_per_tf_rows_by_timeframe`（L136）鍵名含 `timeframe` 而非 `feature_timeframe`，但 L134 明定 dict 鍵語意為 `feature_timeframe`——實作風險低，不另開 blocking。

**5. 修訂引入新問題（C0／C3／C6／Task 9.4）** — **未發現彼此或與 D-001 衝突**。C3 整事件 purge 與 C6 `n_train+n_test+n_purged == n_events`（§V L170）一致（purged 事件不進 assignments）；C0 `selected_timeframe` 對位 `feature_timeframe`（(0.3)）與 9A `discarded` 鍵語意一致；`D-002-C4` (4.4) 明示 D-001 其餘義務繼續有效。主動攻擊：①C3 誤殺合法異側（必答 2 否證失敗）②C6 與 `baseline`/`ic_feed` 列數需求衝突（必答 3 否證失敗）③C0 殘留歧義（必答 4 行號掃描）④Task 9.4 與 Task 9.2 summary 分工重疊——9.2 管 schema 層 `n_events`/`n_event_tf_rows`，9.4 管記帳鏈消費面，職責可區分。

## R1 逐群複驗（七群中本家相關者）

| 群 | 修訂落點 | 複驗 |
|----|----------|------|
| 記帳分母 | `D-002-C6`、`D-002-C5` (5.5)、`Task 9.4` | **閉合**（對位 P1-01） |
| 9A 契約 | `Task 9.1` 重寫 | **閉合**（對位 P2-01） |
| mutation 不足 | §V 18 條 | **閉合**（對位 P1-02） |
| 同側約束 | `D-002-C3` | **閉合**（本家 R1 未開但已採納；本輪實核 (3.1)-(3.4)＋§V L169 成對 ASSERT） |
| timeframe 雙語意／Task 9.3／§G | `D-002-C0`、`Task 9.3`、`§G` (G-1)(G-2)(G-3) | **閉合**（讀 L24-37、L148-155、L121-125；`feature_materialization` 折疊點已逐處列名） |

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無新 finding——R1 三條均已閉合，且對 C0／C3／C6／Task 9.4 四塊之主動攻擊未構造出可證偽缺陷。

**碼證**: ①R1 閉合對照 `D-002-C5` (5.5)、`D-002-C6`、`Task 9.4`、`Task 9.1` L133-137、§V L173-181 ②C3 異側反例 `split_projection.py:530-553`＋`feature_materialization.py:93-130` ③C6 消費者 `pipeline.py:760-762`、`test_splitunify_disclosure.py:282-300`、`baseline.py:120` ④C0 `rg '\btimeframe\b' docs/SPLITUNIFY_SPEC.D-002.md` → 6 行皆為引用／規則 ⑤新義務交叉讀 `D-002-C0`／`C3`／`C6`／`Task 9.4` 與 `D-002-C4` (4.4)。RECHECK: 重讀上述章節＋五處碼證行號。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#708a6bafded5

P3；信心度=High。本輪依 brief 七群落點逐段對照修訂版 SPEC，並以現行碼（`pipeline.py:760-762`、`test_splitunify_wiring.py:103-113`、`ic_feed.py:115,142-145`、`baseline.py:120`、`test_splitunify_disclosure.py:282-300`）驗證必答 2–4。主動攻擊面含：記帳鏈閉合性、mutation 表完整性、C3 過嚴、C6 消費者列數需求、C0 殘留歧義、新義務塊互斥——均未得到需阻擋實作的 P0/P1。

## 主動攻擊面（停輪③）

1. **R1 三條閉合**：逐段讀 `D-002-C5` (5.5)、`C6`、`Task 9.4`、`Task 9.1`、`§V` mutation 表 ⇒ 均已對位。
2. **C3 合法異側**：同事件多 TF 不同 `feature_cutoff_ms` 落異側 ⇒ 非法 OOS，非合法樣本（必答 2）。
3. **C6 列數消費者**：`baseline`/`ic_feed`/`disclosure` 三分命名空間 ⇒ (6.2) 選事件數成立（必答 3）。
4. **C0 裸 timeframe**：全檔 6 處命中，無新欄歧義（必答 4）。
5. **新義務互斥**：C3 purge 與 C6 守恆、C4 保留 D-001 ⇒ 無衝突（必答 5）。
6. **§N 殘留**：L195 `api/services/` 未逐檔讀已在誠實邊界具名；記帳鏈已由 (5.5) 補列，不另開洞。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `rg '\btimeframe\b' docs/SPLITUNIFY_SPEC.D-002.md` | 6 行（L28/30/32/36/107/201），皆為引用或規則 |
| `rg 'M-SU-D2-' docs/SPLITUNIFY_SPEC.D-002.md` | 18 條 mutation（L174-181） |
| 讀 `pipeline.py:760-762` | 現行仍列數求和；SPEC `Task 9.4`＋(6.2) 已指派修正 |
| 讀 `test_splitunify_wiring.py:103-113` | 現行 `dict(zip(event_id,...))`；SPEC mutation `12`＋`Task 9.4` 已指派 |
| 讀 `test_splitunify_disclosure.py:282-300` | `n_test` 事件語意 vs `test_rows` 列語意已分離 |

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: COMPOSER-R1-P1-01,COMPOSER-R1-P1-02,COMPOSER-R1-P2-01

ASSUMPTIONS_VERIFIED: R1 三條逐段閉合對照；C3 異側反例構造；C6 三處消費者碼證；C0 全檔 timeframe rg；§V 18 mutation 對照  
TESTS_RUN: 見「複驗」表；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r2-composer.md --family composer`  
FAILURES_SEEN: none（review 未改碼）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅審查）

STATUS: DONE
