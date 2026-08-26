# GAP3_EVENT_UX_TODO — D 延伸 004（B7 開工前之契約修補）

BASE: docs/GAP3_EVENT_UX_TODO.md @ afa70967
PREDECESSOR: docs/GAP3_EVENT_UX_TODO.D-003.md

改什麼: 三條——A-020 把 Task 4.1 之匯出欄（`future_{h}bar_return` × 12 ＋
`lookahead_bars_declared`）納為**可匯入欄**，解除「SPEC 要寫、契約拒收」之條文衝突；
A-021 定案 Task 4.1 移除主答案窗後之下界守衛改形（保留 fail-closed、移除 scalar 比較與
`inexpressible`）；A-022 更正 SPEC Task 4.2 驗收條與交接 §2B.1 之「G-2 golden 須重凍」誤植。
為什麼: A-020 是**凍結後才發現的真衝突**——照 SPEC 字面實作會產出**匯不回去的檔**（實測）；
A-021 之守衛存廢若不定案，不是留死碼就是讓 `D-002 A-004` 之解除失效；
A-022 若照抄，B7 會宣稱一件沒發生的事（重凍）。三條皆出自三家 consult 之裁定；
🔴 其中 A-021 之子題 (c) 為 **2 vs 1**（非一致），詳見該節之更正說明；
🔴 A-020 之初版**漏記三家一致之三項限制**（`future_*` 不進 `ic_feed`／保留 `receipt_schema.batch` 同名鍵／驗批內一致性），
由戳記輪 R2 之 codex REJECTED 擋下，詳見 A-020 末之「R2 之更正」。
檔名依 `docs/FROZEN_DOC_AMENDMENT_PROCEDURE_V2.md` §2.2（`*.D-NNN.md` 機讀規約）。

## 觸及面宣告

新增: `event_import_contract.json` 之 `optional_fields` 新增 13 鍵
（`future_1bar_return`..`future_12bar_return`、`lookahead_bars_declared`），各帶指定 doc 字面；
`import_contract.py` 對 `lookahead_bars_declared` 之 `Mapping[str,int>=0]` 型別驗證＋**批內一致性**驗證
不動: `event_import_contract.json` 之 `receipt_schema.batch.lookahead_bars_declared`（`:180`）**保留不刪**
覆寫: `event_import_contract.json` 之 `derived_fields.names` **移除** `lookahead_bars_declared`；
`exportFilter.ts` 之 `exportAllowedUnderBound` 簽章與 `nextLowerBoundState` 之 `inexpressible` 分支；
`lookaheadDepthLock.ts` 之 `withHorizonLowerBoundGuard` **簽章與職責**（改名 `withExportLowerBoundGuard`，包裹保留）；
SPEC Task 4.2 驗收條之「G-2 事件 golden 須同步更新」句；交接 `docs/GAP3UX_IMPL_HANDOFF.md` §2B.1
依賴: docs/GAP3_EVENT_UX_TODO.D-001.md、D-002.md、D-003.md；
裁定來源 `handoffs/reconcile/20260826-gap3ux-b7-consult-r1/synth.md`（🔴 該檔群集 B 之 (c) 格記載有誤，更正處在本檔 A-021）

## 內容

### A-020 — Task 4.1 之匯出欄須先納入契約，否則匯出檔匯不回去

- **SPEC 原文**（Task 4.1，L1940–1978）驗收①④要求匯出記錄含
  `future_{1,3,7}bar_return` 與 `records[0].lookahead_bars_declared`。
- **契約現況**（`momentum/Analysis/contracts/event_import_contract.json`）：
  `lookahead_bars_declared` 列於 `derived_fields.names`，該節 doc 逐字
  「對齊/組樣本寫入 receipt/manifest，**非匯入欄；匯入檔出現任一 ⇒ unknown_field**」；
  `future_{h}bar_return` **完全未登記**。
- **實測**（`validate_event_import` 對 canonical 事件加欄，三組皆拒）：

  | 加的欄 | 結果 |
  |---|---|
  | `lookahead_bars_declared` | 拒收 `{"field": "lookahead_bars_declared", "reason": "unknown_field"}` |
  | `future_2bar_return` | 拒收 `{"field": "future_2bar_return", "reason": "unknown_field"}` |
  | 兩者都加 | 兩條都拒 |

