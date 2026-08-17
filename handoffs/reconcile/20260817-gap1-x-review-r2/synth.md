# Reconcile — 20260817-gap1-x-review-r2

**來源** 20260817-gap1-specadv-r2-codex.md, 20260817-gap1-specadv-r2-composer.md, 20260817-gap1-specadv-r2-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-17；SPEC R2→R3）

R2 為 **closure 複驗輪**（章程 §B8：原提出方重跑同一反例）。三家交件含 **8 個 canonical ID**
（codex 4 新 finding／grok 3 新 finding／composer 1 個 zero-findings sentinel），
以及 R1 之 23 條逐條 CLOSED／PARTIAL 判定。下列四群集**引用全部 8 條，0 掉項**。
VERIFY: 逐 ID `grep -c <ID> docs/GAP1_STRATEGY_OVERFIT_SPEC.md` 7/7 新 finding 皆 ≥1（Claude 實跑 2026-08-17）；
`bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → TEMPLATE PASS。

### R1 closure 統計（三家自判）
- **composer 7/7 CLOSED**，Verdict＝可進 TODO，BLOCKING 清單：無。
- **grok 6/7 CLOSED、1 PARTIAL**（GROK-R1-P1-04：資料流已關，但驗收③之 oracle 代數不成立 → 升為 GROK-R2-P0-01）。
- **codex 3 CLOSED（P0-02／P1-07／P1-08）、6 PARTIAL**；PARTIAL 全部屬「義務寫了但殘缺一角」，
  已於 R3 逐條補齊或明文降為具名殘留（見 E4）。

### E1 — 真實代數錯誤：Sharpe 比值 oracle 在 rf≠0 下不成立（BLOCKING，主委承認）
**引用**: CODEX-R2-P0-01, GROK-R2-P0-01

兩家獨立同時抓到。R2 版 Task 1.3 斷言③ 要求 `sharpe(1h)/sharpe(None) == sqrt(8760/730)`，
但 `PerformanceMetrics` 預設 `risk_free_rate=0.02` 且 `excess = mean - rf/periods`
⇒ 該項隨 periods 變動，比值**代數上不等於** `√` 比。
主委獨立複驗：rf=0.02 ⇒ ratio 4.5309 vs 期望 3.4641；rf=0 ⇒ 差 <1e-15 ⇒ **兩家正確**。
**處置**：① 斷言③ 明定 fixture `risk_free_rate=0.0`，並把「兩呼叫點允許顯式傳 `risk_free_rate`」
寫入 §C 白名單（避免實作者為過測而越界改 `performance_metrics.py`）
② 新增斷言③b：以生產預設 rf=0.02 斷言 `periods_per_year` 分叉且兩 sharpe **不相等**（不鎖比值）
③ §V 新增 mutation 13（fixture 用 rf=0.02 ⇒ 該斷言須轉紅）＝回歸鎖。

### E2 — 變異數混淆與單位（部分採納、部分**附證據駁回**）
**引用**: GROK-R2-P1-01, GROK-R2-P1-02

grok 主張 DSR 應改 `Φ((SR−SR0)/√V)`、SR0 與分母共用同一 V。
**主委複驗後駁回該修法，但接受其指出之缺陷**：
判準＝**N=1 時 DSR 必須恰等於 PSR**（此為 §G 既有 oracle，且 grok 自己 R1 亦引用該性質）。
主委實跑（T=50, SR=0.8, γ3=0.5, γ4=4, V_cross=0.2）：
論文形式（Mertens SE 分母）N=1 → 1.000000 ＝ PSR ✓；
grok 建議之「同一 V」形式 N=1 → 0.963181 ≠ PSR ✗。
且兩者本是不同物件：`Var(SR_hat)=den²/(T-1)=0.022041` vs 跨 trial `V[{SR_n}]=0.2`。
⇒ **保留論文形式**；真正缺陷＝主委前版把兩者都叫 `V[SR]` 造成歧義。
**處置**：① Task 1.2 欄位更名 `variance_analytic` → `sr_estimator_variance`（per-period，Mertens）
② §G 明列「兩個變異數為不同物件」節，附上述實跑判準與駁回理由
③ `variance_source` 由三態改**二態**（`explicit`／`ledger_cross_trial`）——`analytic` 移除，
因解析式屬分母而非 SR0；`n_trials=1` 不需跨 trial 變異數，`n_trials>1` 且缺 ⇒
`reason=cross_trial_variance_unavailable` 誠實不可算
④ **單位鎖定（GROK-R2-P1-02）**：進檢定統計量之 SR／γ3／γ4／T 一律 per-period，
`value_annualized` 僅回顯；新增斷言⑦「`periods_per_year ∈ {1,730,8760}` 下 DSR 值不變（`atol=1e-12`）」
＋§V mutation 11／12 鎖住此二點。

### E3 — 契約與 Task 結構殘缺（MAJOR，全採納）
**引用**: CODEX-R2-P1-01, CODEX-R2-P1-02, CODEX-R2-P1-03

① **receipt 路徑錯**（CODEX-R2-P1-01）：R2 版寫 `1h/data`，實際 HDF5 需 symbol 前綴
（`BTCUSDT/1h/data`），照抄會 KeyError ⇒ §A 改為含 symbol 之可重跑命令並標明各 symbol 同列數。
② **契約三集合無內容**（CODEX-R2-P1-02）：`report_sections`／`eligibility_keys`／`reasons`
只有鍵名沒有內容，Task 3.3 之 24 案例可與空 schema 自洽 ⇒ R3 逐一給出內容，
其中 `reasons` 六值定為**唯一** reason 字串來源（程式與測試禁自創字面值）。
③ **Task 1.4 對 1.3 之隱性依賴**（CODEX-R2-P1-03）：1.4 讀 `BacktestResult.annualization`
而該欄位由 1.3 新增，但 B1 宣告「無依賴」且 1.4 排在 1.3 之前 ⇒ R3 明示批內順序
`1.1 → 1.2 → 1.3 → 1.4`、Task 1.4 標依賴 1.3，並定義缺 `annualization` 時
`reason=annualization_unresolved` fail-closed（禁假設 730）。

### E4 — codex PARTIAL 之殘留補齊與具名（全處理，無靜默）
**引用**: COMPOSER-R2-P3-00（zero-findings sentinel；composer 判 7/7 CLOSED 且無新缺陷）

本群集記錄 codex 六條 PARTIAL 之 R3 處置（該六條 ID 屬 R1，已在 R1 收斂檔引用，此處不重複計數）：
- CODEX-R1-P0-01（effective-N）→ **補齊為具名殘留**：§N 新增條款，`adaptive_search` 下
  **不做任何換算**，DSR 輸出 `n_independence="unverified"`（Task 3.2 斷言⑧）＋報告回顯；禁任何折算係數。
- CODEX-R1-P0-03（ledger variance dataflow）→ **補齊**：Task 3.2 簽名新增 `cross_trial_sr_values`
  直接吃 Task 2.2 之 `valid_sharpe_values`，dataflow 落地。
- CODEX-R1-P1-05（alpha oracle 未凍結）→ **補齊**：§G 明列 `mu = 0.01*1.0/sqrt(8760) =
  1.0683760683760685e-04`，並註明 golden 檔僅複製、不得只寫「寫死於 golden 檔」。
- CODEX-R1-P1-06（cap 不隨 n_obs）→ **補齊**：改雙重預算守衛，新增元素上限
  `path_count * n_obs > 20_000_000` ⇒ raise，並加 S=16×n_obs=2000（25,740,000 元素）之 raise 斷言。
- CODEX-R1-P0-04（六條生產 bypass）→ **維持具名殘留**（codex 自己亦認同對純統計核心不擴 scope）：
  §N 已明文列出六條並寫「未覆蓋、無法機器阻止、不得宣稱已關閉 C1 繞過面」。
- CODEX-R1-P1-02 類（無）。

### 未採納 / 部分採納（具名，附證據）
- **GROK-R2-P1-01 之修法駁回**（見 E2）：附主委實跑數值判準（N=1 → PSR 之退化性質）。
  grok 指出之命名混淆缺陷**已採納並修補**。此為本輪唯一「不採納委員修法」之處。

**Verdict**: 需修補後合併 → **已於 SPEC R3 逐條修補完成**（7 條新 finding 全具名引用、
6 條 codex PARTIAL 全數補齊或具名殘留、composer 零 finding）。
收斂趨勢：R1 23 條 → R2 7 條實質 finding（composer 已零）⇒ 收斂中。
**是否可進 TODO 由 R3 複審決定**（另派一輪；grok 與 codex 之 R2 Verdict 皆為「需修補後」，
本輪修補須由其複驗）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R2-P0-01

**斷言**: Task 1.3 要求的 Sharpe 比值 oracle 在既有 `PerformanceMetrics` 預設 risk-free 語意下不成立；照 SPEC 與現有程式同時實作會無法通過驗收。

**碼證**: `SPEC:167-177` 要求比值精確等於 `sqrt(8760/730)`；`momentum/Strategy/performance_metrics.py:20,77-86` 的預設 `risk_free_rate=0.02` 會使年化轉換含 period-dependent subtraction。對同一 equity sequence 實跑：`pm_ratio=3.4728899102086075`、`expected=3.4641016151377544`（命令：`venv/bin/python -c '...PerformanceMetrics(...periods_per_year=8760/730)...'`）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[BLOCKING] 信心度=High；修正方式須固定 oracle 的 risk-free（例如明定為 0）或把非零 risk-free 的完整比值列成 expected，且不得為過測而改掉 `PerformanceMetrics` 既有語意。

## CODEX-R2-P1-01

**斷言**: §A FACT-RECEIPT 的 kline 路徑不是目前真實 HDF5 的可重跑路徑，故由它導出的 20352/T 與數值 gate 沒有有效 receipt。

**碼證**: `SPEC:25` 宣稱直讀 `1h/data`；同一 h5py 命令實跑 `KeyError: component not found`。唯讀檢查 root keys → symbols；`BTCUSDT/1h/data`、`BTCUSDT/4h/data`、`BTCUSDT/12h/data` 才輸出 `(20352,)`、`(5088,)`、`(1696,)`。RECHECK: `venv/bin/python -c 'import h5py; f=h5py.File("data_cache/feature_klines/kline_cache.h5"); print(list(f.keys()))'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；receipt 必須改成存在且記錄 symbol provenance 的 dataset path（或 metadata-derived path），再由該 receipt 重算 T 與 3/13/104/1422。

