# Reconcile — 20260911-verdictgate-b4-review-r1

**來源** 20260911-verdictgate-b4-review-r1-codex.md, 20260911-verdictgate-b4-review-r1-composer.md, 20260911-verdictgate-b4-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

**修訂標的**：scripts/_synth_attr.py

**Verdict**：需修補後合併——composer `proceed`；codex `blocked`（2 P1＋1 P2）、grok `blocked`（1 P1＋1 P2；與 codex 同題）。五條**全採納**並已修；派 codex＋grok 閉合確認輪（原提出方重驗）。本 synth 為新閘上線後第一份：每列逐字引用斷言前 20 字＋整詞處置 token。

| 群集 | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **N1 hook 模組覆寫未綁 harness**——「`SYNTH_ATTR_MODULE` 宣稱僅供測試覆寫，但正式 hook 未以 `GOVERNANCE_TEST_HARNESS` 綁定」⇒ 設環境變數即可旁路產出端閘 | P1 | CODEX-R1-P1-01 | 採納（覆寫只在 `GOVERNANCE_TEST_HARNESS=1` 生效，正式路徑固定 `scripts/_synth_attr.py`；模組缺失之靜默放行保留為已揭露次級邊界；新測試以 PostToolUse JSON 實跑正式路徑＋mutation M25） |
| **N2 處置 token 與延後目標皆子字串比對**——「處置與 `延後→` 目標判定不是 token/目標語法的封閉比對」；「`check_disposition` 以 `tgt not in todo_text` 做子字串包含，故 `延後→Task`（以及被 `、，。；` 截成 `Task` 的 `延後→Task、9.9` 等）」皆 fail-open；全形括號誤擷 `E-4（理由` | P1 | CODEX-R1-P1-02、GROK-R1-P1-01 | 採納（封閉文法：token 整詞（前後不接 CJK／字母／數字，`不採納` 不算）；延後箭號後只准單一目標、形狀 ∈ {`Task N.N`, `[A-Z][A-Z0-9]*(-[A-Z0-9]+)*-\d+`}，其後只准空或 `（`／`(` 起之說明；存在性整詞比對 `E-4`≠`E-40`；形狀與單一性 hook 亦擋。新測試 5 條＋mutation M21–M24。本列寫入時即被新閘擋一次——處置欄含字面延後箭號被當成延後處置，改措辭） |
| **N3 hook／閘一致性測試恆真**——「`test_41_hook_and_gate_agree_on_ids_target_quote` 沒有證明 hook 與 gate 的整合一致性」；「`test_41_hook_and_gate_agree_on_ids_target_quote` 對 `check_ids`／`check_target` 是同呼叫自比恆真」 | P2 | CODEX-R1-P2-03、GROK-R1-P2-01 | 採納（刪恆真測試；改為真驅動兩支 bash 包裝：完整列 fixture 之 ①②⑤ 錯誤行集合逐字相同；草稿列 fixture 之 hook 無②、gate 有②；mutation M26 把 hook 改跑全量必紅） |
| **N4 sentinel**——「本輪逐項核對 brief 必答 1–8、SPEC Task 4.1×5 ASSERT／邊界 ①②③」；composer 必答 4／5 另列 P2：ID 尾隨字母 `…-01X`、`延後→E-4、E-5` 只驗首段 | P3 | COMPOSER-R1-P3-00 | 採納（紀錄；兩條 P2 已併入 N2 修法：`_id_in` 尾隨 `[A-Za-z0-9]` 不中；多目標拒） |

