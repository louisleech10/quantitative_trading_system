# SPLITUNIFY D-002 閉合輪 R6

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R6
findings-round: R6

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。**上游收斂檔沒有戳記是正常狀態**：戳記在審查
收斂之後才蓋；若以「沒戳記」為由拒審，戳記與審查互為前置，任何票的第一輪都無法開始。

## 這一輪要做什麼

R5 三家共 11 條、歸八群、**全部採納零駁回**，`docs/SPLITUNIFY_SPEC.D-002.md` 已第六次修訂。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**；另攻本輪修訂引入的新問題。

🔴 **本輪最該被攻的主張**：我宣稱「`Task 9.2`（含 producer 內部 merge 與輸出欄）
＋`9.2a`＋`9.2b` 到位後，`SU-RESID-2` 的靜默丟棄才會消失」。

**這個主張已經被推翻四次**，每次形態都不同：
- R2：只加欄位，沒要求 producer 停止單選
- R3：改了 `build_event_keys`，沒改唯一生產 caller `pipeline.py:747`
- R4：改了 caller，但 `pipeline.py:723-732` 四參數閘會先 fail-closed
- R5：過了閘，`build_event_keys:291-303` 的 `validate="1:1"` merge 仍會炸、輸出 TF 欄還是觸發 TF

**請假設還有第五層**，自己從 `EventSamplePipeline.run` 入口一路走到 `assignments` 產出
**以及其後的 `feature_materialization`**，不要只信本 brief 列出的關卡。

## 八群的修訂落點（請對照複驗）

| 群 | 你們指出的 | 修訂落點 |
|---|---|---|
| H1 第四層（三家撞題） | `build_event_keys:291-303` merge `1:1` 必炸；輸出 `timeframe` 取自 `event_level`（觸發 TF） | `Task 9.2` 增逐行落點：以 `per_tf` 為行粒度接合、`validate` 改複合鍵判準、**新建** `feature_timeframe` 取自 `per_tf`；另指名 `:271` docstring「恰有一列」舊語意須一併改 |
| H2 (3.2) 無落點 | `AlignmentViolationError` 只見於義務／§V／mutation，無 Task 改法行 | `Task 9.2b` 增：複合鍵唯一 guard 之後、寫入 `assignments` 之前，按 `event_id` 分組檢查 `split_label` 唯一，異側即 raise 且訊息含 event_id，函式 `_derive_single_symbol` |
| H3 mutation 算術與缺項 | 宣稱 23 實列 22；無一條抓 producer 內部 merge | 補 `M-SU-D2-23`／`24`／`25`，條數改為 **25**（主委已自數：表列 25、ID 01–25 連續） |
| H4 baseline 例外 | `Task 9.4` 廣義事件數會壓掉 `baseline` 的樣本數語意 | `Task 9.4` 明列 `baseline` 為例外，配一事件兩列 fixture |
| H5 生產可達性 | 該 route 的 service 永遠走 `run_event_study_only`，拿不到 universe 也無 `discarded` 來源 | `Task 9.1` 增前置：二擇一（改走可取得 universe 之 producer／把終端揭露移出事件掃描端） |
| H6 側別判準 | 跨 TF 網格不一致（1h open 非 4h open 15,264/20,352），集合成員會落空 | `Task 9.2b` 改為**不等式**（`decision_at_ms < test_start_ms`）並對界外 fail-closed |
| H7 斷言標的 | 未指定 `assignments` 或 `features`；舊 wiring 案例與新行為互斥 | §V 逐字指定 `split_plan.assignments`；要求**替換**舊 partial-boundary 參數化案例 |
| H8 TODO 同步 | 狀態債未清 | 維持 §N 既定時點（三家戳記後、`Task 9.1` 動工前） |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R5 十一條歸八群、全部採納 → `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md`
fact-verified: `split_projection.py:291-292` 逐字為 `event_level.merge(selected[["event_id","feature_cutoff_ms"]], on="event_id", how="inner", validate="1:1")`，輸出欄 `timeframe` 取自 `event_level` → 主委實跑 `sed -n '279,303p'`
fact-verified: mutation 表列實數 25、正文宣稱 25、ID 01–25 連續 → 主委實跑 `grep -c` 與 ID 排序
fact-verified: 第六次修訂後 obligation／format rc=0，xref 對 r1–r5 五份 synth 皆 rc=0 → 主委實跑

assumed: `Task 9.2`（含 merge 與輸出欄）＋`9.2a`＋`9.2b` 到位後，生產路徑不再丟列
→ 否證觀測：指出**第五層**——`assignments` 產出之後 `feature_materialization` 的 `groupby("event_id")+row_vals.update` 是否仍折疊，以及該處是否已被 `Task 9.3` 真正涵蓋／我跑了: **沒跑**（前四輪此假設各被推翻一次）
assumed: `Task 9.2b` 的不等式判準（`decision_at_ms < test_start_ms`）與現行 `train_ms`／`test_ms` 集合語意等價
→ 否證觀測：構造 `train_ms`／`test_ms` 非連續區間（有間隙）之情形，看不等式與集合成員是否給出不同側別／我跑了: **沒跑**
assumed: `(3.2)` 的 raise 放在「複合鍵 guard 之後、寫入 `assignments` 之前」是正確位置
→ 否證觀測：指出在該位置檢查會漏掉哪一類異側，或與 `purged` 列的互動有何未定義／我跑了: **沒跑**
assumed: `Task 9.1` 的二擇一足以讓 9A 可驗收
→ 否證觀測：指出兩個選項各自還缺什麼才能寫出可執行的驗收命令／我跑了: **沒跑**

## 必答（成對，缺一不算完成）

1. **你自己 R5 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **第五層在哪**：從 `EventSamplePipeline.run` 走到 `assignments`**再走到 `feature_materialization` 產出**，列出**所有**仍會讓「全量多 feature TF」失效或被折疊的關卡。找不到第五層也要說明你走過哪些分支、為何確信沒有。
3. **不等式 vs 集合成員**：`train_ms`／`test_ms` 有間隙（purge/embargo 造成）時，兩種判準會不會給出不同側別？給反例或碼證。
4. **`(3.2)` raise 的位置**：放在複合鍵 guard 之後、寫入 `assignments` 之前，會漏掉哪一類異側？與 `purged` 列的互動是否已定義？
5. **修訂引入的新問題**：H1–H7 的落點彼此或與 D-001、`D-002-C6`、`Task 9.3` 有無衝突或重複派工？

## 停輪條件

①必答 1–5 皆有立場；②必答 2、3、4 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 Task 9.x 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R6-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
