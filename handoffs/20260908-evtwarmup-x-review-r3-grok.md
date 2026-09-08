# EVTWARMUP／TFWINDOW adversarial review R3（grok）

brief-kind: review
task-id: 20260908-EVTWARMUP-X-REVIEW-R3
family: grok
findings-round: R3
標的 commit: `1007ef28`（`docs/EVTWARMUP_SPEC.md`／`docs/EVTWARMUP_TODO.md`／`docs/TFWINDOW_SPEC.md`；仍未實作）

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核 |
|---|---|---|
| 三份 template PASS | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → 三條 TEMPLATE PASS，rc=0 |
| 改前 golden 探針 | **fact-verified** | `venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`；sha256=`af73d325…` |
| R2 X1–X7 已寫進三份文件 | **fact-verified** | `git diff d090b13c..HEAD -- docs/EVTWARMUP_SPEC.md docs/EVTWARMUP_TODO.md docs/TFWINDOW_SPEC.md`；§C-4／Task 1.2／2.1／TFWINDOW §G 對位 |
| Task 1.1 預檢 `test_events` 與 Task 1.2 stage3 後重算並存不矛盾 | **fact-verified（複核 brief assumed）** | 1.1＝預檢欄位（timestamps∩test_mask；非事件路徑 None）；1.2＝地板前以 consumed 事件列重算；地板 predicate 用 `_is_event_conditional_consumed` ⇒ 棄條件路徑不讀舊值開火 |
| `scan_cube._dumps` 對非有限 icir 與 reporter 一致 | **fact-verified（現況不一致；契約靠上游 sanitize）** | 實跑 `json.dumps({"icir":nan}, **_JSON_KW)` → `"icir":NaN`；`parse_constant` raise。SPEC 以 `_sanitize_summary_table_for_json`＋三入口 gate 收；TODO 驗證只寫 `save_report` → 見 P2-02 |

---

## 1a／1b — R2 原提出方（grok）逐條 CLOSED／OPEN

| R2 ID | 判定 | 閉合證據 | 閉合有無新矛盾 |
|---|---|---|---|
| `GROK-R2-P0-01` | **CLOSED** | SPEC §C-4：地板只在 stage3 後、predicate＝`_is_event_conditional_consumed`；棄條件禁寫 `insufficient_test_events`；Task 1.2 驗證 (e′)＋mutation M9 | 無（時序／predicate 已釘死） |
| `GROK-R2-P1-01` | **CLOSED** | SPEC §C-6／Task 2.1＋TODO 2.1：`get_top_features` 排序 key＝`_finite_or_neg_inf`；驗證不 raise；M10 | 無 |
| `GROK-R2-P2-01` | **CLOSED** | TFWINDOW §G「通過條件（單一套 oracle）」；刪舊「重算期望鍵」；引擎層不改期望鍵 vs 接線主 gate 分工清楚 | 無 |
| `GROK-R2-P2-02` | **CLOSED** | SPEC §C-4／TODO Task 1.2：`MarginalICTable.tsx`＋`generate_ai_json` reason-aware；vitest 釘不含 Full-sample | 無 |

**1b**：R2 四條原缺陷皆對位關閉。本輪僅見文件摘要漂移（§B gate 仍寫 M1–M8；TODO 2.1 驗證未列齊三序列化入口）——屬 P2，不重開 R2 條目。

---

## 必答（成對）

### 2a／2b 地板 predicate／時序（fallback／scan cube）

- **2a**：文件已強制地板＝stage3 後＋`_is_event_conditional_consumed`；`test_events` 以實際被消費事件列重算。fallback 重跑走主線（非 consumed）⇒ 禁寫 `insufficient_test_events`；scan cube「每格各自判定」（TODO 1.1 邊界③）。(e′)＋M9 可證偽「誤用預檢真值」。
- **2b**：**不會**再把棄條件主線假標成事件不足 holdout；合法 ≥30 事件 consumed 路徑亦不誤擋（≥30 ⇒ 無 `oos_downgrade`）。

### 3a／3b serializer＋`_finite_or_neg_inf`

- **3a**：讀取／排序點已列：`ic_reporter` 三處、`get_top_features`、`_apply_thresholds`（跳過）、stage6 tiebreaker＝`ic_mean`。寫出靠 `_sanitize_summary_table_for_json` 轉 None；SPEC 驗三入口 `parse_constant`。現況 `_dumps` 仍可吐 `NaN` 字面（實跑），故**必須**上游 sanitize 生效；TODO 驗證漏列後兩入口 → P2-02（驗收洞，非設計撤回）。
- **3b**：全域有限 icir 排序鍵不變（SPEC 自述）；`test_gap2_golden`／探針 `global_run` 不變；事件路徑才大量 None／診斷。

### 4 ≥10× 不必要複雜？

**無。** 兩 helper＋地板一欄＋ICIR 診斷化＋TFWINDOW 單點 `set_timeframe`。

### 5 可進 B1 實作嗎？

**可派工。** R2 原提出（含 P0）全 CLOSED；無新 P0／P1。兩條 P2（gate 摘要 M1–M8 過期；TODO 2.1 三入口 gate 未同步）可與實作同批修正，不擋 B1。

---

## §1 必查摘要（11 類）