### 本輪程序記錄
- 三家交件皆由 `cx_run` 自動註冊成功（本票 B1 契約閘連續三批實戰）。
- 修後實跑（主委 2026-09-11）：`test_verdictgate_p4.py` 28 passed；`test_synth_attribution_hook.py` 7 passed；`test_debt_clear.py` 30 passed；`handoffs/20260911-verdictgate-mutate-b4.py` UNCOVERED=0（15 條）。
- 本 synth 寫入時 `synth_attribution_hook`（新版）實跑放行＝第一次以自己的閘驗自己的收斂檔。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: `SYNTH_ATTR_MODULE` 宣稱僅供測試覆寫，但正式 hook 未以 `GOVERNANCE_TEST_HARNESS` 綁定；設定不存在或旁路模組時可靜默放行。
**碼證**: `scripts/synth_attribution_hook.sh:35-43` 直接採用環境覆寫且缺檔/非 1 rc 皆 exit 0；實跑 `env -u GOVERNANCE_TEST_HARNESS SYNTH_ATTR_MODULE=/private/tmp/vg-b4-r1-no-module.py bash scripts/synth_attribution_hook.sh`（stdin 指向現有 synth）→ `production_override_rc=0`。收票仍有 debt_clear 次級閘，但產出端必擋契約已失效。
**來源摘要**: scripts/synth_attribution_hook.sh#ad9c334c22dc; docs/VERDICTGATE_TODO.md#012a38a2888f
[MAJOR] 信心度=High；SPLITUNIFY 復工時同一環境可讓不合規 synth 在寫入端通過，後續才於收票失敗；若產出物先被消費，端點保護已破口。修正方向是僅在測試 harness 採用覆寫，正式路徑固定模組；模組自身 fail-open 可保留為已揭露的次級邊界。
## CODEX-R1-P1-02
**斷言**: 處置與 `延後→` 目標判定不是 token/目標語法的封閉比對：子字串可冒充處置，任意 TODO 子字串與多目標前綴可通過全量閘。
**碼證**: `scripts/_synth_attr.py:114-117,149-157` 用 `v in cell` 且僅做 `tgt in todo_text`，未驗 E-1…E-7/`Task N.N` 或拒絕 `、` 後續目標；獨立 probe stdout：`invalid_target=[]`, `multi_target=[]`, `substring_token=[]`；`fullwidth_paren` 反而錯誤擷取為 `E-4（理由`。因此 `延後→E-4、E-9`（TODO 含二者）、`延後→備忘`（TODO 含備忘）、`不採納` 可使 debt_clear 關閉本應拒絕的輪。
**來源摘要**: scripts/_synth_attr.py#8ef20ed5ab7c; scripts/governance_verdicts.json#1d64b0e5a9c2
[MAJOR] 信心度=High；不修時收票可把未定義處置或被截斷/漏檢的 deferred finding 視為已完成，SPLITUNIFY B5 復工同樣可帶著漏掉的第二目標前進。修正方向是對非 deferred token 做邊界/完整 token 判定，對 deferred 僅接受合法單一目標並逐目標精確匹配 TODO §E 或 Task；全形括號後說明需有明確分隔規則。
## CODEX-R1-P2-03
**斷言**: `test_41_hook_and_gate_agree_on_ids_target_quote` 沒有證明 hook 與 gate 的整合一致性，兩個關鍵斷言是同一函式自比，quote 只測全列已完成情境。
**碼證**: `tests/governance/test_verdictgate_p4.py:152-160` 使用 `sa.check_ids(doc) == sa.check_ids(doc)`、`sa.check_target(doc) == sa.check_target(doc)`，未呼叫兩個 shell wrapper；`check_quote20` 只以 `completed_only=True/False` 對全完成 fixture 比對。production wrapper 目前均指向模組，但測試可證偽性不足。
**來源摘要**: tests/governance/test_verdictgate_p4.py#912b27393cfef; scripts/_synth_attr.py#8ef20ed5ab7c
[MINOR] 信心度=High；目前程式碼路徑是共用模組，故不單獨阻擋收票；未補測試時，日後任一 wrapper 分叉仍可能全綠而把 hook/閘差異帶入收斂流程。修正方向是分別呼叫 hook/gate，對同一完整與草稿 fixture 比對預期錯誤類別/內容，並以 mutation 破壞其中一個 wrapper 驗證必紅。
REVIEW_ANSWERS_1_8: 1=五 ASSERT 對應 `test_41_id_in_table_absent_rc_nonzero`、`test_41_quote20_mismatch_rc_nonzero`、`test_41_disposition_absent_rc_nonzero`、`test_41_defer_target_missing_in_todo_rc_nonzero`、`test_41_all_good_rc_zero`；邊界①=`short_assertion_quotes_full_text`、②=`nfc_and_whitespace_tolerant_but_not_punctuation`、③=`two_rows_any_one_compliant_ok`。2=實作共用同模組，但 agreement test 是恆真自比，立場為未充分證明。3=正常 hook 無 token 與 debt_clear 全量閘皆會拒，無手動繞路；但 P1-02 的子字串冒充是實際縫。4=實跑 `…010` 與 `X…` 均 `False`。5=單項測試 1 passed，`Task 9.9` 對僅含 Task 4.1 TODO 會 rc=1；多目標/任意目標/全形括號結果見 P1-02。6=24 份逐份 rc=1；23 clear+1 abandon，現行 `_cmd_clear` 先判狀態故不再經 attribution。7=第二段大寫推導缺檔即不傳 TODO、defer 拒絕，fail-closed 可接受但命名約定脆弱。8=不可收 B4。
ASSUMPTIONS_VERIFIED: R10 三個 RECONCILE-STAMP 均 APPROVED；`bash scripts/debt_ledger.sh --has-open` rc=1（本輪 OPEN）；`_cmd_clear` line 564-584 狀態檢查先於 attribution。 TESTS_RUN: P4 `21 passed`；hook `7 passed`；debt_clear `30 passed`；指定歷史 24/24 attribution rc=1；Task 9.9 單測 `1 passed`；independent probes stdout 如 P1 findings；指定 completeness 命令被 PreToolUse 以 open_debt 擋在腳本前，無 script rc。
FAILURES_SEEN: 實跑未見既有測試失敗；獨立 probe 揭露 P1-01/P1-02。 SCOPE_CHANGES: 僅新增本交件檔，未改 code/tracked/data_cache；mutation 未跑以遵守 brief 禁改 tracked。 NUMERIC_OR_SCHEMA_IMPACT: 未改產品數值/schema；提出的是治理判定語意與測試覆蓋修正。
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r1-codex.md。 TMP_CLEANUP: 已移除本輪 `/private/tmp/vg-b4-r1-history.log`、`history-detail.log`、`one.log`；`/private/tmp/claude-501` 與 `/tmp/claude-501` 保留。
VERDICT: blocked
BLOCKED-BY: CODEX-R1-P1-01,CODEX-R1-P1-02
CLOSED:
STATUS: DONE
## COMPOSER-R1-P3-00

