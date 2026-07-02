# 治理批次：委員會過程檔 prose 豁免（O3-extension）+ R7-emitter 全 task-id 觸發 — SPEC

> 來源 PLAN/診斷：HANDOFF「verify-gate 待修項」+ `handoffs/20260702-FF-P1-57-RECONCILE.md` R7 尾節　|　日期：2026-07-03　|　對應 TODO：docs/GOV_O3EXT_R7_TODO.md（待生成）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：**中**（兩個治理 script 模組 + governance 測試；不碰 momentum/api production 數值路徑）。
- **命中高風險原則**：不命中 (a)(d)（無數值/ML 影響）；治理基礎設施屬敏感共用路徑（gate.sh/checker/stamps_check 是驗收制度本身），**比照 (b) 嚴管**：完整管線 + adversarial（紅隊 R1-R7 前例：治理漏洞=制度性風險）。
- 命中 (a) 或 (d) → 否；§G 移 §N。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（共 5 項，皆實讀 scripts/*.sh、*.py 行號或實測 commit 輸出）：
  1. 既有 O3 豁免僅內容級（fenced/blockquote/inline-code/引號內範例），無檔案類豁免——`scripts/verification_claim_check.py:369-370` 實讀。
  2. `_append_committee_dispatch` 只在「risk high 且 `--adversarial` 為實檔」分支被呼叫——`scripts/gate.sh:52-57,105` 實讀；stamp-review 派工（risk low、`--template n/a:`）不觸發 → 其授權的 RECONCILE-STAMP 無 provenance（p1ff57-stamp-v2 實例：reconcile_stamps_check 對其 provenance FAIL 只能 waived）。
  3. `reconcile_stamps_check.sh` 驗戳記=「`sha256:<body_hash>` 相符 + task:<id> 有 committee_dispatch 審計（2026-07-01 前 grandfather）」——`scripts/reconcile_stamps_check.sh:39-71` 實讀。
  4. 現有 8 份委員會過程檔被 checker 擋 commit（2026-07-03 commit 實測：REVIEW-composer.md 觸發「operational claim 缺少 VERIFY/REF/SIGNOFF backing」）：ALIGN-ORACLE-{FACTS,DESIGN-CODEX}、DSTAR-GATE-{CLAUDE,CODEX}、ALIGN-PROBE-FIX-PROMPT、PROBE-FIX2-composer、P1-57-IMPL-codex、P1-57-REVIEW-composer。
  5. 紅隊 R2（docs 走私）已修：任意豁免通道會復辟 R2——`tests/governance/test_verify_gate_redteam.py` 有既有反例測試。
- **待使用者確認**：無（技術設計委派委員會——使用者 2026-06 定；本批兩項皆使用者已認可的待修項）。
- **已確認結果**：使用者 2026-07-02 認可「趁 P1 空檔處理待修小項」；2026-07-03 詢問進度=確認要做。

## §C 約束（不重抄，引用 + 只列本任務相關）
- **反 R2 復辟紅線**：任何檔案類豁免必須「機器可驗的 provenance 綁定」（audit 事件 + 內容 hash），**禁止**純路徑 glob 豁免（`handoffs/*` 全開=走私通道）。
- **審計不可變**：不得為過閘改委員會親筆檔原文（=竄改 audit trail）；audit.log append-only，不得刪改既有事件。
- 共用路徑：`scripts/gate.sh`（所有派工入口）、`scripts/verification_claim_check.py`（pre-commit/PreToolUse/CI 三處消費）、`scripts/reconcile_stamps_check.sh`（SPEC 派工 gate 消費）。改動後三個消費端都要回歸。
- HANDOFF.md / commit-msg / docs/* 的 claim 檢查**強度不變**（豁免只及委員會過程檔本身）。

## §G Golden / Baseline
- N/A → 見 §N。

## §P Phase 與依賴

### Phase 1 — R7-emitter 全 task-id 觸發（依賴：無）
**Task 1.1 — gate.sh emitter 擴觸發**
- 目標：任何帶 `--task-id` 的 dispatch（不分 risk/有無 adversarial）都發 `committee_dispatch` 審計事件。
- 檔案：`scripts/gate.sh`（dispatch 分支；`_append_committee_dispatch` 泛化為可記任意 output 檔）。
- 改法：新增可選 `--output <path>` 參數（委員產出檔預告；**stamp-review 派工必帶**，見 Task 1.2）；`--task-id` 存在即 emit 事件，欄位沿用既有 schema（dispatch_ts/task_id/**output_path**/family/output_sha256——欄位名與現行 gate.sh:84/verify_task_provenance.py:109 一致，**禁用 out_rel 新名**；檔案未存在時 output_sha256 記 `pending`）。事件行一律經 `"${VENV_PY}" -c 'import json; print(json.dumps({...}))'` 產生（**防 JSON 注入**：task_id/path 含引號/換行/unicode 仍為單行合法 JSON）。新增補記入口 `gate.sh register-output <task-id> <path>`：**必須存在同 task_id 的先行 committee_dispatch 事件，否則 exit 1**（防無派工自造豁免鏈）；hash=**raw file bytes 的 sha256**（與 gate.sh:79-81 現行為一致；**禁用 reconcile_body_hash.sh**——委員會過程檔無戳記節會 ERROR，兩種 hash 語義不可混用）。
- 驗證（可證偽）：`pytest tests/governance/test_verify_gate_r7ext.py -q` 全綠——risk low 無 adversarial 帶 `--task-id` 派工 → audit log grep 到 `committee_dispatch` 事件且欄位齊（task_id/output_path/output_sha256）；不帶 `--task-id` → grep 計數==0（不汙染）。
- 邊界（≥2）：①`--output` 指到不存在檔 → 事件記 pending 不失敗；②同 task-id 重複 register-output → append 新事件不覆蓋舊事件（audit append-only）；③register-output 無先行 dispatch → exit 1；④task_id 含 `"`/`\n` → 事件仍單行合法 JSON（fuzz 測試）。
- 不可做：不改 W3 fail-closed 分支語義；不放寬既有 adversarial provenance 檢查；不用 printf 裸拼 JSON。

