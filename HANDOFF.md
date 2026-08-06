# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-07 | **Branch**: main
**狀態**: `B-39` ✅ ／`B-31` 🟡 ／`B-38` 🟡（**核心殘留未解**）／`B-19` ⏸ 待收斂
**測試**: 701 → **795 passed**

## ▶ 接手第一件事

```
1. git rev-parse HEAD origin/main          # 兩值必須相同（push exit 0 不代表推上去）
2. bash scripts/debt_ledger.sh --has-open  # 應 rc=0
3. git status --short                       # 應恰為 B3 修補的 10 M + 1 ??（見文末）
```

## 🔴 下一步：`票 B-38` 的核心殘留（本輪未解，已具名）

**病**：修法只在**委員照做時**有效。未讀 prompt／截斷／模型未遵循 ⇒
`cx_run` 交件層仍接受 prose-only（`--single` 對 0 canonical ID 直接 PASS）
⇒ 病從「主委忘記寫」變成「委員沒有遵循」〔`CODEX-R1-P1-02`〕。

**修補的前置**：先解「**如何機械識別應有 findings 的產出**」。
主委初測「對 0-ID 產出改判 FAIL」影響 **1073/1418** 檔（76%），
但樣本含 `impl`／`stamp`／runlog（本無 canonical ID）⇒ **誤擋率未證，不得逕行改判**。

**碼證位置**：`cx_run.sh:379-400`（`_run_format_check_if_needed` 只呼叫 `--single`）、
`completeness_check.sh:1493-1506`（對 prose 直接 PASS）。

## 其他待辦（依序）

```
1. B-38 核心殘留（上述）
2. B-19 重收斂 ← B-38 的 sentinel 出路已通，現在可以做了
3. B-15（今日第 5 次發作）／B-29／B-16 擴充 A/B/C
4. 群集 ID 登記（併 B-26）→ B3R → B4-B7
```

### `票 B-19` 現況：裁定已取得，2:1 分歧，**主委實測支持少數方**

| | codex（少數） | composer／grok（多數） |
|---|---|---|
| 主張 | ①③做、②關閉改欄位設計、④併入錯誤訊息 | 三項全關、改走第四方向 |
| ③ 判準 | placeholder-aware ＋ 限 active 檔 → **2 真陽性 0 誤擋** | 粗判準 → 真陽性 0 |

主委獨立驗證：③ **複現**（134 檔命中 2，`<FAMILY>-V1` 與 `<FAMILY>-B0R`，形態不同 ⇒ 通則非打地鼠）；
① **未完全複現**（我 1 份 vs codex 3 份，差在 SPEC/TODO 標的 regex 寬窄）。
🔴 **grok 有系統性盲區**：用 `git pickaxe` 查，但 344 份 brief 只有 48 份在版控。

⇒ 重收斂時如實寫「主委實測支持少數方」，送三家戳記複驗，**不單方推翻**。

## 🔴 分歧判準（本日兩次用到，寫進收斂檔）

> **分歧時不看家族數量，看誰的碼證能證偽對方。**

- `B-38`：1:1，codex 勝——它用 **mutation 證明主委測試假綠**，composer 沒做。
- `B-19`：2:1，主委實測後支持少數方 codex——它的判準有 2 真陽性 0 誤擋。

## 今日完成

| 票 | 結果 |
|---|---|
| `B-39` | E2b 四層 heading 路由；誤擋 1236→292（-76%）；三家戳記＋閉合複驗 |
| `B-31` | 交件前自檢進 prompt 模板；三家戳記；**其誠實性要求逼出 B-38** |
| `B-38` | sentinel 出路已通（檢查器零改動）；**核心殘留未解，維持 OPEN** |

## 🔴 今日新增的坑（會再咬人）

| 坑 | 內容 |
|---|---|
| **push 假成功** | exit 0 不代表推上去 ⇒ **一律 `git rev-parse HEAD origin/main` 比對兩值** |
| **說明檔同步的驗證時機** | 判準看 **commit 時序** ⇒ 必須 **commit 後、push 前**驗，commit 前驗會漏 |
| **code block 不安全** | `extract_heading_ids()` 無 code-fence 狀態機 ⇒ brief 引用一律**行內反引號** |
| **`VERIFY:` 格式** | 冒號後**不得有空格**；exempt 只有 `typo\|doc-example\|migration-note\|template-drift\|tooling-blocked\|spec-ambiguity` |
| **`票 B-34` 必然發作** | review 雙家族 vs `stamps_check` 要三家 ⇒ **戳記輪一次派三家** |
| **戳記區的 `---`** | append `## 戳記` 時**不要**帶 `---`，會污染最後一個 finding 的 body hash |
| **`票 B-15` 洞 B** | 連 `--approver claude` 這種合法參數值都觸發（第 5 次）⇒ 用 `main-agent`；路徑含 `claude` 也會 ⇒ 改用 Write 工具建檔 |
| **reconcile mode** | 建 review 收斂須帶 `--mode review`，否則 `debt_clear` 拒銷 |
| **`grep -c` 疊 `\|\| echo 0`** | grep 找不到已輸出 `0`，再疊會變 `0\n0` ⇒ 數值比較炸 |
| **委員會在 repo 內留殘留檔** | 2026-08-07 codex 做 mutation 後留下 `tests/governance/test_zero_findings_sentinel.py.bak_mut`。**交件後務必 `git status --short` 比對 HANDOFF 清單**，多一個就查清（本次即靠此抓到） |

## 派工前置（每次必跑，單獨跑並讀輸出）

```
1. bash scripts/debt_ledger.sh --has-open
2. bash scripts/session_name_check.sh --session <名> --task-id <大寫同名>
3. bash scripts/doc_format_precheck.sh <brief>
4. python3 scripts/verification_claim_check.py --files <brief>
5. 上游收斂檔須三家 APPROVED
6. 🔴 grep 既有測試與規格（B-39 教訓：撞上不知情的行為契約，繞掉 90 分鐘）
7. 🔴 grep 既有票是否已涵蓋（B-38 教訓：差點與 GOV-NOFINDINGS-SENTINEL 重複實作）
```

## 使用者判準（全域）

```
淨摩擦 = 新增每次成本 × 發生次數 − 省下重工 × 避免次數   為負才做；算不出來不得進執行序
```
forward-only｜優先找通則｜可讀性不是驗收標準｜鐵律直接做不包成問題｜
**治理沒做好不能進主線**（2026-08-07 使用者定：治理正在教系統說謊，要先停掉）

## 🔴 工作區未 commit 的 B3 修補（**不要 commit**）

10 個 `M`（`scripts/_gate_lex.sh`／`extract_phase2_expected_flips.py`／`gate_check.sh`／
`tests/governance/fixtures/*` ×4／`tests/governance/test_gate_*.py` ×3）＋
`?? docs/GOVB0_FRICTION_AMENDMENTS.md`。保留至 B3R。

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜中文路徑 `git -c core.quotepath=false`｜
`rm`／`git clean` 在 deny，用 `mv` 到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`pytest tests/governance` 要 **261 秒**（795 tests）｜`git push` 必須 `run_in_background`
