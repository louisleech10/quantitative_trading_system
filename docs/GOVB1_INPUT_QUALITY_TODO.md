# 第 1 批 — 派工輸入品質與機制自咬修復 TODO

**版本**：v1 DRAFT｜**基於 SPEC**：`docs/GOVB1_INPUT_QUALITY_SPEC.md`（三家 APPROVED 定版）
**授權收斂**：`handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md`
（`reconcile_stamps_check` rc=0，`sha256:b7393dff3bb4fe01f68cd91e0fa917c2ebed274a7719e3ca9b5195d30bdaab99`）
**日期**：2026-08-07｜**起草**：Claude 主委（依 `ORCH:61`／`:190`，TODO 一律主委起草）

---

## §0 全域規則與約束（執行端讀完即可遵守，不必回讀 SPEC）

### 0.1 從憲法提取（本任務相關者）

- **解耦**：本批**只動 `scripts/`＋`tests/governance/`**，不觸及 `momentum/`／`api/`／`frontend/`。
  收尾須 `bash ./scripts/check_decoupling.sh` **無新增紅**（既有紅不計）。
- **Logging**：本批腳本一律 `echo … >&2` 輸出錯誤，**hot loop 不 log**。
- **Error 分類**：檔案缺失／格式不符 ＝ **non-retryable**，一律 fail-closed（rc≠0），
  **禁靜默放行**。範例：`[ -f "${f}" ] || { echo "ERROR: 缺 ${f}" >&2; exit 1; }`

### 0.2 🔴 全域禁令（違反即為 BLOCKING，不論實作於哪一層）

🔴 **本表的「機械驗收」欄於 2026-08-07 全面改寫**〔`CODEX-R7-P1-03`：原 G-2／G-3／G-5／G-6／G-7
**五條的驗收欄不是可直接執行且可判定的檢查**〕。現行每條皆為**可貼上就跑**的命令，
並由 `scripts/govb1_final_gate.sh` 一次驗完（見 §B `GATE-FINAL`）。

| # | 禁令 | 出處 | 機械驗收 |
|---|---|---|---|
| G-1 | **禁止任何使 SPEC `C-2` 表中 `C-2` 表中期望 `rc==0` 之列由 `0` 變為非 `0` 的改動**（`--single`／`--lock`／`cx_run`／新腳本／新 hook 皆同） | SPEC Task 4.1 不可做 | `pytest tests/governance/test_completeness_idlike_fp.py -q` 全綠 **且** `git diff --stat tests/governance/test_completeness_idlike_fp.py` 輸出為空 |
| G-2 | 🔴 **consumer 腳本內禁止字面量分母** | SPEC `C-1` | `bash scripts/govb1_final_gate.sh --only g2` rc=0。🔴 **判準見 §0.1b（唯一來源），本欄不重述**〔沿革與已廢各階見 §0.1b「已廢」欄；`CODEX-R27-P0-01`：本欄原於註解中**複述已廢判準文字**並含第二個 pointer ⇒ 仍是競爭敘述，已刪〕 |
| G-3 | **上線即 fail-closed，禁先以警告模式上線**。不得把驗過的功能藏在預設關閉開關後 | SPEC §R（使用者定死條文） | `grep -rnE 'WARN_ONLY\|--dry-run\|DISABLED_BY_DEFAULT\|SKIP_.*=1' scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/gen_govb1_contract_matrix.sh` **零命中** |
| G-4 | **不得觸碰** `scripts/gen_govflow_manifest.sh:68-95` 的 `phase_of()` | SPEC `C-3` | `git diff --stat scripts/gen_govflow_manifest.sh` 輸出為空 |
| G-5 | **不得修改** `docs/GOV_DISPATCH_FLOW_FIX_SPEC.md` 行為表既有列 | SPEC `C-3` | 🔴 **資料列集合雜湊 vs base commit**〔`CODEX-R8-P0-05`：原基準檔 `scripts/govb1_frozen_hashes.txt` **不在任何 Task 的新建清單、亦無生成命令** ⇒ final gate 無法自洽建立；另原寫死行號 `139-163` 本身即凍結數，行號一漂即失效〕：`bash scripts/govb1_final_gate.sh --only g5` rc=0——以 Task 0.1 的 `_behavior_rows()` **現讀**資料列（**非行號區段**），與 `git show ${base_commit}:` 之同一抽取結果比對雜湊。**抽取結果為空 ⇒ 立即 FAIL**（空對空恆綠） |
| G-6 | **已完成票禁止重做**：`票 B-32` 已 DONE。⚠️ 其票名描述的是**病**不是修法，實際修法＝**按 `brief-kind` 條件注入**，照票名施工會做反 | SPEC `C-5b` | 🔴 **函式區段雜湊 vs base commit**〔`CODEX-R8-P0-06`：原 `git diff -U0 \| grep -c '<函式名>'` **只在 hunk 含宣告列時才命中** ⇒ 只改函式 body 者靜默放行〕：`bash scripts/govb1_final_gate.sh --only g6` rc=0。**不得改用「整檔 `git diff` 為空」**——`scripts/cx_run.sh` 本批確由 Task 1.1（`_bk` case）與 Task 4.3（`_run_format_check_if_needed`）修改，整檔門會恆紅 |
| G-7 | **`檔案` 三類語義**：`只讀` 類**不授予修改權**。把應修改檔標成「只讀」以規避 scope 即 scope 違規 | SPEC `C-4b`＋`CODEX-R5-P3-00` | 🔴 **腳本驗，非人審**〔`COMPOSER-R7-P2-01`＋`CODEX-R8-P0-07`＋`COMPOSER-R8-P2-01`：原實作三缺陷——①抓全檔反引號路徑（含「只讀」欄）②拿全量 `git diff` 當 actual（含動工前既有 dirty）③`${actual}` 未加引號會斷詞〕：`bash scripts/govb1_final_gate.sh --only g7` rc=0——🔴 **commit-range G-7**〔`x-consult-r10` W-1 定案；**U-3**：本欄原寫「乾淨 detached worktree／`git worktree remove`」＝上一版設計，與 §B 偽碼**直接矛盾**，實作者可能依此表採已作廢路徑〕：oracle 作用域＝**`base..HEAD` 之 immutable commit range**（**不建任何 worktree**），decl 來源＝**凍結 manifest**（非現讀散文），**allow 僅宣告集合（`baseline_dirty` allowlist 已廢除，旁路消失）**，未 commit 之 ambient dirty 從不進入 actual，全程加引號 |
| G-8 | **不得改動** `handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md` 附錄區 | SPEC `C-3` 第三列〔`GROK-R7-P2-03`：原 TODO 只覆蓋前兩列〕 | `bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md` **rc=0**（附錄區被改 ⇒ body-hash 變 ⇒ 戳記失效 ⇒ 天然可驗） |

### 0.1a 🔴 三種編號的對應（**本批唯一對應表**）

🔴 **命名地雷**：批次寫 `B1`、票寫 `B-19`——**只差一個連字號**。本表之外提及編號時，
**批次一律寫「批 N」、票一律寫「票 B-NN」**，不得只寫 `B1`／`B19`。

| 層 | 形態 | 是什麼 |
|---|---|---|
| 票 | `票 B-NN` | **要修的病**（backlog 的最小單位） |
| Task | `Task N.M` | **一件工**（一個 Task 修某張票的一部分） |
| 批 | `批 N`（原寫 `B1`） | **一次派工的範圍**（含 1–2 個 Task；依賴與同檔 writer 決定） |

| 批 | Task | 歸屬票 | 對應之確定性 |
|---|---|---|---|
| 批 1 | 0.1 | — | **無**（契約基線，不對單一票） |
| 批 2 | 1.1 | `票 B-19` | 內文提及，**待確認** |
| 批 3 | 1.2 | `票 B-19` ③ | ✔ 標題宣告 |
| 批 3 | 1.4 | `票 B-29` | 內文提及，**待確認** |
| 批 4 | 1.3 | `票 B-29` | ✔ 標題宣告 |
| 批 5 | 1.5 | `票 B-16` 擴充 | ✔ 標題宣告 |
| 批 6 | 2.1 | **未標註** | 內文之 `票 B-23` 係**交叉引用非歸屬** |
| 批 6 | 2.2 | **未標註** | 內文之 `票 B-29` 同上 |
| 批 7 | 3.1 | **未標註** | 內文之 `票 B-6` 同上 |
| 批 7 | 3.2 | **未標註** | 內文之 `票 B-38` 疑為歸屬，**待確認** |
| 批 8 | 4.1 | — | **無** |
| 批 9 | 4.2 | **未標註** | 內文之 `票 B-38` 疑為歸屬，**待確認** |
| 批 10 | 4.3 | `票 B-31` | ✔ 標題宣告 |

🔴 **本表之出生事故（2026-08-07，使用者質問）**：使用者指出白話說明三份文件
各用不同層級編號（`Task 0.1`／`B1`／`B-19`）而無對應。實查技術版**同病且更嚴重**——
**13 個 Task 只有 4 個在標題宣告歸屬票**，其餘只能從內文猜。

🔴 **主委不手填未標註者**：內文第一個出現的票號**可能是交叉引用而非歸屬**
（`Task 2.1` 之 `票 B-23`、`Task 3.1` 之 `票 B-6` 皆屬此），
**「只看誰沒歸類就填空」正是主委今日兩次對帳配反之根因**。
⇒ **6 個「未標註／待確認」須由實作端於各 Task 開工時具名補上**，補法＝在該 Task 標題宣告，
不得由主委事後推測。

### 0.1b 🔴 §0.1 判準單一來源（**唯一可陳述判準之處；他處一律 pointer**）

〔`CODEX-R25-P0-01`＋`GROK-R25-P0-01`：判準散落於 G-* 表、偽碼註解、B.4 三處，
主委每次換判準只改其一 ⇒ **同型漂移已 12 次**。**本節之外任何位置陳述判準即為違規**，
由 adversarial／stamp 檢查。〕

| 判準 | **現行**定義（唯一來源） | 已廢（**不得**再被引用為現行） |
|---|---|---|
| **G-2 consumer 集合** | `scripts/govb1_scope.manifest` 之 **`consumer <path>` 動詞明列**；須為 `allow` 子集，否則 fail-closed。路徑級、受 hash-lock | ①`_g2_regions` markdown 區域 ②glob ∪ 字面 grep ③`_CHECKS` 之 `role` 欄 ④白名單 ∩ 副檔名 |
| **G-7 `actual`** | `git diff --name-only --diff-filter=ACMRD "$(_base)" HEAD`（commit-range） | ①主樹全量 diff ②decl 複製進乾淨 worktree 後之差集 |
| **G-7 `decl`（allow）** | `_g7_policy`：凍結 manifest，`deny` 優先於 `allow` | 現讀 TODO 之反引號路徑 |
| **`_plan` 之 `UNRESOLVED`** | **僅**檢查 `_CHECKS` 所列**函式是否存在**。**不是** consumer closure；動態 command edge 之脫離為**具名殘留**（B.4#6） | 「plan 導出 consumer 閉包」 |

### 0.3 防假綠（三條，缺一不可）

1. **不得放寬既有測試斷言**。驗收時 `git diff` 既有測試檔，任何斷言被刪或放寬 ⇒ FAIL。
2. 🔴 **`completeness --lock` 一律在 `--mode review` 下驗**——`discovery` 判準較弱。
   機械檢查：斷言 `sources.lock` 的 `mode` 欄 == `review`。
3. **誤擋率 receipt** 依 §0.4 定義，缺 receipt ⇒ 不 merge。

### 0.4 誤擋率 receipt 定義（SPEC §V-FP，逐字沿用）

| 項 | 定義 |
|---|---|
| 分母 | 該檢查**實際掃描**的全部檔案數（現跑導出，禁凍結） |
| 分子 | 人工標註真值後判定為 false-positive 的檔案數 |
| 標註者 | 實作端標註 → 至少一非實作者家族複核；分歧交第三家裁決 |
| 抽樣 | 分母 **≤100 全量標註**；**>100 則隨機抽 ≥100** 並報 Wilson 95% CI |
| 報告 | 🔴 **報區間不報點估計**。禁寫「誤擋率 0%」，須寫「95% CI [x%, y%]」 |
| 門檻 | 區間上界 ≤ **5%**（0-FP 時 n=100 → `3.8416/103.8416` = 3.70% ✅；n=50 → 7.14% ❌） |

### 0.5 驗收一律寫「執行後狀態」而非「補救動作的 rc」（`票 B-24` 紀律）

範例：不得只寫「跑 `restore_golden_inventory.sh` rc=0」，須寫「`git status --short tests/golden/` 輸出為空」。

---

## §B 批次執行策略

🔴 **排序判準（`x-stamp-r21` K-3；使用者 2026-08-07 指正）**：
依賴與同檔 writer 衝突為**必要非充分**條件——它們只排除不合法順序，
**合法順序仍有多個**。主委原按 Phase 編號填入＝**等同未排序**。
⇒ 新增**淨摩擦**欄（使用者公式：`新增每次成本 × 發生次數 − 省下重工 × 避免次數`）；
**空欄者不得進執行序**。
🔴 **「填」之定義＝序數帶＋一行下界依據，非絕對值**〔`x-consult-r12` J-3，grok 裁定、composer 同判：
要求假精確絕對值會使全表停擺；本 repo 無 per-round token 計量〕。
與使用者「算不出來不得進執行序」**不衝突**——序數帶仍算得出來；
禁的是**無依據之空白**與**假精確**（後者另受 `feedback_no_metric_gaming` 約束）。

⚠️ **本表淨摩擦欄目前全空 ⇒ 現行順序尚未取得執行資格**（composer 判：屬**暫停非死鎖**）。
🔴 **三家已裁定之目標順序**（`x-consult-r12`，MODIFY）：
`B1 → B6 → B2 → B3 → B4 → B5 → B7 → B8 → B9 → B10`（B5 可與 B2–B4 並行）。
**惟前移有四項前置，未完成前不得改本表順序**：
①消解 SPEC 標頭與本表之依賴閘互斥（`GROK` BLOCKING）②釐清 `B7→B1` 依賴（`CODEX-R29-P1-03`）
③**B6 須擴充 schema 或新增第二 fact-key**——現行 `.rows[]|@tsv` **不適用**表格型判準
（`CODEX-R29-P0-01`＋`COMPOSER-R29-P0-01`，主委原假設**已證偽**）
④每批可稽核之摩擦 receipt。

| Batch | 含 Task | 依賴 | 合併理由 | 規模 | 淨摩擦（**空欄不得執行**） |
|---|---|---|---|---|---|
| **B1** | 0.1 | 無 | 契約基線＋全部 fixture 一次建立；後續每批都要用 | 中 |
| **B2** | 1.1 | B1 | lifecycle matrix 是 1.3／4.2 的宿主，須先獨占建立（single-writer） | 中 |
| **B3** | 1.2, 1.4 | B2 | 同掛 `brief_conformance_check.sh`，同一份解析器，分批做會漂移 | 中 |
| **B4** | 1.3 | B2, B3 | 寫 `govflow_lifecycle.json` 的 `expected_delta` 節；須待 B3 的解析器定型 | 小 |
| **B5** | 1.5 | B1 | 掛 `template_check.sh`，與 B2–B4 無交集，可與之並行 | 中 |
| **B6** | 2.1, 2.2 | B1 | 生成器與其強制層必須同批，否則有生成器無人驗 | 中 |
| **B7** | 3.1, 3.2 | 無 | 同掛 `gate_check.sh` 同一判定函式，分批必衝突 | 中 |
| **B8** | 4.1 | B2 | 讀 lifecycle matrix 的 kind 定義 | 中 |
| **B9** | 4.2 | B2, B8 | 寫 `zero_findings_contract` 節；須待 4.1 的分類判準定型 | 中 |
| **B10** | 4.3 | B9 | 消費 4.2 的 fixture 與契約 | 小 |

