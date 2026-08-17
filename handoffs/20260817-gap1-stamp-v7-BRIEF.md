# GAP-1 review-R7 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r7/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`ad4c5c535461276f43c9a577f22502d76b0399d819727d9a63c7bd227840ab63`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r7/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 背景
GAP-1 之 SPEC 審查共跑七輪（收斂軌跡 23→7→11→7→4→1→收束）。本檔為第七輪（**受限閉合複驗輪**：只複驗
R5 四條 FATAL；群集 I1）之收斂記錄。較早六份（consult-r1／review-r1／r2／r4／r5／r6）已三家 APPROVED。
本檔之後 SPEC 經 R8（使用者白話閘裁決收回三項殘留為 Task）；R8 屬後續輪次，**不影響**本檔 body hash。

## 核可判準（勿一律 APPROVED）
1. 群集 I1 是否逐條對應附錄之 3 個 canonical ID（`CODEX-R6-P0-01`＋兩個 sentinel），有無掉項。
2. 四條 R5 FATAL 之三家 closure 表與附錄原文是否一致（codex 判 P0-03 OPEN、另兩家 CLOSED）。
3. 主委裁定「codex 正確、另兩家漏判」是否附可證偽理由（`LedgerReadResult` 缺 `candidate_ids` 欄位 ⇒ 集合等式不可執行）；
   對應 SPEC 修補是否確實存在：`grep -c "candidate_ids" docs/GAP1_STRATEGY_OVERFIT_SPEC.md` ≥ 4、
   驗收 ⑤b2「同數量不同集合」與 ⑥c 不變式可 grep 到。
4. Verdict 與內文一致（「需修補後合併 → 已於 SPEC R7 修補完成」）。

## 戳記格式（逐字，單行；與 `scripts/reconcile_stamps_check.sh` 之正則一致）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-17 sha256:<你實跑取得的完整 sha256> task:20260817-GAP1-X-STAMP-R8
```
`<family>` ∈ `codex`／`composer`／`grok`（小寫）。不核可時把 `APPROVED` 改 `BLOCKED` 並於你自己的產出檔寫可證偽阻擋理由。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict。
2. **不得**把 findings 或評論 append 進 stamp-target。
3. 不得 commit、不得 push。

## 產出
判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句理由，寫到 cx_run 指定之 output 檔。收尾清 /tmp workdir（保留 claude-501）。
