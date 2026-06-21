# FF 一致性整併 — 分級+批次（Composer 獨立評）

對照 FINAL 六項；風險依 CLAUDE.md (a)數值 (b)共用路徑 (c)難回退 (d)ML/回測。

## ① 分級（獨立判斷）
| 項 | 級 | 理由 |
|---|---|---|
| Q5 | **小** | 僅 `main`/config；零 FF 路徑、(a)(d) 無 |
| #1 | **中** | ProcessPool worker 共用入口(b)；跨進程 smoke 非 trivial；非(a) |
| E-normalize | **中** | 單/批雙路徑 contract(b)；薄函式無(a)；retention 實作可延後 |
| Q3 | **中**（邊界**中-大**） | 後端+WS+TS+Zustand(b)；schema 棄用多消費者；仍無 persist |
| Q2-A | **大** | checkpoint/resume/磁碟/前端(b)(c)；staging 改 output 可見性 |
| Q2-B | **中-大** | 失效面廣(b)(c)但比 A 窄；**仍走大管線**（交易語意） |

Claude 對 Q5/#1/E/Q2-A 同我；Q3 我略升邊界；Q2-B 我降為中-大（相對 A），非降風險。

## ② B1/B2 合批
- **B1(Q5+#1)**：主題同（觀測/logging）、無硬依賴 → **可合批**；但 Q5=小、#1=中，整批走「中」管線會**過度儀式**。建議批內 **Q5 先 SMALL_INLINE 落地**，#1+smoke 同 PR 或緊接，勿讓 Q5 等 SPEC。
- **B2(E+Q3)**：**恰當，Test FINAL「E 隨首次 payload 改」；拆開易 Q3 先繞過 normalize 再 refactor。**整批實際中-大**（跨棧），一 SPEC 可接受。
- **不宜再併**：B1↔B2（子系統不同）；B3↔B4（已大）。

## ③ 依賴
Claude `B1→B2→B3→B4` **無錯置**。補兩點：(1) B2 應**定義** progress+retention schema/error enum（E 全 mandatory），retention normalize **實作/parity④⑤** 留 B3；(2) Q2-A **不硬依賴** Q3 RSS，但 UX 上 B2 後做合理。

## ④ 最終批次表
| 批 | 內容 | 級 | 管線 |
|---|---|---|---|
| B1 | Q5 → #1+smoke（批內 Q5 可先行） | 小+中 | Q5 小；#1 中 |
| B2 | E(progress schema+normalize+parity①-③) + Q3 | 中-大 | 中（含前端） |
| B3 | Q2-A：retention normalize+parity④⑤+非阻塞+背壓+staging+checkpoint+resume+UI | 大 | 大 |
| B4 | Q2-B：bulk-delete+多子系統失效+tombstone | 中-大 | 大 |

**順序**：B1 → B2 → B3 → B4（= FINAL P0a→P2.5）。B1 內 Q5 不應被 #1 阻塞。
