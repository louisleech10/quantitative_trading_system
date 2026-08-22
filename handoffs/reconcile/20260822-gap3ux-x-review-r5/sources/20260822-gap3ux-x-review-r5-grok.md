# GAP-3 事件型 UAT 缺口修補 SPEC — 對抗審 R5（GROK）

TASK_ID: 20260822-GAP3UX-X-REVIEW-R5  
FAMILY: GROK  
brief-kind: review  
brief: `handoffs/20260822-gap3ux-x-review-r5-brief.md`  
標的: `docs/GAP3_EVENT_UX_SPEC.md`  
sha256（開工第一件事重跑）: `64a22dc689b18b180a72c41c8f232152e6c4739bd3a73a28bd40f55d222df228`（與 brief 鎖定值相符；1169 行）  
SCOPE: review-only；禁改碼、禁改 SPEC。

## Verdict：需修訂後定版

R4 十九條之**原病灶**多數已以反例重跑判定 **CLOSED**（含我方五條與他家複核同意項）。  
但 R4 修訂**自行引入／未修淨**三處，足以阻擋 Frozen：

1. **V-11（及 Task 7.2 標題／覆蓋風險）仍以 `contractAccepted`／裸 `accepted` 為集合閘**，與 Task 7.1／7.2 正文之 `selectable = accepted − pathExclusions` 互斥——照 V-11 實作會被迫在 `/search` 啟用 A／B，**重開**剛關閉的語意漂移（群集 D）。
2. **Task 7.5 三組結構未映射到 S-1..S-8**，且覆蓋風險只談 manifest 加欄「G-2 不變」，未要求結構變更時同步 S-1／重凍——重開序列化歧義（群集 B 同類）。
3. **Task 7.7 右界 `horizon_bars 之毫秒數` 未定 timeframe 換算**（含多 TF 批）——單位類缺口，與 future72 同病型。

修完上列後方可 Frozen。

---

## 0. 標的指紋與 fact 重跑

| 項 | 結果 |
|---|---|
| `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md` | `64a22dc689b1…222df228`＝brief 鎖定值 |
| `wc -l` | 1169 |
| `bash handoffs/20260822-gap3ux-x-review-r5-facts.sh` | rc=0；`diff` vs `facts.out` **空**（byte 一致） |
| `python3 handoffs/20260822-gap3ux-x-review-r5-dims.py{, --counts}` | 六維度三層級；control_kind enum=4／accepted=3 |
| `grep -c "覆蓋風險：無"` / `^- 覆蓋風險` | **0**／**41** |
| 三支機械閘 | doc_format／ruling_sync／quant_standard 皆 rc=0 |

---

## 1. R4 十九條 CLOSED／OPEN（反例重跑，非「有寫」）

### 我方 GROK-R4

| R4 ID | 本輪 | 反例／碼證 |
|---|---|---|
| **GROK-R4-P0-01**（群集 A／D） | **PARTIAL → 見 GROK-R5-P0-01** | Task 7.0／7.1／7.2 正文已改三層＋`selectable`＋round-trip；**但 V-11 通過條件仍寫 `contractAccepted`**，與 pathExclusions 反例不相容 |
| **GROK-R4-P0-02**（群集 B／F） | **PARTIAL → 見 GROK-R5-P1-01** | S-1..S-8 已落地；Task 2.2 改純引用。**Task 7.5 三組未納入 S-***，結構變更時序列化再次無定義 |
| **GROK-R4-P0-03**（群集 C／E） | **CLOSED**（含 §C0↔§N） | Task 7.6／7.7＋V-14／V-15 已落；§N #8／#10 改撤回紀錄。殘留之單位換算見新 finding，不否定本條閉合 |
| **GROK-R4-P1-01**（群集 D／G） | **CLOSED** | Task 7.1 邊界：`/search` 只開 C／two_stage；深度公式在 Task 2.1b，1.9／V-12 引用。反例：`grep` 舊「uiOptions===contractEnum」＝0 |
| **GROK-R4-P1-02**（群集 H） | **CLOSED** | §D-7 L1 已改 hours 敘事；`grep future72_max_\*→72` 僅落點表歷史句；SYNC-FORBID 第 4 條涵蓋 `future…→數字` |

### 他家複核

