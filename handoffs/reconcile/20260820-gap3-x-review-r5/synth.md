# Reconcile — 20260820-gap3-x-review-r5

**來源** 20260820-gap3-spec-r5-codex.md, 20260820-gap3-spec-r5-composer.md, 20260820-gap3-spec-r5-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-20）

三家共 **3 條** headings（codex 1 條 MAJOR＋composer/grok 各 1 條 sentinel），下列一群集＋sentinel 節引用全部 3 條，0 掉項。
標的＝`docs/GAP3_EVENT_SPEC.md` @ a8bb7634（#57a429d18129）。閉合統計：**W1 三家同判 CLOSED；R1 P0-01（唯一 BLOCKING）最終 CLOSED**——R1–R4 全部 findings 至此閉合。收斂 15→6→4→1→1（V1 為新面）。
程序註記：composer 首派＋補跑皆 Cursor `resource_exhausted`，20 分鐘後第三次重試成功（同 round、無 abandon——review 輪禁 abandon 之規則遵守）；grok 本輪**明文撤回**其 R3「五語意皆滿足 `entry_at ≤ label_start`」誤判並認可 W1。

Verdict：**需修補後合併**——V1 單條文面消歧寫回後派 R6 終輪；V1 之 `RULING-CONFLICT` 面（U4b「一律」之解釋）**列入白話閘問題**由使用者裁。分歧註記：composer 獨立攻後判 V1 為「文面可讀性、非碼證矛盾」不升級；codex 判 MAJOR——主委採較嚴（codex）：同一輸入不得有兩個可讀出的 label 起點，文面歧義在契約文件＝可執行歧義。

### V1 — label 錨與 `label_return_mode` 的 mode-scope 消歧（codex 唯一提出；RULING-CONFLICT 轉白話閘）
**引用**: CODEX-R5-P1-01
**處置＝改 §0 D1-2/D1-5＋§A 待使用者確認**：
1. D1-5 改寫為 **mode-scoped 錨定義**：label 錨由 `label_return_mode` **機械唯一**決定且**恆與 `decision_offset_bars`／entry 語意無關**——`close_to_close`（預設；U4b 使用者自身標註實務）⇒ 錨＝t₀ close；`open_to_close`／`open_to_horizon_close` ⇒ 錨＝entry 時點之進場價（**顯式宣告才合法、非預設**；為 R2 C1 保留之選項）。同一輸入之 label 起點唯一；「禁以 `decision_at` 列 join 主線 `return_N`」適用 `close_to_close` 路徑。
2. D1-2 之「一律相對 t₀ close」加 scope 註記＝**預設模式下**之語意（U4b 原文脈絡：使用者實務一律 c2c、契約保留語意欄以防沒寫明）。
3. **§A 待使用者確認**登記兩題（白話閘裁）：①`drop_threshold` 之 x 值（Z2）②U4b「一律」是否要**全禁**非 c2c 模式（若裁全禁 ⇒ enum 收斂為單值、`open_to_*` 移除；若裁保留 ⇒ 本消歧版生效）。裁決前 B1.0 契約凍結不得先行。

### sentinel 節 — composer/grok 0-findings＋W1 閉合確認
**引用**: COMPOSER-R5-P3-00, GROK-R5-P3-00
兩家 sentinel：W1 寫回七落點忠實、全文無殘留強制 `entry_at ≤ label_start`、X/Y/Z 未破；grok 撤回 R3 誤判（時間序手推 `entry_at > label_start` 成立）；composer 判 V1 不升級（留 reconcile 合併）。與 V1 處置不衝突。

---

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R5-P1-01

**斷言**: `label_return_mode` 仍有未消歧的契約衝突：D1-5/U4b 無條件把 label 錨定為 t₀ close，但 D2-1 又把 `open_to_close`／`open_to_horizon_close` 的 `label_start` 定為 entry 時點；同一輸入可得到兩個不同 label 起點。

**碼證**: `rg -n 'label_return_mode|label 錨＝t₀ close|label_start.*依|open_to_close|open_to_horizon_close|next_open.*close_to_close|entry_after_label_start' docs/GAP3_EVENT_SPEC.md` → D1-1/2/5 列三 mode 且稱 t₀ close 錨，D2-1/§G-2 又列非 c2c 為 entry 時點；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80

