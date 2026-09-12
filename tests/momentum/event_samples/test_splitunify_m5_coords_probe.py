"""M5 座標系四案真值表——以 pytest 承載，使結論可重跑、改壞會紅。

🔴 本檔驗的是 `docs/SPLITUNIFY_SPEC.D-002.md` `Task 9.2b` 步驟 0③ 之**契約完備性**：
`validate_split_pair_integrity` 對「`row_index` 座標系」與「`ts`／`symbols` 宇宙」
的四種組合各有不同結果，因此 SPEC 只寫「`row_index` 二擇一」並不足以定義行為。

四案（交錯批：全域 symbols = [A, B, A, B]，symbol A 之全域位置 = 0, 2）：
  case1 全域索引 ＋ 全域宇宙 ⇒ PASS
  case2 全域索引 ＋ 局部宇宙 ⇒ IndexError（codex R10 的「誤殺合法批」反例）
  case3 局部索引 ＋ 局部宇宙 ⇒ PASS（SPEC 二擇一未涵蓋的第三條可行路徑）
  case4 局部索引 ＋ 全域宇宙 ⇒ CrossSymbolLeakageError

探針本體在 `handoffs/20260912-splitunify-b9-probe-m5-coords.py`；本檔以 importlib 載入
並呼叫其 `run_case`，**刻意不重寫** fixture 構造，避免兩份構造漂移。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PROBE_PATH = (
    Path(__file__).resolve().parents[3]
    / "handoffs"
    / "20260912-splitunify-b9-probe-m5-coords.py"
)


def _load_probe():
    """載入探針模組；找不到即 fail-closed，不得靜默跳過。"""
    assert _PROBE_PATH.is_file(), f"探針檔不存在: {_PROBE_PATH}"
    spec = importlib.util.spec_from_file_location("splitunify_m5_probe", _PROBE_PATH)
    assert spec is not None and spec.loader is not None, f"探針載入失敗: {_PROBE_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_m5_coordinate_truth_table() -> None:
    """四案結果須與 R11 複驗一致；任一格改變即代表 validator 契約已變。"""
    probe = _load_probe()
    g_ts, g_sym = probe.TS_GLOBAL, probe.SYM_GLOBAL
    l_ts, l_sym = probe.TS_LOCAL, probe.SYM_LOCAL

    case1 = probe.run_case("case1", [0], [2], g_ts, g_sym, g_ts[[0]], g_ts[[2]])
    case2 = probe.run_case("case2", [0], [2], l_ts, l_sym, g_ts[[0]], g_ts[[2]])
    case3 = probe.run_case("case3", [0], [1], l_ts, l_sym, l_ts[[0]], l_ts[[1]])
    case4 = probe.run_case("case4", [0], [1], g_ts, g_sym, l_ts[[0]], l_ts[[1]])

    assert case1 == "PASS", "全域索引配全域宇宙本應通過"
    assert case2 == "IndexError", "全域索引配局部宇宙須誤殺——這正是 codex 的反例"
    assert case3 == "PASS", (
        "局部索引配局部宇宙可通過 ⇒ SPEC 之二擇一不窮盡，須改為座標系三選一"
    )
    assert case4 == "CrossSymbolLeakageError", "局部索引配全域宇宙須被跨標的洩漏閘擋下"
