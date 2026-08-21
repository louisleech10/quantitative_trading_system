# GAP-3 B5 review R4 — grok（閉合輪：原提出方重跑 R3 反例）

task-id: 20260822-GAP3-B5-REVIEW-R4
family: grok
brief-kind: review
brief: handoffs/20260822-gap3-b5-review-r4-brief.md
R3 修補 diff: `git diff 1c54049b..HEAD`
R3 收斂: handoffs/reconcile/20260822-gap3-b5-review-r3/synth.md
修後 receipt: handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log

## Verdict：可進三家 RECONCILE-STAMP／交使用者 UAT（己方 GROK-R3-P0-01＝CLOSED；他家 R3／R2-OPEN 複核同意 CLOSED；本輪無新 finding）

### 必答

1. **己方 R3／他家：CLOSED／OPEN（附重跑）**

   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R3-P0-01 | **CLOSED**（原提出方重跑） | `bash scripts/plain_docs_sync_check.sh` →「全數同步（受管 10 檔）」**rc=0**（直接取 rc）。`git log -1 --oneline`＝`013aa69f` 同 commit 含看板＋R3 修補；與 brief／receipt「plain_docs rc=0」於 HEAD 對齊。 |
   | COMPOSER-R3-P2-01 | **複核同意 CLOSED** | 同 plain_docs 探針 rc=0；Z4 群集與己方 P0 同源。 |
   | CODEX-R3-P1-01 | **複核同意 CLOSED** | 同 plain_docs rc=0；看板時序已修。 |
   | CODEX-R3-P1-02 | **複核同意 CLOSED** | `search/page.tsx`：`eventHorizonBars` 預設 2、confirm 用 `n_missing_label_value`；`eventExport.ts` 回傳該計數；`npx vitest run gap3 pendingFeatures` → **22 passed** rc=0（組裝器＋頁面接線字面）。 |
   | CODEX-R3-P2-03 | **複核同意 CLOSED** | `test_pipeline.py` monkeypatch `_all_bars_for_events` 注入 spy；斷言 `scores[(sym,t₀−k)]==1.0`／`scores[(sym,t₀)]==0.0`／`sum==3`。`pytest …/test_pipeline.py -q -k decision_bar` → **1 passed**。In-memory：buggy `vals[i]` ⇒ 6 fails；`vals[i-k]` ⇒ 0 fails（`FALSIFIABILITY_OK`）。 |
   | CODEX-R2-P1-03 | **複核同意 CLOSED** | 檔案端點選用 `source_file`；`verify_source_digest=true` 且未附 ⇒ 400 `source_file_required_for_verify`；兩檔齊 ⇒ 200＋`source_digest_verified=true`；竄改 ⇒ 422 `digest_mismatch`。`pytest tests/api -q -k "gap3_import and (verify or companion)"` → **3 passed**；全 `-k gap3_import` → **15 passed**。vitest companion sha256 對照 node:crypto 含於 22 passed。 |

2. **修補是否引入新問題（brief Q2 四點）？**

   - ①**`source_file` 選用、未附時既有呼叫端**：`File(None)`＋`verify_source_digest` 預設 `False`；未開 verify 時不讀／不要求 `source_file`。`test_gap3_import_file_verify_requires_source_file` 末段：關 verify 只傳 `file` ⇒ **200**。**行為不變**。不開 finding。
   - ②**`verify_source_digest` 未附 `source_file` ⇒ 400**：顯式 `source_file_required_for_verify`；「上傳檔即來源檔」路徑＝同一檔同時放 `file` 與 `source_file`（brief assumed，見下攻擊）。**可接受**——自我對證本就必然 mismatch，400 優於一堆 `digest_mismatch`。不開 finding。
   - ③**雙檔 `link.click()`**：連續兩次下載屬 UI 便利性；瀏覽器可能擋第二次——**非正確性**（使用者仍可手動存 companion）。不開 P0/P1。
   - ④**horizon 選單預設 2**：`useState<number>(2)`；`buildEventContractRecords` `horizonBars ?? 2` 寫入 `label_definition.window.horizon_bars`；vitest 斷言 h=2／h=4 對齊。**一致**。不開 finding。
   - **觀察（非 finding）**：`case.py` Query description 仍寫「對證位元組＝source_file（若提供）否則 file 自身」，但 route 在 verify=true 時硬性 400 要求 `source_file`——說明字與行為略漂，400 訊息已足夠引導；禁湊數不升格。

3. **B5 Gate 複驗 rc=0？可進 stamp／交使用者 UAT？**

   **可以（grok 本輪）**——本輪實跑：`plain_docs` **rc=0**；`tests/api -k gap3_import` **15 passed**；`-k "gap3_import and (verify or companion)"` **3 passed**；`-k decision_bar` **1 passed**；`npx vitest run gap3 pendingFeatures` **22 passed**。`npm run build` 依 brief「只准一家跑一次」引修後 receipt rc=0，未並行重跑。前提：同輪他家原提出方對己條 CLOSED、三家無新 BLOCKING。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：「上傳檔即來源檔」改為同一檔同時放 `file` 與 `source_file` 可接受（不另加旗標） | **成立（攻擊不推翻）** | `/search` 主路徑本就 events≠source（companion）；真需「事件檔＝來源」的呼叫端只多傳同 bytes 一次。預設 `verify=false` 呼叫端零改動。另加旗標＝過度工程且與「契約來源檔」語意重複。 |