### 批次間 Gate

| Gate | 條件 | 驗證命令 |
|---|---|---|
| **GATE-B1** | `T-0.1-*` 全綠 ＋ fixture **逐名**存在（非數量） | `pytest tests/governance/test_govb1_contract_matrix.py -q`；`bash scripts/gen_govb1_contract_matrix.sh --check-fixtures`（由 SPEC 現讀清單逐項 `test -e`，缺一 rc≠0） |
| **GATE-B2** | `T-1.1-*` 全綠且 `jq -r 'keys[]' scripts/govflow_lifecycle.json` 非空 | `pytest tests/governance/test_govb1_lifecycle_matrix.py -q` |
| **GATE-B3** | `T-1.2-*`／`T-1.4-*` 全綠 ＋ 兩份誤擋率 receipt | `pytest tests/governance/test_govb1_brief_id_pattern.py tests/governance/test_govb1_factverified.py -q` |
| **GATE-B4** | `T-1.3-*` 全綠且 `jq` 頂層 key 為 B2 結果之超集 | `pytest tests/governance/test_govb1_expected_delta.py -q` |
| **GATE-B5** | `T-1.5-*` 全綠 ＋ 誤擋率 receipt | `pytest tests/governance/test_govb1_template_check_ext.py -q` |
| **GATE-B6** | `T-2.1-*`／`T-2.2-*` 全綠且連跑 3 次生成 sha256 相同 | `pytest tests/governance/test_govb1_factkey_gen.py tests/governance/test_govb1_factkey_hook.py -q` |
| **GATE-B7** | `T-3.1-*`／`T-3.2-*` 全綠 **且** `pytest tests/governance/test_gate_decision.py -q` 全綠（既有語料不得放寬） | 兩者皆跑 |
| **GATE-B8** | `T-4.1-*` 全綠 ＋ 誤擋率 receipt ＋ **三入口矩陣逐格 rc 不變** | `pytest tests/governance/test_govb1_findings_kind.py tests/governance/test_govb1_zeroid_no_regression.py -q` |
| **GATE-B9** | `T-4.2-*` 全綠 ＋ G-1 全域禁令驗收（`git diff --stat` 為空） | `pytest tests/governance/test_govb1_zero_findings.py -q` |
| **GATE-B10** | `T-4.3-*` 全綠 | `pytest tests/governance/test_govb1_b31_recovery.py -q` |
| **GATE-FINAL** | §0.2 **八條**全域禁令 ＋ `pytest tests/governance -q` ＋ `bash -n scripts/*.sh` | 🔴 **`bash scripts/govb1_final_gate.sh`**（新建，見下）——**任一條非零即 FAIL**；不得以人審 checklist 代替〔`COMPOSER-R7-P0-02`＋`GROK-R7-P2-01`＋`CODEX-R7-P1-04`〕。🔴 **`pytest`／`bash -n` 為 `_g0_tests`／`_g0_syntax` 兩條，在腳本內**〔`CODEX-R8-P0-08`：原「條件」欄宣稱要跑，腳本 `_g1.._g8` 清單裡卻沒有 ⇒ 宣稱與實作不符〕 |

### 🔴 `scripts/govb1_final_gate.sh`（Task 0.1 建立，收尾執行）

逐條跑 §0.2 的 G-1～G-8，**每條都是可執行命令且輸出 pass/fail**：

**用法**：`bash scripts/govb1_final_gate.sh [--only <檢查名>]`。
`--only` 傳未知名稱 ⇒ **rc=2**（不得靜默零檢查通過）。

