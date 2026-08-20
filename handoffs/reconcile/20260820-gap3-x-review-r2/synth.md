# Reconcile — 20260820-gap3-x-review-r2

**來源** 20260820-gap3-spec-r2-codex.md, 20260820-gap3-spec-r2-composer.md, 20260820-gap3-spec-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

三家共 **8 條** headings（codex 6 條 MAJOR＋composer/grok 各 1 條 **sentinel 0-findings**），下列六群集＋sentinel 節引用全部 8 條，0 掉項。
標的＝`docs/GAP3_EVENT_SPEC.md` @ 21135434（#9f63e290e89a）。閉合統計：R1 15 條中 **12 條三家判 CLOSED**（composer 2/2、grok 5/5、codex 5/8）；codex 3 條 NOT-CLOSED（P0-01→Y1、P1-03→Y2/Y3、P1-07→Y4/Y5）＋1 條衍生（P1-08→Y6）。
分歧處置（看碼證不數人頭）：composer/grok 判「可進 stamp」、codex 判「需修補」——主委逐條驗 codex 六條碼證**全部成立**（行號複核無誤），採較嚴版：六群集全數寫回後派 R3 閉合輪（codex 為原提出方複驗；composer/grok sentinel 確認無新錯）。收斂趨勢 15→6，未觸兩輪斷路器。

Verdict：**需修補後合併**——Y1–Y6 寫回 SPEC 後派 R3；composer/grok 之 sentinel（COMPOSER-R2-P3-00, GROK-R2-P3-00）確認 X1–X13 寫回無漂移、R1 己方 findings 全 CLOSED，此結論**保留**（Y1–Y6 均為 codex 新攻擊面，非寫回漂移）。

### Y1 — entry 語意 → bar/price 唯一映射缺失（codex 唯一提出；R1 P0-01 殘餘）
**引用**: CODEX-R2-P1-01
**處置＝改 §0 D1 加 D1-6 映射表＋D2-4 receipt 增欄＋B2.1／§G-2**：每個 `entry_price_semantic` 值寫死 bar identity＋price 欄：`trigger_open`＝t₀ bar 之 open；`trigger_close`＝t₀ bar 之 close；`next_open`＝t₀ 之後下一根**錨定 TF** bar 之 open；`decision_bar_open`／`decision_bar_close`＝decision bar（t₀−k）之 open／close。`entry_at`＝該 bar 對應時點（open 語意＝bar open_time、close 語意＝bar close_time），validator 檢 `decision_at ≤ entry_at`。receipt 增 `entry_at_ms`＋`entry_price_source{bar_open_ms, field}`。B2.1「entry 依契約語意」改指向 D1-6。§G-2 oracle 涵蓋 k=0／k>0／`next_open` 三形手算。

### Y2 — 反例分類公式與預設值未寫死（codex 唯一提出；R1 P1-03 殘餘）
**引用**: CODEX-R2-P1-02
**處置＝改 Task B1.5（公式為規格、數值為可調預設）**：direction 符號 `dir∈{+1(long),−1(short)}`；`R0 = dir·(close_t0−open_t0)/open_t0`（t₀ 自身走勢）、`Rw = dir·(close_labelEnd−close_t0)/close_t0`（答案窗走勢；錨＝t₀ close，同 D1；window aggregation＝label window 末 close）。分類（僅 `label=0`）：a（同觸發不續漲）＝`R0 ≥ trigger_threshold ∧ Rw ≤ follow_threshold`；b（震盪）＝`|R0| ≤ range_threshold`；c（反向）＝`R0 ≤ −drop_threshold`。預設（可調；唯一列舉處＝契約檔 `counterexample_classifier_config`）：`trigger_threshold=0.05`、`follow_threshold=0.0`、`range_threshold=0.01`、`drop_threshold=0.05`（源＝使用者 §2-4 原例：漲≥5%／上下 1%／跌 x%）。同時滿足多條 ⇒ `unclassifiable`（X4 不變）。B1.5 驗證增 boundary fixtures：每門檻 `=`、`±ε(1e-9)` 三點落位 exact。

### Y3 — `unclassifiable` 值集歸屬（codex 唯一提出）
**引用**: CODEX-R2-P1-03
**處置＝改 Task B1.0／B1.5／B2.2**：匯入欄 `counterexample_kind` 值集維持 `{a_trigger_no_follow, b_range, c_drop}`（僅使用者填）；分類器輸出為**derived 欄** `counterexample_kind_effective ∈ {a_trigger_no_follow, b_range, c_drop, unclassifiable}`（住 manifest，非匯入欄；兩值集皆字面入契約檔）；分層報表一律消費 derived 欄；`unclassifiable` **不進**分層分母、單獨列 `n_unclassifiable`；validator 對匯入欄出現 `unclassifiable` ⇒ 拒（非使用者值）。

