"""GAP-3 特徵物化與決策列選取（docs/GAP3_EVENT_TODO.md Task B1.6；R1 X7）。

J3 落地：**連續** per-TF 物化（呼叫既有 Feature Factory，不重實作特徵）→ 每事件以
decision_at per-TF as-of 取列（列指標＝B1.1 per-TF 收據之 row_id，與 V7 row_index
逐列對證）→ 事件×特徵表。杜絕「每案例固定窗」誤實作；NaN 語意不填 0；
per-TF warmup 不足（該 TF 整列 NaN 前綴）⇒ 事件入失敗枚舉 `warmup_insufficient_<tf>`，
禁 NaN 混入（W5：三元輸出含 failures，記帳守恆）。
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from momentum.Analysis.event_samples.types import AlignmentReceipts


def _combined_columns(cols_by_tf: Dict[str, List[str]]) -> List[str]:
    """多 TF 特徵欄名合併；衝突 ⇒ loud 拒（B1.6 邊界②）。"""
    seen: Dict[str, str] = {}
    out: List[str] = []
    for tf, cols in sorted(cols_by_tf.items()):
        for c in cols:
            if c in seen:
                raise ValueError(f"多 TF 特徵欄名衝突：{c}（{seen[c]} vs {tf}）——loud 拒")
            seen[c] = tf
            out.append(c)
    return out


def materialize_features_at_decision(
    receipts: AlignmentReceipts,
    bars_by_tf: Dict[str, Dict[str, pd.DataFrame]],
    feature_config: dict,
    *,
    events: "pd.DataFrame | None" = None,
) -> Tuple[pd.DataFrame, str, pd.DataFrame]:
    """回 (features_at_decision[index=event_id], feature_manifest_hash, failures{event_id,reason})。

    feature_config：{"config_override": FF config（如 {"preset":"minimal"}）,
    "start_date"/"end_date": 選用（足長段物化——結果須與全史一致，測試看住）}。
    events（選用 keyword；同 dedupe 之 context 模式）：驗證後匯入表，提供 symbol。
    """
    from momentum.factories import create_feature_factory, create_feature_reader

    if events is None or "symbol" not in events.columns:
        raise ValueError("materialize_features_at_decision: 需 events= context 提供 symbol（fail-closed）")

    per_tf = receipts.per_tf.merge(events[["event_id", "symbol"]], on="event_id", how="left", validate="many_to_one")
    if per_tf["symbol"].isna().any():
        raise ValueError("materialize_features_at_decision: per-TF 收據存在無 symbol context 之事件")

    ff = create_feature_factory(cache_dir="data_cache/feature_klines")
    reader = create_feature_reader()
    truncated_mode = bool(feature_config.get("start_date") or feature_config.get("end_date"))

    # ---- 連續 per-TF 物化（persist=True 走 V7 artifact；快取命中即秒回）----
    frames: Dict[Tuple[str, str], pd.DataFrame] = {}
    row_ms: Dict[Tuple[str, str], np.ndarray] = {}
    cols_by_tf: Dict[str, List[str]] = {}
    config_hashes: Dict[str, str] = {}
    for (symbol, tf), _g in per_tf.groupby(["symbol", "timeframe"], sort=True):
        res = ff.generate_features(
            symbol, tf,
            config_override=feature_config.get("config_override"),
            persist=True,
            start_date=feature_config.get("start_date"),
            end_date=feature_config.get("end_date"),
        )
        ch = res.metadata["config_hash"]
        config_hashes[f"{symbol}:{tf}"] = ch
        art = reader._get_v2_artifact(reader._resolve_manifest_v2(symbol=symbol, tf=tf, config_hash=ch, artifact_kind="raw")[0], "raw")
        cols = sorted({c for gi in art.get("groups", {}).values() for c in gi.get("columns", [])})
        if not cols:
            raise ValueError(f"materialize: {symbol}/{tf} 無特徵欄（config_override={feature_config.get('config_override')}）")
        df = reader.load_columns_v2(symbol, tf, ch, cols, "raw")
        idx = reader.load_row_index_v2(symbol, tf, ch, "raw")
        if idx is None or len(idx) != len(df):
            raise ValueError(f"materialize: {symbol}/{tf} row_index 缺席或長度不符（fail-closed）")
        frames[(symbol, tf)] = df
        row_ms[(symbol, tf)] = idx.asi8 // 10**6  # ns → ms（bar open_time）
        cols_by_tf.setdefault(tf, cols)

    all_cols = _combined_columns(cols_by_tf)

    # ---- 每事件 as-of 取列（row_id 與 row_index 逐列對證；規則同 D2-1）----
    out_rows: List[dict] = []
    fail_rows: List[dict] = []
    for eid, g in per_tf.groupby("event_id", sort=False):
        row_vals: Dict[str, float] = {}
        failed = None
        for rec in g.to_dict("records"):
            key = (rec["symbol"], rec["timeframe"])
            df = frames[key]
            ms = row_ms[key]
            target = int(rec["last_bar_open_ms"])
            if target > int(ms[-1]):
                raise ValueError(
                    f"materialize: 事件 {eid} 之取列時點晚於物化段末（tf={rec['timeframe']}）——段須涵蓋 decision，loud"
                )
            if target < int(ms[0]):
                failed = f"warmup_insufficient_{rec['timeframe']}"  # 段起點前＝warmup 未涵蓋
                break
            pos = int(np.searchsorted(ms, target))
            if int(ms[pos]) != target:
                raise ValueError(
                    f"materialize: 收據取列時點與 feature row_index 不對證（event={eid} tf={rec['timeframe']}）"
                )
            # CODEX-R1-P1-05：全史模式（無 start/end_date）row_index 與 bar 網格同列 ⇒ **無條件**對證
            # 0 ≤ row_id < len 且 ms[row_id] == target == ms[pos]；截斷段模式（顯式 start/end_date）
            # 網格位移，改以 timestamp 定位（上方 pos 已對證）。
            if not truncated_mode:
                rid = int(rec["row_id"])
                if not (0 <= rid < len(ms)) or int(ms[rid]) != target or pos != rid:
                    raise ValueError(
                        f"materialize: 收據 row_id 與 feature row_index 不對證（event={eid} row_id={rid} target={target}）"
                    )
            vals = df.iloc[pos]
            if not np.isfinite(vals.to_numpy(dtype=float)).all():
                failed = f"warmup_insufficient_{rec['timeframe']}"  # 任一 NaN＝warmup 未完（禁 NaN 混入）
                break
            row_vals.update({c: float(v) if pd.notna(v) else np.nan for c, v in vals.items()})
        if failed is not None:
            fail_rows.append({"event_id": eid, "reason": failed})
        else:
            out_rows.append({"event_id": eid, **row_vals})

    features = pd.DataFrame(out_rows).set_index("event_id") if out_rows else pd.DataFrame(columns=all_cols)
    if len(features):
        features = features.reindex(columns=all_cols)
    failures = pd.DataFrame(fail_rows, columns=["event_id", "reason"])

    # 記帳守恆（W5）：輸入事件數 == 輸出列 + 失敗列
    n_input = per_tf["event_id"].nunique()
    if n_input != len(features) + len(failures):
        raise AssertionError(f"materialize 記帳破缺：{n_input} != {len(features)} + {len(failures)}")

    manifest_hash = hashlib.sha256(
        json.dumps({"columns": all_cols, "config_hashes": config_hashes}, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return features, manifest_hash, failures
