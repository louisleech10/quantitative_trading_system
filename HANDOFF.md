# HANDOFF — 當前任務狀態

**更新：2026-09-12｜現行票：`SPLITUNIFY 收尾`（大；RISK a,b,c）｜**b8 已結案**（三輪三家審碼、零回歸）｜**現在：b9 規格 `D-002` 第四次修訂完成（commit `3973d124`），R4 閉合輪已派出****

## b8 交付內容（皆已 commit＋push；最新 `29582d96`）
- `SplitPlan` 新增 `row_index_local`／`row_time_fingerprint`（相容 default）；`__post_init__` 對兩個 row 欄 defensive copy ＋ `np.frombuffer(bytes)` 唯讀。誠實邊界：`pickle`／`deepcopy` 還原仍可寫。
- 共用助手 `split_preview.epoch_ms_from_index`／`build_row_time_fingerprint`（該模組不匯入專案模組，無循環）；`split_projection._index_as_ms` 委派之。
- `contracts.attest_row_index_local`：前置合法性閘（整數型／等長／範圍／無重複／嚴格遞增）＋時間序往返。三個 producer 全數接上。
- `derive_event_split_from_plans` 改分派器＋`_derive_single_symbol`；per-symbol 迴圈與 `_manifest_subset`；Task 8.3 逐標的門檻。
- 投影端只讀 `row_index_local`、缺欄 fail-closed 不回退、入口指紋重驗。
- 🔴 **2026-09-12 修掉上一批的自傷缺陷（producer 端指紋時鐘）**：`split_per_symbol` 的 `ts` 與 `ic_filter_orchestrator` 的 `features_df.index` 皆為 **epoch 秒**，上一批卻直接餵給毫秒正規化器 ⇒ `test_split_per_symbol_golden` 與 `tests/api/test_splitunify_disclosure` 全紅，**IC 實跑路徑亦會被自己的守衛擋死**。修法＝指紋時鐘取該 producer **模組內既有的那一支**，不新造第二套換算：`split_per_symbol` 與其 `time_bounds` 共用 `_coerce_timestamp_array`；`ic_filter_orchestrator` 之 `time_bounds` 走 `_coerce_timestamp_array`、指紋走該檔切邊界時**已經在用**的 `_normalize_ic_time_index`——🔴 **兩者是不同函式**（grok R1 指正我先前「同一支」的措辭不精確），但對 epoch 秒皆以 `unit="s"` 解讀，端點實測相等（`ms0 == tb0_ms`）；`ic_split_adapter` 之 `ts` 本為 `datetime64`，維持原樣。
- 測試：目標測試面 **738 passed**；`freeze_splitunify_golden.py` 回報 **GOLDEN OK**（digest 未位移）。新增 `-k time_bounds_inconsistent`，使 `time_bounds` 同源閘不因指紋閘上線而變成沒有測試會紅的死碼。

## b8 未完成
- mutation 自證做完：22 條執行、22 條皆被測試抓到；`M-SU-D1-23` 在單標的 golden fixture 下**不可觸發**（該 fixture 之 `row_index_local` 與 `row_index` 逐值相同），已具名為 `needs-research`，交審碼三家裁定是否值得為它把 golden 改成兩標的交錯重凍。收據：`handoffs/run_receipts/20260912-splitunify-b8-mutation-selfcheck.md`。過程撈出兩個**真實測試缺口**並已補：①`feature_index_by_symbol` 缺 symbol 時改成丟棄，原本一條測試都不會紅 ②重排那條只寫 `pytest.raises(ValueError)`，被 `time_bounds` 閘先擋而失去鑑別力，已改為指名「非嚴格遞增」。
- **審碼 R1 已收**（session `20260911-splitunify-b8-review-r1`、`round_id=67fe8449`、債已清）：composer／grok `proceed` 零 P0／P1；**codex `blocked`**，開兩條 P1＋一條 P2。三條主委獨立複驗後**全部成立**並已修補（commit `5ac5bd8d`）：①dtype 閘被前置 `astype(int)` 繞過（float64 序號靜默救活；`M-SU-D1-22` 測的是 attest 函式、不是 producer 路徑，所以抓不到）②未選列 `NaT` 無人擋卻參與 rows 單位 purge 計數 ③投影 docstring 仍用全框座標。收斂檔 `handoffs/reconcile/20260911-splitunify-b8-review-r1/synth.md`（五條逐條歸戶、completeness PASS）。
- **R2 閉合輪已收**（`round_id=d5bda4d6`，債已清）：R1 三條由 codex（原提出方）與 composer 判定 `CLOSED`；但三家**一致**再開一條——我在 R1 修補時引入的新缺陷：`ic_split_adapter._with_row_positions` 的 NaT 閘 `raise AlignmentViolationError` 卻**未匯入**該類別 ⇒ 觸發時拋 `NameError`，而它不在 `ValueError` 階層、會穿透呼叫端既有的 except。嚴重度 grok 判 P1、另兩家 P2，依「分歧採較嚴版」以 P1 處理。已修（commit `655d52d4`）並補兩條 adapter 路徑測試。🔴 **漏網根因**：上一批只補 `split_per_symbol` 路徑的 NaT 測試，adapter 路徑無測試 ⇒ 缺 import 不會讓任何一條變紅。**同一道閘在兩條 producer 路徑上各需一條測試**。🔴 **我的查證方法錯誤**：當時 grep 該類別名確認可用，命中的卻是我自己剛寫的那行 raise——驗證符號可用要看 import 區或實跑，不能只看名字出現過。
- **R3 閉合輪已收**（`round_id=aefcb7fd`，債已清）：三家皆 `proceed`，各自閉合自家 R2 finding，僅各開一條 P3 sentinel。grok（R2 原提出方）依章程 §B8 重跑自己的反例確認 adapter NaT 閘現拋 `AlignmentViolationError` 且訊息含 `NaT`；三家對「缺 import／單路徑閘／golden 位移」三面主動攻擊未再開洞。收斂檔 `handoffs/reconcile/20260911-splitunify-b8-review-r3/synth.md`，Verdict：可合併。
- **三輪總結**：R1 codex `blocked`（兩 P1＋一 P2，主委獨立複驗全部成立）→ 修補 → R2 三家一致再開一條（主委修補時引入的未匯入例外，依「分歧採較嚴版」以 P1 處理）→ 修補 → R3 三家 `proceed`。🔴 **沒有任何一輪靠「無 finding」停輪**，三輪皆有具名攻擊面。
- **回歸判定：本批回歸為零**。`tests/momentum`＋`tests/api` 跑到約 2,200 條時收窄（FDR 模擬單條數十分鐘），對浮現的 10 筆紅做**對照實驗**：把 b8 動過的六個生產檔整組 `git checkout 0190c918`（b8 前一筆）後重跑，10 筆**全數同樣紅**，還原前後各以 `grep -c row_index_local` 驗證 checkout 真的生效。10 筆分屬 1c-FR allowlist、IC cut1 golden、persist redirect、ichc contract／golden、Optuna，皆為既有紅。

## 坑（沿用＋本日新增）
- impl token 900 秒過期即須重領；生產碼 commit 必帶 `Ticket-Batch: 20260911-SPLITUNIFY/b8`；task-id／session 日期前綴一律沿用 `20260911-SPLITUNIFY`（跨日不得改）。
- 🔴 **G-7 是 warn-only**（2026-09-05 使用者裁定，理由逐字寫在 `scripts/git_hooks/commit-msg:20-24`）——commit 後看到它的提示**不必**補 `Governance-Scope` trailer。本日我誤判為「空心閘」並據此 amend，白繞三趟。
- 產品碼一律用**限定路徑**提交（`git commit -F msg -- <路徑…>`）：不限定會把還在暫存區的 brief 一起帶進宣稱檢查而被擋。目前 `handoffs/20260912-SPLITUNIFY-D001-CLOSURE-R11-BRIEF.md` 仍在暫存區且第 51 行缺 VERIFY 背書。
- `handoffs/*` 已被 `.git/info/exclude` 排除，新交件檔須 `git add -f` 才入版。
- 🔴 **zsh 預設不對未加引號的變數做分詞**：`FILES="a b c"; git checkout <sha> -- $FILES` 會把整串當成**單一路徑**，git 報 pathspec 不符而**什麼都沒還原**——我據此跑完 150 秒對照實驗才發現是空的。批次路徑一律逐一列出，或加 sanity 檢查確認狀態真的變了。
- commit 訊息含「全綠／綠燈／已驗／真紅」等宣稱用語會被 `verification_claim_check.py` 擋，且 commit **零豁免**（不能用 `VERIFY-EXEMPT`）。
- 🔴 **orchestrator 的 float 秒地雷**（grok R1 實跑）：`features_df.index` 若為 **float** 秒，`_normalize_ic_time_index` 解成 1970、`_coerce_timestamp_array` 解成 2023，兩路**值分叉**；目前不構成存活缺陷，因為 `holdout_boundary` 會先 raise「looks like epoch seconds」而不產出 plan。日後若放寬該前置閘，這條會立刻變成真缺陷。
- 戳記外置於 reconcile synth ⇒ 對 `docs/*.md` 直接跑 `reconcile_stamps_check.sh` 必 rc=1，不是治理真空。

## 下一步
第 8 批已結案（三輪三家審碼收斂）。**第 9 批偵察已完成並清債**（session `20260911-splitunify-b9-consult-r1`、`round_id=3b6109c8`；三家委員＋主委自產共 18 條，收斂為六群、17 條入 roster）。