```sh
set -u
_base() { grep -m1 '^base_commit:' scripts/govb1_frozen_hashes.txt | awk '{print $2}'; }
_h()    { shasum -a 256 | cut -c1-12; }

# ── 抽取器（三條共用；各自附非空守衛，空對空恆綠是假綠）────────────────
# 🔴 **本段不陳述任何判準；判準唯一來源＝§0.1b**
#    〔`CODEX-R26-P0-01`＋`GROK-R26-P0-01`：主委新增 §0.1b 後**未刪本段之競爭敘述**
#     ⇒ **第 13 次同型，且犯在「修該病」的修法裡**。演進沿革亦移入 §0.1b「已廢」欄。〕
#    `--print-plan` 與正常執行共用 `_rows` 表，其職責**限於** plan 完整性（`UNRESOLVED` 偵測），
#    **不再參與 G-2 定義域判定**。
_g2_consumers() {   # stdout: consumer 檔清單（一行一檔）；禁人手列舉
  _plan="$(bash scripts/govb1_final_gate.sh --print-plan)" || return 1
  # 🔴 `UNRESOLVED` 之**職責已收窄且具名**〔`CODEX-R24-P0-02`：G-2 定義域改由 manifest 導出後，
  #    plan 的 `UNRESOLVED` **不再是 consumer closure**——它只檢查 `_CHECKS` 所列**函式是否存在**。
  #    **動態 command edge 仍可脫離定義域**，此為**具名殘留**（見 B.4#6），
  #    緩解＝新增 consumer 必須在 manifest 明列 `consumer`，否則不進 G-2 亦不受 hash-lock 保護。〕
  printf '%s\n' "${_plan}" | grep -q '^UNRESOLVED' \
    && { echo "G-2 FAIL: plan 有檢查函式不存在（非 consumer closure，見 B.4#6）" >&2; return 1; }
  # 🔴 **判準敘述唯一來源＝§0.1；本處不重述判準**〔`CODEX-R25-P0-01`＋`GROK-R25-P0-01`：
  #    主委補新判準時不清舊敘述，**已第 12 次**（副檔名／`_plan()`／`role` 欄之舊句與新判準並存
  #    ⇒ 實作者會採互斥 oracle）。**對策不是再逐處修，是讓判準只存在於一處**——
  #    其餘位置一律 pointer，**結構上不可能漂移**。〕
  # 🔴 判準唯一來源＝**§0.1b**；本函式只實作，不陳述判準
  : "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
  _cons="$(awk '$1=="consumer"{print $2}' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u)"
  _allow="$(_g7_policy)" || return 1
  # consumer 必為 allow 之子集；否則 manifest 自相矛盾 ⇒ fail-closed
  _bad="$(comm -23 <(printf '%s\n' "${_cons}") <(printf '%s\n' "${_allow}"))"
  [ -z "${_bad}" ] || { printf 'G-2 FAIL: consumer 不在 allow 內:\n%s\n' "${_bad}" >&2; return 1; }
  printf '%s\n' "${_cons}"
}
_G2_UNITS='份|列|個 fixture|個 Task'   # 量詞集合唯一定義處；本 TODO 正文不重貼此 regex
# 字面量分母＝數字緊鄰量詞。分母**必須**來自 $( ) / wc / 現讀抽取函式，不得寫死。
_frozen_hits() { grep -nE "[0-9]+[[:space:]]*(${_G2_UNITS})"; }

_behavior_rows() { awk '/^[[:space:]]*\| `.*` \| (\*\*)?rc==/ { print }'; }   # 與 Task 0.1 同一 pattern
_g6_func()       { awk '/^_maybe_register_stamp_output\(\)/ { f=1 } f { print } f && /^}/ { exit }'; }
# 🔴 decl 來源＝**凍結 manifest**，不再現讀散文〔`x-consult-r10` W-2〕
#    前一版 `_g7_decl()` 從本 TODO 現讀反引號路徑，兩個病：
#      ①TODO 自身被擴寬即**自我授權**（`CODEX-R16-P1-04`）
#      ②不分正面宣告與負面禁令 ⇒「`govb1_baseline_dirty.txt` **已廢除**、不得建立」
#        竟被抽成 allow，執行端真的建立反而放行（Z-5）
#    🔴 grok：「僅改差集公式而不改 decl 來源 ⇒ Z-5／自我授權仍在」。
#    ⇒ 改為封閉、可機械導出之白名單；**散文寫什麼都不影響 oracle**。
#    〔使用者 2026-08-07 判準：文字類問題一律白名單機械卡，不在散文上耗——列舉不完〕
_g7_policy() {   # stdout: 本批 scope 白名單（一行一筆；目錄以 `/` 結尾）
  : "${GOVB1_SCOPE_MANIFEST:=scripts/govb1_scope.manifest}"
  [ -s "${GOVB1_SCOPE_MANIFEST}" ] \
    || { echo "G-7 FAIL: 缺 scope manifest ${GOVB1_SCOPE_MANIFEST}（fail-closed）" >&2; return 1; }
  # 🔴 hash-lock〔CODEX-R17-P0-02〕：manifest 於**動工前**凍結，其後被改即 fail-closed，
  #    否則「凍結白名單」退化成另一個現讀來源。lock 值由 Task 0.1 寫入 frozen_hashes。
  _want="$(grep -m1 '^scope_manifest:' scripts/govb1_frozen_hashes.txt | awk '{print $2}')"
  _got="$(shasum -a 256 "${GOVB1_SCOPE_MANIFEST}" | cut -c1-12)"
  [ -n "${_want}" ] && [ "${_want}" = "${_got}" ] \
    || { echo "G-7 FAIL: scope manifest 雜湊不符（want=${_want} got=${_got}）" >&2; return 1; }
  # manifest 為**純資料**：`allow <path>` / `deny <path>`；deny 優先且不得被 allow 覆蓋
  awk '$1=="deny"{d[$2]=1} $1=="allow"{a[$2]=1}
       END{ for (p in a) if (!(p in d)) print p }' "${GOVB1_SCOPE_MANIFEST}" | LC_ALL=C sort -u
}
_nonempty() { [ -n "$2" ] || { echo "$1 FAIL: 抽取結果為空（pattern 失效）" >&2; return 1; }; }

# ── 兩條全域（GATE-FINAL 條件欄宣稱者，須真的在腳本裡）──────────────
_g0_tests()  { venv/bin/python -m pytest tests/governance -q >/dev/null; }
_g0_syntax() { s=0; for f in scripts/*.sh; do bash -n "$f" || s=1; done; return "$s"; }

# ── 八條禁令 ──────────────────────────────────────────────────
_g1() { venv/bin/python -m pytest tests/governance/test_completeness_idlike_fp.py -q >/dev/null \
        && [ -z "$(git diff --stat tests/governance/test_completeness_idlike_fp.py)" ]; }
# 🔴 非空守衛保留〔CODEX-R13-P0-01：抽不到 consumer 與 consumer 乾淨同樣 rc=0＝空轉假綠〕
_g2() { c="$(_g2_consumers)"; _nonempty G-2 "${c}" || return 1
        # shellcheck disable=SC2086
        ! _frozen_hits ${c} | grep -q .; }
_g3() { ! grep -rnqE 'WARN_ONLY|--dry-run|DISABLED_BY_DEFAULT|SKIP_.*=1' \
        scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/gen_govb1_contract_matrix.sh; }
_g4() { [ -z "$(git diff --stat scripts/gen_govflow_manifest.sh)" ]; }
_g5() { b="$(git show "$(_base):docs/GOV_DISPATCH_FLOW_FIX_SPEC.md" | _behavior_rows)"
        w="$(_behavior_rows < docs/GOV_DISPATCH_FLOW_FIX_SPEC.md)"
        _nonempty G-5 "${b}" && _nonempty G-5 "${w}" || return 1
        [ "$(printf '%s\n' "${b}" | _h)" = "$(printf '%s\n' "${w}" | _h)" ]; }
_g6() { b="$(git show "$(_base):scripts/cx_run.sh" | _g6_func)"
        w="$(_g6_func < scripts/cx_run.sh)"
        _nonempty G-6 "${b}" && _nonempty G-6 "${w}" || return 1
        [ "$(printf '%s\n' "${b}" | _h)" = "$(printf '%s\n' "${w}" | _h)" ]; }
# 🔴 commit-range G-7〔Y-2 三家收斂 → `x-consult-r10` W-1 定案〕：
#    oracle 作用域＝**`base..HEAD` 之 immutable commit range**〔V-4：本註解原寫
#    「乾淨 detached worktree」＝上一版設計，**已不適用**，現行不建任何 worktree〕。
#    `baseline_dirty` **已移除**——無 allowlist 可灌，「先弄髒再進 allowlist」旁路消失。
#    主樹其餘 dirty（B3 十檔／HANDOFF／audit.log）**從不進入 actual**。
#    🔴 「工作樹 dirty 即 fail-closed」**不得**施加於主樹：三家一致指出那只是把
#    「恆紅」從差集移到前置檢查，與被推翻的 baseline 方案同構。
# 🔴 commit-range G-7〔`x-consult-r10` W-1：三家獨立給出同一設計〕
#    前一版把 decl 路徑 cp 進乾淨 WT 再算差集 ⇒ **由構造 actual ⊆ decl ⇒ extra 恆空** ⇒ oracle 空洞
#    （Z-1，三家 BLOCKING）。改以 **immutable commit range** 取 actual：
#      · 未 commit 之 ambient dirty（B3 十檔／HANDOFF／audit.log）**不在 range 內** ⇒ 不恆紅
#      · commit 內任何未宣告路徑**必然**出現在 actual ⇒ **恆空由構造消失**
# 🔴 **唯一**的 path-vs-decl 比對點〔V-1 三家一致：守衛用 `grep -qxF` 全字、主體用前綴涵蓋
#    ⇒ 同一份 decl 兩套語義，目錄條目下的檔案不觸發守衛。**兩處必須共用本函式。**〕
_g7_covered() {   # $1=path $2=decl(多行) → rc=0 表示被涵蓋
  while IFS= read -r d; do
    [ -n "${d}" ] || continue
    case "${d}" in
      */) case "$1" in "${d}"*) return 0 ;; esac ;;   # 目錄：尾 `/` 即路徑邊界，不誤放行 govb1x/
      *)  [ "$1" = "${d}" ] && return 0 ;;
    esac
  done <<EOF
$2
EOF
  return 1
}
_g7() { decl="$(_g7_policy)" || return 1; _nonempty G-7 "${decl}" || return 1
        # 🔴 交付形態守衛〔CODEX-R17-P0-01〕：未提交即交付 ⇒ **不得**當成 PASS
        #    🔴 用 `-z` NUL 分隔逐筆讀〔U-2：`cut -c4-` 雖修好含空白路徑，但 rename 行
        #       `R  old.md -> new.md` 會得整串 ⇒ 比對必不命中 ⇒ **守衛對 rename 全盲**。
        #       `-z` 下 rename 之 old／new 為**兩個獨立 NUL 欄位**，天然拆開。
        #       **禁 `awk '{print $NF}'`**（V-2：含空白路徑被 $NF 截斷）、**禁 `cut -c4-`**（本項）。〕
        git status --porcelain=v1 --untracked-files=all -z \
          | tr '\0' '\n' | sed -n 's/^[A-Z? ][A-Z? ] //p; s/^\(.*\)$/\1/p' | sort -u \
          | while IFS= read -r p; do
          [ -n "${p}" ] || continue
          _g7_covered "${p}" "${decl}" && { echo "UNCOMMITTED:${p}"; break; }
        done > "${TMPD:=/tmp}/g7_uncommitted.$$"
        if [ -s "${TMPD}/g7_uncommitted.$$" ]; then
          echo "G-7 FAIL: UNSUPPORTED-DELIVERY-SHAPE — 本批宣告路徑仍未 commit" >&2
          cat "${TMPD}/g7_uncommitted.$$" >&2; return 1
        fi
        # 🔴 ancestor 驗證：base 須為 HEAD 之祖先，否則 range 語義不成立
        git merge-base --is-ancestor "$(_base)" HEAD \
          || { echo "G-7 FAIL: base_commit 非 HEAD 祖先（range 無意義）" >&2; return 1; }
        # `--diff-filter` 納入刪除〔W-3〕；range 端點皆為 commit，非工作樹
        actual="$(git diff --name-only --diff-filter=ACMRD "$(_base)" HEAD | LC_ALL=C sort -u)"
        # 目錄型宣告以**前綴涵蓋**判定〔W-3〕——與守衛**共用** `_g7_covered`，禁各寫一套〔V-1〕
        extra=""
        while IFS= read -r p; do
          [ -n "${p}" ] || continue
          _g7_covered "${p}" "${decl}" || extra="${extra}${p}"$'\n'
        done <<EOF
${actual}
EOF
        [ -z "${extra}" ] || { printf 'G-7 FAIL: 未宣告即修改:\n%s\n' "${extra}" >&2; return 1; }; }
_g8() { bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md >/dev/null; }

# 🔴 **檢查本身資料化**——單一表格即唯一真相源〔`x-stamp-r13` T-1 三家一致裁定〕
#
#    病史（三次同型，逐次記錄）：
#      ①`_g2_regions`：在 markdown 文法上列舉「驗收區」⇒ 第 N 類永遠列不完
#      ②`--print-plan` v1：`type|sed` 掃**原始碼**猜路徑 ⇒ 變數組路徑抓不到
#      ③`_plan()` v2：**人手寫的 case 登記表** ⇒ 忘記登記即靜默脫離定義域；
#        且**正常模式直接迭代〔歷史變數 `_ALL`，現已刪除〕、根本沒消費 `_plan()`** ⇒ 兩條路徑必漂移
#
#    ⇒ **本版把「檢查」本身變成資料**：每列即一個檢查。
#      **執行與 `--print-plan` 迭代同一張表** ⇒ 無第二份登記表可漂移；
#      **不在表中即無法執行**（構造上強制，非靠紀律記得同步）。
#
#    欄位：`name | files | fn`（多檔以空白分隔）
#    🔴 **`role` 欄已刪除**〔`CODEX-R22-P1-02` → `CODEX-R23-P0-01` 兩輪演進：
#      ①原標 `SCRIPTS_GLOB|consumer` ⇒ 全部 `scripts/*.sh` 流回 G-2，`_g4`／`_g6` 之 `data` 失效
#      ②改標 `data` 後仍不閉合——**`role` 是「列」的屬性，不是「路徑」的屬性**，
#        同一路徑出現在兩列即分類不明，可被雙重帶回〕
#    ⇒ **`_CHECKS` 的 `files` 欄只服務 plan 完整性（`UNRESOLVED` 偵測），不參與 G-2 定義域判定。**
#      🔴 **G-2 定義域之判準見 §0.1b（唯一來源），本段不陳述**
#      〔`CODEX-R28-P0-01`：本段前次更正**在說明裡逐字抄了已廢階之原文** ⇒ **更正說明本身即一份副本**，
#       **第 15 次同型，且連兩次犯在「修此病」的修法裡**。
#       ⇒ **通則（適用全檔）：引用已廢判準一律只寫「已廢階 N（見 §0.1b）」，
#         禁複述其內容**——內容只存在於 §0.1b 之「已廢」欄。〕
_CHECKS='
_g0_tests|tests/governance|_g0_tests
_g0_syntax|SCRIPTS_GLOB|_g0_syntax
_g1|tests/governance/test_completeness_idlike_fp.py|_g1
_g2|scripts/govb1_final_gate.sh|_g2
_g3|scripts/gen_fact_key_blocks.sh scripts/findings_kind_classify.sh scripts/gen_govb1_contract_matrix.sh|_g3
_g4|scripts/gen_govflow_manifest.sh|_g4
_g5|docs/GOV_DISPATCH_FLOW_FIX_SPEC.md|_g5
_g6|scripts/cx_run.sh|_g6
_g7|scripts/govb1_scope.manifest scripts/govb1_frozen_hashes.txt|_g7
_g8|handoffs/reconcile/20260807-govb1-x-consult-r1/synth.md|_g8
'
_rows() { printf '%s\n' "${_CHECKS}" | grep -v '^[[:space:]]*$'; }
_plan() {   # stdout: `FILE\t<path>` 或 `UNRESOLVED\t<name>\t<reason>`
  _rows | while IFS='|' read -r name files fn; do
    type "${fn}" >/dev/null 2>&1 \
      || { printf 'UNRESOLVED\t%s\t函式 %s 不存在\n' "${name}" "${fn}"; continue; }
    for f in ${files}; do
      if [ "${f}" = "SCRIPTS_GLOB" ]; then
        for s in scripts/*.sh; do printf 'FILE\t%s\n' "${s}"; done
      else
        printf 'FILE\t%s\n' "${f}"
      fi
    done
  done
}
if [ "${1:-}" = "--print-plan" ]; then _plan; exit 0; fi
# 🔴 **執行端與 plan 迭代同一張 `_rows`**〔T-1：前版正常模式直接迭代 `_ALL`、
#    根本沒消費 `_plan()` ⇒「兩者消費同一份」是空頭宣稱〕。`_ALL` 變數**已刪除**。
_names() { _rows | cut -d'|' -f1; }
if [ "${1:-}" = "--only" ]; then
  _names | grep -qx "${2:-}" \
    || { echo "ERROR: 未知檢查 '${2:-}'（可用：$(_names | tr '\n' ' ')）" >&2; exit 2; }
  sel="${2}"
else sel=""; fi

# plan 若有任何 UNRESOLVED，**執行前即 fail-closed**（不得只在 G-2 檢查時才發現）
_plan | grep -q '^UNRESOLVED' && { _plan | grep '^UNRESOLVED' >&2; exit 2; }

rc=0; ran=0
for g in $(_names); do
  [ -z "${sel}" ] || [ "${g}" = "${sel}" ] || continue
  fn="$(_rows | awk -F'|' -v n="${g}" '$1==n{print $4}')"
  ran=$(( ran + 1 ))
  if "${fn}"; then echo "PASS ${g}"; else echo "FAIL ${g}" >&2; rc=1; fi
done
[ "${ran}" -gt 0 ] || { echo "ERROR: 零檢查執行（空轉）" >&2; exit 2; }
exit "${rc}"
```

### 🔴 各 Batch GATE 的 receipts／雜湊／diff 具體命令〔`CODEX-R7-P1-04`〕

| GATE | 原「條件」中不可執行者 | 具體命令 |
|---|---|---|
| `GATE-B3`／`B5`／`B8` | 「＋誤擋率 receipt」 | `: "${TASK_ID:?TASK_ID 未帶入}"; R=handoffs/receipts/govb1-fp-${TASK_ID}.md; test -s "$R" && grep -qE '95% CI \[[0-9.]+%, [0-9.]+%\]' "$R" && awk -F'[][,%]' '/95% CI/{exit ($4+0)>5}' "$R"`（🔴 `${TASK_ID:?}` 守衛：未帶入 ⇒ **立即非零**，不得因變數為空而拼出可存在的路徑） |
| `GATE-B6` | 「連跑 3 次生成 sha256 相同」 | 🔴 **逐次檢查 generator rc**〔`CODEX-R8-P0-08`：原 pipeline 未檢查前段 rc，`false \| shasum` 三輪仍得 `count=1`、rc=0 ⇒ **生成器失敗會假綠**〕：`D=$(mktemp -d); for i in 1 2 3; do bash scripts/gen_fact_key_blocks.sh > "$D/$i" \|\| exit 1; done; test "$(shasum -a 256 "$D"/1 "$D"/2 "$D"/3 \| awk '{print $1}' \| sort -u \| wc -l)" -eq 1` |
| `GATE-B8` | 「三入口矩陣逐格 rc 不變」 | `pytest tests/governance/test_govb1_zeroid_no_regression.py -q`（9 格各一用例） |
| `GATE-B9` | 「G-1 全域禁令驗收」 | `bash scripts/govb1_final_gate.sh` 的 `_g1` 單條 |

### 🔴 序列約束（同 Batch 內共寫同一檔者，**必須依序、禁平行**）

〔`CODEX-R7-P1-02`＋`COMPOSER-R7-P1-03`＋`GROK-R7-P1-04` 三家獨立命中：
原 TODO 僅以散文約定「同批同一執行端依序」，**若派工系統平行兩個 Task 則無機械門可擋**〕

| Batch | 共寫檔 | 強制順序 | 機械驗收 |
|---|---|---|---|
| B3 | `scripts/brief_conformance_check.sh` | **1.2 → 1.4** | `git log --oneline -n 2 -- scripts/brief_conformance_check.sh` 須見**兩個獨立 commit**；合併為單一 commit ⇒ FAIL |
| B6 | 無共寫（2.1 建、2.2 只呼叫） | 2.1 → 2.2 | 依賴序即可 |
| B7 | `scripts/gate_check.sh` | **3.1 → 3.2**（3.2 沿用 3.1 的 `_strip_quoted()`） | 同 B3，須見兩個獨立 commit |

🔴 **派工紀律**：**每次派工 prompt 只含一個 Task**，不得把同批兩 Task 併成一次 prompt。

**誠實邊界**：此為**擋意外不防蓄意**——執行端仍可自行平行處理。具名接受，不在本批解。

### 🔴 動工前基準（`G-5`／`G-6`／`G-7` 的共同前置；Task 0.1 產出）

〔`CODEX-R8-P0-05`＋`CODEX-R8-P0-07`：原 `scripts/govb1_frozen_hashes.txt` **無人建立**
⇒ `_g5` 恆紅；原 `_g7` 拿**全量** `git diff` 當 actual ⇒ 動工前既有 dirty 檔（`HANDOFF.md`／
`.claude/gate/audit.log`／B3 修補的既有 `M` 檔）恆被誤判為「未宣告即修改」。**兩者皆須基準錨定。**〕

| 檔 | 內容 | 生成命令（Task 0.1，**動工前第一個動作**） |
|---|---|---|
| `scripts/govb1_frozen_hashes.txt` | `base_commit: <sha>` ＋ 🔴 `scope_manifest: <hash12>` | `printf 'base_commit: %s\n' "$(git rev-parse HEAD)" > scripts/govb1_frozen_hashes.txt`<br>🔴 `printf 'scope_manifest: %s\n' "$(shasum -a 256 scripts/govb1_scope.manifest \| cut -c1-12)" >> scripts/govb1_frozen_hashes.txt`〔**U-4**：`_g7_policy` 讀該欄，但原表**只生成 `base_commit:`** ⇒ 照 TODO 施工必然 fail-closed 恆紅。**與 `CODEX-R8-P0-05` 同型，第二次**〕 |
| `scripts/govb1_scope.manifest` | `allow <path>`／`deny <path>` 兩欄純資料 | 由 SPEC §V-ASSERT 與各 Task「修改∪新建」建立後**凍結**；建立順序須**先於**上列 hash 生成 |

🔴 **漂移 lint（`T-0.1-F5`）**〔`CODEX-R20-P0-02`／`x-stamp-r13` T-3：hash-lock 只證明
**檔案未被改**，**不能**證明 allow／deny 集合與 Task 檔案欄一致 ⇒ stale／漏列／多列可被凍結後通過〕：
比對 `scripts/govb1_scope.manifest` 之 `allow` 集合與各 Task「修改 ∪ 新建」欄，**不一致即 FAIL**。

🔴 **權責分明，不得混淆**：`scripts/govb1_scope.manifest` 仍是 `_g7` 之**唯一授權來源**
——**不因本 lint 而改回現讀 TODO**；lint 只在兩者漂移時**擋下**，**不參與 allow 判定**。

🔴 **`scripts/govb1_baseline_dirty.txt` 已廢除**〔`x-stamp-r9` X-2＋`x-consult-r7` Y-2〕——
其存在即為旁路（動工前先弄髒 ⇒ 永久免檢）。**〔U-3：本句原寫「Sandbox G-7 在乾淨 worktree 內驗證」
＝上一版設計，已由 `x-consult-r10` W-1 改為 commit-range〕** commit-range G-7 只看 `base..HEAD`，
**根本不存在需要扣除的既有 dirty**，故無需 allowlist。

### 🔴 交付語義（`x-consult-r10` W-1；**本批之交付形態定義**）

**本批交付物＝commit，不是工作樹狀態。** 執行端完成後**須先 commit 本批變更**再跑 `GATE-FINAL`；
`actual` 取自 `base..HEAD` 之 immutable commit range。

| 仍然成立的既有紀律 | 與本節如何並存 |
|---|---|
| **先不要 push** | commit ≠ push；`GATE-FINAL` 只讀本地 range |
| **B3 十檔不得 commit**（留至 `B3R`） | 「commit 本批變更」指**本批 tip**；B3 十檔**不屬本批**，維持未 commit，且因此**不進 `actual`** |
| `HANDOFF.md`／`.claude/gate/audit.log` 長期 dirty | 未 commit ⇒ **不在 range 內** ⇒ 不使 G-7 恆紅 |

🔴 **Z-3 之 clone fallback 已因本設計而不需要**：commit-range G-7 與 `_g5`／`_g6`（`git show`）
**皆不建立 worktree**，故無 `.git/worktrees` 寫入需求。原「執行者約束」表僅保留為**歷史說明**（見下），
其 fallback 條文**作廢**——不得再寫「worktree 失敗則 clone」這種無對應偽碼的宣稱。

### 執行者約束（**已作廢，保留為歷史說明**）

〔`CODEX-R15-P0-02`：codex 實跑 `git worktree add --detach` → **rc=128**
`.git/worktrees … Operation not permitted`；composer 亦 `Permission denied`；
grok 與**主委自跑皆 rc=0**。⇒ 差異來自**執行端沙箱**，非 repo 或閘門。
**判準（本輪確立）**：執行端回報的 rc 是「該沙箱內的 rc」，不等於本 repo 的 rc。〕

🔴 **下表為歷史說明，其要求已全數作廢**〔V-4 三家一致：主委宣告 Z-3 作廢時只改偽碼與一處散文，
未機械全掃殘留 ⇒ 執行端依本表施工會做出不存在的驗收。**本 session 第 7 次「原則修了實例沒修」**〕。
**現行 `_g2_consumers`／`_g5`／`_g6`／`_g7` 皆不建立 worktree、不 clone**（三家實查確認）。

| 〔歷史〕執行者 | 〔歷史〕worktree 路徑 | 〔歷史〕處置 |
|---|---|---|
| main-agent（Claude） | 可用（實跑 add／remove 皆 rc=0） | **預設路徑** |
| 受沙箱限制之執行端 | `.git/worktrees` 不可寫 ⇒ 失敗 | 改用 fallback |

〔歷史〕fallback 條文（**已作廢，不得施工**）：原寫「先試 worktree、失敗則 `git clone --no-local`」。
🔴 **現行設計不需要任何 sandbox**——`actual` 取自 `base..HEAD` commit range，
`_g5`／`_g6` 用 `git show`，皆不寫 `.git/worktrees`。

**為何錨定 base commit 而非工作區**：工作區可被本批自身的改動汙染 ⇒ 基準隨改動一起漂，
比對恆真（**同一形態的空對空恆綠**）。`git show ${base_commit}:` 取的是**不可被本批改動影響**的版本。

驗收見 Task 0.1 之 `T-0.1-F2`：`grep -c '^base_commit: [0-9a-f]\{40\}$'` **== 1**；
`git cat-file -e "$(_base)^{commit}"` rc=0（sha 真實存在）。

### 每 Batch 派工 prompt（可直接複製）

> **前置狀態**：`bash scripts/debt_ledger.sh --has-open` rc=0；上一 Batch 的 GATE 全綠。
> **Task 列表**：見下方對應 Phase。
> **驗證命令**：見該 Batch 的 GATE 行。
> **硬性要求**：①每個新測試須 mutation 自證（revert 修法→轉紅），提交前實跑貼 rc
> ②不放寬既有斷言換綠 ③先不要 push ④§0.2 全域禁令**逐條**遵守（條數以該表現讀為準）。

---

## Phase 0 — 契約基線（目標：把 SPEC 的散文要求變成 repo 內的機器產物與 fixture）

**完成後系統狀態**：`scripts/gen_govb1_contract_matrix.sh` 可現跑產出契約矩陣；
`tests/governance/fixtures/govb1/` 下**全部** fixture 就位（清單由 SPEC §V-ASSERT 現讀），後續各 Batch 皆可直接引用。

### Task 0.1 — 契約矩陣生成器 ＋ 全部 fixture

- **SPEC ref**：Task 0.1／`C-1`／`C-2`／§V-ASSERT　**目標**：產出可現跑的契約基線與全部驗收 fixture。
- **輸入**：`docs/GOV_DISPATCH_FLOW_FIX_SPEC.md`（唯讀契約來源）
  **輸出**：`scripts/gen_govb1_contract_matrix.sh`（stdout 為 `path|contract_lines|touched|evidence` 四欄）
- **實作要點**：
  1. 現跑導出 docs 清單（**禁寫死份數**）：
     ```sh
     docs_list="$(grep -rln 'doc_format_precheck\|completeness_check\|cx_run' docs/*.md | sort)"
     ```
  2. 行為表逐列現讀（**禁寫死列數**）——只取 `| \`…\` | rc==N | **rc==M** |` 形態列。
     🔴 **前導空白必須納入 pattern**〔`GROK-R7-P0-01`：主委原偽碼 `/^\| \`.*\` \| rc==/`
     **對真實表格 0 行命中**，因表格行縮排於 bullet 之下；修正後 19 行命中〕：
     ```sh
     _behavior_rows() {
       # 🔴 前導空白 **與** 粗體 rc 皆須納入：`^\|` 漏縮排（0 命中）、
       #    無 `(\*\*)?` 會漏掉粗體 `**rc==**` 者（部分命中，`>0` 斷言假綠）
       awk '/^[[:space:]]*\| `.*` \| (\*\*)?rc==/ { print }' docs/GOV_DISPATCH_FLOW_FIX_SPEC.md
     }
     ```
     🔴 **非空斷言**（擋同型空轉）：`_behavior_rows | wc -l` **必須 > 0**，
     為 0 ⇒ 立即 `exit 1` 並印 `ERROR: 行為表現讀 0 行，pattern 已失效`。
     **不得只靠偽碼正確——測試層須獨立驗非空。**
  3. 函式簽名：`emit_matrix() -> stdout`；`emit_behavior_rows() -> stdout`；
     `main(): emit_matrix; emit_behavior_rows`。**無參數、無副作用、輸出決定性**（固定排序）。
  4. fixture 建立：**Task 0.1 為全部 fixture 的唯一 owner**
     〔`GROK-R7-P2-02`：原 TODO 讓 0.1 宣稱建「全部」、其餘 7 個 Task 又各自標「新建」同一路徑
     ⇒ **雙重所有權**，與 `GATE-B1`「0.1 後 fixture 齊」語義衝突。
     現改為**其餘 Task 一律列「只讀」**〕。
     🔴 **清單由 SPEC §V-ASSERT 現讀，禁寫死數量**〔`GROK-R7-P1-01`＋`CODEX-R7-P1-05`：
     主委三處寫死「14」，SPEC 實列 **16**，加 Task 1.5 的 2 個 ⇒ 實需 **≥18**〕：
     ```sh
     _fixture_names() {
       sed -n '/fixture 清單/,/^```$/p' docs/GOVB1_INPUT_QUALITY_SPEC.md \
         | grep -oE '[a-z0-9_]+\.(md|json)|factkey_[a-z]+/' | sort -u
     }
     ```
     再併入 Task 1.5 需要的 `spec_assert_pending.md`／`spec_func_missing.md`。
     內容須**足以驅動對應斷言**（例：`brief_id_b0r.md` 須含 `brief-kind:` 行 ＋ `<FAMILY>-B0R-P1-01` 樣板）。
  5. 🔴 **動工前基準（本 Task 的第一個動作，先於任何寫檔）**：依 §B「動工前基準」表產出
     `scripts/govb1_frozen_hashes.txt`（**僅此一檔**；`baseline_dirty` 已廢除，見 §B）。
     **順序不可顛倒**——先動檔再取基準，會把本批自身的改動寫進基準，`_g7` 從此永遠放行。
  6. 🔴 **`scripts/govb1_final_gate.sh`**：實作 §B 之偽碼（`_g0_tests`／`_g0_syntax`／`_g1`～`_g8`
     ＋ `--only` 分派）。**`--only` 傳未知名稱須 rc=2**，不得靜默零檢查通過。
- **修改檔案**｜**修改**：無｜
  **新建**：`scripts/gen_govb1_contract_matrix.sh`、`tests/governance/test_govb1_contract_matrix.py`、
  `tests/governance/fixtures/govb1/`（**全部 fixture 的唯一 owner**；清單由 SPEC §V-ASSERT **現讀**，
  併入 Task 1.5 需要的 2 項；**禁寫死數量**）、
  🔴 `scripts/govb1_final_gate.sh`、`scripts/govb1_frozen_hashes.txt`、
  `scripts/govb1_scope.manifest`（**G-7 之凍結白名單；純資料 `allow`／`deny` 兩欄，
  `deny` 優先且不得被 `allow` 覆蓋**——`x-consult-r10` W-2）
  〔`CODEX-R8-P0-05`：後者原**只被 `_g5` 引用、不在任何 Task 的新建清單**，
  `govb1_final_gate.sh` 亦只在 §B 散文提「Task 0.1 建立」而未進本欄 ⇒ **final gate 無法自洽建立**。
  🔴 `scripts/govb1_baseline_dirty.txt` **已廢除**（Y-2），不得建立〕｜
  **只讀**：`docs/GOV_DISPATCH_FLOW_FIX_SPEC.md`、`scripts/cx_run.sh`、`docs/GOVB1_INPUT_QUALITY_SPEC.md`、
  `docs/GOVB1_INPUT_QUALITY_TODO.md`（`T-0.1-F4` 之 CCS 反例注入標的；**注入後須還原**）
  **既有 caller**：新建無 caller。
- **不可做**：不得把矩陣內容硬編碼進測試；不得為讓行數對齊而排除任何一份 docs；
  **不得寫死份數或列數**（G-2）。
- **邊界**：
  ①`docs/` 新增一份含關鍵字的檔 ⇒ 矩陣列數 +1，且 `T-0.1-C1` 轉紅（提示須更新）；
  ②`GOV_DISPATCH_FLOW_FIX_SPEC.md` 行為表被改列 ⇒ `T-0.1-C2` rc=1；
  ③`docs/` 為空（極端）⇒ rc=0 且輸出僅表頭，**不得 fail**。
- **風險緩解**：G-5（不得修改行為表既有列）——本 Task 只讀。
- **存活至**：Phase 4 完工後仍保留（作為後續批次的契約基線與 fixture 來源）。
- **覆蓋風險**：無。後續 Phase 只讀本產出，不刪不覆蓋。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-0.1-C1`：`bash scripts/gen_govb1_contract_matrix.sh | grep -c '^docs/'`
    **==** `grep -rln 'doc_format_precheck\|completeness_check\|cx_run' docs/*.md | wc -l`（兩者同時現跑）
  - `T-0.1-C2`：行為表**每一列**的 `expected_rc` 與現讀值逐列相符；改任一列 ⇒ 轉紅
  - `T-0.1-C3`（**非空斷言，擋空轉**）：`_behavior_rows | wc -l` **> 0**；為 0 ⇒ FAIL
  - `T-0.1-F1`（**逐名存在性，非數量**）〔`GROK-R7-P1-01`：`ls | wc -l ≥ N` 數量對不代表項目對，本身即可假綠〕：
    由 SPEC §V-ASSERT **現讀**清單，逐項 `test -e tests/governance/fixtures/govb1/<name>`，**缺一即 FAIL**
  - `T-0.1-F2`（**動工前基準自洽**）：
    `test -s scripts/govb1_frozen_hashes.txt` rc=0；
    `grep -c '^base_commit: [0-9a-f]\{40\}$' scripts/govb1_frozen_hashes.txt` **== 1**；
    🔴 `grep -c '^scope_manifest: [0-9a-f]\{12\}$' scripts/govb1_frozen_hashes.txt` **== 1**〔U-4〕；
    🔴 `bash scripts/govb1_final_gate.sh --only g7` rc=0（證明 `_g7_policy` 之 hash-lock 真的對得上，
    非只驗欄位存在）；
    `git cat-file -e "$(_base)^{commit}"` rc=0；
    `test -e scripts/govb1_baseline_dirty.txt` **rc≠0**（該檔已廢除，存在即為旁路殘留）
  - 🔴 `T-0.1-F3`（**commit-range G-7 可執行**）〔Y-2；**V-4 改**：原要求
    `git worktree list` **== 1**，但現行設計已不建 worktree，該驗收無標的〕：
    `bash scripts/govb1_final_gate.sh --only g7` rc=0；
    `git status --porcelain | wc -l` 與執行前**相同**（主樹未被 oracle 汙染）；
    `bash scripts/govb1_final_gate.sh --print-plan` rc=0 且輸出非空（`_g2_consumers` 之閉包來源）
  - 🔴 `T-0.1-F4`（**G-2 定義域為 consumer 閉包**）〔Y-1〕：
    在 `docs/GOVB1_INPUT_QUALITY_TODO.md` 散文附加 `18`＋`份文件` ⇒ `--only g2` 仍 **rc=0**（散文不掃）；
    在 `scripts/govb1_final_gate.sh` 寫入字面量 `14`＋`個 fixture` ⇒ `--only g2` **rc≠0**（consumer 必擋）
    〔🔴 本行刻意以 `＋` 斷開數字與量詞：`govb1_selfcheck.sh` 之 `CHK-NOFROZEN-COUNT`（`x-stamp-r8` 定版）
    仍掃**全文件**，與 CCS「散文不掃」重疊但更嚴。**本批不動定版 runner**，改令散文自律；
    兩者政策落差交 adversarial 裁定〕
  - 🔴 `T-0.1-F5`（**manifest 漂移 lint**）〔`GROK-R21-P0-01`：本項原**只在 §B 具名**，
    **Task 0.1 驗證欄漏加** ⇒ 宣稱有、實際無驗收路徑；與 `scope_manifest:` 無生成契約（U-4）同型〕：
    🔴 **可重跑命令**〔`CODEX-R22-P1-01`：原僅散文描述比對對象，**不是可重跑的 lint**。
    `CODEX-R23-P0-02`：改後之命令**引用未定義的 `_g7_task_decl`** ⇒ 與 `--print-plan` v1
    之「引用未定義介面」**同型第二次**，本輪一併定義。
    `CODEX-R23-P0-03`：原只比 raw `allow`，**未排除 `allow∩deny`** ⇒ 與 deny 優先之
    `_g7_policy` 得出不同集合，**lint 與 oracle 不一致**〕：
    ```sh
    _g7_task_decl() {   # stdout: 各 Task「修改 ∪ 新建」欄之路徑（現讀本 TODO）
      awk '
        /^- \*\*修改檔案\*\*/  { m=1 }
        /\*\*只讀\*\*/         { m=0 }
        /\*\*既有 caller\*\*/  { m=0 }
        /^#/                   { m=0 }
        m                      { print }
      ' docs/GOVB1_INPUT_QUALITY_TODO.md \
        | grep -oE '`(scripts|tests|templates|docs)/[A-Za-z0-9_./-]+`' | tr -d '`' \
        | grep -vxF -f <(awk '$1=="deny"{print $2}' "${GOVB1_SCOPE_MANIFEST:-scripts/govb1_scope.manifest}") \
        | LC_ALL=C sort -u
      # 🔴 須剔除 deny 集合〔`CODEX-R24-P0-03`：`_g7_policy` 排除 deny，但 `_g7_task_decl`
      #    會把「`govb1_baseline_dirty.txt` **不得建立**」之路徑當成 Task 新建路徑抽出
      #    ⇒ 兩側集合**永遠不相等**，該 lint **恆紅**、無法通過。〕
      # 🔴 **但單純剔除會製造靜默放行**〔`CODEX-R25-P0-02`＋`GROK-R25-P1-01`；主委於 R18
      #    brief 特攻第 3 點自招，成立〕：若某路徑**確實應由本批新建**卻被**誤列 `deny`**，
      #    左右兩側皆不出現該路徑 ⇒ `diff` rc=0 **靜默放行**。
      #    ⇒ **須另設一條斷言**（見下 `_g7_deny_conflict`），不得只靠剔除。
    }
    # 🔴 衝突檢查改為 **manifest 內部一致性**，不讀散文
    #    〔`CODEX-R26-P0-02`：前版以 raw parser 讀 TODO 檔案欄，會把負面句
    #     「`govb1_baseline_dirty.txt` 已廢除、**不得建立**」當成 Task 宣告 ⇒ 與 deny 交集 ⇒ **假紅**。
    #     **「在散文裡分辨正面宣告 vs 負面禁令」是列不完的**（本病第四次）——改為完全不讀散文。〕
    _g7_deny_conflict() {   # rc≠0 表示 manifest 自相矛盾
      _m="${GOVB1_SCOPE_MANIFEST:-scripts/govb1_scope.manifest}"
      _dup="$(comm -12 <(awk '$1=="allow"{print $2}' "${_m}" | LC_ALL=C sort -u) \
                       <(awk '$1=="deny"{print $2}'  "${_m}" | LC_ALL=C sort -u))"
      [ -z "${_dup}" ] || { printf 'F5 FAIL: manifest 同一路徑既 allow 又 deny:\n%s\n' "${_dup}" >&2; return 1; }
    }
    # 🔴 左側須與 `_g7_policy` 同語義：**deny 優先**，故用 `_g7_policy` 本身而非 raw allow
    _g7_deny_conflict \
      && diff <(_g7_policy | LC_ALL=C sort -u) <(_g7_task_decl | LC_ALL=C sort -u)
    ```
    **rc=0（集合相等，非包含）**。
    🔴 **`_g7_task_decl` 只服務本 lint，不參與 `_g7` 之 allow 判定**——
    後者唯一授權來源仍是凍結 manifest（見 §B）。
    mutation：於 manifest 增一列未出現於任何 Task 檔案欄之 `allow` 路徑 ⇒ **該 lint 須轉紅**（必附）。
    🔴 **manifest 仍為 `_g7` 唯一授權來源**；本 lint **不參與** allow 判定，只在兩者漂移時擋下。
  - `ASSERT bash scripts/gen_govb1_contract_matrix.sh THEN rc=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --only g0_tests THEN rc=0`
  - `ASSERT bash scripts/govb1_final_gate.sh --only nosuchcheck THEN rc=2`
  - **mutation N/A**：純資料導出與集合相等斷言，測試本身即 oracle。
    🔴 **以下三個 mutation 必附**（皆為委員實證之假綠形態，`revert 修法 → 該測試須轉紅`）：
    ①`T-0.1-C3`：pattern 改回 `^\|`（無前導空白）⇒ 行為表現讀轉 0；
    ②`_g5`／`_g6` 的抽取器改成必然抽空（例：函式名打錯一字）⇒ **須 FAIL 而非 PASS**
    （空對空恆綠是 `CODEX-R8-P0-06` 之病）；
    ③`_g7` 的 `printf '%s\n' "${actual}"` 去掉引號 ＋ 造一個含空白的路徑 ⇒ 須出現假陽性差集
    （證明引號是真的在擋 `COMPOSER-R8-P2-01`）。

