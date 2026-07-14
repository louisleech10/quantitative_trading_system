# IC1C SPEC r2 閉合重驗 — codex
標的:`docs/IC1C_NETIC_SPEC.md` v0.2；日期:2026-07-14；reconcile sha256:`d94d4c14cfa8f88abea661f72a725ae7a44b45e7c371c8dc945dd61d614b72e7`。

## r1 findings 逐項重驗
- **CODEX-1 CLOSED** — §A:22、Task 1.1:73/78、Task 1.2:80-82、拆票:102-103 明禁錯位 `long_short_mean_return`，1c-FR 前 unavailable+reason；原「錯 timestamp 仍有限 net return」反例不能再作為合法輸出。
- **CODEX-2 CLOSED** — §T:27-29 明定 turnover 已含進出、公式無 `×2`；M2/M8 守反例。F11 持有期矩陣拆 1c-FR 合理：B-strict 於 1c 不再把 bar turnover 與 holding return 相減，故原 horizon mismatch 不可構成。
- **CODEX-3 PARTIALLY（BLOCKING）** — Task 2.1:89-94 有 typed request、同步 422、default=False、移除三處 5bps；但 override reject 清單只含 `{default_cost_bps,cost_bps,slippage_bps}`，漏 `cost_enabled`（亦漏舊 `cost_scenarios`）。反例：typed `{cost_enabled:false}` 加 `config_override.net_ic_analysis.cost_enabled=true` 仍可越過唯一 HTTP validator，於背景才 raise/改語意。
- **CODEX-4 CLOSED** — §C:34-50 已納 analyzer/orchestrator/proxy/config/YAML/factory/API/route/reporter/UI/store/types/tests，且 Task 1.3/2.2 明刪 proxy 與 UI 0.1 假 fallback；重跑 `rg` 未見未納入的專屬 consumer。
- **CODEX-5 PARTIALLY（BLOCKING）** — §G:57-63 已改全 feature、獨立公式、NaN mask、phase baseline；但「r2 schema 白名單」不是唯一可枚舉 schema：Task 1.1:73 是扁平 cost 欄，:77/Task 2.1:94 又稱 disabled 時「無 cost 子樹」，skipped variant 亦未列鍵集合。故第 4 feature 多/少 reason/status 鍵仍無確定 equality oracle。
- **CODEX-6 PARTIALLY（BLOCKING）** — summary 刪/正名與 JSON null 原則已寫；但 Task 1.1:73 的 `net_factor_return:null+reason`、Task 1.2:81 的 `{status,reason}`、Task 2.1:93 的 `number|null+reason code` 是三種不相容表示，reason 的欄名/位置與 TS discriminated union 未凍。核心 null 經 HTTP 後仍可有兩種合法 shape，原 DTO 反例未關閉。
- **CODEX-7 STILL-OPEN（BLOCKING）** — §V:109-118 雖增 M1-M8，但只給函式名與「恢復→紅」文字；未依 `TEST_DESIGN_CHARTER.md` B4 給類別及 `測試檔:函式`，亦未依 B1.1 指定同檔 `test_mutation_*` 自證基線綠→注入紅→還原、及 `mutation_probe_check.sh` 驗收。紙面 mutation 仍可假綠。

## RECONCILE 曲解檢查
F1 fail-closed、F3 去 `×2`、F11 持有期矩陣拆 1c-FR 均未曲解 codex finding。F5 的 reconcile 寫 rank correlation `null+reason`，r2:75 改為刪除；雖文字漂移，但更符合 codex r1「刪/正名」與 B-strict，非新增 blocker。

## r2 新洞
- **CODEX-R2-1 — BLOCKING：phase/schema 依賴倒置。** Phase 1 Task 1.1:77 已要求 `cost_enabled=False` 行為，但該欄到 Phase 2:90 才建立；同時 G-NEW 在 Phase 1:57-60 要凍 cost 欄，Phase 2 disabled 又要求無 cost 子樹。逐 phase commit 無法同時滿足自己的 gate。須把功能開關/schema 提前，或把該邊界與 G-NEW2 明確延至 Phase 2，並凍 enabled/disabled/skipped 三套精確鍵集合。

ASSUMPTIONS_VERIFIED: 完整讀 HANDOFF/CLAUDE/brief/r1/SPEC r2/reconcile/TEST_DESIGN_CHARTER B1.1+B4+B8；以現行 request/config/orchestrator/TS 路徑及全域 consumer 搜索重跑反例。
TESTS_RUN: `shasum -a 256 handoffs/20260714-IC1C-SPECREV-RECONCILE.md`→d94d4c...b72e7；`rg -n '(net_ic|default_cost_bps|...)' momentum api frontend/src tests config`→consumer 逐點核對；`test -f tests/fixtures/ic_api_real_kline.py`→存在。review-only，未跑實作 pytest。
FAILURES_SEEN: none；SCOPE_CHANGES: none，唯一產出本檔；NUMERIC_OR_SCHEMA_IMPACT: review-only，指出未凍 schema/phase gate，未改數值或 schema。
SPEC-REVIEW-R2: REJECT(5 BLOCKING)
