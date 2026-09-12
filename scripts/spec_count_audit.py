"""「計數字面 vs 它所計之物」稽核（SPEC-COUNT-DRIFT，2026-08-23）。

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
**未能轉紅**（假綠）。主委實跑 mutation 才發現；該假綠版一度被 commit 進版控
（且 commit 訊息誤稱「未留」），已另一 commit 刪除並更正。此坑與 CLAUDE.md 之
「`stat -f %m` 在 linux 失敗」同類：**shell 文字工具對非 ASCII 不可靠**。

🔴 **2026-08-23 放寬掃描面（使用者裁）**：首版只掃「SPEC 之驗收欄」，
R7 隨即有 **3 條同型錯誤從縫隙漏出**——`facts.sh` 之「四支機械閘」（不是 SPEC）、
§F-2 之「15 增為 16」（不是驗收欄）、Task 7.7 ①之格式斷言（不是計數但同屬「改一處未同步另一處」）。
**收窄之理由本身是錯的**：本閘為**基準比對**式，噪音只是**一次性成本**
（既有字面收進基準即不再叫），主委卻以「寬集合版命中 408 條」為由收窄，
把一次性成本誤當持續代價。⇒ 改為**掃全檔所有語境**，並支援多檔。

設計（feedback_mechanize_dont_police_prose：封閉集合，不做語意判斷）：
掃**全檔所有語境**之計數字面，量詞限縮為指涉「可列舉之物」者。
本閘**不知道正確數字**，只保證計數字面一旦變動，作者必須重新看過它所計之物。

🔴 誠實邊界（不得誇大）：
  1. 不知道正確數字；作者複核後仍寫錯，本閘擋不住 ⇒ 交 adversarial review。
  2. 掃全檔所有語境（2026-08-23 放寬）；但只認**封閉量詞集合**內之字面，
     用其他寫法表達的計數仍抓不到。
  3. **正解仍是「不要寫計數字面」**——改用集合相等斷言（R6 群集 A／B 即如此修）。
     本閘是給「真的必須寫數字」處的最後一道網，不是鼓勵寫計數。

用法（可傳多檔；基準檔為最後一個參數）：
    python3 scripts/spec_count_audit.py --list  <檔1> [檔2 ...]
    python3 scripts/spec_count_audit.py --check <檔1> [檔2 ...] --baseline <基準檔>
rc: 0=無變動；2=有新增／改變／消失之計數字面
"""

import io
import re
import sys

# 量詞封閉集合：指涉 SPEC 內可列舉之物者。
# 🔴 刻意排除「家」（委員家數，屬敘事非斷言）與裸「條」（測試條目數，本就常動且已有 ≥N 語義）。
_UNITS = r"(?:個鍵|支閘|支機械閘|支|個維度|維度|筆|個值|個頂層鍵|個 reason|條 reason)"
_NUMERALS = r"[一二三四五六七八九十兩0-9]+"
_COUNT_WORD = r"(?:筆數|長度|個數|數量|元素數|鍵數)"

_RE_NUM_UNIT = re.compile(_NUMERALS + _UNITS)
_RE_COUNT_ASSERT = re.compile(_COUNT_WORD + r"[^0-9\n]{0,12}[=＝]{1,3}\s*[0-9]+")

# 🔴 2026-09-12 DOCROT consult R2 之 F2（三家一致，**只收窄版**）：
#   裸「條」仍排除，但「共 N 條」是**宣告總數**的固定語型，與它所列之物必須一致。
#   碼證（本閘原本看不到）：`docs/SPLITUNIFY_SPEC.D-002.md:70` 寫「register 共 29 條」、
#   `:90` 的 register 表標題也寫「共 29 條」——同一個數字兩個真相源，改一處漏一處即漂移；
#   本檔原第 51 行「刻意排除『條』」使該形態零命中（實跑 `--list` 對 D-002 輸出為空）。
#   收窄理由：只綁「共…條」三字語型，不碰「22 條 mutation」「十三條」等敘事用法 ⇒ 誤擋面最小。
_RE_TOTAL_ITEMS = re.compile(r"共\s*" + _NUMERALS + r"\s*條")

# 非計數之「一」：任一／每一／唯一／任一維度…
_NOISE = re.compile(r"任一|每一|唯一|同一|其一")

_TASK = re.compile(r"^\*\*Task ([0-9]+\.[0-9]+[a-z]?)")
_SSEC = re.compile(r"^\*\*(S-[0-9]+[a-z]?)")
_VSTART = re.compile(r"^- 驗證|^\*\*S-9 之驗收\*\*|^\*\*S-9 之驗收")
_VEND = re.compile(r"^- (?:內容|存活至|覆蓋風險|邊界|不可做)|^\*\*Task |^## ")


