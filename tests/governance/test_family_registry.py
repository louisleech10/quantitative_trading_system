"""治理家族 SoT(governance_families.json)+ grok 全鏈接線的可證偽測試。

事故(2026-07-23 使用者抓):grok 散在 4 檔 11 處缺漏/被誤記 composer,逐處手補必漏
(連 SPEC「完整清單」都漏 gate.sh:296)。修法=單一 SoT,4 檔全讀。
本測試釘死:①SoT 可讀+fail-closed ②雙語 parity ③grok 在每個接點真的被認得
④gate_check 熱路徑寫死清單 == SoT(防漂移)。任一 grok 接點被 revert → 對應測試紅。
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
SOT = SCRIPTS / "governance_families.json"


def _bash(snippet: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", "-c", snippet], cwd=REPO, capture_output=True, text=True, check=False)


# ---- SoT 本體 ----
def test_sot_exists_and_has_grok() -> None:
    d = json.loads(SOT.read_text(encoding="utf-8"))
    assert "grok" in d["families"]
    assert "grok" in d["review_families"]
    assert "grok" in d["executor_clis"]


def test_bash_getter_and_failclosed() -> None:
    ok = _bash(". scripts/governance_families.sh && families_get review_families")
    assert ok.returncode == 0 and "grok" in ok.stdout
    bad = _bash(". scripts/governance_families.sh && families_get nonexistent")
    assert bad.returncode != 0  # 缺 key → fail-closed


def test_bilingual_parity() -> None:
    b = _bash(". scripts/governance_families.sh && families_get families ' '").stdout.split()
    p = subprocess.run(
        ["python3", str(SCRIPTS / "governance_families_loader.py"), "families", " "],
        cwd=REPO, capture_output=True, text=True, check=False,
    ).stdout.split()
    assert sorted(b) == sorted(p) and "grok" in b


# ---- grok 在各接點被認得 ----
def test_gate_check_gates_grok() -> None:
    """grok 命令無 token → deny(exit 2)。revert(移 grok)→ exit 0 → 本測試紅。"""
    payload = '{"tool_name":"Bash","tool_input":{"command":"grok -p hi"}}'
    p = _bash(f"printf '%s' '{payload}' | GATE_DIR_OVERRIDE=/tmp/frtest.$$ bash scripts/gate_check.sh")
    assert p.returncode == 2


def test_stamp_default_no_silent_drop(tmp_path: Path) -> None:
    """不傳 roster → 預設須等於 **SoT 宣告之家族集合**，且缺任一家即 FAIL。

    原名 `test_stamp_default_requires_grok`，把 `grok` 寫死在斷言裡。
    2026-08-09 委員暫停機制上線後（`active_stampers` 優先、缺席回退 `review_families`），
    名冊會**每週因模型能力／額度而加減**，寫死家族名等於每次換委員都紅。

    🔴 **原意圖逐字保留**：2026-07-23 事故＝預設寫死 `codex,composer` 使 `grok`
    **永不被機檢要求**。本測改為「預設 ≡ SoT 宣告」——名冊換誰都擋得住靜默少要求，
    而不是只擋 grok 這一個名字。

    🔴 **本測不具 mutation 偵測力，勿單獨倚賴**（R-20 / `CODEX-R1-P1-04`）：
    expected 取自**同一份現行 SoT**，故把預設改成硬編現行名單時本測**仍會綠**
    （codex 實跑證實）。真正把「預設有沒有被寫死」釘住的是下方
    `test_stamp_default_reads_sot_not_hardcoded`（隔離 fixture 用**另一個**合法子集）。
    本測留著只補一件事：對**真實 SoT** 驗「蓋不齊即 FAIL 且點名缺席者」。
    """
    fams = json.loads(SOT.read_text(encoding="utf-8"))
    expected = fams.get("active_stampers") or fams["review_families"]
    assert len(expected) >= 2, f"SoT 宣告之蓋章家族少於 2 家: {expected}"

    # 蓋齊「除最後一家以外」的所有家族 ⇒ 必 FAIL，且訊息須點名缺席那家
    stamped, missing = expected[:-1], expected[-1]
    f = tmp_path / "r.md"
    f.write_text("body\n## 戳記\n", encoding="utf-8")
    h = _bash(f"bash scripts/reconcile_body_hash.sh {f}").stdout.strip()
    with f.open("a", encoding="utf-8") as fh:
        for fam in stamped:
            fh.write(f"RECONCILE-STAMP: {fam} APPROVED 2026-07-23 sha256:{h} task:x\n")
    p = _bash(f"bash scripts/reconcile_stamps_check.sh {f}")
    assert p.returncode != 0, f"缺 {missing} 之戳記竟通過（靜默少要求）\n{p.stdout}{p.stderr}"
    assert missing in (p.stdout + p.stderr), (
        f"FAIL 訊息未點名缺席家族 {missing}\n{p.stdout}{p.stderr}"
    )


# ---- active_stampers：隔離 fixture(R-19 / R-20) ----
# 為何要隔離：直接改真 SoT 再還原會與並行 pytest 互相污染（CLAUDE.md Gotchas 已記載
# 「不得並行跑兩份會就地 mutate 檔案再還原的 pytest」）。故複製腳本到 tmp，
# 讓 `SCRIPT_DIR` 指向 tmp，SoT 也在 tmp——真 SoT 全程唯讀。
_STAMP_ENV_SCRIPTS = (
    "reconcile_stamps_check.sh",
    "governance_families.sh",
    "reconcile_body_hash.sh",
)


def _isolated_stamp_env(tmp_path: Path, sot: dict) -> tuple[Path, Path]:
    """複製 stamp 檢查鏈到 tmp + 指定 SoT 內容。回 (腳本路徑, 空戳記之 reconcile 檔)。"""
    s = tmp_path / "scripts"
    s.mkdir(exist_ok=True)
    for f in _STAMP_ENV_SCRIPTS:
        (s / f).write_text((SCRIPTS / f).read_text(encoding="utf-8"), encoding="utf-8")
    (s / "governance_families.json").write_text(
        json.dumps(sot, ensure_ascii=False), encoding="utf-8"
    )
    r = tmp_path / "r.md"  # 檔名刻意不含任何家族名（否則污染「未被點名」斷言）
    r.write_text("body\n## 戳記\n", encoding="utf-8")
    return s / "reconcile_stamps_check.sh", r


def _named_families(out: str) -> set[str]:
    """從 FAIL 訊息抽出被點名『缺戳記』的家族集合（行首 '  · <family>: ...'）。"""
    return {
        ln.split("·", 1)[1].split(":", 1)[0].strip()
        for ln in out.splitlines()
        if "·" in ln
    }


def _base_sot() -> dict:
    real = json.loads(SOT.read_text(encoding="utf-8"))
    return {"families": real["families"], "review_families": real["review_families"]}


# fixture 用「另一個合法子集」——刻意**不含 codex**，才能抓出硬編現行名單。
_R20_FIXTURE_ACTIVE = ["composer", "grok"]


def test_stamp_default_reads_sot_not_hardcoded(tmp_path: Path) -> None:
    """🔴 mutation 可證偽：把預設改成硬編現行名單 ⇒ 本測**必紅**。

    R-20（`CODEX-R1-P1-04`）：上面那個 `test_stamp_default_no_silent_drop` 從
    **同一份現行 SoT** 取 expected，故 codex 實跑把
    `reconcile_stamps_check.sh` 的預設改成硬編 `required="codex,composer"` 後，
    該測**仍 1 passed**——主委為了「換委員不用改測試」把斷言改成與名冊無關，
    結果連「有沒有被寫死」都測不出來。**低摩擦與保護力沒有同時拿到。**

    修法＝隔離 fixture 給**另一個**合法子集 `composer,grok`（不含 codex），
    再斷言被要求的家族集合**恰等於**它。硬編 `codex,composer` 會同時
    ①少了 grok ②多了 codex ⇒ 集合相等當場失敗。
    """
    real = json.loads(SOT.read_text(encoding="utf-8"))
    assert set(_R20_FIXTURE_ACTIVE) <= set(real["review_families"]), "fixture 子集須合法"
    current = set(real.get("active_stampers") or real["review_families"])
    assert set(_R20_FIXTURE_ACTIVE) != current, (
        f"fixture 子集與現行 SoT 相同({current}) ⇒ 本測失去 mutation 偵測力，須換一個子集"
    )

    sot = _base_sot() | {"active_stampers": _R20_FIXTURE_ACTIVE}
    script, r = _isolated_stamp_env(tmp_path, sot)
    p = _bash(f"bash {script} {r}")
    out = p.stdout + p.stderr
    assert p.returncode != 0, f"零戳記竟通過\n{out}"
    assert _named_families(out) == set(_R20_FIXTURE_ACTIVE), (
        f"被要求的家族 != SoT active_stampers（預設被寫死或未讀 SoT）\n{out}"
    )


def test_active_stampers_missing_key_falls_back_to_review_families(tmp_path: Path) -> None:
    """R-19：**缺 key**（非空值）才回退正式名冊——乾淨 clone／CI 行為須逐字不變。"""
    script, r = _isolated_stamp_env(tmp_path, _base_sot())
    p = _bash(f"bash {script} {r}")
    out = p.stdout + p.stderr
    assert p.returncode != 0
    assert _named_families(out) == set(_base_sot()["review_families"]), out


@pytest.mark.parametrize(
    "label,active",
    [
        ("空 list", []),
        ("打錯字", ["codexx"]),
        ("重複", ["codex", "codex"]),
        ("非 list", "codex"),
        ("含空字串", ["codex", "  "]),
        ("非字串元素", ["codex", 3]),
        ("未進正式名冊即擴編", ["codex", "claude"]),
    ],
)
def test_active_stampers_invalid_is_failclosed(tmp_path: Path, label: str, active: object) -> None:
    """R-19（`CODEX-R1-P1-03`）：`active_stampers` 不合法 ⇒ **拒，不得靜默回退全員**。

    原實作 `families_get active_stampers || required=""` 把「缺 key」「空 list」
    「未知家族」併成同一個回退分支：`[]` 被當缺席（使用者以為停了全部，實際要求全員）、
    `["codexx"]` 被當成合法 required（永遠等不到戳記而卡死）。
    這一行是**使用者手改的**，打錯是預期失敗模式而非邊緣案例。

    mutation 反例：把 `reconcile_stamps_check.sh` 的三態 `case` 改回
    「非零一律回退 review_families」⇒ 下列各例會變成「要求全員」的一般 FAIL，
    訊息不再含 `fail-closed`，本測轉紅。
    """
    script, r = _isolated_stamp_env(tmp_path, _base_sot() | {"active_stampers": active})
    p = _bash(f"bash {script} {r}")
    out = p.stdout + p.stderr
    assert p.returncode != 0, f"{label}: 竟放行\n{out}"
    # 🔴 下面兩條**不可只留上面那條**：mutation B 實跑證實 `"fail-closed" in out`
    #   會被 getter 自己寫到 stderr 的同一字串騙過（rc≠0 仍回退全員時，訊息裡照樣有它）。
    #   真正承重的是「**沒有**進入逐家族檢查」——回退分支必然點名家族，拒發分支必然不點名。
    assert "fail-closed" in out, f"{label}: 訊息未說明 fail-closed\n{out}"
    assert not _named_families(out), (
        f"{label}: 竟仍進入逐家族檢查（表示走了回退分支，非拒發）\n{out}"
    )


@pytest.mark.parametrize(
    "label,active,want_rc,want_out",
    [
        ("合法子集", ["composer", "grok"], 0, "composer,grok"),
        ("缺 key", None, 0, "codex,composer,grok"),   # 回退正式名冊
        ("空 list", [], 1, ""),
        ("打錯字", ["codexx"], 1, ""),
        ("重複", ["codex", "codex"], 1, ""),
    ],
)
def test_gate_stamp_families_uses_tristate_getter(
    tmp_path: Path, label: str, active: object, want_rc: int, want_out: str
) -> None:
    """🔴 R-19 須覆蓋**所有** caller〔`CODEX-R2-P1-01` / `COMPOSER-R2-P2-01`〕。

    `gate.sh:_stamp_families` 的結果是以 **explicit required**（第二參）傳給
    `reconcile_stamps_check.sh` 的 ⇒ 它自成一套回退邏輯就等於**繞過**該腳本
    剛修好的 fail-closed 預設。兩家委員獨立實測舊碼：
      · `active_stampers: []`        → `codex,composer,grok`（靜默回退全員）
      · `active_stampers: ["codexx"]` → `codexx`（未知家族成為 required ⇒ 卡死）

    本測取 `gate.sh` 內 `_stamp_families` 的**函式原文**在隔離 SoT 上重跑（跑真碼）。
    mutation 反例：改回 `families_get active_stampers || families_get review_families`
    ⇒「空 list」「打錯字」「重複」三例的 rc 由 1 變 0，轉紅。
    """
    src = (SCRIPTS / "gate.sh").read_text(encoding="utf-8")
    m = re.search(r"_stamp_families\(\) \{.*?\n\}", src, re.S)
    assert m, "找不到 gate.sh:_stamp_families（refactor?→須更新本測）"

    s = tmp_path / "scripts"
    s.mkdir(exist_ok=True)
    (s / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    sot = _base_sot()
    if active is not None:
        sot["active_stampers"] = active
    (s / "governance_families.json").write_text(json.dumps(sot, ensure_ascii=False), encoding="utf-8")

    p = _bash(f". {s}/governance_families.sh\n{m.group(0)}\n_stamp_families\n")
    assert p.returncode == want_rc, (
        f"{label}: rc={p.returncode} want={want_rc}\n{p.stdout}{p.stderr}"
    )
    assert p.stdout.strip() == want_out, f"{label}: stdout={p.stdout!r} want={want_out!r}"


@pytest.mark.parametrize(
    "label,active,target,env,want_rc",
    [
        ("grok 暫停中切 codex", ["codex", "composer"], "codex", "", 2),
        ("grok 暫停中切 composer", ["codex", "composer"], "composer", "", 2),
        ("三家皆可用切 codex", ["codex", "composer", "grok"], "codex", "", 0),
        ("缺 active_stampers 回退全員", None, "codex", "", 0),
        # 🔴 CODEX-R3-P1-03：fallback 失敗不得吞成空集合而跳過前檢（fail-open）
        ("缺 active 且 review_families 壞", "__BREAK_RF__", "codex", "", 2),
        # 🔴 CODEX-R3-P2-04：逃生口須具名理由
        ("逃生口無理由", ["codex", "composer"], "codex", "SET_ROLES_ALLOW_QUORUM_BREAK=1", 2),
        (
            "逃生口有理由",
            ["codex", "composer"],
            "codex",
            "SET_ROLES_ALLOW_QUORUM_BREAK=1 SET_ROLES_QUORUM_BREAK_REASON=額度已恢復",
            0,
        ),
    ],
)
def test_set_roles_refuses_switch_that_breaks_review_quorum(
    tmp_path: Path, label: str, active: object, target: str, env: str, want_rc: int
) -> None:
    """🔴 換實作端**不得**把可用審查者打到 2 家以下〔consult-r1 C4，兩家 APPROVED〕。

    病：`set_roles.sh` 的 `reviewers = 三家 − implementer` 是**紙上名單**，不管誰能用。
    而 `review_quorum_check.sh:49-51` 要求 ≥2 個**非實作者**家族（`:38` 排除實作者）。
    grok 額度封鎖期間，三個 eligible 值中**唯有 grok** 能保住兩家審查者——
    那是巧合不是設計，任何人憑直覺 `set_roles.sh codex` 都會在**下一次派 review 時**
    才發現鐵律已破（此時已改完檔、切換不可見地生效）。

    修法＝切換**前**用機器算 `|active_stampers − {新 implementer}| ≥ 2`，否則拒。
    mutation 反例：移除該前檢 ⇒ 前兩例 rc 由 2 變 0 且 roles.json 被改寫，轉紅。

    真 SoT 全程唯讀：整條鏈複製到 tmp（同 `_isolated_stamp_env` 之理由）。
    """
    s = tmp_path / "scripts"
    s.mkdir(exist_ok=True)
    for f in ("set_roles.sh", "governance_families.sh", "governance_roles.json", "verify_role_gate.sh"):
        src = SCRIPTS / f
        if src.exists():
            (s / f).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    sot = _base_sot()
    if active == "__BREAK_RF__":
        sot["review_families"] = []          # 缺 active_stampers ＋ fallback 來源壞掉
    elif active is not None:
        sot["active_stampers"] = active
    (s / "governance_families.json").write_text(json.dumps(sot, ensure_ascii=False), encoding="utf-8")

    before = (s / "governance_roles.json").read_text(encoding="utf-8")
    p = _bash(f"{env} bash {s}/set_roles.sh {target}".strip())
    after = (s / "governance_roles.json").read_text(encoding="utf-8")
    out = p.stdout + p.stderr

    assert p.returncode == want_rc, f"{label}: rc={p.returncode} want={want_rc}\n{out}"
    if want_rc != 0:
        assert after == before, f"{label}: 拒絕切換卻仍改寫了 roles.json（非零副作用）"
        # 被擋的理由須說得出機械依據（quorum 不足／fail-closed／缺理由）
        assert any(k in out for k in ("review_quorum_check", "fail-closed", "REASON")), (
            f"{label}: 未說明被擋的機械依據\n{out}"
        )
    else:
        assert after != before, f"{label}: 應放行卻沒改寫 roles.json"
        if "ALLOW_QUORUM_BREAK" in env:
            # 🔴 破壞 quorum 須可歸因：理由寫進 history〔CODEX-R3-P2-04〕
            assert "quorum-break" in after, f"{label}: history 未記錄破壞事由\n{after}"


def test_adv_path_re_recognizes_grok() -> None:
    p = subprocess.run(
        ["python3", "-c",
         "import sys; sys.path.insert(0,'scripts'); import verify_task_provenance as v; "
         "print(bool(v.ADV_PATH_RE.match('handoffs/x-ADV-GROK.md')), bool(v.ADV_PATH_RE.match('handoffs/x-ADV-CODEX.md')))"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert p.stdout.strip() == "True True"


def test_gate_family_derivation_labels_grok(tmp_path: Path) -> None:
    """派 grok 任務 → audit family=grok(非 composer)。revert → composer → 本測試紅。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-grok.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-grok --output handoffs/frtest-grok.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role stamp:grok --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-grok"' in l]
        assert fams and all(f == "grok" for f in fams)
    finally:
        out.unlink(missing_ok=True)


