# Reconcile — 20260911-splitunify-b9-review-r23

**來源** 20260911-splitunify-b9-review-r23-codex.md, 20260911-splitunify-b9-review-r23-composer.md, 20260911-splitunify-b9-review-r23-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **G1 codex 以 Rule 12 拒審整輪**——「前置reconcile閘未通過；依Rul」 | P1 | CODEX-R23-P1-01 | 駁回（🔴 **三項依據**：①Rule 12 逐字管的是「動工」，本輪 brief-kind 為 review、產出段明文禁改碼與禁改 SPEC 正文，不是動工；②該讀法是**死鎖且由該家自己觸發**——body 由 76006a76 變成 1b0890e3 正是主委採納該家 r22 之 CODEX-R22-P1-03 並照其修法改 SPEC 所致，若「戳記失效即不得審查／重簽」成立，則「委員要求改 SPEC → 戳記必然失效 → 無人能重簽」成閉環，本 SPEC 永遠無法再取得有效戳記；③**同型第二次**，且該家在 stamp-r2／stamp-r4 兩輪面對同一情境（舊戳記已失效、該輪任務即重簽）皆正常審查並 APPROVED，戳記區 task:20260911-SPLITUNIFY-B9-STAMP-R2 與 task:20260911-SPLITUNIFY-B9-STAMP-R4 兩行可查。**另該家碼證第二半已失效**：其所稱「composer/grok provenance 仍 pending」已由主委 register-output 補記，現行 reconcile_stamps_check 僅剩該家一條雜湊不符。🔴 **處置不是口頭駁回**：AGENTS.md:40 與 .cursorrules:27 之 Rule 12 已改為以 brief-kind 這個封閉集合欄位判適用範圍——僅 impl 適用，review／consult／closure／stamp 一律不適用，白名單由 scripts/brief_conformance_check.sh:191 機械驗證） |
| **G2 composer 零 findings、判可收斂並 APPROVED**——「本輪逐項核對後無需阻擋收斂之findin」 | P3 | COMPOSER-R23-P3-00 | 採納（判 proceed；已 append v19 戳記，provenance 由主委 register-output 補記完成） |
| **G3 grok 零 findings、判可收斂並 APPROVED**——「本輪逐項核對後無finding；F1／F」 | P3 | GROK-R23-P3-00 | 採納（判 proceed；已 append v19 戳記，provenance 同上。該家並誠實更正自己 r22 之「已關閉」立場，改採「部分關閉」） |

### 本輪裁定

1. **r22 之 F1／F2／F3 閉合再驗證**：由 composer 與 grok 兩家實核成立（逐條命令與觀測見附錄）。🔴 **原提出方 codex 未回驗**（見 G1），故依章程 §B8 之「由原提出方重跑同一反例」**尚未滿足**，三條**不標 CLOSED**，留待 r24。
2. **D-002 v19 重簽**：composer、grok 兩家 APPROVED 且 provenance 已補記；**codex 缺**，`reconcile_stamps_check` 現為 rc=1 且**唯一缺口即該家**。
3. **兩家對三條實質問題的一致結論**（主委採納）：
   - `SU-RESID-2` 之部分關閉阻擋者為**兩項**（`Task 9.2b` 側別錨定 ＋ `Task 9.3` 九處消費面），非四項；`Task 9.4` 屬記帳可見性、`Task 9.5` 屬基準檔擴維，各有自己的完成條件，不列為本殘留阻擋者。
   - Task 2.3 之「單 TF 下仍成立」註記**不需**改成條件式寫法（上方已有 SUPERSEDED 指向 `Task 9.5`，該標記本身即指出必須改的目標）。
   - 其他舊 Task 段（2.1／2.3 之 G-3a、G-5②／3.1–3.3／4.1）掃描後**無**新的 B9B 互斥施工令。
