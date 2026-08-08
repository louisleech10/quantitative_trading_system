"""票 B-31 — 交件前自檢指示進 prompt 模板。

為何存在（2026-08-06）：
    委員產出格式不合規（`result_state=format-failed`）後，唯一路徑是整份重跑
    （實測 composer 約 15 分鐘），且該輪債務無法正規銷帳而擋住所有後續派工。

    當日 `GOVB39-B1-CONSULT` R1 兩家皆 format-failed；主委在 R2 brief **手寫**
    「產出後自行跑 `completeness_check --single` 確認 rc=0」後，**兩家一次全過**。
    手寫版靠主委每次記得 ⇒ 依使用者定死的「工具必須自帶強制機制，不准靠紀律和記憶」，
    移進 `cx_run.sh` 的 prompt 模板。

本檔驗三件事：
    1. 自檢指示確實出現在 prompt（執行期，非只讀原始碼）
    2. kind 集合與 `_run_format_check_if_needed` **一致**——這是重點：
       今日已發生三次「同一概念兩處定義不一致」，本測試把它釘死
    3. mutation：移除該分支 ⇒ 轉紅

誠實邊界：本檔只驗「指示有送到委員手上」，**不驗委員真的照做**——
    後者由 `cx_run.sh` 交件當下的格式檢查（既有）把關，屬不同層。

GOVB1 Task 1.1：findings-kind／selfcheck 改由 `govflow_lifecycle.json` 旗標驅動
（`produces_findings`／`completeness_selfcheck`），不再硬編碼 `review|consult|closure` case。
本檔改對 JSON 與 `_cx_kind_bool` 呼叫點做集合／錨點對齊，斷言強度不變。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# 複用既有 harness（同目錄）；pytest rootdir 不含本目錄於 sys.path，故手動插入。
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_cxrun_stamp_prompt import (  # noqa: E402  # type: ignore[import-not-found]
    _harness,
    _open_round,
    _run_cx,
    _write_brief,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CX_RUN = REPO_ROOT / "scripts" / "cx_run.sh"
LIFECYCLE = REPO_ROOT / "scripts" / "govflow_lifecycle.json"

_SELFCHECK_ANCHOR = "completeness_check.sh --single"
# 追加自檢指示的旗標呼叫錨點（mutation 用）。
# 🔴 必須含下一行 prompt 擴充字串，避免誤改其他 _cx_kind_bool 呼叫。
_SELFCHECK_CALL = (
    '  if _cx_kind_bool "${_bk}" "completeness_selfcheck"; then\n'
    '    prompt="${prompt} 寫完產出後'
)

# 「產 findings 的 kind」契約內容（非只驗「多處相同」——一起改錯仍會全綠）
_EXPECTED_FINDINGS_KINDS = {"review", "consult", "closure"}


def _json_kinds_with_flag(flag: str) -> set[str]:
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    kinds = data["kinds"]
    return {k for k, row in kinds.items() if row.get(flag) is True}


def _count_flag_calls(src: str, flag: str) -> int:
    return len(
        re.findall(
            rf'_cx_kind_bool\s+"\$\{{_bk\}}"\s+"{re.escape(flag)}"',
            src,
        )
    )


def test_all_findings_kind_sets_agree() -> None:
    """🔴 SSOT：「產 findings 的 kind」在 matrix 與 cx_run 消費點必須對齊。

    不一致的後果：
      - 自檢指示少了 → 該 kind 仍會 format-failed 後整份重跑（本票沒解到）
      - 自檢指示多了 → 叫 impl/stamp 委員跑一個對它們必然 vacuous 的檢查（製造新誤導）
      - stub 與格式檢查不一致 → 測試 harness 產出必然不合規的 stub

    Task 1.1 後三處皆讀同一 JSON 旗標；本測釘：
      ① JSON produces_findings 集合 == 期望契約
      ② completeness_selfcheck 集合 == produces_findings（現行五 kind 契約）
      ③ cx_run 內 produces_findings 與 completeness_selfcheck 各有呼叫（無硬編碼 case 列表）
    """
    src = CX_RUN.read_text(encoding="utf-8")
    findings = _json_kinds_with_flag("produces_findings")
    selfcheck = _json_kinds_with_flag("completeness_selfcheck")
    assert findings == _EXPECTED_FINDINGS_KINDS, (
        f"findings-kind 契約變更：期望 {sorted(_EXPECTED_FINDINGS_KINDS)}、實際 {sorted(findings)}。"
        "若確為有意變更，請同步 govflow_lifecycle.json 與票 B-31 的處置欄。"
    )
    assert selfcheck == findings, (
        f"completeness_selfcheck {sorted(selfcheck)} != produces_findings {sorted(findings)}"
    )
    n_findings = _count_flag_calls(src, "produces_findings")
    n_self = _count_flag_calls(src, "completeness_selfcheck")
    # stub + format_check 兩處 produces_findings；selfcheck 一處
    assert n_findings >= 2, f"cx_run produces_findings 呼叫點過少：{n_findings}"
    assert n_self >= 1, f"cx_run completeness_selfcheck 呼叫點過少：{n_self}"
    # 禁殘留硬編碼 findings-kind case 列表（第二真相源）
    assert not re.search(
        r'case\s+"\$\{_bk\}"\s+in\s*\n\s*review\|consult\|closure\)',
        src,
    ), "cx_run 仍殘留硬編碼 review|consult|closure case（應改讀 matrix）"


@pytest.mark.parametrize("kind", ["review", "consult", "closure"])
def test_selfcheck_instruction_reaches_prompt(tmp_path: Path, kind: str) -> None:
    """會跑格式檢查的 kind，prompt 須含自檢指示（執行期驗證）。

    🔴 `closure` 必須列入〔`CODEX-R1-P2-03`〕：它走 stamp_prompt_inject 路徑，
    與 review/consult 不同路徑，只測前兩者會漏掉「STAMP 注入後自檢有沒有被覆蓋掉」。
    """
    h = _harness(tmp_path)
    task_id = f"GOVB31-{kind.upper()}"
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind=kind)
    rid = "b3111111-1111-4111-8111-111111111111"
    _open_round(
        h,
        round_id=rid,
        session=f"s-b31-{kind}",
        fams=["codex"],
        out_prefix="handoffs/b31",
        brief_rel=brief_rel,
        task_id=task_id,
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        brief_rel,
        "handoffs/b31-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    assert _SELFCHECK_ANCHOR in prompt, f"{kind} prompt 缺自檢指示:\n{prompt}"
    assert "handoffs/b31-codex.md" in prompt, "自檢指令未帶入實際產出路徑"
    # 🔴 --family 必須帶（COMPOSER-R1-P2-02）：不帶時 extract_heading_ids 改由檔名推 family，
    #    產出路徑不含家族後綴時自檢會弱於交件 ⇒ 破壞「先跑等於預跑」。
    assert "--family codex" in prompt, f"自檢指令缺 --family，與交件檢查不同形:\n{prompt}"
    # 🔴 0-findings 必須有**可正規收斂的出路**（票 B-38）：
    #    舊版只叫委員寫散文「本輪 0 findings」⇒ 收斂端抽不到 heading ID ⇒ vacuous FAIL
    #    ⇒ 誠實則卡住、捏造則通過（2026-08-07 實際發生）。
    #    解法＝P3-00 sentinel（合法 canonical ID，抽得到；空殼仍被 body 檢查擋）。
    assert "0 個 finding" in prompt, f"prompt 未處理 0-findings 情況:\n{prompt}"
    assert "P3-00" in prompt, f"prompt 未給出 sentinel 格式 ⇒ 誠實回報者無正規出路:\n{prompt}"
    assert "sentinel" in prompt, "prompt 未說明這是 sentinel 機制"
    assert "捏造" in prompt, "未警告委員勿為湊數而捏造實質 finding"
    # 🔴 防退回散文版：只叫委員「寫出 0 findings」而不給 sentinel 格式，即為 B-38 的病
    assert not ("明確寫出「本輪 0 findings」" in prompt and "P3-00" not in prompt), (
        "prompt 退回散文版（無 sentinel 格式）⇒ 收斂端仍會 vacuous FAIL"
    )


def test_selfcheck_absent_for_impl(tmp_path: Path) -> None:
    """impl 產出依契約無 canonical finding ID ⇒ **不得**收到自檢指示。

    加了會叫委員去跑一個對它必然 vacuous 的檢查（票 B-38 的病）。
    """
    # 家族須為 implementer（角色閘：brief-kind=impl 只准 implementer，現行 SoT ＝ grok）
    h = _harness(tmp_path)
    brief_rel = "handoffs/brief.md"
    _write_brief(h, kind="impl")
    rid = "b3122222-2222-4222-8222-222222222222"
    _open_round(
        h,
        round_id=rid,
        session="s-b31-impl",
        fams=["grok"],
        out_prefix="handoffs/b31i",
        brief_rel=brief_rel,
        task_id="GOVB31-IMPL",
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "grok",
        brief_rel,
        "handoffs/b31i-grok.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    assert _SELFCHECK_ANCHOR not in prompt, f"impl prompt 不該含自檢指示:\n{prompt}"


def test_selfcheck_catches_real_format_failure(tmp_path: Path) -> None:
    """自檢確實攔得下**真實發生過**的 format-failed 形態〔`COMPOSER-R1-P1-01` ①〕。

    fixture 取自 2026-08-06 `GOVB39-B1-CONSULT` R1 的 composer 產出形態
    （每個 P0/P1 finding 缺 `**來源摘要**` 欄），該次導致整輪 abandon 重派。

    這條回答的是「自檢有沒有用」——修法的前提。
    不回答「委員會不會照做」，那是 prompt 遵循率，n=1 尚不足（具名殘留）。
    """
    fixture = Path(__file__).resolve().parent / "fixtures" / "govb31_missing_digest-composer.md"
    assert fixture.is_file(), f"探針 fixture 不存在: {fixture}"

    bad = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "completeness_check.sh"),
         "--single", str(fixture), "--family", "composer"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert bad.returncode != 0, (
        f"真實 format-failed 形態未被自檢攔下 ⇒ 修法前提不成立\n{bad.stdout}{bad.stderr}"
    )
    assert "digest" in (bad.stdout + bad.stderr).lower(), "攔下的理由不是缺 digest（可能攔錯東西）"

    # 對照：補上 digest 後須放行——證明上面攔的是「缺 digest」而非「整支恆紅」
    fixed = tmp_path / "fixed-composer.md"
    fixed.write_text(
        fixture.read_text(encoding="utf-8").replace(
            "**碼證**: `scripts/completeness_check.sh` 的 P0/P1 digest 檢查。",
            "**碼證**: `scripts/completeness_check.sh` 的 P0/P1 digest 檢查。\n"
            "**來源摘要**: scripts/completeness_check.sh#0123456789ab",
        ),
        encoding="utf-8",
    )
    ok = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "completeness_check.sh"),
         "--single", str(fixed), "--family", "composer"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    assert ok.returncode == 0, (
        f"補 digest 後仍不放行 ⇒ 上面的紅燈不是缺 digest 造成\n{ok.stdout}{ok.stderr}"
    )


def test_mutation_removing_selfcheck_case_turns_red(tmp_path: Path) -> None:
    """反向 mutation：把 completeness_selfcheck 呼叫改成恆不命中 ⇒ 指示消失。

    證明上面的斷言不是恆真——若腳本裡本來就沒這段，測試也該紅。
    """
    src = CX_RUN.read_text(encoding="utf-8")
    assert _SELFCHECK_CALL in src, f"mutation 錨點漂移：{_SELFCHECK_CALL!r}"
    # 只換條件、保留 prompt 行結構——否則會切掉 `prompt="` 的行頭造成語法錯，
    # 那樣測到的是「突變體壞掉」而非「本層失效」。
    mutant = tmp_path / "cx_run_mutant.sh"
    mutant.write_text(
        src.replace(
            _SELFCHECK_CALL,
            '  if false; then\n'
            '    prompt="${prompt} 寫完產出後',
            1,
        ),
        encoding="utf-8",
    )
    syntax = subprocess.run(["bash", "-n", str(mutant)], capture_output=True, text=True)
    assert syntax.returncode == 0, f"突變體語法錯誤: {syntax.stderr}"

    mutated_src = mutant.read_text(encoding="utf-8")
    # 突變後：completeness_selfcheck 呼叫點應少於 production（被 false 取代）
    assert _count_flag_calls(mutated_src, "completeness_selfcheck") < _count_flag_calls(
        src, "completeness_selfcheck"
    ), "mutation 未移除 completeness_selfcheck 呼叫"
    # 執行期：review prompt 不再含自檢指示
    h = _harness(tmp_path / "mut_run")
    # 用突變體覆寫隔離副本
    (h["scripts"] / "cx_run.sh").write_text(mutated_src, encoding="utf-8")
    (h["scripts"] / "cx_run.sh").chmod(0o755)
    _write_brief(h, kind="review")
    rid = "b3133333-3333-4333-8333-333333333333"
    _open_round(
        h,
        round_id=rid,
        session="s-b31-mut",
        fams=["codex"],
        out_prefix="handoffs/b31m",
        brief_rel="handoffs/brief.md",
        task_id="GOVB31-MUT",
    )
    capture = h["root"] / "prompt.capture"
    r = _run_cx(
        h,
        "codex",
        "handoffs/brief.md",
        "handoffs/b31m-codex.md",
        round_id=rid,
        env_overlay={"CX_PROMPT_CAPTURE": str(capture)},
    )
    assert r.returncode == 0, r.stdout + r.stderr
    prompt = capture.read_text(encoding="utf-8")
    assert _SELFCHECK_ANCHOR not in prompt, (
        "MUTATION 未轉紅：移除 selfcheck 後 prompt 仍含自檢指示"
    )
