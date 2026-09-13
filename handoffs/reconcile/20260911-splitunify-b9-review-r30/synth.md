# Reconcile — 20260911-splitunify-b9-review-r30

**來源** 20260911-splitunify-b9-review-r30-codex.md, 20260911-splitunify-b9-review-r30-composer.md, 20260911-splitunify-b9-review-r30-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **P1 不可變字面只切斷「事後平移」，未切斷「初始同源算錯」**——「O3字面切斷事後BASE/H1平移，未切」 | P1 | CODEX-R30-P1-01 | 採納（🔴 **主委 r29 之 assumed「不可變字面已消除共因」被實跑否證**：該家把 BASE **與** fixture 字面**同步**平移 17 毫秒，兩欄仍相等（BASE_SHIFT_AND_HAND_SHIFT_G4E_EQUAL True）——因為那些字面當初是主委**用同一組常數算出來再貼上去的**。已加**第三份獨立副本**於 tests/momentum/Analysis/test_splitunify_golden.py（另一個檔），與 golden 凍結值逐筆對帳。主委實跑複驗**完整攻擊路徑**：同步改 fixture 字面、BASE **與 golden 凍結值** ⇒ 第三份副本那條轉紅並指名。🔴 **誠實邊界**：同一 commit 改三個檔仍可繞過，與 `SU-RESID-V8-ATTEST` 同一 user-ruling 殘留，只是把門檻由「改一個常數」拉到「必須審過三個檔」） |
| **P2 SPEC §P Task 9.2 仍為 live 舊碼態（同型第十次）**——「SPEC§P`Task9.2:197-2」 | P1 | CODEX-R30-P1-02 | 採納（該段六個 bullet 描述的是 `Task 9.2` **開工前**快照——`selected_timeframe` 必傳、`str()` 強制轉型、四參數閘、`validate="1:1"` 每事件恰一列——B9B 落地後全部作廢卻**未標 SUPERSEDED**。該家實跑證明：照舊段把 `selected_timeframe` 加回必填集合並保留 `str(None)` ⇒ 兩條 wiring 測試轉紅。已加 SUPERSEDED 標頭並逐字寫出現行契約；舊字面保留供追溯。🔴 **同型第十次**——前九次見 v19–v24 沿革） |
| **P3 --help 仍寫舊語法，會引導到必然被拒的寫法**——「O1實作要求`<key>=<old8>:」 | P2 | CODEX-R30-P2-03 | 採納（`--accept-value-changes` 已於 v24 改為須帶 `<key>=<old8>:<new8>`，但 --help 仍說「逗號分隔之既有頂層鍵清單」⇒ 照說明寫必被拒。已改寫 help 文字並註明 digest 取法與「只列鍵名不算授權」） |
| **P4 §V `:265` 仍寫「fixture 常數逐筆手算」**——「§V`:265`仍寫「fixture常數」 | P2 | COMPOSER-R30-P2-01 | 採納（該句是 v23 之寫法，v24 已改為「不可變字面、不得由 `BASE`／`H1` 推導」⇒ 兩者互斥，實作者依 SPEC 可能把共因公式寫回。已標 v25 更正、原字面刪節保留。🔴 **這是主委自己 v23 的字面在 v24 改了做法後沒回頭同步**，與 P2 同型） |
| **P5 grok 零 findings、v24 APPROVED**——「本輪逐項核對後無finding——本家r」 | P3 | GROK-R30-P3-00 | 採納（判 proceed） |

### 本輪裁定

