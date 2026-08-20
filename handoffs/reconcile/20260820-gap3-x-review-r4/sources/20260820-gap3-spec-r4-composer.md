# GAP-3 事件型 SPEC adversarial review R4 — COMPOSER（sentinel 終輪）

task-id: `20260820-GAP3-X-REVIEW-R4`  
審查標的: `docs/GAP3_EVENT_SPEC.md` @ `3b254e2f`（sha256 `d65745d4962bca23b27b5d373bdc281bc47f3724e0cf0898a85f6aa86f2d5ec6`）  
R3 收斂權威: `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md`（Z1–Z4＋sentinel 節）  
brief: `handoffs/20260820-gap3-spec-r4-BRIEF.md`

## 被當成事實的未驗證假設（§0）

| 前提 | 標注 | R4 複核結論 |
|---|---|---|
| R3 reconcile completeness PASS（6/6 heading） | fact-verified（brief） | 未重跑 `--lock`；本輪只驗 Z1–Z4 寫回與新錯掃描 |
| R3 修訂版 `template_check spec` PASS | fact-verified | 本輪重跑 `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0 |
| Z2 fail-closed（`drop_threshold` 未設 ⇒ c 不啟用）覆蓋無歧義 | **assumed → 攻後成立** | B1.5 L184 明寫「僅由 a/b 與 `unclassifiable` 覆蓋」；c 公式保留但分支不評估；僅 c 形走勢且不符 a/b ⇒ `unclassifiable`，無第四出口 |
| Z1 兩層 receipt 與 §G-2 三形 oracle 對得上 | **assumed → 攻後成立** | D2-4 L33 事件級＋per-TF 兩層 schema；§G L107 三形 oracle 驗六時間欄＋`entry_at_ms`/`entry_price_source`＋per-TF `feature_cutoff`；與 D2-1 六欄不變式（L30）經 `entry_at`/`decision_at` 銜接，無互斥 |

## Z1–Z4 synth 處置 vs SPEC 寫回忠實度（閉合表）

| 群集 | synth 處置要點 | SPEC 落點 | diff hunk | 漂移？ |
|---|---|---|---|---|
| Z1 | 事件級 receipt `{t0_ms,decision_offset_bars,decision_at_ms,entry_at_ms,entry_price_source}`＋per-TF 列；兩層入 SoT；§G-2 驗兩層 | D2-4 L33；D1-6 L27；§G L107 | `git diff c7ac693e..3b254e2f` D2-4 hunk | 無 |
| Z2 | `drop_threshold` 無預設；未設 ⇒ c 不啟用；fail-closed；x 列白話閘 | B1.5 L184（公式＋預設＋覆蓋語意） | B1.5 hunk | 無 |
| Z3 | D4 分層改 `counterexample_kind_effective`＋`n_unclassifiable` | D4-2 L43；與 B1.0 L126／B2.2 L221 全局 derived 規則一致 | D4-2 hunk | 無 |
| Z4 | M8／B1.4 三道硬檢：非退化、非恆等、經驗分位；identity mutation 必紅 | B1.4 L173；§V M8 L367（引用 B1.4 定式） | B1.4＋M8 hunk | 無 |

## 專項攻擊面（brief 指定）

| 攻擊面 | 探針 | 結果 |
|---|---|---|
| D2-4 兩層 receipt vs D2-1 六欄不變式 | D2-1 `observed_through ≤ feature_cutoff ≤ decision_at ≤ entry_at ≤ label_start < label_end`；事件級 receipt 含 `decision_at_ms`/`entry_at_ms`；per-TF 含 `feature_cutoff_ms`；B1.0 L127 六時間欄為 manifest 衍生欄 | 兩層為 receipt 結構、六欄為 validator 不變式，分工明確、無矛盾 |
| Z2 fail-closed 分類覆蓋 | `rg drop_threshold\|不啟用\|unclassifiable`；讀 `白話說明/GAP-3事件型討論.md` §2 第 4 點（漲≥5%／上下 1%／跌 x%）；B1.5 三門檻有原文、跌 x% 無 x | c 停用後 a∨b∨unclassifiable 完備；`drop_threshold=0.05` 殘留已清除（`rg drop_threshold` 僅 B1.5 一處且為 `default=null`） |
| Z3 effective 欄全局一致 | `rg counterexample_kind[^_]` → 僅匯入欄／分類器輸入語境；D4/B2.2 皆 `counterexample_kind_effective` | Z3 窄縫已閉；無分層消費 raw 欄殘留 |
| M8 三道硬檢 vs B1.4 定式 | 對讀 B1.4 L173 與 §V M8 L367：`N_perm=1000`、variance>0、n_unique>1、非恆等、經驗分位；M8 明引「B1.4 定式」 | 兩處一致；identity mutation 觸發路徑與 Z4 synth 吻合 |
| Y1–Y6／X1–X13 是否被 Z 修補衝突 | `git diff c7ac693e..3b254e2f` 僅 6 hunk（header＋D2-4＋D4-2＋B1.4＋B1.5＋M8）；無反向裁決 | 無衝突 |

## R3 sentinel 結論保留確認

R3 synth sentinel（COMPOSER-R3-P3-00）判 Y1–Y6 忠實、X 無衝突。R4 diff 為 Z1–Z4 窄縫修補（6 hunk），未改動 Y/X 群集正文；本輪重掃 M1–M12（`rg -c "^  - M"` → 12）、B1 批內順序、§N-7/8——**R3 sentinel 結論仍成立**。

## §1 必查（11 類摘要）

| 類 | 結果 |
|---|---|
| 1 矛盾 | 無 |
| 2 漏項 | 無 |
| 3 不可測 | 無 |
| 4 quant 假設 | 無新疑 |
| 5 過度工程 | 無 |
| 6 OOM | 無 |
| 7 Cache | 無 |
| 8 API/型別 | 無 |
| 9 測試品質 | 無 |
| 10 Agent 可執行性 | 無 |
| 11 短命工 | 無 |

## 必答

1. **Z1–Z4 寫回忠實度＋新錯掃描**：四群集全數字面落地於 diff 六 hunk；專項四面攻擊無 BLOCKING/MAJOR；Y/X 歷史寫回無碼證衝突。
2. **可否進三家 RECONCILE-STAMP＋使用者白話閘？**：**可以**——Z1–Z4 終輪閉合可證偽；`drop_threshold` 之 x 值已列白話閘（不受理再攻其無預設）；無實質 finding 須再修 SPEC。

## COMPOSER-R4-P3-00

**斷言**: 本輪逐項核對後無 finding；Z1–Z4 寫回忠實於 R3 synth 處置，與 Y1–Y6／X1–X13 無碼證衝突，專項四面（D2-4↔六欄不變式、Z2 fail-closed 覆蓋、Z3 effective 全局一致、M8↔B1.4 定式）未見新錯。

**碼證**: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `d65745d4962bca23b27b5d373bdc281bc47f3724e0cf0898a85f6aa86f2d5ec6` 與 brief 一致；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS` rc=0；`git diff c7ac693e..3b254e2f -- docs/GAP3_EVENT_SPEC.md` → 6 hunk 涵蓋 Z1–Z4 全部落點；`rg -n "兩層|drop_threshold|counterexample_kind_effective|variance > 0|B1.4 定式" docs/GAP3_EVENT_SPEC.md` → D2-4/B1.5/D4-2/B1.4/§V M8 命中；`rg -c "^  - M"` → 12；對照 `handoffs/reconcile/20260820-gap3-x-review-r3/synth.md` Z1–Z4 處置原文。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#d65745d4962b; handoffs/reconcile/20260820-gap3-x-review-r3/synth.md

sentinel：0 findings（實質）；上列為 R4 Z1–Z4 忠實度＋新錯掃描＋四專項攻擊面之機械複驗摘要。

## Verdict：可派工

Z1–Z4 已終輪閉合、可證偽落地；可進 **三家 RECONCILE-STAMP＋使用者白話閘**（含 `drop_threshold` x 值裁決）。無 BLOCKING/MAJOR 須再修 SPEC。

---

ASSUMPTIONS_VERIFIED: SPEC sha256 `d65745d4…`＝brief；template_check PASS；Z1–Z4 四群集對 synth 0 漂移；Z2 fail-closed 覆蓋 a/b/unclassifiable 完備；Z1 兩層 receipt 與 §G-2 oracle 對齊；M8 與 B1.4 三道硬檢一致；Y/X 無衝突  
TESTS_RUN: `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → TEMPLATE PASS rc=0；`shasum -a 256 docs/GAP3_EVENT_SPEC.md` → d65745d4…；`bash scripts/completeness_check.sh --single handoffs/20260820-gap3-spec-r4-composer.md --family composer` → 見下行  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r4-composer.md`

STATUS: DONE
