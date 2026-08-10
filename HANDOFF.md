# Handoff

REF:handoffs/reconcile/20260810-govb1-x-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b10-review-r2/synth.md
REF:handoffs/reconcile/20260810-govb1-b9-review-r1/synth.md
REF:handoffs/reconcile/20260810-govb1-b8-review-r1/synth.md

🔴 **`REF:` 只准列「已戳記」之 reconcile——所有列。** 派工前 `bash scripts/reconcile_stamps_check.sh <檔>` 驗 rc=0。
本 session 另有四份已戳記收斂檔（站 2.5／2.6／2.7 前半），見下表，未列入 `REF:` 以免本檔過長。

**Agent**: Claude(Opus 5) | **Time**: 2026-08-10 | **Branch**: main | 實作端＝主委自任；review＝codex+composer

## 🔴 狀態一律看唯一來源，本檔不重述

| 事實 | 唯一來源 |
|---|---|
| 施工順序 | `docs/GOVERNANCE_EXECUTION_ORDER.md` 的 `governance-execution-order` block |
| 批次狀態 | 同檔 `governance-batch-status` block（**機械產物，手改會被擋**） |
| 票收案狀態＋對外不得宣稱 | 同檔 `governance-ticket-closure` block |
| 票的內容 | `handoffs/20260801-GOV-AMEND-BACKLOG.md`（53 張） |
| 給使用者的現況 | `白話說明/接下來要做什麼.md`／`白話說明/治理待辦總覽.md` |
| 摩擦統計現值 | `bash scripts/friction_tally.sh --by-event`／`--field-presence`（**數字不寫死**） |

🔴 **上述 block 一律不得手改**：改 `scripts/fact_keys.json` 後跑 `bash scripts/gen_fact_key_blocks.sh --write`。

## 🔴 接手第一件事：**站 2.7 後半**（序 `036`）

### 確切內容（出處 `handoffs/reconcile/20260809-govb1-b4-review-r2/synth.md:95-107`）

1. **`scripts/dispatch.sh:84` 是真缺口（兩家同判）**：缺 `--brief` 即應拒發 token（TODO `T-1.3-N1`）。
   繞過面已由 composer 窮舉——mint dispatch token 之路徑**僅** `gate.sh dispatch`
   （`dispatch.sh`／`committee_run.sh` 皆轉呼、`cx_run.sh` 不 mint）。
2. **TODO `:822` 之字面驗收在現行實作下不成立**：full path 未強制 `EXPECTED-DELTA`；
   已由 `test_full_path_does_not_yet_enforce_expected_delta` 凍結為具名行為（非假綠）。

### 🔴 硬阻塞（動工前必須先解，否則必撞）

掛上 full path 會使 `_B45_HARNESS` 之 minimal impl brief 轉紅——codex 實測 141 tests 中 **6 fail**、
全為缺 `EXPECTED-DELTA`；composer 實測 `rolegate-impl` `full_rc=0`／`only_rc=2`。
而該五檔 epic 期間**禁改**、`g7` scope 亦未 allow。
⇒ **非純實作題**：要嘛先取得「解除 harness 凍結」之裁決，要嘛設計不動那五檔的替代強制點。
**須先開 consult 輪由兩家共識決，不得直接動碼**（`票 B-51`：偏離凍結宣告須先取得裁決）。

🔴 **禁宣稱階段 1 已閉合強制**——`review-r2` 收斂檔明載，codex 之 `ASSUMPTIONS_VERIFIED` 亦未如此宣稱。

> 🔴 本節刻意不寫批次識別碼＋狀態值於同一行——主委 2026-08-10 在此處被**自己建的偵測器**擋下一次
> （`HANDOFF.md:26` 與 `:29`），該檔在 `status_scope` 內。這是機制正常運作。

## ✅ 本 session 已交付（2026-08-10，皆取得兩家 `RECONCILE-STAMP APPROVED`）

| 站 | 票 | 收斂檔（`reconcile_stamps_check` 皆 rc=0） | 審查量 | 🔴 未閉合 |
|---|---|---|---|---|
| 2.5 | `B-25` | `…/20260810-govb25-x-review-r6/synth.md` | 7 輪 33 條 | 八條殘留，含「判準資料化」整項未做 |
| 2.6 | `B-37` | `…/20260810-govb37-x-review-r5/synth.md` | 5 輪 18 條 | 六條殘留，含**票級統計**與**強制機制**兩項未交付 |
| 2.7 前半 | — | `…/20260807-govb1-b1-review-r6/synth.md`、`…/20260809-govb1-b4-review-r4/synth.md` | 1 輪 | 後半見上 |

