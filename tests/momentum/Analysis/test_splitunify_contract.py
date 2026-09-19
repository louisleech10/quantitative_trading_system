"""SPLITUNIFY Task 1.2（B1）：`split_unify.json` 之契約測試。

🔴 **B1 刻意不動生產碼**，所以本批**還沒有** `split_projection.py` 可以對證 Python 常數
（那是 B2b）。為了讓本批仍有「兩端對證」而非只驗自己，本檔改以
**SPEC 文件字面**當第二來源：`docs/SPLITUNIFY_SPEC.md` 內必須逐字出現每一個 reason，
JSON 與 SPEC 任一邊漂了就紅。B2b 建 `split_projection.py` 後**再加**
「JSON ↔ Python 常數集合相等」那條（見本檔尾之 TODO 註記），不刪本檔既有斷言。

對應 SPEC：C-8（JSON 單一真相源）、C-3（三態＝兩容器，故禁 `assignment_states`）、
C-0 決議③(b)（`estimand_scope`）。
"""

from __future__ import annotations

import collections
import contextlib
import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
CONTRACT = REPO / "momentum" / "Analysis" / "contracts" / "split_unify.json"
SPEC = REPO / "docs" / "SPLITUNIFY_SPEC.md"
EVENT_IMPORT_CONTRACT = (
    REPO / "momentum" / "Analysis" / "contracts" / "event_import_contract.json"
)

REQUIRED_KEYS = {
    "schema_version",
    "split_authority_values",
    "fail_closed_reasons",
    "estimand_scope_values",
}


@pytest.fixture(scope="module")
def contract() -> dict:
    assert CONTRACT.exists(), f"契約檔不存在: {CONTRACT}"
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_required_keys_present(contract: dict) -> None:
    """缺任一必填鍵 ⇒ 紅（可證偽：刪掉 fail_closed_reasons 本測試必紅）。"""
    missing = REQUIRED_KEYS - set(contract)
    assert not missing, f"split_unify.json 缺鍵: {sorted(missing)}"


def test_value_sets_are_non_empty_closed_sets(contract: dict) -> None:
    """三個值集皆須非空、無重複、全為 str（空集合＝沒有封閉集合可對證）。"""
    for key in ("split_authority_values", "fail_closed_reasons", "estimand_scope_values"):
        values = contract[key]
        assert isinstance(values, list) and values, f"{key} 須為非空 list"
        assert all(isinstance(v, str) and v for v in values), f"{key} 須全為非空字串"
        assert len(set(values)) == len(values), f"{key} 有重複值: {values}"


def test_split_authority_is_kline_holdout(contract: dict) -> None:
    """SPEC C-1：canonical 權威＝K 線 holdout。"""
    assert set(contract["split_authority_values"]) == {"kline_holdout"}


def test_fail_closed_reasons_exact_set(contract: dict) -> None:
    """SPEC C-0／C-2／`R5-C3` 5. 之六個 fail-closed 原因，逐值相等（不是 issubset）。

    🔴 用 `==` 而非 `issubset` 是刻意的：新增字面必須同時改本條，
    否則前端會收到一個它沒有文案的 reason 而顯示空白。
    """
    assert set(contract["fail_closed_reasons"]) == {
        "multi_symbol_projection_unsupported",
        "missing_train_plan",
        "missing_test_plan",
        "canonical_feature_universe_unavailable",
        # ── `R5-C3` 5.（`Task 10.5`）：run 找得到、universe 也有，但依 IC 設定本來就不切分 ──
        # 🔴 與上一條 `canonical_feature_universe_unavailable` **語意不同**，前端文案須可分辨：
        #    那條是「根本拿不到 universe」，這兩條是「拿得到但這次不切」。混用會讓
        #    使用者以為自己的 run 壞了，而其實只是 `ic_train_test_split` 關著。
        "canonical_holdout_disabled",
        "canonical_holdout_insufficient_rows",
    }


def test_fail_closed_reasons_match_momentum_constants(contract: dict) -> None:
    """🔴 `Task 10.5` 兩條新字面之唯一產生點是 momentum 之常數，不得在契約手打。

    鑑別力：把 `canonical_holdout.py` 的常數值改一個字 ⇒ 本條轉紅
    （契約與程式各寫一份、且只改其中一邊，正是本 epic 反覆受傷處）。
    """
    from momentum.Analysis.event_samples.canonical_holdout import (
        REASON_DISABLED, REASON_INSUFFICIENT_ROWS,
    )

    reasons = set(contract["fail_closed_reasons"])
    assert REASON_DISABLED in reasons, f"{REASON_DISABLED!r} 不在契約 fail_closed_reasons"
    assert REASON_INSUFFICIENT_ROWS in reasons, f"{REASON_INSUFFICIENT_ROWS!r} 不在契約"