[MAJOR, 信心度=High, RULING-CONFLICT] 若 U4b「一律 t₀ close」是全 mode 規則，兩個非 c2c 分支與「各 mode exact」oracle 不可同時成立；若非 c2c 合法，D1-5/D1-4 必須明確限定為 `close_to_close`／benchmark。否則實作者可選不同起點，造成 label/holding estimand 漂移。修法：在 SPEC/contract SoT 明確定義 mode scope，並為非法組合給 fail-closed reason 或保留 mode-specific label anchor。

### 閉合表
- W1／`CODEX-R4-P1-01`: **CLOSED**；D2-1 已拆 PIT／label／持有三段，明定 `next_open × close_to_close` 的 `label_start=t₀ close`、`entry_after_label_start=true`，§G-2 要求 exact oracle。
- `CODEX-R1-P0-01`: **最終 CLOSED via W1**；原 t₀−k canonical form、entry 映射、receipt 與原反例均已落在 D1-6／D2-1／D2-4／§G-2。

### §1 sweep
1 矛盾：見 `CODEX-R5-P1-01`；2–11 漏項、不可測、quant、過度工程、OOM、cache、API/型別、測試、Agent 可執行性、短命工：本輪無新增 finding。

## COMPOSER-R5-P3-00

**斷言**: 本輪逐項核對後無 finding；W1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（D2-1 三段鏈／receipt 三新欄／§G-2 組合案例），全文無殘留強制 `entry_at ≤ label_start`，D1-5 價格錨與 D2-1 mode 時間窗定義相容，與 X/Y/Z 無新碼證衝突。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `57a429d18129ad15c0e0eba5d3d6e2a96d820b9b8e335972c22fa23c95879098`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-6／D2-1／D2-4／AR-1／§G-2；`rg -n 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start' docs/GAP3_EVENT_SPEC.md` → 唯 L30「廢除」；手推 `next_open`×`close_to_close`：t₀ open＜t₀ close＜next open ⇒ `entry_at > label_start`、`entry_after_label_start=true`、三段鏈全過；對照 synth W1 七落點表 0 漂移。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80; handoffs/20260820-gap3-spec-r5-BRIEF.md

sentinel：0 findings（實質）；上列為 R5 W1 忠實度＋殘留單一鏈全文掃＋D1-5↔mode 相容攻擊＋X/Y/Z 新錯掃描之機械複驗摘要。

## GROK-R5-P3-00

**斷言**: 本輪逐項核對後無 finding；W1 寫回忠實於 `handoffs/reconcile/20260820-gap3-x-review-r4/synth.md`（D2-1 三段鏈／receipt 三新欄／§G-2 組合案例），全文無殘留強制 `entry_at ≤ label_start`，D1-5 與 mode 機械 `label_start` 相容，並認可撤回 R3「五語意皆滿足 `entry_at ≤ label_start`」之誤判。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `57a429d18129…`（brief 相符）；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff 3b254e2f..a8bb7634 -- docs/GAP3_EVENT_SPEC.md` → 僅 D1-6／D2-1／D2-4／AR-1／§G-2（± header 無關契約）；讀檔錨點 D1-6=:27、D2-1=:30-34、D2-4=:37、AR-1=:75、§G-2=:111；`grep -nE 'entry_at[[:space:]]*[≤<=]+[[:space:]]*label_start'` → 唯 L30「廢除」；手推 `next_open`×`close_to_close` ⇒ `entry_at > label_start`；對照 R3 本家 Y1 特別面原文（`handoffs/20260820-gap3-spec-r3-grok.md`）確認誤判出處並撤回。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80; handoffs/20260820-gap3-spec-r5-BRIEF.md#2be145bd10f8; handoffs/20260820-gap3-spec-r3-grok.md#ae87c4d78ede

sentinel：0 findings（實質）；上列為 R5 W1 忠實度＋殘留單一鏈全文掃＋R3 誤判更正認可之機械複驗摘要。

---