### Y4 — mutation 逐條可執行化（codex 唯一提出；R1 P1-07 殘餘）
**引用**: CODEX-R2-P1-04
**處置＝改 §V**：每條 M 補（i）固定命令 `venv/bin/python -m pytest tests/momentum/event_samples/test_mutation_guard.py -q -k M<n>`（ii）fixture 身分：M1/M2/M4/M9＝真實 kline `tests/golden/la0/inputs/` 既有 fixture＋固定事件表（seed 20260820）、M3/M5–M8/M10–M12＝合成事件表（seed 20260820＋序號；章程 §F 合法——非價格）（iii）baseline 預期輸出（受測斷言之具體值/狀態）（iv）mutation diff 一句。**誠實邊界明寫**：fixture 之 sha256 digest 於首次建立時記入 `handoffs/run_receipts/gap3_mutation_fixtures.json`（SPEC 無法預寫尚不存在檔案之 digest——那是 receipt 不是規格）；「TODO 展開」字樣刪除，改「TODO 逐字抄本表、不得增刪」。

### Y5 — M8／B1.4 chance-level oracle 依統計種類定 null（codex 唯一提出）
**引用**: CODEX-R2-P1-05
**處置＝改 Task B1.4＋§V M8**：棄近似 CI 式，統一為 **permutation quantile oracle**：固定 seed、`N_perm=1000`，對每 `statistic_kind` 以置亂分布之 `[q_{0.025}, q_{0.975}]` 為帶——binary_discrimination（AUC null 中心 0.5、PR-AUC null 中心＝prevalence，皆由置亂分布自然給出，不用解析式）；conditional_ic（IC null 中心 0）。pass/fail exact：置亂後觀測統計量落帶內＝oracle 綠；恆等排列 mutation ⇒ 必紅（M8 保留）。

### Y6 — control_kind validator 矛盾解除（codex 唯一提出；X13 殘餘）
**引用**: CODEX-R2-P1-06
**處置＝改 Task B1.0**：validator 之 accepted 值集寫死＝`{user_labeled_same_trigger, user_labeled_other, platform_same_trigger_rule}`；`platform_random_bars` 在 schema 閉集但 validator **拒收** reason=`not_implemented_platform_random_bars`（§N-7 解除前恆拒）。「v1 只實作 user_labeled_*」改寫為「**B1 批只有 user_labeled_* 生產者**；`platform_same_trigger_rule` 自 B3.2 起由產生器產出、過**同一** validator（無 profile 分裂、無版本切換）」。B3.2 整合 oracle 維持。

