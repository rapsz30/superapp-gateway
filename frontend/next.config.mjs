// Alamat gateway NGINX (satu pintu ke semua layanan backend).
// Browser hanya memanggil /api/* pada origin frontend; Next.js meneruskannya ke gateway,
// jadi tidak perlu mengatur CORS di NGINX.
const apiBaseUrl = (process.env.API_BASE_URL || 'http://127.0.0.1:8080').replace(/\/+$/, '')

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  experimental: {
    // Panggilan LLM (rekomendasi judul, ekstraksi KHS, rekomendasi matkul) bisa lebih dari 30 detik.
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${apiBaseUrl}/api/:path*` }]
  },
}

export default nextConfig
