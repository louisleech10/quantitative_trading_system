# 規則傷疤帳本（SCAR Ledger）

> **用途**：規則 = 傷疤；本檔存「為什麼有這條規則」的出生事故敘事。**規則本體**在 `CLAUDE.md`、執行端合約（`AGENTS.md` / `.cursorrules`）與 `docs/MULTI_AGENT_ORCHESTRATION.md`。新增或強化制度時，在此記一條出生事故。

| 規則 | 出生事故（日期 + 一行） | 現行 enforcement | 出處 |
|------|------------------------|------------------|------|
| 實測 > 假設（Validate Assumptions） | 2026-05 前：假設欄位用 `underscore` 命名 → blacklist 整 run 靜默失效；假設「前端 warmup 誤判 mid-hole」→ 差點改掉正確分類器 | CLAUDE.md「Validate Assumptions」四步驟；合約「先驗證再 code」 | handoffs/instrev-evidence；CLAUDE.md 移出敘事 |
| 驗證保真度 §A 須附 receipt | 2026-06-05：V2 timestamp §A 把 `raw_data.index` 當 DatetimeIndex 卻未跑 `_layer0`（實為 int64 epoch 秒）→ fail-closed abort 整 run | CLAUDE.md「驗證保真度鐵律」三條；gate §A facts-resolved | adversarial #7 早預言未擋住 |
| 回歸測試禁 sanitized fixture | 2026-06-05：回歸用 ms 構造、真實是秒 → pytest 綠燈卻圖表軸為 **1970-01-21** 錯軸 | 驗證保真度鐵律第 3 條；byte-faithful fixture 或真實 ingestion | V2 timestamp 事故 (b) |
| adversarial finding 不得降級放走 | 2026-06-05：code review 點名 multi-TF 玩具 fixture，被降級 NON-BLOCKING → 假綠 | 驗證保真度鐵律第 2 條；真實路徑測試須已存在並通過 | V2 timestamp 事故 (c) |
| C3 委員會獨立性 | 2026-06：餵相同框架給多模型 → **C3** 相關性錯誤，三家族一起錯到使用者才抓出 | gate `--facts-asked` / `--review-role`；ORCH「獨立性陷阱」；至少一人當 adversary | handoffs/20260705-INSTREV-RECONCILE.md |
| Fail-closed Gate | 兩次：(1) 寫 SPEC 沒開 canonical 範本漏 §G；(2) always-loaded 原則在 context 仍被漏 → 改 harness PreToolUse DENY | `scripts/gate_check.sh` + `gate.sh`；CLAUDE.md Fail-closed Gate 節 | ORCH「Gate」節 |
| 中/大完整管線不得跳步 | 2026-06-04：**feature-browser** 自行跳 TODO + adversarial；2026-06-05 使用者定死 D-1 | CLAUDE.md 任務分派決策表；ORCH 分層表「中」列 | 出處=記憶(原始 commit 未尋獲) |
| 宏觀斷路器（兩輪） | 2026-06-10：solo 硬幹整夜——timeout / 孤兒 temp / fracdiff 誤導，兩輪以上未開委員會 | CLAUDE.md 宏觀斷路器；合約 debug ≤2 輪；ORCH §5 | 2026-06-10/06-25 使用者定 |
| 背景派工 stdin 鐵律 | 2026-06-02：背景 codex 卡在 `Reading additional input from **stdin**...` 永不結束 | ORCH「背景派工防卡死」：`timeout` + `< /dev/null` | 2026-06-02 實測 |
| VERIFY claim / receipt gate | 2026-07-01：FF 驗收 smoke 寫成「已驗」→ 捏造通過 | 合約 VERIFY 義務；HANDOFF 鐵律 VERIFY receipt | handoffs/instrev-evidence |
| 選層動態制（D-4） | 2026-07-05 總審查：選層三處三答案分叉（記憶 vs CLAUDE vs ORCH 不一致） | ORCH §1 單一「現行分工」行；CLAUDE 決策表 pointer | handoffs/20260705-INSTREV-RECONCILE.md |
| 06-03 選層 A/B 實證 | 2026-06-03：codex≈cursor 正確性對等，選層差異在成本/嚴謹度非能力 | ORCH §1 誠實邊界句；§8 T-D | ORCH §1、§8 |