| # | 類 | 結果 |
|---|---|---|
| 1 | 矛盾 | §B「M1–M8」vs SPEC §V／Phase「M1–M11」→ P2-01；Task 3.1 驗證仍寫「mutation M9＝注入拿掉」vs phase3＝T1／TFWINDOW M1（B2 命名殘留，併入 P2-01 碼證） |
| 2 | 漏項 | TODO 2.1 驗證只寫 `save_report`，SPEC 要三入口 → P2-02 |
| 3 | 不可測 | (e′)／M9–M11／三 template／探針可證偽 |
| 4 | quant | 無新疑；`EW-RESID-3` 地板 30 仍 needs-research |
| 5 | 過度工程 | 無 |
| 6 | OOM | 無 |
| 7 | Cache | N/A |
| 8 | API／相容 | 兩值 status；TS `icir: number\|null` 已列 |
| 9 | 測試 | R2 閉合測＋mutation 形狀對；gate 摘要漏 M9–M11 |
| 10 | Agent 可執行 | 地板／ICIR 偽碼足夠；照 §B 寫 gate 可能少跑 M9–M11 |
| 11 | 短命工 | 無 |

§N：`EW-RESID-1..4`／`TW-RESID-1` 三值理由仍成立；無應收回為 Task。

---

## Verdict：可派工

---

## GROK-R3-P2-01

**斷言**: TODO §B 批次 Gate 仍要求 mutation「M1–M8 紅／C0 綠」，但 SPEC §V 與 TODO「Phase 測試與 Gate」已定義 phase 1＝M1–M11＋C0（含 R2 閉合之 M9 地板時序／M10 top-features／M11 serializer）；Agent 若只依 §B 實作 `evtwarmup_phase_gate.sh 1` 會漏驗 R2 三條 mutation。

**碼證**: `docs/EVTWARMUP_TODO.md` §B L17：`mutation M1–M8 紅／C0 綠`；同檔 L67：`phase 1：M1–M11＋C0，定義見 SPEC §V`；`docs/EVTWARMUP_SPEC.md` §V 列 M9–M11。另 Task 3.1 驗證 L60 仍寫「mutation M9（注入拿掉）」——與 EVTWARMUP M9（地板預檢真值）撞名，且同檔 L67 已改 phase3＝T1／T2／C1、TFWINDOW §V＝M1／M2／C0。RECHECK: 將 §B 改「M1–M11」；Task 3.1 驗證改指 T1（或 TFWINDOW M1），刪「M9＝注入拿掉」。

**來源摘要**: docs/EVTWARMUP_TODO.md#5de8901b9f6e；docs/EVTWARMUP_SPEC.md#ef3c3c555571；docs/TFWINDOW_SPEC.md#e51179a38d97

[MINOR] 信心度=High。會怎麼失敗：B1 gate 綠但 M9–M11 未跑 → R2 P0／P1 閉合缺 mutation 護欄（行為測 (e′) 仍在）。修法：§B 與 Task 3.1 驗證字面與 SPEC §V／Phase 測試對齊；可與 B1 實作同批。

---

## GROK-R3-P2-02

**斷言**: SPEC Task 2.1 驗證要求三個序列化入口（`save_report`／`export_all` 之 `safe_report` dump `:726`／`scan_cube._dumps`）皆通過 `json.loads(..., parse_constant=<raise>)`，但 TODO Task 2.1 驗證只寫 `save_report` 一處——SPEC→TODO 驗收面未同步。

**碼證**: SPEC Task 2.1 驗證（三入口）；TODO Task 2.1 驗證：「`save_report` 落檔後 `json.loads(...parse_constant=<raise>)`」無 safe_report／scan_cube。實跑：`json.dumps({"icir":float("nan")}, ensure_ascii=False, sort_keys=False, separators=(",",":"))` → `'{"icir":NaN}'` 且 `parse_constant` raise——證明若上游 `_sanitize_summary_table_for_json` 未覆蓋 icir，cube 格仍可落非法 JSON。RECHECK: TODO 2.1 驗證句補齊三入口（或明示「build_report sanitize 後三入口抽樣」＋各給一測）。

**來源摘要**: docs/EVTWARMUP_SPEC.md#ef3c3c555571；docs/EVTWARMUP_TODO.md#5de8901b9f6e；momentum/Analysis/scan_cube.py（_JSON_KW／_dumps）

[MINOR] 信心度=High。會怎麼失敗：實作者只對 `save_report` 加 gate，cube／export_all 路徑漏測。修法：TODO 驗證與 SPEC 對齊；產品仍以 sanitize 轉 None 為主（不必改 `_dumps` allow_nan，除非要 defense-in-depth）。可與 B1 同批。

---

## §0 挑戰前提（無新 MAJOR）

R2 主委 `allow_nan=False` 假 FACT 已在 SPEC §A 明記推翻並改 serializer 契約——本輪無「再把假設當事實」的新 BLOCKING。

ASSUMPTIONS_VERIFIED: 三 template PASS；探針 golden True／sha256 af73d325…；R2 grok 四條 CLOSED；§B M1–M8 vs M1–M11 漂移；TODO 缺三入口 gate；scan_cube dumps 現況可吐 NaN
TESTS_RUN: `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` rc=0；`… TFWINDOW_SPEC.md` rc=0；`… todo docs/EVTWARMUP_TODO.md` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0／True；未跑 `pytest tests/governance`
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；指出既定 JSON null／TS nullable／mutation M9–M11 契約）
產出檔: handoffs/20260908-evtwarmup-x-review-r3-grok.md

STATUS: DONE
