# GAP-2 SPEC review-R3 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-x-review-r3/synth.md

## 任務
對 `stamp-target`（SPEC adversarial R3 三家收斂檔；三群集 M1–M3，其中 M3＝主委漏跑戳記之流程 finding）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`d2c73b8b2e16…`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-x-review-r3/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 為何現在補（出生事故）
主委在 consult-R1、review-R1、review-R2 三輪後**漏跑戳記步驟**（制度：reconcile 須委員戳記核可，`scripts/reconcile_stamps_check.sh` 機器強制），R3 輪 codex 依 `AGENTS.md` 第 12 條正確停工。consult-R1、review-R1、review-R2 已三家 APPROVED（stamp 1–3/4）；本輪補 review-R3（4/4）；全數 APPROVED 後重派 R4（stamp brief 只容許單一 stamp-target）。全數補齊後重派 R4。

## 核可判準（勿一律 APPROVED）
1. 三群集 M1–M3 是否逐條對應附錄 5 個 canonical ID；有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文一致；M1（§G-4 case_id 對照＝report_ref 檔名）、M2（§C 白名單去 reasons）已寫回 SPEC；M3（戳記補齊 c1/r1/r2/r3 後重派 R4）處置是否成立。
3. 對應 SPEC 修補是否確實存在（`docs/GAP2_MARGINAL_IC_SPEC.md`，grep finding ID）。註：SPEC 於 R2／R3 又修多處，不影響本 synth 之 body hash。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-X-STAMP-R4
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句實質理由。收尾清 /tmp workdir（保留 claude-501）。