| R4 ID | 複核 | 說明 |
|---|---|---|
| CODEX-R4-P0-01／COMPOSER-R4-P0-01／P0-02 | **同意 PARTIAL** | 同 A；正文已修、V-11 殘段未淨 → GROK-R5-P0-01 |
| CODEX-R4-P0-02 | **同意 CLOSED** | Task 1.12：`run_event_study_only`＋`event_split_plan` Optional＋`ci==unavailable`＋禁假 split_plan；對照 `tables.py:88-113` 現碼必填，契約與驗證對症 |
| CODEX-R4-P1-03／COMPOSER-R4-P1-03 | **同意 PARTIAL** | S-1..S-8 關閉原 F；7.5 結構未接 S-* → GROK-R5-P1-01 |
| CODEX-R4-P1-04／COMPOSER-R4-P1-01／P1-02 | **同意 CLOSED** | 7.6／7.7；§N 撤回 |
| CODEX-R4-P1-05／COMPOSER-R4-P1-04 | **同意 CLOSED** | pathExclusions＋深度公式（V-11 殘段另計） |
| CODEX-R4-P1-06 | **同意 CLOSED** | Task 7.5：唯一傳遞點＝manifest context 加 `control_kind`；混值／`not_computed` schema；對照 `dedupe.py:113` 現無該欄 |
| CODEX-R4-P1-07 | **同意 CLOSED** | Task 1.10④ 改名攻擊＋信任邊界；V-12⑥ |
| COMPOSER-R4-P2-01 | **同意 CLOSED** | Task 6.0 驗證欄為完整 `python3 -c`＋成員資格斷言；非 `-c "..."` 佔位 |

---

## 2. 全棧三欄稽核（事件型＋IC＋FL＋`/search`）

| 能力 | 後端 code | 前端 UI | wiring | 判定 |
|---|---|---|---|---|
| 六維度→事件匯出 | ✅ 契約三層級 | ❌ 無選項（寫死） | ❌ `page.tsx:522-527` 未傳；`EventExportOptions` 僅 scenario／entry；`:92/:102/:104` 寫死；`counterexample_kind` 字面 0 | Phase 7.0–7.2 已規劃；**閘殘段見 P0** |
| CSV 匯入新端點 | ❌ 待 1.2 | ❌ 待 1.5 | — | Phase 1 可執行 |
| 事件批次刪除 | ❌ 待 3.1 | ❌ 待 3.2 | — | Phase 3 可執行 |
| IC 止血閘 feature_count | ❌ 待 6.1 | 部分 | — | Phase 6 可執行 |
| IC 頁×事件批六維度 | 批次落檔有欄 | `EventImportPicker` 只 `onPick(id, timestamps[])` | ❌ 不傳語意 | **Task 7.6 規劃 CLOSED 原 E 揭露面** |
| FL／RunInfo `time_range` vs 事件 t0 | manifest／storage 有；`RunInfo` **無**；legacy＝`{None,None}` | 無對證 UI | ❌ 可送不涵蓋之 IC | **Task 7.7 規劃**；換算缺口見 P1 |
| 報酬表依 `control_kind` 分組 | 表函式無 label 分組；manifest 無 `control_kind` | 單組 | — | Task 7.5 規劃；**S-* 映射缺口見 P1** |

assumed「Phase 7 涵蓋面已完整」：**事件匯出＋IC 揭露＋覆蓋對證主線已入 Task**；本輪新缺口在規格內部一致性，而非又發現第三個未列頁面。

---

## 3. R4 新增 Task 7.0／7.6／7.7 與 S-1..S-8 可執行性

| 項 | 可執行？ | 備註 |
|---|---|---|
| Task 7.0 | ✅ | 型別＋參數化＋巢狀 `label_return_mode`；⑦行為不變；mutation 明確 |
| Task 7.6 | ✅ | detail 六鍵＋共用 formatter；不改 onPick 亦可（另 fetch detail） |
| Task 7.7 | ⚠️ | containment／legacy／reason 清單大多可執行；**毫秒換算未定**→P1 |
| S-1..S-8 | ⚠️ | 對**現行單組** `tables.py:88-180` 回傳結構可執行且對症；**未涵蓋 7.5 三組**→P1 |
| Task 7.1／7.2 正文 | ✅ | `selectable`／三層／mutation 可執行 |
| V-11 | ❌ | 與 7.1／7.2 正文矛盾→P0 |

---

## 4. §C0 遵守稽核

- 正面：`quant_standard_check.sh` rc=0；#8／#10 正確性項已收回 Task 7.7；檔頭保留主委自承；禁止「95% 就收」明文仍在。
- 問題：
  1. V-11 殘段若照做＝放回 A／B 語意漂移（資料正確性），屬**修補未修淨**。
  2. Task 7.5 對結構變更未要求 G-2／S-1 同步，有「結構留給實作猜」之實質效果（雖未用放水語）。
- 未見把洩漏／數值正確性降為 §N 具名殘留之新例。

---

## 5. §P 41 Task 欄位／跨 Task 相依

- 41／41 有覆蓋風險欄；「覆蓋風險：無」＝0。
- 相依宣告抽樣：7.0→7.1→7.2、4.2→7.5、5.2→7.5、3.2→3.3、1.10→1.11→1.12、1.9↔2.1b 公式引用——一致。
- **不一致**：Phase 7 標題「依賴：無」，但 Task 7.7 驗收最終 `analysis_rejected` 清單**含** Task 6.0 之 `feature_count_exceeds_cap`（6.0 註明 7.7 加兩項）。實務上 7.7 可一次寫齊三值使 6.0 成員斷言仍過，故列 Suggestions，不升 P1。
- Task 2.2 引用 S-2／S-5 處理 `filters`：S-* 原文綁定報酬表輸出；作為「鍵序／NaN 表示」借用可理解，但易誤導 Agent 以為 filters 進 G-2 hash——Suggestions。

