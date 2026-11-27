import type { MetadataRoute } from 'next'

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'Student Gateway | Layanan Akademik Terpadu',
    short_name: 'Student Gateway',
    description: 'Akses terpadu ke layanan akademik, rencana studi, rekomendasi mata kuliah, dan tugas akhir mahasiswa.',
    start_url: '/login',
    display: 'standalone',
    background_color: '#FFFFFF',
    theme_color: '#0D2E6E',
    icons: [
      { src: '/brand/student-gateway-pwa-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/brand/student-gateway-pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/brand/student-gateway-pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