🔴 **偵察兩項關鍵結論，直接改寫第 9 批的前提**：
① **D-001 第 189 行所列「六個下游單鍵面」是不完整清單**——四家合併盤點後約 15 處（另含 `counterexample_classifier`／`candidate_ledger`／`event_split.build_time_clusters`／`ic_feed` survivor 六鍵／`frontend/src/lib/types.ts`／`frontend/src/app/search/page.tsx:825-835` 的 event_id Map／`tests/golden/splitunify/{splitunify_golden,clusters_oracle}.json`）。SPEC 觸及面**不得沿用那六處**。
② **D-001 第 11／189 行「未完成前多 TF 同批維持 fail-closed」與實況不符**——主委探針與 codex Probe A 逐值一致（4 列輸入、2 列輸出、`UNSELECTED_ROWS_DROPPED 2`）：現行只擋「同一 TF 下事件重複」與「選定 TF 下缺 cutoff」，**多 TF 同批不擋，未選中的列靜默丟棄且不揭露**。該句須於 SPEC 更正。

**`docs/SPLITUNIFY_SPEC.D-002.md` 已建立**（BASE `1be5be3f`、PREDECESSOR D-001；`doc_format_precheck` rc=0）。範圍策略已定：**揭露先行（Phase 9A）＋ 複合鍵主體（Phase 9B）**，同一份 SPEC 分兩階段——揭露成本極低且立刻消除「靜默丟棄」的誠實性缺陷，不必等 15 處全改完。D-002 首要義務是**更正 D-001 第 11／189 行**那兩處與實況不符的陳述（義務區塊 `D-002-CORRECT` (1.1)–(1.4)），並把觸及面由六處重寫為 15 處（分三層、逐處附碼證與「會報錯 vs 靜默錯」分類）。另順道處置 `M-SU-D1-23`：本延伸既必然動 golden，fixture 改兩標的交錯使該 mutation 可觸發。

**D-002 找碴 R1 已收**（session `20260911-splitunify-b9-review-r1`、`round_id=86e88917`）：🔴 **三家全數 `blocked`**（codex 5 條 P1、composer 2 條 P1、grok 3 條 P1；共 15 條）。收斂為七群、**全部採納、零駁回**，收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r1/synth.md`（歸戶與 completeness 皆 PASS）。

🔴 **其中兩條是主委完全未想到的**：
① **`timeframe` 雙語意**（`CODEX-R1-P1-03`）——`canonical_event_id(symbol, timeframe, t0)` 用**觸發** TF，而 `per_tf.timeframe` 是 **feature** TF；同名不同義，複合鍵／purge 換算／同簇規則全建立其上，不先命名分離則整份 SPEC 無法驗收。
② **同事件多 TF 未規定同側**（`GROK-R1-P1-03`，本輪最嚴重）——D-002 只寫「同簇」，但**同簇不等於同側**：1h 進 train、4h 進 test 時，仍偏事件級的消費者會靜默組成**非法 OOS 樣本**。須明定「同事件所有 TF 必須同側，否則整事件 purge」並配可證偽測試。
另有一條屬 SPEC 內部不自洽：我在 §C 寫了「事件數與列數不得混用」，卻**沒有**在 Task 9.3 指派對應修改（三家全中）。

**D-002 已依七群修訂**（commit `d69b471b`；`doc_format_precheck` 與 `spec_xref_check --synth` 皆 rc=0）：新增 `D-002-C0`（`trigger_timeframe`／`feature_timeframe` 分名，複合鍵明定為 `(event_id, feature_timeframe)`）、`D-002-C3`（同事件所有 feature TF **必須同側**，異側則整事件 purged，檢查落在投影端）、`D-002-C6`（`n_train`／`n_test`／`n_purged` 定為**事件數**，列數另立新名）、`Task 9.4`（記帳與報告鏈專責）；觸及面 15 → **16 處**（新增第四層記帳／報告鏈）；`Task 9.3` 由形狀規則改為**逐處列名**（明寫 `feature_materialization` 折疊點在 `groupby+update`、event-level 表粒度不變）；§G 拆為 (G-1)(G-2)(G-3)；mutation 6 → **18 條**逐處對應。

**R2 閉合輪已收**（`round_id=052ad9bc`，債已清）：**composer `proceed`**（R1 三條全閉）；**grok 六條全閉但新開 2 條 P1**；**codex 閉合五條、`R1-P1-06` 未閉並新開 8 條**。新開 11 條收斂為**九群、全部採納零駁回**，收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r2/synth.md`（歸戶與 completeness 皆 PASS）。

🔴 **九群中的關鍵四條**：
① **核心目標漏寫**（`CODEX-R2-P1-04`，最嚴重）——9B 只加 schema 欄位與下游改法，**沒要求 producer 停止 `selected_timeframe` 單選**並輸出全量 keyed rows ⇒ 整批做完 `SU-RESID-2` 的丟棄行為原封不動。
② **同側約束被攻破**（`CODEX-R2-P1-01`）——資料契約只要求各 cutoff `<= decision_at_ms`，**未**要求不同 feature TF 之 cutoff 對齊，故合法事件可能天然異側；C3 一律 purge 會誤殺。須先定義「可比時點」或改為以 trigger TF 之側為準並揭露。
③ **三條自相矛盾**——(0.5) 禁裸 `timeframe` 卻自己定了 `discarded_per_tf_rows_by_timeframe`；要 `clusters` 加欄又要它維持事件級；觸及面列出已刪除的 `D-002-C1`／`C2`（已修）。
④ **量詞一刀切不成立**（`CODEX-R2-P1-03`）——`baseline` 的 `n_test` 是實際模型輸入樣本數，不能與事件數混為一談。

🔴 **主委自評**：`obligation_block_check.sh` 是我自己建的閘，這次修訂我只跑了格式與 xref **沒跑它**，結果 21 條義務項行型全部不合白名單、5 處裁決編號寫在正文（違反我自己定的「項目中只留最新版本」）。已全數修畢，該閘現為 rc=0。

**D-002 第三次修訂已完成**（commit `7bd865ff`；三道閘 `obligation_block_check`／`doc_format_precheck`／`spec_xref_check --synth` **皆 rc=0**）：新增 **`Task 9.2`（producer 停止 `selected_timeframe` 單選、輸出全量 keyed rows）並標為本批核心**（原 schema 工作降為 `Task 9.2a`）；`(3.1)` 加「可比時點」前提使同側判定不再誤殺；`(3.2)` purge 字面定為沿用既有 `interval_crosses_split_boundary`、不新增值集；`(6.2)` 量詞改逐消費者（`baseline` 之 `n_test` 維持樣本數語意）；`clusters` 定案**不加** `feature_timeframe`、維持事件級；新增 `(0.6)` 既有欄位保留／新增欄位分名，summary 新鍵改名 `discarded_rows_by_feature_tf`；mutation 改表格共 **20 條**，每列具完整 ID 與應紅之測試。

**R3 閉合輪已派出**（session `20260911-splitunify-b9-review-r3`、brief `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R3-BRIEF.md`）。brief 已補明 R1／R2 各踩過一次的裁決欄規則：**`BLOCKED-BY` 與 `CLOSED` 都只列本檔本家族 ID，跨輪未閉條目須以新 ID 重開**。

**R3 已收**（`round_id=d414d8c3`）：**composer `proceed`**；**grok `blocked`**（R2 兩條全閉、新開 3 條 P1）；**codex `blocked`**（零條閉合、9 條 P1＋2 條 P2，其中四條明指「R2 某條未閉」）。15 條收斂為**七群、全部採納零駁回**。

🔴 **主委已逐條自驗四項可機械查證之指控，全部成立**：
① `probe_b9_multitf.py` **不在 repo**（`git ls-files` 追蹤數 0）⇒ §A 的 FACT-RECEIPT 不可重跑，直接違反驗證保真度鐵律。**已修**：探針移入 `handoffs/20260911-splitunify-b9-probe-multitf.py`（commit `d9196037`）並實跑確認四組輸出與記載一致。
② `docs/SPLITUNIFY_TODO.md:470` 仍標 `needs-research`，狀態 SoT 未同步。
③ 🔴 **核心目標仍未達成**：`pipeline.py:747` 為 `build_event_keys(receipts, selected_timeframe=str(selected_timeframe))`、**必傳**——我上一輪自以為補上的 `Task 9.2` 只改了被呼叫端，唯一生產 caller 沒動，生產路徑的靜默丟棄**原封不動**。
④ `split_projection.py:441-424` 之 `event_id` 重複 fail-closed guard 排在同側判定**之前**，使 C3 的兩條測試不可執行（順序問題，我完全沒想到）。

🔴 **收斂性判斷**（為何不引用「停在無法收斂處」）：三輪 findings 有明確收斂方向且家族間有交集（codex 與 grok 獨立指向同一組：核心目標、可比時點、Task 9.2 範圍），非各說各話或無限窮舉；R3 九條 P1 中四條是「R2 未閉」，成因是**主委修訂不徹底**而非委員擴張要求 ⇒ 續修。

**D-002 第四次修訂已完成**（commit `3973d124`；三道閘 `obligation_block_check`／`doc_format_precheck`／`spec_xref_check --synth`（r1/r2/r3）**皆 rc=0**）。七群落點：①`Task 9.2` 納入 `pipeline.py:747` 並逐字寫出現行呼叫，另要求**移除 `str()`**（留著會把 `None` 變字面 `"None"`，等於白改）②`(3.1)` 改為**直接給定義**＝事件級錨定（split 側一律由 `decision_at_ms` 決定，各 feature TF 之 cutoff 只用於取特徵、不參與判側 ⇒ 同事件恆同側為**結構性保證**）③🔴 **連帶修訂 R2 裁決**：`(3.2)` 異側處置由「整事件 purged」改為 **fail-closed `AlignmentViolationError`**——R2 該裁決的前提是「異側屬合法」，(3.1) 消除該前提後異側即實作缺陷，purge 會把缺陷偽裝成樣本流失；既有 `interval_crosses_split_boundary` 維持原義不動 ④`Task 9.2a` 定案兩道既有重複 guard 改**複合鍵唯一**判準且**先於** C3 同側檢查 ⑤§V 補 purged 複合鍵唯一與 `n_event_tf_rows_purged`、C3 斷言改正例＋反例成對 ⑥`Task 9.1` 逐處指名 `api/routes/case.py:487`／`case_import_service`／`EventAnalyzeResponse.summary`（`Dict[str, Any]` ⇒ 新鍵自動穿過但**零型別保證**，須寫明列鍵名的契約測試）／`EventTablesPanel.tsx:347,361`；`Task 9.5` 指名 `freeze_splitunify_golden.py` 之 `_plans()`／`_event_keys()`／`_build_actual()` ⑦`M-SU-D2-19` 改反向 mutation、`14`／`15` 應紅測試隨 (3.2) 改為 raise ⑧§N 補 TODO §E 狀態同步時點。

