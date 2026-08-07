# Handoff

REF:handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md
REF:handoffs/reconcile/20260807-govb1-x-stamp-r22/synth.md

**Agent**: Claude(Opus 5) | **Time**: 2026-08-07 | **Branch**: main

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main                     # 兩值須同（本 session 全部未 commit）
2. bash scripts/debt_ledger.sh --has-open             # 期望 rc=0
3. bash scripts/govb1_selfcheck.sh                    # 期望 rc=0
4. bash scripts/govb1_single_source_check.sh          # 期望 rc=0
5. bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md
```

**數字一律現跑取得；本檔不記數字。**

## ▶ 下一步：派 `Task 0.1`（規格與清單皆已定版，這是第一件實作）

```
bash scripts/gate.sh dispatch --task-id <ID> --risk low \
  --intent "impl Task 0.1 <一句>" --facts-asked <...> --review-role <...> \
  --template "n/a:" --spec docs/GOVB1_INPUT_QUALITY_SPEC.md \
  --todo docs/GOVB1_INPUT_QUALITY_TODO.md \
  --reconcile handoffs/reconcile/20260807-govb1-x-consult-r10/synth.md
```

**Task 0.1 ＝ 契約基線＋全部 fixture 一次建立**（TODO `### Task 0.1`）。
實作端＝見 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行。

## 🔴 歸屬閘：6 個 Task 現在派不出去（**設計如此，非故障**）

`scripts/govb1_single_source_check.sh --task N.M`，已掛 `gate.sh` GOVB1 段。
歸屬票為「未標註／待確認」者拒發 impl token。**逐 Task 現況請現跑該指令確認。**

**被擋者的解鎖路徑（錯誤訊息內已寫明）**：
派一輪 **consult**（不帶 `--todo`，本閘不擋）請三家依 Task 意圖裁定歸屬票
→ 於該 Task 標題宣告 `票 B-NN` → 更新 TODO `§0.1a` 該列 → 重跑轉 PASS。

🔴 **主委不得自行推測歸屬**：內文第一個票號常為交叉引用非歸屬
（`Task 2.1` 之 `票 B-23`、`Task 3.1` 之 `票 B-6` 皆不在本批八張內）。
「只看誰沒歸類就填空」＝本日兩次對帳配反之根因。

## 已定版（可作授權依據）

| 檔 | 內容 |
|---|---|
| `docs/GOVB1_INPUT_QUALITY_SPEC.md` | 規格（`x-stamp-r4`） |
| `scripts/govb1_selfcheck.sh` ＋ `gate.sh` 掛載 | 深度自檢（已戳記檔＝`x-consult-r5`；`x-stamp-r8` 是戳記輪本身，**無戳記區、不可當 REF**） |
| `…/20260807-govb1-x-consult-r7/synth.md` | **設計裁定**，三家 APPROVED |
| `…/20260807-govb1-x-consult-r10/synth.md` | **實作收斂**，三家 APPROVED |

## 🔴 三項具名殘留（三家確認，**不得宣稱已閉合**）

1. `govb1_single_source_check.sh` 為**正向斷言**，擋不住「有 pointer 但旁邊另寫互斥判準」
2. 「引用已廢判準只寫階號、禁複述內容」為**寫作紀律**，無機械偵測
3. **完整解**＝判準移出 markdown 進資料檔＋generated block＋diff ⇒ 已併 `票 B-25`，
   前置＝現行 `.rows[]|@tsv` schema **不適用**表格型判準（`x-consult-r12` J-1）

## 批次順序：維持現行，**四項前置未完成前不得改**

三家 MODIFY 裁定目標序 `B1 → B6 → B2 → B3 → B4 → B5 → B7 → B8 → B9 → B10`（`x-consult-r12`）。
前置：①消解 SPEC 標頭與 TODO 批次表互斥（**走 SPEC 延伸檔，不就地改**）
②釐清 `B7→B1` 依賴 ③B6 擴充 schema ④每批摩擦 receipt。
淨摩擦欄之「填」＝**序數帶＋一行下界依據**，非絕對值。

## 命名（本日新增，避免踩雷）

**批一律寫「批 N」、票一律寫「票 B-NN」**——原本 `B1`（批）與 `B-19`（票）只差一個連字號。
三層對應表在 TODO `§0.1a`（**本批唯一對應表**）。

## 本日制度變更

- `票 B-13` 併入四項（對帳只驗出現不驗歸類／跨輪殘留必成漏項／Rule 12 對 stamp 輪誤觸發／白話守衛沒接到本批 ✅已修）
- `票 B-42` **改名** `GOV-TODO-DEPTH-CHECK-GENERALIZE` → `GOV-TODO-GATE-GENERALIZE`，範圍由一項擴為兩項（具名擴大）
- `票 B-25` 併入「判準資料化」
- `templates/TODO_GENERATION_PROMPT.md`：**Task 標題必含 `票 B-NN`**，禁留空／禁「未標註」（前向，不溯及既往）
- `plain_docs_sync_check.sh`：監看前綴 `docs/GOVB0_`→`docs/GOV`；受管清單改**現讀資料夾導出**
- **票數維持 42**（本日新開僅 `B-41`／`B-42`，皆委員裁定要開）

## 派工前置（每次必跑）

```
1. bash scripts/debt_ledger.sh --has-open
2. bash scripts/session_name_check.sh --session <YYYYMMDD-epic-batch-kind-rN> --task-id <同字串大寫>
3. bash scripts/doc_format_precheck.sh <brief>
4. venv/bin/python scripts/verification_claim_check.py --files <brief>
```

🔴 **brief 之 `REF:` 只准指向已戳記之 reconcile**——指未戳記者，執行端依 `AGENTS.md`
Rule 12 回 `BLOCKED`，整輪作廢（本日發生 1 次）。引用未戳記檔須明寫「非授權依據」。
🔴 **已取得三家戳記之收斂檔一律不回頭改**——更正只記當輪（本日誤改 `x-consult-r7` 致戳記失效，已撤回）。
🔴 **`## 戳記` 區禁事後 `>>` 追加 `---`**——會改動 body hash（本日發生 1 次）。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜`--approver claude` 用 `main-agent`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`git push` 必須 `run_in_background`｜`pytest tests/governance` 耗時長，丟背景｜
`completeness_check.sh --lock` 吃 **sources.lock**｜`debt_clear` 用 `--round-id`／`--session`／`--lock`｜
戳記 provenance 須 `bash scripts/gate.sh register-output <task-id> <reconcile 檔本身>`｜
**執行端回報之 rc ＝該沙箱內之 rc**，涉檔案權限者主委須自跑複驗

## 工作區（全部未 commit）

`git status --porcelain | wc -l` 現跑取得。
🔴 **commit 拆分（三家零分歧）**：`scripts/gate.sh`（GOVB1 閘）＋本 session 新檔＋
`HANDOFF.md`／backlog／`白話說明/` 為 **commit A**；
**排除** B3 十檔（`_gate_lex.sh`／`gate_check.sh`／`extract_phase2_expected_flips.py`／
`tests/governance/fixtures/{gate_decision_corpus,phase2_expected_flips}.txt{,.sha256}`／
`test_gate_decision.py`／`test_gate_deny_fields.py`／`test_gate_lexical_contract.py`，留至 `B3R`）、
`.claude/gate/audit.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`。
