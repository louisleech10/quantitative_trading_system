"""票 B-38 — 誠實回報 0 findings 必須有可正規收斂的出路。

病（2026-08-07 實際發生，`GOVB19-X-CONSULT-R1`）：
    委員依 `票 B-31` 加入的 prompt 指示，誠實寫出散文「本輪 0 findings」而未捏造。
    結果 `completeness_check --single` rc=0（0 findings 合法），
    但 `reconcile_build`／`_run_id_layer` 因該來源抽不到 heading ID 而 WARN + FAIL
    ⇒ 整輪只能 abandon ⇒ **誠實則卡住、捏造則通過**。

解（本票，檢查器零改動）：
    沿用既有 `P3-00` sentinel 慣例——它是合法 canonical ID
    （`^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$` 的 `P3` ＋ `00`），
    抽得到就不觸發 vacuous；而空殼仍會被 `_validate_finding_body` 擋。
    改動只在 `cx_run.sh` 的 prompt 措辭。

本檔驗三件事：
    1. 實質 sentinel ⇒ 收斂 PASS（誠實者有出路）
    2. 空殼 sentinel ⇒ 收斂 FAIL（不能用 sentinel 混過去）
    3. 散文版（無 sentinel）⇒ 收斂 FAIL（證明 B-38 的病確實存在，且本解確有必要）

誠實邊界：本檔驗的是**收斂層行為**，不驗「委員會不會照做」——後者是 prompt 遵循率，
    由 `test_cxrun_selfcheck_prompt.py` 驗指示有送到，兩者合起來才完整。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "completeness_check.sh"

_NORMAL_FINDING = """# A

## CODEX-R9-P1-01

**斷言**: 測試用 finding。
**碼證**: 探針。
**來源摘要**: scripts/x.sh#0123456789ab
[MAJOR] 信心度=High。
"""

_SENTINEL_SUBSTANTIVE = """# B

## COMPOSER-R9-P3-00

**斷言**: 本輪逐項核對後無 finding；此為 sentinel，非空殼。
**碼證**: 已跑三項檢查 rc 皆 0（探針）。
**來源摘要**: scripts/x.sh#0123456789ab
[MINOR] 信心度=High。本輪 0 findings。
"""

_SENTINEL_HOLLOW = """# B

## COMPOSER-R9-P3-00

本輪 0 findings。
"""

# 2026-08-07 實際造成整輪 abandon 的形態：只有散文，無 canonical heading
_PROSE_ONLY = """# B

## 本輪 0 findings — 推理保留

逐項核對後無 finding，推理如下：……
"""

_SYNTH = """# Reconcile — 探針

## 群集 / 處置

Verdict: 探針用。

## 附錄：findings 逐字保留

## CODEX-R9-P1-01

**斷言**: 測試用 finding。
**碼證**: 探針。
**來源摘要**: scripts/x.sh#0123456789ab
[MAJOR] 信心度=High。

## COMPOSER-R9-P3-00

