# Reconcile — 20260911-splitunify-b9-consult-r2

**來源** 20260911-splitunify-b9-consult-r2-codex.md, 20260911-splitunify-b9-consult-r2-composer.md, 20260911-splitunify-b9-consult-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_TODO.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **A1 裁定＝`REVERT`：四檔 dirty 是「schema 已 v13、行為仍 v12」之不可交付切片**——「未commit之`pipeline.py」「本批diff未實作`Task9.2b`／」「四檔生產/測試變更無impltoken、」 | P0 | COMPOSER-R2-P0-01, COMPOSER-R2-P0-02, COMPOSER-R2-P1-01 | 採納（兩家獨立達成同一裁定且理由不同源：composer 打「切片不可交付」、grok 打「同一原子契約，逐 hunk 必成不一致中間態」。主委複驗兩項碼證成立——`grep -n "validate_split_pair_integrity" momentum/Analysis/event_samples/pipeline.py` 命中 **0**；`grep -c "decision_at_ms" momentum/Analysis/event_samples/split_projection.py` 命中 **0** 而 `split_label` 仍由 `feature_cutoff_ms` 決定 ⇒ 保留即產生「同事件異側 OOS」而無任何閘會紅） |
| **A2 程序：SPEC 未三家蓋章故本輪不得裁 dirty 去留（codex fail-closed）**——「依`AGENTS.md`Rule12，本」 | P0 | CODEX-R2-P0-01 | 部分採納（**採納其結論、不採納其停輪範圍**。採納：`reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=1 為真，且該家之最小解除集合「三家對 D-002 蓋章」與 composer／grok 之最小閉合集合第 2 項**是同一件事** ⇒ 三家在「先蓋章再動生產碼」上**無分歧**。不採納停輪範圍：`AGENTS.md:40` 逐字為「**動工前**…不動工」，本輪為唯讀裁定、不動工，與 R4 同情境之既有裁定一致（見 `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md` 之駁回段）。🔴 **但本輪不記該家欠輪**——它交了合格 canonical finding 且其 P0 的處置方向與另兩家收斂，與 R4 之「零實質審查」不同） |
| **A3 兩條紅測試之判定（推翻主委 brief 之二選一框架）**——「`test_multi_feature_」「`test_duplicate_even」 | P1 | COMPOSER-R2-P1-02, COMPOSER-R2-P2-01 | 採納（`test_duplicate_event_id_is_fail_closed`＝**測試過時**：行為仍 fail-closed，只是訊息由「event_id 重複」改為「複合鍵重複」，授權＝§V／`Task 9.2a` 現行條文。`test_multi_feature_tf_opposite_sides_must_fail_closed`＝**三重問題**：①`_manifest(keys)` 把兩列同 eid 寫進事件級 `manifest.table`、②`(3.2)` 異側 `AlignmentViolationError` 碼上不存在、③判側仍 `feature_cutoff_ms`。🔴 **主委自承 brief 之必答 3a 把它問成「測試過時 or 實作錯」二選一，該問法本身有洞**，兩家都答出第三種形態） |
| **A4 回退成本上界已閉（主委 brief 之 assumed 第 2 條）**——「`build_event_keys`簽章」 | P2 | COMPOSER-R2-P2-02 | 採納（`build_event_keys` 之 `Tuple` 簽章破壞面止於 repo 內；`handoffs/20260911-splitunify-b9-probe-multitf.py:47` 已用雙回傳值 ⇒ REVERT 四檔後該 probe 成孤兒，須**一併還原或另行改回單回傳值**，已寫入 A1 之執行步驟） |
| **A5 golden 未受本批影響**——「本批diff**未**改動`tests/」 | P3 | COMPOSER-R2-P3-01 | 採納（與 brief fact-verified 第 5 條一致：`Task 9.5`／v8 錨點未開工，REVERT 不觸及 golden 回歸錨） |
| **A6 `feature_timeframe` 欄命中 register `C5-20`／`C5-21`（乙類）**——「`assignments`新增`feat」 | P3 | COMPOSER-R2-P3-02 | 採納（`extract_event_patterns` 仍 `assign.set_index("event_id")`、無 production caller 見 §E `R-4`，本批未紅。處置＝把「動工前重掃 register，`C5-20`／`C5-21` 逐條複驗」寫成 `Task 9.3` 的動工前置條款；該 Task 正由本輪裁定步驟 2 寫入 `docs/SPLITUNIFY_TODO.md`，故不另列延後） |
| **A7 grok 零 findings sentinel**——「本輪逐項核對後無finding；裁定與六」 | P3 | GROK-R2-P3-00 | 採納（該家六組必答皆以 diff／pytest／grep 閉合，無缺陷項；其必答 4a 之驗收命令與 4b 依賴序已併入下方裁定） |

