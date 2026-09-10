# SPLITUNIFY — SPEC v2 ＋ TODO v2 adversarial 審（R2）

brief-kind: review
task-id: 20260911-SPLITUNIFY-X-REVIEW-R2
findings-round: R2

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0（挑戰前提）與 canonical finding
四欄格式**全文照做**；findings 用 `## <FAMILY>-R2-P<0-3>-<NN>`，結尾附 **Verdict**。
審查對象＝`docs/SPLITUNIFY_SPEC.md`（sha256 `84ab732b021b…`）與
`docs/SPLITUNIFY_TODO.md`（sha256 `7d6d4f0c4e90…`），commit `7fd0a255`。
**禁改碼**；碼證以檔案:行號指名。

## 這是什麼

R1（`20260911-SPLITUNIFY-X-REVIEW-R1`）三家收斂 13 群集，全數採納並已改進 v2。
另有五輪戳記（R1–R5）把 consult synth 由 5 個決議項修正為 8 個，
`reconcile_stamps_check.sh` 現為 **rc=0**（三家全數 APPROVED，雜湊 `120b4d042d38…`）。

本輪要打的是：**v2 有沒有真的把 R1 的 13 群集與 consult 的 D1–D8 落實**，
以及**新引入的 C-0／Task 2.1／Task 3.3 本身有沒有新洞**。

## v1 → v2 的實質變更（逐條，供你核對是否落實）

| 來源 | v2 落點 |
|---|---|
| C10（主委 `CLAUDE-R1-P0-01`）＋ consult D6 | 新增 **C-0**：boundary builder 住 `momentum/core/split_preview.py`，兩端共用；無 universe ⇒ event-study-only |
| R1 之 C2（grok＋composer P0） | **C-4** 簽名補 `feature_index`＋`manifest`；集合語意；`index_kind` 檢查；單位歸一 |
| R1 之 C3（grok＋composer P0） | **Task 1.3** 既有紅 nodeid 清單；驗收改逐條 `--deselect` 後 rc=0 且集合相等 |
| R1 之 C4 | **C-4** 未匹配時間戳 ⇒ purged，禁 nearest |
| R1 之 C5 ＋ consult D7 | **C-5** summary 12 鍵、`build_time_clusters` 抽出、embargo 兩欄須為 None |
| R1 之 C6 | **§G** G-3 拆 G-3a（遷移報告，不進綠徑）／G-3b（獨立 oracle） |
| R1 之 C7 | **Task 3.1** `split_events` 生產呼叫點釘 0；四個成員消費者具名 |
| R1 之 C8 | **§D** mutation 由 3 條擴為 12 條 |
| R1 之 C9 | **Task 1.1** D-002 須寫 post-trim 與正確入口路徑 |
| R1 之 C11（主委） | **C-3** 三態＝兩容器；purge reason 沿用既有契約 |
| R1 之 C12（主委） | **C-5** embargo 兩欄須為 None 否則 raise |
| R1 之 C13（主委） | **§A2** 改寫為「兩個 service、兩個 endpoint、無單一合併點」 |
| consult D8 | **C-9** 統一會改變數值；驗收須逐項 diff |
| consult D1（修正版） | **C-1** 理由改為「共用同一 canonical boundary」；containment 未證明；不刪既有 guard |

## 主委已做的實測（別再提被否證的方案）

- `handoffs/20260910-probe-splitunify-multisymbol.py`（receipt `20260910T150504Z-splitunify-multisymbol`）：
  多 symbol 全域切法 12 列 vs per-symbol 8 列，4 列只在全域 ⇒ **不等價**。
- `handoffs/20260911-probe-splitunify-universe-gap.py`
  （receipt `handoffs/run_receipts/20260910T154323Z-splitunify-universe-gap.log`，rc=1）：
  真實 ETHUSDT 1h 20352 列，**未裁切**時 features 與 bars 兩 universe 逐值相同；
  EVTALIGN 裁頭尾後邊界位移 5 根→2h、24 根→10h、168 根→67h
  ⇒ 「兩端各自用同一公式算 canonical 邊界」**不成立**，必須共用 universe。

## 🔴 必答（每題給明確立場＋碼證，不得只列選項）

1. **C-0 的落點是否可執行**：`pipeline.run` 要新增 canonical boundary 與 `feature_index`
   參數，但它的生產 caller `api/services/case_import_service.py:1610` **目前無從取得**
   feature universe（它只載 `bars_from_kline_cache`）。
   ⇒ 這代表事件掃描端**實際上永遠**走 Task 3.3 的 event-study-only 分支嗎？
   若是，`event_forward_return_table`（`tables.py:305` 只取 test 段事件）會怎樣？
   **請正面答，並指名 v2 有沒有把這件事寫清楚。**

