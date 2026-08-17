# GAP-1 review-R9（受限複驗）收斂檔之 RECONCILE-STAMP 核可（含三條修補之落地機械核可）

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r9/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`67a5a742319c47ea4fc1cb1c640aea4d69a71cb0761150b4ef56080fb3d977d9`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r9/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 背景（🔴 本輪戳記兼任「Frozen 前最後一道審查」）
R9 為受限複驗（R8 22 findings 之 closure＋J1 數值實跑＋新機制攻擊面），三家共 6 條 ID，收斂為三群集 J7／J8／J9。
主委裁定**不再派新一輪 adversarial**，理由＝三條修法皆由**你們逐字指定**（非主委自創）且可 grep 驗證；
故把「修補是否真落地、是否落成你要的形狀」**放進本戳記輪的核可判準**。
⇒ 你若認為修補走偏、或認為仍需一輪完整 adversarial，請 **BLOCKED** 並具名理由（這是你唯一的攔阻點）。
戳記 PASS 後 TODO 立即標 **Frozen** 並開工 B1。

## 核可判準（逐項查，任一不成立即 BLOCKED）
1. **0 掉項**：三群集之 `**引用**` 行覆蓋附錄全部 6 個 ID。複驗：
   `bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-x-review-r9/synth.md --lock handoffs/reconcile/20260817-gap1-x-review-r9/sources.lock`
2. **J7（例外集合）落地且形狀正確**——標的：`docs/GAP1_STRATEGY_OVERFIT_TODO.md`（sha256 前 12＝`7ef0ec44e111`）、
   `docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`（`31c3fddb05f0`）：
   - `InvalidValidationArgument(ValueError)` 於 Task 3.1 定義；三處參數驗證＋`x>700` 皆 raise 之
   - Task 3.4 捕獲集合恰為 `(OSError, json.JSONDecodeError, ContractViolation)`，**不含** `ValueError`
   - 入口語意二分：`None`＝未提供 ⇒ `n_unknown`；`t_years<=0`／`target_sharpe<=0`＝呼叫方 bug ⇒ **上拋 5xx**
     （🔴 主委第一版曾把 `<=0` 也正規化為 unavailable ＝「換一種吞法」，已自行推翻；請確認現行文字是二分而非正規化）
   - 驗收⑤ 含 `InvalidValidationArgument` ⇒ 5xx；新增驗收⑧（`t_years=-1.0` ⇒ 5xx 且不得回 `reporter_failed`）
3. **J8（AST 收窄）落地且真能擋你的反例**：
   - Task 2.4 之 W1／W4 收集範圍逐字為「函式**頂層**、未嵌在 `If`／`For`／`While`／`Try`／`With` body 內」
   - mutation 增為 **6 條**，第 ⑥ 條即你的 `if False:` 死分支反例（⇒ rc=1）
   - Task 3.3「不可做」有**配對條款**（禁 helper／迴圈／`setattr`／`dict(**kwargs)` 組裝）——
     若無此條，閘門的「寧誤擋」會讓實作者無合法寫法可用
   - Task 2.4 誠實邊界具名「只做語法層無條件路徑，不做 CFG／可達性」
   - 🔴 請用**你自己的 `if False:` 片段**對照新規則手推一次：新規則下該片段是否確定 rc=1？若否 ⇒ BLOCKED。
4. **J9（§R 覆寫）落地**：延伸檔 A1-18 具名覆寫母 SPEC:653-654，含「B4 ⊃ B3」「先 revert B4 再 B3」
   「不採 post-B4 phase 之理由」。
5. **未動已定案內容**：`bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS；
   J1 三條數值 golden（band `[0.30,0.70]`、`mu=0.01*0.15`、`alpha_undetectable>0.40`）與
   §V-4 新形式、驗收⑨ 之文字**未被本輪修補改動**。
6. Verdict 與內文一致。

## 戳記格式（逐字，單行；與 `scripts/reconcile_stamps_check.sh` 正則一致）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-17 sha256:<你實跑取得的完整 sha256> task:20260817-GAP1-X-STAMP-R10
```
`<family>` ∈ `codex`／`composer`／`grok`（小寫）。不核可時把 `APPROVED` 改 `BLOCKED`，理由寫你自己的產出檔。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改任何群集／處置／Verdict／附錄。
2. **不得**把 findings append 進 stamp-target（要寫就寫自己的 output 檔）。
3. 不得改 SPEC／TODO／延伸檔／程式碼；不得 commit、不得 push。

## 產出
判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋判準 1–6 各一句結論
＋（判準 3）你對自己 `if False:` 反例在新規則下之手推結論。收尾清 /tmp workdir（保留 claude-501）。
