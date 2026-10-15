export type NilaiUII =
  | "A" | "A-"
  | "A/B" | "B+" | "B" | "B-"
  | "B/C" | "C+" | "C" | "C-"
  | "C/D" | "D+" | "D"
  | "E" | "F";

export const NILAI_UII_OPTIONS: NilaiUII[] = [
  "A", "A-",
  "A/B", "B+", "B", "B-",
  "B/C", "C+", "C", "C-",
  "C/D", "D+", "D",
  "E", "F",
];

export type Mutu =
  | "Amat Baik"
  | "Baik"
  | "Cukup"
  | "Kurang"
  | "Sangat Kurang"
  | "Tidak Memenuhi Syarat";

export type StatusLulus = "Lulus" | "Lulus (bersyarat)" | "Tidak Lulus";

export function getMutu(nilai: NilaiUII): Mutu {
  if (nilai === "A" || nilai === "A-") return "Amat Baik";
  if (nilai === "A/B" || nilai === "B+" || nilai === "B" || nilai === "B-") return "Baik";
  if (nilai === "B/C" || nilai === "C+" || nilai === "C" || nilai === "C-") return "Cukup";
  if (nilai === "C/D" || nilai === "D+" || nilai === "D") return "Kurang";
  if (nilai === "E") return "Sangat Kurang";
  return "Tidak Memenuhi Syarat"; // F
}

export function getStatusLulus(nilai: NilaiUII): StatusLulus {
  if (nilai === "E" || nilai === "F") return "Tidak Lulus";

  // Catatan: aturan UII bilang D bisa lulus terbatas.
  // Kalau kamu belum punya aturan kurikulum prodi -> tandai bersyarat.
  if (nilai === "D" || nilai === "D+" || nilai === "C/D") return "Lulus (bersyarat)";

  return "Lulus";
}

export function badgeClass(nilai: NilaiUII) {
  if (nilai === "E" || nilai === "F") return "bg-red-50 text-red-700";
  if (nilai === "D" || nilai === "D+" || nilai === "C/D") return "bg-yellow-50 text-yellow-800";
  return "bg-blue-50 text-blue-700";
}

// Bobot nilai (skala 4.0) sesuai pedoman akademik UII.
const BOBOT_MAP: Record<NilaiUII, number> = {
  A: 4.0,
  "A-": 3.75,
  "A/B": 3.5,
  "B+": 3.25,
  B: 3.0,
  "B-": 2.75,
  "B/C": 2.5,
  "C+": 2.25,
  C: 2.0,
  "C-": 1.75,
  "C/D": 1.5,
  "D+": 1.25,
  D: 1.0,
  E: 0.0,
  F: 0.0,
};

export function getBobot(nilai: NilaiUII): number {
  return BOBOT_MAP[nilai] ?? 0;
}

/**
 * Hitung ringkasan (total SKS, total MK, IPK) dari daftar nilai.
 * IPK = total(bobot * sks) / total(sks), hanya dari baris dengan sks > 0
 * dan nilai huruf yang valid/dikenal.
 */
export function calcRingkasan(
  rows: Array<{ sks?: number | null; nilai?: string | null }>
): { total_sks: number; total_mk: number; ipk: number | null } {
  let totalSks = 0;
  let totalBobotSks = 0;
  let sksDinilai = 0;

  for (const r of rows ?? []) {
    const sks = typeof r.sks === "number" && Number.isFinite(r.sks) ? r.sks : 0;
    totalSks += sks;

    const nilaiKey = String(r.nilai ?? "").trim().toUpperCase() as NilaiUII;
    if (sks > 0 && nilaiKey && nilaiKey in BOBOT_MAP) {
      totalBobotSks += getBobot(nilaiKey) * sks;
      sksDinilai += sks;
    }
  }

  return {
    total_sks: totalSks,
    total_mk: rows?.length ?? 0,
    ipk: sksDinilai > 0 ? totalBobotSks / sksDinilai : null,
  };
}