2. **Task 2.1 的 `holdout_boundary` 是否真的「不引入第二份算術」**：
   它同時回傳 row index 與 ms 邊界。ms 邊界是新東西（既有兩支只回 row index）。
   這算不算第二份算術？`M-SU-11` 的判準（「不呼叫既有兩支」）擋得住嗎？

3. **C-5 的 summary 12 鍵在投影下語意是否自洽**：
   `degraded` 之 `_degraded_flags(n_symbols, cluster_adjusted=True)`
   （`event_split.py:22-33`）在多 symbol fail-closed 之後，`n_symbols` 恆為 1
   ⇒ `single_symbol` 旗標恆亮。這是正確的揭露還是誤導？

4. **Task 3.3 的 reason 與既有 reason 是否會混淆**：
   既有已有 `lookahead_split_blocked` 之 unavailable 分支
   （`case_import_service.py:1590-1594`）。新增
   `canonical_feature_universe_unavailable` 後，前端要怎麼區分？v2 寫夠了嗎？

5. **Task 1.3 的清單有沒有時序陷阱**：清單在 B1 凍結，B3 才用。
   若 B2 期間有人（或 `REDSWEEP`）修好其中一條，B3 的「集合相等」檢查會紅。
   這是**特性**還是**會卡住施工**？請給判準與處置。

6. **§G 的 G-5 四項是否可執行**：codex 要求「逐 row test fingerprint、逐 event
   assignments/purged IDs、answer-window 完整性、leakage negative case」。
   v2 只寫了名字沒寫做法。請指名每一項的**具體 oracle**與可證偽方式。

7. **有沒有 R1 的群集在 v2 被漏掉或降級**：逐條對 `handoffs/reconcile/20260911-splitunify-x-review-r1/synth.md`
   之 C1–C13 核。🔴 主委在 consult 收斂已**掉過 11 條 finding 的歸屬**，
   請假設同樣的事可能又發生一次。

8. **批次是否仍成立**：B2 現含三個 Task（builder＋投影＋golden），規模由「中」升為「大」。
   要不要拆？拆的話依賴鏈怎麼排？

## 停輪條件

① 必答 1–8 皆有明確立場（不得只列選項）；② 必答 1／2／6 有具體檔案:行號或可執行命令；
③ 三家若分歧，各自寫出**判準**（看碼證不數人頭），主委依較嚴版本收斂並具名殘留。
④ 禁以「三家零 finding」當停輪理由——零 finding 須走 sentinel 契約。

## 本 brief 之前提（逐條標）

fact-verified: 戳記閘已通過 → `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260910-splitunify-x-consult-r1/synth.md` rc=0。

fact-verified: 事件掃描端無 feature universe → `pipeline.py:512-516`（`run_with_params` 不帶 `feature_config`）與 `pipeline.py:654-657`（`_materialize` 回 `None`）。

fact-verified: `extract_event_patterns` 無任何 caller → `grep -rn extract_event_patterns momentum api tests` 只命中自身與 `__all__`。

assumed: v2 的 C-0 決議③（無 universe ⇒ event-study-only）不會讓事件掃描端的
`event_forward_return_table` 失去意義
← 否證觀測：該表之統計定義要求 OOS，退回全樣本會被誤讀為 OOS 結果。
／我跑了：**沒跑**，只讀了 `tables.py:298-310`。請正面打（必答 1）。

assumed: Task 1.3 之既有紅清單在 B1→B3 之間不會變動
← 否證觀測：`REDSWEEP` 或本票之副作用修好其中一條 ⇒ B3 之集合相等檢查紅。
／我跑了：**沒跑**。請正面打（必答 5）。

## 🔴 我沒查的

| claim | observable_if_false | reason_code |
|---|---|---|
| 前端事件掃描頁是否已能顯示 `capability.split == "unavailable"` | Task 3.3 上線後前端顯示空白或崩 | cost |
| `event_forward_return_table` 之 bootstrap CI 是否依賴 test 段大小 | 退回全樣本後 CI 寬度失真 | cost |
| `_degraded_flags` 之 `single_symbol` 旗標下游有無消費者 | 恆亮後下游行為改變 | cost |

## ⚠️ 前置

- **禁改碼**、禁改 `docs/SPLITUNIFY_*.md` 與任何 reconcile synth（findings 寫進你自己的交件檔）。
- 不得跑 `pytest tests/governance`（小時級）。
- 既有紅基準見 `HANDOFF.md`「既有紅盤點」（`tests/momentum/Analysis` 20 條，非本票造成）。
- 收尾清 /tmp workdir（保留 claude-501）。

## 產出

canonical 四欄 findings ＋ **Verdict**（一句話結論＋是否可進 B1）。
