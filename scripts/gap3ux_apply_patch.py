#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gap3ux_apply_patch.py — 委員補丁包之**逐字套用**與**強制對證**（R28 新建）

出處（GROK-R28 議題一第 3 點；R27 三家裁定 (丙) 之處方之操作洞修補）：
  R27 主委改行「逐字套用＋字面對證」後，委員自主量測仍判**尚未有效**：
    · grok：AFTER 全行命中 **2/15**、locus rc=0 **1/15**（R26 為 0/15）
    · codex：20 tokens 命中 18＝90%，但「新法改善窄樣本、整體未證有效」
  **操作洞**：主委把「逐字套用」落成 **自選識別字 must_exist**
  ——**主委自己挑要驗哪些字面**，於是挑到的都過、沒挑到的（prepare 草圖行）仍未入。
  這與 R22「主委自擬 grep 清單」、R21「主委自我歸類」**同型**：
  **只要「驗什麼」由主委決定，機械化的就只有執行、不是判斷。**

本檔把該選擇權從主委手上拿掉：
  (i) must_exist ＝ **AFTER fence 之每一非空行**（正規化空白後），**禁自選子集**
  (ii) 套用後於**同一行程式內**跑該包**全部** VERIFY grep
  (iii) 任一 must_exist 行缺失或任一 VERIFY 未達 ⇒ **非零退出**

🔴 **本檔不新建驗收機制類型**（符合 R20 角色卡）：它只是把既有之
   「套用／VERIFY／locus」三件事串成一個不可跳步之流程；判準一字未改。

用法：
  python3 scripts/gap3ux_apply_patch.py <patch.md> [<patch.md> ...] --check
      只檢查（不改檔）：報告每包之 AFTER 行對證率與 VERIFY 達成率
  python3 scripts/gap3ux_apply_patch.py <patch.md> --target docs/X.md --check
rc: 0=全部對證通過；2=有 AFTER 行未入；3=有 VERIFY 未達；4=用法/解析錯誤
"""
import argparse
import io
import os
import re
import subprocess
import sys

DEFAULT_TARGET = "docs/GAP3_EVENT_UX_SPEC.md"

_AFTER_RE = re.compile(r"^AFTER[^\n]*\n(.*?)(?=^VERIFY|\Z)", re.S | re.M)
_FENCE_RE = re.compile(r"```[a-zA-Z]*\n(.*?)```", re.S)
# 🔴 R31：停在下一「區段標題」（行首大寫關鍵字）或 EOF；勿用 ^\S（會切掉 `- \`grep` bullet）
_VERIFY_RE = re.compile(
    r"^VERIFY[^\n]*\n(.*?)(?=^(?:BEFORE|AFTER|VERIFY|AUTHORITY|OWNER|SHAPE|CONSUMER|"
    r"NEGATIVE_MUTATION|SYNC-LOCI|SYNC-LOCI:)\b|\Z)",
    re.S | re.M,
)


def _norm(s):
    """空白正規化：連續空白折成單一空白、去頭尾。"""
    return re.sub(r"\s+", " ", s).strip()


def after_lines(body):
    """AFTER 段之每一非空行；若有 code fence 則只取 fence 內容（那才是要逐字入檔的）。"""
    m = _AFTER_RE.search(body)
    if not m:
        return []
    seg = m.group(1)
    fences = _FENCE_RE.findall(seg)
    src = "\n".join(fences) if fences else seg
    out = []
    for ln in src.split("\n"):
        n = _norm(ln)
        # 略過純標記行與省略號行——它們不是要入檔之字面
        if not n or n in ("…", "...", "```"):
            continue
        out.append(n)
    return out


def verify_greps(body):
    """VERIFY 段中形如 `grep ... <literal> ...` → 0 或 ≥1 之期望；回傳 (literal, expect) 清單。
    只解析**明確寫出期望數**者；其餘交人工／locus。"""
    m = _VERIFY_RE.search(body)
    if not m:
        return []
    out = []
    for ln in m.group(1).split("\n"):
        if "grep" not in ln:
            continue
        # 🔴 R32：字面＝grep 之搜尋 pattern，不是整條反引號指令
        m = re.search(
            r"""(?:-nF|-nE|-F|-E|--fixed-strings)\s+'((?:\\'|[^'])+)'""", ln)
        if not m:
            m = re.search(
                r'''(?:-nF|-nE|-F|-E|--fixed-strings)\s+"((?:\\"|[^"])+)"''', ln)
        if not m:
            m = re.search(r"""grep\s+(?:-[a-zA-Z0-9]+\s+)*'((?:\\'|[^'])+)'""", ln)
        if not m:
            m = re.search(r'''grep\s+(?:-[a-zA-Z0-9]+\s+)*"((?:\\"|[^"])+)"''', ln)
        if not m:
            continue
        lit = m.group(1).replace("\\'", "'").replace('\\"', '"')
        if re.search(r"(→|->|⇒)\s*0\b", ln):
            out.append((lit, 0, ln))
        elif re.search(r"(≥\s*1|>=\s*1)", ln):
            out.append((lit, 1, ln))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("patches", nargs="+")
    ap.add_argument("--target", default=DEFAULT_TARGET)
    ap.add_argument("--check", action="store_true",
                    help="只檢查不改檔（目前唯一模式；套用仍由落地腳本執行）")
    a = ap.parse_args()

    if not os.path.exists(a.target):
        print("🔴 找不到標的：%s" % a.target); return 4
    spec = io.open(a.target, encoding="utf-8").read()
    spec_norm = _norm(spec)

    rc = 0
    tot_l = hit_l = tot_v = ok_v = 0
    for p in a.patches:
        if not os.path.exists(p):
            print("🔴 找不到補丁包：%s" % p); rc = max(rc, 4); continue
        body = io.open(p, encoding="utf-8").read()
        lines = after_lines(body)
        miss = [ln for ln in lines if ln not in spec_norm]
        tot_l += len(lines); hit_l += len(lines) - len(miss)

        vs = verify_greps(body)
        vbad = []
        for lit, expect, vln in vs:
            pm = re.search(r'(docs/[\w./-]+|scripts/[\w./-]+|[\w./-]+\.(?:py|md|sh))', vln)
            blob = io.open(pm.group(1), encoding="utf-8").read() if pm and os.path.exists(pm.group(1)) else spec
            n = blob.count(lit)
            if (expect == 0 and n != 0) or (expect >= 1 and n < 1):
                vbad.append((lit, expect, n))
        tot_v += len(vs); ok_v += len(vs) - len(vbad)

        tag = "✅" if not miss and not vbad else "🔴"
        print("%s %-56s AFTER %d/%d  VERIFY %d/%d"
              % (tag, os.path.basename(p)[:56],
                 len(lines) - len(miss), len(lines),
                 len(vs) - len(vbad), len(vs)))
        for ln in miss[:6]:
            print("     ✗ AFTER 未入：%s" % ln[:96])
        for lit, e, n in vbad[:6]:
            print("     ✗ VERIFY 未達：`%s` 期望 %s 實得 %d" % (lit[:70], e, n))
        if miss:
            rc = max(rc, 2)
        if vbad:
            rc = max(rc, 3)

    print("── 合計：AFTER 行 %d/%d；VERIFY %d/%d" % (hit_l, tot_l, ok_v, tot_v))
    return rc


if __name__ == "__main__":
    sys.exit(main())
