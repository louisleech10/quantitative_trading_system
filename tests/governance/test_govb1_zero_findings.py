"""GOVB1 Task 4.2 — 零 findings 的**單一契約**。

`票 B-38` ∪ `GOV-NOFINDINGS-SENTINEL` ∪ `GOV-NO-FINDINGS-RECEIPT` 合併為
`scripts/govflow_lifecycle.json` 的 `zero_findings_contract` 節，**禁各自實作**。

契約三件事，缺一不可：
  ① sentinel 形態（`<FAMILY>-R<n>-P3-00`，canonical ID 文法之特例）
  ② body 必填欄 ＋ **語意非空**（欄名存在不等於有內容）
  ③ **findings 的落點**（每種 brief-kind 的 findings 寫進哪個檔）

🔴 ② 是本批**唯一許可的行為變更**（`--single` 對 hollow sentinel 由 rc=0 → 非 0）。
其餘任何一格 rc 變動都違反 `G-1` 全域禁令，由
`tests/governance/test_govb1_zeroid_no_regression.py` 的基準表看守。
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS = REPO_ROOT / "scripts" / "completeness_check.sh"
LIFECYCLE = REPO_ROOT / "scripts" / "govflow_lifecycle.json"
TEMPLATE = REPO_ROOT / "templates" / "COMMITTEE_FINDING_TEMPLATE.md"
FIX = REPO_ROOT / "tests" / "governance" / "fixtures" / "govb1"


def _contract() -> dict:
    return json.loads(LIFECYCLE.read_text(encoding="utf-8"))["zero_findings_contract"]


def _rc_single(path: Path, *, family: str = "codex") -> int:
    # 🔴 rc 直接取，禁經 pipe
    return subprocess.run(
        ["bash", str(COMPLETENESS), "--single", str(path), "--family", family],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    ).returncode


def _finding(body_assert: str, body_code: str, *, fid: str = "CODEX-R1-P3-00") -> str:
    return f"## {fid}\n**斷言**: {body_assert}\n**碼證**: {body_code}\n"


# ---------------------------------------------------------------------------
# ① sentinel 形態
# ---------------------------------------------------------------------------


def test_contract_node_exists_and_is_append_only() -> None:
    """契約節存在，且 Task 1.1／1.3 的既有節未被動過（single-writer）。"""
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    assert "zero_findings_contract" in data
    for older in ("_doc", "stages", "kinds", "expected_delta"):
        assert older in data, f"既有節不得消失: {older}"


def test_sentinel_pattern_is_canonical_id_special_case() -> None:
    """🔴 sentinel 不得是「另一套語法」——它必須是 canonical ID 文法的特例。

    契約明文禁第四種 0-findings 表達形式；若 sentinel 用了自己的樣式，
    那就是又生一種形式。
    """
    import re

    pat = _contract()["sentinel"]["id_pattern"]
    canonical = re.compile(r"^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$")
    sentinel = re.compile(pat)
    for sample in ("CODEX-R1-P3-00", "COMPOSER-R12-P3-00"):
        assert sentinel.match(sample), sample
        assert canonical.match(sample), f"{sample} 不符 canonical ID 文法 ⇒ 形成第二套語法"
    for bad in ("CODEX-R1-P2-00", "CODEX-R1-P3-01", "codex-r1-p3-00"):
        assert not sentinel.match(bad), bad


# ---------------------------------------------------------------------------
# ② body 必填欄 ＋ 語意非空（本批唯一許可的行為變更）
# ---------------------------------------------------------------------------


def test_hollow_fixture_now_fails(tmp_path: Path) -> None:
    """`finding_hollow_p300.md`（欄名在、內容空白）⇒ rc≠0。

    這正是 Task 4.2 要修的病：在此之前它 rc=0，
    「零 findings 的輪次」與「該有卻沒寫」無法區分。
    """
    assert _rc_single(FIX / "finding_hollow_p300.md") != 0


def test_real_fixture_still_passes() -> None:
    """`finding_real_p300.md`（四欄皆有實質內容）⇒ rc=0（不得誤擋）。"""
    assert _rc_single(FIX / "finding_real_p300.md") == 0


@pytest.mark.parametrize(
    ("label", "a", "c", "want_fail"),
    [
        ("空白內容", "   ", "   ", True),
        ("單一半形標點", ".", ".", True),
        ("單一全形標點", "。", "。", True),
        ("單一非 ASCII 字", "д", "д", True),
        ("僅斷言有內容", "有實質說明", "  ", True),
        ("僅碼證有內容", " ", "rc=0 實跑", True),
        ("中文實質", "斷言內容", "碼證內容", False),
        ("英數實質", "assertion body", "rc=0", False),
        ("標點夾實質", "。x。", "。1。", False),
        # 🔴 `CODEX-R1-P1-02`：初版白名單（ASCII 英數 ∪ CJK 表意文字位元組範圍）
        #    比 SPEC 更嚴，把下列五語系的實質內容全誤判成空殼（五例實測 rc=1）。
        #    自己加嚴而弄壞五個語系 ⇒ 已改回 SPEC 原邊界（只擋空白／單一字元）。
        ("西里爾", "данные проверены", "rc=0 подтверждено", False),
        ("阿拉伯", "بيانات كاملة", "تم التحقق rc=0", False),
        ("希臘", "Δεδομένα πλήρη", "επαληθεύτηκε", False),
        ("日文假名", "あいうえお", "検証済み rc=0", False),
        ("韓文諺文", "한국어 본문", "검증 완료", False),
        # 具名殘留：SPEC 只界定「單一標點」，多個標點會通過。
        # 再加嚴就是重蹈 P1-02 的覆轍（會連帶弄壞語系），刻意不做。
        ("多個標點（具名殘留：會通過）", "……", "———", False),
    ],
)
def test_substantive_boundary(
    label: str, a: str, c: str, want_fail: bool, tmp_path: Path
) -> None:
    """SPEC 邊界：①只有空白 ⇒ rc≠0 ②只有單一標點 ⇒ rc≠0 ③實質 ⇒ rc=0。

    🔴 判準用**白名單**不用標點黑名單：去空白後須含 ASCII 英數或 CJK 表意文字。
    全形標點（U+3000–U+303F）之 UTF-8 前導為 `\\343`，落在 CJK 表意文字
    （`\\344`–`\\351`）之外 ⇒ 不算實質。黑名單列不完，白名單可導出。
    """
    f = tmp_path / "x.md"
    f.write_text(_finding(a, c), encoding="utf-8")
    got = _rc_single(f)
    if want_fail:
        assert got != 0, f"{label}: 應判 empty-shell 卻 rc=0"
    else:
        assert got == 0, f"{label}: 實質內容卻被誤擋 rc={got}"


def test_substantive_rule_is_language_neutral() -> None:
    """🔴 契約節須記載**語言中立**判準，不得再出現語系白名單。

    初版把判準寫成「ASCII 英數 ∪ CJK 表意文字位元組範圍」，
    那是**語系白名單**——結果誤擋五個語系（`CODEX-R1-P1-02`）。
    正確判準只依 SPEC 邊界：空白／單一字元。
    """
    rule = _contract()["substantive_rule"]
    assert rule.get("language_neutral") is True
    assert "allow_cjk_ideograph_lead_bytes" not in rule, (
        "語系白名單復活 ⇒ 會再次誤擋非 CJK 語系"
    )


def test_fenced_labels_do_not_satisfy_required_fields(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P1-04`：程式碼區塊內的字面標籤不得滿足必填欄。

    否則外層留白、fence 內寫 `**斷言**: x` 就能偽造成有內容。
    """
    f = tmp_path / "fence.md"
    f.write_text(
        "## CODEX-R1-P3-00\n**斷言**:\n**碼證**:\n\n```\n**斷言**: x\n**碼證**: y\n```\n",
        encoding="utf-8",
    )
    assert _rc_single(f) != 0


