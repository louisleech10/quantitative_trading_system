# Handoff

REF:handoffs/reconcile/20260808-govb1-b4-review-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-review-r6/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前
`bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main

## 🔴 接手第一件事：**grok 額度用罄，需使用者處理**

```
403 personal-team-blocked:spending-limit — run out of credits / need Grok subscription
```

⇒ 無法接 impl、無法蓋第三家戳記。**主委未動 `scripts/governance_roles.json`**
（該檔逐字：`implementer_backup` 不自動放行，切換一律由使用者改）。
**使用者二選一**：① 加 grok 額度 ② `bash scripts/set_roles.sh codex`。

期間主委自任實作端，review 仍由 codex＋composer 雙家族（實作者不自審成立）。

```
1. git rev-parse HEAD origin/main            # 不同＝有未 push
2. bash scripts/debt_ledger.sh --has-open    # 期望 rc=0
3. bash scripts/govb1_final_gate.sh          # 期望 rc=0，🔴 約 340s，**必丟背景**
4. bash scripts/plain_docs_sync_check.sh     # 期望 rc=0
```

**數字一律現跑；本檔不記數字。**

## ▶ 進度：第 1 批＝B1–B10

| 批 | 狀態 |
|---|---|
| B1 / B2 / B3 | ✅ 收案（`0b4b576` / `349626c` / `3e8490f`） |
| **B4** | ✅ **階段 1 收案**（`3ce0224`；閉合輪兩家 sentinel＋「可收案」） |
| **B4 階段 2** | ⬜ **下一步**：啟用 (d) fail-closed（見下） |
| B5–B10 | ⬜ `B5(1.5) → B6(2.1→2.2) → B7(3.1→3.2) → B8(4.1) → B9(4.2) → B10(4.3)` |

## ▶ 下一步：**B4 階段 2 — (d) fail-closed**

階段 1 已在生產實測多輪（`committee_run` 每次派工皆 append `--brief`，全部通過）。
階段 2 只做一件事：**impl 判準之派工缺 `--brief` ⇒ 拒發 token**。

🔴 **觸發條件禁用 `--spec` 為代理**（codex audit：31 筆 impl round 中 8 筆無 `--spec`＝25.8% 完全繞過）。
須用 `--brief` 之 kind==impl 或角色閘 family==implementer。
🔴 落地後**同時關閉 `R-11`／`R-12`**（`dispatch.sh` 不 append `--brief` 之繞過）。

## 🔴 具名殘留（**不得宣稱已閉合**）

| # | 殘留 | 追蹤 |
|---|---|---|
| R-1…R-10 | 見 `handoffs/20260801-GOV-AMEND-BACKLOG.md` | 各票 |
| **R-11** | full path 未掛 `_check_expected_delta`（掛了會打紅 `_B45_HARNESS`，B4 窗禁改） | 階段 2 |
| **R-12** | `scripts/dispatch.sh:84` 不 append `--brief` ⇒ 該路徑不觸發 (c) | 階段 2 |
| **R-13** | 未列舉之其他 Unicode `Cf`／`Zs` 碼點可能被當內容（**擋意外不防蓄意**） | 具名接受 |
| **R-14** | `review-r2` 收斂檔僅 **2/3** 戳記（grok 額度封鎖，非拒絕蓋章） | grok 恢復後補蓋 |

🔴 **禁宣稱「階段 1 已閉合強制」**——兩家 review 皆確認現行文字未如此宣稱，維持。

## 🔴 B4 教訓（供 B5 起沿用）

1. **委員開的解法可能本身不可執行**——`b4_start` 錨點被封閉三-key 集合擋住，consult 四方皆未察覺。
   **採信委員修法前須窮舉相關閘**（硬規矩 2 雙向適用）。
2. **恆真斷言我自己也會寫**——`removed == set(_B4_ALLOWED_COVARIANT)` 拿導出值比自身來源；
   由 mutation probe 當場抓出。**oracle 期望值須為字面凍結常數。**
3. **`try/except AssertionError` ＋ 自拋 sentinel ＝ 假綠**（會接住自己的 sentinel）；一律用
   `pytest.raises(..., match=)`。
4. **多餘的深度防禦可能是淨損**——我加的「空 kind ⇒ fail-closed」遮蔽了 `V18` 承重 mutation 之證明。
5. **原始碼子字串斷言極脆**：`_B45_HARNESS` 以逐字比對守衛原始碼，重構改縮排即弄紅全套閘。
   相關守衛已於原處註明「逐字凍結、不得縮排」。
6. **分歧看碼證不看票數**已實際用到兩次（B5 延伸性、`~~~` fence），兩次都靠自跑複驗定案。

## 🔴 硬規矩

1. **執行端跑驗收時，主控端不得動 tracked 檔**；勿並行跑兩份會 mutate 的 pytest。
2. **推翻委員裁定前**、**採信委員修法前**，**皆須窮舉相關閘**（雙向適用）。
3. **`--adversarial` 之 reconcile 必須先戳記**，否則 `gate.sh` 拒發 impl token。
4. **收斂檔改內容 ⇒ 舊戳記失效**：改標 `VOID-STAMP` 保留，依新 hash 重蓋。
5. **戳記須三家一次派齊**（grok 封鎖期間只能 2/3 ⇒ 具名殘留，不得視為滿足）。
6. 🔴 **`STAMP-BLOCKED` 不適用於 stamp-target 本身**（`AGENTS.md:40` 之「所依」指 `REF:`）。
7. **codex 沙箱 `.git/*.lock` rc≠0 已九次為環境問題**；須其他獨立來源 rc=0 且主委自跑複驗。
8. **兩家分歧看碼證不看票數**；純標籤分歧無單向碼證 ⇒ 採較嚴版。
9. 🔴 **收窄型修法之反向風險＝「該擋的從此不受檢」**：review brief 必須要求
   ①既有反例逐項不退化 ②合法樣式列舉清單漏接測試 ③收窄機制自身之退化態。
10. 🔴 **閉合須由原提出方重跑同一反例**（章程 §B8），不憑「已修」信任。

## 委員債務慣例

impl／stamp 輪 ⇒ `debt_clear.sh --abandon --kind no-findings-expected --approver main-agent --reason ...`
（家族失敗／未交件 ⇒ `--kind collection-failed`）。
review／consult 輪 ⇒ `reconcile_build --mode review` ＋ `debt_clear --session <name> --lock <sources.lock>`。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜**session 名與 task-id 須大小寫對應**｜
**gate 誤判**：含 `claude` 之路徑＋任何 `-p` 子字串（含 `--porcelain`）｜
`completeness_check` 正式入口＝`--lock <lock> --synth <synth>`（位置參數會被拒）｜
🔴 **錨點檔 `scripts/govb1_frozen_hashes.txt` 為主委專屬，執行端只讀不寫**

## 工作區

`git status --short` 現跑。🔴 **B3 十檔維持未 commit**（留至 `B3R`）：
`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`。
另 `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 亦不 commit。
