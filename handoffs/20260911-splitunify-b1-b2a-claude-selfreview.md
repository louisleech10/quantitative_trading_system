# SPLITUNIFY B1＋B2a — Claude 自產獨立審查（與三家平行）

依 `feedback_claude_own_version`。審查對象＝我自己寫的 B1（commit `9607430d`）
與 B2a（commit `a58754d6`）。
🔴 **本檔之修法一律等三家收斂後才動檔**——他們正在讀這兩個 commit 的內容，
我現在改會讓他們引用的行號失效。

---

## CLAUDE-R1-P3-01

**斷言**: `_as_ms` 對 tz-aware index 的行為**正確但會放大上游的不一致**：naive 與 UTC 給出**相同**毫秒，非 UTC 時區（Asia/Tokyo）給出**不同**毫秒——這是對的（不同絕對時刻），但若同一批資料在一條路徑是 naive、另一條是 tz-aware，兩端算出的 `test_start_ms` 會差整整一個時區位移。

**碼證**: 主委實跑（500 根 1h，`oos_test_size=0.3, purge_gap=2, embargo=2`）——
`naive` → `test_start_ms=1736964000000`（2025-01-15 18:00）；
`utc` → `1736964000000`（同上，逐值相同）；
`Asia/Tokyo` → `1736931600000`（2025-01-15 09:00，差 9 小時）。
實作見 `momentum/core/split_preview.py` 之 `_as_ms`：走
`pd.Timestamp(value).value // 10**6`，回的是 **UTC 納秒**，故 tz 換算正確。

**來源摘要**: momentum/core/split_preview.py#6b6a1d95c5cc

判定：**不是 bug，是需要具名的前提**。修法（三家收斂後套用）：在 `_as_ms` 之 docstring
補一句「本函式對 tz 之處理正確（回 UTC 毫秒），但**要求同一票內的 feature_index
時區慣例一致**；naive 與 UTC 等價，naive 與非 UTC 時區不等價」。
並在 SPEC C-0 之 boundary builder 段補同一句——這正是 C-0 的核心論點
（**必須共用同一個 universe**）在時區維度上的延伸。

---

## CLAUDE-R1-P3-02

**斷言**: R1 brief 的「我沒查的」第 2 條（`tests/baselines/` 這個新目錄會不會被 pytest 收集規則掃到而報錯）**經查不成立**——該目錄收集到 0 個項目，不干擾。

**碼證**: `venv/bin/python -m pytest -q --collect-only tests/baselines` →
`collected 0 items` / `no tests collected in 0.02s`（rc=5＝無測試可收，非錯誤）。
`analysis_known_failures.nodeids` 非 `.py` 檔，不符 `python_files` 規則。

**來源摘要**: tests/baselines/analysis_known_failures.nodeids

⇒ 本條記為**已自證**，不需三家再答；若三家仍答，以本碼證覆核。

---

## 我對必答 3／4 的自評（先寫下來，之後與三家對照）

- **必答 3（B1 的契約測試算不算兩端對證）**：我的立場是**算，但比 B2b 弱一級**。
  第二來源是 `docs/SPLITUNIFY_SPEC.md` 的文件字面，它與 JSON 由**同一個人（我）**在
  同一批寫成 ⇒ 共同模式失效（common-mode failure）的風險真實存在。
  它擋得住「日後有人只改 JSON 不改 SPEC」或反之，擋不住「我一開始兩邊就都寫錯」。
  ⇒ B2b 之 Python 常數對證才是真正的第二來源（不同作者輪次、不同介質）。
  這條我已在測試檔尾以 `TODO(B2b)` 具名，不是忘了。
- **必答 4（19 vs 20）**：我傾向「既有紅本來就會飄」——`HANDOFF.md` 記的 20 條裡
  有 8 條是「單獨跑會綠」的測試間污染型，那類的數量本來就依收集順序浮動。
  但我**沒有實跑證明**（要 17 分鐘重跑一次 pre-B1 狀態）。
  ⇒ 若三家要求證明，我會跑；若三家同意「方向性判準（只准變短）已經吸收這個浮動」，
  則不跑——因為 B3 的驗收本來就不比對總數，只比對「有沒有清單外的 FAILED」。

---

## Verdict

**可進 B2b。** 兩條自查都是 P3（一條是需具名的前提、一條是已否證的假設）。
必答 3 之弱點已具名且有 B2b 的補強路徑；必答 4 之浮動已被 B3 的方向性判準吸收。
