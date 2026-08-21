# Reconcile — 20260822-gap3-b5-review-r4

**來源** 20260822-gap3-b5-review-r4-codex.md, 20260822-gap3-b5-review-r4-composer.md, 20260822-gap3-b5-review-r4-grok.md　|　**roster** codex,composer,grok

<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。
     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->

## 群集 / 處置（主委 Claude 裁決；R3 全 CLOSED＋codex 一條 P1 修補）

**Verdict**: 需修補後合併——R3 六條（含 R2-P1-03 續修）由原提出方重跑全數 CLOSED，composer／grok 判可進 stamp、0 新 findings；**codex 抓 CODEX-R4-P1-01 成立**（我在 brief 宣稱「同檔可通過 verify」不實）已修。R5 由 codex 重跑同一探針閉合（兩家 sentinel 複核）→ 三家 RECONCILE-STAMP → 交使用者 UAT。

**修後實測（receipt `handoffs/run_receipts/20260822T023000Z-gap3-b5-r4-fix-gate.log`；數字自 receipt 複製）**：`tests/api -k gap3_import` **16 passed**／rc=0；`tests/momentum/event_samples/` **230 passed**／rc=0。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| W1 同檔 verify 相容宣稱不實 | CODEX-R4-P1-01 | **採納**：事件檔含自身 `source_file_digest` 欄 ⇒ 對自己取 sha256 恆不自洽，同檔對證**數學上不可能**。改為路由層機械拒：`source_file` 位元組 == 事件檔 ⇒ 400 `source_file_must_differ_from_event_file`（訊息指出正解＝附產生事件的來源檔／`*.source.json`，或關閉 verify）；`verify_source_digest` 之 description 與 service docstring 一併改為「**必須另附相異來源檔**」；UAT 增 B2b 驗這三態。**我在 R4 brief 的 assumed「同一檔同時放 file 與 source_file 可接受」為錯**——codex 以 service-level 探針推翻，記錄於此 |
| W2 R3 六條閉合 | CODEX-R2-P1-03（R3 OPEN）, CODEX-R3-P1-01, CODEX-R3-P1-02, CODEX-R3-P2-03, GROK-R3-P0-01, COMPOSER-R3-P2-01 | **CLOSED**：companion 驗證三態（200／400／422）、plain_docs rc=0、匯出 horizon 選單＋缺欄提示、決策根測試**經 codex 實跑 mutation（`vals[i-k]→vals[i]`）確認會紅**（不再是假綠） |
| W3 兩家 sentinel | COMPOSER-R4-P3-00, GROK-R4-P3-00 | **採認**：0 新 findings；兩家判 B5 Gate 各命令 rc=0，可進 stamp（兩家自跑輸出逐條見附錄各家交件之 TESTS_RUN 欄） |

**主委自陳**：W1 是我第三次在 brief 的前提欄寫了未實測的宣稱（前兩次：plain_docs 綠、測試計數）。這次是 assumed 欄（已標請攻、委員也確實攻破），程序上正確，但根因同樣是「我從推理寫、沒跑一次」。相容性宣稱屬可實測項，日後一律先跑探針再寫。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01

**斷言**: brief 所稱「上傳檔即來源檔」可把同一檔同時放入 `file` 與 `source_file` 並通過 verify 不成立；事件檔含 `source_file_digest` 時，完整檔案位元組的 SHA-256 不可能自洽，該路徑仍拒收。

**碼證**: `api/routes/case.py:153-165` 將 `source_file` 完整 bytes 傳入 validator；`momentum/Analysis/event_samples/import_contract.py:108,182-184` 對完整 `source_bytes` 取 SHA-256 並逐列比 `source_file_digest`。實跑 `venv/bin/python -c '<EventImportService same file/file probe>'` → `same_file_status=reject kind=contract_violation reasons=['digest_mismatch']`；分開 companion 的 `venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"` → 3 passed rc0。RECHECK: 若保留 same-file 相容性，需改定不含內嵌 digest 的 canonical source bytes（或明確只接受 distinct companion）並新增 same-file 成功測試。

