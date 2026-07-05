# TGF TODO Adversarial RECONCILE（2026-07-04）

對象：docs/TEMPLATE_GATE_FIX_SPEC.md（v3）＋ docs/TEMPLATE_GATE_FIX_TODO.md（v2）＋ docs/TEMPLATE_GATE_FIX_MANIFEST.md。
兩家 findings（Codex 5＋Composer 10＋REOPEN 1）全數 ACCEPTED。機檢：spec/todo 的 template_check 與 coverage 四道全 exit 0。

## 對映表（[ID] → [修補位置] → [RECHECK]）

| Finding ID | 級別 | 修補位置 | RECHECK |
|---|---|---|---|
| ADV-CODEX-5 ＝ ADV-COMPOSER-15 | BLOCKING | TODO Task 6.1 ③改「含 `[BLOCKING]` 或 `ID:` 任一」與 SPEC 同句；④同步改「無 ID 且無 BLOCKING」 | 〔RECHECK 修正版，原 pattern 未計 Markdown 粗體，Codex 退回有理〕`grep -cE "BLOCKING.*或.*ID:" docs/TEMPLATE_GATE_FIX_TODO.md` ≥1（Claude 實跑=1） |
| ADV-CODEX-6 | MAJOR | SPEC＋TODO Task 6.1：5 個 gate fixture 路徑寫死＋GATE_DIR_OVERRIDE 高風險完整命令為主驗收，低風險 smoke 降為 token 回歸 | 〔RECHECK 修正版，原 grep -c 計行數而兩處同行〕`grep -o "GATE_DIR_OVERRIDE" docs/TEMPLATE_GATE_FIX_TODO.md \| wc -l` ≥2（Claude 實跑=2）；`grep -c "gate_id_major_no_reconcile" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1（Claude 實跑=1） |
| ADV-CODEX-7 ＝ ADV-COMPOSER-22 | MAJOR | TODO Task 3.2 驗證改 delta 制（基線凍結 60，`test $((after-before)) -le 13`） | `grep -c "before=60" docs/TEMPLATE_GATE_FIX_TODO.md` ≥1；`grep -c "≤ 75" docs/TEMPLATE_GATE_FIX_TODO.md` = 0 |
| ADV-CODEX-8 ＝ ADV-COMPOSER-20 | MAJOR | TODO Task 1.2 ⑦ 定 `--mutate <id>` 契約（sed 破壞→紅→還原→綠→git diff 淨）；§B B2→B3 gate 改可執行迴圈；Task 2.1–2.4 mutation 驗證統一用 `--mutate A-*` | `grep -c -- "--mutate" docs/TEMPLATE_GATE_FIX_TODO.md` ≥6 |
| ADV-CODEX-9 | MAJOR | TODO 頭註加 `WAIVER: TODO_GEN_STAGE0_DEVIATION`（補償控制＋本輪雙戳記即核可） | `grep -c "WAIVER: TODO_GEN_STAGE0_DEVIATION" docs/TEMPLATE_GATE_FIX_TODO.md` = 1 |
| ADV-COMPOSER-12（REOPEN） | MAJOR | SPEC §G「重建 4 探針」改「Task 1.1 所列 13 fixture」；§A「計 3 支」字面移除 | `grep -c "4 探針\|計 3 支\|三個繞過\|3 繞過" docs/TEMPLATE_GATE_FIX_SPEC.md` = 0 |
| ADV-COMPOSER-14 | MAJOR | TODO §0 加「本 epic 適用之解耦/紅線子集」枚舉 4 條（E-3 自撞消解） | `grep -cE "禁 fake|越界寫入|只加強機檢|factories" docs/TEMPLATE_GATE_FIX_TODO.md` ≥4 |
| ADV-COMPOSER-16 | MAJOR | manifest [C-3] 改三條並點名 [E-3] | `grep -c "三條" docs/TEMPLATE_GATE_FIX_MANIFEST.md` ≥1 |
| ADV-COMPOSER-17 | MAJOR | 同 ADV-COMPOSER-12（§G 凍結段） | 同上 |
| ADV-COMPOSER-18 | MINOR | TODO 末行改「現狀=DRAFT，與頭部狀態一致」 | `grep -c "Internal Frozen" docs/TEMPLATE_GATE_FIX_TODO.md` = 0 |
| ADV-COMPOSER-19 | MINOR | SPEC 頭注「待生成」→「已生成」 | `grep -c "待生成" docs/TEMPLATE_GATE_FIX_SPEC.md` = 0 |
| ADV-COMPOSER-21 | MAJOR | SPEC Phase 6 標題＋TODO §B B4 列寫死「可先行僅限 [D-3]；[F-3] 必須 B2 後」 | `grep -c "可先行部分僅限" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |
| ADV-COMPOSER-23 | MINOR | SPEC Task 6.1 邊界回寫「--reconcile 給了但無 BLOCKING/ID → 僅 WARN」 | `grep -c "僅 WARN 不拒發" docs/TEMPLATE_GATE_FIX_SPEC.md` ≥1 |