- **為何是真衝突而非可忽略**：`/search` 匯出之檔**就是拿來匯入的**
  （`eventExport.ts` 之 `verify_note` 逐字說明匯入流程）；今日之匯出檔**可匯入**
  （只寫 `label_value`／`search_rule_summary`／`kind_source`，三者皆在 `optional_fields`）。
  三家 consult 各自實跑複驗「今日匯出檔可匯入」成立 ⇒ 4.1 會**打破既有迴圈**，非既有債。
- **裁定**（三家一致，採 (a) 改契約；不採「匯出/匯入檔分離」、不採「塞 `meta`」）：

  🔴 **本條初版漏記三家一致之三項限制，由戳記輪 R2 之 codex REJECTED 擋下**——
  更正說明見本節末之「R2 之更正」。

  1. `lookahead_bars_declared` 自 `derived_fields.names` **刪除**，加入 `optional_fields`，
     型別 `object`，**其 doc 字面須含**「逐 timeframe 深度 oracle（`Mapping[str,int>=0]`）；
     可隨事件列匯入攜帶；**對齊後複製至 `receipt_schema.batch.lookahead_bars_declared`**」
     （三家 consult 之 doc 字面近乎逐字相同，取其聯集）；
     `import_contract.py` 對其做與 receipt 相同之 `Mapping[str,int>=0]` 驗證
     （`bool` 拒、負數拒、非字串鍵拒），**且驗批內一致性**——同批各列該鍵之值須相同，
     否則拒（codex consult 明列，另兩家未反對 ⇒ 採較嚴版）。
     🔴 **不得雙登記**（同名不得同時留在 `derived_fields.names` 與 `optional_fields`）。
     🔴 **`receipt_schema.batch.lookahead_bars_declared` 須保留**（已存在於契約檔 `:180`，
     型別字面 `Mapping[str,int>=0]`）——那是**第三處**、不在雙登記之禁止範圍；
     移出 `derived_fields` **不得**連帶把它自 receipt schema 刪掉（三家 consult 皆明列）。
  2. `future_{h}bar_return`（h ∈ 1..12）**逐欄列舉 13−1＝12 鍵**加入 `optional_fields`，
     各為 `float`，**其 doc 字面須含**「附帶報酬欄；純供 Excel 攜帶；**不進 `ic_feed`**；
     不參與深度導出／label 判定」（三家 consult 之 doc 字面一致含此四項）。
     🔴 **不用 pattern**——契約之 `allowed_top_level_keys`
     ＝ `required ∪ optional ∪ conditional` 之**閉集**（`import_contract.py:49-55`），
     無 pattern 機制；為此新增 pattern 屬契約結構變更，超出本次範圍。
  3. 缺該欄仍合法（`optional_fields` 之語意）；`/search` **匯出檔則必帶**
     `lookahead_bars_declared`（SPEC Task 4.1 ③）。
  4. SPEC Task 4.1 之契約欄位**以本延伸檔為準**（SPEC 已 FROZEN，不就地改）。
- **不可做**：不得以靜默放寬 validator（例如把未知欄一律放行）取代登記；
  不得把 `future_*` 或 `lookahead_bars_declared` 納入 `event_id` 之輸入（D-2）；
  不得讓 `future_*` 參與深度導出（D-7 明禁「由欄位存在與否推斷」）；
  🔴 **不得讓 `future_*` 進入 `ic_feed`，不得以它決定任何 horizon**
  （三家 consult 一致明列；SPEC L1947 亦同字面）；
  🔴 不得因把該鍵移出 `derived_fields` 而順手刪掉 `receipt_schema.batch` 之同名鍵。
