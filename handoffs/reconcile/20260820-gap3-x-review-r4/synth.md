# Reconcile — 20260820-gap3-x-review-r4

**來源** 20260820-gap3-spec-r4-codex.md, 20260820-gap3-spec-r4-composer.md, 20260820-gap3-spec-r4-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

三家共 **3 條** headings（codex 1 條 MAJOR＋composer/grok 各 1 條 sentinel），下列一群集＋sentinel 節引用全部 3 條，0 掉項。
標的＝`docs/GAP3_EVENT_SPEC.md` @ 3b254e2f（#d65745d4962b）。閉合統計：Z2/Z3/Z4 codex 判 **CLOSED**；R1 遺留三條中 P1-03/P1-07 **最終 CLOSED**；P0-01 餘最後一縫（W1）。收斂趨勢 15→6→4→1。
獨立性/正確性註記：W1 為 codex 抓到 grok R3 之誤判（「五語意皆滿足 `entry_at ≤ label_start`」——`next_open` 進場嚴格晚於 t₀ close，close_to_close 下 label_start＝t₀ close ⇒ 不變式必炸）；主委手推時間序（t₀ open < t₀ close < next bar open）確認 codex 碼證成立。

Verdict：**需修補後合併**——W1 單縫寫回（不變式三段拆分，忠實於 U4b「標籤 vs 實際持有兩數並排」原意，**不**禁用 next_open×close_to_close 組合）後派 R5 終輪；通過即三家 RECONCILE-STAMP＋白話閘。

### W1 — 六欄不變式與 next_open×close_to_close 衝突：拆三段鏈（codex 唯一提出；R1 P0-01 最後一縫）
**引用**: CODEX-R4-P1-01
**處置＝改 §0 D2-1／D2-4／D1-6 註記／§G-2**：單一鏈 `…≤ entry_at ≤ label_start…` 廢除，改**三段**——
1. **PIT 鏈**：`observed_through ≤ feature_cutoff[tf] ≤ decision_at ≤ entry_at`。
2. **label 鏈**：`decision_at ≤ label_start < label_end`；`label_start` 依 `label_return_mode` 機械定：`close_to_close` ⇒ t₀ bar close_time；`open_to_close`／`open_to_horizon_close` ⇒ entry bar 之 entry 時點。
3. **持有鏈**：`entry_at < label_end`（持有窗＝entry → label_end close；D1-4／D4 之實際持有報酬）。
`entry_at` 與 `label_start` **無強制順序**（label 錨已依 D1-5 與 decision/entry 脫鉤）；receipt 事件級增 `label_start_ms／label_end_ms／entry_after_label_start: bool`（`next_open`×`close_to_close` ⇒ true；報告兩數並排處必標此旗標——「標籤從 t₀ close 起算、實際持有從 next open 起算」的機器可讀形）。§G-2 oracle：各 `label_return_mode` 之 `label_start/label_end` exact 手算入三形案例；`next_open`×`close_to_close` 案例斷言 `entry_after_label_start=true` 且三段鏈全過。禁用組合＝無（使用者語意本就允許兩數並排）。

### sentinel 節 — composer/grok 0-findings 收錄
**引用**: COMPOSER-R4-P3-00, GROK-R4-P3-00
兩家確認 Z1–Z4 寫回忠實、X/Y 無衝突、R3 sentinel 結論仍成立。W1 與 sentinel 不衝突（sentinel 驗的是「寫回忠實於 synth 處置」，W1 攻的是處置本身未覆蓋的跨欄語意；grok R3 對該組合之判斷被 codex 碼證推翻，本輪明文更正）。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R4-P1-01
**斷言**: Z1 尚未形成單一可驗收的時間契約：`next_open` 嚴格晚於 t₀ close，而預設 `close_to_close` 的 label 基準是 t₀ close；D2.1 卻要求 `entry_at ≤ label_start`，SPEC 未定義此組合的 `label_start` 或 fail-closed 條件。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '23,33p;107p'` → D1.2/D1.4 鎖 t₀ close、D1.6 定義 next bar open、D2.1 要求 `entry_at≤label_start`、§G-2 僅要求三形 receipt exact；`git diff --unified=0 c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → Z1 只補 receipt 層，未補該跨欄位語意。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md#fd7610553bcf
[MAJOR, 信心度=High] 以 t₀ bar open < t₀ bar close < next bar open 的實際時間順序，若 `label_start=t₀ close` 則 invariant 失敗；若改成 next-open 又改變 close-to-close label 起點。需明定禁止組合，或拆開 label benchmark 與 actual-holding window，並把 `label_start/label_end` 語意納入 §G-2 exact oracle。
## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；Z1–Z4 寫回忠實於 R3 synth 處置，與 Y1–Y6／X1–X13 無碼證衝突，專項四面（D2-4↔六欄不變式、Z2 fail-closed 覆蓋、Z3 effective 全局一致、M8↔B1.4 定式）未見新錯。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `d65745d4962bca23b27b5d373bdc281bc47f3724e0cf0898a85f6aa86f2d5ec6` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → 6 hunk 涵蓋 Z1–Z4 全部落點；`rg -n "兩層|drop_threshold|counterexample_kind_effective|variance > 0|B1.4 定式" docs/GAP3_EVENT_SPEC.md` → D2-4/B1.5/D4-2/B1.4/§V M8 命中；`rg -c "^  - M"` → 12；對照 `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md` Z1–Z4 處置原文。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md

sentinel：0 findings（實質）；上列為 R4 Z1–Z4 忠實度＋新錯掃描＋四專項攻擊面之機械複驗摘要。

## GROK-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；Z1–Z4 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md` 處置，特別面（D2-4 兩層 receipt↔六欄不變式／§G-2 三形、Z2 fail-closed 下 a/b/unclassifiable 覆蓋、M8 三道硬檢↔B1.4）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `d65745d4962b…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → 僅 header／D2-4／D4-2／B1.4／B1.5／M8 六處 ±；讀檔錨點 D2-1=:30、D2-4=:33、D4-2=:43、B1.4=:173、B1.5=:184、M8=:367、§G-2=:107；`drop_threshold=0.05` 字面＝0 命中；D4 分層僅 `counterexample_kind_effective`；M8 引用「B1.4 定式」＋三道硬檢與 B1.4 (i)(ii)(iii) 同構；Z2 覆蓋＝c 跳過＋a/b 互斥（0.05 vs 0.01）＋殘差 `unclassifiable`。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md#fd7610553bcf; handoffs/20260820-gap3-spec-r4-BRIEF.md#2a424870a0d3

sentinel：0 findings（實質）；上列為 R4 Z1–Z4 忠實度＋新錯掃描之機械複驗摘要。

---