**兩票皆不得宣稱閉合。** 殘留逐條見 backlog 對應節。
🔴 兩家於 2.7 前半明確確認：`b4-review-r4` **僅涵蓋階段 1**，蓋章**不等於**該批次整體完成。

## 🔴 未修的活缺口

- `gate_check` 對真派工放行：process substitution／`xargs -n 1`／`env FOO=bar`／動態賦值／絕對路徑 `bash -c` ⇒ GOVB0 `B4`
- `票 B-15` 誤擋在 `B7` 之後仍存在（`printf`／`find`／`ls`／`gate.sh` 自身）⇒ GOVB0 `B4` Task 2.3/2.4
- `B3R` 的 **O(n) scanner 未交付**（`CODEX-R8-P1-03`）⇒ 不得宣稱達標
- `票 B-50` 流程面**永久標記為跳步**；形態①④ 未做
- `票 B-31` 對外**不得說「強制」**，只能說「產出端已有檢查點」（`票 B-53` 落地前）
- `plain_docs_sync_check.sh` 的 catch-all 回空字串 ⇒ **新增說明檔預設不受監看**
- 票號抽取器**內嵌於測試檔**（新增 `scripts/` 檔會撞 G-7 除非帶 OOE）⇒ 見 `docs/GOV_B25_SCOPE_AMENDMENT.md` §4
- `R-15`：`scripts/governance_families.json` 不可 commit ⇒ ambient M
- `.claude/gate/*.log`、`docs/GOVB0_FRICTION_AMENDMENTS.md`、`handoffs/**` 不得 commit

## ⚠ 操作紀律（踩過的坑，一律照做）

- 🔴 **`docs/` 與新增 `scripts/` 檔皆不在 manifest** ⇒ commit 須帶 `Governance-Scope: out-of-epic` trailer，收尾跑 `--only g7`。
- 🔴 **改一個事實前先 `grep -rn` 掃全部副本**。
- 🔴 **背景任務的 exit code ＝ 指令鏈最後一個指令的 rc**；推完用 `git rev-list --count origin/main..HEAD` 實查。
- 🔴 **`git push` 用 harness 的 `run_in_background`，不得用 shell `&`**（會隨工具呼叫結束被砍）。
- 🔴 **改 `scripts/fact_keys.json` 須同步兩份 fixture**（clean/drifted；drifted 保留單列竄改，兩份行數須相同）。
- 🔴 **BSD awk 的 `-v` 值不接受換行**（本 epic 犯三次）⇒ 多行值一律經**檔案**餵入。
- 🔴 **awk 無 regex 型別**：`f($0, /re/)` 會先求值成 `0`／`1` 再傳入，**不報錯**。樣式一律以字串傳入 `match()`。
- 🔴 **token 邊界不得切片後重判**：`s=substr(...)` 丟失左側前文 ⇒ `B3RB3R` 誤抽。用絕對位移。
- 🔴 **mutation 錨點須唯一**：新增含同字串之函式會讓 `replace(...,1)` 打錯位置，測試轉紅但原因是錨點失準。
- 🔴 **可構造出可重現反例者＝缺陷，不得寫成「上界」**；**自陳未測攻擊面時不得附自己的嚴重度判定**。
- 🔴 **兩家分歧看碼證不數人頭**；零 findings 屬「未觀察到」，不能推翻附探針的 findings。
- 🔴 **散文契約補不完**：同類邊界連兩輪被打穿時，改「參考實作＋差分 fixture」當契約。
  出處＝`handoffs/reconcile/20260810-govb37-x-review-r3/synth.md`「方法論轉向」節；
  其效果由 r4 codex 複驗（`…-r4/synth.md`：該類 finding 於下一輪歸零）。
- 🔴 **「我跑過了」≠「有機制保證」**：人工 probe 過的契約沒有測試釘住，未來會無聲退回（`CODEX-R5-P1-04`）。
- 🔴 **`$( )` 內禁用 `case`**（macOS bash 3.2）；`rc` 禁經 pipe；改檔一律用 Edit/Write，禁 `sed -i`／heredoc。
- 全套 `pytest tests/governance -q` **≈470 秒 / 1373 passed**（2026-08-10 實測）⇒ 丟背景，跑完 `bash scripts/restore_golden_inventory.sh`。
- 銷帳前確認 `sources.lock` 是 review 模式；session 命名 `<YYYYMMDD>-<epic>-<batch>-<kind>-r<N>`，未分批用 `x`。
- stamp 輪產出為散文無 canonical ID ⇒ 收集節點必失敗，走 `no-findings-expected` 銷帳（`票 B-52`，已發作七次）。
- `grok` 額度封鎖 ⇒ 委員＝codex＋composer（使用者 2026-08-10 確認）。