**R4 已收**（`round_id=492855fb`，債已清）：**codex 拒審零實質**（駁回，見下）、**composer 3 條 P1**、**grok 4 條 P1 並閉合自家 R3 三條**。8 條歸五群、**7 條採納 1 條駁回**，收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r4/synth.md`（歸戶、completeness、xref 皆 rc=0；xref 對本輪處置欄驗到 21 個概念）。

🔴 **G1 是 grok 獨得、我與 composer 都沒看到的一條**：`pipeline.py:723-732` 的 `given = [k for k, v in projection_args.items() if v is not None]` 要求四參數同時非 `None` ⇒ **就算照 `Task 9.2` 移除 `str()` 並傳 `None`，也會在抵達 `build_event_keys` 之前 fail-closed**。這是同一個核心目標**第三次**以不同形態沒補到（R3：沒改 caller → R4：四參數閘先擋死）。

🔴 **G2 兩家撞題**：`(3.1)` 定死以 `decision_at_ms` 判側，卻**沒有任何 Task 指向真正在判側的碼**——`split_projection.py` 全檔 `decision_at_ms` 命中數為 **0**，`:530-553` 仍逐列取 `feature_cutoff_ms`。**義務寫進規格 ≠ 施工單派到落點**，與 G1 同型。

**駁回 `CODEX-R4-P1-01`**（以上游收斂檔未戳記為由拒審）：`AGENTS.md:40` 逐字為「**動工前**…**不動工**」而本輪 brief 明列禁改碼禁改 SPEC；且本批 R1／R2／R3 收斂檔之 `RECONCILE-STAMP` 數**皆為 0**，該家在那三輪分別交付 **6／8／11** 條實質 finding ⇒ 同情境前後不一致。該讀法會使戳記與審查互為前置、流程無法啟動。該家本輪**欠一輪**，併入 R5。

**D-002 第五次修訂已完成**（commit `d073ce7f`；obligation／format rc=0，xref 對 r1–r4 四份 synth 皆 rc=0）：`Task 9.2` 範圍再加四參數閘與其 docstring、驗收改**端到端**經 `EventSamplePipeline.run`；**新增 `Task 9.2b`**（指名 `split_projection.py:530-553` 改以 `manifest.table` 之 `decision_at_ms` 每事件定側並廣播，答案窗 purge 改按事件側）；§V 增端到端全量斷言與 `selected_timeframe=None` 不 raise，原 schema 句改掛 `Task 9.2a`；`(5.2)` 改寫為落地後契約；mutation 20 → **23 條**；觸及面補列 `Task 9.2b`。

🔴 **`Task 9.2b` 之可行性已由主委自驗（不是照抄委員的話）**：①`_derive_single_symbol` 簽名第 337 行逐字 `manifest: EventManifest`，**確在作用域**；②`dedupe.py:107` 逐字 `"decision_at_ms": ev["decision_at_ms"].astype("int64").to_numpy()`——`manifest.table` 之該欄是**顯式建構且固定 int64**（非 pass-through 僥倖），與 `train_ms`／`test_ms` 比較無型別落差；③`_manifest_subset`（`split_projection.py:671-681`）只濾列不砍欄，逐 symbol 切片後該欄仍在。**誠實邊界**：`build_event_manifest` 只對 `label_start_ms`／`label_end_ms` 做缺欄 fail-closed，**未**對 `decision_at_ms` 設防；且 `_EVENT_COLS`（`alignment.py:31`）這個常數**沒有任何地方拿它驗欄**（grep 零命中）⇒ `Task 9.2b` 仍應配一條「取不到 `decision_at_ms` 即 fail-closed」的前置斷言，不得假設欄位必在。

🔴 **G1「不改切分數學」亦由主委自驗**：`selected_timeframe` 在生產碼**只有兩個去處**——`pipeline.py:725`（四參數閘）與 `pipeline.py:747`（傳給 `build_event_keys`）；`split_projection.py` 內全部集中於 `:259-297` 之過濾與三道 fail-closed，**無任何記帳／物化／統計路徑讀它** ⇒ 降為可選不會有連鎖影響，該宣稱成立。**順帶撈到一條四輪四家都沒提的殘留**：`split_projection.py:271` 之 docstring 逐字寫「每個事件在 `selected_timeframe` 下必須**恰有一列** `per_tf`」，與 `Task 9.2` 之全量複合鍵**直接互斥**——與 `(5.2)` 同型的舊語意，但住在**程式碼註解**裡；`Task 9.2` 須把它列入必改（否則實作者讀 docstring 會照舊語意寫）。

🔴 **主委在 R5 等待期自驗時抓到的一條（四家四輪都沒提）**：`_PURGE_REASON`（`interval_crosses_split_boundary`）在 `split_projection.py` **兩處共用**——`:541` 是答案窗跨界（`in_train and label_end_ms >= test_start_ms`），`:553` 是 else 分支「cutoff 既不在 train 也不在 test」。後者**不是**跨界，語意完全不同。⇒ `D-002` `(3.2)` 寫「既有 `interval_crosses_split_boundary` 維持原義（標籤區間跨越 split 邊界）」與**現況不符**：該字面現在就已承載兩種語意，第六次修訂須處理（要嘛承認雙語意並分別定義，要嘛在 `Task 9.2b` 一併分流）。

🔴 **探針二推翻了下面那條結論（保留原文供追溯，但以本段為準）**：`venv/bin/python handoffs/20260912-splitunify-b9-probe-decision-vs-cutoff.py` 實跑四個真實事件（12h 觸發＋4h／12h 雙 feature TF）：**`decision_at_ms` 與 `cutoff_12h` 逐值相同（delta 全為 0）**，且 `decision_at_ms` 落在 12h open 網格 **4/4**、4h open 網格 **4/4**。成因：`_select_cutoff_idx` 取 `max{close ≤ decision_at}`，而 close 恆等於下一根 open ⇒ `decision_at` 本身落在網格點時，cutoff 恰等於它。⇒ **「系統性位移一根」不成立**；`Task 9.2b` 之集合成員判定**可直接沿用**，不必改區間比較。**誠實邊界**：`decision_offset_bars` 為整數根故 `decision_at` 結構上必落網格點；但若 `feature_index` 用的是**與觸發 TF 不同**的網格，仍可能落空 ⇒ `Task 9.2b` 仍須配「`decision_at_ms` 不在 `index_ms` 集合中即 fail-closed」之守衛，不得靜默 purge。

（以下為探針一之原始結論，**已被上段更正**，保留供追溯）**探針已跑，刻度問題定案——`Task 9.2b` 之改法必須改寫**（`venv/bin/python handoffs/20260912-splitunify-b9-probe-clock-alignment.py`，真實 ETHUSDT 12h bars 共 1696 根）：`close[i] - open[i] = 43200000`、**`open[i+1] - close[i] = 0`**、`close[i] == open[i+1]` 成立 **1695/1695**、close 落在 open 集合 **200/200**。⇒ 本專案 bar 採**右閉慣例**（一根之 close_time 即下一根之 open_time），現行 `cutoff in train_ms` 命中的是**下一根**之刻度，即判側實際以「特徵可用之後的那一根」為準。**照 `Task 9.2b` 現文直接換成 `decision_at_ms`（本根 open）會系統性往前位移一根**，在 train/test 交界處改變歸屬。第六次修訂須：①明寫刻度轉換（`decision_at_ms` 須映射到其**對應的 cutoff 刻度**再比對，或改為區間比較 `decision_at_ms < test_start_ms`）②配一條「位移一根」之可證偽斷言（改壞即紅）③`M-SU-D2-22` 之應紅測試隨之指名交界事件。**四輪四家皆未觸及此層**——它要實跑真實 bar 網格才看得見。

（原始碼證，供追溯）：`alignment.py:206` 之 `cutoff = int(sub_ct[idx])` 取自 **`close_time_ms`** ⇒ `feature_cutoff_ms` 是 bar **close**；`alignment.py:157` 之 `decision_at = int(ot[decision_idx])` 取自 **`open_time_ms`** ⇒ 是 bar **open**。兩者**不同刻度**，而現行判側是 `cutoff in train_ms`（集合成員）。⇒ `Task 9.2b` 若直接把它換成 `decision_at_ms in train_ms` 有**系統性落空或位移一根**的風險。`tests/momentum/event_samples/test_splitunify_wiring.py` 之 `_canonical()` 用 `open_time_ms` 當 `feature_index` 而斷言 `cut in train_ms` 卻通過 ⇒ 只能實測解釋。探針已入版：`handoffs/20260912-splitunify-b9-probe-clock-alignment.py`。**第六次修訂前必須先跑它**。

🔴 **主委在這段自驗裡連犯兩次同型查法錯誤（記著防再犯）**：①`grep -rn "run(" … | grep "train_plan"` 要求**同一行**，而實際呼叫跨多行 ⇒ 得出「零命中」並當成事實（import 那條同理，`pipeline.py:25` 就是多行括號 import）；②`grep -rl … | head -12` **截斷**清單，tests 的檔案被切掉 ⇒ 又得出一個假的「矛盾」。**兩次都是用不可靠的查法得出「零命中」就下結論**——與記憶裡「驗 scanner 勿 tail 截斷」同型。判準：凡結論是「某物不存在」，查法必須先自證完備（不截斷、不要求同一行、必要時列檔案而非列行）。

**R5 已收並收斂完畢**（`round_id=ee68cb30`，債已清）：三家皆 `blocked`，**codex 補完了 R4 欠的完整審查**（5 條 P1＋1 條 P2，並逐條交代 R3／R4 閉合）；composer 2 條 P1（R4 三條全閉）、grok 3 條 P1（R4 四條全閉）。11 條歸八群、**全部採納**。收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r5/synth.md`（歸戶 rc=0、completeness rc=0、xref 處置欄 23 個概念全對上）。

