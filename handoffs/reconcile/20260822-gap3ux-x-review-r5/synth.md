# Reconcile — 20260822-gap3ux-x-review-r5

**來源** 20260822-gap3ux-x-review-r5-codex.md, 20260822-gap3ux-x-review-r5-composer.md, 20260822-gap3ux-x-review-r5-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**輪次事實**：三家全員產出，Verdict 三家一致「需修訂後定版」。findings 13 條
（codex 8／composer 2／grok 3）。收斂 R1 24 → R2 7 → R3 18 → R4 19 → **R5 13**。

🔴 **本輪最重要的統計事實**：13 條中 **5 條為主委 R4 修訂自行引入**（群集 A／C／D／J），
形態高度一致——**「改了某處的權威定義，未同步所有複述它的位置」**。
`feedback_cross_reference_sync` 載此類錯已犯 8 次，本輪為**第 9 次**，
且發生在主委剛為前 8 次做完機械閘之後：現有 `spec_ruling_task_sync.sh` 只驗
§D→§P 之引用存在性與宣告式禁用語，**完全不檢查 §P↔§V 一致性**，正是 V-11 破口所在。

**處置總則（使用者 2026-08-22 裁定）**：13 條**全數 ACCEPT**，但**修法不由主委自訂**——
改派 consult 輪請三家**逐條指定確切修法**，主委照抄實作。
理由＝連兩輪（R4 造 3 條、R5 造 5 條）自傷皆出自「主委選擇怎麼修」這一步。
consult 輪之每條回覆須含**「本改動必須同步哪些其他位置」**欄（直接對症本輪之 5 條自傷）。

### 群集 A — §V 與 §P 雙源：V-11 仍寫 `contractAccepted`（**主委 R4 自傷**）
**ID**：COMPOSER-R5-P1-01、GROK-R5-P0-01（**兩家獨立命中**）
**內容**：R4 把 Task 7.1／7.2 之權威集合改為 `selectable(path,dim)=accepted−pathExclusions`，
但 §V 之 V-11 通過條件仍為 `new Set(selectableOptions) === new Set(contractAccepted)`。
對 `/search`×`scenario` 兩者不相等（accepted 4 值 vs selectable 2 值）
⇒ 照 V-11 實作會**強迫 UI 啟用 A／B**，推翻 Task 7.1「邊界」之路徑級限制、重開 label 語意漂移。
grok 另指出 Task 7.2 之標題與覆蓋風險亦仍寫「＝契約 accepted」，**雙源共三處**。
**處置＝ACCEPT；修法交 consult**。併問結構題：§V 是否應由「複述斷言」改為「純引用 Task ID」，
並加機械閘擋「§V 出現與 §P 重複之斷言字面」——此為本類錯之根因修法，由三家裁而非主委自定。

### 群集 B — §G S-1..S-8 仍不足以跨實作者位元組重現
**ID**：CODEX-R5-P0-05
**內容**：R4 之 S-1..S-8 定義了欄位白名單、排序、omission、NaN／浮點語意，
但**未定義從 Python dict 到 sha256 bytes 之完整 encoder**（JSON separators、escaping、
UTF-8 處理、結尾 newline、特殊 float 之實際位元組形式）⇒ G-2 仍不可跨實作者位元組級重現。
**處置＝ACCEPT；修法交 consult**（須給出可直接寫進 SPEC 之 encoder 規格）。

### 群集 C — 三組報酬表與 §G S-1「頂層八鍵不得增減」互斥（**主委 R4 自傷**）
**ID**：GROK-R5-P1-01
**內容**：Task 7.5 要求報酬表改正／反／全體三組（含全體組 `{"status":"not_computed",...}`），
而 R4 新寫之 S-1 凍結頂層八鍵「不得增減」、S-7 固定 horizon 區塊鍵集
⇒ 全文未定義三組掛在何處（`strata.by_label`／三次呼叫外包／新頂層皆無裁定），Agent 無法唯一實作。
另 Task 7.5 覆蓋風險只要求「manifest 加 `control_kind` 後 G-2 byte 不變」，
未如 Task 4.2 要求「結構／數值輸出變更時同步更新 G-2」。
**處置＝ACCEPT；修法交 consult**（三種掛法擇一並說明為何，且須同時給 G-2 之更新規則）。

### 群集 D — `horizon_bars → ms` 之 timeframe 來源未定（**主委 R4 自傷；與 future72 同型**）
**ID**：GROK-R5-P1-02、CODEX-R5-P1-04
**內容**：Task 7.7／V-15 之 containment 右界寫 `max(t0) + horizon_bars 之毫秒數`，
但未定義換算所用之 timeframe 來源（事件列 `timeframe`／run 之 tf／批內多 TF 取 max／拒收）
⇒ 選 1h 或 12h 得到相反之放行／拒絕。grok 明指此與 R3 之 future72 單位錯**同型**。
codex 另指 Task 7.7 目前**不可執行**：`/features/runs` 未把 manifest `time_range` 帶進 `RunInfo`。
**處置＝ACCEPT；修法交 consult**（須給出唯一之 tf 來源規則與批內多 TF 之處置）。

