import type { NextConfig } from "next";

const config: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Keep `next dev` output separate from `next build`. Running a production
  // build while the local launcher is active must not delete dev-server chunks.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  async rewrites() {
    const hostport = process.env.API_PROXY_HOSTPORT;
    if (!hostport) return [];
    return [{ source: "/api/:path*", destination: `http://${hostport}/api/:path*` }];
  },
};

export default config;
