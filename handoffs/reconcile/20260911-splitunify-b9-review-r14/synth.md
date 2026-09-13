# Reconcile — 20260911-splitunify-b9-review-r14

**來源** 20260911-splitunify-b9-review-r14-codex.md, 20260911-splitunify-b9-review-r14-composer.md, 20260911-splitunify-b9-review-r14-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置

**修訂標的**：docs/SPLITUNIFY_SPEC.D-002.md

| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置 |
|---|---|---|---|
| **U1 register 之 mutation 欄有一整類錯配（逐列窮舉後共五列；三家分別命中）**——「C5register有五列mutatio」「`C5-25`之mutation欄指`M」「`C5-29`（`tables.py:3」「`C5-25`（survivor餵入端須」 | P1 | CODEX-R14-P1-03, COMPOSER-R14-P2-01, GROK-R14-P1-01, GROK-R14-P1-02 | 採納（🔴 **v14 的 `C5-20`／`C5-21` 只是冰山一角**。本輪依 brief 要求做 `C5-01`..`C5-29` **逐列窮舉**，三家合計再找出五列：`C5-24` 原只掛 `M-SU-D2-05`（缺「略過唯一側去重」那半）⇒ 改掛兩條；`C5-25` 原掛 `M-SU-D2-19`（該條屬 `C5-10`）⇒ 新增 `M-SU-D2-38`；`C5-27` 原掛 `M-SU-D2-13`（該條屬 `C5-26`）⇒ 新增 `M-SU-D2-39`；`C5-29` 原掛 `M-SU-D2-06`（該條屬 `C5-13`）⇒ 新增 `M-SU-D2-40`；`C5-28` 之 `—` 經複驗**確為刻意**（交付面隨 `SU-RESID-9A-UI` 殘留延後、無碼可壞），已於該列具名理由類別 `blocked-by`。條數 36 → **40**，ID 01–40 連續。🔴 **窮舉已完成**：三家獨立確認 `C5-01`..`23` 與 `C5-26` 無誤，此類存量錯配到此為止） |
| **U2 `M-SU-D2-35`／`36` 之應紅欄可被軟包短路（兩家撞題）**——「`M-SU-D2-35`/`36`的應紅」「`M-SU-D2-35`／`36`之「應」 | P1 | CODEX-R14-P1-01, GROK-R14-P2-03 | 採納（兩家各自實證：v14 只寫「欄缺時 `duplicated(subset=...)` 會 `KeyError`」，但實作者若寫成 `if "feature_timeframe" in df.columns` 軟包，欄缺就靜默略過而**不紅**；grok 另以單 TF fixture 實跑「無重複」佐證。codex 另指出兩個具名測試**目前不存在**（以 `-k` 實跑全數 deselected、rc=5）。改法逐字採 codex 必答 (3b) 提供之字面：**先**斷言 `feature_timeframe` 在該表之 `columns` 內、**再**做複合鍵唯一性斷言；**刪欄**與**軟包**兩種破壞皆須 FAIL；fixture 須為多 feature TF。SPEC 兩列與 TODE `Task 9.2a` 同步改） |
| **U3 `Task 9.3` receipt 閘仍可假完成（三家撞題）**——「Task9.3新receipt閘仍接受e」「`Task9.3`新receipt閘驗e」「Task9.3新receipt閘在exa」 | P1 | CODEX-R14-P1-02, COMPOSER-R14-P2-02, GROK-R14-P2-04 | 採納（三家各自構造出繞過：ID 集合正確但分類全填 `甲 -> 甲`、碼證填占位路徑、`COMMIT:` 欄填任意 sha 無人對證——codex 實跑其 exact-set 與列格式兩道判準皆 PASS。改法在 `docs/SPLITUNIFY_TODO.md` 之 `Task 9.3` 再加兩條內容對證：①**改前分類須逐列等於 SPEC register 現況之第 3 欄**（直接殺掉「全填同一值」）；②**碼證之 `path:line` 須指向真實存在的檔與不超範圍的行**（殺掉占位）；並把 `COMMIT:` 從「有這一行」改為「須等於該 impl task-id 在 audit 所記之 round-start HEAD」） |
| **U4 `doc_friction_ratio` 之封閉字面集合過窄**——「`doc_friction_ratio`」 | P2 | CODEX-R14-P2-04 | 部分採納（**判定成立、但本輪不改判準**。成立面：R13 之 `CODEX-R13-P2-03`（「六個」vs 表列九列）語意上就是文檔病，卻因用詞未命中集合而算不進分子——該家並給出可直接替換之加強 regex。**不改的理由**：該判準是 DOCROT 結票時三家戳記核可之成效標準，**在量測進行中由被量測者單方放寬或收緊都不正當**；且其 SSOT 位於已蓋章之 DOCROT consult-r3 收斂檔，改它會使 DOCROT 之戳記失效。⇒ 本輪**同時報兩個數字**並具名此缺口，交由使用者／下一輪委員裁定是否換判準） |

