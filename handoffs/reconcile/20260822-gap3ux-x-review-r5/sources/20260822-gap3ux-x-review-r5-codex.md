# GAP-3 UAT SPEC R5 — CODEX review

**R4 十九條逐條**: A(CODEX-R4-P0-01,COMPOSER-R4-P0-01,COMPOSER-R4-P0-02,GROK-R4-P0-01)=OPEN；B(CODEX-R4-P1-03,COMPOSER-R4-P1-03,GROK-R4-P0-02)=OPEN；C(CODEX-R4-P1-04,COMPOSER-R4-P1-01,COMPOSER-R4-P1-02,GROK-R4-P0-03)=OPEN；D(CODEX-R4-P1-05,COMPOSER-R4-P1-04,GROK-R4-P1-01)=OPEN；E CODEX-R4-P0-02=CLOSED；F CODEX-R4-P1-06=OPEN；G CODEX-R4-P1-07=OPEN；H GROK-R4-P1-02=CLOSED；I COMPOSER-R4-P2-01=CLOSED。
## CODEX-R5-P0-01
**斷言**: Task 7.0/7.1 可讓宣告的 entry/decision/mode 與 `label_value` 數值不一致，因匯出仍固定取 `future_${horizon}bar_return`。
**碼證**: `eventExport.ts:81-85,92-102` 不讀三個 opts；SPEC:902-904,910-918,1003-1004；修法＝共用可驗 label producer 或禁用未支援組合並加非預設值 exact golden。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; frontend/src/lib/eventExport.ts#b2024ac8970f。信心度=High。
## CODEX-R5-P0-02
**斷言**: `counterexample_kind` 是 optional、逐列 user 欄，卻被 Task 7.0/7.1 當成批次 scalar 選項；沒有 enum 外的 unset/混合列契約會污染或誤填反例分類。
**碼證**: contract:53-58,189-194；SPEC:886-893,906-919,928-950；修法＝逐列映射/僅 label=0、保留 omitted，並以 mixed a/b/c/missing fixture 驗收。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e。信心度=High。
## CODEX-R5-P0-03
**斷言**: `/search` 開放 `two_stage` 但 exporter 只產 t0 `positive_case` label，沒有兩段 producer/provenance；同樣 `source_file_digest` 排除 future 欄，rename/篩選後深度證據不足。
**碼證**: SPEC:149-168,460-472,962-968；`eventExport.ts:27-37,75-107`；`two_stage_search.py:210-228`；修法＝先禁 `two_stage` 或定義兩段 schema、producer digest、label/depth golden。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; frontend/src/lib/eventExport.ts#b2024ac8970f; api/routes/two_stage_search.py#1c801f1c12ed。信心度=High。
## CODEX-R5-P1-04
**斷言**: Task 7.7 的 coverage gate 尚不可執行：現行 `/features/runs` 未把 manifest `time_range` 帶進 `RunInfo`，且 `horizon_bars` 不能直接當毫秒加到時間戳。
**碼證**: `feature_factory_service.py:756-809,811-835` 只讀 feature_count/row_count/quality；`alignment.py:152-169` 以實際 bar 推 label_end；SPEC:1084-1108；修法＝明定 API wiring、TF/實際 bar 時間轉換與端點 exact fixture。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; api/services/feature_factory_service.py#de451ac20681; momentum/Analysis/event_samples/alignment.py#0a7cf0773cc4。信心度=High。
## CODEX-R5-P0-05
**斷言**: §G S-1..S-8 仍未定義從 Python dict 到 sha256 bytes 的完整 encoder（JSON separators/escaping/UTF-8/newline/特殊 float 等），G-2 不能跨實作者位元組級重現。
**碼證**: SPEC:293-337；`tables.py:171-180` 僅回傳 dict；修法＝寫死 canonical encoder、encoding 與 golden path/命令後再凍 hash。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; momentum/Analysis/event_samples/tables.py#e9856a0caa68。信心度=High。
## CODEX-R5-P1-06
**斷言**: Task 7.5 對 accepted 的 `platform_same_trigger_rule` 沒有全體組語意，並新增 `mixed_control_kind_in_batch` 卻未登記於任何契約 SoT，違反 §C/D-6。
**碼證**: contract:43-48；SPEC:266-268,1030-1055；`ic_report_contract.json:12-16` 無該 reason；修法＝指定三值分支與 owner contract，先加 schema/member test。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e; momentum/Analysis/contracts/ic_report_contract.json#808c611283ed。信心度=High。
## CODEX-R5-P1-07
**斷言**: R5 F-11 receipt 把不存在路徑的 grep 放在 `grep | sed` 後，未開 pipefail 仍報 rc=0，故「14 條皆可重跑」不成立。
**碼證**: `bash ...facts.sh`→F-11 `[rc=0]` 且 stderr `No such file`；`set -o pipefail; grep ... momentum/Analysis/case_search_engine.py | sed ...`→rc=2，正確檔為 `momentum/DataExtraction/case_search_engine.py`；修法＝正確路徑＋pipefail＋expected-match assertion。**來源摘要**: handoffs/20260822-gap3ux-x-review-r5-facts.sh#8b8ac09e1c9a; handoffs/20260822-gap3ux-x-review-r5-brief.md#43a866243dfb。
## CODEX-R5-P1-08
**斷言**: §A 同時把 A-6 標為「請使用者於白話閘確認」與「待使用者確認：無」，但 R5 brief 未提供該 user-visible 決策 receipt，不能把它當已驗證事實凍結。
**碼證**: SPEC:205,213-214；brief 明定審查標的/方法但未列 A-6 confirmation receipt；修法＝附白話閘逐字裁決，或維持 pending 並禁止 FROZEN。**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1; handoffs/20260822-gap3ux-x-review-r5-brief.md#43a866243dfb。信心度=High。
## Verdict：需修訂後定版
