import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["@radix-ui/react-icons"],
  },
  allowedDevOrigins: [
    '*',
  ],
};

export default nextConfig;