🔴 **核心目標第四次以不同形態沒補到（三家獨立撞題）**：`build_event_keys` 內部 `split_projection.py:291-303` 之 `event_level.merge(..., validate="1:1")` 在全量多 feature TF 必 `MergeError`；且輸出欄 `timeframe` **取自 `event_level`**（觸發 TF），merge 只帶 `feature_cutoff_ms` ⇒ 縱使放寬 `validate`，兩列也會得到**相同** TF 值而使複合鍵碰撞。四次形態：只加欄位 → 沒改 caller → caller 前的四參數閘 → **閘後 producer 內部的 merge 與輸出欄**。

🔴 **`(3.2)` 也是「有義務無落點」**（與 R4 的 `(3.1)` 同型）：`AlignmentViolationError` 在本 SPEC 只出現於義務 L48／§V／mutation，**任一 Task 改法均未指名**在何處插入同側檢查 ⇒ 實作者可做完廣播而永不寫 fail-closed，`M-SU-D2-14`／`15` 無碼可紅。

🔴 **我的探針結論被 codex 正確限縮**：探針二只覆蓋「特徵網格為觸發 TF 之整數倍」（12h 觸發配 12h／4h），故 `decision_at_ms` 必命中；codex 給出反例——1h open 非 4h open 者 **15,264／20,352** ⇒ 特徵網格**粗於**觸發 TF 時集合成員判定會大量落空。`Task 9.2b` 已改為**不等式**判準＋界外 fail-closed。

🔴 **`Task 9.1` 的落點是「查了行號沒查可達性」**：指名的 route 之 service 現行**永遠走 `run_event_study_only`**（`case_import_service.py:1592-1626`），拿不到 canonical universe 也就沒有 `discarded` 來源。**指名落點 ≠ 該落點走得到**。

**D-002 第六次修訂已完成**（commit `0b4d905a`；obligation／format rc=0，xref 對 **r1–r5 五份** synth 皆 rc=0）：八群逐條落地；mutation 22 → **25 條**（前一版宣稱 23 而實列 22，沿革「20→23（新增 21、22）」本身即算術錯誤；本版主委**自數**表列 25、ID 01–25 連續後才宣稱）。

🔴 **主委自產（R6 等待期自驗）：第五層存在，但方向與前四輪相反——是我的 `Task 9.3` 派工過度，不是漏派**。碼證：`feature_materialization.py:93-131` 之 `groupby("event_id")` ＋ `row_vals.update(...)` 是**設計上的橫向合併**（同事件各 feature TF 的特徵欄拼成**一個**特徵向量）；`_combined_columns:22-32` 逐字為「多 TF 特徵欄名合併；**衝突 ⇒ loud 拒**」——欄名**不帶 TF 前綴**，而是要求各 TF 欄名互斥。⇒ `Task 9.3` 現文要求改為 `groupby(["event_id","feature_timeframe"])` ＋ MultiIndex，會把「一事件一個完整特徵向量」變成「一事件多列、每列只有自己 TF 的欄、其餘 NaN」，**破壞既有設計並讓 ML 輸入充滿 NaN**。**根因是範圍誤判**：切分歸屬層要複合鍵（`SU-RESID-2`），特徵物化層要**維持**一事件一列——我把兩層一起派工了。第七次修訂須改寫 `Task 9.3` 對 `feature_materialization` 之改法（改為「維持事件級橫向合併**不動**，僅在 `merge validate` 與 `set_index` 之粒度斷言上確保不因多列而靜默覆蓋」），並於 R6 收斂檔以**主委自產條**提出、標明非委員意見。

🔴 **主委自產（續）：`Task 9.3` 的 16 處清單把「事件級表」與「複合鍵表」混在一起派工，至少四處判定錯誤**（皆已取碼證）：
- `feature_materialization:93-131`＋`_combined_columns:22-32` — **橫向合併是設計**（一事件一列，各 feature TF 欄名互斥、衝突即 loud 拒）。派工要求改 `groupby(["event_id","feature_timeframe"])`＋MultiIndex ⇒ **破壞特徵矩陣語意**，ML 輸入變多列＋大量 NaN。**應改為維持事件級**。
- `dedupe:122-129` — `cluster_first` 以 `dedupe_cluster_id` 分組取 `observation_interval_start_ms` 最早者，是**事件級去重**（每重疊簇留一個事件）。派工要求改 `(event_id, feature_timeframe)` 粒度 ⇒ 同事件多 TF 各自被保留，**破壞去重語意**。**應維持事件級**。
- `ic_feed:83,109` — `timeframe` 是函式**必填參數**，`per_tf[per_tf["timeframe"] == timeframe]` **先過濾單一 TF 再** `set_index` ⇒ 索引本就唯一。**單一 TF 是設計、非缺陷**，`D-002-C5` 將其列為待改消費面屬**誤列**。
- `tables.py:214,229,234,257` — `ev` 為 `event_level`、`cl` 為 `clusters`（已定案維持事件級）⇒ 這些 `.loc[eid]` 本就對事件級表操作，**不受複合鍵影響**，同屬誤列。
- **真缺陷但改法錯**：`pattern_bridge:125-127` — `lab_by_id[e] == "train"` 是事件級消費（`X_all` 亦為事件級），複合鍵後 `set_index("event_id")` 索引重複、`lab_by_id[e]` 回傳 Series，`== "train"` **靜默變成 Series** ⇒ 確為缺陷；但正確改法是「**去重取唯一側、不唯一則 fail-closed**」（依 (3.1) 同事件恆同側），**不是**改成複合鍵索引。
**續驗（同批，碼證齊）**：
- `baseline.py:105-109` — `test_ids` 取自 `assignments`（複合鍵後同事件兩列），但下一行 `features_at_decision.index.intersection(pd.Index(test_ids))` 之 `intersection` **對 Index 會去重** ⇒ `X`／`y` 仍事件級、**行為不會壞**；其 `n_test` 語意問題屬 `Task 9.4`（H4 已處理），**不需**改複合鍵。
- `counterexample_classifier:52-62` — 迴圈為 `for rec in events.to_dict("records")`（**事件級匯入表**），`ev_receipt` 亦事件級 ⇒ **誤列**。
- `candidate_ledger:139-161` — 迴圈為 `for eid in sorted(signaled)`，`signaled` 是 `set(...)`（**集合本身去重**），`rec`／`ev` 皆事件級 ⇒ **誤列**。
- 前端 `search/page.tsx:825-835` — Map 鍵為 `canonicalEventId(symbol, timeframe, t0)`，來源是使用者上傳 CSV 之**原始列**，`timeframe` 取 `row.timeframe || searchParams.timeframe`＝**觸發** TF；一事件在原始檔只有一列 ⇒ **誤列**（(5.4) 所述「後者覆蓋前者」是「同一 CSV 有重複列」之情形，與多 feature TF 無關）。
- golden — `splitunify_golden.json` 之 `g1_membership` 為 train/test/purged 之 **event_id 清單**（複合鍵後同事件兩列會被清單去重而看不出差異）⇒ **確需擴維**；`clusters_oracle.json` 以 `event_id` 為 fixture 鍵（簇已定案事件級）、`report_int_keys.json` 為報告整數葉鍵集（與事件無關）⇒ **兩者不動**。

**末三處（16 處至此全部讀完）**：
- `ic_feed.event_context_from_windows:56-60` — `rows` 取 `event_id`／`label_start_ms`／`label_end_ms` 三欄按 `event_id` 排序後雜湊，**不含任何 TF 欄**，是事件集合之身分 ⇒ 列為待改消費面屬**誤列**；`M-SU-D2-19` 定為反向 mutation 正確。🔴 **但另有前置條件**：複合鍵後若把同事件多列 `WindowRow` 全餵進來，`rows` 會出現重複三元組而改變雜湊 ⇒ **餵入端須先去重**（與「不得改成含 TF」是兩件事，須分開寫）。
- 前端 `types.ts:2951` `batch_facts: EventBatchFacts` — **批次級**事實（`control_kind_values`、`decision_offset_bars_record_values` 等批內彙總），與事件粒度無關 ⇒ **誤列**。
- `test_splitunify_wiring.py:103-104` — `dict(zip(per_tf["event_id"], per_tf["feature_cutoff_ms"]))` 與 `dict(zip(assignments["event_id"], ...))`，複合鍵後同事件多列**後者覆蓋前者**，且會讓「歸屬與邊界對證」那條斷言只驗到其中一個 TF ⇒ **真缺陷，須改複合鍵映射並逐列驗**。

⇒ **16 處全部逐處讀完之最終分類**：**九處誤列**；**一處派工過度**（`feature_materialization`，應維持事件級橫向合併）；**一處真缺陷但原改法錯**（`pattern_bridge`，應為去重取唯一側＋不唯一 fail-closed）；**三處確需改**（`assignments`／`purged` 組裝、golden `g1_membership`、wiring `dict(zip)`）；**一處需分開寫**（`ic_feed` survivor：不得含 TF ＋ 餵入端須去重）；**一處屬 `Task 9.4`**（`pipeline` 記帳）。

（以下為前十處之逐條碼證）⇒ **十處已逐處讀完之結論**：**七處誤列**（`ic_feed`、`tables` 兩處、`counterexample_classifier`、`candidate_ledger`、前端 Map、`clusters_oracle`＋`report_int_keys`）、**一處派工過度**（`feature_materialization`）、**一處真缺陷但改法錯**（`pattern_bridge`，應為「去重取唯一側、不唯一 fail-closed」）、**一處確需改**（`g1_membership`）。第七次修訂須**逐處重新分類**：事件級（維持）／複合鍵（改）／事件級但需去重取唯一值（三類），`D-002-C5` 之 16 處清單同步更正。此為主委自產，須於 R6 收斂檔標明非委員意見。🔴 **根因**：我列該清單時以「有無 `set_index("event_id")` 之形狀」為判準，**未逐處問「這張表的一列代表什麼」**——而 `Task 9.3` 正文我自己寫著「不得用凡看到某索引一律改這種形狀規則」。

