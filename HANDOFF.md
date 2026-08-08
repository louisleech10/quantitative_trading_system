# Handoff

REF:handoffs/reconcile/20260808-govb1-b2-review-r7/synth.md
REF:handoffs/reconcile/20260808-govb1-b2-review-r6/synth.md
REF:handoffs/reconcile/20260808-govb1-b2-consult-r2/synth.md
REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md
REF:handoffs/reconcile/20260807-govb1-x-consult-r7/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列，不只第一列。**
上列**五份皆已三家 APPROVED**（派工前一律 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0）。
其餘 `b1-review-r6`／`b2-review-r3`／`b2-review-r5` 等**皆無戳記**，列入即使執行端依
`AGENTS.md` STAMP-BLOCKED 回 `BLOCKED`、整輪作廢（2026-08-07、08-08 各一次，皆主委違反自己寫的規矩）。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-08 | **Branch**: main

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main             # 不同＝有未 push
2. bash scripts/debt_ledger.sh --has-open     # 期望 rc=0
3. bash scripts/govb1_final_gate.sh           # 期望 rc=0，🔴 約 330s，**必丟背景**
4. bash scripts/govb1_single_source_check.sh  # 期望 rc=0（全表）
5. bash scripts/plain_docs_sync_check.sh      # 期望 rc=0
```

**數字一律現跑；本檔不記數字。**

## 🔴 使用者定義：「第 1 批」＝ GOVB1 的 **B1–B10 全部**，不是批次 B1

離線期間一律不停不問，取捨交委員共識決。

## ▶ 進度

| 批 | 內容 | 狀態 |
|---|---|---|
| **B1** | Task 0.1 契約基線＋fixture | ✅ 收案並 push（`0b4b576`） |
| **B2** | Task 1.1 lifecycle matrix | ✅ **部分完成收案**（`b03595b`＋`5112aa9`），三家戳記；**未 push** |
| B3–B10 | 見下執行序 | ⬜ |

**執行序**：`B3(1.2→1.4) → B4(1.3) → B5(1.5) → B6(2.1→2.2) → B7(3.1→3.2) → B8(4.1) → B9(4.2) → B10(4.3)`

## ▶ 下一步：B3（Task 1.2 → 1.4）

🔴 **B3 之 impl 派工阻塞於 `票 B-45` 或明確 waiver**；**consult／SPEC 層可平行**
REF:handoffs/reconcile/20260808-govb1-b2-consult-r2/synth.md
（`consult-r2` 群集 5，碼證＝TODO `:151` `GATE-B3` 綁 `T-1.2-*`／`T-1.4-*`，不依 Task 1.1 全綠）。
⇒ **接手者先決定：走 waiver 還是先解 `票 B-45`。** 兩者皆須委員裁定，不得主委獨斷。

同檔 `brief_conformance_check.sh`，Task 1.2 → 1.4 **須依序、禁併同一 commit**。

## 🔴 具名殘留（**九項，不得宣稱已閉合**）

| # | 殘留 | 機械綁定 |
|---|---|---|
| R-1 | `_g7` 交付守衛僅攔 `??`/`A*` | ✅ 到期閘（批 3 標的進 range 而守衛仍窄 ⇒ 轉紅）；已加 anti-drift ＋ 真實 git range |
| R-2 | TODO §B 三處偽碼不可執行 | ❌ `票 B-43` |
| R-3 | `single_source_check` 擋不住「有 pointer 但旁邊互斥」 | ❌ 併 `票 B-25` |
| R-4 | 「引用已廢判準只寫階號」為寫作紀律 | ❌ 併 `票 B-25` |
| R-5 | 兩份 `_g7_policy` 分叉（production 含 `meta`＋`mpath()`；F5 內嵌僅 `allow`＋`$2`） | ❌ 無 |
| R-6 | `§0.1a` 人讀過期（`1.1=票 B-19`、`1.4=票 B-29` 兩處已判定為錯，TODO 不可寫） | ❌ 待 B-6 生成器投影 |
| R-7 | 治理守衛可自我授權 | ❌ `票 B-44`——repo 內無解，須外部信任錨 |
| ~~R-8~~ | ~~embed 與 production 漂移~~ | ✅ **已閉合**：`lifecycle_embed` 閘（byte-identical ＋ mutation） |
| **R-9** | `_lifecycle_cleanup_if_temp` rc 被吞（`rm` 失敗 ⇒ temp 殘留且 rc=0） | ❌ `票 B-46` |

## 🔴 `票 B-45` / `票 B-46` 之禁區（三家戳記確認，勿重議）

- **`B-45`**：`P0-01` case data-drive ＋ 五 harness 同步 JSON。**本 epic 凍結 scope 內不可執行**
  （五檔 `in_allow=0 in_meta=0`；加 `allow` 撞 `T-0.1-F5`；改 F5 期望＝自我授權）。**先解 `B-44`。**
- **`B-46`**：🔴 **禁採「cleanup 失敗即回非零」**——會使派工鏈路在 temp 刪不掉時 fail-closed 且不可自救。
  codex 已明確接受此拒絕。偏好修法＝每輪私有 temp 目錄 ＋ stderr 告警 ＋ **保留派工 rc** ＋ rm-failure 回歸測試。

## 🔴 硬規矩

1. **執行端跑驗收時，主控端不得動 tracked 檔**（dirty 數斷言會 flaky）；亦不得並行跑兩份會就地 mutate 的 pytest。
2. **推翻委員裁定前，須窮舉所有相關閘**。
3. 🔴 **採信委員修法前，亦須窮舉相關閘**——2026-08-08：codex 之 `P0-01`/`P0-02` 修法需改 5 個不在 `allow` 的檔，
   照字面派出必 `G-7` 紅。**規矩雙向適用。**
4. **執行端須先 commit 再跑 `GATE-FINAL`**；**見 commit 出現 ≠ 該輪結束**。
5. `govb1_final_gate.sh` 全跑約 330s ⇒ **必丟背景**。
6. **codex 沙箱之 `g0_tests`／`restore_golden_inventory` rc≠0 已五次為環境問題**（`.git/*.lock`）——
   判定前須有**其他獨立來源** rc=0；**主委須自跑複驗**。
7. **composer 可能 `resource_exhausted`** ⇒ `ROUND_ID=<id> bash scripts/cx_run.sh composer <brief> <out>` 同輪重試。
8. 🔴 **`REF:` 所有列皆須已戳記**（見檔頭）。
9. 🔴 **兩家分歧看碼證不看票數**；純標籤分歧且無單向碼證 ⇒ **採較嚴版**（`review-r7` 群集 2 反向亦適用：
   委員修法若引入更大風險，得**拒修法但接受 finding**，轉具名殘留——須於戳記輪指名該家表態）。
10. 🔴 **`--adversarial` 之 reconcile 必須先戳記**，否則 `gate.sh` 拒發 impl token（2026-08-08 實際被擋）。
11. **收斂檔改內容 ⇒ 舊戳記失效**：改標 `VOID-STAMP` 保留為稽核軌跡，依新 hash 重蓋。
12. **戳記須三家**（`review_families` SoT＝codex/composer/grok），**一次派齊**，勿先派兩家再補。

## 委員債務慣例

impl／stamp 輪交件非 findings 文件 ⇒ `debt_clear.sh --abandon --kind no-findings-expected --approver main-agent`。
review／consult 輪走 `reconcile_build --mode review` ＋ `debt_clear --lock`。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜**session 名與 task-id 須為大小寫對應**（`session_name_check`）｜
macOS bare `mktemp` **忽略 `TMPDIR`**，須給 template｜
**gate 誤判**：含 `claude` 之路徑 ＋ 任何 `-p` 子字串（如 `mkdir -p`）⇒ 被判 dispatch（`票 B-15`）｜
戳記 provenance 須 `gate.sh register-output <task-id> <reconcile 檔本身>`

## 工作區

`git status --porcelain` 現跑。🔴 **B3 十檔維持未 commit**（留至 `B3R`）：
`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`。
另 `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 亦不 commit。