### 本輪裁定
1. **review-r13 三條全數由原提出方 CLOSED**（codex `CODEX-R13-P1-01`／`P1-02`／`P2-03`）。
2. **U1–U3 已修**（SPEC 進 **v15**：register 五列改指／補掛、新增 `M-SU-D2-37`..`M-SU-D2-40`、條數 36→40、`M-SU-D2-35`／`36` 應紅欄強化；TODO 同步 `Task 9.2a`／`Task 9.3`／`Task 9.4` 與 `Task 9.3` 表之三列）。
3. **戳記**：v14 之 composer APPROVED 與 codex／grok REJECTED 皆因 body 再變而失效。新 body sha256 為 c674086e5f66985ed4bb3107483803425eaec27731acc49f173ed89efe4b8bf0，須於下一輪重簽。
4. **仍不可領 impl token**；最小閉合集合＝U1–U3 修補（已完成）＋ 新 body 之三家 APPROVED 且 `reconcile_stamps_check` rc=0。

### DOCROT 成效量測（第二輪）
本輪 canonical finding 總數＝**10**（codex 4 ＋ composer 2 ＋ grok 4；≤20 ✓）。
- **依現行（consult-r3 已蓋章之）封閉字面集合**：無一條之碼證 `path:line` 落在 `HISTORY-BEGIN..END`，亦無一條斷言命中該集合 ⇒ **`doc_friction_ratio` = 0/10 = 0.00**。
- **依 codex `CODEX-R14-P2-04` 提議之加強集合**（加入「兩個數量對照且明示不符」之樣式）：本輪仍為 **0/10 = 0.00**（本輪無「同一段明示兩個數量」型 finding；該加強集合影響的是 R13 的 `CODEX-R13-P2-03`，會使第一輪由 0/5 變 **1/5 = 0.20**，仍 ≤0.30）。
- ⇒ **兩輪在兩種判準下皆 ≤0.30 且每輪 ≤20 條，DOCROT 成效判準達標**。
🔴 **誠實邊界（具名，不得當作已解決）**：本輪十條中有**七條**是「register／mutation 對應錯配」與「驗收判準可被繞過」——那是**另一種**文檔病（指標指錯、閘寫得不夠緊），**現行 `doc_friction_ratio` 完全量不到它**。換言之「0.00」只證明 DOCROT 所針對的那一種病（一決定多落點）沒再發作，**不等於**文件健康。此限制須在回報使用者時一併講明。

Verdict：需修補後合併

<!-- 群集表格式（Task 4.1 閘）：| 群集（含斷言前 20 字逐字） | 嚴重度 | 來源 ID | 處置（採納｜部分採納｜駁回｜延後→E-n 或 Task N.N，單一目標，說明以（）括起；token 須整詞：`不採納` 不算） | -->