### 本輪裁定（執行順序，逐項可機檢）

1. **`REVERT`**：`git checkout -- momentum/Analysis/event_samples/split_projection.py momentum/Analysis/event_samples/pipeline.py tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples/test_splitunify_wiring.py`，並一併還原 staged 之 `handoffs/20260911-splitunify-b9-probe-multitf.py`（A4）。驗收＝上列兩測試檔重跑無 failed。
2. **補 `docs/SPLITUNIFY_TODO.md` 之 `Task 9.1`–`9.5`**，依賴序逐字為 `9.1 → 9.2 → 9.2a → 9.2b → (9.3 ∥ 9.4) → 9.5`（三家與主委獨立版**四方一致**）；`9.2`／`9.2a` 不得拆批；`9.5` 必須最後（golden 重凍會把未定側別寫死）；`9.3` 動工前須重掃 register（grok 原文，主委版未寫，採納）。
3. **派 stamp 輪**對 `docs/SPLITUNIFY_SPEC.D-002.md`（body sha256 `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`）取三家 `RECONCILE-STAMP`。🔴 **stamp brief 須明示**：§V 之 `V8_BASELINE_SHA256=` 64-hex 錨點**尚未寫入**且 SPEC 自標「凍結當下才生效」，不得以其缺失為由 REJECT（composer 原文之折衷）。
4. **領 impl token** 後才動生產碼，進 `Task 9.1`。

🔴 **必答 5a 之分歧與收斂**：grok 判 APPROVED、composer 判 REJECTED，但 composer 逐字寫「規格正文 v13 停輪內容本身 R12 已閉；阻擋在 **TODO 同步** 與 **golden 錨點程序**」⇒ 兩家對 **SPEC body 本身**無異議，分歧只在「TODO 缺段該不該擋 SPEC 的 stamp」。執行上以**步驟 2 先於步驟 3** 同時滿足兩家，不需再開一輪。

🔴 **主委具名不採納委員原文兩處（附理由，供追溯）**：
- grok 之 `Task 9.4` 驗收命令 `venv/bin/python -m pytest -q --tb=short -k 'n_test_events or ...'` **無路徑參數** ⇒ pytest 自 rootdir 收集全套（小時級）；`-k` 只過濾執行、不減少收集。改採逐檔明列。
- composer 之 `Task 9.2b` 驗收含 `bash scripts/freeze_splitunify_golden.py`：①該檔是 `.py`，正確調用為 `venv/bin/python scripts/freeze_splitunify_golden.py`（grok 版）；②golden 重凍屬 `Task 9.5`，放進 `9.2b` 會把未定案側別寫進 golden，與兩家在 4b 都主張的「9.5 最後」互斥。

Verdict：可合併

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01

**斷言**: 依 `AGENTS.md` Rule 12，本輪所依 `docs/SPLITUNIFY_SPEC.D-002.md` 尚未取得 codex、composer、grok 三家全數 `APPROVED` 戳記，因此本輪必須 fail-closed 停止，不能可靠裁定 `KEEP`／`REVERT`／`PARTIAL`。