**來源摘要**: api/routes/case.py#c481747e887b；momentum/Analysis/event_samples/import_contract.py#58c331ca3d5d；tests/api/test_gap3_import.py#51774859bf14；handoffs/20260822-gap3-b5-review-r4-brief.md#00a885cee1ca

正文：[P1] 信心度=High。分開 companion 的 R3 修法可用，但目前說明把「同檔相容」與「companion 相容」混為一談；在修法或文件裁決前阻擋 stamp/UAT。
ASSUMPTIONS_VERIFIED: R3 四條己方 finding 與兩條他家 finding 均依實跑命令閉合；horizon 2 接線一致；same-file 假設被 service-level probe 反例推翻；scale receipt `n_events=10000`、`wall_clock_s`、`peak_rss_mb` 存在。
TESTS_RUN: `venv/bin/python -m pytest tests/api -q -k "gap3_import and (verify or companion)"`→3 passed；`venv/bin/python -m pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar`→1 passed；in-memory `vals[i-k]→vals[i]` mutation→target assertion failed；`npx vitest run gap3 pendingFeatures`→4 files/22 passed；`npm run build`→rc0；`venv/bin/python -m pytest tests/api/ -q -k gap3_import`→15 passed；`venv/bin/python -m pytest tests/momentum/event_samples/ -q`→230 passed；`bash scripts/plain_docs_sync_check.sh`→rc0。
FAILURES_SEEN: 初次 in-memory mutation harness 因雙 staticmethod 包裝 TypeError，修正 harness 後得到預期決策根斷言失敗；直接 TestClient probe 受 Binance DNS startup 影響，改用相同 service/validator 路徑完成反例；`restore_golden_inventory.sh` 因 sandbox 禁寫 `.git/index.lock` 未執行，既有 golden dirty 狀態未變。
SCOPE_CHANGES: none；未改產品碼、測試、data_cache、root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: review-only；未修改輸出；指出 verify provenance 語意與 same-file 路徑不一致。
HANDOFF_OUTPUT: handoffs/20260822-gap3-b5-review-r4-codex.md
HANDOFF_NOT_UPDATED: root HANDOFF.md 由 Claude 維護；本檔為本任務唯一產出。
STATUS: DONE
## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding——COMPOSER-R3-P2-01 重跑 CLOSED；他家 R3 修補 RECHECK 全綠且複核同意 CLOSED；R3 修補未引入可證偽 P0–P2 缺陷；brief 兩條 assumed（同源雙欄／companion 欄位集）攻擊不推翻。

**碼證**: `bash scripts/plain_docs_sync_check.sh` → rc=0；`pytest tests/api -q -k gap3_import` → **15 passed** rc=0；`pytest tests/api -q -k "gap3_import and (verify or companion)"` → **3 passed** rc=0；`pytest tests/momentum/event_samples/test_pipeline.py -q -k decision_bar` → **1 passed** rc=0；`pytest tests/momentum/event_samples/ -q` → **230 passed** rc=0；`cd frontend && npx vitest run gap3` → **18 passed** rc=0；`npx vitest run gap3 pendingFeatures` → **22 passed** rc=0。in-memory falsifiability：`wrong_vals[i]_assertions_would_pass=False`。修法落點：`case.py:142-165` source_file+verify；`eventExport.ts:60-121` horizon+companion；`page.tsx:526-548` confirm+雙下載；`test_pipeline.py:101-130` score 攔截斷言。

**來源摘要**: handoffs/reconcile/20260822-gap3-b5-review-r3/synth.md#eaec8254b879；handoffs/run_receipts/20260822T014000Z-gap3-b5-r3-fix-gate.log#3f37d9e7b733；scripts/plain_docs_sync_check.sh#1d127ae13f1a；frontend/src/lib/eventExport.ts#8966db1df2a1；frontend/src/app/search/page.tsx#04ac28eca77b；tests/api/test_gap3_import.py#fc12718ec299

正文：閉合輪義務＝原提出方重跑 COMPOSER-R3-P2-01 ＋複核他家 CLOSED ＋掃 R3 修補新問題；三項皆通過。禁捏造湊數。

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

