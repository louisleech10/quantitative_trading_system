#!/usr/bin/env python
"""Task 0.2（重做版）：`ASSUME-2` 之**改前基線** —— 切分計畫之完整指紋。

    venv/bin/python handoffs/20260907-probe-split-baseline.py [--write]

## 為什麼重做（R2 三家獨立命中）

首版只記六個標量欄位。`CODEX-R2-P1-05`／`COMPOSER-R2-P1-03`／`GROK-R2-P1-02`：
「六欄位在**端點不變但中段列被刪**時全部不變」⇒ 不足以偵測切分漂移。
首版 golden（`sha256 = f01550db…`）已作廢。本版加：
- `split_row_fingerprint`：train／test **列索引集合**之 sha256（中段少一列就變）
- `retained_event_ids`：一組固定事件在 train／test 各保留哪些 id（事件路徑之保留集合）
- **預載 labels 路徑**之案例（`labels_df` 非 None）——那是 B 的第二個呼叫點（stage0 `:2790`）
  所依賴的 horizon 解析路徑

## 🔴 誠實邊界
- 呼叫的是 `_build_holdout_split_plan`（純函式）＋ `_resolve_effective_label_horizon`，
  **不跑完整 analyze**（8 GB 機器上十分鐘級）⇒ 覆蓋切分計畫本身，不覆蓋 stage1 之後。
- `retained_event_ids` 以「事件 timestamp ∈ 該段列之時間集合」機械導出，
  **不是**跑真實 `_run_event_label_stages`（那需要事件批＋K 線快取）。
- `embargo` 以參數化涵蓋，不等於跑過真實事件批之 `purge_rows` 注入。
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

OUT = REPO / "tests" / "golden" / "evtalign" / "split_baseline.json"
DEFAULT_HORIZON = 5  # config/ic_config.yaml 之 global.default_horizon


def _make_config(horizon: int, embargo: int, oos_test_size: float = 0.2,
                 min_test_rows: int = 20):
    from types import SimpleNamespace

    return SimpleNamespace(
        oos_test_size=oos_test_size,
        embargo=embargo,
        min_test_rows=min_test_rows,
        labels=SimpleNamespace(horizons=[horizon], return_type="log"),
        global_settings=SimpleNamespace(default_horizon=DEFAULT_HORIZON),
    )


def _fingerprint(rows) -> str:
    return hashlib.sha256(",".join(str(int(r)) for r in rows).encode()).hexdigest()


def _events(idx: pd.DatetimeIndex) -> dict[str, pd.Timestamp]:
    """固定一組事件（每 37 根一個），id 可重現。"""
    return {f"ev{k:03d}": idx[i] for k, i in enumerate(range(3, len(idx), 37))}


def _case(name: str, n_rows: int, horizon: int, embargo: int, *, preload_labels: bool) -> dict:
    from momentum.Analysis.ic_filter_orchestrator import (
        SkippedResult,
        _build_holdout_split_plan,
        _resolve_effective_label_horizon,
    )

    # tz-naive：對齊真實管線（EA-RESID-3：tz-aware 會讓 _validate_expected_frequency 拋 TypeError）
    idx = pd.date_range("2024-01-01", periods=n_rows, freq="1h")
    features = pd.DataFrame({"f0": np.arange(n_rows, dtype=float)}, index=idx)
    config = _make_config(horizon, embargo)

    # 預載 labels 路徑（stage0 `:2790` 依賴之 horizon 解析）：欄名決定 horizon
    labels_df = (pd.DataFrame({f"return_{horizon}": np.zeros(n_rows)}, index=idx)
                 if preload_labels else None)
    try:
        eff_h = int(_resolve_effective_label_horizon(config, labels_df))
        result = _build_holdout_split_plan(
            features, config, "ETHUSDT", pd.Timedelta("1h"),
            purge_gap=eff_h, labels_df=labels_df,
        )
    except Exception as exc:  # noqa: BLE001  失敗本身也是基線
        return {"case": name, "status": "error", "error": f"{type(exc).__name__}: {exc}"}

    if isinstance(result, SkippedResult):
        return {"case": name, "status": "skipped",
                "reason": getattr(result, "reason", str(result)),
                "details": getattr(result, "details", None)}

    train_plan, test_plan = result
    tr_rows, te_rows = list(train_plan.row_index), list(test_plan.row_index)
    tr_ts, te_ts = set(idx[tr_rows]), set(idx[te_rows])
    events = _events(idx)
    return {
        "case": name,
        "status": "ok",
        "horizon_source": "column_parse" if preload_labels else "config_default",
        "effective_horizon": eff_h,
        "purge_gap": int(train_plan.purge_gap),
        "embargo": int(train_plan.embargo),
        "train_rows": len(tr_rows),
        "test_rows": len(te_rows),
        "train_time_bounds": [str(v) for v in train_plan.time_bounds],
        "test_time_bounds": [str(v) for v in test_plan.time_bounds],
        # 🔴 重做版新增：中段少一列就變
        "split_row_fingerprint": {"train": _fingerprint(tr_rows), "test": _fingerprint(te_rows)},
        # 🔴 重做版新增：事件在切分計畫下的保留集合
        "retained_event_ids": {
            "train": sorted(k for k, ts in events.items() if ts in tr_ts),
            "test": sorted(k for k, ts in events.items() if ts in te_ts),
            "dropped": sorted(k for k, ts in events.items() if ts not in tr_ts and ts not in te_ts),
        },
    }


REQUIRED = ("effective_horizon", "purge_gap", "embargo", "train_rows", "test_rows",
            "train_time_bounds", "test_time_bounds", "split_row_fingerprint", "retained_event_ids")


def main() -> int:
    write = "--write" in sys.argv
    cases = []
    for horizon in (2, DEFAULT_HORIZON, 12):
        for embargo in (0, 12):
            cases.append(_case(f"h{horizon}_emb{embargo}_n500", 500, horizon, embargo, preload_labels=False))
    # stage0 預載 labels 路徑：horizon 由欄名解析，h≠default 時尤其要釘
    for horizon in (2, 12):
        cases.append(_case(f"preload_h{horizon}_emb0_n500", 500, horizon, 0, preload_labels=True))
    cases.append(_case("h5_emb0_n40_insufficient", 40, DEFAULT_HORIZON, 0, preload_labels=False))

    ok = [c for c in cases if c["status"] == "ok"]
    print(f"組合數 = {len(cases)}（ok={len(ok)}、skipped={sum(c['status']=='skipped' for c in cases)}、"
          f"error={sum(c['status']=='error' for c in cases)}）\n")
    bad = []
    for c in cases:
        if c["status"] == "ok":
            missing = [k for k in REQUIRED if k not in c]
            if missing:
                bad.append((c["case"], missing))
            r = c["retained_event_ids"]
            print(f"  {c['case']:<28} h={c['effective_horizon']:>2}({c['horizon_source'][:6]}) "
                  f"purge={c['purge_gap']:>2} emb={c['embargo']:>2} train={c['train_rows']} "
                  f"test={c['test_rows']:>3} ev(tr/te/drop)={len(r['train'])}/{len(r['test'])}/{len(r['dropped'])} "
                  f"fp={c['split_row_fingerprint']['test'][:8]}")
        else:
            print(f"  {c['case']:<28} {c['status']}: {str(c.get('reason') or c.get('error'))[:60]}")
    if bad:
        print(f"\n🔴 缺必填欄位：{bad}"); return 1
    if len(ok) < 6:
        print(f"\n🔴 ok 組合數 {len(ok)} < 6"); return 1
    if not any(c.get("horizon_source") == "column_parse" for c in ok):
        print("\n🔴 缺預載 labels（stage0）路徑之案例"); return 1

    payload = json.dumps({"cases": cases}, ensure_ascii=False, sort_keys=True, indent=1)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    print(f"\nsha256 = {digest}")
    if write:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(payload + "\n", encoding="utf-8")
        print(f"已寫入 {OUT.relative_to(REPO)}")
    elif OUT.is_file():
        cur = hashlib.sha256(OUT.read_text(encoding="utf-8").rstrip("\n").encode()).hexdigest()
        print(f"與既有 golden 相同？ **{cur == digest}**")
        return 0 if cur == digest else 1
    else:
        print("（尚無 golden；加 --write 產生）")
    print("\n🔴 誠實邊界：純函式層基線；不跑完整 analyze；事件保留集合為機械導出，非真實事件批路徑。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
