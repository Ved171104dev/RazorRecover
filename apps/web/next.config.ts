import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    const apiOrigin = (process.env.API_PROXY_URL || "https://razorrecover-api-ved171104dev.onrender.com").replace(/\/$/, "");
    return [{ source: "/api/:path*", destination: `${apiOrigin}/api/:path*` }];
  },
  // Keep `next dev` output separate from `next build`. Running a production
  // build while the local launcher is active must not delete dev-server chunks.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default config;
