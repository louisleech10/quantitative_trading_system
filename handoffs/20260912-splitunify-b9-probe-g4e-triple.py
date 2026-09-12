#!/usr/bin/env python3
"""b9 探針：(G-4e) 第三份判準在「三份同錯」時是否仍會放行。

🔴 為什麼需要這支：R10 composer 在交件中自陳其探針結果為「獨立實作時
`g4e_pass=False`、三份同錯時 `g4e_pass=True`」。依本專案之驗證保真度鐵律，
主委採納該結論前**須自行複跑**，不得只引用委員交件。

本探針以純函式重現三個判側實作，不 import 任何專案模組（避免與被測邏輯耦合）：
  · proj      ＝投影端判側
  · oracle    ＝獨立 oracle 判側（(G-4c) 的第二份推導）
  · expected  ＝(G-4e) 的第三份判準（應依 decision-anchor 三段式）

情形 A（獨立實作）：proj/oracle 誤用 cutoff，expected 正確用 decision
  ⇒ 期望 g3b_pass=True（兩邊一致而放行）、g4e_pass=False（第三份抓到）
情形 B（三份同錯）：expected 亦複製 cutoff 邏輯
  ⇒ 期望 g3b_pass=True 且 g4e_pass=True（三份皆綠，錯誤成員集會被凍結）

用法：`venv/bin/python handoffs/20260912-splitunify-b9-probe-g4e-triple.py`
"""


def side_by_cutoff(cutoff, train_last, test_start):
    """錯誤語意：以 feature_cutoff_ms 判側（換錨前的舊做法）。"""
    if cutoff <= train_last:
        return "train"
    if cutoff >= test_start:
        return "test"
    return "purged"


def side_by_decision(decision, train_last, test_start):
    """正確語意：以 decision_at_ms 判側（Task 9.2b 三段式，隔離帶 ⇒ purged）。"""
    if decision <= train_last:
        return "train"
    if decision >= test_start:
        return "test"
    return "purged"


def run_case(name, *, decision, cutoff, train_last, test_start, expected_uses_decision):
    proj = side_by_cutoff(cutoff, train_last, test_start)
    oracle = side_by_cutoff(cutoff, train_last, test_start)
    if expected_uses_decision:
        expected = side_by_decision(decision, train_last, test_start)
    else:
        expected = side_by_cutoff(cutoff, train_last, test_start)
    correct = side_by_decision(decision, train_last, test_start)

    g3b_pass = proj == oracle
    g4e_pass = (proj == oracle) and (oracle == expected)

    print(
        "%-22s proj=%-7s oracle=%-7s expected=%-7s correct=%-7s "
        "g3b_pass=%-5s g4e_pass=%-5s 成員集正確=%s"
        % (name, proj, oracle, expected, correct, g3b_pass, g4e_pass, proj == correct)
    )
    return g3b_pass, g4e_pass, proj == correct


if __name__ == "__main__":
    # R9/R10 三家各給的反例，皆為 decision != cutoff 且落在隔離帶
    CASES = [
        ("composer decision=250", dict(decision=250, cutoff=200, train_last=200, test_start=300)),
        ("grok gapX decision=950", dict(decision=950, cutoff=900, train_last=900, test_start=1000)),
    ]

    print("=== 情形 A：第三份判準獨立實作（用 decision-anchor）===")
    a = [run_case(n, expected_uses_decision=True, **kw) for n, kw in CASES]

    print()
    print("=== 情形 B：三份同錯（第三份也複製 cutoff 邏輯）===")
    b = [run_case(n, expected_uses_decision=False, **kw) for n, kw in CASES]

    print()
    print("判定：")
    ok_a = all(g3b and (not g4e) and (not correct) for g3b, g4e, correct in a)
    ok_b = all(g3b and g4e and (not correct) for g3b, g4e, correct in b)
    print("  情形 A 全部『G-3b 放行但第三份攔下』：%s" % ok_a)
    print("  情形 B 全部『三份皆綠而成員集錯』  ：%s" % ok_b)
    if ok_a and ok_b:
        print("  ⇒ composer 之結論**成立**：(G-4e) 只在第三份獨立實作時有效；")
        print("    三份同錯仍會放行 ⇒ §G 須把此列為**殘餘誠實邊界**，並明禁共用實作／同 PR 複製。")
    else:
        print("  ⇒ 與 composer 所述不符，須逐案檢視（勿直接採納其結論）。")
