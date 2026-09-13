# Reconcile — 20260911-splitunify-b9-review-r13

**來源** 20260911-splitunify-b9-review-r13-codex.md, 20260911-splitunify-b9-review-r13-composer.md, 20260911-splitunify-b9-review-r13-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **T1 `C5-20` 之 mutation 對應錯配，該欄無專屬 mutation**——「C5-20把`feature_timef」 | P1 | CODEX-R13-P1-01 | 採納（主委複驗成立：`M-SU-D2-20` 破壞的是 producer 之 `selected_timeframe` 預設，與 `assignments` 的 `feature_timeframe` 欄無關。改法：新增 `M-SU-D2-35` 專責該欄遺失，`C5-20` 改指之。🔴 **主委同型自查另補一條**：`C5-21` 有**完全相同**的錯配（原指 `M-SU-D2-24`，而該條破壞的是答案窗 purge 之逐列判定）⇒ 新增 `M-SU-D2-36`、`C5-21` 改指之。mutation 條數 34 → **36**，ID 01–36 連續無缺。此為 SPEC body 變更 ⇒ v13 之三家戳記失效，新 body sha256 為 7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2，須重簽） |
| **T2 `Task 9.3` receipt 閘只比行數，重複同一 ID 即可繞過**——「Task9.3receiptgate只比」 | P1 | CODEX-R13-P1-02 | 採納（該家實跑構造出「29 行全是同一個 ID 也判相等」的繞過反例。改法見 `docs/SPLITUNIFY_TODO.md` 之 `Task 9.3`：驗收改為三條——①receipt 首兩行須為 TASK／COMMIT 標頭並與當輪 audit 對證，②**exact ID set** 須與 SPEC register 之 ID 集合相等，明文禁 `wc -l`，③每列格式與封閉分類值域） |
| **T3 `B9D` 批次描述「六個」與 `Task 9.3` 表列九列不一致**——「B9D寫「六個下游消費面」，但Task9」 | P2 | CODEX-R13-P2-03 | 採納（主委複驗成立且**我原本的算術也錯**：改寫時先寫「六個消費模組＋兩個支撐面」＝8，與九列仍不符；正確為**七個**下游消費模組（含 `pattern_bridge`）＋ event-level 表／manifest 與前端 `byEventId` 兩個支撐面＝九列。已逐列具名寫入 `B9D` 欄） |
| **T4 stamp-r1 五條修補之獨立複驗（composer）**——「本輪對stamp-r1五條修補與brie」 | P3 | COMPOSER-R13-P3-00 | 採納（零 finding；該家獨立複驗四項修補，判 proceed） |
| **T5 stamp-r1 finding 閉合（grok）**——「本輪逐項核對後無finding；stam」 | P3 | GROK-R13-P3-00 | 採納（`GROK-R1-P2-01` 由原提出方 CLOSED；零新 finding，判 proceed） |

### 本輪裁定
1. **stamp-r1 五條 finding 全數由原提出方 CLOSED**（codex 四條、grok 一條；章程 §B8 之閉合再驗證已滿足）。
2. **三家一致之兩項收斂**：①批次切法採 **`B9A`–`B9F` 六批**（codex 於本輪亦改判六批，理由＝`B9D`／`B9E` 合批會讓同檔 rebase 與 named test 遺失不可見）；②**不為三條 ASSERT 重開 SPEC §V**——`§C-9` 已以具名測試承接，改壞會在對應測試轉紅，重開與重簽成本不換取足夠風險下降。
3. **T1 使 SPEC body 變更 ⇒ v13 戳記失效**，須對新 body sha256 `7455b305c6f3c013de84d1941c4d69bc731fb5fa90f6e91d447e14382f0b10e2` 重跑戳記輪。
4. **現在仍不可領 impl token**；最小閉合集合＝T1＋T2 修補（已完成）＋ 新 body 的三家重簽。

### DOCROT 成效量測（第一輪）
本輪 canonical finding 總數＝**5**（≤20 ✓）。依 `handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md` 之機械判準逐條套用：
無一條之碼證／來源摘要 `path:line` 落在 `docs/SPLITUNIFY_SPEC.D-002.md` 之 `HISTORY-BEGIN..END`（`CODEX-R13-P1-01` 錨 `split_projection.py:555`、`P1-02` 錨 `tables.py:372`、`P2-03` 錨 `SPLITUNIFY_TODO.md:67,606-616,621`，皆為現行條文）；亦無一條斷言命中封閉字面集合。
⇒ **`doc_friction_ratio` = 0/5 = 0.00**（及格線 ≤0.30）。🔴 **誠實邊界**：`CODEX-R13-P2-03` 語意上確實是「同一件事寫在兩處而數字不一致」之文檔病，只是其斷言用詞未命中該封閉字面集合；**判準是機械的，我按機械算**，但把這件事具名記在此，供第二輪判斷該字面集合是否過窄。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R13-P1-01
**斷言**: C5-20 把 `feature_timeframe` assignments coverage 綁到 M-SU-D2-20，但 M20 實際只破壞 producer 的 `selected_timeframe` 預設；該欄位沒有對應 mutation。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:555
MUTATION: 在 assignments 組裝中刪除 `feature_timeframe` 欄，保留全量 producer 行為，再跑 Task 9.2a named tests；現行 M20 不能指向此破壞。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735; docs/SPLITUNIFY_SPEC.D-002.md#60ad8380c73f
修法：為欄位遺失新增專屬 mutation／red test，並把 M20 留給 Task 9.2；可行性依據是 assignments 的明確欄位建構點（上列 anchor）。信心度=High；否則 mutation coverage 可假綠。

## CODEX-R13-P1-02
**斷言**: Task 9.3 receipt gate 只比較 `C5-NN` 行數，重複同一 ID 29 次即可通過，未證明 C5-01..29 逐條重掃，也未綁定當輪 receipt。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 保留 C5-29 的單鍵 lookup 不修，receipt 寫 29 行 `C5-01 ...`；現行判準仍輸出 `bad_receipt_count=29 spec_register_count=29 count_gate_equal=yes`。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735; docs/SPLITUNIFY_SPEC.D-002.md#60ad8380c73f
修法：驗 sorted unique ID set 恰等於 `C5-01..C5-29`，並以 task／commit 綁定唯一 receipt、移除 `<該檔>` placeholder。RECHECK：對同一 duplicate probe 應 rc!=0；目前 probe 已證明 count-only gate 可被繞過。信心度=High。

## CODEX-R13-P2-03
**斷言**: B9D 寫「六個下游消費面」，但 Task 9.3 表列九列（並在 line 621 寫「九處」），批次 scope 文字不一致，可能漏做 pattern_bridge／event-level／frontend 面。
**碼證**: `docs/SPLITUNIFY_TODO.md:67`、`:606-616`、`:621`；表列計數=9。
**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735
修法：將 B9D 的「六個」改成九處，或明確拆成六個 consumer modules + 三個 supporting surfaces；doc-literal-only，信心度=High。

1a/1b：CODEX-R1-P1-01/02/03/04 均 CLOSED；GROK-R1-P2-01（與 03 同題）CLOSED。實跑 `grep -nE '雙家族|兩家族' CLAUDE.md docs/MULTI_AGENT_ORCHESTRATION.md docs/DEVELOPMENT_GUIDE.md` 僅剩 ORCH:195 明示「本行原寫」之歷史說明；mutation IDs=34 且 01..34 無缺；前端 anchors 361/3174/各列測試行號吻合；`pytest -q -rxX tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_fracdiff_truncation_invariant` rc=0，`1 xfailed`；C5 count=29，TODO literal 在 629-630。Composer 獨立複驗四項，無新增 finding。
2：選六批 B9A–B9F；若併成五批，風險在 B9D/E 合批，執行兩組各自 named pytest + frontend build 時可見同檔 rebase／named test 遺失，故保留獨立 gate。
3：不值得重開已 APPROVED SPEC；C9 已承接 clusters event-level、purged/assignments disjoint、composite-key error message 三條 named tests，改壞會在對應測試轉紅；重開與三家重蓋章成本不換取本輪足夠風險下降。
4：現在不可領 impl token；最小閉合集合＝修正 C5-20 mutation 對應＋把 9.3 receipt 改為當輪 exact-ID-set gate（P1-01/P1-02）。
VERDICT: blocked
BLOCKED-BY: CODEX-R13-P1-01,CODEX-R13-P1-02
CLOSED: CODEX-R1-P1-01,CODEX-R1-P1-02,CODEX-R1-P1-03,CODEX-R1-P1-04
## COMPOSER-R13-P3-00

**斷言**: 本輪對 stamp-r1 五條修補與 brief 攻擊面逐項獨立複驗後無需阻擋收斂之 finding；§C-9 機械驗收字面（xfail `1 xfailed`、register `grep -cE`）在本機 pytest 8.4.2／grep 下可執行。

**碼證**: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0；`awk '/^## §C-9/,0' docs/SPLITUNIFY_TODO.md | grep -oE 'M-SU-D2-[0-9]{2}' | sort -u | wc -l` → 34；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → 摘要含 `1 xfailed`；`grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29。

