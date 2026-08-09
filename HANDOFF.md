# Handoff

REF:handoffs/reconcile/20260808-govb1-b4-review-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b4-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-review-r6/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前
`bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-09 | **Branch**: main

## ▶ 兩個低摩擦機制（2026-08-09 上線，使用者授權）

### ① 換委員 ＝ 改一行

```json
"review_families": ["codex", "composer", "grok"],   // 正式名冊，**不動**
"active_stampers": ["codex", "composer"]            // ← 改這行（grok 暫停中）
```

- `reconcile_stamps_check` **預設**優先讀 `active_stampers`，缺席才回退 `review_families`
  ⇒ **所有呼叫端自動生效**（含被 frozen mutation 測試逐字錨定、無法傳參的 V-C 呼叫點）
- `gov_check` 每次 push 印「⚠ 委員暫停中（未清）: grok」⇒ **不靠記憶**
- `active_stampers` 含不在 `review_families` 之家族 ⇒ `rc=1`（防悄悄擴編）
- 🔴 **`review_families` 絕不動**——9 個既有斷言依賴它，其中
  `test_rolegate_predispatch.py` 屬 `_B45_HARNESS` **硬性禁改**

### ② 任務中穿插修別的問題 ＝ commit 加一行 trailer

```
Governance-Scope: out-of-epic <理由>
```

該 commit 觸及之路徑**豁免 manifest allow 檢查**。

🔴 **仍硬保護**（out-of-epic 亦禁）：`docs/GOVB1_`／`govb1_scope.manifest`／`govb1_frozen_hashes.txt`
🔴 **刻意不含 `_B45_HARNESS` 五檔**——out-of-epic 工作正是治理 harness 之維護，
那五檔的真正守衛是 pre-push 全套 pytest；檔案凍結只是 epic 內防 scope creep。
🔴 **非靜默旁路**：`gov_check` 每次 push 列出 range 內所有 out-of-epic commit。

**mutation 實證**：帶 trailer 改非 manifest 檔 ⇒ `g7 PASS`；
amend 掉 trailer ⇒ `g7 rc=1` 且具名該檔；放回 ⇒ `PASS`。

**出生理由**：epic 期間 G-7 要求每個改動檔都在 manifest allow，而 manifest ≡ 凍結唯讀 TODO
之宣告集合 ⇒ **整個 repo 被凍住，治理設施無法演進自己**（2026-08-09 一天內撞牆四次）。

## 🔴 grok 額度用罄（流程已不受阻，但仍建議處理）

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

## 🔴 B4 階段 2 — **已嘗試，被批次 scope 擋下，已撤回**（`ed8a6dc` → `eaef2db`）

**做法**：因觸發條件**禁用 `--spec` 為代理**（audit：31 筆 impl round 中 8 筆無 `--spec`＝25.8% 繞過），
唯一非代理的表述是「**所有 dispatch 皆須 `--brief`**」。實作後：
缺 `--brief` rc=1 且歸因正確、帶 `--brief` rc=0 發 token、mutation 兩測轉紅——**功能本身正確**。

🔴 **但波及面超出批次 scope**：全套 `pytest tests/governance` **31 failed**，
橫跨 **10 個測試檔**（`test_debt_gate`／`test_dispatch_wrapper`／`test_family_registry`／
`test_verify_gate_r7ext`／`test_reconcile_target_bound_to_synth`／`test_low_risk_impl_requires_reconcile`／
`test_waived_adversarial_still_stamps`／`test_completeness_semantic`／`test_reconcile_completeness_enforced`／
`test_verify_gate_b4`／`test_verify_gate_redteam`）——它們直接呼叫 `gate.sh dispatch` 而不帶 `--brief`。

**這些檔全部不在 `scripts/govb1_scope.manifest`** ⇒ G-7 會擋「未宣告即修改」。
而擴充 manifest 會被 **我自己在 §0 立的 B4 窗守衛**擋下
（`scripts/govb1_scope.manifest` 在 `_B4_FORBIDDEN_PREFIXES`）
⇒ **那正是「被約束方自解約束」，不得對自己網開一面。**

🔴 **這是本 epic 第五次結構性死鎖。**

### 恢復階段 2 需要的**明確決策**（不得由主委單方擴大 scope）

擇一，皆須經委員裁定：
1. **擴充批次 scope**：把上列 10 檔納入 `govb1_scope.manifest`，並同步放寬 B4 窗守衛
   ——須說明為何這不算 scope accretion。
2. **另立票**：`(d)` 移出 B4，獨立為一張「派工鏈路全域改造」票，其 scope 自帶那 10 檔。
3. **改設計**：找出既非 `--spec` 代理、又不需改那 10 檔的觸發條件（目前未找到）。

**主委傾向 2**（爆炸半徑本來就跨批次，硬塞進 B4 是 scope 錯配）。

## ▶ 下一步：**B5（Task 1.5）— 偵察已完成，四項待定案**

**偵察收斂檔**：`handoffs/reconcile/20260809-govb1-b5-consult-r1/synth.md`
（body `sha256:5a2c61ac…29c5`；**codex／composer 皆 APPROVED**，
🔴 **`grok` 因 403 額度封鎖缺席 ⇒ 只有 2/3，具名殘留 `R-14`，不得視為滿足三家**）
三方獨立產出（codex／composer／主委平行）。

### 🔴 開工前必定案四項

| # | 事項 |
|---|---|
| `P0` | 🔴🔴 **第六次結構性死鎖**：`gate.sh:697,702` 對 `--spec`／`--todo` **必跑** `template_check.sh` 且失敗即拒發 token；Task 1.5 之 **C** 要加進該腳本且套用範圍涵蓋**本 epic 自己唯讀凍結的 SPEC/TODO** ⇒ **C 一落地，所有帶 `--spec` 之派工全部拒發，無人能修**。修法（兩家一致）＝C **禁掃自然語言 occurrence**，只解析**明示結構化欄位**（如 `SCOPE-CLAIM:`）。🔴 **三方計數不一致（主委 16/22、codex 9/6 與 17/16、composer 4/11）本身即為發現：判準未定義。** |
| `P0` | **`A` 之 `pending` 是無判準的 fail-open**：不存在腳本 `rc=127` 也會被吞成 pending。須限縮為封閉條件（命令與依賴可解析 ＋ Task 明示新建之路徑恰為 `ENOENT`），其餘非零保留失敗。可參照 `scripts/verify_narrowing_consistency.sh:16-20,103-116` 之嚴格文法 |
| `P0` | **`_func_exists` 偽碼雙向缺陷**（`票 B-43` **第六例**）：`function foo {`（無括號）**漏接**；`${1}` 未跳脫使 `f.oo` 誤命中 `fXoo`、`f*` 誤命中 `f`。須依語言形態分支 ＋ literal 化 |
| `P0` | 三掛點（`_run_assert_lines`／`_func_exists`／`_check_scope_claim`）與 `test_govb1_template_check_ext.py` **皆不存在**，須先建再接線。🔴 **但都已在 manifest allow 清單內 ⇒ scope 無阻礙**（與 B4 階段 2 不同） |

**已澄清**：只讀 fixture `spec_assert_pending.md`／`spec_func_missing.md` **實測存在**（T-4 成立）；
註解問題**非** `B-43` 第六例（`^` 錨點已擋；採 codex 碼證），
但 impl brief 須明寫「邊界②之剝除要求已由 `^` 錨點滿足」避免實作端照抄困惑。

### 接手照序做

1. ✅ **戳記輪已完成**（2/2 可用家族 APPROVED）
2. ✅ **impl brief 已寫好並通過合規檢查**：`handoffs/20260809-govb1-b5-impl-r1-brief.md`
   （`brief_conformance_check` rc=0、`--only expected-delta` rc=0）
   兩個定案已在 `§0` 內逐字釘死：
   - **C 之封閉文法** `SCOPE-CLAIM:<id> <subject> DERIVE:<executable command>`
     （行首錨定＋`<id>` 不得重複＋fence 內不算＋CRLF 正規化；**不執行該命令**）
   - **`A` 之 `pending` 三條件**（可解析 ＋ 恰為 `ENOENT` ＋ 路徑明示於「新建」欄），
     其餘非零一律保留失敗
3. **接手直接執行該 brief**。🔴 **實作端**：`grok` 封鎖期間由主委自任
   （角色檔禁 Claude 自選備援），review 仍 codex＋composer 雙家族。
4. 🔴 **最高優先驗收 `T-1.5-C0`**：交付後
   `bash scripts/template_check.sh spec docs/GOVB1_INPUT_QUALITY_SPEC.md` **rc 須仍為 0**（`todo` 同）。
   **任一非零＝做成了掃描式，第六次死鎖成真，退回重做。**

## 🔴 具名殘留（**不得宣稱已閉合**）

| # | 殘留 | 追蹤 |
|---|---|---|
| R-1…R-10 | 見 `handoffs/20260801-GOV-AMEND-BACKLOG.md` | 各票 |
| **R-11** | full path 未掛 `_check_expected_delta`（掛了會打紅 `_B45_HARNESS`，B4 窗禁改） | 階段 2 |
| **R-12** | `scripts/dispatch.sh:84` 不 append `--brief` ⇒ 該路徑不觸發 (c) | 階段 2 |
| **R-13** | 未列舉之其他 Unicode `Cf`／`Zs` 碼點可能被當內容（**擋意外不防蓄意**） | 具名接受 |
| ~~R-14~~ | ~~收斂檔僅 2/3 戳記~~ | ✅ **已解**：`roster_full` 機制（見下），grok 正式列為暫停中 |
| **R-15** | 🔴 `governance_families.json` **不可 commit**（不在 manifest；out-of-epic 通道亦不適用，因它是**設定**非修復），改動走 ambient M | epic 結束後 commit |
| **R-16** | 早前 `b4-review-r2`／`b5-consult-r1` 兩份收斂檔**當時**是 2/3 而要求是 3 家；現 `active_stampers` 為 2 家 ⇒ 它們**回溯地**變成合格。此為真實語意變動，非「本來就合格」 | 具名接受 |
| ~~R-17~~ | ~~impl(`--spec`) 戳記門檻不受暫停機制影響~~ | ✅ **已解**：改 `reconcile_stamps_check` 預設值，所有呼叫端自動生效 |

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
🔴 **再加一項**：`scripts/governance_families.json`（`roster_full` ＋ grok 暫停）
——**epic 期間一律 ambient M，不可 commit**（`R-15`；理由見上「委員怎麼調換」節）。
