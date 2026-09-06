# GAP-3 事件分析頁揭露補完 — TODO

改什麼: 依 `docs/GAP3_EVENT_DISCLOSURE_SPEC.md` Phase 1（Task 1.1–1.5）產生冷啟動可寫碼之施工清單。本票**不改任何數值計算**，全部是「系統已算出來但沒告訴使用者」之投影與顯示。

為什麼: 2026-09-06 使用者 UAT B21／B22／B23 回報十條。主委實跑定性後：**無一項是數值算錯**——一項真缺陷（當根時 h 掃描未停用）、兩項 UI 揭露缺失（主結果 vs 掃描矩陣、`degraded_full_sample` 之原因與門檻）、其餘為文案缺口。

## 觸及面宣告
新增: `frontend/src/lib/eventParamDocs.ts`；`白話說明/GAP-3驗收清單.md` 之 B24。
覆寫: none（既有 Task 之產出皆不改條文）。
依賴: `docs/GAP3_EVENT_UX_SPEC.D-001.md` D4.3（k/h 掃描）與 D5.3（隨機對照組）之既有交付；本票只在其上加揭露。

## 內容

## §0 全域規則與約束（執行端讀完即可遵守）
- 實作者＝Claude 主委自任（ORCH §1 現行分工行）；完成後三家 code review（codex＋composer＋grok）至閉合；實作者不自審。
- 解耦 7 條：`momentum/` 不 import `api/`；服務不互 import。Task 1.3 之新 metadata 一律由 `ic_analysis_service` 讀 report metadata 後投影，**前端與 route 不得直接讀 `ic_filter_orchestrator`**。
- **不得改動任何判定規則**：`_resolve_root_status` 之分支、`_scan_axes` 之軸導出、`min_test_rows` 之值——三者本票**唯讀**。
- **防幽靈功能**（B-D4／B-D5 各踩一次）：每個新 props／新揭露欄**必須有攔真實 render 或攔 HTTP body 之接線測試**，不接受「元件測試通過」。
- **防假綠**：既有斷言不得放寬；`icEventBatchDisclosure.test.tsx` 之既有 fixture 只准**加欄**，不得改既有期望值。
- **golden 為回歸護欄**：`tests/golden/gap3_label/*.json`（46）與 `tests/golden/gap3_random_control/*.json`（2）之值本票**必須逐位元組不變**，變動即代表誤觸計算路徑 ⇒ 不 merge。
- Logging：`get_logger(__name__)`；不得在 render 或迴圈內 log。

## §B 批次執行策略（依賴拓撲 → 一批；一次實作＋三家 review）

| Batch | 含 Task | 依賴 | 合併理由 | 規模 |
|---|---|---|---|---|
| **B-E1** | 1.1 1.2 1.3 1.4 1.5 | 無（皆建立在既有交付之上） | 五個 Task 動的是**同一個面板**與其唯一的後端揭露來源；拆批會讓 `EventBatchDisclosurePanel.tsx` 被連續改五次而每次都要重跑同一組 vitest，且 Task 1.1／1.4 之文案來源互為輸入（1.1 消費 1.4 的 `h_scan_inapplicable`） | 中 |

- **批內順序**（非批次 Gate，只是實作順序）：1.4（文案先建，其餘 Task 引用）→ 1.1 → 1.2 → 1.3 → 1.5（白話最後寫，寫的是已定案的行為）。
- **批次 Gate**：Phase 1 測試全綠 ＋ mutation 三條改壞→紅 ＋ golden 值逐位元組不變 ＋ 三家 review CLOSED ＋ commit 推送。
- 本票**只有一批**：五個 Task 合計動 6 個檔，不觸及數值計算，拆批之協調成本高於收益。

## Phase 1 — 事件分析頁之揭露與說明補完（目標：使用者看得到「為什麼」與「還差多少」；完成後畫面上每個要填的數字都有說明、每個降級都有具名原因）

