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
| SPEC consumer-map 須含所有 reindex/merge 下游 | 2026-07-07：第一刀（load 貼回 DatetimeIndex）三方簽核+13passed 卻漏——`_append_cross_sectional_labels` 未列入 consumer map，其對 kline(RangeIndex) reindex 隱性依賴舊 positional 契約 → producer 改真時間軸後橫截面標籤 100% 全 NaN、IC 靜默全壞（0/5088），僅在使用者要求動工前真資料實跑才現形 | SPEC §C consumer map 須含「對 load 結果 reindex/merge 的所有跨模組 consumer」+ 每列出 consumer 須一條真路徑 red-on-break 測試；index 型別變更 Golden 須含 downstream 端到端斷言 | handoffs/CUT2-XSECTIONAL-RECON.md（VERIFY:20260707T023954Z-cut2-xsectional-label-f1） |
| cross_sectional 真路徑須真測非 stub | 2026-07-07：唯一 cross_sectional 測試用 monkeypatch 假 frame+stub analyzer+無空值 oracle → 翻轉 producer index 型別零測試轉紅（廉價綠燈） | 測試設計章程；聲稱驗正確性的測試須 red-on-break；端到端須跑真 load_multi→append labels→analyze | 同上 |
