#!/usr/bin/env python3
"""產生 GAP-3 UAT 用的樣本檔（供 `白話說明/GAP-3驗收清單.md` 逐項使用）。

🔴 **所有時間與價格都取自真實 kline**（`data_cache/feature_klines/kline_cache.h5`），
   **不造任何假數字**。本專案禁合成 fixture（CLAUDE.md「資料與數值」）。
   本腳本唯一「編造」的是 `label`（正／反例）——那本來就是**使用者自己聲明**的東西，
   系統從不替使用者判斷；這裡用「未來 h 根報酬的正負」當作一個**你可以自己檢查**的規則，
   並把該規則寫進每個檔的 `_readme` 欄，不讓它變成看不見的魔術。

🔴 **event_id 不在此手寫**：呼叫契約之唯一實作 `import_contract.canonical_event_id()`。
   在這裡自寫第二份公式，就是本 epic 反覆付過代價的副本漂移。

產出（預設寫到 `uat_samples/`）：
  1. `events_ok.json`              新契約 JSON，可直接匯入；事件全在 2024-07 之後
                                   ⇒ 讓「特徵 run 涵蓋期」那項（B18）有雙向可測
  2. `events_mixed_control_kind.json`  同上但批內混兩種 `control_kind`
                                   ⇒ 讓報酬表的「全體組不可算」那條（B16）看得到
  3. `events_mapping.csv`          欄名**故意不是**契約欄名的 CSV ⇒ 練逐欄對映（B9）
  4. `events_legacy_3col.csv`      舊三欄格式 ⇒ 驗舊格式擋得住（B11）

用法：
  venv/bin/python scripts/gen_uat_samples.py            # 產生
  venv/bin/python scripts/gen_uat_samples.py --check    # 只檢查現有樣本是否仍過契約
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from momentum.Analysis.event_samples.import_contract import (  # noqa: E402
    canonical_event_id,
    validate_event_import,
)

KLINE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
OUT_DIR = REPO / "uat_samples"

SYMBOL = "ETHUSDT"
TIMEFRAME = "12h"
#: 事件全部落在這之後——`be993398` 那個 run 只涵蓋到 2024-06-25，
#: 於是「run 涵蓋不到事件期」有真實可測的一側（B18）。
START_UTC = datetime(2024, 7, 1, tzinfo=timezone.utc)
END_UTC = datetime(2025, 12, 31, tzinfo=timezone.utc)
N_EVENTS = 60
#: label 規則：往後第 `LABEL_H` 根 close 相對本根 close 的漲跌。你可以自己用 Excel 驗。
LABEL_H = 3


def _load_bars():
    import h5py
    import numpy as np

    if not KLINE.is_file():
        raise SystemExit(f"找不到真實 kline：{KLINE}（本腳本禁用合成資料）")
    with h5py.File(KLINE, "r") as f:
        arr = f[SYMBOL][TIMEFRAME]["data"][:]
    ts = arr["timestamp"].astype("int64")      # epoch **秒**
    close = arr["close"].astype("float64")
    lo = int(START_UTC.timestamp())
    hi = int(END_UTC.timestamp())
    mask = (ts >= lo) & (ts <= hi)
    idx = np.flatnonzero(mask)
    if len(idx) < N_EVENTS + LABEL_H + 1:
        raise SystemExit(f"該區間之真實 K 線只有 {len(idx)} 根，不足以產 {N_EVENTS} 個事件")
    return ts, close, idx


def _pick(ts, close, idx):
    """等距挑 N 個事件，確保正反例兩類都有（缺任一類 ⇒ 契約 `missing_control_group`）。"""
    step = max(1, (len(idx) - LABEL_H - 1) // N_EVENTS)
    rows = []
    for k in range(N_EVENTS):
        i = int(idx[k * step])
        if i + LABEL_H >= len(close):
            break
        fwd = float(close[i + LABEL_H] - close[i]) / float(close[i])
        rows.append({"t0_s": int(ts[i]), "close": float(close[i]),
                     "fwd": fwd, "label": 1 if fwd > 0 else 0})
    labels = {r["label"] for r in rows}
    if labels != {0, 1}:
        raise SystemExit(f"挑出的樣本只有單一類別 {labels}——契約會以 missing_control_group 拒收")
    return rows


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _record(row: dict, *, control_kind: str, source_digest: str) -> dict:
    t0_ms = row["t0_s"] * 1000
    return {
        "event_id": canonical_event_id(SYMBOL, TIMEFRAME, t0_ms),
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "t0": t0_ms,
        "decision_offset_bars": 0,
        "entry_price_semantic": "trigger_close",
        "direction": "long",
        "scenario": "C",
        "label": row["label"],
        "label_definition": {
            "rule_id": "uat-sample:fwd3-close-sign",
            "canonical_digest": _digest(["uat-sample", "fwd3-close-sign", LABEL_H]),
            "window": {"horizon_bars": LABEL_H},
            "label_return_mode": "close_to_close",
        },
        "control_kind": control_kind,
        "source_file_digest": source_digest,
        "data_snapshot_digest": f"uat-sample:{SYMBOL}:{TIMEFRAME}:kline_cache.h5",
        "lookahead_bars_declared": {TIMEFRAME: LABEL_H},
    }


def _write_json(path: Path, records: list, note: str) -> None:
    payload = {
        "_readme": note,
        "_label_rule": (
            f"label = 1 若 close[t0 + {LABEL_H} 根] > close[t0]，否則 0。"
            f"時間與價格全部取自 {KLINE.relative_to(REPO)} 之真實 K 線，未造假。"
        ),
        "_readme_numbers": (
            f"🔴 **本樣本的數字不可作為結論**：label 就是用第 {LABEL_H} 根的報酬正負定義的，"
            f"所以事件後報酬表在 h={LABEL_H} 那一列，正例組必然為正、反例組必然為負"
            f"——那是定義出來的，不是發現（同義反覆）。有資訊的是 h≠{LABEL_H} 的列。"
            f"本樣本的用途是驗『跑得動、畫面顯示對不對』，不是驗訊號。"
        ),
        "records": records,
        "source_name": path.name,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _flatten(obj: dict, prefix: str = "") -> dict:
    """與 `frontend/src/lib/eventContractCsv.ts::flatten` 同規則：巢狀 → 點路徑。"""
    out: dict = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(v, key))
        else:
            out[key] = v
    return out


def _cell(v: object) -> str:
    """與 `eventContractCsv.ts::cell` 同規則（陣列走 JSON 字面、必要時引用）。"""
    if v is None:
        return ""
    s = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
    return '"' + s.replace('"', '""') + '"' if any(c in s for c in ',"\n\r') else s


def _write_contract_csv(path: Path, records: list, extras: list) -> None:
    """⑤ 契約欄名 CSV：**零對映**可直接上傳，`meta.` 欄留給 Excel 篩選（B9 主路徑）。

    與 `/search`「導出CSV檔案（可回灌）」產出的是同一種格式；這份只是離線備用，
    好讓沒跑搜尋時也能驗 B9。
    """
    rows = []
    for i, rec in enumerate(records):
        flat = _flatten(rec)
        for k, v in extras[i].items():
            flat[f"meta.{k}"] = v
        rows.append(flat)
    names = sorted({k for r in rows for k in r},
                   key=lambda n: (1 if n.startswith("meta.") else 0, n))
    lines = [",".join(names)] + [",".join(_cell(r.get(n)) for n in names) for r in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只驗現有樣本是否仍過契約")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()
    out = Path(args.out)

    if args.check:
        rc = 0
        for name in ("events_ok.json", "events_mixed_control_kind.json"):
            p = out / name
            if not p.is_file():
                print(f"CHECK ✗ 缺 {p}")
                rc = 2
                continue
            recs = json.loads(p.read_text(encoding="utf-8"))["records"]
            try:
                df = validate_event_import(recs)
                print(f"CHECK ✓ {name}：{len(df)} 筆通過契約")
            except Exception as exc:  # noqa: BLE001 —— 顯示 reason 給使用者看
                print(f"CHECK ✗ {name}：{type(exc).__name__} {exc}")
                rc = 2
        return rc

    out.mkdir(parents=True, exist_ok=True)
    ts, close, idx = _load_bars()
    rows = _pick(ts, close, idx)
    src_digest = _digest([SYMBOL, TIMEFRAME, [r["t0_s"] for r in rows]])

    # ① 可直接匯入之新契約 JSON
    ok = [_record(r, control_kind="user_labeled_same_trigger", source_digest=src_digest) for r in rows]
    validate_event_import(ok)          # 🔴 產出前先過契約，不交一份匯不進去的樣本
    _write_json(out / "events_ok.json", ok,
                "GAP-3 UAT 樣本：可直接由 /data-preparation 之「匯入事件（GAP-3 新契約）」上傳。"
                "事件全在 2024-07 之後 ⇒ 可用來驗「特徵 run 涵蓋期」雙向（驗收清單 B18）。")

    # ② 批內混兩種 control_kind ⇒ 報酬表之全體組應顯示 mixed_control_kind_in_batch（B16）
    mixed = []
    for n, r in enumerate(rows):
        kind = "user_labeled_same_trigger" if n % 2 == 0 else "user_labeled_other"
        mixed.append(_record(r, control_kind=kind, source_digest=src_digest))
    validate_event_import(mixed)
    _write_json(out / "events_mixed_control_kind.json", mixed,
                "GAP-3 UAT 樣本：批內故意混兩種 control_kind。匯入並分析後，"
                "事件後報酬表之「全體組」應顯示 not_computed：mixed_control_kind_in_batch，"
                "而正例組與反例組仍正常顯示（驗收清單 B16）。")

    # ③ 欄名故意不是契約欄名 ⇒ 練逐欄對映（B9）
    csv_path = out / "events_mapping.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["幣種", "週期", "進場時間_毫秒", "我的標記", "當根收盤"])
        for r in rows:
            w.writerow([SYMBOL, TIMEFRAME, r["t0_s"] * 1000, r["label"], f"{r['close']:.2f}"])

    # ④ 舊三欄格式 ⇒ 驗舊格式擋得住（B11）
    legacy = out / "events_legacy_3col.csv"
    with legacy.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["symbol", "timestamp", "Positive_case"])
        for r in rows:
            iso = datetime.fromtimestamp(r["t0_s"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            w.writerow([SYMBOL, iso, "True" if r["label"] == 1 else "False"])

    # ⑤ 契約欄名 CSV ⇒ 零對映直接上傳（B9 主路徑；與 /search 匯出同格式）
    _write_contract_csv(
        out / "events_contract.csv",
        ok,
        [{"timestamp": datetime.fromtimestamp(r["t0_s"], tz=timezone.utc)
                              .strftime("%Y-%m-%d %H:%M:%S"),
          "close": f"{r['close']:.2f}"} for r in rows],
    )

    span = (datetime.fromtimestamp(rows[0]["t0_s"], tz=timezone.utc).strftime("%Y-%m-%d"),
            datetime.fromtimestamp(rows[-1]["t0_s"], tz=timezone.utc).strftime("%Y-%m-%d"))
    n_pos = sum(r["label"] for r in rows)
    # 🔴 產出前先讓**後端自己**把這份 CSV 解回契約列並過 validator——
    #    不然交出去的是一份「看起來像契約」但上傳會被拒的檔（B9 就是被這種檔卡住的）。
    import pandas as pd  # noqa: PLC0415 —— 只有這一段要用
    from api.services.case_import_service import EventImportService  # noqa: PLC0415

    parsed = EventImportService()._csv_rows_to_records(
        pd.read_csv(out / "events_contract.csv", dtype=str).where(lambda d: d.notna(), None)
    )
    validate_event_import(parsed)

    print(f"✓ 產生 5 個樣本於 {out}/")
    print(f"  事件 {len(rows)} 筆（正例 {n_pos}／反例 {len(rows) - n_pos}），"
          f"{SYMBOL} {TIMEFRAME}，{span[0]} → {span[1]}")
    print("  events_ok.json / events_mixed_control_kind.json 皆已通過契約 validator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
