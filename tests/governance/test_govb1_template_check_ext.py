"""GOVB1 Task 1.5 — `票 B-16` 擴充 A/B/C 之可證偽測試。

受測物＝`scripts/template_check.sh` 新增之 `_run_assert_lines`／`_func_exists`／
`_check_scope_claim`。

🔴 **本檔一律跑生產原文，不抄複製品**：以 `awk` 從 `template_check.sh` 抽出函式
**原始碼**在隔離 shell 重跑。理由＝主委在 OOE 那批被委員證明「源碼比對擋不住
行為差異」；抽原文重跑則實作一改、測試立刻跟著改。

🔴 **最高優先＝`T-1.5-C0` 死鎖判準**：凍結之 SPEC/TODO 經本擴充後**仍須 rc=0**。
   若三個判準做成「掃描自然語言」，會命中本 epic 自己唯讀凍結的
   `docs/GOVB1_INPUT_QUALITY_{SPEC,TODO}.md`，而 `gate.sh:697,702` 對
   `--spec`／`--todo` 必跑 template_check 且失敗即拒發 token
   ⇒ **所有派工全部拒發、無人能修**（第六次結構性死鎖）。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "template_check.sh"
FROZEN_SPEC = REPO / "docs" / "GOVB1_INPUT_QUALITY_SPEC.md"
FROZEN_TODO = REPO / "docs" / "GOVB1_INPUT_QUALITY_TODO.md"

# 抽函式原文所需的相依（`_tc_live_lines`／`_tc_ere_escape` 為共用 helper）
_DEPS = ("_tc_live_lines", "_tc_live_or_die", "_tc_ere_escape")


# 函式所依賴之頂層常數（非函式，須另抽；漏抽會使受測函式在隔離 shell 下 unbound）
_CONSTS = ("_TC_ASSERT_SAFE_CHARS",)


def _extract(*fns: str) -> str:
    """從 template_check.sh 抽出指定函式之**原始碼**（含共用 helper 與其依賴常數）。"""
    src = SCRIPT.read_text(encoding="utf-8")
    out = []
    for const in _CONSTS:
        m = re.search(rf"^{re.escape(const)}=.*$", src, re.M)
        assert m, f"找不到常數 {const}（重構?→須更新本測）"
        out.append(m.group(0) + "\n")
    for fn in (*_DEPS, *fns):
        marker = f"\n{fn}() {{\n"
        i = src.find(marker)
        assert i >= 0, f"找不到函式 {fn}（重構?→須更新本測，不得靜默略過）"
        j = src.find("\n}\n", i)
        assert j > i, f"函式 {fn} 未正常結束"
        out.append(src[i + 1 : j + 3])
    return "".join(out)


def _run_fn(fns: tuple[str, ...], body: str, tmp: Path) -> subprocess.CompletedProcess[str]:
    """在隔離 shell 內載入生產原文並執行 `body`。"""
    script = tmp / "probe.sh"
    script.write_text("set -u\n" + _extract(*fns) + "\n" + body + "\n", encoding="utf-8")
    return subprocess.run(
        ["bash", str(script)], cwd=REPO, capture_output=True, text=True, check=False
    )


def _tc(kind: str, path: Path, force: bool = True) -> subprocess.CompletedProcess[str]:
    """端到端跑 template_check.sh。force=True 時強制啟用擴充判準。"""
    env = {"TEMPLATE_CHECK_EXT_SCOPE": "force"} if force else {}
    return subprocess.run(
        ["bash", str(SCRIPT), kind, str(path)],
        cwd=REPO, capture_output=True, text=True, check=False,
        env={**dict(__import__("os").environ), **env},
    )


# ── T-1.5-C0：死鎖判準（最高優先）────────────────────────────────────
@pytest.mark.parametrize("kind,doc", [("spec", FROZEN_SPEC), ("todo", FROZEN_TODO)])
def test_t15_c0_frozen_docs_still_pass(kind: str, doc: Path) -> None:
    """🔴 凍結之 SPEC/TODO 經本擴充後**仍須 rc=0**（否則所有派工被拒、無人能修）。

    非零 ⇒ 判準做成了掃描式，退回重做。**本測失敗時不得改斷言求綠。**
    """
    p = _tc(kind, doc, force=False)  # 走真實接線路徑（docs/*SPEC*.md 自動命中）
    assert p.returncode == 0, (
        f"🔴 死鎖判準失敗：{doc.name} rc={p.returncode}\n{p.stdout}{p.stderr}"
    )


def test_t15_c0_anchoring_is_load_bearing() -> None:
    """錨定是承重的，不是風格——量給後人看。

    未錨定的 `ASSERT ` 在凍結 TODO 有數十個命中（含 `gate.sh dispatch`）；
    若判準不錨定行首，`template_check` 會在**每次派工時真的執行那些命令**。
    """
    text = FROZEN_TODO.read_text(encoding="utf-8")
    unanchored = [ln for ln in text.splitlines() if "ASSERT " in ln]
    anchored = [ln for ln in text.splitlines() if ln.lstrip().startswith("ASSERT ")]
    assert len(unanchored) >= 10, "凍結 TODO 之 ASSERT 樣本數變了，請重新評估錨定必要性"
    assert not anchored, (
        f"凍結 TODO 出現行首 ASSERT（{len(anchored)} 行）⇒ 會被真的執行，須重新裁定"
    )
    assert any("gate.sh dispatch" in ln for ln in unanchored), (
        "凍結 TODO 內原本含 `gate.sh dispatch` 之 ASSERT 樣本；樣本消失則本測失去意義"
    )


# ── T-1.5-B1：_func_exists 四種形態 ＋ literal 化 ──────────────────────
_FIXTURE_FUNCS = """\
def py_fn(x):
    pass