4. 🔴 **同輪重派被 brief-sha 綁定擋下**：`cx_run` 將 brief sha256 綁在開債記錄上，換 brief 掛既有 round 會拒（逐字 `ERROR: brief_sha256 與開債記錄不符（換 brief 掛既有 round 已拒）`）。⇒ 駁回依據無法在本輪送達該家，改於 **r24** 單派該家，brief 內明列本表 G1 之三項依據並要求其若仍主張 blocked 須具體否證至少一項、且說明如何避免第②點的死鎖。該家本輪之拒審交件原檔已備份存證。
5. **下一步**：派 `review-r24`（單派 codex）＝ r22 三條之原提出方閉合再驗證 ＋ v19 重簽；三家齊備後進 `Task 9.2b`（批次 B9C）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R23-P1-01
**斷言**: 前置 reconcile 閘未通過；依 Rule 12 本輪不得重簽 SPEC 或進入下游實作。
**碼證**: `reconcile_stamps_check` 實跑 rc=1：codex 最新戳記宣稱 sha256:76006a…，實際 body 為 sha256:1b0890…；composer/grok R23 provenance 仍 pending。
CODE-ANCHOR: scripts/reconcile_stamps_check.sh:126
MUTATION: 在未修正 hash/provenance 下啟動下游實作，會把未全數核可的 reconcile 傳入執行流程。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#d3a633424b03; scripts/reconcile_stamps_check.sh#df3a5bd20c1d
**必要性**: P1；未核可狀態是執行合約的硬阻塞，不可自行繞過。
ROUND_STATUS: R22 三項不能標記 CLOSED；本輪 diff、反例與新 finding 未在閘未通過時正式裁定。
STAMP: 未追加 R23 codex 戳記；SPEC 與程式碼均未修改。
ANSWER_1: 1a blocked；1b 未執行，避免在未核可 reconcile 上做 review 結論。
ANSWER_2: SU-RESID-2 blockers 未重判；不宣稱僅 9.2b／9.3 或其他數量。
ANSWER_3: Task 9.2b 三分支一致性未正式重驗。
ANSWER_4: Task 2.3 單 TF golden 條件未正式重判。
ANSWER_5: 5a／5b 不作 finding 結論；因此不寫 0-finding sentinel。
ANSWER_6: 不進 B9C；待 reconcile 全數 APPROVED 且 provenance 可驗後重開本輪。
ASSUMPTIONS_VERIFIED: body hash=1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7；SPEC/TODO doc_format_precheck 均 rc=0。
TESTS_RUN: bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md；rc=1（codex hash mismatch，composer/grok provenance pending）。
FAILURES_SEEN: reconcile precondition gate failed；未執行回歸測試或 mutation。
SCOPE_CHANGES: 僅新增本交接檔；未改 SPEC 正文、TODO、程式碼、根 HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none。
TMP_CLEANUP: /tmp 為空，無 workdir 或 claude-501 目標可清理；未刪除任何項目。
VERDICT: blocked
BLOCKED-BY: CODEX-R23-P1-01
CLOSED:
STATUS: BLOCKED — reconcile 未全數 APPROVED（codex body hash mismatch；composer/grok provenance pending）
## COMPOSER-R23-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂之 finding；F1–F3 修補已閉合，v19 body 可重簽，可進 `Task 9.2b`。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；`venv/bin/python -m pytest -q -rxX tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/event_samples tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/Analysis/test_splitunify_contract.py tests/api/test_splitunify_disclosure.py tests/api/test_splitunify_event_study_only.py` → **706 passed, 1 xfailed** rc=0；`grep -n "部分關閉" docs/SPLITUNIFY_TODO.md docs/SPLITUNIFY_SPEC.D-002.md` → TODO `:889`、SPEC `:327` 同步。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1b0890e367ab

---

## GROK-R23-P3-00

**斷言**: 本輪逐項核對後無 finding；F1／F2／F3 修補成立，v19 body APPROVED，可進 Task 9.2b（B9C）。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `1b0890e367ab0609bddcb7a04ce11eef0ca680912f269b22b8ca78f3433203e7`；`git show 4ee9632b -- docs/SPLITUNIFY_SPEC.D-002.md docs/SPLITUNIFY_TODO.md` 僅 F1–F3；TODO:889／SPEC:327「部分關閉」＋`blocked-by:Task 9.2b／9.3`；`pattern_bridge.py:125` 仍 raw `set_index("event_id")`；TODO:283 `SUPERSEDED BY Task 9.5`；`freeze_splitunify_golden.py:110` 單一 feature TF；§P 交付 bullet 刪節線＋v19 註；§P／§V Task 9.1 逐句對讀無第三處互斥；舊 Task 2.1／2.3／3.1–3.3／4.1 掃無未標 B9B 互斥施工令；SPEC↔TODO Task 9.2b 三段式一致；`venv/bin/python -m pytest -q -rxX` 三節點 → **2 passed, 1 xfailed**；戳記已 append 且 body hash 不變。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R23-BRIEF.md#4fd774eb26af

[P3] 信心度=High。閉合＋重簽輪 sentinel；F1–F3 由 diff／grep／抽樣 pytest 核對；assumed 兩條攻擊後不阻 B9C。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body hash 1b0890e3…；doc_format 兩份 rc=0；r22 CLOSED；F1 部分關閉同步＋下游仍 raw；F2 SUPERSEDED＋單 TF freeze；F3 metadata 刪節線；阻擋者＝兩項非四項；Task 2.3 不必改條件式；§P／§V 無第三處互斥；可進 B9C
TESTS_RUN: `pytest -q -rxX` 三節點（xfail 錨＋sixteen_keys＋feature_timeframe 來源）→ 2 passed, 1 xfailed；`reconcile_body_hash.sh` → 1b0890e3…；`doc_format_precheck` SPEC／TODO → rc=0
FAILURES_SEEN: none
SCOPE_CHANGES: none（review-only；僅 SPEC 戳記區 append）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r23-grok.md
STAMP_APPENDED: docs/SPLITUNIFY_SPEC.D-002.md（舊戳記保留）

STATUS: DONE
