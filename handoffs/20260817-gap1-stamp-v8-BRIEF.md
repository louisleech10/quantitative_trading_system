# GAP-1 review-R8（TODO 第一輪 adversarial）收斂檔之 RECONCILE-STAMP 核可

brief-kind: stamp

stamp-target: handoffs/reconcile/20260817-gap1-x-review-r8/synth.md

## 任務
對 `stamp-target` append 一則 `RECONCILE-STAMP`，放進該檔 `## 戳記` 區段內。
body sha256（`## 戳記` 標題**前**之內容）＝`f6385eb7ce27d0c9d15ee1d5c558d8160b87ae234e8b3bea5d26885bcd00ac14`；
請自行 `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260817-gap1-x-review-r8/synth.md` 重跑確認，
不一致請 BLOCKED 而非照抄。

## 背景
本檔為 **TODO 第一輪 adversarial**（`20260817-GAP1-X-REVIEW-R8`）之收斂記錄：三家共 22 條 canonical ID
（codex 12／grok 7／composer 3）＋主委自產版 3 條 P0（非鎖來源）。六群集 J1–J6。
Verdict 分歧（codex「有根本缺陷需重作」vs grok・composer「需修補後派工」）之裁定理由寫在群集前言。
修補落在兩處：`docs/GAP1_STRATEGY_OVERFIT_AMENDMENTS.md`（A1-1..A1-15；母 SPEC 定版故走延伸檔）
與 `docs/GAP1_STRATEGY_OVERFIT_TODO.md`（DRAFT R2，就地改）。

## 核可判準（勿一律 APPROVED；逐項查，任一不成立即 BLOCKED）
1. **0 掉項**：J1–J6 之 `**引用**` 行是否覆蓋附錄全部 22 個 canonical ID（可用
   `bash scripts/completeness_check.sh --synth handoffs/reconcile/20260817-gap1-x-review-r8/synth.md --lock handoffs/reconcile/20260817-gap1-x-review-r8/sources.lock` 複驗）。
2. **裁定是否附碼證而非數人頭**：codex 之 `CODEX-R8-P0-01` 被降為「層界限制＋可觀測欄位＋殘留 G1-R9」，
   `CODEX-R8-P0-02` 判為實作級並修——你若認為 P0-01 之處置不足以誠實反映風險（例如認為必須一律非 `ok`），
   請 **BLOCKED** 並附理由。
3. **處置真的落地**（逐項 grep，不接受「文件說有」）：
   - `grep -c "universe_scope" docs/GAP1_STRATEGY_OVERFIT_TODO.md` ≥ 5；`grep -n "G1-R9" docs/IC_QUANT_GAP_REGISTRY.md` 命中
   - `grep -n "pos\[champion\]" docs/GAP1_STRATEGY_OVERFIT_TODO.md` 命中（J3-a）
   - `grep -n "n_rows_rejected" docs/GAP1_STRATEGY_OVERFIT_TODO.md` ≥ 3（J5-4）
   - `grep -n "reporter_failed" docs/GAP1_STRATEGY_OVERFIT_TODO.md` 命中（J4-4）
   - Task 2.4 是否確實在 B4 末（`grep -n "Task 2.4" docs/GAP1_STRATEGY_OVERFIT_TODO.md` 之位置晚於 Task 4.3）
   - `bash scripts/template_check.sh todo docs/GAP1_STRATEGY_OVERFIT_TODO.md` → PASS
4. **J1 三條數值處置是否可重現**：主委 receipt
   `handoffs/run_receipts/20260817T143000Z-gap1-todoadv-claude-pbo-probe.{py,log}` 與
   `20260817T150000Z-gap1-minbtl-conservatism-probe.{py,log}`；你**可**重跑（`venv/bin/python <path>`，各數分鐘）。
   若你認為新 band `[0.30,0.70]` 或 `mu=0.01*0.15` 之選擇無依據，請 BLOCKED 並附你的數值。
5. Verdict 與內文一致。

## 戳記格式（逐字，單行；與 `scripts/reconcile_stamps_check.sh` 正則一致）
```
RECONCILE-STAMP: <family> APPROVED 2026-08-17 sha256:<你實跑取得的完整 sha256> task:20260817-GAP1-X-STAMP-R9
```
`<family>` ∈ `codex`／`composer`／`grok`（小寫）。不核可時把 `APPROVED` 改 `BLOCKED`，理由寫你自己的產出檔。

## 硬性要求
1. **只** append 到 stamp-target 的 `## 戳記` 區段；不得改任何群集／處置／Verdict／附錄。
2. **不得**把 findings 或評論 append 進 stamp-target（要寫的話寫自己的 output 檔）。
3. 不得改 SPEC／TODO／延伸檔／程式碼；不得 commit、不得 push。

## 產出
判定（APPROVED／BLOCKED）＋實跑之 body_sha256＋逐項核可判準之結論（1–5 各一句）。收尾清 /tmp workdir（保留 claude-501）。