### sentinel 節 — composer/grok 0-findings 收錄
**引用**: COMPOSER-R2-P3-00, GROK-R2-P3-00
兩家 sentinel 確認：X1–X13 寫回忠實（0 掉項、0 反向裁決、0 主委抄寫漂移）；己方 R1 findings 全 CLOSED；AR 裁決與各家原意相容（grok 明示 AR-6 屬多數否決少數、不重開）；D1-5↔D2-2、B1.6 順序、M1–M12、§N-7/8 sweep 無新錯。此結論與 Y1–Y6 不衝突（不同攻擊面），一併保留入卷。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P1-01
**斷言**: R1 P0-01 只閉合了 t₀−k 的 offset representation；`entry_at` 與五種 `entry_price_semantic` 到實際 bar/price 的唯一映射仍未成為可驗收契約，故 B2.1 的 `entry` 仍可由 agent 自行解讀。 **碼證**: `rg -n 'entry_at|entry_price_semantic|next_open|decision_bar_' docs/GAP3_EVENT_SPEC.md` → D1-1 有值集、D2-1 有 `entry_at` invariant，但 D2-4 receipt 不含 `entry_at`/entry price，B2.1 僅寫「entry 依契約語意」；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → PASS, rc=0（只證錨點）。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：補齊每個 semantic 的 bar identity/open-close price、`entry_at` 推導與 receipt oracle，並納入 k=0/k>0/next-open 邊界。
## CODEX-R2-P1-02
**斷言**: R1 P1-03 未閉合：AR-2 仍沒有 direction-aware signed-return 的精確公式、答案窗聚合、a/b/c 門檻的實際單位/預設值與 contract schema；實作者仍須發明分類規則。 **碼證**: `sed -n '121,125p;179,185p' docs/GAP3_EVENT_SPEC.md` → 僅見「門檻/單位/預設值」占位與 a「不續漲」/b「震盪」/c「反向」，沒有數值或公式；驗證只要求 exact boundary，未給 boundary oracle。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：在唯一 JSON SoT 寫死公式、單位、預設、window aggregation、所有 boundary/conflict fixtures，否則 B1.5/B2.2 不可重現。
## CODEX-R2-P1-03
**斷言**: X4 導入的 `unclassifiable` 沒有納入 `counterexample_kind` 的契約值集或獨立 derived/output 欄；schema 只列 a/b/c，但分類器與分層報表又會產生並消費 `unclassifiable`，可導致 validator reject、遺失或誤納分母。 **碼證**: `rg -n -C 2 'counterexample_kind|unclassifiable' docs/GAP3_EVENT_SPEC.md` → line 123 為 `(a/b/c)`，lines 183–185 產生 `unclassifiable`，line 42/220 仍以 `counterexample_kind` 分層；無 output schema/closed-set 定義。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：明確將 `unclassifiable` 放入契約或另立 derived classifier result，並固定 validator、分母與持久化欄位語意。
## CODEX-R2-P1-04
**斷言**: R1 P1-07 的 mutation contract 仍未逐條可執行：M1–M12 沒有各自的 command、fixture/input digest、baseline receipt 與 exact expected output；「TODO 展開」不能作為本輪 SPEC 的可證偽 gate。 **碼證**: `sed -n '356,370p' docs/GAP3_EVENT_SPEC.md` → line 358 將 digest/逐條命令延後 TODO；M3/M7/M9–M12 沒有明確 baseline/fixture digest/命令，僅寫紅或 `rc!=0`。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：每個 M 項補可執行命令、真實/固定 fixture digest、baseline output、mutation diff、expected rc/output；再由 TODO 逐字展開。
## CODEX-R2-P1-05
**斷言**: M8 的 `|stat| < z/sqrt(n_test)`「類」CI 式不能作為 AUC、PR-AUC、conditional IC 的共同 chance-level oracle，且不是 exact 判定；它可能把壞 oracle 判綠或把正確結果判紅。 **碼證**: `sed -n '172,174p;358,370p' docs/GAP3_EVENT_SPEC.md` → B1.4/§V 對全統計套同一近似式，文字明寫「類」且未以 AUC=0.5、PR-AUC=prevalence、IC=0 的 metric-specific null/variance 定義；`template_check` 仍只回 PASS。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：按 statistic_kind 固定 null、seed、class/prevalence-aware CI 或 permutation quantile，並寫 exact pass/fail oracle。
## CODEX-R2-P1-06
**斷言**: X13 的 scope 拆分留下 validator 矛盾：B1.0 宣告 v1 只實作 `user_labeled_*`，但 B3.2 在同一 v1 SPEC 啟用 `platform_same_trigger_rule` 並要求產出直接通過 B1.0 validator；B3.2 可能被自身 validator 拒絕。 **碼證**: `rg -n -C 2 'control_kind|platform_same_trigger_rule|v1.*user_labeled|validator' docs/GAP3_EVENT_SPEC.md` → lines 122、277–278 同時出現兩條要求，沒有 validator mode/version boundary 或 accepted-value exception。 **來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a [MAJOR, 信心度=High]：明確把 platform_same_trigger_rule 納入 B1.0 accepted schema，或將 B3.2 產出 validator profile 與 v1 import profile 分開並加整合 oracle。
## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無需阻擋收斂的實質 finding；R1 兩條 MAJOR 均已 CLOSED，X1–X13 寫回忠實，殘餘 sweep 五面未見新錯。

**碼證**: `sha256sum docs/GAP3_EVENT_SPEC.md` → `9f63e290…` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`rg -n "cluster_weight = 1/n_events_in_time_cluster|依賴：\*\*B1＋B2\.5|禁平行實作|unclassifiable|B1\.6"` → 命中 B1.3/B3/B1.5/B1 批內順序；`git diff e0af4a3d..21135434 -- docs/GAP3_EVENT_SPEC.md` → 224 行修訂對齊 synth 十三群集。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a; handoffs/reconcile/20260820-gap3-x-review-r1/synth.md

sentinel：0 findings（實質）；上列為 R2 閉合＋synth 忠實度＋殘餘 sweep 之機械複驗摘要。

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；R1 本家五條（P1-01..03／P2-04..05）對修訂版 SPEC 皆 CLOSED，X1–X13 寫回無實質語意漂移，殘餘 sweep（D1-5↔D2-2、B1.6 順序、X6 共同約束、M1–M12、§N-7/8）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `9f63e290e89a…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`；`grep`/讀檔：D1-5=:26、B3 依賴 B1＋B2.5=:260、entry 頂層=:22/:122、G1–G6=:278、C9 腳註=:297、`cluster_weight = 1/n_events_in_time_cluster`=:160、`unclassifiable`=:183、B1.6=:190、M9–M12=:367-370、§N-7/8=:395-396；`grep 'label_definition{[^}]*entry'` → 無命中。對照 `handoffs/reconcile/20260820-gap3-x-review-r1/synth.md` X1–X13 處置原文。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#9f63e290e89a; handoffs/reconcile/20260820-gap3-x-review-r1/synth.md#a4d0025eb1f8; handoffs/20260820-gap3-spec-r1-grok.md#a89aacb71ff9

---

