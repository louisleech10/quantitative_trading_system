"""GOVB0 B3R Phase 3 — 詞法層 O(n) 重寫的驗收（SPEC §V.2 C-5 ＋ 行為不變）。

對應 `docs/GOVB0_B3R_LEXER_SPEC.md` §V.2 C-5 與 §P Task 3.1。
量測與根因收據：`docs/GOV_B3R_PHASE3_RECEIPT.md`。

三組斷言，缺一不可：
  ① **效能**（C-5 條文）：引號內 100K <2s、500K <5s、4MB 有界且不 fail-open。
  ② **行為不變**：批次快路徑關掉後，前處理輸出必須逐位元組相同
     ——重構的正當性全靠這一條，不是靠「跑起來比較快」。
  ③ **可證偽**：把視窗存取還原成直接 substr，①的門檻必須被撞破；
     否則①只是在量一個與修法無關的東西。
"""
from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
GATE_LEX = REPO_ROOT / "scripts" / "_gate_lex.sh"
CORPUS_A = REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_invariance_corpus.txt"
CORPUS_B = REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_decision_corpus.txt"

# SPEC §V.2 C-5 的門檻。**不得放寬**（§P Task 3.1「不可做」）。
C5_100K_SEC = 2.0
C5_500K_SEC = 5.0
# 4MB 只要求「有界且不 fail-open」，沿用既有 D-2d 樁的 30s 上界。
C5_4MB_SEC = 30.0
# 長度加倍時可接受的耗時比值上界。線性≈2.0、平方≈4.0。
# 本機實測最差 2.19（quote／2M→4M）⇒ 2.6 留約 19% 餘裕給 runner 抖動，
# 同時距離平方的 4.0 仍有足夠鑑別力。
MAX_DOUBLING_RATIO = 2.6
# 跑「變異版」時的硬性時間上限。變異可能造成無窮迴圈（實測 win_at_boundary 就會），
# 沒有上限的話測試不是紅、也不是綠，而是**永遠不結束**——那比紅更糟，
# 因為「程序還在」跟「還在跑」長得一模一樣。
MUTANT_TIMEOUT_SEC = 20
# 逾時的專用回傳碼；與任何真實 rc 不重疊，確保「卡住」是可比對的具體結果。
HANG_RC = -9999


def _run_bounded(argv: list[str], timeout: float) -> tuple[int, bytes]:
    """跑一個子程序，逾時就把**整個 process group** 殺掉。

    🔴 為什麼不能只用 `subprocess.run(timeout=...)`：那只殺**直接子程序**。
       這裡的直接子是 `bash`，真正在跑的是它底下的 `awk`——bash 被殺之後
       awk 變孤兒、繼續空轉。本輪實測留下 **5 個各吃 ~70% CPU 的失控 awk**，
       把之後的全套測試由 8 分鐘拖成 27 分鐘，且外觀上完全看不出來。
       ⇒ `start_new_session=True` 讓子程序自成一個 group，逾時時整組 SIGKILL。
    """
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, out
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()
        # 逾時是一個**可觀察的結果**，不是無限等待。
        return HANG_RC, b"<TIMEOUT>"


def _decide(cmd: str, gate_dir: Path, lex_path: Path | None = None) -> tuple[str, float]:
    """跑一次完整判定，回傳 (BLOCK|ALLOW, 秒數)。

    lex_path 給定時，改用該份 _gate_lex.sh（mutation 用）。
    """
    import json

    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    script = GATE_CHECK
    if lex_path is not None:
        script = lex_path.parent / "gate_check.sh"
        script.write_text(GATE_CHECK.read_text(encoding="utf-8"), encoding="utf-8")
        script.chmod(0o755)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}, ensure_ascii=False)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            ["bash", str(script)],
            input=payload,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            env=env,
            # 🔴 上限給得比任何門檻都寬鬆；它不是效能斷言，是「不准無限等」的保險。
            timeout=C5_4MB_SEC * 4,
        )
    except subprocess.TimeoutExpired:
        return "HANG", time.perf_counter() - t0
    elapsed = time.perf_counter() - t0
    return ("BLOCK" if proc.returncode != 0 else "ALLOW"), elapsed


