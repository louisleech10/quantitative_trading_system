# TEMPLATE_GATE_FIX TODO — Adversarial Review（Composer 2.5）

審查對象：`docs/TEMPLATE_GATE_FIX_TODO.md`（交叉對照 `docs/TEMPLATE_GATE_FIX_SPEC.md`、`docs/TEMPLATE_GATE_FIX_MANIFEST.md`）  
PLAN：`handoffs/2026-07-04-template-review-RECONCILE.md`  
焦點：完整審查；重點＝SPEC↔TODO 交叉一致性＋TODO 可執行性  
前輪閉合：`handoffs/2026-07-04-TGF-SPEC-ADV-RECONCILE.md`（ADV-COMPOSER-12/13 重驗義務）

---

## Verdict：需修補後派工

TODO 整體忠實承接 SPEC v2 的 12 Task／29 manifest ID／13 fixture 矩陣；`coverage_check` 對 SPEC/TODO 皆 29/29 PASS；Task 1.1 的 13 檔清單與 SPEC 逐檔一致（含 `spec_ic_phase0_style.md`）。但 **§G/§A 殘留舊探針計數**、**Task 6.1 reconcile 觸發條件 SPEC↔TODO 分叉**、**§B mutation 批次 gate 不可機械執行**、**TODO §0 未滿足自身 Task 4.1/E-3 要求** 等問題會讓 B2/B4 執行端實作或驗收走樣。修補量小，不需重作 TODO。

---

## 前輪閉合重驗（閉合鐵律）

| Finding | RECHECK | 判定 |
|---------|---------|------|
| **ADV-COMPOSER-12** | `grep -c "3 繞過\|三個繞過" docs/TEMPLATE_GATE_FIX_SPEC.md` → **0**；但 §G L30 仍寫「重建 **4** 探針」、§A L17 仍寫「繞過探針計 **3** 支」（雖有括註擴充至 7，與 §G L32／Task 1.1 的 7+1+5 不一致） | **REOPEN**（字面舊計數未清乾淨，§G 與 F-1 未完全一致） |
| **ADV-COMPOSER-13** | `grep -c "MULTI_AGent" docs/TEMPLATE_GATE_FIX_MANIFEST.md` → **0** | **CLOSED** |

VERIFY（ADV-COMPOSER-12 殘留字面）:
```text
$ grep -n "4 探針\|計 3 支\|7 個繞過" docs/TEMPLATE_GATE_FIX_SPEC.md
17:  - Composer 委員會輪實跑之繞過探針計 3 支（...
30:- **凍結時機 / reference 設定**：... 重建 4 探針＋收集 ≥3 份 ...
32:- **通過條件（可證偽）**：... **[F-1] 所列全部 7 個繞過探針** ...
```

---

## Findings

### 挑戰前提（§0 優先）

**ID:ADV-COMPOSER-14 [MAJOR] 信心度:High** — TODO §0 **未滿足** 自身 Task 4.1／manifest [E-3] 將由 adversarial 強制檢查的「解耦 7 條＋不可違反原則相關子集」；本檔卻會被 B3 後的 adversarial 拿來驗收 epic。  
證據：TODO §0 L6 僅一句「解耦 7 條…天然不觸發」，未列 7 條規則、未列「只加強機檢／禁 fake data／禁弱化 gate」等本子集；Task 4.1 L120 要求 prompt §2 查「TODO §0 含解耦 7 條＋不可違反原則…缺 → MAJOR」。  
會怎麼失敗：B3 完成後對本 TODO 跑新一輪 adversarial → 自指 MAJOR → 無法 Frozen；執行端亦無 §0 可照抄的紅線清單。  
修法：§0 增緊湊子集（解耦 #1/#3/#5/#6 對本 epic +「只加強機檢」等 3–5 條），或 §0 明示「本 epic 適用子集＝…」並引用 AGENTS.md 章節。  
VERIFY:
```text
$ grep -n "解耦\|不可違反\|fake\|NaN" docs/TEMPLATE_GATE_FIX_TODO.md | head -6
6:- **只加強機檢...（解耦 7 條與資料紅線因此天然不觸發...
120:- ...TODO §0 含解耦 7 條＋不可違反原則相關子集...
（§0 無 7 條枚舉、無不可違反原則逐條）
```
RECHECK: `grep -cE "momentum/.*不 import|factories|只加強機檢|禁 fake|弱化.*gate" docs/TEMPLATE_GATE_FIX_TODO.md` ≥ 3（§0 段內）

---

