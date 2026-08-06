"""B-39 E2b — heading 路由分層的 mutation 鑑別力。

為何存在（2026-08-06）：
    `test_completeness_idlike_fp.py` 從 SPEC 行為表機械抽取 23 列逐列比對 rc，
    但**它證明不了「每一層都在做事」**——某層被移除後若另一層恰好給出相同 rc，
    行為表仍會全綠。本檔補的就是這個缺口：對 E2b 新增的兩層各做一支反向 mutation。

E2b 四層（`scripts/completeness_check.sh` 的 `extract_heading_ids()`）：
    (1)  整行 canonical                    → 既有 family-binding（本檔不測，既有測試已覆蓋）
    (3a) 首 token 命中 ^[A-Z]+-R[0-9]+-P   → rc==1（near-canonical 守衛）
    (3b) 首 token ∈ STRUCT_TOKEN_ALLOWLIST → 放行
    (3c) arity：id-like 且 n==1 → rc==1 ；n>1 → 放行

裁定來源：`handoffs/reconcile/20260806-govb39-b1-consult-r2/synth.md`（三家零分歧採 E2b）。

誠實邊界：本檔只驗「層存在且有鑑別力」，不驗「判準涵蓋所有畸形 ID」——
    後者為 SPEC §V 具名殘留（`## CODEX-NOTES 討論` 會被 (3c) 放行），
    已由 `test_named_residual_is_explicit` 釘成測試而非留在散文裡。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "completeness_check.sh"

# (3a) 守衛錨點：移除它，帶尾綴的 finding ID 會被 (3c) 當結構標題放行
_GUARD_ANCHOR = "      if (tok ~ /^[A-Z]+-R[0-9]+-P/) {"
# (3c) arity 錨點：拿掉 n==1 條件即退回舊的形狀猜測
_ARITY_ANCHOR = "      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/ && n == 1) {"
_ARITY_REVERTED = "      if (tok ~ /^[A-Z]+(-[A-Z0-9]+)+$/) {"


def _write_doc(tmp_path: Path, heading: str) -> Path:
    doc = tmp_path / "probe-codex.md"
    doc.write_text(f"# 探針\n\n{heading}\n\n內容。\n", encoding="utf-8")
    return doc


def _proc(script: Path, doc: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), "--single", str(doc)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def _run(script: Path, doc: Path) -> int:
    return _proc(script, doc).returncode


def _heading_layer_rejected(script: Path, doc: Path) -> bool:
    """heading 路由層是否判它為畸形 ID。

    不能只看 rc：`_validate_finding_body()` 有**自己一套** finding ID 判定，
    heading 層放行後它仍可能以「empty-shell finding」擋下同一份檔
    （2026-08-06 實測，同一概念兩處定義不一致——已具名記錄於 SPEC）。
    只看 rc 會把兩層混為一談，讓 mutation 測不到 (3a) 這一層。
    """
    return "invalid finding ID" in _proc(script, doc).stderr


def _mutate(tmp_path: Path, old: str, new: str, name: str) -> Path:
    """產生突變體；錨點不存在即失敗（防測試與實作脫節）。"""
    src = CHECKER.read_text(encoding="utf-8")
    assert old in src, f"mutation 錨點漂移，須更新：{old!r}"
    mutant = tmp_path / name
    mutant.write_text(src.replace(old, new, 1), encoding="utf-8")
    syntax = subprocess.run(["bash", "-n", str(mutant)], capture_output=True, text=True)
    assert syntax.returncode == 0, f"突變體語法錯誤: {syntax.stderr}"
    return mutant


def test_struct_token_allowlist_entries_are_live() -> None:
    """allowlist 三個初始元素須真的寫在腳本裡（防被靜默拿掉）。"""
    src = CHECKER.read_text(encoding="utf-8")
    for token in ("OUT-OF-SCOPE", "NON-BLOCKING", "FACT-RECEIPT"):
        assert f'struct_ok["{token}"]=1' in src, f"allowlist 缺初始元素: {token}"


def test_mutation_removing_arity_breaks_structural_passthrough(tmp_path: Path) -> None:
    """移除 (3c) 的 n==1 條件 ⇒ 退回舊形狀猜測 ⇒ 帶尾綴結構標題轉紅。

    這是 B-39 的核心：`### G-1 extra` 必須靠 arity 才放行。
    """
    doc = _write_doc(tmp_path, "### G-1 extra")
    assert _run(CHECKER, doc) == 0, "前提不成立：現行實作應放行帶尾綴結構標題"

    mutant = _mutate(tmp_path, _ARITY_ANCHOR, _ARITY_REVERTED, "mutant_arity.sh")
    assert _run(mutant, doc) != 0, "移除 arity 條件後仍放行 ⇒ 放行測試無鑑別力（廉價綠燈）"


def test_mutation_removing_guard_lets_trailing_finding_id_escape(tmp_path: Path) -> None:
    """移除 (3a) near-canonical 守衛 ⇒ 帶尾綴的 finding ID 被 arity 誤放。

    這證明 (3a) 不是冗餘層——沒有它，行為表第 146 列
    （`## CODEX-R4-P0-01 附加標題` rc==1）會失守。
    """
    # 🔴 案例刻意**不含**合法家族名——否則會被 (3a2) 攔下，測不到 (3a) 這一層。
    #    `NOTAFAMILY-R1-P9-01`：P9 非法故不是 canonical，但首 token 命中 ^[A-Z]+-R[0-9]+-P。
    doc = _write_doc(tmp_path, "## NOTAFAMILY-R1-P9-01 附加標題")
    assert _heading_layer_rejected(CHECKER, doc), (
        "前提不成立：現行 heading 層應以 invalid finding ID 擋下帶尾綴的 near-canonical ID"
    )

    mutant = _mutate(tmp_path, _GUARD_ANCHOR, "      if (0) {", "mutant_guard.sh")
    assert not _heading_layer_rejected(mutant, doc), (
        "移除 near-canonical 守衛後 heading 層仍判畸形 ⇒ 該層是冗餘的，或 mutation 沒生效"
    )


@pytest.mark.parametrize(
    "heading,why",
    [
        ("## ADV-CODEX-1 討論", "舊格式 adversarial finding ID ＋ 尾綴"),
        ("## CODEX-BAD 追加說明", "家族前綴 ＋ 尾綴"),
        ("## CODEX-NOTES 討論", "家族前綴 ＋ 尾綴（原具名殘留，已由 (3a2) 關閉）"),
        ("## ADV-GROK-4 說明", "語料中 334 個同形舊格式 ID 的代表"),
    ],
)
def test_family_token_never_escapes_via_arity(
    tmp_path: Path, heading: str, why: str
) -> None:
    """首 token 含合法家族名者，加尾綴也不得逃脫（(3a2) 層）。

    這一層是 code review 補的〔`CODEX-R1-P1-01`〕：純 arity 會讓
    `## ADV-CODEX-1 討論` 這類舊格式 finding ID 靠加尾綴繞過。
    """
    assert _run(CHECKER, _write_doc(tmp_path, heading)) == 1, why


@pytest.mark.parametrize(
    "heading",
    ["### G-1 extra", "## OUT-OF-SCOPE", "### E-1 換行繞道", "## NON-BLOCKING"],
)
def test_family_guard_does_not_break_structural_passthrough(
    tmp_path: Path, heading: str
) -> None:
    """(3a2) 收窄後，B-39 要放行的結構標題必須不受影響。

    收窄的同時證明沒把放行面弄壞——這是 B-39 三輪修補失敗的教訓
    （每次修補都製造新缺口，觸發斷路器）。
    """
    assert _run(CHECKER, _write_doc(tmp_path, heading)) == 0, f"結構標題被誤擋: {heading}"
