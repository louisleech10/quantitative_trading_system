"""倍數表逐起點驗證之機械閘（2026-09-30 事故：七項純窗口重指標單項 67–135 CPU 小時，7 程序卡 8 小時無一完成、
監看只看完成數而未察覺）：①開跑前逐項估時，超過上限整批拒跑、不計算不寫表（單程序與平行皆然，審查 r39 codex P1-03）；
②執行中逐項超預算即中止並寫收據（codex P1-04：估時只為下界）；③平行執行中超過上限時間無任何一項完成即中止、終止子程序
並寫收據（codex P1-06）；④純窗口型具名清單不窮舉、K＝窗口長度（codex P1-05）。真實 K 線（BTCUSDT 1d 長歷史）。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_l1_warmup_requirements.py"
LONGHIST = ROOT / "data_cache" / "feature_klines_longhist"

pytestmark = pytest.mark.skipif(not LONGHIST.exists(), reason="需要真實長歷史 K 線 data_cache/feature_klines_longhist")


def _run(tmp_path: Path, *extra: str, workers: str = "2") -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    cmd = [sys.executable, str(SCRIPT), "--exhaustive", "--workers", workers, "--timeframes", "1d",
           "--symbols", "BTCUSDT", "--no-write", "--output", str(tmp_path / "table.yaml"), *extra]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)


@pytest.mark.parametrize("workers", ["1", "2"])
def test_preflight_refuses_over_budget_before_any_computation(tmp_path: Path, workers: str) -> None:
    receipt = tmp_path / "receipt.json"
    proc = _run(tmp_path, "--only", "RSI", "--max-task-cpu-hours", "0.00001", "--receipt", str(receipt),
                workers=workers)
    assert proc.returncode == 2, proc.stdout[-2000:]
    assert "REFUSED 1d BTCUSDT RSI" in proc.stdout
    assert "[progress]" not in proc.stdout and "[measure]" not in proc.stdout  # 拒跑發生於任何計算之前
    assert not (tmp_path / "table.yaml").exists()
    doc = json.loads(receipt.read_text(encoding="utf-8"))
    assert doc["exit_code"] == 2 and [r["indicator"] for r in doc["preflight_refused"]] == ["RSI"]
    assert all({"k", "per_call_s", "starts"} <= set(c) for c in doc["preflight_refused"][0]["cases"])


def test_window_only_analytic_entry_not_exhaustive(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    proc = _run(tmp_path, "--only", "ENT_APEN", "--max-task-cpu-hours", "0.00001", "--receipt", str(receipt))
    assert proc.returncode == 0, proc.stdout[-2000:]  # 純窗口型不估時、不窮舉 ⇒ 不被極小預算擋
    rows = json.loads(receipt.read_text(encoding="utf-8"))["rows"]
    assert rows and all(r["exhaustive"]["skipped"] == "window_only_analytic" for r in rows)
    assert all(r["k"] == int(r["period"]) for r in rows)


def test_stall_aborts_terminates_workers_and_writes_receipt(tmp_path: Path) -> None:
    receipt = tmp_path / "receipt.json"
    proc = _run(tmp_path, "--only", "RSI", "--max-stall-minutes", "0.02", "--receipt", str(receipt))
    assert proc.returncode == 3, proc.stdout[-2000:]
    assert "[STALL]" in proc.stdout and "1d BTCUSDT RSI" in proc.stdout and "STALL_ABORTED" in proc.stdout
    assert not (tmp_path / "table.yaml").exists()
    doc = json.loads(receipt.read_text(encoding="utf-8"))
    assert doc["exit_code"] == 3 and doc["abort"] == "stall" and doc["running"] == ["1d BTCUSDT RSI"]


def test_task_budget_exceeded_raises_during_scan() -> None:
    """執行中預算：deadline 已過 ⇒ 掃描輪第一次檢查即拋（實際耗時之上界，不依估時）。"""
    sys.path.insert(0, str(ROOT))
    import scripts.verify_l1_warmup_requirements as v

    entry = next(e for e in v.build_catalog() if e.name == "RSI")
    frame = v.load_frame("BTCUSDT", "1d")
    with pytest.raises(v.TaskBudgetExceeded):
        v.verify_exhaustive(entry.cases[0], frame, 30, 1000, 0.005, 4000, deadline=time.time() - 1, label="RSI")


RECEIPT = ROOT / "handoffs" / "run_receipts" / "20260930-ffstat-warmup-measure.json"


def _merge(tmp_path: Path, name: str, receipts: list, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    cmd = [sys.executable, str(SCRIPT), "--merge-receipts", *[str(p) for p in receipts], "--timeframes", "1d",
           "--output", str(tmp_path / f"{name}.yaml"), "--receipt", str(tmp_path / f"{name}.json"), *extra]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)


@pytest.mark.skipif(not RECEIPT.exists(), reason="需要倍數量測收據")
def test_merge_is_order_independent_and_conservative(tmp_path: Path) -> None:
    """v55（審查 r40 codex P1-02）：同一實例多份收據衝突時取 K 最大者，與輸入順序無關（真實收據之 1d BTC 子集）。"""
    rows = [r for r in json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]
            if r["timeframe"] == "1d" and r["symbol"] == "BTCUSDT"]
    bumped = [dict(r, k=int(r["k"]) + 7) for r in rows if r["indicator"] == "RSI" and r.get("converged")][:3]
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    b.write_text(json.dumps({"rows": bumped}), encoding="utf-8")
    p1 = _merge(tmp_path, "ab", [a, b], "--symbols", "BTCUSDT")
    p2 = _merge(tmp_path, "ba", [b, a], "--symbols", "BTCUSDT")
    assert p1.returncode == 0 and p2.returncode == 0, (p1.stdout[-800:], p2.stdout[-800:])
    t1 = (tmp_path / "ab.yaml").read_text(encoding="utf-8").split("indicators:", 1)[1]
    t2 = (tmp_path / "ba.yaml").read_text(encoding="utf-8").split("indicators:", 1)[1]
    assert t1 == t2
    merged = {json.dumps([r["indicator"], sorted(r["params"].items()), r.get("source")]): r["k"]
              for r in json.loads((tmp_path / "ab.json").read_text(encoding="utf-8"))["rows"]}
    for r in bumped:
        assert merged[json.dumps([r["indicator"], sorted(r["params"].items()), r.get("source")])] == r["k"]


@pytest.mark.skipif(not RECEIPT.exists(), reason="需要倍數量測收據")
def test_merge_fails_closed_on_missing_symbol_timeframe(tmp_path: Path) -> None:
    """v55（審查 r40 codex P1-03）：要求之（標的, 週期）格缺列 ⇒ exit 5、不寫表、收據列缺格。"""
    rows = [r for r in json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]
            if r["timeframe"] == "1d" and r["symbol"] == "BTCUSDT"]
    a = tmp_path / "a.json"
    a.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    proc = _merge(tmp_path, "m", [a], "--symbols", "BTCUSDT", "ETHUSDT")
    assert proc.returncode == 5, proc.stdout[-800:]
    assert not (tmp_path / "m.yaml").exists()
    doc = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert doc["abort"] == "merge_coverage_missing" and all("ETHUSDT" in m for m in doc["missing"])