**ID:ADV-COMPOSER-15 [BLOCKING] 信心度:High** — Task 6.1 **`--reconcile` 觸發條件 SPEC↔TODO 分叉**。  
證據：SPEC Task 6.1 L116「含 `[BLOCKING]` **或** `ID:` 格式 finding 時」→ `--reconcile` 必填；TODO Task 6.1 L144「含 `ID:` 格式 finding **且含** `[BLOCKING]`」→ 兩者同時才必填。  
會怎麼失敗：執行端照 TODO 實作 → 僅 MAJOR 且帶 `ID:` 的 adversarial 檔可無 reconcile 過 gate → 與 SPEC／reconcile U9 定案不符，MAJOR finding 可靜默未銷帳。  
修法：TODO Task 6.1 實作要點③改為與 SPEC 一致（`[BLOCKING]` 或 `ID:` 任一即觸發；建議與 SPEC 同句複製）。  
VERIFY:
```text
$ grep "reconcile" docs/TEMPLATE_GATE_FIX_SPEC.md | grep -oE "BLOCKING.*ID:|ID:.*BLOCKING"
BLOCKING]` 或 `ID:
$ grep "ID:" docs/TEMPLATE_GATE_FIX_TODO.md | grep 6.1 -A2 | head -1
③--adversarial 檔含 `ID:` 格式 finding 且含 `[BLOCKING]`
（TODO 多「且」，比 SPEC 窄）
```
RECHECK: `diff <(grep -A1 "②" docs/TEMPLATE_GATE_FIX_SPEC.md | tail -1) <(sed -n '144p' docs/TEMPLATE_GATE_FIX_TODO.md)` 觸發子句應等價

---

### SPEC↔TODO 交叉一致性

**ID:ADV-COMPOSER-16 [MAJOR] 信心度:High** — manifest [C-3] 仍寫「§2 加**兩條**必查」，SPEC／TODO Task 4.1 已擴為**三條**（含 [E-3] TODO §0）。  
證據：`docs/TEMPLATE_GATE_FIX_MANIFEST.md` L24 vs `docs/TEMPLATE_GATE_FIX_SPEC.md` L98／TODO L120。  
會怎麼失敗：`coverage_check` 只驗字串存在 → manifest 與實作語義漂移；派工者以 manifest 為準會漏 E-3 驗收。  
修法：manifest [C-3] 改三條並點名 E-3；或 [C-3] 改「見 Task 4.1 三條」避免再 drift。  
RECHECK: `grep -c "三條\|兩條" docs/TEMPLATE_GATE_FIX_MANIFEST.md docs/TEMPLATE_GATE_FIX_SPEC.md`

---