def test_estimand_scope_exact_set(contract: dict) -> None:
    """SPEC C-0 決議③(b)：event-study-only 之表身須標非 OOS。"""
    assert set(contract["estimand_scope_values"]) == {"full_sample_not_oos"}


def test_assignment_states_must_not_exist(contract: dict) -> None:
    """🔴 SPEC C-3：三態＝兩容器（`assignments` ＋ 獨立 `purged`），**不是**三值枚舉。

    v1 曾把 `assignment_states=["train","purged","test"]` 寫進本檔；若照字面實作成
    `assignments.split_label` 三值，只認兩值的消費者（`pipeline.py:697-698`、
    `baseline.py:106`、`tables.py:305`、`pattern_bridge.py:115,125-127`）**不會報錯，
    只會靜默少算**。本斷言就是擋這個回潮。
    """
    assert "assignment_states" not in contract, (
        "split_unify.json 不得含 assignment_states——三態是兩個容器不是三值枚舉（SPEC C-3）"
    )


def test_purge_reason_stays_in_event_import_contract() -> None:
    """🔴 SPEC C-3：purge reason 沿用既有契約，**不得**在 split_unify.json 另造第二份。"""
    existing = json.loads(EVENT_IMPORT_CONTRACT.read_text(encoding="utf-8"))
    assert existing["split_purge_reasons"] == ["interval_crosses_split_boundary"], (
        "既有 purge reason 字面已漂——SPLITUNIFY 之投影沿用它，漂了要一起改"
    )


def test_every_reason_appears_verbatim_in_spec(contract: dict) -> None:
    """兩端對證（B1 版）：SPEC 內須逐字出現每一個 reason 與權威值。

    B2b 之後會再加「JSON ↔ `split_projection.py` 常數集合相等」，本條不刪。
    """
    spec_text = SPEC.read_text(encoding="utf-8")
    literals = (
        list(contract["fail_closed_reasons"])
        + list(contract["split_authority_values"])
        + list(contract["estimand_scope_values"])
    )
    missing = [lit for lit in literals if lit not in spec_text]
    assert not missing, f"SPEC 未逐字出現這些字面（JSON 與 SPEC 漂了）: {missing}"


# TODO(B2b)：`split_projection.py` 建立後，於本檔新增
#   test_python_constants_equal_json —— `set(split_projection.FAIL_CLOSED_REASONS) ==
#   set(contract["fail_closed_reasons"])`，並驗「刪 JSON 一鍵 ⇒ import 期 raise」。
#   B1 之所以還沒加，是因為本批不動生產碼（SPEC §P 之 B1 定義）。


# ---------------------------------------------------------------------------
# D-002 `D-002-C5` register 碼證錨點（v26；R32 `CODEX-R32-P1-01`）
#
# 🔴 為什麼放在這個檔：六路回歸逐檔明列路徑，本檔已在其中 ⇒ 錨點每次回歸都會被驗，
#    而不是「`Task 9.3` 驗收當下跑一次」。codex 在 R32 明指前一版的問題正是
#    「沒有獨立可重跑的 persisted checker」。
# ---------------------------------------------------------------------------

import importlib.util as _importlib_util  # noqa: E402

_ANCHOR_CHECKER = REPO / "scripts" / "register_anchor_check.py"


def _load_anchor_checker():
    # 🔴 R33 `CODEX-R33-P1-02` 之 assumed ②：checker 被刪／改名時，這裡必須是**明確的紅**，
    #    不是靜默 collect error。
    assert _ANCHOR_CHECKER.is_file(), (
        f"錨點閘不見了：{_ANCHOR_CHECKER}——register 落點就此無人驗證"
    )
    spec = _importlib_util.spec_from_file_location(
        "register_anchor_check", _ANCHOR_CHECKER
    )
    mod = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_d002_register_anchors_all_valid():
    """register 每個 ANCHOR 子句都必須指到它所述之碼（單一精確行＋token 序列恰一次）。"""
    mod = _load_anchor_checker()
    anchors = mod.parse_anchors(mod.SPEC_PATH.read_text(encoding="utf-8"))
    # 🔴 R34 `CODEX-R34-P1-03` ＝ `GROK-R34-P2-01`（兩家撞題）：舊版只寫 `len >= 16`，
    #    把某列的 ANCHOR 整個剝掉、再從別列複製一條補回總數，該測仍綠。
    #    ⇒ 改為**逐列精確計數**：哪一列該有幾個錨點寫死，少一個、多一個、跑錯列都紅。
    expected_per_row = {
        "C5-13": 3, "C5-14": 1, "C5-19": 3, "C5-21": 2, "C5-23": 2,
        "C5-25": 3, "C5-26": 3, "C5-27": 3, "C5-28": 1, "C5-29": 1,
    }
    actual_per_row = collections.Counter(a.row_id for a in anchors)
    assert dict(actual_per_row) == expected_per_row, (
        "register 之 (甲) 列錨點分佈不符：\n"
        f"      期望: {expected_per_row}\n"
        f"      實際: {dict(actual_per_row)}"
    )
    assert len(anchors) == sum(expected_per_row.values()), (
        f"ANCHOR 子句總數 {len(anchors)} ≠ 逐列期望合計 {sum(expected_per_row.values())}"
    )
    bad = []
    for a in anchors:
        ok, why = mod.check_anchor(a)
        if not ok:
            bad.append(f"{a.row_id} {a.path}:{a.line} — {why}")
    assert not bad, "register 錨點失準：\n" + "\n".join(bad)