**斷言**: 本輪逐項核對 brief 必答 1–8、SPEC Task 4.1×5 ASSERT／邊界 ①②③、Q4/Q5/Q6 實跑與 p4／hook／debt_clear／mutation 測試後，composer 家族無 P0/P1 finding。

**碼證**: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed；`venv/bin/python -m pytest tests/governance/test_synth_attribution_hook.py -q` → 7 passed；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → UNCOVERED=0；`bash scratchpad/b4_q5_defer.sh` → `延後→Task 9.9` rc=1；歷史 synth 掃描 24/24 rc=1；`_id_in` 實跑 010／X- 前綴正確。RECHECK: 重跑上述命令 + 必答 1 表。

**來源摘要**: scripts/_synth_attr.py#8ef20ed5ab7c;scripts/reconcile_cluster_attribution_check.sh#8f1b90735e2b;scripts/synth_attribution_hook.sh#ad9c334c22dc;scripts/debt_clear.sh#47c5bdcc8d2d;tests/governance/test_verdictgate_p4.py#912b27393cfe;docs/VERDICTGATE_SPEC.md#d723f42d7194;docs/VERDICTGATE_TODO.md#012a38a2888f

[P3] 信心度=High。核對依據＝ASSERT↔test 表、hook/gate 讀碼、Q4 `_id_in` 實跑、Q5 defer 反例、Q6 24 份 gate 實跑 + debt_clear 呼叫點、mutation 全覆蓋；P2 殘留已列必答 4/5/8（不捏造 P0/P1）。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

---

ASSUMPTIONS_VERIFIED: p4 21/21；hook 7/7；debt_clear attribution 2/2；mutation UNCOVERED=0；Q4 `_id_in` 五案例；Q5 defer 七案例；Q6 歷史 24/24 rc=1；debt_clear 僅清債路徑呼叫 `_run_attribution`  
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed rc=0；`venv/bin/python -m pytest tests/governance/test_synth_attribution_hook.py -q` → 7 passed rc=0；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → UNCOVERED=0 rc=0；`bash scratchpad/b4_q5_defer.sh` → Task9.9 rc=1  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 review；新增 `scratchpad/b4_q5_defer.sh`、`scratchpad/b4_review_probe.sh` 為 VERIFY）  
NUMERIC_OR_SCHEMA_IMPACT: none  
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r1-composer.md  
TMP_CLEANUP: 已清 `/tmp/tmp.*`；保留 `/tmp/claude-501`

