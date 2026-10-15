export type Kegiatan =
  | "Pengembangan Diri Qur'ani"
  | "Student Soft Skill Development"
  | "Pelatihan Kepemimpinan dan Dakwah"
  | "Pendalaman Nilai Dasar Islam"
  | "Pelatihan Pengembangan Diri";

export type NilaiManualKegiatan = {
  kegiatan: Kegiatan;
  kelasKelompok: string;
  nilaiAkhir: string;
  tahun: number | null;
};

export const KEGIATAN_OPTIONS: Kegiatan[] = [
    "Pengembangan Diri Qur'ani",
    "Student Soft Skill Development",
    "Pelatihan Kepemimpinan dan Dakwah",
    "Pendalaman Nilai Dasar Islam",
    "Pelatihan Pengembangan Diri",
];

export const KEGIATAN_KODE: Record<Kegiatan, string> = {
  "Pengembangan Diri Qur'ani": "PDQ",
  "Student Soft Skill Development": "S3D",
  "Pelatihan Kepemimpinan dan Dakwah": "PKD",
  "Pendalaman Nilai Dasar Islam": "PNDI",
  "Pelatihan Pengembangan Diri": "PPD",
};

export const KEGIATAN_STORAGE_KEY = "khs_nilai_manual_kegiatan";

/** Ambil nilai terbaru per kegiatan dari sessionStorage. */
export function loadNilaiKegiatanMap(): Record<string, string> {
  const map: Record<string, string> = {};
  try {
    const raw = sessionStorage.getItem(KEGIATAN_STORAGE_KEY);
    if (!raw) return map;
    const parsed = JSON.parse(raw) as NilaiManualKegiatan[];
    if (!Array.isArray(parsed)) return map;
    for (const item of parsed) {
      if (!map[item.kegiatan]) map[item.kegiatan] = item.nilaiAkhir;
    }
  } catch {
    // biarkan map kosong kalau data corrupt/tidak ada
  }
  return map;
}