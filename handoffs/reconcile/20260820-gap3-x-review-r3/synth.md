# Reconcile — 20260820-gap3-x-review-r3

**來源** 20260820-gap3-spec-r3-codex.md, 20260820-gap3-spec-r3-composer.md, 20260820-gap3-spec-r3-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

三家共 **6 條** headings（codex 4 條 MAJOR＋composer/grok 各 1 條 sentinel），下列四群集＋sentinel 節引用全部 6 條，0 掉項。
標的＝`docs/GAP3_EVENT_SPEC.md` @ c7ac693e（#377c9a39b01e）。閉合統計：codex 判 Y4/Y6 CLOSED；Y1/Y2/Y3/Y5 各餘一窄縫（Z1–Z4）。composer/grok sentinel 判六群集寫回忠實、無新錯（兩家皆注意到 D4 之 `counterexample_kind` 措辭殘留但判非升級——codex Z3 判其為 D4 規格文字必須精確，主委採 codex：D4 是 all-bars 契約正文，措辭殘留＝可執行歧義）。收斂趨勢 15→6→4，持續縮窄。

Verdict：**需修補後合併**——Z1–Z4 為窄縫修補（receipt schema 補欄／預設值收回／措辭精確化／oracle 防退化），寫回後派 R4 終輪（codex 閉合＋兩家 sentinel）；通過即進三家 RECONCILE-STAMP＋白話閘。**Z2 特別註記**：`drop_threshold` 之 x 值屬使用者產品語意、任何預設都是發明 ⇒ 收回預設、fail-closed，**列入白話閘問題清單**由使用者裁。

### Z1 — D2-4 canonical receipt schema 補事件級欄（codex；Y1 殘縫）
**引用**: CODEX-R3-P1-01
**處置＝改 §0 D2-4**：receipt 明分兩層——**事件級**一列 `{t0_ms, decision_offset_bars, decision_at_ms, entry_at_ms, entry_price_source{bar_open_ms, field}}`＋**per-TF** 每 TF 一列 `{feature_cutoff_ms, last_bar_open_ms, last_bar_close_ms, row_id}`；兩層皆入 SoT；§G-2 oracle 驗兩層。

### Z2 — `drop_threshold` 預設值收回（codex；Y2 殘縫；未驗證假設寫成 fact）
**引用**: CODEX-R3-P1-02
**處置＝改 Task B1.5＋白話閘清單**：使用者 §2-4 原文＝「跌 x%」，x **從未裁定**；`drop_threshold` 改**無預設**（契約中 `default=null`）；未設 ⇒ c 類判定**不啟用**、僅由 a/b 規則與 `unclassifiable` 覆蓋（fail-closed，不發明數字）；x 值列入**白話閘問題**請使用者裁，裁後寫入契約 default 並在 §A 已確認結果補記。其餘三門檻（0.05/0.0/0.01）有使用者原文（漲≥5%／續漲/不續漲分界／上下 1%）依據，保留。

### Z3 — D4 分層欄措辭精確化（codex；Y3 殘縫；composer/grok 已見但判非升級——採 codex）
**引用**: CODEX-R3-P1-03
**處置＝改 §0 D4-2**：`counterexample_kind` 改 **`counterexample_kind_effective`**＋分層報表列 `n_unclassifiable`（與 B1.0/B2.2 全局規則一致；D4 為 all-bars 契約正文，不留歧義措辭）。

### Z4 — M8 permutation oracle 防退化（codex；Y5 殘縫）
**引用**: CODEX-R3-P1-04
**處置＝改 Task B1.4＋§V M8**：oracle 增三道硬檢——(i) permutation 分布**非退化**：`variance > 0` 且 `n_unique_perm_stats > 1`，否則 oracle 自身 FAIL（不是綠）；(ii) 抽樣排列**非恆等**：斷言至少一個排列 ≠ identity（seed＋排列 digest 寫 receipt）；(iii) 帶判定以 N_perm=1000 之經驗分位為準。M8 mutation（恆等排列）⇒ (i)(ii) 必觸發 ⇒ 紅，rc!=0；退化帶「觀測值∈觀測值」的假綠路徑封死。

