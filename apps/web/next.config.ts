import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    optimizePackageImports: ["@radix-ui/react-icons"],
  },
  allowedDevOrigins: [
    '*',
  ],
};

export default nextConfig;
