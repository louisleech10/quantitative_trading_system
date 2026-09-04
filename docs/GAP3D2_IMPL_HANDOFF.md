# GAP-3 `G3-D2` 灰色項目完成 — **實作交接**（2026-09-04，使用者已放行）

> **給實作 session 的交接。** `HANDOFF.md` 只放指標，細節在本檔。讀完本檔＋TODO 延伸檔即可開工，不必回頭問。
> 🔴 使用者 2026-09-04 原話等價：「看起來好像沒問題，可以放行實作」。實作者＝Claude 主委自任（ORCH §1 現行分工行）；code review＝codex＋composer＋grok 三家全員；實作者不自審。

---

## §0 一句話狀態

**SPEC 延伸 `docs/GAP3_EVENT_UX_SPEC.D-001.md` 與 TODO 延伸 `docs/GAP3_EVENT_UX_TODO.D-006.md` 皆 v2 三家戳記 FROZEN（2026-09-04）；實作從 B-D0 開始，五批串行 B-D0→B-D1→B-D3→B-D4→B-D5，每批三家 code review 至閉合才進下一批。**

| 文件 | 路徑 | 用途 |
|---|---|---|
| SPEC 延伸（語意權威） | `docs/GAP3_EVENT_UX_SPEC.D-001.md` | Phase D0／D1／D3／D4／D5；§A 已確認結果（v2 四裁定）；§G golden；§N 殘留；`## 戳記`（v1＋v2） |
| TODO 延伸（操作依據） | `docs/GAP3_EVENT_UX_TODO.D-006.md` | §0 全域規則；§B 批次表；每 Task 實作要點／修改檔案／驗證／邊界；`## 戳記` |
| 原檔（未被覆寫之條文原樣有效） | `docs/GAP3_EVENT_UX_SPEC.md`、`docs/GAP3_EVENT_UX_TODO.md` | Task 7.0b／7.1／7.2／7.3／7.6、§D-3′、§F、§G G-3 |
| 原 SPEC | `docs/GAP3_EVENT_SPEC.md` | D1-5 label 錨、D1-6 entry 映射、D2-2 決策時點單一表示法（**不動**） |
| 契約（單一真相源） | `momentum/Analysis/contracts/event_import_contract.json` | 本票所有新字面（見 D-001 D1.1「契約字面總表」） |
| 戳記 | `handoffs/reconcile/20260903-gap3d2v2-x-review-r2/synth.md`（本機）；鏡像於兩延伸檔 `## 戳記` | `bash scripts/reconcile_stamps_check.sh <synth>` PASS |
| 白話（給使用者） | `白話說明/G3-D2灰色項目說明.md` | 每批完成後更新「做到哪」 |
| 票 | `docs/IC_QUANT_GAP_REGISTRY.md` `G3-D2`；殘留 `G3-R7`（本票收回）、`G3-R9`、`G3-R12`、`G3-R13` | 收案時改 CLOSED |

🔴 **層級**：操作依據＝D-006；語意權威＝D-001（衝突以 D-001 為準並回報）；驗收字面之唯一來源＝D-001 各 Task「驗證」欄（D-006 只細化，不得弱化）。

---

## §1 五批與順序（D-006 §B）

| 批 | Task | 依賴 | 重點 |
|---|---|---|---|
| **B-D0** | D4.1（提前） | 無 | `EntryPriceRef` 側載＋進 `_receipt_hash` payload（六鍵 code fence 為唯一權威）；`open_to_*` 基準價取 entry bar 之 `field`；跳空 bar golden；三 mutation；既有 `close_to_close` 值逐位元組不變（hash 合法變一次，commit message 具名） |
| **B-D1** | D1.1–D1.7 | B-D0 | 契約字面（`label_origin`／`scenario_depth_inconsistent`／`entry_price_semantic.default`／`scenario.doc`）；`event_known_at_decision`；`SUPPORTED_MATRIX` 四對；golden loader＋`--check`；`/search` 解灰預測型與三元組值；detail 六鍵；**D1.7** IC 頁三 preset＋依深度預設＋當根 wire `horizon_bars=1`＋混 tf 不自動選＋送出守衛 |
| ~~B-D2~~ | — | — | ⛔ RETIRED（A 併入預測型） |
| **B-D3** | D3.1 | B-D1 | two_stage：兩段必填、`search_unlabeled` 未標籤路徑、深度≥1、去重 `all_with_uniqueness` |
| **B-D4** | D4.2、D4.3 | B-D0、B-D1；串行於 B-D3 後 | 13 對矩陣＋`rejected_pairs`／`pair_rejected` UI＋成對可行域與兩上界＋三層 oracle；k 參數化（seeds 去 k、雙值揭露）＋`event_label_scan` 網格（背景 task、`to_thread`、timeout、progress、partial；**benchmark 子步先於凍結 cap**） |
| **B-D5** | D5.1–D5.4 | B-D4、B-D0、B-D1 | `random_control_spec` typed nested schema（`required:false` 鍵級語義）、`label_rule`、規則身分閘四段、`/case/import-events/random-control`、`compare_random_control`（唯一 owner `ic_analysis_service`）、決定性 golden |

