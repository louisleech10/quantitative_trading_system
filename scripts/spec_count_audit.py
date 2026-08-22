"""SPEC 驗收欄之「計數字面」稽核（SPEC-COUNT-DRIFT，2026-08-23）。

病根（量化事實）：GAP-3 UAT 缺口 SPEC 之 R6 十五條中，**6 條為主委整合時自傷**，
其中 3 條形態完全相同——**SPEC 寫死了一個計數，而它所計之物後來變了**：

  · R6 群集 A：`pathExclusions` 由 1 筆擴為 3 筆，驗收欄仍寫「該常數之筆數 `=== 1`」
    （COMPOSER-R6-P1-01／GROK-R6-P0-01 兩家獨立命中）
  · R6 群集 B：批次維度六改五，Task 7.6 驗收仍寫「detail 回應含**六個鍵**」
    （CODEX／COMPOSER／GROK 三家全員命中）
  · R6 群集 F：機械閘由三支增為四支，receipt 產生器仍寫「三支機械閘」
    （COMPOSER-R6-P2-01）

三條皆非判斷錯誤，是**字面沒跟著動**。使用者 2026-08-23 裁定：主委直接修 ＋ 做成機械閘。

🔴 **為何是 Python 而非 shell**：首版寫成 `scripts/spec_count_audit.sh`，以 awk 之
`[一二三四五六七八九十兩0-9]+` 字元類別比對中文——**macOS 之 BWK awk 不是 UTF-8 aware，
會逐位元組比對** ⇒ 輸出中文被咬碎（`\xe5\x85\x83組`）、且 `筆數 === 1` 之 mutation
**未能轉紅**（假綠）。主委實跑 mutation 才發現，未留該版。此坑與 CLAUDE.md 之
「`stat -f %m` 在 linux 失敗」同類：**shell 文字工具對非 ASCII 不可靠**。

設計（feedback_mechanize_dont_police_prose：封閉集合，不做語意判斷）：
只掃**驗收語境**（`- 驗證` bullet 及其續行）之計數字面，量詞限縮為指涉
「SPEC 內可列舉之物」者。本閘**不知道正確數字**，只保證計數字面一旦變動，
作者必須重新看過它所計之物。

🔴 誠實邊界（不得誇大）：
  1. 不知道正確數字；作者複核後仍寫錯，本閘擋不住 ⇒ 交 adversarial review。
  2. 只掃驗收語境；正文散文之計數不在涵蓋面。
  3. **正解仍是「不要寫計數字面」**——改用集合相等斷言（R6 群集 A／B 即如此修）。
     本閘是給「真的必須寫數字」處的最後一道網，不是鼓勵寫計數。

用法：
    python3 scripts/spec_count_audit.py --list  <SPEC.md>
    python3 scripts/spec_count_audit.py --check <SPEC.md> <基準檔>
rc: 0=無變動；2=有新增／改變／消失之計數字面
"""

import io
import re
import sys

# 量詞封閉集合：指涉 SPEC 內可列舉之物者。
# 🔴 刻意排除「家」（委員家數，屬敘事非斷言）與「條」（測試條目數，本就常動且已有 ≥N 語義）。
_UNITS = r"(?:個鍵|支閘|支機械閘|個維度|維度|筆|個值|個頂層鍵)"
_NUMERALS = r"[一二三四五六七八九十兩0-9]+"
_COUNT_WORD = r"(?:筆數|長度|個數|數量|元素數|鍵數)"

_RE_NUM_UNIT = re.compile(_NUMERALS + _UNITS)
_RE_COUNT_ASSERT = re.compile(_COUNT_WORD + r"[^0-9\n]{0,12}[=＝]{1,3}\s*[0-9]+")

# 非計數之「一」：任一／每一／唯一／任一維度…
_NOISE = re.compile(r"任一|每一|唯一|同一|其一")

_TASK = re.compile(r"^\*\*Task ([0-9]+\.[0-9]+[a-z]?)")
_SSEC = re.compile(r"^\*\*(S-[0-9]+[a-z]?)")
_VSTART = re.compile(r"^- 驗證|^\*\*S-9 之驗收\*\*|^\*\*S-9 之驗收")
_VEND = re.compile(r"^- (?:內容|存活至|覆蓋風險|邊界|不可做)|^\*\*Task |^## ")


def extract(path):
    """回傳 sorted 之 '<ctx>\\t<字面>' 集合。"""
    out = set()
    ctx = "(檔頭)"
    in_verify = False
    for line in io.open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        m = _TASK.match(line)
        if m:
            ctx, in_verify = "Task " + m.group(1), False
        else:
            m2 = _SSEC.match(line)
            if m2:
                ctx = m2.group(1)
        if _VSTART.match(line):
            in_verify = True
        elif _VEND.match(line) and not _VSTART.match(line):
            in_verify = False
        if not in_verify:
            continue
        probe = _NOISE.sub("", line)
        for hit in _RE_NUM_UNIT.findall(probe):
            out.add("%s\t%s" % (ctx, hit))
        for m3 in _RE_NUM_UNIT.finditer(probe):
            out.add("%s\t%s" % (ctx, m3.group(0)))
        for m4 in _RE_COUNT_ASSERT.finditer(probe):
            out.add("%s\t%s" % (ctx, re.sub(r"\s+", " ", m4.group(0))))
    return sorted(out)


def main(argv):
    if len(argv) < 3 or argv[1] not in ("--list", "--check"):
        print(__doc__.rsplit("用法：", 1)[-1], file=sys.stderr)
        return 0
    mode, spec = argv[1], argv[2]
    cur = extract(spec)
    if mode == "--list":
        print("\n".join(cur))
        return 0
    if len(argv) < 4:
        print("ERROR: --check 需要基準檔", file=sys.stderr)
        return 2
    base = [l.rstrip("\n") for l in io.open(argv[3], encoding="utf-8") if l.strip()]
    added = sorted(set(cur) - set(base))
    removed = sorted(set(base) - set(cur))
    if not added and not removed:
        return 0
    print("[spec_count_audit] 🔴 %s 之驗收欄計數字面有變動 ⇒ 請逐條複核它所計之物的實際數"
          % spec, file=sys.stderr)
    if added:
        print("  ── 新增／改變 ──", file=sys.stderr)
        for a in added:
            print("    + " + a, file=sys.stderr)
    if removed:
        print("  ── 消失（確認是刻意移除，非誤刪斷言）──", file=sys.stderr)
        for r in removed:
            print("    - " + r, file=sys.stderr)
    print("\n  病根：R6 十五條中 3 條為「計數字面沒跟著它所計之物一起改」"
          "（pathExclusions 1→3 筆／維度 6→5 個／機械閘 3→4 支）。", file=sys.stderr)
    print("  正解：能改成集合相等斷言的就別寫計數字面；真要寫數字，複核後更新基準：",
          file=sys.stderr)
    print("        python3 scripts/spec_count_audit.py --list %s > %s"
          % (spec, argv[3]), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