**Task 1.2 — reconcile_stamps_check 消費新事件**
- 目標：stamp-review 派工授權的戳記可經 committee_dispatch（Task 1.1 產生）通過 provenance 檢查，去除 waived 常態。
- 檔案：`scripts/reconcile_stamps_check.sh`。
- 改法：W2 檢查除既有路徑外，接受「task:<id> 對應 committee_dispatch 事件且其 output_path==被戳記檔 或 register-output 記錄的 sha256 與戳記 sha256 一致」。**閉合 p1ff57 根因的完整鏈**：stamp-review 派工帶 `--output <reconcile路徑>`（Task 1.1）→ 委員審完 → `register-output`（hash 非 pending）→ 戳記 → stamps_check PASS。
- 驗證（可證偽）：`pytest tests/governance/test_verify_gate_r7ext.py -q`——**用 RECONCILE 檔 fixture 走全鏈**（dispatch --output → register-output → 戳記）→ `reconcile_stamps_check.sh` exit 0 且輸出含 `PASS` 無 `waived`；偽 task-id（audit 無事件）→ exit 1；dispatch 有但 output_sha256=pending 且無 register-output → exit 1。
- 邊界：①grandfather 日期前舊戳記行為不變；②audit log 缺失/不可讀 → fail-closed（FAIL 非 PASS）。
- 不可做：不移除 body_hash 相符檢查。