## CODEX-R2-P1-02

**斷言**: Task 2.1 宣稱 13-key JSON SoT，但 `report_sections`、`eligibility_keys`、`reasons` 沒有內容或型別/枚舉定義，Task 3.3 因而仍可由實作者任意選 schema。

**碼證**: `SPEC:192-206` 只逐項定義 `ledger_record_keys`、`n_fields` 與五個 `*_values`，在 `reasons` 後沒有三個未定義集合的內容；`SPEC:319-330` 只 pointer `report_sections`/`eligibility_keys` 並要求 validator。RECHECK: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '192,216p;319,330p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；需為三個集合補機器可驗證內容，否則空/錯的報告 schema 仍可讓 24-case 測試自洽而非與契約對證。

## CODEX-R2-P1-03

**斷言**: 新 Task 1.4 依賴 Task 1.3 才存在的 `BacktestResult.annualization`，但 B1 宣告無依賴且 Task 1.4 排在 Task 1.3 之前，TODO 順序可先產出不可執行的 canonical extractor。

**碼證**: `SPEC:105` 宣告 B1 無依賴；`SPEC:137-155` 的 Task 1.4 明確讀「新增之 annualization」；`SPEC:160-172` 才由 Task 1.3 新增該欄位。RECHECK: `nl -ba docs/GAP1_STRATEGY_OVERFIT_SPEC.md | sed -n '103,172p'`。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High；需明列 1.4→1.3 依賴或調整 task/契約順序，並指定缺 annualization 時的 fail-closed 行為。