### 群集 E — Task 7.7 左界未扣 `decision_offset_bars`
**ID**：COMPOSER-R5-P1-02
**內容**：左界寫 `run.time_range.start <= min(t0)`，未扣 `decision_offset_bars`；
而 IC 特徵截止規則為 `max_close_ms <= decision_at`、`decision_at = t0 往前第 k 根`
⇒ `k > 0` 時存在「run 覆蓋 `[min(decision_at), min(t0)]` 卻通過 gate」之 fail-open 窗口。
**處置＝ACCEPT；修法交 consult**。

### 群集 F — 匯出仍固定取 `future_${horizon}bar_return`，與宣告之 entry／mode 可不一致
**ID**：CODEX-R5-P0-01
**內容**：Task 7.0／7.1 讓使用者宣告 `entry_price_semantic`／`decision_offset_bars`／
`label_return_mode`，但匯出仍固定取 `future_${horizon}bar_return`
⇒ 宣告值與 `label_value` 之實際數值語意可以不一致（宣告 `next_open` 而數值仍是觸發根 close-to-close）。
**處置＝ACCEPT；修法交 consult**（此條觸及數值正確性，依 §C0 不得降殘留）。

### 群集 G — `counterexample_kind` 是逐列選填欄，卻被當批次 scalar 選項
**ID**：CODEX-R5-P0-02
**內容**：契約中 `counterexample_kind` 位於 `optional_fields`、為**逐列使用者填寫**之欄
（`unclassifiable` 不可匯入），Task 7.0／7.1 卻把它接成批次 scalar 選項；
且無 unset／混合列之契約 ⇒ 會污染或誤填反例分類。
**處置＝ACCEPT；修法交 consult**。

### 群集 H — `/search` 開放 `two_stage` 但同樣無 producer
**ID**：CODEX-R5-P0-03
**內容**：R4 之路徑級限制只擋 A／B，放行 `two_stage`；但 exporter 對 `two_stage` 同樣只產
t0 `positive_case` label、無兩段 producer／provenance ⇒ 同一語意漂移未被擋住。
codex 另指 `source_file_digest` 排除 future 欄，rename／篩選後之深度證據仍不足。
**處置＝ACCEPT；修法交 consult**。

### 群集 I — `mixed_control_kind_in_batch` 未登記契約 SoT；`platform_same_trigger_rule` 無全體組語意
**ID**：CODEX-R5-P1-06
**內容**：R4 於 Task 7.5 新增 reason `mixed_control_kind_in_batch` 卻**未登記於任何契約 SoT**，
違反 §C「契約唯一真相源」與 D-6；且 `accepted` 之第三值 `platform_same_trigger_rule`
在 Task 7.5 之全體組語意**未定義**（只寫了 same_trigger 與 other 兩種）。
**處置＝ACCEPT；修法交 consult**。

### 群集 J — `facts.sh` F-11 未開 pipefail ⇒ 「14 條皆可重跑 rc=0」不成立（**主委自傷**）
**ID**：CODEX-R5-P1-07
**內容**：主委自製之 receipt 產生器把不存在路徑之 `grep` 放在 `grep | sed` 之後，
未開 `pipefail` ⇒ 仍報 rc=0 ⇒ brief 所宣稱之「14 條 fact 皆可重跑」**不成立**。
此即 CLAUDE.md 已載之「`cmd | head` 讀到的是 head 的 rc」同一坑，主委在自己的 receipt 工具上再犯。
**處置＝ACCEPT，主委直接修**（此條為工具 bug 而非 SPEC 判斷，無須交 consult）：
`facts.sh` 加 `set -o pipefail`，並對每條 fact 之命令逐一重跑驗 rc。
**已完成**：加 `pipefail` 後立即暴露 F-11 指向不存在路徑
（`momentum/Analysis/case_search_engine.py`，實為 `momentum/DataExtraction/`），
修正後 `bash handoffs/20260822-gap3ux-x-review-r5-facts.sh` rc=0、14/14 條逐條 rc=0。
VERIFY-EXEMPT:session-probe:20260822-r5-facts-pipefail（重現法＝直接重跑該腳本並取 rc）

