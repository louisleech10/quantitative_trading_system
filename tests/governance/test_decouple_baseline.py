"""canonical Rule 2/3/4 scanner 之 baseline 模式（`scripts/check_decoupling_imports.py`）。

為何存在（使用者 2026-08-14T18:40+08:00：「可以掛的就要掛上去」）：
    該 scanner 自 2026-07-14 起**實質停擺**——`scripts/decouple_allowlist.md` 缺 grok 戳記，
    fail-closed 於戳記關卡 ⇒ 從未掃到任何一行程式碼，Rule 2/3/4 無人看守。
    戳記補回後仍有 20 筆既有違反（CLAUDE.md 記載之 P2 債），直接掛上會擋死
    所有 `momentum/`／`api/` 編輯 ⇒ 加 baseline：**觀測集合 ⊆ baseline 即通過，只擋新增**。

🔴 四象限缺一不可：
    · 只驗「子集通過」⇒ 無法排除它恆通過（等於沒有 scanner）
    · 只驗「新增被擋」⇒ 無法排除它恆擋
    · **缺檔必須 fail-closed**：「baseline 不在就當零違反放行」正是 S1.2 的 fail-open 病灶
    · **空 baseline 必須是最嚴格**，不是「跳過」：S1.2／S6.2 兩度出現
      「schema 欄位被清空即整段跳過」的形態，此處刻意反向設計

🔴 本檔以**函式層注入 verifier** 取得掃描結果：production CLI 刻意不提供 stamp bypass，
   而現樹戳記未齊 ⇒ 不注入就測不到 baseline 邏輯本身。注入點是 `scan()` 既有的測試介面。
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "scripts" / "check_decoupling_imports.py"
BASELINE = REPO / "scripts" / "decouple_baseline.txt"


def _mod():
    spec = importlib.util.spec_from_file_location("check_decoupling_imports", SRC)
    assert spec and spec.loader
    m = importlib.util.module_from_spec(spec)
    sys.modules["check_decoupling_imports"] = m
    spec.loader.exec_module(m)
    return m


def _scan(m):
    return m.scan(
        REPO / "momentum",
        [REPO / "api" / n for n in ("services", "routes", "websocket", "models")],
        REPO / "scripts" / "decouple_allowlist.md",
        stamp_verifier=lambda p: (True, "test-injected"),
        service_root=REPO / "api" / "services",
    )


def _observed_keys(m):
    return set(m.baseline_keys(_scan(m).violations, REPO))


def test_baseline_file_exists_and_is_nonempty() -> None:
    m = _mod()
    keys = m.load_baseline(BASELINE)
    assert keys, "baseline 為空 ⇒ 每一筆既有債都會被當成新增，掛上即擋死"


def test_current_tree_is_subset_of_baseline() -> None:
    """該放的放了：現樹觀測集合須 ⊆ baseline，否則掛上去我自己動不了。"""
    m = _mod()
    extra = _observed_keys(m) - m.load_baseline(BASELINE)
    assert not extra, f"現樹有不在 baseline 內的違反：{sorted(extra)}"


def test_new_violation_is_detected(tmp_path: Path) -> None:
    """🔴 承重反例：baseline 少一筆 ⇒ 對應違反必須被判為新增。

    以移除 baseline 中一列來模擬「新出現的違反」，等價於加入一筆新違反，
    且不必真的去改 api/ 或 momentum/ 的程式碼。
    """
    m = _mod()
    observed = _observed_keys(m)
    assert observed, "現樹應有既有債；若為 0 表示 scanner 空轉，本測試前提不成立"
    victim = sorted(observed)[0]
    shrunk = tmp_path / "b.txt"
    shrunk.write_text(
        "\n".join(sorted(observed - {victim})) + "\n", encoding="utf-8"
    )
    new_keys = observed - m.load_baseline(shrunk)
    assert new_keys == {victim}, f"新增違反未被偵測：{new_keys}"


def test_missing_baseline_fails_closed(tmp_path: Path) -> None:
    """🔴 缺檔 ⇒ ScannerError，不得靜默視為零違反。"""
    m = _mod()
    with pytest.raises(m.ScannerError) as exc:
        m.load_baseline(tmp_path / "does_not_exist.txt")
    assert "不存在" in str(exc.value)


def test_empty_baseline_is_strictest_not_skip(tmp_path: Path) -> None:
    """🔴 只有註解的 baseline ⇒ 零筆已知 ⇒ 所有違反皆為新增（最嚴格），而非跳過。"""
    m = _mod()
    empty = tmp_path / "b.txt"
    empty.write_text("# 只有註解\n#\n", encoding="utf-8")
    assert m.load_baseline(empty) == set()
    assert _observed_keys(m) - m.load_baseline(empty) == _observed_keys(m)


def test_key_is_line_number_independent() -> None:
    """鍵不含行號——否則每次編輯就整批失效，baseline 等於沒有。"""
    m = _mod()
    for key in m.load_baseline(BASELINE):
        parts = key.split("|")
        assert len(parts) == 5, f"鍵欄數不對（應為 路徑|規則|形式|標的|#序號）: {key}"
        assert ":" not in parts[0], f"鍵含行號: {key}"
        assert parts[4].startswith("#") and parts[4][1:].isdigit(), f"序號欄格式錯: {key}"


def test_line_shift_does_not_invalidate_baseline() -> None:
    """整批行號位移不得使 baseline 失效——這正是不含行號的目的。"""
    m = _mod()
    violations = _scan(m).violations
    shifted = [
        m.Violation(path=v.path, line=v.line + 1000, rule=v.rule, form=v.form, target=v.target)
        for v in violations
    ]
    assert set(m.baseline_keys(shifted, REPO)) == set(m.baseline_keys(violations, REPO))


def test_extra_occurrence_in_same_group_is_new(tmp_path: Path) -> None:
    """🔴 CODEX-R1-P1-05：同檔對同標的**再多加一個** import 必須判為新增。

    只用群組鍵（不含 occurrence 序號）時，這一筆會落在既有鍵上被放行——
    那會讓 baseline 從「擋新增」退化成「擋新檔案」。
    """
    m = _mod()
    violations = list(_scan(m).violations)
    assert violations, "現樹應有既有債；為 0 表示 scanner 空轉"
    dup_src = violations[0]
    dup = m.Violation(
        path=dup_src.path,
        line=dup_src.line + 7,          # 同檔同標的、不同行 ⇒ 群組鍵相同
        rule=dup_src.rule,
        form=dup_src.form,
        target=dup_src.target,
    )
    before = set(m.baseline_keys(violations, REPO))
    after = set(m.baseline_keys(violations + [dup], REPO))
    assert after - before, "多加一筆同群組違反卻未產生新鍵 ⇒ 新增債會被誤放行"


def test_stamp_gate_still_blocks_production_cli() -> None:
    """🔴 反向確認：baseline 模式**不得**順手繞過戳記檢查。

    現樹 `decouple_allowlist.md` 缺 grok 戳記 ⇒ 帶 --baseline 的 CLI 仍須 rc≠0。
    少了這條，baseline 就可能變成一個無聲的 stamp bypass。
    """
    import subprocess

    res = subprocess.run(
        [
            sys.executable,
            str(SRC),
            "--baseline",
            "scripts/decouple_baseline.txt",
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    if "戳記" in res.stderr:
        assert res.returncode != 0, "戳記未齊卻放行 ⇒ baseline 變成 stamp bypass"
    else:
        # 戳記已補齊（grok 已核可）⇒ 應走到 baseline 比對且通過
        assert res.returncode == 0, res.stderr
        assert "BASELINE OK" in res.stdout