---

## §2 每批固定流程（不得跳步）

1. `bash scripts/agent_preflight.sh`；讀 D-006 該批全部 Task 與 D-001 對應段。
2. 實作（Claude 自任）：逐 Task 照「實作要點」；**每個新測試 mutation 自證**（改壞→紅，貼 rc）；不放寬既有斷言；`pytest` 指定選擇器綠；前端 `cd frontend && npx vitest run <檔>`（rc 直接取）。
3. golden：`venv/bin/python scripts/gap3_label_golden.py --check "tests/golden/gap3_label/*.json"` rc=0；跑完 `bash scripts/restore_golden_inventory.sh`。
4. 寫 review brief（`bash scripts/new_brief.sh review handoffs/<YYYYMMDD>-GAP3D2-B<n>-REVIEW-R1-BRIEF.md "…"`；依 `templates/BRIEF_REVIEW_TEMPLATE.md`：fact-verified 附命令輸出、assumed 附否證觀測且先跑、「我沒查的」表、必答成對、含固定必問「有無 ≥10× 不必要複雜」、停輪條件＝原提出方逐條 CLOSED）。
5. `bash scripts/gate.sh dispatch --intent … --risk low --template "n/a: 用 brief" --task-id <SESSION 大寫>` mint token → `bash scripts/committee_run.sh --session <YYYYMMDD>-gap3d2-b<n>-review-r<N> <brief> handoffs/<同名前綴> codex,composer,grok -- --intent … --risk low --facts-asked … --review-role … --template "n/a: 用 brief" --task-id <大寫>`（`run_in_background`）。
6. 收件：`bash scripts/reconcile_build.sh <session> --mode review <三檔>` → 手填群集／處置 → `reconcile_cluster_attribution_check.sh`／`completeness_check.sh --lock` → `debt_clear.sh --round-id … --session … --lock <sources.lock>`；修訂 → 閉合輪（原提出方確認 CLOSED）至無新 P0／P1。
7. `bash scripts/agent_postflight.sh` PASS → commit（`Governance-Scope:` trailer 於最末段；claim 閘：訊息不寫「全綠／passed」，收據放本檔 §5）→ `git push -q origin main`（背景）→ 更新本檔 §5、`HANDOFF.md`、白話 §六「做到哪」→ 下一批。
8. 派工進度每 10 分鐘回報一次；任何問題自己弄 ≤2 輪仍失敗 ⇒ 開委員會，禁 solo 硬幹。

---

## §3 已知地雷（本票期間實際踩過）

