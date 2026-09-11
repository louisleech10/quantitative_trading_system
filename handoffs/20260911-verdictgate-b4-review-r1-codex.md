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
