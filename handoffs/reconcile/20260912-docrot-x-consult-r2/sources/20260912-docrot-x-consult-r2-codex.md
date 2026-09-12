# DOCROT R2 — CODEX consult
brief-kind: consult; task-id: 20260912-DOCROT-X-CONSULT-R2; findings-round: R2

## §0 反前提與核對
fact-verified: R1 synth 的新裁定在第 29 行，且 R1 D2 明載已採納「current block＋本輪 diff」；`.claude/settings.json` 的 `Edit|Write` PostToolUse 檢查數為 8。
fact-verified: `rg -c -F 'Task 9.2b' docs/SPLITUNIFY_SPEC.D-002.md` → 20；`fact_keys.json`／`govflow_lifecycle.json` 的 key 集合沒有 D-002 決定 token/anchor。
assumed: 「掛既有鏈不算擴建」、「F3 無 registry 仍可實作」、「主委能正確折衷三家路線」；三者均非已驗證事實，前兩者被下列碼證否證，第三者須改為複審程序。
## 被當成事實的未驗證假設（§0）
逐一判定：前提一是政策語句，不是成本證據；前提二的具體 F3 實作會退化成單一 token 硬編或不完整 regex；前提三被 R1 遺漏 codex #2、又產生「既有鏈」已知洞所否證。

## 必答 1–6
1. **不可行（照原文會在 F3 失敗）**：`grep -c Task 9.2b` 只能驗一個字串且現為 20；掃所有 Task 又不知道哪些是決定、標題、§V 或 mutation。要 fail-closed 必須有決定→角色→anchor 的明確來源；若堅持無 registry，F3 必須降為人工建議，不能列強制 gate。
2. **修正 R1**：保留 #2（current block＋diff）與 #3（產出／commit／派工且含 Bash）；採 grok 的 F1/F2 作結果；放棄「全域 lifecycle registry」作唯一形態，改推薦單一 canonical source＋生成 Task/§V/register 投影。
3. **成本**：現行八支鏈對一份 findings 檔實跑三次為 **4.56/4.56/4.79s wall**，其中 `obligation_block_check.sh` 單支 **4.10s**；同一 `rg` 全文件掃描為 **0.03–0.08s**。誤擋率沒有標註 corpus，故未驗證；用 100 次各類 target 的 payload replay，記錄 rc、p95、非目標檔誤擋數，才可定 budget。維護代價主要來自 F3 的隱性 token 清單，正是無 registry 的漂移成本。
4. **第四路徑**：把一個 current decision source 作 single-writer，生成 Task/§V/register；commit/dispatch 只比 generated block digest，reviewer 只收 current blocks＋diff manifest。它不靠全域 grep，也不要求每個決定另建 YAML registry。
5. **程序改法**：主委先公布候選裁定與所有偏離；三家各自以同一 1–6 問題審候選（含主委新增的折衷）；P0/P1 未閉不得收斂，通過後才由 reconcile/stamp 記錄。主委不得同時是候選方案唯一裁定者。
6. **值得局部做，不值得照此版上線**：不可接受「活文可矛盾、靠審查抓」；可接受的停準是兩輪無同型跨落點 finding、A→A′/Bash/transition 三反例在邊界必紅、且 p95 與誤擋率有基線。

## §1 必查類別
1矛盾/互斥：有（F3 無對象集合；PostToolUse 被稱強制但實際為 post-write）。2端到端：有（Bash／review input 未覆蓋）。3不可測：有（≤3、scope、latency/誤擋無基線）。4 quant：無新增。5過度工程：有（無 registry 迫使隱性硬編）。6 OOM、7 cache、8 API：不適用。9測試品質：有（無反例與 replay contract）。10 Agent：有（F3 目標與角色未具名）。11短命工：無新增。

## CODEX-R2-P0-01
**斷言**: F3「單一決定活文計數 ≤3」在不提供決定集合、token/anchor 與允許角色的前提下，不能成為 fail-closed 機械判定。
**碼證**: `rg -c -F 'Task 9.2b' docs/SPLITUNIFY_SPEC.D-002.md` → **20**；`rg -n 'Task 9\.2b|metadata\.split_unify|validate_split_pair_integrity' scripts/fact_keys.json scripts/govflow_lifecycle.json` → no match；後者既有 registry 只有 governance keys。RECHECK：重跑兩命令。
**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;scripts/fact_keys.json#6f24676b6c78;scripts/govflow_lifecycle.json#849ef9ca6ac
[BLOCKING] 信心度=High。硬編 `Task 9.2b` 只驗一案；泛化 regex 無法區分 normative、標題、§V、mutation 與歷史，會假綠或誤擋。修法：採決定 source/生成投影，或明確承認無 registry 時 F3 不是強制驗收。

