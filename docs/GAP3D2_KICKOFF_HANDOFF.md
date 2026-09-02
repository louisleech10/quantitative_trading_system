# GAP-3 `G3-D2` 灰色項目完成 — **開工交接**（2026-09-02 深夜寫，給新 session）

> 讀完本檔即可開工，不必回頭問。本檔是**指標＋裁定＋現況**，不是 SPEC；SPEC 由新 session 依完整管線起草。

---

## §0 使用者裁定（2026-09-02 深夜，原話等價）

- 三組灰項**全部要做到可選且真的算得出來**（延續 2026-08-31「不接受永久灰著」）。
- **順序：(a) → (c) → (b)**。
  - (a) `scenario` 之 `A`／`B`／`two_stage`（預測型／兩段式）
  - (c) `entry_price_semantic` 其餘四值、`label_return_mode` 其餘兩值、`decision_offset_bars > 0`
  - (b) `control_kind` 之 `platform_random_bars`
- GAP-3 UAT B1–B20 已由使用者全部驗畢（B3 依本票記未完成）；D10–D17 八票已修已推（`docs/IC_QUANT_GAP_REGISTRY.md`）。
- 🔴 **使用者主目標＝B 預測型**（8/19–8/20 原話：用 t₀ 之前的指標預測 t₀ 會不會漲 ≥5%，在 t₀ open 買；進場可提前 k 根）。
  GAP-3 交付的是 **C 確認型**全鏈；使用者 2026-09-02 深夜才知道主目標未在其中（見 `白話說明/流程摩擦記錄.md` 同日）。
  ⇒ 本票 (a) 的 B 是**第一優先**，A／two_stage 其次；白話文件每一步都要明講「B 做到哪了」。
- **可重用（情境無關）**：事件匯入契約與對映、PIT 對齊（`decision_at_ms`／`entry_at_ms`／`label_start_ms`／`label_end_ms`）、宣告與 purge（D-8）、去重（`_POLICY_BY_SCENARIO` 已含 A／B）、條件 IC 五階段、survivor 六鍵、UI 五維度與揭露。
  **缺**：B 之決策時點＝t₀ open（`trigger_open`＋`k≥0` 之 label golden）、`scenario` 解灰與 provenance、揭露文案隨情境變、§3.1「全部 K 線驗證」（是否屬本票＝consult 必答）。

## §1 任務大小與流程（依 CLAUDE.md 分派表）

**大任務**（命中 (a) 數值／(d) ML 回測正確性／(b) 跨模組）⇒ 完整管線：**consult（唯讀，三家＋主委各完整版）→ 白話給使用者裁 → SPEC（Claude 起草，D 延伸或新 SPEC，見 §4）→ 三家 adversarial 至收斂 → 三家 RECONCILE-STAMP → TODO → 實作（Claude 自任）→ 三家 code review 至閉合**。
執行端分工以 `docs/MULTI_AGENT_ORCHESTRATION.md` §1 現行分工行為準。
派工命名：`<YYYYMMDD>-gap3d2-<batch>-<kind>-r<N>`（batch ∈ `x`／`b1`…；kind ∈ consult／review／stamp／impl／closure），task-id＝大寫。
派工前 `bash scripts/agent_preflight.sh`；brief 用 `bash scripts/new_brief.sh <kind> <path> "<title>"` 產骨架，寫法紅線見記憶 `feedback_brief_writing_method`。

## §2 權威來源（SoT；先讀）

| 主題 | 位置 |
|---|---|
| 三種情境之語意（使用者原話） | `白話說明/GAP-3事件型討論.md` §3.1（全部 K 線驗證）、§3.2（A／B／C／兩段式表）、§3.7（去重：A／B 降權不刪） |
| 契約 enum 與 doc | `momentum/Analysis/contracts/event_import_contract.json` `required_fields.scenario`（`A/B 預測型（事件在未來、不進特徵）／C 確認型／兩段式`）、`control_kind.accepted`（`platform_random_bars` 恆拒） |
| 深度通則（R 重開後） | `docs/GAP3_EVENT_UX_SPEC.md` §D-3′ L796–822：**四種 scenario 同一式**，深度＝使用者逐 tf 宣告（D-8）；「機制相同、僅語意不同」（L818） |
| 支援矩陣與開放前置 | SPEC §F-1′（本批只 `(trigger_close, close_to_close, k=0)`）、**R8 註 L2456–2472**：分析時 label producer 已由 Task 7.0b 滿足，**剩下之唯一前置＝逐組合 exact golden**（§G G-3 擴充） |
| 可選集合定義與灰項落點 | SPEC L3024–3044 `selectable = accepted − pathExclusions`；前端唯一常數 `frontend/src/lib/eventDimensions.ts`（L143 起 `/search` scenario 排除、`rejected_with_reason`）；元件 `components/case/EventDimensionFields.tsx`、`ic-analysis/EventBatchDisclosurePanel.tsx`；測試 `lib/contractEnumWiring.test.tsx`、`eventContractOptions.test.tsx` |
| 分析時 label producer | `momentum/Analysis/event_samples/label_value_from_case.py`（`prepare_analysis_windows`／`resolve_label_value_at_analyze`；F-1′ 矩陣檢查在此）；pipeline 出口 `event_samples/pipeline.py`；五階段編排 `api/services/ic_analysis_service.py::_run_event_label_stages` |
| 去重政策依 scenario | `momentum/Analysis/event_samples/dedupe.py` `_POLICY_BY_SCENARIO`（C＝cluster_first；A／B＝all_with_uniqueness） |
| 票與殘留 | `docs/IC_QUANT_GAP_REGISTRY.md` **G3-D2**（本票）、G3-R7（`platform_random_bars` 抽樣契約未定義）、G3-R9（辨別表無模型分數）、registry #4（Pooled IC，跨 symbol 不在本票） |
| 既有 golden 機制 | SPEC §G G-3（analysis-label golden；owner Task 7.0b；typed loader＋sha256 凍結） |

