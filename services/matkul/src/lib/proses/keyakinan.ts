import type { KhsPreview } from "../openai.ts";
import { evaluateRows } from "./recommend.ts";

/**
 * Keyakinan 0..1 hasil ekstraksi KHS, dihitung di pembungkus tanpa mengubah prompt:
 *  - 40% proporsi kolom wajib terisi (nama, nim, prodi, sksKumulatif, ipk)
 *  - 30% proporsi baris nilai yang lengkap (kode, nilai, sks)
 *  - 30% kecocokan jumlah SKS lulus dengan sksKumulatif
 * Di bawah 0,9 proses AlurKerja meminta mahasiswa memeriksa hasil ekstraksi.
 */
export function hitungKeyakinan(khs: KhsPreview): number {
  const m = khs.mahasiswa;
  const wajib = [m.nama, m.nim, m.prodi, m.sksKumulatif, m.ipk];
  const fieldsRatio = wajib.filter((v) => v !== null && v !== "").length / wajib.length;

  const rows = khs.nilai;
  if (rows.length === 0) return 0;
  const rowsRatio = rows.filter((r) => r.kode && r.nilai && r.sks !== null).length / rows.length;

  let sksMatch = 0.5; // tidak bisa diverifikasi bila sksKumulatif kosong
  if (typeof m.sksKumulatif === "number" && m.sksKumulatif > 0) {
    const lulus = evaluateRows(khs)
      .filter((r) => r.lulus)
      .reduce((a, r) => a + (r.sks ?? 0), 0);
    const selisih = Math.abs(lulus - m.sksKumulatif) / m.sksKumulatif;
    sksMatch = selisih === 0 ? 1 : selisih <= 0.1 ? 0.5 : 0;
  }

  return Math.round((0.4 * fieldsRatio + 0.3 * rowsRatio + 0.3 * sksMatch) * 100) / 100;
}

const digits = (s: unknown) => String(s ?? "").replace(/\D+/g, "");

/** NIM pada KHS dibandingkan NIM akun. Hanya dianggap beda bila keduanya terbaca dan berlainan. */
export function nimCocok(nimKhs: unknown, nimAkun: unknown): boolean {
  const a = digits(nimKhs);
  const b = digits(nimAkun);
  return a.length === 0 || b.length === 0 || a === b;
}