- **驗證**：`pytest tests/momentum/event_samples/ -q -k gap3_attached_columns_contract` **≥7 條**——
  ①雙列事件加 `lookahead_bars_declared={"12h":0}` 與三個 `future_*` ⇒ `validate_event_import` 通過；
  ②`lookahead_bars_declared` 之值為非 `Mapping[str,int>=0]`（含 `bool`、負數、非字串鍵）⇒ 拒；
  ③`future_*` 之值非 float ⇒ `type_error`；
  ④**防雙登記**：`lookahead_bars_declared` 不得同時出現於 `derived_fields.names`
  與 `optional_fields`（讀契約檔斷言，非讀碼）；
  ⑤`receipt_schema.batch.lookahead_bars_declared` 仍存在且型別字面 `== Mapping[str,int>=0]`
  （讀契約檔斷言；防「移出 derived 時順手刪掉第三處」）；
  ⑥同批兩列之 `lookahead_bars_declared` 值不相同 ⇒ 拒（批內一致性）；
  ⑦🔴 **`ic_feed` 隔離之執行期斷言**：事件表帶 `future_1bar_return` 等欄時，
  `build_event_ic_inputs()` 之回傳**不含任何** `future_` 前綴之鍵，且 `event_label_values`
  之值逐一 `==` 各列 `label_value`（**實跑比對，非斷言 doc 字面**——doc 是散文，
  只驗字串等於把限制降級成宣稱）。
- **mutation**：把 `lookahead_bars_declared` 加回 `derived_fields.names` ⇒ ④轉紅；
  移除 `optional_fields` 之 `future_7bar_return` ⇒ ①轉紅；
  自 `receipt_schema.batch` 刪掉 `lookahead_bars_declared` ⇒ ⑤轉紅；
  批內一致性檢查改為只驗第一列 ⇒ ⑥轉紅；
  `build_event_ic_inputs` 改以 `future_1bar_return` 充當 label 值 ⇒ ⑦轉紅。還原皆轉綠。

#### R2 之更正（🔴 主委第六次「宣稱大於實作」，形態與 R1 同型）

R2：composer **APPROVED**、grok **APPROVED**、codex **REJECTED**——**REJECTED 又是對的**。
codex 之理由逐字：「A-020 未如實收錄 codex consult 明列的限制：`future_*` 僅供 Excel 攜帶、
不得進 `ic_feed`；D-004 僅禁止其參與深度導出。」

主委逐家回讀 consult 原文後確認**不只 codex 一家這樣裁，而是三家一致**，且漏的不只一條：

| 漏記之限制 | 三家 consult 原文出處 |
|---|---|
| `future_*` 之 doc 須含「不進 `ic_feed`」 | codex「附帶欄不進 `ic_feed`、不決定 horizon」／composer `RULING-4` 判準 2 之 doc 字面／grok `RULING-4` 判準 2 之 doc 字面 |
| `receipt_schema.batch.lookahead_bars_declared` **保留**、對齊後複製至該處 | codex「保留 receipt batch schema；匯入時映射至 receipt」／composer 判準 1 之 doc 字面／grok 判準 1 之末行「**保留**（已存在）」 |
| validator 須驗**批內一致性** | codex「逐列同值以滿足 `records[0]`，並由 validator 驗型/批內一致性」（另兩家未反對 ⇒ 採較嚴版） |
| 缺欄仍合法、匯出檔必帶 | codex「缺欄仍合法，匯出檔必帶」 |

🔴 **形態與 R1 完全相同**：R1 是「未逐家交叉核對即宣稱一致」而採了少數版；
R2 是**同一動作的另一半**——三家一致講了某條限制，主委摘要時整條掉了，卻仍標「三家一致」。
⇒ **對策不是「下次記得」**：本節之判準字面已逐條標出 consult 原文出處欄，
下一輪核對者可**逐格回查**，不必依賴主委的摘要。

🔴 **另一件必須寫下來的事**：本輪 composer 與 grok 皆對 A-020 標「一致／如實」，
但兩家自己的 consult 原文**都**寫了那條 doc 字面 ⇒ **兩家也沒回讀自己的原文**。
「兩家 APPROVED」因此**不構成**放行理由（B4／B5 之第 1 條教訓在戳記輪同樣成立）。

### A-021 — Task 4.1 移除主答案窗後，B5 下界守衛之改形（不刪、不留死碼）

- **背景**：B5（`D-002 A-004` 之解除）把下界守衛整套綁在匯出面板之 `eventHorizonBars`；
  Task 4.1 要移除的正是那個單選。