**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735

[P3] 信心度=High。DOCROT 成效量測第一輪；審查輸入僅 §C-9 current block＋`87d38dd9` diff，未重審 SPEC body。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: SPEC stamp rc=0；34/34 mutation；12/12 pytest 路徑；xfail 摘要字面；register grep 29；六批切法；§V 三條 §C-9 承接足夠  
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=0；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → 1 xfailed；family-drift grep（必答 1b）；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r13-composer.md --family composer`（收尾）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（唯讀 review）

STATUS: DONE
## GROK-R13-P3-00

**斷言**: 本輪逐項核對後無 finding；stamp-r1 本家 `GROK-R1-P2-01` 與同題修補均已關閉，§C-9 可支撐領 impl token 進 Task 9.1。

**碼證**: (1) `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS rc=0，sha256 `06b2d4cb…`；(2) Task 9.4 現行文刪除 `types.ts:1582`／`:2257` 修改指令，改「不動既有介面」——`sed -n '1578,1586p;2250,2260p;3174,3177p' frontend/src/lib/types.ts` 仍證兩舊錨非事件批、`summary: Record<string, unknown>`；(3) `venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → summary 含 `1 xfailed`；(4) `grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29；(5) mutation 完整 ID 計數 34。

**來源摘要**: docs/SPLITUNIFY_TODO.md#9cbdedd0a735

[P3] 信心度=High。sentinel＝零阻擋 finding；非空殼。DOCROT 摩擦候選＝0（無歷史段落點 finding）。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED: GROK-R1-P2-01

ASSUMPTIONS_VERIFIED: stamps rc=0；GROK-R1-P2-01 錯錨已刪且 types.ts 現況仍證舊錨非事件批；`1 xfailed` 字面（pytest 8.4.2）；C5 grep＝29（含 TODO 跳脫形）；mutation 34；家數活文無派工漂移；六批技術耦合
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → PASS rc=0；`venv/bin/python -m pytest -rxX -q tests/test_feature_factory_operators.py::test_rolling_aggregator_handles_duplicate_columns` → `1 xfailed` rc=0；missing-node 同 node id → `ERROR: not found` rc=4；`grep -cE '^\| `C5-[0-9]+`' docs/SPLITUNIFY_SPEC.D-002.md` → 29
FAILURES_SEEN: none（長跑 `test_fracdiff_truncation_invariant` 中途中止，改用輕量 xfail 取字面）
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r13-grok.md

STATUS: DONE