---

## 6. 實作順序可行性

| 宣告順序 | 判定 |
|---|---|
| 7.0→7.1→7.2 | ✅ 可行且必要 |
| 4.2→7.5 | ⚠️ 可行，但 7.5 前必須先擴 S-1／約定三組序列化，否則 G-2 無定義可凍 |
| 5.2→7.5、4.3→5.3、4.1b→7.3 | ✅ |
| 1.10→1.11→1.12；1.9／2.1b 共用公式 | ✅ |
| Phase 6 vs 7.7 | 建議 6.0 先於 7.7（或 7.7 一次登錄三 reason）；標題「依賴：無」宜改 |

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 |
|---|---|
| fact-verified F-01..F-14 | **成立**（重跑＝facts.out） |
| assumed：R4 十九條處置未引入新內部矛盾 | **不成立**（V-11 vs selectable；7.5 vs S-1） |
| assumed：S-1..S-8 涵蓋表輸出全部序列化歧義 | **對現行單組成立；對 7.5 三組不成立** |
| assumed：pathExclusions 不違反「不得寫死單一 scenario」 | **成立**（路徑級；CSV 四種全開） |
| assumed：`ci` unavailable 於 split=None | **成立**（與 `tables.py:61-69` common 塊一致） |
| assumed：7.7 containment 足以擋覆蓋不足 | **方向對；毫秒換算未定⇒不可 Frozen** |
| assumed：深度公式對四 scenario 皆成立 | **機械式已入 2.1b；／search 不開 A／B 使漂移面封閉** |
| assumed：Phase 7 涵蓋面無其他漏接 | **本輪未再發現未列頁面之同型漏接** |

---

## §1 十一類摘要

1. 矛盾/互斥：V-11 `contractAccepted` vs Task 7.1/7.2 `selectable`；Task 7.5 三組 vs S-1 八鍵凍結  
2. 漏項/E2E：7.5 序列化位置；7.7 TF→ms  
3. 不可測驗收：同上兩處使 G-2／coverage 右界不可唯一實作  
4. 可疑 quant：毫秒換算單位；其餘 D-7 三層本輪 CLOSED  
5. 過度工程：無  
6. OOM：Phase 6 足夠（非本輪焦點）  
7. Cache：無新增  
8. API/型別：RunInfo／opts 缺口已有 Task  
9. 測試品質：V-11 若照做會與 7.2 mutation(b)（A disabled）互打  
10. Agent 可執行性：7.0／7.6／多數 7.7／S-*（單組）可執行；上列三缺口不可  
11. 短命工：4.1b→7.3、6.x→GAP-6 已標明；無新發現短命白工  

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

## Suggestions（非 Blocking）

- Phase 7 標題「依賴：無」改為「7.7 依賴 Task 6.0 之 `analysis_rejected` 分類（或 7.7 一次登錄三 reason）」。
- Task 2.2 引用 S-2／S-5 時加一句「僅借用鍵序／NaN 表示，filters **不**進入 G-2 表輸出 hash」。
- `/search` 是否也應 pathExclude `control_kind=platform_same_trigger_rule`（無產生器、易假 provenance）——本輪不升 finding，供主委裁定。
- Task 編號 1.10→1.12→1.9 可讀性（R4 Suggestions 仍在）。

---

ASSUMPTIONS_VERIFIED: SPEC sha256＝brief 鎖定；facts.sh 與 facts.out diff 空；dims 三層級＋control_kind 4/3；覆蓋風險 0／41；三機械閘 rc=0；R4 十九條反例重跑（V-11 殘段、S-1..S-8、7.6／7.7、1.12、1.10、6.0、§D future72、§N 撤回）；全棧三欄現況與 Phase 7 規劃對照；7.5 無 S-* 映射；7.7 缺 TF→ms。  
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_UX_SPEC.md`→鎖定值相符；`bash handoffs/20260822-gap3ux-x-review-r5-facts.sh`→rc=0、diff 空；`python3 handoffs/20260822-gap3ux-x-review-r5-dims.py{, --counts}`→rc=0；`bash scripts/doc_format_precheck.sh`／`spec_ruling_task_sync.sh`／`quant_standard_check.sh`→rc=0；`grep -c "覆蓋風險：無"`→0、`^- 覆蓋風險`→41；`bash scripts/completeness_check.sh --single handoffs/20260822-gap3ux-x-review-r5-grok.md --family grok`→見收尾。未跑產品 pytest／vitest（review-only）。  
FAILURES_SEEN: none  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none（未改產品／SPEC）  
OUTPUT: handoffs/20260822-gap3ux-x-review-r5-grok.md

STATUS: DONE