- **關鍵碼證**：`momentum/Analysis/event_samples/lookahead_depth.py:76-89` 之
  `depth_by_timeframe` 計算 `max(declared, *欄位深度)`——`declared` 是輸入之一；
  而 SPEC 4.1 要求 `window.horizon_bars = max(1, lookahead_bars_declared[**該列** timeframe])`，
  即**逐列依該列 tf** 導出。
- **裁定**（(a)(b)(d)(e) 三家一致；**(c) 為 2 vs 1，取 codex＋grok**）：

  🔴 **本條之初版記載有誤，由 D-004 戳記輪 R1 之 codex REJECTED 當場擋下**：
  主委逐字採用了 composer 表格中「自 `/search` 匯出路徑**移除** `withHorizonLowerBoundGuard`」
  那一格，並將整條標為「三家一致」——**但 codex 與 grok 皆裁「保留 `proceed` 結構保證、改簽章」**。
  codex 之 REJECTED 理由逐字：「codex 原裁定要求保留 withHorizonLowerBoundGuard 包住所有下載副作用
  並承擔 readiness fail-closed；D-004 卻寫成自 /search 匯出路徑移除」。
  ⇒ 這是本 epic 主委第**五**次「宣稱大於實作」（前四次見 `handoffs/reconcile/20260826-gap3ux-b6-review-r6/synth.md`），
  形態＝**未逐家交叉核對即宣稱一致**。已改為採多數且較嚴之 codex＋grok 版。
  🔴 併更正：`handoffs/reconcile/20260826-gap3ux-b7-consult-r1/synth.md` 之群集 B 表格
  亦承載同一錯誤（該檔已銷帳不就地改，更正處為本節）。

  | 子題 | 裁定 |
  |---|---|
  | `declared_window_bars` | `/search` 路徑各 tf 送 **`0`**；**不得省略鍵**（缺 tf ⇒ `KeyError`，`lookahead_depth.py:66-69`） |
  | `exportAllowedUnderBound` | 刪 `selectedBars` 參數與 `selectedBars >= bound` 比較（4.1 後恆真＝死碼），改名 `exportAllowedByLowerBoundState(state)`；`unconstrained`／`resolved` ⇒ `true`，`pending`／`error` ⇒ `false` |
  | `withHorizonLowerBoundGuard` | 🔴 **保留 `proceed` 結構保證，改簽章與職責**（**非**移除）：改為 `withExportLowerBoundGuard(state, {notify, proceed})`——`pending`／`error` ⇒ notify 且**不呼叫** `proceed`；否則 `return proceed()`。**整段下載／組裝仍包在 `proceed` 內**，保留 B5／`D-002 A-004` 之「擋在網路動作**之前**」這個**結構事實**。職責由「比較選值與下界」改為 **readiness fail-closed**。🔴 **不得**退回裸 `if (…) return;` 後接長串 `await`——那是 B5 R3 已否定、可被 AST 繞過之形狀 |
  | `inexpressible` | **改為可匯出**：各 tf 深度不全相同時回 `{status:'resolved', bound:null}`；匯出寫**逐列** `window.horizon_bars` |
  | `horizonOptions()` | **刪除**（B7 後無 caller＝死碼）；Task 7.6 之 IC 答案窗用 `ICConfigPanel` 本地常數 |

- **`inexpressible` 為何可解除**：它當初存在是因單一 scalar 表達不了逐 tf 之不同下界
  （SPEC §D-3′-a(ii) 禁「以單一 batch scalar 冒充 per-scope 下界」）；
  4.1 之後 `horizon_bars` **逐列**寫入、依該列自己的 tf ⇒ 混 TF 已可表達。
  三家皆**未能**構造「逐列寫入仍不足以表達 per-scope 下界」之反例；
  composer 另指出：混 TF 不同深度時 Task 4.1b 本就要求「逐 tf 各顯示一行」，
  與 `inexpressible` 之「單一答案窗」前提**互斥**。
- **🔴 `D-002 A-004` 之解除不得因此失效**：`pending`／`error` 之 fail-closed
  （算不出下界即不得匯出）**保留**，且**仍由 `proceed` 之結構保證承載**——
  述詞只決定「要不要呼叫 `proceed`」，不取代包裹本身。