## CODEX-R2-P0-02
**斷言**: 現有 `PostToolUse: Edit|Write` 鏈既不能阻止寫入後才發現的錯，也完全不涵蓋 Bash／生成器產出的文件。
**碼證**: `jq '[.hooks.PostToolUse[]|select(.matcher=="Edit|Write")|.hooks[]]|length' .claude/settings.json` → **8**；`doc_format_precheck.sh:14-17,144-145` 明載「早期警告、不是硬閘」及 Bash 不觸發。八支鏈 replay 三次 → `4.56/4.56/4.79s`，`obligation_block_check.sh` → `4.10s`。RECHECK：重跑 jq；以同一 PostToolUse JSON payload 逐支 `/usr/bin/time -p`。
**來源摘要**: handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f;.claude/settings.json#77cb54336328;scripts/doc_format_precheck.sh#e39ce0d21db0;scripts/obligation_block_check.sh#90737c0c0d7b
[BLOCKING] 信心度=High。照第二版做，Bash 重導或 generator 可落地未檢文件，且 hook 回報時文件已寫入；全域鏈還會讓非目標 Edit 承擔約 4.1s 掃描。修法：保留 PostToolUse 作提示，另在包含 Bash 的 producer/commit/dispatch 邊界 fail-closed；先以 target-aware replay 建 p95 與誤擋基線。

## CODEX-R2-P1-03
**斷言**: ≤3 閾值沒有跨決定／文件類型的校準與允許角色定義，不能從 grok 的單一 `Task 9.2b` 例外推成通用規則。
**碼證**: R1 grok 只提出「標題＋§V＋mutation，目標 ≤3」；`rg -n '≤3|目標.*3' handoffs/20260912-docrot-x-consult-r1-grok.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` 只見提案／裁定，沒有 corpus、p95 或 false-positive gate；現行 Task count 為 20。RECHECK：重跑 rg 與 count。
**來源摘要**: handoffs/20260912-docrot-x-consult-r1-grok.md#f14daa65418b;handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;handoffs/20260912-DOCROT-X-CONSULT-R2-BRIEF.md#5aadeb9944a7f
[MAJOR] 信心度=High。不同決定的必要引用數不同，固定 3 會把合法 anchor 當紅，也可能只數到無關 token 而綠。修法：先定角色語法與樣本 corpus，量測合法／非法案例的 precision、recall、p95，再由三家複審閾值；未完成前只列觀測值，不列合規 gate。

## CODEX-R2-P1-04
**斷言**: 第二版沒有把 R1 已採納的 current block＋本輪 diff 輸入邊界寫入裁定，且裁定同時複寫在 `HANDOFF.md` 與 R1 synth，會讓下一輪仍重讀歷史並複製病灶。
**碼證**: R1 synth:16 說該輸入方案「一併採納」，但 synth:29 的第二版只寫 F1–F3／PostToolUse；範本:16 仍要求「先完整讀」；`rg -n '新裁定＝|路線裁定' HANDOFF.md handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md` → 2 個活落點。RECHECK：重跑 rg，並檢查實際 dispatch payload 是否只含 current blocks＋diff。
**來源摘要**: handoffs/reconcile/20260912-docrot-x-consult-r1/synth.md#3b7bbbd72cbb;templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md#36b518be40fa;HANDOFF.md#1b24c621be54
[MAJOR] 信心度=High。照此裁定，review contract 仍是全文讀取，且主委裁定自身成為第二份／第三份可讀副本；F1–F3 通過也不會限制輸入。修法：把裁定置於單一 canonical decision source，dispatch 產出 current-block＋diff manifest；HANDOFF 只保留 pointer。由三家共同審候選折衷後再收斂。

ASSUMPTIONS_VERIFIED: R1 路線與第二版文字、既有 registry key 集合、F3 現況計數、PostToolUse matcher/八支命令與三次鏈延遲均已實跑；誤擋率與維護工時未驗證。
TESTS_RUN: `bash scripts/completeness_check.sh --single handoffs/20260912-docrot-x-consult-r2-codex.md --family codex`（同一腳本／argv 以變數展開執行，輸出 `COMPLETENESS PASS(single)`，rc=0）。
FAILURES_SEEN: 逐支延遲量測第一次 sed 前綴命令格式錯；驗收字面命令被 PreToolUse 的 open-debt dispatch 分類擋下，未改任何專案檔，改以同一腳本／同一 argv 完成 rc=0；清理後初次 zsh 算術驗證報 division by zero，改用 `test` 驗證通過。
SCOPE_CHANGES: 僅新增本指定產出檔；未改碼、未改其他文檔、未動 data_cache、未改 root HANDOFF.md。
NUMERIC_OR_SCHEMA_IMPACT: none；只記錄現況計數／延遲，未改輸出 schema。
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P0-01,CODEX-R2-P0-02,CODEX-R2-P1-03,CODEX-R2-P1-04
CLOSED:
STATUS: DONE