### 群集 K — §A 之 A-6 自相矛盾
**ID**：CODEX-R5-P1-08
**內容**：§A 同時把 A-6 標為「請使用者於白話閘確認」與「待使用者確認：無」，
兩者互斥；且 R5 brief 未提供該 user-visible 決策 receipt ⇒ 不得當已驗證事實凍結。
VERIFY-EXEMPT:doc-example:gap3ux-r5-cluster-K（本列為委員 finding 之轉述，
重現法＝`grep -n "A-6\|待使用者確認" docs/GAP3_EVENT_UX_SPEC.md`）
**處置＝ACCEPT；修法交 consult**（併問：此類「需使用者確認」項在 SPEC 中之正確標法）。

---

### 未採納 / 降級
無。13 條全數 ACCEPT，0 條 REJECT、0 條降級為具名殘留（§C0 條文 2）。

Verdict：需修補後合併（13 條全數 ACCEPT；**修法由 consult 輪三家指定、主委照抄**，
其後派 R6 複審，不得逕行 FROZEN）

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R5-P1-01

**斷言**: R4 群集 A 宣稱 V-11 已改寫為三層驗證且比對基準為 `accepted` 減 `pathExclusions`，但 §V 之 V-11 集合層仍要求 `new Set(selectableOptions) === new Set(contractAccepted)`，與 Task 7.1/7.2 之 `selectable(path,dim)` 定義矛盾；實作者若以 V-11 為權威會在 `/search` 之 `scenario` 上假綠（應僅 {C,two_stage} 可操作）。

**碼證**: `nl -ba docs/GAP3_EVENT_UX_SPEC.md | sed -n '933,943p;974,987p;1137p'` → Task 7.1 定義 `selectable=accepted−pathExclusions`、Task 7.2 ① 斷言 `selectable(path,dim)`；V-11 通過條件仍寫 `contractAccepted` 且未提 `path`／`pathExclusions`。反例：`/search`+`scenario` 之 selectable 長度 2、accepted 長度 4，依 V-11 字面必紅、依 Task 7.2 必綠。RECHECK：重跑上述 sed；對照檔頭群集 A 落點 L27。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1

[MAJOR] 信心度=High。R4 群集 A 處置**未修淨**：Task 7.1/7.2 已對，V-11 殘留 R3 基準用語。修法：V-11 集合層改為「`selectable(path,dim)` 與 UI enabled 集合相等」，通過條件與 Task 7.2 ① 逐字對齊；mutation 增「清空 `pathExclusions` 湊足 scenario 四值」須紅。

---

## COMPOSER-R5-P1-02

**斷言**: Task 7.7 之 containment 左界 `run.time_range.start <= min(t0)` 未扣除 `decision_offset_bars`，與 IC 特徵截止規則 `max_close_ms <= decision_at`（`decision_at = t0 往前第 k 根`）不一致；當 k>0 時存在 run 覆蓋 `[min(decision_at), min(t0)]` 卻通過 gate、送 IC 後特徵區間不足之 fail-open 窗口。

**碼證**: Task 7.7 L1090-1091 左界僅 `min(t0)`；`alignment.py:65-78` `_decision_idx(t0_idx,k)=t0_idx-k`、`_select_cutoff_idx` 取 `close_ms <= decision_at`；`ic_feed.py:75-76` `decision_time_rule=t0_open_minus_k_bars`、`feature_cutoff_rule=max_close_ms_le_decision_at`。反例：k=3、bar=1d、`min(t0)=T`，則 `min(decision_at)=T-3d`；若 `run.start=T-2d` 則滿足 `start<=min(t0)` 但不滿足 `start<=min(decision_at)`。RECHECK：`sed -n '1088,1092p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '65,78p' momentum/Analysis/event_samples/alignment.py`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1；momentum/Analysis/event_samples/alignment.py#6f8d8418dbe0；momentum/Analysis/event_samples/ic_feed.py#f03b11fe7a8b

[MAJOR] 信心度=High。屬 §C0 條文 2 之資料正確性類，不得殘留放行。修法：左界改為 `run.start <= min(decision_at_ms)`（批內逐列依契約 `decision_offset_bars` 與 anchor TF 換算）；V-15 增 fixture：k=3 且 run.start 介於 decision_at 與 t0 之間 ⇒ fail-closed。右界 `horizon_bars`→毫秒亦應引用與 Task 2.1b 相同之 `hours_per_bar(tf)`，避免多 timeframe 批次各說各話。

---

## GROK-R5-P0-01

**斷言**: V-11 之通過條件仍要求 `new Set(selectableOptions) === new Set(contractAccepted)`（手段欄亦寫「vs 契約 accepted」），而 Task 7.1／7.2 正文之權威集合為 `selectable(path,dim)=accepted−pathExclusions`；對 `/search`×`scenario` 兩者不相等（accepted={A,B,C,two_stage}，selectable={C,two_stage}）。照 V-11 實作會迫使 UI 啟用 A／B，直接推翻 Task 7.1「邊界」之路徑級限制並重開 label 語意漂移；Task 7.2 標題與覆蓋風險仍寫「＝契約 accepted／比對基準為 accepted」加重雙源。