sh_paren() {
  :
}
function sh_noparen {
  :
}
function sh_both() {
  :
}
# commented_fn() {
fXoo() { :; }
f() { :; }
"""


@pytest.mark.parametrize(
    "name,want_rc,why",
    [
        ("py_fn", 0, "Python def"),
        ("sh_paren", 0, "shell name() {"),
        ("sh_noparen", 0, "🔴 POSIX function name {（TODO 偽碼漏接）"),
        ("sh_both", 0, "shell function name() {"),
        ("commented_fn", 1, "註解中不算存在（^ 錨點已滿足，不必另剝除 #）"),
        ("nosuch", 1, "不存在"),
        ("f.oo", 1, "🔴 `.` 不得當 regex 誤命中 fXoo"),
        ("f*", 1, "🔴 `*` 不得當 regex 誤命中 f"),
    ],
)
def test_t15_b1_func_exists(tmp_path: Path, name: str, want_rc: int, why: str) -> None:
    """`_func_exists` 之雙向缺陷（漏接合法形態／誤命中不存在標的）皆須關閉。"""
    target = tmp_path / "t.sh"
    target.write_text(_FIXTURE_FUNCS, encoding="utf-8")
    p = _run_fn(("_func_exists",), f'_func_exists {name!r} {target}; echo "rc=$?"', tmp_path)
    assert p.returncode == 0, p.stderr
    assert f"rc={want_rc}" in p.stdout, f"{name}（{why}）: got {p.stdout.strip()}"


# ── T-1.5-C1：_check_scope_claim 封閉文法 ─────────────────────────────
@pytest.mark.parametrize(
    "label,content,want_rc",
    [
        ("合法", "SCOPE-CLAIM:S1 全部守衛已驗 DERIVE:grep -c foo bar.sh", 0),
        ("縮排合法", "   SCOPE-CLAIM:S1 全部守衛已驗 DERIVE:grep -c foo bar.sh", 0),
        ("缺 DERIVE", "SCOPE-CLAIM:S1 全部守衛已驗", 1),
        ("空 subject", "SCOPE-CLAIM:S1 DERIVE:grep -c foo bar.sh", 1),
        ("空命令", "SCOPE-CLAIM:S1 全部守衛已驗 DERIVE:", 1),
        ("id 含非法字元", "SCOPE-CLAIM:S!1 全部 DERIVE:x", 1),
        ("id 缺席", "SCOPE-CLAIM: 全部 DERIVE:x", 1),
        ("DERIVE 出現兩次", "SCOPE-CLAIM:S1 a DERIVE:x DERIVE:y", 1),
        ("重複 id", "SCOPE-CLAIM:D1 a DERIVE:x\nSCOPE-CLAIM:D1 b DERIVE:y", 1),
        ("fence 內不算宣告", "```\nSCOPE-CLAIM:F1 fence 內\n```", 0),
        ("CRLF 須正規化", "SCOPE-CLAIM:R1 x DERIVE:y\r", 0),
        ("普通散文提及不觸發", "本節談到 SCOPE-CLAIM: 的格式，不是行首宣告", 0),
        # 🔴 COMPOSER-R1-P2-01：`[[:space:]]` 含 NBSP／全形空白 ⇒ 貼上來的縮排會被當行首宣告
        ("NBSP 前綴不得視為行首", " SCOPE-CLAIM:N1 缺 DERIVE", 0),
        ("全形空白前綴不得視為行首", "　SCOPE-CLAIM:N2 缺 DERIVE", 0),
        ("ASCII 空白仍須視為行首", " SCOPE-CLAIM:N3 缺 DERIVE", 1),
        ("TAB 仍須視為行首", "\tSCOPE-CLAIM:N4 缺 DERIVE", 1),
    ],
)
def test_t15_c1_scope_claim_grammar(
    tmp_path: Path, label: str, content: str, want_rc: int
) -> None:
    """C 只認正向結構化宣告；**普通散文完全不觸發**（防自鎖之根本）。"""
    doc = tmp_path / "c.md"
    doc.write_text(content + "\n", encoding="utf-8")
    p = _run_fn(
        ("_check_scope_claim",), f'_check_scope_claim {doc} >/dev/null 2>&1; echo "rc=$?"', tmp_path
    )
    assert p.returncode == 0, p.stderr
    assert f"rc={want_rc}" in p.stdout, f"{label}: got {p.stdout.strip()}"


# ── T-1.5-A1：_run_assert_lines ＋ pending 三條件 ─────────────────────
def test_t15_a1_assert_rc_compared(tmp_path: Path) -> None:
    """`ASSERT <cmd> THEN rc=<n>`：rc 相符 ⇒ 0；不符 ⇒ 非零。"""
    ok = tmp_path / "ok.md"
    ok.write_text("ASSERT true THEN rc=0\n", encoding="utf-8")
    bad = tmp_path / "bad.md"
    bad.write_text("ASSERT false THEN rc=0\n", encoding="utf-8")
    for doc, want in ((ok, 0), (bad, 1)):
        p = _run_fn(
            ("_run_assert_lines",),
            f'_run_assert_lines {doc} >/dev/null 2>&1; echo "rc=$?"', tmp_path,
        )
        assert f"rc={want}" in p.stdout, f"{doc.name}: {p.stdout.strip()}"


def test_t15_a1_pending_requires_all_three_conditions(tmp_path: Path) -> None:
    """🔴 `pending` 是 fail-open 的入口：**預設拒絕**，且 opt-in 後仍須三條件全成立。

    TODO `:846` 原文「引用尚未實作的腳本 ⇒ rc=0 並標 pending」無判準：
    codex 實測**不存在腳本 rc=127 也會被吞**。
    🔴 `CODEX-R2-P1-02` 再指出：只憑「受檢檔自己寫一行 `新建：`」授權 pending，
    等於**權威來源就是受檢物本身**。採較嚴版：`TEMPLATE_CHECK_ALLOW_PENDING=1`
    才可能 pending ⇒ 凍結文件路徑**永不 pend**。
    """
    body = '_run_assert_lines {doc} >/dev/null 2>&1; echo "rc=$?"'

    # ① 預設（未 opt-in）：即使列於「新建：」也不得 pending
    decl = tmp_path / "b.md"
    decl.write_text(
        "新建：`scripts/never_built_xyz.sh`\n"
        "ASSERT bash scripts/never_built_xyz.sh THEN rc=0\n",
        encoding="utf-8",
    )
    p = _run_fn(("_run_assert_lines",), body.format(doc=decl), tmp_path)
    assert "rc=1" in p.stdout, f"未 opt-in 卻 pending（fail-open）: {p.stdout.strip()}"

    # ② opt-in ＋ 未列於「新建：」⇒ 仍拒
    no_decl = tmp_path / "a.md"
    no_decl.write_text("ASSERT bash scripts/never_built_xyz.sh THEN rc=0\n", encoding="utf-8")
    p = _run_fn(
        ("_run_assert_lines",),
        "TEMPLATE_CHECK_ALLOW_PENDING=1; export TEMPLATE_CHECK_ALLOW_PENDING\n"
        + body.format(doc=no_decl),
        tmp_path,
    )
    assert "rc=1" in p.stdout, f"opt-in 後未列新建仍 pending: {p.stdout.strip()}"

    # ③ opt-in ＋ 列於「新建：」⇒ 允許 pending
    p = _run_fn(
        ("_run_assert_lines",),
        "TEMPLATE_CHECK_ALLOW_PENDING=1; export TEMPLATE_CHECK_ALLOW_PENDING\n"
        + body.format(doc=decl),
        tmp_path,
    )
    assert "rc=0" in p.stdout, f"三條件全成立仍被拒: {p.stdout.strip()}"

    # ④ 標的**存在**但 rc 不符 ⇒ 一律失敗（不得因 pending 機制放行）
    real = tmp_path / "c.md"
    real.write_text(
        "新建：`scripts/template_check.sh`\n"
        "ASSERT bash scripts/template_check.sh THEN rc=0\n",
        encoding="utf-8",
    )
    p = _run_fn(
        ("_run_assert_lines",),
        "TEMPLATE_CHECK_ALLOW_PENDING=1; export TEMPLATE_CHECK_ALLOW_PENDING\n"
        + body.format(doc=real),
        tmp_path,
    )
    assert "rc=1" in p.stdout, (
        f"標的存在時仍走了 pending 分支（缺參數應 rc=1 而非放行）: {p.stdout.strip()}"
    )


@pytest.mark.parametrize(
    "label,content,want_rc",
    [
        # 🔴 CODEX-R2-P1-03：`THEN rc=` 須恰一個且位於行尾
        ("重複 THEN rc（畸形行）", "ASSERT false THEN rc=0 THEN rc=1", 1),
        ("THEN rc 後有尾隨字元", "ASSERT true THEN rc=0 備註", 1),
        # 🔴 CODEX-R2-P1-04：命令不得含 shell 元字元／重導向／命令替換
        ("重導向", "ASSERT true > /tmp/govb1_probe_marker THEN rc=0", 1),
        ("分號串接", "ASSERT true; false THEN rc=0", 1),
        ("命令替換", "ASSERT echo $(id) THEN rc=0", 1),
        ("管線", "ASSERT true | false THEN rc=0", 1),
        ("合法單一命令", "ASSERT true THEN rc=0", 0),
        # 🔴 CODEX-R2-P1-01：未閉合 fence 不得吞到 EOF 而靜默漏檢
        ("未閉合 fence ⇒ fail-closed", "```\nASSERT true THEN rc=0", 1),
        ("~~~ 不得收合 ``` ", "```\n~~~\nASSERT true THEN rc=0", 1),
    ],
)
def test_t15_a1_assert_line_grammar_and_no_eval(
    tmp_path: Path, label: str, content: str, want_rc: int
) -> None:
    """A 之整行封閉文法 ＋ 禁 `eval`〔`CODEX-R2-P1-03`／`P1-04`／`P1-01`〕。"""
    doc = tmp_path / "g.md"
    doc.write_text(content + "\n", encoding="utf-8")
    p = _run_fn(
        ("_run_assert_lines",), f'_run_assert_lines {doc} >/dev/null 2>&1; echo "rc=$?"', tmp_path
    )
    assert f"rc={want_rc}" in p.stdout, f"{label}: got {p.stdout.strip()}"


def test_t15_a1_no_side_effect_from_redirection(tmp_path: Path) -> None:
    """🔴 承重：帶重導向之 ASSERT **不得產生副作用**（codex 實證舊版真的建了檔）。"""
    marker = tmp_path / "marker"
    doc = tmp_path / "s.md"
    doc.write_text(f"ASSERT : > {marker} THEN rc=0\n", encoding="utf-8")
    _run_fn(("_run_assert_lines",), f'_run_assert_lines {doc} >/dev/null 2>&1; echo "rc=$?"', tmp_path)
    assert not marker.exists(), "🔴 ASSERT 之重導向產生了副作用（eval 未被移除？）"


def test_t15_a1_unparseable_assert_is_failure(tmp_path: Path) -> None:
    """解析失敗 ⇒ **失敗**，不得靜默略過或 pending。"""
    doc = tmp_path / "a.md"
    doc.write_text("ASSERT bash scripts/template_check.sh\n", encoding="utf-8")  # 缺 THEN rc=
    p = _run_fn(("_run_assert_lines",), f'_run_assert_lines {doc} >/dev/null 2>&1; echo "rc=$?"', tmp_path)
    assert "rc=1" in p.stdout, f"無法解析卻放行: {p.stdout.strip()}"


# ── T-1.5-M1：mutation 必附 ───────────────────────────────────────────
def test_t15_m1_missing_function_turns_red(tmp_path: Path) -> None:
    """🔴 mutation：規格內宣告一個**不存在**的函式 ⇒ rc≠0；改成存在的 ⇒ rc=0。

    這是本 Task 的承重斷言——證明 B 真的在查存在性，而不是恆真。
    """
    base = (
        "# fixture\n\n## §A 已驗證事實\n\n- 佔位\n\n"
        "## §G 交付\n\n## §V 驗證\n\n- 驗證：`pytest` 3 passed\n"
    )
    bad = tmp_path / "spec_bad.md"
    bad.write_text(base + "函式：totally_missing_function_xyz\n", encoding="utf-8")
    good = tmp_path / "spec_good.md"
    good.write_text(base + "函式：_func_exists\n", encoding="utf-8")

    pb = _tc("spec", bad)
    pg = _tc("spec", good)
    out_b, out_g = pb.stdout + pb.stderr, pg.stdout + pg.stderr

    assert "totally_missing_function_xyz" in out_b, (
        f"不存在之函式未被點名（B 未生效或恆真）\n{out_b}"
    )
    assert pb.returncode != 0, f"不存在之函式竟通過\n{out_b}"
    assert "totally_missing_function_xyz" not in out_g, out_g
    assert "_func_exists" not in out_g.replace("template_check", ""), (
        f"存在之函式被誤報不存在（誤擋）\n{out_g}"
    )


def test_t15_ext_not_applied_to_handoffs(tmp_path: Path) -> None:
    """🔴 B/C **不得**套用於 `handoffs/` 委員產出（討論語境，會誤擋；Task 1.2 教訓）。

    以未 force 之真實接線路徑驗證：同一份含壞宣告的內容放在 handoffs 形態路徑下，
    擴充判準不得觸發（其他既有檢查照舊）。
    """
    src = SCRIPT.read_text(encoding="utf-8")
    i = src.find("case \"${_tc_rel}\" in")
    assert i >= 0, "找不到接線之 scope 判定（重構?→須更新本測）"
    seg = src[i : i + 300]
    assert "docs/*SPEC*.md" in seg and "docs/*TODO*.md" in seg, seg
    assert "handoffs/" not in seg, "🔴 接線 scope 含 handoffs/ ⇒ 會誤擋委員產出"