🔴 **R6 兩家已交（codex 未交），三條主委已獨立複驗、全部成立**：
- **我第六次修訂的不等式判準自己引入新缺陷**（composer／grok 獨立撞題）：`split_preview.py:313-316` 之 `train_rows = arange(0, split_point)`、`test_rows = holdout_test_row_index(..., purge_gap, embargo)` ⇒ `purge_gap+embargo > 0` 時中間數列**兩邊皆不屬**。我寫的 `decision_at_ms < test_start_ms` 會把隔離帶事件收成 **train**，而現行集合成員語意是 **purged** ⇒ **切分成員集漂移**。我為修 A（網格不一致）引入了 B。第七次修訂須把 gap 處置**寫死為三者擇一**（建議 fail-closed，與 `outside_both_bounds` 一致，且不把隔離帶收成 train），並配成對斷言與一條 mutation。
- **`tier_min_test_events` 被 TF 維度膨脹繞過**（grok；命中高風險 (d)）：`split_projection.py:562` `n_test = int((assignments["split_label"]=="test").sum())` → `:569` `per_symbol_test_n` → `:716-719` 比門檻。複合鍵後 1 事件 × 2 TF 使 `n_test=2 ≥ tier_min=2` 而真實事件數為 1 ⇒ **靜默繞過測試段樣本下限**。`Task 9.4` 檔案清單未含此路徑。
- **物化記帳不變式會直接炸**（grok）：`feature_materialization.py:138-140` `n_input = per_tf["event_id"].nunique()`；若照 `Task 9.3` 改 MultiIndex，`len(features)` 成列數而 `n_input` 仍事件數 ⇒ `AssertionError`，或誘使實作者保留事件級 groupby 假綠。**與主委自產之「該處應維持事件級」互相印證**。
- composer 另開兩條：`(3.2)` 檢查漏「同事件一列 purged、一列 assignments」之混態（只驗 `split_label` 唯一抓不到，因 purged 列無該欄）；`Task 9.1` 二擇一**規格自己沒擇**，兩選項皆無具名 route／fixture ⇒ 9A 仍寫不出驗收命令。

🔴 **`Task 9.1` 之二擇一已由主委定案＝選 (b)，且我原指名的落點整組是錯的**：`case_import_service.py:1592-1609` 逐字寫著「**事件掃描端恆走 event-study-only**」，並註明此為 **SPEC C-0 決議③／R2 之 D1 之既有裁定**，理由是碼證——「本 service 手上只有匯入的事件與 K 線，**完全不碰 FF run**，拿不到 canonical feature universe」；同段另交代「日後補上 `features_run_id` 跨棧參數時**不得刪除本分支**（殘留 `R-5`）」，且 capability **刻意不留 `"ok"` 分支**（「留一個永遠走不到的 `ok` 會讓前端以為有時候是有切分的」）。⇒ **選項 (a) 會直接推翻本票自己的既有裁定**（該裁定有碼證、且已具名殘留給 `R-5`）⇒ **只能選 (b)**：終端揭露自事件掃描端**移出**，改掛在真正走投影的 **IC 主線**（`ic_filter_orchestrator` 才是 `holdout_boundary` 的生產呼叫點）。**連帶結論**：我在第四次修訂為 `Task 9.1` 指名的 `api/routes/case.py:487`／`case_import_service`／`EventTablesPanel.tsx:347,361` **整組是錯的落點**——該路徑在本票設計上**永遠不會有 `discarded`**，因為它根本不呼叫 `build_event_keys`。第七次修訂須整段改寫，並在 R6 收斂檔以主委自產條記明。

🔴 **`tier_min` 繞過之嚴重度已定案（比 R6 所述更精確）**：`insufficient_events_in_test` **不擋任何分析**——它只被 `tables.py:162` 原樣放進報告供人看；且 `grep` 確認**前端完全未顯示**（前端命中的 `warmup_insufficient` 屬 Feature Factory，是不同的東西）。⇒ TF 膨脹繞過 `tier_min` 的後果**不是**「擋下的閘被繞過」，而是**「測試段事件數不足」這個警告靜默消失，而使用者本來就看不到它**。仍命中高風險 (d)（樣本不足卻無人知情），但第七次修訂須把它與「該旗標無終端揭露」**一起**處理——只改計數而不補揭露，修了也沒人看得到。此判定與 `Task 9.1` 之終端揭露缺口同源。

🔴 **第七次修訂之兩項寫法已可定案（主委先取事實，免得又寫成模糊指示）**：
- **gap 可精確定義，不必用模糊的「兩個 `time_bounds` 之外」**：`split_preview.holdout_test_row_index:41-43` 逐字為 `split_point = floor((1-oos_test_size)*n)`、`start = split_point + purge_gap + embargo`、`test = arange(start, n)`；train 為 `arange(0, split_point)` ⇒ **gap 恰為位置半開區間 `[split_point, split_point+purge_gap+embargo)`**。`Task 9.2b` 應寫成「`decision_at_ms` 映射之位置落在該區間 ⇒ fail-closed」，並明示**不得**收成 train。
- **跨表檢查只能用集合交集**：`purged` 僅兩欄 `["event_id","reason"]`（`split_projection.py:556`）、**無 `split_label`** ⇒ composer 之「只驗 `split_label` 唯一抓不到 purged 混態」**結構上成立**；`(3.2)` 之補充檢查須寫成 `set(purged["event_id"]) ∩ set(assignments["event_id"]) == ∅`，而非擴充 `split_label` 值域（後者會動到已戳記之封閉值集）。