### Phase 0 測試 + Gate

- **單元**：`T-0.1-C1`／`T-0.1-C2`　**邊界**：`T-0.1-B1`（docs 新增）／`T-0.1-B2`（行為表改列）／`T-0.1-B3`（空 docs）
- **效能**：⋅跳過（腳本 <1s，無效能需求）
- **Phase Gate**：`GATE-B1`

---

## Phase 1 — brief 機器區單次擴充（目標：派工前的輸入品質四項語意一次擴充完成）

**完成後系統狀態**：`brief_conformance_check.sh` 與 `template_check.sh` 皆由
`scripts/govflow_lifecycle.json` 驅動；brief 的四項語意（kind 規則／`EXPECTED-DELTA`／ID 樣板／
`fact-verified` 兩規則）在寫檔當下與派工當下皆被機械檢查。

### Task 1.1 — lifecycle matrix（單一真相源）

- **SPEC ref**：Task 1.1　**目標**：以單一資料檔定義 `brief-kind → 各階段責任`，取代三處硬編碼。
- **輸入**：現行 `brief_conformance_check.sh:65,89` 白名單、`cx_run.sh` 的 `_bk` case 分支
  **輸出**：`scripts/govflow_lifecycle.json`（頂層 key ＝ `kinds`、`stages`）
