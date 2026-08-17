# GAP-1 SPEC R2 複審（closure 複驗：R1 之 23 條是否真關閉）

brief-kind: review

## 範本
照 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。
findings 用 canonical ID：`## <FAMILY>-R<輪次>-P<0-3>-<NN>`，**本輪輪次=R2**。
四欄含 `**來源摘要**: <證據檔路徑>#<sha256 前 12 碼>`（純 hex 緊接 `#`，**勿寫** `#sha256:` 前綴）。

## 審查標的
- **SPEC R2**：`docs/GAP1_STRATEGY_OVERFIT_SPEC.md`（commit `4f59a010`）
- 你 R1 的 findings：`handoffs/20260817-gap1-specadv-<你的家族>.md`
- R1 收斂與處置：`handoffs/reconcile/20260817-gap1-x-review-r1/synth.md`（群集 D1–D7 ＋未採納節）

## 本輪唯一任務＝closure 複驗（章程 §B8：由原提出方重跑同一反例）
對**你自己 R1 的每一條 finding**，逐條給：
`CLOSED`（附重跑同一反例之證據，證明現在不會再發生）／
`OPEN`（附仍失敗之反例）／
`PARTIAL`（明確指出殘缺哪一塊）。
**不得**僅因 SPEC 出現該 finding ID 就判 CLOSED——ID 引用不等於義務落地。

## ⚠️ 前置說明
- 本輪是 **SPEC 審查**：「函式/檔案尚不存在」不是缺陷；攻擊面是「義務有沒有寫成可證偽驗收」。
- **禁改碼、禁改 SPEC**；只產你自己的 review 檔。
- 允許提**新** finding（R2 編號），但請優先完成 closure 複驗。

## 本 brief 前提（逐條標；請優先攻 assumed）
fact-verified: 23 條 R1 finding ID 於 SPEC R2 內命中數皆 ≥1 → 逐 ID `grep -c` 實跑（Claude 2026-08-17）
fact-verified: `bash scripts/template_check.sh spec docs/GAP1_STRATEGY_OVERFIT_SPEC.md` → `TEMPLATE PASS`（Claude 實跑）
fact-verified: GROK-R1-P0-01 之數值錯誤已由主委獨立複驗確認為真（`floor`→13／1422；`min_btl(14)=2.3458>T`），SPEC 驗收已改 13 並新增 mutation 3 作回歸鎖
assumed: D1–D7 七個群集之處置**逐條完整**回應了 23 條 findings，無「引用了 ID 但義務只寫一半」者 ← 請直接攻這條
assumed: 新增之 Task 1.4（canonical 報酬序列與 T 語意）＋Task 2.1 擴為 13 個頂層鍵，已足以關閉 C2 之 T 語意與 codex 的 forward dependency ← 請攻
assumed: V[SR] 三態（explicit／analytic／ledger_cross_trial）解決了「今日無 ledger ⇒ DSR 恆 unavailable」與「N=1 退化為 PSR」之矛盾 ← 請攻
assumed: §C 之「允許改動白名單三處」已使 Task 1.3 可實作且不需碰 `performance_metrics.py` ← 請攻

## 必答（逐條 verdict）
1. **closure 表**：你 R1 每條 finding 的 CLOSED／OPEN／PARTIAL ＋證據。
2. **新引入之缺陷**：R2 的修補本身是否引入新問題（新 Task 1.4 與既有 Task 之依賴、13 鍵契約是否過度、
   lazy iterator＋20000 上限是否與 §G 之 S=16（12,870）衝突、24 案例笛卡兒是否可實作）？
3. **數值複核**：§A 的 7 條 FACT-RECEIPT 與 §G 的解析等式，逐條重算是否成立（特別是 3／13／104／1422、
   `min_btl(13)<=T<min_btl(14)`、`E[maxSR]/√V` 三點、`C(S,S/2)`、解析 V[SR] 公式）。
4. **是否可進 TODO 生成**？若否，列 BLOCKING 清單（**只列真正阻擋者**）。

## Time-box 與範圍紀律
- 優先序＝必答 1（closure）＞ 3（數值）＞ 2（新缺陷）。
- **不受理範圍**：治理流程與 gate 機制、前端樣式、其他 registry 票、要求本票現在就接線（使用者已裁決降級）、
  重議使用者兩項裁決（範圍 A／降級展示不硬擋）、要求把 MinBTL 上界改成精確值（已具名為不做）。

## 產出
closure 表 + canonical 四欄（僅新 finding 需要）+ **Verdict**（可進 TODO／BLOCKING 清單）。
**禁改碼、禁改 SPEC**。收尾清 /tmp workdir（保留 claude-501）。
