# Handoff

REF:handoffs/reconcile/20260807-govb1-x-consult-r7/synth.md
REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列，不只第一列。**
現況**僅** `x-consult-r7`／`x-consult-r10` 有戳記；
`b1-review-r6`／`b2-review-r3`／`b2-review-r5` 等**皆無戳記**，
列入 `REF:` 會使執行端依 `AGENTS.md` STAMP-BLOCKED 回 `BLOCKED`、整輪作廢
（2026-08-07 一次、2026-08-08 一次，**皆主委違反自己寫的規矩**）。
無戳記之收斂檔須在**本文**具名列出並標「**非授權依據**」。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-08 | **Branch**: main

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main             # 不同＝有未 push
2. bash scripts/debt_ledger.sh --has-open     # 期望 rc=0
3. bash scripts/govb1_final_gate.sh           # 期望 rc=0，🔴 約 300s，**必丟背景**
4. bash scripts/govb1_single_source_check.sh  # 期望 rc=0（全表）
5. bash scripts/plain_docs_sync_check.sh      # 期望 rc=0
```

**數字一律現跑；本檔不記數字。**

## 🔴 使用者定義：「第 1 批」＝ GOVB1 的 **B1–B10 全部**，不是批次 B1

2026-08-08 使用者糾正。**B1 只是十分之一。** 離線期間一律不停不問，取捨交委員共識決。

## ▶ 進度

| 批 | 內容 | 狀態 |
|---|---|---|
| **B1** | Task 0.1 契約基線＋fixture | ✅ **收案並 push**（`0b4b576`） |
| **B2 前置** | `W′` 歸屬資料化／`meta` expected-set／列數契約 | ✅ 完成，**未 push** |
| **B2** | Task 1.1 lifecycle matrix | 🔴 **實作已交件，review 判 3 BLOCKING，修補未派** |
| B3–B10 | 見下執行序 | ⬜ |

**執行序（三家一致，四項前置未完成前不得前移 B6）**：
`B2 → B3(1.2→1.4) → B4(1.3) → B5(1.5) → B6(2.1→2.2) → B7(3.1→3.2) → B8(4.1) → B9(4.2) → B10(4.3)`

## ▶ 下一步：派 Task 1.1 之修補輪（三項 BLOCKING）

裁定＝`handoffs/reconcile/20260808-govb1-b2-review-r5/synth.md`（**無戳記，工作輸入，非授權依據**）。
🔴 **採 codex（三條皆附可重現反例）；composer r1 之 APPROVED 被覆蓋（無反例支撐）。**

| # | BLOCKING | codex 之反例 | 修法 |
|---|---|---|---|
| `P0-01` | `case` 仍列舉 kind，JSON 非唯一 membership／behavior source | **只在 JSON 加 `experimental` ⇒ 仍 rc=2** | 以 JSON flags **data-drive 行為**，移除所有 kind key 之 `case` 臂與錯誤字串列舉 |
| `P0-02` | 🔴 `_LIFECYCLE_EMBED_B64` ＋ 缺檔自動 cp ＝ **fallback**；**fail-closed 退化為 fail-open** | **缺 JSON 之 probe 反而 rc=0**、`GENERATED_JSON=yes` | 移除 embed fallback 與自動 cp；缺 JSON ⇒ fail-closed。**五個隔離 harness 須同步複製 JSON** |
| `P0-03` | 到期 proxy 由實作端擅改，新 proxy 兩檔名於 `dc234ce..HEAD` **為 false**；批 3 改名即**永久不過期**，無 rename protection | 同上實跑 | **保留委員核准之 expiry invariant**，或改由**凍結 task-scoped manifest／批次 marker** 導出；**不得由本 Task 改 literal proxy** |

🔴 **`P0-02` 是本 epic 第五個「假綠」**：TODO 邊界①明訂「JSON 缺 ⇒ fail-closed」，
但 `U4`／`U5` **只測缺 key 與語法錯，未測整檔不存在**。

**修補完成後** → 雙家族閉合 → 再進 B3（Task 1.2 → 1.4，
**同檔 `brief_conformance_check.sh`，須依序、禁併同一 commit**）。

🔴 **每份剩餘 brief 必加**（因 `票 B-43` 修不掉）：
> TODO §B 之偽碼**已知有三處不可執行**（`_frozen_hits` 缺 `"$@"`／fixture `sed` 截斷／`_CHECKS` `$4`應`$3`）。
> **不得照抄**；使用前須自行實跑驗證，發現有誤請明講。

## 🔴 具名殘留（**七項，不得宣稱已閉合**）

| # | 殘留 | 機械綁定 |
|---|---|---|
| R-1 | `_g7` 交付守衛僅攔 `??`/`A*` | ✅ 到期閘：批 3 標的檔進 range 而守衛仍窄 ⇒ 轉紅 |
| R-2 | TODO §B 三處偽碼不可執行（`票 B-43`） | ❌ 無 |
| R-3 | `single_source_check` 正向斷言擋不住「有 pointer 但旁邊互斥」 | ❌ 併 `票 B-25` |
| R-4 | 「引用已廢判準只寫階號」為寫作紀律 | ❌ 併 `票 B-25` |
| R-5 | 兩份 `_g7_policy` 分叉（production 含 `meta`＋`mpath()`；F5 內嵌僅 `allow`＋`$2`） | ❌ 無 |
| R-6 | `§0.1a` 人讀過期（`1.1=票 B-19`、`1.4=票 B-29` **兩處已判定為錯**，TODO 不可寫） | ❌ 待 B-6 生成器投影 |
| **R-7** | **治理守衛可自我授權**（`票 B-44`）：同時改 `_meta_want`＋manifest＋hash 即可放行未裁定路徑 | ❌ **無**——repo 內無解，須外部信任錨 |

| **R-8** | **test harness 之 embed 漂移**：`test_stamp_taskid_inject.py` 之 `_SCRIPT_NAMES` 未列 `govflow_lifecycle.json`；腳本以 base64 embed 物化 ⇒ **embed 與 production 漂移時 harness 測舊 schema** | ❌ 無——**已併入 Task 1.1 之 `P0-02` 修法**；若修法未涵蓋則須另立機檢「embed 雜湊 ≡ 檔案」 |

🔴 **R-7 非純蓄意**（codex 修正主委原判）：合法新增簿記或讀取端時同步三處，即可**無意間**擴大授權。

## 治理機制現況（批 2 前置建立）

- **`meta` 動詞**：恰 **6 項**（`HANDOFF.md`／`CLAUDE.md`／backlog／`白話說明/`／
  `govb1_task_tickets.tsv`／`govb1_single_source_check.sh`），`_g7_policy` 內 **expected-set**
  以**列數＋multiset** 比對（重複拒、順序放）。🔴 **expected-set 須在腳本內，不得放 manifest（自證）**。
- **`W′`**：歸屬事實權威＝`scripts/govb1_task_tickets.tsv`；
  🔴 **`docs/GOVB1_INPUT_QUALITY_TODO.md` 全程不可寫**（不在 `allow`／`meta`）。
- 歸屬裁定（三家）：`1.1=—`／`1.4=B-19`／`2.1=2.2=B-25`／`3.1=3.2=B-15`／`4.2=B-38`。

## 🔴 硬規矩（本次踩到才立的）

1. **執行端跑驗收時，主控端不得動 tracked 檔**——`test_t01_f3` 斷言 dirty 數不變；
   亦不得並行跑兩份會就地 mutate 的 pytest。
2. **推翻委員「不在本輪」之裁定前，須窮舉所有相關閘**（漏查 scope manifest ⇒ `G-7` 違規，已撤回）。
3. **執行端須先 commit 再跑 `GATE-FINAL`**。
4. **見 commit 出現 ≠ 該輪結束**，勿提早銷帳。
5. `govb1_final_gate.sh` 全跑含 `_g0_tests` ⇒ **必丟背景**。
6. **codex 沙箱之 `g0_tests`／worktree rc=1 已三次為環境問題**——涉檔案權限者**主委須自跑複驗**。
7. **composer 可能 `resource_exhausted`**——用 `ROUND_ID=<id> bash scripts/cx_run.sh composer <brief> <out>` 同輪重試。
8. 🔴 **`REF:` 所有列皆須已戳記**（見檔頭）——2026-08-08 因此害 codex 一輪作廢，**第二次犯**。
9. 🔴 **兩家分歧時看碼證不看票數**：本日 composer 判 APPROVED、codex 判 3 BLOCKING，
   **codex 三條皆附可重現反例、composer 無反例 ⇒ 採 codex**。
   「先審的家族沒看到後審家族的 probe」不是採信前者的理由。

## 委員債務慣例

impl 輪交件非 findings 文件 ⇒ `debt_clear.sh --abandon --kind no-findings-expected --approver main-agent`，
理由據實寫「判斷已轉入下一輪 review brief」。review 輪走 `reconcile_build --mode review` ＋ `--lock`。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜`pytest tests/governance` 現約 **860+ tests／約 300s**｜
**gate 誤判**：含 `claude` 之路徑 ＋ 後續任何 `-p` 子字串（如 `git rev-parse`）⇒ 被判 dispatch（`票 B-15`）｜
heredoc 亦會觸發分類器｜戳記 provenance 須 `gate.sh register-output <task-id> <reconcile 檔本身>`

## 工作區

`git status --porcelain` 現跑。🔴 **B3 十檔維持未 commit**（留至 `B3R`）：
`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`。
另 `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 亦不 commit。