### Phase 2 — O3-extension 委員會過程檔 prose 豁免（依賴：Phase 1 事件基礎）
**Task 2.1 — checker 檔案類豁免（provenance 綁定）**
- 目標：`handoffs/` 下有對應 committee_dispatch/committee_output 審計事件、且**當下內容 sha256 與事件記錄相符**的檔案，其 prose operational claim 免 VERIFY/REF backing；hash 不符（事後改動）→ 豁免失效照常擋。
- 檔案：`scripts/verification_claim_check.py`（`_detect_source_context` / 豁免判定新函式）。
- 改法：讀**委員會審計 log**（`.claude/gate/audit.log`，經 `VERIFY_GATE_COMMITTEE_AUDIT_LOG` 環境覆蓋——沿 verify_task_provenance.py:19 慣例；**禁止**复用 `_audit_log_path()`——那是 verify_audit.log/receipt 審計，是**不同的 log**，混讀=豁免必失效或假綠）建 {output_path→sha256 集合}；unit 的 source_file 正規化後命中且 `sha256(檔案 raw bytes)∈集合` → 該檔 claim 降為豁免。HANDOFF/commit-msg/docs/* 路徑**不進**此豁免。
- 驗證（可證偽）：`pytest tests/governance/test_verify_gate_o3ext.py -q`——①已註冊+sha256 相符檔 → checker exit 0；②同檔改一字（sha256 不符）→ exit 1；③把同樣 prose 放 HANDOFF.md → exit 1（`pytest tests/governance/test_verify_gate_redteam.py -q` R2 反例回歸全綠）。
- 邊界：①committee audit log 無事件（含「事件只在 verify_audit.log 那類錯 log」情境）→ 不豁免；②欄位缺失/JSON 壞行 → 該行跳過且不豁免（fail-closed）；③hash=raw bytes sha256，與 register-output 同一演算法（無額外正規化——CRLF 改動=內容改動=豁免失效，此為特性非 bug）。
- 不可做：不豁免 docs/*；不引入路徑 glob 白名單；不動既有內容級 O3 邏輯。

**Task 2.2 — legacy 8 檔一次性註冊 + 補 commit**
- 目標：8 份既有委員會過程檔（§A.4 清單）註冊後補 commit。task-id 可稽者用原 id 走 `register-output`；不可稽者走**一次性 legacy 腳本**（8 檔白名單+sha256 寫死於腳本內、人工稽核、白名單耗盡即拒絕）；`register-output` 主命令**拒絕 `legacy-*` task-id**（legacy 通道不成為常態後門）。
- 檔案：無新碼；操作步驟寫入 TODO；commit 由編排端執行。
- 驗證（可證偽）：8 檔 staged 後 `python scripts/verification_claim_check.py --files <8檔>` exit 0；隨改任一檔一字重跑 → exit 1 且報該檔。
- 邊界：register-output 對不存在檔 → 拒絕；對 handoffs/ 外路徑 → 拒絕。
- 不可做：不為過閘修改 8 檔原文。

### Phase 3 — 回歸與文件（依賴：Phase 1+2）
**Task 3.1** — governance 全套回歸（含紅隊 R1-R7 反例）+ `docs/MULTI_AGENT_ORCHESTRATION.md` Gate 節與 `docs/VERIFY_GATE_SPEC.md` 增補說明。
- 驗證（可證偽）：`pytest tests/governance/ -q` 全綠（基線 106 passed 只增不減）；`git diff tests/governance/` 顯示既有斷言零放寬。
- 邊界（≥2）：①`VERIFY_GATE_O3_FILECLASS=0` 時全部豁免失效、行為==現狀；②audit log 為空檔時 checker 對 8 檔照常 FAIL。
- 不可做：不改既有紅隊反例測試的預期方向。

## §V 驗證策略與邊界測試目錄
- 層級：governance 單元+整合（`pytest tests/governance/ -q`，不需 run_api.py）；每 Task 驗證欄=可證偽反例（改壞→FAIL 實跑證明）。
- **防假綠**：diff 既有 governance 測試斷言，不得放寬；紅隊 R2/R3/R6 既有反例測試必須維持綠（豁免不得使其轉綠方向改變）。**新測試檔 test_verify_gate_{r7ext,o3ext}.py 目前不存在——為 B1/B2 各自第一個子任務，Phase Gate 命令須 assert collected>0 防「0 tests collected 假綠」。**
- **新增紅隊反例（必須全紅）**：①無先行 dispatch 直接 `register-output` 走私檔 → exit 1（F3 攻擊腳本收錄為測試）；②task_id 含 `"`/`\n` fuzz → 事件仍合法 JSON 且 provenance 可查（F4）；③committee 事件只寫錯 log（verify_audit.log）→ checker 不豁免（F1）。
- 邊界目錄：audit log 缺失/損壞/錯 log、hash 不符、重複註冊、handoffs/ 外路徑、JSON 注入 fuzz（各對應 Task 邊界欄）。

## §R 回退
- Phase 1/2 獨立 commit 可單獨 revert；checker 豁免加環境開關 `VERIFY_GATE_O3_FILECLASS=0` 可一鍵停用（預設 on——本功能本身是解鎖非上鎖，停用=回現狀更嚴）；audit 事件 append-only 無需回退。

## §N N/A 登記
- **§G：N/A** — 本批不碰數值/特徵/ML 路徑，無 baseline 可凍結；正確性由 governance 可證偽反例測試承擔（§V）。
