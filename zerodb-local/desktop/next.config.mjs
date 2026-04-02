/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  trailingSlash: true,
  poweredByHeader: false,
  reactStrictMode: true,
  images: {
    unoptimized: true,
  },
  env: {
    ZERODB_API_URL: process.env.ZERODB_API_URL || 'http://localhost:8000',
  },
}

export default nextConfig
