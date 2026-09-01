import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 🔴 `npm run dev` 走 turbopack、`npm run build` 走 webpack，兩者對「專案根目錄之外的
  //    import」判準不同：webpack 解得開、**turbopack 直接 Module not found**。
  //    `frontend/src/lib/eventMetricsGlossary.ts` 依 Task 5.0 之裁定
  //    **必須 build-time import 契約 JSON 本體**（鏡像常數的 production bundle 根本不讀該檔，
  //    改了字畫面照樣顯示舊文案＝`CODEX-R1-P1-01`），而那個檔在 repo 根的 `momentum/` 底下
  //    ⇒ turbopack 需要把 root 指到 repo 根才解得開。
  //    2026-09-01 使用者 UAT B12 實測：`/ic-analysis` 在 dev 下整頁 Build Error。
  //    🔴 我先前只驗 `npm run build`（webpack）就宣稱前端可直接 import 契約——
  //    那個結論**只對 build 成立**，dev 是壞的。
  //    🔴 **turbopack 在 15.3.4 沒有 root 選項**：`turbopack.root` 與
  //       `experimental.turbo.root` 兩個位置皆實跑得到
  //       `Unrecognized key(s) in object: 'root'`。
  //    ⇒ 解法改為**把 `--turbopack` 從 dev script 拿掉**，讓 dev 與 build 走同一個打包器。
  //       這同時消掉「dev 過不了但 build 過得了」這一整類缺陷的來源。
  //       代價＝dev 啟動與熱更新較慢；換來的是**你在 dev 看到的就是 build 出來的**。
  async rewrites() {
    // Proxy API requests to backend server
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    return [
      {
        source: '/api/v1/:path*',
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
