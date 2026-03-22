import type { NextConfig } from "next";

// BACKEND_URL is baked in at build time via Docker --build-arg.
// For local dev it falls back to localhost:8000.
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${BACKEND_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