def extract(path):
    """回傳 sorted 之 '<檔名>|<ctx>\\t<字面>' 集合（掃全檔，不限語境）。"""
    out = set()
    short = path.rsplit("/", 1)[-1]
    ctx = "(檔頭)"
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = _TASK.match(line)
        if m:
            ctx = "Task " + m.group(1)
        else:
            m2 = _SSEC.match(line)
            if m2:
                ctx = m2.group(1)
            elif line.startswith("## "):
                ctx = line[3:].split(" ")[0]
        probe = _NOISE.sub("", line)
        for m3 in _RE_NUM_UNIT.finditer(probe):
            out.add("%s|%s\t%s" % (short, ctx, m3.group(0)))
        for m4 in _RE_COUNT_ASSERT.finditer(probe):
            out.add("%s|%s\t%s" % (short, ctx, re.sub(r"\s+", " ", m4.group(0))))
        for m5 in _RE_TOTAL_ITEMS.finditer(probe):
            out.add("%s|%s\t%s" % (short, ctx, re.sub(r"\s+", " ", m5.group(0))))
    return sorted(out)


def dupes(path):
    """回傳 [(字面, [行號…])]：同一計數字面出現在**兩行以上**者。

    🔴 2026-09-13 DOCROT R2 第 3 項（掛載）之 warn-only 形態：
    `--list`／`--check` 是**集合**比對，同一字面寫在兩處會去重成一筆 ⇒ 看不見
    「同一個數字兩個真相源」。而那正是病根本身：`docs/SPLITUNIFY_SPEC.D-002.md`
    曾把 register 條數同時寫在節標題、表標題、§RISK、§R 回退句與 (5.6) 內文五處，
    改三處漏兩處。本模式不需基準檔、不需維護，只回答「這份文件裡有沒有同一個
    計數字面出現在多行」。
    """
    seen = {}
    for i, line in enumerate(io.open(path, encoding="utf-8", errors="replace"), 1):
        # 🔴 沿革段以下不計：append-only 的歷史**本來就要**逐字保存舊字面
        #   （「原寫 25 條」「v12 補為 29 條」），那是它的職責，不是第二個真相源。
        #   不停在這裡的話，每做一次活文收縮就會永久多一條誤報 ⇒ 閘自己製造噪音。
        if "HISTORY-BEGIN" in line or line.startswith("## 沿革"):
            break
        probe = _NOISE.sub("", line.rstrip("\n"))
        for rx in (_RE_NUM_UNIT, _RE_COUNT_ASSERT, _RE_TOTAL_ITEMS):
            for m in rx.finditer(probe):
                lit = re.sub(r"\s+", " ", m.group(0))
                seen.setdefault(lit, [])
                if i not in seen[lit]:
                    seen[lit].append(i)
    return sorted((k, v) for k, v in seen.items() if len(v) > 1)


def main(argv):
    if len(argv) < 3 or argv[1] not in ("--list", "--check", "--dupes"):
        print(__doc__.rsplit("用法", 1)[-1], file=sys.stderr)
        return 0
    mode = argv[1]
    rest = argv[2:]
    baseline = None
    if "--baseline" in rest:
        i = rest.index("--baseline")
        if i + 1 >= len(rest):
            print("ERROR: --baseline 後須接基準檔", file=sys.stderr)
            return 2
        baseline = rest[i + 1]
        rest = rest[:i] + rest[i + 2:]
    files = [f for f in rest if f]
    if not files:
        print("ERROR: 未指定要掃的檔", file=sys.stderr)
        return 2
    cur = []
    for f in files:
        try:
            cur.extend(extract(f))
        except IOError:
            print("ERROR: 讀不到 %s（fail-closed）" % f, file=sys.stderr)
            return 2
    cur = sorted(set(cur))
    if mode == "--list":
        print("\n".join(cur))
        return 0
    if mode == "--dupes":
        # warn-only：一律 rc=0（R2 第 4 項之遷移序——先收縮活文，第一期只 warn）。
        n = 0
        for f in files:
            for lit, lines in dupes(f):
                n += 1
                print(
                    "[spec_count_audit] ⚠ 同一計數字面在多處：%s 之 %r @ 行 %s"
                    % (f, lit, ",".join(str(x) for x in lines)),
                    file=sys.stderr,
                )
        if n:
            print(
                "  同一個數字寫在兩個地方 ⇒ 改一處漏一處。"
                "正解：留一處當唯一來源，其餘寫指標。（warn-only，不擋）",
                file=sys.stderr,
            )
        return 0
    if not baseline:
        print("ERROR: --check 需要 --baseline <基準檔>", file=sys.stderr)
        return 2
    base = [l.rstrip("\n") for l in io.open(baseline, encoding="utf-8") if l.strip()]
    added = sorted(set(cur) - set(base))
    removed = sorted(set(base) - set(cur))
    if not added and not removed:
        return 0
    print("[spec_count_audit] 🔴 計數字面有變動 ⇒ 請逐條複核它所計之物的實際數",
          file=sys.stderr)
    if added:
        print("  ── 新增／改變 ──", file=sys.stderr)
        for a in added:
            print("    + " + a, file=sys.stderr)
    if removed:
        print("  ── 消失（確認是刻意移除，非誤刪斷言）──", file=sys.stderr)
        for r in removed:
            print("    - " + r, file=sys.stderr)
    print("\n  病根：R6 三條、R7 三條皆為「計數字面沒跟著它所計之物一起改」"
          "（閘 3→4→5 支／維度 6→5 個／reason 16 vs 20）。", file=sys.stderr)
    print("  正解：能改成集合相等斷言的就別寫計數字面；真要寫數字，複核後更新基準：",
          file=sys.stderr)
    print("        python3 scripts/spec_count_audit.py --list %s > %s"
          % (" ".join(files), baseline), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
