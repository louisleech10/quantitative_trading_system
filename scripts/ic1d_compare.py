#!/usr/bin/env python3
"""IC 1d golden comparator（Task 0.1 / D-2 / D-11）。

用法:
  python scripts/ic1d_compare.py <before.json> <after.json> \\
      [--allow-add P1,P2] [--allow-change P1,P2] [--allow-remove P1,P2]

路徑語法（D-11 subtree）:
  三個 --allow-* flag 皆為**逗號分隔的字面 path 前綴**；
  一條 allow 路徑涵蓋該節點及其**整棵子樹**（該 path 及所有後代）。
  --allow-change：前綴下 ADDED / REMOVED / CHANGED 皆允許
  （子樹鍵替換，如 factor_attribution 幽靈鍵 → {status,value,reason}）。
  --allow-add / --allow-remove：僅各自涵蓋新增 / 刪除。
  canonical_sha256 為派生 digest，略過 leaf 比對。
  **禁 shell brace 展開**——腳本只收逗號分隔字面路徑
  （實測三組 `{}` 連寫會爆成 251 詞笛卡爾積）。

路徑段編碼（flatten / allow 共用）:
  - **dict key**：以 `.` 銜接，key 內 `\\` / `.` / `[` / `]` 會 escape 成
    `\\\\` / `\\.` / `\\[` / `\\]`
    （例：`{"a.b":1}` → `a\\.b`；`{"x[0]":1}` → `x\\[0\\]`；
    巢狀 `{"a":{"b":1}}` → `a.b`）。
  - **list index**：以 `[i]` 銜接（例：`{"data":[100]}` → `data[0]`），
    **不得**與 dict key `"0"`（`data.0`）撞 path（Bug1）；
    **不得**與含括號 dict key `"x[0]"`（`x\\[0\\]`）撞 path。
  - **路徑碰撞 fail-closed（字元無關）**：flatten 時若同一 path 字串
    由多個結構位置產生 → raise `PathCollisionError`（寧可 raise 不可靜默漏報）。
    不靠「再補一字元 escape」打地鼠；escape 只降低誤觸，碰撞偵測才是底線。
  - **allow 與 escape 對稱（Bug2）**：
    - 明確轉義：`--allow-change 'metrics.return_1d\\.ic'` 精確匹配含點 key。
    - 未轉義：`--allow-change "metrics.return_1d.ic"` 亦會匹配 flatten 後的
      `metrics.return_1d\\.ic`（path 內 `\\.` 可對應 allow 的裸 `.`；
      同理 `\\[` / `\\]` 可對應 allow 的裸 `[` / `]`）。
    - 正常無點 key 的階層路徑（如 B3 的 15 條 allow-remove）仍以 `.` 為分隔，
      語意不變；若同一字面同時可解讀為「含點 key」與「多層無點 key」，
      allow 會涵蓋兩者（白名單略寬，避免靜默失效）。

數值容差: atol=1e-12, rtol=1e-9（float32 放寬）。
NaN↔NaN 視為相等；NaN↔數值 視為變更。

exit:
  0 = 無未白名單差異
  1 = 有差異 / 路徑碰撞（印出違規 path 或碰撞錯誤）
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

# float32 友好容差（SPEC / TODO 寫死）
ATOL = 1e-12
RTOL = 1e-9


class PathCollisionError(ValueError):
    """flatten 時同一 path 字串由多個結構位置產生（fail-closed）。

    字元無關：無論 metachar 是否已 escape，只要 path 碰撞即 raise，
    禁止 comparator 靜默合併而漏報結構差異。
    """


def _parse_path_list(raw: Optional[str]) -> list[str]:
    """解析逗號分隔字面路徑；空字串 → []。不展開 brace。

    保留使用者輸入中的 `\\.` / `\\\\` / `\\[` / `\\]`（與 flatten escape 對稱）；
    不在此強制 re-escape 整段——階層 `.` 與 key 內 metachar 的對應
    由 `path_in_subtree_allowlist` 做對稱匹配。
    """
    if raw is None:
        return []
    text = str(raw).strip()
    if not text:
        return []
    # 防 brace：若含 `{` 直接拒（避免 shell 未展開殘片或誤用）
    if "{" in text or "}" in text:
        raise SystemExit(
            "FAIL: brace `{}` is forbidden in --allow-* paths; "
            "pass comma-separated literal paths (D-11 / ADV-GROK-1)"
        )
    parts = [p.strip() for p in text.split(",")]
    return [p for p in parts if p]


def _escape_path_segment(key: Any) -> str:
    """將 dict key 編碼為 path 段（escape 結構 metachar）。

    字面 key 內的 `\\` / `.` / `[` / `]` 先 escape，避免：
    - `{"a.b":1}` 與巢狀 `{"a":{"b":1}}` 撞 path（A2）
    - `{"x[0]":1}` 與 list `{"x":[1]}` 撞 path（B0 rem3）
    list index **不**走此函式，改用字面 `[i]`（Bug1）。
    注意：escape  alone 無法覆蓋未來所有 metachar；碰撞偵測才是底線。
    """
    text = str(key)
    # 順序：先 `\\`，再結構字元，避免二次 escape 互相污染
    return (
        text.replace("\\", "\\\\")
        .replace(".", "\\.")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def _absorb_leaves(target: dict[str, Any], source: dict[str, Any]) -> None:
    """合併子樹 leaf；path 已存在 → fail-closed raise（字元無關碰撞偵測）。"""
    for p, v in source.items():
        if p in target:
            raise PathCollisionError(
                f"路徑 {p!r} 由多個結構位置產生,comparator 無法安全編碼"
            )
        target[p] = v


def flatten_leaves(obj: Any, *, path: str = "") -> dict[str, Any]:
    """遞迴 flatten JSON 成 {path: leaf_value}。

    空 dict / 空 list 視為葉（保留結構差異可偵測）。
    - dict：path 段以 `.` 連接；key 內 `.` / `\\` / `[` / `]` 已 escape。
    - list：index 以 `[i]` 連接（`data[0]`），與 dict key `data.0` 不碰撞（Bug1）。
    - 任一 path 字串若由多個結構位置產生 → raise PathCollisionError（fail-closed）。
    """
    out: dict[str, Any] = {}
    if isinstance(obj, dict):
        if not obj:
            leaf_path = path if path else ""
            out[leaf_path] = {}
            return out
        for k, v in obj.items():
            seg = _escape_path_segment(k)
            child = f"{path}.{seg}" if path else seg
            _absorb_leaves(out, flatten_leaves(v, path=child))
        return out
    if isinstance(obj, list):
        if not obj:
            leaf_path = path if path else ""
            out[leaf_path] = []
            return out
        for i, v in enumerate(obj):
            # Bug1：list index 用 [i]，避免與 dict key "0" 的 data.0 碰撞
            child = f"{path}[{i}]" if path else f"[{i}]"
            _absorb_leaves(out, flatten_leaves(v, path=child))
        return out
    leaf_path = path if path else ""
    out[leaf_path] = obj
    return out


def _path_matches_allow_prefix(path: str, prefix: str) -> bool:
    """判斷 flatten path 是否落在 allow prefix 的 subtree 內。

    對稱規則（Bug2 + bracket escape）:
    - path 來自 flatten（含 `\\.` / `\\\\` / `\\[` / `\\]` / 結構 `[i]`）
    - prefix 可為未 escape 的使用者字面（`metrics.return_1d.ic`）
      或已 escape 字面（`metrics.return_1d\\.ic`）
    - path 的 `\\.` 可對應 prefix 的 `.` 或 `\\.`
    - path 的 `\\\\` 可對應 prefix 的 `\\` 或 `\\\\`
    - path 的 `\\[` / `\\]` 可對應 prefix 的 `[` / `]` 或 `\\[` / `\\]`
    - path 的裸 `.` / `[` 為結構銜接，須與 prefix 對應字元一致
    - 前綴耗盡後：path 亦耗盡（exact），或下一個結構銜接為 `.` / `[`（後代）
    """
    if not prefix:
        return False
    # 快速路徑：字面已完全一致（含明確 escape 的 allow）
    if path == prefix:
        return True
    if path.startswith(prefix + ".") or path.startswith(prefix + "["):
        return True

    i = 0
    j = 0
    n_path = len(path)
    n_pref = len(prefix)
    while i < n_path and j < n_pref:
        # path 跳脫序列
        if path[i] == "\\" and i + 1 < n_path:
            nxt = path[i + 1]
            if nxt == ".":
                # `\\.` → allow 的 `.` 或 `\\.`
                if j + 1 < n_pref and prefix[j] == "\\" and prefix[j + 1] == ".":
                    i += 2
                    j += 2
                    continue
                if prefix[j] == ".":
                    i += 2
                    j += 1
                    continue
                return False
            if nxt == "\\":
                # `\\\\` → allow 的 `\\` 或 `\\\\`
                if j + 1 < n_pref and prefix[j] == "\\" and prefix[j + 1] == "\\":
                    i += 2
                    j += 2
                    continue
                if prefix[j] == "\\":
                    i += 2
                    j += 1
                    continue
                return False
            if nxt in ("[", "]"):
                # `\\[` / `\\]` → allow 的裸括號或已 escape 括號
                if j + 1 < n_pref and prefix[j] == "\\" and prefix[j + 1] == nxt:
                    i += 2
                    j += 2
                    continue
                if prefix[j] == nxt:
                    i += 2
                    j += 1
                    continue
                return False
            # 其他 `\\X`：要求 prefix 同樣兩字元
            if j + 1 < n_pref and prefix[j] == "\\" and prefix[j + 1] == nxt:
                i += 2
                j += 2
                continue
            return False

        # 雙邊結構銜接或普通字元必須一致
        if path[i] != prefix[j]:
            return False
        i += 1
        j += 1

    if j != n_pref:
        # allow 前綴未耗盡
        return False
    if i == n_path:
        return True
    # 後代：下一個必須是結構銜接（dict `.` 或 list `[`）
    return path[i] in (".", "[")


def path_in_subtree_allowlist(path: str, allow_prefixes: Iterable[str]) -> bool:
    """subtree 語意：path 等於 prefix 或為 prefix 的後代。

    allow 前綴可為字面 nested path（未/已 escape）；與 flatten path
    的對稱匹配見 `_path_matches_allow_prefix`（Bug2）。
    list 子節點以 `[` 銜接，亦視為後代（Bug1）。
    """
    for prefix in allow_prefixes:
        if _path_matches_allow_prefix(path, prefix):
            return True
    return False


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, (int, float))


def _is_nan(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isnan(float(value))
    return False


def values_equal(before: Any, after: Any, *, atol: float = ATOL, rtol: float = RTOL) -> bool:
    """數值容差比對；NaN↔NaN 相等；NaN↔數值 不相等。

    A1：bool 與非 bool（int/float 等）型別不符一律視為變更
    （避免 Python `True == 1` 漏報 consumer_deny/concentrated 等欄）。
    """
    # A1：bool 與非 bool 不得因 True==1 被視為相等
    if isinstance(before, bool) != isinstance(after, bool):
        return False
    if _is_nan(before) and _is_nan(after):
        return True
    if _is_nan(before) or _is_nan(after):
        return False
    if _is_number(before) and _is_number(after):
        b = float(before)
        a = float(after)
        if not math.isfinite(b) or not math.isfinite(a):
            # inf ↔ inf 同號視為相等；inf ↔ 數值 / 異號 inf 視為變更
            if math.isinf(b) and math.isinf(a):
                return (b > 0) == (a > 0)
            return False
        return abs(a - b) <= atol + rtol * abs(b)
    return before == after


# 由 golden 其餘確定性內容派生的 digest；內容合法變更時必變。
# 不參與 leaf 比對（否則 allow-change 子樹替換永遠被 hash 拖紅）。
_DERIVED_COMPARE_SKIP_PATHS: frozenset[str] = frozenset({"canonical_sha256"})


def compare_payloads(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    allow_add: Iterable[str] = (),
    allow_change: Iterable[str] = (),
    allow_remove: Iterable[str] = (),
    atol: float = ATOL,
    rtol: float = RTOL,
) -> list[str]:
    """回傳違規 path 字串清單；空 = PASS。

    allow-change 語意（D-11 / Phase 3 子樹替換）:
      前綴下**任一** leaf 的 ADDED / REMOVED / CHANGED 皆允許
      （例：factor_attribution 整棵從幽靈鍵換成 {status,value,reason}）。
    allow-add / allow-remove 仍只各自涵蓋新增 / 刪除。
    canonical_sha256 為派生 digest，略過比對。
    """
    allow_add_l = list(allow_add)
    allow_change_l = list(allow_change)
    allow_remove_l = list(allow_remove)

    before_leaves = flatten_leaves(before)
    after_leaves = flatten_leaves(after)

    # 去掉空 path（根為空 dict 時）+ 派生 digest
    before_leaves = {
        p: v
        for p, v in before_leaves.items()
        if p and p not in _DERIVED_COMPARE_SKIP_PATHS
    }
    after_leaves = {
        p: v
        for p, v in after_leaves.items()
        if p and p not in _DERIVED_COMPARE_SKIP_PATHS
    }

    violations: list[str] = []
    all_paths = sorted(set(before_leaves) | set(after_leaves))

    for path in all_paths:
        in_b = path in before_leaves
        in_a = path in after_leaves

        if in_a and not in_b:
            # allow-add 或 allow-change（子樹結構替換）皆可
            if not (
                path_in_subtree_allowlist(path, allow_add_l)
                or path_in_subtree_allowlist(path, allow_change_l)
            ):
                violations.append(f"+ ADDED {path} = {after_leaves[path]!r}")
            continue

        if in_b and not in_a:
            # allow-remove 或 allow-change（子樹結構替換）皆可
            if not (
                path_in_subtree_allowlist(path, allow_remove_l)
                or path_in_subtree_allowlist(path, allow_change_l)
            ):
                violations.append(f"- REMOVED {path} = {before_leaves[path]!r}")
            continue

        bv = before_leaves[path]
        av = after_leaves[path]
        if not values_equal(bv, av, atol=atol, rtol=rtol):
            if not path_in_subtree_allowlist(path, allow_change_l):
                violations.append(f"~ CHANGED {path}: before={bv!r} after={av!r}")

    return violations


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"FAIL: {path} root must be object/dict, got {type(data).__name__}")
    return data


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="IC 1d golden comparator (subtree allowlists, D-11)"
    )
    parser.add_argument("before", type=Path, help="before baseline JSON")
    parser.add_argument("after", type=Path, help="after baseline JSON")
    parser.add_argument(
        "--allow-add",
        default="",
        help="comma-separated literal path prefixes allowed to be added (subtree)",
    )
    parser.add_argument(
        "--allow-change",
        default="",
        help="comma-separated literal path prefixes allowed to change (subtree)",
    )
    parser.add_argument(
        "--allow-remove",
        default="",
        help="comma-separated literal path prefixes allowed to be removed (subtree)",
    )
    args = parser.parse_args(argv)

    if not args.before.is_file():
        print(f"FAIL: before not found: {args.before}", file=sys.stderr)
        return 1
    if not args.after.is_file():
        print(f"FAIL: after not found: {args.after}", file=sys.stderr)
        return 1

    try:
        allow_add = _parse_path_list(args.allow_add)
        allow_change = _parse_path_list(args.allow_change)
        allow_remove = _parse_path_list(args.allow_remove)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    before = load_json(args.before)
    after = load_json(args.after)

    try:
        violations = compare_payloads(
            before,
            after,
            allow_add=allow_add,
            allow_change=allow_change,
            allow_remove=allow_remove,
        )
    except PathCollisionError as exc:
        # fail-closed：路徑碰撞不可靜默 PASS
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    if not violations:
        print("PASS: no unallowed differences")
        print(f"before={args.before}")
        print(f"after={args.after}")
        print(f"allow_add={allow_add}")
        print(f"allow_change={allow_change}")
        print(f"allow_remove={allow_remove}")
        return 0

    print(f"FAIL: {len(violations)} unallowed difference(s)", file=sys.stderr)
    for line in violations:
        print(line, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