def test_d002_register_anchor_gate_rejects_known_false_greens():
    """must-fail 回歸：歷來**四代**閘各自放行過的落點，現行閘必須全部拒絕。

    - `:341` 是 `raise ValueError` 的**訊息字串**；`:566` 是另一道重複閘——
      v26 的「行範圍＋子字串」對兩者皆綠（R32 `CODEX-R32-P1-01` 實跑）。
    - `:556`／`pipeline.py:760` 是**純註解行**——v15 的「行號 ≤ 總行數」對兩者皆綠。
    """
    mod = _load_anchor_checker()
    sp = "momentum/Analysis/event_samples/split_projection.py"
    c519 = ("columns", "=", "{", '"timeframe"', ":", '"feature_timeframe"', "}")
    must_fail = [
        (sp, 341, c519),
        (sp, 341, ("feature_timeframe",)),
        (sp, 566, c519),
        (sp, 566, ("feature_timeframe",)),
        (sp, 556, ("purged",)),
        ("momentum/Analysis/event_samples/pipeline.py", 760, ('"n_purged"',)),
    ]
    leaked = []
    for path, line, toks in must_fail:
        ok, why = mod.check_anchor(mod.Anchor("(must-fail)", path, line, toks))
        if ok:
            leaked.append(f"{path}:{line} {list(toks)} — 竟然通過：{why}")
    assert not leaked, "錨點閘又變成弱閘了：\n" + "\n".join(leaked)


@contextlib.contextmanager
def _rooted_at(mod, root):
    """把 checker 的 repo 根暫時指到 fixture 目錄。

    🔴 R34 `CODEX-R34-P1-02` 修法後，`check_anchor` 拒絕絕對路徑與 repo 外路徑
    ⇒ decoy fixture 必須以「換 root ＋ repo 相對路徑」餵入，不能再丟 `tmp_path` 絕對路徑。
    """
    old = mod.REPO_ROOT
    mod.REPO_ROOT = root
    try:
        yield
    finally:
        mod.REPO_ROOT = old


