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


def _meta() -> dict:
    """真實量測收據之 meta（判準：容差 0.005、評估窗、評估位置、市場）；合併輸入沿用以通過判準核對（b5）。"""
    return json.loads(RECEIPT.read_text(encoding="utf-8"))["meta"]


def _merge(tmp_path: Path, name: str, receipts: list, *extra: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    meta = _meta()  # 本次判準取真實收據之值（b5：合併核對判準；`extra` 在後可覆寫，argparse 取最後一個）
    criteria = ["--eval-window", str(meta["eval_window_bars"]), "--eval-positions", str(meta["eval_positions"]),
                "--threshold", str(meta["scale_normalized_error_threshold"])]
    cmd = [sys.executable, str(SCRIPT), "--merge-receipts", *[str(p) for p in receipts], "--timeframes", "1d",
           "--output", str(tmp_path / f"{name}.yaml"), "--receipt", str(tmp_path / f"{name}.json"), *criteria,
           *extra]
    return subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)


@pytest.mark.skipif(not RECEIPT.exists(), reason="需要倍數量測收據")
def test_merge_is_order_independent_and_conservative(tmp_path: Path) -> None:
    """v55（審查 r40 codex P1-02）：同一實例多份收據衝突時取 K 最大者，與輸入順序無關（真實收據之 1d BTC 子集）。"""
    rows = [r for r in json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]
            if r["timeframe"] == "1d" and r["symbol"] == "BTCUSDT"]
    bumped = [dict(r, k=int(r["k"]) + 7) for r in rows if r["indicator"] == "RSI" and r.get("converged")][:3]
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps({"meta": _meta(), "rows": rows}), encoding="utf-8")
    b.write_text(json.dumps({"meta": _meta(), "rows": bumped}), encoding="utf-8")
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
    a.write_text(json.dumps({"meta": _meta(), "rows": rows}), encoding="utf-8")
    proc = _merge(tmp_path, "m", [a], "--symbols", "BTCUSDT", "ETHUSDT")
    assert proc.returncode == 5, proc.stdout[-800:]
    assert not (tmp_path / "m.yaml").exists()
    doc = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert doc["abort"] == "merge_coverage_missing" and all("ETHUSDT" in m for m in doc["missing"])


def test_empty_admissible_starts_not_reported_as_passed() -> None:
    """b4 審碼 r1 codex P1-01：可採起點集合為空（2K > n−評估窗）⇒ passed=False、no_admissible_starts=True（零次檢查不得記通過）。"""
    sys.path.insert(0, str(ROOT))
    import scripts.verify_l1_warmup_requirements as v

    entry = next(e for e in v.build_catalog() if e.name == "RSI")
    frame = v.load_frame("BTCUSDT", "1d")
    k = (len(frame) - 1000) // 2 + 10
    ex = v.verify_exhaustive(entry.cases[0], frame, k, 1000, 0.005, 4000)
    assert ex["rounds"][-1]["starts"] == 0
    assert ex["passed"] is False and ex["no_admissible_starts"] is True


@pytest.mark.skipif(not RECEIPT.exists(), reason="需要倍數量測收據")
def test_merge_fails_closed_on_missing_parameter_case(tmp_path: Path) -> None:
    """b4 審碼 r1 codex P1-02：同一指標缺某一參數 case（TR_CVAR alpha=0.05）⇒ exit 5，不以「指標有列」放行。"""
    rows = [r for r in json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]
            if r["timeframe"] == "1d" and r["symbol"] == "BTCUSDT"
            and not (r["indicator"] == "TR_CVAR" and float((r.get("params") or {}).get("alpha", 0)) == 0.05)]
    a = tmp_path / "a.json"
    a.write_text(json.dumps({"meta": _meta(), "rows": rows}), encoding="utf-8")
    proc = _merge(tmp_path, "m", [a], "--symbols", "BTCUSDT")
    assert proc.returncode == 5, proc.stdout[-800:]
    doc = json.loads((tmp_path / "m.json").read_text(encoding="utf-8"))
    assert doc["missing"] and all("TR_CVAR" in m and "0.05" in m for m in doc["missing"])


