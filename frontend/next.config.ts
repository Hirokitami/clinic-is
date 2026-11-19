import type { NextConfig } from "next";

// Адрес FastAPI. Браузер обращается к /api/* на том же домене, Next проксирует запросы на бэкенд,
// поэтому cookie с токеном работает без CORS.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone", // для Docker-образа
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