def test_d002_register_anchor_gate_rejects_r33_r34_decoys(tmp_path):
    """must-fail 回歸（R33 三條 ＋ R34 三條 finding 之逐條反例；全部由委員實跑構造）。

    `CODEX-R33-P1-01`：token **子序列**可跳過 token ⇒ 語義替身冒充真實落點。
    `CODEX-R33-P1-02`：貪婪不重疊計數漏算重疊命中 ⇒「恰好一次」不成立。
    `CODEX-R33-P1-03`：`.tsx` 只比指定行、不驗檔內唯一性。
    `CODEX-R34-P1-01`a：**跨行 token**（多行字串）的中間行拿到整個字串 token。
    `CODEX-R34-P1-01`b：`.tsx` 只驗單檔 ⇒ 整行搬到另一個檔即看不出來。
    `CODEX-R34-P1-02`：`REPO_ROOT / <絕對路徑>` 會丟掉前綴 ⇒ 錨可指 repo 外。
    """
    mod = _load_anchor_checker()
    c519 = ("columns", "=", "{", '"timeframe"', ":", '"feature_timeframe"', "}")
    tsx_line = (
        "            ? `／train ${fmt(s.n_train, 0)}／test ${fmt(s.n_test, 0)}"
        "／purge ${fmt(s.n_purged, 0)}`"
    )
    tsx_sha = mod._SHA_PREFIX + hashlib.sha256(
        mod._normalize_text_line(tsx_line).encode("utf-8")
    ).hexdigest()

    (tmp_path / "decoy_semantic.py").write_text(
        'def f():\n    columns = ["timeframe"]; emit("feature_timeframe")\n', encoding="utf-8"
    )
    (tmp_path / "decoy_dup_seq.py").write_text(
        'def f():\n'
        '    columns = {"timeframe": "feature_timeframe"}\n'
        '    columns = {"timeframe": "feature_timeframe"}\n',
        encoding="utf-8",
    )
    # R34-P1-01a：多行字串的中間行——舊版會拿到整個 STRING token
    (tmp_path / "decoy_multiline.py").write_text(
        'def f():\n'
        '    s = """\n'
        '    columns = {"timeframe": "feature_timeframe"}\n'
        '    """\n',
        encoding="utf-8",
    )
    (tmp_path / "decoy_dup_line.tsx").write_text(
        "const a = 1;\n" + tsx_line + "\n" + tsx_line + "\n", encoding="utf-8"
    )
    (tmp_path / "decoy_shadow.tsx").write_text(
        "const decoy = `／train ${fmt(s.n_train, 0)}`;\n" + tsx_line + "\n", encoding="utf-8"
    )
    # R34-P1-01b：同一行搬到另一個檔——單檔唯一性看不出來
    (tmp_path / "old.tsx").write_text("const a = 1;\n" + tsx_line + "\n", encoding="utf-8")
    (tmp_path / "new.tsx").write_text("const b = 2;\n" + tsx_line + "\n", encoding="utf-8")

    cases = [
        ("R33-P1-01 語義替身", "decoy_semantic.py", 2, c519),
        ("R33-P1-02 同序列出現兩行", "decoy_dup_seq.py", 2, c519),
        ("R33-P1-03 同正規化行兩處", "decoy_dup_line.tsx", 2, (tsx_sha,)),
        ("R33-P1-03b 指定行是 decoy", "decoy_shadow.tsx", 1, (tsx_sha,)),
        ("R34-P1-01a 多行字串中間行", "decoy_multiline.py", 3, c519),
        ("R34-P1-01b 同行搬到另一個檔", "old.tsx", 2, (tsx_sha,)),
    ]
    leaked = []
    with _rooted_at(mod, tmp_path):
        for label, rel, line, toks in cases:
            ok, why = mod.check_anchor(mod.Anchor("(decoy)", rel, line, toks))
            if ok:
                leaked.append(f"{label}: {rel}:{line} 竟然通過 — {why}")

    # R34-P1-02：絕對路徑／`..` 必須在**真實 repo root** 下被拒
    outside = tmp_path / "outside.py"
    outside.write_text('def f():\n    columns = {"timeframe": "feature_timeframe"}\n', encoding="utf-8")
    for rel in (str(outside), "../outside.py"):
        ok, why = mod.check_anchor(mod.Anchor("(decoy)", rel, 2, c519))
        if ok:
            leaked.append(f"R34-P1-02 repo 外路徑: {rel} 竟然通過 — {why}")

    assert not leaked, "錨點閘又變成弱閘了：\n" + "\n".join(leaked)


def test_d002_register_anchor_gate_accepts_the_real_lines(tmp_path):
    """可證偽之另一半：**正確**的錨點必須通過，否則上面的 must-fail 可以靠「永遠回 False」作弊。"""
    mod = _load_anchor_checker()
    (tmp_path / "real.py").write_text(
        'def f():\n    columns = {"timeframe": "feature_timeframe"}\n', encoding="utf-8"
    )
    c519 = ("columns", "=", "{", '"timeframe"', ":", '"feature_timeframe"', "}")
    with _rooted_at(mod, tmp_path):
        ok, why = mod.check_anchor(mod.Anchor("(real)", "real.py", 2, c519))
    assert ok, f"真實落點竟被拒（閘壞成永遠 False）：{why}"


def test_d002_register_anchor_gate_fails_cleanly_on_malformed_targets(tmp_path):
    """must-fail 回歸（R35 `CODEX-R35-P2-01`）：壞掉的標的檔要**乾淨地紅**，不是整支 crash。

    非 UTF-8、語法錯誤、未閉合多行字串——三者舊版都會把例外往外丟，
    使 `register_anchor_check.py` 在該情境下是 crash 而非 `ANCHOR_FAIL`。
    """
    mod = _load_anchor_checker()
    (tmp_path / "bad_syntax.py").write_text("def f(:\n    x = 1\n", encoding="utf-8")
    (tmp_path / "bad_utf8.py").write_bytes(b"x = 1\n\xff\xfe\x00bad\n")
    (tmp_path / "unterminated.py").write_text('s = """abc\n', encoding="utf-8")
    problems = []
    with _rooted_at(mod, tmp_path):
        for name in ("bad_syntax.py", "bad_utf8.py", "unterminated.py"):
            try:
                ok, why = mod.check_anchor(mod.Anchor("(malformed)", name, 1, ("x",)))
            except Exception as exc:  # noqa: BLE001 — 這裡就是要抓「不該冒出來的例外」
                problems.append(f"{name}: 竟然 crash — {type(exc).__name__}: {exc}")
                continue
            if ok:
                problems.append(f"{name}: 竟然通過 — {why}")
    assert not problems, "壞檔未被乾淨拒絕：\n" + "\n".join(problems)
