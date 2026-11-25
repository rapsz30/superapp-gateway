import { apiFetch } from '@/src/lib/api'

export interface ThesisReference {
  sitasi: string
  link: string
}

export interface ThesisRecommendation {
  judul: string
  deskripsi: string
  metodologi: string
  keywords: string[]
  referensi: ThesisReference[]
}

export const judulService = {
  async getRecommendations(interests: string): Promise<ThesisRecommendation[]> {
    const result = await apiFetch<{ rekomendasi?: ThesisRecommendation[] }>('/api/judul-recommender/get-recommendations', {
      method: 'POST',
      json: { interests },
    })
    return (result.rekomendasi ?? []).map((item) => ({
      judul: item.judul ?? '',
      deskripsi: item.deskripsi ?? '',
      metodologi: item.metodologi ?? '',
      keywords: Array.isArray(item.keywords) ? item.keywords : [],
      referensi: Array.isArray(item.referensi) ? item.referensi : [],
    }))
  },
}