**R6 已收並收斂完畢**（`round_id=ad644930`，債已清）：三家皆 `blocked`，共 **16 條歸八群、全部採納**（codex 7、grok 5、composer 4）。收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r6/synth.md`（歸戶 rc=0、completeness rc=0、xref 處置欄 **32 個概念**全對上）。**三群是三家獨立撞題**：I1 不等式在隔離帶不等價、I2 `(3.2)` 抓不到 purged∩assignments、I5 `Task 9.1` 未擇一。

🔴 **本輪方向反轉**：八群中**四群是我派工過度或派錯**（I3 物化層本該維持事件級、I4 16 處清單用形狀判準誤列、I5 `Task 9.1` 指的 route 永遠走不到、I6 前端匯出 Map 改鍵會弄壞使用者 CSV），而非「又漏了一層」。前六輪都在追「還有沒有第 N 層」，R6 起要**雙向**攻。

**D-002 第七次修訂已完成**（commit `fa2620c9`；obligation／format rc=0，xref 對 **r1–r6 六份** synth 皆 rc=0；mutation 25 → **26 條**，主委**自數**表列 26、ID 01–26 連續後才宣稱）。八群逐條落地，其中 `Task 9.2b` 側別判準改為**三段式且順序不得調換**、`D-002-C5` 之 16 處**全面重新分類為三類**、`Task 9.1` 原指名之四個落點**全部作廢**（字面保留供追溯）。

🔴 **`Task 9.1` 採 (b) 之落點已由主委查到（第八次修訂須寫死，不得再泛稱「IC 主線」）**：`ic_filter_orchestrator.py:1530` 呼叫 `build_split_unify_disclosure(...)` 寫入 `metadata["split_unify"]`，而該函式（`split_projection.py:123-143`）docstring 逐字為「`metadata.split_unify` 之**唯一**產生點（Task 4.1／SPEC C-6）」。⇒ **(b) 的具名落點＝`metadata.split_unify`**。🔴 **同時帶出新約束**：該揭露之 `reason` 必須落在 `split_unify.json` 之**封閉集合**（`FAIL_CLOSED_REASONS`，非法字面即 raise），且 `n_test=None` 專指「沒得算」而非 0 ⇒ 要承載 `discarded_rows_by_feature_tf` 必須**擴充該函式的回傳結構**，**不得**改動 reason 封閉值集（那會動到已戳記之契約與前端枚舉面）。**誠實邊界**：`pipeline.run` 之四參數投影分支在生產碼中**仍無呼叫端**（帶 `train_plan=` 的生產命中皆屬 ML 校準與 IC 自身 adapter，非事件投影），故 `discarded` 的**產生**仍需 `Task 9.2` 完成後才會真的有值——`Task 9.1` 之揭露落點與「誰產生它」是兩件事，須分開寫明。

🔴 **`(5.3)`／`(5.4)` 整段仍是改判前敘事，與 `(5.1)` 新分類互斥六處（grok 併進 `P1-01` 未單獨列，第八次修訂漏掉則 R8 必再開）**——主委已逐條查出：①`feature_materialization` 之 `groupby("event_id")+row_vals.update` 被標為「🔴 **靜默**，真正的折疊點」，而 `(5.1)` 已定它是**設計上的橫向合併**、屬 (甲)；②`tables` 兩處 `set_index`（**靜默**）、③`ic_feed` 兩處 ＋ `.loc[keep["event_id"]]`（**靜默**）、④`dedupe` 之 `cluster_first` 保留集（**靜默折掉 TF**）——三者皆已改判 (甲)；⑤`counterexample_classifier` 之 `.loc[eid]`（**靜默綁錯 receipt 列**）與 `candidate_ledger` 雙 `set_index`（**靜默**）——已改判 (甲)；⑥前端 `byEventId` Map（**靜默後者覆蓋前者**）已改判 (甲) 且 `Task 9.5` 明文排除，`clusters_oracle.json` 被列入「看不出差異」而 `(5.1)` 已定其維持事件級不動。**仍與新分類一致的只有** `pattern_bridge`（靜默取到 Series ⇒ (丙)）與 `splitunify_golden.json`（(乙) 確需擴維）。⇒ 第八次修訂須把 `(5.3)`／`(5.4)` 之「靜默／須改」敘事改寫為**現況描述 ＋ 指向 `(5.1)` 分類**，不得留著舊判定。

🔴 **`Task 9.1` 終端揭露需要一個決策（第八次修訂必須擇一寫死，否則 R8 會再開同一條）**：grok `P1-03` 要求「(b) 若尚無生產路徑，須含**新增／恢復**該路徑的 route＋service＋前端檔案:行」——但那等於**新建一條 API**，與 Phase 9A「揭露成本極低、立刻消除靜默丟棄之誠實性缺陷」的原始定位直接衝突。三個選項：**(b1)** 新增 IC 路徑之 API 揭露（成本不低，9A 不再是低成本先行）；**(b2)** 終端揭露降級為「producer 回傳 ＋ `EventSplitPlan.summary` ＋ `metadata.split_unify`」三層，不要求 API／前端（但使用者仍看不到，與 9A 初衷相違）；**(b3)** **承認根本障礙不在本票**——`api/` 零 `EventSamplePipeline.run` 呼叫、投影路徑**本身沒有任何生產接線**（b3 批次「接線」留下的既有狀態），故 9A 之**終端**揭露具名為殘留（類別 `blocked-by`：投影路徑尚無生產接線），本票只交付 producer 層 `discarded` 回傳 ＋ summary 鍵 ＋ `metadata.split_unify` 欄位，並在 §N 寫明「終端可見性待投影接線上線後補」。🔴 **主委傾向 (b3)**：硬要在 9A 補一條新 API，是把別票的缺口塞進本票；且依「殘留只准 blocked-by／user-ruling／needs-research」之規約，(b3) 的理由類別為 **blocked-by**、有碼證（零呼叫點），合規。**此為需委員複驗之判斷，非事實**——第八次修訂寫入後須在 R8 brief 明列為最該被攻的一處。

🔴 **第八次修訂之兩項事實已備（主委實跑）**：①**時間域判準可行**——`split_projection.py:524-526` 現有 `train_ms`／`test_ms`／`test_start_ms`，**無** `train_last_ms`；但 `train_rows` 就在作用域，新增 `train_last_ms = int(index_ms[train_rows[-1]])` 為**一行**且與既有 `test_start_ms` 取法對稱 ⇒ grok 之「以 `train_last_ms < decision_at_ms < test_start_ms` 定義隔離帶」可直接落地，不必依賴 `∈ index_ms`。②**mutation 04–11 有七條方向相反，非僅數條**：`04`（「不改 `groupby` 折疊」＝缺陷）與「物化維持橫向合併」互斥；`06`／`07`／`08`／`09`／`10`（`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`／`dedupe` 之「退回單鍵／退回事件級粒度」＝缺陷）與 `(5.1)` **甲類維持事件級**全部互斥；`11`（Map 鍵退回 `event_id`＝缺陷）與 `Task 9.5` 排除遷移互斥。**唯一方向仍成立的是 `05`**（`pattern_bridge` 退回單鍵）——它屬 **(丙)**，確實需要改。⇒ 第八次修訂須把 `04`／`06`–`11` 改為**反向 mutation**（誤改成複合鍵才紅）或刪除，並同步條數與 ID 連續性。

🔴 **R8 grok 已交，與 composer 四條高度重疊（兩家獨立撞題）**：G-4a 不可機械驗證、`Task 9.1` 殘留**沒落地**、`(6.2)` 與 `Task 9.4` 互斥、反向 mutation 現行不紅（除 `04` 可依 `n_input` 不變式紅）。兩點差異須在收斂記明：
- 🔴 **`blocked-by` 類別兩家判定相反**：composer 判**不成立**（該類別須指名具體阻塞票，「零呼叫點」是能力缺口）；grok 判**成立**（零呼叫點＝依賴投影生產接線，確為被擋）。依「分歧採較嚴版」**採 composer**：改標 `needs-research`，或先開一張具名 projection-wiring 票再以其票號 `blocked-by`；收斂檔須記明分歧與採納理由。
- **grok 補了兩處我與 composer 都沒列到的殘留落地缺口**：`Task 9.1` 標題句「**缺任一層即視為 9A 未完成**」仍含 API／前端；`Task 9.4` L204 仍寫「**同批必須補**該旗標之終端揭露」——兩處與具名殘留直接互斥，第九次修訂須一併改。
- grok **未否證**我自驗的「`dedupe` 廣播不改 `w=1/n`」，並給出同向碼證（`event_split._cluster_weight` 亦建在事件級）⇒ 該條可標為**主委自驗＋一家附議**，不需再問。

🔴 **第九次修訂要改的兩句原文已取（免得又字串對不上）**：`docs/SPLITUNIFY_SPEC.D-002.md:140` 逐字＝「`- **API 與前端揭露落點（逐處指名，缺任一層即視為 9A 未完成）**：`」——仍把 API／前端算進 9A 完成條件；`:204` 逐字＝「`- 🔴 **同批必須補該旗標之終端揭露，否則修了也沒人看得到**：…本條與 `Task 9.1` 之終端揭露同源，須一併處置。`」——與具名殘留直接互斥。兩處皆須改為「本延伸只交付 producer 層；終端揭露隨 `Task 9.1` 之殘留一併延後」。

🔴 **主委查證推翻兩家共同前提，並更正我自己的採納**：`templates/BRIEF_REVIEW_TEMPLATE.md:71` 逐字為 `reason_code` 閉集＝**`blocked-by`／`needs-research`／`cost`／`out-of-scope`**（**四值**，我先前記成三值）；同檔 `R-BRIEF-1` 之實例逐字為「`blocked-by` **現行派工架構**」——**指向架構限制而非票號**。⇒ composer 主張「`blocked-by` 須指名具體阻塞票」**不成立**，grok 判「成立」才對；我先前依「分歧採較嚴版」採 composer，**採錯了**（較嚴版之適用前提是雙方都合規而寬嚴不同，這裡是一方的前提與範本牴觸）。**第九次修訂之處置**：`Task 9.1` 終端可見性殘留維持 **`blocked-by`**（對象＝投影路徑無生產接線之架構現況，與 `R-BRIEF-1` 同型），**但仍須真的寫進 §N**（那才是 R8 兩家共同成立的部分）。§N 條目格式照既有形狀：`` - `<ID>` — <一句處置>，`<reason_code>`（<對象或觸發條件>）``。收斂檔須記明此更正，不得讓「採較嚴版」變成不看範本的預設反射。

🔴 **七條反向 mutation 之具名落點已盤好（R8 兩家要求「不得再寫散文」；主委實跑 `ls`）**：**六條有現成測試檔可掛**——`M-SU-D2-04`→`tests/momentum/event_samples/test_feature_materialization.py`；`06`→`test_tables.py`；`08`→`test_counterexample_classifier.py`；`09`→`test_candidate_ledger.py`；`10`→`test_dedupe.py`；`02`／`03`（隨殘留決策改指 summary 與 `metadata.split_unify`）→`tests/momentum/Analysis/test_splitunify_derive.py`。**兩條需處理**：`07`（`ic_feed`）**無專屬測試檔**，最近者為 `test_gap3_conditional_ic.py`／`test_gap3_attached_columns_contract.py`，須擇一或新建；`11`（前端 `byEventId`）**無對應 vitest**，須新建（例 `frontend/src/lib/eventExport.composite-guard.test.ts`）。⇒ 第九次修訂之 §V `Task 9.3` 可直接把七條逐一指到上列具名檔，成本低；🔴 **在那些測試實際存在前，不得宣稱 mutation 網已閉**（R8 兩家共同要求）。

🔴 **`P1-01` 之處置已定案（主委查證後，比兩家提的方案都省）**：`scripts/freeze_splitunify_golden.py:133-138` 之 `_oracle_membership` docstring 逐字「直接由 `feature_index[row_index]` 投影出成員集合——**與被測函式無因果關係**」「🔴 刻意**逐行重寫**兩段式規則（**不 import 投影**）：oracle 的價值就在於它是**第二份推導**，共用實作就退化成同義反覆（B2b review `CODEX-R1-P2-05` 之教訓）」⇒ **防同義反覆的紀律已明文在該處**。關鍵：它**目前也用 cutoff 判側**（`cut = int(rec["feature_cutoff_ms"])`、`in_train, in_test = cut in train_ms, cut in test_ms`）。⇒ 第九次修訂之 `Task 9.2b` 須寫死：**落地時同步以 decision-anchor 逐行重寫該 oracle（維持「不 import 投影」）**，則 G-3b（`g1_membership != g3b_oracle`，`main()` 每次都驗）**自動成為「換錨 vs 寫錯」的區分閘**——換錨改側兩邊同步、實作寫錯只有投影那邊改即紅。**不必**新造 `allowed_reanchor_diff` 檔（composer 替代①／grok 修法②），**也不必**保留 cutoff-anchor 平行鍵。另保留 grok 之第三點為硬斷言：**`decision == cutoff` 之事件必須零位移**。

（以下為較早的初步判斷，保留供追溯）🔴 **composer `P1-01`（G-4a 不可機械驗證）有成本極低的解法——主委查到現成骨架**：`scripts/freeze_splitunify_golden.py:346-352` **已經有**雙路徑比對 `if actual["g1_membership"] != actual["g3b_oracle"]`，註解逐字「G-3b：新投影 vs 獨立 oracle，集合相等（**每次都驗**，不只在凍結時）」，而 `_oracle_membership()` 是**依公式手推、與投影無因果關係**的獨立 oracle。⇒ 第九次修訂只要要求「`Task 9.2b` 落地時**同步**把該 oracle 改為 decision-anchor」，G-3b 即自動成為區分閘：**因換錨而改側的事件會在兩邊同時改，實作寫錯則只有投影那邊改**，`g1_membership != g3b_oracle` 直接紅。**不必**新造 `allowed_side_diff_events.json`、也不必保留 cutoff-anchor 平行鍵。🔴 **但須明文寫死**「oracle 與投影**不得由同一段程式碼產生**」（B2b 曾踩過：抽共用函式後 oracle 變成同義反覆，見 `clusters_oracle.json` 檔頭註解），否則這個閘會空心化。

🔴 **R8 composer 已交，三條主委已複驗、全部成立——「改一處漏一處」第四次，且這次漏的是我自己承諾的動作**：
- **`P1-03`（最難堪）**：§N 現有六條殘留，**沒有任何一條**是 9.1 終端揭露。我在 `Task 9.1` 白紙黑字寫「**登記於 §N**」，**然後沒去登記**。它對 `blocked-by` 的質疑也成立：§N 既有之 `R-4` 用 `blocked-by` 時指名了「屬 GAP-3」這張**具體的票**，而我只寫「零呼叫點」＝**能力缺口**，無可追的阻塞對象 ⇒ 類別應改 `needs-research`（投影接線設計未定），或先開一張具名的 projection-wiring 票再以其票號 `blocked-by`。
- **`P2-02`**：`(6.2)` L92 仍逐字「`baseline` 之 `n_test`…**不得**改判為事件數」，而 L205 我剛改成「**仍為事件數**」——同檔兩處**正面衝突**。
- **`P2-03`**：`M-SU-D2-02`／`03` 仍是「不傳到 API 回應」「前端不顯示」，而 §V 已作廢那兩層 ⇒ 實作者**寫測試違殘留、不寫違 mutation**，兩邊都錯。
- 另 `P1-01`／`P1-02` 是對我兩個取捨的正面攻擊（G-4a 不可機械驗證、9A 對終端零揭露且 `metadata.split_unify` 在生產路徑不可達），須在第九次修訂正面回應——它給了具體替代（雙跑 cutoff vs decision 產 `allowed_side_diff_events.json`；或保留 cutoff-anchor 平行鍵一個 Phase）。

🔴 **R8 brief 之 assumed「dedupe 廣播不改權重」已由主委自驗成立（不必等委員）**：`dedupe.py:98-99` 逐字 `overlap_count = [len(s) for s in overlap_sets]`、`weights = [1.0 / c for c in overlap_count]` ⇒ `w=1/n` 之分母是**標籤窗重疊的事件數**（`overlap_sets` 建在事件級 table 上），**與 feature TF 無關**；`:141-142` 之 `eff_primary` 要嘛是 `in_primary` 的**事件列**計數（`cluster_first`）、要嘛是 `sum(weights)`，兩者皆事件級。⇒ 保留集仍在事件級決定、再把保留之 `event_id` 廣播到 per-TF 列，`w=1/n` 與 effective count **逐值不變**；反之若照 v7 舊指示改複合鍵粒度，`overlap_sets` 被迫展開成多列、分母 `c` 膨脹而權重被稀釋——正是 R7 兩家警告的語意破壞。**此條可在 R8 收斂時標為主委自驗、不需委員再答**。

🔴 **第八次修訂進行中，我又一次只改一處、漏改六條（這次靠自查抓到，不是委員）**：J1 的處置是「mutation 與 `(5.1)` 分類同步」，我卻只改了 `M-SU-D2-11`，`04`／`06`–`10` 六條仍是舊方向（「退回單鍵＝缺陷」）——與甲類「維持事件級」全部互斥。**這是同型錯誤第三次**（第 51、52 筆各記過一次）：改了結論，沒回頭改所有依賴那個結論的條目。差別是這次我在跑閘前自查表格內容抓到，沒等 R8。六條已全部改為**反向 mutation**（誤改為複合鍵才紅）。⇒ **判準補充**：凡改動一條「分類／定案」，**必須把該檔內所有引用它的條目列成清單逐條核對**，不能只改當下那一段——這一步現在沒有任何機械閘能代勞（同檔互斥，見摩擦第 51 筆）。

🔴 **R7 grok 已交，兩項對第八次修訂直接有用**：①**三分類本身經抽樣複驗為對**——grok 明說「**未找到『甲類判錯、複合鍵上線後會靜默取錯列』的反例**」，真正會靜默取錯的是 `pattern_bridge`（`:125-127` 複合鍵後 `.loc` 變 Series），而它已正確歸在 **(丙)** ⇒ 錯的只是施工單未同步，不是分類。②**它的 `P1-02` 與主委自驗結論一致（隔離帶應 `purged` 不是 raise），且修法更好**：以**時間域**定義隔離帶（`train_last_ms < decision_at_ms < test_start_ms`），如此**不必依賴 `decision_at_ms ∈ index_ms`**——同時解掉 composer `P2-01` 之「位置映射演算法未定義」。第八次修訂之 `Task 9.2b` 步驟 1 應改採此時間域判準。③grok 另指出 mutation `M-SU-D2-04`～`11` 多條與新定案**方向相反**（`04` 仍把「不改 groupby 折疊」當缺陷、`11` 仍把「Map 鍵退回 `event_id`」當缺陷），須改為反向 mutation 或刪除。

🔴 **主委自驗：第七次修訂對 I1 的處置選錯方向，與本延伸自己的 §G 硬衝突（第八次修訂必改）**：`scripts/freeze_splitunify_golden.py:94` 之 docstring 逐字「固定 12 筆：train 段 5（其中 1 筆答案窗跨界）、**隔離區 2**、test 段 5」；`:101-102` 之 `gap1`／`gap2` 其 `feature_cutoff_ms = int(index[tr[-1]]) + i * H1`（i=1,2）＝train 末列之後 1／2 小時，**刻意造在隔離帶上**；而 `tests/golden/splitunify/splitunify_golden.json` 之 `g1_membership.purged` 現值為 `["gap1","gap2","tr_leak"]`。⇒ 我把隔離帶改判 **fail-closed raise**，會讓該單標的 golden fixture **整批拋錯**，違反 §G「單 TF 路徑逐值不變（exact）；任一單 TF 舊值位移即 FAIL」。**更根本**：現行設計把「事件落在隔離帶」視為**合法且預期**（fixture 刻意造兩筆），正確處置是 **`purged`** 而非錯誤——隔離帶的用途就是「落在這裡的事件要丟掉」。⇒ R6 三家指出「不等式會把隔離帶收成 train」**成立**，但**我選的補救方向錯了**：`Task 9.2b` 三段式步驟 1 應改為「以位置判定落在隔離帶 ⇒ **`purged`**，沿用既有 `interval_crosses_split_boundary` 字面」，**不是** raise；raise 只保留給「落在 `train_plan`／`test_plan` 覆蓋區與隔離帶**之外**」（真正的界外）。（線索來自 grok runlog 的中途紀錄，主委獨立取證確認。）

🔴 **R7 composer 已交（另兩家未交），四條主委已複驗、全部成立——同一個病第三次發作**：我第七次修訂**只改了新寫的 `(5.1)` 三分類段，沒回頭同步 `Task 9.3`／mutation 表／§V 裡第六次修訂留下的舊條目**，導致同一份文件內部互斥：
- `Task 9.3` 第三 bullet 逐字仍為「`pattern_bridge`／`tables`／`ic_feed`／`counterexample_classifier`／`candidate_ledger`：`.loc[eid]` 之 scalar lookup **改為複合鍵 lookup**」，而 `(5.1)` 已把後四者列為 **(甲) 事件級維持**。
- 次一 bullet 逐字「`dedupe`：`cluster_first` 保留集改 `(event_id, feature_timeframe)` 粒度」，而 `(5.1)` 把它列為 (甲)。
- `M-SU-D2-11` 仍以「前端 `byEventId` Map 鍵**退回** `event_id`」為缺陷，而 `Task 9.5` 已改判該 Map **排除於遷移之外**、正確實作正是維持 `event_id` ⇒ 實作者為通過該 mutation 會把它改回複合鍵，重現匯出 miss。
- §V `Task 9.1` L207 仍寫「`ASSERT summary／API 回應／前端型別三層皆帶該欄`」，而那三層落點已被我在 `Task 9.1` 標為作廢。
🔴 **根因**：這正是我自己在摩擦記錄第 23 筆寫過的「同一份文件內部兩句話互斥，交叉引用閘看不到」——閘只比對**跨檔案**同步（synth 處置欄 ↔ SPEC），對**同檔內部**互斥完全無能為力；而 `(5.1)` 那段我還特地寫了「不得用形狀規則」。第八次修訂必須**逐段回頭掃**，不能只改新寫的那一段。

**R7 已收並收斂完畢**（`round_id=9ec83c83`，債已清）：三家皆 `blocked`，共 **15 條歸八群、全部採納**（codex 6、composer 6、grok 3）。收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r7/synth.md`（歸戶 rc=0、completeness rc=0、xref 處置欄 **31 個概念**全對上）。**三群為三家獨立撞題**：J1 分類改了施工單沒改、J3 `Task 9.1` dataflow 未封、J4／J5 判準與 golden。

