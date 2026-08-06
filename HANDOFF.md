# Handoff

**Agent**: Claude(Opus 5) | **Time**: 2026-08-06 深夜 | **Branch**: main（`84e7479`，本地＝遠端）
**狀態**: ✅ `票 B-39` 實作完成並 push（782 passed）→ 待 grok 補戳記 → 下一步＝**第 1 批**

## ▶ 接手第一件事

1. `git rev-parse HEAD origin/main` — **兩值必須相同**（今日踩過：push exit code 0 但實際被拒）
2. `bash scripts/debt_ledger.sh --has-open` — 應 rc=0
3. 若 `handoffs/reconcile/20260806-govb39-b2-review-r1/synth.md` 缺 grok 戳記，
   跑 `bash scripts/reconcile_stamps_check.sh <該檔>` 確認，缺就補派（見下 `票 B-34`）

## 執行順序

```
1. 票 B-39   ✅ 完成（commit 1515827＋84e7479）
2. 第 1 批    ← 現在這裡。偵察已完成：handoffs/20260806-BATCH1-RECON.md
              B-19 → B-31 → B-38 → B-15 → B-29 → B-16 擴充 A/B/C
3. 群集 ID 登記（併 B-26）
4. B3R       詞法層重寫
5. B4 → B5 → B6 → B7
```

## 第 1 批：偵察已做完，開工可直接用

**`handoffs/20260806-BATCH1-RECON.md`** — 五張票的目標檔全部存在、既有測試已定位、
機制現況已實跑確認、依賴順序已初判。**開工前必讀**（B-39 就是漏了這步繞掉 90 分鐘）。

兩個已定位的低成本切入點：
- **B-31**：把「交件前自跑 `completeness_check --single`」從 brief 手寫移進 `cx_run.sh` prompt 模板。
  今日 R2 實驗證實有效（R1 兩家 format-failed → R2 一次全過）。**淨摩擦顯著為負。**
- **B-19**：`brief_conformance_check.sh` 實測只有 **6 個條件分支**，擴充項可用主委今日的 4 個 brief 錯誤當實證來源。

## 🔴 今日新增的坑（會再咬人）

| 坑 | 內容 |
|---|---|
| **push 假成功** | `git push` exit code 0 不代表推上去。**一律 `git rev-parse HEAD origin/main` 比對兩值** |
| **code block 不安全** | `extract_heading_ids()` 無 code-fence 狀態機 ⇒ code block 內行首 `#` 一樣被當 heading。**brief 的引用指示一律用行內反引號** |
| **`VERIFY:` 格式** | 冒號後**不得有空格**，接 `[A-Za-z0-9_.\-:]+`；用 finding ID 當 receipt id 會 fail。exempt 類別只有 `typo\|doc-example\|migration-note\|template-drift\|tooling-blocked\|spec-ambiguity` |
| **`票 B-34` 必然發作** | review 是雙家族，但 `reconcile_stamps_check` 要三家 ⇒ 每個 review 輪都要多派一輪求 grok 空戳記。今日第 2 次，已追加事故計數 |
| **戳記區的 `---`** | append `## 戳記` 時**不要**帶 `---` 分隔線，它會落進最後一個 finding 的 body 使 hash 不符 |

## 🔴 工作區有未 commit 的 B3 修補（**不要 commit**）

10 個 `M`（`scripts/_gate_lex.sh`、`scripts/extract_phase2_expected_flips.py`、
`scripts/gate_check.sh`、`tests/governance/fixtures/*` ×4、`tests/governance/test_gate_*.py` ×3）
＋ 1 個 `??`（`docs/GOVB0_FRICTION_AMENDMENTS.md`）。保留至 B3R。

## 使用者判準（全域）

```
淨摩擦 = 新增每次成本 × 發生次數 − 省下重工 × 避免次數     為負才做
```
以前和現在的**釘死不動**（forward-only）｜優先找通則，別逐洞開票｜
可讀性不是驗收標準｜有信心自己做完的就做，不需詰問的不必 call 委員｜
**鐵律直接做不包成問題**（雙家 review／三方戳記／閉合再驗證／gate 前置）

## 本日主委錯誤：同型 16 次

「驗了 A 就當作 B 也成立」。最嚴重的第 16 次：把**自己多寫一條 `---`** 造成的 hash 不符
歸因為「兩個工具定義不一致」，並據此廢掉一整輪委員債。
⇒ 對策已開票：**`票 B-16` 擴充 C**（宣稱的量詞範圍 > 實際驗證範圍 ⇒ 須帶 `COVERAGE:` 欄），
排在第 1 批，落地後這類會在寫檔當下被擋。

## 派工前置（每次必跑，單獨跑並讀輸出）

```
1. bash scripts/debt_ledger.sh --has-open
2. bash scripts/session_name_check.sh --session <名> --task-id <大寫同名>
3. bash scripts/doc_format_precheck.sh <brief>
4. python3 scripts/verification_claim_check.py --files <brief>
5. 上游收斂檔須三家 APPROVED
6. 🔴 **grep 既有測試與規格**（B-39 的教訓，本條今日新增）
```

## 坑（沿用）

`rc` 禁經 pipe｜禁 `cd <專案路徑>` 前綴｜中文路徑 `git -c core.quotepath=false`｜
`rm`／`git clean` 在 deny，用 `mv` 移到 `.claude/tmp/`｜commit 訊息用 `-F 檔案`｜
`pytest tests/governance` 要 **267 秒**（782 tests），`git push` 必須 `run_in_background`（前景上限 120 秒）
