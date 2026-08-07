# Handoff

REF:handoffs/reconcile/20260807-govb1-b1-review-r3/synth.md
REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md

**Agent**: Claude(Opus 5) | **Time**: 2026-08-07 | **Branch**: main

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main            # 差異＝本批未 push
2. bash scripts/debt_ledger.sh --has-open    # 期望 rc=0
3. bash scripts/govb1_final_gate.sh          # 期望 rc=0，🔴 約 300–370s，**必須丟背景**
4. venv/bin/python -m pytest tests/governance/test_govb1_contract_matrix.py -q   # 23 passed
5. bash scripts/plain_docs_sync_check.sh     # 期望 rc=0
```

**數字一律現跑；本檔不記數字。**

## ✅ 批 1 已收案並收尾（`GATE-B1` 通過；收尾亦兩家 APPROVED 零 finding）

`base=62787fe` → `ae68bc3`(r1) → `b92aff6`(r2) → `d56b07e`(r3) → `fd7f0f1`(r4)
→ `1768232`／`98101e9`／`ddbc24d`／`0ea95d2`(r5) → `947e0b2`／`277ed5f`(r6)
→ `bac3d13`／`9de1694`(r7, HEAD)

**主委自跑之權威值**：`bash scripts/govb1_final_gate.sh` → **rc=0**（`g0_tests`／`g0_syntax`／`g1`–`g8` 全 PASS）。
🔴 codex 該輪回報 rc=1，根因為**其沙箱 `.git` lock 建不起 worktree**，codex 自陳不得稱綠；
composer 同命令 rc=0。依「執行端 rc ＝該沙箱內 rc」以主委自跑為準。

**裁定鏈**（皆無戳記工作輸入）：
`…/b1-review-r3/synth.md`（`GATE-B1` 收案）→ `…/b1-consult-r1/synth.md`（簿記 vs `G-7` 互斥，採方案 B）
→ `…/b1-review-r4`（`CODEX-R4-P1-01`）→ `…/b1-review-r5`（`CODEX-R5-P1-01`，改採有界解）
→ `…/b1-review-r6/synth.md`（**最終收案，含五項殘留表**）。

### 收尾期間之三項設計變更（皆經三家或雙家裁定）

1. **manifest 增 `meta` 動詞**（封閉四項：`HANDOFF.md`／`CLAUDE.md`／backlog／`白話說明/`）
   ——解「治理簿記檔 commit 即違反 `G-7`」vs「不 commit 則 pre-push 擋」之互斥。
   `_g7_policy` decl ＝ `(allow ∪ meta) − deny`；🔴 **`T-0.1-F5` 維持只比 `allow`**。
2. **`_g7` 路徑處理 NUL-safe**：manifest path ＝動詞後整段（禁 `$2` 截斷）；
   actual ＝ `git -c core.quotepath=false diff --name-only -z`。
3. **manifest grammar fail-closed**：路徑之 `leading-whitespace`／`trailing-whitespace`／`control-char`
   ⇒ 顯式拒絕並印 `form=<名>`。**設計即「不支援者顯式拒絕」，非缺陷**——
   後續同類形態變體一律不受理（`…/b1-review-r5/synth.md` 收斂裁定）。

## ▶ 下一步：批 2（Task 1.1 lifecycle matrix）

🔴 **開工前必辦**（依 `x-consult-r12` 之批次重排前置，未完成前不得改批次表順序）：
①消解 SPEC 標頭與 TODO 批次表之依賴閘互斥（**走 SPEC 延伸檔，不就地改**）
②釐清 `B7→B1` 依賴 ③B6 擴充 schema ④每批摩擦 receipt。

🔴 **Task 1.1 之歸屬票為「待確認」⇒ 歸屬閘會拒發 impl token**。
解鎖＝派 consult 輪（不帶 `--todo`）請三家裁定 → 於 Task 標題宣告 → 更新 TODO `§0.1a`。
**主委不得自行推測**（內文第一個票號常為交叉引用）。

## 🔴 批 1 之具名殘留（**五項，不得宣稱已閉合**）

| # | 殘留 | 機械綁定 |
|---|---|---|
| R-1 | `_g7` 交付守衛僅攔 `??`/`A*`；allow 內檔案之未 commit 修改逃檢 | ✅ 到期閘：批 3 標的檔進 `base..HEAD` 而守衛仍窄 ⇒ `test_g7_narrow_guard_expiry_live_pass` 轉紅 |
| R-2 | TODO §B 三處偽碼不可執行（`票 B-43`） | ❌ **無**——照抄得假綠，無檢查會擋 |
| R-3 | `single_source_check` 為正向斷言，擋不住「有 pointer 但旁邊另寫互斥判準」 | ❌ 併 `票 B-25` |
| R-4 | 「引用已廢判準只寫階號」為寫作紀律 | ❌ 併 `票 B-25` |
| R-5 | **兩份 `_g7_policy` 分叉**：production 含 `meta`＋`mpath()`；`_f5_shell()` 內嵌僅 `allow`＋`$2` | ❌ 無——修法方向＝共用單一 manifest parser（`CODEX-R4-P2-02`，兩家判 MINOR、未證明已假綠） |

**R-1 到期時**：放寬 `_g7` 與更新到期測試**須配對**；只改測試不改守衛＝假綠。

## 🔴 本日新增之硬規矩（皆為實際踩到）

1. **執行端跑驗收時，主控端不得動檔**——會使「工作區 dirty 數前後不變」類斷言 flaky。
   亦不得並行跑兩份會就地 mutate 的 pytest。
2. **推翻委員「不在本輪」之裁定前，須窮舉所有相關閘**——本日只查「TODO 非凍結文件」
   而漏查 scope manifest，造成 `G-7` 違規（`d56b07e` → `fd7f0f1` 撤回）。
3. **執行端須先 commit 再跑 `GATE-FINAL`**（`x-consult-r10` W-1）——
   commit 前跑會漏掉「未宣告即修改」類違規。
4. **看到 commit 出現 ≠ 該輪結束**，勿提早銷帳。
5. `govb1_final_gate.sh` 全跑含 `_g0_tests`（全套 pytest）⇒ **必丟背景**，前景必 timeout。

## 委員債務處理慣例（本日確立）

impl 輪交件為實作回報、非 findings 文件 ⇒ 無 canonical heading ID ⇒ 正規銷帳走
`debt_clear.sh --abandon --kind no-findings-expected --approver main-agent`，理由據實寫明
「其判斷已逐項轉入下一輪 review brief」。review 輪則走 `reconcile_build --mode review` ＋ `--lock`。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜`pytest tests/governance` 現為 **828 tests／約 280s**
（`CLAUDE.md` 記的 766／267s 已過期）｜
**gate 誤判**：含 `claude` 之路徑 ＋ 後續任何 `-p` 子字串（如 `git rev-parse`）⇒ 被判 dispatch
（`票 B-15` 洞 B，本 TODO Task 3.2 修）｜
戳記 provenance 須 `bash scripts/gate.sh register-output <task-id> <reconcile 檔本身>`

## 工作區

`git status --porcelain` 現跑。🔴 **B3 十檔維持未 commit**（留至 `B3R`）：
`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`。
另 `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 亦不 commit。