🔴 **codex 揭出一層我與另兩家都沒想到的（J5 後半）**：`alignment.py:87-93` 允許 `cutoff < decision` ⇒ **換錨本身**就會讓邊界事件改側（`test_start=1000, decision=1000, cutoff=900` ⇒ 舊 train、新 test），與 §G「單 TF 逐值不變」**本質互斥**，不是補 fixture 能解決。

**D-002 第八次修訂已完成**（commit `2dd245a4`；obligation／format rc=0，xref 對 **r1–r7 七份** synth 皆 rc=0；mutation 表列 26／ID 01–26 連續，主委自數）。八群逐條落地，其中**兩個是在互斥選項中挑邊**：**§G (G-4a)**（承認事件級錨定為正確語意，單 TF golden 落地後重凍一次、僅允許「因換錨而改側」這一種差異）與 **`Task 9.1` 終端可見性具名殘留**（`blocked-by`，碼證＝`api/` 零 `EventSamplePipeline.run` 呼叫點）。

**R8 已收並收斂完畢**（`round_id=16a8c27e`，債已清）：三家皆 `blocked`，共 **14 條歸八群**（七群採納、一群**部分採納**）。收斂檔 `handoffs/reconcile/20260911-splitunify-b9-review-r8/synth.md`（歸戶 rc=0、completeness rc=0、xref 處置欄 **42 個概念**全對上）。**三群為三家獨立撞題**：K1 (G-4a) 不可機械歸因、K2 殘留決策未落地、K6／K7。

