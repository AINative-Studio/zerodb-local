/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  poweredByHeader: false,
  reactStrictMode: true,
  env: {
    API_URL: process.env.VITE_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.VITE_API_INTERNAL_URL || 'http://zerodb-api:8000'}/:path*`,
      },
    ]
  },
}

export default nextConfig