**碼證**: `sed -n '1137p' docs/GAP3_EVENT_UX_SPEC.md` → 通過條件含 `contractAccepted`；`sed -n '933,938p;972,988p' docs/GAP3_EVENT_UX_SPEC.md` → `pathExclusions` 封閉一筆 `('/search','scenario')→{A,B}`，且 7.2①斷言為 `selectable(path,dim)`。反例演算：accepted≠selectable。RECHECK：同上 sed；對照 Task 7.1 L961-969 邊界原文。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1

[BLOCKING] 信心度=High。會怎麼失敗：Agent 以 §V 為驗收 SoT 啟用 A／B；或 7.2 與 V-11 兩閘互打（一紅一綠）而放寬 pathExclusions。修法：V-11 手段／通過條件一律改 `selectable(path,dim)`（含路徑對照）；Task 7.2 標題與覆蓋風險同步改掉裸 `accepted` 字樣；mutation 保留「清空 pathExclusions⇒紅」。＝R4 群集 A／D **修補未修淨**（GROK-R4-P0-01 PARTIAL）。

---

## GROK-R5-P1-01

**斷言**: Task 7.5 要求報酬表改為正例／反例／全體三組（含全體組 `{"status":"not_computed","reason":...}`），但 §G S-1 凍結頂層八鍵「不得增減」、S-7 固定 horizon 區塊鍵集為統計欄＋`ci`，全文未定義三組嵌在既有八鍵何處（`strata.by_label`／三次呼叫外包／新頂層皆無裁定）；同時 Task 7.5 覆蓋風險只要求「manifest 加 `control_kind` 後 G-2 byte 不變」，未如 Task 4.2 要求結構／數值輸出變更時同步更新 G-2——Agent 無法唯一實作又可位元組證偽。

**碼證**: S-1 L299-301；S-7 L329-333；Task 7.5 L1030-1061（無任何 `S-` 引用）；V-13 L1141 只驗列數／n／`not_computed`、無序列化位置；現行 `tables.py` 回傳單一模組八鍵（至 strata.by_scenario），無 by_label。RECHECK：`sed -n '299,337p;1030,1061p;1141p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '170,195p' momentum/Analysis/event_samples/tables.py`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1；momentum/Analysis/event_samples/tables.py#e9856a0caa68

[MAJOR] 信心度=High。會怎麼失敗：合法實作產生不同頂層形狀／不同 hash；或為保 G-2 不變而把三組只做前端切分、後端仍全批混算（與 7.5 驗證②③衝突時再放寬斷言）。修法：在 S-1／S-7（或新 S-9）寫死三組容器位置與 `not_computed` 替代 block 之規則；Task 7.5／V-13 改為引用；並明示三組上線＝D-4 合法輸出變更、須同 commit 更新 G-2。＝R4 群集 B 在 7.5 面之**新缺口**。

---

## GROK-R5-P1-02

**斷言**: Task 7.7／V-15 之 containment 右界寫 `max(t0) + horizon_bars 之毫秒數 <= run.time_range.end`，但未定義 `horizon_bars→ms` 之 timeframe 來源（事件列 `timeframe`／run 之 tf／批內多 TF 時取 max／拒收），Agent 可選 1h 或 12h 換算得到相反的放行／拒絕結果；此為與 future72 單位錯同型之不可唯一執行缺口。

**碼證**: Task 7.7 L1090-1091；V-15 L1140③；對照 Task 2.1b L609 對小時欄有 `hours_per_bar(tf)` 而 7.7 無對等式。實批 `20260822T011331Z-eb210a16` 全為 `12h`、horizon=3（換算敏感）。`RunInfo` L116-133 確無 `time_range`；legacy `feature_reader.py:455` 為 `{None,None}`（7.7④已覆蓋）。RECHECK：`sed -n '1084,1108p;1140p' docs/GAP3_EVENT_UX_SPEC.md`；`sed -n '116,133p' api/models/feature_factory_models.py`。

**來源摘要**: docs/GAP3_EVENT_UX_SPEC.md#64a22dc689b1；api/models/feature_factory_models.py#fb5f998d5d4c；momentum/FeatureEngineering/feature_reader.py#f03b11fe7a8b

[MAJOR] 信心度=High。會怎麼失敗：12h×3 根應加 36h，若誤用 1h→只加 3h⇒假綠放行末段無特徵之事件；多 TF 批則左右界各實作各話。修法：寫死 `ms = horizon_bars * bar_duration_ms(tf)`，`tf` 取自事件列；批內多 TF ⇒ 對每列各自檢查或 fail-closed（擇一寫死）；V-15 加 12h vs 1h 對照 fixture。

---

