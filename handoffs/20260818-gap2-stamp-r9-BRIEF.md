# GAP-2 TODO review-R8 收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260818-gap2-x-review-r8/synth.md

## 任務
對 `stamp-target`（TODO adversarial R8 三家收斂檔；十群集 U1–U10；15 findings：14 接受寫回 TODO DRAFT R3＋延伸檔 A1-4，1 駁回 U6 附碼證）append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`60163294cb12…`；請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260818-gap2-x-review-r8/synth.md` 重跑確認，不一致請 BLOCKED 而非照抄。

## 背景
R7 收斂檔已三家 APPROVED（stamp r8）。本輪為 TODO review-R8 之常規戳記；APPROVED 後派 R9 複核 TODO DRAFT R3（stamp brief 只容許單一 stamp-target）。制度：reconcile 須委員戳記核可，`scripts/reconcile_stamps_check.sh` 機器強制。

## 核可判準（勿一律 APPROVED）
1. 十群集 U1–U10 是否逐條對應附錄 15 個 canonical ID（codex 9／grok 4／composer 2），有無掉項或「引用 ID 但義務只寫一半」。
2. Verdict 與內文一致；十群集處置是否確實寫入 `docs/GAP2_MARGINAL_IC_TODO.md`（DRAFT R3）與 `docs/GAP2_MARGINAL_IC_AMENDMENTS.md`（A1-4）——grep 關鍵字（`A1-4`、`_inject_root_oos`、`case_id` 於 Task 4.0、`persist_suppressed` 五鍵、`fit_projection` spy、`analyze_cross_sectional`、`mutation_probe_check.sh tests/`）。
3. U6 駁回之碼證是否可證偽：`grep -n -F '非獨立 OOS 驗證' docs/GAP2_MARGINAL_IC_TODO.md` 應 0 命中、TODO L256 文案為「…非獨立驗證」。若你重跑結果與 U6 不符 ⇒ BLOCKED 並附你的 grep 輸出。
4. 母 SPEC 未就地改（`git diff` 不含 `docs/GAP2_MARGINAL_IC_SPEC.md`）；A1-4 之白名單擴張只限三檔。

## 戳記格式（逐字，單行）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-18 sha256:<你實跑取得的完整 body sha256> task:20260818-GAP2-X-STAMP-R9
```
不核可時把 `APPROVED` 改 `BLOCKED` 並在你自己的交件檔寫可證偽的阻擋理由。

## 硬性要求
1. **只** append 一行到 stamp-target 的 `## 戳記` 區段；不得改任何 finding／群集／Verdict／既有行。
2. **不得**把 findings 或評論 append 進 stamp-target（本輪產 stamp，不產 finding）。
3. 不得 commit、不得 push。

## 產出
在你自己的交件檔回報：判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋一句實質理由。收尾清 /tmp workdir（保留 claude-501）。
