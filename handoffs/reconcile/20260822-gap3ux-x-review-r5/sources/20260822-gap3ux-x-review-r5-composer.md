# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R5（COMPOSER）

task-id: 20260822-GAP3UX-X-REVIEW-R5  
brief: `handoffs/20260822-gap3ux-x-review-r5-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`（sha256 `64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`，1169 行；**尚未實作**）  
家族: COMPOSER | 輪次: R5

---

## 被當成事實的未驗證假設（§0）

| 宣稱 | 分類 | 本輪覆核 |
|---|---|---|
| SPEC sha256／行數與 brief 鎖定一致 | **fact-verified** | `shasum -a 256` → `64a22dc6…df228`；`wc -l` → 1169 |
| Phase 7 六維度三層巢狀路徑 | **fact-verified** | `python3 handoffs/20260822-gap3ux-x-review-r5-dims.py` 與 `facts.out` F-02 逐字一致 |
| `control_kind` enum=4／accepted=3 | **fact-verified** | `dims.py --counts`；契約 `event_import_contract.json` |
| `eventExport.ts` 五處寫死／`counterexample_kind` 未送 | **fact-verified** | facts.sh F-06 |
| `/search` 呼叫端未傳六維度 opts | **fact-verified** | facts.sh F-07；`page.tsx:522-527` |
| 三支機械閘 rc=0 | **fact-verified** | facts.sh F-14：`doc_format=0`／`ruling_sync=0`／`quant_std=0` |
| 41 Task 皆有「覆蓋風險」欄 | **fact-verified** | `grep -c "^- 覆蓋風險"` → 41；`grep -c "覆蓋風險：無"` → 0 |
| R4 十九條處置皆對症、未引入新矛盾 | **assumption，部分不成立** | 群集 A 之 V-11 與 Task 7.1/7.2 基準不一致；群集 C 之 Task 7.7 左界未扣 `decision_offset_bars`（見 **COMPOSER-R5-P1-01／02**） |
| §G S-1..S-8 涵蓋全部序列化歧義 | **assumption，本輪未反證** | S-1..S-8 與 `tables.py:88-180` 對照可執行；S-6 預設 `n_boot` 引用 tables 內建 500，與 `pipeline.py:98` 傳入 300 並存——golden 須顯式寫死（S-6 已要求） |
| Task 7.7 containment 足以擋特徵覆蓋不足 | **assumption，不成立** | 左界公式見 **COMPOSER-R5-P1-02** |

---

## R4 十九條之 CLOSED／OPEN（反例重跑判定）

| R4 ID | 群集 | 本輪 | 碼證摘要 |
|---|---|---|---|
| CODEX-R4-P0-01 | A | **部分 OPEN** | Task 7.0/7.1/7.2 三層驗證已寫；**V-11 L1137 仍比對 `contractAccepted` 全文**，未引用 `pathExclusions` ⇒ 與 7.1/7.2 矛盾（**COMPOSER-R5-P1-01**） |
| COMPOSER-R4-P0-01 | A | **部分 OPEN** | 同上；`accepted` 基準已入 7.1/7.2，V-11 未同步 |
| COMPOSER-R4-P0-02 | A | **CLOSED** | Task 7.0 補 opts＋round-trip；7.2 ②③ 與 mutation (c)(d) 覆蓋 B5 病因 |
| GROK-R4-P0-01 | A | **部分 OPEN** | 同 CODEX-P0-01（V-11 殘段） |
| CODEX-R4-P0-02 | E | **CLOSED** | Task 1.12 L518-544：`run_event_study_only()`、`event_split_plan` Optional、`ci` unavailable、禁假 split plan |
| CODEX-R4-P1-03 | B | **CLOSED** | §G S-1..S-8（L293-337）；Task 2.2 純引用 S-2/S-5（L634-637） |
| COMPOSER-R4-P1-03 | B | **CLOSED** | 複核同意 CODEX |
| GROK-R4-P0-02 | B | **CLOSED** | 複核同意；S-8 獨立 oracle 已列 |
| CODEX-R4-P1-04 | C | **CLOSED** | Task 7.6/7.7、V-14/V-15；§N #8/#10 撤回（L1166） |
| COMPOSER-R4-P1-01 | C | **CLOSED** | 複核同意 |
| COMPOSER-R4-P1-02 | C | **部分 OPEN** | Task 7.7 已寫 containment，但左界／換算未對齊 PIT（**COMPOSER-R5-P1-02**） |
| GROK-R4-P0-03 | C | **CLOSED** | §N 與 §C0 互斥已解；檔頭 L16-17 與 §N L1166 一致 |
| CODEX-R4-P1-05 | D | **CLOSED** | Task 7.1 邊界 L961-968：`/search` 僅 C/two_stage；CSV 四種全開 |
| COMPOSER-R4-P1-04 | D | **CLOSED** | 複核同意 |
| GROK-R4-P1-01 | D | **CLOSED** | Task 2.1b 深度公式 L604-614；V-12 六組 fixture |
| CODEX-R4-P1-06 | F | **CLOSED** | Task 7.5 L1034-1063：manifest context 唯一傳遞點、混值 fail-closed、`not_computed` schema |
| CODEX-R4-P1-07 | G | **CLOSED** | Task 1.10 信任邊界 L463-484；V-12⑥ 改名攻擊 fixture |
| GROK-R4-P1-02 | H | **CLOSED** | §D L129-134 已改寫小時命名；SYNC-FORBID 第 4 條；`spec_ruling_task_sync.sh` rc=0 |
| COMPOSER-R4-P2-01 | I | **CLOSED** | Task 6.0 L815 完整 `python3 -c`；`doc_format_precheck.sh` rc=0 |

