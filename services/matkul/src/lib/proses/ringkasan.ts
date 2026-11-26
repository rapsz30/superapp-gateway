// Ringkasan nilai untuk dasbor mahasiswa, dipindahkan dari program/src/lib/akademik.ts. Fungsi murni.
// Hasilnya tidak memuat nama atau NIM: hanya data mata kuliah.
import { calcRingkasan } from "../uii-grade.ts";
import { evaluateRows, type KhsPreview } from "./recommend.ts";

export type StatusMk = "lulus" | "bersyarat" | "tidak_lulus";
export type MkNilai = { kode: string; nama: string; sks: number | null; nilai: string; status: StatusMk };
export type SemesterNilai = { semester: number; ip: number | null; sks: number; mk: MkNilai[] };

export type RingkasanAkademik = {
  ipk: number | null;
  sks_lulus: number;
  sks_total: number;
  jumlah_mk: number;
  /** Mata kuliah yang wajib atau disarankan diulang. */
  perhatian: MkNilai[];
  distribusi: { nilai: string; jumlah: number }[];
  /** semester 0 = semester tidak terbaca di KHS (ditaruh paling akhir). */
  per_semester: SemesterNilai[];
};

const URUTAN_NILAI = ["A", "A-", "A/B", "B+", "B", "B-", "B/C", "C+", "C", "C-", "C/D", "D+", "D", "E", "F"];

function bacaSemester(nilai: unknown): number {
  if (typeof nilai === "number" && Number.isFinite(nilai)) return nilai;
  const m = String(nilai ?? "").match(/(\d{1,2})/);
  return m?.[1] ? Number(m[1]) : 0;
}

export function bangunRingkasanAkademik(khs: KhsPreview): RingkasanAkademik {
  const baris = evaluateRows(khs).map((r) => {
    const status: StatusMk =
      r.status_lulus === "Tidak Lulus" ? "tidak_lulus" : r.status_lulus === "Lulus (bersyarat)" ? "bersyarat" : "lulus";
    return {
      semester: bacaSemester(r.semester),
      mk: { kode: r.kode, nama: r.nama, sks: r.sks, nilai: r.nilai, status } satisfies MkNilai,
    };
  });
  const semua = baris.map((b) => b.mk);
  const jumlahSks = (daftar: MkNilai[]) => daftar.reduce((a, x) => a + (x.sks ?? 0), 0);

  const kelompok = new Map<number, MkNilai[]>();
  for (const b of baris) kelompok.set(b.semester, [...(kelompok.get(b.semester) ?? []), b.mk]);

  const hitung = new Map<string, number>();
  for (const x of semua) hitung.set(x.nilai, (hitung.get(x.nilai) ?? 0) + 1);
  const urutan = (nilai: string) => {
    const i = URUTAN_NILAI.indexOf(nilai);
    return i < 0 ? URUTAN_NILAI.length : i;
  };

  return {
    ipk: khs.mahasiswa?.ipk ?? calcRingkasan(khs.nilai ?? []).ipk,
    sks_lulus: jumlahSks(semua.filter((x) => x.status !== "tidak_lulus")),
    sks_total: jumlahSks(semua),
    jumlah_mk: semua.length,
    perhatian: semua.filter((x) => x.status !== "lulus"),
    distribusi: [...hitung.entries()]
      .map(([nilai, jumlah]) => ({ nilai, jumlah }))
      .sort((a, b) => urutan(a.nilai) - urutan(b.nilai)),
    per_semester: [...kelompok.entries()]
      .sort(([a], [b]) => (a || 99) - (b || 99))
      .map(([semester, mk]) => ({ semester, ip: calcRingkasan(mk).ipk, sks: jumlahSks(mk), mk })),
  };
}