1. **r29 五條中四條由原提出方 CLOSED**（`CODEX-R29-P1-01`／`P1-03`／`P1-04`／`P1-05`）；`CODEX-R29-P1-02` 判 **STILL-OPEN 之半**——`HISTORY` 那半已閉，**四檔同 commit 那半**維持 `SU-RESID-V8-ATTEST`（`user-ruling`），該家明示**非 blocking**。
2. 🔴 **該家另實查否證了「倉內還有可用信任根」這個可能**：`run_with_receipt.py:4-5` 明載 receipt 與 audit 同一可寫主體、非防惡意偽造；`verify_audit_chain.py:72-74` 純報告永遠 rc=0；`git config --get commit.gpgsign` 無輸出 ⇒ **既有倉內層都不能成為獨立信任根**。⇒ 殘留歸類 `user-ruling` **經獨立查證成立**，不是主委自己認定的。
3. **四條全數採納並修完**；回歸六路 **737 passed、0 failed、0 xfailed**；`GOLDEN OK`；兩份 `doc_format_precheck` rc=0。
4. **SPEC 進 v25**，新 body sha256 為 29149ae8bd8bbdd77b84dc1d979f2ac4c1cb8e37f2feee8416f93fd3fb0b7b71 ⇒ v24 戳記失效須重簽。
5. 🔴 **同型第十次（P2）＋ 第十一次（P4）**。P4 尤其值得記：**那是主委 v23 寫的字面，v24 改了做法卻沒回頭同步自己的句子**——不是繼承前人的，是本人兩輪內自產自漏。
6. **下一步**：派 `review-r31` 做 P1–P4 閉合再驗證 ＋ 對 v25 新 body 三家重簽；齊備後進 `Task 9.3`（批次 **B9D**）。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R30-P1-01
**斷言**: O3 字面切斷事後 BASE/H1 平移，未切斷初始同源算錯；G-4e 可在錯誤初始時間軸上相等。
**碼證**: `_feature_index()` 用 `BASE + i*H1`，`_event_keys()` 用 index 產生實際 decision，並以同函式 hand mapping 產生 expected；自建 probe 得 BASE-only `13` mismatches，但 BASE+hand 同步平移得 `BASE_SHIFT_AND_HAND_SHIFT_G4E_EQUAL True`（sample `1700000000017 1700000000017`）。
CODE-ANCHOR: scripts/freeze_splitunify_golden.py:151
MUTATION: 暫存 import 將 `BASE` 平移 17ms，並同步把 `_event_keys()` 回傳的 `expected_decision_at_ms` 平移 17ms；執行 G-4e 時刻比較，觀察兩欄仍相等。
**來源摘要**: scripts/freeze_splitunify_golden.py#d67f48046c6c; tests/momentum/Analysis/test_splitunify_golden.py#09ea562d2e5c。P1/High；一次修訂將事件輸入改為獨立、手寫、非 BASE/H1 生成的 13 筆 committed fixture，expected mapping 由獨立測試／receipt 提供；既有 JSON/bytes/digest 對證模式證明可落地，同 commit 惡意替換仍是既有 user-ruling 殘留。
## CODEX-R30-P1-02
**斷言**: SPEC §P `Task 9.2:197-202` 未標 SUPERSEDED，仍把 B9B 舊契約寫成現行碼態；照 SPEC 實作會退回 selected 必傳、四參數閘、單列 merge。
**碼證**: SPEC 仍寫 `build_event_keys(... selected_timeframe=str(selected_timeframe))`、四者同時非 None、每事件恰一列；現行 `pipeline.py:727-743` 只要求三個 canonical 邊界，wiring 兩測試實跑 `2 passed`。
CODE-ANCHOR: momentum/Analysis/event_samples/pipeline.py:727
MUTATION: 把 `selected_timeframe` 加回 `projection_args` required set 並保留 `str(None)`，執行 `test_partial_boundary_gate_accepts_none_selected_timeframe` 與 `test_run_without_selected_timeframe_emits_all_feature_tf_rows`；兩者應轉紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#1c29e2132fa8; momentum/Analysis/event_samples/pipeline.py#ab9322e5cf0f; tests/momentum/event_samples/test_splitunify_wiring.py#6f1e3711c2fc。P1/High；可直接貼入：「`selected_timeframe=None`＝全量 `(event_id,feature_timeframe)` keyed rows；字串＝可選過濾；required set 僅三 canonical 邊界；merge 以 `per_tf` 為行粒度、欄取 `per_tf.timeframe`；docstring 改為複合鍵唯一」。
## CODEX-R30-P2-03
**斷言**: O1 實作要求 `<key>=<old8>:<new8>`，但 `--help` 仍說「逗號分隔之既有頂層鍵清單」，會引導到必然被拒的 key-only 語法。
**碼證**: `venv/bin/python scripts/freeze_splitunify_golden.py --help` 顯示舊 help；temp probe key-only `rc=1`，正確 token `g4_per_symbol_n=dd296919:b7088eec` `rc=0`，改新值同 token `rc=1`。CODE-ANCHOR: scripts/freeze_splitunify_golden.py:558；**來源摘要**: scripts/freeze_splitunify_golden.py#d67f48046c6c。P2/Medium、doc-literal-only；help 改為 old8/new8 canonical JSON sha256 前 8 碼說明，非 blocking。
# 必答
**(1a/1b)** r29 P1-01 CLOSED（exact digest）；P1-02 STILL-OPEN（HISTORY half closed；四檔同 commit half 仍是 `SU-RESID-V8-ATTEST` user-ruling）；P1-03 CLOSED（BASE-only）；P1-04 CLOSED（main init/transaction）；P1-05 CLOSED。自建 O1/O2/O3/O4 probes 分別觀察 key-only拒／貼回正確且改值拒、HISTORY anchor `None`、13 mismatches／同步錯仍 equal、init pair 建立後 digest fail-closed 並可刪後重建；O5 fixture 13/12/`bnd_shift`，node `1 passed`。
**(2a/2b)** `REJECTED`；blocking=`CODEX-R30-P1-01,CODEX-R30-P1-02`。一次修訂最小集合：獨立非 BASE/H1 timestamp fixture＋independent expected mapping；同步把 SPEC §P Task 9.2 三個舊字面改成三參數／全量複合鍵／per_tf 行粒度；P2 help 可同批修。
**(3a/3b)** O2 residual 歸類成立；O1 digest 不等價於無閘成立；O3 共因假設不成立，修法見 P1-01；O5 修補對齊但窮盡假設不成立，修法見 P1-02。O2 不需新工具：`run_with_receipt.py:4-5` 明載 receipt/audit 同一可寫主體且非防惡意偽造，`verify_audit_chain.py:72-74` 純報告永遠 rc=0，`git config --get commit.gpgsign` 無輸出，既有倉內層不能成獨立信任根。
**(4a/4b)** 自立詞表：`legacy side source`、`legacy row grain`、`legacy timestamp source`、`legacy count/source`、`stale auth syntax`；命令為自建 `venv/bin/python - <<'PY'` regex scan（SPEC 截於沿革、TODO 全文）。SPEC C0/C5/C6/RISK/A/G/V/N 與 TODO §0/§B/Task1–4/9.1/9.2b–9.5/§D/§E 無新矛盾；TODO 9.2a xfail hits 均有 SUPERSEDED/刪節線且現行 1 passed；唯一 live contradiction 是 SPEC §P Task 9.2:197-202（P1-02）；可貼字面見 P1-02。
**(5a/5b)** 不可進 B9D；最小阻擋集合 `CODEX-R30-P1-01,CODEX-R30-P1-02`。`SU-RESID-V8-ATTEST` 是 user-ruling、非 blocking；O1/O4/O5 已修半不另增 blocker。
VERDICT: blocked
BLOCKED-BY: CODEX-R30-P1-01,CODEX-R30-P1-02
CLOSED: CODEX-R29-P1-01,CODEX-R29-P1-03,CODEX-R29-P1-04,CODEX-R29-P1-05
ASSUMPTIONS_VERIFIED: O1 exact token；O2 same-writer receipt boundary；O4 init-v8 delete/rebuild 後仍 digest fail-closed；O5 13/12/bnd_shift；O3 深層共因被 probe 否證；SPEC §P 舊 live 字面被 scan 確認。
TESTS_RUN: O1–O4 自建 temp probes；fixture probe；指定 node→1 passed；wiring pair→2 passed；derive pair→2 passed；doc_format SPEC/TODO→rc=0；reconcile_body_hash→`bc4a2b3e…`, rc=0；freeze `--help` 與 `git diff --name-status fa0ca3f4^ fa0ca3f4` 已實跑；`bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r30-codex.md --family codex`→PASS, rc=0。
FAILURES_SEEN: 初版 O1 probe 忘建 temp receipt dir、再漏設 temp REPO，均為 harness setup traceback；修正後結論完成，未改 repo code/test。 NUMERIC_OR_SCHEMA_IMPACT: 未修改 runtime、golden、numeric 或 wire schema；修法為提案。
SCOPE_CHANGES: 僅新增本檔及 append required codex REJECTED stamp；未改 code、SPEC正文、TODO、root HANDOFF、data_cache；`/tmp/workdir` 不存在、無需刪除，`/tmp/claude-501` 保留。 OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r30-codex.md
STATUS: DONE
## COMPOSER-R30-P2-01

