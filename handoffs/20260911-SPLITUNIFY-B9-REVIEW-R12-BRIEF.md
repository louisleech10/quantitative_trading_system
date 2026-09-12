# SPLITUNIFY D-002 閉合輪 R12

brief-kind: review
task-id: 20260911-SPLITUNIFY-B9-REVIEW-R12
findings-round: R12

## 範本

照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` **全文照做**：§0 挑戰前提、
canonical finding 四欄格式、結尾 Verdict 區塊。🔴 **禁改碼、禁改 SPEC**。

## 🔴 開審前先讀這一段（本輪為唯讀審查）

`AGENTS.md` 第 12 條（STAMP-BLOCKED）逐字為「**動工前**若所依 reconcile/SPEC 的
`RECONCILE-STAMP` 未全數 APPROVED → 輸出 `STATUS: BLOCKED — reconcile 未核可`，**不動工**」
——該條管的是**實作動工**，不是唯讀審查。上游收斂檔沒有戳記是正常狀態。

## 這一輪要做什麼

R11 三家共 12 條、歸六群（五群採納、一群部分採納），`docs/SPLITUNIFY_SPEC.D-002.md` 已第十二次修訂（v12）。
依章程 §B8 由**原提出方**確認是否真關閉，**不憑作者說「已改」**。

🔴 **本輪特有必答（承 R11 之發現）：檢驗自證第七條「可實作性」。**

R11 三家一致指出我的自證清單缺第七種形態——**跨既有介面／座標契約的可實作性**：
文字位置對、交叉引用也對，但寫下的落點在既有契約下**根本不能實作**（v11 的 M5 兩案
皆牴觸 `D-001-C2` (4.10)）。我已把它加進自證清單並在 v12 逐條套用。

**請檢驗這件事本身**：v12 新寫的每一段（N1–N6 共六群之落點），是否都**可實作**？
有沒有哪一條在既有介面／契約下做不到、或與 D-001、既有 golden、`docs/SPLITUNIFY_TODO.md` §E 衝突？

## 六群的修訂落點（請對照複驗）

| 群 | 你們指出的 | v12 落點 |
|---|---|---|
| N1 整鏈無可執行交接（codex＋composer） | 孤立 builder 單測可綠 | §V 值相等斷言**指定**掛在 `EventSamplePipeline.run`；🔴 **部分採納**：兩家建議的「經 `ic_filter_orchestrator` 驗值」經主委複驗**走不到**（該檔 `discarded` 命中 0、走 `holdout_boundary`、不呼叫 `build_event_keys`），故 `metadata.split_unify` 層**明確併入** `SU-RESID-9A-UI` 殘留、不宣稱交付 |
| N2 register 漏記帳消費面（三家） | 25 條不完整 | register 25 → **29**，補 `C5-26` `pipeline.py:760-762`／`C5-27` `split_projection.py:559-569`＋`:716-719`／`C5-28` `EventTablesPanel.tsx:361`／`C5-29` `tables.py:372`；`(5.3)` 之「tables 兩處」更正為 4 處；標題／§RISK／§R 同步。🔴 **駁回**「API 計數模型」一列（見前提） |
| N3 M5 座標二擇一（codex＋grok） | 不窮盡且兩案皆違反 D-001 | 改為：validator **不在 derive 內呼叫**，由仍持有 full `ts`／`symbols` 的 producer／adapter 層呼叫；投影端維持只讀 `row_index_local`；契約明寫「`row_index` 與 `ts`／`symbols` 同一座標系、禁混用」；四案真值表逐格進 §V |
| N4 M6 可繞過（三家） | 自參照雜湊＋整檔 `--write` | (G-4d)① 增 **(v)** `O_EXCL` write-once（建立後拒更新）、**(vi)** 外部錨（首次 `sha256` 字面寫進 §V）、**(vii)** `--write` 對主檔既有 11 鍵 fail-closed；§V 補三條母斷言；新增 `M-SU-D2-33` |
| N5 `M-SU-D2-29` 舊字面（grok） | mutation 對新落點不可驗 | 改壞面改為「刪／覆寫 `.v8.json`、改內容未同步旁檔、`--write` 未 raise、主檔既有鍵被覆蓋」，對齊 §V 第 6 條 |
| N6 `M-SU-D2-03` 舊字面（grok） | 只寫鍵斷言 | 改壞面加「鍵在而值不等於 summary／producer」 |

## 前提（範本 §0；請逐條挑戰）

fact-verified: R11 十二條歸六群（五群採納、一群部分採納）→ `handoffs/reconcile/20260911-splitunify-b9-review-r11/synth.md`
fact-verified: mutation 表列 **33**、ID 01–33 連續且無重複；register 表列 **29**、ID 01–29 連續且無重複 → 主委實跑 `grep -c` ＋ `comm` 缺號比對 ＋ `uniq -d`
fact-verified: `tables.py` 共 **4 處** `set_index`（`:214` event_level／`:229` clusters／`:372` assignments／`:373` clusters），v11 以前寫「兩處」為漏數 → 主委實跑 `grep -n`
fact-verified: `api/models/` 無具名 split 計數欄——`n_purged` **零命中**，`n_test` 只命中 `tier_min_test_events` 與 `n_test_groups`；`EventAnalyzeResponse.summary` 為 `Dict[str, Any]`（`api/models/event_import_models.py:308`）→ 主委實跑 grep（此為**駁回**「API 計數模型」一列之依據，請挑戰）
fact-verified: `pipeline.py:759` 為 `{k: v for k, v in plan.summary.items() if k != "per_symbol_n"}` 整包展開 ⇒ summary 新鍵零成本穿透報告、不需白名單 → 主委實讀
fact-verified: M5 四案真值表（全域索引＋全域宇宙 PASS／全域索引＋局部宇宙 `IndexError`／局部索引＋局部宇宙 PASS／局部索引＋全域宇宙 `CrossSymbolLeakageError`）→ 主委探針 `handoffs/20260912-splitunify-b9-probe-m5-coords.py`，receipt `20260912T112625Z-splitunify-b9-m5-coords`（1 passed，`runtime_class=helper_smoke`）
fact-verified: `D-001-C2` (4.10) 逐字「投影端只消費 `row_index_local`；`derive_event_split_from_plans` 內部一律不得索引 `row_index`」→ 主委實讀 `docs/SPLITUNIFY_SPEC.D-001.md`
fact-verified: v12 後 `obligation_block_check` rc=0、`doc_format_precheck` rc=0（SPEC 與 TODO）、`spec_xref_check --synth` 對 **r1–r11 十一份** 皆 rc=0；R11 債已清 → 主委實跑

assumed: N1 之「斷言掛 `EventSamplePipeline.run`」在**沒有生產接線**的情況下仍是有意義的驗收
→ 否證觀測：說明只在測試入口驗整鏈，與「孤立 builder 單測」相比實質差異何在；或指出這只是把 mock 換個位置／我跑了: **沒跑**（只驗了 orchestrator 那條走不到）
assumed: N3 之「validator 由 producer／adapter 層呼叫」在既有程式結構下**做得到**（有一層同時持有 full `ts`／`symbols` 與兩個 plan）
→ 否證觀測：指出該層不存在、或指出它拿不到其中一項／我跑了: **沒跑**（只證明了 derive 內呼叫不可行）
assumed: N4 之 `O_EXCL` write-once ＋ 外部錨**確實堵住**三家給的兩條繞過
→ 否證觀測：在 (v)(vi)(vii) 都落地的前提下，再構造一條繞過／我跑了: **沒跑**
assumed: register 29 條**這次**涵蓋完全
→ 否證觀測：再掃一次，指出仍不在表內的消費面（附檔:行）／我跑了: 只補了三家具名的四處，**沒有重新全域掃描**
assumed: 「API 計數模型」不存在具名落點，故駁回正確
→ 否證觀測：指出 `api/` 內任何具名 split 計數欄位／我跑了: `api/models/` 全域 grep（**只掃 models，未掃 routes／services**）

## 必答（成對，缺一不算完成）

1. **你自己 R11 的 finding 是否閉合**？逐條給判定並說明確認方式。
2. **檢驗自證第七條「可實作性」**（本輪特有）：v12 的六群落點，逐項指出是否在既有介面／契約下做得到；列出做不到的。
3. **攻 N1**：只在測試入口驗整鏈，與孤立單測的實質差異何在？把 `metadata` 層併入殘留是誠實還是逃避？
4. **攻 N3／N4**：producer／adapter 層是否真的存在且拿得到 full context？(v)(vi)(vii) 落地後還有沒有繞過？請附**具體構造**。
5. **攻 register 29 與那條駁回**：還有沒有漏列的消費面？「API 計數模型」的駁回是否成立（請掃 `api/routes/`／`api/services/`，我只掃了 `api/models/`）？
6. **修訂引入的新問題**：N1–N6 落點彼此、或與 D-001／既有 golden／`docs/SPLITUNIFY_TODO.md` §E 有無衝突？

## 停輪條件

①必答 1–6 皆有立場；②必答 2、4、5 須附**具體反例或碼證**，不得只讀 SPEC 推論；
③🔴 **禁以「無 finding」當停輪**；④若仍 blocked，須說明「不改會在 `Task 9.x` 實作時具體怎麼失敗」。

## 格式（🔴 分家族寫明）

findings 用 `## <你的家族大寫>-R12-P<0-3>-<NN>` 二級標題；完成訊號**逐字** `STATUS: DONE`。

🔴 **`BLOCKED-BY` 與 `CLOSED` 兩欄都只能列「本檔本家族」開過的 ID**：跨輪未閉之條目請
在本輪**以新 ID 重開**，或於正文敘述，**不要**填進裁決欄；他家 ID 一律不得填入任一裁決欄。

裁決塊三行分寫。