- **實作要點**：
  1. Schema（**本 TODO 不列欄位表，以檔為準**；建檔時同步寫 `_doc` 欄說明）：
     `{"_doc": "...", "kinds": {"review": {...}, "consult": {...}, "closure": {...}, "impl": {...}, "stamp": {...}}}`
  2. `brief_conformance_check.sh` 改法（偽碼）：
     ```sh
     _valid_kinds() { jq -r '.kinds | keys[]' "${SCRIPT_DIR}/govflow_lifecycle.json"; }
     _bk_ok() { _valid_kinds | grep -qx "$1"; }   # 取代 :89 的 case 列舉
     ```
  3. `cx_run.sh` 同理改讀 JSON，**禁保留硬編碼 fallback**（那是第二真相源）。
  4. 🔴 **`debt_clear.sh` 不納入 kind 集合相等**——其 `--kind` 是 `abandon_kind`
     （`no-findings-expected`｜`collection-failed`，源自 `scripts/audit_events.json` `enums.abandon_kind`），
     **與 `brief-kind` 是不同枚舉**。matrix 中 `debt_clear` 欄記的是「該 `brief-kind` 的**銷帳前置條件**」。
  5. **single-writer 契約**：本 Task **獨占**建立頂層 schema；Task 1.3／4.2 只新增各自具名節，禁改既有節。
- **修改檔案**｜**修改**：`scripts/brief_conformance_check.sh`（新增 `_valid_kinds()`／`_bk_ok()`，取代 `:65,89` 硬編碼）、
  `scripts/cx_run.sh`（`_bk` case 分支）｜
  **新建**：`scripts/govflow_lifecycle.json`、`tests/governance/test_govb1_lifecycle_matrix.py`、
  **只讀**：`scripts/debt_clear.sh`、`scripts/audit_events.json`、
  `tests/governance/fixtures/govb1/brief_consult_ok.md`、`tests/governance/fixtures/govb1/brief_kind_unknown.md`
  （**fixture 由 Task 0.1 唯一建立**，T-4）
  **既有 caller**：`committee_run.sh` → `cx_run.sh` → `brief_conformance_check.sh`（三者皆須同步）。
- **不可做**：不得在 JSON 之外再列舉 kind；不得保留硬編碼 fallback；**不得改 `debt_clear.sh`**。
- **邊界**：①JSON 缺該 kind ⇒ **fail-closed rc≠0**，禁靜默放行；②JSON 語法錯 ⇒ rc≠0 且訊息含檔名。
- **風險緩解**：G-7（只讀類不得改）。
- **存活至**：Phase 4 完工後仍保留（`govflow_lifecycle.json` 為 1.3／4.2 的宿主）。
- **覆蓋風險**：🔴 **有**——Task 1.3／4.2 會再寫同一檔。已定 **single-writer ＋ append-only 節**契約
  （本 Task 獨占頂層 schema，後續只新增具名節、禁改既有節），且 §B 依賴序 B2→B4→B9 保證不並發。
  **不合併 Phase 的理由**：1.3 需待 B3 的解析器定型、4.2 需待 4.1 的分類判準定型，強行合併會製造 forward dependency。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-1.1-U1`：`brief_conformance_check.sh` 與 `cx_run.sh` 的 kind 集合與 JSON **集合相等**（`set(a)==set(b)`）
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_consult_ok.md THEN rc=0`
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_kind_unknown.md THEN rc!=0`
  - **mutation N/A**：集合相等斷言，測試本身即 oracle。

### Task 1.2 — `票 B-19` ③ ID 樣板驗證（三限縮條件缺一不可）

- **SPEC ref**：Task 1.2　**目標**：brief 內宣告的 finding ID 樣板須符合 `CANONICAL_ID_RE`。
- **輸入**：brief 檔　**輸出**：rc ＋ 三段式錯誤訊息
- **實作要點**：
  1. 判準＝**active ＋ findings-kind ＋ placeholder-aware ＋ canonical regex**，**三個限縮缺一不可**。
     regex 來源 `scripts/completeness_check.sh:63`，**引用不重寫**：
     ```sh
     _canon_re() { grep -m1 '^CANONICAL_ID_RE=' "${SCRIPT_DIR}/completeness_check.sh" | cut -d"'" -f2; }
     ```
  2. 函式簽名：`_check_id_pattern(brief_path) -> rc`；內部
     `_is_findings_kind()`／`_is_active()`／`_strip_placeholder()` 三個判準各自可獨立 mutate。
  3. 🔴 錯誤訊息**三段皆必填**（G-4 處置④的落點）：
     ```
     ERROR: brief 內 finding ID 樣板不合規
       違規 token: <原文>
       期望樣式:   <CANONICAL_ID_RE 字面>
       修法:       把 <違規段> 改為 R<數字>
     ```
- **修改檔案**｜**修改**：`scripts/brief_conformance_check.sh`（新增 `_check_id_pattern()`）｜
  **新建**：`tests/governance/test_govb1_brief_id_pattern.py`、
  **只讀**：`scripts/completeness_check.sh`、`scripts/_role_gate.sh`、
  `tests/governance/fixtures/govb1/brief_id_b0r.md`、`tests/governance/fixtures/govb1/brief_id_discussion.md`
  （**fixture 由 Task 0.1 唯一建立**，T-4）
  **既有 caller**：`cx_run.sh`（派工前硬擋）、`doc_format_precheck.sh`（寫檔當下）。
- **不可做**：🔴 **不得實作 ①（kind/target 通用硬擋）與 ②（reconcile/stamp 通用硬擋）**——
  ① 會誤殺合法 review（`_role_gate.sh` 明定 `review → family != implementer`）；
  ② 實測 **42% 誤擋（81/193）**〔`COMPOSER-R1-P1-02`〕。
- **邊界**：①brief 完全無 ID 樣板 ⇒ rc=0（不適用，不得誤擋）；②樣板出現在 code fence 內 ⇒ rc=0；
  ③樣板出現在**委員產出檔**（非 brief）⇒ 不掃（限 findings-kind brief）。
- **風險緩解**：誤擋率 receipt 依 §0.4。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：🔴 **有**——Task 1.3／1.4 亦改 `brief_conformance_check.sh`。
  §B 已把 1.2＋1.4 合為 B3、1.3 排 B4，**同批由同一執行端處理，不並發**；各自新增獨立函式，不改對方函式。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-1.2-U1..U6`：正反 fixture 各 ≥3
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_id_b0r.md THEN rc!=0`
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_id_discussion.md THEN rc=0`
  - `T-1.2-M1`（**mutation 必附**）：移除任一限縮條件 ⇒ 對應誤擋 fixture 轉紅
  - `T-1.2-E1`：stderr 逐項 `assert` 三段字串存在，缺一轉紅

### Task 1.4 — `fact-verified:` 兩項機械規則

- **SPEC ref**：Task 1.4　**目標**：擋下本 session 實際發生的兩種假事實。
- **輸入**：brief 檔　**輸出**：rc ＋ 訊息
- **實作要點**：
  1. 規則①：`fact-verified:` 若宣稱**計數**（以明示標記 `count:` 界定，**禁自然語言判斷**），
     其附帶指令**不得含截斷運算子**：
     ```sh
     _has_trunc() { printf '%s' "$1" | grep -qE '(^|[|[:space:]])(head|tail)([[:space:]]|$)|[[:space:]]-m[[:space:]]'; }
     ```
     〔出生事故〔歷史〕：主委宣稱之份數係 `head -20` 截斷值，與現跑值不符〕
  2. 規則②：`fact-verified:` 引用的 rc 若會被派工動作本身改變，須標註「派工後預期值」。
     判定集合（**具名有界，禁無限擴張**）：`debt_ledger --has-open`、`gate_check` token 新鮮度。
  3. 函式簽名：`_check_fact_verified(brief_path) -> rc`。
- **修改檔案**｜**修改**：`scripts/brief_conformance_check.sh`（新增 `_check_fact_verified()`／`_has_trunc()`）｜
  **新建**：`tests/governance/test_govb1_factverified.py`｜
  **只讀**：`tests/governance/fixtures/govb1/brief_factverified_head.md`、
  `tests/governance/fixtures/govb1/brief_factverified_ok.md`（**Task 0.1 唯一建立**，T-4）
  **既有 caller**：同 Task 1.2。
- **不可做**：不得把「宣稱是否為計數」交由自然語言判斷——須以明示標記界定，否則誤擋不可控。
- **邊界**：①指令含 `head` 但宣稱非計數（無 `count:`）⇒ rc=0；②`fact-verified:` 不含指令 ⇒ 維持既有行為。
- **風險緩解**：誤擋率 receipt 依 §0.4。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：🔴 **有**——同 Task 1.2（同檔多 writer）。緩解方式同上：同批處理＋各自獨立函式。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_factverified_head.md THEN rc!=0`
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_factverified_ok.md THEN rc=0`
  - `T-1.4-M1`（**mutation 必附**）：移除規則① ⇒ `brief_factverified_head.md` 用例轉綠

### Task 1.3 — `票 B-29` `EXPECTED-DELTA:` 宣告

- **SPEC ref**：Task 1.3　**目標**：brief 須宣告「改動後應改變判定的真實標的」。
- **輸入**：brief 檔　**輸出**：rc（區塊存在性）
- **實作要點**：
  1. `brief-kind=impl` 時要求 `EXPECTED-DELTA:` 區塊；格式定義**寫入 JSON 的 `expected_delta` 節**
     （**append-only，禁改既有節**）：
     ```sh
     _check_expected_delta() {   # $1=brief_path -> rc
       _bk="$(_brief_kind "$1")" || return 1
       [ "${_bk}" = "impl" ] || return 0            # 非 impl 不適用
       grep -q '^EXPECTED-DELTA:' "$1" || {
         echo "ERROR: brief-kind=impl 缺 EXPECTED-DELTA: 區塊" >&2; return 1; }
       # 區塊存在但為空 ⇒ 亦 FAIL
       sed -n '/^EXPECTED-DELTA:/,/^$/p' "$1" | grep -qE '[^[:space:]EXPECTED-DELTA:]' || {
         echo "ERROR: EXPECTED-DELTA: 區塊為空" >&2; return 1; }
     }
     ```
  2. 🔴 **先加 `--brief` 旗標，掛點才存在**〔`CODEX-R8-P1-02` 複驗（2026-08-07 主委實跑）：
     `gate.sh` **無 `--brief`**，未知參數在 `scripts/gate.sh:197` `*) echo "ERROR: 未預期參數"; exit 1`
     直接離開 ⇒ 原偽碼的 `${brief}` **無來源**，掛點寫不出來；且原 ASSERT 的負向用例會因
     「未知參數」而非「缺 EXPECTED-DELTA」轉紅＝**假綠**，正向用例則**必然失敗**〕：
     ```sh
     # (a) scripts/gate.sh:181-198 的參數解析 case 內新增一行
     --brief)           brief="${2:-}"; shift 2 ;;
     # (b) :75 的初始化行加入 brief=""
     # (c) _dispatch_preflight()：在既有 --reconcile 檢查之後插入
     if [ -n "${brief}" ] && [ "$(_brief_kind "${brief}")" = "impl" ]; then
       bash "${SCRIPT_DIR}/brief_conformance_check.sh" --only expected-delta "${brief}" \
         || { echo "GATE 拒發 token — brief-kind=impl 缺 EXPECTED-DELTA:" >&2; exit 1; }
     fi
     ```
     🔴 **不得停在「省略即跳過」**〔`CODEX-R13-P0-04` [BLOCKING]＋`GROK-R13-P1-03`：既有 caller
     從不帶 `--brief` ⇒ EXPECTED-DELTA 閘**永遠不跑**，ASSERT 全綠而生產零強制——與 runner 出生事故
     「零呼叫者」同型〕。**兩層都要做**：
     ```sh
     # (d) fail-closed：impl 派工（--spec 非空）缺 --brief ⇒ 拒發 token
     #     位置＝既有 V-C「impl(--spec) 一律須顯式 reconcile」同段（scripts/gate.sh:553）
     if [ -n "${spec}" ] && [ -z "${brief}" ]; then
       miss brief "impl 派工(--spec)一律須 --brief（EXPECTED-DELTA 閘的輸入）"
     fi
     # (e) caller 接線：committee_run.sh 已有 brief 變數，派工前強制 append 到 gate args
     gate_args+=(--brief "${brief}")
     ```
     🔴 **非 impl 路徑（`--spec` 為空）維持既有行為**，否則所有既存 consult／review 派工同時轉紅。
     驗收見 `T-1.3-N1`（缺旗標必拒）。
- **修改檔案**｜**修改**：`scripts/brief_conformance_check.sh`（新增 `_check_expected_delta()`）、
  `scripts/gate.sh`（**`:75` 初始化 `brief=""`**、**`:181-198` case 新增 `--brief`**、
  `:553` 段加 impl 缺 `--brief` 之 `miss`、`_dispatch_preflight()` 內插 impl 分支）、
  🔴 `scripts/committee_run.sh`（**派工前強制 append `--brief` 到 gate args**；
  〔`GROK-R13-P1-03`：不接線則掛點空轉〕）、
  `scripts/govflow_lifecycle.json`（新增 `expected_delta` 節）｜
  **新建**：`tests/governance/test_govb1_expected_delta.py`｜
  **只讀**：`tests/governance/fixtures/govb1/brief_impl_delta_absent.md`、
  `tests/governance/fixtures/govb1/brief_impl_delta_present.md`（**Task 0.1 為唯一 owner**，T-4）、
  `docs/GOVB1_INPUT_QUALITY_SPEC.md`、`handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md`（驗收命令引用）
  **既有 caller**：`committee_run.sh` → `gate.sh dispatch`。
