# SPLITUNIFY D-002 閉合輪 R4 — COMPOSER

task-id: 20260911-SPLITUNIFY-B9-REVIEW-R4  
family: composer  
findings-round: R4  
審查對象: `docs/SPLITUNIFY_SPEC.D-002.md`（第四次修訂）

## 被當成事實的未驗證假設（§0）

| 宣稱 | 判定 | 核對 |
|------|------|------|
| brief fact-verified: R3 七群 15 條全採納零駁回 | **fact-verified** | 讀 `handoffs/reconcile/20260911-splitunify-b9-review-r3/synth.md` 群集表 |
| brief fact-verified: `pipeline.py:747` 逐字 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))` | **fact-verified** | `sed -n '745,748p' momentum/Analysis/event_samples/pipeline.py` |
| brief fact-verified: 第四次修訂後三道閘 rc=0 | **fact-verified（本輪 2/3）** | `obligation_block_check.sh` rc=0；`doc_format_precheck.sh` rc=0；`spec_xref_check --synth` 依 brief 背書未重跑 |
| brief assumed: `(3.1)` 事件級錨定不會讓 feature TF 拿到跨側特徵 | **assumption，本輪否證未成功** | 見必答 2：PIT 鏈＋`feature_materialization` 取列邏輯；**兩者皆非**（非洩漏、非資訊不足） |
| brief assumed: `(3.2)` fail-closed 不會讓合法資料上線後 raise | **fact-verified（碼證）** | 見必答 3：合法輸入在 (3.1) 下異側不可產生；raise 僅覆蓋實作退回 per-cutoff 判側 |
| brief assumed: 複合鍵 guard 先於同側不會吃掉真缺陷 | **fact-verified（論證）** | 見必答 5：同時「鍵重複＋異側」時重複鍵即根本缺陷，先報鍵重複不誤導 |
| brief assumed: 移除 `str()` 後 `None` 下游皆有定義 | **fact-verified（caller 盤點）** | `grep build_event_keys(` → 唯一生產 caller `pipeline.py:747`；`build_event_keys` 簽名仍 `selected_timeframe: str`（L259），改 Optional 須同步 Task 9.2 |

## 必答 1–5（成對立場）

**1. 本家 R3 finding 是否閉合**

本家 R3 僅 `COMPOSER-R3-P3-00`（sentinel，`proceed`），**無 P0／P1 ID 待列 CLOSED**。回顧：該 sentinel 宣稱「九群已對位、無 P1」，但同輪 codex／grok 開出 15 條 P1 且全採納——sentinel **過早**，不影響本輪裁決欄（無本家 P1 可填）。

對 **R3 七群**（第四次修訂落點）之複驗：

| 群 | 第四次修訂落點 | 判定 | 確認方式 |
|----|----------------|------|----------|
| 核心 caller | Task 9.2 含 `pipeline.py:747`＋移除 `str()` | **規格已閉、實作未動** | SPEC L148-152；現碼 L747 仍 `str(selected_timeframe)` |
| (3.1) 可比時點 | 事件級 `decision_at_ms` 錨定 | **義務已閉、Task 未指派改碼落點** | C3 L46；但 `split_projection.py:530-553` 仍用 `feature_cutoff_ms` 判側（見 P1-03） |
| (3.2) R2 裁決修訂 | 異側改 `AlignmentViolationError` | **閉合** | C3 L48；§V L186 反例；`M-SU-D2-14`／`15` |
| guard 先後 | 複合鍵唯一先於 C3 | **閉合** | Task 9.2a L159-161 |
| §V 缺口 | purged 鍵／API／golden 入口 | **閉合** | §V L184-187、Task 9.1 L139-142、Task 9.5 L178-179 |
| M-SU-D2-19 | 反向 mutation | **閉合** | L213 |
| TODO 同步時點 | §N 三家戳記後、Task 9.1 前 | **閉合** | §N L222；`SPLITUNIFY_TODO.md:470` 仍 `needs-research`（預期，未到同步時點） |

**2. `(3.1)` 事件級錨定——cutoff 早於 split 邊界是否洩漏**

**兩者皆非（非洩漏、非資訊不足）。** 碼證：`alignment.py:197-213` 各 TF as-of 取 `feature_cutoff_ms` 且強制 `cutoff <= decision_at`（PIT）；`feature_materialization.py:96-126` 以 `last_bar_open_ms`／`row_id` 在該 cutoff 取特徵，不用 split 邊界後資料。反例構造（本輪實跑）：`decision_at=5000∈test_ms`，`cutoff_1h=3000∈train_ms`，`cutoff_4h=4500`——PIT 成立；現行 per-cutoff 判側得混側／purge，(3.1) 以 `decision_at` 錨定兩列皆 `test`。**日曆 train 期的 bar 在決策時已可觀測，不等於標籤洩漏**；側別應跟 `decision_at`，跟 cutoff 才會誤殺（R2 已證）。

**3. `(3.2)` purge 改 fail-closed 是否正確**

**同意。** (3.1) 落地後，合法 receipts 下同事件各 TF 共享 `decision_at_ms`（`alignment.py:219` event_level）⇒ 側別唯一，異側**只能**來自實作仍用 `split_projection.py:530-533` 之 per-cutoff 邏輯。現行該迴圈對每列獨立 `in_train/in_test = cutoff in train_ms/test_ms`，合法多 TF 可產生同行異側 assignment（非法 OOS）；(3.1) 修正後應廣播同一側，**不應** purge 掩蓋。`interval_crosses_split_boundary` 仍管 L540-541 答案窗跨邊界 purge，與 C3 異側 raise **不衝突**。

**4. `Task 9.2` 是否真補上核心**

**規格面已補（含 caller＋`str()` 警告）；§V 與 C5 (5.2) 仍有缺口（見 P1-01、P1-02）；實作未動屬預期。** `grep -rn 'build_event_keys(' momentum api` → **唯一生產** `pipeline.py:747`（測試／probe 另計）。三者到位後：`selected_timeframe=None`＋移除 `str()`＋caller 不傳 ⇒ `SU-RESID-2` 靜默丟棄消失；若 caller 仍傳 selected ⇒ 丟棄依舊。缺：**無第二生產 caller**；設定來源仍須 Task 9.2 實作時一併處理 `config.split.selected_timeframe` 上溯（SPEC L150 已點名）。

**5. 修訂引入的新問題**

見下方三條 P1：C5 (5.2) 舊語意殘留（與 R3 `CODEX-R3-P1-01` 同型、第四次修訂未改）；§V `Task 9.2` 仍只驗 9.2a schema（`M-SU-D2-20` 悬空）；C3 (3.1) 未在任一 Task「改法」指名 `split_projection.py:530-553` 從 cutoff 改 decision_at。與 D-001／`D-002-C6`／guard 先後／`M-SU-D2-19` 反向 **無新衝突**。

## COMPOSER-R4-P1-01

**斷言**: `D-002-C5` (5.2) 仍描述「選定 feature TF 後 `event_id` 唯一」與 assignments／purged「僅以 `event_id` 標識」，與第四次修訂之 `Task 9.2`（全量複合鍵）及 `Task 9.2a`（兩表加 `feature_timeframe`）**直接矛盾**；R3 `CODEX-R3-P1-01` 同型問題**未閉**。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:76` (5.2) 逐字保留 selected-only／event-only 形狀；同檔 `:148-157` 要求全量 `(event_id, feature_timeframe)` 與兩表加欄。`sed -n '76p;148,157p' docs/SPLITUNIFY_SPEC.D-002.md`。RECHECK: 重跑 sed＋對照沿革 L235（第四次修訂未列 (5.2) 更新）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223

[BLOCKING] 信心度=High。Agent 照 (5.2) 實作會保留單選 producer 與 event-only 兩表，與 Task 9.2／9.2a 及 `M-SU-D2-20` 衝突，形成假綠。**修法**：將 (5.2) 三處改寫為 post-D002 契約（全量複合鍵 producer、assignments／purged 含 `feature_timeframe`、clusters 維持事件級並 cross-ref Task 9.2a L158）。**可行性**：純文檔替換，不改程式；與 Task 9.2／9.2a 現文一致即可機械 grep 驗證。

## COMPOSER-R4-P1-02

**斷言**: 第四次修訂已把 `pipeline.py:747` 納入 `Task 9.2`，但 §V 之 `Task 9.2` ASSERT 仍只有 `assignments` schema（=9.2a），**缺**經 `EventSamplePipeline.run`／`build_event_keys(selected_timeframe=None)` 之全量列數 ASSERT；`M-SU-D2-20` 指向的「全量 keyed rows 測試」在 §V **無對位句**，Agent 可只改 schema 而 live path 仍單選。

**碼證**: §V L185：`Task 9.2` 僅 `assignments … feature_timeframe … 唯一`；L214 `M-SU-D2-20` 寫「`Task 9.2` 全量 keyed rows 測試」。Task 9.1 §V L184 對 `discarded` 有 producer 級 ASSERT，Task 9.2 **無對稱** pipeline 級。`pipeline.py:747` 現仍必傳 selected。RECHECK: `sed -n '184,186p;214p' docs/SPLITUNIFY_SPEC.D-002.md`＋`pytest -k build_event_keys_picks_selected_timeframe_only`（1 passed，確認現況仍單選）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/pipeline.py#55ca7327764f

[BLOCKING] 信心度=High。Task 9.x 實作可讓 §V L185 綠燈而 `pipeline.run` 仍傳 `selected_timeframe=str(...)`，SU-RESID-2 核心目標假完成。**修法**：§V 增 `Task 9.2` ASSERT：`WHEN per_tf 含 1h+4h 且經 EventSamplePipeline.run（selected_timeframe=None）THEN build_event_keys 輸出列數=per_tf 列數且兩 TF 皆在`；schema 唯一性 ASSERT 標為 `Task 9.2a`；`M-SU-D2-20` 改指該 ASSERT。**可行性**：全 repo 僅一處生產 caller（已 grep）；現有 `test_splitunify_wiring.py` 可擴一條 pipeline 級案例。

## COMPOSER-R4-P1-03

**斷言**: `D-002-C3` (3.1) 定案 split 側由 `decision_at_ms` 決定，但**任一 Task 之「改法」均未指名** `split_projection.py:530-553` 現行 per-`feature_cutoff_ms` 判側須改為事件級 `decision_at_ms`；Agent 可只完成 Task 9.2a（guard／schema）而漏改側別邏輯，§V 正例 ASSERT（L186）才會紅。

**碼證**: C3 L46 要求 decision_at 錨定；`rg decision_at_ms momentum/Analysis/event_samples/split_projection.py` → **0 命中**；L530-553 逐列 `cutoff = rec["feature_cutoff_ms"]` 後 `in_train/in_test`。Task 9.2a L159-161 只定 guard 先後；Task 9.3 未列此迴圈。RECHECK: 讀 `split_projection.py:528-556`＋C3 L46。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d01a2fee2223;momentum/Analysis/event_samples/split_projection.py#99bfddace904

[BLOCKING] 信心度=High。實作者照 Task 清單改 guard 與欄位、不改 L530-553 ⇒ (3.1) 名義落地、行為仍 per-cutoff 混側，C3 正例 ASSERT 失敗或靠僥倖通過。**修法**：在 `Task 9.2a` 或 `Task 9.3` 增改法條：`derive_event_split_from_plans`／`_derive_single_symbol` 集合成員判定改以 `manifest.table`（或 event_keys 帶出）之 `decision_at_ms` 對 `train_ms`／`test_ms` 定側並廣播到同事件各 feature TF 列；`feature_cutoff_ms` 僅保留給下游物化。**可行性**：`manifest` 已在 `_derive_single_symbol` 作用域（L337）；`manifest.table` 含 `decision_at_ms`（`event_split.py:68` 同欄用法可照抄）。

## 複驗（本人）

| 命令 | 結果 |
|------|------|
| `venv/bin/python handoffs/20260911-splitunify-b9-probe-multitf.py` | A/C `NO_RAISE 2列`；B/D `RAISED`（與 §A 一致） |
| `bash scripts/obligation_block_check.sh docs/SPLITUNIFY_SPEC.D-002.md` | **OBLIGATION_RC=0** |
| `bash scripts/doc_format_precheck.sh docs/SPLITUNIFY_SPEC.D-002.md` | **rc=0** |
| `grep -rn 'build_event_keys(' momentum api` | 生產僅 `pipeline.py:747` |
| `pytest -k build_event_keys_picks_selected_timeframe_only -q` | **1 passed** |

---

VERDICT: blocked
BLOCKED-BY: COMPOSER-R4-P1-01,COMPOSER-R4-P1-02,COMPOSER-R4-P1-03
CLOSED:
STATUS: DONE
