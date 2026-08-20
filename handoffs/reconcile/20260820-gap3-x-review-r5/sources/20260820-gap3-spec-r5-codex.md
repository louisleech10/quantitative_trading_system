# GAP-3 事件型 SPEC R5 終輪閉合（codex）
task-id: `20260820-GAP3-X-REVIEW-R5` ｜ target: `docs/GAP3_EVENT_SPEC.md` @ `a8bb7634` ｜ family: codex

## CODEX-R5-P1-01

**斷言**: `label_return_mode` 仍有未消歧的契約衝突：D1-5/U4b 無條件把 label 錨定為 t₀ close，但 D2-1 又把 `open_to_close`／`open_to_horizon_close` 的 `label_start` 定為 entry 時點；同一輸入可得到兩個不同 label 起點。

**碼證**: `rg -n 'label_return_mode|label 錨＝t₀ close|label_start.*依|open_to_close|open_to_horizon_close|next_open.*close_to_close|entry_after_label_start' docs/GAP3_EVENT_SPEC.md` → D1-1/2/5 列三 mode 且稱 t₀ close 錨，D2-1/§G-2 又列非 c2c 為 entry 時點；`bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#57a429d18129; 白話說明/GAP-3事件型討論.md#7c884b1cdb70; handoffs/reconcile/20260820-gap3-x-review-r4/synth.md#089874745d80

[MAJOR, 信心度=High, RULING-CONFLICT] 若 U4b「一律 t₀ close」是全 mode 規則，兩個非 c2c 分支與「各 mode exact」oracle 不可同時成立；若非 c2c 合法，D1-5/D1-4 必須明確限定為 `close_to_close`／benchmark。否則實作者可選不同起點，造成 label/holding estimand 漂移。修法：在 SPEC/contract SoT 明確定義 mode scope，並為非法組合給 fail-closed reason 或保留 mode-specific label anchor。

### 閉合表
- W1／`CODEX-R4-P1-01`: **CLOSED**；D2-1 已拆 PIT／label／持有三段，明定 `next_open × close_to_close` 的 `label_start=t₀ close`、`entry_after_label_start=true`，§G-2 要求 exact oracle。
- `CODEX-R1-P0-01`: **最終 CLOSED via W1**；原 t₀−k canonical form、entry 映射、receipt 與原反例均已落在 D1-6／D2-1／D2-4／§G-2。

### §1 sweep
1 矛盾：見 `CODEX-R5-P1-01`；2–11 漏項、不可測、quant、過度工程、OOM、cache、API/型別、測試、Agent 可執行性、短命工：本輪無新增 finding。

## Verdict：需修補後進三家 RECONCILE-STAMP＋使用者白話閘
本輪不是 0 findings；W1 已閉合，但 mode/label 錨衝突需先明確化。
ASSUMPTIONS_VERIFIED: target commit/hash；workspace SHA-256=`57a429d18129…`；W1 三段鏈與 next_open oracle；全文 mode/anchor 掃描；template_check PASS rc=0。
TESTS_RUN: `shasum -a 256 docs/GAP3_EVENT_SPEC.md` → `57a429d18129…`; `bash scripts/template_check.sh spec docs/GAP3_EVENT_SPEC.md` → `TEMPLATE PASS`, rc=0; `rg` 探針 → 相關語句僅見 D1/D2/§G-2/契約欄位。
FAILURES_SEEN: `CODEX-R5-P1-01`（未修補，非命令失敗）。
SCOPE_CHANGES: review-only；未改 SPEC、程式或既有 dirty files。
NUMERIC_OR_SCHEMA_IMPACT: 未修改輸出；指出 label mode/anchor 契約需消歧。
HANDOFF_OUTPUT: `handoffs/20260820-gap3-spec-r5-codex.md`。
TMP_CLEANUP: `/tmp`（`/private/tmp`）無 `*workdir*` 目錄可清理；`/private/tmp/claude-501` 已確認保留。
STATUS: DONE