**碼證**: CODE-ANCHOR: scripts/reconcile_stamps_check.sh:119
MUTATION: `tmp="$(mktemp)"; cp docs/SPLITUNIFY_SPEC.D-002.md "$tmp"; printf '%s\n' 'RECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77 task:STAMP-PROBE' >> "$tmp"; bash scripts/reconcile_stamps_check.sh "$tmp"; rc=$?; rm -f "$tmp"; test "$rc" -eq 1`（只補一家的暫存副本，composer／grok 仍缺戳記，預期 rc=1）。RECHECK: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1，輸出列明三家皆「缺 APPROVED 戳記」；body hash 實跑為 `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`（`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=0）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

BLOCKING；信心度=High。最小解除集合是：三家各自完成本輪審查並以該 body hash、有效 task provenance append `RECONCILE-STAMP: <family> APPROVED ...`，再重跑同一支 `reconcile_stamps_check.sh` 確認 rc=0；在此之前不進行本 brief 的 current-block／diff 裁定。可行性證據是 `scripts/reconcile_stamps_check.sh:134-141` 有明確的全數核可與 hash 相符 PASS 分支；本輪未宣稱該 PASS 已達成。

ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` 實跑 rc=1；`bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` 實跑 rc=0 且輸出 body hash `06b2d4cb5f6b24ea311bce0853912e101b56572cd34bc50f6c044a4a53508b77`。
TESTS_RUN: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → FAIL/rc=1（三家 APPROVED 戳記皆缺）；未執行 diff 審查與 pytest，因 Rule 12 已阻擋。指定的 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-consult-r2-codex.md --family codex` 於執行前被 PreToolUse `open_debt` hook 擋下，故沒有 script rc 可報。
FAILURES_SEEN: reconcile stamp gate rc=1；completeness command 未啟動（hook 阻擋，不是格式失敗）；未觀察其他測試失敗。
SCOPE_CHANGES: 未改動生產碼、測試、SPEC、TODO 或既有 dirty 檔；本檔為唯一新增交件。
NUMERIC_OR_SCHEMA_IMPACT: none。
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P0-01
CLOSED:
STATUS: BLOCKED — reconcile 未核可
## COMPOSER-R2-P0-01

**斷言**: 未 commit 之 `pipeline.py` 未實作 v13 O4：進入 `derive_event_split_from_plans` 之前須以 `feature_index` 作 `ts`、`train_plan.symbol` 廣播作 `symbols` 呼叫 `validate_split_pair_integrity`；保留本批碼會讓 Task 9.2b 前置永遠缺落點。

**碼證**: `grep -n validate_split_pair_integrity momentum/Analysis/event_samples/pipeline.py` → **0** 命中；對照 `ic_split_adapter.py:305` 有呼叫；v13 §V Task 9.2b 前置改寫 O4。CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:755; MUTATION: 刪除 `derive_event_split_from_plans` 呼叫塊後插入 validator 前後再跑 `grep -c validate_split_pair_integrity momentum/Analysis/event_samples/pipeline.py` 應由 0 變 ≥1。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT 後於 `EventSamplePipeline.run` 在 `:755` 前插入 validator（含座標 adapter 四案）；驗收掛 §V pair 完整性斷言。**可行性**：validator 已存在於 `ic_split_adapter.py`，事件路徑缺的是呼叫與 `symbols` 構造，非新算法。

---

## COMPOSER-R2-P0-02

**斷言**: 本批 diff 未實作 `Task 9.2b`／`D-002-C3`：`_derive_single_symbol` 仍以 `feature_cutoff_ms` 集合成員定 `split_label`（`:586-621`），全檔 `decision_at_ms` 命中 **0**；保留即 schema 複合鍵、語意仍 v12，會靜默產生同事件異側 OOS。

**碼證**: `grep -n decision_at_ms momentum/Analysis/event_samples/split_projection.py` → **0**；`:587-588` 仍 `cutoff in train_ms`/`test_ms`。CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:586; MUTATION: 將 `:587` 改回純 `feature_cutoff_ms` 判側後 `pytest tests/momentum/Analysis/test_splitunify_derive.py::test_multi_feature_tf_opposite_sides_must_fail_closed -q` 應不再觸發 C3 路徑（若 9.2b 已實作則 mutation 應轉紅）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT 後按 §P Task 9.2b 三段式＋C3 `AlignmentViolationError` 整段實作；不可只保留 9.2a schema。**可行性**：spec 已具名落點與 §V 反例；缺的是施工，非規格空白。

---

## COMPOSER-R2-P1-01

**斷言**: 四檔生產/測試變更無 impl token、D-002 零 `RECONCILE-STAMP`，卻已改 producer 簽章與投影門檻，屬流程違規進度，不得 KEEP。

**碼證**: `bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → 三家皆「缺 APPROVED 戳記」；`git diff --stat` 僅四檔、無 `.claude/gate/*impl*` token 紀錄。CODE-ANCHOR: docs/SPLITUNIFY_SPEC.D-002.md:172; MUTATION: 在無 stamp／無 token 下 commit 四檔後 `reconcile_stamps_check.sh` 仍 rc≠0 ⇒ 程序仍 fail-closed。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[BLOCKING] 信心度=High。**修法**：REVERT → TODO 9.1–9.5 → stamp → impl token → 重寫。**可行性**：回退成本已證為四檔 diff 上界。

---

## COMPOSER-R2-P1-02

**斷言**: `test_multi_feature_tf_opposite_sides_must_fail_closed` 之 `_manifest(keys)` 對多 feature TF keys 複製 `event_id`，違反 v13「manifest 事件級唯一」；測試在 C3 實作完成前必紅，不能當 KEEP 理由。

**碼證**: `tests/momentum/Analysis/test_splitunify_derive.py:142-149` 逐列複製 `keys["event_id"]`；`:1068-1072` 兩列同 `e_x` ⇒ manifest 雙列。CODE-ANCHOR: tests/momentum/Analysis/test_splitunify_derive.py:142; MUTATION: `_manifest` 改 `drop_duplicates("event_id")` 後若 9.2b 未實作，測試應 fail 於異側而非 manifest 重複 — 用於區分「僅 fixture 錯」vs「實作缺」。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MAJOR] 信心度=High。**修法**：REVERT 後重寫測試：manifest 一事件一列、keys 兩 feature TF；期待 `AlignmentViolationError`。**可行性**：§V `D-002-C3` (3.2) 已授權。