- **session 命名**：`<YYYYMMDD>-<epic>-<b<n>|x>-<kind>-r<N>`，kind ∈ {impl, review, stamp, consult, fix}；task-id＝session 大寫；違反 ⇒ 不發 token。
- **PreToolUse gate**：含 `committee_run`／`cx_run` 或以 `codex|cursor-agent|grok|agy` 開頭之 Bash 指令需 **fresh token（900s）**；債 OPEN 時 `gate.sh dispatch` 拒發 ⇒ 先銷帳或 abandon。**查看檔案的 Bash 指令開頭勿寫家族名**（`for f in codex …` 會被當 dispatch 擋）。
- **外部故障**：composer（`Cannot use this model: composer-2.5`／`read ETIMEDOUT`／`ECONNRESET`）、codex（chatgpt backend 404）、grok（API 500）整晚輪流出現 ⇒ `bash scripts/debt_clear.sh --abandon --round-id <id> --kind collection-failed --reason … --approver claude` → mint → `ROUND_ID=<id> bash scripts/cx_run.sh <family> <brief> <out>`（背景）。兩正式家族＝review quorum，但**戳記須三家**。
- 🔴 **codex 於 B-D0 三度未交件（2026-09-04）；根因未定，勿當已知**。
  **已排除之假說（皆有反證，不要再重查）**：
  ① 「全域 skill `~/.agents/skills/gstack/review/` 是新的／才開始劫持」——**否**：該檔 mtime 為 5/25–6/15，
     且 `20260903-gap3d2v2-x-review-r1`（命中 18 次）與 `20260903-gap3d2todo-x-review-r1`（17 次）
     **同樣載入它而正常交件**。
  ② 「撞 `hook: PreCompact` 所以卡死」——**否**：`todo-r3`／`todo-r4`／`v2-r1` 皆有 PreCompact 且交件。
  ③ 「輸出量太大」——**否**：`todo-r2` runlog 1.7MB > B-D0 之 941KB，且它交件。
  ④ 「外部 API 故障（401/403/429/500）」——**否**：那些字樣經 `grep -n -B2 -A2` 覆查全是 codex
     **grep 到的檔案內容**（`RECONCILE-STAMP` 行號、文件裡「Retryable: rate_limit/timeout」字面）。
  **已知事實**：codex 在 B-D0 確實跑完 mutation 腳本（runlog 有 `BASELINE rc=0`／`RESTORED rc=0`），
  只是never 寫產出檔；`collab: SpawnAgent` × 3 只在 R1 之**重派**那次出現。
  **唯一確定的差異（推測性解釋，未證明）**：D-001／D-006 各輪是**文件審查**；B-D0 是本 epic
  **第一次程式碼審查**——386 行 diff ＋ 10 條驗收命令，其中兩支 mutation 驅動各重跑 pytest 六七次
  （合計約 15 次 pytest）。工作量數倍於前。
  **副作用風險（與根因無關但真實）**：同一 skill 集之 `greptile-triage` 自述
  「not read-only，AUTO-FIX items are applied directly」⇒ 委員可能改碼；B-D0 實測 15/15 檔雜湊 OK。
  殘留代號 `B0-REVIEW-1`／`B0-REVIEW-2`。**下一批仍派三家**，若 codex 再度未交件，
  優先查「驗收命令的重量」而非 skill。
- 🔴 **派工期間須守檔**：委員會跑本批的 mutation 腳本（就地改生產碼再還原）。收件前後一律
  `shasum -a 256 -c <baseline>` 全檔比對。**建 baseline 時勿用 `| tee x | head -3`**——SIGPIPE 會把
  baseline 截斷（B-D0 踩過，4 行當成 10 行用）。
- 🔴 **mutation 腳本之還原權威＝版控，不得用自存備份**（2026-09-04 B-D1 事故）：
  舊版把備份寫成 `handoffs/_b1_bak_*` 且只在**第一次**建立。之後又 commit 了 D1.6，
  備份仍停在 D1.6 之前 ⇒ 委員跑腳本時 `restore()` 用**過期備份**覆蓋現檔，把 D1.6 整段回捲，
  而腳本自己印 `restored`、沒有任何東西會紅。
  **治法**：`git checkout -- <檔>` 還原 ＋ 啟動時檢查「目標檔與 HEAD 一致」，不乾淨即 rc=3 拒跑
  （否則還原會吃掉未提交改動）。現行 `20260904-gap3d2-b1-mutate{,2}.py` 已是此形。
  **診斷提示**：工作區突然出現「把某個 commit 的改動整段刪掉」的 diff，先看
  `ls -l handoffs/_*bak*` 的時間戳 vs 該 commit 時間，別急著怪委員。
- 🔴 **清理／還原動作不得早於前置檢查**（2026-09-04 同日**第二次**事故，比第一次嚴重）：
  改用 `git checkout --` 之後，外層 shell 腳本仍在**迴圈開頭無條件 `restore()`**
  ⇒ 順序變成「先還原（未提交的修正沒了）→ 再檢查乾淨（此時當然乾淨）→ 通過」，
  一次沖掉依 review 剛做完、尚未 commit 的**四個檔**之修正。**檢查沒錯，錯在它在清理之後。**
  **治法**：開場檢查一次，不乾淨即 `exit 3` 拒跑；迴圈內之 restore 只在「本腳本剛套過 mutation」之後。
  **流程上的推論**：閉合輪之修正**先 commit 再跑 mutation**，不要留在工作區。
