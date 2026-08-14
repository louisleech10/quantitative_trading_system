"""窄觸發檢查路由器之產出端掛載（`scripts/narrow_check_router.sh`）。

為何存在（使用者 2026-08-14T18:40+08:00 逐字）：
    「可以掛的就要掛上去，只有掛和不掛兩種結果……**不是表格列出，是實際上線**。」

    `check_agent_contract_sync.sh` 與 `extract_phase2_expected_flips.py --check`
    兩支都有判定、都是秒級，卻**未掛任何自動路徑** ⇒ 只有人想到才會跑。
    本路由器把它們掛上 `PostToolUse:Edit|Write`，並以窄對照表控制成本。

🔴 四條缺一不可（同 test_zero_findings_guard 的四象限紀律）：
    · 只驗「該擋的擋了」⇒ 無法排除它恆擋（那會讓每次編輯都卡住）
    · 只驗「該放的放了」⇒ 無法排除它恆放（等於沒掛）
    · 未命中時必須**完全不 fork**：成本模型建立在命中率低，恆跑就是每次編輯多幾秒
    · 對照表腐爛（腳本被刪／改名）必須 rc≠0：`rc=2 略過` 正是 S1.2 的 fail-open 病灶

🔴 測試在沙箱 repo 內跑，**不動真實工作樹**：路由器以自身位置導出 REPO_ROOT，
   故把同一份原始碼複製進 tmp/scripts/ 即可讓它以 tmp 為根，
   對照表裡的相對路徑自然指向沙箱的樁腳本。**跑的是同一份原始碼，非另抄一份。**
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ROUTER_SRC = REPO / "scripts" / "narrow_check_router.sh"


def _sandbox(tmp: Path, *, stub_rc: int = 0, drop_stub: bool = False) -> Path:
    """建沙箱：同一份路由器原始碼 ＋ 可控 rc 的樁檢查腳本。"""
    (tmp / "scripts").mkdir(parents=True, exist_ok=True)
    router = tmp / "scripts" / "narrow_check_router.sh"
    router.write_text(ROUTER_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    router.chmod(0o755)

    # 對照表命中的四源合約檔
    (tmp / "AGENTS.md").write_text("x\n", encoding="utf-8")
    (tmp / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (tmp / "unrelated.txt").write_text("x\n", encoding="utf-8")

    if not drop_stub:
        stub = tmp / "scripts" / "check_agent_contract_sync.sh"
        # 樁會落一個 marker，用以證明「有沒有真的被呼叫」
        stub.write_text(
            "#!/usr/bin/env bash\n"
            'printf "STUB RAN\\n" >> "$(dirname "$0")/../ran.marker"\n'
            f"exit {stub_rc}\n",
            encoding="utf-8",
        )
        stub.chmod(0o755)
    return router


def _run(router: Path, arg: str | None = None, stdin: str | None = None):
    cmd = ["bash", str(router)]
    if arg is not None:
        cmd.append(arg)
    return subprocess.run(
        cmd,
        input=stdin if stdin is not None else "",
        capture_output=True,
        text=True,
    )


def test_hit_and_check_passes_allows(tmp_path: Path) -> None:
    """該放的放了：命中對照表且檢查 rc=0 ⇒ 路由器 rc=0。"""
    router = _sandbox(tmp_path, stub_rc=0)
    res = _run(router, "AGENTS.md")
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "ran.marker").exists(), "命中卻沒有真的跑檢查"


def test_hit_and_check_fails_blocks(tmp_path: Path) -> None:
    """🔴 承重反例：命中且檢查 rc≠0 ⇒ 路由器必須 rc=2 並指名檔案與命令。"""
    router = _sandbox(tmp_path, stub_rc=1)
    res = _run(router, "AGENTS.md")
    assert res.returncode == 2, f"檢查紅了卻沒擋：rc={res.returncode}"
    # 🔴 不只斷言 rc：本 epic 兩次「rc 如期轉紅」實為別的原因紅
    assert "AGENTS.md" in res.stderr
    assert "check_agent_contract_sync.sh" in res.stderr


def test_miss_does_not_fork(tmp_path: Path) -> None:
    """未命中 ⇒ rc=0 且**完全沒有呼叫任何檢查**（成本模型的前提）。"""
    router = _sandbox(tmp_path, stub_rc=1)  # 樁刻意會紅，若被誤呼叫會現形
    res = _run(router, "unrelated.txt")
    assert res.returncode == 0, res.stderr
    assert not (tmp_path / "ran.marker").exists(), "未命中卻仍呼叫了檢查"


def test_table_rot_is_loud_not_silent(tmp_path: Path) -> None:
    """🔴 對照表腐爛（表列腳本不存在）⇒ rc=2，不得靜默略過。"""
    router = _sandbox(tmp_path, drop_stub=True)
    res = _run(router, "AGENTS.md")
    assert res.returncode == 2, f"表腐爛卻靜默放行：rc={res.returncode}"
    assert "對照表腐爛" in res.stderr


def test_hook_mode_stdin_equivalent_to_argv(tmp_path: Path) -> None:
    """hook 模式（stdin JSON）與直接傳路徑必須等效——否則掛上去等於沒掛。"""
    router = _sandbox(tmp_path, stub_rc=1)
    payload = json.dumps({"tool_input": {"file_path": str(tmp_path / "AGENTS.md")}})
    res = _run(router, None, stdin=payload)
    assert res.returncode == 2, f"hook 模式沒擋：rc={res.returncode} err={res.stderr}"
    assert "AGENTS.md" in res.stderr


def test_unparseable_payload_fails_open(tmp_path: Path) -> None:
    """payload 壞掉 ⇒ 靜默放行（刻意的 fail-open，邊界 3）。

    hook 不得因自己解析失敗而擋住工作；該代價由 pre-push 的 gov_check 承接。
    """
    router = _sandbox(tmp_path, stub_rc=1)
    res = _run(router, None, stdin="not json at all")
    assert res.returncode == 0, res.stderr
    assert not (tmp_path / "ran.marker").exists()


@pytest.mark.parametrize(
    "rel",
    ["AGENTS.md", ".cursorrules", "CLAUDE.md", "docs/MULTI_AGENT_ORCHESTRATION.md"],
)
def test_real_tree_stays_green_for_contract_files(rel: str) -> None:
    """🔴 現樹反向確認：掛上之後，改這四個檔**不會**被新 hook 擋住。

    少了這條就可能掛上一個「現樹本來就紅」的檢查，
    使主委自己再也編輯不了合約檔——本 epic 已因此類疏漏付過代價。
    """
    res = subprocess.run(
        ["bash", str(ROUTER_SRC), rel],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"{rel} 在現樹即被擋：{res.stderr}"


def test_unwritable_tmpdir_fails_closed(tmp_path: Path) -> None:
    """🔴 CODEX-R1-P1-01／GROK-R1-P1-03：TMPDIR 不可寫 ⇒ 檢查未執行，必須 rc=2。

    原版寫 `mktemp … || continue`：暫存檔開不了就跳過該檢查，`_fail` 仍為 0
    ⇒ 整支路由器 rc=0。磁碟／TMPDIR 異常時，產出端守衛靜默變成「沒有守衛」。
    """
    router = _sandbox(tmp_path, stub_rc=0)
    bad_tmp = tmp_path / "nowrite"
    bad_tmp.mkdir()
    bad_tmp.chmod(0o500)  # r-x：mktemp 建不了檔
    try:
        res = subprocess.run(
            ["bash", str(router), "AGENTS.md"],
            capture_output=True,
            text=True,
            env={**os.environ, "TMPDIR": str(bad_tmp)},
        )
        assert res.returncode == 2, f"TMPDIR 不可寫卻放行：rc={res.returncode}"
        assert "無法建立暫存檔" in res.stderr
        assert "這不是通過" in res.stderr
    finally:
        bad_tmp.chmod(0o700)


# 🔴 目錄前綴之封閉白名單（GROK-R1-P2-03 之修法，2026-08-14 由「一律禁止」改為「明列才准」）。
#
# 原本一律禁止，但 canonical Rule 2/3/4 的 scanner 必須對 `momentum/`／`api/` 觸發——
# 那正是它要守的主線程式碼。一律禁止會逼人繞道（另開 hook 條目），反而讓成本模型
# 分散到看不見的地方。改為集合相等鎖：新增前綴必須同時改本表 ⇒ 一定被 review。
#
# 收錄條件（加列時逐條答，答不出來就不要加）：
#   ① 該前綴涵蓋的路徑**不是高頻編輯面**（`scripts/`、`docs/` 這類一律不准）
#   ② 對應檢查已實測秒數，且寫在 narrow_check_router.sh 的註解裡
#   ③ 該檢查在現樹為綠（否則掛上即擋死該目錄的所有編輯）
ALLOWED_PREFIXES = {"momentum/", "api/"}


def test_routes_have_no_directory_prefix() -> None:
    """🔴 GROK-R1-P2-03：成本模型（未命中不 fork）建立在「命中率低」上。

    路由器的碼**支援** `/` 結尾的目錄前綴，一旦有人加入 `scripts/` 這類列，
    每次 Edit 都會命中，成本模型當場失效而測試不會發現。
    ⇒ 前綴須在 `ALLOWED_PREFIXES` 內，且以**集合相等**鎖住（多一個少一個都紅）。
    """
    # 🔴 不能 `source` 本檔取 `_routes`：檔尾就是主流程，source 會直接跑掉並 exit。
    #    改自原始碼抽 `_routes()` 的 body——仍是**同一份**定義，不另抄一張表。
    src = ROUTER_SRC.read_text(encoding="utf-8")
    start = src.index("_routes() {")
    end = src.index("\n}", start)
    body = src[start:end]
    rows = re.findall(r"printf '%s\\n' \"([^\"]+)\"", body)
    assert rows, "取不到對照表（`_routes()` 之抽取樣式已漂）"
    found = {r.split("|", 1)[0] for r in rows if r.split("|", 1)[0].endswith("/")}
    assert found == ALLOWED_PREFIXES, (
        f"目錄前綴與白名單不相等：多={sorted(found - ALLOWED_PREFIXES)} "
        f"少={sorted(ALLOWED_PREFIXES - found)}。"
        "新增前綴須同時修改本表與 narrow_check_router.sh 之成本註解——"
        "這正是「不得靜默擴大觸發面」的機械強制點。"
    )


def test_prefix_checks_are_green_on_current_tree() -> None:
    """🔴 前綴列涵蓋面大，掛上前必須在現樹為綠，否則整個目錄都改不動。

    少了這條就可能掛上一個現樹本來就紅的檢查，使主委再也編輯不了 momentum/ 或 api/。
    """
    for rel in ("momentum/factories.py", "api/services/__init__.py"):
        res = subprocess.run(
            ["bash", str(ROUTER_SRC), rel], cwd=REPO, capture_output=True, text=True
        )
        assert res.returncode == 0, f"{rel} 在現樹即被擋：{res.stderr}"


def test_real_tree_stays_green_for_phase2_fixture() -> None:
    """同上，針對 Phase 2 fixture 那條路由。"""
    res = subprocess.run(
        ["bash", str(ROUTER_SRC), "docs/GOVB0_FRICTION_TODO.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
