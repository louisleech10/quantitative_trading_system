## Verdict

需修補後派工；FINDINGS_COUNT: 5（P0/BLOCKING=2，P1=3），未達 Internal Frozen 出場判準。

## §0 前提宣告

FACT-RECEIPT: `bash scripts/template_check.sh todo docs/GOVB0_FRICTION_TODO.md` → `TEMPLATE PASS`、rc=0；`grep -c '^\*\*Task '` / `grep -c '^### Task '` → `11/11`；`bash scripts/reconcile_stamps_check.sh handoffs/reconcile/20260805-govb0-spec-r7/synth.md` → `PASS`、rc=0（sha256:b502bac9…0f82fa4bd）。

fact-verified: `git status --short` 只有既存 `.claude/gate/audit.log`、R6 codex handoff/source/synth 變更；本輪未改碼、TODO、SPEC。`bash scripts/brief_conformance_check.sh handoffs/20260805-GOVB0-TODO-REVIEW-BRIEF.md` → rc=0。

四項假設攻擊結果：①追溯 100% 覆蓋為假（缺具名 ID/合理合併宣告，另缺 OPEN-2）；②冷啟動可直接實作為假（Task 1.1 使用不存在的 `_bc_kv`，Task 3.3 的 duration manifest 無來源契約）；③B1–B7 無衝突為假（B5 要求在 B3 前凍結 snapshot，但 B5 排在 B3/B4 後；B6 gate 漏 Task 3.1）；④`TEST-3.3-PROVISIONAL` 三條件可機械讀取為假（manifest 未定義，backlog B-14 無「未定稿」）。

## 逐項核對表

1. 追溯 FAIL。SPEC 的實際 literal ID 清單（`LC_ALL=C rg -o -N '(D-[0-9]+|E-[0-9]+|F-[0-9]+|G-[0-9]+|H-[0-9]+|E-SCOPE|OPEN-[0-9]+)' docs/GOVB0_FRICTION_SPEC.md | sort -uV`）為 `D-1,D-2,D-3,D-4,D-5,D-6,D-8,D-11,D-12,D-13,E-1,E-2,E-3,E-7,E-8,E-9,E-10,E-13,E-SCOPE,F-1,F-3,F-6,F-7,OPEN-1,OPEN-2,OPEN-3`；G/H literal ID 為 0。TODO 落點：`D-1→T2.1; D-2→T3.2; D-3→T0.1; D-5→T1.1; D-11→T1.1; D-12→T0.1; D-13→T2.5; E-2→T1.1; E-3→T2.1/T2.2; E-7/E-8→T0.1; E-10→T3.3; E-SCOPE→§0.2/T3.2; F-6→T2.1; OPEN-1→§0.2/T3.3; OPEN-3→§0.2`；缺具名落點或合併說明：`D-4,D-6,D-8,E-1,E-9,E-13,F-1,F-3,F-7,OPEN-2`。`H-1/H-2` 只在 brief/TODO 作 R7 殘留別名，非 SPEC literal，依不受理範圍不列 finding。
2. 深度紅線部分通過：11 Tasks 的實作要點均 ≥3；邊界均 ≥2 個具體向量；驗證均有具體狀態條件。`T0.1/T1.1/T2.0/T3.1/T3.2/T3.3` 有偽碼或命令流程，`T2.1–T2.5` 有明確 top-level 判定區塊/輸出 entrypoint；但 T1.1 的 helper/函式錨點錯誤，T3.3 的輸入 artifact 未定義，詳 finding。
3. §0 三項狀態 FAIL。B-24「部分完成」與 H-2「人工清理」只有散文；沒有讀取狀態來源的可執行斷言。E-10 雖有 `TEST-3.3-PROVISIONAL` 三條件文字，第三條跨檔不可執行，且 manifest 無路徑/格式/producer。
4. 批次 FAIL。B1–B4 的依賴及同檔聚批本身合理，未見其他跨批同檔衝突；但 B5 的 pre-Phase-2 snapshot 時序與 B3/B4→B5 排序矛盾，B6→B7 只 gate `test_atomic_publish.py`，沒有 Task 3.1 duration/schema gate。當前 DRAFT 的 future test/script artifacts 尚不存在，故其餘命令未宣稱已可實跑。
5. rc 配對 PASS（逐條）：T0.1 的 `RC-BLOCK/RC-ALLOW` 對應 `INVARIANCE/FIELDS/ENUM`；T1.1 的 `CONSULT/STAMP/UNKNOWN` 對應 prompt 狀態與 `UNKNOWN-NOSIDEEFFECT`；T3.3 的 `HANG` 對應 `FAILED`。未發現有 `ASSERT … THEN rc` 而同 Task 無狀態斷言者。
6. 可證偽性 FAIL。T0.1、T1.1、T2.0–T2.4、T3.1–T3.3 均列 mutation；T2.5 完全沒有 mutation test，違反 SPEC §V「全部 11 Task 必附 mutation」。靜態未見恆真斷言，但 future tests 尚未存在，mutation 實跑 rc 均未驗證。

