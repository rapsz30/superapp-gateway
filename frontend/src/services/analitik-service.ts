import { apiFetch } from '@/src/lib/api'

export type DashboardRow = Record<string, string | number | boolean | null>

/** Satu kartu dashboard Analytics AlurKerja. Posisi memakai kisi 12 kolom seperti di Studio. */
export interface DashboardCard {
  id: string
  x: number
  y: number
  w: number
  h: number
  judul: string
  jenis: string
  konfigurasi: { title?: string; header?: string; value_column?: string; x_axis?: string; y_axis?: string[]; colors?: string[]; legend?: boolean }
  baris: DashboardRow[]
  galat: string | null
}

export interface Dashboard {
  judul: string
  deskripsi: string
  diambil_pada: string
  kartu: DashboardCard[]
}

/** Tab halaman Analitik; tiap tab mencerminkan satu dashboard di Studio. */
export type TabAnalitik = 'ringkasan' | 'matkul' | 'judul'

export const analitikService = {
  dashboard: (tab: TabAnalitik): Promise<Dashboard> => apiFetch<Dashboard>(`/api/identity/analitik/dashboard?tab=${tab}`),
}