- **不可做**：不得默默刪掉整個守衛；不得保留守不住任何東西的死碼；
  🔴 不得把包裹拆成裸 `if (…) return;` 後接長串 `await`（B5 R3 已否定之形狀）。
- **驗證**：`npm --prefix frontend test -- --run exportFilter` 之下界節須含——
  ①`pending` ⇒ 不允許匯出；②`error` ⇒ 不允許；③各 tf 深度不同 ⇒ **允許**且 `bound === null`；
  ④`exportFilter.ts` 不再 export `horizonOptions`（讀模組 export 面斷言，非 grep 原始碼）。
  ⑤🔴 **page runtime**：`pending`／`error` 時於 `/search` 真的按匯出 ⇒
  `buildEventContractRecords` 之呼叫次數 `== 0`（執行期計數，非讀碼形狀）。
- **mutation**：`pending` 改為允許匯出 ⇒ ①⑤轉紅；把不同深度改回 `inexpressible` ⇒ ③轉紅；
  把 `proceed` 包裹拆成裸 `if (…) return;` ⇒ ⑤須仍能抓到（若抓不到，表示 ⑤ 是形狀而非執行期斷言）。

### A-022 — SPEC Task 4.2 與交接 §2B.1 之「G-2 golden 須重凍」為誤植

- **原文**：SPEC Task 4.2 驗收條「**且 G-2 事件 golden 須同步更新並在 commit message 說明**」；
  交接 `docs/GAP3UX_IMPL_HANDOFF.md` §2B.1「4.2 改列數 ⇒ golden **必然不符**」。
- **實況**：`scripts/gap3_freeze_golden.py` 之 `_run` 來自
  `scripts/gap2_freeze_golden.py`，跑的是 `tests.momentum.helpers.ichc_run.run_analyze`
  （**IC 分析**管線，`ic_gatekeeper` case），凍的是 IC 報告之 `summary_table` ＋ `canonical_sha`；
  它**不呼叫** `analyze_tables`／`event_forward_return_table`——而 Task 4.2 動的正是後者。
- **實測**：加入 4 條 `-k horizon_curve` 測試後執行
  `python3 scripts/gap3_freeze_golden.py --check` ⇒ rc=0，
  `canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463` **未變**。
  三家 consult 一致複驗此判斷成立。
- **裁定**：B7 **不重凍** G-2；commit message **不得**寫「已重凍 golden」。
  SPEC 該句以本延伸檔具名更正（SPEC 已 FROZEN，不就地改）；交接 §2B.1 於 B7 收尾時更正。
- **為何要寫下來**：照抄一句沒查證的話去宣稱一件沒發生的事，正是本 epic 已犯四次之
  「宣稱大於實作」；不留下更正，下一個 session 會再照抄一次。
- **驗證**：`python3 scripts/gap3_freeze_golden.py --check` rc=0 且
  `canonical_sha` 等於上列值；`grep -c "必然不符" docs/GAP3UX_IMPL_HANDOFF.md` `== 0`（收尾後）。
- **mutation**：不適用（本條為文件更正，無產品碼落點）；其可證偽性由上列 `--check` 承載。

## 驗證（本延伸檔整體）

- `bash scripts/doc_format_precheck.sh docs/GAP3_EVENT_UX_TODO.D-004.md` rc=0
- `pytest tests/momentum/event_samples/ -q -k gap3_attached_columns_contract` **≥7 條**
- `npm --prefix frontend test -- --run exportFilter` 之下界節四條
- `python3 scripts/gap3_freeze_golden.py --check` rc=0（`canonical_sha` 不變）
- 三家 **RECONCILE-STAMP APPROVED**（比照 `D-002`；戳記前不得動契約）

## 修訂一覽