ADV-COMPOSER-13：前輪已 CLOSED（Composer 本輪確認）。
ADV-COMPOSER-24（Composer 閉合輪新增，MINOR）：TODO 四處「四例/4 gate fixture」已全改 5＋exit 序列 1/1/1/1/0；RECHECK `grep -c "四例\|4 gate fixture\|gate fixture 4" docs/TEMPLATE_GATE_FIX_TODO.md` = 0（Claude 實跑=0，待 Composer 於下輪任一互動確認）。

## 請兩位委員做的事（閉合鐵律：原提出方重驗）
1. 逐條重跑**你自己提出**之 finding 的 RECHECK（Codex：5..9；Composer：12 REOPEN、14..23）。
2. 全部真關閉 → append `RECONCILE-STAMP: <CODEX|COMPOSER> APPROVED 2026-07-04`；否則 append REJECTED＋ID＋理由。
3. 戳記即同時核可 WAIVER: TODO_GEN_STAGE0_DEVIATION（ADV-CODEX-9 之處置）。
4. 本輪後 SPEC/TODO 若無 REJECTED 即改 Frozen 進實作派工（Composer 實作 B1–B4、Codex code review）。

---
## 閉合重驗紀錄（歷史區；canonical 戳記見文末「## 戳記」。原始戳記行加 HISTORY 前綴避免與機檢衝突，內容一字未改）

## Composer 2.5 閉合重驗（2026-07-04）

| ID | RECHECK 結果 | 判定 |
|---|---|---|
| ADV-COMPOSER-12 REOPEN | `4 探針\|計 3 支\|…` = 0；`7 個繞過\|13 fixture` = 2；§G L30 已改 Task 1.1 全 13 fixture | **CLOSED** |
| ADV-COMPOSER-14 | `grep -cE "禁 fake\|…\|factories"` = 3 行（L8 同列多關鍵詞）；§0 L8 已枚舉 ①–④ 四條子集含 #1/#6/fake/NaN/factories | **CLOSED**（實質；機械 ≥4 因同行多詞未達，非漏修） |
| ADV-COMPOSER-15 | 字面 `或 .ID:.` = 0（`**或**` markdown）；`或.*ID:.*任一` = 1；TODO L146 與 SPEC L116「或」語義一致 | **CLOSED** |
| ADV-COMPOSER-16 | manifest `三條` = 1、`兩條` = 0；[C-3] 點名 [E-3] | **CLOSED** |
| ADV-COMPOSER-17 | 同 12 | **CLOSED** |
| ADV-COMPOSER-18 | `Internal Frozen` = 0；末行 `現狀=DRAFT，與頭部狀態一致` | **CLOSED** |
| ADV-COMPOSER-19 | `待生成` = 0；頭注 `已生成` | **CLOSED** |
| ADV-COMPOSER-20 | `--mutate` = 6；§B L25 for-loop + Task 1.2 L46 契約齊 | **CLOSED** |
| ADV-COMPOSER-21 | SPEC `可先行部分僅限` = 1；TODO §B L23 對齊 [D-3]/[F-3] | **CLOSED** |
| ADV-COMPOSER-22 | `before=60` = 1；`≤ 75` = 0 | **CLOSED** |
| ADV-COMPOSER-23 | SPEC `僅 WARN 不拒發` = 1（L118） | **CLOSED** |

附驗：`template_check` spec/todo exit 0；`coverage_check` 29/29 PASS。WAIVER 行 = 1。

### 新引入（本輪，不阻閉合）

**ADV-COMPOSER-24 [MINOR]** — ADV-CODEX-6 增第 5 gate fixture 後，TODO 仍殘留「四例/4」：L29 B4 prompt、L145 輸入輸出、L167 總表、L202 合計數（Task 6.1 驗證欄與 §B L25 已正確寫 5）。派工可能少建 `gate_id_major_no_reconcile.md`。修法：四處改 5＋exit 序列 1/1/1/1/0。

HISTORY | RECONCILE-STAMP: COMPOSER APPROVED 2026-07-04
（同時核可 WAIVER: TODO_GEN_STAGE0_DEVIATION）

