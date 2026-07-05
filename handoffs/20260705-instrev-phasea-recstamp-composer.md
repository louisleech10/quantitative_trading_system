# instrev-phasea-recstamp-composer — Composer stamp-review 收尾

> task-id: instrev-phasea-recstamp-composer | 2026-07-05

## 核對摘要

### BLOCKING 收錄與落地
- **ADV-COMPOSER-3**: reconcile §B 忠實採納(12 真實 baseline token + 分 CLAUDE/合約表)。已落 SPEC §V ③、TODO Task 2.3、§B Gate [A-4] 迴圈。舊臆想 token(`繁體`/`VERIFY`/`先問`)已移除。
- **ADV-COMPOSER-4**: reconcile §B 忠實採納。SPEC Task 2.2 L62、TODO Task 2.2 L79 均已改 `grep -nE "Codex.*實作|Composer.*實作|GPT-5.5.*實作"`(有牙)。§B Gate 未列此 grep( reconcile E.4 亦未要求;Task 2.2 驗證欄承擔)。

### 其餘裁決
- COMPOSER-1 MAJOR→MINOR 收窄但 §A 措辭已修:可接受。
- COMPOSER-2/5/6/7/10/11/12:採納合理,已見 SPEC/TODO。
- COMPOSER-8/9:TODO 已修;SPEC Task 3.1/1.2 **未同步**(見下)。
- 兩項 BLOCKING **未被降級或抹除**。

### 拒絕理由(戳記 REJECTED)
1. `docs/INSTREV_PHASEA_SPEC.md:69` Task 3.1 改法仍寫 `Codex 實作+Composer review`,與 reconcile §E.1、SPEC §A L20、TODO Task 3.1 L99 的 **Composer 實作+Codex review**(07-05 額度切換)矛盾。
2. SPEC Task 1.2 邊界仍「內文引用→BLOCKED」;reconcile CONV-3/C 與 TODO Task 1.2 已改為檔名級→SCOPE_CHANGES。

### body-hash
`bash scripts/reconcile_body_hash.sh handoffs/20260705-INSTREV-PHASEA-ADV-RECONCILE.md` → `6a14a0f69f38203e38530f3d0d2489b8f535d21b6f6d72e45e2893b2ce8452c5`(與任務指定一致)

ASSUMPTIONS_VERIFIED: reconcile body-hash;12 baseline token 11/12 字面+`不得`+`跳` 替代;SPEC/TODO 逐段對照
TESTS_RUN: reconcile_body_hash.sh PASS;grep baseline tokens CLAUDE.md;SPEC/TODO/COMPOSER-3/4 對照
FAILURES_SEEN: none(審閱任務)
SCOPE_CHANGES: none(僅 append reconcile 戳記行+本 handoff)
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE

---

## R2 重審(2026-07-05, task: instrev-phasea-recstamp-composer-r2)

### R1 兩項 BLOCKING 閉合確認
1. **選層對調**: SPEC §A L20/L22、§P Task 3.1 L69 改法、TODO Task 3.1 L99 皆為 `Composer 2.5(cursor-agent)實作 + Codex(codex)code review`;無殘留「Codex 實作+Composer review」。
2. **Task 1.2 邊界**: SPEC L48 與 TODO L55 一致——檔名級引用→**不 BLOCKED**,SCOPE_CHANGES 註記;僅內文段落/數值引用才 BLOCKED。

### body-hash
`bash scripts/reconcile_body_hash.sh handoffs/20260705-INSTREV-PHASEA-ADV-RECONCILE.md` → `6a14a0f69f38203e38530f3d0d2489b8f535d21b6f6d72e45e2893b2ce8452c5`

ASSUMPTIONS_VERIFIED: reconcile body-hash;SPEC §P Task3.1/§A/TODO Task3.1 選層一致;SPEC/TODO Task1.2 邊界一致
TESTS_RUN: reconcile_body_hash.sh PASS;grep SPEC/TODO 選層與 Task1.2 邊界欄
FAILURES_SEEN: none
SCOPE_CHANGES: none(僅 append reconcile 戳記一行+本 handoff R2 節)
NUMERIC_OR_SCHEMA_IMPACT: none

STATUS: DONE