**ID:ADV-COMPOSER-17 [MAJOR] 信心度:High** — §G L30「重建 **4** 探針」與 Task 1.1／§G L32／TODO 1.2「13 fixture／7 繞過」**不同步**（ADV-COMPOSER-12 殘留）。  
證據：SPEC §G L30 vs L32；TODO 未複製此句故無矛盾，但 SPEC 內自相矛盾會誤導 B1 手填 EXPECTED。  
會怎麼失敗：執行端只讀 §G 凍結段 → 建 4 探針 + 9 正樣本 → EXPECTED 行數／exit 矩陣錯 → 假綠或永紅。  
修法：§G L30 改「重建 Task 1.1 所列 13 fixture（7 繞過＋1 pending＋5 正樣本）」；§A L17 歷史句改「初版 3 支，現 F-1 共 7 支」或移入 footnote。  
RECHECK: `grep -c "4 探針" docs/TEMPLATE_GATE_FIX_SPEC.md` = 0；`grep -c "7 個繞過\|13 fixture" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥ 2

---

**ID:ADV-COMPOSER-18 [MINOR] 信心度:High** — TODO 狀態 **DRAFT**（L1）與文末「現狀=**Internal Frozen**」（L203）互斥。  
證據：TODO L1 vs L203。  
會怎麼失敗：gate／執行端不知可否派 B1。  
修法：統一為 DRAFT（adversarial 前）或 Frozen（修補後）；刪另一處。  
RECHECK: `head -1 docs/TEMPLATE_GATE_FIX_TODO.md; tail -3 docs/TEMPLATE_GATE_FIX_TODO.md`

---

**ID:ADV-COMPOSER-19 [MINOR] 信心度:High** — SPEC 頭注仍寫「對應 TODO：…（**待生成**）」而 TODO 已存在。  
證據：`docs/TEMPLATE_GATE_FIX_SPEC.md` L3。  
RECHECK: `grep "待生成" docs/TEMPLATE_GATE_FIX_SPEC.md` = 0

---

### TODO 可執行性（§B 批次＋Task 12 忠實度）

**ID:ADV-COMPOSER-20 [MAJOR] 信心度:High** — §B **B2→B3 批次 gate**「4 條 mutation case **各轉紅**」無單一可執行命令，與 Task 2.1–2.4 分散驗收脫節。  
證據：TODO §B L23「B2→B3 gate＝…`test_template_check.sh` = 0 **且 4 條 mutation case 各轉紅**」；Task 1.2 L44「MUTATION.txt 先建骨架…**B2 填 case**」；`scripts/test_template_check.sh`／`tests/gate_fixtures/` **尚不存在**（`ls tests/gate_fixtures` → No such file or directory）。  
會怎麼失敗：B2 執行端跑矩陣全綠即宣稱過 gate，跳過 4 次「改壞一字元」；A-3/A-4/A-5 回歸 oracle 空洞。  
修法：§B 增明確 gate 命令，例如「`for id in A-1 A-3 A-4 A-5; do bash scripts/test_template_check.sh --mutate $id; test $? -ne 0 || exit 1; done`」或在 Task 1.2 規定 `--mutate` 讀 MUTATION.txt；B2 prompt 逐條列 4 個改壞點檔名／行號。  
VERIFY:
```text
$ ls tests/gate_fixtures 2>&1
ls: tests/gate_fixtures: No such file or directory
$ ls scripts/test_template_check.sh 2>&1
ls: scripts/test_template_check.sh: No such file or directory
```
RECHECK: Phase 1 完成後 `bash scripts/test_template_check.sh --mutate-all; echo $?` 在破壞態非 0、還原後 0

---

**ID:ADV-COMPOSER-21 [MAJOR] 信心度:Medium** — §B **B4「6.2 部分可先行」**未在 SPEC §P 展開，與「Phase 6 依賴 Phase 2 矩陣綠」並存，派工邊界模糊。  
證據：TODO §B L21「6.2 部分可先行」；SPEC §P L113 僅「依賴 Phase 2（探針矩陣綠）；D-3 可先行」——**未說明** 6.2 哪一段可先行、是否允許在 B2 前跑 grandfather 掃描。  
會怎麼失敗：B4 agent 用舊 template_check 掃 docs/ 產 GRANDFATHER → 清單與 B2 後機檢不一致；或與 6.1 gate 改動交錯 revert 困難。  
修法：SPEC Task 6.2 或 TODO §B 寫死「可先行＝僅 D-3 舊錨點 7 處替換；F-3 盤點必須在 B2 之後」。  
RECHECK: `grep -n "可先行\|先行" docs/TEMPLATE_GATE_FIX_SPEC.md docs/TEMPLATE_GATE_FIX_TODO.md`

---

**ID:ADV-COMPOSER-22 [MINOR] 信心度:Medium** — Task 3.2 行數預算 **基線錯誤**：TODO L113「現 **61**＋增幅 ≤12」；實測 `wc -l templates/SPEC_TEMPLATE.md` = **60**。  
會怎麼失敗：B3 驗收 `wc -l ≤ 75` 仍過，但基線漂移使「≤12 行增幅」約束不可稽核。  
VERIFY:
```text
$ wc -l < templates/SPEC_TEMPLATE.md
60
```
RECHECK: TODO Task 3.2 驗證欄基線改 60 或改為 `$(wc -l)+12` 動態敘述

---

**ID:ADV-COMPOSER-23 [MINOR] 信心度:Medium** — Task 6.1 TODO 獨有邊界「`--reconcile` 給了但 adversarial 無 BLOCKING → 僅 WARN」**未出現在 SPEC**，下游行為不可從 SPEC 推導。  
證據：TODO Task 6.1 L147 vs SPEC Task 6.1（無此句）。  
RECHECK: 若要保留，回寫 SPEC Task 6.1 邊界；否則刪 TODO 獨有句

---

### 專項：Task 12 忠實度（前輪 SPEC adversarial 11+2 條修法）

| 前輪 ID | TODO 落點 | 判定 |
|---------|-----------|------|
| ADV-COMPOSER-1～11 | Task 1.1–6.2／附錄 M 均覆蓋 | **忠實** |
| ADV-COMPOSER-12 | §G L30／§A L17 舊計數仍在 SPEC；TODO 1.2 手填敘述正確（7+1+5） | **SPEC 未閉合；TODO 無走樣** |
| ADV-COMPOSER-13 | manifest 已修正 | **CLOSED** |
| 衍生 | Task 6.1 reconcile 觸發見 ADV-COMPOSER-15 | **TODO 走樣** |

**Task 1.1 fixture 13 檔**：SPEC 與 TODO 清單 **set 相等**（含 `spec_ic_phase0_style.md`；注意檔名含數字 `0`，naive `[a-z_]+` 正則會漏計）。  
VERIFY:
```text
$ python3 -c "import re; ..."  # digit-aware parse
docs/TEMPLATE_GATE_FIX_SPEC.md count 13
docs/TEMPLATE_GATE_FIX_TODO.md count 13
（13 檔名列表一致）
```

---

### §1 必查十類（摘要）

| 類別 | 結論 |
|------|------|
| 1 矛盾/互斥 | **有** — ADV-COMPOSER-15/17/18/21 |
| 2 漏項/端到端 | **有** — ADV-COMPOSER-14（§0 子集）；MUTATION 批次 gate 漏命令（ADV-20） |
| 3 不可測驗收 | **有** — B2→B3 mutation gate 不可機械驗（ADV-20） |
| 4 可疑 quant 假設 | **無** |
| 5 過度工程 | **無** |
| 6 OOM/並行 | **無** |
| 7 Cache 正確性 | **無** |
| 8 API/型別/相容 | **有（輕）** — ADV-COMPOSER-15 gate CLI 語義 |
| 9 測試品質 | **有** — 現行機檢繞過仍實證（見下 VERIFY）；TODO 正確要求 Phase 1/2 固化 |
| 10 Agent 可執行性 | **有** — §B 批次 gate 部分不可執行（ADV-20/21） |

### §2 範本錨點 + 獵空殼

- **TODO 錨點**：§0/§B、12×Task 均含驗證／邊界／不可做 — **非空殼**（`template_check.sh todo` exit 0）。
- **獵空殼**：§B 批次 gate 一句「mutation 各轉紅」**無實質命令** → 列 ADV-COMPOSER-20。
- **coverage_check**：SPEC/TODO 各 29/29 PASS（**僅 ID presence**）。

### §3 不可違反原則

- TODO §0「只加強機檢」與 SPEC §C 一致。**無違反**。

---

## 機檢實跑 VERIFY（現行繞過仍成立，支撐 Phase 1/2 必要性）

```text
$ bash scripts/template_check.sh spec docs/TEMPLATE_GATE_FIX_SPEC.md; echo rc=$?
TEMPLATE PASS ...
rc=0