# ---- 防漂移:所有寫死家族清單的消費者 == SoT(委員 B;取代脆弱 regex group 抽取,委員 RC-6) ----
_UNIVERSE = {"codex", "composer", "grok", "claude", "agy", "cursor-agent"}


def _fams_in_lines(fname: str, locate: str) -> list[set[str]]:
    """回**所有**含 locate 的行各自的 family token 集合(涵蓋重複 site,如 completeness 105/678)。

    找不到任何行(pattern 被重構)→ AssertionError(逼更新 drift 測試,非靜默漏)。
    """
    text = (SCRIPTS / fname).read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if locate in ln]
    assert lines, f"{fname}: 找不到含 '{locate}' 的家族清單行(refactor?→須更新 drift 測試)"
    out = []
    for ln in lines:
        low = ln.lower()
        out.append({u for u in _UNIVERSE if re.search(rf"(?<![a-z-]){re.escape(u)}(?![a-z-])", low)})
    return out


# (檔, 定位子字串, SoT key, 排除):寫死清單**每個 site** 須 == SoT[key]-排除。加/減家族未同步 → 紅。
# gate_check 同行含 `claude -p` 特例(非 executor_clis)→ 排除 claude。
# completeness_check 有 6 個 site(委員 codex B:單釘一行不夠)→ 全涵蓋。
_DRIFT = [
    ("gate_check.sh", "grok|agy)[", "executor_clis", {"claude"}),
    # 🔴 GOVB0 B4 r3：家族清單在 `_gate_lex.sh` 由「散落在多條正則裡」收斂成
    #    **單一定義** `_GL_FAMS='(codex|cursor-agent|grok|agy)'`（`CODEX-R2-P0-01` 之修法）。
    #    錨點隨之改為釘那一行的變數名——比釘整串正則穩定得多：
    #    正則會因每次擴充而漂，變數定義不會。
    ("_gate_lex.sh", "_GL_FAMS=", "executor_clis", set()),
    ("completeness_check.sh", "FAMILY_ALLOW_RE=", "families", set()),
    ("completeness_check.sh", "FAMILY_FILE_RE=", "families", set()),
    ("completeness_check.sh", 'fam["CODEX"]', "families", set()),
    ("completeness_check.sh", "allow = {", "families", set()),
    ("completeness_check.sh", 're.match(r"^.+-(codex', "families", set()),
    ("completeness_check.sh", "FAM = {", "families", set()),  # 913/1029/1103(委員 codex round2)
    ("completeness_check.sh", "allowlist 外家族", "families", set()),  # 557 訊息
    ("review_quorum_check.sh", "codex|composer|grok) :", "review_families", set()),
    ("write_sources_lock.sh", "allow = {", "families", set()),
    ("write_sources_lock.sh", "family_re = ", "families", set()),
    ("cx_run.sh", "family 須為", "review_families", set()),
    ("write_committee_accepted.sh", "FAM = {", "families", set()),
]

