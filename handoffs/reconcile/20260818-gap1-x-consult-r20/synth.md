# Reconcile — 20260818-gap1-x-consult-r20

**來源** 20260818-gap1-r11-consult-codex.md, 20260818-gap1-r11-consult-composer.md, 20260818-gap1-r11-consult-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-18；G1-R11 諮詢 → 小任務修補＋三家 review）

三家共 **5 條** canonical ID（codex 1／composer 1 sentinel／grok 3）；下列 **兩群集 O1–O2 引用全部 5 條，0 掉項**。
三家 Verdict **一致＝採主委方案**（`std == 0.0 or np.ptp(values) == 0.0`／`all(values == values[0])`）、**反對相對容差**、**不維持現狀**；
歸類一致＝「對 SPEC『常數序列 ⇒ NaN』字面之**實作修補**，非語意變更」⇒ 小任務＋三家 code review，不開延伸檔／adversarial。
使用者提問（「業界怎麼算」）之答案（grok 逐一貼源碼行號、composer 文獻）：empyrical／quantstats／ffn／vectorbt／pyfolio 對零波動**皆不採相對容差、亦不採 ptp**——
要嘛直接除（NaN／inf）、要嘛精確 `std==0` 回 NaN／inf／0.0；文獻（Bailey & López de Prado PSR/DSR、Lo 2002、Sharpe 1994）未定義零波動 SR，視為 undefined。
本專案選「精確常數 ⇒ NaN＋status」較業界嚴，且不引入任何 ε 常數。

### O1 — 採 `ptp==0`（bit-exact 相等）為常數判定；scope 須明示為「編碼值相等」，非「數學／十進位意圖相等」
**引用**: CODEX-R20-P2-01, GROK-R20-P2-02, GROK-R20-P2-03, COMPOSER-R20-P3-00

codex：`ptp==0`／`all-equal` 只辨識 exact encoded equality，須寫進測試說明避免被誤讀為漏判；grok P2-03：`0.01` 與 `0.1*0.1` 可共存 ⇒ `ptp≠0`，但此為 IEEE 真實微差、與「近常數微擾得巨大 SR」同類，**不**構成反對理由；
grok P2-02：屬 SPEC 字面之實作修補；golden 三案例不受影響（三家皆實跑確認）。composer sentinel：支持、無 blocking。
**處置（修，小任務）**：`sharpe.py:89` 退化條件改為 `std == 0.0 or not np.isfinite(std) or np.ptp(values) == 0.0`；`pbo._sharpe_pp_1d` 同步同一判定；
`test_sharpe.py` 新增「非二進位可精確表示之常數（80×0.01）⇒ NaN＋status 非 ok」與「`0.01+1e-9·k` 微擾 ⇒ 仍有限」；
`test_pbo.py::test_vectorized_sharpe_matches_compute_sharpe` 之 `0.01` 欄斷言由「巨大有限」翻轉為 NaN（逐位等價仍成立）；docstring 明示「常數＝輸入陣列元素**位元全等**（`ptp==0`），不保證跨異源浮點表達式之數學相等」；
探針新增 §V-16（拿掉 `ptp` 判定 ⇒ 該測試轉紅）。registry G1-R11 由 needs-research 改為「已修（commit …）」。

### O2 — 業界／文獻對照（記錄，無處置）
**引用**: GROK-R20-P2-01

grok 逐一貼行號：empyrical `sharpe_ratio` 直接除（std=0 ⇒ inf／NaN）、quantstats 同、ffn／vectorbt／pyfolio 皆無 ε 亦無 ptp。⇒ 本專案方案為「較業界嚴、且不自創常數」，與 A1 系列「禁調常數」一致。

**Verdict**: 可合併 → 修補走小任務（Claude 自做＋自測）＋三家 code review（實作者不自審）；三家 review 後戳記。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R20-P2-01

**斷言**: `ptp == 0`／`all(values == values[0])` 只辨識 exact encoded equality，不能辨識「同一數學／十進位意圖但不同 double 表示」；採主委方案時必須把這個 scope 寫進契約或測試說明，否則使用者可能把不同 double 誤讀成 guard 漏判。

**碼證**: `momentum/Analysis/strategy_validation/sharpe.py:82-92` 先將輸入收口為 float64，再以 std 判退化；timeout probe 觀測 `np.full(80,0.01)` 的 `ptp=0.0` 但 std `1.7456682121588365e-18`、SR `5728465426791027.0`；同 probe 的 `[0.01,0.01,0.010000000000000002]` 為 `ptp=1.734723475976807e-18`；`returns_contract.py:73-78` 的 pct-change→float64 路徑沒有原始 decimal provenance。

**來源摘要**: `momentum/Analysis/strategy_validation/sharpe.py#cdaa1007c3b7`

正文：這是非阻塞的語意邊界，不是要求發明 ε。exact-equality 修補可先收斂 G1-R11；後續若產品真的需要 decimal-level canonicalization，應另定輸入精度／來源契約，並用可追溯 provenance，而不是在 Sharpe 分母上增加全域相對容差。`np.all(values == values[0])` 比 `np.ptp(values) == 0.0` 更直接；兩者都不應被描述成「數學實數相等」判定。

## COMPOSER-R20-P3-00

**斷言**: 本輪逐項核對 A–E 與 §0 前提後，支持採主委 `ptp==0` 方案、拒絕相對容差與現狀；無需額外 blocking finding。

