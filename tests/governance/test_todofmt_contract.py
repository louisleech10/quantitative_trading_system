"""TODOFMT Task 0.1：manifest 契約與 contract_digest（docs/TODOFMT_SPEC.md Task 0.1）。

每條邊界一個具名測試；於 tmp 迷你 repo 內執行檢查器之複本（契約與 repo 根皆由檢查器所在位置推導），
故不碰真實工作區、不依賴真實檔案之存在與否。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "todofmt_check.sh"
CONTRACT = REPO_ROOT / "scripts" / "todofmt_contract.json"

# SPEC Task 0.1 契約表之鍵集（說明欄；權威為契約 JSON——本測試斷言二者相等）
SPEC_TABLE_KEYS = {
    "stub_modules", "test_files", "script_acceptance", "contract_jsons", "spec_path",
    "contract_digest", "run_receipts", "batch_card",
    "batch_card.depends", "batch_card.touches", "batch_card.callers_now", "batch_card.callers_later",
    "batch_card.relocates_to", "batch_card.relocates_at", "batch_card.reexport", "batch_card.tests_stay",
    "batch_card.gate_cmd", "batch_card.forbidden", "batch_card.risk_mitigation", "batch_card.coverage_risk",
    "batch_card.lifecycle", "batch_card.not_executable",
}


def _mini_repo(tmp_path: Path) -> Path:
    """迷你 repo：檢查器與契約取自模組層級之 CHECKER／CONTRACT（mutation 探針以 monkeypatch 換成改壞之複本）。"""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy(CHECKER, repo / "scripts" / "todofmt_check.sh")
    shutil.copy(CONTRACT, repo / "scripts" / "todofmt_contract.json")
    for rel, body in {
        "docs/X_SPEC.md": "x\n",
        "tests/test_x.py": "x\n",
        "momentum/m.py": "x\n",
        "api/now.py": "x\n",
        "handoffs/run_receipts/r.json": json.dumps({"schema_version": 1, "command": "c", "exit_code": 0}),
    }.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return repo


def _digest(repo: Path) -> str:
    out = subprocess.run(
        ["bash", str(repo / "scripts" / "todofmt_check.sh"), "--digest"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert len(out) == 128, out
    return out


def _valid(repo: Path) -> dict:
    return {
        "stub_modules": ["momentum/m.py"],
        "test_files": ["tests/test_x.py"],
        "script_acceptance": [],
        "contract_jsons": ["scripts/todofmt_contract.json"],
        "spec_path": "docs/X_SPEC.md",
        "contract_digest": _digest(repo),
        "run_receipts": [
            {"path": "handoffs/run_receipts/r.json", "cmd": "c", "rc": 0, "honest_bounds": "n/a"}
        ],
        "batch_card": {
            "depends": [],
            "touches": ["momentum/m.py"],
            "callers_now": [],
            "callers_later": ["api/later.py"],
            "gate_cmd": "pytest -q tests/test_x.py",
            "forbidden": [{"rule": "R1", "observable": False}],
            "risk_mitigation": [],
            "coverage_risk": [],
            "lifecycle": "keep",
            "not_executable": [
                {"item": "R1", "reason": "needs-research", "owner": "o", "expiry": "2099-01-01"}
            ],
        },
    }


def _run(repo: Path, manifest: dict | str) -> tuple[int, str]:
    mf = repo.parent / "manifest.json"
    mf.write_text(manifest if isinstance(manifest, str) else json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run(
        ["bash", str(repo / "scripts" / "todofmt_check.sh"), str(mf)],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _mini_repo(tmp_path)


def test_contract_keys_equal_spec_table() -> None:
    out = subprocess.run(["bash", str(CHECKER), "--keys"], capture_output=True, text=True, check=True).stdout
    assert set(out.split()) == SPEC_TABLE_KEYS


def test_valid_manifest_passes(repo: Path) -> None:
    rc, out = _run(repo, _valid(repo))
    assert rc == 0, out
    assert "TODOFMT PASS" in out


def test_boundary_01_all_five_categories_empty_fails(repo: Path) -> None:
    m = _valid(repo)
    m.update(stub_modules=[], test_files=[], script_acceptance=[], contract_jsons=[], run_receipts=[])
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "stub_modules 為空" in out and "contract_jsons 為空" in out
    assert "test_files 與 script_acceptance 皆空" in out  # b1 審碼 grok：原未斷言此句，刪其子句仍綠


def test_boundary_01b_script_acceptance_alone_satisfies_test_category(repo: Path) -> None:
    """合取之另一半：test_files 空而 script_acceptance 非空者，第二類視為齊備。"""
    m = _valid(repo)
    m.update(test_files=[], script_acceptance=["scripts/todofmt_check.sh"])
    rc, out = _run(repo, m)
    assert rc == 0, out


def test_boundary_02_only_batch_card_fails(repo: Path) -> None:
    rc, out = _run(repo, {"batch_card": _valid(repo)["batch_card"]})
    assert rc == 1, out
    assert "缺必填鍵：stub_modules" in out


def test_boundary_03_reason_outside_enum_fails(repo: Path) -> None:
    m = _valid(repo)
    m["batch_card"]["not_executable"][0]["reason"] = "later"
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "reason 非封閉值" in out


def test_boundary_04_expiry_past_fails(repo: Path) -> None:
    m = _valid(repo)
    m["batch_card"]["not_executable"][0]["expiry"] = "2000-01-01"
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "已過期" in out


def test_boundary_05_exists_check_true_missing_path_fails(repo: Path) -> None:
    m = _valid(repo)
    m["test_files"] = ["tests/test_missing.py"]
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "路徑不存在（exists_check）：test_files" in out


def test_boundary_06_empty_gate_cmd_fails(repo: Path) -> None:
    m = _valid(repo)
    m["batch_card"]["gate_cmd"] = "  "
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "gate_cmd" in out


def test_boundary_07_digest_mismatch_fails(repo: Path) -> None:
    m = _valid(repo)
    m["contract_digest"] = "0" * 128
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "contract_digest 與現行計算值不等" in out


@pytest.mark.parametrize("value", [None, ""], ids=["missing", "empty"])
def test_boundary_08_spec_path_missing_or_empty_fails(repo: Path, value: str | None) -> None:
    m = _valid(repo)
    if value is None:
        del m["spec_path"]
    else:
        m["spec_path"] = value
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "spec_path" in out


def test_boundary_09_receipt_missing_key_fails(repo: Path) -> None:
    (repo / "handoffs/run_receipts/r.json").write_text(json.dumps({"schema_version": 1, "command": "c"}))
    rc, out = _run(repo, _valid(repo))
    assert rc == 1, out
    assert "receipt 缺" in out


def test_boundary_09b_receipt_path_is_directory_fails(repo: Path) -> None:
    """b1 審碼 grok：receipt 路徑為目錄時原本跳過三鍵檢查而放行。"""
    (repo / "handoffs/run_receipts/subdir").mkdir()
    m = _valid(repo)
    m["run_receipts"][0]["path"] = "handoffs/run_receipts/subdir"
    rc, out = _run(repo, m)
    assert rc == 1 and "須為一般檔" in out, out


def test_boundary_10_exists_check_false_missing_path_passes(repo: Path) -> None:
    m = _valid(repo)
    m["batch_card"]["callers_later"] = ["api/not_yet.py"]
    m["batch_card"]["relocates_to"] = "momentum/future/place.py"
    rc, out = _run(repo, m)
    assert rc == 0, out


def test_boundary_11_callers_now_nonempty_accepted_and_checked(repo: Path) -> None:
    m = _valid(repo)
    m["batch_card"]["callers_now"] = ["api/now.py"]
    rc, out = _run(repo, m)
    assert rc == 0, out
    m["batch_card"]["callers_now"] = ["api/absent.py"]
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "batch_card.callers_now" in out


def test_boundary_12_checker_only_change_changes_digest(repo: Path) -> None:
    m = _valid(repo)
    before = m["contract_digest"]
    checker = repo / "scripts" / "todofmt_check.sh"
    checker.write_text(checker.read_text(encoding="utf-8") + "# 無關註解\n", encoding="utf-8")
    after = _digest(repo)
    assert before[:64] == after[:64], "只改檢查器時契約之半邊不應變"
    assert before != after
    rc, out = _run(repo, m)
    assert rc == 1 and "contract_digest 與現行計算值不等" in out, out


def test_boundary_13_contract_exists_check_change_changes_digest(repo: Path) -> None:
    before = _digest(repo)
    contract = repo / "scripts" / "todofmt_contract.json"
    data = json.loads(contract.read_text(encoding="utf-8"))
    data["batch_card"]["callers_later"]["exists_check"] = True
    contract.write_text(json.dumps(data), encoding="utf-8")
    after = _digest(repo)
    assert before[64:] == after[64:], "只改契約時檢查器之半邊不應變"
    assert before != after


def test_boundary_14_absolute_path_fails_even_if_exists(repo: Path) -> None:
    m = _valid(repo)
    m["stub_modules"] = [str(repo / "momentum" / "m.py")]
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "不得以 / 開頭" in out


def test_boundary_15_dotdot_segment_fails(repo: Path) -> None:
    m = _valid(repo)
    m["test_files"] = ["tests/../tests/test_x.py"]
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "不得含 .. 段" in out


def test_boundary_16_symlink_resolving_outside_repo_fails(repo: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside.py"
    outside.write_text("x\n", encoding="utf-8")
    (repo / "momentum" / "link.py").symlink_to(outside)
    m = _valid(repo)
    m["stub_modules"] = ["momentum/link.py"]
    rc, out = _run(repo, m)
    assert rc == 1, out
    assert "位於 repo 根之外" in out


@pytest.mark.parametrize(
    "field,value",
    [
        ("test_files", ["tests/test_x.py\nfalse\tignored\tnot-present.py"]),  # b1 審碼 codex 之反例原樣
        ("test_files", ["tests/test_x.py\nnot-present.py"]),  # b1 審碼 grok：換行後接不存在路徑
        ("test_files", ["tests/test_x.py\n../outside"]),  # 換行後接 ..
        ("test_files", ["tests/test_x.py\n/etc/passwd"]),  # 換行後接絕對路徑
        ("spec_path", "docs/X_SPEC.md\n/etc/passwd"),
        ("touches", ["momentum/m.py\n../outside"]),
        ("receipt", "handoffs/run_receipts/r.json\n../outside"),
    ],
    ids=["codex-tab-forge", "newline-missing", "newline-dotdot", "newline-abs", "spec_path", "touches", "receipt"],
)
def test_path_domain_rejects_control_characters(repo: Path, field: str, value: object) -> None:
    """路徑值域不得含控制字元：逐行＋tab 讀取不得被路徑值本身拆開而使其後段逃過檢查。"""
    m = _valid(repo)
    if field == "touches":
        m["batch_card"]["touches"] = value
    elif field == "receipt":
        m["run_receipts"][0]["path"] = value
    else:
        m[field] = value
    rc, out = _run(repo, m)
    assert rc == 1 and "控制字元" in out, out


def test_recorded_digest_equals_loader_computed(repo: Path) -> None:
    assert _valid(repo)["contract_digest"] == _digest(repo)


def test_real_template_check_todofmt_valid_rc0_and_missing_batch_card_nonzero(tmp_path: Path) -> None:
    """Task 0.1 驗證段：合法 manifest 經 `template_check.sh todofmt` rc=0；缺 batch_card 者 rc 非 0。"""
    digest = subprocess.run(["bash", str(CHECKER), "--digest"], capture_output=True, text=True, check=True).stdout.strip()
    ok = {
        "stub_modules": [],
        "test_files": ["tests/governance/test_todofmt_contract.py"],
        "script_acceptance": [],
        "contract_jsons": ["scripts/todofmt_contract.json"],
        "spec_path": "docs/TODOFMT_SPEC.md",
        "contract_digest": digest,
        "run_receipts": [],
        "batch_card": {
            "depends": [], "touches": ["scripts/todofmt_check.sh"], "callers_now": [], "callers_later": [],
            "gate_cmd": "bash scripts/todofmt_check.sh --keys", "forbidden": [], "risk_mitigation": [],
            "coverage_risk": [], "lifecycle": "keep",
            "not_executable": [{"item": "stub_modules", "reason": "needs-research", "owner": "o", "expiry": "2099-01-01"}],
        },
    }
    good = tmp_path / "good.json"
    good.write_text(json.dumps(ok), encoding="utf-8")
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({k: v for k, v in ok.items() if k != "batch_card"}), encoding="utf-8")
    tc = REPO_ROOT / "scripts" / "template_check.sh"
    r_good = subprocess.run(["bash", str(tc), "todofmt", str(good)], capture_output=True, text=True, check=False)
    r_bad = subprocess.run(["bash", str(tc), "todofmt", str(bad)], capture_output=True, text=True, check=False)
    assert r_good.returncode == 0, r_good.stdout + r_good.stderr
    assert r_bad.returncode != 0, r_bad.stdout


def test_mutation_value_domain_check_is_load_bearing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把 reason 之封閉值判定改為恆假 ⇒ 非封閉值之 manifest 轉為通過（證邊界③之測試有鑑別力）。"""
    src = CHECKER.read_text(encoding="utf-8")
    anchor = 'select(.reason|IN("blocked-by","user-ruling","needs-research")|not)'
    assert src.count(anchor) == 1, "mutation 錨點不在檢查器中（檢查器已改寫，本探針需同步）"
    mutant_src = tmp_path / "mutant_check.sh"
    mutant_src.write_text(src.replace(anchor, "select(false)"), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "CHECKER", mutant_src)
    repo = _mini_repo(tmp_path)
    m = _valid(repo)
    m["batch_card"]["not_executable"][0]["reason"] = "later"
    rc, out = _run(repo, m)
    assert rc == 0, f"mutation 未生效或另有他條擋下：{out}"