**斷言**: §V `:265` 仍寫「fixture 常數逐筆手算」，與 v24 O3 已落地的「不可變字面、不得由 BASE／H1 推導」互斥，實作者依 SPEC 可能把共因公式寫回。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:265` 逐字含「逐筆手算」；`scripts/freeze_splitunify_golden.py:145-164` 為 `_hand_decision` 字面 dict；`pytest tests/momentum/Analysis/test_splitunify_golden.py::test_hand_decision_timestamps_are_immutable_literals -q` → **1 passed**。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#bc4a2b3ea78f; scripts/freeze_splitunify_golden.py#c8c5a46f6804

doc-literal-only；信心度=High。修法見必答 4(4b)；一次文件修訂可閉合，不動碼。

---

## GROK-R30-P3-00

**斷言**: 本輪逐項核對後無 finding——本家 r29 為零 finding sentinel 無反例可重跑；O1–O4 四探針與 O5 fixture 皆如預期轉紅／成立；assumed ①殘留歸類正確且無隱藏可做層、②貼回 hint≠只列鍵名、③執行期共因已除、④自立詞表無第十處 live 互斥；v24 body 可重簽；可進 `Task 9.3`（B9D）之前提在本家側已滿足。

**碼證**: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `bc4a2b3ea78fbb09a7989cbb4b36ce6e421ec9abe155d086ece8d21461b4457c`；`doc_format_precheck` SPEC／TODO → rc=0／0；`./venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py tests/momentum/Analysis/test_splitunify_golden.py tests/momentum/event_samples/test_splitunify_wiring.py` → **144 passed**；O1 只列鍵名 rc=1（格式不合）；O2 HISTORY-only 錨 `None`；O3 `BASE+17` mismatch＝13、hand 不變；O4 既有 `--init-v8` rc=1、temp 重建後 intact rc=1；O5 equal＝12／non-equal=`['bnd_shift']`；詞表 `grep` live 互斥＝0（見必答 4 表）。

**來源摘要**: handoffs/20260911-SPLITUNIFY-B9-REVIEW-R30-BRIEF.md#80fcbf7fdd0b; docs/SPLITUNIFY_SPEC.D-002.md#bc4a2b3ea78f; docs/SPLITUNIFY_TODO.md#7667beb456fe; scripts/freeze_splitunify_golden.py#d67f48046c6c; handoffs/reconcile/20260911-splitunify-b9-review-r29/synth.md#23c0ce228dc8

---

