"""TESTSEL I10：全規模研究收據之新鮮度（產品、研究程式或數值環境改了就必須重跑）。

ICPERF ㊺ B⑥／B⑦（虛無拒絕率與檢定力）與 ④(c)（n＝500,000 警示模擬分塊）之全規模驗證已自常規測試移為一次性研究腳本
＋收據（`scripts/icperf_hac45_study.py`、`scripts/icperf_hac_large_n_receipt.py`）。本檔以秒級機械保證收據不過期
（審碼 b2 r2 群集 B）：讀 `handoffs/run_receipts/` 各研究最新之收據，斷言
① 研究程式（研究腳本自身＋被呼叫之測試模組）與受檢產品檔之 sha256 ≡ 現行檔，且研究程式清單須含 REQUIRED_STUDY_CODE；
② 數值環境指紋（python 與 numpy／scipy／pandas／numba 版本）≡ 現行環境（本檔獨立以 importlib.metadata 取）；
③ `ok` 欄存在且為 True。任一不符或缺收據 ⇒ 紅，訊息附重跑命令。
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
from importlib import metadata
from pathlib import Path
from typing import Dict, List, Mapping, Optional

import pytest

REPO = Path(__file__).resolve().parents[3]
RECEIPTS = REPO / "handoffs" / "run_receipts"
LOCK = "lockf <repo>/runs/testsel_full/heavy.lock venv/bin/python scripts/run_watched.py --log <log> -- "
ENV_PACKAGES = ("numpy", "scipy", "pandas", "numba")
HAC45_CODE = ("scripts/icperf_hac45_study.py", "tests/momentum/Analysis/test_icperf_hac45_size.py")

#: 研究 ⇒ (收據檔名樣式, 須列入 study_code_sha256 之研究程式, 重跑命令)
STUDIES: Dict[str, tuple] = {
    "hac45-b6": ("*-icperf-hac45-b6.json", HAC45_CODE,
                 LOCK + "venv/bin/python scripts/icperf_hac45_study.py b6"),
    "hac45-b7": ("*-icperf-hac45-b7.json", HAC45_CODE,
                 LOCK + "venv/bin/python scripts/icperf_hac45_study.py b7"),
    "hac-large-n": ("*-icperf-hac-large-n.json", ("scripts/icperf_hac_large_n_receipt.py",),
                    LOCK + "venv/bin/python scripts/icperf_hac_large_n_receipt.py"),
}


def current_env_fingerprint() -> Dict[str, str]:
    return {"python": platform.python_version(), **{p: metadata.version(p) for p in ENV_PACKAGES}}


def latest_receipt(pattern: str, receipts_dir: Optional[Path] = None) -> Optional[Path]:
    """檔名以 UTC 時戳開頭 ⇒ 字典序最大者為最新；無 ⇒ None。未給目錄 ⇒ 呼叫當下之模組 RECEIPTS（可替換供改壞對照）。"""
    paths = sorted(Path(receipts_dir if receipts_dir is not None else RECEIPTS).glob(pattern))
    return paths[-1] if paths else None


def stale_entries(receipt: Mapping, repo_root: Path) -> List[str]:
    """收據所記之 sha256（product_sha256 與 study_code_sha256）與 repo_root 下現行檔不等者（含檔不存在）。"""
    recorded = dict(receipt.get("product_sha256") or {})
    recorded.update(receipt.get("study_code_sha256") or {})
    out: List[str] = []
    for rel, sha in sorted(recorded.items()):
        p = Path(repo_root) / rel
        cur = hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
        if cur != sha:
            out.append(f"{rel}: 收據 {sha[:12]} ≠ 現行 {cur[:12] if cur else '不存在'}")
    return out


def receipt_problems(receipt: Mapping, required_code, repo_root: Path, env: Mapping[str, str]) -> List[str]:
    """收據不可接受之全部原因（空＝新鮮且通過）。"""
    out: List[str] = []
    if "ok" not in receipt:
        out.append("收據缺 ok 欄")
    elif receipt["ok"] is not True:
        out.append(f"收據 ok＝{receipt['ok']!r}（研究判定未通過）")
    if not receipt.get("product_sha256"):
        out.append("收據未記受檢產品檔 sha256")
    missing = sorted(set(required_code) - set(receipt.get("study_code_sha256") or {}))
    if missing:
        out.append(f"收據未記研究程式 sha256：{missing}")
    rec_env = receipt.get("env_fingerprint")
    if not isinstance(rec_env, Mapping):
        out.append("收據缺數值環境指紋 env_fingerprint")
    elif dict(rec_env) != dict(env):
        diff = {k: (rec_env.get(k), env.get(k)) for k in sorted(set(rec_env) | set(env)) if rec_env.get(k) != env.get(k)}
        out.append(f"數值環境指紋不符（收據, 現行）：{diff}")
    out += stale_entries(receipt, repo_root)
    return out


@pytest.mark.parametrize("study", sorted(STUDIES))
def test_study_receipt_matches_current_product(study: str) -> None:
    pattern, required, rerun = STUDIES[study]
    path = latest_receipt(pattern)
    assert path is not None, f"{study}：缺收據 handoffs/run_receipts/{pattern}；重跑：{rerun}"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    problems = receipt_problems(receipt, required, REPO, current_env_fingerprint())
    assert not problems, f"{study}：收據 {path.name} 不可用 ⇒ 須重跑：{rerun}\n" + "\n".join(problems)


def _tmp_repo_copy(receipt: Mapping, tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    for rel in {**(receipt.get("product_sha256") or {}), **(receipt.get("study_code_sha256") or {})}:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    return root


def _flip_last_byte(p: Path) -> None:
    data = bytearray(p.read_bytes())
    data[-1] ^= 0x01
    p.write_bytes(bytes(data))


@pytest.mark.parametrize("study", sorted(STUDIES))
def test_stale_detection_one_byte_change(study: str, tmp_path: Path) -> None:
    """改壞對照（不動真檔）：受檢產品檔之 tmp 複本改一個位元組 ⇒ 恰報該檔；未改之複本 ⇒ 無問題。"""
    pattern, required, _ = STUDIES[study]
    receipt = json.loads(latest_receipt(pattern).read_text(encoding="utf-8"))
    root = _tmp_repo_copy(receipt, tmp_path)
    env = current_env_fingerprint()
    assert receipt_problems(receipt, required, root, env) == []
    victim = sorted(receipt["product_sha256"])[0]
    _flip_last_byte(root / victim)
    problems = receipt_problems(receipt, required, root, env)
    assert len(problems) == 1 and problems[0].startswith(victim), problems


@pytest.mark.parametrize("study", sorted(STUDIES))
def test_study_script_env_and_ok_mutations_turn_red(study: str, tmp_path: Path) -> None:
    """改壞對照（審碼 b2 r2 群集 B，皆用 tmp 複本／收據副本）：①只改研究腳本一位元組 ⇒ 恰報研究腳本；②只改環境指紋一欄
    ⇒ 報指紋不符；③刪 ok 欄 ⇒ 報缺 ok；④研究程式清單漏研究腳本 ⇒ 報未記。"""
    pattern, required, _ = STUDIES[study]
    receipt = json.loads(latest_receipt(pattern).read_text(encoding="utf-8"))
    env = current_env_fingerprint()
    root = _tmp_repo_copy(receipt, tmp_path)
    script = next(p for p in required if p.startswith("scripts/"))
    _flip_last_byte(root / script)
    problems = receipt_problems(receipt, required, root, env)
    assert len(problems) == 1 and problems[0].startswith(script), problems
    for key in sorted(env):
        bad_env = dict(env, **{key: env[key] + ".mutant"})
        problems = receipt_problems(receipt, required, REPO, bad_env)
        assert len(problems) == 1 and problems[0].startswith("數值環境指紋不符") and key in problems[0], (key, problems)
    no_ok = {k: v for k, v in receipt.items() if k != "ok"}
    assert receipt_problems(no_ok, required, REPO, env) == ["收據缺 ok 欄"]
    no_script = dict(receipt, study_code_sha256={k: v for k, v in receipt["study_code_sha256"].items() if k != script})
    problems = receipt_problems(no_script, required, REPO, env)
    assert len(problems) == 1 and "未記研究程式" in problems[0], problems