_CONSUMER_FILES = [
    "gate_check.sh", "_gate_lex.sh", "completeness_check.sh", "review_quorum_check.sh",
    "write_sources_lock.sh", "cx_run.sh", "write_committee_accepted.sh",
]


# 已知 doc 行(訊息/usage 範例;非功能碼)——**明確**白名單,非靜默 substring 排除(委員 codex round3)。
# 只有這幾行 doc 免 SoT-pin;任何**功能行**(含帶 echo/--roster 者)未 pin 一律紅。
_DOC_ALLOW = [
    "非實作者家族 code review",          # review_quorum echo 訊息
    "--roster codex,composer,grok",      # write_sources_lock usage 範例
    "cx_run.sh <codex|grok|composer>",   # cx_run usage 訊息
]


def test_no_unpinned_family_list_line() -> None:
    """反 whack-a-mole:除 #註解 與 _DOC_ALLOW 明列 doc 外,任何 ≥3 家族 token 的行都須被 _DRIFT 釘到。

    委員 codex round3:移除粗 substring 排除(echo/--roster/bash),否則功能行含這些字會被誤排漏網。
    未釘 → 紅(逼加入 _DRIFT 或 _DOC_ALLOW)。不再靠委員一輪輪找漏。
    """
    locates = [loc for _, loc, _, _ in _DRIFT]
    unpinned: list[str] = []
    for fname in _CONSUMER_FILES:
        for i, ln in enumerate((SCRIPTS / fname).read_text(encoding="utf-8").splitlines(), 1):
            if ln.lstrip().startswith("#"):  # 純註解 auto-skip(doc)
                continue
            fams = {u for u in _UNIVERSE if re.search(rf"(?<![a-z-]){re.escape(u)}(?![a-z-])", ln.lower())}
            if len(fams) < 3:
                continue
            if any(loc in ln for loc in locates):  # 已 pin
                continue
            if any(d in ln for d in _DOC_ALLOW):  # 明列 doc
                continue
            unpinned.append(f"{fname}:{i}: {ln.strip()[:72]}")
    assert not unpinned, "未釘 family 清單行(加入 _DRIFT 或明列 _DOC_ALLOW):\n" + "\n".join(unpinned)


