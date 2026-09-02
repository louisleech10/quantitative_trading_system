# GAP-3 事件型 UAT 缺口修補 — SPEC

<!-- SYNC-FORBID: 正反例由 \*\*t0 條件\*\*決定 -->
<!-- SYNC-FORBID: 掃描條件引用之 `future_\{N\}bar_return` 欄 -->
<!-- SYNC-FORBID: lookahead_bars.*=.*72 -->
<!-- SYNC-FORBID: future[0-9]+_[^→]*→[[:space:]]*[0-9] -->
<!-- SYNC-FORBID: contractAccepted -->
<!-- SYNC-FORBID: 二擇一 -->
<!-- 上一條之出處（R11）：主委在 R10 之 §D-3′-a（ii）原寫「TODO 二擇一」（已撤回），其中一個選項
     （把深度折進 label 窗）**根本不可行**，三家全員命中；R11 自查又在 Task 1.3 找到
     第三處（浮點 digest「前端自算或後端算」之二擇一；原寫如此，已改為定案）。
     形態一致＝**把「我還沒想清楚」包裝成「留給實作者選」**；實作者沒有主委手上的碼證，
     只會挑看起來簡單的那個。⇒ 規格內**不得**出現未定案之實作分叉字面。
     歷史／撤回敘事以既有豁免詞（撤回／已改／原寫／不得…）標示即可通過。 -->
<!-- 上列由 `scripts/spec_ruling_task_sync.sh` 機械強制：
     ①每條 `**D-<n>` 裁定須被 §P 至少一個 Task 引用（否則只停在敘述層）
     ②禁用語不得在 §P 殘留。
     出處＝2026-08-22 R3 之三條 P0（Task 4.1b 寫死 scenario 專屬文案／Task 2.1b 未同步 D-7 L1／
     Task 1.10 把 future72 之 72 誤當根數），皆為「改 §D 未同步 §P」之同一病根，
     `feedback_cross_reference_sync` 載此類錯已犯 7 次 ⇒ 改以閘門而非紀律。 -->

出處：使用者 2026-08-22 跑完 UAT B1–B13 後提出的 10 條問題。
本 SPEC 涵蓋**事件型**那批（#0/#1/#2/#3/#4/#5/#6 ＋ #9a 止血閘）。
#7 為回答性問題（已答，見 §N）；**#8/#10 之殘留於 R4 撤回，改為本批 Task 7.7**（見 §N 與下表群集 C）；
#9b 規模防護本體排入 GAP-6。

> ## 🔴 R 重開（2026-09-02，依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.1；**非 D 延伸**）
>
> **為何是 R 而非 D**：使用者 2026-09-02 裁定（原話）「上傳都有要填答案窗了，那 G3-D1 這在 /search 的
> 新增條件都不用了吧，使用者直接 CSV 篩選就好」⇒ **整區移除 `/search` 匯出前篩選**。
> 這推翻了本檔 **§A `A-1`（已確認：「匯出前篩選與上傳自篩 CSV 兩者都做」）** 與 **Phase 2 之定位字面**
> （「本批唯一能把答案窗宣告變成機器可證事實的路徑」）＝§2.1「既有設計被證偽」；§2.2「與原檔互斥 ⇒ 不是 D」。
> 三家 consult 一致（`handoffs/reconcile/20260902-gap3ux-x-consult-r1/synth.md`，本機留存；
> `CODEX-R1-P0-01`／`COMPOSER-R1-P0-01`／`GROK-R1-P0-01`）。使用者離線 ⇒ 依 §2.1「爭議預設 R」。
>
> **效力**：本檔 R1–R34 之戳記**作廢**；`docs/GAP3_EVENT_UX_TODO.D-001.md`…`D-005.md` **全部
> `SUPERSEDED-BY-R`**（v2.0 安全閥①：全量作廢，不做只作廢重疊者），內容依下表併回；
> 本檔須**重跑完整對抗審**（whole-body；依賴閉包只作必讀 focus，**未列入者仍受審、仍重簽**）。
>
> **本次 R 之變更（裁定本體＝§D **D-8**）**：
> ① **Phase 2 退役**（Task 2.1／2.1b／2.2／2.3 標 ⛔ RETIRED；`/case/lookahead-depth` 端點與前端
>    `exportFilter*`／`lookaheadDepthLock*`／篩選面板退役；`label_definition.filters` 不再由匯出端寫入）。
> ② **答案窗深度之唯一來源改為「使用者於批次建立時之逐 tf 宣告」**（`declared_window_bars` map），
>    兩條路徑同一規則、同一 validator：CSV 匯入（Task 1.9）與 **`/search` 匯出（新 Task 1.9′）**；
>    `lookahead_bars_declared[tf] = declared_window_bars[tf]`，**不再與條件引用欄取 max**（無條件可引用）。
> ③ **匯出端 fail-closed 等價替代**：`withExportLowerBoundGuard` 改形為 `withExportDeclarationGuard`
>    （保留 D-004 A-021 之 `proceed` 結構保證），缺 map／缺 tf／非 int／調低未勾聲明 ⇒ 匯出不發生。
> ④ **purge 規則不變**（§D-3′-a（ii）權威式原樣），只換其 `lookahead_bars_declared` 之來源；
>    使用者 8/31 裁定「purge ＝ 正反例篩選深度取大者」以**宣告框文案**承載（使用者填的是兩者之最遠者）。
> ⑤ Task 1.5／2.3 之 `computeExportCounts` **保留**（1.5 仍用，空條件＝恆等）；`/search` 改顯示 M／X／Y。
> ⑥ Task 4.1③／4.1b／7.3 之「深度來源」改為「使用者宣告」；§V V-12 改寫；Task 1.11 之 L2 由
>    「未知欄才觸發」改為「一律宣告」（L1 registry 保留供揭露與 rename 攻擊防護）。
>
> 🔴 **D-001…D-005 逐節落點表（併回完整性之唯一憑據；R 對抗審須逐列核）**：
>
> | 延伸檔 | 條目 | 落點／處置 |
> |---|---|---|
> | D-001 | A-001（§B B1 列含 2.1b、4.2 S-9） | **改寫**：B1 ＝ 1.1、1.10、4.2（S-9）；2.1b 退役 ⇒ 自 B1 移除（TODO §B B1 列＋「B1 之實際內容」句；R35 三家對證：成立） |
> | D-002 | A-002（S-9 ≥7 條、⑦ 重複 h raise） | **併回**：Task 4.2 驗證（SPEC「≥7 條」；TODO Task 4.2 與 Phase 4 Gate 同步）——R35 前為假（仍寫 6 條），已修 |
> | D-002 | A-003（小時→根數 `ceil`） | **併回**：Task 1.10 內容「換算捨入方向＝向上取整；registry `hours_to_bars_rounding: "ceil"`」——R35 前 SPEC 沉默，已補 |
> | D-002 | A-005（`future{1,2,4,6}_close_return` 為 bar 命名） | **併回**：Task 1.10 內容第一子點（以 producer `shift(-N)` 為準）——R35 前 SPEC 仍列為小時命名（**P0**），已修 |
> | D-002 | A-006／A-008／A-009／A-011／A-012／A-013（S-9 對照組、AST 綁定、CPython 例外、負例、參數面、共用 traversal） | **併回本體**（各對應 Task 之驗證欄既有條文；R35 三家未逐條證偽，標「未全證」——閉合輪對證） |
> | D-002 | A-004／A-007／A-010／A-014（2.1b 前端下界值來源／真實呼叫點／行為級驗收／文案子字串） | **自然關閉（Phase 2 退役）**；A-010 之「把匯出包進 `proceed`」結構保證**移植**至 Task 1.9′ 之守衛（R35 三家對證：成立） |
> | D-003 | A-016（`mapping_provenance` 七欄＋批內單一 digest invariant） | **併回**：Task 1.6 內容與驗證①–④——R35 前仍四項（**P1**），已修 |
> | D-003 | A-017（Task 1.3 承載點＝`api/routes/case_search.py`） | **併回**：TODO Task 1.3「修改檔案」——已修 |
> | D-003 | A-019（digest 單位互斥） | **併回**：Task 1.3 舊句劃掉、以 `/search` 完整 CaseData canonical digest 為唯一定義——已修 |
> | D-003 | A-018（Task 2.2 後端序列化函式字面） | **自然關閉（Task 2.2 退役）** |
> | D-004 | A-020（匯出欄納入契約） | **併回本體**（契約 `optional_fields` 之 `future_{h}bar_return`×12 與 `lookahead_bars_declared`；Task 4.1）——R35 三家對證：契約側成立 |
> | D-004 | A-022（G-2 不重凍） | **併回**：Task 4.2 驗證改「`gap3_freeze_golden.py --check` rc=0 且 sha 不變、不重凍」——R35 前仍寫重凍（**P2**），已修 |
> | D-004 | A-021（下界守衛改形、不刪不留死碼） | **移植**：守衛改名為 `withExportDeclarationGuard`，`proceed` 結構保證不變（Task 1.9′；R35 三家對證：成立） |
> | D-005 | A-023（`PreparedAnalysisWindows.direction_sign`） | **併回**：Task 7.0b 欄集第十欄＋要件①–④（signed 公式／hash 綁定／三驗收／四 mutation）——R35 前欄集無該欄（**P0**），已修 |
> | D-005 | **A-024**（⑧(a) 前綴判準改逐 namespace） | **併回**：Task 1.1 驗收 ⑧(a) 四條並列判準——R35 前**整條漏列於本表**（GROK-R35-P1-01），已補 |
>
> ⚠️ 本表首版為主委手寫、未逐列 grep 對證——R35 三家全部命中「宣稱併回、本體無字」（與 P16 群 1 同型）；
> 上表「已修」各列之落點於閉合輪由原提出方重跑 grep 對證。

**版本**：R36-landing（🔴 **R 重開**；R35 全檔對抗審 23 findings（codex 9／composer 7／grok 7）全部採納已落地；R36 閉合輪 20 CLOSED／3 PARTIAL＋4 條相鄰漏改已修，待 R37 閉合＋三家戳記；收斂履歷：R1 24 → R2 7 → R3 18 → R4 19 → R5 13 → R6 15 → R7 12
→ R8 17 → R9 14 → R10 11 → R11 20 → R12 15 → R13 14 → R14 18 → R15 10 → R16 9
→ R17 12 → R18 8 → R19 8 → R20 12 → R21 14 → R22 9 → R23 11 → R24 8 內容＋1 流程 P0 → R25 13 → R26 15 → R27 15 → R28 12 → R29 8 條 findings（**composer 降至 1 條**；兩件跨包衝突已解除）；**P0=0**；**(N)=0 連十四輪**；🔴 R27 判 (丙)、R28 判「新法尚未有效」⇒ 改採 `scripts/gap3ux_apply_patch.py` 全行對證（must_exist 不再由主委自選）；🔴 R20／R21／R22 三輪之治理裁定（停止新建機制／條件②′／主委不得自我歸類＋②′(2) 換指標）皆見角色卡）。
🔴 **`ERRATA-R30-01`——R30 輪之 `-landing` 字樣不代表有內容落地**：R30 輪（ledger round
`03422383-21ae-4efb-ab14-a3214950522e`）因 codex 交件格式不合規、且「同輪重派需 dispatch token
／`gate.sh` 於 OPEN 債時拒發」構成主委路徑上的死鎖，已依設計逃生口
`debt_clear --abandon --kind collection-failed` 銷帳，**該輪零 findings 落地、SPEC 內容一字未改**。
本行之 `R30-landing` 係 `gap3ux_header_round_check.sh` 對「已終結輪次」之固定字面格式要求
（該閘於 R19 起將 ABANDONED 與 CLOSED 同等對待），**屬帳本收據，非內容宣稱**。
## 🔴 **狀態：FROZEN**（2026-08-24，**使用者裁定**）

**42 Task 定版**，自 R34 起不再受理規格審查輪次。

**凍結依據**：量化正確性面已到位——P0＝0；全新缺口 (N)＝0 **連二十輪**；
Task 42 **連三十四輪未增未減**；三方資料正確性 scope 內無未結項。

🔴 **誠實邊界（不得美化）**：委員定之四條件中，**條件①（OPEN P1＝0）並未滿足**（凍結時 P1＝11）。
使用者於 2026-08-24 直接裁定凍結，**覆蓋**該條件。理由與代價逐條記錄如下，未來回頭者請先讀：

- 那 11 條 **無一為量化正確性**：全部是（a）主委落地字面之對證工具缺陷、
  （b）治理閘互相打架（同輪重派死鎖、作廢輪收據、補丁包檔名碰撞）、
  （c）編排草圖含 illustrative 佔位故不通過 `compile()`。
- 🔴 **這批問題是主委自己造出來的**：R27 三家判定瓶頸為主委之落地方式後，
  主委的反應是**新建對證工具**（R28）而非提高抄寫精度；此後六輪都在修該工具，
  並把工具問題寫進每輪派工單 ⇒ 委員回更多治理 findings ⇒ 再生下一輪。
  **此舉違反使用者 2026-08-14 之裁定「回量化主線、治理不再擴建」**（見 `CLAUDE.md`）。
- **本次不另立治理票**：依同一裁定，開新票只是換包裝。四類殘留具名記錄於 §N，**不排工**。

**（FROZEN 之四條件定義見 `docs/GAP3_EVENT_UX_ROLE_CARD.md`，本檔不重述。）**
🔴 **R17 已由委員裁定條件④＝(甲)**（composer＋grok 兩家）：條件④之量測範圍＝**當輪**補丁包；
歷史輪之 anchor 債以具名紀錄結案（見 §N）。主委未參與該裁定（受益方）。
🔴 **本行為單一 current-round receipt**：每輪落地須同批更新，**不得**停在舊輪次
（CODEX-R14：本行自 R8 起未更新，會誤導 reviewer 對 FROZEN 狀態之判讀）。
🔴 **R16 起本行由機械閘強制**：`scripts/gap3ux_header_round_check.sh`
（掛在 `gap3ux_pre_review.sh`）——SPEC 有未提交改動時，本行輪次須等於已有委員產出之
最大輪次，否則 fail-closed。**該閘上線首跑即抓到本行仍停在 R15**（散文版沒抓到）。

🔴 **本版之產生方式與前五輪不同（使用者 2026-08-22 裁定）**：
R5 之 13 條中**有 5 條為主委 R4 修訂自行引入**（R4 亦有 3 條），共 8 條形態一致——
**改了 §P 之權威定義，未同步 §V 之複述**。出錯的是「主委選擇怎麼修」這一步。
使用者逐字裁定：「乾脆你直接問委員要怎麼修，然後照著做?」
⇒ 開 consult 輪（`handoffs/20260822-gap3ux-x-consult-r2-brief.md`），
三家各交 10–11 條**四欄修法**（改哪裡／改成什麼成品文字／怎麼驗／**必須同步哪些其他位置**），
主委**照抄實作、不自行發揮**；三家 Verdict 一致「照抄後進 R6」。
**A-6′ 已於 R8 經使用者 2026-08-23 逐字裁定確認**（見 §A）；FROZEN 之其餘條件見角色卡。

**R5 十一群集之落點**（reconcile：`handoffs/reconcile/20260822-gap3ux-x-review-r5/synth.md`）：

| 群集 | 內容 | 落點 |
|---|---|---|
| A | §V 複述 §P 之斷言（V-11 等六列雙源） | **§V 書寫規則**＋六列引用化＋Task 7.2 標題與覆蓋風險＋新閘 `spec_v_task_ref_check.sh` |
| B | G-2 無 dict→bytes encoder | **§G S-9** |
| C | 三組報酬表與 S-1 八鍵互斥 | **§G S-1a／S-7a**＋Task 7.5 輸出形狀 |
| D | `horizon_bars→ms` 之 tf 來源未定 | **Task 7.7 ①②**（逐列取事件列 tf；**注入之** `timeframe_seconds`——R24 更正：原寫 module 常數，與 L3006 注入模型互斥） |
| E | Task 7.7 左界未扣 `decision_offset_bars` | **Task 7.7 ③**（左界改 `decision_at_ms`） |
| F | 匯出固定取 `future_${h}bar_return` 與宣告不符 | **Phase 7 前言 F-1..F-5**＋Task 7.0 ⑦⑧ |
| G | `counterexample_kind` 為逐列選填欄 | **維度由六改五**＋逐列映射規則 |
| H | `/search` 放行 `two_stage` 但無 producer | **Task 7.1 邊界**＋`pathExclusions` 擴充 |
| I | `mixed_control_kind_in_batch` 未登記契約 | **Task 7.5**（`ic_report_contract.json` 之 `event_return_table`） |
| J | `facts.sh` 未開 pipefail ⇒ 假 rc=0 | 主委直接修（工具 bug，非 SPEC 判斷） |
| K | §A 之 A-6 自相矛盾 | **§A**（A-6 待白話閘；確認前不得 FROZEN）。🔴 **R8 已結案**：A-6 之前提被使用者裁定推翻而整條作廢，取代者 A-6′ 已確認，見 §A |

**三家分歧之裁決點（全部記錄，不隱藏）**：
S-9 尾端 newline 禁用（2:1）／S-9 章節編號（2:1）／`by_label` 鍵名逐鍵取多數
（`positive`／`negative` 2:1、`all` 2:1）／新閘命名採 composer／
群集 K 之嚴格度採 composer。
**唯二不投票者**：①`RunInfo.time_range` 型別依**實碼**裁 `str|None`
（grok 之 `int|None` 與 `_resolve_l7_v2_time_range` 之簽章不符）
②Task 7.7 ④之 ISO 字串 parse 規則為**主委補充**（三家皆未觸及該層），已具名標為待 R6 裁定。

🔴 **主委自承（保留為警示，不得刪）**：R4 19 條中 3 條、R5 13 條中 5 條由主委修訂自行引入，
另 R3→R4 有 1 條不實宣稱。三家能抓到，是因為 brief **事前具名標示「該批改寫未經任何審查」**。

**R4 十九條之落點**（reconcile：`handoffs/reconcile/20260822-gap3ux-x-review-r4/synth.md`）：

| 群集 | 內容 | 落點 |
|---|---|---|
| A（＝R3 遺留 **D**） | Task 7.2 只驗集合、可被 disabled 湊過、無 round-trip；`enum`(4) vs `accepted`(3) 基準不明 | 新增 **Task 7.0**（先擴 `EventExportOptions`）；改寫 **Task 7.1／7.2** 為三層驗證，比對基準＝`selectable(path,dim)`；**V-11 改為純引用**（R5 consult 裁，見 §V 書寫規則） |
| B（＝R3 遺留 **F**） | G-2 canonical serialization 未定義 ⇒ 不可位元組級證偽 | **§G 新增 S-1..S-8**；Task 2.2 改為純引用 |
| C（＝R3 遺留 **E**） | IC 分析頁與 Feature Library `time_range` 對證缺口；且檔頭禁殘留而 §N 仍殘留 | 新增 **Task 7.6／7.7**、**V-14／V-15**；**§N 之 #8／#10 殘留撤回** |
| D（＝R3 遺留 **G**） | A／B 之 label 來源與機械深度未定義 | **Task 7.1「邊界」**加路徑級限制（`/search` 本批只開 C／two_stage）；**深度公式**落 Task 2.1b，由 1.9／V-12 引用（⛔ R 重開後：2.1b 退役，深度＝Task 1.9／1.9′ 之使用者宣告，見 D-8） |
| E（**新面**） | D-7 L3 之「不進 split 但仍可產表」與實碼呼叫鏈矛盾 | **Task 1.12** 增 `run_event_study_only()` 契約＋`ci` 標 unavailable |
| F（**新面**） | `control_kind` 未進 manifest ⇒ Task 7.5 分組讀不到 | **Task 7.5** 明定唯一傳遞點＋混值 fail-closed＋`not_computed` schema |
| G（**新面**） | registry 可被改名攻擊繞過 | **Task 1.10** 增信任邊界（系統產生欄 vs 外部上傳欄）＋改名 mutation |
| H（R3 群集 C 之殘段） | R3 版 §D-7 L1 原寫 `future72_max_*→72`（暗示根數＝72），與 Task 1.10 之「存 `lookahead_hours`、12h⇒6 根」矛盾 | **§D-7 L1 已改寫**；新增第 3 條 `SYNC-FORBID` 涵蓋該形態 |
| I（**新面**） | Task 6.0 驗證欄為 `python3 -c "..."` 佔位卻通過機檢 | **Task 6.0 補完整命令**；`doc_format_precheck.sh` 增佔位形態偵測 |

🔴 **主委自承（保留為警示，不得刪）**：R4 十九條中，**2 條由主委 R4 前之改寫直接引入**
（群集 B 之 Task 2.2 對不存在的定義下同步義務；群集 C 之檔頭禁殘留與 §N 殘留互斥），
另 **1 條為主委不實宣稱**——R3 版檔頭寫「C（future72 單位）已修」，而 §D-7 L1 之敘事**未改**。
三家皆據主委事前於 R4 brief 具名標示之「該批改寫未經任何審查」查出。

---

## §RISK 風險分級

RISK-HIT: a,b

- **(a) 數值/資料品質**：Task 1.2 讓使用者指定「哪一欄是 label」。
  **三家 R1 一致指出：`label` 的語意正確性在機械上不可證明**——使用者若對映到另一個
  恰好也是二元的欄，所有 fail-closed 檢查全過，而條件 IC／正反例辨別表**靜默錯誤**。
  ⇒ §D-1 之處置：把它明確定義為 **user assertion（使用者聲明）而非系統保證**，
  並以 provenance／預覽確認／可疑欄警示三層降低誤指機率。
- **(b) 跨模組/共用路徑**：動 `api/routes/case.py`、`frontend/src/`、
  `momentum/Analysis/event_samples/`，跨 api↔momentum↔frontend 三層。
- **非 (c)**：各 Phase 獨立 commit，可逐一 revert。
- **非 (d)**：不動回測與 ML 正確性路徑。

---

## §D R1 六條 P0 之裁定（本版新增；R2 起為 SPEC 的一部分）

**D-1（CODEX-R1-P0-01 ＋ COMPOSER-R1-P1-01 ＋ GROK-R1-P1-01，三家全員）
`label` 正確性不可機械證明 ⇒ 改以 user assertion 定義**
接受。`label` 之語意由使用者聲明，系統**不宣稱**其正確，只保證：
① 照抄使用者指定之欄（V-1）②記錄對映 provenance 使日後可追（Task 1.6）
③ 送出前強制預覽確認（Task 1.5）④對「多個欄都是二元」時出示警示清單（Task 1.7）。
SPEC 與 UI 文案一律用「你聲明的正反例標記」，**禁用「label 正確」字樣**。

**D-2（COMPOSER-R1-P0-02 ＋ GROK-R1-P0-01，兩家獨立命中）
`event_id` 必須與既有匯出一致，不得另發明**
接受，且我的原設計是錯的。現行 `frontend/src/lib/eventExport.ts:88` 為
`` `${symbol}:${timeframe}:${t0}` ``（含 timeframe、不含 label、非 sha256）。
我原寫 `sha256(symbol,t0,label)[:16]` 會使**同一事件經 Excel 回灌後 id 改變**，
直接打斷使用者「匯出→Excel 細篩→CSV 回灌」的閉環，且使我自訂的 V-3 在真實對照下不可達。
⇒ CSV 路徑**沿用同一 canonical**，見 Task 1.3。

**D-3（R8 架構調整；使用者 2026-08-23 提出、三家碼證確認）條件 IC 之答案窗層次裁定**

🔴 **本裁定取代 R1 之 (a) 方案**（原文保留於下方「原裁定與撤回理由」）。

**使用者原話**：「條件 IC 本來就算一種類型的 IC-Analysis，條件給定應該就是要在
IC 分析的頁面，而不是 `/search` 吧」。

**採 (d) 分析時計算**：
- `/search` 匯出**只承載事件事實**——t0、`label`（來自 t0 條件之 `positive_case`）、
  五維度契約設定。
- **不得**在匯出端寫入 `label_value`。
- 答案窗（`horizon_bars`）與報酬語意（`entry_price_semantic`／`label_return_mode`／
  `decision_offset_bars`）於 **IC 分析頁**由使用者給定；
  後端以 `bars_from_kline_cache` ＋ `align_events` **同一公式**於分析時計算。

🔴 **D-3′-a｜匯出端仍須寫 `label_definition.window.horizon_bars`，但其語意改變**

**主委裁決點（兩份補丁包互斥；依角色卡「在具體提案之間裁決並記錄理由」）**：
- `-arch-shift.md` 之 D-3 diff 主張「**不得**在匯出端寫入
  `label_definition.window.horizon_bars`」。
- `-arch-analyze-time-label.md` §3 主張「既有批若帶烤入之 `label_value`／**窗欄**：
  分析端以本次 h 重算並覆蓋**分析用副本**」——其前提是**匯出仍帶窗欄**。

**採後者。理由為實碼 receipt，非偏好**：
`momentum/Analysis/event_samples/import_contract.py:163` 對 `label_definition.window`
強制 `horizon_bars` 為 `int ≥ 1`，缺欄／非法即 `missing_required_field`；
且 `label_definition` 在 `event_import_contract.json` 之 **`required_fields`** 內
（`label_value` 則在 `optional_fields` ⇒ 省略合法）。
⇒ 照 `-arch-shift` 實作，匯出檔**一律無法匯入**，該句不可實作。

**改採之語意（本節為權威，他處只得引用）**：
| 欄 | 屬哪一層 | 誰寫 | 誰讀 |
|---|---|---|---|
| `label_definition.window.horizon_bars`（匯出檔內） | **事件事實層** | `/search` 匯出端 | 深度之**序列化投影**（`max(1, map[該列 tf])`）；深度 oracle 為 `lookahead_bars_declared` |
| 條件 IC 之答案窗 `h`（`event_label_spec`） | **分析層** | IC 分析頁 | 分析時 label／purge |

- 匯出檔內之 `window.horizon_bars` ＝ **`max(1, lookahead_bars_declared[該列 timeframe])`**
  ——它是**深度之序列化投影（含 floor）**，**不是**深度 oracle、**更不是**條件 IC 之答案窗。
  🔴 **R11 更正（GROK-R11-P1-08）**：R10 版此處寫「＝該批 label 定義所引用之最遠未來根數」，
  與同節（i）「不得讀 `horizon_bars` 當深度、一律讀 map」互相招募 ⇒ 已改為明寫其為投影。
  深度之唯一 oracle ＝ derived 欄 `lookahead_bars_declared`（map）。
- 分析層**禁止**把匯出檔之 `window.horizon_bars` 讀為答案窗；
  答案窗只能來自本次 `event_label_spec`（見 D-3a）。
- `/search` 之 `label` 由 t0 條件判定（`scenario=C`、無品質過濾）⇒ 該欄之值為 **lookahead 深度**，
  🔴 R 重開（D-8）：由**使用者於匯出前逐 tf 宣告**（Task 1.9′），**不得**由任何欄位推導（原「依 D-7 由實際引用之欄位導出」已退役）。

🔴 **R9 已裁定（原「待 R9 裁定」之兩項，三家皆有回覆；以下為裁定後之權威條文）**：

**（i）深度 0 與契約下限 1 之衝突 —— 裁定：保留契約下限 1，另登記真實深度欄**
D-7 明訂 `scenario=C` 且無品質過濾時 lookahead 深度 **＝ 0**
（實查證之既有批 `20260822T011331Z-eb210a16.json` 即此形態），
而 `import_contract.py:163` 之下限為 `int ≥ 1` ⇒ 深度 0 **無法寫進該欄**。

- **契約下限維持 1，不改為 0**（改下限會放寬既有 fail-closed，§C0 禁；三家一致）。
- `label_definition.window.horizon_bars = 1` 在深度 0 時**僅是 serialization floor**，
  **不是**深度 oracle。
- **真實深度**寫入契約新登記之 derived／receipt 欄 **`lookahead_bars_declared`**
  （登記處＝`momentum/Analysis/contracts/event_import_contract.json` 之
  `derived_fields.names` ＋ `receipt_schema`；先改契約，D-6）。
  🔴 **R10 修正其型別**：該欄為 **`Mapping[timeframe -> int >= 0]`**（逐 tf 各一值），
  **不是** scalar——理由與碼證見下方（ii）之「R10 修正」（小時命名欄 `future72_*`
  在不同 tf 之根數不同，批次 scalar 在混 TF 批次沒有唯一值）。
  單一 TF 批次退化為單鍵 map。**型別與非負性須機械驗收**（Task 1.1 ⑧）。
- 🔴 **所有下游一律讀 `lookahead_bars_declared`，不得讀 `window.horizon_bars` 當深度**：
  Task 1.9／1.9′ 之宣告寫入（R 重開；原 Task 2.1b 之深度公式已退役）、Task 4.1 ③ 之匯出寫入、Task 4.1b 之 UI 揭露、
  本節（ii）之 purge 式、§G G-3 之 golden。深度 > 0 時兩值相等。
- **receipt 缺該欄 ⇒ fail-closed**，不得以 `1` 默認替代。
- ⚠️ 主委 R8 版原寫「寫 1 屬保守偏差、可接受」——**該說法被 CODEX-R9-P1-03 推翻**：
  把 1 當真實深度會使 UI／purge／golden 互相不一致，且違反 §C0「過度 purge 亦屬錯誤」（原引 Task 2.1b，該 Task 已隨 R 重開退役）。
  ⇒ 改為「floor 只影響序列化欄位，深度語意另有其欄」。

**（ii）purge 下界 —— 裁定：逐列解析深度為 ms、逐 split scope 取 max、per-scope embargo**

出處＝R9 三家全員（CODEX-R9-P0-02／COMPOSER-R9-P0-01／GROK-R9-P0-01）指出 R8 版
`max(lookahead 深度, 本次 h 窗寬)` **混用單位**；R10 再由 CODEX-R10-P0-01 指出主委 R9 之
換算式**本身仍錯**（見下方「R10 修正」）。

**權威式（本節為唯一定義；Task 7.0b／§G G-3 只引用）**：
```
# 逐 timeframe 之深度（bars）；🔴 R 重開（D-8）：來源＝**使用者逐 tf 宣告** declared_window_bars[tf]
#   （Task 1.9 匯入端／Task 1.9′ 匯出端，同一 validator），不再由條件引用欄導出（Task 2.1b 已退役）
lookahead_bars_declared : Mapping[timeframe -> int >= 0]     # 批內每個出現過的 tf 各一值 ＝ declared_window_bars

lookahead_depth_ms(e) = lookahead_bars_declared[e.timeframe] * timeframe_seconds[e.timeframe] * 1000
#   🔴 R22（COMPOSER-R22-P1-02）：`timeframe_seconds` ＝ **注入之 map**
#   （見 §G G-3 ⑥(d) 之 keyword-only 簽章），**不是** module-level `TIMEFRAME_SECONDS`。
#   原文寫死 module 常數，與 R20 之注入改法互斥——**撤回未清乾淨之第四處**。
label_window_ms(e)    = row(e).label_end_ms - row(e).label_start_ms   # 分析時 align_events
                        # row(e) ＝ windows 中 event_id == e 之唯一 WindowRow
                        # 🔴 R15：windows 已是 tuple[WindowRow, ...]，**不得**用 windows[e] 下標
purge_lower_bound_ms(scope) = max over e in scope of max( lookahead_depth_ms(e), label_window_ms(e) )
                              # scope ＝ symbol（event_split.py:54 之 groupby）；R10 鎖 per-scope embargo
                              # e ∈ aligned_pre_coverage_windows（見下方 R26 之角色分離）
```

🔴 **R26：兩個 pre-coverage 集合之角色分離（採 CODEX-R26-P1-02 補丁包）**
**問題**：權威式之 `row(e)` 指向 alignment receipt 之 `WindowRow`，而階段 2 之 purge 輸入
又被寫成「coverage 前之**全部**事件」。碼證 `alignment.py:199-218`：**對齊失敗之列只進
`failures`、不會產生 `event_level`／`WindowRow`** ⇒ 對失敗列之 `label_window_ms(e)`
**根本沒有定義**——既無法證明「只是略寬」，也無法安全排除其 under／over-purge 影響。
⚠️ §C0 明定**過度 purge 亦是錯誤**，不得以「保守」一語代替範圍定義。

| 集合 | 內容 | 用途 |
|---|---|---|
| `records` | 該批**全部已落檔**事件列（pre-alignment、pre-coverage） | **只供** `lookahead_bars_declared` 鍵集凍結／`timeframe_seconds` 鍵集／digest |
| `aligned_pre_coverage_windows` | **＝ `prepared0.windows`**（prepare 產出、coverage 前之 `tuple[WindowRow, ...]`；即 records 中對齊成功者） | **只供** purge 權威式之 `scope` 與 split |

🔴 **Task 7.0b mutation（R27 新增；三家）**：**對齊失敗列被餵入
`purge_lower_bound_ms(scope)`／split ⇒ 紅**（失敗列不在 `prepared0.windows`）。
🔴 **R27 更正（GROK-R27-P1-05＋CODEX-R27）**：R26 主委引入之
`aligned_pre_coverage_windows` **無碼上對應物**（全檔僅 2 處、皆主委所寫）
⇒ 綁既有具名欄 **`prepared0.windows`**，**不新增物件**；
並補上 R26 缺少之「失敗列不進 purge／split」可紅 mutation。
**主委已於 R27 brief 自行揭露此假設**（議題二 B ①③），三家確認。

- **對齊失敗之列**：**不進** purge／split（其無 `WindowRow`，公式對它無定義）；
  **但其 `timeframe` 仍保留在鍵集內**（維持 R11 之 P0 凍結不變式）。
- ⇒ 鍵集**不隨對齊結果變動**（P0 不變式成立），而 purge 之 max **只取有 window 之列**
  （公式有定義）。**兩件事分開，不再互相污染。**
- 🔴 **R25 主委採 (甲) 時未看出此缺口**——(甲) 只解決了「鍵集兩側不同源」，
  未處理「purge 輸入集合與 `row(e)` 之定義域不一致」。此為 (甲) 之補完，非推翻。

🔴 **R18：purge 之自由變數集合（由上式**導出**，非逐次列舉）**
（出處：同一「已全部綁進 hash」之宣稱**連三輪被反例打破**——R16 版漏 `symbol`
（CODEX-R17-P1-01）、R17 版漏**觸發** `timeframe`（CODEX-R18-P1-01＋GROK-R18-P1-01
兩家）。**病根不是漏了哪一欄，是主委用「列舉＋宣稱窮盡」代替「從式子導出」**。）

**導出程序（唯一；實作與驗收都照這個做，不得改抄清單）**：
把上式**逐符號展開**，凡出現且非常數者即為自由變數：

| 出現處 | 符號 | 是逐事件還是批次 | 落在 hash 何處 |
|---|---|---|---|
| `scope` 之定義 | `e.symbol` | 逐事件 | `event_level.symbol` |
| `lookahead_depth_ms` | `lookahead_bars_declared` | 批次 | `batch.lookahead_bars_declared` |
| `lookahead_depth_ms` | `e.timeframe`（**觸發 TF**） | 逐事件 | `event_level.timeframe` ← 🔴 **R18 新增** |
| `label_window_ms` | `row(e).label_start_ms` | 逐事件 | `event_level.label_start_ms` |
| `label_window_ms` | `row(e).label_end_ms` | 逐事件 | `event_level.label_end_ms` |
| **不是常數** | `TIMEFRAME_SECONDS` | 批次 | `batch.timeframe_seconds_digest` ← 🔴 **R19 新增** |

🔴 **R19 更正（CODEX-R19-P1-01）：`TIMEFRAME_SECONDS` 不是常數，本表原將它排除是錯的。**
碼證 `momentum/core/constants.py:6`：`TIMEFRAME_SECONDS: dict[str, int] = {...}`
——**module-level 可變 dict**，任何 import 它的模組都能改（alias mutation）
⇒ `batch`／`event_level` 之 canonical bytes 完全不變，而正確之 purge **已改變**。
**這是「常數排除清單不封閉」之實例**，也正是 R18 主委在導出程序裡自認已封閉之處。
**處置**：`batch` 增列第七鍵 `timeframe_seconds_digest`
——值＝對**本次分析實際用到之 tf 子集**取 `{tf: secs}` 後，以 §G S-9 同一 encoder
序列化再 sha256（**不是**整個 dict：整個 dict 會讓無關 tf 之增修改變 hash）。
🔴 **導出程序之「常數排除」自本輪起改為 fail-closed**：**不得**再有「（常數，不計）」列。
凡出現在權威式中之符號，**一律**須指出它落在 hash 何處；
若確信某符號不可變，須附**碼證**證明其為 immutable（如 `Final` ＋ frozen 容器），
否則一律視為自由變數。（理由：本表上一版把可變 dict 寫成常數，正是列舉式思維之殘留。）

⚠️ **`per_tf.timeframe` 不能代替 `event_level.timeframe`**（兩家碼證）：`per_tf` 逐
(event_id, timeframe) 一列、記的是**特徵 TF 集合**，一個事件可有多列
⇒ **無法唯一還原該事件之觸發 TF**。兩者名字相同、語意不同，須各自存在。

🔴 **完整性之唯一落點＝§G G-3 ⑥(d)**（本節**不重述**任何判準）。
🔴 **R20 刪除本處原有之衛星句（三家全員：COMPOSER-R20-P1-01＋CODEX-R20-P1-02＋GROK-R20-P1-02）**：
原文要求「測試**解析本節權威式之符號**，與 hash fence 做集合相等」——
該作法已於 **R19 因不可實作而撤回**（markdown 無文法），但主委**只改了 ⑥(d)、
沒刪本處**，形成兩套互斥驗收並存；實作者可只實作其一而宣稱合規。
**這正是主委自己宣稱要消除的「第二套並行敘事」，卻由主委自己製造。**

🔴 **R10 修正：`lookahead_bars_declared` 由「批次 scalar」改為「逐 timeframe 之 map」**
（CODEX-R10-P0-01；**主委 R9 之裁決在此半邊是錯的，已推翻**）。
主委 R9 在兩份補丁包間裁「換算採**批次層深度** × 逐列 tf」，理由是「D-7 只定義批次層深度」。
**該裁決錯誤**，碼證：`case_search_engine.py:1385-1387,1522-1533` 之 `future72_*` 為**小時**命名欄，
（原）Task 2.1b 之 `bars_of(c, tf) = c.lookahead_hours ÷ hours_per_bar(tf)`（⛔ R 重開後該 Task 退役；本段保留為 map 型別之**歷史論證**，Task 1.10 registry 之換算規則仍有效）⇒
同一個 `future72_*` 欄在 **1h 線 ＝ 72 根、12h 線 ＝ 6 根**（receipt：
`python3 -c "from momentum.core.constants import TIMEFRAME_SECONDS;print(72*3600//TIMEFRAME_SECONDS['1h'],72*3600//TIMEFRAME_SECONDS['12h'])"` → `72 6`）。
⇒ **「批次層深度」在混 TF 批次中根本沒有唯一值**；把單一 bars 數乘上逐列 tf，
對小時命名欄會得到錯誤 ms（1h 列 72h 正確、12h 列變 864h ＝ 過度 purge；
反向指定則 under-purge）。
**改為逐 tf map 後兩者皆正確**：`future72_*` 在 1h 得 `72×1h`、在 12h 得 `6×12h`，**同為 72 小時**；
bar 命名欄（`future_4bar_return`）則本就逐 tf 不同（1h 得 4h、12h 得 48h），亦正確。
- 單一 TF 批次退化為單鍵 map，行為與 R9 版相同。
- `e.timeframe` 不在該 map 之鍵集 ⇒ **fail-closed**（沿用 Task 7.7 ② 之
  `feature_coverage_unknown_timeframe` 同型處置，本節不新增 reason）。
- 🔴 **R11：鍵集之凍結時點（CODEX-R11-P0-01）**——鍵集＝**匯入驗證通過後、
  prepare-windows 與 coverage 之前**，由 **`records`**（Task 7.0b (a) 之具名物：
  「以 `request.event_import_id` 查出該批已落檔 records」）之 `timeframe` 集合決定，
  並隨批次固化。
  🔴 **R26 綁定具名物**（三家）：原寫中文散文詞「整批已落檔事件列」，
  與 (d-3a)／digest 之定義同病 ⇒ 三處自本輪起**同綁 `records`**，不再以散文詞指涉。
  **coverage 只過濾 (event, tf) 配對，不得重建鍵集**；亦即某 TF 之列被 coverage 全數剔除時，
  該 TF 之鍵**仍留在 map 內**。
  理由：若容許 coverage 後重建，`lookahead_depth_ms` 與 purge 下界會**隨 coverage 結果改變**，
  且不同 consumer 可能持有不同鍵集 ⇒ under-purge／過度 purge／三處不一致。
- 🔴 **R11：左項 `declared_window_bars` 亦為逐 tf（CODEX-R11-P0-01）**——
  R10 版把輸出定為 map 卻把左項留成單一值，混 TF 時無唯一單位語意。
  ⇒ 使用者宣告之答案窗根數亦以 `Mapping[timeframe -> int >= 0]` 表達
  （單一 TF 批次退化為單鍵；CSV 上傳由 Task 1.9、`/search` 匯出由 Task 1.9′ 之同一 UI 逐 tf 收集或以同值填滿）。
  🔴 R 重開（D-8）：`lookahead_bars_declared[tf] = declared_window_bars[tf]`（原 Task 2.1b 之 `depth(tf)=max(宣告, 引用欄)` 已退役；無條件可引用）。
- **禁止**用 run 之 tf、批內 `max/min/平均 tf`（同 Task 7.7 ②）。
  🔴 **R22 更正單位來源**：秒數一律取自**注入之 `timeframe_seconds` map**；
  `momentum/core/constants.py:6` 之 `TIMEFRAME_SECONDS` 僅為該 map 之**建構素材**，
  **不得**於計算路徑直接讀取（見 §G G-3 ⑥(d) 之 AST 禁用條）。

- `row(e)`（即 `windows` 中之對應 `WindowRow`）必須來自**本次分析**之 align_events receipt（見下方（iii）），
  **不得**取匯入檔烤入之舊 `label_end_ms`／`label_start_ms`。
- **`scope` ＝ split scope ＝ `symbol`**（碼證：`event_split.py:54` 之
  `for symbol, g in t.groupby("symbol", sort=True)`；`:58-61` 之 `window`／`embargo`
  皆在該 group 內計算）。R9 主委裁決點（per-symbol vs 全批 `max_e`）**經 R10 三家覆核維持**：
  切分本就逐 symbol，洩漏只發生在同 symbol 時間軸內；取全批 max 會對窗較小之 symbol
  **過度 purge**，違反 §C0「過度保守亦屬錯誤」（原引 Task 2.1b，已退役）。

🔴 **R10 規格階段鎖定唯一實作路徑（R9 之「TODO 二擇一」已撤回）**

出處＝COMPOSER-R10-P0-01（BLOCKING）＋GROK-R10-P1-02＋CODEX-R10-P1-02（**三家全員**）。
R9 版原寫把實作留成二擇一（已撤回），其中選項②「傳 `embargo_ms=None`，並確保深度下界已被折進
`label_end_ms − label_start_ms`」**不可行且會 under-purge**：
- `align_events`（`alignment.py:152-168`）之 `label_end_ms` **只依答案窗 `h`** 導出，
  **不**把 `lookahead_bars_declared` 折進去；`event_split.py:59` 於 `embargo_ms is None`
  時取 `int(window.max())` ⇒ 深度側勝出時（Task 7.0b ⑨(a)）隔離不足。
- 且同一 receipt 之窗欄同時被 **3a（Task 7.7 feature-run gate）**、§G G-3 ②、materialize labels 讀取
  （🔴 R14 修正：原寫「Task 7.7 coverage」，與 3b event-coverage 混淆）
  ⇒ 為了塞 purge 而改寫窗欄，會使 `label_window_ms(e)` 不再等於分析 h 之真窗（污染語意）。
- 混 TF 時單一 `horizon_bars` 覆寫**無法**同時表達兩列不同之 `lookahead_depth_ms`。

**⇒ 規格階段鎖定（R11 定死唯一 API，不再有「或」）**：

🔴 **R11 追記（CODEX-R11-P1-05＋GROK-R11-P1-04 兩家）**：R10 版雖宣稱「鎖定唯一路徑」，
文字卻仍寫「例如 `embargo_ms_by_symbol`，**或**於 `split_events` 內…」
——**那還是兩條路徑**，等於把「我還沒想清楚」包裝成「留給實作者選」。同型錯誤第二次。

**唯一 API（欄名、型別、互斥、fail-closed 全部寫死）**：
```python
# momentum/Analysis/event_samples/types.py :: EventSplitConfig
embargo_ms:            Optional[int]                  # 既有欄；非事件分析路徑沿用
embargo_ms_by_symbol:  Optional[Mapping[str, int]]    # R11 新增；事件分析路徑**必傳**
```
🔴 **R15 補：`tuple[SymbolPurgeRow, ...]` → `Mapping[str, int]` 之投影規則（唯一）**
（CODEX-R15＋GROK-R15 兩家：receipt 欄已改 tuple，而 `EventSplitConfig` 仍收 Mapping，
全文**無**兩者之轉換契約 ⇒ 實作者會自行發明，或把 receipt 欄改回 Mapping 而打穿 R14 probe）。
⚠️ **這不是新機制**：`tuple[SymbolPurgeRow, ...]`（receipt 側）與
`Mapping[str, int]`（`event_split` 既有簽章）**兩者皆已存在**，本節只定義其邊界轉換。
```
project_purge(rows: tuple[SymbolPurgeRow, ...]) -> Mapping[str, int]
    # 唯一實作點＝階段 4 之呼叫端；**禁**在 receipt 側預存 Mapping 副本
    # **禁** dict／dict-comp 靜默去重（R16：原偽碼與下方 fail-closed 條互斥）
    seen: set[str] = set()
    out: dict[str, int] = {}
    for r in rows:
        if r.symbol in seen:
            raise ValueError(f"duplicate symbol in purge rows: {r.symbol}")  # fail-closed
        seen.add(r.symbol)
        out[r.symbol] = r.purge_lower_bound_ms
    return MappingProxyType(out)
```
- `rows` 內 `symbol` **重複 ⇒ fail-closed**（不做去重、不取最大值）。
- 投影**只在呼叫 `split_events` 之當下產生**，用完即棄；
  **不得**掛回 `PreparedAnalysisWindows`（那會使 (β)「禁可變容器」與 (γ) 之 tuple 化失效）。
- 🔴 **驗收之唯一所在＝Task 7.0b ⑨(f)**（不改寫既有 ⑨(d) 之本義）。
  🔴 **R18 刪除本處原有之衛星驗收段**（CODEX-R18-P1-02＋GROK-R18-P1-02 兩家）：
  該段複述了 R16 版之兩條 mutation（「取 max 去重」「改成全體 max」），
  而那正是 CODEX-R17-P1-03 **已證明可假綠**之版本（expected 用 dict 生成式建，
  重複列先被靜默折疊）。⑨(f) 已於 R17 重寫為三條較強 mutation，
  兩處並存＝**雙源**，Agent 抄到衛星段就回到假綠版。
  **本節不重述任何 mutation 條文**——**唯一來源在 ⑨(f)**。
- **互斥**：兩欄**同時非 None ⇒ fail-closed**（不做「以哪個為優先」之隱含規則）。
- **事件分析路徑（§D-3′-a（iii）階段 4）必傳 `embargo_ms_by_symbol` 且非空**；
  傳 `embargo_ms` 或留兩者皆 None ⇒ fail-closed。
- **逐 symbol 檢核**（缺一即 fail-closed，**不得**跳過或補預設）：
  ① 該次 split 之每個 symbol 都必須是 map 之鍵；
  ② 值須為 `int >= 0`；
  ③ 值 `>= purge_lower_bound_ms(該 symbol)`。
- **非 GAP-3 之既有 caller**（只傳 `embargo_ms` 或都不傳）**行為完全不變**
  ——`embargo_ms_by_symbol is None` 時走現行 `embargo_ms or window.max()` 分支。
  這是**新增一條路徑**，不是改既有語意。

**明令禁止（已廢之作法，保留為紀錄）**：
- 傳 `embargo_ms=None` 並把深度「折進」`label_end_ms − label_start_ms`；
- 以單一 batch scalar `embargo_ms` 冒充 per-scope 下界。

- 此式之驗收落 Task 7.0b ⑨（含混 1h／12h、同一小時命名欄、跨 symbol、兩側各自勝出之反例）。

**（iii）分析時 receipt 之唯一性與階段順序（CODEX-R9-P0-01）**

R8 版 §D-3a 只寫「②以該次 h 建立 purge／split ③以同一 spec 產生 labels」，
**未定義②所用之 window 從哪來** ⇒ 實作者會沿用匯入檔之
`label_start_ms`／`label_end_ms`，使 h=7 在 h=1 之舊 window 上建 split（under-purge）。
碼證：現行可執行鏈為 `align_events` → `build_event_manifest` → `split_events`
（`pipeline.py:189-200`），而 `event_split.py:58-61` 直接吃 manifest 之
`label_end_ms − label_start_ms`。

**五階段（固定順序，不得顛倒；取代 R8 版之三步）**：
1. **驗證** `event_label_spec`（h／entry／mode／k 之型別與 §F-1′ 支援矩陣）。
2. **prepare-windows**：以該 spec 覆寫 in-memory record copy 之四欄後跑**一次**
   `align_events`，產生分析時
   `decision_at_ms`／`entry_at_ms`／`label_start_ms`／`label_end_ms` ＋ per-TF feature cutoff，
   並**在此唯一一處**計算下方之 `analysis_alignment_receipt_hash`。
3. 🔴 **兩個 coverage 是不同的東西，R13 起分開命名**（COMPOSER-R13-P0-01：R12 落地把兩者
   混為一步，Agent 會跳過 event-id 過濾、或把 feature gate 嵌進 analyze 內部）：
   - **3a. feature-run coverage gate（Task 7.7）**：驗「特徵 run 之 `time_range` 是否涵蓋事件期」
     ——**批次級 pass/fail**，不產生 event-id 子集；讀同一份分析時 receipt（不得讀匯入檔舊值）。
     不通過 ⇒ 整批 `capability_status == "unavailable"`。
   - **3b. event-coverage（`apply_event_coverage()`，本 Task 之階段）**：逐列剔除不可用事件，
     產生 `allowed_event_ids` 並回傳新的 `PreparedAnalysisWindows`（見 Task 7.0b ①）。
   **順序固定 3a → 3b**；3a 為批次閘、3b 為逐列過濾，**不得合併、不得互換**。
4. **purge／split**：**讀**同一 receipt 之 `purge_lower_bound_ms_by_symbol`（階段 2 末已算出）並建 split。
   🔴 **R14 改「計」為「讀」**（兩家）：R13 已裁定階段 4 不重算，但本句仍寫「計」，
   與 ⑭(f) 疊加後可誘導 Agent 對 post-coverage 之 surviving scope 重算。
   🔴 **R13 修正（CODEX-R13＋GROK-R13 兩家）**：`purge_lower_bound_ms(scope)` 之
   **輸入事件集合＝3b 之前（pre-coverage）之全部事件**，於**階段 2 末**即算出
   **immutable per-symbol tuple**（`tuple[SymbolPurgeRow, ...]`）並隨 receipt 攜帶；
   階段 4 只**讀該 tuple**、不重算。
   （🔴 R15 統一詞彙：R14 已改型別；**原文此處與 ⑭ 旁白之「map」字面已於 R15／R16 撤回**，
   本括號僅為歷史紀錄，**不指涉當前資料結構**——當前型別即上句之
   `tuple[SymbolPurgeRow, ...]`。CODEX-R17-P2-06：原括號是作用中之第四處 map 殘留）
   理由：R12 版之⑭(f) 要求「剔除某 TF 全部列後 purge 不變」，而（ii）之式對
   **scope 內事件**取 max ⇒ 剔除後 max 當然會變，**兩者互斥**（我 R12 自己造的矛盾）。
   固定為 pre-coverage 之後，「不變」成為**定義上為真**，⑭(f) 才可判定。
   ⚠️ **副作用須揭露**：purge 因此以未過濾之事件集合為準，可能**略寬**於「只看倖存列」
   ——依 §C0「只能更嚴」接受，並在 ⑭(f) 明寫此為刻意。
5. **materialize labels**：只用同一 receipt 之有效事件產生 `label_value` 並餵 `ic_feed`；
   **不得**重跑 `align_events`（重跑即 hash 變 ⇒ Task 7.0b ⑩須紅）。

🔴 **分析時 receipt 之身分（R10 新增；權威定義在此，他處只引用）**

出處＝CODEX-R10-P0-03＋COMPOSER-R10-P1-01＋GROK-R10-P1-03（**三家全員**）：
R9 版反覆要求「同一 receipt id／hash」，卻**未定義** hash 輸入位元組、唯一產生點與契約落點；
現碼 `AlignmentReceipts`（`types.py:26-30`）僅 `event_level`／`per_tf` 兩個 DataFrame，
契約 `receipt_schema` 亦無該欄 ⇒ 該斷言不可實作，Agent 只能發明或省略。

- **唯一產生點**：階段 2（見上）。coverage／split／labels **禁止**各自重算。
- 🔴 **hash 輸入之 dict 形狀（R11 定死；CODEX-R11-P0-02／COMPOSER-R11-P1-02／
  GROK-R11-P0-01 三家全員：R10 版只列 tuple 欄位，未給可直接組裝之 dict
  ⇒ 不同實作者可分別採 `rows`／`events`／`event_level` 當頂層鍵、或把 per-TF 納入／排除，
  同一語意資料得到不同 digest）**。
  **唯一合法之輸入 dict（頂層鍵固定此三個、固定此順序，不得增減）**：
  ```python
  {
    "batch": {                       # 鍵序固定如下（**恰七鍵**；R19 增 timeframe_seconds_digest）
      "event_import_id": str,
      "horizon_bars": int,
      "entry_price_semantic": str,
      "label_return_mode": str,
      "decision_offset_bars": int,
      "lookahead_bars_declared": "Mapping[tf -> int >= 0]",  # R16 新增；鍵按 UTF-8 升冪後入 S-9
                                       # 🔴 值之型別判定＝`type(v) is int`（**不用 isinstance**）
                                       # ——`bool ⊂ int`，`True` 會序列化為 `true` 而非 `1`
      "timeframe_seconds_digest": str, # 🔴 R19 新增（CODEX-R19-P1-01）
                                       #   ＝對**觸發 TF 子集**取 {tf: secs} 後
                                       #     以 §G S-9 同一 encoder 序列化再 sha256
                                       #   🔴 R20 定義收緊（三家全員：CODEX-R20-P1-03＋
                                       #     COMPOSER-R20-P1-03＋GROK-R20-P1-03）：
                                       #     「本次分析實際用到之 tf 子集」有歧義
                                       #     （可被讀成 union per_tf 之特徵 TF、
                                       #      或 post-coverage 重算）。
                                       #   **唯一定義**：
                                       #   `sorted(set(r["timeframe"] for r in records))`
                                       #     ——即**觸發 TF** 之相異值
                                       #     🔴 R27（COMPOSER-R27-P1-02）：R26 主委寫成
                                       #     `set(e.timeframe for r in records)`——**迴圈變數 `r`
                                       #     而取用 `e`**，該 comprehension 根本不可執行。
                                       #     （`records` 見 Task 7.0b (a)；R26 由散文詞改綁具名物），
                                       #     依 §D-3′-a（ii）L278–282 之凍結規則
                                       #     （＝`lookahead_bars_declared.keys()`）。
                                       #   🔴 R25 更正（COMPOSER-R25-P2-03）：原寫 `event_level`
                                       #     ——那是**對齊成功列**，與 (d-3a) 及鍵集凍結規則分叉，
                                       #     為「撤回沒清乾淨」之**第七類**。三處自本輪起同一來源。
                                       #   🔴 R21 更正（CODEX-R21-P1-02）：R20 版稱「與
                                       #     lookahead_bars_declared 之鍵集凍結規則同源」，
                                       #     但兩者來源**實不相同**——SPEC 該處指「匯入驗證後
                                       #     整批 persisted rows」，而現行 pipeline 之
                                       #     `event_level` **只含 alignment 成功之列**
                                       #     ⇒ 對齊失敗之事件其 TF 會從 digest 消失，
                                       #     而 lookahead 鍵集仍含之。
                                       #   ⇒ **定死唯一 producer**：兩者皆於階段 2 產生，
                                       #     不各自從 records／pipeline 中段重建；
                                       #     其 receipt identity 即 `analysis_alignment_receipt_hash`。
                                       #   🔴 R24 刪「同讀同一個 frozen 物件」之**同源宣稱**
                                       #     （GROK-R24-P1-01）：R23 主委宣稱以集合相等取代同源，
                                       #     **卻只刪了 (d-3a) 那一處、漏了本處** ⇒ 第六次「撤回沒清乾淨」。
                                       #     兩者之一致性由 (d-3a) 之**集合相等**對證，**不以物件身分宣稱**。
                                       #   ⇒ **unknown TF 之 fail-closed**：某觸發 TF 不在
                                       #     注入之 `timeframe_seconds` 鍵中 ⇒ **拒算**
                                       #     （不得略過該列、不得以預設秒數代入）。
                                       #   🔴 R23 更正（三家：CODEX-R23-P1-01＋GROK-R23-P1-01＋
                                       #     COMPOSER-R23-P1-04）——R22 點名之 **Task 7.0b ⑨(g)
                                       #     並不存在**（⑨ 僅 (a)–(f)）：主委寫下「見該 Task」
                                       #     卻**從未建立該子條**，形成 dangling reference。
                                       #   ⇒ unknown-TF fail-closed 之**可執行落點**＝
                                       #     §G G-3 ⑥ 之 (d-3a) 鍵集集合相等（階段 2 producer）
                                       #     **與** Task 7.7 之 feature-run gate；**不得**虛構 ⑨(g)。
                                       #   🔴 **不得** union `per_tf.timeframe`（那是特徵 TF）；
                                       #   🔴 **不得** 於 coverage 後重算。
                                       #   出處：TIMEFRAME_SECONDS 是 module-level 可變 dict
                                       #   （momentum/core/constants.py:6），非常數
                                       #   ⇒ 不入 hash 則 alias mutation 可改 purge 而 hash 不變
                                       #   ⚠️ 只取用到之子集：整個 dict 會讓無關 tf 之增修改變 hash
    },
    # 🔴 `batch` 為**恰七鍵**。本欄集之「purge 相關子集」由 §D-3′-a（ii）之導出表決定，
    #    並由 §G G-3 ⑥(d) 之 `inspect.signature(purge_lower_bound_ms)` 機械導出（R20 改為簽章注入）。
    "event_level": [                 # 按 event_id 之 UTF-8 升冪
      {"event_id": str, "symbol": str, "timeframe": str,
       "decision_at_ms": int, "entry_at_ms": int,
       "label_start_ms": int, "label_end_ms": int},   # 鍵序固定，**恰七鍵**
      # 🔴 本列之欄集**不得手動維護**：其「purge 相關子集」由上方
      #    §D-3′-a（ii）之權威式**導出**（`symbol`／`timeframe`／`label_*_ms`），
      #    並由 §G G-3 ⑥(d) 之 `inspect.signature` 簽章注入對證強制。
      #    🔴 R21 更正（COMPOSER-R21-P1-03＋GROK-R21-P1-02）：本註解原寫
      #    「集合相等斷言」——該作法已於 R20 撤回，此為**第三處** active 殘留。
      #    ⚠️ 主委已於 R20 摩擦紀錄寫下「撤回一個做法要 grep 所有同義字面」，
      #      **下一輪立刻又犯同一個錯**。
      #    R17 新增 `symbol`（CODEX-R17-P1-01）、R18 新增 `timeframe`
      #    （CODEX-R18-P1-01＋GROK-R18-P1-01）——**兩次都是列舉漏項**，
      #    故 R18 起改由式子導出＋機械對證，不再靠列舉。
      #    ⚠️ `timeframe` 指**觸發 TF**（`lookahead_depth_ms` 所讀），
      #    **不是** `per_tf` 之特徵 TF 集合；後者一事件可多列，無法唯一還原前者。
      # 其餘列同形，逐列一個 dict
    ],
    "per_tf": [                      # 先 event_id 升冪、同 event_id 再 timeframe 升冪
      {"event_id": str, "timeframe": str, "feature_cutoff_ms": int},  # 鍵序固定，恰三鍵
      # 其餘列同形，逐 (event_id, timeframe) 一個 dict
    ],
  }
  ```
  🔴 **R16 修正：`batch` 增列第六鍵 `lookahead_bars_declared`（置於
  `decision_offset_bars` 之後，鍵序固定）**，值為 `Mapping[tf -> int >= 0]`，
  由 S-9 第 2–6 條序列化（鍵按 UTF-8 升冪，與其餘 dict 同規則）。
  **出處（CODEX-R16-P1-02）**：`purge_lower_bound_ms(scope)` 之三個輸入為
  `lookahead_bars_declared`（深度）、`timeframe`（換算）、`label_start_ms`／`label_end_ms`
  （窗寬）；後兩者已在 `per_tf`／`event_level` 內，**唯獨深度 map 不在 hash 輸入**
  ⇒ 只改深度宣告即可得到**不同 purge、相同 hash**，⑩ 之「三處同一 receipt」
  對 purge 邊界形同虛設（洩漏面）。依 §C0「只能更嚴」納入。

  🔴 **主委裁決（兩份判斷互斥，理由入規格供 R17 覆核）**：
  - CODEX-R16-P1-02 主張把 **`lookahead_bars_declared` 與 per-symbol purge rows 兩者**
    都加進 `batch`；GROK-R16 判此 finding **不成立**（理由：purge 之保護在 §G G-3 ④
    之逐列 golden 與列等式，不在本 hash）。
  - **裁定：採 codex 之機制、但只納入 `lookahead_bars_declared`；不納入 purge rows。**
  - 理由一（採 codex 之部分）：grok 所指之 G-3 ④ 是**凍結 fixture 之回歸保護**，
    而 hash 是**執行期身分綁定**；兩者守不同東西。深度宣告改變而 receipt 身分不變，
    是身分碰撞，golden 擋不到 live run。
  - 理由二（不採 codex 之另一半）：`purge_lower_bound_ms_by_symbol` 是
    **由上述輸入導出之值**。把導出值也納入 hash，等於在權威式之外再立
    第二個可與之相左的來源——即本 epic 反覆踩到之「複述即第二份副本」。
    輸入全部入 hash 後，purge 已**遞移地**被綁定。

  🔴 **R17 更正：理由二在 R16 版**不成立**，已由 CODEX-R17-P1-01 之反例打破**——
  R16 版列出之輸入只有三個（深度 map／`timeframe`／label 窗），而 **purge 之 scope＝symbol**，
  `event_level` 原五鍵**不含 `symbol`** ⇒ 同一組時間／窗寬／深度 bytes 下，
  **只交換 event→symbol 之分派**即可改變 per-symbol purge 而 hash 不變。
  **處置**：不改裁定方向（仍不納入導出之 purge rows），而是**補齊缺的那個輸入**
  ——`event_level` 每列增 `symbol`（見上方 fence）。四個輸入
  （深度 map／`timeframe`／label 窗／`symbol`）全在 hash 後，「遞移綁定」才真正成立。
  ⚠️ **這是主委裁決被反例修正之紀錄，不得刪**：R16 之「遞移綁定」係主委未逐項列舉
  purge 公式之全部自由度即宣稱成立；R17 之要求（構造反例）正是為此而設。

  - **negative mutation（三條，皆須紅，落 §G G-3 ⑥）**：
    (a) 保持 `event_level`／`per_tf`／`batch` **除受測鍵外之其餘各鍵**不變
        （🔴 R26 更正：原寫「六鍵」，而 canonical `batch` 為**恰七鍵**；
        照抄會漏凍 `timeframe_seconds_digest`。**本處起不再寫死鍵數**
        ——鍵數已在 canonical fence 唯一定義，此處複述即第二份副本。
        CODEX-R26-P1-05＋GROK-R26-P1-05＋COMPOSER-R26-P2-02）
        （🔴 R21 更正：`batch` 已為恰七鍵，本處為第二處複述且漏同步；
        少凍 `timeframe_seconds_digest` ⇒ 該 mutation 形同虛設。
        三家全員：COMPOSER-R21-P1-01＋CODEX-R21-P1-05＋GROK-R21-P1-01），
        **只改 `lookahead_bars_declared` 之任一鍵值** ⇒ hash **必須改變**；
    (b) 🔴 **R17 新增**：保持全部時間欄、窗寬、深度 map 不變，
        **只交換兩個 event 之 `symbol` 分派** ⇒ hash **必須改變**
        （此即 CODEX-R17-P1-01 之反例本身，改為常設 mutation）；
    (c) 🔴 **R17 新增**：`lookahead_bars_declared` 之某值以 `True` 取代 `1`
        ⇒ **fail-closed**（`type(v) is int`；不得序列化為 `true`）。
    三者之舊 receipt 皆不得通過 ⑩。
  - **row keyset 為封閉集合**：多一鍵、少一鍵、改鍵序皆為契約違反（不是「等價寫法」）。
  - **缺席欄處理**：`event_level`／`per_tf` 之任一鍵**不得缺席**；取不到值 ⇒ **fail-closed**，
    **不得**補 `null`（與 S-9 第 3 條「缺席鍵保持缺席」不同——這裡是**必填**）。
  - `event_label_spec` 之四鍵**攤平**進 `batch`（不巢狀），避免「巢或不巢」之第二種寫法。
- **序列化規則**：**引用 §G S-9 之同一 encoder**
  （`canonical_serialize.py::canonical_event_table_bytes`）。
  🔴 **S-9 第 1 條之「已依 S-1..S-7 組好」不適用於本輸入**（COMPOSER-R11-P1-02：
  S-1..S-7 是 `event_forward_return_table` 之欄位語意，與 receipt 之輸入域不同）
  ⇒ 本節之上表**即**本輸入之「S-1..S-7 等價物」；S-9 之第 2–6 條（型別白名單／
  正規化／`json.dumps` 參數／尾端／編碼與雜湊）**逐條適用，不得改**。
  **不得**為此另寫第二個 encoder。
  🔴 **主委裁決點（兩份補丁包互斥）**：`-analysis-receipt-id.md`（composer）指定
  `pandas.DataFrame.to_json(orient='records', date_unit='ms')`；
  `-receipt-id-hash.md`（grok）指定引用 §G S-9。**採 grok**——S-9 第 7 條已明訂
  「只准 import 該函式，禁複製邏輯；複製即第二份副本」，而 `to_json` 之浮點與跳脫規則
  與 S-9（`repr(float)`／`ensure_ascii=False`／`separators=(',',':')`）**不同**，
  引入即為第二個 encoder。
- **欄名（先改契約，D-6）**：`analysis_alignment_receipt_hash: str`，
  登記於 `momentum/Analysis/contracts/event_import_contract.json` 之 `receipt_schema`；
  缺欄 ⇒ fail-closed。`analysis_receipt_id` 與其**同值**（測試可擇一斷言）。
- Task 7.0b ⑩／Task 7.7 ③／§G G-3 ⑥ 之「同一 receipt」斷言**比對該欄**，
  並**保留**「三處 windows 逐列位元組相同」與「不等於匯入檔舊值」兩條（互為補強，不可互相取代）。

- 🔴 **匯入檔之舊 `label_start_ms`／`label_end_ms`／`label_value` 不得進入 3／4／5 任一處。**
- 🔴 producer API 須**明示**「prepare windows」與「materialize values」兩階段
  ——🔴 **R10 收緊（CODEX-R10-P0-03）**：不得只在散文層「明示」，
  **須為兩個具名函式**（簽章見 Task 7.0b ①），階段 3／4 只能吃階段 2 之產物；
  **不得靠呼叫順序推測**，亦不得由同一函式在三處各呼叫一次。
  🔴 **R11：以 `prepared_token`（非決定性）＋ spy `call_count == 1` 機械擋住重入**
  ——只比 hash 擋不住，因 hash 是決定性的（見 Task 7.0b ① 之三條硬性約束）。
- 驗收落 Task 7.0b ⑧⑨⑩；mutation：coverage 或 split 改讀匯入檔舊 receipt ⇒ 須紅。

**碼證（皆可重跑）**：
`eventExport.ts:75-79`（`label` 來自 `positive_case`，**不看答案窗**）／
`ic_feed.py:4-5`（「v1 不重算」為**版本限制非能力限制**）／
`pipeline.py:77-81`（`bars_from_kline_cache` 已是**服務端取 bars 唯一入口**）。

🔴 **D-3a｜embargo 必須由分析時之 h 重新導出（本裁定之不可分割部分）**

出處＝CODEX-R8-P0-02 ＋ GROK-R8-P0-02（**兩家獨立命中**），
推翻主委於 R8 brief 之 assumed「PIT 可由既有 `decision_time_rule`／`feature_cutoff_rule`
保證、不需新機制」。
⚠️ 補丁包 `-arch-shift.md` 之 AUTHORITY 亦持該被推翻之宣稱 ⇒ **該句不採**；
採 `-codex-pit-wiring.md` 之版本。

- IC analyze 之執行順序固定且不得顛倒。
  🔴 **R9 改寫**：R8 版寫「3 步：①檢核 spec ②以該次 h 建立 purge／split ③以同一 spec 產生 labels」
  ——**②所用之 window 從哪來未定義**（CODEX-R9-P0-01）⇒ 實作者會沿用匯入檔舊值。
  **階段之權威定義已移至 §D-3′-a（iii）之五階段**（prepare-windows 先於 coverage／split／labels），
  本節不重述階段清單。
- **禁止**沿用匯入檔烤入之舊 `label_end_ms − label_start_ms` 當 embargo
  ——改大 h 時 purge 會小於實際 label window ⇒ **train/test 洩漏，違反 §C0**。
- 每列 feature sample key 須為 receipt 之 `last_bar_open_ms`／`decision_at_ms`，
  **不是原始 t0**；`decision_offset_bars = k > 0` 之 t0→decision 映射須有 exact receipt
  （CODEX-R8-P0-03）。
- 驗收：`pytest tests/api -q -k event_analysis_horizon_purge`——
  `h=7` **不得**沿用 `h=1` 之 labels／split；`split purge >=` 本次 label end。
  **mutation**：把 purge 改回沿用匯入值 ⇒ 該測試須紅。

**原裁定與撤回理由（保留，不得刪）**：R1 採 grok 之 **(a)**——
「多選只影響匯出檔帶哪些 `future_{h}bar_return` 欄；`label_value` 與 `horizon_bars`
仍綁單一主答案窗」。當時理由為「契約 `window.horizon_bars` 為單一 int，改動超出本批範圍」。
**撤回理由**：該方案把**分析參數烤進資料**——同一批事件事實，想比較 h=3 與 h=7
必須重新匯出兩次（grok：「強迫為換 h 而重匯出未變之事件事實批」）。
且 A-6 因此是在**錯誤的層次**發問（見 §A）。

**D-4（CODEX-R1-P0-05 ＋ GROK-R1-P1-03 ＋ COMPOSER-R1-P2-01）§G 主張過度，需拆 golden**
接受。實查證：`scripts/gap3_freeze_golden.py:28` import `gap2_freeze_golden._run`，
跑的是 `run_analyze`（IC 主線），**未覆蓋事件路徑**；且該 check 對 `summary_table` 用
數值容差而非位元組相等。而 Task 4.2 會改 `analyze_tables` 之預設 `horizons=(1,2,4)`
（`pipeline.py:98`）⇒ **確實動到事件數值輸出**。
⇒ §G 改寫：新增**事件專屬 golden**，逐 horizon 驗 exact return／NaN mask／PIT anchor；
既有 `163c4ce` 只作為「IC 主線未被波及」之守衛，不再宣稱涵蓋事件路徑。

**D-5（CODEX-R1-P0-06 ＋ COMPOSER-R1-P1-03 ＋ GROK-R1-P2-02，三家全員）
記憶體 cap 之量測協定必須可重現**
接受。原 V-8「footprint 增幅 < 0.2GB」無基線、無採樣窗、無 pid 綁定、無硬體記錄
⇒ 可被 `ps rss`（macOS 壓縮下失真）或「在 cap 檢查之後才 sample」假綠。
⇒ 見 Task 6.2／6.4 之量測協定與 V-8 改寫。

**D-6（COMPOSER-R1-P0-01 ＋ CODEX-R1-P1-03 ＋ COMPOSER-R1-P1-04）
新欄位／新 reason 必須先進契約**
接受。`label_definition.filters` 不在契約 `label_definition.fields`（只有 `rule_id`／
`canonical_digest`／`window`／`label_return_mode`）；`feature_count_exceeds_cap` 不在任何契約。
⇒ Task 1.1 擴充為「先改契約」，Task 6.0 新增 IC 錯誤 reason 之登記處。

**D-7（本版新增；出自使用者 2026-08-22 對話，非委員 finding）
答案窗同時決定 purge 寬度 ⇒ 低報即資料洩漏**
`event_split.py:59-61`：`embargo = split_config.embargo_ms 或 int(window.max())`，
且 `embargo < window.max()` 直接 raise。即**答案窗不只餵條件 IC，還決定 train/test 的隔離寬度**。

使用者實際流程：在 Excel 用 `future_1..12bar_return` 複合條件定義正例
（例如「t0 +5% 且 future_1 ≥ +2% 且 future_2 ≥ +2% 且 future_4 ≥ +1%」）。
此時標籤最遠用到 t0 之後**第 4 根**——若匯入時宣告答案窗為 1，purge 只隔 1 根，
train 段末尾事件的答案會落進 test 區間 ⇒ **靜默洩漏，現行無任何機制擋**。

🔴 **偵測不可能**：使用者指出「CSV 本來就有 future_1..12 全欄，我用哪幾欄是在 Excel 決定的」
⇒ 系統無法由「欄位存在與否」推斷實際用到第幾根。此為**與 D-1 同類**的不可驗事實。

**D-7 之修訂（R2；CODEX-R2-P0-01＋GROK-R2-P0-01＋COMPOSER-R2-P1-01 三家全員）**
原處置以「掃描 `future_{N}bar_return` 欄名取 max(N)」為機器可證基礎，**該基礎不成立**：
- 搜尋結果另含 `future_{N}bar_max_drawdown`（同深度）與 `future72_max_return`／
  `future72_max_drawdown`（更深），引用它們**不會**抬高下界（`case_search_engine.py:669-697`）。
  🔴 使用者實際會這樣寫——以 drawdown 排除「漲完就崩」比用 return 更直接。
- CSV 實際欄名為 `Future_NBar_Return_%`／`Future_NBar_Drawdown_%`（大寫＋百分比後綴，
  `search/page.tsx:567-573`），**非契約蛇形**，字串比對全部落空。
- 使用者可刪高 N 欄後上傳以壓低「檔內最大值」。
- 自訂欄／衍生欄（Excel 算完貼回）之前視深度**靜態不可知**。

**修訂後之處置（採 codex「可驗 provenance；不可證則 fail-closed」）**：
- **L1 欄位級 lookahead 標註**：搜尋結果之每個未來欄在契約登記其深度；
  **兩套命名之單位不同，登記形態亦不同**（權威定義見 Task 1.10，本節不得另立版本）：
  - **bar 命名**（`future_4bar_return`／`future_4bar_max_drawdown`）：`N` 即根數 ⇒ 存 `lookahead_bars = 4`
  - **小時命名**（`future72_max_return`／`future72_max_drawdown`／`future{H}_close_return`）：
    `H` 是**小時**，存 `lookahead_hours = 72`，實際根數 ＝ `H ÷ 每根小時數`（12h 線 ⇒ **6 根**、
    1h 線 ⇒ 72 根）⇒ **禁止在任何地方寫死 `bars = 72`**
  掃描改**讀標註**而非猜欄名。辨識須涵蓋大小寫、`Return`／`Drawdown`、蛇形與 `%` 後綴。
- **L2 強制宣告**（🔴 R 重開 D-8：**一律觸發**、兩路徑皆須宣告；下述「未知欄」自 R 後只是額外警語之條件，本段為 R 前之觸發敘述）：出現無法解析深度之 `future*` 或自訂欄 ⇒
  **不得靜默採用偏小 max**，改為強制使用者填寫宣告＋不可驗聲明（Task 1.9）。
- **L3 算不出來 ⇒ 擋在切分外**：仍無法證明 lookahead 深度者，該批**禁止進入
  train/test 切分與條件 IC**，只允許看事件研究表（無訓練即無洩漏）。

**🔴 通則化（使用者 2026-08-22 打斷並糾正；本 SPEC 原本把單一 scenario 當成全部）**

主委原寫「使用者的 label 由『事件條件＋品質過濾』兩段組成」——**那只是 `scenario=C` 的形態**，
被我當成系統通則。使用者逐字糾正：「其他情況，像是預測未來幾根會漲或跌也是一種 scenario，
所以你不能將系統寫死，要考量到其他的設想狀況」。

**契約本來就已區分四種**（`event_import_contract.json` 之 `scenario` enum，主委先前未用上）：

| scenario | 事件在哪 | lookahead 來源 | 深度 |
|---|---|---|---|
| **C 確認型** | t0 當根 | 品質過濾（可選） | 0 或過濾引用之最遠根數 |
| **A／B 預測型** | **未來** | 事件定義本身即在未來 | ≥ 事件之時間距離 |
| **two_stage** | 兩段 | 兩段各自 | 取兩段最大 |

**唯一通則（取代原本的分段描述）**：

> **lookahead 深度 ＝ 該批 label 定義所引用之最遠未來根數（逐 timeframe 各一值）**——🔴 R 重開後其**值**由使用者宣告承載（D-8；系統不再推導）
> ——🔴 **R11 明確化**：「根數」隨 timeframe 而變（小時命名欄尤然），
> 故本通則之量化形態為 `Mapping[tf -> bars]`，其唯一 oracle ＝ `lookahead_bars_declared`；
> 🔴 R 重開（D-8）：承載＝使用者逐 tf 宣告（Task 1.9／1.9′；原 Task 2.1b 承載式已退役）、ms 換算與 purge 下界見 §D-3′-a（ii）。
> ——不論該條件在語意上是「事件本身」還是「品質過濾」。
> **purge 必須 ≥ 此深度。**

⇒ 系統的職責是**確定或要求宣告此深度**，**不得假設它從哪一段來**。
一條規則涵蓋 A／B／C／two_stage 全部，無須為預測型另寫一套。

使用者確認：以「選 t0 漲跌 ＋ 自行篩 future 1-12」即可構成預測型事件（label 由未來條件決定）
⇒ **機制相同、僅語意不同**，現有工具已足以表達，缺的是前端沒把 `scenario` 接出來（見 Phase 7）。

**UI 揭露須動態**：顯示「本批 scenario＝X、lookahead 深度＝N、來源＝使用者宣告（逐 tf；R 重開 D-8，原「引用之欄位清單」已退役）」，
**禁寫死任何固定文案**（主委原擬之「正反例由 t0 條件決定、不看未來」僅對 C 成立，對 A/B 全錯）。

**處置（三層）**：
1. **CSV 上傳路徑**：答案窗**預設取檔內最大可用 horizon**（保守）；使用者可往下調，
   但須明確勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示此為**無法驗證的聲明**。
2. ~~**系統內篩選路徑（Phase 2）**：系統確知使用者用了哪些欄 ⇒ 自動導出 `max(N)` 並鎖定，使用者不得調低。
   這使 Phase 2 的定位從「方便」升級為「把不可驗聲明轉成機器可證事實」。~~
   ⛔ **已由 D-8 廢止（R 重開，2026-09-02）**：Phase 2 退役；`/search` 匯出路徑改走與第 1 點**同一**宣告框
   （Task 1.9′），規則同第 1 點（可調低但須聲明）。
3. 答案窗欄位接受**任意非負整數**，不限 1..12（使用者：「12 根也是我自己訂的，沒有理論根據，
   會不會用到 12 根以外也有可能」；🔴 R35：`0` ＝「未用任何未來資訊」須明填、留白≠0）。

🔴 **D-7 之 R8 增訂｜分析時答案窗（出處＝`-arch-analyze-time-label.md` §3；不削弱既有 L1／L2／L3）**

架構變更後條件 IC 之 h 在 IC 頁給定（D-3′）⇒ D-7 之 purge 約束須同時涵蓋**分析層**：
- purge／embargo 之下界須取 **D-3′-a（ii）之 `max` 式**（該式之權威定義在 D-3′-a，本節不重述）。
- **不得**沿用匯入檔內過期之 `horizon_bars`／`label_end_ms` 而使 embargo 偏小。
- 既有批帶烤入之 `label_value`／窗欄者：分析端**以本次 `event_label_spec` 重算並覆蓋
  分析用副本**（in-memory；不回寫匯出檔）；**不得**靜默混用「舊窗＋新 h」。
- 覆蓋之欄恰為 `align_events` 之四個輸入：`label_definition.window.horizon_bars`／
  `label_definition.label_return_mode`／`entry_price_semantic`／`decision_offset_bars`
  （receipt：`alignment.py:152-168` 逐欄取用處）。

**🔴 主委對使用者既有批次之判斷已兩度修正，此為最終版（實查證，非推論）**：
實讀 `data_cache/events/20260822T011331Z-eb210a16.json`：780 筆、`label` 分布 0:520／1:260、
`control_kind` 全為 `user_labeled_same_trigger`、`scenario=C`、`decision_offset_bars=0`、
`label_definition.window.horizon_bars=3`。
使用者 2026-08-22 明言該批**未做任何篩選**（「單純跑出來就匯出」），
且案例搜尋之正反例**僅依 t0 條件**判定（「沒在管後面 30 個欄位」）。
⇒ 該批 label 之 lookahead **＝ 0**，D-7 之洩漏情境**不適用**。
⇒ 原寫「其 IC／分類結果應視為可能偏樂觀」**撤回**——那是把使用者舉例的假設條件
套到一批實際未篩選的資料上，屬推論過頭。
⇒ 該批 `purge 2` 係為 `horizon_bars=3` 之**條件 IC** 而付，與其分類任務無關。

**PIT 已驗證無洩漏**：`ic_feed.py:76` 之 `feature_cutoff_rule = "max_close_ms_le_decision_at"`
＋`decision_time_rule = "t0_open_minus_k_bars"`，`decision_offset_bars=0`
⇒ 特徵最晚僅取至 **t0−1 收盤**，**未偷看 t0 那根**。使用者「用 t0 之前資訊抓 t0 事件」之設定成立。

---

**D-8（R 重開，2026-09-02；出自使用者裁定，非委員 finding；類別經三家 consult 一致判 R）
匯出前篩選整區移除；答案窗深度之唯一來源改為使用者逐 tf 宣告；purge 取宣告與答案窗之較大者**

- **裁定本體（使用者原話）**：2026-09-02「上傳都有要填答案窗了，那 G3-D1 這在 /search 的新增條件都不用了吧，
  使用者直接 CSV 篩選就好」；2026-08-31「我反例的篩選方式和正例一定不一樣，這兩個篩選可以說是獨立系統，
  所以正反案例篩選條件絕對不能共用。如果匯出前篩選只是要知道後續要用幾根 Bar 去 Purge／切分／Train 分割等，
  那為何不只接給使用者輸入最大使用了哪個 timeframe 的第幾根 Bar 做案例區分，而且 Purge 就是正反案例篩選取大的 Bar 數做使用」。
- **證偽之既有設計**：§A `A-1`（「兩者都做」）；Phase 2 定位「唯一能把答案窗宣告變成機器可證事實的路徑」
  ——後者之前提（系統確知使用者引用了哪些欄）在使用者於系統外標記時**不成立**（篩選面板為空 ⇒ 深度 0、purge 0 而無人喊；
  `G3-D1`），且 Task 2.1b 自記四種抽不出引用欄之失敗形態、抽不出仍要問使用者 ⇒ 機器可證性名實不符。
- **三條規則**：
  ① `/search` 匯出面板**無**篩選；匯出＝搜尋結果**全部**列（含未標記者，`label` 留空供 Excel 補）。正反例判定在系統外完成。
  ② 答案窗深度＝使用者於**批次建立時**逐 tf 宣告（`declared_window_bars` map）；CSV 匯入（Task 1.9）與 `/search` 匯出（Task 1.9′）
     **同一元件、同一 validator、同一規則**（預設＝檔內／結果內最大可用 horizon；可調低但須勾不可驗聲明；接受任意**非負整數**（`0` ＝未用未來資訊，須明填、留白≠0；R36 更正殘留字面）；缺即 fail-closed）。
     `lookahead_bars_declared[tf] = declared_window_bars[tf]`——**不再與任何欄位取 max**（`label_definition.filters` 無寫入者 ⇒
     `depth_by_timeframe()` 之 `referenced_columns` 恆為空集，函式本體保留作匯入端之逐 tf 驗證投影；附帶欄不得參與）。
  ③ purge 權威式（§D-3′-a（ii））**不變**；使用者裁定「取正反例篩選深度之較大者」由宣告框文案承載
     （「填正例與反例兩邊判定所用之最遠者」），不新增契約欄。
- **D-7 三層之對應**：L1 registry **保留**（供揭露預設值候選、rename 攻擊防護與 Task 7.7）；L2 由「未知欄才觸發」改為**一律宣告**
  （Task 1.11 改寫）；L3 不變（Task 1.12）。
- **落點（§P；`scripts/spec_ruling_task_sync.sh` 對證）**：Task 1.9（改寫）、**Task 1.9′（新增）**、Phase 2 全部（⛔ RETIRED）、
  Task 1.11（改寫）、Task 4.1 ③④／4.1b／7.3（深度來源改宣告）、§V V-12（改寫）。
- **殘餘風險（三值具名）**：`user-ruling`——宣告勝過推導（機器可證性不再宣稱）；`needs-research`——匯出端宣告框之預設值候選
  只能來自附帶欄，使用者未附帶任何 `future_*` 欄時預設為空（留空不預填，走「尚未填寫」）；若日後允許無深度匯出 ⇒ `blocked-by` L3 直至補宣告。
- **併回**：D-001…D-005 之落點表見檔頭。

## §A 假設與待使用者確認

| # | 假設 | 狀態 |
|---|---|---|
| ~~A-1~~ | #0 採 (c)：匯出前篩選 **與** 上傳自篩 CSV 兩者都做，先做上傳 | ⛔ **2026-09-02 使用者裁定推翻（R 重開，見檔頭與 D-8）**：匯出前篩選整區移除；只剩「上傳自篩 CSV」一條路 |
| A-1′ | `/search` 只負責把搜尋結果**全部**匯出成可回灌 CSV／JSON；正反例篩選由使用者於系統外（Excel）完成；答案窗深度由使用者於**批次建立時逐 tf 直接宣告**（CSV 匯入與 `/search` 匯出同一規則）；purge 取宣告深度與分析答案窗之較大者 | ✅ **已確認**——使用者 2026-09-02 原話「上傳都有要填答案窗了，那 G3-D1 這在 /search 的新增條件都不用了吧，使用者直接 CSV 篩選就好」＋ 2026-08-31「不然只接給使用者輸入最大使用了哪個 timeframe 的第幾根 Bar 做案例區分，而且 Purge 就是正反案例篩選取大的 Bar 數做使用」 |
| A-2 | #9a 止血閘採「直接擋下」而非「警告後容許硬跑」 | 已確認 |
| A-3 | #9b 排入 GAP-6 | 已確認 |
| A-4' | `label` 為**使用者聲明**，系統不推斷、不預設、不宣稱其正確；未指定 ⇒ fail-closed | R1 三家一致，已改寫（§D-1） |
| A-5' | 批次層預設值對整批一致；**異質列須顯式拒收**（非靜默取第一列） | R1 codex 指出原 A-5 不足，已補（Task 1.8） |
| ~~A-6~~ | D-3 之 (a) 方案（多選只影響匯出欄，label 仍綁單一主答案窗）符合使用者訴求 | ⛔ **R8 作廢**：該問句建立在「條件 IC 之答案窗屬匯出層」之前提上，**前提已被使用者 2026-08-23 裁定推翻**（見 §D-3 撤回理由）⇒ 整條作廢，非「仍待確認」 |
| A-6′ | 條件 IC 之答案窗與連續 `label_value` 於 **IC 分析頁分析時計算**；`/search` 事件批次只固化事實（t0＋二元 `label`＋五維度契約設定） | ✅ **已確認**——使用者 2026-08-23 逐字裁定即取代裁定本身（見下） |
| A-4'／A-5' 之狀態語 | — | 二者為**技術裁定（委員）**，不屬「待使用者確認」 |

**已確認**（使用者 2026-08-22 回覆逐字）：
- A-1：「#0選(c)」
- A-2：「看你怎麼設計都可以」
- A-3：「將#9排在Gap-4(Pooled IC), Gap-5(容量接線)，併入Gap-6規模防護之後」
  ＋「這樣我就等Gap-6之後再針對整個IC-Analysis做測試就好。先把事件型做完」

**A-6′ 之確認 receipt（R8；取代 R5 群集 K 之待確認狀態）**

- **A-4'／A-5'**：純技術主張，依「技術決策委派委員會」由委員裁決，**不列入**本區塊。
- **A-6′ 已確認之依據**：白話閘之目的＝取得使用者對「改變其可見行為」之逐字同意。
  本項之改變**由使用者自己提出**——2026-08-23 逐字：「條件 IC 本來就算一種類型的
  IC-Analysis，條件給定應該就是要在 IC 分析的頁面，而不是 `/search` 吧」，
  三家以碼證確認該架構成立（見 §D-3 碼證）⇒ **使用者原話即取代裁定本身**，
  不存在「還要再問使用者一次他自己提的事」之空間。
  使用者 2026-08-23 就 FROZEN 條件另逐字裁定：該條件視為滿足。
- **可見行為之變更清單（本項之實質內容，供日後追溯）**：
  ① `/search` 匯出面板**移除**「主答案窗」單選；
  ② `/search` 匯出檔**不再**含 `label_value`；
  ③ IC 分析頁**新增**答案窗與報酬語意之分析參數（見 Task 7.6）；
  ④ 比較 h=3 與 h=7 **不需**重新匯出事件批。
- 🔴 **仍為 user assertion、系統不宣稱其正確者**＝ D-1 之 `label` 語意，與本項無關，狀態不變。

### 已驗證事實（FACT-RECEIPT；14 條，皆可由 repo 內命令重現）

- FACT-RECEIPT: `python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));print(len(c['required_fields']),len(c['import_failure_reasons']))"` → 印出 `13 15`（Claude 實跑 2026-08-22）
- FACT-RECEIPT: `python3 -c "import json,re;raw=open('momentum/Analysis/contracts/event_import_contract.json').read();print(re.search(r'\"scenario\"\s*:\s*\{[^}]*\}',raw).group(0))"` → 印出含 `\"enum\": [\"A\", \"B\", \"C\", \"two_stage\"]` 與 doc「A/B 預測型（事件在未來、不進特徵）／C 確認型／兩段式」（Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "_POLICY_BY_SCENARIO" momentum/Analysis/event_samples/dedupe.py` → 印出 `20:_POLICY_BY_SCENARIO = {"C": "cluster_first", "A": "all_with_uniqueness", "B": "all_with_uniqueness", "two_stage": "all_with_uniqueness"}`（**四種 scenario 後端皆已分流**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -nE "scenario:|control_kind:|entry_price_semantic|label_return_mode|decision_offset_bars" frontend/src/lib/eventExport.ts` → 印出 `92: decision_offset_bars: 0,`／`93: entry_price_semantic: opts.entryPriceSemantic ?? 'trigger_open',`／`95: scenario: opts.scenario ?? 'C',`／`102: label_return_mode: 'close_to_close',`／`104: control_kind: 'user_labeled_same_trigger',`（**五處寫死**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -c "counterexample_kind" frontend/src/lib/eventExport.ts` → 印出 `0`（**第五維度完全未送**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `for f in scenario controlKind entryPriceSemantic labelReturnMode decisionOffset counterexample; do echo -n "$f:"; grep -rl "$f" frontend/src/app frontend/src/components 2>/dev/null | wc -l; done` → 印出 `scenario:2`、其餘五項皆 `0`（**UI 未接出**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 88p frontend/src/lib/eventExport.ts` → 印出 ``event_id: `${c.symbol}:${c.timeframe || opts.timeframe}:${t0}`,``（**event_id canonical；含 timeframe、不含 label、非 sha256**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 59,61p momentum/Analysis/event_samples/event_split.py` → 印出 `embargo = split_config.embargo_ms if split_config.embargo_ms is not None else int(window.max())` 與 `if embargo < int(window.max()): raise ValueError(...)`（**答案窗決定 purge 寬度**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 76,77p momentum/Analysis/event_samples/ic_feed.py` → 印出 `"feature_cutoff_rule": "max_close_ms_le_decision_at",`／`"label_window_rule": ...`；同檔 `:75` 印出 `"decision_time_rule": "t0_open_minus_k_bars",`（**特徵最晚取至決策前已收盤 bar，PIT 無洩漏**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "def event_forward_return_table" -A 7 momentum/Analysis/event_samples/tables.py` → 簽章為 `(manifest, receipts, bars_by_tf, event_split_plan, table_config)`，**無 `labels` 參數**，docstring 含「不需反例」（**報酬表全批混算、不看 control_kind**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -n "horizons" momentum/Analysis/event_samples/pipeline.py | head -1` → 印出 `98: horizons: Tuple[int, ...] = (1, 2, 4), seed: int = 20260820, n_boot: int = 300,`（**事件報酬表預設只算三個 horizon**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `sed -n 1385,1387p momentum/DataExtraction/case_search_engine.py` → 印出 `df['future24_close_return'] = (df['close'].shift(-periods_24h) - df['close']) / df['close']` 等三行（**`future{H}_*` 之 H 為小時、非根數；根數＝`H // hours_per_candle`**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `grep -noE "future_?[0-9]*[a-z_]*(return|drawdown)[a-z_]*" momentum/DataExtraction/case_search_engine.py | cut -d: -f2 | sort -u | head -3` → 印出 `future1_close_return`／`future24_close_return`／`future2_close_return`（**bar 命名與小時命名兩套並存**；Claude 實跑 2026-08-22）
- FACT-RECEIPT: `python3 -c "import json,collections;d=json.load(open('data_cache/events/20260822T011331Z-eb210a16.json'));r=d if isinstance(d,list) else d.get('records',[]);print(len(r),collections.Counter(x.get('label') for x in r),r[0]['control_kind'],r[0]['scenario'],r[0]['label_definition']['window']['horizon_bars'])"` → 印出 `780 Counter({0: 520, 1: 260}) user_labeled_same_trigger C 3`（**使用者實際批次**；Claude 實跑 2026-08-22）

---

## §C0 收斂標準（使用者 2026-08-22 定死，最高位階，覆蓋一切其他規則）

🔴 **「95% 解法就收、殘留具名記錄不當阻塞」在本 SPEC 與整條量化主線一律不適用。**

使用者逐字：
> 「95% 解法就收、殘留具名記錄不當阻塞這是在針對治理 epic 中會有散文化和文字問題，
> **在量化主線完全不接受，數據/品質一定是要 100% 正確，只能更嚴但不能放水**。」
> 「你要絕對保證在量化正確性不能用治理那套『95% 就收』這點，
> **絕對不能犯或不小心有任何一條或引用到，要整條刪除都可以**。」

**適用範圍**：本 SPEC 全部 Phase／Task／§V 各條目，以及其衍生之 TODO、實作、review、蓋章各輪。

**具體禁止**（任一出現即為違規，須停下重做，不得以殘留登記帶過）：
1. 不得以「95%／夠好了／先收再說」為由結束任一輪審查。
2. 不得把**數值正確性**或**資料洩漏**類 finding 降級為具名殘留而放行
   （殘留只適用於「已證明不影響正確性」之工程增強，且須帶三值理由）。
3. 不得以「委員已同意可合併」替代「該條 finding 已實際修復並經 mutation 證偽」。
4. 主委不得援引治理 epic 之收斂慣例（含 P1-6 無限迴圈教訓）來收窄量化正確性之審查範圍。

**主委違規紀錄（保留為警示，不得刪）**：2026-08-22 SPEC R3 輪，主委因 findings 由 7 條反彈至 18 條，
援引「95% 就收」建議收斂並停止加固——**該建議被使用者當場駁回**。
援引錯誤在於：該規則出自治理散文之對抗審無限迴圈，而本 SPEC 之標的是
**lookahead 深度、purge 寬度、資料洩漏**，屬不可妥協之數值正確性。

**與 §V 之關係**：§V 全部條目為**必達**（rc=0 或斷言 `==` 成立），非「盡量達成」；
任一條未通過即不得進入下一 Phase，亦不得定版。

---

## §C 約束（引用，不重抄）

- **契約唯一真相源**：`momentum/Analysis/contracts/event_import_contract.json`——欄位名與
  `import_failure_reasons` 字面值一律由該檔取，程式與前端**禁複列**；
  **新增欄位／reason 一律先改契約再實作**（D-6）。
- **`event_id` canonical 唯一**：`` `${symbol}:${timeframe}:${t0}` ``，
  由 `eventExport.ts` 與 CSV 路徑**共用同一實作**（D-2）。
- **解耦七規則**：R1／R3／R7；驗收 `python3 scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` rc=0。
- **PIT 不變式**：`t0` 為決策根、`decision_offset_bars` 語意不得因本批改動而變。
- **既有事件型測試 230 條為回歸底線**，不得降級。
- 使用者定死「驗過就別預設關閉」：本批新功能通過 §V 全部項目後即預設開啟，不藏 flag 後。

---

## §G Golden / Baseline

R1 推翻了原版「本批不動任何數值路徑」之主張（§D-4），本版拆為**兩條互不替代**的守衛：

**G-1 IC 主線未被波及**：`python3 scripts/gap3_freeze_golden.py --check` 須維持通過。
誠實邊界：該 check 委派 `gap2_freeze_golden._run`（跑 `run_analyze`），
**只守 IC 主線、不涵蓋事件路徑**，且 `summary_table` 用數值容差非位元組相等。
故 G-1 **不得**被引用為「事件輸出未變」之證據。

**G-2 事件路徑專屬 golden（本批新建）**：固定 fixture（真實 kline 切片）＋固定 horizons，
凍結 `event_forward_return_table` 之輸出為 sha256——**該 sha256 之計算規則唯一定義於 S-9**
（`sha256 = S-9(輸出 dict)`），凍結與比對腳本只准 import S-9 之參考實作；逐 horizon 驗
① exact return 值（`atol=0`，位元組相等）②NaN／缺 bar mask 位置 ③PIT anchor（t0 對應根）。
Task 4.2 若改預設 horizons，**必須同步更新 G-2 並在 commit message 說明改了什麼、為什麼**
（合法變更），而非靜默重凍。

**G-3 analysis-label golden（R8 新建；R9 擴逐列 purge；R10 加 receipt hash 與混 TF 覆蓋面）**

§D-3′ 把 `label_value` 由**匯出時**移到**分析時**產生 ⇒ G-2（事件報酬表）**涵蓋不到**這條新路徑：
G-2 凍的是 `event_forward_return_table` 之輸出，而分析時 label 走的是
**§D-3′-a（iii）之五階段**（prepare-windows → coverage → purge/split → materialize labels
→ `ic_feed`）。**兩者不可互相替代。**
🔴 **R11 更正（CODEX-R11-P1-07）**：R10 版此處寫成舊三段鏈
`align_events → resolve_label_value_at_analyze → ic_feed`，
與 §D-3′-a（iii）之五階段互斥 ⇒ golden 作者可能只測 align／label／feed，
**漏掉 prepare identity、coverage allowed set、per-scope purge/split** 而誤稱已覆蓋。
本節之階段清單**只引用** §D-3′-a（iii），不自寫第二份。

**固定輸入（全部寫死於 fixture，缺一即 bytes 不可重現）**：
真實 kline 切片（`data_cache/feature_klines/kline_cache.h5`，禁合成 fixture）、
t0 清單、`decision_offset_bars = k`、`horizon_bars = h`、`label_return_mode = mode`、
`entry_price_semantic`、`direction`、`timeframe`。

**凍結對象（逐項 exact，`atol=0`）**：
① 每 event 之 `label_value`
② 每 event 之 label window（`label_start_ms`／`label_end_ms`）
③ feature timestamp map（`event_id → decision_at_ms`；即餵給 `ic_feed` 之 sample key）
④ **purge boundary**——🔴 **R9 擴充**：須逐列凍結 `timeframe`、`lookahead_depth_ms(e)`、
   `label_window_ms(e)`，再凍結**逐 scope（symbol）**之 `purge_lower_bound_ms(scope)`
   （式之權威在 §D-3′-a（ii））。只凍一個 aggregate 數字**不足以**證偽單位換算錯誤
⑤ NaN／尾端不足之 mask（哪些 event_id 之 `label_value` 為 `None`）
⑥ 🔴 **分析時 receipt 之身分**——凍結 **`analysis_alignment_receipt_hash`** 與 `prepared_token`
   （後者非決定性 ⇒ 不進 golden bytes，只在同一次執行內比對三處是否同值）
   （欄名、產生點、hash 輸入與序列化規則之權威在 §D-3′-a（iii），本節不重述）。
   同一次分析中 coverage／split／labels 三處所讀之該欄須同值；
   golden 凍住它，使「其中一處改讀匯入檔舊值」或「某階段自行重跑 `align_events`」皆可被證偽。
   ⚠️ 本欄由 §G S-9 之同一 encoder 產生 ⇒ **不得**為它另寫序列化（S-9 第 7 條）
   🔴 **R16／R17 追加 negative mutation（三條，皆須紅）**（權威與裁決紀錄在
   §D-3′-a（iii），本節不重述理由）：
   (a) 保持 `event_level`／`per_tf` 與 `batch` **除受測鍵外之其餘各鍵逐位元組不變**
       （🔴 R26：本處歷經 R20「五→六鍵」、R26「六鍵→不寫死」兩次更正——
       **寫死鍵數本身就是缺陷來源**，鍵數唯一定義在 canonical fence），
       **只改 `lookahead_bars_declared` 之任一鍵值** ⇒ 本欄必須改變（R16）；
   (b) 保持全部時間欄／窗寬／深度 map 不變，**只交換兩個 event 之 `symbol` 分派**
       ⇒ 本欄必須改變（R17；CODEX-R17-P1-01 之反例）；
   (c) `lookahead_bars_declared` 之某值以 `True` 取代 `1` ⇒ **fail-closed**（R17）。
   (d) 🔴 **R19 重寫——purge 自由變數之單一來源（R18 版不可實作，已撤回）**
       🔴 **撤回理由（CODEX-R19-P1-02＋GROK-R19-P1-02 兩家）**：R18 版寫「測試**解析**
       §D-3′-a（ii）權威式 code fence 之符號得 `V`」，但 **SPEC 未定義文法**；
       對 markdown fence 做 identifier 抽取會納入 `Mapping`／`WindowRow`／`max`／`over`／
       `bars_of` 等註解與型別詞，實作者只能**硬編碼期望集合** ⇒ 機械守衛**名存實亡**。
       且集合相等**只驗名稱、不驗語意**：日後把 scope 由 `symbol` 改成 `(symbol, timeframe)`，
       `V == H` 仍可為真而 purge 語意已變。
       ⚠️ **這是主委連續第二輪寫出「看起來很嚴、實作跑不起來」之驗收**
       （前一次＝R18 群集 E 之 ESM `require`）。**病根：把「解析自然語言文件」當成機械檢查。**

       **R19 版（可實作；單一來源在**碼**，不在文件）**：
       🔴 **R20 撤回 (d-1)(d-2)(d-3) 之 R19 版——宣稱被反例打破（第四次）**
       （GROK-R20-P1-01＋CODEX-R20-P1-01）：R19 版仍是**手維清單＋語意宣稱**。
       grok 之反例實跑：常數少 `timeframe_seconds_digest` 時
       `omit_digest_still_computes True`（`v1=14400000`／`v2=28800000`，
       mutate `TIMEFRAME_SECONDS['1h']` 3600→7200）——**purge 照樣算出看似合理之值**。
       codex 另指出 (d-3) 為**循環自證**：「同一份 shape 宣告」未具名，自指則恆真
       （`d3_tautology True`）。
       ⚠️ **這是同一宣稱第四次被打破**（R16 三輸入／R17 四輸入／R18 解析文件／R19 常數清單）。

       **R20 版（採 GROK-R20 補丁包 `-purge-binding-inject.md`；主委未自創）**：
       (d-1) **改為簽章注入**，不再有任何「自由變數清單」：
             ```
             def purge_lower_bound_ms(
                 rows, *, lookahead_bars_declared, timeframe_seconds
             ) -> int: ...
             ```
             · **keyword-only**：漏任一個 ⇒ **`TypeError`**（語言層 fail-closed）。
               🔴 **R21 誠實收窄（三家全員：CODEX-R21-P1-01＋COMPOSER-R21-P1-02＋
               GROK-R21-P1-03）**：`TypeError` **只覆蓋「缺參數」**，
               **不覆蓋「傳錯物件／錯值」**——呼叫端可傳齊 kwargs 卻傳入
               **module 全表 `TIMEFRAME_SECONDS`**（而非本次子集），不觸發任何錯誤，
               purge 可**靜默翻倍**。
               ⇒ **R20 之「沒有任何宣稱可錯」為誇大，撤回該句**（見下方修正）。
             · **錯 map 之防護分工（R23 更正；GROK-R23-P2-01）**：R22 版寫「主防護＝(d-3)」，
               但同輪已裁定 (d-3) **擋不住多／少鍵** ⇒ 該句過時。
               **鍵集面＝(d-3a)**；**值面＝mutation ⑤ 與實作 pytest**；
               (d-3) 只保證「digest 對應傳入之同一物件」：digest 須對傳入物件做 S-9；
               鍵齊而秒數錯之 map ⇒ digest 不同 ⇒ 綁定比對紅。
             · 🔴 **禁在函式內取用 module-level `TIMEFRAME_SECONDS`**——
               禁 `ImportFrom` **且**禁名為 `TIMEFRAME_SECONDS` 之 `Attribute Load`
               （GROK-R21 補丁包；原文只禁 import，`module.TIMEFRAME_SECONDS` 可繞）。
               ⚠️ **此條之 AST 斷言依 CODEX-R21-P1-03 之裁定改標「待裁定」**，見下。
       (d-2) **期望自由變數集合由 `inspect.signature(purge_lower_bound_ms)` 機械導出**
             ——**沒有第二份清單可漂移**；新增一個自由變數 ⇒ 必須加參數 ⇒ 呼叫端漏傳即 `TypeError`。
       (d-3) `batch.timeframe_seconds_digest` 綁定「**傳入之同一個 map**」之 S-9 位元組
             （非 module-level 之 `TIMEFRAME_SECONDS`）⇒ alias mutation 不再能改結果而 hash 不變。
             🔴 **R22 補（三家；CODEX-R22-P1-01＋GROK-R22-P1-02＋COMPOSER-R22 議題三）**：
             (d-3) **只保證 digest 與傳入 map 位元組一致**，**擋不住**下列兩形——
             ①傳入之 map **多了本批未用到之 tf** ⇒ digest 不同 ⇒ **假紅**；
             ②**少了某 tf** 而該 tf 之事件已被 coverage 濾掉 ⇒ 兩邊自洽 ⇒ **假綠**。
       (d-3a) 🔴 **鍵集集合相等（採 GROK-R22 提案；R23 依委員補丁包更正來源）**：斷言
             `set(timeframe_seconds.keys())`
             **==** `set(lookahead_bars_declared.keys())`
             **==** `set(r["timeframe"] for r in records)`
             （`records` ＝ **Task 7.0b (a) 已具名之物**：
             「以 `request.event_import_id` **查出該批已落檔 records**」；
             🔴 **R26 更正（三家：CODEX-R26-P1-01＋GROK-R26-P1-04＋COMPOSER-R26-P1-01）**：
             R25 版寫中文散文詞「整批已落檔事件列」——**全檔 5 處皆為散文、非可 grep 之具名物**，
             與 R24 之 `pre_coverage_event_rows` **同型**（指向沒有具名 shape 之物）。
             主委已於 R26 brief 自行揭露此假設，三家確認並指出**既有具名物即 `records`**。
             ⇒ 綁定 `records`，**不新增任何物件**。）
             （**依 §D-3′-a（ii）L278–282 之凍結規則**：鍵集＝匯入驗證通過後、
             prepare-windows 與 coverage **之前**，由 **`records`**（Task 7.0b (a)）之 `timeframe`
             集合決定並隨批次固化 ⇒ 依定義**此即 `lookahead_bars_declared.keys()`**，
             故三側實為**同一個凍結集合**。）
             🔴 **R25 主委裁決（兩份補丁包互斥；三家全員命中同一假紅）**：
             委員給 (甲)「第三側改為整批已落檔事件列」與 (乙)「把 L278–282 之鍵集改為
             `prepared.windows`」兩案。**採 (甲)**。
             **理由**：L278–282 係 **R11 之 P0 裁決**，其明文理由為
             「若容許 coverage 後重建，`lookahead_depth_ms` 與 purge 下界會**隨 coverage 結果改變**」
             ——採 (乙) 等於把該 P0 不變式換掉，**以洩漏風險換取寫法方便**，違反 §C0。
             ⚠️ **`prepared.windows` 只供逐列 window 值，不作全批 TF keyset oracle**
             （codex 補丁包原話）。
             🔴 **本假紅已連三輪未除**（R23 用 `event_level`／R24 用
             `pre_coverage_event_rows`／R25 用 `prepared.windows`）——
             **三次都是主委挑了一個「對齊成功後」的集合去比對一個「對齊前」凍結的集合**。
             根因不是選錯名字，是**主委沒有先確認兩側各自涵蓋哪些列**（R23 摩擦一百五十四已載）。
             🔴 **R24 更正（兩家；COMPOSER-R24-P1-01＋GROK-R24-P1-01）**：R23 版寫
             `pre_coverage_event_rows`——**該名稱全檔僅出現於該行、欄集未定義**，
             與 R23 才剛修掉之 `⑨(g)` **同型**（指向不存在之物），主委下一輪又犯一次。
             ⇒ 當時改用 `prepared.windows`（**歷史敘事；已於 R26 再改為 `records`**）。
             🔴 **R27 更正（COMPOSER-R27-P1-01＋GROK-R27）**：本行原為 **active imperative**，
             與同節 L980 之 `records`、(甲) 裁決**並存互斥** ⇒ Agent 順序閱讀會實作錯第三側。
             **active 第三側唯一在 L980；本行僅存為歷史敘事。**
             🔴 **鍵集斷言須在階段 2 末執行**；**coverage 後禁重算 map 鍵集**
             （否則 post-coverage 兩側自洽 ⇒ 假綠）。
             🔴 **R23 更正右側來源（COMPOSER-R23-P1-02）**：R22 版寫
             `set(e.timeframe for e in event_level)`，但 `event_level`
             **只含 alignment 成功之列**（R21 已載），與「pre-coverage 快照」**互斥**
             ⇒ 對齊失敗之事件其 TF 會從右側消失而左側仍有 ⇒ **假紅**。
             **不得**以 post-alignment 之 `event_level` 取代 pre-coverage 列集合。
             🔴 **同步刪除「兩側皆取自同一 frozen 物件」之同源宣稱**
             （GROK-R23-P1-01＋CODEX-R23-P1-01）：R22 主委宣稱以集合相等**取代**同源語意，
             **卻未刪該句** ⇒ 本條改為**只做集合相等對證，不宣稱物件身分同源**。
             多一鍵、少一鍵**皆紅**——集合成員比對，屬角色卡 (b)。
             此條**同時**涵蓋 unknown-TF：未知 tf 必使兩側集合不等 ⇒ 紅。
             🔴 **其餘「錯值面」不再以規格條文加防護**
             （grok 明示「此處不宜再堆第 N 版敘事防護」）——**下推實作階段之 pytest**
             （mutation ⑤ 已覆蓋「鍵齊而秒數錯」）。
             ⚠️ **本處已被連續六輪攻擊**（列舉三／列舉四／解析文件／常數清單／
             `TypeError` 誇大／(d-3) 不足）；R22 起**鍵集面由 (d-3a) 機械收斂、
             值面由實作測試收斂**，規格層**不再新增第七版敘事**。
       **mutation（清單如下；**不寫死條數**——見下方更正史）**（🔴 R26 第三次更正本處計數字面：R24 由「五條」改「四條 active＋一條待裁定」，R25 又新增 ⑥⑦ 而**未同步本標題** ⇒ 實際 active 為 ①③④⑤⑥⑦。**同一處計數字面三輪三錯 ⇒ 本輪起不再寫死條數**，以清單本身為準。CODEX-R26-P2-06＋GROK-R26-P1-01。原 R24 更正出處：
       R23 把 ② 標【待裁定】、VERIFY 只列 ①③④⑤，**標題卻仍寫「五條」**；
       依 R22 通則「mutation 效力不得高於其所依賴之驗收條」，計數字面須同步）：
       ①呼叫端漏傳 `timeframe_seconds` ⇒ `TypeError`；
       ②**【待裁定】**函式內改用 module-level `TIMEFRAME_SECONDS`
       （`ImportFrom` 或 `Attribute Load`）⇒ AST 斷言紅
       🔴 **R23 更正（GROK-R23-P2-01＋COMPOSER-R23-P1-03 兩家）**：本條所依賴之 AST 斷言
       已於 R21 標「待裁定」，而 R22 又立通則「**mutation 之效力不得高於其所依賴之驗收條**」
       ——**主委卻在同一輪把本條留在 active「五條」內、只在後註提一句**，
       自己違反自己剛寫的通則。⇒ 本條**與其依賴同標「待裁定」**；
       ③digest 改由 module-level dict 算而非傳入之 map ⇒ alias mutation 反例紅；
       ④新增自由變數而未加參數 ⇒ (d-2) 之 signature 對證紅；
       ⑤🔴 **R21 新增**：kwargs 傳齊但傳入**鍵齊而秒數錯**之 map ⇒ digest 不同 ⇒ 綁定比對紅
       （此即三家指出「`TypeError` 擋不了錯 map」之反例，改為常設 mutation）。
       🔴 **R21 標記（依角色卡 Rule 3；CODEX-R21-P1-06）**（🔴 R25 更正計數字面：原寫「本五條」，與 R24 已改之標題「四條 active ＋一條【待裁定】」及 VERIFY 只跑 ①③④⑤ 互斥；**第八處計數漂移**）：本清單之 mutation 與 ② 之 AST 斷言
       **主委皆未隔離實跑**（規格階段尚無實作）⇒ **①③④⑤ 標「實作階段必跑」，
       ② 之 AST 斷言標 `待裁定`**（與下方 Task 7.0b 之 `keys.py` AST 條同一裁定）。
       寫在 SPEC 內**不等於**已跑過；未見 `pytest` 實跑輸出前不得宣稱其成立。
       ⑥🔴 **R25 新增（COMPOSER-R25-P1-02）**：`timeframe_seconds` **多一個**
         本批凍結鍵集外之 tf ⇒ (d-3a) 之集合相等紅。
       ⑦🔴 **R25 新增（同上）**：`timeframe_seconds` **少一個**凍結鍵集內之 tf
         （含「該 tf 之列已被 coverage 全數剔除」之情形）⇒ (d-3a) 之集合相等紅。
         🔴 **出處**：R24 版散文已寫「多一鍵、少一鍵皆紅」與「鍵集斷言須在階段 2 末執行」，
         **但 VERIFY 只列 ①③④⑤** ⇒ **鍵集面實際上無可執行驗收**，散文與驗收脫節。
       - 驗證：`pytest tests/momentum/event_samples/ -k purge_signature_injection` 之
         mutation ①③④⑤⑥⑦ 各自 `exit != 0`；`inspect.signature(purge_lower_bound_ms)` 之
         keyword-only 參數集合 `== {"lookahead_bars_declared", "timeframe_seconds"}`；
         mutation ⑤ 之兩份 map 其 `sha256` **不相等**；
         ⑥⑦ 之 `set(timeframe_seconds) != set(lookahead_bars_declared)` 且斷言 `exit != 0`。
       (d-4) 🔴 **語意 mutation（補 R18 版只驗名稱之不足）**：把 scope 由 `symbol`
             改為 `(symbol, timeframe)` ⇒ 必須有測試變紅（受影響者＝逐 scope 之 purge 值
             與 `SymbolPurgeRow` 之鍵；**不是** `V == H`）。
       🔴 **本條之存在理由（不得刪）**：同一「purge 自由變數已全部綁進 hash」之宣稱
       **連四輪被反例打破**——R16 漏 `symbol`／R17 漏觸發 `timeframe`／
       R18 之「解析文件比對集合」不可實作／R19 之「常數清單」被 grok 實跑打破
       （`omit_digest_still_computes True`）。
       **四次都是同一種錯：主委用「一份要人維護的清單＋一句語意宣稱」當機械保證。**
       R20 改為**簽章注入**後，**「清單可漂移」這一面**確已消除
       （自由變數集合由 `inspect.signature` 導出，無第二份清單）。
       🔴 **但 R20 之「沒有任何宣稱可錯」是誇大，R21 撤回**（三家全員）：
       `TypeError` 只擋缺參數，**擋不了傳錯 map**；錯 map 之防護在 (d-3) 之 digest 綁定，
       那仍是一條需要被驗證的條文，不是語言層保證。
       **第五次的教訓：把「某一面已解決」寫成「全面已解決」，本身就是下一個 finding。**
       🔴 **R20 刪除本處原有之第二份 mutation 清單**（它仍寫著已撤回之
       `PURGE_FREE_VARIABLES`）——主委在同一次修訂中一邊宣稱要消除第二套並行敘事、
       一邊留下一套，正是三家本輪點名之病。
   (e) 🔴 **R18：交換觸發 `timeframe` 之 mutation**——保持全部時間欄／窗寬／深度 map／
       `symbol` 不變，**只交換兩個 event 之 `timeframe`** ⇒ 本欄必須改變
       （CODEX-R18-P1-01＋GROK-R18-P1-01 之反例本身，改為常設 mutation）。

**覆蓋面（最小集；不足即不得宣稱本 golden 有效；R11 追加小時命名欄組，見可證偽條 5(b)）**：
`direction ∈ {long, short}` × `timeframe ∈ {1h, 12h}` × `h ∈ {1, 7}`，
外加一組「尾端不足」之邊界 fixture。
🔴 **R9 追加兩組（CODEX-R9-P0-02）**：
（甲）**同批混 1h 與 12h**（同一 symbol）——證明 ms 換算逐列取該列 `timeframe`；
（乙）**兩個 symbol、窗寬不同**——證明 `purge_lower_bound_ms` 逐 scope 各自成立，
      小窗 symbol 未被大窗 symbol 過度 purge。

**可證偽條（五條，皆須可獨立跑）**：
1. 特徵截止仍為 `feature_cutoff_rule = max_close_ms_le_decision_at`（不變；受本 golden 之③保護）。
2. `label_value` 與**獨立手算** `(close[t0+h] − close[t0]) / close[t0]`（long）相等，`atol=0`；
   short 取其相反數。🔴 **oracle 獨立性同 S-8**：expected 值須另寫直算腳本產生，
   **禁以 `resolve_label_value_at_analyze` 自產 golden 後回頭比自己**。
3. 尾端不足 ⇒ `label_value is None` 且該 event **不進** `ic_feed`（loud），**禁填 0**。
4. **同批 h=3 與 h=7 兩次分析**：事件事實 id 集合**相同**；`label_value` 集合**不同**；
   ②④各自對應自己的 h。
5. **多 TF 與多 symbol 之逐列換算**（R9 追加甲乙兩組 fixture）：
   (a) **bar 命名欄**（`future_4bar_return`）：`lookahead_depth_ms(e)` 於 12h 列為 1h 列之 12 倍；
   (b) 🔴 **小時命名欄**（同一個 `future72_max_drawdown`）：
       ⚠️ **R12 更正（CODEX-R12-P2-08）**：R11 版寫「鏡像 Task 7.0b ⑨(e)」——
       「鏡像」不是機制，兩份 fixture 可各自漂移而仍各自通過。
       ⇒ 兩處**共用同一份具名 fixture**。
       🔴 **R13 補（CODEX-R13：同名不等於同一份）**：僅寫路徑仍可各自 inline 或
       resolve 到不同資料。**定死三件**：
       (1) **owner ＝ Task 7.0b**，提供**唯一 typed loader**
           `load_hour_named_mixed_tf() -> HourNamedFixture`（frozen）；
       (2) fixture 檔 `tests/momentum/event_samples/fixtures/hour_named_mixed_tf.json`
           之 **sha256 一併凍進 §G G-3 之 golden**；loader 於載入時比對，不符 ⇒ fail-closed；
       (3) 本節與 Task 7.0b ⑨(e) **皆呼叫該 loader**（斷言同一 exported 函式參考），
           **不得**各自 `json.load` 或 inline 資料。
       **mutation**：改動 fixture 一個位元組 ⇒ 兩處**同時**轉紅（證明共用而非各持一份）。
       斷言：兩 tf 之 `lookahead_depth_ms` **相等**，
       而 `lookahead_bars_declared` 之兩鍵值**不等**。
       ⚠️ **只有 (b) 能證偽「scalar 深度 × 逐列 tf」之回歸**；R10 版只寫 (a)
       ⇒ G-2／G-3 為 byte golden 而與 pytest ⑨ 脫鉤時，hour-named 錯換算可假綠
       （COMPOSER-R11-P1-01／GROK-R11-P1-02 兩家命中）。
   (c) `purge_lower_bound_ms` 逐 symbol 各自成立。
6. **mutation（七條，皆須紅）**：分析改 h 卻不重算 window／embargo ⇒ ④紅；
   以匯出檔烤入之舊 `label_value` 覆蓋分析結果 ⇒ ①紅；
   ms 換算改用批內 max tf 或固定 run tf ⇒ 5(a) 紅；
   **把 `lookahead_bars_declared` 塌成 scalar 再乘逐列 tf ⇒ 5(b) 紅**；
   `purge_lower_bound_ms` 改成全批單一 scalar ⇒ 5(c) 紅；
   coverage／split／labels 三者改讀不同 receipt ⇒ ⑥紅；
   **任一 consumer 自行重跑 prepare（token 不同）⇒ ⑥紅**。

**序列化**：本 golden 之 dict → bytes **沿用 S-9 之同一參考實作**
（`canonical_serialize.py::canonical_event_table_bytes`），**不得**另寫第二個 encoder。

**驗收命令**：`pytest tests/momentum/event_samples/ -q -k analysis_label_golden`。

#### G-2 canonical serialization（R4 群集 B；三家全員判「未定義即不可位元組級證偽」）

主委 R2 曾裁「留實作階段」，被三家推翻；R3 未補；R4 三家再次全員命中。本節即該定義，
**為 sha256 之唯一計算規則**，實作不得另行約定。取材＝`momentum/Analysis/event_samples/tables.py:88-180`
之實際回傳結構（非推測）。

**S-1 欄位白名單（頂層八鍵，固定此順序，不得增減）**：
`statistic_kind`／`horizons`／`primary_macro`／`sensitivity_micro`／`uniqueness_weighted`／
`strata`／`common`／`receipts`。新增鍵即為輸出契約變更，須改本節並重凍。
🔴 Task 7.5 之正／反／全體**三組不得新增第九頂層鍵**——唯一掛載點為 `strata.by_label`
（見 S-1a，R5 consult 三家全員裁）。`strata` 之**內容**擴充不改變頂層八鍵集合。

**S-1a 三組之掛載點（R5 consult；三家獨立皆選 `strata.by_label`）**：
Task 7.5 之三組統計掛於既有頂層鍵 `strata` 之下，鍵集**固定恰為**
`positive`／`negative`／`all` 三者，不多不少。
🔴 鍵名為三家分歧之裁決點，**逐鍵取多數**：`positive`／`negative` 採 codex＋composer
（grok 提 `"1"`／`"0"`）；`all` 採 codex＋grok（composer 提 `aggregate`）。理由僅為多數。
- `positive`／`negative`：各為一個 S-7 之 horizon map。
- `all`：**可計算時**亦為 S-7 之 horizon map；**不可計算時**改為 S-7a 之狀態塊。
- 序列化順序依 **S-2 之通則**（未列名巢狀物件按鍵之 UTF-8 升冪）⇒ `all`／`negative`／`positive`，
  **不得**依執行期 dict 插入序。本鍵集無須另立排序特例。
- **不得**以三次 `event_forward_return_table` 呼叫各產一表代替本結構——那會產生三份可能各自
  漂移的 hash，且把分組踢出表格契約。API／UI 可垂直排列，但**序列化與 G-2 只認這一棵樹**。

**S-2 三層排序**：
- 物件鍵：一律依上列固定順序；未列名之巢狀物件依鍵之 UTF-8 code point 升冪。
- **horizon 鍵須以 `int` 值升冪，禁用字典序**——`primary_macro` 等之鍵為 `str(h)`，
  字典序會把 `"10"` 排在 `"2"` 之前 ⇒ 同一組 horizons 依輸入順序不同得到不同 bytes。
- `horizons` 陣列**原樣保留輸入順序**（它是 `table_config` 之透傳）；因此
  **golden fixture 之 `horizons` 規定為升冪、無重複之整數清單**，避免順序成為隱藏輸入。
- `strata.by_symbol`／`by_direction`／`by_period` 之鍵依 UTF-8 升冪。

**S-3 重複與非法 horizon**：現碼只擋 `h < 1` 與空清單（`:104-105`），**不擋重複**——
重複 h 會產生重複列並在 `block()` 之 `out[str(h)]` 互相覆寫。
⇒ 本批明定：`horizons` 出現重複值即 `raise ValueError`，與 `h < 1` 同級 fail-closed。

**S-4 缺 bar ＝ omission，不是 NaN**：`:129-130` 之 `exit_idx >= len(bars)` 走 `continue`
⇒ 該 (event_id, h) **整列不存在**，由 `n` 反映排除，不灌 0、不產生 NaN 列。
mask oracle ＝ 「(event_id × horizon) 之布林出現矩陣」，須與 golden 一併凍結；
只比 aggregate 會漏掉局部列漂移。

**S-5 NaN 與浮點之表示**：`_weighted_stats` 於空集合回 `float("nan")`（`:47`），
`macro` 亦可能為 `nan`（`:161`）。JSON 無 NaN 字面 ⇒ **一律序列化為 `null`**，
禁用 `NaN`／`Infinity` 非標準字面。浮點以 `repr()`（Python 之 round-trip 最短表示）輸出，
禁用固定小數位（會吞掉最低位漂移）。

**S-6 隨機性輸入**：`ci` 由 `_cluster_bootstrap_ci` 產生，受 `seed`／`n_boot` 決定
（預設 `20260820`／`500`，`:106-107`）⇒ golden fixture 之 `table_config` **必須顯式寫死**
兩者，且其值一併進 `receipts` 與 sha256；未寫死時 bytes 不可重現。

**S-7 統計欄範圍**：每個 horizon 區塊之鍵集固定為
`mean`／`median`／`win_rate`／`n`／`n_effective`（`_weighted_stats`，`:52-58`）
＋`label_anchor_mean`＋`ci`；`primary_macro` 之鍵集為 `mean`／`n_symbols`。
`by_scenario` 之鍵由 `str(sc)` 產生且 `dropna=False` ⇒ 缺值會成為字串 `"nan"`；
本批明定**golden fixture 之 `scenario` 不得有缺值**，避免該字串進入 hash。

**S-7a `not_computed` 狀態塊（S-7 之唯一替代形態）**：
當某組不可計算時（現況只有 `strata.by_label.all`，見 Task 7.5 之 `control_kind` 規則），
該組之值改為**恰兩鍵**之物件：`{"status": "not_computed", "reason": <契約登記之字面>}`。
- `status` 之值固定為字串 `"not_computed"`；`reason` 之值須為契約已登記者（見 Task 7.5）。
- 🔴 **不得**回傳 `n=0` 之空統計塊冒充——那會被讀成「算過但沒樣本」，
  與「這組在語意上不該算」是完全不同的兩件事。
- 本塊亦依 S-9 序列化，**無第二 encoder**。

**S-8 oracle 獨立性**：expected rows 須以**獨立手算**產生（另寫一份直算 entry/exit close 之腳本
或試算表數值），**禁以被測函式自產 golden 後回頭比自己**。至少涵蓋：
`horizons=[1,3,7]`、`ret_entry` 與 `ret_label_anchor` 兩種 return、尾端資料不足之 omission。

**S-9 位元組 encoder（G-2 sha256 之唯一計算規則）**

出處＝R5 consult 三家全員（CODEX-R2-P0-01／COMPOSER-R2-P0-01／GROK-R2-P0-02）：
S-1..S-8 定義了**欄位語意與排序**，但未定義 **dict → bytes** 這一步
⇒ 不同實作者選不同 `separators`／escaping／尾端 newline 仍各自「符合 S-1..S-8」卻得到不同 sha256。
本節即該步之唯一規則；**任何實作不得自行約定 `json.dumps` 參數**。

1. **輸入**：已依 S-1..S-7 組好之 Python `dict`（鍵序已符合 S-2，**不得再 sort**）。
2. **型別白名單**：只接受 `bool`／`int`／有限 `float`／`str`／`list`／`dict`／`None`；
   其他型別（`Decimal`、`numpy` 純量、`datetime` 等）**一律先轉為上列型別**，禁依賴 encoder 隱式轉換。
3. **正規化**：`NaN`／`+Inf`／`-Inf` **一律轉 `None`**（與 S-5 一致）；`-0.0` **保留為 `-0.0`**
   （不得正規化為 `0.0`——兩者 JSON lexeme 不同，會使 hash 隨實作漂移）；
   **缺席鍵保持缺席**（不得補 `null`）；`list` 順序原樣保留。
4. **JSON 生成**：
   `json.dumps(obj, ensure_ascii=False, separators=(',', ':'), allow_nan=False, sort_keys=False)`
   - 禁 `indent`；禁 `sort_keys=True`（順序由 S-2 保證，排序會破壞 S-1 固定序與 horizon 之 int 序）。
   - 字串 escaping 依 JSON 規則：只 escape `"`、`\` 與 `U+0000`–`U+001F`；
     非 ASCII 以**字面 UTF-8** 輸出（`ensure_ascii=False`），不得 `\u` 脫逃。
   - 有限 `float` 之 JSON number lexeme 須等於 CPython `repr(float)`（與 S-5 之 round-trip 一致）。
5. **尾端**：**不得**附加尾端 `\n` 或任何 whitespace。
   🔴 **此為三家分歧之裁決點**：composer 與 grok 指定「禁尾端 newline」、codex 指定「加一個 `\n`」
   ⇒ 採 2:1 之「禁」。裁決理由僅為多數，**非**技術優劣——兩者皆自洽，重點是全專案唯一。
6. **編碼與雜湊**：`.encode('utf-8')`（禁 UTF-8 BOM）→ `hashlib.sha256(bytes).hexdigest()`。
7. **參考實作**：`momentum/Analysis/event_samples/canonical_serialize.py::canonical_event_table_bytes`
   （Task 4.2 實作時建）。G-2 之凍結與比對腳本**只准 import 該函式，禁複製邏輯**——
   複製即第二份副本，副本必然漂移（同 §V 書寫規則之理由）。
   🔴 檔名為三家分歧之裁決點（composer `canonical_serialize.py` vs grok `canonical_json.py`）
   ⇒ 採 composer 版；實質無差異。

**S-9 之驗收**（`pytest tests/momentum/event_samples/ -q -k canonical_serialize` ≥7 條）：
① fixture bytes 與 golden 逐位元組相等
② `separators` 改成 `(', ', ': ')` ⇒ hash 變、測試紅
③ 附加尾端 `\n` ⇒ hash 變、測試紅
④ `ensure_ascii=True` ⇒ hash 變、測試紅
⑤ `NaN` 未轉 `None` ⇒ `allow_nan=False` 之 `json.dumps` raise（**非**靜默輸出 `NaN` 字面）
⑥ `-0.0` 被正規化成 `0.0` ⇒ hash 變、測試紅
⑦**重複 horizon**（R6 群集 J）：`horizons=[1,3,3,7]` ⇒ `event_forward_return_table`
  **raise `ValueError`**（S-3 已規定 fail-closed，R5 版卻無對應測試；
  現碼只擋 `h < 1` 與空清單，重複 h 會在 `out[str(h)]` 互相覆寫而靜默通過）
fixture 須同時含：非 ASCII（`é`）、`"`、`\`、控制字元、`NaN`／`±Inf`、`-0.0`、`None`、缺席鍵。
**S-9 之 mutation**：移除重複 h 之守衛 ⇒ ⑦須紅。

---

## §P Phase 與依賴

### Phase 1 — 使用者自篩 CSV 匯入（依賴：無）　【#0(b) ＋ #5】

**Task 1.1 — 契約先行：新增 reason 與 label_definition.filters**
- 內容（**R8 改寫：改為集合差集，不再寫計數字面**）：
  ① `import_failure_reasons` 增 `column_mapping_missing`／`column_not_found_in_file`／
     `label_column_not_binary`／`heterogeneous_rows_in_batch`。
  ② 🔴 **R8 依 §F-2′ 改掛層次**：`label_producer_unsupported_for_declared_semantics`
     **不再**進 `import_failure_reasons`（R6 群集 D 之落點作廢），改進
     `capability_unavailable_reasons`——理由：§D-3′ 後該 reason 之語意由「匯入失敗」
     變為「本次分析之能力不可用」，兩個清單語意不同，放錯清單會使前端在錯誤的
     生命週期顯示它。
  ③ `capability_unavailable_reasons` 因此增兩值：②之 reason
     ＋ Task 1.12 之 `split_blocked_unverifiable_lookahead`。
  ④ `label_definition.fields` 增 `filters`（型別＋`_doc`）以承載 Phase 2 之篩選條件（D-6）。
  ⑤ 🔴 **R9 新增（CODEX-R9-P1-03）／R10 修正型別（CODEX-R10-P0-01）**：
     登記 **`lookahead_bars_declared`**——`derived_fields.names` 加該名，
     `receipt_schema` 加其欄位與**型別 `Mapping[timeframe -> int >= 0]`**（逐 tf 一值，
     **非 scalar**；理由見 §D-3′-a（ii）之 R10 修正）。
     語意＝**使用者宣告之最遠未來根數**（R 重開 D-8：兩路徑之逐 tf 宣告；原「label 定義所引用之最遠未來根數之真實值」之導出已退役），
     與 `label_definition.window.horizon_bars` **不同**（後者下限為 1，深度 0 時只是
     serialization floor，見 §D-3′-a（i））。
     receipt 缺該欄 ⇒ fail-closed，**不得**以 `1` 默認替代。
  ⑥ 🔴 **R10 新增（CODEX-R10-P0-03 等三家）**：登記
     **`analysis_alignment_receipt_hash`**（`str`）於 `receipt_schema`——
     其產生點、hash 輸入與序列化規則之權威在 §D-3′-a（iii），本欄不重述。
  ⑦ 🔴 **R10 新增（CODEX-R10-P1-05）／R11 定死 migration 形狀（CODEX-R11-P1-06＋
     GROK-R11-P0-02 兩家）**：`receipt_schema` 現況為**巢狀之欄名清單**
     ——`{"event_level": [...], "per_tf": [...]}`（`event_import_contract.json:135-142`），
     無型別 ⇒ 「`int >= 0`」這類要求無處可機械驗。
     R10 版只寫「升為 `{欄名: 型別}`」，**未說是攤平還是保留 namespace** ⇒ 三種寫法皆可，
     且驗收⑧(a) 之 `pre_names` 全檔未定義、⑧(b) 又直接 top-level lookup，互相矛盾。
     **R11 定死（namespace-aware，不攤平）**：
     ```
     receipt_schema = {
       "event_level": { <既有欄名>: <型別>, ... },   # 既有欄名與順序照抄，只補型別
       "per_tf":      { <既有欄名>: <型別>, ... },   # 同上
       "batch":       {                              # R11 新增之第三個 namespace
         "lookahead_bars_declared": "Mapping[str,int>=0]",
         "analysis_alignment_receipt_hash": "str",
       },
     }
     ```
     - **兩個新 derived 欄一律放 `batch`**（它們是批次層屬性，不是逐列或逐 TF）。
     - `pre_names` 之定義（驗收用）：**改前** `receipt_schema` 各 namespace 之
       欄名清單，以 `"<namespace>.<欄名>"` 之扁平字串集合表示；
       `now_names` 以相同 traversal 由改後 dict 產生。**兩者同一 traversal 函式**。
     - 既有欄之**順序**以 list→dict 之插入序保留（Python 3.7+ 保序），驗收⑧(a) 逐一比對。
     - runtime validator 與驗收**共用同一 typed path**（同一個 traversal ＋ 型別判定函式），
       不得各寫一份。
  🔴 **步驟順序寫死（CODEX-R9-P1-05）**：本 Task 之**第一個動作**是建立改前基準，
  **在動任何契約欄位之前**：
  ```
  cp momentum/Analysis/contracts/event_import_contract.json \
     tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json
  cmp -s momentum/Analysis/contracts/event_import_contract.json \
         tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json
  shasum -a 256 tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json
  ```
  三條之輸出**須入 commit message** 作為 byte-faithful receipt。
  fixture 建立後即視為 **immutable**；**runtime loader 不得讀該 fixture**
  （只有測試以顯式 path 載入）；fixture 事後被改動 ⇒ 驗收 fail-closed。
  ⚠️ 先改契約再複製、或產生 sanitized／重排版之 fixture ⇒ 差集失去改前語意，屬違規。
  🔴 **改前基準以 fixture 凍結**：`tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json`
  ＝本批動工前之契約副本（位元組拷貝）。所有增量以**對該 fixture 之差集**表述，
  **不在 SPEC 或測試內重列既有 reason 字面**（重列即第二份副本）。
- 驗證：`pytest tests/api -q -k gap3_contract_reason_registry` ≥5 條——
  ①`set(now['import_failure_reasons']) - set(pre['import_failure_reasons'])` **集合相等**於
    `{'column_mapping_missing','column_not_found_in_file','label_column_not_binary','heterogeneous_rows_in_batch'}`
  ②`set(pre['import_failure_reasons']) - set(now['import_failure_reasons'])` 為**空集**
    且 `now['import_failure_reasons'][:len(pre['import_failure_reasons'])] == pre['import_failure_reasons']`
    （既有字面與**順序**皆不變）
  ③`'label_producer_unsupported_for_declared_semantics' not in now['import_failure_reasons']`
  ④`set(now['capability_unavailable_reasons']) - set(pre['capability_unavailable_reasons'])` **集合相等**於
    `{'split_blocked_unverifiable_lookahead','label_producer_unsupported_for_declared_semantics'}`
  ⑤`'filters' in now['label_definition']['fields']`
  ⑥🔴 **baseline fixture 之存在性與 byte-faithful**（CODEX-R9-P1-05）：
    `test -f tests/momentum/event_samples/fixtures/event_import_contract.pre_gap3.json` rc=0；
    該 fixture 之 sha256 `==` commit message 所記之值；
    且 runtime loader（`load_event_import_contract` 之類）之搜尋路徑**不含** `tests/`
    （斷言以 `inspect.getsource` 或設定值檢查，不靠註解宣稱）
  ⑦🔴 **兩個新登記欄**（🔴 **R12 更正名稱**，CODEX-R12-P2-07：R11 版把兩者都叫
    「新 derived 欄」，但機械差集只允許 `derived_fields.names` 新增**前者**，
    後者只進 `receipt_schema.batch` ⇒ registry 語意與驗收名稱不一致。
    正名：`lookahead_bars_declared` ＝ **derived 欄**（進 `derived_fields.names` ＋ receipt schema）；
    `analysis_alignment_receipt_hash` ＝ **batch receipt 欄**（**只**進 `receipt_schema.batch`））：
    `set(now['derived_fields']['names']) - set(pre['derived_fields']['names'])`
    **集合相等**於 `{'lookahead_bars_declared'}`；且
    `{'batch.lookahead_bars_declared', 'batch.analysis_alignment_receipt_hash'}
     <= flatten(now['receipt_schema'])`（`flatten` 見⑧(a)）
  ⑧🔴 **typed receipt schema 與型別實際生效**（CODEX-R10-P1-05；R11 定死 migration 形狀）：
    (a) 以**同一個** `flatten(schema) -> ["<ns>.<欄名>", ...]`（保序）產生
        `pre_names = flatten(pre['receipt_schema'])`（改前為 list 形態）與
        `now_names = flatten(now['receipt_schema'])`（改後為 dict 形態）；
        斷言 `now_names[:len(pre_names)] == pre_names`
        🔴 **R 重開併回 D-005 A-024（R 首版落點表漏列）**：上式為**全域** append-only，會讓非末端 namespace（如 `event_level`）
        永遠不能加欄（A-023 之 `direction_sign` 即被它擋）⇒ ⑧(a) 改為**四條並列、全部須成立**（本處為唯一權威字面）：
        (1) **逐 namespace 前綴保留**：對 `pre` 之每個 namespace `ns`，`now[ns]` 之攤平名單須以 `pre[ns]` 之攤平名單為前綴；
        (2) **namespace 順序保留**：`now` 之 namespace 出現序須以 `pre` 之 namespace 序為前綴（原式沒有；新增，擋整個 namespace 搬位）；
        (3) **無遺漏**：`set(pre_names) <= set(now_names)`；(4) **確有成長**：`len(now_names) > len(pre_names)`。
        淨效果：多抓一種壞法（namespace 重排），少限制的只有「新欄必須全域排最後」這件與品質無關的事。
        mutation：把 `event_level` 內任兩個既有鍵對調 ⇒ (1) 紅；把 `per_tf` 整個搬到 `event_level` 前 ⇒ (2) 紅；刪任一既有鍵 ⇒ (3) 紅；
        over 向：在 `event_level` **尾端**加新鍵 ⇒ 四條皆綠（那正是 A-023 要做的事）。
        （**既有欄名與順序一個不差、且都排在新欄之前**）
    (b) `now['receipt_schema']` 之每個 namespace 之值為 `{欄名: 型別}`（非 list）；
        `now['receipt_schema']['batch']['lookahead_bars_declared']` 之型別宣告為
        `Mapping[timeframe -> int >= 0]` 之契約表示；
        `now['receipt_schema']['batch']['analysis_alignment_receipt_hash'] == 'str'`
    (c) **runtime validator 真的擋得住**：以 `lookahead_bars_declared` 為
        `{'1h': -1}`／`{'1h': 1.5}`／**`72`（root scalar，＝R9 之形態）**／`{'1h': '3'}`／
        🔴 **`{'1h': True}`（R17 新增第五反例）** 五個反例落檔 ⇒ **各自 fail-closed**（非僅警告）
        🔴 root scalar 一條為 GROK-R11-P1-07 補：R10 版反例只有 map 內負數／非 int，
        「該欄直接是一個裸整數」這種 R9 形態**可以通過型別登記**
        （反例值即上句 (c) 所列之 root scalar）
        🔴 **第五反例為 CODEX-R17-P1-02 補**：R16 把本欄納入 receipt hash 之 `batch`，
        而 `bool ⊂ int` ⇒ `isinstance(True, int)` 為真、S-9 白名單又同時收 `bool`
        ⇒ `True` 通過檢查卻序列化為 `true` 而非 `1`，產出不同 bytes、綁定比對失效。
        **判定一律 `type(v) is int`，不用 `isinstance`**（同 R14 對 `event_label_spec`
        normalizer 之定死；本條與該處**共用 (e) 之同一 traversal／型別判定函式**，
        不得各寫一份）。
    (d) 正例對照：`{'1h': 0, '12h': 6}` ⇒ 通過（防「恆紅型假保證」）
    (e) validator 與本驗收**呼叫同一 exported traversal／型別判定函式**
        （斷言同一函式參考，非各自複製）
  **mutation（六條，皆須紅）**：把 `label_producer_unsupported_for_declared_semantics`
  放回 `import_failure_reasons` ⇒ ③④；改動既有 reason 之順序 ⇒ ②；
  刪除或改動 baseline fixture ⇒ ⑥；移除任一新 derived 欄之登記 ⇒ ⑦；
  把 `receipt_schema` 退回欄名清單 ⇒ ⑧(a)；拿掉 runtime validator ⇒ ⑧(c)。
- 存活至：Phase 6。
- 覆蓋風險：契約為**唯讀增量**——新 reason 與 `filters` 鍵在 Phase 2..7 全程只被讀取或填值，
  無任一 Task 刪改其字面與順序。Phase 2 之 Task 2.2 只寫 `filters` 之**值**；Phase 6 之 Task 6.0
  另建 IC 側 reason 檔而**不併入本檔**（D-6）；Phase 7 之五維度動的是 `label_definition` 之其他鍵
  ⇒ 本 Task 產出不被覆蓋。
  🔴 **R8 改寫之理由（本欄自身即事故現場）**：R6／R7 兩輪之自傷各有一條發生在本欄——
  「`15→19`」「`== 19` 改 `== 20`」「`3→4`」皆為**計數字面**，而它所計之物在同一批內又被改了兩次
  （R6 把 §F-2 之 reason 加進本清單、R8 依 §F-2′ 又把它移到另一個清單）。
  ⇒ 本 Task 之驗收已全面改為**對凍結 fixture 之差集**，SPEC 內**不再出現任何 reason 計數**；
  日後任一 Phase 增值，只需更新該 Phase 自己的差集斷言，本 Task 不必跟著改。
  **須同步**：Task 1.12 之 `split_blocked_unverifiable_lookahead` 與 §F-2′ 之
  `label_producer_unsupported_for_declared_semantics` **同進** `capability_unavailable_reasons`
  ⇒ 兩者之差集斷言在本 Task 驗收④**合併驗一次**，Task 1.12 不得另寫第二份。
- 邊界：只加，**不動**既有 reason 之字面與順序（以驗收②機械對證，不靠計數）。
- 不可做：不得在 `api/` 或 `frontend/` 另寫一份 reason 清單。

**Task 1.2 — 新端點 POST /api/v1/case/import-events/csv**
- 內容：multipart 收 CSV ＋ `column_mapping`＋`batch_defaults`；組出契約記錄後
  **呼叫與 `/import-events` 相同的 schema 檢核與落檔函式**（同一 `.py` 函式，由 V-3 之 AST oracle 機械對證）。
- 驗證：`pytest tests/api -q -k gap3_csv_import` ≥8 條全綠；
  共用性以 V-3 之**兩重 oracle**證（見 §V，非單靠 sha256 相等）。
- 存活至：Phase 6。
- 覆蓋風險：Phase 4 疊加 horizon 欄，端點簽章不變。
- 邊界：只新增端點；**不改** `/import-events` 與 `/import-events/json` 之任何行為。
- 不可做：不得為 CSV 路徑另寫一份 schema 檢核邏輯（須共用同一函式）。

**Task 1.3 — event_id 沿用既有 canonical（D-2）**
- 內容：`event_id` ＝ `` `${symbol}:${timeframe}:${t0}` ``，與 `eventExport.ts:88` **同一實作**
  （抽為共用函式，前後端各自呼叫同一定義來源）。
  ~~`source_file_digest` ＝上傳 CSV 位元組之 `hashlib.sha256(raw).hexdigest()`。~~
  🔴 R 重開併回 D-003 A-019：上句與下段互斥，**以下段為唯一定義**——`source_file_digest` 綁 `/search` 之完整 `CaseData` 列之
  canonical bytes（§G S-9）並**由後端計算**；上傳 CSV 路徑之 digest 由使用者自檔攜帶、匯入端以 companion 來源檔對證
  （Task 1.6 之 `source_digest_verified`）。
  🔴 **`/search` 路徑之 `canonicalSourceText` 須綁完整 `CaseData`（R6 群集 H；R5 群集 H 之未閉合半邊）**：
  現行只取五欄（symbol／timeframe／timestamp／positive_case／price_change，`eventExport.ts:27-37`）
  ⇒ 刪除、改名或改值任一 `future_*` 欄後 digest **不變**，改名攻擊（Task 1.10 之信任邊界）之證據面未閉合。
  改為：**每列完整 `CaseData` 之遞迴 canonical JSON**——保留所有 own keys 與值（含全部 future return／drawdown 欄），
  只做固定 key ordering（依 §G S-2 之 UTF-8 升冪），**不改名、不篩欄、不省略**；
  digest 綁此完整 bytes。
  🔴 **序列化須依 §G S-9**（R7 群集 G；composer 命中）：含**浮點 lexeme 規則**
  （`repr(float)` round-trip）、NaN／±Inf → `null`、`-0.0` 保留、separators、UTF-8 無 BOM。
  未引用該規則時，瀏覽器之 `JSON.stringify` 與 Python 之 `repr(float)` 對**同一數值**
  可產生不同字面 ⇒ 同一批事件跨執行環境之 digest 不同，改名攻擊之證據面反而不穩。
  🔴 **R11 定案（主委自查；同型於 CODEX-R11-P1-05／GROK-R11-P1-04 所指之「留選項＝延後錯誤」）**：
  R7 版此處原寫「前端自行實作等價浮點格式化，**或**改由後端計算 digest，二擇一須明示」
  ——那是**第三處**未定案之實作分叉，已撤回。
  **定案：digest 一律由後端計算**（R13 修正承載，見下）。
  🔴 **R13：不新增 transport（CODEX-R13 裁「新端點違反入口閘」＋GROK-R13 抓到殘句）**——
  R12 版寫「送 `POST /api/v1/case/source-digest`（**或**既有匯出端點之同一服務端路徑）」，
  ①新增第二個 transport 違反角色卡入口閘①，且主委給的理由「唯一承載」**不是**可機械判定之例外；
  ②那個「或」本身又是第二承載殘句——**已撤回**；
  （誠實邊界：既有之未定案分叉閘只擋四字字面，寫成「或」就繞過去了）。
  ⇒ **定案：沿用既有匯出流程之服務端路徑**——`/search` 匯出在送出前呼叫既有
  case 匯出／檢核之同一服務端入口取得 digest，**不新增任何 route**。
  由 Python 端**直接呼叫 §G S-9 之參考實作**產生。
  理由：「等價實作」本身不可機械證明（要證等價就得逐值比對兩個實作，
  那等於已經有後端實作了）；且 S-9 第 7 條明訂「只准 import 該函式，禁複製邏輯」，
  在 TS 重寫一份浮點格式化正是該條所禁之第二份副本。
  ⇒ 前端**不得**自行計算 `source_file_digest`；驗收見下方⑤。
- 驗證：同一批事件「JSON 匯出檔」與「CSV 回灌」之 `event_id` 集合 `==`（集合相等斷言）；
  改 1 byte 重傳 ⇒ `source_file_digest !=` 原值。
  **R6 群集 H 追加**（`npx vitest run canonicalSourceCoverage` ≥3 條）：對同一組 cases，
  ①**刪除**一個 `future_*` 欄 ⇒ digest 改變 ②**改名**一個 `future_*` 欄 ⇒ digest 改變
  ③**改值**一個 `future_*` 欄之數值 ⇒ digest 改變
  ④🔴 **前端不得自算 digest**（R11 定案；**R12 修正驗收互斥**——
    R7 版之④⑤原寫「前端與後端**各算一次**、位元組相等」，
    與 R11「前端不得自算」**直接互斥**，且 mutation 還假設前端可改用 `JSON.stringify`
    ⇒ 三家 R12 命中，該兩條已刪）：
    (a) 🔴 **R13 改為 call-boundary 斷言，不用 grep**（CODEX-R13：grep 只掃
        `eventExport.ts` 且只認三個字面，改名／搬 helper／改用 `crypto.subtle.digest`
        即可假綠——實跑 probe 已證 `grep -cE …` 對 `crypto.subtle.digest` 回 `0`）：
        🔴 **R15 改為封閉之呼叫面枚舉＋靜態掃描雙軌**（CODEX-R15：
        「spy 整個 `frontend/src/`」仍是模糊描述，改名／搬 helper／純 JS helper／
        dynamic import 皆可繞過）：
        (a) **執行期**：vitest 於 `setupFiles` 統一 stub **全域雜湊入口之封閉集合**
            ——`globalThis.crypto.subtle.digest`、`node:crypto` 之
            `createHash`／`hash`／**`Hash`（建構子）**／`webcrypto`
            （🔴 R17：R16 版補了 `hash` 仍**漏 `Hash` 建構子**——`new crypto.Hash('sha256')`
            與 `createHash` 同 hex，且 `Hash === createHash` 為 `false`（是兩個入口），
            DeprecationWarning 不等於廢除。CODEX-R17-P1-04＋GROK-R17-P1-02 各自實跑。
            🔴 **本清單已連三輪被補**（R15 三項→R16 補 `hash`→R17 補 `Hash`）
            ⇒ 實作時**不得**以本清單自稱窮舉。
            🔴 **R18 改寫此要求為可執行形式（CODEX-R18-P1-03）**：R17 版寫
            `Object.getOwnPropertyNames(require('node:crypto'))`，但本專案 vitest
            `environment: 'jsdom'`、測試以 **ESM** 執行 ⇒ 裸 `require` 是 `ReferenceError`；
            且該呼叫回傳 **71 個** export，SPEC 未定義如何從中篩出「雜湊入口」
            ⇒ 原文**不可執行**。改為：
              (i) 取得模組用 `await import('node:crypto')`（ESM）或
                  `import * as nodeCrypto from 'node:crypto'`；**不得**用 `require`。
              (ii) 🔴 **R19 撤回 R18 之「篩選判準」——三家實跑證明它錯**
                   （CODEX-R19-P1-04＋COMPOSER-R19-P1-01＋GROK-R19-P1-01）：
                   ·`webcrypto` 是 **object 不是 function** ⇒ 外層 `typeof === 'function'`
                     守衛使它**永遠不會命中**（而它正是清單內的項目）；
                   ·`k.includes('hash')` 額外命中 **`getHashes`**（那是列出演算法名稱的函式，
                     不是雜湊入口）；
                   ·prototype 具 `update`+`digest` 之規則命中 **`Hmac`**（清單外）。
                   ⇒ (iii) 之 `⊆ 清單` 在**正確實作下仍恆紅**——這條驗收壞了。
                   ⚠️ **病根：主委想用述詞自動「分類什麼是雜湊入口」，那是語意判斷，不是機械判準。**

                   **R19 版（不分類，改為「變更即人工複審」）**：
                   (ii-a) 測試以 `await import('node:crypto')` 取模組，
                          斷言 `Object.getOwnPropertyNames(m).sort()` **逐字等於**
                          一份**簽入版控之 golden 清單**（`tests/.../node_crypto_exports.golden.json`）。
                   (ii-b) 🔴 **R20 補閉環（CODEX-R20-P1-05）**：R19 版寫「測試紅 ⇒ 由人複審 ⇒
                          若是則同批加入 stub 清單」——**沒有 receipt、沒有機械連結**，
                          只更新 golden 而漏更新 stub 時**測試仍綠**，§C0 之判斷被推給未來的人。
                          ⇒ 保留「不分類之 golden boundary」，並新增版本化之複審 manifest
                          （`tests/.../node_crypto_review_manifest.json`）作為
                          **「誰在何時複審過哪些 delta」之 receipt**，逐筆記：
                          golden 之 added／removed export 名、reviewer、commit context。
                          測試以 **golden delta × manifest 做封閉集合比對**：
                          ①golden 有而 manifest 無 ②manifest 有而 golden 無 ⇒ **兩者皆紅**。
                          🔴 **R21 刪除原第三欄「是否為 digest entry」與其 mutation③**
                          （CODEX-R21-P1-04＋GROK-R21-P1-04 兩家）：那是把 **R19 已撤回之
                          「分類什麼是雜湊入口」重新做成一個要人維護的布林欄**；
                          且三條 mutation 只驗集合同步、**不驗分類正確**——
                          人工誤標 `false` 時 golden／manifest 仍綠。
                          **主委原自我歸類為 (c)「修既有閘」不成立**（兩家）。
                          ⇒ digest 入口之顯式 stub 清單維持既有枚舉 (ii-c)，
                          **不由 manifest 分類推導**；「stub 漏更新」由既有
                          stub 清單 × 呼叫面之斷言承擔。
                          ⚠️ §N 之「純 JS 手刻 sha256」殘留**仍獨立標記**，
                          **不得**宣稱已被本閘解決。
                   (ii-c) **stub 清單維持顯式枚舉**（`subtle.digest`／`createHash`／`hash`／
                          `Hash`／`webcrypto`），**不再嘗試自動推導**。
                   ⚠️ **誠實邊界（寫明，不假裝解決）**：本設計**不分類**，只保證
                   「Node 的雜湊面變動時有人會看到」。它擋不住「清單內入口以外的手刻實作」
                   ——那條仍是 §N 之具名殘留。
              (iv) `globalThis.crypto.subtle.digest` 屬 Web Crypto，不在 node 模組列舉內，
                   須**另行**斷言其已被 stub。
            （🔴 R16：R15 版**漏 `crypto.hash`**——codex 與 grok 各自實跑 Node v22.18.0
            證得 `typeof crypto.hash === 'function'` 且 `crypto.hash('sha256', x, 'hex')`
            與 `createHash` 同輸出；`webcrypto.subtle.digest` 與 `globalThis` 為同一語意入口之
            兩條取得路徑，stub 須兩者皆蓋。新增入口須同批更新本清單）；
            跑完整匯出流程後斷言：與 `source_file_digest` 相關之呼叫數 `== 0`
            （`rule_digest` 之呼叫另計，兩者已於上方分離）。
        (b) **靜態**：以 AST（非 grep）掃 `frontend/src/**`，斷言
            **無任何模組同時** import 上述任一雜湊入口 **且** 出現 `source_file_digest` 之寫入。
        ⚠️ 誠實邊界：純 JS 手刻 sha256（不經上述入口）本閘看不見
        ——列為**具名殘留**（三值理由 `needs-research`；owner 主委；觸發＝FROZEN 後）。
        （🔴 R16 刪除此處三行 R13 殘句——原為 R13 版之呼叫面敘事，R15 插入 (a)/(b) 雙軌後
        未一併刪除，與上方 (a) 之 `call_count == 0` 及 (b) 之靜態條件並列會被讀成**第三套**
        判準；執行期斷言已由 (a) 承載、靜態條件已由 (b) 承載。CODEX-R16-P1-01＋GROK-R16-P1-03）
    (b) 同一組 cases 經**前端流程**取得之 digest，與**直接呼叫** Python
        §G S-9 參考實作所得者 **位元組相同**（證明前端拿到的就是後端算的那一個，
        **不是**前端自己算出巧合相同之值）；
    (c) 含 `-0.0`／極大極小浮點之 fixture ⇒ (b) 仍成立。
  🔴 **端點與時序（R12 補；CODEX-R12-P1-03＋COMPOSER 命中「route 不存在、時序未裁」）**：
    - **承載（R13 定案；不新增 route）**：沿用既有匯出流程之服務端入口，
      其回應**增兩鍵** `{source_file_digest: str, source_file_text: str}`
      （`source_file_text` 為 §G S-9 之 exact bytes 之 UTF-8 解碼，**無尾端 newline**）。
      🔴 **`rule_digest` 與 `source_file_digest` 為兩件事，須分離**（CODEX-R13）：
      前者綁搜尋規則（`search_rule_summary`），後者綁完整 `CaseData` 列；
      同一 helper **不得**同時產出兩者而共用序列化路徑。
    - **時序（定案）**：digest 於**匯出當下**由後端就該批 `cases` 產生，並與
      `source_file_text` 一同回傳、一同寫進匯出檔；**匯入時不重算**，只做比對
      （`verify_source_digest`）。理由：匯入端拿到的是使用者可能已在 Excel 動過的檔，
      重算會把「使用者改過」與「序列化不一致」混為一談。
  **mutation（三條，皆須紅）**：把 `canonicalSourceText` 改回五欄子集 ⇒ ①②③；
  前端改為自算（任何 hash 呼叫）⇒ ④(a)；
  後端改用非 S-9 之序列化（如 `json.dumps` 預設參數）⇒ ④(b)(c)。
- 存活至：Phase 6。
- 覆蓋風險：`event_id` 之輸入僅 symbol／timeframe／t0 三者，後續 Phase 皆不改此三者之定義——
  Phase 2 之篩選條件由 Task 2.2「不可做」明令禁止進入 `event_id` 輸入（D-2）；Phase 4 之附帶
  `future_*` 欄只加輸出欄；Phase 7 之五維度屬 `label_definition` 層設定 ⇒ 不被覆蓋。
  **須同步**：Phase 7 之 `decision_offset_bars`／`entry_price_semantic` 若被實作成改動 t0 之取值，
  同一事件將跨批得到不同 `event_id` ⇒ 實作 Task 7.1 時須重跑本 Task 之集合相等斷言
  （JSON 匯出 vs CSV 回灌 `==`），不得只跑 7.1 自身測試。
- 邊界：digest 綁**上傳的位元組**，不綁解析後的 DataFrame。
- 不可做：**不得發明新的 event_id 演算法**（R1 兩家獨立指出此為 BLOCKING）。

**Task 1.4 — t0 單位偵測**
- 內容：沿用契約 `ms_magnitude_min`；秒級 ×1000；無法判定 ⇒ `invalid_timestamp_unit`。
- 驗證：三組 fixture（ms／秒／不合法）各 1 測；ms 值精確比對 `== 1704067200000`。
- 存活至：Phase 6。
- 覆蓋風險：單位偵測位於解析入口，其輸出（毫秒整數）為後續全部 Phase 之唯一時間表示；
  無任一 Task 改寫 `ms_magnitude_min` 或新增第二條單位判定路徑 ⇒ 不被覆蓋。
  **須同步**：Task 1.2 之 CSV 端點與既有 `/import-events` 須共用同一偵測函式
  （Task 1.2「不可做」已要求共用 schema 檢核），否則兩條路徑會各自演化出不同單位判定
  ⇒ V-3 之 AST oracle 涵蓋面須包含此偵測函式，不得只證 schema 檢核共用。
- 邊界：只判單位，不做時區推斷。
- 不可做：不得在判不出單位時猜預設值。

**Task 1.5 — 前端上傳、預覽與對映 UI（含強制確認）**
- 內容：選檔 → 顯示前 5 列預覽與全部欄名 → 逐項下拉對映 → 填批次預設 →
  **顯示「你聲明的正例 X 筆／反例 Y 筆」並要求勾選確認** → 送出。
- 驗證：`npx vitest run gap3_csv` ≥5 條；斷言未勾確認時 `fetch` call count `== 0`；
  `npm run build` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：Phase 4 於同頁加 horizon 多選，屬疊加。
- 邊界：只做上傳與對映；資料篩選在 Phase 2 之 `/search`。
- 不可做：不得預設任何欄位對映（A-4'）；文案禁用「label 正確」字樣（D-1）。

**Task 1.6 — 對映 provenance 落檔（D-1）**
- 內容（🔴 R 重開併回 D-003 A-016）：`mapping_provenance` 為**七欄**寫入該批 receipt：
  `column_mapping`／`source_file_name`／`source_file_digest`／**`source_digest_verified`**（未附 companion 來源檔時為 `false`
  ——宣告值只證明使用者填了同一串）／**`event_id_source`**（`csv_column`｜`derived_from_template`）／`confirmed_at`／
  **`confirmed_at_source`**（`client_declared`｜`server_received`）；使日後可追「這批的正反例是依哪一欄、哪個檔宣告的」。
  **批內單一 digest invariant**：對映路徑落檔時各列宣告之 `source_file_digest` 須解析出**單一值**；批內不一致或缺 ⇒ 視為缺值
  ⇒ `missing_required_field` fail-closed、落檔數 0。
- 驗證：`pytest tests/api -q -k gap3_csv_provenance` ≥4 條；
  ①receipt 之 `column_mapping.label ==` 送出值；②receipt 之 `mapping_provenance` 鍵集 `==` 契約 `receipt_schema.mapping_provenance` 七鍵；
  ③未附來源檔 ⇒ `source_digest_verified == False`；④批內兩個不同 `source_file_digest` ⇒ 落檔數 `== 0`。
- 存活至：Phase 6。
- 覆蓋風險：receipt 為只增欄位之記錄檔，Phase 2..7 只讀不改；Phase 2 之 `filters` 與 Phase 7 之
  五維度均寫入 `label_definition` 而非本 receipt ⇒ 本 Task 之既有欄位不被覆蓋。
  **須同步**：Task 7.1 讓五維度由寫死改為使用者可選之後，「這批依哪一欄、哪個檔宣告」已不足以
  還原全批設定 ⇒ Task 7.1 實作時 receipt 須一併記錄五維度之實際選值；未同步則 provenance 在
  Phase 7 之後對「這批是用什麼語意算出來的」不可追。
- 邊界：只記錄，不參與任何計算。
- 不可做：不得省略 `source_file_digest`（否則無法對證來源）。

**Task 1.7 — 可疑欄警示（D-1）**
- 內容：預覽階段掃描所有欄，列出**其他也是二元（值域 ⊆ {0,1} 或 {true,false}）的欄名**，
  提示「這些欄看起來也像標記，請確認你選的是哪一個」。
- 驗證：fixture 含 3 個二元欄 ⇒ 警示列出另外 2 個（`len == 2` 且集合相等）。
- 存活至：Phase 6。
- 覆蓋風險：警示只在 Phase 1 之預覽階段執行，不寫入任何持久產物，後續 Phase 無讀取者亦無改寫者
  ⇒ 不被覆蓋。**須同步**：Phase 2 之篩選作用於系統內搜尋結果（欄位由系統產生，非使用者上傳），
  **不得**與本掃描合併為同一實作——合併後，凡值域落在 {0,1} 之系統旗標欄都會被列為「可疑標記欄」，
  警示失去鑑別力（Task 1.7 驗證之「`len == 2` 且集合相等」即會鬆脫）。
- 邊界：只警示不阻擋（語意不可機械判定，見 D-1）。
- 不可做：不得因為只有一個二元欄就自動選它（A-4'：不推斷）。

**Task 1.8 — 異質列顯式拒收（A-5'）**
- 內容：若 CSV 各列在 `direction`／`scenario`／`label_definition` 上不一致而
  `batch_defaults` 未涵蓋 ⇒ `heterogeneous_rows_in_batch`，訊息列出前 3 個衝突列號與欄名。
- 驗證：fixture 混 long/short ⇒ 得該 reason 且**落檔數 `== 0`**。
- 存活至：Phase 6。
- 覆蓋風險：拒收判準（列間於 `direction`／`scenario`／`label_definition` 不一致且 `batch_defaults`
  未涵蓋即拒收）本身在後續 Phase 不變 ⇒ 本 Task 之邏輯不被覆蓋。**須同步**：Task 7.1 將 `scenario`
  由寫死 `'C'` 改為四值可選（A／B／C／two_stage），`batch_defaults` 之可能取值面隨之擴大
  ⇒ 本 Task 之 fixture 須加一組「defaults 指定 `scenario='A'` 而列間混 A／B」之案例並斷言落檔數
  `== 0`，否則 Phase 7 擴大出來的取值面沒有對應測試。
- 邊界：只拒收並指出衝突；不自動分批。
- 不可做：不得靜默取第一列之值套用全批。

**Task 1.10 — 欄位級 `lookahead_bars` 契約（D-7 之 L1；Task 1.9／1.9′ 預設值候選與 Task 7.7 之前置；原「2.1b 之前置」已隨 R 重開退役）**
- 內容：新建 `momentum/Analysis/contracts/future_column_lookahead.json`，
  登記搜尋結果**每一個**未來欄之 `lookahead_bars`：
  🔴 **兩套命名並存、單位不同**（GROK-R3-P1-01 抓出主委原寫死 72 之錯誤，實查證屬實）：
  - **bar 命名**（`future_{N}bar_return`／`future_{N}bar_max_drawdown`）：`N` **就是根數** ⇒ `lookahead_bars = N`
  - 🔴 **R 重開併回 D-002 A-005（GROK-R35-P0-02；以 producer 為準）**：`future{N}_close_return`，**N ∈ {1,2,4,6}**
    ＝ `df['close'].shift(-N)`（`case_search_engine.py:1379-1385`）⇒ **根數**，`kind: bar`、`lookahead_bars = N`，
    與 timeframe 無關（原文誤列為小時命名；照原文登記會在 12h 線把 `future6_close_return` 讀成 1 根、低估六倍）。
  - **小時命名**（`future{H}_close_return` 之 **H ∈ {24,48,72}**／`future72_max_return`／`future72_max_drawdown`）：
    `H` 是**小時**，實際根數 ＝ `H ÷ 每根小時數`（`case_search_engine.py:1385-1387` 之 `periods_{H}h`；
    12h 線 ⇒ `future72_*` 為 **6 根**，1h 線 ⇒ **72 根**）⇒ `lookahead_bars` **與 timeframe 相依，不得寫死常數**。
  ⇒ registry 對小時命名欄須存 `lookahead_hours` 並於執行期換算，**禁存固定 bar 數**；
  🔴 **R 重開併回 D-002 A-003：換算捨入方向＝向上取整**（`ceil`；registry 存 `hours_to_bars_rounding: "ceil"`，
  loader 對該值 fail-closed）——依 §C0 只准往保守方向解讀（`future24_*` 在 12h 線為 2 根；整除情形不受影響）。
  ⚠️ **另註**：`periods_72h` 亦被用於**過去 3 天 lookback**（`:1028-1046`），
  與未來欄同名不同義，登記時**不得混淆**（主委原將其誤認為未來欄）。
  盤點來源＝`case_search_engine.py:669-697`（CaseData 欄位）＋`:946-947`（擴展欄），不得遺漏。
  **辨識規則**須同時涵蓋：契約蛇形、CSV 標題形（`Future_NBar_Return_%`／`Future_NBar_Drawdown_%`，
  大小寫與 `%` 後綴，見 `search/page.tsx:567-573`）。
  **owner**：新增未來欄之 PR 須同步登記；**未登記即 fail-closed**（見下方②）。
  🔴 **信任邊界（R4 群集 G；CODEX-R4-P1-07）**：registry 之接受條件**不得只是欄名比對**——
  欄名可被改寫，使用者可把實際引用 20 根未來資料之自訂欄**改名**為已登記之 `future_4bar_return`，
  使 L2 不觸發、purge 被低估到 4 根。⇒ 分**兩類來源**，規則不同：
  - **系統產生欄**（`/search` 之搜尋結果，有 producer／manifest provenance）：
    可由 L1 直接依 registry 解析深度。判定依據＝該批之 provenance 記錄
    （`case_search_engine` 產出＋批次 receipt），**非欄名**。
  - **外部上傳欄**（CSV 匯入路徑）：**一律不得僅憑欄名進入可切分路徑**。
    須帶 producer/schema/digest 綁定；未帶者無論欄名是否命中 registry，
    皆走 Task 1.11 之 L2 強制宣告，並依 Task 1.12 之 L3 決定可否進切分。
  ⇒ 「名稱命中 registry」只在**系統產生欄**上成立；外部欄之名稱不具證據力。
- 驗證（`pytest` 與 `python3 -c` 實跑，逐項 `==` 斷言）：
  ①bar 命名：`m['future_4bar_max_drawdown']['lookahead_bars'] == 4`；
    小時命名：`m['future72_max_return']['lookahead_hours'] == 72` **且無 `lookahead_bars` 鍵**
    （防寫死）；換算函式對 `timeframe='12h'` 回 `6`、對 `'1h'` 回 `72`（`==` 精確比對）
  ②**缺標註 validator**：`pytest tests/momentum/event_samples/ -q -k lookahead_registry_complete`——
    掃描 `CaseData` 之所有 `future*` 欄名，**任一未登記即紅**（斷言未登記集合 `== set()`）
  ③辨識三形態：`Future_4Bar_Return_%`／`future_4bar_return`／`FUTURE_4BAR_RETURN` 皆解析為 4
  ④**registry 內容正確性**（R7 群集 F；codex：R6 版只驗「未登記集合 `== set()`」，
    **未驗登記的深度對不對**）：以實跑盤出之全部 `future*` 欄名逐欄對證單位與深度——
    `future_{N}bar_*` ⇒ `lookahead_bars == N`；
    🔴 R36 更正（GROK-R36-P1-01；R35 修 A-005 時漏改本驗收）：`future{N}_close_return`，**N ∈ {1,2,4,6}** ⇒ `kind == "bar"`、
    `lookahead_bars == N`、**無** `lookahead_hours` 鍵；
    小時命名 `future{H}_*`（H 為 24、48 或 72）⇒ `lookahead_hours == H` 且**無** bar 數鍵（本行刻意不與根數鍵同列：SYNC-FORBID 之防寫死 72 規則）；
    ⑦（R36 新增，D-002 A-003）換算捨入：`hours_to_bars(24, '12h') == 2`（ceil；非 floor 之 2 亦非 int 除之 2——以 `hours_to_bars(1, '12h') == 1` 區分，floor 得 0）；
    🔴 **無數字之 legacy 欄**（`future_max_return`／`future_max_drawdown` 等）
    ⇒ 其深度**不可由欄名導出** ⇒ registry 須顯式標 `lookahead_unknown: true`，
    並依 D-7 之 L2／L3 走強制宣告與禁進切分，**不得**給任何預設深度。
    盤點命令：`grep -oE "future[_0-9][A-Za-z0-9_]*" momentum/DataExtraction/case_search_engine.py | sort -u`
    ——該清單之每一項須在 registry 有對應且分類正確（三類：bar／hour／unknown）。
  ⑤**改名攻擊**（R4 群集 G）：`pytest tests/api -q -k lookahead_rename_attack` ≥2 條——
    上傳一份 CSV，欄名為 `future_4bar_return` 但**無 producer provenance**
    ⇒ 斷言 `requires_declaration == True`（不得因名稱命中 registry 而直接放行）；
    未填宣告即送出 ⇒ 依 L3 `split_events` 未被呼叫。
    對照組：同一欄名但來自 `/search` 之系統產生批（有 provenance）⇒ 深度直接解析 `== 4`。
  **mutation（三條，皆須紅）**：刪掉 registry 中 `future_4bar_max_drawdown` 一筆 ⇒ ②；
  把 `future_max_return` 改標成 `lookahead_bars: 12`（猜一個深度）⇒ ④；
  把外部上傳欄改成「名稱命中 registry 即直接解析」⇒ ⑤。
- 存活至：Phase 7（終）。
- 覆蓋風險：registry 為 D-7 三層防線之根（L1），Task 1.11（L2）／1.12（L3）／1.9′（預設值候選）皆只讀它（2.1b 已退役）、
  無一改寫它——「存活至 Phase 7（終）」即由此而來 ⇒ 不被覆蓋。**須同步**：Phase 4 之 Task 4.1
  引入附帶 `future_*` 欄、Phase 7 之 Task 7.5 分組報酬表若引入任何新的未來欄，皆須**先**在本
  registry 登記；未登記時 Task 1.10 驗證②之「未登記集合 `== set()`」會紅，該紅為 fail-closed 之
  預期行為，**不得以放寬 validator 或加白名單消紅**。
- 邊界：只登記深度，不改任何欄位之計算。
- 不可做：不得以欄名字串樣式**推測**深度（推測即可被改名偽造，見 L2）；
  不得漏登 `*_max_drawdown` 與 `future72_*`（R2 三家指出之實際繞法）。

**Task 1.11 — 強制宣告（D-7 之 L2；R 重開 D-8 改寫為「一律宣告」）**
- 內容（R 重開改寫）：**全部批次**於建立時（CSV 匯入＝Task 1.9；`/search` 匯出＝Task 1.9′）皆須
  逐 tf 宣告答案窗；後端 `resolve_declaration` 之 `needs` **恆為 True**（R 前之條件式
  `any(requires_declaration…) if referenced else (batch_has_filters and not canonical)` **刪除**——
  R 後 `referenced=∅`、`batch_has_filters=False` 會使其恆假而 fail-open，三家 R35 P0）。
  缺 `declared_window_bars`（任一出現之 tf 無鍵）⇒ CSV／對映路徑 **reject**（`lookahead_declaration_required`）。
  **JSON 直傳**：列內 `lookahead_bars_declared` 視為 Task 1.9′ 攜帶之宣告——須**批內同值**且**每個出現之 tf 皆有鍵**
  （不齊 ⇒ `heterogeneous_rows_in_batch`／缺鍵 ⇒ reject）；整批缺該欄 ⇒ **reject**（R 前之 `ON_MISSING_BLOCK` 改為拒收）。
  仍保留 R 前之語意一項：對無法由 Task 1.10 registry 解析之欄，UI 額外明示「系統無法驗證此深度，錯報將導致資料洩漏」。
  🔴 具名殘留 `R35-L2-ACK`（`needs-research`）：JSON 直傳無法複驗匯出端之 `acknowledged_unverifiable` provenance
  （契約無該欄；新增欄須 D-6）。
- 驗證（`pytest tests/api -q -k lookahead_declaration` ≥4 條）：
  ①fixture 含 `my_custom_signal` 欄 ⇒ `requires_declaration == True`
  ②🔴 fixture **全為系統產生欄、全可解析、無 `filters`** ⇒ `requires_declaration == True`（R 後不得因「無需宣告」放行）
  ③未填宣告即送出（CSV／對映）⇒ fail-closed（落檔數 `== 0`）
  ④JSON 直傳整批缺 `lookahead_bars_declared` ⇒ 拒收（HTTP 422，落檔數 `== 0`）；批內兩列該欄不同值 ⇒ `heterogeneous_rows_in_batch`
  **mutation（三條，皆須紅）**：把 `needs` 改回條件式 ⇒ ②③；JSON 直傳缺欄改回 block ⇒ ④；改為「忽略無法解析之欄」⇒ ①。
- 存活至：Phase 7（終）。
- 覆蓋風險（R 重開 D-8 改寫）：L2 之強制宣告自本 R 起**一律觸發**（兩路徑皆須宣告；原「只在 registry 解析不出深度時觸發」
  與 Task 2.1b 之「機器可證互斥分支」已隨 Phase 2 退役而不存在）⇒ 本 Task 之觸發面**擴大為全部批次**，
  其 UI 與 validator 即 Task 1.9／1.9′ 之同一份，本 Task 不另建。
  **須同步**：Task 7.1「邊界」已限定只接出後端既有能力、不新增後端未支援之值，故 Phase 7 不擴大
  本 Task 之觸發面；日後若任一 Phase 允許使用者自訂欄名進入篩選條件，該 Phase 須同批擴充本 Task
  之宣告 UI，否則自訂欄會落入「無人負責宣告深度」之縫隙而被 L3 一律擋死。
- 邊界（R36 更正殘句）：**全部批次皆須宣告**；「解析不出深度」之欄只是**額外加警語**之條件，不是觸發條件。
- 不可做：不得因為「其他欄都能解析」就用它們的 max 當全批深度；不得因「無條件引用欄」而免宣告。

**Task 1.12 — 不可證則禁進切分（D-7 之 L3）**
- 內容（🔴 R 重開 D-8：兩路徑缺宣告於**匯入時已 reject**（Task 1.11），本 L3 為分析時之第二道——對 R 前落檔、
  `lookahead_bars_declared` 缺欄或缺鍵之舊批仍須擋）：若使用者**未填** L2 之宣告、或宣告與 registry 衝突 ⇒ 該批**禁止進入
  train/test 切分與條件 IC**（`split_events` 與 `ic_feed` 皆拒），僅允許事件研究表
  （無訓練即無洩漏）。批次狀態標 `split_blocked_unverifiable_lookahead`（登記處見「須同步」）。
  🔴 **event-study-only 執行路徑（R4 群集 E；CODEX-R4-P0-02）**：R3 版只寫「仍可產出」，
  但實碼**做不到**——`pipeline.py:178` 之 `run()` **無條件**呼叫 `split_events`，
  且 `tables.py:88-93` 之 `event_forward_return_table` 之 `event_split_plan` 為**必填**、
  `:113` 直接 `event_split_plan.clusters.set_index(...)` ⇒ 照現有呼叫鏈只能在
  「違反 L3」與「產不出表」之間二選一。本批補齊該路徑，三項改動：
  ① 新增 executor `run_event_study_only()`——**不呼叫** `split_events`／`ic_feed`／不進訓練。
  ② `event_forward_return_table` 之 `event_split_plan` 改 `Optional`；為 `None` 時
     所有列之 `time_cluster_id` 取 `-1`（現碼 `:140` 對不在 `cl.index` 者已是此值）。
  ③ 🔴 `event_split_plan is None` 時 **`ci` 一律標為 unavailable，不得計算**——
     `_cluster_bootstrap_ci` 依 cluster 重抽樣，全部塞同一個 `-1` 會產生**看似有效但錯誤**的
     信賴區間。`common` 區塊本已 fail-closed（`tables.py:61-69`：無 split plan ⇒
     `formal_pooled_inference_allowed=False`、`reason=no_event_split_plan`），本項與之一致。
  **不得**以空的假 `split_plan` 冒充「未執行切分」（codex 具名之假綠形態）。
- 驗證（`pytest tests/momentum/event_samples/ -q -k split_blocked` ≥6 條）：
  ①該批呼叫 analyze ⇒ 切分**未執行**（斷言 `split_events` 未被呼叫，非只回警告字串）
  ②條件 IC ⇒ `capability_status == "unavailable"`、reason `== "split_blocked_unverifiable_lookahead"`
  ③事件研究表**仍可產出**：走 `run_event_study_only()`，斷言
    `len(result['sensitivity_micro']) == len(horizons)` 且 `receipts['n_rows'] > 0`
  ③b `event_split_plan=None` 時每個 horizon 之 `ci` `== "unavailable"`（**非** 數值區間），
    且 `common['formal_pooled_inference_allowed'] is False`、
    `common['reason'] == "no_event_split_plan"`
  ③c 傳入一個 `clusters` 為空 DataFrame 之假 split plan ⇒ **raise**（不得靜默當成 None 走過去）
  ④reason 字面取自契約：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/event_import_contract.json'));assert 'split_blocked_unverifiable_lookahead' in c['capability_unavailable_reasons']"` rc=0
    （🔴 **R8 移除本條之計數斷言**——該清單之增量已由 Task 1.1 驗收④以**對凍結 fixture 之差集**
    一次驗完；此處再寫計數即第二份副本，且 R8 已因 §F-2′ 再增一值而使原 `== 4` 失效），
    且 `grep -rc 'split_blocked_unverifiable_lookahead' api/ frontend/src/ momentum/ --include=*.py --include=*.ts` 之硬編碼字面數 `== 0`
  **mutation（四條，皆須紅）**：把禁令改成僅記 log ⇒ ①；把 reason 硬寫進程式 ⇒ ④；
  讓 `run_event_study_only()` 內部仍呼叫 `split_events` ⇒ ①；
  在 `event_split_plan is None` 時照算 `ci`（而非標 unavailable）⇒ ③b。
- 存活至：Phase 7（終）。
- 覆蓋風險：本禁令作用於 `split_events` 與 `ic_feed` 兩個消費端；Phase 6 之止血閘擋的是 IC 分析
  入口之**特徵數**，兩者為不同拒絕條件、不同 reason 來源（本 Task 走契約之
  `capability_unavailable_reasons`，Task 6.0 走 `ic_report_contract.json` 之 `reasons.analysis_rejected`）
  ⇒ 互不覆蓋，亦不得合併為同一回應
  （合併會使使用者無法分辨「洩漏不可證」與「特徵數過大」兩種完全不同的拒絕）。
  **須同步**：`split_blocked_unverifiable_lookahead` 登記於 `capability_unavailable_reasons`、
  **不進** `import_failure_reasons`；🔴 **R8 改寫**：該清單之增量由 Task 1.1 驗收④
  以對凍結 fixture（`event_import_contract.pre_gap3.json`）之差集統一驗證，本 Task 不再自寫計數
  （原文之「現 3 → 4」與 Task 1.1 之「`== 20`」皆已因 §F-2′ 改掛層次而失效——
  同型錯誤本欄已犯過，故改為機械差集而非人工同步）。
- 邊界：只擋切分與條件 IC，不擋事件研究。
- 不可做：不得以「警告後放行」替代（R2 codex 明指此為 fail-open）。

**Task 1.9 — 答案窗宣告與 purge 下界（D-7 之 L2 使用者介面；依賴 Task 1.10／1.11）**
- 內容：CSV 上傳時，答案窗**預設取檔內最大可用 horizon**（有 `future_1..12` ⇒ 預設 12）；
  可往下調但須勾選「我的篩選條件未用到超過第 N 根」之聲明，UI 明示**此為無法驗證的聲明**；
  欄位接受**任意非負整數**（不限 1..12；🔴 R35：`0` ＝「未用任何未來資訊」須明填、留白≠0，validator `v < 0` 才拒）。🔴 R 重開（D-8）：宣告值**即** derived 欄
  **`lookahead_bars_declared`**（map；逐 tf 直接取 `declared_window_bars[tf]`，不再經 Task 2.1b 解析——該 Task 已退役），
  並以 `max(1, lookahead_bars_declared[該列 timeframe])` 寫入
  `label_definition.window.horizon_bars`（契約下限之投影；
  🔴 **R9 修正**：R8 版只寫後者，會把真實深度 0 讀成 1，見 §D-3′-a（i）。
  🔴 **R11 修正（GROK-R11-P1-03）**：R10 版寫「該批所屬 tf」——批內可有多 TF，
  「該批所屬 tf」無唯一值 ⇒ 改為**逐列**取該列自己的 `timeframe`，與 Task 4.1 ③一致）。
  🔴 **UI 亦須逐 tf 收集宣告值**（`declared_window_bars` 為 map，見 §D-3′-a（ii））：
  批內只有一種 TF 時退化為單一輸入框；多 TF 時**逐 tf 各一個輸入框**，
  **不得**以單一輸入框套用到所有 tf（那會在小時命名欄上重現 R9 之錯）。
  purge 寬度之下界式見 §D-3′-a（ii），本欄不重述。
- 驗證：`pytest tests/api -q -k gap3_horizon_declaration` ≥5 條——
  ①CSV 含 future_1..12 ⇒ 預設值 `== 12`
  ②未勾聲明而調低 ⇒ fail-closed（落檔數 `== 0`）
  ③宣告 `== 4` 之**單一 1h 批**⇒ 該 symbol 之 `embargo_ms_by_symbol` 值
    `== 4 * TIMEFRAME_SECONDS['1h'] * 1000`
    （🔴 R11：原寫「4 根之毫秒數」在多 TF 下無唯一值，已綁定 tf 與 per-symbol map）
  ⑥🔴 **多 TF 批之宣告**：批內含 1h 與 12h，UI 逐 tf 各填 ⇒
    `declared_window_bars` 與 `lookahead_bars_declared` **鍵集皆恰為 `{'1h','12h'}`**；
    以單一輸入框套用全部 tf ⇒ fail-closed
  ④宣告 20（>12）⇒ 接受（不限 1..12）
  ⑤**宣告 validator 一致性**（R4 群集 D；R 重開改寫）：CSV 匯入路徑與 `/search` 匯出路徑（Task 1.9′）
    對同一組宣告輸入回傳**相同** `lookahead_bars_declared`，且呼叫**同一 exported** validator
    （`validateDeclaration`／`parse_lookahead_declaration`），非各自實作。兩路徑規則**相同**（皆可調低但須聲明）。
  **mutation（兩條，皆須紅）**：把預設值改回 1 ⇒ ①；
  讓任一路徑另寫一份 validator（不呼叫同一函式）⇒ ⑤。
- 存活至：Phase 6。
- 覆蓋風險：本 Task 之宣告值寫入 `label_definition.window.horizon_bars`，與 `/search` 路徑
  （Task 4.1 ③）之深度宣告為**同一欄位、同一寫入點**（R8 改寫：Phase 4 之「主答案窗」已依
  §D-3′ 移除，該欄不再有第二種語意）⇒ 兩路徑須呼叫**同一宣告 validator**（R 重開；原「Task 2.1b 之同一深度函式」已退役）；
  Task 4.1「不可做」已明令附帶欄多選不得改變該欄之來源。
  **須同步**（R 重開改寫）：原「系統內篩選路徑鎖定下界且不可調低 vs CSV 可調低但須聲明」之分派**已無對象**
  ——Task 1.9′ 使 `/search` 匯出路徑與本 Task **同一規則、同一 validator**；實作**不得**再依批次來源分派規則。
- 邊界：只管「宣告多遠」與其 purge 連動；不改 `event_split.py` 之 purge 演算法。
- 不可做：不得以「檔內有哪些 future_N 欄」推斷實際用到第幾根（D-7：偵測不可能）；
  不得給小於檔內最大 horizon 的預設值。

**Task 1.9′ — `/search` 匯出端答案窗宣告框（D-8；R 重開新增；取代 Task 2.1b 之導出路徑）**
- 內容：`/search` 兩條匯出（事件契約 JSON、可回灌 CSV）**匯出前**顯示與 Task 1.9 **同一元件**
  （`LookaheadDeclarationFields`）之逐 tf 宣告框：批內出現之每個 `timeframe` 各一個輸入框；
  預設值＝該搜尋結果**附帶** `future_*` 欄之最大可用 horizon（逐 tf；來源＝Task 1.10 registry 之揭露用途，
  ——不是深度導出；🔴 預設值之 wire path（CODEX-R35-P1-04）＝新增 `POST /api/v1/case/lookahead-declaration/preview-columns`，
  輸入＝搜尋結果之欄名集合＋timeframe 集合，回 `LookaheadDeclarationPreview`；**唯一實作**＝
  `lookahead_declaration.py::preview_from_columns`（與匯入端 preview 同一函式），前端只顯示、**禁**在 TS 重寫換算表）；
  可往下調但須勾選「我的正反例判定未用到超過第 N 根」之聲明（🔴 R35 裁定：N 為**非負整數**，`0` ＝「未用任何未來資訊」
  須**明填**、留白≠0，前後端 validator 之 `v < 1` 改 `v < 0`，Task 1.9 同步），UI 明示此為無法驗證的聲明，
  並明示「**填正例與反例兩邊判定所用之最遠者**」（使用者 2026-08-31：purge 取兩者較大）；
  欄位接受任意**非負整數**（`0` 須明填、留白≠0；R36 更正殘留字面）。宣告值即 `lookahead_bars_declared`（map），投影規則同 Task 1.9
  （`max(1, ·)` 入 `window.horizon_bars`——serialization floor，與宣告 oracle `0` 刻意分層）。
  🔴 **守衛**：`withExportLowerBoundGuard` 改形為 **`withExportDeclarationGuard(state, {notify, proceed})`**
  ——保留 D-004 A-021／D-002 A-010 之 **`proceed` 結構保證**（匯出動作只存在於 `proceed` 內，
  守衛外不可能發生匯出）；缺 map／批內某 tf 無鍵／非 int／`< 0`／調低未勾聲明 ⇒ **不呼叫 `proceed`**、
  `fetch`／下載 call count `== 0`。兩條匯出共用同一守衛實例。
  🔴 **validator 唯一**：前端 `lookaheadDeclaration.ts::validateDeclaration`／後端
  `lookahead_declaration.py::parse_lookahead_declaration` 與 Task 1.9 **同一份**，禁第二份實作。
- 驗證：`npx vitest run exportDeclaration` ≥7 條——
  ①批內 `{1h,12h}` ⇒ 恰兩個輸入框（`data-testid=lookahead-window-1h`／`-12h`），單一 tf 退化為一個
  ②不填任一 tf 即按匯出 ⇒ `proceed` 未呼叫、`URL.createObjectURL` call count `== 0`、`fetch` call count `== 0`
  ③調低於預設且未勾聲明 ⇒ 同②；勾選後 ⇒ 匯出成功且 `records[i].lookahead_bars_declared` 深度相等於宣告 map（逐列同值）
  ④宣告 `{1h: 20}`（>12）⇒ 接受；`records[i].label_definition.window.horizon_bars === Math.max(1, 20)`；
    🔴 R36 增 `0` 案例：宣告 `{1h: 0}`（明填）⇒ 接受，`records[i].lookahead_bars_declared['1h'] === 0` 且 `window.horizon_bars === 1`；
    留白（未填）⇒ 走②之擋（留白≠0）
  ⑤附帶欄選擇改變 ⇒ 宣告 map 與 `window.horizon_bars` **皆不變**（附帶欄只影響預設值之候選，不影響已宣告值）
  ⑥JSON 與 CSV 兩條匯出對同一宣告產出**相同** `lookahead_bars_declared`（逐鍵 `==`）
  ⑦`/search` 頁與匯入頁取用**同一 exported** `validateDeclaration` 參考（斷言同一函式物件）
  **mutation（四條，皆須紅）**：把匯出動作移到 `proceed` 外 ⇒ ②③；守衛對缺鍵 tf 以 `1` 默認 ⇒ ②；
  CSV 路徑另寫一份 map 組裝 ⇒ ⑥；前端自寫第二份 validator ⇒ ⑦。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **取代** Phase 2 Task 2.1b 對 `/search` 路徑之深度來源；Task 4.1 ③ 之寫入點不變、
  只換來源；Task 7.3 揭露之「lookahead 深度」自本 Task 之宣告讀取（**禁**殘留對 `exportFilters`／2.1b map 之讀取）。
  **須同步**：Task 1.9 之「可調低但須聲明」規則自本 Task 起**兩路徑相同**（原「系統內篩選鎖定不可調低」之分派已無對象）。
- 邊界：只管宣告與 fail-closed 守衛；不改 `event_split.py`；不做任何欄位掃描導出。
- 不可做：不得由附帶欄或任何欄名**推斷**深度（D-7：偵測不可能）；不得給小於預設之預設值；不得在 `proceed` 外匯出。

### ~~Phase 2 — 匯出前篩選~~　⛔ **R 重開退役（2026-09-02，D-8）**　【#0(a) 作廢】

> ⛔ **本 Phase 全部 Task 退役，不再實作、不再驗收**；原文保留供追溯（下方條文**不具效力**）。
> 退役理由（D-8）：使用者裁定匯出前篩選整區移除；深度來源改為使用者宣告（Task 1.9／1.9′）。
> 已落地之實作依 CROSS-FILE 退役清單移除（並同步 `docs/GAP3UX_IMPL_HANDOFF.md`——R 前交接，已加作廢 banner、下一批開工前重寫；R36 補列）：`frontend/src/lib/{exportFilter,lookaheadDepthLock}.ts`（＋測試）、
> `exportFilterPersist.test.ts`、`page.tsx` 篩選面板與 `export-count-n`、`api/routes/case.py` 之
> `/case/lookahead-depth` 與 `EventImportService.lookahead_depth()`（2.1b 之**前端導出端點**）；
> 🔴 **`lookahead_depth.py::depth_by_timeframe()` 本體保留**——它是匯入端 L2（`lookahead_declaration.py` →
> `pipeline.py:228`）寫入 `lookahead_bars_declared` 之唯一路徑；R 後其 `referenced_columns` **恆為空集**
> （`label_definition.filters` 無寫入者）⇒ 退化為 `declared_window_bars` 之逐 tf 驗證投影，**不再有 max 語意**；
> **保留**：`computeExportCounts`（Task 1.5 仍用，空條件＝恆等；`/search` 改顯示 M／X／Y）、
> `lookahead_declaration.py`／`lookahead_gate.py`／`lookahead_registry.py`。
> `label_definition.filters` 契約鍵**保留但匯出端不再寫入**（既為 optional；匯入端接受缺鍵）。
>
> ~~**定位（D-7 改正）**：Phase 2 不是「方便功能」——它是本批唯一能把「答案窗宣告」從不可驗的使用者聲明
> 變成機器可證事實的路徑。~~ ⛔ 此定位已被證偽：使用者於系統外標記時篩選面板為空 ⇒ 推不出深度、purge 為 0 而無人喊；
> 且 2.1b 自記四種抽不出引用欄之失敗形態，抽不出仍要問使用者（`G3-D1`）。

**Task 2.1 — /search 匯出前篩選面板**　⛔ RETIRED（D-8）
> ⛔ 以下原文不具效力（R 重開退役）。
- 內容：對搜尋結果任一數值欄設 `>=`／`<=`／區間，多條件 AND。
- 驗證：`npx vitest run exportFilter` ≥6 條；含「篩選後筆數 `==` 手算筆數」之數值斷言。
- 存活至：Phase 6。
- 覆蓋風險：面板只讀搜尋結果並產生條件物件，不改任何原始欄位值（「不可做」已鎖）⇒ 後續 Phase
  無改寫者。**須同步**：Phase 4 之附帶欄多選（Task 4.1）與 Phase 7 之五維度選擇（Task 7.1）與本
  面板同處匯出面板，但作用於不同輸出區塊——篩選決定**哪些列**、4.1 決定**哪些欄**、
  7.1 決定**用什麼語意算**，三者疊加不互相覆蓋；三個區塊須共用 Task 2.3 之同一筆數計算函式，
  否則使用者會在同一畫面看到互相矛盾的筆數。
- 邊界：只篩**數值**欄；字串欄不在本 Task。
- 不可做：不得在篩選中改動任何原始欄位值。

**Task 2.1b — 由篩選條件自動導出答案窗下界（D-7 第 2 層）**　⛔ RETIRED（D-8；深度來源改 Task 1.9／1.9′ 宣告；`/case/lookahead-depth` 端點與前端導出退役；`depth_by_timeframe()` 本體保留為匯入端投影，`referenced_columns` 恆為空集）
> ⛔ 以下原文不具效力（R 重開退役）。
- 內容：系統內篩選時，**依 Task 1.10 之欄位級標註**解析條件引用之**所有**欄位
  （含 `*_max_drawdown`／`future72_*`／任何登記欄），取其最大深度為答案窗**下界並鎖定**，
  使用者**不得調低**（與 CSV 路徑之「可調低但需聲明」不同——此處是機器可證，不需聲明）。
  🔴 **深度公式（R4 群集 D；本批唯一權威定義，Task 1.9 與 V-12 一律引用本式）**：
  ```
  depth(tf) = max( declared_window_bars[tf] ,
                   max over 所有實際被引用之欄位 c of  bars_of(c, tf) )
  bars_of(c, tf) = c.lookahead_bars                     # bar 命名欄
                 = c.lookahead_hours ÷ hours_per_bar(tf) # 小時命名欄（禁寫死常數）
  lookahead_bars_declared = { tf: depth(tf) for tf in 批內出現之 timeframe 集合 }
  # 🔴 鍵集於**匯入驗證通過後、prepare／coverage 之前**凍結；coverage 不得重建（§D-3′-a（ii））
  ```
  🔴 **R9 修正左項（CODEX-R9-P1-03）**：R8 版左項寫
  `label_definition.window.horizon_bars`——該欄自 §D-3′-a（i）起**下限為 1**，
  深度 0 時只是 serialization floor ⇒ 直接當左項會把真實 0 讀成 1，
  使 UI／purge／golden 互相不一致，且違反本 Task 覆蓋風險所禁之「過度 purge」。
  ⇒ 左項改為 **`declared_window_bars[tf]`**（使用者宣告之答案窗根數，**逐 tf**，
  不含 floor；缺該 tf 之鍵 ⇒ fail-closed，**不得**以 `1` 或其他 tf 之值默認替代。
  🔴 R11 修正：R10 版把左項留成單一值，混 TF 時無唯一單位語意）。
  🔴 **R10：本式之輸出為逐 tf 值（CODEX-R10-P0-01）**：`bars_of(c, tf)` 本就
  tf-parameterized（小時命名欄 `future72_*` 在 1h ＝ 72 根、12h ＝ 6 根）
  ⇒ `depth` 亦逐 tf 不同。**本式對批內每個出現過的 `tf` 各求一次**，
  結果即契約 derived 欄 **`lookahead_bars_declared: Mapping[tf -> int]`**
  （Task 1.1 ⑤ 登記）。匯出／CSV 兩路徑寫入該 map；purge 之 ms 換算見 §D-3′-a（ii）。
  ⇒ 深度**同時**取「宣告的答案窗」與「條件實際引用的最遠欄」之較大者，兩者缺一不可：
  只取前者會漏掉品質過濾欄；只取後者會漏掉「宣告 12 但條件只用 2」之情形。
  **四種 scenario 一律適用同一式**——A／B 之「事件在未來」由其 `window.horizon_bars` 表達，
  不另立公式（R3 之 A／B 敘事「≥ 事件之時間距離」即為本式左項，本批予以機械化）。
- 驗證：`pytest tests/api -q -k gap3_lookahead_depth` ≥4 條——
  ①條件用到 `future_2` 與 `future_7`（bar 命名，1h 批）⇒ 答案窗鎖定 `>= 7`；
    嘗試設 5 ⇒ 前端阻擋且 `fetch` call count `== 0`
  ②🔴 **小時命名欄之逐 tf 解析**（CODEX-R10-P0-01）：條件只用 `future72_max_drawdown`，
    批內同時有 1h 與 12h ⇒ 該 map 之 **1h 鍵值為 72 根、12h 鍵值為 6 根**
    （receipt：`python3 -c "from momentum.core.constants import TIMEFRAME_SECONDS;
    print(72*3600//TIMEFRAME_SECONDS['1h'], 72*3600//TIMEFRAME_SECONDS['12h'])"` → `72 6`）
    ⚠️ 本條刻意**不寫成** `lookahead_bars…＝72` 之形態——那正是檔頭 SYNC-FORBID
    所禁之字面（R3 之 future72 單位錯），因為它暗示「根數恆為 72 而與 tf 無關」；
    本條要表達的恰是**相反**：根數逐 tf 不同，時間長度才相同。
  ③同批之兩個 tf 換算回 ms **相等**（皆 72 小時）——證明小時命名欄與 tf 無關；
    對照組：改用 `future_4bar_return` ⇒ 兩 tf 之 ms **相差 12 倍**（bar 命名本就逐 tf 不同）
  ④批內僅單一 tf ⇒ map 退化為單鍵，值與 R9 版 scalar 相同（回歸保護）
  **mutation（三條，皆須紅）**：把 `max()` 改成 `min()` ⇒ ①；
  把 `bars_of` 之小時分支改成直接取 `lookahead_hours` 當根數 ⇒ ②；
  把 map 塌成單一 scalar（取批內任一 tf）⇒ ③。
- 存活至：Phase 6。
- 覆蓋風險：下界導出完全依賴 Task 1.10 之 registry，該 registry 存活至 Phase 7（終）且只增不改
  ⇒ 本 Task 之導出結果不因後續 Phase 失效。**須同步**：Phase 4 之 Task 4.1 讓使用者多選附帶
  `future_*` 欄——附帶欄**不是**篩選條件所引用之欄，**不得**納入 `max(lookahead_bars)`，
  否則答案窗會被與 label 判定無關的攜帶欄推高（過度保守亦屬錯誤：purge 過寬會吃掉訓練樣本）。
  此區分須以測試釘死：條件只引用 `future_2`、附帶欄選 `[1,3,7]` ⇒ 導出下界仍 `== 2`。
- 邊界：只導出下界；使用者可往上調（保守方向永遠允許）。
- 不可做：不得允許調低於導出值（那等於明知條件用到第 7 根卻只隔 5 根）。

**Task 2.2 — 篩選條件寫入 label_definition.filters**　⛔ RETIRED（D-8；契約鍵保留、匯出端不再寫入）
> ⛔ 以下原文不具效力（R 重開退役）。
- 內容：把篩選條件寫進契約已登記之 `label_definition.filters`（Task 1.1 已加）。
- 驗證：匯出檔 `label_definition.filters` 與送出條件深度相等（`==`）；
  且 `filters` 鍵存在於契約 `label_definition.fields`（防漂移斷言）。
- 存活至：Phase 6。
- 覆蓋風險：`filters` 為 Task 1.1 已登記之契約欄位，Phase 3..7 無 Task 改寫其 schema；D-2 禁止
  `filters` 進入 `event_id` 之輸入 ⇒ 寫入 `filters` 不回頭改變事件識別。**須同步**：Phase 7 之
  五維度亦寫入 `label_definition`（同一物件之其他鍵）⇒ 兩者須在同一序列化點寫出，並**依 §G 之
  S-1..S-9**處理（S-2 鍵序／S-5 NaN 與浮點／**S-9 位元組 encoder**）；
  本 Task **不自行定義**序列化規則，一律引用該節。
  （R4 群集 B 之修正：R3 版此欄把序列化義務寫成本 Task 自行宣告，而當時 §G 尚無該定義
  ⇒ 等於對一個不存在的規則下義務。§G 之 S-1..S-8 補上後，本欄改為純引用。）
- 邊界：只記錄條件，不改變 `label` 值本身。
- 不可做：不得把篩選條件納入 `event_id` 之輸入（會使同事件跨批 id 不同，違反 D-2）。

**Task 2.3 — 即時筆數顯示**　⛔ RETIRED（D-8；`computeExportCounts` 保留供 Task 1.5，`/search` 只顯示 M／X／Y、無篩選耦合）
> ⛔ 以下原文不具效力（R 重開退役）。
- 內容：顯示「將匯出 N 筆（原 M 筆）／你聲明的正例 X／反例 Y」。
- 驗證：vitest 斷言 `N + 被濾掉數 == M` 且 `X + Y == N`。
- 存活至：Phase 6。
- 覆蓋風險：本 Task 無持久產物，但其「正例 X／反例 Y」與 Task 1.5 之上傳確認、Task 4.1b／7.3 之
  動態揭露為**同一組事實之多個顯示點** ⇒ 四處須取自同一計算函式，任一 Phase 改變計數口徑時全部
  顯示點同步改變。**須同步**：Task 7.5 把報酬表拆為正／反／全體三組後計數口徑不變
  （`X + Y == N` 仍成立），但 `control_kind == 'user_labeled_other'` 時全體組標為 `not_computed`
  ⇒ 本 Task 之文案不得讓使用者以為全體組必然可算。
- 邊界：純顯示。
- 不可做：不得以估算值顯示。

### Phase 3 — 事件批次刪除（依賴：無）　【#4】

**Task 3.1 — DELETE /api/v1/case/events/{import_id}**
- 內容：刪除該批事件與其 artifact。
- 驗證：`pytest tests/api -q -k gap3_event_delete` ≥4 條；刪後 `GET` status_code `== 404`；
  且斷言該 `import_id` 之所有落檔路徑（事件檔＋Task 1.6 之 receipt＋該批 artifact）殘留檔數 `== 0`
  （防孤兒檔：僅驗 404 無法偵測磁碟殘留）。
- 存活至：Phase 6。
- 覆蓋風險：刪除只作用於已落檔之批次與其 artifact，不改任何契約與計算路徑，後續 Phase 無讀取
  或改寫此端點者 ⇒ 不被覆蓋。**須同步**：Phase 1 之 Task 1.6 receipt 與 Phase 2 寫入之
  `label_definition.filters` 皆屬「該批之 artifact」⇒ 刪除範圍須隨這兩個 Phase 新增之產物同步擴張；
  「刪後 `GET` `== 404`」偵測不到孤兒檔（端點回 404 但 receipt 仍在磁碟），故本 Task 之驗證
  另加落檔路徑清空斷言。
- 邊界：只刪該批；不連帶刪 kline 快取或 Feature Library。
- 不可做：不得提供「刪除全部」端點。

**Task 3.2 — 前端刪除鈕與二次確認**
- 內容：確認框顯示該批筆數與匯入時間。
- 驗證：vitest 斷言未確認時 `fetch` call count `== 0`。
- 存活至：Phase 6。
- 覆蓋風險：本確認框為 Phase 3 專屬元件，與 Task 4.3／5.3 之「缺答案窗欄」確認框為不同元件、
  不同觸發點 ⇒ 不共用亦不覆蓋。**須同步**：Task 3.3 於**同一個**確認框疊加警語 ⇒ 兩者合併實作
  （3.2 先、3.3 後），且 3.3 上線後本 Task 之「未確認時 `fetch` call count `== 0`」斷言須維持
  通過（回歸），不得因加警語而改動確認流程之控制流。
- 邊界：只在批列表提供。
- 不可做：不得以 `window.confirm` 帶過。

**Task 3.3 — 已被引用批次之警語**
- 內容：仍可刪，確認框明示「引用它的分析結果將無法重現」。
- 驗證：vitest 斷言該字串出現於確認框（`toContain` 斷言）。
- 存活至：Phase 6。
- 覆蓋風險：警語疊加於 Task 3.2 之確認框，不改刪除行為本身，後續 Phase 無改寫者 ⇒ 不被覆蓋。
  **須同步**：警語「引用它的分析結果將無法重現」之正確性依賴 Task 3.1 之刪除範圍確實涵蓋該批
  全部產物；若 3.1 未隨 Phase 1／2 新增之 receipt 與 `filters` 擴張刪除範圍，警語與實況不符
  （部分產物仍在、分析其實仍可重現）⇒ 3.1 與 3.3 須同批驗收。
- 邊界：只加警語。
- 不可做：不得靜默刪除被引用批次。

### Phase 4 — 匯出端之報酬欄與揭露（原名「答案窗」；依賴：無；**修正 R1 之錯誤相依聲明**）　【#1】

> 🔴 **R8 更名理由**：§D-3′ 把答案窗移到 IC 分析層 ⇒ 本 Phase 已不含答案窗。
> 保留舊名會使實作者在此尋找答案窗 UI 而找不到，或反過來把它加回匯出面板。
> 答案窗之落點＝Task 7.6（UI）＋ Task 7.0b（計算）。

> GROK-R1-P1-05 指出原版標「依賴 Phase 1、覆蓋 Phase 1 單 horizon 邏輯」是**錯的**：
> Phase 1 是 CSV **匯入**對映，不含答案窗／`future_*`／`label_value` 產生；
> 現行單 horizon 邏輯在 `eventExport.ts` 與 `/search`（B5 已落地）。已改正。

**Task 4.1 — 匯出檔之附帶 `future_*` 欄；並移除匯出端之答案窗與 `label_value`（D-3′）**

🔴 **R8 REOPEN 改寫**：本 Task 原名「可多帶 future_* 欄（D-3 之 (a)）」，
其「主答案窗」單選為 D-3 撤回之 (a) 方案之產物 ⇒ 依 D-3′ 移除。

- 內容（三件事）：
  ① **新增**「附帶報酬欄」多選（預設全選 1..12），匯出檔為每個選中 h 帶
     `future_{h}bar_return`——**純供 Excel 分析攜帶**，不進 `ic_feed`、不決定任何 horizon。
  ② **移除**匯出面板之「主答案窗」單選；匯出端**不再**寫入 `label_value`
     （`label_value` 於契約為 `optional_fields`，省略合法）。
  ③ `label_definition.window.horizon_bars` **仍寫入**，其值＝
     `max(1, lookahead_bars_declared[該列 timeframe])`（**下限 1 為契約 serialization floor**）；
     **真實深度**另寫入 derived 欄 `lookahead_bars_declared`（map；Task 1.1 ⑤ 登記）。
     語意與寫入規則之權威在 §D-3′-a（i），本 Task 不重述。
- 驗證：`npx vitest run eventExportHorizonColumns` ≥5 條——
  ①附帶選 `[1,3,7]` ⇒ 匯出檔含 `future_{1,3,7}bar_return` 三欄
  ②`'label_value' in records[0]` `=== false`（**每一列皆然**，非只驗第一列）
  ③匯出面板**不存在**「主答案窗」控制項（以 testing-library `queryBy*` 斷言為 `null`）
  ④`records[0].lookahead_bars_declared` **深度相等**於 Task 1.9′ 宣告框送出之 `declared_window_bars` map
    （R 重開：原「Task 1.10／2.1b 深度導出函式」已退役；**以同一 exported validator 之回傳比對，非寫死數字**），
    且 `records[0].label_definition.window.horizon_bars ===
    Math.max(1, records[0].lookahead_bars_declared[records[0].timeframe])`
  ⑤附帶欄之選擇改變 ⇒ ④所斷言之 `lookahead_bars_declared` 與 `window.horizon_bars`
    **皆不變**（證明附帶欄不參與深度導出）
  ⑥🔴 **深度 0 之 floor 行為**（§D-3′-a（i））：`scenario='C'` 且無品質過濾之 1h fixture
    ⇒ `lookahead_bars_declared['1h'] === 0` 且 `window.horizon_bars === 1`（兩者刻意不等）
  **mutation（四條，皆須紅）**：匯出端恢復寫 `label_value` ⇒ ②；
  把「主答案窗」控制項加回 ⇒ ③；`window.horizon_bars` 改讀附帶欄之 `max` ⇒ ④⑤；
  把 `lookahead_bars_declared` 也寫成 `max(1, depth)` ⇒ ⑥。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **覆蓋** R1 版之 (a) 方案（刻意，見 §D-3 撤回理由）。
  **須同步**：Task 1.9 之覆蓋風險原寫「本 Task 之宣告值…與 Phase 4 之『主答案窗』為**同一欄位**」
  ——「主答案窗」已移除 ⇒ 該處已改寫為「與 `/search` 路徑之深度宣告為同一欄位、同一寫入點」。
  兩路徑（CSV 宣告 vs `/search` 宣告）呼叫同一宣告 validator（R 重開；原「Task 2.1b 之同一深度函式」已退役）。
- 邊界：附帶欄 h ∈ 1..12；附帶欄只是攜帶，不參與 label 判定、不參與深度（只作 Task 1.9′ 預設值之候選）。
- 不可做：不得在匯出端以任何形式寫入 `label_value`（含寫 `null`、寫 `0`、
  或另立 `label_value_status` 之類新欄——新欄須先改契約，D-6）；
  不得把附帶欄之 `max` 當成 lookahead 深度（那是 D-7 明禁之「由欄位存在與否推斷」）。

**Task 4.1b — 匯出時揭露每個選項在動什麼（使用者 2026-08-22：「我不知道有什麼東西」；R8 依 §D-3′ 改寫③）**
- 內容：匯出面板明文顯示三件現行完全未告知之事實：
  ① **本批 scenario ＝ {實際值} — {契約 doc 之白話}**（由實際設定導出，**禁寫死**）
  ② **lookahead 深度 ＝ {N} 根，來源＝使用者宣告（Task 1.9′；R 重開 D-8）**——`N` 取自 derived 欄
    **`lookahead_bars_declared[本批之 timeframe]`**（R 重開 D-8：使用者宣告；C 未用未來資訊時**明填 0**；
    批內多 TF 時**逐 tf 各顯示一行**，不得只顯示其中一個）；
    🔴 **不得**顯示 `label_definition.window.horizon_bars`（該欄有下限 1 之 floor，
    深度 0 時會顯示成 1，見 §D-3′-a（i））
  ③ **本批之 purge 下界（事件事實層）＝ {N} 根**，並說明「此深度來自你宣告的最遠根數（正反例兩邊之較大者）」
    （R 重開 D-8；原「來自你的 label 定義最遠引用到 t0 之後第幾根」之導出敘述已退役）。🔴 **R8 增訂**：同時明示「條件 IC 分析時之實際 purge 另取本次答案窗，
    取兩者較大者」——公式之權威在 §D-3′-a（ii），本欄只揭露、不重述式子
  ④ 本批 `control_kind` 之值與白話意思（現由 `eventExport.ts:104` 寫死 `user_labeled_same_trigger`，
    使用者從未選過亦不知其存在）。
- 驗證：vitest 斷言四段文字皆出現；`control_kind` 顯示值 `==` 匯出檔實際值（防寫死漂移）。
- 存活至：Phase 6。
- 覆蓋風險：**會被 Phase 7 之 Task 7.3 覆蓋**——7.3 之動態揭露涵蓋 scenario／**control_kind**／
  進場價／報酬算法／決策位移／lookahead 深度／purge，為本 Task 四段揭露之嚴格超集，
  且同樣由實際設定導出、同樣禁寫死。
  🔴 **超集關係須以逐項對照驗證，非口頭宣稱**（R7 群集 D：本欄原宣稱超集，
  而 7.3 之揭露清單當時**漏掉 `control_kind`**，取代後 UI 反而少揭露一項）
  ——移除 4.1b 之獨立實作前，須逐項比對兩邊之揭露項集合並斷言 4.1b ⊆ 7.3。
  ⇒ 實作順序 4.1b 先、7.3 後；**7.3 上線時須移除本 Task 之獨立實作**，否則同一面板出現兩份揭露、
  兩份文案來源，日後改一份漏一份。此為**刻意覆蓋**，非漂移。**須同步**：兩者皆為 UI 文案、
  不進序列化產物 ⇒ 此覆蓋不影響 G-2 golden。
- 邊界：只揭露，不改任何預設值。
- 不可做：不得只寫在文件而不顯示於 UI（使用者原話：「我不知道你 JSON 內怎麼寫」）。

**Task 4.1c — 明文標示本批不提供 IC decay（CODEX-R2-P1-02／GROK-R2-P2-01）**
- 內容（**R8 依 §D-3′ 改寫措辭**）：SPEC §D-3 與 UI 皆須明寫：
  「條件 IC decay **曲線**（一次分析同時得到多個 h 的 IC）**非本批交付**；
  附帶之 `future_*` 欄**不進入 `ic_feed`**；
  要看不同答案窗，請**於 IC 分析頁改答案窗重跑分析**——
  **不需重新匯出事件批**（同一批事件事實可重複分析，見 §D-3′）；
  一次得到整條 decay 曲線待 GAP-6 之 IC-Analysis 整體處理。」
  🔴 舊措辭「需要 decay 則換**主答案窗**重跑」已隨主答案窗移除而作廢，不得殘留。
- 驗證：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；
  vitest 斷言該說明出現於匯出面板；**加兩條驗收**：
  ①選 `[1,3,7]` 附帶欄 ⇒ `label_definition.window.horizon_bars` **不變**
    （證明附帶欄不改深度宣告；`label_value` 已不存在於匯出檔，見 Task 4.1 ②）
  ②文案中**不得**出現「重新匯出」作為換 h 之手段（斷言該字串不出現）。
- 存活至：GAP-6。
- 覆蓋風險：GAP-6 若交付 multi-horizon IC，本說明須撤除。
- 邊界：只是揭露邊界，不改行為。
- 不可做：不得讓使用者以為多選附帶欄就會得到多條 IC。

**Task 4.2 — 事件後報酬表顯示完整曲線**
- 內容：`analyze_tables` 之 `horizons` 由呼叫端傳入（現碼預設 `(1,2,4)`，`pipeline.py:98`），
  前端可選要看的 horizon 集合。
- 驗證：`pytest tests/momentum/event_samples/ -q -k horizon_curve` ≥3 條；列數 `== len(horizons)`；
  🔴 **R 重開併回 D-004 A-022**：~~G-2 事件 golden 須同步更新~~ ⇒ **不重凍**——`scripts/gap3_freeze_golden.py` 跑的是 IC 分析管線
  （`ichc_run.run_analyze`），不呼叫 `analyze_tables`／`event_forward_return_table`；驗收改為
  `python3 scripts/gap3_freeze_golden.py --check` rc=0 且 `canonical_sha` **不變**。若日後 golden 真變，另依 D-4 實測說明，不預設重凍。
  本 Task 一併建 §G S-9 參考實作（`canonical_serialize.py::canonical_event_table_bytes`）並附 S-9 之
  🔴 **≥7 條**驗收（R 重開併回 D-002 A-002；⑦＝`horizons=[1,3,3,7]` 重複 h 須 `raise ValueError`，見 §G S-9 驗收）。
- 存活至：Phase 6。
- 覆蓋風險：改變 `analyze_tables` 預設值之呼叫形態（**刻意**，已由 G-2 守）。
- 邊界：只改要算哪些 horizon；**不改**每個 horizon 之計算式。
- 不可做：不得因列數變多而改變 `n_eff` 之定義。

**Task 4.3 — 缺欄確認框逐 horizon 列出**
- 內容（**R8 依 §D-3′ 改寫**）：訊息改為**逐附帶 horizon** 列缺幾筆。
  🔴 原文之「主答案窗與附帶欄**分開列**」已作廢——主答案窗已移除，匯出端不再有
  「答案窗缺欄」這件事（`label_value` 不在匯出檔內）⇒ 只剩附帶欄一類。
  答案窗之可算／缺筆數改於 **IC 分析頁**揭露（落點＝Task 7.6 之分析參數區）。
- 驗證：vitest 斷言訊息含每個缺欄**附帶** horizon 之筆數數字；
  **加一條**：訊息**不得**含「主答案窗」字樣（斷言不出現）。
- 存活至：Phase 7（終）。
- 覆蓋風險：覆蓋現行單一 horizon 之訊息字串（**刻意**）。**須同步**：Task 5.3 原以
  「主答案窗 h：N/M 筆可算」為顯示內容，已隨本 Task 一併改寫（見 Task 5.3）。
- 邊界：只改訊息，不改「缺欄不寫值」之既有行為。
- 不可做：不得因缺欄而阻擋匯出；不得在此處揭露答案窗（那已不屬匯出層）。

### Phase 5 — 錯誤訊息與表頭說明（依賴：Task 5.0）　【#2 ＋ #3 ＋ #6】

**Task 5.0 — 建立指標詞彙 SoT（GROK-R1-P1-04）**
- 內容：R1 查證 `event_import_contract.json` 之頂層 `_doc` 是**整份契約的敘事字串**，
  **不含** `macro mean`／`n_eff`／`lift_threshold`／`prevalence_full` 等表頭鍵
  ⇒ 原 Task 5.2 之「取自契約 `_doc`」不可執行。
  新建 `momentum/Analysis/contracts/event_metrics_glossary.json`：每個指標鍵對應
  `{term, definition, formula_ref}`，作為前後端**唯一**文案來源。
- 驗證：`python3 -c "import json;g=json.load(open('momentum/Analysis/contracts/event_metrics_glossary.json'));assert set(g)>= {'macro_mean','micro_mean','n_eff','lift_threshold','prevalence_full','prevalence_learn','signal_frequency','tail_excluded'}"` rc=0。
- 存活至：Phase 6。
- 覆蓋風險：glossary 為前後端唯一文案來源，Task 5.2 只讀不寫，Phase 6 不動事件型兩表
  ⇒ 本 Task 之既有鍵集不被覆蓋。**須同步**：Task 7.5 把報酬表改為正／反／全體三組後，
  新增之分組標籤與 `not_computed` 狀態文字亦屬表頭文案 ⇒ 須登記進 glossary；未登記則 Task 5.2 之
  「tooltip 文字 `==` glossary `definition`」對新表頭無可比對之來源，前端只能另寫一份定義，
  即本 Task「不可做」所禁之第二份副本。
- 邊界：只放文案與公式指標，不放數值。
- 不可做：不得把定義同時寫在前端（Task 5.2 以 `==` 斷言防漂移）。

**Task 5.1 — .source.json 誤傳之訊息追加正解**
- 內容：判別依據＝內容為 `canonicalSourceText` 形狀
  （symbol/timeframe/timestamp/positive_case/price_change）；
  訊息追加「此為來源對證檔，請改放在 `source_file` 欄並勾選 `verify_source_digest`」。
- 驗證：`pytest tests/api -q -k source_json_hint`；status_code `== 400` 且訊息含 `source_file`。
- 存活至：Phase 6。
- 覆蓋風險：只在既有回應訊息尾端追加提示字串、reason 字面不變 ⇒ 任何依 reason 字面判斷之下游
  （含 Task 1.1 之契約清單）不受影響，後續 Phase 無改寫者。**須同步**：Task 1.2 新增 CSV 端點後，
  誤把 `.source.json` 送到 CSV 端點會走另一條錯誤路徑（副檔名非 `.csv`）⇒ 該路徑須給出同一則
  正解提示，否則使用者在新端點得到的訊息比舊端點更難排除，本 Task 的修補在新路徑上等於沒做。
- 邊界：只追加提示；`legacy_schema_detected` 之 reason 字面**不變**。
- 不可做：不得因判別為 source.json 就自動改走 `source_file` 流程（靜默轉換＝契約禁止）。

**Task 5.2 — 事件型兩表 tooltip（讀 Task 5.0 之 SoT）**
- 內容：兩表所有表頭加 tooltip，文案取自 `event_metrics_glossary.json`。
- 驗證：vitest 斷言每個表頭之 tooltip 文字 `==` glossary 對應 `definition` 值。
- 存活至：Phase 6。
- 覆蓋風險：tooltip 純讀 Task 5.0 之 glossary，不改數值與版面；Phase 6 不動事件型兩表
  ⇒ 本 Task 不被覆蓋。**須同步**：Task 7.5 改變表格結構（單組 → 三組垂直排列）⇒ 三組共用同一組
  表頭鍵，本 Task 之「每個表頭之 tooltip `==` glossary `definition`」斷言須在三組結構下**逐組**
  重跑；實作順序 5.2 先、7.5 後，且 7.5 不得為分組另寫一份表頭文案。
- 邊界：只加 tooltip，不改數值與版面。
- 不可做：不得在前端另寫一份定義。

**Task 5.3 — #2 缺答案窗欄之確認框（GROK-R1-P2-01 指出 #2 原版未交代）**
- 內容：使用者 #2 問「要自己找案例時間點測嗎」——現行確認框只在缺 `future_{h}bar_return`
  時跳。改為：匯出前**主動顯示**「附帶欄 h：N/M 筆可算、K 筆因資料尾端不足而缺」，
  使用者不必自己去湊時間點才知道。
  🔴 **R8 依 §D-3′ 改寫**：原文顯示對象為「主答案窗 h」，該概念已移出匯出層
  ⇒ 匯出前之顯示對象改為**每個附帶 horizon**；答案窗之可算／缺筆數於 IC 分析頁揭露
  （落點＝Task 7.6）。使用者關切之「要自己找案例時間點測嗎」在兩處各自被回答。
- 驗證：fixture 尾端 3 筆不足 ⇒ 訊息含 `3`（數字精確比對）；
  **加一條**：訊息**不得**含「主答案窗」字樣。
- 存活至：Phase 7（終）。
- 覆蓋風險：與 Task 4.3 同一訊息區塊，兩者須合併實作（Task 4.3 先）。
- 邊界：只改顯示時機與內容。
- 不可做：不得阻擋匯出。

### Phase 6 — IC 分析止血閘（依賴：Task 6.0）　【#9a】

**Task 6.0 — IC 錯誤 reason 之登記處（D-6）**
- 內容：`feature_count_exceeds_cap` 不屬 `event_import_contract`（那是匯入契約）。
  **沿用**既有之 IC 側契約 `momentum/Analysis/contracts/ic_report_contract.json`，
  於其 `reasons` 物件新增分類 `analysis_rejected`（現有三類：`net_ic_unavailable`／
  `event_fallback`／`xsec_not_applicable`）並登記該值；程式與前端一律由該檔取字面。
- 驗證：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/ic_report_contract.json'));r=c['reasons'];assert 'analysis_rejected' in r;assert 'feature_count_exceeds_cap' in r['analysis_rejected'];assert len(r)==4"` rc=0
  （🔴 **斷言為成員資格而非等值**：Task 7.7 會往**同一個** `analysis_rejected` 再加兩個 reason，
  寫成 `== ['feature_count_exceeds_cap']` 會在 7.7 上線時假紅；該清單之**最終**內容由 Task 7.7 斷言）；
  且 `grep -rn 'feature_count_exceeds_cap' api/ frontend/src/ --include=*.py --include=*.ts --include=*.tsx | grep -v 'ic_report_contract' | wc -l` 之硬編碼數 `== 0`。
  **mutation**：把該字面硬寫進 `api/routes/ic.py` ⇒ 第二條斷言須紅。
- 存活至：GAP-6。
- 覆蓋風險：GAP-6 之規模防護可能新增更多 reason，屬疊加。
- 邊界：只登記 reason 字面。
- 不可做：不得在程式內硬寫該字串。

**Task 6.1 — analyze 前置特徵數檢查**
- 內容：`/api/v1/ic/analyze` 啟動任務**前**檢查特徵數；超過上限 ⇒ 400、
  reason 取自 Task 6.0 之登記檔，訊息含實際數與上限數。
  **碼內須註明本 Task 為過渡止血，GAP-6 之分塊計算上線後取代**。
- 驗證：`pytest tests/api -q -k ic_feature_cap` ≥3 條；以 218369 特徵之 run 呼叫 ⇒
  status_code `== 400` **且任務未被建立**（斷言 task store 筆數不變，非只驗 HTTP 碼）。
- 存活至：GAP-6。
- 覆蓋風險：**會**被 GAP-6 取代。
- 邊界：只擋 IC 分析入口；不擋 Feature Factory 產生大 run。
- 不可做：不得提供「強制略過上限」之開關。

**Task 6.2 — 上限值之量測協定（D-5）**
- 內容：定義**可重跑**之量測協定並產 receipt，每個量測點須記：
  ① 機器 RAM 總量與機型 ②目標 pid（單一，不得混進程）③baseline footprint（發請求前）
  ④peak footprint（採樣至任務結束或被 kill）⑤採樣間隔與總時長 ⑥該 run 之 `feature_count`。
  量測工具固定為 macOS `sample <pid>` 之 **Physical footprint** 欄（**禁用 `ps rss`**——
  R1 三家指出 macOS 壓縮頁面使 RSS 失真：UAT 實測 RSS 96–400MB vs footprint 7.1GB）。
  上限＝最小超標點之 `feature_count` **再乘安全係數 0.5**。
- 驗證：receipt 含 ≥3 個量測點且每點六欄齊全；同一 run 重跑 2 次之 peak 差異 `< 20%`
  （否則量測不穩定，須增加採樣或改協定）；設定值 `<=` 最小超標點 × 0.5。
- 存活至：GAP-6。
- 覆蓋風險：同 Task 6.1。
- 邊界：只量 IC 分析路徑；不量 Feature Factory。
- 不可做：**禁拍腦袋填數字**；無 receipt 不得寫入設定；禁以 `ps rss` 當量測值。

**Task 6.3 — 進度回報與前端狀態區分**
- 內容：進度加 `feature_count` 與細分階段；前端區分「後端無回應」與「任務執行中」。
- 驗證：`pytest tests/api -q -k ic_progress_fields` 斷言 response 含 `feature_count` 鍵；
  vitest 斷言兩種狀態之顯示字串 `!==`。
- 存活至：GAP-6 之後仍保留。
- 覆蓋風險：本 Task「存活至 GAP-6 之後仍保留」——Phase 6 五個 Task 中，6.0／6.1／6.2／6.4 之
  「存活至」皆止於 GAP-6（隨止血閘一併被取代），只有本 Task 為永久產出 ⇒ 本批內不被覆蓋。**須同步**：GAP-6 引入分塊計算後進度階段
  會細分得更多 ⇒ 本 Task 之階段字串須設計為**可擴充集合**，測試不得以固定 enum 之窮舉相等斷言
  鎖死（否則 GAP-6 會被迫改寫本 Task 之測試，而改測試是掩蓋行為變更的常見路徑）。
- 邊界：只加欄位與狀態區分。
- 不可做：不得以固定假進度值填充（UAT 已證實 `progress==0.12` 卡 15 分鐘之誤導性）。

**Task 6.4 — 止血閘之存活驗證（D-5）**
- 內容：以 218369 特徵之 run 呼叫 analyze 後，**在 cap 檢查之後、回應之前與之後各採樣一次**
  footprint，證明「未載入大矩陣」。
- 驗證：V-8 之三項斷言（見 §V）。
- 存活至：GAP-6。
- 覆蓋風險：V-8 三項斷言綁定「cap 檢查**之後**才採樣」之取樣時點，而該時點由 Task 6.1 之前置檢查
  位置決定 ⇒ 6.1 之檢查若被移到任務啟動之後，本 Task 會量到已載入大矩陣之 footprint 而失去意義；
  兩者須同批實作並以同一測試釘住先後順序。**須同步**：GAP-6 之分塊計算取代 6.1 時本 Task 一併作廢
  ⇒ 須在 GAP-6 之 SPEC 明列作廢並刪除，不得留著空跑而成為永遠通過的假綠。
- 邊界：只驗記憶體與存活。
- 不可做：不得在 cap 檢查**之前**採樣就宣稱通過（R1 明列此假綠形態）。

### Phase 7 — 全棧接線：把後端既有能力接出前端（依賴：無）　【使用者 2026-08-22 裁定「全接出來，一次做完整」】

> **病因（使用者問「怎麼又出現前後端無法串聯的情況？」）**：
> B5 之 SPEC 寫的是「API 接線＋前端三頁」、驗收條件是「UAT 能跑通」
> ⇒ 主委做了「能跑通的最小路徑」，六個維度全走預設值。
> 三輪 code review 未抓到，因**委員審的是 SPEC/TODO 有無被正確實作**——
> SPEC 沒要求接，實作沒接就不算違規。**規格層的漏，審查層抓不出來。**
> 主委另有現成規則 `feedback_fullstack_wiring_audit`（全棧三欄稽核）**未執行**，
> 而該規則正是上次「幽靈 feature_filter」事故後所立——同病第二次。

**盤點結果（實查證）**：後端五維度皆已實作，前端**一個都沒接**，全走 `eventExport.ts` 之寫死預設。

| 契約欄位 | 契約內完整路徑 | 後端 enum（元素數） | 前端現況 | UI |
|---|---|---|---|---|
| `scenario` | `/required_fields/scenario` | 4：A／B／C／two_stage | 寫死 `'C'`（`:95`） | ❌ |
| `control_kind` | `/required_fields/control_kind` | enum 4；另有 `accepted` 子集 3（`platform_random_bars` 恆拒） | 寫死 `user_labeled_same_trigger`（`:104`） | ❌ |
| `entry_price_semantic` | `/required_fields/entry_price_semantic` | 5 | 寫死 `trigger_open`（`:93`） | ❌ |
| `label_return_mode` | **`/required_fields/label_definition/fields/label_return_mode`**（唯一巢狀者） | 3 | 寫死 `close_to_close`（`:102`） | ❌ |
| `decision_offset_bars` | `/required_fields/decision_offset_bars` | 無 enum（`int`，`min=0`） | 寫死 `0`（`:92`） | ❌ |
| ~~`counterexample_kind`~~ | `/optional_fields/counterexample_kind` | 3 | **完全未送** | 🔴 **R5 群集 G：移出批次維度** |

🔴 **本表為「批次設定」，共 **五** 個維度**（R5 群集 G；codex＋composer 一致）：
`counterexample_kind` 位於契約之 `optional_fields`、語意為**逐列由使用者填寫**之欄
（`unclassifiable` 不可匯入 ⇒ `counterexample_kind_not_importable`），
**不是**可整批選一個值的第六個 scalar。把它接成批次下拉會污染或誤填反例分類。
⇒ 本批之處置：
- **移除**其批次下拉與 `EventExportOptions` 之 `counterexampleKind` 欄。
- 每列若來源有合法值則**原樣映射**；缺值**保持 omitted**（不寫 `null`、不填預設、不取第一列之值）；
  同批可任意混合 `a_trigger_no_follow`／`b_range`／`c_drop`／omitted。
- `label == 1`（正例）**不得**帶此反例欄；帶入或值非三個 enum ⇒ fail-closed，
  reason `== "counterexample_kind_not_importable"`（契約既有值，不新增）。
- `/search` 無來源值 ⇒ 全部 omitted；`/data-preparation` 之 CSV 路徑才可逐列匯入。
- `tables.py` 之反例分層仍讀 derived 之 `counterexample_kind_effective`，
  **不得**改讀任何批次層 UI 值。
⇒ Task 7.0／7.1／7.2 之「維度」一律指**上表前五列**；Task 7.3／7.6 之揭露亦只揭露五項。

> 路徑欄之 receipt：`python3 handoffs/20260822-gap3ux-x-review-r4-dims.py`（遞迴搜尋，不預設層級）。
> 六者分佈於 `required_fields`／`optional_fields`／`label_definition.fields` **三個不同層級**
> ⇒ Task 7.2 之機械閘不得以單一固定層級讀取 enum。

`buildEventContractRecords` 之 `opts` 介面**已有** `scenario?`／`entryPriceSemantic?` 等參數，
但 `/search` 呼叫端（`page.tsx:522-525`）**一個都沒傳** ⇒ 介面留了、UI 沒做。

**數值影響（須告知使用者）**：`entry_price_semantic`／`decision_offset_bars`／`label_return_mode`
三者**直接改變報酬數字**；若使用者實際策略是「訊號後下一根開盤進場」（`next_open`），
現有數字與其策略不符。

#### `label_value` producer 綁定（R5 群集 F；R8 依 §D-3′ 由匯出層改掛分析層；觸及數值正確性，§C0 不得降殘留）

🔴 **R8 改寫之範圍聲明（先讀本段再讀 F-1..F-5）**：本節原題為「`/search` 之 `label_value`
producer 綁定」，其全部條文都建立在「`/search` 匯出端寫 `label_value`」之前提上。
§D-3′ 已裁定匯出端**不寫** `label_value` ⇒ **前提消失**。
本節改寫為**分析層** producer 之綁定；`/search` 端之對應規則退化為單一條 F-0。

**F-0（`/search` 端；取代原 F-1..F-3 對匯出層之全部要求）**：
`/search` 匯出端**不產生、不寫入 `label_value`**（Task 4.1 ②）
⇒ 匯出層不再有「宣告語意 vs 實際數值不一致」之問題，原 F-2 之整批拒絕匯出
與 reason `label_producer_unsupported_for_declared_semantics` **不掛在匯出層**（改掛分析層，見 F-2′）。
`entry_price_semantic`／`label_return_mode`／`decision_offset_bars` 三者在匯出檔內
之角色 ＝ **該批之預設宣告（批次事實層）**，供 IC 分析頁作為分析參數之初始值；
其**不**決定任何數值，因為匯出檔內已無數值可決定。

🔴 **實碼查證之既有不一致（三家 R5 命中；主委實測覆核屬實）**：
`/search` 匯出之 `label_value` 固定取 `future_{horizon}bar_return`，而該欄之產生式為
`(close.shift(-h) - close) / close`（`case_search_engine.py:1317-1318`）
⇒ 其真實語意 ＝ **`entry_price_semantic=trigger_close` ∧ `label_return_mode=close_to_close` ∧
`decision_offset_bars=0`**。
但 `eventExport.ts:93` 之現行預設寫 `entry_price_semantic: 'trigger_open'`
⇒ **現行預設宣稱的語意與實際數值本來就不一致**，不是接出 UI 之後才產生的問題。

🔴 **R8 註**：上段之「既有不一致」在 §D-3′ 下**自動消失**——匯出端不寫 `label_value`，
就沒有「宣告 `trigger_open` 卻寫 close→close 數字」這回事。
保留本段為**病因紀錄**（它是 F-1 支援矩陣之由來），不得刪；但其結論已被 F-0 取代。

**F-1′ 分析層支援矩陣（封閉集合；R8 由匯出層改掛分析層）**：
條件 IC 之分析層 producer 本批只支援**唯一**之報酬語意三元組
`(trigger_close, close_to_close, k=0)`；**答案窗 `h` 為任意正整數，不受本矩陣限制**。
落在此三元組內才產生 `label_value`。short 取負之既有規則不變。

🔴 **主委裁決點（兩份補丁包互斥）**：
- `-arch-shift.md` 之 Task 7.6 diff 主張「**允許**在 IC 頁設定分析參數
  （`horizon_bars`、報酬語意三元組）」——即三元組亦可自由設定。
- `-arch-analyze-time-label.md` §6.2 之 golden 只涵蓋「(t0, h, direction, **F-1 三元組**)」，
  `-codex-pit-wiring.md` 之 golden 只涵蓋 long/short × 1h/12h × h=1/7
  ——**兩份補丁包所指定之 exact golden 皆未涵蓋其他三元組**。
- 既有 F-5 明訂「開放更多組合須先有逐組合之 exact golden」（R5 三家）。

**裁決**：三元組之控制項**移到 IC 分析頁**（arch-shift 之「可設定」在**位置**上落實），
但**本批之可操作集合仍鎖 F-1′**，其餘值 disabled ＋顯示 F-5′ 之開放前置理由。
理由：§C0「只能更嚴」；且無 golden 之組合一旦可選，使用者會拿到**沒有任何 oracle 驗過**
之 `label_value` 直接餵條件 IC——這正是 F-2′ 要根除者。
機制**沿用** Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`（路徑鍵新增 `'/ic-analysis'`），
**不另創第四種機制**。

**F-2′ 偏離即 fail-closed（分析層）**：三元組任一偏離 F-1′ ⇒ **該次分析拒絕**，
`capability_status == "unavailable"`，reason `== "label_producer_unsupported_for_declared_semantics"`。
🔴 **登記處隨層次改變**：本 reason 原登記於 `event_import_contract.json` 之
`import_failure_reasons`（匯入失敗）；改掛分析層後，其語意為**分析能力不可用**
⇒ 須改登記於 `event_import_contract.json` 之 **`capability_unavailable_reasons`**
（該鍵既有值＝`missing_label_value`／`missing_prevalence_disclosure`／`one_class_test_segment`；
receipt：`event_import_contract.json` 之同名鍵）。
🔴 **兩處清單之最終內容之權威在 Task 1.1**，本節**不重述計數亦不重述最終集合**。
🔴 **R9 刪除 R6 殘段（三家全員命中：CODEX-R9-P1-04／COMPOSER-R9-P1-01／GROK-R9-P1-01）**：
此處原殘留 R6 之祈使句「登記於 `import_failure_reasons`」，與上一段之
`capability_unavailable_reasons` **同段互斥**，實作者讀後段會把 reason 加回匯入失敗清單。
⇒ 該段已刪。本節對登記處**只引用 Task 1.1**，不再自寫任何登記祈使句或計數。
程式與前端一律由契約檔取字面，硬編碼數須 `== 0`。
🔴 **不得**單列 skip 後假裝成功，**更不得**在宣告 `next_open` 之下仍寫入 close→close 之數字
——那正是本群集要根除的假語意。

**F-3′ 預設值更正（D-4 合法變更；誠實預設）**：`entry_price_semantic` 之寫死預設由
`trigger_open` 改為 **`trigger_close`**，使「使用者完全不動 UI」時三元組落在 F-1′ 內。
⚠️ **R8 下之性質改變**：原文說「改前改後 `label_value` 位元組相同」——匯出端現已無
`label_value` ⇒ 該保證改述為：**本改動不影響任何數值**，只改該批之宣告欄字面，
且使該宣告與分析層之預設分析參數一致。須在 commit message 說明。

**F-4′ 單一公式來源（分析層）**：判定與換算須由**後端唯一函式**承載，
其呼叫點在**條件 IC 分析路徑**（非 `/search` 匯出）；
前端**不得**在 TS 產生、推導或攜帶 `label_value`（第二份副本必漂移）。
函式與 transport 之定義見 **Task 7.0b**（本節不重述簽章與端點）。

**F-5′ 開放更多組合之前置**：`next_open`／`decision_bar_*`／`k > 0`／非 `close_to_close`
於**條件 IC 分析頁**本批不開放（disabled ＋顯示理由）。
要開放，須有**逐組合之 exact golden**（§G G-3 之 analysis-label golden 擴充）；
在那之前產生不匹配之 `label_value` 一律視為 F-2′ fail-closed 之對象。
🔴 **R8 註**：R5 版所列之開放前置「須先有真正的 label producer（重用 `align_events` 之
`decision_at_ms`／`entry_at_ms`／`label_start_ms`／`label_end_ms` 與 bars）」
**已由 §D-3′ 之分析時 producer 滿足**（Task 7.0b）⇒ 剩下之唯一前置是 golden 覆蓋。
CSV 匯入路徑不經本矩陣（使用者自帶 `label_value`），但仍須過既有契約與 D-7 之 L2／L3；
🔴 **自帶 `label_value` 與分析時重算之互斥處置（`-arch-analyze-time-label.md` §5 要求「須寫死一種」）**：
採 **fail-closed** ——CSV 自帶 `label_value` 之批次，若使用者在 IC 頁給定與匯入宣告
不同之答案窗 `h`，該次分析**拒絕**，reason `== "label_producer_unsupported_for_declared_semantics"`。
理由：另一選項（鎖定匯入值、禁改 h）等於把不可驗之使用者數值當 oracle 沿用，
而系統無法證明該值對應哪個 h ⇒ 依 §C0 取嚴版。
📌 **具名標「待 R9 裁定」**：補丁包原寫只要求二擇一、未指定哪一個，本裁決為主委選擇。

**Task 7.0 — 前置：擴 `EventExportOptions` 補齊五維度（R4 群集 A；Task 7.1／7.2 之前置）**
- 內容：`frontend/src/lib/eventExport.ts` 之 `EventExportOptions`（`:9-17`）現缺
  `controlKind`／`labelReturnMode`／`decisionOffsetBars`／`counterexampleKind` 四個欄位，
  而 `buildEventContractRecords` 之 `:92`／`:102`／`:104` 仍為寫死值。
  本 Task **只做型別與參數化**：補齊五個 opts 欄位、把三處寫死改為 `opts.X ?? <現行預設>`、
  🔴 **不含** `counterexample_kind`（R5 群集 G：逐列選填欄，非批次維度）。
  🔴 **預設值之唯一例外**：依 §F-3′ 把 `entry_price_semantic` 之寫死預設由 `trigger_open`
  改為 `trigger_close`（D-4 合法變更；**不影響任何數值**，變的只有宣告欄字面
  ——匯出端於 R8 已不寫 `label_value`，見 Task 4.1 ②）。
  **除此一項外不動任何預設值、不加任何 UI。**
  🔴 `label_return_mode` 之寫入路徑為**巢狀**（`label_definition.fields`，見 Phase 7 前言表格），
  與其餘五者之頂層路徑不同，須各自對應正確路徑。
- 驗證：`npx vitest run eventExportOptions` ≥7 條——
  ①~⑤每維度各一條：傳**非預設值** ⇒ 產出記錄之對應路徑 `===` 傳入值
    （`label_return_mode` 須斷言 `records[0].label_definition.label_return_mode`，非頂層）
  ⑦全部不傳 opts ⇒ 五欄之值 `===` 預設（`'C'`／`user_labeled_same_trigger`／
    **`trigger_close`**／`close_to_close`／`0`），且 `counterexample_kind` **不出現於輸出**
    （逐列選填欄，見 G-1）
    🔴 `entry_price_semantic` 之預設基準已由 `trigger_open` 改為 `trigger_close`（見 F-3′）
    ——本 Task 之「行為不變」指 **G-2 事件 golden byte 級不變**，宣告欄字面刻意改正
  ⑧🔴 **R8 依 §F-0 改寫**：原⑧要求「三元組偏離 F-1 ⇒ 產出 `n_records === 0` 且 reason
    `label_producer_unsupported_for_declared_semantics`」——該 fail-closed 已隨
    §D-3′ 移到**分析層**（§F-2′，驗收落 Task 7.0b ③⑤）。
    匯出端已不寫 `label_value` ⇒ **沒有可假冒的數值**，整批拒絕匯出即無依據。
    改為：傳任一非 F-1′ 之三元組 ⇒ 匯出**照常成功**，
    且每一列皆**不含** `label_value`，`records[0].entry_price_semantic` 忠實等於所傳值
    （宣告即事實，不再有「宣告與數值不符」之可能）
  **mutation（兩條，皆須紅）**：把任一 `opts.X ?? default` 改回寫死 ⇒ 對應那條；
  在任一三元組之下於匯出端寫入 `future_{h}bar_return` 作為 `label_value` ⇒ ⑧。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task 只擴介面不接 UI，其產出被 Task 7.1（接 UI）與 7.2（機械閘）**依賴而非覆蓋**
  ⇒ 三者為 7.0 → 7.1 → 7.2 之嚴格順序。**須同步**：7.0 之⑦「不傳即等於現行預設」是 7.1
  golden byte 回歸之**基準**；若 7.0 順手改了任一預設值，7.1 之回歸就失去意義 ⇒ 兩者須同批驗。
- 邊界：只擴型別與參數化＋§F-3 之單一預設更正；不加 UI；
  **本 Task 範圍內**不改後端（F-4 之後端唯一 producer 由 **Task 7.0b** 承載）。
- 不可做：**除 §F-3 明列之 `entry_price_semantic` 一項外**，不得調整任何其他預設值
  （R6 群集 C：R5 版三處禁令與 F-3 互斥，Agent 可援引禁令拒絕 F-3）；
  不得把 `label_return_mode` 寫到頂層——正確路徑為
  `label_definition.label_return_mode`，寫錯位置會使契約 schema 檢核通過但語意落在錯的物件。

**Task 7.0b — 分析時 `label_value` producer 與其 wiring（R6 群集 E；F-4′ 之承載 Task；R10 拆兩階段函式）**

🔴 **R8 REOPEN 重寫**：R7 才補上之 `POST /api/v1/case/label-values` 落在**匯出**生命週期
（request 帶 `cases`＝`/search` 之結果列、呼叫點為 `buildEventContractRecords`）。
§D-3′ 裁定答案窗屬**分析層** ⇒ 該端點之整個生命週期位置錯誤，**非改參數可補**，故重寫。
原版條文保留於本 Task 末「原版與撤回理由」，不得刪。

- 內容（四件事）：

  **① 後端唯一 producer 函式**
  新建 `momentum/Analysis/event_samples/label_value_from_case.py`。
  🔴 **R11 更正**：R10 版此處寫「公開單一函式」，與下方已拆成之**兩個**具名函式互斥
  （CODEX-R11-P0-03 之拆分要求）⇒ 本模組公開**恰兩個**函式，簽章如下
  ```
  # 階段 2（prepare-windows）：唯一產生 receipt 與其 hash 之處
  def prepare_analysis_windows(
      records,
      bars_by_tf,
      *,
      event_label_spec,
      event_import_id,
      lookahead_bars_declared,
      timeframe_seconds) -> PreparedAnalysisWindows:
  # 🔴 R33 三家逐字一致：本塊為**簽章**（`def …:` 形），`*` 後為 required keyword-only；
  #   **不得**寫成呼叫形 `名=值`（在簽章語境會被讀成預設值，並使 §G G-3 之
  #   `inspect.signature` 驗收失去唯一來源）。呼叫形只出現在下方編排草圖。
  # 🔴 R27（三家：CODEX-R27-P1-01＋GROK-R27-P1-01＋COMPOSER-R27-P1-01）：
  #   R25／R26 之取得點散文要求「prepare 前建構一次 timeframe_seconds、以同一物件傳入
  #   purge 與 gate」，但**本 producer 之簽章未列該 map** ⇒ 規格內無路徑可傳進來，
  #   散文與簽章互斥。**主委連兩輪未同步簽章**（R26 之 prepare-map-kwargs 補丁包整包未套）。
  #   ⇒ 簽章補 `lookahead_bars_declared`／`timeframe_seconds` 兩個 keyword-only 參數，
  #   與 §G G-3 ⑥(d) 之 keyword 集合一致。
  # PreparedAnalysisWindows 欄集恰如下
  #    .supported: bool
  #    .windows: tuple[WindowRow, ...]           # R13 (β) 定死；**不是 dict**
  #                                              #   WindowRow 為 frozen dataclass，欄集恰
  #                                              #   {event_id, symbol, timeframe,
  #                                              #    decision_at_ms, entry_at_ms,
  #                                              #    label_start_ms, label_end_ms}，
  #                                              #   按 event_id UTF-8 升冪
  #                                              #   🔴 R18：symbol／timeframe 為 R17／R18
  #                                              #   新增，來源見 §D-3′-a（ii）之導出表
  #    .analysis_alignment_receipt_hash: str     # 決定性（同輸入同值）
  #    .per_tf: tuple[PerTfRow, ...]             # R12 補：逐 (event_id, timeframe) 之
  #                                              #   feature_cutoff_ms；欄集恰三鍵、按
  #                                              #   (event_id, timeframe) UTF-8 升冪。
  #                                              #   **coverage／Task 7.7／G-3／ic_feed 之唯一讀取路徑**
  #    .normalized_spec_bytes: bytes             # R13 定死（R12 之 Mapping + 「canonically 相等」
  #                                              #   無定義，三家命中）：本 receipt 實際使用之
  #                                              #   event_label_spec 經**唯一 normalizer** 後，
  #                                              #   以 §G S-9 encoder 產出之 **exact bytes**。
  #                                              #   相等判定＝**bytes 相等**，非 dict==、非 json.dumps。
  #    .allowed_event_ids: frozenset[str]        # prepare 之**初值＝通過驗證之全部 event_id**；
  #                                              # coverage **不得原地寫入**（frozen ⇒ TypeError），見下
  #    .purge_lower_bound_ms_by_symbol: tuple[SymbolPurgeRow, ...]
  #                                              # R14 (γ)；🔴 R15 補列入本欄集
  #                                              #（原「欄集恰如下」漏列本欄，與 (γ) 互斥）
  #    .prepared_token: str                      # **非決定性**：每次呼叫都不同
  #    .reason: str | None
  #    .direction_sign: int                      # 🔴 R 重開併回 D-005 A-023：恰 +1（long）或 -1（short），
  #                                              #   批次 scalar；來源＝keys.py::event_direction_sign(record)
  #                                              #   （第三個 accessor，同檔同紀律）；WindowRow 維持恰七鍵、
  #                                              #   event_label_spec normalizer 維持恰四鍵（皆不動）
  # 🔴 A-023 要件（併回本體，原文在 D-005，該檔已 SUPERSEDED-BY-R）：
  #   ① 階段 5 之 signed 值 = direction_sign * (close[label_end_ms] - close[label_start_ms]) / close[label_start_ms]
  #      —— 乘號**只在 producer**，consumer（ic_filter_orchestrator／ic_feed）不再乘第二次
  #   ② direction_sign **須進** analysis_alignment_receipt_hash 之輸入（同批 long／short 兩次 prepare 之 hash 不相等）
  #   ③ 驗收（三條）：short 批 label_value == -x（atol=0）；long／short hash 不相等；event_direction_sign 對非法值 raise
  #   ④ mutation（四條，皆須紅）：short 回 +1 ⇒ ②；乘號移到 consumer ⇒ producer 級 mutation 打不到 ⇒ ③；
  #      direction_sign 自 hash 輸入移除 ⇒ hash 相等斷言紅；accessor 接受第三值 ⇒ raise 斷言紅
  #   ⑤ A-024（同檔第二條；R 首版落點表漏列）：驗收 ⑧(a) 之前綴保留判準改為**逐 namespace**（見 Task 1.1 ⑧(a) 之 R 註）

  # 階段 5（materialize values）：吃階段 2 之**物件**，**不得**重跑 align_events
  # 🔴 R12（CODEX-R12-P1-05）：`event_label_spec` 須與 prepared 綁定——
  #    resolve 收到之 spec 經**同一 normalizer + S-9 encoder** 產出 bytes 後，
  #    與 `prepared.normalized_spec_bytes` **不逐位元組相等 ⇒ fail-closed**。
  #    🔴 **normalizer（唯一；R13 定死）**：輸入須恰為四鍵
  #      `{horizon_bars:int, entry_price_semantic:str, label_return_mode:str, decision_offset_bars:int}`
  #      ——**多一鍵／少一鍵／型別不符 ⇒ fail-closed**（不做預設值填補、不做型別轉換）；
  #      🔴 **R14 定死型別判定為 `type(v) is int` / `type(v) is str`，不用 `isinstance`**
  #        （三家命中）：`isinstance(True, int)` 為真，而 S-9 白名單同時含 `bool`／`int`
  #        ⇒ `horizon_bars=True` 會通過寬鬆檢查、卻序列化成 `true` 而非 `1`，產出不同 bytes。
  #        `numpy.int64` 等純量同理 ⇒ 一律 fail-closed，**不得**先 `int()` 轉換。
  #      鍵序固定為上列順序；輸出 dict 直接餵 §G S-9 encoder。
  #    否則可用 h=7 prepare 產生 hash／token，再以 h=3 resolve，兩者仍回同一 hash／token
  #    而驗收⑩全綠（＝purge 用 h=7、label 用 h=3，正是 §D-3a 要根除者的復發）。
  resolve_label_value_at_analyze(prepared: PreparedAnalysisWindows, bars_by_tf,
                                 *, event_label_spec)
      -> {"supported": bool,
          "label_values": {event_id: float | None},
          "analysis_alignment_receipt_hash": str,   # 與 prepared 之值相同
          "prepared_token": str,                    # 與 prepared 之值相同
          "reason": str | None}
  ```
  🔴 **R10：兩階段須為兩個具名函式**（CODEX-R10-P0-03）——R9 版只有一個
  `resolve_label_value_at_analyze` 同時做 windows 與 values，
  「明示兩階段」只停在散文層，實作者仍可在 coverage／split／labels 各自呼叫它一次
  ⇒ 各自重跑 `align_events`、各自得到一份 window。

  🔴 **R11：拆函式**不足**，須加 single-pass 之機械約束**
  （CODEX-R11-P0-03＋GROK-R11-P1-05 兩家）：`prepare_analysis_windows` 是**決定性**的，
  三個 consumer 各自呼叫一次會得到**相同 hash** ⇒ 驗收⑩仍綠，
  但三份 object 可能是不同的 mutable DataFrame／不同中間狀態。
  **「hash 相同」不能代替「同一次呼叫」。** ⇒ 三條硬性約束：
  1. `prepare_analysis_windows` 之回傳為 **typed 物件 `PreparedAnalysisWindows`**
     （非裸 dict），內含 `windows`／`analysis_alignment_receipt_hash`／
     `allowed_event_ids`／`prepared_token: str`。
  2. `prepared_token` 由 prepare 於**該次呼叫**產生，**不由輸入決定**
     （即：同輸入兩次呼叫得到**不同** token；與 hash 之決定性刻意相反）。
     coverage／split／labels **只接受 `PreparedAnalysisWindows` 物件**，
     不接受 dict、不接受重新組裝之等價物。
  3. `_run_analysis` 之事件分支**只呼叫 prepare 一次**；
     驗收以 spy／`unittest.mock.patch(..., wraps=...)` 斷言 `call_count == 1`。

  🔴 **R12 修正：frozen ／「寫回」／`is` 同一物件，三者在 Python 不可同時成立**
  （CODEX-R12-P0-01＋COMPOSER-R12-P0-01＋GROK-R12-P0-01，**三家全員**；
  這是主委 R11 自己引入之矛盾——frozen 禁屬性賦值，而 `dataclasses.replace` 會產生新身分）。
  **唯一路徑（採 `-prepared-coverage-writeback.md`；codex／composer 之兩份提案結論相同，
  取 grok 版因其把初值、函式名與驗收改寫都寫死）**：
  🔴 **R13 補三條（不補則 R12 之修法仍不可實作）**：
  - **(α) `replace` 會重跑 `__post_init__`**（CODEX-R13-P0-01 實跑 probe：
    `replace_reruns_post_init True`）⇒ 若 token／hash 由 `__post_init__` 衍生，
    `prepared1` 之值會**重算**，(ii′) 之「兩者相等」可假綠亦可假紅。
    **定死**：`PreparedAnalysisWindows` **不得有 `__post_init__`**；
    `analysis_alignment_receipt_hash` 與 `prepared_token` 皆為**建構參數**，
    由 `prepare_analysis_windows` 於階段 2 一次算出後傳入，`replace` 原樣攜帶。
  - **(β) frozen 是淺層**（CODEX-R13 probe：`frozen_shallow_nested_mutation True`）
    ⇒ `.windows` 若為普通 `dict`，consumer 改一列即可讓 hash 與內容不一致。
    **定死**：`.windows` 之型別為 `tuple[WindowRow, ...]`（`WindowRow` 亦 frozen dataclass，
    欄集恰 `{event_id, symbol, timeframe, decision_at_ms, entry_at_ms,
    label_start_ms, label_end_ms}`，按 `event_id` UTF-8 升冪）；
    `.per_tf` 同理為 `tuple[PerTfRow, ...]`。
    🔴 **R18 補 `symbol`／`timeframe` 兩欄與其來源（COMPOSER-R18-P1-01）**：
    R17 只在 hash 之 `event_level` 要求 `symbol`，**卻未同步本欄集**，亦未規定該值從哪來
    ⇒ 實作者會自行從匯入檔或其他處取，與 split 之 groupby 鍵可能不同源。
    **定死來源（唯一）**：
    - 現碼 `momentum/Analysis/event_samples/alignment.py:21` 之 `_EVENT_COLS`
      **不含** `symbol`／`timeframe` ⇒ **本 Task 須擴充該常數**（先改契約，D-6）。
    - 兩欄之值一律取自 `records` 中該事件之 `Mapping[str, Any]` record，經
      `event_scope_key(record)`／`event_trigger_timeframe(record)` 取得；accessor 內固定使用
      `record["symbol"]`／`record["timeframe"]`，禁 `records[event_id]` 與 attribute access。
      **不得**由檔名、UI 選單或 run 設定推得。
      🔴 **R28（CODEX-R28-P1-03）**：R27 版寫 `records[event_id].symbol`——
      既用 **id 下標**又用 **attribute 存取**，與 R27 才剛定死之
      「`records` 為 `tuple[Mapping,...]`、一律 key access」**兩處互斥**。
      若需按 id 查詢，**先建** `Mapping[event_id, row]` 再 `by_id[eid]["symbol"]`。
    - `symbol` 須與 `event_split.py:54` 之 `groupby("symbol")` 鍵**同一個值**。
      🔴 **R19 補齊（CODEX-R19-P1-03）**：R18 版只寫「同一 exported 取值函式」，
      **沒給函式名、owner、參數／回傳 shape，而現碼也沒有這樣一個 accessor**
      ⇒ 該驗收當時**寫不出來**。定死如下（本 Task 之交付物）：
      ```
      # momentum/Analysis/event_samples/keys.py   ← 新檔；owner＝本 Task
      def event_scope_key(record) -> str:
          """事件之 split scope 鍵。**唯一**取值點。"""
      ```
      · 🔴 **R20 刪除「consumer 恰三處」之枚舉（CODEX-R20-P1-04）**：R19 版列了三處
        （`align_events`／hash 組裝／`event_split` groupby），**漏算**階段 2 之 purge rows、
        depth map 查表、digest 之 keyset 等資料路徑。正確實作之 consumer **超過三處**；
        硬守三處反而逼實作者在階段 2 直接讀 raw field。
        ⚠️ **枚舉 consumer 數量正是本 epic 反覆出錯之形態**（purge 自由變數四次、
        雜湊入口三次），**不再枚舉**。
      · 🔴 **R21 降級為「待裁定」（CODEX-R21-P1-03 裁定，主委自我歸類被推翻）**：
        R20 主委把本條自判為角色卡允許之 (b)「三類機械斷言」，**該自判錯誤**——
        AST 斷言是**解析 Python source 並分類 AST 節點**，不是位元組／集合／`is` 比對。
        且該掃描面只涵蓋 `event_samples/**` 之**屬性直取**，
        現行主要 consumer 用的是 **dict subscript**，掃不到；
        「每個實際 consumer」亦無可驗證之枚舉器。
        ⇒ **本條不作 active acceptance**，改標 **`待裁定`**：
        由實作 Task 明定 code-owned accessor 之 call-site／identity 證據與 scope，
        **不得**以「未維護之 consumer 數量」或「不完整之 AST 掃描」收斂。
        （採 CODEX-R21 補丁包 `-keys-consumer-guard.md`；主委未自創。）
      · **本輪仍成立之部分**：`record.symbol`／`record.timeframe` 之任何讀取皆須經該函式
        ——此為**規範陳述**，其驗收形式待實作 Task 定。
      · 🔴 **`timeframe` 同理**：`event_trigger_timeframe(record) -> str`，同檔、同驗收方式。
    - `timeframe` 為**觸發 TF**，與 `per_tf` 之特徵 TF 集合**不同語意**（見 §D-3′-a（ii））。
    **mutation**：①`WindowRow` 移除 `symbol` 或 `timeframe`
    ⇒ §G G-3 ⑥(d) 之 signature 對證紅（**本條生效**）。
    🔴 **R22 更正（三家；COMPOSER-R22-P1-01＋CODEX-R22-P1-03＋GROK-R22-P1-01）**：
    原 ②③ 分別指向 (i) 之 AST 斷言與 (ii) 之 `is` 斷言，而**該兩條已於 R21 標「待裁定」**
    ⇒ **依賴待裁定條文之 mutation，其自身亦為待裁定**；原寫「三條**皆須紅**」會使
    reviewer 把**尚未生效**之驗收當成凍結門檻。
    ⇒ **②③ 同步標 `待裁定`**：②`symbol` 改由匯入檔欄位直取而非 `event_scope_key()`；
    ③任一 consumer 改為自寫取值。二者之驗收形式**與 (i)(ii) 同批由實作 Task 定**。
    ⚠️ **通則（本輪起適用全檔）**：**mutation 之效力不得高於其所依賴之驗收條**；
    降級一條驗收時，**須同批降級所有指向它的 mutation**。
    **禁**任何 `dict`／`list`／可變容器出現在本物件之欄位型別中。
  - **(γ) purge 下界隨 receipt 攜帶**：`.purge_lower_bound_ms_by_symbol: tuple[SymbolPurgeRow, ...]`
    （🔴 R15 修正標題行：R14 已於後文改為 tuple，但此處仍寫 `Mapping[str, int]`
    ⇒ 實作者依標題行實作 `MappingProxyType` 會直接打穿 R14 之兩個 probe）
    🔴 **R14 改型別**（CODEX-R14 probe `direct_assign`／GROK-R14 probe
    `shared_underlying_after_mut` 兩家獨立打穿）：`types.MappingProxyType` **只擋 proxy 上的寫入，
    不隔離建構時傳入之 mutable dict alias**——持有原 dict 者改值即改變 receipt，
    且 `replace` 原樣攜帶同一 proxy ⇒ `prepared0`／`prepared1` 會一起變。
    又與 (β)「禁任何 dict／可變容器」自相矛盾。
    ⇒ 型別改為與 (β) **同型**：`tuple[SymbolPurgeRow, ...]`
    （`SymbolPurgeRow` 為 frozen dataclass，欄集恰 `{symbol, purge_lower_bound_ms}`，
    按 `symbol` UTF-8 升冪）。
    🔴 **R14 補鍵集定義（CODEX-R14）**：其 `symbol` 集合**恰等於 pre-coverage 之 symbol 集合**；
    某 symbol 於 3b 後全數消失時，該列**仍留在 tuple 內**（split 讀到不存在於本次 assignments 之
    symbol 時**略過即可，不得 fail**——它只是未被使用之下界，非錯誤）。
    於**階段 2 末**由 pre-coverage 事件集合算出
    （見 §D-3′-a（iii）階段 4 之 R13 修正）；階段 4 只讀不算。
  ```text
  apply_event_coverage(prepared: PreparedAnalysisWindows, ...) -> PreparedAnalysisWindows
      # 回傳 dataclasses.replace(prepared, allowed_event_ids=<過濾後 frozenset>)
      # **禁** prepared.allowed_event_ids = ...（frozen 下 TypeError）
      # hash 與 prepared_token **原樣攜帶**（無 __post_init__ ⇒ replace 不會重算）

  # _run_analysis 事件分支：
  # 匯入 validation 通過後、prepare 前：建構一次 timeframe_seconds（鍵集滿足 (d-3a)）
  prepared0 = prepare_analysis_windows(
      records, bars_by_tf,
      event_label_spec=event_label_spec,
      event_import_id=event_import_id,
      lookahead_bars_declared=lookahead_bars_declared,
      timeframe_seconds=timeframe_seconds)  # spy: call_count == 1
  # 3a：time_range 唯一來源＝Task 7.7 ① 具名物（禁 feature_run_manifest／feature_run_time_range）
  # <Task 7.7 picker 所選 run_id> 之表達式權威在 Task 7.7；本草圖不發明第三名
  run_info = _browse_metadata_for_run(<Task 7.7 picker 所選 run_id>)  # -> RunInfo
  feature_manifest_time_range = run_info.time_range  # Optional[dict] 同形；禁轉型別
  check_feature_run_coverage(
      timeframe_seconds=timeframe_seconds,
      feature_manifest_time_range=feature_manifest_time_range,
      event_windows=prepared0.windows)
  prepared1 = apply_event_coverage(prepared0, ...)   # 新身分、同 token 同 hash
  # manifest／split／materialize／ic_feed **只**吃 prepared1
  ```
  🔴 **`ERRATA-R31-C`——上列草圖之呼叫行**：原文在**呼叫**位置寫裸 `*`，為非法 Python
  （`compile()` → `SyntaxError: iterable argument unpacking follows keyword argument unpacking`；
  CODEX-R31-P1-04／COMPOSER-R31-P1-04 同時提出）。**本 ERRATA 不重貼該非法字面**
  （R32 三家一致：引用反例會被字面對證工具算成落地，本身即一條自傷）。本條有兩份補丁包：
  COMPOSER `r31-prepare-call-fix` 之 AFTER **與其自附之 VERIFY 字串**皆仍為同一非法形，
  主委實跑 `compile()` 兩者**皆 SyntaxError**，即該包之 VERIFY 為假綠；
  CODEX `r31-codex-prepare-call` 之 SHAPE 明寫「四個明確 keyword assignment」且
  NEGATIVE_MUTATION 明列「bare `*`」須紅。⇒ **採 CODEX 版**（機器可導出，非偏好）。
  落地後對 SPEC 現存字面實跑 `compile()` → **rc=0**；**R32 三家一致判本擇取未越權**。
  🔴 **`ERRATA-R32-C`**：R32 另查出 Task 7.0b ① 之**權威簽章塊**當時仍為同一非法形，
  與已修正之編排草圖分裂（COMPOSER-R32-P1-01）⇒ 依 `r32-prepare-signature-fix` 同步改為
  明確 keyword 形式。⚠️ **主委具名保留一點疑義（R33 裁）**：該塊之標題寫「簽章如下」，
  而所採 AFTER 為**呼叫形式**（`名=值`），在簽章語境下 `=` 會被讀成預設值；
  主委**無競爭補丁包可依**，故照套未改寫，請 R33 確認此形式是否正確。
  - `event_label_spec` ＝ `{horizon_bars, entry_price_semantic, label_return_mode,
    decision_offset_bars}`；`supported` 由 §F-1′ 判定，偏離 ⇒ F-2′ 之 reason。
  - **禁止**自行實作報酬公式：`windows` 與 `label_value` 一律由既有 `align_events`
    產生（receipt：`alignment.py:152-172` 已由 `label_definition.window.horizon_bars`／
    `label_return_mode`／`entry_price_semantic`／`decision_offset_bars` 導出四個時間戳）。
  - 呼叫前先建**分析用副本**：把 `event_label_spec` 之四值覆寫到記錄副本之對應欄
    （in-memory；**不回寫**匯出檔／已落檔事件批），覆寫規則之權威在 §D-7 之 R8 增訂。
  - bars 一律經 `bars_from_kline_cache`（服務端取 bars 唯一入口，`pipeline.py:77-81`）；
    取不到 bars ⇒ `supported=False`、reason 走既有 capability unavailable 路徑。
  - 尾端不足 ⇒ 該 event 之 `label_value` 為 `None` 且**不進 IC**（loud），**禁填 0**。

  **② transport：折進既有 IC analyze，不另開端點**
  🔴 **主委裁決點（三份補丁包提出三種 transport，互斥）**：
  - `-arch-shift.md`：`POST /api/v1/ic/event-label-values`（前端先取 `label_values` 再送分析）
  - `-arch-analyze-time-label.md`：`POST /api/v1/event-batches/{id}/conditional-ic`
  - `-codex-analysis-label.md` ＋ `-codex-pit-wiring.md`：**不另開端點**，於
    `ICAnalyzeRequest` 增 `event_import_id` ＋ `event_label_spec`，
    由 `ic_analysis_service._run_analysis` 於服務端呼叫 producer
    （兩份補丁包之 SYNC-LOCI 皆列 `api/models/ic_models.py#ICAnalyzeRequest`
    與 `api/services/ic_analysis_service.py#_run_analysis`）。

  **裁決：採第三種（折進 IC analyze）。理由為正確性，非偏好**：
  前兩種讓 `label_value` 經前端往返一趟 ⇒ 前端可能以 `h=3` 取得 `label_values`
  卻以 `h=7` 送出分析，**purge 與 label 分屬不同 h**，正是 **§D-3′-a（iii）五階段**
  （prepare-windows 須先於 coverage／split／labels，且三者讀同一分析時 receipt）要根除者；
  該五階段必須**在同一次分析內原子完成**，跨請求即無法保證。
  （階段清單之權威在 §D-3′-a（iii）；本段不重述、不引用 R8 三步字面
  ——GROK-R10-P1-01：R9 版此處殘留「§D-3a 明訂①②③」，是 R9 宣稱已消除之第二份階段副本。）
  `-arch-shift.md` 自身亦允許「或**同函式之服務端呼叫**」⇒ 本裁決在其容許範圍內。
  ⇒ **不採**任何獨立 `label-values` 端點；前端**不得**持有或傳送 `label_value`。

  **③ 契約欄位（先改契約，D-6）**
  - `ICAnalyzeRequest` 新增 `event_import_id: Optional[str]` 與
    `event_label_spec: Optional[dict]`（欄集恰為 ① 所列四鍵）。
  - `event_label_spec` 存在而 `event_import_id` 缺 ⇒ `400`；反之（只給 import_id）
    ⇒ **報酬語意三元組**以該批之匯出宣告值為初始值（F-0 之三鍵）；
    🔴 **`horizon_bars` 缺省為字面常數 `1`**（GROK-R9-P1-03；本批不做 session 記憶）。
    **禁止**以匯出檔／已落檔批之 `label_definition.window.horizon_bars` 種子化分析用 `h`
    ——§D-3′-a 已裁定該欄語意為 D-7 深度宣告、**分析層禁止讀為答案窗**；
    既有批之該欄殘值為 `3`，種子化即等於靜默給錯預設答案窗。
  - 🔴 現況 `event_import_id` **只存在於前端 config**、從未送到後端
    （receipt：`ICConfigPanel.tsx:275-277` 寫入 config；`useICAnalysis.ts:283-286`
    只送 `event_timestamps`）⇒ 本 Task 一併補此 wiring。
  - 🔴 **R10 明列 wiring 落點（CODEX-R10-P1-04；只寫「逐字實作」不足以避免 bypass）**：
    (a) `api/services/ic_analysis_service.py::_run_analysis` 之事件分支——
        以 `request.event_import_id` **查出該批已落檔 records**
        🔴 **R27 定義 `records` 之 normalized shape（CODEX-R27-P1-02）**：
        本處為 `records` **首次取得之落點**，此後全 SPEC 之規範性讀取**一律採同一存取法**。
        · **shape**：`tuple[Mapping[str, Any], ...]`，每列**至少**含
          `event_id`／`symbol`／`timeframe`／`t0`；**鍵集由契約 `required_fields` 決定**
          （receipt：`event_import_contract.json`；`t0_ms` 屬 alignment 後 `event_level`／`WindowRow`，**非**本集合之鍵）。
        · **存取法**：一律 `r["timeframe"]` 之 **key access**；
          🔴 **禁**同一物件在 SPEC 內時而 `r.timeframe`、時而 `r["timeframe"]`
          ——R26 主委即因此寫出 `set(e.timeframe for r in records)` 之不可執行式。
        · **alignment 失敗不改變本集合**：`records` 於**對齊之前**取得並固化，
          故 pre-coverage TF keyset 不隨對齊結果變動（維持 R11 之 P0 不變式）。
        （🔴 R11：此處取得之 records **即**後續唯一資料來源；coverage 之過濾結果
        寫回 `PreparedAnalysisWindows.allowed_event_ids`，manifest／split／materialize／
        `ic_feed` 一律只吃過濾後之 (events, receipts) **配對**，不得只濾其一）（現行只傳
        `event_timestamps`，`:229-237`）；
    (b) 🔴 **coverage 之插入點與輸出，R11 定死（CODEX-R11-P0-04）**——
        R10 版只寫「插在 split 之前」，實作者仍可放在 `build_event_manifest` **之後**、
        或**只過濾 events 而不過濾 receipt** ⇒ manifest／assignments／IC feed 之
        event-id 集合不一致，或 manifest 已含被拒列（stale rows）。
        現行鏈為 `validate → align_events → build_event_manifest → split_events → materialize`
        （`pipeline.py:187-204`），**manifest 建在 aligned 之上、split 只吃 manifest**。
        ⇒ **唯一合法位置＝prepare-windows 之後、`build_event_manifest` 之前**。
        coverage 以 `apply_event_coverage()` **回傳新的** `PreparedAnalysisWindows`
        （`dataclasses.replace` 之 `allowed_event_ids`；**禁原地寫入**，見 Task 7.0b ① 之 R12 修正）；
        **此後 manifest／split／materialize／`ic_feed` 一律只吃該集合過濾後之
        (events, receipts) 配對**——兩者須**同時**過濾，不得只濾其一。
        `allowed_event_ids` 為空 ⇒ 走既有 loud／`capability unavailable` 路徑，不得靜默出空表。
        驗收：⑭（見下）以 id-set 相等與 stale-manifest mutation 對證。
    (c) `split_events` 之呼叫改傳 **`EventSplitConfig.embargo_ms_by_symbol = project_purge(prepared1.purge_lower_bound_ms_by_symbol)`**
        （🔴 R16 具名：原只寫欄名未具名投影函式，實作者會自行發明取值路徑；唯一合法取值即此式，權威定義在 §D-3′-a（ii））
        （欄名、互斥與 fail-closed 規則之權威在 §D-3′-a（ii），本欄不重述）；
    (d) `momentum/Analysis/event_samples/types.py::AlignmentReceipts` 增
        `analysis_alignment_receipt_hash` 欄（現僅 `event_level`／`per_tf` 兩個 DataFrame）。
    ⚠️ (a)–(d) 皆為**實作階段**之改動；本 Task 只定義其契約與順序。

  **④ 執行順序與 purge（§D-3′-a（iii）五階段之落地點）**
  `_run_analysis` 之事件分支**逐字實作 §D-3′-a（iii）之五階段**，本欄不重述階段清單。
  purge 下界取 **§D-3′-a（ii）之 `purge_lower_bound_ms(scope)`**（本欄不重述公式）。
  **禁止**沿用匯入檔之 `label_end_ms − label_start_ms` 當 embargo。
  🔴 **R9 改寫**：R8 版此欄自寫「①②③④」四步，與 §D-3a 之三步**又是第二份副本**，
  且同樣未定義②所用之 window 來源（CODEX-R9-P0-01）⇒ 改為純引用。

- 驗證（pytest 兩組 ＋ vitest 兩組，逐條如下）：
  `pytest tests/momentum/event_samples/ -q -k analysis_label_producer` ≥7 條——
  ①F-1′ 內（`trigger_close`／`close_to_close`／`k=0`）⇒ `supported is True` 且
    `label_values[eid] ==` 手算之 `(close[t0+h]-close[t0])/close[t0]`（long，`atol=0`）
  ②同上 short ⇒ 值為①之相反數（`== -x`，`atol=0`）
  ③`entry_price_semantic='next_open'` ⇒ `supported is False`、`label_values == {}`
  ④`decision_offset_bars=3` ⇒ 同③；且該 eid 之 `WindowRow.decision_at_ms` `<` `t0`
    （🔴 R15：`windows` 為 tuple，**不得**用 `windows[eid][...]` 之 dict API）
    （證明 k 之映射確實生效，而非被忽略）
  ⑤`label_return_mode='open_to_close'` ⇒ 同③
  ⑥同一批以 `h=3` 與 `h=7` 各跑一次 ⇒ event id 集合**相同**、
    `label_values` **不相同**、各 `WindowRow.label_end_ms` 各自對應自己的 h
    （🔴 R15：同上，禁 `windows[*][...]`）
  ⑦尾端不足 ⇒ 該 eid 之 `label_value is None` 且**不出現**於餵給 `ic_feed` 之輸入
    （斷言 `ic_feed` 輸入之鍵集不含該 eid；**非**填 0）
  `pytest tests/api -q -k event_analysis_horizon_purge` ≥5 條——
  ⑧`h=7` **不得**沿用 `h=1` 之 labels／split；`split purge >=` 本次 label end
  ⑨purge 下界 `==` §D-3′-a（ii）之 `purge_lower_bound_ms(scope)`（R10 擴為五組 fixture）
  ⑨(h) 🔴 **R31（GROK；保 per-symbol ==，刪 dangling 名）**：
      在既有 mixed-alignment fixture 中，**對每個 symbol scope** 斷言
      餵入 `purge_lower_bound_ms` 之 event_id 集合
      `== {w.event_id for w in prepared0.windows if w.symbol == scope}`
      （`WindowRow.symbol` 見欄集；右側即 scope 之定義域）；
      且 alignment-failure `event_id` **不得**出現在 split assignments。
      **mutation**：把 failure row 餵入 purge／split，或使某 scope 之餵入集為右側真子集
      ⇒ `exit != 0`。
      （(d-3a) 三側鍵集相等仍只在 §G G-3 ⑥(d-3a)；本條不重述。）
      🔴 **R31（COMPOSER 表態）**：同意 per-symbol 形式；理由見 R29 codex 碼證
      `event_split.py:54-61`；「per-symbol 嚴格蘊含全域」成立。
      🔴 **主委之擇取理由（`ERRATA-R31-A`；依使用者工作方法「補丁包互相矛盾時在具體提案之間
      裁決並把理由寫進 SPEC」）**：本條有兩份互斥補丁包——GROK `r31-purge-scope-ids`
      主張**刪除**該 dangling 名並改用既有 `purge_lower_bound_ms` 之餵入集；
      COMPOSER `r31-purge-scope-define` 主張在 §D-3′-a（ii）**新增一個具名輔助函式**
      （其名稱與簽章見該補丁包，本檔不複述）。**採 GROK 版**，兩個理由皆非偏好：
      ① 方向面 codex＋grok 兩家一致（CODEX-R31-P1-02 明寫「不新增 dangling helper」）；
      ② composer 版須新建一個具名物，落在 R20「停止新建驗收機制」之疑義面，grok 版只用既有物。
      ⚠️ **composer 未見此擇取即交件** ⇒ 具名保留其異議，**R32 請 composer 確認或推翻**。
    （深度與窗寬**皆已換算 ms**；公式之唯一定義在 §D-3′-a（ii），本欄不重述）。
    fixture 須涵蓋**五組**，證明各維度都可能是勝者且換算逐列：
    (a)「深度 12、h=3」⇒ 深度側勝　(b)「深度 1、h=7」⇒ 窗寬側勝
    (c) **bar 命名欄之混 TF**：同批混 1h 與 12h 各一列（同 symbol）、條件用
        `future_4bar_return` ⇒ 兩列之 `lookahead_depth_ms` **相差 12 倍**，
        斷言用**該列** `timeframe` 換算，而非批內 max／min tf
    (e) 🔴 **小時命名欄之混 TF**（CODEX-R10-P0-01）——
        **共用 §G G-3 條 5(b) 之同一份具名 fixture `fixtures/hour_named_mixed_tf.json`**
        （R12 更正：原寫「鏡像」，兩份會漂移）：同批混 1h 與 12h 各一列（同 symbol）、
        條件用**同一個** `future72_max_drawdown` ⇒ 兩列之 `lookahead_depth_ms`
        **完全相等**（皆 72 小時），而兩列之 `lookahead_bars_declared[tf]` **不相等**。
        本條與 (c) 互為對照：**只有 (c) 會通過「批次 scalar 深度 × 逐列 tf」之錯誤實作，
        (e) 不會** ⇒ 缺 (e) 則 R9 之錯誤換算式可假綠通過。
    (d) **兩個 symbol、各自窗寬不同** ⇒ 斷言 purge 下界**逐 symbol 各自成立**；
        小窗 symbol 之實際 purge `>=` 其自身下界，且**未被**大窗 symbol 之值抬高
        （證偽「全批單一 scalar embargo」）
    (f) 🔴 **R16 新建——`project_purge()` 之投影正確性**
        （CODEX-R16-P1-03＋GROK-R16-P1-02；**不改寫 (d) 之本義**）：
        斷言 `dict(split_events 收到之 embargo_ms_by_symbol)
        == {r.symbol: r.purge_lower_bound_ms
            for r in prepared1.purge_lower_bound_ms_by_symbol}`
        （在合法、**無重複 symbol** 之 prepared 上；函式之權威定義在 §D-3′-a（ii））。
        **mutation（三條，皆須紅；🔴 R17 重寫——原兩條仍可假綠）**：
        ① **duplicate case 用 exception oracle，不用等式**：
           以 rows `[('A',100), ('A',200)]` 呼叫 ⇒ **必須 raise**（`ValueError`）。
           🔴 **不得**以「投影結果 == expected dict」判定——expected 若也用 dict 生成式建，
           重複列已被**靜默折疊**，`{'A':200}` 兩邊相等而綠（CODEX-R17-P1-03 之反例）。
        ② **合法 case 用非最大鍵之 exact 等式**：rows `[('A',100), ('B',300)]`，
           把投影某鍵值改成 `max(全部 purge 值)`（即 `A→300`）⇒ 等式紅。
           **兩值必須不同、且被改的是非最大鍵**，否則 mutation 與原值相同而不紅。
        ③ 把 `seen` 檢查整段刪除 ⇒ ① 之 duplicate case 不再 raise ⇒ 紅。
        ⚠️ ⑨(f) 與 ⑨(d) 之語意分離：⑨(f) 驗**投影**（tuple → Mapping 之邊界），
        ⑨(d) 驗**逐 symbol 窗寬**（證偽全批單一 scalar）；兩者不得互相取代。
        🔴 **本條之出處＝原掛 (d) 不可證偽**：(d) 之 fixture symbol 唯一，
        grok probe 實跑 `D2_unique_take_max_equals_exact True`
        ——取 max 與 exact 投影在唯一 symbol 下位元組相同 ⇒ 該 mutation 不紅。
  ⑩🔴 **分析時 receipt 之唯一性（§D-3′-a（iii））**：同一次分析中，
    **3a（Task 7.7 feature-run gate）**、split 之 purge、餵 `ic_feed` 之 labels **三者所用之
    （🔴 R14 修正：R13 已拆 3a／3b，此處原寫「Task 7.7 之 coverage」會把 **event-id 過濾**
    誤接到 3a——3a 是批次級 pass/fail、不產生 event-id 子集）
    `label_start_ms`／`label_end_ms`／`decision_at_ms` 逐列位元組相同**，
    **且三處讀到之 `analysis_alignment_receipt_hash` 為同一值**（R11 另加 `prepared_token` 同值）
    （該欄之產生點、hash 輸入與序列化規則之權威在 §D-3′-a（iii），本欄不重述）；
    且該 receipt **不等於**匯入檔之對應值
    （以 `decision_offset_bars=3`、匯入 `window.horizon_bars=3`、分析 h=7 之 fixture 驗）
    ⚠️ **兩條斷言互為補強、不可互相取代**：逐列位元組相同擋「值不同」，
    hash 相同擋「各自重算出巧合相同之值」。
    🔴 **R11 補第三條（CODEX-R11-P0-03／GROK-R11-P1-05）**：hash 是**決定性**的，
    三個 consumer 各自呼叫一次 prepare 也會得到相同 hash ⇒ 前兩條**擋不住重入**。
    ⇒ 另斷言 **single-pass**：
    (i) 以 spy／`patch(..., wraps=...)` 包住 `prepare_analysis_windows`，
        一次 `_run_analysis` 之 `call_count == 1`；
    (ii′) 🔴 **R12 取代原「三個 consumer `is` 同一物件」**（該條與 frozen 互斥，見上）：
        `prepared0 is not prepared1`（證明走 `dataclasses.replace`、**非**原地突變）
        且 `prepared0.prepared_token == prepared1.prepared_token`
        且 `prepared0.analysis_alignment_receipt_hash == prepared1.analysis_alignment_receipt_hash`；
    (ii″) manifest／split／materialize／`ic_feed` 四處收到之物件**皆 `is prepared1`**
        （coverage **之後**之單一物件；身分，非值）；
    (iii) 該四處讀到之 `prepared_token` 同值（token 非決定性 ⇒ 重入必不同值）；
    (iv) 🔴 **spec 綁定**（CODEX-R12-P1-05）：以 `h=7` prepare、再以 `h=3` 呼叫 resolve
        ⇒ **fail-closed**（比對 `prepared.normalized_spec_bytes`，**逐位元組**；
        🔴 R14 修正：R13 已改名為 `_bytes`，此處殘留幽靈欄名）；
        `h=7` prepare ＋ `h=7` resolve ⇒ 通過（正例對照）；
    (v) 🔴 **per-TF 單一讀取路徑**（CODEX-R12-P1-02；**R13 修正斷言方式**，
        COMPOSER-R13：G-3 是 golden／pytest 層、Task 7.7 是 API 層、`ic_feed` 是 momentum 層
        ——**跨層要求 `is` 同一 tuple 不可實作，也不該成為規格要求**）：
        改為**值相等 ＋ 來源可追**：三處讀到之 per-TF 內容
        **逐列位元組相同**，且各自所屬之 `analysis_alignment_receipt_hash` **同值**；
        另斷言三處**皆未**呼叫 `align_events`（spy `call_count == 0`），
        以此證明沒有旁讀未綁定之 `AlignmentReceipts`、也沒有各自重算。
    **mutation（三條，皆須紅）**：在任一 consumer 內改為自行呼叫 prepare ⇒ (i)(iii)；
    coverage 改為原地賦值 ⇒ 直接 `TypeError`（frozen），(ii′) 紅；
    coverage 回傳全新建構之物件（未帶原 token／hash）⇒ (ii′) 紅。
  ⑪`event_label_spec` 存在而 `event_import_id` 缺 ⇒ `400`
  ⑫`event_import_id` 確實由前端送達後端（`npx vitest run icEventAnalysisRequest` ≥3 條：
    選批後送出之 payload 含 `event_import_id` 與 `event_label_spec`；
    且**只給 import_id 時** `event_label_spec.horizon_bars === 1`（非匯出之深度欄值））
  ⑭🔴 **coverage 過濾之配對一致性（R11；CODEX-R11-P0-04）**：
    以「兩列被 coverage 拒、其餘放行」之 fixture 驗——
    (a) `manifest.table` 之 `event_id` 集合 **集合相等**於 `allowed_event_ids`；
    (b) `split_events` 之 assignments ＋ purge 兩者之 `event_id` 聯集 ⊆ `allowed_event_ids`；
    (c) 餵 `ic_feed` 之鍵集 ⊆ `allowed_event_ids`；
    (d) `allowed_event_ids` 為空 ⇒ `capability_status == "unavailable"`（loud），**非**空表
    (e) 🔴 **prepare 之初值為全集**（COMPOSER-R12 命中「初值未定 ⇒ 空集 vs 全集不可區分」）：
        `prepared0.allowed_event_ids == frozenset(r.event_id for r in prepared0.windows)`；
        （🔴 R14 修正：R13 已把 `.windows` 定為 tuple，`.keys()` 不可執行）
        coverage 未剔除任何列時 `prepared1.allowed_event_ids == prepared0.allowed_event_ids`
    (f) 🔴 **R13 修正之判準**（CODEX-R13＋GROK-R13 兩家：R12 版之「purge 不因剔除而改變」
        與（ii）式「對 scope 內事件取 max」**互斥**，因剔除後 max 當然會變）：
        purge 下界之輸入已固定為 **pre-coverage 事件集合**，且於階段 2 末算出
        `purge_lower_bound_ms_by_symbol` 隨 receipt 攜帶（見 §D-3′-a（iii）階段 4 之 R13 修正）
        ⇒ 本條之斷言改為：`prepared0.purge_lower_bound_ms_by_symbol
        == prepared1.purge_lower_bound_ms_by_symbol`（coverage 前後**同一 tuple 之列／值相等**），
        且 split 實際採用之 `embargo_ms_by_symbol`
        **讀自 `project_purge(prepared1.purge_lower_bound_ms_by_symbol)` 之投影**、不重算。
        （🔴 R16：R15 宣稱群集 E 已閉，但本條本體未同步——三家全員命中，歸類 (R) 回歸）
        ⚠️ 此為**刻意之保守偏差**：purge 以未過濾集合為準，可能略寬於「只看倖存列」，依 §C0 接受。
    (g) 🔴 **coverage 剔除某 TF 之全部列後，`lookahead_bars_declared` 之鍵集不變**
        （CODEX-R12-P1-04＋COMPOSER＋GROK-R12-P1-02 **三家全員**：
        §D-3′-a（ii）雖已寫死此規則，但**無任何 fixture 或 mutation 證偽「coverage 後重建鍵集」**
        ⇒ 實作者在 coverage 後由 surviving rows 重建，現有測試全綠）：
        以「批內 1h 與 12h，12h 之列被 coverage **全數**剔除」之 fixture 驗——
        `set(lookahead_bars_declared)` 於 coverage 前後**相等**（仍含 `'12h'`），
        （🔴 **R14 刪除原「且 `purge_lower_bound_ms(scope)` 之值不因該剔除而改變」半句**
        ——purge 之不變性已由 (f) 以「讀階段 2 之唯讀 tuple」承擔，本條只管**symbol 集合**；
        兩處並列會誘導 Agent 對 surviving scope 重算，兩家命中）
    **mutation（四條，皆須紅）**：coverage 只濾 events 不濾 receipts ⇒ (a)；
    coverage 移到 `build_event_manifest` 之後 ⇒ (a)；
    prepare 之初值改為空集 ⇒ (e)；
    **coverage 後由 surviving rows 重建 `lookahead_bars_declared` ⇒ (g)**；
    🔴 **purge 下界改在階段 4 由 post-coverage 集合重算
    （而非讀階段 2 之 tuple／`project_purge` 投影）⇒ (f)**。
  ⑬🔴 **前端不得持有 `label_value`**：斷言
    `grep -cE "label_value" frontend/src/lib/eventExport.ts` `== 0` 且
    `grep -cE "label_value" frontend/src/hooks/useICAnalysis.ts` `== 0`
  **mutation（十二條，皆須紅）**：`supported` 恆真 ⇒ ③；short 不取負 ⇒ ②；
  purge 改回沿用匯入值 ⇒ ⑧；把 ms 換算改成批內 max tf 或固定 run tf ⇒ ⑨(c)；
  🔴 **把 `lookahead_bars_declared` 塌成批次 scalar 再乘逐列 tf ⇒ ⑨(e)**
  （此即 R9 版之錯誤實作，本條為其回歸樁）；
  purge 下界改成全批單一 scalar ⇒ ⑨(d)；深度與窗寬直接 `max` 而不換算 ⇒ ⑨(a)；
  🔴 **`embargo_ms=None` 並把深度折進 label 窗 ⇒ ⑨(a) 紅且 §G G-3 ② 之 `label_end_ms`
  偏離手算 h 窗而紅**（R9 之已廢選項②之回歸樁）；
  coverage 或 split 改讀匯入檔舊 receipt ⇒ ⑩；
  🔴 **materialize 階段重跑 `align_events`（而非吃階段 2 之產物）⇒ ⑩之 hash 不等而紅**；
  尾端不足改填 0 ⇒ ⑦；在 TS 重寫一份公式 ⇒ ⑬。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **取代** R7 版之匯出端 producer（刻意；見上「REOPEN」）。
  **須同步**：§F-5′ 若日後開放更多三元組，只需擴充本函式之支援矩陣與 §G G-3 之 golden，
  **不得**在前端或匯出層另開分支；Task 7.6 之分析參數 UI 與本 Task 之 `event_label_spec`
  為**同一組欄位**，欄位增減須同批改。
- 邊界：只在分析時判定與換算 `label_value` 與其 window；不改 `event_id`、
  不回寫任何已落檔之事件批、不改契約其他欄位。
- 不可做：不得在不支援之組合下回傳任何非 `None` 之 `label_value`（§F-2′）；
  不得讓前端持有、推導或傳送 `label_value`（§F-4′）；
  不得為「省一次計算」而快取上一次 h 之 labels 給不同 h 之分析使用。

**原版與撤回理由（R7 版，保留不得刪）**：
R7 版定義 `resolve_label_value(case, *, ...)` 單列函式 ＋ `POST /api/v1/case/label-values`，
request 之 `cases` 為 `/search` 之結果列，前端呼叫點為 `buildEventContractRecords`，
並要求「`buildEventContractRecords` **只得**由本端點取 `label_value`」。
**撤回理由**：該設計把 producer 綁在**匯出**生命週期上，而 §D-3′ 裁定答案窗屬分析層
⇒ 匯出時根本還不知道使用者要用哪個 h，端點的 `horizon_bars` 參數無來源。
R7 版之驗收⑥（reason 取自 `import_failure_reasons`）亦隨 F-2′ 之登記處改變而作廢。

**Task 7.1 — 五維度全部接出前端（依賴 Task 7.0）**
- 內容：`/search` 匯出面板與 `/data-preparation` 匯入表單各提供五個維度之選擇；
  每個選項旁附白話說明（取自契約 `doc` 欄，不另寫）。預設值維持現行以免既有流程改變，
  但**必須可見可改**。
  🔴 **可選集合之定義（R4 群集 A＋D）**：
  `selectable(path, dim) = accepted(dim) − pathExclusions(path, dim)`
  - `accepted(dim)` ＝ 契約之 `accepted` 鍵；無該鍵者取 `enum` 全集。
    （`control_kind`：`enum` 4 值、`accepted` 3 值，`platform_random_bars` 恆拒。）
  - `pathExclusions` ＝ **前端單一具名常數**（如 `EVENT_DIM_PATH_EXCLUSIONS`），
    每筆須帶**非空理由字串**。**本批之封閉內容**（R5 群集 F／H 擴充後）：
    ```
    ('/search',      'scenario',             { A, B, two_stage })   # 皆無獨立 label producer
    ('/search',      'entry_price_semantic', { trigger_open, next_open, decision_bar_open, decision_bar_close })
    ('/search',      'label_return_mode',    { open_to_close, open_to_horizon_close })
    ('/ic-analysis', 'entry_price_semantic', { trigger_open, next_open, decision_bar_open, decision_bar_close })
    ('/ic-analysis', 'label_return_mode',    { open_to_close, open_to_horizon_close })
    ```
    ⇒ `/search` 之 `scenario` 只開 `C`；`entry_price_semantic` 只開 `trigger_close`；
    `label_return_mode` 只開 `close_to_close`——恰為 §F-1′ 之支援矩陣。
    `decision_offset_bars` 非 enum，於 `/search` 與 `/ic-analysis` 之可輸入範圍均鎖定為 `0`（見 §F-1′）。
    🔴 **新增 `/ic-analysis` 列之理由**：§D-3′ 後三元組之控制項移到 IC 分析頁
    （Task 7.6 ③），該處之可操作集合須與 §F-1′ 一致 ⇒ 沿用**同一具名常數**，
    **不另建第二份排除清單**（另建即第二份副本）。
    🔴 **`/search` 各列之理由字串須隨 §F-0 更新**：原理由為「匯出端會寫 `label_value`，
    偏離即假語意」；匯出端已不寫 `label_value` ⇒ 新理由為
    「該值宣告後，分析層本批不支援以其計算 `label_value`（§F-5′）⇒ 該批將無法做條件 IC」。
    依 §C0「只能更嚴」**保留**排除，只改理由字串。
    ⇒ 排除是**封閉可列舉集合**，不是散落在元件裡的 if；新增或移除排除須改該常數並同步本 SPEC。
  - 兩類**不可選**值之 UI 呈現不同、須分別顯示：契約恆拒者顯示契約之 `rejected_with_reason`
    字面；路徑排除者顯示 `pathExclusions` 之理由字串。兩者皆 **disabled 且不計入 selectable**。
- 驗證：`npx vitest run eventContractOptions` ≥10 條——
  ①~⑤每維度各一條，斷言「**可操作**（非 disabled）之 UI 選項集合 `==` `selectable(path, dim)`」
    （`accepted` 由契約導出、排除由具名常數導出，**兩者皆非硬編碼清單**）
  ⑦`control_kind` 之 disabled 選項存在且其 title/aria 含 `not_implemented_platform_random_bars`
  ⑧`/search` 之 `scenario` 之 `A`／`B`／**`two_stage`** 三者皆為 disabled 且顯示排除理由；
    同一維度在 `/data-preparation` 之 selectable `==` 全部 4 值（證明限制**只在該路徑**）
  ⑨`EVENT_DIM_PATH_EXCLUSIONS` 之每個理由字串 `!== ''`，且該常數之內容**集合相等**於
    ```
    {('/search','scenario'):                 {A, B, two_stage},
     ('/search','entry_price_semantic'):     {trigger_open, next_open, decision_bar_open, decision_bar_close},
     ('/search','label_return_mode'):        {open_to_close, open_to_horizon_close},
     ('/ic-analysis','entry_price_semantic'):{trigger_open, next_open, decision_bar_open, decision_bar_close},
     ('/ic-analysis','label_return_mode'):   {open_to_close, open_to_horizon_close}}
    ```
    🔴 **以集合相等斷言，不用計數字面**（理由見本 Task 覆蓋風險）
  ⑩**五維度全部維持預設 ⇒ G-2 事件 golden byte 級不變**（證明接出 UI 本身不動數值）
  ＋`npm run build` rc=0。
  **mutation**：把 `pathExclusions` 清空 ⇒ ⑧須紅；把排除改成寫在元件內的 if ⇒ ⑨須紅。
- 存活至：Phase 7（終）。
- 覆蓋風險：Phase 7 為最後一個 Phase，本 Task 純新增 UI 控制項且「內容」已鎖預設值維持現行
  ⇒ 無後續 Phase 覆蓋。**須同步**：本 Task 讓 `entry_price_semantic`／`decision_offset_bars`／
  `label_return_mode` 之實際取值面由單一寫死值擴為 enum 全集，而這三者**直接改變報酬數字**
  （見本 Phase 前言「數值影響」）⇒ 驗收須含一條「五維度全部維持預設 ⇒ G-2 事件 golden **byte 級
  不變**」之回歸，證明**接出 UI 這件事本身不動任何數值**；使用者主動改動預設值所導致之 golden
  改變，屬 D-4 之合法數值輸出變更，須在 commit message 說明，不得靜默重凍。
- 覆蓋風險（R6 群集 A 追記）：驗收⑨改以**集合相等**斷言之理由——R4 版寫「該常數之筆數
  `=== 1`」，主委依 consult 群集 F／H 把該常數擴為三筆時**未同步該計數字面**，
  COMPOSER-R6-P1-01 與 GROK-R6-P0-01 兩家獨立命中。**計數字面會隨擴充而漂，集合相等不會**
  ⇒ 本 SPEC 一律優先用集合相等；殘存之計數字面由 `scripts/spec_count_audit.py` 稽核。
- 邊界：只接出既有能力；**不新增**任何後端未支援之值。
  🔴 **`scenario` 之路徑級限制（R4 群集 D；R5 群集 H 收緊）**：
  `/search` 匯出路徑本批**只可選 `C`**；`A`／`B`／**`two_stage`** 於該路徑 disabled 並顯示理由
  （R5 更正：R4 版放行 `two_stage`，但 `two_stage_search.py` 合併後同樣只有 t0 之 `positive_case`、
  **無兩段式 producer 與 provenance**，與 A／B 是同一個問題；三家一致指出，已收緊）
  「此路徑之 `label` 由 t0 條件產生（`eventExport.ts:75-85` 以 `positive_case` 判定），
  A／B 為預測型、事件在未來，需獨立之 label producer 與 provenance，**本批未交付**」。
  `/data-preparation` 之 **CSV 匯入路徑四種全開**（label 由使用者自帶，系統只照抄）。
  ⇒ 這是**路徑級**限制，不是把系統寫死於單一 scenario——後者為使用者 2026-08-22 明令禁止者。
  未加此限制時，使用者選 A／B 可通過 enum validator，但 `label` 仍是 t0 之 `positive_case`
  ⇒ 契約宣稱預測型、實際是確認型（語意漂移），且 Task 7.3 之動態揭露只會忠實顯示這個錯誤設定。
- 不可做：不得在前端硬寫 enum 清單（必須由契約導出，否則下次加值又漂）；
  不得在未交付 A／B label producer 前於 `/search` 開放 A／B（見「邊界」）。

**Task 7.2 — 機械閘：可操作選項集合 ＝ `selectable(path,dim)`，且選值真的傳到落檔（依賴 Task 7.0／7.1）**
- 內容：新增測試，對五個維度逐一驗**三層**（R4 群集 A：R3 版只驗第一層，三家全員判不足）：
  **① 集合層**——「**可操作**（`disabled === false` 且可 focus）之 UI 選項集合」`==`
    `selectable(path, dim)`（定義見 Task 7.1：`accepted` 減 `pathExclusions`）。
    **disabled／hidden 選項一律不計入**，因此無法以放一個 disabled 的 `platform_random_bars`
    湊足元素數，也無法把 `/search` 之 `A`／`B` 改成 enabled 而不動 `pathExclusions`。
  **② round-trip 層**——每維度選一個**非預設值** → 呼叫 `buildEventContractRecords`
    → 斷言落檔記錄之對應路徑 `===` 所選值。這層才是擋住 B5 病因（「介面有、沒傳」）的那一層；
    只有 ① 時 UI 可以全對而 payload 仍是寫死預設。
  **③ 非 enum 欄**——`decision_offset_bars` 無 enum，驗：有可輸入且非唯讀之控制項、
    輸入 `-1` ⇒ fail-closed（契約 `min: 0`）、輸入 `k` ⇒ 落檔 `decision_offset_bars === k`。
  並禁止 `eventExport.ts` 出現無 UI 對應的寫死值。
- 驗證：`npx vitest run contractEnumWiring` ≥14 條（5×①＋5×②＋2×③＋2×路徑對照：
  同一維度在 `/search` 與 `/data-preparation` 之 selectable 各自成立）；
  ①之斷言為 `new Set(uiEnabledOptions)` 等於 `new Set(selectable(path, dim))`
  且長度相等；
  ②之斷言含巢狀路徑 `records[0].label_definition.label_return_mode === '<非預設值>'`；
  ③之斷言 `records[0].decision_offset_bars === 3` 與 `-1` 之 fail-closed。
  **mutation（四條，皆須紅）**：
  (a) 契約新增第 5 個 `scenario` 值而不改 UI ⇒ ①紅
  (b) 把 `platform_random_bars` 或 `/search` 之 `scenario=A` 改成 enabled 湊數 ⇒ ①紅
      （前者不在 `accepted`，後者被 `pathExclusions` 排除）
  (c) 呼叫端 `page.tsx` 漏傳某維度之 opts ⇒ ②紅
  (d) 把某維度改回寫死 ⇒ ②紅
- 存活至：Phase 7（終）。
- 覆蓋風險：本閘為 Task 7.0／7.1 之防漂移守衛，存活至 Phase 7（終）。
  🔴 比對基準為 `selectable(path,dim)`（定義見 Task 7.1），**非**裸契約 `accepted`——
  其中 `accepted(dim)` 導出自契約檔、`pathExclusions` 導出自具名常數，二者皆非人工清單
  ⇒ 後續任一 Phase 於契約增值時本閘自動變紅，該紅為設計意圖，**不得以更新人工清單消紅**。**須同步**：Task 1.1 於契約新增之 reason 與 `filters` 屬非 enum 型欄位，
  **不在本閘涵蓋面內** ⇒ 本閘只保護五個批次維度、不保護契約全部欄位；此邊界須明寫於實作註解與測試名稱，
  避免日後誤以為「有機械閘＝契約全欄受保護」而略過 Task 1.1 之常數同步（見 Task 1.1 覆蓋風險）。
  另：`accepted` 為契約既有鍵，本 Task **不新增**該鍵到其他維度——只在存在時採用。
  🔴 **R8 邊界追記**：§D-3′ 後 IC 分析頁另有一組**分析參數** UI（Task 7.6 ③），其可操作集合
  由 **Task 7.6 驗收⑤** 守、其常數內容由 **Task 7.1 驗收⑨** 之集合相等守
  ⇒ 本閘**不擴及** `/ic-analysis`，避免同一斷言出現兩份。
  若日後把分析參數也納入本閘，須同時刪除 Task 7.6 ⑤，不得兩處並存。
- 邊界：涵蓋五個批次維度之三層；enum 型走①②、`decision_offset_bars`（`int`, `min: 0`）走②③。
  **不驗**「選了之後後端算出來對不對」——那是 G-2 與各 Phase 自身驗收的事。
- 不可做：**不得以人工清單當比對基準**（那就是第三份副本）。

**Task 7.3 — 動態揭露本批設定（取代原擬之固定文案）**
- 內容：匯出前顯示「本批：scenario＝X／**control_kind＝C**／進場價＝Y／報酬算法＝Z／
  決策位移＝K／lookahead 深度＝N（來源：**使用者宣告**，逐 tf；R 重開 D-8，原「引用欄位清單」已退役）／purge 將為 N 根」，
  **全部由實際設定導出**；深度自 Task 1.9′ 之宣告 state 讀取，**禁**殘留對 `exportFilters`／2.1b map 之讀取。
  🔴 `control_kind` 為 R7 群集 D 補入：Task 4.1b 之覆蓋風險宣稱本 Task 為其**嚴格超集**
  並要求 7.3 上線時移除 4.1b 之獨立實作，但本清單原**漏掉 4.1b 明列之 `control_kind`**
  ⇒ 取代後 UI 反而不再揭露該批 control kind（codex 命中）。
  🔴 **R9 追記（實作形態）**：本 Task 之文案須來自 Task 7.6 內容②所定義之
  **欄位級 formatter registry**（每欄一個 formatter），本頁只選取自己的欄集；
  **不得**寫成硬編欄集之面板級 formatter——IC 分析頁之欄集與本頁不同，
  面板級共用會逼其中一頁多顯示或少顯示欄位。
- 驗證：`npx vitest run eventExportDisclosure` ≥3 條——
  ①改任一維度 ⇒ 顯示字串隨之改變（斷言前後 `!==`）
  ②`control_kind` 顯示值 `==` 匯出檔實際值（防寫死漂移）
  ③本頁與 Task 7.6 取用**同一 registry 物件**（斷言同一 exported 參考），
    且兩頁之欄集**不相等**（證明共用的是 registry 而非欄集）。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task **取代** Phase 4 之 Task 4.1b（後者為其真子集，見 4.1b 之覆蓋風險）；
  Phase 7 為最後一個 Phase ⇒ 本 Task 為本批揭露之終點，無更後續之覆蓋者。**須同步**：本 Task 之
  驗證「改任一維度 ⇒ 顯示字串 `!==` 前值」偵測不到「**新增**維度未被顯示」⇒ 維度涵蓋率由 Task 7.2
  之 enum 對證閘負責；兩者缺一，日後契約新增維度會靜默不揭露，回到 Phase 7 前言所述之病因。
- 邊界：只揭露，不改預設值。
- 不可做：不得寫死任何「正反例由 t0 條件決定」類之 scenario 專屬文案（D-7 通則化）。

**Task 7.4 — 條件 IC decay 之邊界揭露（CODEX-R2-P1-02／GROK-R2-P2-01；R8 依 §D-3′ 改寫措辭）**
- 內容（**R8 依 §D-3′ 改寫措辭；與 Task 4.1c 為同一文案來源，不得各寫一份**）：
  明文標示「條件 IC decay **曲線**（一次分析同時得到多個 h）**非本批交付**；
  附帶之 `future_*` 欄**不進入** `ic_feed`；
  要看不同答案窗，於 **IC 分析頁改答案窗重跑分析**，**不需重新匯出事件批**；
  一次得到整條曲線待 GAP-6。」
- 驗證：`grep -c "IC decay" docs/GAP3_EVENT_UX_SPEC.md` `>= 1`；vitest 斷言該說明現於匯出面板；
  **加驗收**：①選附帶欄 `[1,3,7]` ⇒ `window.horizon_bars` **不變**
  ②本 Task 與 Task 4.1c 之文案來自**同一 exported 常數／formatter**（斷言同一參考）
  ③文案中**不得**出現「重新匯出」作為換 h 之手段。
- 存活至：GAP-6（屆時若交付 multi-horizon IC 則撤除）。
- 覆蓋風險：GAP-6 可能取代。
- 邊界：只揭露邊界。
- 不可做：不得讓使用者以為多選附帶欄就會得到多條 IC。

**Task 7.5 — 事件後報酬表正／反／全體三組（使用者 2026-08-22 指定垂直排列）**
- 內容：報酬表由單一組改為**三組垂直排列**（正例組／反例組／全體組），每組各自跑完所有 horizon。
  🔴 **輸出形狀（R5 群集 C；三家獨立皆選同一掛法）**：回傳頂層仍為 §G S-1 之八鍵；
  三組寫入 `strata.by_label`，鍵集固定恰為 `positive`／`negative`／`all`（定義見 §G S-1a）。
  **不得**新增第九頂層鍵，**不得**以三次呼叫各產一表代替。
  🔴 **`control_kind` 之全體組規則（R5 群集 I；契約 `accepted` 三值全覆蓋）**：
  | `control_kind` | `strata.by_label.all` |
  |---|---|
  | `user_labeled_same_trigger` | **正常計算**（同觸發） |
  | `platform_same_trigger_rule` | **正常計算**（同觸發；R5 前未定義，本批補齊） |
  | `user_labeled_other` | `{"status":"not_computed","reason":"control_kind_not_comparable"}` |
  | 批內 distinct 值 `> 1` | `{"status":"not_computed","reason":"mixed_control_kind_in_batch"}`，**不取多數決** |
  （`platform_random_bars` 由匯入契約先行拒收，不會走到本表。）
  🔴 **兩個 reason 須先登記契約**（R5 群集 I：R4 版新增 `mixed_control_kind_in_batch`
  卻未登記任何 SoT，違反 §C「契約唯一真相源」與 D-6）：於
  `momentum/Analysis/contracts/ic_report_contract.json` 之 `report_sections` 新增
  `event_return_table` 物件，內含
  `not_computed_reasons: ["control_kind_not_comparable","mixed_control_kind_in_batch"]`
  與 `group_status_object_keys: ["status","reason"]`；程式與前端一律由該檔取字面。
  ⚠️ 此為**表格層** reason，**不得**混入 Task 6.0 之 `reasons.analysis_rejected`
  （那是 IC 分析入口之拒絕原因，兩者語意不同）。
  🔴 **`control_kind` 之傳遞點（R4 群集 F；CODEX-R4-P1-06）**：現行資料流**讀不到**該欄——
  `dedupe.py:112-115` 之 manifest context 只 merge
  `event_id,symbol,timeframe,label,scenario,direction`，**無 `control_kind`**；
  `tables.py:88-93` 之 `event_forward_return_table` 亦不收原始事件表。
  ⇒ 本批明定**唯一傳遞點＝`build_event_manifest` 之 manifest context**（於該 merge 清單加入
  `control_kind`），表格層一律由 `manifest.table` 取用。
  **禁止**另建第二份事件索引，也**禁止**在表格層寫死或讀不到時當 `None` 放行。
  **批內多值與 `not_computed` 之形狀**：見上表與 §G **S-7a**（狀態塊恰兩鍵）；
  本 Task **不重述**該形狀（避免第二份副本，同 §V 書寫規則之理由）。
- 驗證：`pytest tests/momentum/event_samples/ -q -k return_table_by_label` ≥10 條——
  ①`set(out.keys())` `==` §G S-1 之八鍵集合（證明三組**沒有**新增第九頂層鍵）
  ②`set(out['strata']['by_label'])` `== {'positive','negative','all'}`（不多不少）
  ③`positive`／`negative` 之列數各 `== len(horizons)`
  ④`control_kind == 'user_labeled_same_trigger'` ⇒ `all` 可算，且
    `positive` n ＋ `negative` n `==` `all` n
  ⑤`control_kind == 'platform_same_trigger_rule'` ⇒ `all` **可算**（本批補齊之第三值）
  ⑥`control_kind == 'user_labeled_other'` ⇒
    `out['strata']['by_label']['all'] == {"status":"not_computed","reason":"control_kind_not_comparable"}`
  ⑦同批混入兩種 `control_kind` ⇒ `all` 之 reason `== 'mixed_control_kind_in_batch'`
  ⑧`control_kind` 確實出現在 `build_event_manifest` 產出之 `manifest.table.columns`
    （斷言 `'control_kind' in manifest.table.columns`）——防「讀不到就當 `None`」
  ⑨兩個 reason 字面取自契約：`python3 -c "import json;c=json.load(open('momentum/Analysis/contracts/ic_report_contract.json'));s=c['report_sections']['event_return_table'];assert s['not_computed_reasons']==['control_kind_not_comparable','mixed_control_kind_in_batch'];assert s['group_status_object_keys']==['status','reason']"` rc=0
  ⑩`positive`／`negative` 兩組之統計值在三種 `control_kind` 下 **byte 級相同**
    （證明 `control_kind` 只影響 `all`）
  ⑪**前端實際顯示三組**（R6 群集 I；全棧三欄稽核產物）：
    `npx vitest run eventTablesPanelByLabel` ≥3 條——`EventTablesPanel` 讀
    `strata.by_label` 之三組並垂直排列；`all` 為 `not_computed` 時顯示其 `reason` 而非空表；
    🔴 現行該元件只讀 `sensitivity_micro` ⇒ 後端通過本 Task 之 pytest 仍會讓前端顯示舊的單一組
    （靜默失效）。**本 Task 之驗收不得只有 backend pytest。**
  **mutation（六條，皆須紅）**：三組提到新頂層鍵 ⇒ ①；`control_kind` 從 manifest merge 清單移除 ⇒ ⑧；
  前端仍讀 `sensitivity_micro` ⇒ ⑪；
  多值時改取多數決 ⇒ ⑦；`not_computed` 改回 `n=0` 空統計塊 ⇒ ⑥；
  把 `platform_same_trigger_rule` 當成 `other` 處理 ⇒ ⑤。
- 存活至：Phase 7（終）。
- 覆蓋風險：與 Task 4.2 同一表格，兩者須合併實作（4.2 先）。**須同步（R5 群集 C 改寫）**：
  本 Task 新增 `strata.by_label` ⇒ 這是**已核准之結構／數值輸出變更（D-4 合法變更）**
  ⇒ **須同一 commit 依 §G S-9 重建 G-2 golden 並在 commit message 說明**，
  且新 golden 須以 §G S-8 之**獨立 oracle** 驗證，不得以被測函式自產。
  ⚠️ 與此**分開**的另一件事：本 Task 於 `dedupe.py` 之 manifest context 加 `control_kind` 欄
  ⇒ 該加欄**不應**改變 G-2 bytes（`manifest` 本身不進輸出）⇒ 仍須保留
  「加欄前後 G-2 byte 級不變」之回歸；若真變了代表加欄意外進了輸出，須查明而非重凍。
  （R4 版只寫了後者、漏了前者，被 GROK-R5-P1-01 指出與 Task 4.2 之 D-4 規則不一致。）
- 邊界：只分組顯示與 `control_kind` 之傳遞；**不改**每組之計算式。
- 不可做：不得因分組而改變 `n_eff` 或 bootstrap 之定義；不得在表格層寫死 `control_kind`。

**Task 7.6 — IC 分析頁：批次事實欄唯讀揭露 ＋ 分析參數可設定（R4 群集 C／遺留 E；R8 依 §D-3′ 改寫；R10 定死事實欄形狀）**

🔴 **R8 改寫之衝突與其解**：R7 版之「邊界」寫「**不允許**在 IC 頁修改批次設定」，
與 §D-3′「答案窗與報酬語意於 IC 分析頁由使用者給定」**直接互斥**。
解法＝**把原本混為一談的「批次設定」拆成兩類**（`-arch-shift.md` 之 Task 7.6 diff 即此意）：

🔴 **R9 再改（CODEX-R9-P1-07＋GROK-R9-P1-02 兩家獨立命中）**：R8 版之「批次事實欄」表列
`direction`／`t0`／`label`，而同 Task 之 detail 驗收鍵集卻是三元組三鍵 ⇒ **同 Task 兩處互斥**，
Agent 無法唯一決定唯讀集合與 `direction` 之歸屬。下表為**三分之權威定義**（封閉集合）：

| 類別 | 欄集合（封閉） | 在 IC 頁 | detail 端點 | 寫回事件批？ |
|---|---|---|---|---|
| **批次事實欄** | `{scenario, control_kind, direction, t0, label}` | **唯讀揭露** | **必須**回傳；驗收①之集合相等對象、驗收③之 DOM 不可編輯對象皆為本集合 | — |
| **批次宣告種子（F-0）** | `{entry_price_semantic, label_return_mode, decision_offset_bars}` | 顯示於分析參數區作為初始值 | 可回傳，但**不計入**「批次事實欄」之集合相等 | — |
| **分析參數**（`event_label_spec`） | `{horizon_bars, entry_price_semantic, label_return_mode, decision_offset_bars}` | **可設定**；三元組初始值＝F-0 種子，`horizon_bars` 初始值＝**常數 `1`** | — | 🔴 **否**——只作用於本次分析用副本 |

🔴 `direction` 歸**批次事實**（它決定 short 取負、是 §G G-3 之 golden input），
**不**進 `event_label_spec`、**不**可在 IC 頁修改。

🔴 **R10：批次事實欄之「形狀」（COMPOSER-R10-P1-02）**——R9 版只寫鍵集，未寫形狀，
而 `t0`／`label` 在落檔記錄是**逐列**欄（`event_id` 即含 `t0`；既有批 780 列），
沒有單一 scalar 語意 ⇒ detail 回應與 IC 頁 formatter 無唯一實作。**定死如下**：

🔴 **R11 定死 wire shape（CODEX-R11-P1-08＋GROK-R11-P1-01 兩家）**：R10 版一邊說
「`t0`／`label` 合成一個 `records` 陣列、元素三鍵」，一邊在驗收①要求
`detail['t0']`／`detail['label']` **各自**是陣列 —— **兩條互斥**，
且 formatter registry 是「每欄一個 formatter」，餵三鍵 records 會讓
t0 formatter 讀得到 label、label formatter 讀得到 t0（欄位語意重疊）。
**採「兩個各自的 typed array」**（不採單一 records 欄）：

| 欄 | 形狀 | detail 回應（wire shape，唯一） |
|---|---|---|
| `scenario`／`control_kind`／`direction` | 批次內**常數**（異質即 Task 1.8 拒收） | **scalar** |
| `t0` | **逐列** | `[{"event_id": str, "t0_ms": int}, …]`，按 `event_id` UTF-8 升冪 |
| `label` | **逐列** | `[{"event_id": str, "label": 0\|1}, …]`，按 `event_id` UTF-8 升冪 |

- 兩陣列之 `event_id` 集合**須相等**且長度＝該批 `n_events`（驗收①(c)）。
- 每個元素之鍵集**恰為該欄自己的兩鍵**——`t0` 之元素**不得**含 `label`，反之亦然。
- **禁止**以 scalar 冒充整批之 `t0`／`label`（例如只回第一列、或回 `min(t0)`）。
- **formatter signature（欄位級 registry 之陣列型欄位）**：
  `format_t0(rows: list[{event_id, t0_ms}]) -> str`、
  `format_label(rows: list[{event_id, label}]) -> str`；
  各自只吃自己那個陣列，**不得**共用一個三鍵 records 輸入。
- IC 頁 formatter 由該陣列**導出摘要**（如 `n_events`、`label` 之 0／1 分佈、t0 之
  首末時間）；**不得**在前端另算一份 `t0` 語意。

- 內容（三件事）：
  ① 事件批 detail 端點回傳該批之**五維度實際值**（既有需求，不變）。
  ② IC 分析頁選批後：**批次事實欄唯讀揭露**，文案與 Task 7.3 之匯出面板揭露
     **共用同一實作**（不另寫第二份）。
     🔴 **共用之粒度為「欄位級」，非「面板級」**（CODEX-R9-P1-07 之衍生要求）：
     兩頁之揭露**欄集不同**（匯出面板揭露五維度＋lookahead＋purge；IC 頁揭露批次事實五欄），
     故共用者為單一 exported **欄位→白話字串** registry
     （每個欄位一個 formatter，值由實際設定導出），各頁只選取自己的欄集。
     🔴 **R11：陣列型欄位之 signature 亦寫死**——`t0`／`label` 各自吃**自己那個兩鍵陣列**
     （`format_t0(rows: list[{event_id, t0_ms}])`／`format_label(rows: list[{event_id, label}])`），
     **不得**共用一個三鍵 records 輸入（否則兩個 formatter 之欄位語意重疊）。
     **不得**寫成兩個各自硬編欄集的面板級 formatter——那正是第二份副本。
  ③ IC 分析頁新增**分析參數區**：`event_label_spec` 之四欄。
     - `horizon_bars`：任意正整數，可自由設定（§F-1′ 不限制 h）；
       🔴 **初始值＝字面常數 `1`**，**禁止**以匯出檔之 `label_definition.window.horizon_bars`
       種子化（該欄語意為 D-7 深度宣告，§D-3′-a 已裁定分析層禁止讀為答案窗）。
     - 報酬語意三元組：本批**可操作集合鎖定 F-1′**，其餘值 disabled ＋顯示
       §F-5′ 之開放前置理由。排除集合沿用 Task 7.1 之 `EVENT_DIM_PATH_EXCLUSIONS`
       （新增路徑鍵 `'/ic-analysis'`），**不另建第二份排除清單**。
     - 🔴 同時揭露 **本次答案窗之可算／缺筆數**（Task 4.3／5.3 由匯出層移來之揭露）。
     - 🔴 同時揭露 **本次 purge 下界**，其式之權威在 §D-3′-a（ii），本區只顯示結果。
- 驗證（pytest 一組 ＋ vitest 一組，逐條如下）：
  `pytest tests/api -q -k event_batch_detail_dims` ≥3 條——
  ①detail 回應之**批次事實欄**鍵集**集合相等**於 `{scenario, control_kind, direction, t0, label}`
    （🔴 **明列鍵名、不用計數字面**；集合之權威在上方三分表）
    🔴 **並驗形狀**（R10；R11 定死）：
    (a) `scenario`／`control_kind`／`direction` 為 scalar；
    (b) `detail['t0']` 與 `detail['label']` 各為**陣列**，
        長度皆 `== 該批 n_events`；`t0` 元素之鍵集**恰為** `{event_id, t0_ms}`、
        `label` 元素之鍵集**恰為** `{event_id, label}`（**互不含對方之欄**）；
    (c) 兩陣列之 `event_id` 集合**相等**，且各自按 `event_id` UTF-8 升冪
  ②detail 回應**另含** F-0 種子三鍵 `{entry_price_semantic, label_return_mode, decision_offset_bars}`，
    且該三鍵**不**計入①之集合相等
  ③各值 `==` 該批落檔記錄之實際值（非預設值）；
    逐列欄以**集合相等**比對 `event_id`，並抽驗任兩列之 `t0_ms`／`label`；
  `npx vitest run icEventBatchDisclosure` ≥7 條——
  ①批次事實欄之各段文字皆出現，且與 Task 7.3 呼叫**同一 exported formatter**
    （斷言為同一函式參考，非各自複製）
  ②改批次之任一事實欄 ⇒ 顯示字串 `!==` 前值
  ③**批次事實欄不可編輯**：斷言其 DOM 節點無可輸入控制項（`queryByRole('combobox'/'textbox')` 為 `null`）
  ④**分析參數可編輯**：`horizon_bars` 有可輸入控制項；輸入 `7` ⇒ 送出 payload 之
    `event_label_spec.horizon_bars === 7`
  ⑤三元組之**可操作**選項集合 `==` §F-1′ 之唯一三元組；其餘值 disabled 且顯示理由
  ⑥**改分析參數不改事件批**：改 `horizon_bars` 後重查 detail 端點，
    該批落檔記錄之 `label_definition.window.horizon_bars` **不變**（證明不回寫）
  ⑦🔴 **`h` 不得由匯出深度欄種子化（GROK-R9-P1-03）**：既有批之
    `label_definition.window.horizon_bars === 3`（深度欄殘值）且使用者**未改**分析參數
    ⇒ 送出 payload 之 `event_label_spec.horizon_bars === 1`（**非** `3`）
  **mutation（五條，皆須紅）**：把揭露文案改成前端寫死 ⇒ ①；
  把批次事實欄改成可編輯 ⇒ ③；三元組開放 F-1′ 以外之值 ⇒ ⑤；
  分析參數回寫事件批 ⇒ ⑥；改回以匯出 `window.horizon_bars` 種子化 `h` ⇒ ⑦。
- 存活至：Phase 7（終）。
- 覆蓋風險（R6 群集 B 追記）：驗收改以**明列鍵名之集合相等**之理由——R4 版寫「detail 回應
  含六個鍵」，R5 群集 G 把批次維度六改五時該字面未同步，**三家全員命中**；
  且因未列鍵名，Agent 無法唯一決定第六鍵，可能把已移出之 `counterexample_kind` 加回。
  🔴 **R8 追記**：本 Task 由「只讀不寫」改為「讀 ＋ 收分析參數」⇒ **確實改動 IC 計算路徑**
  （分析參數餵 Task 7.0b 之 producer）；原「不改任何 IC 計算路徑 ⇒ 無後續 Phase 覆蓋」
  之理由已不成立，改由 Task 7.0b 之驗收⑧⑨⑩承接該路徑之正確性。
  **須同步**：與 Task 7.3 共用**欄位級** formatter registry ⇒ 新增欄位時兩頁自動有文案，
  但**欄集各自選取**（兩頁欄集不同，見內容②）；
  分析參數之欄集與 Task 7.0b 之 `event_label_spec` 為**同一組**，欄位增減須同批改。
- 邊界：批次事實欄**只揭露、不可改**；分析參數**只作用於本次分析**、**不回寫**事件批。
- 不可做：不得只在 tooltip 顯示 `importId` 就算揭露（使用者要的是語意，不是識別碼）；
  不得讓分析參數以任何形式回寫已落檔之事件批（那會使同一批事實隨分析而變，
  §D-3′ 之整個分層即為此而設）。

**Task 7.7 — Feature run `time_range` 與事件期之對證（R4 群集 C；R5 群集 D／E 改寫；R8 增訂⑦ picker 之 decision_at 映射）**
- 內容：`RunInfo`（`api/models/feature_factory_models.py:116-133`）**無 `time_range`**，
  而 manifest artifact **已有**（`feature_reader.py:455`；非 legacy 路徑之產生處＝
  `feature_storage._resolve_l7_v2_time_range`）⇒ 資料在後端、前端拿不到，
  IC 分析可在「特徵 run 根本不涵蓋事件期」時照送。
  ① **wiring（本 Task 之一部分，非另開票）**：
     `RunInfo.time_range: Optional[dict]`，形狀與 manifest **同形**：`{"start": str|None, "end": str|None}`。
     🔴 **型別依實碼裁定，非投票**：`_resolve_l7_v2_time_range` 之回傳型別為
     `Dict[str, Optional[str]]` ⇒ **值為字串，不是 epoch 毫秒整數**
     （grok 之修法寫 `int|None`，與實碼不符，不採）。
     ⚠️ **該字串之實際格式見 ④**——`_format_manifest_value` 只對有 `isoformat` 屬性者
     走 ISO，其餘走 `str(value)`；實測現存 manifest 皆為 **epoch 秒數字字串**。
     （R7 群集 C：R6 版此處斷言「是 ISO-8601 字串」而 ④ 已裁定為 epoch 秒字串，
     同一 Task 內兩處互斥，兩家獨立命中——主委修 ④ 未同步 ①。）
     service 端 `_browse_metadata_for_run` 由 manifest **原樣帶出**（禁在此層轉型別）；
     `/features/runs` response 與前端 `types.ts` 之 `RunInfo` 均須含此鍵。
  ② **時間基準之換算（R5 群集 D；三家一致「逐列取事件列之 tf」）**：
     `bar_ms(e) = timeframe_seconds[e.timeframe] * 1000`
     🔴 **R23 更正單位來源（三家：CODEX-R23-P1-02＋GROK-R23-P1-02＋COMPOSER-R23-P1-01）**：
     R22 已把 §D-3′-a 之權威式改為**注入之 `timeframe_seconds`**，並定死
     「module-level `TIMEFRAME_SECONDS` 僅為建構素材、不得於計算路徑直讀」，
     **但本處未同步** ⇒ 同一 SPEC 內兩個互斥之單位 SoT，實作者可任選其一。
     ⇒ 本處之 `timeframe_seconds` **即 §G G-3 ⑥(d) 注入之同一 map**；
     其鍵集由 (d-3a) 之集合相等對證。
     🔴 **R24 補「取得點」（兩家；COMPOSER-R24-P1-02＋GROK-R24-P1-02）**：R23 版只說
     「即同一 map」，**未定義本 Task 從何處取得它**——該 map 之注入寫在
     `purge_lower_bound_ms` 之簽章內，而 feature-run gate **不在該函式內**
     ⇒ 實作者可在 coverage 路徑**直讀 module 常數而不違反任何可執行條文**。
     **取得點（唯一）**：`_run_analysis` 之事件分支，
     於**匯入 validation 通過後、prepare-windows 之前**建構**一次** `timeframe_seconds`，
     並以**同一物件**傳入 `purge_lower_bound_ms` 與本 gate。
     **禁**各自建構、**禁**在本 gate 內直讀 module 常數。
     🔴 **R25 更正三處（三家：CODEX-R25-P1-02＋GROK-R25-P1-02＋COMPOSER-R25-P1-03）**：
     ①**時序矛盾**：R24 版寫「prepare-windows **之後**建構」，但
     `purge_lower_bound_ms_by_symbol` **於階段 2（prepare-windows 內）末即須算出**
     ⇒ 該 map 必須**更早**存在，否則循環依賴。**改為匯入驗證通過後、prepare-windows 之前**
     ——與 §D-3′-a（ii）L278–282 之鍵集凍結時點**同一時點**。
     ②**刪除 R24 版之「同一物件／等位元組拷貝」並列寫法**：R24 版未定義 bytes equivalence、
     亦無驗收可證兩 consumer 收到同一 map ⇒ **只准同一物件**，驗收以 `is` 比對
     （角色卡 (b) 之物件參考比對）。
     ③**子集來源具名**：`timeframe_seconds` 之鍵集 **==** `lookahead_bars_declared.keys()`
     （即 L278–282 之凍結集合，源自 `records`）；**禁**傳 module 全表、
     **禁**以對齊成功列或 post-coverage 子集建構。此即 (d-3a) 三側之一。
     ④🔴 **R26 補「同一物件」之可紅 mutation（三家：CODEX-R26-P1-03＋GROK-R26-P1-03＋
     COMPOSER-R26-P1-02）**：R25 版之「只准同一物件、以 `is` 比對」**全檔僅散文、
     無任何可紅條** ⇒ 依角色卡 Rule 3「驗收寫不出可紅 mutation ⇒ 不得入 SPEC」，
     本輪補齊：
     **驗收**：以 spy 記錄 `purge_lower_bound_ms` 與 feature-run gate 各自收到之
     `timeframe_seconds`，斷言 `a is b` 為真（物件參考比對，角色卡 (b)）。
     **mutation（三條，皆須紅）**：(m1) 任一 consumer 改為自行建構一份**內容相同**之 map
     ⇒ `is` 斷言紅；（m2) 任一 consumer 改為直讀 module 常數 ⇒ `is` 斷言紅；
     (m3) feature-run gate 改以 **positional** 傳入 `timeframe_seconds`（map 內容相同）
     ⇒ `exit != 0`（證明「只准 keyword-only」可機械紅）。
     - 驗證：`pytest tests/api -q -k timeframe_seconds_identity` 之 (m1)(m2) 各自 `exit != 0`；
       正例斷言
       `spy_purge.kwargs["timeframe_seconds"] is spy_gate.kwargs["timeframe_seconds"]`
       為 `True`。
       feature-run gate 之 `timeframe_seconds` **只准 keyword-only**（禁 positional）。
       兩 spy 掛載點具名（字面須可 grep）：
       - `unittest.mock.patch("momentum.Analysis.event_samples.label_value_from_case.purge_lower_bound_ms")` → `spy_purge`
  `def check_feature_run_coverage(*, timeframe_seconds: Mapping[str, int],
      feature_manifest_time_range: dict[str, str | None],
      event_windows: tuple[WindowRow, ...]) -> None`
  ——Task 7.7 ② 3a；由 `_run_analysis` 事件分支在 `prepare_analysis_windows` 之後、
  `apply_event_coverage` 之前以 **keyword-only** 呼叫一次；讀 `_feature_library` manifest
  之 `time_range` 與 `event_windows` 比對；不符 ⇒ `ValueError`。
       - `unittest.mock.patch("api.services.ic_analysis_service.check_feature_run_coverage")` → `spy_gate`
       （**唯一**呼叫點＝`_run_analysis` 事件分支；禁 `pipeline._assert_feature_run_covers_events`、禁 `args[N]`。）
       🔴 **R31 裁定**：函式**須新建**（現行碼 grep→0）；掛載層＝API service（(乙)），非 `pipeline.py`。
       🔴 **主委之擇取理由（`ERRATA-R31-B`）**：本條有兩份互斥補丁包——COMPOSER
       `r31-spy-gate-shape` 與 GROK `r31-spy-gate-must-create`，**方向一致**（皆維持 (乙)、
       皆要求明列須新建、皆要求收斂重複合議段），差異在字面與涵蓋面。**採 COMPOSER 版**，
       理由為機器可導出、非偏好：GROK 版之編排草圖 AFTER 在**呼叫位置**使用裸 `*`
       （與本輪 P1-04 同一病），`compile()` 實跑為 **SyntaxError**，照抄即不可執行；
       **本 ERRATA 不重貼該非法字面**（避免 must_exist／Agent 誤抄）。
       COMPOSER 版另為唯一提供 `def` 簽章者（三家皆要求之 shape 要素）。
       ✅ **R32 已結**：三家一致判本擇取**未越權**。GROK 之「須於本 Task 新建」字面
       依 CODEX-R32-P2-01 之裁定**視為撤回之冗餘字面**（上方「函式**須新建**」已保留語義）。
       🔴 **`ERRATA-R32-B2`——gate 具名呼叫之擇取**：本群集有兩份互斥 AFTER。
       COMPOSER／GROK 版（同名檔 `r32-spy-gate-call.md`，見下方 `ERRATA-R32-COLLISION`）
       之第二引數取自**一個本檔從未定義的 manifest 變數**（名稱見該補丁包，**本 ERRATA
       刻意不重貼**）——屬 R11 意義下之 dangling，與本 epic 連三輪判為 P1 之缺陷同類；
       CODEX `r32-feature-run-gate-call` 之引數則**即上方 `def` 之 keyword-only 參數名**。
       ⇒ **採 CODEX 版**（機器可導出：該 dangling 名於本檔之定義數＝0）。
       🔴 **`ERRATA-R32-COLLISION`**：COMPOSER 與 GROK 本輪**輸出同一檔名**
       `handoffs/patches/20260824-gap3ux-r32-spy-gate-call.md` ⇒ **其中一家之補丁包被靜默覆蓋**
       （本輪 15 條 findings 卻只有 14 份補丁檔）。主委**無法判定倖存者為何家**，
       亦無法復原被覆蓋者 ⇒ **R33 請兩家各自改名重交**，並請三家裁此檔名碰撞是否須機械擋。
       🔴 **R27（三家：CODEX-R27＋GROK-R27＋COMPOSER-R27）**：R26 主委寫之 `args[N]` 中
       **`N` 未定**，且兩 spy 掛載點未具名 ⇒ 為 dangling。
       **主委已於 R27 brief 自行揭露此假設**，三家確認並給出上列 AFTER。
     （`momentum/core/constants.py:6` 之 `TIMEFRAME_SECONDS` 為該 map 之**建構素材**，
     七值閉集；**不得**於本處直讀。）
     🔴 **禁止**取 run 之 tf、批內 `max(tf)`／`min(tf)`／平均——**逐列用該列自己的 `timeframe`**；
     批內多 TF **允許**（不整批拒收），但任一列之 `e.timeframe` 不在**注入之** `timeframe_seconds` 鍵集
     ⇒ 整批 fail-closed，reason `== "feature_coverage_unknown_timeframe"`。
     此為與 R3 之 future72 單位錯**同型**之缺口（grok 明指），故單位來源須寫死於本欄。
  ③ **containment policy（唯一；R5 群集 E 修正左界）**：
     🔴 **R9 收緊（CODEX-R9-P0-01）／R10 具名欄（三家）**：所取之 receipt **必須是
     §D-3′-a（iii）階段 2 產生之本次分析 receipt**——以
     **`analysis_alignment_receipt_hash` 相等**機械對證（該欄之定義在 §D-3′-a（iii）），
     其值與 split／labels 所用者相同；
     **不得**讀匯入檔烤入之 `label_start_ms`／`label_end_ms`——否則 h=7 之 coverage
     會以 h=1 之舊右界判定而 fail-open。
     取 alignment receipt 之既有欄位，**不自行以裸 `horizon_bars` 加時間戳**：
     ```
     required_start(e) = receipt.decision_at_ms(e)      # = t0 往前 decision_offset_bars 根
     required_end(e)   = receipt.label_end_ms(e)        # = 含答案窗之右界
     ```
     無 receipt（如純 fixture 推導）時才以 ② 之 `bar_ms(e)` 計算同義值。
     放行條件（**批內全部列皆須成立**）：
     `run_start_ms <= min_e required_start(e)` 且 `max_e required_end(e) <= run_end_ms`。
     🔴 左界用 `decision_at_ms` **而非** `min(t0)`：IC 之特徵截止規則為
     `max_close_ms <= decision_at`（`ic_feed.py`），`decision_offset_bars = k > 0` 時
     `decision_at < t0` ⇒ 用 `min(t0)` 會放行「run 未涵蓋決策時點」之批次（fail-open 窗口）。
     **不得**在本 Task 任何處殘留 `min(t0)` 之舊字面。
  ④ **`time_range` 字串 → epoch ms 之 parse 規則（R6 群集 G：三家以真實 manifest 推翻 R5 版）**：
     🔴 **實測事實**：現存非 legacy manifest 之 `time_range` 為 **epoch 秒之數字字串**，例
     `data_cache/features/BCHUSDT/1h/4a8a0b3726cc906ab3534994605e77f5/feature_manifest.json`
     → `{"start": "1704067200", "end": "1777330800"}`（兩值型別皆 `str`）。
     R5 版指定之 `datetime.fromisoformat(s)` 對此**直接 raise**
     ⇒ 照 R5 版實作會把**全部現存 run** 判為 parse failure。三家全員命中，主委獨立覆核屬實。
     **解析順序（唯一；先數字後 ISO）**：
     1. `s` 去除前後空白後**全為十進位數字**（可含前導 `-`）⇒ 視為 **epoch 秒**，
        `epoch_ms = int(s) * 1000`。
        合理性檢查：`0 < int(s) < 4102444800`（＝2100-01-01）；超出 ⇒ fail-closed。
     2. 否則以 `datetime.fromisoformat(s)` 解析：**tz-aware ⇒ 轉 UTC epoch ms**；
        **tz-naive ⇒ fail-closed**（把 naive 當 UTC 是假設，假設錯誤會使覆蓋判斷整體偏移）。
     3. 兩者皆不成 ⇒ fail-closed。
     1–3 之任何 fail-closed 皆回 reason `== "feature_coverage_unknown_timestamp_format"`
     （取代 R5 版之 `feature_coverage_unknown_timestamp_format`；後者語意過窄，涵蓋不了數字字串路徑）。
     ⚠️ **不得**以「猜一個格式試試看」實作——三條分支之判定須為封閉且可逐條測試。
     📌 **本項之處理過程保留為範例**：R5 版由主委補充並**自行具名標為「待 R6 裁定」**，
     R6 三家即以真實 manifest 打穿之。該「主委補充須具名待裁」之作法有效，予以保留。
  ⑤ **legacy run**：`time_range` 為 `{"start": None, "end": None}`（`feature_reader.py:455`）
     ⇒ **不得**視為「涵蓋全部」而放行，一律 fail-closed，
     reason `== "feature_coverage_unknown_legacy_run"`。
  ⑥ 不滿足 ③ ⇒ fail-closed，`capability_status == "unavailable"`、
     reason `== "feature_coverage_insufficient"`。
  ⑦ 🔴 **IC picker 之 feature timestamp 映射（CODEX-R8-P0-03；R8 新增）**：
     現行 `eventT0MsToIcTimestamps`（`frontend/src/lib/api.ts:1042-1048`）把
     **原始 `t0` ÷1000** 當成 IC 主線之 `event_timestamps`。
     §D-3a 已裁定「每列 feature sample key 須為 receipt 之
     `last_bar_open_ms`／`decision_at_ms`，**不是原始 t0**」
     ⇒ `decision_offset_bars = k > 0` 時，現行映射會把特徵取樣點推到**決策時點之後**，
     與 `ic_feed.py:76` 之 `feature_cutoff_rule = max_close_ms_le_decision_at` 互斥。
     **處置**：映射改由**後端**於分析時依 receipt 產生（隨 Task 7.0b ② 之 `event_import_id`
     入後端後，前端不再需要自算 timestamps）；
     前端之 `eventT0MsToIcTimestamps` **移除**，`useICAnalysis` 不再送 `event_timestamps`。
     映射不合法（該 t0 無對應 bar）⇒ fail-closed，reason 取自契約既有
     `alignment_failure_reasons.missing_bar`；
     兩個事件映射到**同一** decision bar ⇒ fail-closed，reason `duplicate_bar`。
     🔴 **不新增 reason**（D-6：能用契約既有字面就不擴清單）。
  ②④⑤⑥ 所列之 reason 一律登記於 `ic_report_contract.json` 之 `reasons.analysis_rejected`
  （與 Task 6.0 同一處；程式與前端由該檔取字面；**最終集合見下方驗證②，本欄不重述**）。
  ⑦ 所引之 reason 集合恰為 `{missing_bar, duplicate_bar}`，取自
  `event_import_contract.json` 之既有 `alignment_failure_reasons`，
  **不登記於** `analysis_rejected`（層次不同：對齊失敗 vs 分析入口拒絕）。
- 驗證：`pytest tests/api -q -k feature_coverage_gate` ≥9 條——
  ①`assert 'time_range' in RunInfo.model_fields`；且讀一份**真實** manifest 斷言
    `start`／`end` 原樣進 `/api/v1/features/runs`（型別為 `str` 或 `None`，未被轉型）
  ②`analysis_rejected` 之**最終**內容 `== ['feature_count_exceeds_cap',
    'feature_coverage_insufficient', 'feature_coverage_unknown_legacy_run',
    'feature_coverage_unknown_timeframe', 'feature_coverage_unknown_timestamp_format']`
  ③小型跨日期 fixture：事件期全落在 run 區間內 ⇒ 放行（`capability_status != "unavailable"`）
  ④`decision_offset_bars = 3` 且 `run_start` 落在 `decision_at` 與 `t0` **之間**
    ⇒ **fail-closed**，reason `== "feature_coverage_insufficient"`（左界回歸；R5 群集 E）
  ⑤`max(t0)` 在區間內但 `label_end` 超出右界 ⇒ **仍 fail-closed**（右界含答案窗）
  ⑥**1h 與 12h 同 `t0`、同 `horizon_bars` 之對照**：兩者之 `required_end` 相差 12 倍
    ⇒ 12h 之 fixture 須被擋、1h 之須放行（證明未寫死單一 tf）
  ⑦批內混 1h 與 12h ⇒ **逐列各用自己的 tf**，結果與逐列單獨計算一致
  ⑧`e.timeframe` 為 `'3h'`（不在**注入之** `timeframe_seconds` 鍵集）⇒ fail-closed，
    reason `== "feature_coverage_unknown_timeframe"`
  ⑨`time_range == {"start": None, "end": None}` ⇒ fail-closed，
    reason `== "feature_coverage_unknown_legacy_run"`；
    `start` 為 tz-naive ISO 字串 ⇒ fail-closed，reason `== "feature_coverage_unknown_timestamp_format"`
  ⑩**epoch 秒數字字串正例**（現存 run 之實際格式）：`time_range == {"start":"1704067200","end":"1777330800"}`
    ⇒ **解析成功**（`1704067200 * 1000` 得 epoch ms）且覆蓋判斷正常進行——
    此條防「照 R5 版實作而擋下全部現存 run」之回歸
  ⑪`start == "99999999999"`（超出 2100-01-01）⇒ fail-closed，
    reason `== "feature_coverage_unknown_timestamp_format"`
  ⑫🔴 **decision_at 映射（內容⑦；R8 新增）**：`decision_offset_bars = 3` 之批次
    ⇒ 送入 `ic_feed` 之每列 feature sample key `==` receipt 之
    `decision_at_ms`（換算後）且 `!=` 原始 `t0`；`k = 0` 之批次兩者相等（對照組，
    證明本條不是恆真也不是恆假）
  ⑬映射不合法（某 t0 無對應 bar）⇒ fail-closed，reason `== "missing_bar"`；
    兩事件映射到同一 decision bar ⇒ fail-closed，reason `== "duplicate_bar"`
  ＋`npx vitest run icEventPickerNoLocalMapping` ≥2 條——
  ⑭`grep -c "eventT0MsToIcTimestamps" frontend/src/` `== 0`（前端不再自算映射）
  ⑮`useICAnalysis` 送出之 payload **不含** `event_timestamps`、**含** `event_import_id`
  ⑯🔴 **R17 新增——後端對「兩欄同時出現」之優先序（CODEX-R17-P1-05）**：
    ⑮ 只驗**新前端**不送 `event_timestamps`，但 `ICAnalyzeRequest` **仍接受該欄**，
    且 `_run_analysis` 與 full-analysis 路徑仍**無條件**把它傳給 analyzer
    ⇒ 任何非本前端之呼叫端（curl／舊分頁／第三方）同時帶兩欄時，
    **可繞過 receipt-derived `decision_at`**，回到原始 `t0÷1000`（洩漏面）。
    ⇒ 定死：**`event_import_id` 存在時，同一 request 帶 `event_timestamps` ⇒ HTTP 400
    fail-closed**（不是忽略、不是取其一）；事件路徑之時間戳**唯一來源**＝receipt。
    🔴 **R18 更正（CODEX-R18-P1-04）——R17 版之兩處寫錯**：
    (a) **驗收自相矛盾**：原寫「斷言 spy 收到之時間戳來自 receipt，**且**回應為 400」。
        兩者不可同時成立——若 validator 在 request boundary 就拒絕，analyzer **根本不會被呼叫**。
        ⇒ **拆成兩條獨立驗收**（見下 (i)(ii)）。
    (b) **「`ICFullAnalysisRequest` 之第二次 analyzer 呼叫」不存在**：碼證
        `api/models/ic_models.py:173` 為 `class ICFullAnalysisRequest(ICAnalyzeRequest)`
        ——**繼承**，故 validator 掛在父類即同時涵蓋兩個端點；full-analysis 路徑
        （`ic_analysis_service.py:793 start_full_analysis`）並無第二次獨立的
        event-analyzer 呼叫。原文之「易漏的第二條路徑」係主委臆測，撤回。
    **落點與驗收**：
    (i) **互斥 → 400**：validator 掛 `ICAnalyzeRequest`（`ICFullAnalysisRequest` 由繼承取得）。
        測試**參數化涵蓋兩個端點**，斷言 ①HTTP `400` ②event-analyzer 之 spy
        `call_count == 0`（**不是**斷言 spy 收到什麼）。
    (ii) **正常事件路徑**：只帶 `event_import_id`（不帶 `event_timestamps`）⇒
        斷言 analyzer 收到之 `decision_at` **逐列等於** receipt 導出值。
    (iii) **legacy 非事件呼叫端**（只帶 `event_timestamps`、無 `event_import_id`）
        之既有路徑**保留**，須在契約明示為 legacy，並有獨立測試釘住其存活。
    **mutation（三條，皆須紅）**：①把 validator 從父類移到子類 ⇒ 純
    `ICAnalyzeRequest` 端點之 (i) 不再回 400；②把互斥改成「忽略 `event_timestamps`」
    ⇒ (i) 之 `400` 斷言紅；③把 (ii) 之時間戳來源改回原始 `t0÷1000` ⇒ (ii) 紅。
  **mutation（八條，皆須紅）**：左界改回 `min(t0)` ⇒ ④；右界不含答案窗 ⇒ ⑤；
  改用 run 之 tf 或批內 `max(tf)` ⇒ ⑥⑦；legacy 之 `None` 改成放行 ⇒ ⑨；
  未知 tf 改成沿用預設 ⇒ ⑧；fail-closed 改成只回警告字串 ⇒ ③；
  把解析改回「只用 `datetime.fromisoformat`」⇒ ⑩須紅（R6 群集 G 之回歸樁）；
  🔴 把 feature sample key 改回原始 `t0` ⇒ ⑫須紅（R8 之回歸樁）。
- 存活至：Phase 7（終）。
- 覆蓋風險：本 Task 之 gate 位於 IC 分析**入口**，與 Phase 6 之特徵數止血閘（Task 6.1）同在入口
  但為**不同拒絕條件、不同 reason**（覆蓋不足 vs 特徵數過大）⇒ 兩者須各自回應、不得合併。
  **須同步**：Task 6.1 隨 GAP-6 之分塊計算被取代時，本 Task **不隨之作廢**——
  日期錯配與規模無關，分塊計算上線後仍須此對證（codex R4 原話：等待分塊計算不會使日期錯配變安全）。
- 邊界：只驗「特徵覆蓋範圍是否包含事件期」；不驗特徵值本身之品質。
- 不可做：不得以「使用者自己會看」替代機械對證；不得在無法取得 `time_range` 時預設放行。

---

## §V 驗證策略與邊界測試目錄

### §V 書寫規則（R5 consult 裁；三家全員同向）

🔴 **§V 是索引，不是第二份規格。**
出處＝R4／R5 連兩輪之自傷共 8 條，形態一致：**改了 §P 之權威定義，未同步 §V 之複述**
（最嚴重者＝V-11 仍寫 `contractAccepted` 而 Task 7.1／7.2 已改 `selectable(path,dim)`，
照 V-11 實作會強迫 UI 啟用 A／B、推翻路徑級限制）。
**複述即第二份副本，副本必然漂移**——故本節不靠紀律，改以規則＋機械閘消除複述本身。

- 凡 V 列對應某個 Task 者：「手段／通過條件」**只寫**「執行 Task `<id>` 之驗證欄，其命令 rc=0」
  （可加一句路徑對照），**禁止**重寫集合等式、公式、enum 字面清單或 mutation 條文。
- 唯一例外：跨多 Task 之整合列（如 V-M）可列 Task ID **清單**，仍不得另造第二套通過條件。
- 機械強制：`scripts/spec_v_task_ref_check.sh`（掛 `narrow_check_router.sh`）。

| ID | 驗什麼 | 手段 | 通過條件 |
|---|---|---|---|
| V-1 | CSV 對映之 label **照抄正確** | 真實 CSV fixture → 匯入 → 逐列比對 | 每列 `label ==` CSV 指定欄之值。**誠實邊界：本項不證明使用者選對欄**（D-1，語意不可機械證明）；選欄風險由 V-1b/V-1c 降低 |
| V-1b | 可疑欄警示有鑑別力 | fixture 含 3 個二元欄 | 警示列出另外 2 個（`len == 2` 且集合相等） |
| V-1c | provenance 可追 | 匯入後讀 receipt | `column_mapping.label ==` 送出值；`source_file_digest` 存在且 `!=` 空 |
| V-2 | 對映缺失／欄不存在／label 非二元／異質列 各自 fail-closed | 四個反例各一測 | 各得對應 reason；**落檔數 `== 0` 且 task store 筆數不變**（CODEX-R1-P1-04：不只驗落檔，須驗無其他狀態副作用） |
| V-3 | CSV 與 JSON 路徑**共用同一函式** | **兩重 oracle**（R1 三家指出單靠 sha256 相等不成立） | ①靜態：AST 斷言 CSV route 呼叫 `/import-events` 之同名驗證函式 ②行為：mutation——把該共用函式改壞，**兩條路徑之測試須同時轉紅**（只有一條紅 ⇒ 存在平行實作） |
| V-4 | `event_id` 跨路徑一致（D-2） | 同批事件之 JSON 匯出 vs CSV 回灌 | `event_id` 集合 `==`（集合相等，非逐列順序） |
| V-5 | 刪除後該批消失 | 刪除 → 列表／analyze 各查一次 | 列表無該批；analyze status_code `== 404` |
| V-6 | 附帶 `future_*` 欄與**分析層** `label_value` 分離；匯出端不寫 `label_value`；換 h 不需重匯出（D-3′） | **執行 Task 4.1／4.1c 之驗證欄全部條目**；§V 不重述斷言字面 | 兩 Task 之命令皆 rc=0 且條目數 `>=` 各自所列 |
| V-7 | `.source.json` 誤傳之訊息含正解 | 上傳 `.source.json` 當事件檔 | status_code `== 400` 且訊息含 `source_file` |
| V-8 | 止血閘生效且**未載入大矩陣**（D-5） | **執行 Task 6.4 之驗證欄全部條目**（其 V-8 三項斷言與採樣時點）；§V 不重述斷言字面 | `pytest tests/api -q -k ic_stop_gate_alive` rc=0 且條目數 `>=` Task 6.4 所列；量測工具與禁令見 Task 6.2 |
| V-9 | 止血閘不誤擋 | 小 run（15 特徵）呼叫 | status_code `== 200` **且任務確實被建立**（task store 筆數 +1；R1 指出只驗 200 不足） |
| V-10 | tooltip 與 glossary 不漂移 | 逐表頭比對 | tooltip 文字 `==` glossary `definition` |
| G-1 | IC 主線未被波及 | `python3 scripts/gap3_freeze_golden.py --check` | 通過。**誠實邊界：不涵蓋事件路徑**（D-4） |
| G-2 | 事件路徑數值未意外改變 | 本批新建之事件 golden | 逐 horizon exact return（`atol=0`）／NaN mask／PIT anchor 全等；Task 4.2 之合法變更須同 commit 更新並說明 |
| G-3 | **分析時** `label_value`／window／purge／feature timestamp map 未意外改變（D-3′） | 本批新建之 analysis-label golden（§G G-3） | `pytest tests/momentum/event_samples/ -q -k analysis_label_golden` rc=0；覆蓋面與可證偽條之唯一定義見 §G G-3。**誠實邊界：G-2 涵蓋不到此路徑**（兩者不可互相替代） |
| V-16 | 分析時 producer 之支援矩陣、purge 下界（含逐列 ms 換算與 per-scope 聚合）、分析時 receipt 之唯一性、前端不持有 `label_value`（D-3′／D-3a／F-1′／F-2′／F-4′） | **執行 Task 7.0b 之驗證欄全部條目**；§V 不重述支援矩陣、purge 公式與階段清單 | Task 7.0b 之命令皆 rc=0 且條目數 `>=` 其所列；purge 下界之唯一定義見 §D-3′-a（ii）、階段之唯一定義見 §D-3′-a（iii） |
| V-17 | IC 分析頁：批次事實欄唯讀、分析參數可設定且不回寫（D-3′） | **執行 Task 7.6 之驗證欄全部條目**；§V 不重述斷言字面 | Task 7.6 之命令皆 rc=0 且條目數 `>=` 其所列 |
| V-11 | 五維度全接出、不可漂移、且**選值真的傳到落檔**（Phase 7） | **執行 Task 7.2 之驗證欄全部條目**（三層＋其 mutation）；§V 不重述任何斷言字面 | `npx vitest run contractEnumWiring` rc=0 且用例數 `>=` Task 7.2 所列；集合層之唯一基準 ＝ Task 7.1 定義之 `selectable(path, dim)` |
| V-12 | lookahead 深度由**使用者宣告**、缺即擋（D-7 之 L1/L2/L3；R 重開 D-8 改寫） | **執行 Task 1.10／1.11／1.12／1.9／1.9′ 之驗證欄全部條目**；§V 不重述 fixture 條文 | 各該 Task 之命令皆 rc=0；深度之唯一來源＝Task 1.9／1.9′ 之宣告（原 Task 2.1b 已退役），改名攻擊之判準見 Task 1.10。🔴 **R8 邊界**：本列只管**深度導出**；深度與分析時 h 合成 purge 下界之 `max` 式屬 §D-3′-a（ii），由 **V-16** 承接，兩列不重疊 |
| V-14 | IC 分析頁揭露該批五維度 | **執行 Task 7.6 之驗證欄全部條目**；§V 不重述斷言字面 | `pytest tests/api -q -k event_batch_detail_dims` 與 `npx vitest run icEventBatchDisclosure` 皆 rc=0 且條目數 `>=` Task 7.6 所列 |
| V-15 | 特徵覆蓋對證 fail-closed | **執行 Task 7.7 之驗證欄全部條目**；§V 不重述 containment 邊界公式 | `pytest tests/api -q -k feature_coverage_gate` rc=0 且條目數 `>=` Task 7.7 所列；containment 之唯一定義見 Task 7.7 |
| V-13 | 報酬表正／反／全體三組 | **執行 Task 7.5 之驗證欄全部條目**；§V 不重述斷言字面 | `pytest tests/momentum/event_samples/ -q -k return_table_by_label` rc=0 且條目數 `>=` Task 7.5 所列 |
| V-M | 可證偽性 | **逐 Task** 列出：mutation 內容、命令、預期紅、實際 receipt 路徑 | 逐條紅；還原後全綠。**不得只寫「逐條紅」**（CODEX-R1-P0-06） |

**測試設計紀律**（本 session 已四次交出假綠，逐條套用）：
1. 斷言**中間值與副作用**，不只斷言例外型別或 HTTP 碼（V-2／V-8／V-9 皆已加 store 筆數斷言）。
2. fixture 不得把受測依賴設成 `None` 而使受測路徑整段跳過。
3. 「共用實作」不可只靠輸出相等證明，須有**改壞共用點 ⇒ 兩路同時紅**之 mutation（V-3）。
4. 量測型驗收須定義**口徑、基線、採樣點、工具**，否則必假綠（V-8）。

---

## §R 回退

各 Phase 獨立 commit，可逐一 `git revert`。
Task 1.1（契約）為其他 Task 之前置，回退須連同 Phase 1/2 一併回退。
🔴 **Phase 4 之回退性已於 R8 改變**：原為「純疊加（D-3 之 (a)），回退不影響既有 label 語意」；
§D-3′ 後 Phase 4 **移除**匯出端之答案窗與 `label_value` ⇒ 單獨回退 Phase 4 會使匯出端
恢復寫 `label_value`，而分析層（Task 7.0b）仍會自行計算一份 ⇒ **同一批出現兩份 `label_value`**。
⇒ Phase 4 與 Task 7.0b／7.6 為**同一回退單元**，須一併 revert。
Phase 6 為純新增之前置檢查，回退即恢復「可按但會吃垮機器」的現況（不建議）。

---

## §N N/A 登記

### 🔴 下推清單（R14 三家裁定；具名殘留，**凍後執行**）

**出處**：R14 議題三第 10 點——主委問「現行 SPEC 有哪些內容本來就不該由規格承擔」，
三家**直接裁定**並給出具體條目。
**為何是殘留而非現在刪**：TODO 檔尚未生成（SPEC 未凍結），現在刪會產生 dangling reference。
三值理由＝`blocked-by`（blocked by FROZEN 與 TODO 生成）；**owner＝主委**；
**觸發＝FROZEN 之後、TODO 生成當批**。

| 條目 | 下推理由（三家） |
|---|---|
| Task 1.3 ④(a) 之 vitest spy **路徑列舉**（`crypto.subtle.digest`／`*Hex` 等） | 實作綁線細節；規格保留「該呼叫面之 `call_count == 0`」即足 |
| Task 7.0b ⑩(i) 之 `patch(..., wraps=...)` **精確模組路徑** | pytest 慣例，屬測試計劃層 |
| Task 7.0b ⑩(v) 之 `align_events` spy **掛載點** | 同上 |
| Task 7.7 驗證① 之**真實 manifest 逐檔路徑列舉** | 保留一條 FACT-RECEIPT 即可，刪逐檔列舉 |
| Task 7.0b 之 `tuple`／`bytes` **容器實作細節** | 規格保留「不可變、鍵序固定、封閉欄集」之語意；容器選型屬實作 |
| Task 7.6 之 **payload／UI 佈局細節** | 規格保留 wire shape 與唯讀性，版面屬實作 |
| Task 7.7 之 **parser 分支實作**（3a 之 epoch/ISO 解析順序） | 規格保留三分支之語意與 fail-closed，實作屬 TODO |

🔴 **不得以本清單為由現在刪除任何條文**——凍結前 SPEC 仍是唯一規範來源。

### 🔴 R15 新登記之具名殘留（兩條；**非下推**，是本 epic 內未封口者）

| 條目 | 三值理由 | owner／觸發 |
|---|---|---|
| **純 JS 手刻 sha256 繞過 digest 閘**：Task 1.3 ④ 之閘枚舉「雜湊入口封閉集合」＋AST 靜態掃描，兩軌皆看不見「不呼叫任何標準入口、自行實作 sha256 之程式碼」 | `needs-research`——**位置無限、入口有限**，故閘只能枚舉入口；要擋手刻實作需另尋可判定形式（如輸出 bytes 之 differential test），尚無成案 | 主委／FROZEN 後 |
| ~~**三條主委紀律仍為 prose**~~ → 🔴 **R16 拆分處置**：①檔頭 current-round receipt **已封口**（見下）；②「先問後做」與③scope accretion 入口閘**維持殘留** | ②③`needs-research`（理由見下方裁決） | 主委／FROZEN 後 |

#### 🔴 R16 主委裁決：治理紀律殘留之拆分（CODEX-R16-P2-05 vs GROK／COMPOSER-R16）

**兩造**：codex 判 R15 之「三條紀律維持殘留」是**藉口**——角色卡已列出有限觸發面
（producer／transport／receipt／encoder／parallel fixture ＋ owner／shape），故可 diff-based 機械化；
grok 判 `needs-research` **理由成立、非逃避**，composer 判已登記無問題。

**裁定：三條逐條拆開，不整包接受也不整包拒絕。**

| # | 條目 | 裁定 | 理由 |
|---|---|---|---|
| ① | SPEC 檔頭 current-round receipt | **採 codex，本輪封口** | 觸發面確實封閉且兩端皆可導出：「SPEC 有未提交改動」×「檔頭輪次 ≠ 已有委員產出之最大輪次」。已落為 `scripts/gap3ux_header_round_check.sh`，掛在 `gap3ux_pre_review.sh`。🔴 **該閘上線首跑即抓到檔頭仍停在 R15**——散文版連續兩輪沒抓到 |
| ② | 「先問後做」 | **維持殘留** | 「決定不先問」不會在任何 diff 留下痕跡，**結構上不可觀測**；這不是設計難度問題 |
| ③ | scope accretion 入口閘 | **維持殘留**（`needs-research`） | codex 所指之封閉集合是**機制種類**之集合，不是 **diff 字面**之集合；以關鍵字比對 diff 即**黑名單**，正是 `_g2_regions`「一機制衍生四條旁路」之同型（記憶：文字問題用白名單機械卡）。**兩者之對應關係才是未解的部分** |

##### 🔴 R17 更正（CODEX-R17-P2-08）：上表②③之理由**過度概括**，此處收窄

codex 指出：**package／consult 之內容、hash、時序本身都是可觀測 artifact**，
故「結構上不可觀測」對②③並非全稱成立。**此更正成立，主委接受**——原表述把
「無法觀測**意圖**」誤寫成「無法觀測**任何相關事物**」。收窄後之準確表述：

| 標的 | 可否機械觀測 | 現況 |
|---|---|---|
| 主委**心裡有疑慮卻沒問** | **不可**（無 artifact） | 永久不可機械化；只能靠事後由委員從結果反推 |
| 一份 mechanism package **有無**對應之 consult receipt，且該 receipt 之 hash 出現在**目標修改之前**的 audit event | **可**（ancestry＋hash 皆為 artifact） | 🔴 **可做，但本輪不做**——理由見下 |
| 一段 diff **是不是**引入了新 producer／transport | **不可**（需語意判斷；關鍵字比對＝黑名單） | 維持殘留 |

**為何第二列可做卻不在本輪做**（三值理由改為 `blocked-by`，不再是 `needs-research`）：
它擋的是「**已宣告**之 mechanism package」，而本 epic 剩餘工作已無新 package 產生；
在收斂期再添主委自建閘，其風險（自建閘屢有自欺紀錄，R17 又抓到本輪新閘之
fail-open 分支）高於它在剩餘輪次內能擋到的東西。**blocked-by＝FROZEN**；
owner＝主委；觸發＝FROZEN 後之第一個新 mechanism package。

⚠️ **本裁決之誠實邊界**：①封口後，②③仍為 fail-open；主委自建閘之 4 次自欺紀錄依然成立，
故 ① 之閘本身應由 R17 覆核其可證偽性（mutation：把檔頭改回舊輪次 ⇒ 須紅）。

#### 🔴 FROZEN 條件④之歷史 locus 債：R16 已清 12 條，餘 13 條**須 R17 裁定**

**R16 已做（不改判準、不豁免）**：R15 之 10 份補丁包原有 **25 條**未達 anchor。
其中 **12 條**之失敗原因為「anchor 只出現在**刪除行**，而補丁包正文未逐字引用該字面」
——已把被刪字面逐字補進各該補丁包之新增區塊「R16 補：被刪字面」，
可於 `git show ae9f8d99^:docs/GAP3_EVENT_UX_SPEC.md` 覆核。
**結果：25 → 13；全綠補丁包 2 → 4。**

**餘 13 條之三類，主委不自行處置，理由如下**：

| 類 | 條數 | 為何主委不自行處置 |
|---|---|---|
| 敘述型 anchor（當前內容與 diff hunk 皆找不到） | 4 | 須**改寫歷史補丁包之 anchor 本身**。R12 三家已裁「anchor 寫法屬委員責任」⇒ 由主委代改，等於主委替委員重寫其產物 |
| anchor 未出現在該檔之 diff hunk 內 | 7 | 該 anchor 所指之行**當時確實沒被改動**（多為 context anchor）。要turn 綠只能宣稱發生過未發生的改動 ⇒ **這是造假，不做** |
| 檔案未被本次改動 | 2 | 同上（role card 在該 commit 未被觸及） |

**🔴 請 R17 在下列兩個具體選項之間裁定（主委不自裁，因主委是受益方）**：
- **(甲)** 條件④之量測範圍＝**當輪**補丁包（歷史輪之 anchor 債以具名紀錄結案）。
  依據：使用者 2026-08-05「面向未來不溯及既往」；且 R15 之落地已由 R16 委員
  **以反例重跑**獨立證實（6 群集中 5 個確認閉合、第 6 個被抓出並於本輪修好）
  ——那是比 anchor grep **更強**的證據。
- **(乙)** 逐條清到 0，由**原提出家族**重寫其 anchor（不由主委代改）。
  依據：CODEX-R16「不得改弱判準或豁免」。

⚠️ **主委立場揭露**：(甲) 對主委有利，故不自裁。但若採 (乙)，主委**不得**代委員改寫
——需另派一輪 anchor 重寫工，且該輪不產生任何規格內容改善。


| 段 | 理由 |
|---|---|
| 使用者問題 #7 | 回答性非施工項：B8/B8b 來自 `POST /case/events/{id}/analyze` 當下計算、價格讀 `data_cache/kline_cache.h5`（`pipeline.py:78-82`），**不經 Feature Library**（已答） |
| 使用者問題 #8／#10 | 🔴 **殘留已於 R4 撤回，改為本批 Task 7.7**（R4 群集 C；GROK-R4-P0-03 指出 §C0 與本表互斥）。已答部分＝事件型兩表不需 Feature Library、IC 分析才需要。**原「未答部分」＝「事件標的/日期只需被 Feature Library 涵蓋即可」**，R3 以 `blocked-by` GAP-6 登記為具名殘留——**該登記錯誤**：三家 R4 獨立判定此為**資料正確性**缺口（特徵 run 不涵蓋事件日期仍可送 IC），非規模效能問題，且小型跨日期 fixture 即可驗、不需等 GAP-6 之分塊計算。依 §C0 條文 2（資料正確性類不得降級為具名殘留放行）⇒ **本批做**，落點＝**Task 7.7**（`RunInfo` 暴露 `time_range` ＋ containment 對證 ＋ fail-closed）。本列保留為撤回紀錄，不得刪 |
| #9b 規模防護本體 | 排入 GAP-6（registry #6「430K 規模防護」），使用者 2026-08-22 裁定 |
| **純事件研究模式（新模組）** | **具名殘留，另立模組**。使用者 2026-08-22 提出第三種用途：「單純想知道某事件（大漲 10% 後／從高點跌 15% 後）之後 1/5/10/30/60 天或任意天的漲跌數值」。此為 **event study**，與分類、條件 IC 皆不同：**不需 label、不需答案窗、不需 purge**（無訓練即無洩漏）。已查證只需 kline（`pipeline.py:78-82` 之 `bars_from_kline_cache`），**與 IC-Analysis 無關**。<br>現況缺口：契約 `required_fields` 含 `label`／`label_definition`／`control_kind`／`scenario`，且 `scenario` enum 僅 `A/B/C/two_stage`（皆為預測／確認型），**無「純描述」值** ⇒ 使用者為了看報酬分布被迫先編一個假 label。<br>三值理由＝`user-ruling`：使用者 2026-08-22 逐字「這可以未來另做一個模組研究就好」。**排程**：另立模組票，不在本批。<br>**定位**：這是**另一種用途**（想知道某類事件的後續行為分布時使用），**不是分類流程的前置條件**。<br>🔴 **主委原判斷已撤回（使用者 2026-08-22 糾正，糾正成立）**：原寫「研究順序應為事件研究 → 分類，使用者現況是直接跳到分類」。**該判斷錯誤**——它假設「標籤 ＝ 某單一根的報酬」，那種情況才需要先知道訊號在第幾根衰減。使用者的標籤是**複合形狀定義**（例「t0 +5% 且 future_1≥+2% 且 future_2≥+2% 且 future_4≥+1%」＝「漲上去且撐得住」），那是交易意圖之直接指定，**本就不需前置研究**；用「全體事件的平均衰減曲線」去推導「我要抓哪種形狀」方向亦不對。<br>**真正成立的機械約束只有 D-7**（答案窗須 ≥ 標籤最遠觸及之根數），該約束由使用者的定義**直接推導**，與研究順序無關。<br>衰減研究之**可選**用途：回頭優化既有定義（如「卡在第 4 根是否提早收手」「future_4 ≥ +1% 門檻是否過鬆」），屬事後精修而非動手前的必要功課。 |
| **觸發條件需回看歷史（如「從高點跌 15%」）** | **待盤點**。使用者 2026-08-22 提出之事件形態需回看歷史高點；現行案例搜尋是否支援此類回看型觸發條件**尚未查證**。三值理由＝`needs-research`。**owner**：主委。**觸發**：純事件研究模組開票時一併盤點。 |

---

## 🔴 凍結時之具名殘留（2026-08-24，使用者裁定凍結；**不排工，不另立治理票**）

**四類皆非量化正確性。** 依使用者 2026-08-14 裁定「回量化主線、治理不再擴建」，
**不另立治理票**（開新票只是換包裝）；本節即其唯一登記處。
三值理由一律填 `user-ruling`（使用者 2026-08-24 逐字：治理是無解才不做，岔題問委員永遠沒完沒了）。

| # | 殘留 | 現況（皆為實跑，非推測） | 為何現在不做 |
|---|---|---|---|
| F-1 | **同輪重派死鎖** | 重派需 dispatch token，`gate.sh` 於 OPEN 債時一律拒發，而銷帳需要更新後之交件事件 ⇒ 互等。唯一出口＝`debt_clear --abandon`，代價是其餘家族之合格產出一併作廢（R30 實害）。三家六份修補皆被實跑否證（讀不存在之 `GATE_CHECK_CMD`／散文無可套用字面／引用未定義變數） | `user-ruling` |
| F-2 | **補丁包同名跨家族靜默覆蓋** | R32 實害：findings 檔數與補丁檔數不符，一份永久遺失、無法判定倖存者為何家。三家一致確認**產出端在本架構無可攔截點**（`cx_run.sh` 從未碰 patch 目錄；PreToolUse hook 只攔主控端工具，委員為外部 CLI 行程）。三份收集端修補亦被否證（散文／引用不存在之腳本／`declare -A` 而本機 bash 3.2.57） | `user-ruling` |
| F-3 | **編排草圖不通過 `compile()`** | Task 7.0b 草圖含 illustrative 佔位 `<Task 7.7 picker 所選 run_id>`（R34 為修 dangling RHS 而引入）。三家皆標 illustrative，但無人明講可放棄該 receipt。**不影響本 SPEC 任一 Task 之驗收條**，僅影響「整段抄出即可執行」之便利性 | `user-ruling` |
| F-4 | **`gap3ux_apply_patch.py` 之 VERIFY 撰寫缺陷** | 已修兩處假綠（區段截斷、整條指令當字面）與一處假紅（跳脫反引號）。剩餘為**包側**缺陷：VERIFY 期望範圍過寬、字面雙重跳脫、與自身 AFTER 自相矛盾。原則已定（`CODEX-R34-P2-02`）：由 package author 修 scope，**不放寬 extractor 或判準** | `user-ruling` |

🔴 **主委對本節之自承**：F-1／F-2／F-4 **是主委自己造出來的**——R27 三家判定瓶頸為主委落地方式後，
主委新建對證工具而非提高抄寫精度，此後六輪修該工具、並把工具問題寫進派工單，
使委員持續回覆治理 findings ⇒ 自我餵養之迴圈。**這違反使用者 2026-08-14 之裁定。**
日後若有人想「順手把 F-1 修一修」，請先讀本段：**同樣的順手已經花掉六輪。**
