# Handoff

**Agent**: Claude(Opus 5) | **Branch**: main | 實作＝主委自任（`implementer=claude`）；
討論／review／adversarial＝**codex+composer+grok 三家全員**

> 🔴 本檔超過 CLAUDE.md 之 ≤30 行規約，**結構上不可能達成**：下方「未修的活缺口」節是
> **機器輸入**（`governance-ticket-closure` 之導出來源），長度由未收案票數決定。
> 刪它會使 `test_e3_ticket_union_matches_key_rows` 轉紅（實測過）。修訂案待使用者裁定。

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序／批次狀態／票收案狀態 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 之三個 generated block |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md` |
| 給使用者的現況 | `白話說明/接下來要做什麼.md` |
| 委員名冊 | `scripts/governance_roles.json`＋`governance_families.json` |
| `B-49` as-built 落差與殘留 | `docs/GOV_B49_ASBUILT_DELTA.md` |

🔴 改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`；
本檔**不得手寫**票／批次的狀態字面值（偵測器 fail-closed，本 session 踩三次）。

# 🔴🔴🔴 接手第一件事：等使用者回答兩個問題

使用者 2026-08-12 指示：「**要做就做乾淨，不要用斷路器當理由又殘留**」、
「把 PUSH 卡住問題和 ASSERT 問題清乾淨」、「**然後交接寫明確做 B-25，然後才是站 5**」。
主委提出**四項一批做完**之方案，**使用者尚未答覆**：

**(a)** 四項一批（Phase A 實作＋B.1 實作＋錨點檢查＋89 行遷移），不再拆 —— 認可否？
**(b)** 第四項需改 `docs/GOVB1_INPUT_QUALITY_SPEC.md` 與 `..._TODO.md` 兩凍結檔內之
　　舊 ASSERT 行（**只改那些行、技術內容不動**，比照 `票 B-49` 作法）—— 授權否？
　　🔴 **若不授權**：交接須寫明「ASSERT 問題差最後一哩，卡在凍結檔授權」，
　　**不得寫成一張沒人會做的票**（使用者已明確反對該作法）。

## 已完成並 push（`origin/main`，0 筆待推）

- `票 B-49`：凍結出口補上、幽靈路徑 11→0、關票條件機械可驗（**狀態值見生成區塊**）
- **ASSERT 自鎖 T0 止血**（`53966e90`）：寫檔路徑零執行 ＋ 逐行 timeout ＋ `proc_guard.sh`
  實測 605s → 1s，fork 耗盡不再發生

## 未完成（本 session 最大失敗）

🔴 **PUSH 11 分鐘問題：一行程式碼都沒改。**
`docs/GOV_GATECHAIN_SPEC.md`（288 行／3 Task）已走 **8 輪** adversarial，
finding 數 13→16→17→10→10→12→16→19，**未收斂**。

**根因（實測分類）**：r6/r7/r8 之 finding 有 4／5／**8** 條屬同一型——
「改法寫了要求、驗證欄沒對應格」。**手工維持該配對必然漏，且配對數隨修補增加。**
⇒ 主委結論：**SPEC 已夠好到可實作**；再審是打磨文件記帳，不降低實作風險。
剩餘記帳問題在測試寫出來後自動消失（測試即驗證）。

**Phase A 實質內容只有約 30 行 shell**：把段 4（白話 1s）／段 5（fact-key 0s）＋
新增 G-7 預檢（`--only g7`，**必須帶此旗標**否則會跑全套 pytest）移到段 2（pytest 678s）之前；
失敗摘要以 `GOV-CHECK-FAILED:` 印在**最末**。`--fast` 同批重定義為「pytest 前所有便宜段」。

## 實測事實（勿重測，直接用）

- 全套 `pytest tests/governance` ≈ **678s／1521 passed**；最慢 26 項合計 276s（長尾，非單一元凶）
- 三條便宜閘：`g7=7s factkey=0s plaindocs=1s`，**合計 8s**
- 舊 ASSERT 文法：`grep -rlE "ASSERT .* THEN rc(=|!=)[0-9]+" docs/`＝**9 檔**、**89 行**；
  其中 `GOVB1_INPUT_QUALITY_SPEC.md`／`..._TODO.md` 兩凍結檔佔 **45 行**
- `ulimit -H -u` 本機**不能降**（`Invalid argument`）；只降 soft 必被子程序抬回
- **無 `setsid` 指令**；`set -m` 可使背景 job 自成 pgid，`kill -TERM -<pgid>` 實測連孫程序一併終止
- per-user process 上限 `ulimit -u`＝**1333**

## 🔴 未修的活缺口

> 🔴 **本節是機器輸入**：`governance-ticket-closure` 之導出集合＝本節 ∪
> backlog「2026-08-10 scope 缺口」節所提及之票號。增刪票號提及須同步 `scripts/fact_keys.json`。