- **不可做**：**不得**在本 Task 實作「前後對照的實際比對」（`票 B-29` 第 2 段，本批不做）。
- **邊界**：①`kind=consult` 無此區塊 ⇒ rc=0（不適用）；②區塊存在但為空 ⇒ rc≠0。
- **風險緩解**：single-writer 契約——完成後 `jq -r 'keys[]' scripts/govflow_lifecycle.json | sort`
  須為 Task 1.1 結果之**超集**。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：🔴 **有**——`govflow_lifecycle.json` 與 `brief_conformance_check.sh` 皆為多 writer。
  緩解＝single-writer ＋ append-only 節契約，且 §B 依賴序 B2→B3→B4→B9 保證不並發。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_impl_delta_absent.md THEN rc!=0`
  - `ASSERT bash scripts/brief_conformance_check.sh tests/governance/fixtures/govb1/brief_impl_delta_present.md THEN rc=0`
  - 🔴 **`gate.sh` 掛點的正反斷言**〔`COMPOSER-R7-P1-02`：原驗證只覆蓋 `brief_conformance_check.sh`，
    **未覆蓋 gate 掛點** ⇒ 該掛點無驗收路徑〕
    🔴 **前置＝債本為空**：`_check_open_debt`（`scripts/gate.sh:514`）先於本掛點執行，
    有未清債時**正向用例必失敗**，故兩式皆須 `WHEN debt_open=0`。
    🔴 **負向用例須歸因，不得只斷 `rc!=0`**——未知參數／缺必填欄同樣是非零，
    會讓掛點根本沒跑也算通過：須另斷 stderr 含 `缺 EXPECTED-DELTA`。
    `ASSERT bash scripts/gate.sh dispatch --task-id 20260807-GOVB1-X-IMPL-R2 --risk low --intent probe --facts-asked probe --review-role probe --template "n/a:" --spec docs/GOVB1_INPUT_QUALITY_SPEC.md --reconcile handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md --brief tests/governance/fixtures/govb1/brief_impl_delta_absent.md WHEN debt_open=0 THEN rc!=0`
    `ASSERT bash scripts/gate.sh dispatch --task-id 20260807-GOVB1-X-IMPL-R2 --risk low --intent probe --facts-asked probe --review-role probe --template "n/a:" --spec docs/GOVB1_INPUT_QUALITY_SPEC.md --reconcile handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md --brief tests/governance/fixtures/govb1/brief_impl_delta_present.md WHEN debt_open=0 THEN rc=0`
  - `T-1.3-E1`（**歸因斷言**）：負向用例之 stderr 須含 `缺 EXPECTED-DELTA`；
    把掛點整段註解掉 ⇒ 該斷言轉紅（證明 rc≠0 不是別的原因造成）
  - 🔴 `T-1.3-N1`（**掛點不得空轉**）〔`CODEX-R13-P0-04`〕：
    `ASSERT bash scripts/gate.sh dispatch --task-id 20260807-GOVB1-X-IMPL-R2 --risk low --intent probe --facts-asked probe --review-role probe --template "n/a:" --spec docs/GOVB1_INPUT_QUALITY_SPEC.md --reconcile handoffs/reconcile/20260807-govb1-x-stamp-r4/synth.md WHEN debt_open=0 THEN rc!=0`
    （**刻意不帶 `--brief`**；stderr 須含 `--brief`）
  - 🔴 `T-1.3-N2`（**caller 接線**）：`grep -c -- '--brief' scripts/committee_run.sh` **≥ 1**；
    移除該行 ⇒ `T-1.3-N1` 之等效 caller 路徑轉為可靜默跳過
  - **mutation N/A**：僅驗區塊存在性，行為為布林，正反 fixture 已足。

### Task 1.5 — `票 B-16` 擴充 A/B/C

- **SPEC ref**：Task 1.5　**目標（3 項）**：規格內檢查條件落筆即跑（A）；引用標的存在性確認（B）；
  宣稱範圍不得大於已驗範圍（C）。
- **輸入**：SPEC/TODO 檔　**輸出**：rc ＋ 訊息
- **實作要點**：
  1. **A**：抽出 `ASSERT` 行並執行，記 rc。**引用尚未實作的腳本 ⇒ rc=0 並標 `pending`**
     （SPEC 階段禁止寫實作，範本明訂那不是缺陷）。
  2. **B**：規格內 `檔案`／`函式：<name>` 須存在：
     ```sh
     _func_exists() { grep -qE "^[[:space:]]*(def |function )?${1}[[:space:]]*\(" "$2"; }
     ```
     **註解中出現不算存在**（須先剝除 `#` 起始行）。
  3. **C**：宣稱含全稱詞（`全部`／`所有`／`N/N`）時須附機械導出命令，否則 rc≠0。
  4. 🔴 **只對 `docs/*SPEC*.md`／`docs/*TODO*.md` 套用 B/C，不對 `handoffs/` 委員產出套用**
     （那是討論語境，會誤擋——同 Task 1.2 教訓）。
- **修改檔案**｜**修改**：`scripts/template_check.sh`（新增 `_run_assert_lines()`／`_func_exists()`／`_check_scope_claim()`）｜
  **新建**：`tests/governance/test_govb1_template_check_ext.py`、
  **只讀**：`tests/governance/fixtures/govb1/spec_assert_pending.md`、
  `tests/governance/fixtures/govb1/spec_func_missing.md`（**Task 0.1 唯一建立**，T-4）
  **既有 caller**：`doc_format_precheck.sh:149`、`gate.sh` freeze 路徑。
- **不可做**：不得對 `handoffs/` 下的委員產出套用 B/C。
- **邊界**：①`ASSERT` 行引用尚未實作的腳本 ⇒ rc=0 標 `pending`；②函式名出現在註解中 ⇒ 不算存在。
- **風險緩解**：誤擋率 receipt 依 §0.4。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。`template_check.sh` 僅本 Task 修改，無其他 writer。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-1.5-A1/B1/C1` 各 ≥2 正反 fixture
  - `T-1.5-M1`（**mutation 必附**）：規格內故意寫一個不存在的函式名 ⇒ rc≠0

### Phase 1 測試 + Gate

- **單元**：`T-1.1-U1`／`T-1.2-U1..U6`／`T-1.3-U1..U2`／`T-1.4-U1..U2`／`T-1.5-A1,B1,C1`
- **邊界**：各 Task 的邊界欄逐條
- **效能**：⋅跳過
- **Phase Gate**：`GATE-B2`＋`GATE-B3`＋`GATE-B4`＋`GATE-B5` 全綠

---

## Phase 2 — `票 B-25` 事實單一來源（目標：同一事實只存在一個資料檔，文件由生成器產出）

**完成後系統狀態**：手改文件或忘跑生成 ⇒ `gov_check.sh` 非零 ⇒ push 被拒。

### Task 2.1 — fact-key 註冊表與生成器

- **SPEC ref**：Task 2.1　**目標**：建立唯一來源與決定性生成器。
- **輸入**：`scripts/fact_keys.json`　**輸出**：各文件的 generated block
- **實作要點**：
  1. 初始 fact-key 集合**由已發生的漂移事故導出**，**初始只收 `governance-execution-order` 一項**。
  2. 決定性輸出（缺一即 diff 恆紅）：
     ```sh
     gen_block() {   # $1=key -> stdout（決定性）
       printf '<!-- BEGIN GENERATED: %s -->\n' "$1"
       LC_ALL=C jq -r --arg k "$1" '.[$k].rows[] | @tsv' "${SCRIPT_DIR}/fact_keys.json" \
         | LC_ALL=C sort                       # 固定 collation，禁依賴環境 locale
       printf '<!-- END GENERATED: %s -->\n' "$1"
     }                                          # 全程 LF；不輸出 BOM；不含時間戳
     check_all() {   # -> rc；重新生成並與檔內既有區塊 diff
       root="${GOVB1_FACTKEY_ROOT:-.}"; rc=0
       for k in $(LC_ALL=C jq -r 'keys[]' "${SCRIPT_DIR}/fact_keys.json"); do
         tgt="$(LC_ALL=C jq -r --arg k "$k" '.[$k].target' "${SCRIPT_DIR}/fact_keys.json")"
         cur="$(sed -n "/<!-- BEGIN GENERATED: ${k} -->/,/<!-- END GENERATED: ${k} -->/p" "${root}/${tgt}")"
         [ "${cur}" = "$(gen_block "$k")" ] || { echo "FACTKEY DRIFT: ${k} in ${tgt}" >&2; rc=1; }
       done
       return "${rc}"
     }
     ```
  3. 環境變數 `GOVB1_FACTKEY_ROOT` 供測試指向 fixture 目錄（預設 repo root）。
  4. 🔴 **目標檔缺邊界標記 ⇒ `cur` 為空 ⇒ 與 `gen_block` 不等 ⇒ rc≠0**（fail-closed，非靜默放行）。
- **修改檔案**｜**修改**：無｜
  **新建**：`scripts/fact_keys.json`、`scripts/gen_fact_key_blocks.sh`、
  `tests/governance/test_govb1_factkey_gen.py`、
  **只讀**：`docs/GOVERNANCE_EXECUTION_ORDER.md`、
  `tests/governance/fixtures/govb1/factkey_clean`、`tests/governance/fixtures/govb1/factkey_drifted`
  （**Task 0.1 唯一建立**，T-4）
  **既有 caller**：新建無 caller（Task 2.2 才接）。
- **不可做**：🔴 **不得實作「權威宣稱詞黑名單」**——已被使用者推翻（①靠記憶 ②禁止清單列不完＝`票 B-23` 同病）。
- **邊界**：①`fact_keys.json` 為空 ⇒ rc=0（無事可做，不得 fail）；②目標文件缺邊界標記 ⇒ rc≠0 且訊息含檔名與 key。
- **風險緩解**：非決定性 ⇒ diff 恆紅 ⇒ 機制退化成噪音〔`COMPOSER-R1-P2-03`〕。
- **存活至**：Phase 4 完工後仍保留（`票 B-25` 的長期基礎設施）。
- **覆蓋風險**：無。`fact_keys.json` 與生成器僅本 Task 建立，Task 2.2 只呼叫不改。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-2.1-D1`：連跑 3 次 `bash scripts/gen_fact_key_blocks.sh | shasum -a 256` **三次相同**
  - `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_clean THEN rc=0`
  - `ASSERT bash scripts/gen_fact_key_blocks.sh --check WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_drifted THEN rc!=0`
  - `T-2.1-M1`（**mutation 必附**）：把排序改為未指定 locale ⇒ 決定性測試轉紅

### Task 2.2 — 強制層掛載與 hook 次序

- **SPEC ref**：Task 2.2　**目標**：把 2.1 的檢查掛進 push 前的強制點。
- **輸入**：`gen_fact_key_blocks.sh --check` 的 rc　**輸出**：`gov_check.sh` 的 rc
- **實作要點**：
  1. `gov_check.sh` 新增段（**函式名 `_gov_check_factkey`**）：
     ```sh
     _gov_check_factkey() {   # -> rc
       echo "[gov_check] 5/5 事實單一來源 (fact-key)…"
       [ -x "${ROOT}/scripts/gen_fact_key_blocks.sh" ] || {
         echo "gov_check: gen_fact_key_blocks.sh 缺失 → fail-closed" >&2; return 1; }
       bash "${ROOT}/scripts/gen_fact_key_blocks.sh" --check || return 1
     }
     ```
  2. 🔴 **新增段前須先統一段號**——現行三處 echo 的**分母彼此不一致**（含一個帶字母後綴的段），
     實跑 `grep -n 'gov_check\] ' scripts/gov_check.sh` 可見。
     統一規則：**分母＝該檔實際段數（現算）**，帶字母後綴者併入前一段；**禁在字串中寫死分母**。
  3. **hook 次序須寫進註解**（與 `票 B-29` 不矛盾的理由）：
     `B-29` 管**派工當下的宣告**（brief）；`B-25` 管**文件副本一致性**（repo 狀態，
     只有 push 前才有完整快照）。
- **修改檔案**｜**修改**：`scripts/gov_check.sh`（新增 `_gov_check_factkey()`；段號統一為 `n/5`）｜
  **新建**：`tests/governance/test_govb1_factkey_hook.py`｜
  **只讀**：`scripts/git_hooks/pre-push`、`tests/governance/fixtures/govb1/factkey_clean`、
  `tests/governance/fixtures/govb1/factkey_drifted`、`scripts/gen_fact_key_blocks.sh`（Task 2.1 建立，本 Task 只呼叫）
  **既有 caller**：`scripts/git_hooks/pre-push:24`。
- **不可做**：🔴 **不得宣稱「single-source 已完成」**。具名殘留：生成器不知道的新文件第三份副本擋不到；
  `git push --no-verify` 可繞。**不得改 `pre-push` 本身**。
- **邊界**：①生成器不存在 ⇒ **fail-closed rc≠0**，不得靜默略過；②段號分母不一致 ⇒ 先修再加。
- **風險緩解**：G-3（禁先以警告模式上線）。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：無。`gov_check.sh` 僅本 Task 修改；`pre-push` 為只讀，不改。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/gov_check.sh --no-probe WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_drifted THEN rc!=0`
  - `ASSERT bash scripts/gov_check.sh --no-probe WHEN GOVB1_FACTKEY_ROOT=tests/governance/fixtures/govb1/factkey_clean THEN rc=0`
  - **mutation N/A**：僅驗 hook 掛載，行為為布林，正反 fixture 已足。

### Phase 2 測試 + Gate

- **單元**：`T-2.1-D1`／`T-2.2-U1..U2`　**邊界**：各 Task 邊界欄
- **效能**：生成器單次 <2s（`time bash scripts/gen_fact_key_blocks.sh` 實測貼 receipt）
- **Phase Gate**：`GATE-B6`

---

## Phase 3 — `票 B-15` 唯讀查詢誤判（目標：唯讀診斷指令不再被當成派工擋下）

**完成後系統狀態**：`pgrep -fl '…|grok '`、`.claude/` 路徑查詢、`--approver claude` 皆不被誤擋，
**且真派工仍被擋**。

### Task 3.1 — 洞 A：家族名段不理解引號

- **SPEC ref**：Task 3.1　**目標**：引號內的 `;` `&` `|` 不再被當成命令分隔符。
- **輸入**：hook 的 stdin JSON　**輸出**：rc
- **實作要點**：
  1. 🔴 **先判未閉合引號（奇偶計數），再剝除成對引號**
     〔`CODEX-R7-P1-06`：原偽碼用 `sed` 剝除成對引號，**無法偵測未閉合引號**
     ⇒「未閉合 ⇒ fail-closed」這條邊界實作不出來〕：
     ```sh
     _unbalanced_quote() {   # $1=cmd -> rc=0 表示未閉合
       sq=$(printf '%s' "$1" | tr -cd "'" | wc -c)
       dq=$(printf '%s' "$1" | tr -cd '"' | wc -c)
       [ $(( sq % 2 )) -ne 0 ] || [ $(( dq % 2 )) -ne 0 ]
     }
     _strip_quoted() { printf '%s' "$1" | sed "s/'[^']*'//g; s/\"[^\"]*\"//g"; }
     _family_seg_hit() {   # $1=cmd -> rc=0 表示命中（判為 dispatch）
       _unbalanced_quote "$1" && return 0        # 未閉合 ⇒ fail-closed，當作有分隔符
       printf '%s' "$(_strip_quoted "$1")" \
         | grep -qE '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]'
     }
     ```
  2. **不得**改為關鍵字白名單（打地鼠）。
- **修改檔案**｜**修改**：`scripts/gate_check.sh`（`:86` 家族名段：新增 `_unbalanced_quote()`／`_strip_quoted()`，改寫 `_family_seg_hit()`）｜
  **新建**：無｜
  **只讀**：`tests/governance/test_gate_decision.py`、`tests/governance/fixtures/gate_decision_corpus.txt`、
  `tests/governance/fixtures/govb1/gatecmd_pgrep_quoted.json`、
  `tests/governance/fixtures/govb1/gatecmd_real_dispatch.json`（**Task 0.1 唯一建立**，T-4）
  **既有 caller**：PreToolUse hook（`.claude/settings.json`）。
- **不可做**：不得動 `.claude/gate/` 下的 token 有效期邏輯（`票 B-6`，不在本批）。
- **邊界**：①巢狀引號；②**引號未閉合 ⇒ fail-closed 當作有分隔符**（寧誤擋不漏放）。
- **風險緩解**：本 Task 為**放寬型**改動 ⇒ 風險是漏放 ⇒ 既有語料必須全綠。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：🔴 **有**——Task 3.2 亦改 `gate_check.sh`，且 3.2 會**沿用** 3.1 的
  `_strip_quoted()`。§B 已把兩者合為 **B7 同批**，由同一執行端依序完成，不並發。
  **不合併為單一 Task 的理由**：兩個洞的成因與驗收語料不同，合併會使 mutation 無法定位。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_pgrep_quoted.json THEN rc=0`
  - `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_real_dispatch.json THEN rc!=0`
  - `T-3.1-R1`：`pytest tests/governance/test_gate_decision.py -q` 全綠（**禁放寬既有斷言**）
  - **mutation N/A**：以既有語料逐案例比對，語料即 mutation 基準。