## CODEX-TODO-P1-01

**斷言**: TODO 沒有逐條保留 SPEC 的 `D-4,D-6,D-8,E-1,E-9,E-13,F-1,F-3,F-7,OPEN-2` 對帳鏈；其中 `OPEN-2` 明文要求寫入 TODO §0，實際缺失。
**碼證**: `LC_ALL=C rg -o -N '(D-[0-9]+|E-[0-9]+|F-[0-9]+|G-[0-9]+|H-[0-9]+|E-SCOPE|OPEN-[0-9]+)' docs/GOVB0_FRICTION_SPEC.md | sort -uV`；`rg -n 'D-8|OPEN-2|B-33|F-7|B-36' docs/GOVB0_FRICTION_TODO.md` 無命中；SPEC §N:587-595 指向 B-36/D-8，§A:61 指向 OPEN-2。
**來源摘要**: `docs/GOVB0_FRICTION_SPEC.md#15ce4f6e6a11`；`docs/GOVB0_FRICTION_TODO.md#eabf0456f3c1`
[MAJOR] 信心度=High。語意內容部分散落在 Task 2.5/3.2，但沒有 canonical ID 或具名「合理合併」說明，機械/人工追溯無法證明沒有掉項；修法：在 TODO §T 為每個缺項補一列 `SPEC ID → TODO 落點`，對語意已合併者明寫合併理由；在 §0.2 補 `OPEN-2/B-33 locale` 已知 MAJOR 債，並補 `F-7/B-36` 的具名殘留。

## CODEX-TODO-P0-02

**斷言**: Task 1.1 的冷啟動偽碼呼叫不存在的 `_bc_kv` helper，且把 prompt 組裝 caller 指成 `_run_cli_and_emit`；照 TODO 實作會在既有路徑上失敗或改錯函式。
**碼證**: `rg -n '_bc_kv' scripts/cx_run.sh scripts/brief_conformance_check.sh` → `_bc_kv` 只有 `cx_run.sh:39,44,45,46,47` 的 temp-file 變數；`nl -ba scripts/cx_run.sh | sed -n '500,514p'` → prompt 在 `_prepare_and_run:501-513`；TODO:179-196 卻寫 `_bc_kv` 與 `_run_cli_and_emit`。
**來源摘要**: `docs/GOVB0_FRICTION_TODO.md#eabf0456f3c1`；`scripts/cx_run.sh#39cfdddec350d6`
[BLOCKING] 信心度=High。修法：Task 1.1 的輸入改為既有 `brief_conformance_check.sh <brief> --emit <kv>`，由 `_prepare_and_run` 讀 `_bk`（或明確新增並命名真正 helper）；修改檔案欄改成 `_prepare_and_run`，驗證同時用 `GOVERNANCE_TEST_HARNESS=1` 讀實際 prompt capture，避免把不存在的 parser 當 SoT。

## CODEX-TODO-P0-03

