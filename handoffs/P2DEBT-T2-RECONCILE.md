# P2DEBT-T2 reconcile(SPEC+TODO 三件套閉合,派實作前)
Task-id: p2debt-t2 | Date: 2026-07-11 | Chair: Claude

## 定稿
- SPEC 正式版=docs/P2DEBT_T2_DCREDIRECT_SPEC.md(源 R4;template_check spec PASS;正式化補機檢錨點 3 處+§G sha256 字樣顯式化,語意零改動)。
- TODO 正式版=docs/P2DEBT_T2_DCREDIRECT_TODO.md(源 R6=R5 內容+結構整備;template_check todo PASS;零改動)。

## 審查鏈(全檔 register-output,sha 見 audit.log)
- SPEC:R1 雙家 BLOCK(grok 3B+5M/codex 6B)→R2 Composer 全改→複驗 grok 1 open/codex 6 open→R3 Composer(+可執行原型)→複驗 grok 2 新 B/codex TLS 跨執行緒架構洞→**斷路器換手 Codex R4**(process-global gate+to_thread 原型 8/8)→grok+composer 雙 STAMP。
- TODO:R1 Composer→雙 BLOCK→R2 Composer→grok NEW-B1/B2(同類兩輪未閉)→**斷路器換手 Grok R3**→codex 3 finding(§8 masking/§7 dirty-overlap/2.5 assert)→R4 Grok→codex Task 4.1 fail-open→R5 Grok→codex STAMP+composer diff STAMP→R6 結構整備(機檢 PASS)→grok+codex diff STAMP。
- 裁定:升級「大」(RISK-HIT a,b);A/B→B 案;Run C hermetic root;seam 完整性斷言;digest 全集。

## 實作派工參數
- 執行端=Codex(四調行;SPEC 作者=codex 可實作,審查腿=grok+composer 不自審);scope=TODO §C allowed files;禁改生產 persist 語意;pre-dirty 快照由主委持有 /tmp/p2debt-t2-pre-dirty.txt(派工前重拍)。
- 驗收=TODO Final Acceptance §1-§8(digest 全集 hermetic+golden A/B/C sha256+isolation subprocess+mutation canary+scope delta=whitelist∖pre-overlap+run_step any-fail exit 契約)。
- 委員請驗:本檔敘事 vs 你們各自輪次輸出;正式版兩檔頭注「零語意改動」屬實(diff 草稿 vs docs/)。

## Verdict
Verdict: APPROVE — 三件套審查鏈閉合,全數委員輪次 APPROVED

## 戳記
RECONCILE-STAMP: codex APPROVED 2026-07-11 sha256:8119fb8d7e45860e9378e08cf245901455d2d5605e6066d0ac48ba20c31f1770 task:p2debt-t2
RECONCILE-STAMP: composer APPROVED 2026-07-11 sha256:8119fb8d7e45860e9378e08cf245901455d2d5605e6066d0ac48ba20c31f1770 task:p2debt-t2