### Task 3.2 — 洞 B：`claude` 段比對子字串

- **SPEC ref**：Task 3.2　**目標**：`.claude/` 目錄與 scratchpad 路徑不再誤觸。
- **輸入**：hook 的 stdin JSON　**輸出**：rc
- **實作要點**：
  1. `claude` 須為**命令位置**（沿用 Task 3.1 的分隔符判定）。
  2. `-p`／`--print` 須為**獨立 token**（不得命中 `rev-parse`／`--porcelain`／`-print` 子字串）：
     ```sh
     _has_flag() { printf '%s\n' $1 | grep -qx -e '-p' -e '--print'; }
     ```
  3. 函式簽名：`_claude_seg_hit(cmd) -> rc`。
- **修改檔案**｜**修改**：`scripts/gate_check.sh`（`claude` 段：新增 `_has_flag()`，改寫 `_claude_seg_hit()`）｜
  **新建**：無｜
  **只讀**：`tests/governance/fixtures/govb1/gatecmd_claude_path.json`、
  `tests/governance/fixtures/govb1/gatecmd_claude_p_real.json`（**Task 0.1 唯一建立**，T-4）
  **既有 caller**：同 Task 3.1。
- **不可做**：不得以「路徑白名單」解（`.claude/` 之外仍有 scratchpad，列不完）。
- **邊界**：①`--print` 出現在引號內；②路徑含 `claude` 且指令另有獨立 `-p` 旗標 ⇒ **仍須擋**。
- **風險緩解**：同 Task 3.1（放寬型改動，既有語料必須全綠）。
- **存活至**：Phase 4 完工後仍保留。
- **覆蓋風險**：🔴 **有**——同 Task 3.1（同檔）。緩解＝B7 同批依序完成。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_claude_path.json THEN rc=0`
  - `ASSERT bash scripts/gate_check.sh < tests/governance/fixtures/govb1/gatecmd_claude_p_real.json THEN rc!=0`
  - `T-3.2-R1`：三例現場事故逐一轉綠（`head -3 <scratchpad>; git rev-parse --short origin/main` 等）
  - **mutation N/A**：同上。

### Phase 3 測試 + Gate

- **單元**：`T-3.1-U1..U2`／`T-3.2-U1..U2`　**邊界**：各 Task 邊界欄
- **效能**：hook 單次 <0.1s（`gate_check.sh` 在熱路徑上，實測貼 receipt）
- **Phase Gate**：`GATE-B7`

---

## Phase 4 — `票 B-38` 分類判準與 `票 B-31` 補救層

**完成後系統狀態**：可機械判斷「哪些產出應該有 findings」；零 findings 契約單一化；
格式不合規不必整份重跑，且自檢涵蓋主委自產物。

### Task 4.1 — findings-kind 產出的機械分類判準

- **SPEC ref**：Task 4.1　**目標**：產出可證偽的分類判準＋誤擋率 receipt。**不含改判。**
- **輸入**：`scripts/govflow_lifecycle.json` 的 kind 定義　**輸出**：分類結果 ＋ 混淆矩陣
- **實作要點**：
  1. 由 JSON 讀 `kind → is_findings_kind`；對 `handoffs/*.md` 全量分類：
     ```sh
     classify() {   # $1=path -> "findings"|"non-findings"|"unknown"
       bk="$(grep -m1 '^brief-kind:' "$1" 2>/dev/null | awk '{print $2}')"
       [ -n "${bk}" ] || { echo "unknown"; return 0; }        # 無 brief-kind ⇒ 不猜
       v="$(LC_ALL=C jq -r --arg k "${bk}" '.kinds[$k].is_findings_kind // "unknown"' \
            "${SCRIPT_DIR}/govflow_lifecycle.json")"
       case "${v}" in true) echo "findings" ;; false) echo "non-findings" ;; *) echo "unknown" ;; esac
     }
     audit() {   # $1=corpus_dir -> stdout 混淆矩陣 + rc
       for f in "$1"/*.md; do printf '%s\t%s\n' "$(classify "${f}")" "${f}"; done \
         | LC_ALL=C sort | awk -F'\t' '{c[$1]++} END {for (k in c) printf "%s\t%d\n", k, c[k]}'
     }
     ```
  3. **三入口交叉 oracle**（新測試檔）：對三種輸入 × 三個入口，**逐格 rc 改前 == 改後**：

     | 輸入 | `--single` | `--lock` | `cx_run` 交件路徑 |
     |---|---|---|---|
     | 0-ID 單行 heading probe | rc 不變 | rc 不變 | `result_state` 不變 |
     | prose-only 產出 | rc 不變 | rc 不變 | `result_state` 不變 |
     | hollow `P3-00` | **允許 0 → 非 0**（Task 4.2 唯一許可） | rc 不變 | `result_state` 可變 |
- **修改檔案**｜**修改**：無｜
  **新建**：`scripts/findings_kind_classify.sh`、`tests/governance/test_govb1_findings_kind.py`、
  `tests/governance/test_govb1_zeroid_no_regression.py`｜
  **只讀**：`scripts/govflow_lifecycle.json`、`tests/governance/test_completeness_idlike_fp.py`、
  `scripts/completeness_check.sh`、`scripts/cx_run.sh`
  **既有 caller**：新建無 caller（Task 4.2 才接）。
- **不可做**：🔴 **G-1 全域禁令**——禁止任何使 `C-2` 表中期望 `rc==0` 之列由 0 變非 0 的改動，
  **不論實作於哪一層**。**改判本身不在本批 scope。**
- **邊界**：①`impl`／`stamp`／runlog（本無 canonical ID）⇒ 判 non-findings-kind；
  ②測試探針單行 heading 檔 ⇒ 判 non-findings-kind；③未知 kind ⇒ 判 `unknown`，**不得猜**。
- **風險緩解**：誤擋率 receipt 依 §0.4（**分母 >100 ⇒ 抽 ≥100 ＋ Wilson CI**）。
- **存活至**：本批完工後保留，供後續「改判」票消費（改判本身不在本批 scope）。
- **覆蓋風險**：無。`findings_kind_classify.sh` 僅本 Task 建立；Task 4.2 只讀其判準不改其實作。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/findings_kind_classify.sh --audit --corpus handoffs THEN rc=0`
  - `T-4.1-Z1..Z9`：三入口 × 三輸入矩陣逐格
  - `T-4.1-G1`：`git diff --stat tests/governance/test_completeness_idlike_fp.py` 輸出為空
  - `T-4.1-M1`（**mutation 必附**）：mutate 分類判準任一條件 ⇒ 對應 fixture 由 pass 轉 fail

### Task 4.2 — 零 findings 契約合併

- **SPEC ref**：Task 4.2　**目標**：`票 B-38` 與 `GOV-NOFINDINGS-SENTINEL`／`GOV-NO-FINDINGS-RECEIPT`
  合併為**單一契約**，禁各自實作。
- **輸入**：委員產出檔　**輸出**：rc
- **實作要點**：
  1. 契約定義**三件事，缺一不可**：①sentinel 形態（`<FAMILY>-R<n>-P3-00`）
     ②body 必填欄 ＋ **語意非空判準** ③🔴 **findings 的落點**（每種 `brief-kind` 的 findings 寫進哪個檔）。
     〔③ 的出生事故：`stamp` 輪 brief 未寫落點，一委員 append 進 stamp-target ⇒
     自身產出檔 0 heading ID ⇒ **整輪作廢**〕
  2. `_validate_finding_body` 改法（現行 `:279-280` 只匹配標籤字面、不 trim 內容）：
     ```sh
     # 現行：seen_assert = /\*\*斷言\*\*/
     # 改後：標籤後須有非空白內容
     if ($0 ~ /\*\*斷言\*\*/) { rest=$0; sub(/.*\*\*斷言\*\*[：:]?/, "", rest);
                                gsub(/[[:space:]]/, "", rest); if (rest != "") seen_assert=1 }
     ```
  3. `zero_findings_contract` 節 **append 進 JSON，禁改既有節**。
- **修改檔案**｜**修改**：`scripts/govflow_lifecycle.json`（新增 `zero_findings_contract` 節）、
  `scripts/completeness_check.sh`（`_validate_finding_body`）、
  `templates/COMMITTEE_FINDING_TEMPLATE.md`（pointer）｜
  **新建**：`tests/governance/test_govb1_zero_findings.py`｜
  **只讀**：`tests/governance/fixtures/govb1/finding_hollow_p300.md`、
  `tests/governance/fixtures/govb1/finding_real_p300.md`（**Task 0.1 唯一建立**，T-4）、
  `tests/governance/test_completeness_idlike_fp.py`（**禁改**，G-1 回歸護網）
  **既有 caller**：`cx_run.sh` 交件路徑、`debt_clear.sh` 銷帳路徑。
- **不可做**：不得新增第四種 0-findings 表達形式；🔴 **G-1 全域禁令**（唯一許可的行為變更＝
  hollow body 非空判定）。
- **邊界**：①欄名存在但只有空白字元 ⇒ rc≠0；②欄名存在且內容為單一標點 ⇒ rc≠0；
  ③實質 sentinel ⇒ rc=0。
- **風險緩解**：G-1 的三入口矩陣（Task 4.1）即為本 Task 的回歸護網。
- **存活至**：本批完工後保留。
- **覆蓋風險**：🔴 **有**——`govflow_lifecycle.json` 為多 writer（Task 1.1 建、1.3／4.2 各新增節）。
  緩解＝append-only 節契約 ＋ §B 依賴序 B2→B4→B9。
  `completeness_check.sh` 亦被 Task 4.1 只讀引用，本 Task 為**唯一 writer**。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `ASSERT bash scripts/completeness_check.sh --single tests/governance/fixtures/govb1/finding_hollow_p300.md --family codex THEN rc!=0`
  - `ASSERT bash scripts/completeness_check.sh --single tests/governance/fixtures/govb1/finding_real_p300.md --family codex THEN rc=0`
  - `T-4.2-M1`（**mutation 必附**）：移除語意非空判準 ⇒ hollow fixture 轉綠
  - `T-4.2-G1`：`pytest tests/governance/test_completeness_idlike_fp.py -q` 全綠

### Task 4.3 — `票 B-31` 補救層＋自檢涵蓋主委產出

- **SPEC ref**：Task 4.3　**目標**：格式不合規不必整份重跑；自檢涵蓋主委自產物。
- **輸入**：委員／主委產出檔　**輸出**：`result_state` ＋ stderr 清單
- **實作要點**：
  1. `format-failed` 時輸出**逐條可修補清單**（非只 rc）：每條含 `檔:行`＋違規類型＋修法一行。
  2. 該輪帳不因格式失敗而卡住後續派工。
  3. 🔴 交件前自檢的要求**擴及主委自產物**：
     ```sh
     _run_format_check_if_needed() {   # $1=out_path $2=family -> rc
       # 現行：僅當 family ∈ review_families 時跑
       # 改後：只要顯式傳入 --family（含 claude）一律跑
       [ -n "$2" ] || return 0
       bash "${SCRIPT_DIR}/completeness_check.sh" --single "$1" --family "$2" >"${_fc_log}" 2>&1 && return 0
       _emit_fixup_list "${_fc_log}"          # 逐條可修補清單（非只 rc）
       _emit_result_state "format-failed"     # 不得標 failed
       return 1
     }
     _emit_fixup_list() {   # 每條含 檔:行 ＋ 違規類型 ＋ 修法一行
       awk -F: '/^COMPLETENESS FAIL/ { printf "  %s:%s\t%s\t%s\n", FILENAME, NR, $2, "見 templates/COMMITTEE_FINDING_TEMPLATE.md" }' "$1" >&2
     }
     ```
     〔出生事故：主委自己的 `**來源摘要**` 寫行號而非 12 位雜湊，4 個 P0/P1 全 FAIL〕
- **修改檔案**｜**修改**：`scripts/cx_run.sh`（改寫 `_run_format_check_if_needed()`、新增 `_emit_fixup_list()`）｜
  **新建**：`tests/governance/test_govb1_b31_recovery.py`｜
  **只讀**：`tests/governance/fixtures/govb1/finding_hollow_p300.md`、
  `docs/TEST_DESIGN_CHARTER.md`、`scripts/debt_clear.sh`、
  `templates/COMMITTEE_FINDING_TEMPLATE.md`（修補清單訊息引用，不改）
  **既有 caller**：`committee_run.sh` → `cx_run.sh`。
- **不可做**：不得放寬 `debt_clear` 只接受 `success` 的守衛（三值契約，`P16_COMMITTEE_DEBT_SPEC` 凍結）。
- **邊界**：①格式失敗但產出實質完整 ⇒ 標 `format-failed` **不得**標 `failed`；
  ②主委產出無家族後綴 ⇒ 自檢須仍可跑（顯式傳 `--family claude`）。
- **風險緩解**：G-6（不得重做 `票 B-32`）——本 Task 動 `cx_run.sh` 的**交件路徑**，非 stamp prompt 路徑。
- **存活至**：本批完工後保留。
- **覆蓋風險**：🔴 **有**——`cx_run.sh` 亦被 Task 1.1 修改（`_bk` case 分支讀 JSON）。
  兩處為**不同函式**（`_bk` case vs `_run_format_check_if_needed`），且 §B 依賴序 B2→B10 保證不並發。
- **驗證**（pytest 正反 rc 對照；逐項如下）：
  - `T-4.3-U1`：以 hollow fixture 跑交件路徑，斷言 audit 記為 `format-failed`（非 `failed`）
  - `T-4.3-U2`：stderr 含逐條可修補清單（`assert` 至少一條含 `檔:行`）
  - `T-4.3-U3`：主委自產物走同一支檢查（顯式 `--family claude`）rc 與委員產出一致
  - **mutation N/A**：整合路徑，以 `result_state` 三值轉移測試覆蓋。

### Phase 4 測試 + Gate

- **單元**：`T-4.1-*`／`T-4.2-*`／`T-4.3-U1..U3`
- **邊界**：各 Task 邊界欄　**效能**：⋅跳過
- **Phase Gate**：`GATE-B8`＋`GATE-B9`＋`GATE-B10`＋`GATE-FINAL`

---

## 附錄 A — SPEC 索引與 100% 覆蓋追溯（交付物 #1）

### A.1 SPEC Task ID（合計 **13**）

| SPEC Task | SPEC 原文節錄（≤30 字） | TODO 落點 |
|---|---|---|
| 0.1 | 「產出 docs 契約矩陣與行為表交叉對照」 | Phase 0 / Task 0.1 |
| 1.1 | 「lifecycle matrix（單一真相源）」 | Phase 1 / Task 1.1 |
| 1.2 | 「`票 B-19` ③ ID 樣板驗證（三限縮條件缺一不可）」 | Phase 1 / Task 1.2 |
| 1.3 | 「`票 B-29` `EXPECTED-DELTA:` 宣告」 | Phase 1 / Task 1.3 |
| 1.4 | 「`fact-verified:` 兩項機械規則」 | Phase 1 / Task 1.4 |
| 1.5 | 「`票 B-16` 擴充 A/B/C」 | Phase 1 / Task 1.5 |
| 2.1 | 「fact-key 註冊表與生成器」 | Phase 2 / Task 2.1 |
| 2.2 | 「強制層掛載與 hook 次序」 | Phase 2 / Task 2.2 |
| 3.1 | 「洞 A：家族名段不理解引號」 | Phase 3 / Task 3.1 |
| 3.2 | 「洞 B：`claude` 段比對子字串」 | Phase 3 / Task 3.2 |
| 4.1 | 「findings-kind 產出的機械分類判準」 | Phase 4 / Task 4.1 |
| 4.2 | 「`票 B-38` 零 findings 契約合併」 | Phase 4 / Task 4.2 |
| 4.3 | 「`票 B-31` 補救層＋自檢涵蓋主委產出」 | Phase 4 / Task 4.3 |

**全部有落點**（數量由 `bash scripts/govb1_selfcheck.sh --manifest` 現讀導出，**本檔不記數字**）。

### A.2 SPEC §C 約束（合計 **8**：C-1／C-2／C-3／C-4b／C-5b／C-5／C-4／§C 開頭解耦）

| SPEC 約束 | 節錄 | TODO 落點 |
|---|---|---|
| `C-1` | 「分母一律現跑結果」 | §0.2 G-2 ＋ Task 0.1 實作要點 1 |
| `C-2` | 「期望 `rc==0` 之列逐列納入」＋行為禁令 | §0.2 G-1 ＋ Task 4.1 不可做 |
| `C-3` | 「不得觸碰清單」 | §0.2 G-4／G-5 |
| `C-4`（掛點對照） | 「禁寫『改 doc_format_precheck.sh』」 | 各 Task 的「修改檔案」欄逐一指定下游 delegate |
| `C-4b` | 「`檔案` 欄三類格式」 | §0.2 G-7 ＋ 各 Task「修改檔案」欄 |
| `C-5` | 「新資料結構一律建檔，SPEC 只 pointer」 | Task 1.1 實作要點 1（schema 以檔為準，TODO 不列欄位表） |
| `C-5b` | 「已完成票禁止重做」 | §0.2 G-6 |
| §C 開頭 | 「只動 `scripts/`＋`tests/governance/`」 | §0.1 解耦 |

**全部有落點**（逐條對照上表，**不記數字**）。

### A.3 SPEC §V 驗證項（合計 **6**）

| 項 | 節錄 | TODO 落點 |
|---|---|---|
| mutation 條件 | 「1.2／1.4／1.5／2.1／4.1／4.2 必附 mutation」 | 該 6 個 Task 的驗證欄各有 `T-*-M1` |
| §V-ASSERT | 「fixture 清單」（**逐名，數量現讀**） | Task 0.1 實作要點 4 ＋ `GATE-B1` |
| §V-FP | 「誤擋率定義」 | §0.4 逐字沿用 |
| 防假綠 1 | 「不得放寬既有測試斷言」 | §0.3-1 |
| 防假綠 2 | 「`--mode review` 機械可檢」 | §0.3-2 |
| 防假綠 3 | 「誤擋率 receipt」 | §0.3-3 ＋ §0.4 |

**全部有落點**（逐條對照上表，**不記數字**）。

### A.4 SPEC §RISK 命中原則

`RISK-HIT: b,c`（(b) 跨模組共用路徑、(c) 多 phase 難回退）→ §0.1 解耦 ＋ §B 的 10 Batch 依賴拓撲。

### A.5 Phase 依賴（合計 **5** Phase）

Phase 0（無依賴）→ Phase 1（依 Phase 0）→ Phase 2（依 Phase 1 Task 1.1）
／Phase 3（**無依賴，可與 Phase 1/2 並行**）→ Phase 4（依 Phase 1）。
**無 forward dependency。**

### A.6 環境變數／flag（合計 **1**）

`GOVB1_FACTKEY_ROOT`（Task 2.1 建立，Task 2.2 消費）。
🔴 **本批無任何 feature flag**——依 §0.2 G-3，禁先以警告模式上線。

### A.7 §N「本批不做」項（合計 **6**，須確認 TODO 未偷做）

`票 B-29` 第 2 段／`票 B-38` 改判／幽靈 ID（`票 B-13`）／`--mode` 枚舉不對齊（`票 B-13`）／
`template_check` 空殼誤判（`票 B-16` 原條文）／`票 B-41` 分工零強制。
**TODO 全文無對應 Task，確認未偷做。**

---

## 附錄 B — 一輪聚焦自檢（交付物 #3）

| # | 檢查 | 結果 |
|---|---|---|
| 1 | **追溯**：SPEC 各類 ID → 合計數與附錄 A 一致 | ✅ 逐類全數落點（**數量現讀，不記**） |
| 2 | **深度全掃**：每 Task 過深度紅線 | ✅ 由 `bash scripts/govb1_selfcheck.sh` 機械判定（**禁手寫勾選**） |
| 3 | **語義**：Cross-Task 同檔衝突？引用檔案/函式存在？改既有函式的呼叫者有同步？Test 測核心行為？ | ✅ 見下 |
| 4 | **全棧跨層** | ⋅跳過（純腳本層，無 API/前端） |
| 5 | **錨點自檢**：`## §0`、`## §B`、每 Task 含「驗證」「邊界」「不可做」 | ✅ 由 `doc_format_precheck.sh` 機械判定（**數量不記**） |