HISTORY | RECONCILE-STAMP: CODEX REJECTED 2026-07-04
REJECTED: ADV-CODEX-5 — 指定 RECHECK `grep -c "或 .ID:. 格式 finding 任一" docs/TEMPLATE_GATE_FIX_TODO.md` 回傳 0；TODO Task 6.1 語義上已有 `[BLOCKING]` 或 `ID:` 任一，但 Markdown 粗體標記使 reconcile 表的精確 grep 不成立。
REJECTED: ADV-CODEX-6 — 指定 RECHECK `grep -c "GATE_DIR_OVERRIDE" docs/TEMPLATE_GATE_FIX_TODO.md` 回傳 1，未達 ≥2；TODO 同一行內語義上已有 high-risk 主驗收與 low-risk smoke 兩個 `GATE_DIR_OVERRIDE`，但 reconcile 表的 `grep -c` 計行數，精確 RECHECK 不成立。`grep -c "gate_id_major_no_reconcile" docs/TEMPLATE_GATE_FIX_SPEC.md` 回傳 1。ADV-CODEX-7..9 recheck 通過；template_check/coverage_check for SPEC/TODO 均 exit 0。WAIVER: TODO_GEN_STAGE0_DEVIATION 未由 Codex 戳記核可。

HISTORY | RECONCILE-STAMP: CODEX APPROVED 2026-07-05（缺 sha256/task 欄位，由文末 canonical 戳記取代）

## 機檢處置索引（D-2 逐 ID 同行處置；語義詳見上方對映表與各輪 RECHECK 紀錄）
- ADV-CODEX-5 → TODO Task 6.1 ③「或」語義與 SPEC 同句（CLOSED，Codex 重驗）
- ADV-CODEX-6 → SPEC＋TODO Task 6.1 五 fixture＋GATE_DIR_OVERRIDE 主驗收（CLOSED，Codex 重驗）
- ADV-CODEX-7 → TODO Task 3.2 delta 制基線 60（CLOSED，Codex 重驗）
- ADV-CODEX-8 → TODO Task 1.2 ⑦ --mutate 契約＋§B 迴圈 gate（CLOSED，Codex 重驗）
- ADV-CODEX-9 → TODO 頭註 WAIVER 行＋雙戳記核可（CLOSED，Codex 重驗）
- ADV-COMPOSER-1 → SPEC 輪已閉合（見 handoffs/2026-07-04-TGF-SPEC-ADV-RECONCILE.md；本檔僅忠實度表引用）
- ADV-COMPOSER-12 → SPEC §G 13 fixture 統一＋§A 計數字面移除（REOPEN 後 CLOSED，Composer 重驗）
- ADV-COMPOSER-13 → manifest 檔名 typo 已修（CLOSED，Composer 確認）
- ADV-COMPOSER-14 → TODO §0 解耦/紅線子集枚舉 4 條（CLOSED，Composer 重驗）
- ADV-COMPOSER-15 → 同 ADV-CODEX-5（CLOSED）
- ADV-COMPOSER-16 → manifest [C-3] 三條並點名 [E-3]（CLOSED，Composer 重驗）
- ADV-COMPOSER-17 → 同 ADV-COMPOSER-12（CLOSED）
- ADV-COMPOSER-18 → TODO 狀態頭尾一致（CLOSED，Composer 重驗）
- ADV-COMPOSER-19 → SPEC 頭注「已生成」（CLOSED，Composer 重驗）
- ADV-COMPOSER-20 → 同 ADV-CODEX-8（CLOSED）
- ADV-COMPOSER-21 → 可先行僅限 [D-3]、[F-3] 必須 B2 後（CLOSED，Composer 重驗）
- ADV-COMPOSER-22 → 同 ADV-CODEX-7（CLOSED）
- ADV-COMPOSER-23 → SPEC Task 6.1 邊界 WARN 句回寫（CLOSED，Composer 重驗）
- ADV-COMPOSER-24 → TODO 四處 gate fixture 計數改 5（CLOSED，Claude 修＋Composer 於 canonical 戳記輪確認）

## 戳記
<!-- canonical 戳記區：委員 append '^RECONCILE-STAMP: <family> APPROVED <date> sha256:<body-hash> task:<task-id>'；本體雜湊=本標題之前全部內容 -->
RECONCILE-STAMP: codex APPROVED 2026-07-05 sha256:9d9c51751557eb9fe6f730d7631bd6fca1b7e6988e9197dd28a63a5d34a3ce44 task:tgf-todo-stamp-codex-r3
RECONCILE-STAMP: composer APPROVED 2026-07-05 sha256:9d9c51751557eb9fe6f730d7631bd6fca1b7e6988e9197dd28a63a5d34a3ce44 task:tgf-todo-stamp-composer-r3
RECONCILE-STAMP: codex APPROVED 2026-07-05 sha256:88d3078f252eb4ea46a18a39f4ccd07f14a02b5dc8b17e708d9c630de27bc5b5 task:tgf-todo-stamp-codex-r4
RECONCILE-STAMP: composer APPROVED 2026-07-05 sha256:88d3078f252eb4ea46a18a39f4ccd07f14a02b5dc8b17e708d9c630de27bc5b5 task:tgf-todo-stamp-composer-r4