def _preprocess_bytes(cmd: str, lex_path: Path, work: Path) -> tuple[int, bytes]:
    """直接呼叫 _gate_lex_preprocess，回傳 (rc, stdout 原始位元組)。

    🔴 回傳 bytes 而非 str：尾端有沒有換行正是這類重構最容易壞的地方，
       用文字比對（或命令替換）會把證據吃掉。
    🔴 輸入暫存檔一律寫在 work（pytest tmp_path）底下，**不得**寫進 lex 所在目錄
       ——那會是 repo 的 scripts/。
    """
    script = (
        f'. "{lex_path}"\n'
        '_gate_lex_preprocess "$(cat "$1")"\n'
    )
    work.mkdir(parents=True, exist_ok=True)
    with_input = work / "_in.txt"
    with_input.write_bytes(cmd.encode("utf-8"))
    return _run_bounded(["bash", "-c", script, "_", str(with_input)], MUTANT_TIMEOUT_SEC)


def _mutated_lex(tmp_path: Path, name: str, old: str, new: str) -> Path:
    """複製一份 _gate_lex.sh 並做字面替換；錨點失配即 fail（禁靜默通過）。"""
    text = GATE_LEX.read_text(encoding="utf-8")
    assert old in text, f"mutation 錨點漂移：{name} 找不到 {old!r}"
    mutated = text.replace(old, new)
    assert mutated != text, f"mutation 未生效：{name}"
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "_gate_lex.sh"
    p.write_text(mutated, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ① 效能（SPEC §V.2 C-5）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "shape,unit",
    [
        ("plain", "a"),
        ("semi", ";"),
        ("space", " "),
        ("bslash", "\\"),
        ("quote", '"a'),
    ],
)
def test_c5_quoted_100k_under_2s(tmp_path: Path, shape: str, unit: str) -> None:
    """C-5：引號內 100K 字元 <2s。

    🔴 不只測全 a：全 a 只證明「無趣字元多」時快。分隔符／空白／反斜線／
       交替引號各自走不同分支，其中反斜線與交替引號**無法批次**，是真正的下界。
    """
    body = (unit * (100_000 // len(unit) + 1))[:100_000]
    verdict, elapsed = _decide(f'echo "{body}"', tmp_path / f"p100_{shape}")
    assert elapsed < C5_100K_SEC, f"{shape} 100K 逾時 {elapsed:.2f}s（門檻 {C5_100K_SEC}s）"
    assert verdict == "ALLOW", f"{shape} 100K 無害字串不得誤擋"


@pytest.mark.parametrize(
    "shape,unit",
    [
        ("plain", "a"),
        ("semi", ";"),
        ("space", " "),
        ("bslash", "\\"),
        ("quote", '"a'),
        ("mixed", "a; \\b"),
    ],
)
def test_c5_quoted_500k_under_5s(tmp_path: Path, shape: str, unit: str) -> None:
    """C-5：引號內 500K 字元 <5s（SPEC E-2 記載的舊值為 29.92s）。"""
    body = (unit * (500_000 // len(unit) + 1))[:500_000]
    verdict, elapsed = _decide(f'echo "{body}"', tmp_path / f"p500_{shape}")
    assert elapsed < C5_500K_SEC, f"{shape} 500K 逾時 {elapsed:.2f}s（門檻 {C5_500K_SEC}s）"
    assert verdict == "ALLOW", f"{shape} 500K 無害字串不得誤擋"


def test_b3r_growth_ratio_is_near_linear_not_quadratic(tmp_path: Path) -> None:
    """成長率斷言：長度加倍，耗時不得超過 `MAX_DOUBLING_RATIO` 倍。

    🔴 為何需要這條，而不是只有上面的絕對秒數門檻（使用者 2026-08-11 質疑，直接命中要害）：
      ① 絕對門檻**綁機器**——本機 0.38s 的東西在共用 runner 上可能 3s，門檻訂多少都是猜硬體。
      ② 絕對門檻只量**一個點**，量不到成長的形狀：一個平方級實作只要常數夠小，
         照樣通過 500K < 5s，然後在 4MB 死掉。
      ③ 本輪實證：C-5 三條時間門檻**全綠**，但 codex 仍正確指出漸近契約未達標
         （SPEC §B.1 寫 O(n)，實作是 O(n·sqrt(n))）⇒ 時間門檻擋不住該擋的東西。

    比值把機器速度的常數**約掉**：線性 → 2.0、平方 → 4.0，快慢機器算出來一樣。
    量測取兩次的**最小值**（min 對偶發的機器卡頓穩健，不會把別人的負載算到我頭上）。
    """
    # quote 形狀＝每字元都得逐字決策，是成長最快的下界（見收據 §4）
    sizes = (250_000, 500_000, 1_000_000)
    times: list[float] = []
    for idx, n in enumerate(sizes):
        body = ('"a' * (n // 2 + 1))[:n]
        runs = [
            _decide(f'echo "{body}"', tmp_path / f"g{idx}_{k}")[1]
            for k in range(2)
        ]
        times.append(min(runs))

    ratios = [times[i + 1] / times[i] for i in range(len(times) - 1)]
    assert all(r <= MAX_DOUBLING_RATIO for r in ratios), (
        f"長度加倍之耗時比值 {[round(r, 2) for r in ratios]} 超過 {MAX_DOUBLING_RATIO}"
        f"（線性≈2.0、平方≈4.0）；times={[round(t, 3) for t in times]}"
        " ⇒ 成長率退化，即使絕對秒數仍在門檻內也不接受"
    )


@pytest.mark.parametrize(
    "shape,unit",
    [("space", " "), ("semi", ";"), ("bslash", "\\")],
)
def test_c5_4mb_mapping_heavy_bounded(tmp_path: Path, shape: str, unit: str) -> None:
    """C-5 第三條的補強：4MB **需要映射**的形狀，不只全 a。

    出處 `CODEX-R1-P2-01`：原本 4MB 樁只放 `"a" * 4_000_000`，
    走的是「整段無趣、一次搬移」的最順路徑 ⇒ 量不到 XFORM_Q 與逐字路徑在 4MB 的行為。
    """
    body = (unit * (4_000_000 // len(unit) + 1))[:4_000_000]
    verdict, elapsed = _decide(f'echo "{body}"', tmp_path / f"m4_{shape}")
    assert elapsed < C5_4MB_SEC, f"4MB {shape} 逾時 {elapsed:.2f}s（上界 {C5_4MB_SEC}s）"
    assert verdict == "ALLOW", f"4MB {shape} 無害字串不得誤擋"


def test_c5_quoted_4mb_bounded_and_not_failopen(tmp_path: Path) -> None:
    """C-5 第三條：**引號內** 4MB 有界，且尾端真派工仍 BLOCK。

    既有的 `test_21_c1_oversize_failclosed_bounded` 用的是**無引號** 4MB，
    那條走 raw grep 捷徑、根本不進前處理 ⇒ 涵蓋不到本次修的路徑。
    """
    body = "a" * 4_000_000
    verdict_h, t_h = _decide(f'echo "{body}"', tmp_path / "m4h")
    assert t_h < C5_4MB_SEC, f"4MB 引號內逾時 {t_h:.2f}s"
    assert verdict_h == "ALLOW", "4MB 無害引號字串不得誤擋"

    verdict_d, t_d = _decide(f'echo "{body}"; codex exec hi', tmp_path / "m4d")
    assert t_d < C5_4MB_SEC, f"4MB + 尾端派工逾時 {t_d:.2f}s"
    assert verdict_d == "BLOCK", "4MB 之後的真派工不得因長度 fail-open"


# ---------------------------------------------------------------------------
# ② 行為不變（重構的正當性來源）
# ---------------------------------------------------------------------------


# 🔴 heredoc 結構案例：既有兩份語料是**逐行**檔案，結構上放不進跨行的 heredoc，
#    所以裡面一條可成功解析的 heredoc 都沒有。後果是 Pass 1 從不真的改動 src
#    ⇒ 「src 換手後要重置視窗」那條守衛在既有語料下**永遠測不到**。
#    本輪實際發生：`win_reset` mutation 對 95 條語料完全無差異。
#    ⇒ 手寫下列案例補進 mutation 語料。沒被測到的守衛不算防護。
_HEREDOC_CASES: tuple[str, ...] = (
    "cat <<EOF\nplain body\nEOF",
    "cat <<EOF\ncodex exec x\nEOF",
    'cat <<EOF\ncodex exec x\nEOF\n"a b"',
    'cat <<EOF\nbody one\nbody two\nEOF\necho "p q"',
    'cat <<-EOF\n\tindented body\n\tEOF\necho "r s"',
    "cat <<'EOF'\nquoted delim body\nEOF\necho \"t u\"",
    'cat <<"EOF"\ndq delim body\nEOF\necho "v w"',
    'echo pre; cat <<EOF\ninner "quoted" body\nEOF\necho post',
    'cat <<EOF\nbody with ; and | and &\nEOF\necho "ii jj"',
    'cat <<EOF\nbody\nEOF\ncat <<EOF2\nbody2\nEOF2\necho "ee ff"',
)


def _mutation_cases() -> list[str]:
    """mutation 偵測用語料＝既有兩份語料 ＋ 手寫 heredoc 案例。"""
    return _corpus_lines() + list(_HEREDOC_CASES)


def _corpus_lines() -> list[str]:
    lines: list[str] = []
    for f in (CORPUS_A, CORPUS_B):
        assert f.is_file(), f"缺語料 {f}"
        for raw in f.read_text(encoding="utf-8").splitlines():
            if raw and not raw.startswith("#"):
                lines.append(raw)
    assert len(lines) >= 50, f"語料過少（{len(lines)}），涵蓋度不足以支撐等價宣稱"
    return lines


def test_b3r_fastpath_equals_slowpath(tmp_path: Path) -> None:
    """關掉 Pass 2 批次快路徑後，前處理輸出必須**逐位元組相同**。

    這是本批唯一的正當性論證：快路徑只是「跳過那些逐字分支必然原樣處理的字元」。
    若兩者輸出有任何差異，代表快路徑改變了語義 ⇒ 整個重構無效。
    """
    slow = _mutated_lex(tmp_path, "slowpath", "if (np == 0) np = n + 1", "np = i")
    work = tmp_path / "work"
    mismatches: list[str] = []
    for line in _corpus_lines():
        rc_f, out_f = _preprocess_bytes(line, GATE_LEX, work)
        rc_s, out_s = _preprocess_bytes(line, slow, work)
        if (rc_f, out_f) != (rc_s, out_s):
            mismatches.append(f"{line!r}: fast=({rc_f},{out_f!r}) slow=({rc_s},{out_s!r})")
    assert not mismatches, "快路徑與逐字路徑輸出不一致：\n" + "\n".join(mismatches[:5])


def test_b3r_leading_blank_lines_semantics_unchanged(tmp_path: Path) -> None:
    """前導空行的處理必須與重寫前**逐位元組相同**（丟棄，不保留）。

    出處：本批 12000 例 fuzz 差分抓到 233 例差異，根因是 Phase 2 的機械改寫
    把 `if (src != "")` 換成「不是第一行」旗標，語義從「丟棄前導換行」
    變成「保留」。判定 rc 未受影響，但本批是效能重構 ⇒ 一律還原。

    🔴 本測試釘死的是「與舊版一致」，**不是**「這個行為是對的」。
       舊版丟掉前導換行是否本身該修，另立票，不在本批夾帶。
    """
    for cmd, expected in [
        ("\na", b"a\n"),
        ("\n\na", b"a\n"),
        ("\n\n\na", b"a\n"),
        ("a\n\nb", b"a\n\nb\n"),
    ]:
        rc, out = _preprocess_bytes(cmd, GATE_LEX, tmp_path / "blank")
        assert rc == 0, f"{cmd!r} 前處理不應 fail-closed"
        assert out == expected, f"{cmd!r} 前處理輸出 {out!r} != {expected!r}"


# ---------------------------------------------------------------------------
# ③ 可證偽（證明①量到的就是修法本身）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,old,new",
    [
        (
            "next_of_off1",
            "if (r > 0) return pos + r - 1",
            "if (r > 0) return pos + r",
        ),
        (
            "ch_off1",
            "return substr(_win, pos - _wbase + 1, 1)",
            "return substr(_win, pos - _wbase + 2, 1)",
        ),
        (
            "slice_off1",
            "if (take >= len) return substr(_win, from - _wbase + 1, len)",
            "if (take >= len) return substr(_win, from - _wbase + 1, len - 1)",
        ),
        (
            "win_at_boundary",
            "if (pos < _wbase || pos >= _wbase + _wlen) {",
            "if (pos < _wbase || pos > _wbase + _wlen) {",
        ),
        (
            "xform_sep",
            'gsub(/[;&|]/, " ", t)',
            'gsub(/[;&|]/, ";", t)',
        ),
        (
            "win_reset",
            "      WIN_RESET()\n\n      # Pass 2",
            "      _wsz = _wsz\n\n      # Pass 2",
        ),
    ],
)
def test_b3r_helper_mutation_is_detected(tmp_path: Path, name: str, old: str, new: str) -> None:
    """視窗／批次 helper 的邊界不變式，各自有能讓它轉紅的 mutation。

    出處 `CODEX-R1-P2-02`：原本這些 mutation 只活在主委本機的 `.claude/tmp/mutate_lex.sh`，
    **CI 完全沒有**。共用 helper 若在 fast/slow 兩路徑同時錯，
    `test_b3r_fastpath_equals_slowpath` 仍會相等 ⇒ 那條擋不住這類缺陷。

    判準：mutant 對語料的前處理輸出，**至少一條**與基準不同。
    一條都不同 ⇒ 該不變式沒有被任何語料涵蓋（等同沒測）。
    """
    mut = _mutated_lex(tmp_path, name, old, new)
    work = tmp_path / f"w_{name}"
    for line in _mutation_cases():
        if _preprocess_bytes(line, GATE_LEX, work) != _preprocess_bytes(line, mut, work):
            return
    pytest.fail(f"mutation {name} 未被任何語料偵測到 ⇒ 該不變式無覆蓋")


def test_b3r_next_of_empty_guard_is_load_bearing(tmp_path: Path) -> None:
    """`NEXT_OF` 對空 `c2` 的保護擋的是**無窮迴圈**，不只是效能。

    `index(s, "")` 在 awk 回傳 1 ⇒ 少了 `if (c2 != "")`，`NEXT_OF` 在某些狀態下
    會回傳目前位置而不前進，或在視窗尾取到空字串後 `pos` 停滯 ⇒ 掃描永不結束。

    🔴 這條的由來是真的踩到：主委原本猜它「只是效能保護」，
    結果沒設 timeout 的實驗與 pytest 各凍死一次（後者 95 分鐘）。
    ⇒ 「卡住」在本檔一律是**可觀察的結果**（`HANG_RC`），不是無限等待。
    """
    mut = _mutated_lex(tmp_path, "empty_guard", 'if (c2 != "") {', "if (1) {")
    work = tmp_path / "w_guard"
    for line in _mutation_cases():
        base = _preprocess_bytes(line, GATE_LEX, work)
        got = _preprocess_bytes(line, mut, work)
        assert base[0] != HANG_RC, f"基準版不得卡住：{line!r}"
        if got != base:
            return
    pytest.fail("拿掉空字串保護後行為完全不變 ⇒ 該保護無覆蓋，或它根本不承重")


def test_c5_mut_direct_substr_blows_threshold(tmp_path: Path) -> None:
    """把視窗存取還原成直接 substr ⇒ 500K 必須顯著變慢。

    🔴 這條的存在理由：若沒有它，①的門檻可能是在量 subprocess 啟動成本之類
       與修法無關的東西，改壞了也照樣綠。
    用**相對倍數**而非絕對秒數，避免綁死機器速度。
    """
    mut = _mutated_lex(
        tmp_path,
        "direct_substr",
        "      WIN_AT(pos)\n      return substr(_win, pos - _wbase + 1, 1)",
        "      return substr(src, pos, 1)",
    )
    body = "\\" * 500_000  # 反斜線：每個字元都得逐字處理，最能放大 substr 成本
    cmd = f'echo "{body}"'

    _, t_base = _decide(cmd, tmp_path / "mb")
    _, t_mut = _decide(cmd, tmp_path / "mm", lex_path=mut)

    assert t_base < C5_500K_SEC, f"基準版已逾門檻 {t_base:.2f}s，本測試前提不成立"
    assert t_mut > t_base * 3, (
        f"還原成直接 substr 後未顯著變慢（base={t_base:.2f}s mut={t_mut:.2f}s）"
        " ⇒ 效能斷言沒有量到修法本身"
    )