## COMPOSER-R2-P3-00

**斷言**: 本輪在優先完成 7 條 R1 closure 複驗與 §A／§G 數值重算後，未發現需以 `COMPOSER-R2-P0/P1/P2` 立項之新缺陷；R2 修補（Task 1.4、13 鍵契約、V[SR] 三態、§C 三處白名單、lazy CSCV 守衛、24 案例笛卡兒）與既有 Task 依賴一致且可證偽。

**碼證**: ① closure 表 7/7 為 CLOSED（上表逐條 RECHECK）② `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → PASS ③ python 重算：預算 3/13/104/1422、`min_btl(13)≤T`、`E[max SR]` 三點、`C(16,8)=12870<20000`、C5 oracle ④ 新缺陷四項（1.4 依賴、13 鍵、20000 上限、24 案例）逐項無 BLOCKING。RECHECK：重跑 closure 表 RECHECK 列＋本節 python 區塊。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[NON-BLOCKING] 信心度=High。依據＝R1 原反例重跑均不再失敗；未為湊數捏造實質 finding。

---

## GROK-R2-P0-01

**斷言**: Task 1.3 驗收③要求同一報酬序列在 `timeframe="1h"` 與 `timeframe=None` 下 `metrics["sharpe_ratio"]` 比值恰為 `√(8760/730)`（`atol=1e-9`），但既有 `PerformanceMetrics.sharpe_ratio` 使用預設 `risk_free_rate=0.02` 做 `excess = mean - rf/periods`，該比值**代數上不等於**純 √periods 比；Task 1.3 又明文不改 `performance_metrics.py` 且兩呼叫點未規定改 rf⇒正確實作無法通過該斷言（或只能暗改 rf／metrics 越界）。

**碼證**: SPEC Task 1.3:176-177「比值 ＝ `sqrt(8760/730)`（`atol=1e-9`）」；`performance_metrics.py:20,77-86` 預設 rf=0.02 且 `return excess/std*√periods`。本輪：
```
rf=0.02 → ratio≈3.021 vs √(8760/730)≈3.464 (|diff|≈0.44)
rf=0    → ratio≈3.464 (|diff|<1e-15)
```
RECHECK: 任意非零 mean 序列實例化 `PerformanceMetrics(eq, [], periods_per_year=8760|730).sharpe_ratio()` 比比值。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[BLOCKING] 信心度=High。會怎麼失敗：agent 依白名單只傳 `periods_per_year` → 測紅；或為了綠改 rf／改 metrics 類 → 違 §C。修法（擇一寫死）：① 斷言③ 改為與 rf 一致之解析比，或要求測試 fixture `risk_free_rate=0` 並在兩呼叫點明示可傳 rf；② 改斷言為「`annualization["periods_per_year"]` 分叉 + sharpe 絕對值有序關係」而不鎖 √ 比；③ 若堅持 √ 比，允許 Task 1.3 在呼叫點傳 `risk_free_rate=0.0`（寫進白名單改法）。未修則 Task 1.3 不可誠實收斂。

---

## GROK-R2-P1-01

**斷言**: Task 3.2 雖宣告 V[SR] 三態，但寫死的 DSR 組裝式在 `SR0=√V·E[max]` 使用三態 V 的同時，檢定統計量分母固定為矩形式 `√(1-γ3·SR+(γ4-1)/4·SR²)/√` 結構（即等價強制 analytic V），使 `variance_source∈{explicit,ledger_cross_trial}` 時 SR0 與 DSR 未共用同一 V，偏離 Bailey `DSR=Φ((SR−SR0)/√V)`；且現有驗收未對非 analytic 路徑做數值對照⇒錯誤組裝可綠。

**碼證**: SPEC Task 3.2:296-301（SR0 用 √V[SR]；下式 DSR 分母寫矩展開，未寫 `/√V` 同一 V）；驗證⑥僅「三個 source 有案例覆蓋」、⑤只測 ledger 長度<2 之 status。本輪反例（T=50,SR=0.8,g3=0.5,g4=4,N=200,V_ledger=0.2）：
```
dsr_hybrid(SPEC 字面)≈0.00163
dsr_correct(同 V)   ≈0.16437
|diff|≈0.163
```
RECHECK: 實作兩式對同一 (SR,V_ledger,moments) 比較。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High。修法：DSR 唯一定義改 `Φ((SR_obs−SR0)/√V)`，V 與 SR0 同源；矩展開僅作為 `variance_source="analytic"` 之 V 定義（§G 已有）。§V 增 mutation：ledger/explicit 路徑若仍走矩分母⇒與 `/√V` 參考分叉轉紅。否則 R1「三態」只修好 SR0 半邊。

---

## GROK-R2-P1-02

**斷言**: Task 1.2 以必填 `periods_per_year` 強烈暗示 `SharpeResult.value` 為**年化** SR，卻要求 `variance_analytic` 直接套 §G 之 `V=(1-γ3·SR+(γ4-1)/4·SR²)/(T-1)`（文獻矩公式預設與 **同頻、非年化** SR 及 period-return 之 γ3/γ4 一致）；SPEC 未寫死「進 DSR 的 SR/V 用非年化、年化僅報告」或「V_ann=V_bar·periods」二選一，agent 可把年化 SR 直接代入矩公式而系統性偏誤，N=1 自洽測仍可能綠。

**碼證**: Task 1.2:125-127（periods 必填 + variance_analytic 依 §G）；§G:93-94 公式無 `periods_per_year` 因子；Task 3.2:298「SR_obs／γ3／γ4／T 皆取自 SharpeResult（同一 periods 基準）」未定義 value 是否已 ×√periods。對照 Task 1.3 路徑之 `sharpe_ratio` 確為年化（`*√periods`）。RECHECK: 規定手算案例同時給 `periods_per_year∈{1,730,8760}` 三值，要求 DSR 不變（若採非年化進檢定）或呈 √periods 縮放（若全年化且 V 正確縮放）。

**來源摘要**: docs/GAP1_STRATEGY_OVERFIT_SPEC.md#03e6832ae4ae

[MAJOR] 信心度=High。修法：在 Task 1.2／3.2 釘死單一慣例——建議 **檢定全程用非年化 SR_bar 與 V_bar**（γ3/γ4 來自 period returns），`periods_per_year` 只用於報告欄位的年化展示；並加 `periods_per_year` 變換下 DSR 不變之 golden。未釘前 TODO 會產出兩種「全綠」實作。

---