STATUS: DONE
## GROK-R1-P1-01

**斷言**: `check_disposition` 以 `tgt not in todo_text` 做子字串包含，故 `延後→Task`（以及被 `、，。；` 截成 `Task` 的 `延後→Task、9.9` 等）在 TODO 僅有 `Task 4.1` 時 gate 仍 rc=0——延後目標存在性 fail-open。

**碼證**: `_synth_attr.py:149-157`（`延後→([^|，。；、）)]*)`＋`tgt not in todo_text`）。VERIFY: `bash /tmp/vg-b4-r1-probe/run_bare_gate.sh` → gate_rc=0（row4=`延後→Task`，TODO=`### Task 4.1`）；同目錄 probe 對 `延後→Task、9.9`／`延後→E`／`延後→4.1`／`延後→Task 4` 皆 PASS_FAILOPEN。對照：`延後→Task 9.9` vs 僅 `Task 4.1` 仍紅（M15c 範圍）。RECHECK: 重跑 bare_gate；或 `check_disposition(parse(延後→Task), todo='### Task 4.1')` 須改為非空錯後再收 B4。

**來源摘要**: scripts/_synth_attr.py#8ef20ed5ab7c;tests/governance/test_verdictgate_p4.py#912b27393cfe;handoffs/20260911-VERDICTGATE-B4-REVIEW-R1-BRIEF.md#30505338ef5f;docs/VERDICTGATE_SPEC.md#d723f42d7194

[P1] 信心度=High。不改則：收斂檔可把找不到的延後目標寫成 `延後→Task`／標點截斷形，debt_clear ④ 放行 ⇒ finding「延後」無真實 TODO 錨，SPLITUNIFY／後續票復工時該項從機械追蹤消失——正是 Task 4.1／C-1 要閉的洞。修法見必答 8。

---

## GROK-R1-P2-01

**斷言**: `test_41_hook_and_gate_agree_on_ids_target_quote` 對 `check_ids`／`check_target` 是同呼叫自比恆真，對 quote 只在「已完成列」fixture 上比 True/False——不能證偽 hook.sh 與 gate.sh 包裝是否偏離。

**碼證**: `tests/governance/test_verdictgate_p4.py:152-160`；對照生產呼叫 `synth_attribution_hook.sh:38` vs `reconcile_cluster_attribution_check.sh:18`（同模組，測試未驅動兩包裝）。RECHECK: 將測試改為比 `run(...,"hook")` 與 `run(...,"gate")` 共享子集，或真呼叫兩支 bash。

**來源摘要**: tests/governance/test_verdictgate_p4.py#912b27393cfe;scripts/synth_attribution_hook.sh#ad9c334c22dc;scripts/reconcile_cluster_attribution_check.sh#8f1b90735e2b

[P2] 信心度=High。不改不會單獨造成現行銷帳 fail-open（實作確為單一模組）；回歸時雙包裝若分叉可能假綠。不擋在 P1 之後的獨立收案理由，但應修。

---

VERDICT: blocked
BLOCKED-BY: GROK-R1-P1-01
CLOSED:

---

ASSUMPTIONS_VERIFIED: p4 21/21；hook+xref+debt_clear 52/52；mutate-b4 UNCOVERED=0；歷史 24 synth 全 rc=1；`_id_in` 不誤中 010／X 前綴；`Task 9.9` 空白整詞仍紅；`延後→Task`／標點截斷對 `Task 4.1` TODO gate_rc=0（否證 assumed）；CLOSED early-return 在 attribution 之前（碼證）；epic 第二段推 TODO 缺檔 fail-closed
TESTS_RUN: `venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q` → 21 passed rc=0；`… test_synth_attribution_hook.py test_spec_xref_check.py test_debt_clear.py -q` → 52 passed rc=0；`venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py` → 9/9 COVERED UNCOVERED=0；hist 24× attribution_check → 24× rc=1；bare_gate `延後→Task` → rc=0
FAILURES_SEEN: none（審查過程；發現之 fail-open 為產品縫，非本輪測試回歸）
SCOPE_CHANGES: none（review-only；probe 僅 /tmp/vg-b4-r1-probe）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b4-review-r1-grok.md

STATUS: DONE