## §3 現況（唯讀盤點，新 session 開工第一步須重驗）

- `scenario`／`control_kind`／三元組在前端已「可見、正確灰掉、附契約 doc 理由」（B3 已驗）。
- 分析時 producer 只支援 `(trigger_close, close_to_close, k=0)`；其他組合 fail-closed（reason `label_producer_unsupported_for_declared_semantics`）。
- CSV 匯入路徑使用者自帶 `label`（0／1）；`label_value`（連續）由分析當下產生（Task 7.0b）。
- 跨 symbol 事件已於 D17 定為「只餵同 symbol」；Pooled IC 另票。
- 小樣本 IC Mean 顯示 `--`（G3-R12，needs-research）。

## §4 三組的技術關係（🔴 consult 必答；主委初判，可被推翻）

1. **(a) 在技術上內含 (c) 的一部分**：A／B 之決策時點＝t₀ 之 **open**（或更早，`decision_offset_bars > 0`），進場語意＝`trigger_open`／`decision_bar_open`；而這些正是 (c) 的組合。依 SPEC L818「機制相同、僅語意不同」與 R8 註，A／B 之 label 仍由 Task 7.0b 之分析時 producer 算，**缺的是那些組合的 exact golden**＋scenario 語意之 provenance／揭露／去重政策接線。
   ⇒ 建議 SPEC 把 (a) 定義為：「**A／B／two_stage 所需之 (c) 子集 golden ＋ scenario 語意接線**」，做完後 (c) 剩餘組合是同一機制的擴充。
2. **two_stage** 之「兩段各自答案窗、取最大」（§D-3′ 表）在 R 重開後＝使用者宣告時填兩段之較大者；SPEC 須寫清楚 UI 文案與 provenance 欄。
3. **§3.1「全部 K 線驗證」**（precision／recall 在驗證期每根 bar 上跑）是 A／B 的主目標，但需要模型分數（G3-R9：現無模型分數來源）⇒ 本票是否含它，**consult 必答**；主委初判：不含（歸 ML 層／pattern 橋），本票只到「A／B 事件可匯入、可算條件 IC、可揭露」。
4. **(b)** 須先定抽樣契約與 estimand（G3-R7；當年「時間分離隨機反例」被判廢設計、禁隱式 fallback）。建議獨立 consult。

## §5 使用者已裁（2026-09-03 凌晨，開工前）

| # | 題 | 裁定 |
|---|---|---|
| 1 | (a) 完成是否須含 §3.1「全部 K 線驗證」 | **不含**。使用者原話等價：「現在是用 IC 篩特徵、留可能的給後續 ML，那時候才是全部 K 線驗證」⇒ 屬 IC→ML 橋（registry #2b）之 ML 層驗證。(a) 完成＝B 情境可匯入、可算條件 IC、倖存者可交後續 ML |
| 2 | `decision_offset_bars`（k）之預設與上限 | **使用者不填 k**。使用者原話：「我就是不知道交易訊號在哪一根，我怎麼給數字」——訊號提前幾根由 lookback 型特徵自己抓；k 只作**分析時掃描參數**（與 h 同層，IC 分析頁掃 k=0,1,2…），批次事實不記 k；預設 k=0（t₀ open 決策）。🔴 SPEC 須把 k 從「匯入時宣告」改為「分析時參數」，並定掃描上限（consult 給依據） |
| 3 | 反例種類 a／b／c 是否必標 | **不必標**；使用者只標 0／1，種類由平台依 t₀ 實際走勢自動分類（門檻可調），僅作報表分組；排第二期 |
| 4 | 標籤基準 | 維持 8/20：t₀ close、close-to-close；開盤進場之實際報酬並排顯示 |
| 5 | (a) 內部順序 | **B → A → two_stage**；(c) 先做 B／A 用到之組合（`trigger_open`、k 掃描），其餘同機制擴充 |

**仍留給 consult／之後白話閘**：`two_stage` 之 UI 表達；(b) 隨機對照組之抽樣範圍與 estimand；k 掃描上限。

## §6 完成定義（沿 registry G3-D2）

該值在 `/search`（與 `/ic-analysis` 適用者）**可選**；選了之後匯出／分析算得出對應 `label_value`（(a) 另需該情境自己的 provenance）；每個組合有獨立手算 exact golden；B3 驗收改為可選項全部通過。