### B.2 深度紅線逐 Task 核對 — 🔴 **機械導出，禁手寫勾選**

🔴 **本節原為主委手寫勾選表，經 `CODEX-R7-P1-01`＋`COMPOSER-R7-P1-01`＋`GROK-R7-P1-03`
三家獨立命中為假綠**（實測 Task 1.3／2.1／2.2／4.1／4.3 無偽碼、
Task 1.1／1.3／1.4／1.5／2.2 修改檔案未到函式名）。
⇒ **修個案不夠，產生假綠的機制要拿掉**：本節改為由下列命令**現跑導出**，
**驗收時重跑，不看本節的歷史值**。

```sh
# ① 每 Task 的偽碼 fence 數（須 ≥1）
awk '/^### Task [0-9]/{t=$3; f[t]=0; o[++n]=t} /```sh/{if(t!="")f[t]++} \
     END{for(i=1;i<=n;i++) printf "Task %s fence=%d\n", o[i], f[o[i]]}' \
    docs/GOVB1_INPUT_QUALITY_TODO.md | awk '$2 ~ /fence=0/ {bad=1; print} END{exit bad}'

# ② 每 Task 的「修改」欄是否到函式名（須含 () 或具名區段）
awk '/^### Task [0-9]/{t=$3} /\*\*修改\*\*：/{if(t!="" && $0 !~ /\(\)|案 branch|節|分支|區段|無/) \
     printf "Task %s 修改欄未到函式名\n", t}' docs/GOVB1_INPUT_QUALITY_TODO.md

# ③ 每 Task 的「檔案三類聯集 ⊇ body 路徑」差集（須為空）——見 §0.2 G-7 的 _diff_set_subset_of_task_decl
```

**2026-08-07 主委實跑 ①**：13 個 Task 的 fence 數分別為
`0.1:3｜1.1:1｜1.2:1｜1.3:2｜1.4:1｜1.5:1｜2.1:1｜2.2:1｜3.1:1｜3.2:1｜4.1:1｜4.2:1｜4.3:1`
⇒ **無 fence=0 者**。〔歷史值，驗收須重跑〕

### B.3 語義檢查明細

- **Cross-Task 同檔衝突**：`scripts/govflow_lifecycle.json` 由 Task 1.1（建）／1.3（`expected_delta` 節）／
  4.2（`zero_findings_contract` 節）三處寫入 ⇒ 已定 **single-writer ＋ append-only 節**契約，
  且 §B 的依賴序（B2 → B4 → B9）保證**不並發**。
  `scripts/brief_conformance_check.sh` 由 Task 1.1／1.2／1.3／1.4 四處寫入 ⇒
  §B 已把 1.2＋1.4 合為 B3、1.3 排 B4，**同批內由同一執行端處理，不並發**。
  `scripts/gate_check.sh` 由 Task 3.1／3.2 兩處寫入 ⇒ §B 已合為 **B7 同批**。
- **引用檔案/函式存在**：本 TODO 引用的「修改」與「只讀」類路徑，
  已於 SPEC 階段以腳本驗過**全部存在**（唯一不存在者 `handoffs/govb0-probes` 已移除）。
- **改既有函式的呼叫者有同步**：`brief_conformance_check.sh` 的呼叫者
  `cx_run.sh`／`doc_format_precheck.sh` 已列入 Task 1.1／1.2 的「既有 caller」欄並要求同步。
- **Test 測核心行為**：全部 13 Task 的驗證欄皆為**正反 rc 對照**或**集合相等**，
  無「不拋錯」型 smoke；6 個 Task 另附 mutation。

### B.4 🔴 具名殘留（本 TODO 無法保證者）

1. **`票 B-25` 的第三份副本**：生成器不知道的新文件擋不到（SPEC §N 已具名）。
2. **`git push --no-verify`** 可繞過 Phase 2 的強制層。
3. **端到端驗收缺口**：`reconcile --mode` 與 `brief-kind` 枚舉不對齊留在批外
   ⇒ **lifecycle matrix 只能覆蓋到 `reconcile` 之前，不得宣稱端到端打通**。
4. **`票 B-41`**（分工規則零機械強制）本批不做——本 TODO 的起草者身分本身即該票的事故來源。
5. 🔴 **同 Batch 內平行派工**：§B 的「序列約束」為**擋意外不防蓄意**——
   若執行端自行平行處理同批兩 Task，`git log` 雙 commit 檢查只能**事後**發現，不能**事前**阻止。
   具名接受〔`CODEX-R7-P1-02`／`COMPOSER-R7-P1-03`／`GROK-R7-P1-04`〕。
6. 🔴 **G-2 改為 CCS 後的殘留**〔`x-consult-r7` Y-1；本項歷經兩次改寫：
   `〔歷史〕` 標記制度已廢除、`_g2_regions` 區域判準亦已廢除〕：
   - **文件散文完全不掃**：SPEC／TODO 正文可寫歷史數字，**一律非 oracle**。
     通過條件**只**以 consumer 腳本＋pytest 為準。**不得宣稱「全庫無凍結分母」。**
   - 🔴 **反向失敗模式**（grok 自陳，已設閘）：有人把通過條件**只寫進散文、不寫進腳本**
     ⇒ enforce 錯面。閘＝「每條 `G-*` 的機械驗收欄必須是可 exec 的 script 函式名」，
     由 adversarial／stamp 檢查。
   - **consumer 集合膨脹**：新腳本忘記納入。
     🔴 **〔U-3 修正；原句殘留「集合由 `final_gate` 呼叫圖 ∪ glob」已刪〕**
     🔴 **判準見 §0.1b（唯一來源），本處不重述**〔`CODEX-R25-P0-03`：原句把
     「無法保證之動態 edge」寫成可由 `_CHECKS`／`_plan` fail-closed 之 consumer 集合，
     **與 `UNRESOLVED` 之新職責矛盾**〕。
     🔴 **本項為具名殘留**：`UNRESOLVED` 只保證檢查函式存在；
     **動態 command edge 之脫離無機械保證**，緩解＝新增 consumer 必須在 manifest 明列。
7. ✅ **`govb1_baseline_dirty.txt` 旁路已消除，非殘留**〔`x-stamp-r9` X-2＋`x-consult-r7` Y-2〕：
   原以「具名殘留」收（`COMPOSER-R6-P2-02`＋`GROK-R13-P1-05`），
   據以裁定的前提是 grok 第①點「不扣 baseline 則 G-7 恆紅」。
   codex 提出 detached worktree 替代設計後**該前提被證偽** ⇒ 裁定推翻。
   🔴 **〔T-4 修正·本 session 第 9 次同型〕本句原寫「Sandbox G-7 在乾淨 worktree 內驗證」
   ＝已被 `x-consult-r10` W-1 取代之上一版設計。** 現行為 **commit-range G-7**：
   只看 `base..HEAD`、**不建任何 worktree**，**無 allowlist 可灌**，旁路消失。
   🔴 **該殘留已隨 commit-range 設計消失**〔V-4；**`CODEX-R22-P1-03`**：本處原**同時**保留
   「`GATE-FINAL` 依賴 `.git` metadata 可寫」與「該殘留已消失」**兩個相反敘述**，
   實作者會得到矛盾的交付語義。**前者已刪除。**〕：現行 `_g7` 取 `base..HEAD` commit range、
   `_g5`／`_g6` 用 `git show`，**皆不寫 `.git/worktrees`** ⇒ 無 sandbox 依賴、無需 fallback。
   **現行具名殘留改為**：①未宣告且未 commit 之改動不擋（V-5：G-7 ＝交付完整性，非工作站衛生）
   ②manifest hash 由建立者自定基準（V-6a，與 `base_commit` 同型）
   ③`--print-plan` 之動態邊 guard 為**有限啟發式**，不得作為「封閉可導出」之依據（V-6b）。
8. 🔴 **`base_commit` 不驗歷史純淨**〔三家一致：`CODEX-R13-P1-03`／`COMPOSER-R6-P2-01`／
   `GROK-R13-P2-01`〕：`G-5`／`G-6` 證明的是「相對動工前快照無漂移」，**不是**「行為表／函式從未被改」。
   若動工前 HEAD 已含被汙染內容，其後比對恆真。**文件中不得出現把 G-5／G-6 說成絕對保證的句子。**
9. ✅ **`Task 3.1` 未閉合引號 fail-closed 已解，非殘留**——原偽碼確實做不到
   （`CODEX-R7-P1-06`），已改為引號**奇偶計數**先判，再剝除成對引號。

---

## 附錄 C — Frozen 前 handoff

```
SPEC=docs/GOVB1_INPUT_QUALITY_SPEC.md
TODO=docs/GOVB1_INPUT_QUALITY_TODO.md
FOCUS=13 Task 的可執行深度；三類檔案欄的傳遞；三入口矩陣的可實作性；single-writer 契約是否足以防並發
```

**狀態**：`DRAFT` —— 未過三家（codex＋composer＋grok）adversarial review 前，
**不得標 Frozen、不得派 impl**。

---

## 附錄 D — B-49 授權擴充：epic 期間得修改之路徑（2026-08-12 使用者授權）

> 本節**不新增技術內容**，只補登「本 epic 施工期間實際會被修改、先前漏登記」之路徑。
> 🔴 **登記 ≠ 解凍**：`_B45_HARNESS` 五檔之凍結由三道 waiver 的 `hit_harness` 獨立看守。

- **修改檔案**｜**修改**：`docs/GOVB1_INPUT_QUALITY_TODO.md`、`tests/governance/test_brief_conformance.py`、`tests/governance/test_completeness_idlike_fp.py`、`tests/governance/test_cxrun_selfcheck_prompt.py`、`tests/governance/test_cxrun_stamp_prompt.py`、`tests/governance/test_debt_emit.py`、`tests/governance/test_doc_format_precheck.py`、`tests/governance/test_gov_check_dep_failclosed.py`、`tests/governance/test_result_state_format_failed.py`、`tests/governance/test_rolegate_predispatch.py`、`tests/governance/test_stamp_taskid_inject.py`、`tests/governance/test_verify_gate_b3.py`、`tests/governance/test_govb49_path_grant.py`、`docs/GOV_B49_ASBUILT_DELTA.md`｜
