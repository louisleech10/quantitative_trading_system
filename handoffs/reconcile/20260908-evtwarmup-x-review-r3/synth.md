# Reconcile — 20260908-evtwarmup-x-review-r3

**來源** 20260908-evtwarmup-x-review-r3-codex.md, 20260908-evtwarmup-x-review-r3-composer.md, 20260908-evtwarmup-x-review-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置

R2 X1–X7 由原提出方全部 **CLOSED**（codex 逐條、composer sentinel、grok 逐條）。composer／grok Verdict「可派工」；codex「需修補後派工」因一條新 P1。三條皆為 **SPEC→TODO 字面同步**，無設計缺陷。

### Y1 — P1 TODO 未同步 SPEC 之三序列化入口（`CODEX-R3-P1-01`、`GROK-R3-P2-02`）
codex 實跑：`scan_cube._dumps({"icir":nan})` → `{"icir":NaN}`，strict parse raise。**處置**：TODO Task 2.1 檔案／驗證補齊 `save_report`／`safe_report`（`:726`）／`build_cube` Tier A／B（`_dumps` `:71-73`、`:228`／`:309`），單一政策＝producer 端 sanitize 轉 `None`、`_JSON_KW` 不改（維持 raw-copy invariant）；每入口 strict parse 測試，scan cube 以事件路徑 2 格實跑。

### Y2 — P2 TODO §B mutation 清單 M1–M8 vs SPEC §V M1–M11；Task 3.1 「M9」撞名（`GROK-R3-P2-01`）
**處置**：§B 改 M1–M11；Task 3.1 驗證改 T1（TFWINDOW 命名）。

Verdict: 可派工——Y1／Y2 已改 TODO（template_check PASS）；三家 R2 全 CLOSED、無新 P0；Y1 之閉合由 codex 於 B1 code review（R4）以同一反例（`_dumps` strict parse）對實作驗證。開工 B1。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01

**斷言**: R2 X4 的 serializer gate 在 SPEC／TODO 未同步覆蓋三個入口；`scan_cube._dumps` 可讓非有限 ICIR 落成非標準 JSON，實作只照 TODO 會漏驗。
**碼證**: SPEC `EVTWARMUP_SPEC.md:80-81` 要求 `save_report`、`ic_reporter.py:726`、`scan_cube._dumps:71-73` 皆過 strict `parse_constant`；TODO `EVTWARMUP_TODO.md:46-48` 檔案／驗證只明列 `ic_reporter.py` 與 `save_report`。`build_cube` 以 `_dumps` 寫 `scan_cube.py:228,309`；實跑 `venv/bin/python -c 'import json; from momentum.Analysis.scan_cube import _dumps; text=_dumps({"icir":float("nan"),"ic_mean":float("inf")}); print("SCAN_CUBE_DUMPS="+text); json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))'` → `SCAN_CUBE_DUMPS={"icir":NaN,"ic_mean":Infinity}`、`ValueError: NaN`、rc=1。RECHECK：重跑同一命令並檢查 `scan_cube.py:68-73,228,309`。
**來源摘要**: docs/EVTWARMUP_SPEC.md#ef3c3c555571;docs/EVTWARMUP_TODO.md#5de8901b9f6e;momentum/Analysis/scan_cube.py#2b27c3d9e42f
[MAJOR] 信心度=10/10；未來 Agent 可能完成 reporter sanitizer 卻遺漏 Tier A／B scan cube，產生可被寬鬆 parser 接受、但 strict JSON gate 拒絕的產物。修法：在 TODO Task 2.1 明列 `scan_cube.py`（Tier A／B）與 `export_all` 的 producer／serializer 責任、非有限值轉 `null` 或 fail-closed 的單一政策，並為兩層落檔各加 strict parse gate；保持既有逐列／逐節 raw-copy invariant。

R2 disposition：X1 CLOSED；X2 CLOSED；X3 CLOSED；X4 CLOSED（原錯誤 allow_nan 事實已改列 FACT-RECEIPT）；X5 CLOSED；X6 CLOSED；X7 CLOSED。
必答 1b：有新矛盾，即 SPEC 三入口要求與 TODO 僅驗 `save_report`／未列 `scan_cube.py` 不一致（見 CODEX-R3-P1-01）。
必答 2a/2b：fallback rerun 會重算 consumed predicate，scan cube 每格獨立判定；文件指定的 stage3 後地板時序可行，且 (e′) 防止合法棄條件路徑誤標 `insufficient_test_events`。
必答 3a/3b：`_finite_or_neg_inf` 的 reporter 三處與 `get_top_features` 已列全；serializer 三入口只在 SPEC 列全，TODO／scan cube 尚未閉合。有限全域值的排序／golden 不變有明文 oracle，但未實作前不能宣稱已驗。
必答 4：無 ≥10× 不必要複雜度；必答 5：不可進 B1，先修 P1-01。
類別(1–11)：1=P1-01；2=P1-01；3=P1-01；4=無；5=無；6=無；7=無；8=P1-01；9=P1-01；10=P1-01；11=無。
§0：fact-verified＝三份 template_check rc=0；baseline probe rc=0、sha256 `af73d325e0c4` 且 golden=True；scan cube strict probe rc=1 並輸出 NaN/Infinity。assumed＝尚未有本票實作，因此完整真實 scan cube payload 的非有限值分布未驗；finding 僅主張序列化政策與 TODO 覆蓋不足。
TESTS_RUN：`bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md` rc=0；同命令 TFWINDOW rc=0；`bash scripts/template_check.sh todo docs/EVTWARMUP_TODO.md` rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` rc=0／golden=True；上述 scan cube strict probe rc=1（預期暴露缺口）。
FAILURES_SEEN：scan cube strict probe 預期 rc=1；無測試治理套件。
SCOPE_CHANGES：唯讀審查；未改程式、SPEC、TODO 或 data_cache；產出=`handoffs/20260908-evtwarmup-x-review-r3-codex.md`。
NUMERIC_OR_SCHEMA_IMPACT：本次未修改；指出 scan cube JSON null／strict gate 與既有 raw-copy invariant 的待明確化影響。
STATUS: DONE
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的 P0／P1／P2 finding；R2 本人提出之四條均已 CLOSED，SPEC↔TODO 閉合無新 blocking 矛盾。

**碼證**: `bash scripts/template_check.sh spec docs/EVTWARMUP_SPEC.md`／`…TFWINDOW_SPEC.md`／`…todo docs/EVTWARMUP_TODO.md` → TEMPLATE PASS×3, rc=0；`venv/bin/python handoffs/20260908-probe-evtwarmup-baseline.py` → `與既有 golden 相同？ **True**`, rc=0；`git diff d090b13c..HEAD -- docs/EVTWARMUP_SPEC.md docs/EVTWARMUP_TODO.md docs/TFWINDOW_SPEC.md` 對照 R2 synth X1–X7 處置位；COMPOSER-R2-P1-01/02/P2-01/02 修訂句在 SPEC §C-4／§C-6／Task 1.2／2.1 與 TODO 同檔同段可搜；TFWINDOW §G「單一套 oracle」刪舊重算句；brief assumed `test_events` 並存→TODO 1.2「先重算」已否證。

**來源摘要**: docs/EVTWARMUP_SPEC.md#ef3c3c555571;docs/EVTWARMUP_TODO.md#5de8901b9f6e;docs/TFWINDOW_SPEC.md#e51179a38d97;handoffs/reconcile/20260908-evtwarmup-x-review-r2/synth.md

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

