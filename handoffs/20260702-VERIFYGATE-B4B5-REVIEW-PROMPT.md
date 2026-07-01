# B4+B5 Codex adversarial code review 指派

Composer 2.5 已實作驗收防偽閘 B4（TODO Task 4.1-4.4）與 B5（Task 5.1-5.3）。你做**跨家族 adversarial code review**（作者不自審），目標=獵漏繞過面，不是確認式 review。

## 範圍（未 commit 的工作樹 diff + 新檔）
- `git diff scripts/gate.sh scripts/mutation_probe_check.sh scripts/reconcile_stamps_check.sh scripts/template_check.sh scripts/verification_claim_check.py`
- 新檔:`scripts/verify_audit_chain.py`、`scripts/verify_task_provenance.py`、`templates/RESULT_TEMPLATE.md`、`tests/governance/test_verify_gate_b4.py`、`test_verify_gate_b5.py`
- 規格:`docs/VERIFY_GATE_TODO.md` Task 4.1-4.4 / 5.1-5.3、`docs/VERIFY_GATE_SPEC.md` P4/P5
- 實作端收尾:`handoffs/20260701-VERIFYGATE-B4-composer.md`、`-B5-composer.md`

## 必審攻擊面（每項給 BLOCKING / NON-BLOCKING / PASS + 反例）
1. **Task4.1 行為不變真偽**:mutation_probe_check.sh 接 run_with_receipt 後,PASS/FAIL 判定、exit code、對外訊息是否真的不變?receipt 失敗時會不會把紅判成綠(或反之)?
2. **Task4.2/4.3 provenance 可偽造面**:自寫 fake-ADV.md / 自 append 戳記,新檢查真擋得住?`waived:` 逃生口會不會變成萬能繞過?
3. **Task4.4 audit chain**:TAMPER 偵測可被「改 receipt+同步改審計事件」繞過嗎(誠實邊界要明列)?
4. **Task5.1 枚舉欄位**:`RUNTIME_CHECK=PASS` 無 RECEIPTS 真 FAIL?大小寫/全形/註解行變體繞過?
5. **Task5.2 fingerprint 衝突**:先綠後紅未標 SUPERSEDED 真擋?fingerprint 歸一化可被空白/同義詞繞過?
6. **Task5.3 FACT-RECEIPT**:「已確認」行偵測的誤報/漏報;grandfather 設計有沒有把新 SPEC 也放掉?
7. **測試有無牙齒**:test_verify_gate_b4/b5 的斷言是否可證偽(改壞實作會紅)?有無自指 oracle?
8. **既有流程回歸**:Claude 已親驗 49 passed + reconcile/template 現行檔 PASS;你複核測試覆蓋是否足以保證。
9. **已知疑點**:agent 開發時把 4 筆 `mutation-test_b4_*` fixture receipt 寫進真實 `.claude/gate/verify_audit.log` 與 `handoffs/run_receipts/`——判定:可接受殘留 or 須清除 or 暴露隔離缺陷?

## 輸出
寫 `handoffs/20260702-VERIFYGATE-B4B5-REVIEW-CODEX.md`:每 finding 給 檔:行號+反例+建議修法,分 BLOCKING/NON-BLOCKING;結尾 `VERDICT: APPROVED` 或 `VERDICT: CHANGES_REQUIRED`。最後輸出一行 STATUS: DONE。