| 代號 | 觸及 | 裁定 | 日期 |
|---|---|---|---|
| **A-020** | Task 4.1 之匯出欄 vs 契約 | 🔴 實測 `unknown_field` 拒收 ⇒ 照 SPEC 字面實作會產出**匯不回去的檔**；改契約：`lookahead_bars_declared` 移出 `derived_fields` 入 `optional_fields`（**`receipt_schema.batch` 之同名鍵保留**、驗批內一致性）、`future_{1..12}bar_return` 逐欄列舉入 `optional_fields`（契約無 pattern 機制），兩者 doc 字面須含指定限制（🔴 **`future_*` 不進 `ic_feed`**；初版漏記三家一致之三項限制，由戳記輪 R2 codex REJECTED 擋下） | 2026-08-26 |
| **A-021** | Task 4.1 移除主答案窗後之下界守衛 | 改形不刪：`declared` 送 0、刪 scalar 比較與 `horizonOptions`、`inexpressible` 改為可匯出（逐列寫入已可表達 per-scope）、🔴 **`proceed` 結構保證保留並改簽章**（非移除；(c) 為 2 vs 1，初版誤採少數版並誤標「三家一致」，由戳記輪 codex REJECTED 擋下） | 2026-08-26 |
| **A-022** | SPEC Task 4.2 ＋ 交接 §2B.1 之 G-2 重凍句 | 誤植：golden 跑 IC 管線、不碰 `analyze_tables`；實測 `--check` rc=0、sha 未變 ⇒ **不重凍**、commit message 不得寫「已重凍」 | 2026-08-26 |

## 戳記

（委員於此 append；格式：
`RECONCILE-STAMP: <family> APPROVED <YYYY-MM-DD> sha256:<body-hash> task:<harness-task-id>`）

RECONCILE-STAMP: composer APPROVED 2026-08-26 sha256:2c8780355cc9011ff79ae9f468c611930e336af6a96a6ad1536de8d6cf558c13 task:20260826-GAP3UXTODOD004-X-STAMP-R1
RECONCILE-STAMP: grok APPROVED 2026-08-26 sha256:2c8780355cc9011ff79ae9f468c611930e336af6a96a6ad1536de8d6cf558c13 task:20260826-GAP3UXTODOD004-X-STAMP-R1
RECONCILE-STAMP: codex REJECTED 2026-08-26 sha256:2c8780355cc9011ff79ae9f468c611930e336af6a96a6ad1536de8d6cf558c13 task:20260826-GAP3UXTODOD004-X-STAMP-R1 — A-021 記載與 codex consult 裁定不符：codex 原裁定要求保留 withHorizonLowerBoundGuard 包住所有下載副作用並承擔 readiness fail-closed；D-004 卻寫成自 /search 匯出路徑移除。
RECONCILE-STAMP: composer APPROVED 2026-08-26 sha256:705f4ad0ac7ad4360216f20067d1878d76e2c04789b300def58fab7f4b0421ad task:20260826-GAP3UXTODOD004-X-STAMP-R2
RECONCILE-STAMP: grok APPROVED 2026-08-26 sha256:705f4ad0ac7ad4360216f20067d1878d76e2c04789b300def58fab7f4b0421ad task:20260826-GAP3UXTODOD004-X-STAMP-R2
RECONCILE-STAMP: codex REJECTED 2026-08-26 sha256:705f4ad0ac7ad4360216f20067d1878d76e2c04789b300def58fab7f4b0421ad task:20260826-GAP3UXTODOD004-X-STAMP-R2 — A-020 未如實收錄 codex consult 明列的限制：future_* 僅供 Excel 攜帶、不得進 ic_feed；D-004 僅禁止其參與深度導出。
RECONCILE-STAMP: codex APPROVED 2026-08-26 sha256:12a8fc74a86550f1ea09787419d3c9e504877f695326cf43a74a949a4f955403 task:20260826-GAP3UXTODOD004-X-STAMP-R3
RECONCILE-STAMP: composer APPROVED 2026-08-26 sha256:12a8fc74a86550f1ea09787419d3c9e504877f695326cf43a74a949a4f955403 task:20260826-GAP3UXTODOD004-X-STAMP-R3
RECONCILE-STAMP: grok APPROVED 2026-08-26 sha256:12a8fc74a86550f1ea09787419d3c9e504877f695326cf43a74a949a4f955403 task:20260826-GAP3UXTODOD004-X-STAMP-R3