### sentinel 節 — composer/grok 0-findings 收錄
**引用**: COMPOSER-R3-P3-00, GROK-R3-P3-00
兩家確認：Y1–Y6 寫回忠實（0 掉項、0 反向裁決）、與 X1–X13 無衝突、特別四面（D1-6↔D2 六欄／Y2↔§2-4／Y3 SoT／Y6↔§N-7）通過、R2 sentinel 結論仍成立。與 Z1–Z4 不衝突：Z1/Z3 為兩家已見之呈現層級殘差被 codex 升級為契約精確性要求；Z2 為兩家判「忠實」但 codex 抓到依據缺失（原文無 x 值）——主委查原文後採 codex。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R3-P1-01
**斷言**: Y1 的 entry 映射仍未形成完整 receipt schema；D1-6 要求的 `entry_at_ms`/`entry_price_source` 沒有寫入 D2-4 的 canonical per-TF receipt 欄位。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '27,33p;107p'` → D1-6/G-2 提到兩欄，但 D2-4 仍只列 `{feature_cutoff_ms,last_bar_open_ms,last_bar_close_ms,row_id}`；`git diff --unified=0 21135434 c7ac693e -- docs/GAP3_EVENT_SPEC.md` → 無 D2-4 hunk。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] 缺 canonical receipt 欄位時，agent 可只實作映射而不持久化 entry source，§G-2 無法驗證；需把兩欄及其 anchor TF/field 納入 D2-4／SoT。
## CODEX-R3-P1-02
**斷言**: Y2 把 `drop_threshold=0.05` 當成使用者 §2-4 原例，但原例只寫「跌 x%」，未裁定 x=5%。
**碼證**: `rg -n "drop_threshold|跌 x%|跌 [0-9]+%|漲≥5%|上下 1%" '白話說明/GAP-3事件型討論.md' docs/GAP3_EVENT_SPEC.md` → 使用者檔命中「漲≥5%」「上下 1%」「跌 x%」，5% 的 `drop_threshold` 只出現在 SPEC:184。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; 白話說明/GAP-3事件型討論.md#7c884b1cdb70. [MAJOR, 信心度=High] 這是未驗證假設被寫成 fact，會固定錯誤反向門檻；須移除該預設或取得明確裁決並將來源寫入契約。
## CODEX-R3-P1-03
**斷言**: Y3 的 derived 值集沒有覆蓋所有分層報表；D4 all-bars 仍要求按原始 `counterexample_kind` 分層，與「一律消費 `counterexample_kind_effective`」直接衝突。
**碼證**: `rg -n -C 2 "counterexample_kind|counterexample_kind_effective|unclassifiable" docs/GAP3_EVENT_SPEC.md` → D4:43 為 `counterexample_kind`，B1.0:126 宣告 derived 欄與 `unclassifiable` 分母規則，B2.2:221 才改用 effective 欄。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] B2.5 可遺失平台自動分類或把使用者欄誤當全 K 線分類；D4 必須改用 effective 並列 `n_unclassifiable`。
## CODEX-R3-P1-04
**斷言**: Y5 的 M8 oracle 沒有保證恆等排列 mutation 會失敗；閉區間 `[q.025,q.975]` 在恆等排列下退化為觀測值本身，觀測值仍落帶內。
**碼證**: `nl -ba docs/GAP3_EVENT_SPEC.md | sed -n '173,174p;367p'` → oracle 以 permutation quantile 閉區間判定，M8 僅宣稱 identity mutation「必紅」，未定零變異/非恆等排列 gate。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721. [MAJOR, 信心度=High] 測試可對壞 oracle 報綠，R1 P1-07 仍未閉合；需明定 permutation 非恆等、null variance>0/固定 seed receipt 與量化帶判定。
## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；Y1–Y6 寫回忠實於 R2 synth 處置，與 X1–X13 無碼證衝突，專項四攻擊面（D1-6↔D2、Y2↔§2-4、Y3↔JSON SoT、Y6↔§N-7）未見新錯。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `377c9a39…` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md` → 98 行、涵蓋 Y1–Y6 全部落點；`rg -n "D1-6|counterexample_kind_effective|permutation quantile|test_mutation_guard|platform_random_bars.*恆拒"` → 命中 D1-6/B1.0/B1.4/§V/B1.0；`rg -c "^  - M"` → 12；對照 `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md` Y1–Y6 處置原文與 `白話說明/GAP-3事件型討論.md` §2 第 4 點反例三類原例。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md

sentinel：0 findings（實質）；上列為 R3 Y1–Y6 忠實度＋X1–X13 衝突掃描＋四專項攻擊面之機械複驗摘要。

## GROK-R3-P3-00

**斷言**: 本輪逐項核對後無 finding；Y1–Y6 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r2/synth.md` 處置，與 X1–X13 既有條文無衝突，特別面（D1-6↔D2 六欄、Y2↔§2-4、Y3 兩值集 SoT、Y6↔§N-7）未發現新 BLOCKING/MAJOR。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `377c9a39b01e…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 21135434..c7ac693e -- docs/GAP3_EVENT_SPEC.md` 涵蓋 D1-6／B1.0 control_kind＋derived 值集／B1.5 公式與預設／B1.4＋M8 permutation／§V 逐條命令；讀檔錨點 D1-6=:27、D2-1=:30、B1.0=:123-126、B1.5=:184、B2.2=:221、B3.2=:278、§N-7=:396、M8=:367；D1-1 與 D1-6 五元值集相等；accepted 三值 ⊂ schema 四值且 `platform_random_bars` 為唯一恆拒元。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#377c9a39b01e; handoffs/reconcile/20260820-gap3-x-review-r2/synth.md#2618f362f721; handoffs/20260820-gap3-spec-r3-BRIEF.md#03a913b7a5ab

sentinel：0 findings（實質）；上列為 R3 Y1–Y6 忠實度＋新錯掃描之機械複驗摘要。

---