$ bash scripts/template_check.sh todo docs/TEMPLATE_GATE_FIX_TODO.md; echo rc=$?
TEMPLATE PASS ...
rc=0

$ bash scripts/template_check.sh spec docs/IC_PHASE0_SPEC.md; echo rc=$?
TEMPLATE PASS ...
rc=0

$ # Codex ADV-C1 探針（全錨點 + 標題下 bullet 無 FACT-RECEIPT）
$ bash scripts/template_check.sh spec $tmpdir/spec_heading_verified_bypass.md; echo rc=$?
TEMPLATE PASS ...
rc=0

$ # RISK-HIT:a,d + §N §G N/A（現行機檢未聯動）
$ bash scripts/template_check.sh spec $tmpdir/spec_highrisk_no_g.md; echo rc=$?
TEMPLATE PASS ...
rc=0

$ bash scripts/coverage_check.sh docs/TEMPLATE_GATE_FIX_MANIFEST.md docs/TEMPLATE_GATE_FIX_TODO.md; echo rc=$?
COVERAGE PASS: ... 29 項。
rc=0
```

---

## 被當成事實的未驗證假設（§0）

1. **「TODO 已 Internal Frozen」** — 頭注 DRAFT，僅文末一句（ADV-COMPOSER-18）。
2. **「B2→B3 gate 可照 §B 一句驗收」** — mutation 四 case 無聚合命令（ADV-COMPOSER-20）。
3. **「執行端讀 SPEC 與 TODO 得到相同 reconcile 契約」** — 已證偽分叉（ADV-COMPOSER-15）。
4. **「§0 已滿足 E-3 將要求的解耦子集」** — 未列舉，僅一句帶過（ADV-COMPOSER-14）。

---

## 修補優先序（建議）

1. **ADV-COMPOSER-15** — Task 6.1 reconcile 觸發與 SPEC 对齐（BLOCKING）
2. **ADV-COMPOSER-12/17** — SPEC §G L30、§A L17 探針計數統一為 F-1 七支＋13 fixture
3. **ADV-COMPOSER-14** — TODO §0 補解耦／不可違反子集（否則 Frozen 前自撞 E-3）
4. **ADV-COMPOSER-20** — §B／Task 1.2 補 mutation 批次驗收命令
5. **ADV-COMPOSER-16/18/19/21/22/23** — 文檔一致性收尾

---

HANDOFF_NOT_UPDATED: adversarial 委員會任務；依合約寫入本檔，不覆寫根 HANDOFF.md。

STATUS: DONE
