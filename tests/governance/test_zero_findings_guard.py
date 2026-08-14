"""票 B-48 之產出端綁定：「預期零 findings」標籤不得與實際 findings 矛盾。

為何存在（使用者 2026-08-14T17:10+08:00 核可）：
    該票標題即實例——「`abandon_kind` 宣告『預期零 findings』，該輪卻實收 5 個 findings
    （含 1 個 BLOCKING P0）」。此前該標籤**純靠紀律**，零機械綁定。
    全期實測：180 輪標此 kind，其中 **20 輪標籤不實**，那些 findings 未經處置即結案。

🔴 四條缺一不可：
    · 只驗「該擋的擋了」⇒ 無法排除它恆擋（那會讓所有戳記輪都卡住）
    · 只驗「該放的放了」⇒ 無法排除它恆放（等於沒有閘）
    · sentinel 對照組單獨存在：`## <FAMILY>-R<n>-P3-00` 是**合法的零 findings 表達**，
      誤擋它會逼委員不敢用正確格式。初版判準未排除，把 4 輪合法 sentinel 誤判成不實
    · 逃生口必須落審計：不寫進 audit 的逃生口＝無聲的萬用鑰匙
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUARD_SRC = REPO / "scripts" / "debt_clear.sh"


def _extract_guard(tmp: Path) -> Path:
    """把守衛函式與其常數抽出成可獨立跑的最小腳本。

    🔴 不直接跑 debt_clear.sh：它會先撞 registry／ledger 等一長串前置，
    測不到本閘就先死了。抽出來跑的是**同一份原始碼**（從檔案讀取，非另抄一份），
    故不會出現「測試綠但正式碼是別的邏輯」。
    """
    src = GUARD_SRC.read_text(encoding="utf-8")
    start = src.index("_DC_FINDING_RE=")
    end = src.index("_dc_zero_findings_guard() {")
    body_start = end
    body_end = src.index("\n}\n", body_start) + 3
    sh = tmp / "guard.sh"
    sh.write_text(
        "#!/usr/bin/env bash\nset -u\n"
        + src[start:end]
        + src[body_start:body_end]
        + '\n_dc_zero_findings_guard "$1"\n',
        encoding="utf-8",
    )
    return sh


def _mk_audit(tmp: Path, outputs: dict[str, str]) -> Path:
    """造一筆 committee_round_open，expected_outputs 指向指定檔案。"""
    log = tmp / "audit.log"
    log.write_text(
        json.dumps(
            {
                "event": "committee_round_open",
                "round_id": "R-TEST",
                "expected_outputs": outputs,
                "ts": "2026-08-14T00:00:00Z",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return log


def _run(tmp: Path, log: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(_extract_guard(tmp)), "R-TEST"],
        cwd=str(tmp), capture_output=True, text=True,
        env={"PATH": __import__("os").environ["PATH"], "AUDIT_LOG": str(log)},
    )


@pytest.fixture()
def tree(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "handoffs").mkdir()
    return tmp_path


def test_real_findings_are_blocked(tree: Path) -> None:
    """產出檔含實質 finding ⇒ 擋，且訊息要指出是哪個檔哪一行。"""
    out = tree / "handoffs" / "r-codex.md"
    out.write_text("# x\n\n## CODEX-R2-P1-03\n\n**斷言**: something\n", encoding="utf-8")
    r = _run(tree, _mk_audit(tree, {"codex": "handoffs/r-codex.md"}))
    assert r.returncode != 0, f"有 findings 卻放行 ⇒ 那些 findings 會憑空消失：{r.stdout}{r.stderr}"
    assert "handoffs/r-codex.md:3" in r.stderr, f"未指出具體位置，使用者無從判斷真偽：{r.stderr}"
    assert "--zero-findings-verified" in r.stderr, f"未給出逃生口 ⇒ 死鎖：{r.stderr}"


def test_zero_findings_sentinel_is_allowed(tree: Path) -> None:
    """🔴 對照組：`P3-00` sentinel 是**合法的零 findings 表達**，不得誤擋。

    誤擋它會逼委員不敢用正確格式，反而回到「散文回報」的舊病。
    """
    out = tree / "handoffs" / "r-codex.md"
    out.write_text("# x\n\n## CODEX-R4-P3-00\n\n**斷言**: 本輪未發現需阻擋收斂的 finding\n",
                   encoding="utf-8")
    r = _run(tree, _mk_audit(tree, {"codex": "handoffs/r-codex.md"}))
    assert r.returncode == 0, f"合法 sentinel 被誤擋 ⇒ 委員不敢用正確格式：{r.stdout}{r.stderr}"


def test_clean_output_passes(tree: Path) -> None:
    """對照組：產出檔真的沒有 findings ⇒ 放行（證明本閘非恆擋）。"""
    out = tree / "handoffs" / "r-codex.md"
    out.write_text("# x\n\n沒有發現問題。\n", encoding="utf-8")
    r = _run(tree, _mk_audit(tree, {"codex": "handoffs/r-codex.md"}))
    assert r.returncode == 0, f"乾淨產出被擋 ⇒ 本閘恆擋，所有戳記輪都會卡住：{r.stdout}{r.stderr}"


def test_missing_output_file_does_not_block(tree: Path) -> None:
    """產出檔不存在（handoffs/** 多不進版控）⇒ 不阻擋。

    這是**刻意的**：本閘的判定對象是「檔裡有沒有 findings」，
    檔不在就無從判定，一律判紅會使所有舊輪無法銷帳。
    誠實邊界：此路徑因而擋不到「把產出檔刪掉再結案」——具名，不宣稱防蓄意。
    """
    r = _run(tree, _mk_audit(tree, {"codex": "handoffs/不存在.md"}))
    assert r.returncode == 0, f"檔不存在卻判紅 ⇒ 舊輪全部銷不了帳：{r.stdout}{r.stderr}"


def test_escape_hatch_is_written_to_audit() -> None:
    """🔴 逃生口必須落審計——不寫進 audit 的逃生口是無聲的萬用鑰匙。

    初版只解析旗標、未加入 _emit_abandon 的欄位，等於零防護。
    """
    src = GUARD_SRC.read_text(encoding="utf-8")
    assert "--field \"zero_findings_verified=${ZF_VERIFIED}\"" in src, (
        "逃生口未寫入 audit ⇒ 用了幾次不可查 ⇒ 無法偵測它被當橡皮圖章"
    )


def test_guard_only_applies_to_zero_findings_kind() -> None:
    """本閘只約束 no-findings-expected；其餘 kind 之查核條件不同（票 B-48 明載另議）。"""
    src = GUARD_SRC.read_text(encoding="utf-8")
    assert '[ "${kind}" = "no-findings-expected" ]' in src, "本閘之適用範圍未被限縮，會誤擋其他 kind"