### Task 1.1 — 當根（`open_to_close`）時停用 h 掃描（`票 UAT-B22-5`）
- SPEC ref：Task 1.1　目標：報酬量法為「當根」時，h 掃描之勾選與上限一律 disabled 並顯示不適用之理由。
- 輸入 / 輸出：`spec.label_return_mode`（既有 state）→ `hScanApplicable: boolean` → 兩個控制項之 `disabled` 與一則說明。
- 實作要點：
  1. 於 `EventBatchDisclosurePanel` 之 render 段（`ic-param-scan` 區之前）新增
     `const hScanApplicable = spec.label_return_mode !== 'open_to_close';`
     （**不查表、不查 preset key**——判準是**底層 mode**，因為進階區可直接改 mode 而不經 preset）。
  2. `ic-param-scan-h-toggle` 之 `disabled` 由 `undefined` 改為 `!hScanApplicable`；
     `ic-param-scan-h-max` 之 `disabled` 由 `!hScanOn` 改為 `!hScanApplicable || !hScanOn`。
  3. `useEffect(() => { if (!hScanApplicable && hScanOn) setScan({ horizon_bars_max: undefined }); }, [hScanApplicable])`
     ——切到當根時**清掉**既有的 h 上限（留著會讓送出之 `event_label_scan` 帶一個不會被用到的值）。
  4. `!hScanApplicable` 時 render `<span data-testid="ic-param-scan-h-inapplicable">`，
     文字取自 `EVENT_PARAM_DOCS.h_scan_inapplicable`（Task 1.4 提供，**不在元件內寫死**）。
