# Handoff

REF:handoffs/reconcile/20260808-govb1-b3-review-r6/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-review-r5/synth.md
REF:handoffs/reconcile/20260808-govb1-b3-consult-r1/synth.md
REF:handoffs/reconcile/20260808-govb1-b2-review-r7/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前一律
`bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
（主委 2026-08-08 曾把未戳記檔寫進 `REF:` 並附註解說明，仍被 `verify_pretooluse` 當場擋下。
**規則是機械的，註解不能豁免。**）

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
| **B3** | ✅ **收案**（`3e8490f`）——三家戳記；主委自跑全套閘 rc=0（12 條全 PASS） |
| B4–B10 | ⬜ `B4(1.3) → B5(1.5) → B6(2.1→2.2) → B7(3.1→3.2) → B8(4.1) → B9(4.2) → B10(4.3)` |

## ▶ 下一步：**B4（Task 1.3 — `EXPECTED-DELTA:` 宣告）**

**偵察已完成**（主委＋三家平行）：`handoffs/reconcile/20260808-govb1-b4-consult-r1/synth.md`
——**尚未戳記**（工作輸入，非授權依據）。

### 接手照序做

1. **派該收斂檔之三家戳記輪**（body sha256 現跑）
2. 戳記後**派 B4 impl**，須先定案下列 **六項**（皆已四方確認）：

| # | 事項 |
|---|---|
| `P0` | TODO 空區塊判定**恆真**（`D-D` 被當範圍運算子 ⇒ literal `-` 未排除 ⇒ 標題行恆命中）。`票 B-43` 第五例。修法須附「移除檢查後空區塊用例轉綠」之 mutation |
| `P0` | `brief_conformance_check.sh --only` 與 `gate.sh` `_brief_kind()` **皆不存在**（實跑各 0）——須先建掛點；🔴 **禁在 `gate.sh` 另寫第二份 kind parser** |
| `P0` | **`--spec` 非 impl 可靠判準**（codex 更正主委）——(d) 以 `--spec` 為代理會留 bypass |
| `P0` | `scripts/cx_run.sh` **為必改共變檔但未列 Task 欄**（新增 JSON 節 ⇒ 兩支 embed 皆須更新） |
| `P0` | 🔴 **B3 waiver 測試以 `b3_start..HEAD` 開放區間持續生效，禁改 `cx_run.sh`／`govflow_lifecycle.json` ⇒ 會擋住 B4**（**第四次結構性死鎖**）。須**主委撰寫 `b4_start` 錨點**收斂區間；**禁實作端自行放寬** |
| `P1` | 交付順序須分階段：`--brief`＋(c) 先落地 → 主委改派工慣例實測 → **最後**才啟用 (d)。同批交付會使主委派不出工 |

另 `P1`：single-writer superset **無機械強制**，B4 擇一（補強制或立票），**須明說選哪個**。

## 🔴 B3 收斂軌跡（**六輪**，供 B4 起參照）

```
review-r1: 4（守衛根本不生效） → r2: 4（邊界繞過；此輪定死停損條件）
→ r3: 1（偶數巢狀） → r4: 1（討論語境誤擋）＋1 立票 → r5: 2（皆 REGRESSION）
→ r6: 0 blocking ⇒ 收案
```

**停損機制實際運作**：`SAME-CLASS-VARIANT` 轉殘留、`REGRESSION` 無例外須修、`NEW-CLASS` 逐案裁定
——**未出現無限追逐**。

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