@pytest.mark.parametrize("fname,locate,key,exclude", _DRIFT)
def test_consumer_family_list_matches_sot(fname: str, locate: str, key: str, exclude: set) -> None:
    expected = set(json.loads(SOT.read_text(encoding="utf-8"))[key])
    for got in _fams_in_lines(fname, locate):
        assert (got - exclude) == expected, (
            f"{fname} 家族清單 {got - exclude} != SoT {key} {expected}(漂移;改 SoT 須同步或反之)"
        )


# ---- fail-closed 邊界(委員 A/D):SoT 缺/壞 → 拒,不 fallback ----
def test_getter_failclosed_sot_missing(tmp_path: Path) -> None:
    """getter 複製到無 json 的 tmp → families_get fail-closed(不動真 SoT)。"""
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_getter_failclosed_sot_malformed(tmp_path: Path) -> None:
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "governance_families.json").write_text("{bad json", encoding="utf-8")
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_provenance_failclosed_on_sot_import(tmp_path: Path) -> None:
    """verify_task_provenance 從無 SoT 的 dir import → 拋錯(fail-closed,非 fallback)。"""
    for f in ("verify_task_provenance.py", "governance_families_loader.py"):
        (tmp_path / f).write_text((SCRIPTS / f).read_text(encoding="utf-8"), encoding="utf-8")
    p = subprocess.run(
        ["python3", "-c", f"import sys; sys.path.insert(0,'{tmp_path}'); import verify_task_provenance"],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert p.returncode != 0 and "fail-closed" in p.stderr


def test_review_role_substring_no_false_positive(tmp_path: Path) -> None:
    """`stamp:codexx` 不得誤判 codex(詞界);→ unknown(委員 codex C)。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-cxx.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-cxx --output handoffs/frtest-cxx.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role stamp:codexx --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-cxx"' in l]
        assert fams and all(f == "unknown" for f in fams), f"codexx 誤判: {fams}"
    finally:
        out.unlink(missing_ok=True)


def test_getter_failclosed_partial_families_key(tmp_path: Path) -> None:
    """families key null/壞但 review_families 好 → families_get families 仍 fail-closed(委員 codex A)。"""
    (tmp_path / "governance_families.sh").write_text(
        (SCRIPTS / "governance_families.sh").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (tmp_path / "governance_families.json").write_text(
        '{"families": null, "review_families": ["codex","composer","grok"]}', encoding="utf-8"
    )
    p = _bash(f". {tmp_path}/governance_families.sh && families_get families")
    assert p.returncode != 0


def test_gate_unknown_family_is_unknown_not_composer(tmp_path: Path) -> None:
    """未知 review_role → family=unknown(非 composer);歧義多家 → unknown。"""
    gate_dir = tmp_path / "g"
    out = REPO / "handoffs" / "frtest-unk.md"
    out.write_text("x\n", encoding="utf-8")
    try:
        _bash(
            f"GATE_DIR_OVERRIDE={gate_dir} bash scripts/gate.sh dispatch "
            f"--task-id frtest-unk --output handoffs/frtest-unk.md --intent t --risk low "
            f"--facts-asked none-needed:t --review-role single-executor:n/a --template n/a:t"
        )
        audit = (gate_dir / "audit.log").read_text(encoding="utf-8")
        fams = [json.loads(l)["family"] for l in audit.splitlines()
                if l.strip() and '"frtest-unk"' in l]
        assert fams and all(f == "unknown" for f in fams)
    finally:
        out.unlink(missing_ok=True)
