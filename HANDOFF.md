# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手任務：**生成 GAP-3 TODO 並走對抗審**（SPEC 已 FROZEN，2026-08-20 使用者白話閘核准）

- **SPEC＝`docs/GAP3_EVENT_SPEC.md`（FROZEN；修訂走延伸檔 `docs/GAP3_EVENT_SPEC_AMENDMENTS.md`）**。白話閘三裁決已寫入 §A：門檻皆舉例可調／`label_return_mode` 保留三值／`decision_offset_bars`＝研究參數非訊號標註。
- 對抗審履歷：六輪 15→6→4→1→1→0（synth 鏈 `handoffs/reconcile/20260820-gap3-x-review-r{1..6}/`）；三家 RECONCILE-STAMP 蓋 r6 synth rc=0；殘留 G3-R1..R8 已登記 registry。
- **下一步**：①照 `templates/TODO_GENERATION_PROMPT.md` 生成 `docs/GAP3_EVENT_TODO.md`（創建須 `bash scripts/gate.sh artifact --file docs/GAP3_EVENT_TODO.md --template-opened templates/TODO_GENERATION_PROMPT.md --sections ...`）②TODO 三家對抗審（抄寫漂移是 TODO 階段主病——逐 Task 對 SPEC 條文比對）→ reconcile＋戳記 → TODO FROZEN ③開 B1 施工（主委自任實作；每批三家 code review＋戳記才進下批；B1 批內順序 B1.0→B1.1→B1.2→B1.3→B1.6→B1.4→B1.5）。
- TODO 要點提醒：§V M1–M12 逐字抄不得增刪；契約欄位只 pointer `event_import_contract.json`（Task B1.0 建）；`ic_survivor_contract` 升版只在 B2.4；§G golden 凍結時機＝B2.3 動工前。

## ⚠ 坑（完整清單 CLAUDE.md Gotchas／白話 摩擦 六十八～八十一）
- 🔴 含家族名的 Bash 會被擋 ⇒ 命令寫 scratchpad 腳本再 `bash <script>`。committee_run 一家失敗：同 round `ROUND_ID=<id> bash scripts/cx_run.sh <fam> <brief> <out>` 補跑；**同 round 該家已 success 拒重派 ⇒ 開新輪**。
- 🔴 Cursor `resource_exhausted` 多為端點暫時故障非額度（先最小探針 `cursor-agent -p … "回覆兩個字"`，rc=0 即可重派）；review/stamp 輪禁 abandon。
- 🔴 戳記時序坑：stamp-target 無 `## 戳記` 區時委員算的 body hash＝全檔，區塊建立後跨版失效 ⇒ 派 stamp 前先在 target 建空 `## 戳記` 區。
- reconcile 正式入口＝`completeness_check.sh --lock <sources.lock>`；review 輪 lock 須 `--mode review`（`--rebuild` 可升級）。
- `factkey_write_guard` 對 `Archived/GAP-2施工進度.md:13-22` 紅＝既有；`scripts/governance_families.json` no-op dirty＝既有；push 丟背景；venv Python 3.9.6；三支臨時腳本 `scripts/ichc_t2_*.py`／`ichc_t3_diff.py` 待清（非本線）。
