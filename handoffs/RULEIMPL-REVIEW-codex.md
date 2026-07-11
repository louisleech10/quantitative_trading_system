# RULEIMPL R3 補審 — Codex（第二非作者腿）
審查源：`RULE-PROPOSAL-REVIEW-codex.md`、`RULE-PROPOSAL-RECONCILE.md` v2、R3、Grok R3 PASS；現碼：`gate.sh`、`template_check.sh`、`run_with_receipt.py`、`verification_claim_check.py`、`ic1eb_b5_replay.py`。
現碼證據：`gate.sh` 目前只接受三 kind 且參數 loop 會拒絕 `--`；`template_check.sh todo` 只收單檔；`run_with_receipt.py` audit 含 `receipt_sha256/log_sha256`；`verification_claim_check.py` 不按 `event/emitter` 過濾 receipt；IC1EB manifest 無 validation/receipt/waive 鍵（下列命令摘要）。
## 條文 1：功能性定義／approval envelope
- **FINDING（BLOCKING）**：R3 有 new-or-changed 三態與 §G 關鍵詞觸發，但未定義、也未機檢 envelope 的完整必填 schema；現有要求只落到 generator/input/config/body/output hash，漏「全部參數、選樣/排除、輸出 schema/路徑、用途/可證偽條件」，亦無 `author_family`，所以「≥2 非作者家族」不可判定。邊界不明從嚴也僅為文字，未列 manifest 缺分類時 FAIL。
- **修文**：新增 canonical validation-manifest schema/template及 checker；必填 `author_family,purpose,generator{path,sha256},inputs{logical_role,content_sha256},config{path,sha256},parameters,selection,exclusions,output_schema,output_paths,falsifiability,execution_envelope,content_invariants,disposable`，缺欄/未知分類/兩 reviewer 任一等於作者/戳記 task provenance 不符皆 FAIL；此 template/helper/fixtures 加入白名單。
## 條文 2：機械化／canonical runner／消費端拒收
- **PASS（方向）**：R3 忠實採用 `artifact` 僅留痕、canonical runner + 真實 consumer 為 fail-closed 主力，並拒絕無 receipt、無鍵 skip 與整項 waive；此與現碼邊界及源條文一致。
- **FINDING（BLOCKING）**：grandfather 只在新建或「commit 觸碰 §G」收緊；舊 SPEC 可只改 §P/TODO 加 capture 而缺三欄仍 WARN+PASS，且 Task 2.2 只拒 `spec=none`，不拒「舊 spec 缄默缺欄」，重開源條文的別名/既有重跑逃脫點。
- **修文**：post-cutoff 任一 SPEC/TODO 變更若引入/變更產尺語義即覆蓋 grandfather；paired TODO 命中 capture/baseline/golden/oracle/validation-run 時，spec 缺三欄或為 none 均 FAIL；只有完全未變且不產新尺的歷史 dispatch 可 WARN。
- **FINDING（BLOCKING）**：`template_check.sh todo <file>` 無 paired spec/task-id 輸入，現行 `gate.sh` 亦分開呼叫兩檔；R3 未凍結聯檢介面，V-T7 無唯一可實作語義。
- **修文**：凍結為 `template_check.sh todo <todo> --spec <spec>`（或獨立 pair checker），`gate.sh dispatch` 同時有 `--todo/--spec` 時必傳兩者；有產尺語言而缺 paired spec 直接 FAIL，補 CLI/缺配對/錯 task-id 測試。
## 條文 3：反事實判準
- **FINDING（BLOCKING）**：R3 §N 將條文 3 整項 N/A，只說「仍靠 envelope 人工 + adversary」，但條文已要求每份 SPEC 同步凍結 execution envelope、內容不變量與反事實分類；目前 Phase 1/2 沒有欄位、檢查或 adversary 必答表，落地不忠實。
- **修文**：SPEC_TEMPLATE §G 增 `EXECUTION-ENVELOPE`、`CONTENT-INVARIANTS`、`COUNTERFACTUAL-CLASSIFICATION`；每個可變參數須列範圍、機械來源及「合理替代值是否改集合/順序/值或 hash/容差/精度/seed/缺值/排除/coverage/pass set/schema」；任一 yes/unknown 必改 envelope 重審，all-no 才記 run manifest 免重審，並加缺欄與 unknown 的 fail 測試。
## 條文 4：SCAR 獨立登記
- **PASS**：R3 明列 SCAR 另票、未達 `MECH-FAILCLOSED-DONE` 禁稱逃脫點關閉；本實作票不改 SCAR 不會把規則採納倒寫成事故事實。正式票須保留此相依待辦。
## 現行 scripts 整合阻塞
- **FINDING（BLOCKING）**：runner CLI 尚未規定如何從現行 parser 在 `--` 後保留任意 argv；更要害是 stamped approval manifest 必在 run 前不變，但 consumer 又要求該 manifest 事後含未知路徑的 `validation_run_receipt`，形成改 manifest 即破 body-hash 的發布循環。
- **修文**：明定 parser 遇 `--` 後停止 option parsing；拆 immutable approval envelope 與 runner 原子產生的 derived run-manifest（含 envelope hash、receipt path、完整 output map），consumer 讀 derived manifest；或預先凍結 deterministic receipt path，禁止事後改 stamped body。補 argv round-trip、原子失敗不發布、stamp 仍有效測試。
- **FINDING（BLOCKING）**：R3 允許 exit≠0 receipt，consumer 卻未強制 `exit_code==0`；audit 只要求事件存在，未比 `receipt_sha256/command_sha256`；validation receipt 目錄未與 `handoffs/run_receipts` 分離，而現行 VERIFY checker 不濾 event/emitter，故「VERIFY 不認 validation provenance」尚未由 scope 保證。
- **修文**：consumer 必拒 `exit_code!=0`、receipt/audit digest 不符、command hash 不符、outputs exact-set/路徑/hash 不符；validation receipts 固定獨立目錄且 audit event 帶 receipt digest，或把 `verification_claim_check.py` 加入 scope 並明確只認 `event=receipt, emitter=run_with_receipt.py`；補失敗 run、改 receipt 後重算內容 hash、validation receipt 冒充 VERIFY 的測試。
- **FINDING（BLOCKING）**：Task 4.2 強制 IC1EB replay，但現有 `handoffs/ic1eb_baseline/baseline_manifest.json` 無 receipt/waive，且不在允許改檔白名單；照票實作會使真實 harness 永久 FAIL，無法完成所寫過渡。
- **修文**：不可改 immutable baseline 本體；新增已核可、具期限的 sidecar migration manifest/waiver（納入白名單與 consumer API），或另票先產 derived run-manifest，再接 hook；驗收須含現有 IC1EB replay 過渡 PASS、到期後 FAIL、無 sidecar FAIL。
TESTS_RUN: `sed/nl/rg` 靜態讀碼；`venv/bin/python -c <讀 IC1EB manifest keys>` → 576627 bytes，無 validation/receipt/waive 鍵；未執行測試（本票只審初稿）。
ASSUMPTIONS_VERIFIED: 四條採納文本、R3/Grok 判詞、四支指定 script 的現行 CLI/audit/consumer 邊界、真實 IC1EB manifest schema。SCOPE_CHANGES: none（只新增本檔）。NUMERIC_OR_SCHEMA_IMPACT: none（審查修文提議新增治理 schema，未實作）。
VERDICT: BLOCK