**D-002 第九次修訂已完成**（commit 見下；obligation／format rc=0，xref 對 **r1–r8 八份** synth 皆 rc=0；mutation 表列 26／ID 01–26 連續；`SU-RESID-9A-UI` 已真的入 §N，`grep -c` ＝ 3）。**本輪兩處是我自己的缺陷**：K5（我在 R7 才把判準改成時間域，**改完四條規則彼此重疊**——`decision=50` 同時命中 train 與界外，codex 獨得）與 K2（**寫了「登記於 §N」卻沒登記**，三家獨立抓到）。另 K3 我**駁回** composer 前提並更正自己先前「採較嚴版」的套用錯誤（範本 `reason_code` 閉集為四值、`R-BRIEF-1` 以架構為 `blocked-by` 對象）。

🔴 **收斂性判斷（主委實跑計數，供 R9 收斂決策用）**：各輪 findings 數 **R1–R8＝15／11／15／8／11／16／15／14**——**九輪無下降趨勢**。但依「停在無法收斂處」之判準，關鍵不是數量而是**性質**：每輪皆為**具體可閉合、有碼證、且多條三家獨立撞題**之條目，非各說各話或無限窮舉 ⇒ **不符合「無法收斂」之停輪條件**。真正的訊號是**近三輪有四項屬我「寫了要做卻沒做」或「引錯依據」**（K2 §N 未登記、(G-4d) 未進 §V、K3 引錯範本、L137 目標句漏改）——那不是規格複雜度問題，是**我的修訂紀律問題**。⇒ **判斷：續修，但第十次修訂必須改做法**——每一項改完**立即逐條 grep 自證它落在該落的段落**（§V 驗行號區間、§N 驗強制欄 `為何現在不做:`、mutation 驗表列與 ID 連續），**自證通過才算完成**，不得寫完即宣稱。此判斷須在 R9 收斂檔具名記載，並在 R10 brief 請委員檢驗「自證步驟是否真的執行」。

🔴 **R9 grok 已交，與 composer 四條全部撞題；主委複驗其兩條關鍵事實，成立且比它說的更嚴重**：
- **現行 golden fixture 全部事件 `decision == cutoff`**：`scripts/freeze_splitunify_golden.py:117` 逐字 `"decision_at_ms": keys["feature_cutoff_ms"].astype("int64")` ⇒ 12 筆事件無一例外。**後果**：整份換錨的行為差異**在現行 golden 上一筆都測不到**——`(G-4d)②` 之「零位移」斷言雖會通過，卻是**空心通過**（沒有 `decision != cutoff` 樣本）；`(G-4d)③` 要求的邊界 fixture **根本還不存在**。⇒ 第十次修訂須把「**freeze fixture 新增 `decision != cutoff` 事件**」列為 `Task 9.2b` 的前置工作，否則 G-4 整組驗收是空的。
- **`SU-RESID-9A-UI` 缺 `SPEC_TEMPLATE` 強制欄**：`grep` 該條目之 `為何現在不做:` 命中數 **0** ⇒ 我寫的殘留**不符強制格式**（`SPEC_TEMPLATE.md:107-112` 要求每條殘留必須帶該欄）。
- **`gapX` 構造確認 (G-4c) 擋不住 correlated error**：`decision=950`／`cutoff=900`／`train_last=900`／`test_start=1000`，正解為隔離帶 `purged`；兩邊同寫 R6 不等式 ⇒ 皆判 train、G-3b **綠**；且因 `decision != cutoff`，`(G-4d)②` 不適用。⇒ 必須加 grok 提的**第三份判準**（以三段式含步驟 0 從 fixture 純函式算期望側，與投影／oracle **雙邊**比對；可內嵌測試不必新檔）。

🔴 **`P1-02` 亦複驗成立——「寫了要做卻沒做」第五次**：`decision != cutoff`／`零位移`／`v8 baseline` 三個字面**只出現在 `:129`（§G (G-4d)）與 `:282-283`（沿革）**，而 §V 範圍是 `:216-257` ⇒ **(G-4d) 三項硬性附帶完全沒進 §V，也沒進 mutation 表**。我在 (G-4d) 逐字寫著「**須進 §V 與 mutation**，不得只寫在 §G 散文」，然後**自己沒去做**。與 K2（寫「登記於 §N」卻沒登記）同型——**同一天第五次**。第十次修訂須：§V 增三條（`decision == cutoff` 零位移對 v8 舊鍵、`decision != cutoff` 單 TF 邊界、界外 early／late raise），mutation 增對應項，並**改完後逐條 grep 自證落在 §V 行號區間內**。

🔴 **R9 composer 已交；主委複驗三條，全部成立——其中一條是我引錯權威，須自我推翻 K3 的駁回**：
- **`P2-01` 成立（最嚴重）**：§N 殘留之 canonical 規則在 **`templates/SPEC_TEMPLATE.md:106-109`**，逐字「值**只允許三種**：`blocked-by:<具體依賴（檔/層/前置票）>`／`user-ruling:<日期＋裁決內容>`／`needs-research:<研究題目>`」——**明文要求「具體依賴（檔/層/前置票）」**。我在 K3 引的 `templates/BRIEF_REVIEW_TEMPLATE.md:71` 是 brief 內「**沒查的那句話**」六欄表之 `reason_code`（四值閉集），**服務的是另一件事**。⇒ **我駁回 composer 是錯的，它原本的主張才對**；grok 判「成立」亦基於我引的同一份錯範本。我先前「閉集是四值、我記成三值」之更正**本身就是引錯造成的**——真正的 §N 規則就是**三值**。**第十次修訂**：`SU-RESID-9A-UI` 改依 `SPEC_TEMPLATE`，`blocked-by:` 後接**具名依賴**（例「投影生產接線 Task（待開）」）或改 `needs-research:<生產投影接線設計>`；收斂檔須記明我兩度更正之經過。
- **`P2-02` 成立**：`Task 9.1` 目標句仍逐字「必須讓**終端使用者**看得到」，與下方 v9「只交付 producer 層」並存——K2 我宣稱四處同批改完，實際漏了目標句本身。
- **`P1-01` 成立且我認**：其構造（`decision = cutoff = train_last = 200`，投影與 oracle **同步**把 `<=` 誤寫成 `<`）使兩邊同錯、G-3b 仍綠，且該事件**不在** `decision != cutoff` fixture 覆蓋內 ⇒ **(G-4c) 擋不住 correlated error**，我的「同步改寫 oracle 可取代 allowlist」判斷錯誤。第十次修訂須**保留 G-4c 作 regression，另加** allowlist 或 cutoff-anchor 平行鍵（回到 R8 三家原案）。

🔴 **R9 brief 兩條 assumed 已由主委自驗（不必等委員）**：①**`SU-RESID-9A-UI` 之觸發條件可機械判定**——現行 `api/` 對 `EventSamplePipeline().run(`／`create_event_sample_pipeline().run(` 命中數為 **0**，故「該數 > 0」是**封閉可導出**判準，可寫成一行 grep 斷言掛進閘，**不會變成永遠沉睡的殘留**；第十次修訂應把此判準逐字寫進 §N 該條之觸發欄。②**`D-002-C6` 內仍有一處潛在不一致**：`(6.1)` 標題與內文仍為「事件數與列數是**兩個量**」「三個量各自定義、**不得互相代用**」，而 `(6.2)` 已把 baseline 之樣本數與事件數判為**等價**；兩者字面可並存（baseline 只是其中一個消費者），但 `(6.3)` 之「任一消費面把列數當事件數顯示或斷言即為缺陷」會讓實作者對 baseline 產生疑義 ⇒ 第十次修訂須在 `(6.3)` **明列 baseline 為已定案之等價例外**。

**R9 已派出**（session `20260911-splitunify-b9-review-r9`、brief `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R9-BRIEF.md`）。brief 列三處必攻：(G-4c) 以同步改寫 oracle 取代 allowlist 是否等效（含「兩邊同錯而 G-3b 仍綠」之構造）、K3 駁回依據是否適用 SPEC §N、K4「成本超標時改交付範圍」是否又是**自己沒擇的二擇一**。

（以下為 R8 派出時之記載）**R8 已派出**（session `20260911-splitunify-b9-review-r8`、brief `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R8-BRIEF.md`）。brief 把上述兩個取捨列為**必須被攻的決策**，並要求逐條驗「七條反向 mutation 誤改後是否真能紅」。

（以下為 R7 派出時之記載）**R7 已派出**（session `20260911-splitunify-b9-review-r7`、brief `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R7-BRIEF.md`）。brief 首次要求**雙向攻擊**：既問「還有沒有漏派的關卡」，也要求委員**挑戰我新做的三分類**——特別是被我判為「(甲) 事件級維持」的那些，若其實該改，複合鍵上線後會靜默取到錯的列。

（以下為 R6 派出時之記載）**R6 已派出**（session `20260911-splitunify-b9-review-r6`）。brief 把「此主張已被推翻四次」逐輪列出，必答 2 擴大到 **`feature_materialization`**——前四輪的推翻都停在 `assignments` 之前，這次要求走到物化產出。

（以下為 R5 派出時之記載）**R5 已派出**（session `20260911-splitunify-b9-review-r5`、brief commit 見 `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R5-BRIEF.md`）。brief 開頭**直接寫死**「唯讀審查不適用 STAMP-BLOCKED」並附碼證，把 R4 那條誤讀擋在委員讀 brief 的當下；必答 2 要求委員**自己從 `EventSamplePipeline.run` 入口走到 `assignments`**，假設還有第四層我沒看到。

其後：三家放行 → 戳記 → 才進 `Task 9.1` 實作；再後 `D1` 走 R 重開重戳 → 最後一批 `R-5`。

其後：三家放行 → 戳記 → 才進 Task 9.1 實作；再後 `D1` 走 R 重開重戳 → 最後一批 `R-5`（不得與未完成之 `D1` 同批上線）。