---

## COMPOSER-R2-P2-01

**斷言**: `test_duplicate_event_id_is_fail_closed` 之 regex 仍綁 v12「event_id 重複」語意；v13 `Task 9.2a` 已改複合鍵 guard，屬測試過時而非 producer 回歸。

**碼證**: `:811-818` `match="event_id 重複"`；實跑 raise 含 `(event_id, feature_timeframe) 複合鍵重複`。CODE-ANCHOR: tests/momentum/Analysis/test_splitunify_derive.py:815; MUTATION: 僅改 regex 為 `複合鍵重複` 而不改 `split_projection.py:486-496` ⇒ 若 guard 被刪則應轉紅。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MAJOR] 信心度=High。**修法**：impl 時同步改 regex 或改 dup fixture 為同 `(event_id, feature_timeframe)` 兩列。

---

## COMPOSER-R2-P2-02

**斷言**: `build_event_keys` 簽章改為 `Tuple[DataFrame, Dict]` 之破壞範圍已閉合於 repo 內呼叫點；`handoffs/20260911-splitunify-b9-probe-multitf.py:47` 已用雙回傳值，REVERT 四檔不會留孤兒 caller（probe 可獨立再改）。

**碼證**: `grep -rn build_event_keys --include='*.py' .` → 僅 `split_projection`/`pipeline`/兩測試檔/probe；無 `api/` 命中。CODE-ANCHOR: handoffs/20260911-splitunify-b9-probe-multitf.py:47; MUTATION: 暫改 probe 為單回傳 `build_event_keys(...)` 應 TypeError — 證明 probe 與新簽章綁定，REVERT 生產碼時 probe 須一併改回或暫不跑 case C/D。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MINOR] 信心度=High。doc_friction：攻擊面表格已列、本輪逐 caller 核對後閉合。

---

## COMPOSER-R2-P3-01

**斷言**: 本批 diff **未**改動 `tests/golden/splitunify/splitunify_golden.json` 任一頂層鍵；Task 9.5／v8 錨點仍未開工，與 brief fact-verified 一致。

**碼證**: `git diff -- tests/golden/splitunify/` → 空；`ls tests/golden/splitunify/` 無 `splitunify_golden.v8.json`。CODE-ANCHOR: tests/golden/splitunify/splitunify_golden.json:1; MUTATION: 對主檔任一頂層鍵改值後 `pytest tests/momentum/Analysis/test_splitunify_golden.py -q` 應轉紅（證明 9.5 回歸網仍有效、本批未觸）。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#06b2d4cb5f6b

[MINOR] 信心度=High。無需因本批 KEEP/REVERT 重算 golden。

---

## COMPOSER-R2-P3-02

**斷言**: `assignments` 新增 `feature_timeframe` 欄命中 register **C5-20**／**C5-21**（乙類）；`extract_event_patterns` 仍 `assign.set_index("event_id")`（`:125`），無 production caller（§E `R-4`），本批未紅但 **Task 9.3** 前不得宣稱消費面安全。

**碼證**: `pattern_bridge.py:125`；§E `R-4` blocked-by。CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125; MUTATION: 對含同 event 雙 feature TF 之 assignments 跑 `extract_event_patterns` ⇒ `lab_by_id[e]` 變 Series 非純量（Task 9.3 應 fail-closed）。

**來源摘要**: docs/SPLITUNIFY_TODO.md#e44da6448b01

[MINOR] 信心度=Medium。不阻本輪 REVERT 裁定；列入 9.3 施工清單。

---

VERDICT: proceed  
BLOCKED-BY:  
CLOSED:
## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；裁定與六組必答已用 diff／pytest／grep 閉合，無需另列 P0–P2 缺陷項。

**碼證**: 核對依據＝(1) `git diff` 四檔＋staged probe；(2) `pytest` 兩檔 → 2 failed／91 passed，失敗訊息分別為複合鍵重複字面 vs manifest event_id 重複；(3) `grep -c validate_split_pair_integrity pipeline.py`＝0 且側別仍 `feature_cutoff_ms` @ `split_projection.py:587-589`；(4) `grep -rn build_event_keys --include='*.py'` 呼叫點表；(5) `reconcile_stamps_check` 三家缺戳；未對 HISTORY 段下 anchor。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-CONSULT-R2-BRIEF.md#688ccf955989

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:
STATUS: DONE