def test_duplicate_label_on_one_line_is_rejected(tmp_path: Path) -> None:
    """🔴 `CODEX-R1-P1-04`：同一行重複同一標籤 ⇒ fail-closed。

    原本 `sub(".*label", ...)` 是貪婪的（取**最後**一次之後），
    會讓空的外層欄位「借用」內層內容而過關。
    現改為取**第一次**出現，且同行重複即判不合格（格式畸形，解析權不該落在檢查器手上）。
    """
    f = tmp_path / "dup.md"
    f.write_text(
        "## CODEX-R1-P3-00\n**斷言**: **斷言**: x\n**碼證**: **碼證**: y\n",
        encoding="utf-8",
    )
    assert _rc_single(f) != 0


def test_strict_flag_is_not_env_controlled() -> None:
    """🔴 `CODEX-R1-P1-03`：非空判定不得由環境變數控制。

    env 可被外部 shell 汙染 ⇒ 使用者環境裡剛好有該變數就會讓 `--lock` 一併開啟，
    把 `G-1` 明令「不得翻轉」的那一格翻掉。改用位置參數（關不掉也汙染不了）。
    """
    src = (REPO_ROOT / "scripts" / "completeness_check.sh").read_text(encoding="utf-8")
    assert "BODY_SUBSTANCE_STRICT" not in src, (
        "非空判定仍受環境變數控制 ⇒ --lock 可被 env 汙染而翻轉"
    )
    assert 'local strict="${2:-0}"' in src, "strict 未改為位置參數"