- **`reconcile_cluster_attribution_check.sh`** 對前輪 ID（正文提及、非附錄 heading）誤報「未被引用」＝假警。
- **completeness**：`## DEGRADE-<FAMILY>-<NN>` 一行一 ID，勿合寫兩家。
- **commit**：staged 含 `.claude/gate/*.log`／`docs/site/*.html`／交接檔 ⇒ pre-commit G-7 要求 `Governance-Scope: out-of-epic …` 為最末段；`handoffs/` 為 gitignore（委員產物只在本機）；白話新檔須登記 `scripts/plain_docs_sync_check.sh::_watched_for`。
- **測試**：`tests/api` 既有紅（`G3-R11`）；`test_ic_deep_analysis` 與其他並行 ERROR、單跑綠；`tsc --noEmit` 8 行既有債；全套 `pytest tests/governance` 十分鐘級一律背景。
- **資料**：golden 一律真實 `data_cache/feature_klines/kline_cache.h5`（`tests.momentum.event_samples.helpers.load_bars`）；跳空 bar：ETHUSDT 12h 有 828/1696 根 `open != prev_close`，測試先斷言不等式；`data_cache/events/` 9/1 之 9 批＝使用者確認之測試檔，不保留不遷移。
- **探針**：`handoffs/20260903-gap3d2-probe-triplets.py`（本機）示範四三元組之窗與 `_close_at` 別名。

---

## §4 使用者裁定總表（不得偏離）

| 來源 | 裁定 |
|---|---|
| kickoff §5（9/3 凌晨） | ①不含全部 K 線驗證 ②k 不由使用者填 ③反例種類不必標（第二期）④標籤基準（已被 v2 ② 改為三選項之一）⑤B→A→two_stage（已因 A 併入作廢） |
| consult 共識（離線）甲乙丙 | 甲 C 只改揭露＋`G3-R13`；乙 契約 k 欄保留必填恆 0；丙 k 軟上限 10（判斷值） |
| v2 四裁定（9/3 白話閘） | ①A 併入預測型 ②IC 三種報酬選項依深度預設、D4.1 提前 D0 ③k／h 掃描網格 ④k 註記 |
| 9/4 | 放行實作 |

---

## §5 收據（每批完成後填）

| 批 | commit | 測試選擇器／rc | golden `--check` | review sessions | 狀態 |
|---|---|---|---|---|---|
| B-D0 | `49204458`（2026-09-04；訊息具名「hash 合法改變一次、label_values 逐位元組不變」） | `pytest tests/momentum/event_samples/ -q -k "open_to or entry_price_ref"` **21 passed rc=0**；`pytest tests/momentum/event_samples/ -q` **365 passed rc=0**；`pytest tests/api -q -k "event_analysis or event_batch_detail_dims"` **32 passed rc=0** | `--check "tests/golden/gap3_label/*.json"` **rc=0（9 cases PASS）** | `20260904-gap3d2-b0-review-r1`（composer＋grok 交件，皆 P3-00 零 finding）；`…-r2`（codex 單家重派，未交件，見殘留） | **DONE**（review quorum＝兩家；殘留 `B0-REVIEW-1/2` 待使用者裁定 codex 環境） |
| B-D1 | 實作 `6352b6d6..cb22f725`（5 commit）＋R2 閉合 `5adbe126`＋文件 `7eae878f` | `pytest tests/momentum/event_samples/ -q` **407 passed rc=0**；`pytest tests/api -q -k "ic_event_label_defaults or event_batch_detail_dims or horizon_purge or contract_reason_registry"` **69 passed rc=0**；前端 `npx vitest run` **69 檔 433 passed**；`npx tsc --noEmit` **8 行（既有債，無新增）**；`check_decoupling_imports.py --baseline` **BASELINE OK 無新增違反** | `--check "tests/golden/gap3_label/*.json"` **rc=0（23 cases）** | `20260904-gap3d2-b1-review-r2`（**三家全數交件**：codex 4／composer 4／grok 3 findings；verdict 不一致，取聯集全修） | **待 R3 閉合輪**（原提出方複核）。mutation 兩批 **15 種全紅、還原全綠** |
| B-D3 | — | — | — | — | — |
| B-D4 | — | — | — | — | — |
| B-D5 | — | — | — | — | — |