@pytest.mark.skipif(not RECEIPT.exists(), reason="需要倍數量測收據")
def test_merge_rejects_criteria_mismatch_and_uncheckable_partial_log(tmp_path: Path) -> None:
    """b5（b4 評測 gpt-6.1-sol 反例）：合併不重量，故輸入之量測判準須與本次參數全等——①本次 `--threshold 0.0001`
    而收據為 0.005 ⇒ exit 6、不寫表、收據列不符項；②收據市場與 `--market` 不同 ⇒ exit 6；③收據缺 meta ⇒ exit 6；
    ④續跑檔紀錄無 `criteria`（無從核對）⇒ exit 6；⑤判準全等（含帶 `criteria` 之續跑檔）⇒ exit 0。"""
    rows = [r for r in json.loads(RECEIPT.read_text(encoding="utf-8"))["rows"]
            if r["timeframe"] == "1d" and r["symbol"] == "BTCUSDT"]
    good, other_market, no_meta = tmp_path / "good.json", tmp_path / "market.json", tmp_path / "nometa.json"
    good.write_text(json.dumps({"meta": _meta(), "rows": rows}), encoding="utf-8")
    other_market.write_text(json.dumps({"meta": dict(_meta(), market_scopes=["tw_stock"]), "rows": rows}),
                            encoding="utf-8")
    no_meta.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    cases = {"threshold": ([good], ("--threshold", "0.0001")), "market": ([other_market], ()),
             "no_meta": ([no_meta], ())}
    for name, (inputs, extra) in cases.items():
        proc = _merge(tmp_path, name, inputs, "--symbols", "BTCUSDT", *extra)
        assert proc.returncode == 6, (name, proc.stdout[-800:])
        assert not (tmp_path / f"{name}.yaml").exists(), name
        doc = json.loads((tmp_path / f"{name}.json").read_text(encoding="utf-8"))
        assert doc["abort"] == "merge_criteria_mismatch" and doc["mismatches"], name
    crit = {"threshold": float(_meta()["scale_normalized_error_threshold"]), "eval_window": _meta()["eval_window_bars"],
            "positions": _meta()["eval_positions"], "market": _meta()["market_scopes"][0]}
    legacy, checked = tmp_path / "legacy.jsonl", tmp_path / "checked.jsonl"
    legacy.write_text(json.dumps({"key": "k", "task": ["1d", "BTCUSDT", "RSI"], "rows": []}) + "\n", encoding="utf-8")
    checked.write_text(json.dumps({"key": "k", "task": ["1d", "BTCUSDT", "RSI"], "rows": [],
                                   "criteria": crit}) + "\n", encoding="utf-8")
    proc = _merge(tmp_path, "legacy", [good], "--symbols", "BTCUSDT", "--merge-partial-logs", str(legacy),
                  "--merge-partial-timeframes", "1d")
    assert proc.returncode == 6, proc.stdout[-800:]
    proc = _merge(tmp_path, "ok", [good], "--symbols", "BTCUSDT", "--merge-partial-logs", str(checked),
                  "--merge-partial-timeframes", "1d")
    assert proc.returncode == 0, proc.stdout[-800:]


def test_infinite_values_in_eval_window_never_pass() -> None:
    """b5（Codex 模型評測 gpt-5.6-luna max 反例）：評估窗內 ground truth 或 test 含 ±inf ⇒ 未收斂——
    ①`verify_exhaustive`：P75 下界為 0 時，std 捷徑曾以 inf 尺度把誤差上界算成 0 而回報通過；
    ②`scale_normalized_error`：inf−inf＝NaN 曾經 max 吞掉。兩處皆須回 inf／不通過。
    mutant 紀錄（主委實跑）：拿掉 ② 之判定即紅；拿掉 `error_at` 內之判定仍綠——捷徑未通過時落回 ②，已由 ② 擋下
    （等價 mutant；`error_at` 之判定為捷徑前之防線，保留）。"""
    import numpy as np
    import pandas as pd

    sys.path.insert(0, str(ROOT))
    from scripts import verify_l1_warmup_requirements as v

    def fn(frame):
        if len(frame) == 7:
            return [np.array([1.0, 1.0, np.inf, 1.0, 1.0, 1.0, 1.0])]
        return [np.array([np.nan] + [1.0] * (len(frame) - 1))]

    case = v.Case(params={}, fn=fn, integer=False)
    out = v.verify_exhaustive(case, pd.DataFrame({"x": np.arange(7)}), 1, 5, 0.005, 2)
    assert out["passed"] is False, out
    gt = np.array([1.0, np.inf, 2.0])
    assert v.scale_normalized_error(gt.copy(), gt, False) == np.inf
    assert v.scale_normalized_error(np.array([1.0, 1.0, 2.0]), gt, False) == np.inf
    assert v.scale_normalized_error(np.array([1.0, -np.inf]), np.array([1.0, 2.0]), False) == np.inf
    assert v.scale_normalized_error(np.array([1.0, 2.0]), np.array([1.0, 2.0]), False) == 0.0


def test_resume_refuses_partial_log_with_other_market(tmp_path: Path) -> None:
    """b5 審碼 r1 codex P1-02：續跑檔沿用與正式合併同一判準核對——同腳本、同任務改 `--market` 即不沿用舊紀錄
    （改前鍵不含市場、讀取不核對 criteria，改市場仍 reused 並被本次 metadata 重標）；同市場重跑則沿用。"""
    log = tmp_path / "partial.jsonl"
    env = dict(os.environ, PYTHONPATH=str(ROOT))

    def run(market: str) -> str:
        cmd = [sys.executable, str(SCRIPT), "--symbols", "BTCUSDT", "--timeframes", "1d", "--only", "RSI",
               "--eval-positions", "2", "--workers", "1", "--partial-log", str(log), "--no-write",
               "--market", market]
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        assert proc.returncode == 0, proc.stdout[-800:] + proc.stderr[-800:]
        return proc.stdout

    run("crypto")
    assert log.exists() and log.read_text(encoding="utf-8").strip()
    assert "[resume] reused 1/1" in run("crypto")
    other = run("tw_stock")
    assert "[resume] reused 0/1" in other, other[-800:]
