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

🔴 **時鐘刻度：`Task 9.2b` 改法尚未定案（主委自驗中，待探針）**：`alignment.py:206` 之 `cutoff = int(sub_ct[idx])` 取自 **`close_time_ms`** ⇒ `feature_cutoff_ms` 是 bar **close**；`alignment.py:157` 之 `decision_at = int(ot[decision_idx])` 取自 **`open_time_ms`** ⇒ 是 bar **open**。兩者**不同刻度**，而現行判側是 `cutoff in train_ms`（集合成員）。⇒ `Task 9.2b` 若直接把它換成 `decision_at_ms in train_ms` 有**系統性落空或位移一根**的風險。`tests/momentum/event_samples/test_splitunify_wiring.py` 之 `_canonical()` 用 `open_time_ms` 當 `feature_index` 而斷言 `cut in train_ms` 卻通過 ⇒ 只能實測解釋。探針已入版：`handoffs/20260912-splitunify-b9-probe-clock-alignment.py`。**第六次修訂前必須先跑它**。

🔴 **主委在這段自驗裡連犯兩次同型查法錯誤（記著防再犯）**：①`grep -rn "run(" … | grep "train_plan"` 要求**同一行**，而實際呼叫跨多行 ⇒ 得出「零命中」並當成事實（import 那條同理，`pipeline.py:25` 就是多行括號 import）；②`grep -rl … | head -12` **截斷**清單，tests 的檔案被切掉 ⇒ 又得出一個假的「矛盾」。**兩次都是用不可靠的查法得出「零命中」就下結論**——與記憶裡「驗 scanner 勿 tail 截斷」同型。判準：凡結論是「某物不存在」，查法必須先自證完備（不截斷、不要求同一行、必要時列檔案而非列行）。

**R5 已派出**（session `20260911-splitunify-b9-review-r5`、brief commit 見 `handoffs/20260911-SPLITUNIFY-B9-REVIEW-R5-BRIEF.md`）。brief 開頭**直接寫死**「唯讀審查不適用 STAMP-BLOCKED」並附碼證，把 R4 那條誤讀擋在委員讀 brief 的當下；必答 2 要求委員**自己從 `EventSamplePipeline.run` 入口走到 `assignments`**，假設還有第四層我沒看到。

其後：三家放行 → 戳記 → 才進 `Task 9.1` 實作；再後 `D1` 走 R 重開重戳 → 最後一批 `R-5`。

其後：三家放行 → 戳記 → 才進 Task 9.1 實作；再後 `D1` 走 R 重開重戳 → 最後一批 `R-5`（不得與未完成之 `D1` 同批上線）。
