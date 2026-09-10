"""SPLITUNIFY B2b 自查：負向注入掃描（主委版，與三家平行）。

出生理由（B2b review R1 之教訓）：H1／H2／H3 三條**讀碼看不出來**——契約本身沒寫
「要檢查身份」，只有 codex **主動餵壞資料**才現形。⇒ 這一類必須靠負向注入，不能靠對照。

逐條列出「餵什麼壞資料 → 期望被擋 → 實際如何」。**未擋不代表一定是 bug**，
但一定要被看見並具名裁定（擋／不擋／不適用）。
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.split_projection import (
    build_time_clusters,
    derive_event_split_from_plans,
)
from momentum.Analysis.event_samples.types import EventManifest
from momentum.core.contracts import SplitPlan
from momentum.core.split_preview import holdout_boundary

H1 = 3_600_000
BASE = 1_700_000_000_000
N = 100
SYM = "ETHUSDT"


def _index(n: int = N) -> pd.Index:
    return pd.Index([BASE + i * H1 for i in range(n)], dtype="int64")


def _plans(index, symbol=SYM):
    b = holdout_boundary(index, oos_test_size=0.3, purge_gap=2, embargo=2)
    kw = dict(index_kind="positional", purge_gap=2, embargo=2, purge_semantic="rows",
              base_universe_hash="x", symbol=symbol)
    tr = SplitPlan(split_label="train", row_index=b["train_row_index"],
                   time_bounds=(int(index[0]), int(index[b["train_row_index"][-1]])), **kw)
    te = SplitPlan(split_label="test", row_index=b["test_row_index"],
                   time_bounds=(int(index[b["test_row_index"][0]]), int(index[-1])), **kw)
    return tr, te


def _keys(rows):
    return pd.DataFrame([
        {"event_id": e, "feature_cutoff_ms": int(c), "label_start_ms": int(c),
         "label_end_ms": int(le), "symbol": SYM, "timeframe": "1h"}
        for e, c, le in rows
    ])


def _manifest(keys):
    return EventManifest(
        table=pd.DataFrame({
            "event_id": keys["event_id"], "symbol": keys["symbol"],
            "timeframe": keys["timeframe"],
            "decision_at_ms": keys["feature_cutoff_ms"].astype("int64"),
            "label_start_ms": keys["label_start_ms"].astype("int64"),
            "label_end_ms": keys["label_end_ms"].astype("int64"),
        }),
        summary={"n_events_raw": len(keys), "n_events_effective": len(keys)},
        policy={},
    )


def _run(name, fn, *, expect_block: bool):
    try:
        fn()
        blocked, detail = False, "（無例外）"
    except Exception as exc:  # noqa: BLE001 - 探針刻意收所有例外並分類
        blocked, detail = True, f"{type(exc).__name__}: {str(exc)[:90]}"
    mark = "✓" if blocked == expect_block else "✗"
    verdict = "已擋" if blocked else "**未擋**"
    print(f"  {mark} {name}: {verdict} {detail}")
    return blocked == expect_block


def main() -> int:
    index = _index()
    train, test = _plans(index)
    keys = _keys([("a", index[0], int(index[0]) + H1)])
    man = _manifest(keys)
    ok = []

    # ① NaT／NaN 時間戳
    dt = pd.to_datetime(np.asarray(index, dtype="int64"), unit="ms").to_list()
    dt[7] = pd.NaT
    ok.append(_run("① feature_index 含 NaT",
                   lambda: derive_event_split_from_plans(
                       train, test, keys, pd.DatetimeIndex(dt), manifest=man, bucket_ms=H1),
                   expect_block=True))

    # ② event_keys 缺欄
    ok.append(_run("② event_keys 缺 label_end_ms 欄",
                   lambda: derive_event_split_from_plans(
                       train, test, keys.drop(columns=["label_end_ms"]), index,
                       manifest=man, bucket_ms=H1),
                   expect_block=True))

    # ③ row_index 為 float
    # 注：SplitPlan.__post_init__ 自己要求 purge_gap < len(row_index)，故 float 列要夠長。
    bad = SplitPlan(split_label="train", index_kind="positional",
                    row_index=np.asarray([0.5, 1.5, 2.5, 3.5, 4.5]),
                    time_bounds=train.time_bounds,
                    purge_gap=2, embargo=2, purge_semantic="rows",
                    base_universe_hash="x", symbol=SYM)
    ok.append(_run("③ row_index 為 float（0.5..4.5）",
                   lambda: derive_event_split_from_plans(
                       bad, test, keys, index, manifest=man, bucket_ms=H1),
                   expect_block=True))  # R2 之 I4：三家有兩家判該擋，依較嚴版推翻主委原裁定

    # ④ manifest 缺 decision_at_ms
    man_bad = EventManifest(table=man.table.drop(columns=["decision_at_ms"]),
                            summary=man.summary, policy={})
    ok.append(_run("④ manifest 缺 decision_at_ms",
                   lambda: derive_event_split_from_plans(
                       train, test, keys, index, manifest=man_bad, bucket_ms=H1),
                   expect_block=True))

    # ⑤ bucket_ms = 0 / 負值
    ok.append(_run("⑤ bucket_ms = 0",
                   lambda: build_time_clusters(man, 0), expect_block=True))
    ok.append(_run("⑥ bucket_ms = -1",
                   lambda: build_time_clusters(man, -1), expect_block=True))

    # ⑦ label_end_ms < label_start_ms
    inverted = _keys([("a", index[0], int(index[0]) - H1)])
    ok.append(_run("⑦ label_end_ms < label_start_ms",
                   lambda: derive_event_split_from_plans(
                       train, test, inverted, index, manifest=_manifest(inverted),
                       bucket_ms=H1),
                   expect_block=True))

    # ⑧ feature_index 未排序
    shuffled = pd.Index(np.asarray(index, dtype="int64")[::-1])
    ok.append(_run("⑧ feature_index 反序",
                   lambda: derive_event_split_from_plans(
                       train, test, keys, shuffled, manifest=man, bucket_ms=H1),
                   expect_block=True))

    # ⑨ feature_index 有重複值
    dup = np.asarray(index, dtype="int64").copy()
    dup[10] = dup[9]
    ok.append(_run("⑨ feature_index 有重複時間戳",
                   lambda: derive_event_split_from_plans(
                       train, test, keys, pd.Index(dup), manifest=man, bucket_ms=H1),
                   expect_block=True))

    n_bad = sum(1 for v in ok if not v)
    print(f"\n未如預期者 = {n_bad} / {len(ok)}")
    return 1 if n_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