| **assumed**：companion `*.source.json` canonical 欄位集（symbol/timeframe/timestamp/positive_case/price_change）足以作 provenance **來源**定義 | **成立（攻擊不推翻）** | digest 綁的是搜尋命中「來源」而非整份事件匯出；`label_value`／`future_*` 故意可手改後匯入（契約允許、verify 不覆蓋標籤）。竄改來源五欄 ⇒ digest 變（vitest）；竄改 label_value 仍可過 verify＝**設計邊界**，非本輪回歸。若要綁標籤須另定契約欄——超出本輪修補。 |
| fact-verified: api 15／event_samples 230／FE+GAP-1 289／vitest 22／build rc=0／plain_docs rc=0 | **本輪子集實核成立；全套／build 引 receipt** | 本輪：api 15、verify/companion 3、decision_bar 1、vitest 22、plain_docs rc=0。event_samples 230／289／build 引 `20260822T014000Z-…` receipt（禁並行 build）。 |

## GROK-R3-P0-01

**斷言**: （閉合）R3 修補 commit `013aa69f` 已同 commit 更新 `白話說明/GAP-3施工進度.md`；HEAD 上 `bash scripts/plain_docs_sync_check.sh` **rc=0**，原「WATCHED 新於看板／敘事稱 rc=0」矛盾已消除。STATUS=**CLOSED**。

**碼證**: 本輪 `bash scripts/plain_docs_sync_check.sh` → stdout「✓ 白話說明 全數同步（受管 10 檔）」、**rc=0**（直接取 rc，未經 pipe）。`git log -1 --oneline -- 白話說明/GAP-3施工進度.md` 落在 `013aa69f`（與 R3 修補同 commit）。`RECHECK:` 同上命令須持續 rc=0。

**來源摘要**: handoffs/20260822-gap3-b5-review-r4-brief.md#00a885cee1ca；handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log#8fa0d1b52484；scripts/plain_docs_sync_check.sh#1d127ae13f1a；白話說明/GAP-3施工進度.md#aed2051f213a；handoffs/20260822-gap3-b5-review-r3-grok.md#e37ed0b2cd50

正文：原提出方重跑閉合；不進本輪 OPEN 分母。摩擦八十九（commit 前 `--staged`）為流程補強，本輪只驗 HEAD Gate 綠。

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——己方 GROK-R3-P0-01 重跑 CLOSED；CODEX-R2-P1-03／CODEX-R3-P1-01／P1-02／P2-03／COMPOSER-R3-P2-01 複核同意 CLOSED；R3 修補（source_file 驗證路徑、decision_bar 真攔截、horizon confirm、看板同步）未引入可證偽 P0–P2 新缺陷；brief 兩條 assumed 攻擊不推翻。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=0；`venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"` → **3 passed** rc=0；`… -k gap3_import` → **15 passed** rc=0；`…/test_pipeline.py -q -k decision_bar` → **1 passed** rc=0；in-memory falsify buggy `vals[i]` 紅／`vals[i-k]` 綠；`cd frontend && npx vitest run gap3 pendingFeatures` → 4 files／**22 passed** rc=0。落點：`api/routes/case.py:141-165`；`frontend/src/lib/eventExport.ts:61,118-121`；`frontend/src/app/search/page.tsx:53-54,526-548`；`tests/momentum/event_samples/test_pipeline.py:101-130`；`tests/api/test_gap3_import.py:207-251`。`npm run build` 引 receipt rc=0（brief 禁並行）。

**來源摘要**: handoffs/20260822-gap3-b5-review-r4-brief.md#00a885cee1ca；handoffs/reconcile/20260822-gap3-b5-review-r3/synth.md#1d1b0e21fb64；handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log#8fa0d1b52484；api/routes/case.py#c481747e887b；frontend/src/lib/eventExport.ts#b2024ac8970f；frontend/src/app/search/page.tsx#4b967e3fb875；tests/momentum/event_samples/test_pipeline.py#4aa6ee3bcfc0；tests/api/test_gap3_import.py#51774859bf14

正文：閉合輪義務＝重跑己方 R3 反例＋複核他家修補＋掃本輪修補引入面；三項皆通過。不受理 SPEC/TODO 重審／G3-R11／ML／效能門檻／R1–R3 已裁 CLOSED 再議。禁捏造湊數。Query description「否則 file 自身」字面漂移僅記觀察。

## 被當成事實的未驗證假設（§0）

見上表；兩條 assumed 攻擊不推翻。fact-verified 子集本輪實核；build／event_samples 全套／289 引 receipt。

ASSUMPTIONS_VERIFIED: GROK-R3-P0-01 plain_docs HEAD rc=0→CLOSED；CODEX-R2-P1-03 兩檔 verify／缺檔 400／竄改 422→複核同意 CLOSED；CODEX-R3-P2-03 spy 真斷言＋falsify→CLOSED；CODEX-R3-P1-02 horizon+confirm→CLOSED；Q2①預設呼叫不變②雙欄上傳可接受③雙 click 非正確性④horizon 預設=2 與 label_definition 一致；assumed 兩條攻擊不推翻
TESTS_RUN: `bash scripts/plain_docs_sync_check.sh` → rc=0；`venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"` → 3 passed rc=0；`venv/bin/python -m pytest tests/api -q -k gap3_import` → 15 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar` → 1 passed rc=0；in-memory falsify → FALSIFIABILITY_OK；`cd frontend && npx vitest run gap3 pendingFeatures` → 4 files／22 passed rc=0；`npm run build` 未本輪重跑（brief 禁並行），引 receipt rc=0；event_samples 230／FE+GAP-1 289 引 receipt
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260822-gap3-b5-review-r4-grok.md

STATUS: DONE
