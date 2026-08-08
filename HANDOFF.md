# Handoff

REF:handoffs/reconcile/20260808-govb1-b3-review-r4/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-review-r3/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b2-review-r7/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前一律
`bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
⚠️ **`handoffs/reconcile/20260808-govb1-b3-review-r5/synth.md` 尚未戳記**
（工作輸入，**非授權依據**，故不列於上）——戳記輪未派。
（主委 2026-08-08 曾把它寫進 `REF:`，被 `verify_pretooluse` 當場擋下。**規則是機械的，註解不能豁免。**）

**Agent**: Claude(Opus 5) | **Time**: 2026-08-08 | **Branch**: main

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main             # 不同＝有未 push
2. bash scripts/debt_ledger.sh --has-open     # 期望 rc=0
3. bash scripts/govb1_final_gate.sh           # 期望 rc=0，🔴 約 340s，**必丟背景**
4. bash scripts/plain_docs_sync_check.sh      # 期望 rc=0
```

**數字一律現跑；本檔不記數字。**

## ▶ 進度：第 1 批＝**B1–B10 全部**

| 批 | 狀態 |
|---|---|
| **B1** | ✅ 收案並 push（`0b4b576`） |
| **B2** | ✅ **部分完成**收案並 push（`349626c`）；殘留 `票 B-45`／`B-46` |
| **B3** | 🔄 實作已到 `67c86e0`；`review-r5` 判 **2 項 `REGRESSION`** 未修 |
| B4–B10 | ⬜ `B4(1.3) → B5(1.5) → B6(2.1→2.2) → B7(3.1→3.2) → B8(4.1) → B9(4.2) → B10(4.3)` |

## ▶ 下一步（**照序**）

1. **派 `b3-review-r5` 收斂檔之戳記輪**（三家；body sha256 現跑）
   —— `gate.sh` 對 `--adversarial` 機器強制要戳記，未戳記派不出修補輪
2. 戳記後**派 B3 修補輪 5**，兩項 `REGRESSION`：
   - 行首錨定漏接 `1.`／`>`／`**…**`／`+` ⇒ 擴**有界**前綴集合（**禁開放式**）
   - `_strip_code_fences` 未閉合 fence 吞至 EOF、縮排閉合不辨識 ⇒ **fail-closed**
   🔴 **禁動 `_extract_cmds`**（兩家已確認閉合）；**禁以放寬解析器補償選列變窄**
3. review → 戳記 → B3 收案 → 更新 `白話說明/` → commit + push

## 🔴 B3 收斂軌跡（供判斷是否該收）

```
review-r1: 4（守衛不生效） → r2: 4（邊界繞過） → r3: 1 → r4: 1+殘留 → r5: 2（皆 REGRESSION）
```

**停損條件（`review-r2` 三家戳記定死）**：同一批元件再現**同類更刁鑽變體** ⇒ 轉具名殘留，不開新輪。
🔴 **但 `REGRESSION` 無例外，一律須修。** 委員 findings **必標**
`NEW-CLASS`／`SAME-CLASS-VARIANT`／`REGRESSION`，未標者當變體。

🔴 **防滑坡界線（`STAMP-R7` 三家共答）**：
「必修群集內併入變體 OK；**群集外一律轉殘留＋立票**」；
**若第三次連續『同函式順帶』而 brief 未預先寫入限縮 ⇒ 視為滑坡，預設轉殘留**。

## 🔴 具名殘留（**十項，不得宣稱已閉合**）

| # | 殘留 | 追蹤 |
|---|---|---|
| R-1 | `_g7` 窄守衛 | ✅ B3 已放寬為 task-scoped（到期閘＋五例） |
| R-2 | TODO §B 偽碼不可執行（**四處**） | `票 B-43` |
| R-3／R-4 | single_source 正向斷言／寫作紀律 | 併 `票 B-25` |
| R-5 | 兩份 `_g7_policy` 分叉 | ❌ 無 |
| R-6 | `§0.1a` 人讀過期 | 待 B-6 生成器投影 |
| R-7 | 治理守衛可自我授權 | `票 B-44`（repo 內無解） |
| ~~R-8~~ | ~~embed 漂移~~ | ✅ 已閉合（`lifecycle_embed` 閘） |
| R-9 | cleanup rc 被吞 | `票 B-46`（🔴 **禁採「失敗即回非零」**） |
| **R-10** | `assumed:` 列之計數宣稱不受檢 | **`票 B-47`**（超出 TODO Task 1.4 範圍） |
| 另 | receipt 無版控（`handoffs/*` 在 exclude）／semantic-fake receipt（防蓄意） | 具名接受 |

## 🔴 硬規矩

1. **執行端跑驗收時，主控端不得動 tracked 檔**；勿並行跑兩份會 mutate 的 pytest。
2. **推翻委員裁定前**、**採信委員修法前**，**皆須窮舉相關閘**（雙向適用）。
3. **`--adversarial` 之 reconcile 必須先戳記**，否則 `gate.sh` 拒發 impl token。
4. **收斂檔改內容 ⇒ 舊戳記失效**：改標 `VOID-STAMP` 保留，依新 hash 重蓋。
5. **戳記須三家**（`review_families` SoT），**一次派齊**。
6. 🔴 **`STAMP-BLOCKED` 不適用於 stamp-target 本身**（`AGENTS.md:40` 之「所依」指 `REF:` 授權依據）
   —— codex 曾因此誤判造成**循環死結**，brief 須明寫。
7. **codex 沙箱 `g0_tests`／`restore_golden_inventory` rc≠0 已七次為環境問題**（`.git/*.lock`）；
   須有其他獨立來源 rc=0，且**主委自跑複驗**。
8. **兩家分歧看碼證不看票數**；純標籤分歧無單向碼證 ⇒ 採較嚴版。
9. 🔴 **收窄型修法之反向風險＝「該擋的從此不受檢」**（`review-r5` 通則）：
   review brief 必須要求 ① 既有反例逐項不退化 ② 合法樣式**列舉清單**漏接測試 ③ 收窄機制自身之退化態。

## 委員債務慣例

impl／stamp 輪 ⇒ `debt_clear.sh --abandon --kind no-findings-expected --approver main-agent`。
review／consult 輪 ⇒ `reconcile_build --mode review` ＋ `debt_clear --lock`。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜**session 名與 task-id 須大小寫對應**｜
macOS bare `mktemp` **忽略 `TMPDIR`**｜**gate 誤判**：含 `claude` 之路徑＋任何 `-p` 子字串（如 `mkdir -p`）｜
戳記 provenance 須 `gate.sh register-output <task-id> <reconcile 檔本身>`｜
🔴 **`b3_start` 錨點（`scripts/govb1_frozen_hashes.txt`）為主委專屬，執行端只讀不寫**

## 工作區

`git status --porcelain` 現跑。🔴 **B3 十檔維持未 commit**（留至 `B3R`）：
`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`。
另 `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md` 亦不 commit。
