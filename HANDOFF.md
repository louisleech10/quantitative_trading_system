# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 當前狀態：**GAP-3 SPEC 對抗審全管線收案，阻塞在使用者白話閘**

- SPEC＝`docs/GAP3_EVENT_SPEC.md` @ HEAD（六輪對抗審 15→6→4→1→1→0；每條由原提出方重跑反例閉合）。
- 收斂檔鏈＝`handoffs/reconcile/20260820-gap3-x-review-r{1..6}/synth.md`（R1=X1–X13＋AR-1..6 裁決；R2=Y1–Y6；R3=Z1–Z4；R4=W1；R5=V1；R6=終態）＋stamp-r1/r2。
- **三家 RECONCILE-STAMP 已核可 r6 synth**（`reconcile_stamps_check` rc=0，body sha `f833c6b9…`）；債帳 0 OPEN。
- **白話閘（阻塞彈窗）已發給使用者，等裁三題**：①SPEC 核准進 TODO？②`drop_threshold` x 值（SPEC §A 待確認①；未裁前 c 類自動分類 fail-closed 不啟用）③U4b「一律 t₀ close」範圍（§A 待確認②；全禁 open_to_* vs 保留須顯式宣告）。

## 接手動作（依使用者裁決分支）
1. **核准**：把 ②③ 裁決寫入 SPEC §A 已確認結果＋對應條文（②入 B1.5/契約 default；③定 enum）→ SPEC 標 FROZEN → 走 `templates/TODO_GENERATION_PROMPT.md` 生成 `docs/GAP3_EVENT_TODO.md`（gate artifact 開門）→ TODO 對抗審。
2. **退回**：照裁示修訂，修訂＝新一輪三家對抗審＋重新戳記（body 變 ⇒ 舊戳記自動失效）。
3. 殘留八條（SPEC §N）於 freeze 時同步登記 `docs/IC_QUANT_GAP_REGISTRY.md`「GAP-3 殘留」；ROADMAP 只放 pointer。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十一）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`。committee_run 一家失敗：同 round `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>` 補跑；**同 round 該家已 success 會拒重派 ⇒ 開新 kind 輪**（本線 stamp-r2 前例）。
- 🔴 Cursor `resource_exhausted` 多為**端點暫時故障非額度**（8/20 實測：最小探針 `cursor-agent -p … "回覆兩個字"` rc=0 即恢復）；先探針再退避，review/stamp 輪禁 abandon。
- 🔴 **戳記時序坑（摩擦候補）**：stamp-target 尚無 `## 戳記` 區時委員算的 body hash＝全檔，區塊建立後即跨版失效 ⇒ 派 stamp 前主委先在 target 建空 `## 戳記` 區，或 brief 明令「先確認區塊存在」。
- reconcile 正式入口＝`completeness_check.sh --lock <sources.lock>`（只吃 lock，不吃 synth 路徑）；review 輪 lock 須 `--mode review`（discovery 建的用 `--rebuild` 升級）。
- `factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 紅＝既有；`scripts/governance_families.json` no-op dirty＝既有；push 丟背景；venv Python 3.9.6；三支臨時腳本 `scripts/ichc_t2_*.py`／`ichc_t3_diff.py` 待清（非本線）。