- 🔴 `票 B-25`：**判準資料化整項未做**，卡在 `fact_keys` 之 `.rows[]|@tsv` 只支援平面列。
  三項殘留：①正向斷言擋不住「有 pointer 但旁邊另寫互斥判準」②引用已廢判準無機械偵測
  ③完整解未做。2026-08-12 併入兩條機械檢查提案：**同 Task 內互斥判準偵測**、
  **改法段之機制須有 FACT-RECEIPT**。🔴 **B-25 不在票狀態表內**（該表正是它的交付物）
  ⇒ 其殘留對機器隱形；使用者已指示「交接寫明確做 B-25」。
- `R-12`：`brief_conformance_check.sh` full path 不驗 EXPECTED-DELTA；OOE 通道救不了
- `R-13` Unicode 不可見碼點；`R-14` `b4-review-r2` 僅 2/3 戳記；`R-16`＝`票 B-55`
- `票 B-49`：四條具名殘留見 `docs/GOV_B49_ASBUILT_DELTA.md` §3
- `票 B-54`：戳記 64 位 hex 由委員手抄，曾掉字一次
- `B3R` 已進主樹但三家 review 未戳記 ⇒ 只能說「已交付、待戳記」
- `票 B-56`／`票 B-57`（優先序低）／`票 B-58`（前導空行是否為缺陷未判定）
- `票 B-59`（優先序高）：dispatch gate 判定式為黑名單列舉，**不得宣稱閘已完備**
- `票 B-60`：`review_quorum_check.sh:35` 家族清單硬編未讀 SoT
- `票 B-61`：`_role_gate.sh` 之 `known_only` 對未知家族靜默放行
- `票 B-15` 誤擋仍在（含 `for f in codex composer grok` 這類唯讀迴圈被家族名偵測誤擋）
- `票 B-50` 流程面永久標記為跳步；`票 B-31` 只能說「產出端已有檢查點」（`票 B-53` 落地前）
- 站 5 未修殘留：`CODEX-R3-P0-03`／`CODEX-R3-P1-04`／`gate_check.sh` audit 分類器未同步
- 另有兩條空心探針不在 `LEGACY_PROBE_DEBT` 內（`test_mutation_g5_g6_empty_extract_fails`／
  `test_mutation_removing_selfcheck_case_turns_red`）⇒ `gov_check` 全跑必紅（pre-push 用
  `--no-probe` 跳過故不擋推送）。**既有債**，pre-B49 基準實測同樣紅。刻意不加進具名排除清單。
- `R-15`：`scripts/governance_families.json` 不可 commit
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**`（`run_receipts/` 除外）不得 commit
- 卡頓偵測器錯誤歸因：`settings.json` 之 `ts_stamp.sh OUT`（`:184`）早於
  `doc_format_precheck`（`:197`）⇒ hook 執行時間被記成「Claude 生成慢」。屬使用者設定檔，需其同意

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **推送前必跑 8 秒快閘**：`govb1_final_gate.sh --only g7` ＋ `gen_fact_key_blocks.sh --check`
  ＋ `plain_docs_sync_check.sh`。本 session 全套跑 9 次＝100.7 分，其中約 44 分可避免。
- 🔴 **push 失敗先 `grep -E "✗|FAIL|FACTKEY" <push.log>`，禁直接重跑套件**——
  log 有 1600+ 行且已含失敗原因；本 session 兩次只 `tail -3` 就重跑，白花 22 分鐘。
- 🔴 **G-7／F5 用 endpoint 淨差**：commit **前**是綠的（檔還沒進範圍），一 commit 才現形
  ⇒ **commit 之後必須重驗**。本 session 頭尾各踩一次。
- 🔴 **反向驗證才算數**（移除判定 ⇒ 對應斷言須轉紅）；**前必先 commit**——
  `git clone --local` 只取已提交內容（曾因此白驗一輪）。
- 🔴 **實測 > 假設**：本 session 三輪審查（`setsid`／`ulimit`）全因主委未實跑即寫入 SPEC。
  **量測時 pattern 須一致**（曾以 `rc=` 算檔數、`rc(=|!=)` 算行數 ⇒ 誤報 10 檔，實為 9）。
- 🔴 **不以家數表決，以碼證定**（本 epic 三次「兩家一種說法、一家附碼證」，皆採後者）。
- 🔴 **同一支腳本不得並行跑多份**——曾三份 `template_check` 併發導致 fork 耗盡（上限 1333）。
- 🔴 fact-key 註記**不得含日期**；改 `fact_keys.json` 後 `factkey_clean`／`factkey_drifted`
  兩 fixture 皆須用 `GOVB1_FACTKEY_ROOT=<目錄>` 重生成，drifted 須維持「恰一列不同」。
- 🔴 `handoffs/run_receipts/` 進 commit 須帶 `Governance-Scope: out-of-epic` trailer，
  且 **trailer 必須在最後一段**（git 只解析最末段）。
- 🔴 閘會把含家族名的**讀取指令與 commit 訊息**當成派工 ⇒ 訊息一律用 Write 工具寫檔再 `-F`。
- 🔴 禁 `cd <專案路徑>` 前綴、禁 `sed -i`、禁 `rm`（用 `mv` 到 `.claude/tmp/`）、
  禁 `python3 - <<'PY'` heredoc；改檔一律用 Edit／Write。
