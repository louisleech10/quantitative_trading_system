# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任（Fable/Opus）；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 **B2 code review 三家已回報（21 條），待收斂→修→戳記→B3**

**文件三件套**：TODO **FROZEN R3**（`docs/GAP1_STRATEGY_OVERFIT_TODO.md`）＋延伸檔 **A1-1..A1-20**
（`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`，**衝突以延伸檔為準**）＋母 SPEC R8（不改）。
白話看板：`白話說明/GAP-1施工進度.md`（🔴 **每批收尾必改**；WATCHED 已綁實作路徑，不改會被 push 擋）。

**接手順序**：
1. **收斂 B2 review**：三檔 `handoffs/20260818-gap1-b2-review-{codex,composer,grok}.md`
   （codex 6／composer 5／grok 10；composer／grok 皆「需修補後進 B3」，codex 檔頭見其 Verdict）。
   session `20260818-gap1-b2-review-r14`、round `d38851a5-0557-4b42-82ac-cbb0935946c1`（OPEN）。
   `bash scripts/reconcile_build.sh 20260818-gap1-b2-review-r14 --mode review <三檔>` → 填群集（**引用全部 21 ID**）
   → `completeness_check --synth … --lock …` → `debt_clear.sh --round-id … --session … --lock …`。
   🔴 brief 段 B／D 我**主動列了四條自己最可疑的決定**（`set(row)!=set(schema)` 一次擋兩類；float 收 int；
   併發寫 TOCTOU；`annualized` row 計入 `n_rows_rejected` 是否誤判）＋段 C「`monkeypatch ledger_path` 使路徑推導無覆蓋」——
   請優先看委員對這幾條的判定，**取較嚴版**。
2. **修 → commit → 派 B2 戳記輪**（brief 仿 `handoffs/20260818-gap1-b1-stamp-v3-BRIEF.md`；
   🔴 **戳記期間主控端不得動工作區、不得跑探針**；探針有互斥鎖，**brief 只叫一家跑**）。
3. **B3**（3.1 MinBTL → 3.2 DSR → 3.3 報告 → 3.4 reporter/API）→ 三家 review → 戳記 → **B4**（4.1→4.2→4.3→**2.4**）。
   B3 開工前先跑 `git stash list` 確認乾淨；每 Task 完成即補探針 mutation（§V-1／2／3／11／12 屬 B3）。
3b. **🔴 小任務（使用者 2026-08-18 定，排在 B2 收斂之後、B3 之前）：白話說明之人類閱讀介面**。
   決定＝**來源維持 .md**（我與委員、所有守衛不動），另**由腳本生成 HTML**：
   `scripts/plain_docs_render.sh` → 用 venv 內已有的 `markdown_it`（rich 依賴）把 `白話說明/*.md` 渲染成
   `docs/site/*.html`（含 `index.html`、簡潔 CSS、表格／狀態燈可讀、手機友善），**每次 commit 白話檔時同一 commit 產出**
   （掛 pre-commit：staged 含 `白話說明/*.md` 即重生成並 `git add docs/site/`；缺產出＝擋）。
   本機：`open docs/site/index.html`；GitHub：**使用者須在 repo Settings → Pages 選「Deploy from branch: main, /docs」**
   （這步只有使用者能點），之後網址＝`https://<user>.github.io/<repo>/site/`。
   小任務流程（Claude 自做＋自跑測試：渲染冪等、每個 .md 都有對應 .html、連結不死）；不派委員。
4. **每批收尾固定動作**（順序不可調）：pytest → 探針 → commit → `git push -q origin main`（背景；pre-push 為 `--fast` 秒級）
   → 改 `白話說明/GAP-1施工進度.md`＋`接下來要做什麼.md` 現況段 → 再 commit+push。
   🔴 **使用者要求 commit+push 皆須秒級完成且每次都同步推上 GitHub**（2026-08-18 明示，覆蓋舊「push 需明示」）。

## 現在的狀態

| 事實 | 怎麼查 |
|---|---|
| 待推筆數 | `git log --oneline origin/main..HEAD \| wc -l`（本 session 末已 push；應為 0） |
| 測試 | `strategy_validation/` **90 passed**；`Strategy/`＋`Optimization/` 合計 297 passed／2 既有紅（`test_model_hyperparam_enhanced`，stash 驗證與本 epic 無關） |
| mutation | `bash scripts/gap1_b1_mutation_probe.sh` → 8 條全紅 rc=0（§V-5／7／8／9a／9b／10／13／15）；**有互斥鎖**，併發 exit 3 |
| 戳記 | consult-r1／review-r1／r2／r4／r5／r6／r7／r8／r9／**b1-review-r10** 皆三家 PASS |
| 債 | `debt_ledger.sh --list` 末筆應為 b2-review-r14 OPEN（待上述第 1 步銷） |
| 殘留 | registry「GAP-1 待補完」G1-R1..R7＋R9（帳本完整性）＋R10（`IBacktestEngine` Protocol 未宣告新參） |
| 探針 receipt | `handoffs/run_receipts/20260818T030000Z-gap1-mutation-locked.log` |

## ⚠ 本 session 學到的（完整清單在 CLAUDE.md Gotchas，本檔不重述）

- 🔴 **委員驗收期間主控端不得動工作區——含「跑會讀寫工作區的驗證腳本」**（codex R11 BLOCKED，對）。
- 🔴 **就地 mutate 的探針不可並行**——三家同跑 ⇒ 互看 mutant、baseline 不穩（codex R12 BLOCKED，對）。已加鎖；brief 只叫一家跑。
- 🔴 **凡寫進契約的宣稱先有反例測試**：A1-19「不靜默退回 730」被兩家反例推翻（K1）⇒ A1-20 作廢。同型錯本 epic 已兩次（J1／K1）。
- 🔴 白話看板：治理 factkey 守衛把裸 `B1..B4` 當治理批次識別碼 ⇒ 看板用「第N批」。新增白話 .md 須加 `plain_docs_sync_check.sh` WATCHED（含 `scripts/` 才可持有進度）。
- 🔴 委員產出須 `gate.sh register-output <task> <file>` 才過 claim checker；自寫 brief 用 `VERIFY-EXEMPT:doc-example:<id>` 並註明「提問清單非結論」。
- 🔴 `Governance-Scope:` trailer 須與 `Co-Authored-By:` 同一段。
- 🔴 `git checkout` 還原不了未追蹤檔；mutation 若造成 SyntaxError（rc=2）不算轉紅。