**碼證**: 探針 `80×0.01`：`ptp=0` `std=1.75e-18` `SR=5.73e15`；行業 4 套件源碼無 ε/ptp（empyrical `stats.py:709-717`、quantstats `798-807`、ffn `1424-1427`、vectorbt `341-342`）；ULP 反例 `ptp=1.73e-18`；pytest golden+constant **4 passed**；`ptp` 仿真：`80×0.01`/`zeros`/`0.5` 皆 degenerate，`edge3`/`micro` 不 degenerate。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[P3] 核對依據＝§0 表 + A–E 段；ULP residual 已記於 C 段，不升格 blocking。

---

ASSUMPTIONS_VERIFIED: sharpe.py L88-90；80×0.01 探針；4 套件源碼+實跑；ULP/CSV/f32 探針；pytest 4 cases  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_noise_band tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_detectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_golden_alpha_undetectable tests/momentum/Analysis/strategy_validation/test_pbo.py::test_constant_slices_produce_exclusions_and_all_degenerate -q` → 4 passed rc=0；`bash scripts/completeness_check.sh --single handoffs/20260818-gap1-r11-consult-composer.md --family composer`（收尾跑）  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（唯讀 consult；`/tmp/composer-gap1-r20` 為探針用）  
NUMERIC_OR_SCHEMA_IMPACT: none（未改碼）  
OUTPUT_ARTIFACT: `handoffs/20260818-gap1-r11-consult-composer.md`  
TMP_CLEANUP: 刪除 `/tmp/composer-gap1-r20`；保留 `/tmp/claude-501`  
STATUS: DONE
## GROK-R20-P2-01

**斷言**: 業界主流 Sharpe 實作（empyrical／quantstats／ffn／vectorbt／pyfolio）對零波動皆不採相對容差、亦不採 `ptp`／`all-equal`；要嘛直接除（得 NaN／inf），要嘛精確 `std==0`→NaN／inf／0.0。

**碼證**: 本輪下載並標行號：empyrical `sharpe_ratio` L700–717 直接 `nanmean/nanstd` divide；quantstats `sharpe` L892 無零檢、`sortino` L1041 `downside==0`→nan、`risk_return_ratio` L2404 `std==0`→nan；ffn `calc_sharpe` L1456–1458 `np.divide`+errstate、`information_ratio` L1484 `diff_std==0`→0.0；vectorbt `sharpe_ratio_1d_nb` L346–347 `if std==0.0: return np.inf`；pyfolio L290 委派 empyrical。相對容差搜尋於上列函式體 → 0 命中。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[MAJOR] 信心度=High。坐實 brief assumed A；支持「反對相對容差」。本專案加 `ptp==0` 是比業界更貼「常數」字面的補洞，不是跟風發明 ε。

---

## GROK-R20-P2-02

**斷言**: `ptp==0`（並存既有 `std==0`）是對 SPEC「常數序列⇒NaN」驗收句的實作修補，不是 Task 1.2 已蓋章「近常數微擾得巨大 SR」語意之變更；golden 三案例不受影響。

**碼證**: SPEC ≈L154–155 驗「常數序列」；`sharpe.py:89` 僅 `std==0.0`。本輪：`np.full(80,0.01)` → `ptp=0`、`std≈1.75e-18`、現行 `status=ok` 且 SR≈5.7e15；擬修謂詞 `std==0 or ptp==0` 對該欄為 True、對 `0.01+1e-9·arange` 為 False。`pytest .../test_pbo.py -q` → 17 passed；golden noise 矩陣 `any_ptp0=0`。

**來源摘要**: momentum/Analysis/strategy_validation/sharpe.py#cdaa1007c3b7

[MAJOR] 信心度=High。歸類＝小任務 bugfix＋三家 review；同步 `_sharpe_pp_1d`；翻轉 `test_vectorized_sharpe_matches_compute_sharpe` 對欄 7 之 `|SR|>1e6` 斷言為 NaN。

---

## GROK-R20-P2-03

**斷言**: brief assumed「真實管線不會產生同一數學值之不同 double」不完全成立（`0.01` 與 `0.1*0.1` 可共存於一序列且 `ptp≠0`），但此反例屬 IEEE 真實微差、與主委保留之「近常數微擾」同類，**不**構成反對 `ptp` 修法或改採相對容差之理由。

**碼證**: `0.1*0.1` bits=`4576918229304087676`＝`nextafter(0.01)`；`0.01` bits=`4576918229304087675`；混合序列 `ptp>0`、`all_eq=False`。對照：CSV `'0.01'`、`float32→float64` 同構、`[0.01,1e-2,1/100]` → 皆 `ptp==0`。

**來源摘要**: handoffs/20260818-gap1-r11-consult-BRIEF.md#0daaf5679e9c

[MAJOR] 信心度=High。建議文件化：常數判定＝「輸入陣列元素位元全等」（`ptp==0`），不保證跨異源浮點表達式之「數學相等」。

---

ASSUMPTIONS_VERIFIED: F1–F3 重跑成立；A1 業界無相對容差坐實；A2 部分證偽（異源 double）；A3 golden 不受 ptp 影響坐實；文獻結構支持零波動＝退化／未定義、無 ε。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/test_pbo.py -q --tb=line` → 17 passed rc=0；本地探針（80×0.01／ptp／異 double／CSV／float32）見段 C–D。
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀；僅新增本產出檔）
NUMERIC_OR_SCHEMA_IMPACT: none（本輪未改碼；建議修法若落地會讓 `0.01` 常數欄由巨大 SR 改 NaN——屬 G1-R11 意圖）
OUTPUT: handoffs/20260818-gap1-r11-consult-grok.md
STATUS: DONE

## 戳記