- 修改檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`（h 掃描之兩個控制項與新 `useEffect`）。　既有 caller：同檔之 `setScan`；`frontend/src/app/ic-analysis/page.tsx`（傳 `labelScan`／`onChangeLabelScan`，不需改）。
- 路徑：
  - `frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`
  - `frontend/src/components/ic-analysis/icEventBatchDisclosure.test.tsx`
  - `frontend/src/lib/eventParamDocs.ts`
- 不可做：不得改 `_scan_axes` 或後端任何計算；不得把 `horizon_bars` 從送出的 `event_label_spec` 拿掉（契約四鍵，缺鍵 normalizer fail-closed）；不得以 preset key 當判準。
- 邊界：
  1. `labelSpec === undefined`（尚未選報酬量法）⇒ `hScanApplicable` 視為 **true**（不 disable）——尚未決定量法時 disable 會讓使用者以為壞了。
  2. `preset=same_bar` 時 **k 掃描仍可用**（k 對當根有意義，只有 h 沒有）。
- 風險緩解：⊘（顯示層，無數值影響）
- 驗證：`cd frontend && npx vitest run icEventBatchDisclosure`（rc 直接取）
  - `ASSERT npx vitest run icEventBatchDisclosure WHEN mode=open_to_close THEN rc=0`：`ic-param-scan-h-toggle` 之 `disabled === true` 且 `ic-param-scan-h-inapplicable` 存在
  - 正向對照：`mode=open_to_horizon_close` ⇒ 該 toggle `disabled === false` 且說明**不存在**
  - 切換對照：`mode=close_to_close` 勾 h 掃描填 `5` → 切 `mode=open_to_close` ⇒ `onChangeLabelScan` 最後一次收到之 `horizon_bars_max === undefined`
  - mutation：把 `hScanApplicable` 改成常數 `true` ⇒ 上述第一條紅
- **存活至**：保留（Phase 1 完工後仍是唯一的 h 掃描適用性判準）。
- **覆蓋風險**：無——Task 1.2／1.3 動的是不同區塊（掃描結果表、OOS 警語），不覆蓋本 Task 之控制項。

### Task 1.2 — 主結果與掃描矩陣之關係揭露（`票 UAT-B22-7,8`）
- SPEC ref：Task 1.2　目標：畫面明說「主結果＝框裡的 (k,h)」，且矩陣中對應那一格有標示。
- 輸入 / 輸出：`spec.decision_offset_bars`／`spec.horizon_bars` ＋ `labelScan.cells` → 一行說明 ＋ 逐格 `data-primary`。
- 實作要點：
  1. 於 `ic-param-scan-result` 區最上方 render `<p data-testid="ic-scan-primary-note">`，
     內容以模板字串帶入**當前 spec 之實際值**：`主要結果＝k＝${k}、h＝${h}（分析參數框裡的值）。下表是另外跑的；沒有勾掃描的那一軸就用框裡的值。`
  2. 逐格 render 時計算 `const isPrimary = c.k === spec.decision_offset_bars && c.h === spec.horizon_bars;`
     於該格 `<td>` 加 `data-primary={isPrimary ? 'true' : undefined}` 與可見標記（例：外框加粗＋「主」字）。
  3. 若 `cells.every(c => !isPrimary)`（主結果落在掃描範圍外），於 `ic-scan-primary-note` **追加**
     一句「主要結果不在下表範圍內」——**不得**靜默（使用者會以為漏了一格）。
- 修改檔案：`frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`（`ic-param-scan-result` 區之 render 迴圈）。　既有 caller：無（同檔內）。
- 路徑：
  - `frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`
  - `frontend/src/components/ic-analysis/icEventBatchDisclosure.test.tsx`
- 不可做：不得在前端重算任何一格之 IC；不得把主結果「塞進」矩陣當一格（兩者是分開跑的，合併顯示會讓人以為是同一次計算）。
- 邊界：
  1. 未開掃描（`labelScan == null`）⇒ 整區不 render，**不得**出現空表或孤兒說明行。
  2. 只開一軸（例：只掃 k）⇒ 另一軸只有框裡那個值，主格**仍須唯一**。
- 風險緩解：⊘
- 驗證：`cd frontend && npx vitest run icEventBatchDisclosure`
  - `ic-scan-primary-note` 之 `textContent` 含當前 `k` 與 `h` 之實際值；改 spec 之 k ⇒ 該行文字跟著變（**不是**寫死字串）
  - `document.querySelectorAll('[data-primary="true"]').length === 1`，且該格之 `data-testid` 為 `ic-scan-cell-${k}-${h}`
  - 主結果在範圍外（k 框＝5、k 掃 0～3）⇒ `data-primary` 之格子數 `=== 0` 且說明行含「不在下表範圍內」
  - mutation：把 `isPrimary` 改成常數 `false` ⇒ 第二條紅
- **存活至**：保留（掃描結果表之主格標示為長期功能）。
- **覆蓋風險**：無——本 Task 只在既有 `ic-param-scan-result` 區內加標示，不改該區之資料來源。

### Task 1.3 — `degraded_full_sample` 之原因與門檻投影到畫面（`票 UAT-B22-9`）
- SPEC ref：Task 1.3　目標：使用者看得到「為什麼沒有 OOS 保證」與「還差多少列」。
- 輸入 / 輸出：降級分支（`_downgrade_branch`）＋ fallback details → `metadata["oos_downgrade"]` → 前端一行說明。
  🔴 **R1 修訂**（`CODEX-R1-P2-06`／`GROK-R1-P2-01`）：**不經 task_info**。`DegradedBanner` 已讀
  `report.metadata`（同 `event_filter` 那條路），再開一條投影會是沒有消費端的死表面。metadata 為唯一 contract。
- 實作要點：
  1. `momentum/Analysis/ic_filter_orchestrator.py` 之 full-sample fallback 段（現行只 `logger.warning`，見 SPEC §A receipt）：
     於 `fallback_override` 組裝**之後**、rerun **之前**，把
     `{"reason": reason, "train_rows": train_rows, "test_rows": test_rows, "min_test_rows": min_test_rows}`
     寫入 `report["metadata"]["oos_downgrade"]`。
  2. 🔴 **R1 新增**：判定收斂為單一函式 `_downgrade_branch(meta) -> Optional[str]`，
     `_resolve_root_status` 改為其薄包裝（**分支順序與判準逐字不變**，由既有參數化基線測試守）。
     於 `_annotate_root_status_and_pass_class`（root 紅標之唯一寫出點）補：降級且該鍵缺席時
     寫 `{reason: <branch>, train_rows: null, test_rows: null, min_test_rows: null}`。
     **只在缺席時補**——fallback 已寫的四數字版不得被覆蓋。
  3. `frontend/src/lib/types.ts` 增 `ICOosDowngrade { reason: string; train_rows: number | null; … }`
     （三個列數可為 `null`：只有 fallback 那條路產生列數）；
     `DegradedBanner` 於警語**之下**加 `data-testid="ic-oos-downgrade"`：
     三個列數**同時為數字**才顯示列數段，否則顯示 reason 與其意義（`ic-oos-downgrade-no-rows`）。
- 修改檔案：`momentum/Analysis/ic_filter_orchestrator.py`（`_downgrade_branch`／`_resolve_root_status`／fallback 段／`_annotate_root_status_and_pass_class`）；`frontend/src/lib/types.ts`；`DegradedBanner.tsx`。　既有 caller：`_resolve_root_status` 之既有呼叫端（簽章不變）。
  🔴 **不動** `api/services/ic_analysis_service.py`——R1 裁定 metadata 為唯一 contract。
- 路徑：
  - `momentum/Analysis/ic_filter_orchestrator.py`
  - `api/services/ic_analysis_service.py`
  - `frontend/src/lib/types.ts`
  - `frontend/src/hooks/useICAnalysis.ts`
  - `frontend/src/components/ic-analysis/*.tsx`
  - `tests/api/test_gap3_oos_downgrade.py`
- 不可做：**不得**改 `_resolve_root_status` 之任何分支；不得因為要顯示而放寬 `min_test_rows`；不得在前端自行推算「還差幾筆事件」（**列數與事件數不是同一個量**，換算需要對齊層資訊）。
- 邊界：
  1. `analysis_status == "ok_oos"` ⇒ `oos_downgrade is None`，前端不 render 該行（**不得恆常出現**）。
  2. 非事件模式（全域 IC）之 fallback 同樣要有本欄——本欄不綁事件路徑。
- 風險緩解：本 Task 動 `ic_filter_orchestrator`（共用路徑）⇒ 完工後須跑 `venv/bin/python -m pytest tests/api -q -k "ic_ or gap3"` 確認無新增紅。
- 驗證：`venv/bin/python -m pytest tests/api/test_gap3_oos_downgrade.py -q` 全綠，且逐條：
  - 真實 115 筆事件批（`20260906T110025Z-c0bc6b37`）＋15 特徵 run ⇒ `oos_downgrade["reason"] == "rolling_warmup_insufficient"` 且 `oos_downgrade["min_test_rows"] == 131` 且 `oos_downgrade["test_rows"] < 131`
  - 正向對照：`analysis_status == "ok_oos"` 之情形 ⇒ `oos_downgrade is None`
  - `ASSERT venv/bin/python -m pytest tests/api/test_gap3_oos_downgrade.py -q WHEN mutation=drop_downgrade_projection THEN rc!=0`
  - golden 回歸：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0（46 cases，值不變）
- **存活至**：保留（`oos_downgrade` 為長期揭露欄，非事件路徑專屬）。
- **覆蓋風險**：無——本 Task 只**新增** metadata 鍵；`_resolve_root_status` 讀的鍵集不變，既有判定不被覆蓋。

### Task 1.4 — 參數說明文案單一來源（`票 UAT-B21-2,3,4／B23-1`）
- SPEC ref：Task 1.4　目標：每個使用者要填的數字旁邊都說得出「這是什麼、影響什麼」。
- 輸入 / 輸出：無輸入（靜態）→ `EVENT_PARAM_DOCS: Record<string, {what: string; effect: string}>`。
- 實作要點：
  1. 新建 `frontend/src/lib/eventParamDocs.ts`，匯出 `EVENT_PARAM_DOCS`，鍵**恰為 11 個**（R1 修訂後）：
     `horizon_bars`／**`decision_offset_bars_analysis`**／`advanced_pair`／`n_requested`／
     `decision_offset_bars_scan_max`／`horizon_bars_scan_max`／`seed`／`neighborhood_bars`／
     `embargo_bars`／`h_inert_same_bar`／`h_scan_inapplicable`。
     🔴 `CODEX-R1-P1-03`：k 之鍵**帶 `_analysis` 後綴**——契約已有同名 `decision_offset_bars.doc`
     （匯入欄位之 k），同名即第二份真相源。
     🔴 `CODEX-R1-P1-04`：`n_requested`／兩個 scan max 是 user-editable 數字欄，原本沒有說明。
  2. 每鍵之 `what` 一句（這是什麼）、`effect` 一句（影響什麼）。內容依 SPEC §A 之定性：
     `horizon_bars`＝往後看幾根決定答案；影響＝**換 h 等於換問題**，IC 不可跨 h 比較。
     `decision_offset_bars`＝提前幾根決定；影響＝特徵截止點往前，可用資料變舊，IC 通常變低。
     `advanced_pair`＝直接改底層 entry／mode，可組出 preset 沒有的組合；影響＝一般用不到，開放是因為矩陣已全開。
     `seed`／`neighborhood_bars`／`embargo_bars` 見 SPEC §A。
     `h_scan_inapplicable`＝當根只看事件那一根，h 不參與計算，掃出來每格都一樣。
  3. 元件以 `data-testid="ic-param-doc-<key>"` render `what` 與 `effect`。
- 修改檔案：新增 `frontend/src/lib/eventParamDocs.ts`；`EventBatchDisclosurePanel.tsx`（六處 render，`h_scan_inapplicable` 由 Task 1.1 消費）。　既有 caller：新建無。
- 路徑：
  - `frontend/src/lib/eventParamDocs.ts`
  - `frontend/src/lib/eventParamDocs.test.ts`
  - `frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx`
- 不可做：**不得**把契約既有 `doc` 複製進本檔（`entry_price_semantic`／`label_return_mode` 已有 `eventContractDocs.ts` 鏡像，複製即第二份真相源）；不得在本檔寫任何數值門檻（門檻來自後端揭露，見 Task 1.3）。
- 邊界：
  1. `/search` 已無 k 控制項 ⇒ 該頁**不得**出現 `ic-param-doc-decision_offset_bars`。
  2. 契約已有 `doc` 之欄位**不進**本檔——以測試斷言兩邊鍵集**不相交**。
- 風險緩解：⊘
- 驗證：`cd frontend && npx vitest run eventParamDocs icEventBatchDisclosure`
  - `Object.keys(EVENT_PARAM_DOCS).length === 7`，每鍵之 `what`／`effect` 皆非空
  - 六個 `ic-param-doc-<key>` 皆在 DOM，文字**逐字等於** `EVENT_PARAM_DOCS[key]`（不是 `toContain`）
  - 鍵集相等：`new Set(Object.keys(EVENT_PARAM_DOCS))` 減去 `h_scan_inapplicable` 後，與 DOM 實際 render 的 `ic-param-doc-*` 集合**相等**（多一個沒顯示、少一個顯示不出來皆紅）
  - 不相交：`Object.keys(EVENT_PARAM_DOCS)` ∩ `Object.keys(EVENT_CONTRACT_DOCS)` `=== 0`
- **存活至**：保留（本檔為 UI 文案之單一來源，後續新參數一律加在此）。
- **覆蓋風險**：無——Task 1.1 只**消費** `h_scan_inapplicable`，不改寫本檔任何鍵。

### Task 1.5 — 白話驗收清單同步（`票 UAT-B21,22,23`）
- SPEC ref：Task 1.5　目標：`白話說明/GAP-3驗收清單.md` 與本票交付一致，並新增 B24。
- 輸入 / 輸出：本票四個 Task 之 testid 與行為 → 清單之 B21／B22／B23 修訂 ＋ 新增 B24。
- 實作要點：
  1. B21 補一段：選「當根」時 **h 掃描也會一起變灰**，並說明理由（當根不用 h）。
  2. B22 補兩段：①主結果＝框裡的 (k,h)，矩陣會標出是哪一格；②沒勾掃描的那一軸用框裡的值（不是獨立的）。
  3. B23 之三個參數說明改為「對照畫面上那行說明」（畫面已有文案，清單不再重寫一份）。
  4. 新增 **B24 ── 沒有 OOS 保證時，看得到為什麼**：你做什麼（跑一個小事件批）／應該看到什麼（警語下方一行具體原因與門檻）／不是這樣代表什麼（只有籠統警語＝Task 1.3 沒生效）。
  5. 簽字表加 B24 一列。
- 修改檔案：`白話說明/GAP-3驗收清單.md`（B21／B22／B23 段落 ＋ 新增 B24 ＋ 簽字表）。　既有 caller：`docs/site/GAP-3驗收清單.html`（由 `plain_docs_render.sh` 生成，同 commit 產出）。
- 路徑：
  - `白話說明/GAP-3驗收清單.md`
  - `docs/site/GAP-3驗收清單.html`
- 不可做：不得把 `rolling_warmup_insufficient` 這類技術字面直接搬進白話清單而不附解釋；不得刪除既有已標 OK 之項次。
- 邊界：
  1. 清單為使用者文件 ⇒ 出現的每個英文字面都要有中文解釋。
  2. B24 之「應該看到」須寫**具體數字形態**（例「訓練 82 列、測試 30 列，需要至少 131 列」），不得只寫「會顯示原因」。
- 風險緩解：⊘
- 驗證：`bash scripts/plain_docs_render.sh --check` rc=0；
  `grep -c "B24" 白話說明/GAP-3驗收清單.md` **== 2**（一處內文、一處簽字表）；
  `grep -c "ic-param-scan-h-inapplicable\|ic-scan-primary-note\|ic-oos-downgrade" frontend/src/components/ic-analysis/EventBatchDisclosurePanel.tsx` **>= 2**
- **存活至**：保留（B21–B24 為使用者驗收之常設項）。
- **覆蓋風險**：無——本 Task 為本批最後執行，不會被同批其他 Task 覆寫；日後票若再改畫面，須同步本清單（規則已寫在清單開頭）。

### Phase 1 測試（單元 / 邊界 / 效能三層）+ Phase Gate
- **單元**：`cd frontend && npx vitest run`（全綠）；`venv/bin/python -m pytest tests/api/test_gap3_oos_downgrade.py -q`（全綠）。
- **邊界**：未選量法／未開掃描／只開一軸／主結果在範圍外／`ok_oos` 無降級——各一條測試。
- **效能**：⊘（純顯示層，無新增計算；Task 1.3 之投影為 dict 讀取）。
- **回歸護欄**：`gap3_label` 46 檔與 `gap3_random_control` 2 檔 `--check` rc=0 且**值逐位元組不變**；
  `venv/bin/python scripts/check_decoupling_imports.py --baseline scripts/decouple_baseline.txt` → `BASELINE OK`；
  `cd frontend && npx tsc --noEmit` **8 行**（既有債，不得新增）。
- **Phase Gate**：上列全綠 ＋ mutation（Task 1.1／1.2／1.3 各一條）改壞→紅 ＋ 三家 code review CLOSED ＋ `bash scripts/restore_golden_inventory.sh` ＋ commit＋push。