**斷言**: 本輪逐項核對後無 finding；此為 sentinel，非空殼。
**碼證**: 已跑三項檢查 rc 皆 0（探針）。
**來源摘要**: scripts/x.sh#0123456789ab
[MINOR] 信心度=High。本輪 0 findings。
"""


def _run_convergence(tmp_path: Path, composer_body: str, synth: str = _SYNTH) -> int:
    """跑收斂層（測試隔離 argv 路徑）。"""
    (tmp_path / "synth.md").write_text(synth, encoding="utf-8")
    (tmp_path / "probe-codex.md").write_text(_NORMAL_FINDING, encoding="utf-8")
    (tmp_path / "probe-composer.md").write_text(composer_body, encoding="utf-8")
    return subprocess.run(
        [
            "bash", str(CHECKER),
            str(tmp_path / "synth.md"),
            str(tmp_path / "probe-codex.md"),
            str(tmp_path / "probe-composer.md"),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={
            **dict(__import__("os").environ),
            "GOVERNANCE_TEST_HARNESS": "1",
            "COMPLETENESS_ALLOW_ARGV_SOURCES": "1",
        },
    ).returncode


def test_substantive_sentinel_converges(tmp_path: Path) -> None:
    """實質 sentinel ⇒ 收斂 PASS——這是誠實回報者的出路。"""
    assert _run_convergence(tmp_path, _SENTINEL_SUBSTANTIVE) == 0, (
        "實質 sentinel 無法收斂 ⇒ 誠實回報 0 findings 仍無正規出路（B-38 未解）"
    )


def test_hollow_sentinel_rejected(tmp_path: Path) -> None:
    """空殼 sentinel ⇒ FAIL——不能靠貼一個 `P3-00` 就混過去。

    🔴 **本測試曾是假綠**〔`CODEX-R1-P1-01`，2026-08-07〕：原版的 hollow source
    與 synth 的 body 不同，實際擋下它的是 **body-hash 不一致**而非 body validator；
    codex 把 source validator 改成 `if false` 後本測試仍 passed，證明它沒測到目標。

    修法：synth 內的該 finding body **與 hollow source 逐字相同**，
    body-hash 因此一致，唯一能擋下的就只剩 body validator。
    """
    # synth 的 sentinel 區塊與 hollow source 逐字相同 ⇒ 排除 body-hash 這條擋法
    hollow_synth = (
        _SYNTH.split("## COMPOSER-R9-P3-00")[0]
        + "## COMPOSER-R9-P3-00\n\n本輪 0 findings。\n"
    )
    assert _run_convergence(tmp_path, _SENTINEL_HOLLOW, hollow_synth) != 0, (
        "空殼 sentinel 被接受 ⇒ 可用空 P3-00 規避實質審查"
    )


def test_hollow_rejection_is_not_body_hash_artifact(tmp_path: Path) -> None:
    """對照：證明上一條擋下的理由確實是 body validator，不是 body-hash。

    若 stderr 只有 body-hash 不符而無 `empty-shell`，代表上一條又退回假綠。
    """
    hollow_synth = (
        _SYNTH.split("## COMPOSER-R9-P3-00")[0]
        + "## COMPOSER-R9-P3-00\n\n本輪 0 findings。\n"
    )
    (tmp_path / "synth.md").write_text(hollow_synth, encoding="utf-8")
    (tmp_path / "probe-codex.md").write_text(_NORMAL_FINDING, encoding="utf-8")
    (tmp_path / "probe-composer.md").write_text(_SENTINEL_HOLLOW, encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(CHECKER), str(tmp_path / "synth.md"),
         str(tmp_path / "probe-codex.md"), str(tmp_path / "probe-composer.md")],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={**dict(__import__("os").environ),
             "GOVERNANCE_TEST_HARNESS": "1", "COMPLETENESS_ALLOW_ARGV_SOURCES": "1"},
    )
    assert "empty-shell" in proc.stderr, (
        f"擋下理由不是 empty-shell ⇒ 測試又回到假綠\nstderr={proc.stderr}"
    )


def test_prose_only_still_fails(tmp_path: Path) -> None:
    """散文版仍 FAIL——證明 B-38 的病確實存在，本解確有必要。

    這是**反向對照**：若散文版本來就能過，那 sentinel 解法就是多餘的。
    採用 2026-08-07 `GOVB19-X-CONSULT-R1` 實際造成整輪 abandon 的形態。
    """
    synth_without_sentinel = _SYNTH.split("## COMPOSER-R9-P3-00")[0]
    assert _run_convergence(tmp_path, _PROSE_ONLY, synth_without_sentinel) != 0, (
        "散文版竟能收斂 ⇒ B-38 的病不存在，本票的 sentinel 解法為多餘"
    )


@pytest.mark.parametrize(
    "heading,why",
    [
        ("## COMPOSER-R9-P3-00", "P3-00 為合法 canonical（P[0-3] ＋ 2 位數）"),
        ("## COMPOSER-R9-P3-01", "同族其他編號亦合法"),
    ],
)
def test_sentinel_id_is_canonical(tmp_path: Path, heading: str, why: str) -> None:
    """sentinel 必須是合法 canonical ID——這正是「零改動」成立的前提。

    若 P3-00 不合 canonical，抽取層就會判它畸形，整個解法崩潰。
    """
    doc = tmp_path / "probe-composer.md"
    doc.write_text(
        f"# t\n\n{heading}\n\n**斷言**: x。\n**碼證**: y。\n"
        f"**來源摘要**: scripts/x.sh#0123456789ab\n[MINOR] 信心度=High。\n",
        encoding="utf-8",
    )
    rc = subprocess.run(
        ["bash", str(CHECKER), "--single", str(doc), "--family", "composer"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    ).returncode
    assert rc == 0, f"{heading} 未被當作合法 canonical ID（{why}）"