**斷言**: B5 無法取得「Phase 2 動工前」的 immutable gate snapshot，因為 TODO 把 B5 排在 B3/B4 之後，卻要求 snapshot 在 B3 動工前凍結；B6 gate 也未驗 Task 3.1 duration/schema。
**碼證**: TODO:76 `B5|B3,B4`；TODO:388-390 要求 B3 前凍結；TODO:77,88 的 B6 gate 僅 `pytest .../test_atomic_publish.py -q`；Task 3.1:429/445-450 有獨立 duration/schema 需求但無 B6 gate。
**來源摘要**: `docs/GOVB0_FRICTION_TODO.md#eabf0456f3c1`；`docs/GOVB0_FRICTION_SPEC.md#15ce4f6e6a11`
[BLOCKING] 信心度=High。若 B3 已改 `gate_check.sh` 才複製 snapshot，Task 2.5 差集的「舊版」可已含新修法，merge gate 失去 oracle；修法：新增 B3 前置批/步驟先固定並 commit `gate_check_pre_phase2.sh.snapshot`，再跑 B3/B4；同時在 Task 3.1 明列 test 檔與 manifest/schema，並把該 test 加入 B6→B7 gate。

## CODEX-TODO-P1-04

**斷言**: §0 的三項誠實邊界不能全部由測試機械讀取；B-24/H-2 沒有狀態 test，E-10 的 manifest 與 B-14 票面來源均不可解析。
**碼證**: TODO:14-33/491-493 只有 B-24/H-2 宣告；`TEST-3.2-LOCK-⑤` 未覆蓋 ③→④ crash；TODO:429 定義輸出沒有 manifest；`LC_ALL=C rg -n '未定稿' handoffs/20260801-GOV-AMEND-BACKLOG.md` → rc=1，而 B-14 段:316-330 只有 OPEN/繞法文字。
**來源摘要**: `docs/GOVB0_FRICTION_TODO.md#eabf0456f3c1`；`handoffs/20260801-GOV-AMEND-BACKLOG.md#894b9748bdbe`
[MAJOR] 信心度=High。修法：Task 3.1 明定 duration manifest 的檔案路徑、schema、producer 與 `PROVISIONAL` 欄位；Task 3.2 增加 deterministic ③→④ crash probe，斷言 orphan/EEXIST/人工清理狀態；Task 3.3 增加讀取 backlog B-14 bounded section 的狀態 test，並使 canonical B-14 status 明確含「未定稿」；另補 B-24「部分完成」狀態 test。

## CODEX-TODO-P1-05

**斷言**: Task 2.5 沒有 mutation test，無法證明 immutable corpus、snapshot 或非預期差集 gate 被移除/弱化時會轉紅。
**碼證**: `rg -n 'TEST-2\.5-MUT|mutation' docs/GOVB0_FRICTION_TODO.md` → 只有 T0.1/T1.1/T2.0–T2.4/T3.1/T3.2/T3.3 的 mutation，T2.5:401-409 無 mutation；TODO §0.4 與 SPEC §V 都要求全部 11 Task。
**來源摘要**: `docs/GOVB0_FRICTION_TODO.md#eabf0456f3c1`；`docs/GOVB0_FRICTION_SPEC.md#15ce4f6e6a11`
[MAJOR] 信心度=High。修法：Task 2.5 驗證欄新增至少一個可重跑 mutation，例如移除 corpus SHA 綁定/改用 HEAD 或移除「非預期」拒絕分支，並明定 `TEST-2.5-CORPUS-SHA`/`TEST-2.5-EXTRA` 在 mutation 下轉紅、貼直接取 rc 的實跑摘要；不可用恆真或只驗不拋錯取代。

## 出場判準核算

數字：findings=5（≤5：是）；BLOCKING/P0=2（=0：否）；因此需第二輪修補後再審，TODO 目前不可標 Internal Frozen。六項核對結論依序為 `FAIL / PARTIAL / FAIL / FAIL / PASS / FAIL`。

STATUS: DONE