---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R14-P1-01
**斷言**: `M-SU-D2-35`/`36` 的應紅測試只依賴缺欄時 pandas `KeyError`，未強制欄位存在；`if "feature_timeframe" in df.columns` 可短路而不紅，且具名測試目前不存在。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:545
MUTATION: 刪除 assignments/purged row dict 的 `feature_timeframe` 後執行 `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'assignments_composite_key_unique or purged_composite_key_unique'`。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3;docs/SPLITUNIFY_TODO.md#5738e9c63f6f `[MAJOR]` 信心度=High；實跑結果為 `78 deselected / 0 selected`, rc=5。一次修訂可直接把兩列應紅字面改成：`先 ASSERT "feature_timeframe" in assignments/purged.columns，再 ASSERT not duplicated(subset=["event_id","feature_timeframe"]).any()；刪欄或以 if "feature_timeframe" in df.columns 包住 guard 均須 fail`；先欄位斷言即可阻止短路，修法可行。
## CODEX-R14-P1-02
**斷言**: Task 9.3 新 receipt 閘仍接受 exact ID set、合法列格式但全列假填 `甲 -> 甲`，並接受未與 audit HEAD 綁定的任意 `COMMIT`。
**碼證**: CODE-ANCHOR: scripts/completeness_check.sh:350
MUTATION: 構造 `TASK: 20260911-SPLITUNIFY-B9-REVIEW-R14-IMPL`、`COMMIT: deadbeef`，C5-01..29 全寫 `甲 -> 甲 fake:1`，執行 TODO:632-640 的 exact-set diff 與 row-format grep。
**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f `[MAJOR]` 信心度=High；實跑 `EXACT_ID_SET=PASS`、`ROW_FORMAT=PASS`、`COMMIT=deadbeef`。一次修訂可在 dispatch audit 記錄 round-start HEAD，驗收強制 `COMMIT` 等於該欄，並逐 ID 對證分類與現存 `path:line`；目前規範只驗 ID/值域/格式，未驗內容。
## CODEX-R14-P1-03
**斷言**: C5 register 有五列 mutation 覆蓋不對或缺失：C5-24 的 M05 未描述唯一側去重/fail-closed，C5-25 的 M19 未描述餵入去重，C5-27 的 M13 未描述 per-symbol threshold 去重，C5-28 無 mutation，C5-29 的 M06 未描述 assignments symbol reindex。
**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/pattern_bridge.py:125; CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:56; CODE-ANCHOR: momentum/Analysis/event_samples/split_projection.py:641; CODE-ANCHOR: frontend/src/components/ic-analysis/EventTablesPanel.tsx:361; CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 依序省略 pattern_bridge 唯一側去重、ic_feed survivor 餵入去重、per-symbol event_id 去重、前端事件數映射、以及 assignments symbol 唯一化，並執行各列 Task 9.3/9.4 named tests；每一列都須各自轉紅。
**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3 `[MAJOR]` 信心度=High；逐列命令 `sed -n '93,123p' docs/SPLITUNIFY_SPEC.D-002.md` 取到 29 列：C5-01..23、C5-26 可對應，C5-24/25/27/28/29 為上述五列。一次修訂需改寫 M05 或新增五個專屬 mutation，並把 register 指向各自反向測試。
## CODEX-R14-P2-04
**斷言**: `doc_friction_ratio` 的封閉字面規則漏掉「六個下游消費面、表列九列」這類同一段明示兩個數量但未使用既有關鍵詞的文檔病。
**碼證**: `handoffs/20260912-docrot-x-consult-r3/synth.md:33` 的現行 regex 定義；brief 的 R13 B9D 反例。
**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r3/synth.md#b668b6c7ade7;handoffs/20260911-SPLITUNIFY-B9-REVIEW-R14-BRIEF.md#f41f50fff891 `[MINOR]` doc-literal-only，信心度=High；是，集合過窄。可直接替換為 `多落點|漏一處|同一計數|共\s*\S+\s*條.*兩|前版修法|原寫|已作廢主張|([0-9]+|[零一二三四五六七八九十百]+)(個|處|列|項|家|支撐面|消費面).*(但|卻|與|不符|不一致|不相符|少了|多了|漏).*([0-9]+|[零一二三四五六七八九十百]+)(個|處|列|項|家|支撐面|消費面)`；按現行集合本輪為 0/4=0.00，顯示該漏報。
ANSWERS: Q1＝R13 P1-01/P1-02/P2-03 均 CLOSED（grep 顯示 C5-20→M35、C5-21→M36、B9D=七模組＋兩支撐面＝九列；duplicate probe=`DUPLICATE_ID_SET=FAIL`）；Q2＝5 列錯配如 P1-03，其餘 24 列可對應/刻意 `—`；Q3＝不足，採 P1-01 直接貼字面；Q4＝可繞過如 P1-02，最小修補為 audit HEAD＋逐 ID 分類/path 對證；Q5＝REJECTED，阻擋項可在一次修訂內關閉；Q6＝現在不可領 token，需先關閉三個 P1、三家以新 body 重簽並使 `reconcile_stamps_check` rc=0。§1：B9A–F↔9.1–9.5、必要性/quant/OOM/cache/API 無新增 finding；DOCROT 本輪 4 findings、現行字面分子 0。
ASSUMPTIONS_VERIFIED: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`→`7455b305c6f3…`; counts→mutation 36、§C-9 36、register 29、條數標題恰一處；兩次 `doc_format_precheck` rc=0；C5 receipt exact/duplicate probes 與 R13 closure grep 均如上。
TESTS_RUN: `venv/bin/python -m pytest -q tests/momentum/Analysis/test_splitunify_derive.py -k 'assignments_composite_key_unique or purged_composite_key_unique'`→78 deselected/0 selected rc=5；未跑全套 pytest（本輪唯讀文檔審查）。
FAILURES_SEEN: 上述 0 selected 是現況證據；`reconcile_stamps_check` 讀取命令被 OPEN-debt PreToolUse gate 擋下，未繞過、未改檔。SCOPE_CHANGES: 僅新增本交件與 codex stamp；未改 `data_cache/`、根 `HANDOFF.md`、碼、SPEC 正文、TODO。NUMERIC_OR_SCHEMA_IMPACT: 無 runtime/schema/output-size 變更。HANDOFF_OUTPUT: `handoffs/20260911-splitunify-b9-review-r14-codex.md`。
VERDICT: blocked
BLOCKED-BY: CODEX-R14-P1-01,CODEX-R14-P1-02,CODEX-R14-P1-03
CLOSED: CODEX-R13-P1-01,CODEX-R13-P1-02,CODEX-R13-P2-03
STATUS: DONE
## COMPOSER-R14-P2-01

**斷言**: `C5-25` 之 mutation 欄指 `M-SU-D2-19`，但該 mutation 描述「survivor 六鍵雜湊含 feature TF」，與本列處置「餵入端先去重否則重複三元組改變雜湊」不是同一可紅缺陷。

**碼證**: `docs/SPLITUNIFY_SPEC.D-002.md:120`（register `C5-25`）對照 `:296`（`M-SU-D2-19` 改壞什麼）；`momentum/Analysis/event_samples/ic_feed.py:142-145` 為餵入端雜湊（dedupe 語意），與 TF 入鍵無關。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#7455b305c6f3

[P2] doc-literal-only 否（影響 mutation 網覆蓋）。修法：新增專屬 mutation（例：餵入 `keep` 未 `drop_duplicates` 即算 hash）並改 `C5-25` 指向之；可行性＝`ic_feed.py:142-145` 為單一 hash 輸入點。信心度=High。v13 前既有，不阻本輪 v14 三處修補收斂。

---

## COMPOSER-R14-P2-02

**斷言**: `Task 9.3` 新 receipt 閘驗 exact ID set 後，仍可提交 29 行唯一 ID 但分類全為 `甲 -> 甲`、碼證填占位 path，不證明逐條重掃。

**碼證**: `docs/SPLITUNIFY_TODO.md:636-640` 僅要求 ID set 與格式；探針 `scratchpad/receipt_bypass.txt`（29 唯一 ID + 全 `甲 -> 甲`）→ `diff <(grep register IDs) <(receipt IDs)` rc=0。

**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f

[P2] 修法：驗收加「至少一列改前≠改後 **或** path 須為 repo 內存在之檔」；可行性＝`test -f` 迴圈即可。信心度=High。相較 R13 行數閘已關重大繞過，本條為殘留摩擦。

---

VERDICT: proceed
BLOCKED-BY:
CLOSED:

ASSUMPTIONS_VERIFIED: body sha256 7455b305…；36/36 mutation；29 register；R13 三條+主委 C5-21 CLOSED；receipt dup 繞過 FAIL、全甲 bypass PASS；pandas KeyError 路徑  
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md`；`grep -cE` 計數；receipt 繞過探針（scratchpad）；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` rc=1（預期，待 v14 戳記）；收尾 `bash scripts/completeness_check.sh --single handoffs/20260911-splitunify-b9-review-r14-composer.md --family composer`  
FAILURES_SEEN: none（stamps_check rc=1 為預期）  
SCOPE_CHANGES: none（戳記 append 除外）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only；v14 body 已由 9ec33871 引入）

STATUS: DONE
## GROK-R14-P1-01

**斷言**: `C5-29`（`tables.py:372` assignments 消費須去重／fail-closed）仍指向 `M-SU-D2-06`，而該條破壞的是甲類 `.loc[eid]` **被誤改為複合鍵**且應紅於 receipts／clusters——與「略過 :372 去重」不同缺陷，屬與 R13 `C5-20`／`C5-21` 同型的 mutation 錯配。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/tables.py:372
MUTATION: 保留 `assignments.set_index("event_id")["symbol"].reindex(idx)` 不去重、不 fail-closed；多 TF 下索引重複時靜默取錯 symbol——現行 `M-SU-D2-06` 之應紅測試只覆蓋 receipts／clusters 誤改複合鍵，不會因此轉紅。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[BLOCKING] 信心度=High。修法：新增 `M-SU-D2-37`（WHAT＝`:372` 略過去重／fail-closed；應紅＝`test_tables.py` 具名「assignments 消費去重」測試），`C5-29` 改指之；`M-06` 仍歸 `C5-13`。可行性：`:372` 已存在且 SPEC 已標丙類真缺陷；與 R13 新增 M-35／36 同形手術。條數 36→37（若併 P1-02 則→38）。

---

## GROK-R14-P1-02

**斷言**: `C5-25`（survivor 餵入端須先去重）仍指向 `M-SU-D2-19`，而該條破壞的是六鍵**被改成含 feature TF**——與「餵入略過去重致重複三元組改雜湊」不同；`M-19` 應只覆蓋 `C5-10`。

**碼證**: CODE-ANCHOR: momentum/Analysis/event_samples/ic_feed.py:143
MUTATION: 多 TF 下把含重複 `event_id` 之窗列直接餵入 `event_context_from_windows`／survivor 六鍵組裝且**不**先 `drop_duplicates(event_id)`，鍵集仍不含 TF——雜湊漂移但 `M-SU-D2-19`（鍵含 TF）之測試仍可綠。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[BLOCKING] 信心度=High。修法：新增 `M-SU-D2-38`（餵入略過去重；應紅＝Task 9.3／`test_gap3_conditional_ic.py` 具名「餵入去重後雜湊穩定」），`C5-25` 改指之；`M-19` 留 `C5-10`。可行性：`(5.1)`／`(5.4)` 已明文要求餵入去重；缺的是專屬反向 mutation。

---

## GROK-R14-P2-03

**斷言**: `M-SU-D2-35`／`36` 之「應紅之測試」只寫欄缺 ⇒ `duplicated(...KeyError)`，未禁止 `in df.columns` 軟包、未要求多 TF fixture——單 TF＋軟 subset 可對欄缺維持綠。

**碼證**: 實跑 `python3`：單 TF `DataFrame(event_id=[1,2])` 無 `feature_timeframe`，`subset=["event_id"]+([..] if in columns else [])` ⇒ `any_dup=False`；對照無條件 subset ⇒ `KeyError`。SPEC L312–313 現文字面僅提 KeyError。

**來源摘要**: docs/SPLITUNIFY_SPEC.D-002.md#39f981a4a636

[MAJOR] 信心度=High。doc 面可修：把應紅欄換成必答 (3b) 字面。非空殼。

---

## GROK-R14-P2-04

**斷言**: Task 9.3 新 receipt 閘在 exact ID set 之後，仍可用「正確 ID 集合＋分類全填同一值」或「任意 COMMIT sha」通過檔案級機械條件。

**碼證**: `/tmp/grok-r14-receipt-sim/bypass-sameclass.txt`：`diff` ID set rc=0 且每列 `甲 -> 甲 nowhere:0`；對照 duplicate-ID 檔 `diff` 非 0（證明只堵了 R13 具名洞）。TODO L632–639 無 audit／HEAD 強制命令。

**來源摘要**: docs/SPLITUNIFY_TODO.md#5738e9c63f6f

[MAJOR] 信心度=High。修法見必答 (4b)。不阻擋「是否掃過 29 ID」之主目標，但可假完成語意重掃。

---

VERDICT: blocked
BLOCKED-BY: GROK-R14-P1-01,GROK-R14-P1-02
CLOSED:

ASSUMPTIONS_VERIFIED: body sha `7455b305…`；mutation 36 連續；§C-9 認領 36；register 29；doc_format 雙綠；R13 三條＋C5-21 字面落地；stamps 對新 body FAIL（預期）；stamp 腳本 `tail -1`；C5 逐列對照得 2 錯配；KeyError／軟 subset 實跑；receipt 兩構造實跑
TESTS_RUN: `bash scripts/reconcile_body_hash.sh docs/SPLITUNIFY_SPEC.D-002.md` → `7455b305…`；`bash scripts/doc_format_precheck.sh` SPEC／TODO → rc=0；`bash scripts/reconcile_stamps_check.sh docs/SPLITUNIFY_SPEC.D-002.md` → rc=1（hash mismatch）；receipt sim ID-set／dup 構造；pandas KeyError／軟 subset 探針
FAILURES_SEEN: none
SCOPE_CHANGES: none（未改 SPEC／TODO 正文；僅將 append REJECTED 戳記）
NUMERIC_OR_SCHEMA_IMPACT: none
OUTPUT_PATH: handoffs/20260911-splitunify-b9-review-r14-grok.md

STATUS: DONE
