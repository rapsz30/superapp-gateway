// Rencana yang sudah dilihat mahasiswa di pratinjau disimpan di server, lalu dipakai apa adanya oleh proses
// pengajuan: mengajukan tidak membaca KHS dan tidak menyusun rencana untuk kedua kalinya.
// Yang disimpan selalu hasil buatan server. Nilai yang diubah mahasiswa di wizard dibandingkan dengan bacaan
// berkas aslinya dan dicatat sebagai peringatan untuk pembimbing akademik.
import { UMUR_BACAAN_HARI } from "./bacaan.ts";
import { query } from "./db.ts";
import type { KhsRow, RecommendResult } from "./recommend.ts";
import { NILAI_UII_OPTIONS } from "../uii-grade.ts";

const huruf = (nilai: unknown) => {
  const n = String(nilai ?? "").trim().toUpperCase();
  return (NILAI_UII_OPTIONS as string[]).includes(n) ? n : "";
};
const bentuk = (r: KhsRow) => ({
  kode: String(r.kode ?? "").trim().toUpperCase(),
  nama: String(r.nama ?? "").trim(),
  sks: Number(r.sks) || 0,
  nilai: huruf(r.nilai),
});
const sebut = (r: ReturnType<typeof bentuk>) => `${r.sks} SKS, nilai ${r.nilai || "kosong"}`;

/** Perbedaan antara nilai hasil bacaan berkas dan nilai yang dipakai pratinjau, dalam kalimat. */
export function bandingkanNilai(asli: KhsRow[], dipakai: KhsRow[]): string[] {
  const sisa = asli.map(bentuk);
  const hasil: string[] = [];
  for (const baris of dipakai.map(bentuk)) {
    // Utamakan pasangan yang persis sama, supaya mata kuliah yang tercantum dua kali tidak tertukar.
    let i = sisa.findIndex((a) => JSON.stringify(a) === JSON.stringify(baris));
    if (i >= 0) {
      sisa.splice(i, 1);
      continue;
    }
    i = sisa.findIndex((a) => (a.kode && a.kode === baris.kode) || a.nama === baris.nama);
    if (i < 0) {
      hasil.push(`${baris.kode || baris.nama} ditambahkan mahasiswa (${sebut(baris)}); tidak ada di KHS`);
      continue;
    }
    const [a] = sisa.splice(i, 1);
    const nama = a.kode !== baris.kode || a.nama !== baris.nama ? `, ditulis "${baris.kode} ${baris.nama}"` : "";
    hasil.push(`${a.kode || a.nama} diubah mahasiswa menjadi ${sebut(baris)}${nama} (di KHS: ${sebut(a)})`);
  }
  for (const a of sisa) hasil.push(`${a.kode || a.nama} dihapus mahasiswa (di KHS: ${sebut(a)})`);
  return hasil;
}

export type KunciPratinjau = { sidik: string; pemilik: string; panduanId: string };

const BATAS = `now() - interval '${UMUR_BACAAN_HARI} days'`;

export async function simpanPratinjau(kunci: KunciPratinjau, hasil: RecommendResult, perubahan: string[]) {
  await query(`DELETE FROM matkul_pratinjau WHERE created_at <= ${BATAS}`);
  await query(
    `INSERT INTO matkul_pratinjau (sidik, pemilik, panduan_id, semester_target, data, perubahan)
     VALUES ($1, $2, $3, $4, $5, $6)
     ON CONFLICT (sidik, pemilik, panduan_id, semester_target)
     DO UPDATE SET data = EXCLUDED.data, perubahan = EXCLUDED.perubahan, created_at = now()`,
    [kunci.sidik, kunci.pemilik, kunci.panduanId, hasil.semester_target, JSON.stringify(hasil), JSON.stringify(perubahan)],
  );
}

/** Pratinjau terbaru; tanpa `semester` hanya dipakai untuk tahu bahwa mahasiswa sudah melihat hasilnya. */
export async function ambilPratinjau(kunci: KunciPratinjau, semester?: number | null) {
  const [row] = await query<{ data: RecommendResult; perubahan: string[] }>(
    `SELECT data, perubahan FROM matkul_pratinjau
     WHERE sidik = $1 AND pemilik = $2 AND panduan_id = $3 AND ($4::int IS NULL OR semester_target = $4)
       AND created_at > ${BATAS}
     ORDER BY created_at DESC LIMIT 1`,
    [kunci.sidik, kunci.pemilik, kunci.panduanId, semester ?? null],
  );
  return row ?? null;
}