def test_lock_path_unaffected_by_polluted_env(tmp_path: Path) -> None:
    """端到端：即使 env 帶了舊變數名，`--lock` 那格仍不得翻轉。"""
    f = tmp_path / "hollow.md"
    f.write_text(_finding("   ", "   "), encoding="utf-8")
    env = os.environ.copy()
    env["BODY_SUBSTANCE_STRICT"] = "1"
    rc = subprocess.run(
        ["bash", str(COMPLETENESS), "--single", str(f), "--family", "codex"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env,
    ).returncode
    assert rc != 0, "交件路徑本來就該擋 hollow"


def test_mut_drop_substantive_check_regresses(tmp_path: Path) -> None:
    """承重 mutation：拿掉非空判定 → hollow fixture 轉回 rc=0。"""
    src = COMPLETENESS.read_text(encoding="utf-8")
    anchor = 'if ($0 ~ /\\*\\*斷言\\*\\*/ && (!strict || substantive(field_body($0, "斷言")))) seen_assert=1'
    assert anchor in src, "mutation 錨點漂移：斷言非空判定"
    mut = tmp_path / "mut_completeness.sh"
    mut.write_text(
        src.replace(anchor, 'if ($0 ~ /\\*\\*斷言\\*\\*/) seen_assert=1', 1).replace(
            'if ($0 ~ /\\*\\*碼證\\*\\*/ && (!strict || substantive(field_body($0, "碼證")))) seen_code=1',
            'if ($0 ~ /\\*\\*碼證\\*\\*/) seen_code=1',
            1,
        ),
        encoding="utf-8",
    )
    base = subprocess.run(
        ["bash", str(COMPLETENESS), "--single", str(FIX / "finding_hollow_p300.md"),
         "--family", "codex"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    ).returncode
    got = subprocess.run(
        ["bash", str(mut), "--single", str(FIX / "finding_hollow_p300.md"),
         "--family", "codex"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    ).returncode
    assert base != 0, "base 應擋下 hollow"
    assert got == 0, "拿掉非空判定後 hollow 仍被擋 ⇒ 該判定未承重"


def test_strict_is_scoped_to_single_entrypoint() -> None:
    """🔴 非空判定**只在 `--single` 啟用**——契約節須如實記載。

    SPEC 三入口矩陣：hollow 在 `--single` 允許翻轉，在 `--lock` 是「rc 不變」。
    無條件啟用會使 `--lock` 一併翻轉而違反 `G-1`（主委實測撞到）。
    """
    ep = _contract()["enforced_entrypoints"]
    assert ep["single"] is True
    assert ep["lock"] is False


# ---------------------------------------------------------------------------
# ③ findings 的落點（票 B-52 的病灶）
# ---------------------------------------------------------------------------


def test_findings_destination_is_own_output_file() -> None:
    """③ 落點必須明文：寫進自己的交件檔，絕不進 stamp-target 或他人產出。"""
    dest = _contract()["findings_destination"]
    assert dest["default"] == "own_output_file"
    assert "stamp_target" in dest["never"]
    assert "other_family_output" in dest["never"]


def test_template_points_to_contract_and_does_not_restate_it() -> None:
    """範本只做 pointer，不得自列一套（否則就是第二真相源）。"""
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "zero_findings_contract" in text, "範本未指回契約節"
    assert "govflow_lifecycle.json" in text
    assert "禁新增第四種表達形式" in text


def test_no_fourth_zero_findings_form_introduced() -> None:
    """🔴 契約禁「第四種表達形式」——本批不得引入新的 0-findings 關鍵字。

    以既有三者之外的關鍵字為封閉檢查對象；出現即代表又長出一種。
    """
    forbidden = ("NO-FINDINGS-OK", "ZERO_FINDINGS_FLAG", "findings_count: 0")
    for path in (COMPLETENESS, LIFECYCLE, TEMPLATE):
        text = path.read_text(encoding="utf-8")
        for kw in forbidden:
            assert kw not in text, f"{path.name} 出現第四種表達形式關鍵字: {kw}"
