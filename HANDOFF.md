# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-07 凌晨 | **Branch**: main（本地＝遠端）
**狀態**: `票 B-39` ✅ ／`票 B-31` ✅ 部分 ／`票 B-19` ⏸ 裁定已取得待收斂 → 下一步＝**`票 B-38`**

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main        # 兩值必須相同（push exit 0 不代表推上去）
2. bash scripts/debt_ledger.sh --has-open # 應 rc=0
3. 讀 handoffs/20260806-BATCH1-RECON.md   # 第 1 批偵察，開工前必讀
```

## 🔴 下一步：`票 B-38`（已提至第 1 批之首，有決定性證據）

**它現在擋著三件事**：正規銷帳、`票 B-31` 自檢的可信度、`票 B-19` 的裁定收斂。

**2026-08-07 決定性實證**：`票 B-31` 的誠實性要求把它逼了出來——
composer 依 prompt 指示誠實寫「本輪 0 findings」，`--single` rc=0 但 `reconcile_build` rc=1
⇒ **誠實則卡住、捏造則通過**。codex 在前一日的 review 已預言（`CODEX-R1-P1-01`），24 小時內重現。

### 🔴 開工前務必知道（偵察已做完，寫在票內）

1. **B-38 與 OPEN 舊票 `GOV-NOFINDINGS-SENTINEL` 是同一件事的兩面** ⇒ **建議合併為單一票**，
   否則會造出第四種「0 findings」表達。
2. **現存已有三種表達**：`P3-00` sentinel（未機器強制）／「本輪 0 findings」散文
   （**主委 2026-08-06 寫進 `cx_run.sh` prompt，與舊慣例不一致**）／什麼都不寫。
3. **可能連帶關閉 `票 B-35`**（截斷偵測）：若契約含「宣告 findings 數」，宣告 vs 實際不符即可測截斷。
4. ⚠️ **必然撞到既有測試契約**：`test_completeness_oracles.py:603`
   `assert cov["union_size"] > 0` ⇒ 設計階段就要決定怎麼處置，**不得逕行改斷言**。
5. 判定點：`completeness_check.sh:892-894`。

## `票 B-19` 現況（裁定已取得，收斂被 B-38 擋住）

**三家 2:1 分歧，主委獨立實測支持少數方（codex）**：

| | codex（少數） | composer／grok（多數） |
|---|---|---|
| 主張 | ①③ 做、②關閉改欄位設計、④併入錯誤訊息 | 三項全關、改走第四方向 |
| ③ 實測 | placeholder-aware 判準 → **2 真陽性 0 誤擋** | 用粗判準 → 真陽性 0 |

**主委獨立驗證**：③ 複現（134 檔命中 2，`<FAMILY>-V1` 與 `<FAMILY>-B0R`，**形態不同 ⇒ 是通則非打地鼠**）；
① **未完全複現**（我 1 份 vs codex 3 份，差在 SPEC/TODO 標的 regex 寬窄）。

🔴 **grok 的方法有系統性盲區**：用 `git pickaxe` 查事故字串，但 `handoffs/*` 在 `.git/info/exclude`
⇒ 344 份 brief 只有 48 份在版控，它本來就查不到。

⇒ **B-38 修好後重收斂**，把「主委實測支持少數方」如實寫進收斂檔送三家戳記複驗。**不單方推翻 2:1。**

## 今日完成

| 票 | 結果 |
|---|---|
| `B-39` | E2b 四層 heading 路由；誤擋面 1236→292（-76%）；三家戳記＋閉合複驗 |
| `B-31` | 交件前自檢進 prompt 模板；9 findings→4 群集；三家戳記；**其誠實性要求逼出 B-38** |
| 測試 | 701 → **789 passed** |

## 🔴 今日新增的坑

| 坑 | 內容 |
|---|---|
| **push 假成功** | exit 0 不代表推上去，**一律 `git rev-parse HEAD origin/main` 比對兩值** |
| **code block 不安全** | `extract_heading_ids()` 無 code-fence 狀態機 ⇒ brief 引用一律用**行內反引號** |
| **`VERIFY:` 格式** | 冒號後**不得有空格**；exempt 類別只有 `typo\|doc-example\|migration-note\|template-drift\|tooling-blocked\|spec-ambiguity` |
| **`票 B-34` 必然發作** | review 雙家族 vs `stamps_check` 要三家 ⇒ **戳記輪一次派三家**可省一輪 |
| **戳記區的 `---`** | append `## 戳記` 時**不要**帶 `---`，會落進最後一個 finding 的 body 使 hash 不符 |
| **`票 B-15` 洞 B** | `--approver claude` 這種**合法參數值**也會觸發（第 4 次）⇒ 用 `main-agent` |
| **reconcile mode** | `reconcile_build.sh` 建 review 收斂須帶 `--mode review`，否則 `debt_clear` 拒銷 |

## 派工前置（每次必跑，單獨跑並讀輸出）

```
1. bash scripts/debt_ledger.sh --has-open
2. bash scripts/session_name_check.sh --session <名> --task-id <大寫同名>
3. bash scripts/doc_format_precheck.sh <brief>
4. python3 scripts/verification_claim_check.py --files <brief>
5. 上游收斂檔須三家 APPROVED
6. 🔴 grep 既有測試與規格（B-39 教訓）
7. 🔴 grep 既有票是否已涵蓋（B-38 教訓：差點與 SENTINEL 重複實作）
```

## 使用者判準（全域）

```
淨摩擦 = 新增每次成本 × 發生次數 − 省下重工 × 避免次數     為負才做；算不出來不得進執行序
```
forward-only｜優先找通則｜可讀性不是驗收標準｜鐵律直接做不包成問題｜
有信心自己做完的就做，不需詰問的不必 call 委員

## 🔴 工作區未 commit 的 B3 修補（**不要 commit**）

10 個 `M`（`scripts/_gate_lex.sh`／`extract_phase2_expected_flips.py`／`gate_check.sh`／
`tests/governance/fixtures/*` ×4／`tests/governance/test_gate_*.py` ×3）＋
`?? docs/GOVB0_FRICTION_AMENDMENTS.md`。保留至 B3R。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜中文路徑 `git -c core.quotepath=false`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`pytest tests/governance` 要 **258 秒**（789 tests）｜`git push` 必須 `run_in_background`（前景上限 120 秒）
