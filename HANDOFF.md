# Handoff

**Agent**: Claude(Fable 5) ｜ **Branch**: main ｜ 實作＝主委自任；review／adversarial＝codex+composer+grok 三家

> 🔴 **本檔只寫「接手要做什麼」。** 不寫日誌、不寫歷史、不重述別處已有的狀態。

---

## 🔴 接手第一件事：GAP-1 已 **全票 CLOSED（2026-08-18）**——沒有進行中的 epic；**等使用者點下一步**

**現況**（`git log origin/main..HEAD` 應為空；`bash scripts/debt_ledger.sh --list` 無 OPEN）：
- B1–B4 各三家 code review＋三家 RECONCILE-STAMP PASS（收斂檔 `handoffs/reconcile/20260818-gap1-b{2,3,4}-review-r{14,16,18}/synth.md`、`20260817-gap1-b1-review-r10`）。
- 測試 `venv/bin/python -m pytest tests/momentum/Analysis/strategy_validation/ tests/api/test_ml_pipeline_strategy_validation.py -q` → **280 passed**；
  探針 `bash scripts/gap1_b1_mutation_probe.sh` → 20 條全紅（有互斥鎖，只能一人跑）；`bash scripts/strategy_wiring_check.sh` rc=0。
- 文件：TODO FROZEN R3＋延伸檔 A1-1..A1-24（衝突以延伸檔為準）；白話看板 `白話說明/GAP-1施工進度.md` 已標收工；Pages 上線 https://louisleech10.github.io/quantitative_trading_system/site/ 。
- 殘留：registry「GAP-1 待補完」G1-R1..R7／R9／R10／**R11**（新：`compute_sharpe` 對浮點非精確常數不退化，needs-research）。

**候選下一步（由使用者點，勿自行開 epic）**：
1. ROADMAP 小票 **PA-CUMSUM**（`prediction_analyzer.py:155` cumsum→cumprod；Claude 小任務流程自做自測）。
2. G1-R11 容差研究／裁定（動 Task 1.2 已蓋章語意 ⇒ 須三家審）。
3. IC 主線其他缺口票（`docs/IC_QUANT_GAP_REGISTRY.md`）。

## ⚠ 本 session 學到的（完整清單在 CLAUDE.md Gotchas／白話 摩擦記錄 六十一～六十五）
- 🔴 委員 CLI 已有看門狗（`cx_run.sh`：產出 `STATUS: DONE` 逾 5 分鐘不退即殺子樹視為完成；硬上限 90 分鐘）；brief 要求委員自建探針加 timeout。
- 🔴 接手先 `ps aux | grep -E "cursor-agent|codex exec|grok "` 看有無殘留委員行程／舊 Claude session（本日曾兩個 session 同時活著）。
- 🔴 每批收尾：pytest → 探針 → commit → push（背景）→ 白話 5 檔同步 → commit+push（`plain_docs_sync_check` 是 pre-push 硬擋，動 `scripts/` 就要更新白話 5 檔）。
- 🔴 `handoffs/*` 新檔被 `.git/info/exclude` 隱藏：reconcile 目錄／brief 須 `git add -f`。
- 🔴 白話 .md commit 時 pre-commit 會同 commit 重生成 `docs/site/`（`plain_docs_render.sh --check` 缺產出／死連結即擋）。
- 🔴 對多處同型行做 `sed` 前先 `grep -c`（本 epic 兩次誤傷）；「為了讓閘門過而放寬規則」會被委員反例打回——正解是收窄白名單再讓碼配合。
- `scripts/governance_families.json` 有既有 no-op dirty（`active_stampers`），非本 epic 產生，未歸屬。