**計數**：19 條中 **15 CLOSED**、**4 部分 OPEN**（皆落在群集 A 之 V-11 殘段，或群集 C 之 Task 7.7 左界）。

---

## 必查涵蓋面（brief 七項）

**1. 全棧三欄稽核**（規格層：現碼缺口＝本批施工範圍，但 SPEC 須寫清接線）

| 能力 | 後端 | 前端 UI | wiring | 判定 |
|---|---|---|---|---|
| 六維度（Phase 7） | ✅ 契約＋validator | ❌ 無控制項 | ❌ `page.tsx` 未傳 opts | Task 7.0–7.2 已列；**待實作** |
| IC 頁批次語意揭露 | ✅ `GET /case/events/{id}` 含 records | ❌ picker 只顯示 t0 | ❌ `onPick` 兩參數 | Task 7.6 已列 |
| Feature run 日期覆蓋 | ✅ manifest `time_range` | ❌ `RunInfo` 無欄 | ❌ IC 無交集檢查 | Task 7.7 已列；**公式有缺口**（P1-02） |
| `/search` 匯出 | ✅ `buildEventContractRecords` | ⚠️ opts 介面部分 | ❌ 呼叫端未傳 | Task 7.0–7.2 |
| D-7 registry | ❌ 未實作 | — | — | Task 1.10（待做） |
| `/data-preparation` CSV | ✅ import 路徑 | ⚠️ 六維度待接 | ⚠️ 待 Task 7.1 | 已列 |

**2. R4 新增 Task 7.0／7.6／7.7 與 §G S-1..S-8**：逐條可執行；S-1..S-8 有明確白名單／排序／omission／oracle 獨立性。Task 7.7 containment 左界與換算需補（P1-02）。

**3. §C0**：無放水語；`覆蓋風險：無`＝0；§N #8/#10 已撤回而非殘留放行。未見「留實作階段」繞過數值正確性（§G L295 僅為歷史敘事）。

**4. §P 41 Task**：機械閘 41/41 覆蓋風險欄齊；抽樣 Task 1.12／2.1b／6.0／7.2 驗證欄皆含可跑命令與 mutation。Task 7.5 與 Task 5.0 glossary 同步義務僅寫在 5.0「須同步」，7.5 自身無驗收——實作順序 5.2→7.5 時 V-10 可能假綠（**次要**，未單列 finding）。

**5. 實作順序**：7.0→7.1→7.2、4.2→7.5、5.2→7.5、3.2→3.3、4.3→5.3、4.1b→7.3、1.10→1.11→1.12 均在 SPEC 內具名；可行。

**6. §2 獵空殼**：未見 `python3 -c "..."` 佔位（Task 6.0 已修）；Task 驗證欄普遍含 `pytest`/`vitest`/`==` 斷言。

---

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

## Verdict：需修訂後定版

R4 十九條主體已落地（15/19 CLOSED），三支機械閘與 §G S-1..S-8 可執行性良好。尚餘 **2 條 P1**：V-11 與 Task 7.2 基準不同步（R4 群集 A 修補未淨）、Task 7.7 覆蓋左界未對齊 PIT 決策時點（R4 群集 C 新內容缺口）。修復後可 FROZEN；不建議逕行定版。

---

ASSUMPTIONS_VERIFIED: SPEC sha256=64a22dc6…1169 行；facts.sh 14 條 rc=0；dims.py 六維度路徑；三支閘 doc/sync/quant=0；覆蓋風險 41/41  
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`；`bash handoffs/20260822-gap3ux-x-review-r5-facts.sh`；`bash scripts/doc_format_precheck.sh`／`spec_ruling_task_sync.sh`／`quant_standard_check.sh`；`grep -c` 覆蓋風險  
FAILURES_SEEN: none（審查階段）  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（僅 review 產出）

產出檔：`handoffs/20260822-gap3ux-x-review-r5-composer.md`

STATUS: DONE
