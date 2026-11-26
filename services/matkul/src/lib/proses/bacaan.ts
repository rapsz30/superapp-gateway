// Satu KHS dibaca LLM satu kali: pratinjau menyimpan hasilnya, proses pengajuan resmi memakai hasil yang sama.
// Kuncinya sidik (SHA-256) isi berkas, dan yang disimpan selalu hasil bacaan server dari berkas itu, sehingga
// browser tidak bisa menyisipkan nilai: berkas yang diubah sedikit pun mendapat sidik lain dan dibaca baru.
import { createHash } from "node:crypto";
import type { KhsPreview } from "../openai.ts";

/** Hasil bacaan memuat nama dan NIM, jadi tidak disimpan lebih lama dari ini. */
export const UMUR_BACAAN_HARI = 7;

export type Penyimpanan = {
  ambil(sidik: string): Promise<KhsPreview | null>;
  /** Simpan bila belum ada; mengembalikan hasil yang akhirnya tersimpan (penulis pertama menang). */
  simpan(sidik: string, hasil: KhsPreview): Promise<KhsPreview>;
};

export const sidikBerkas = (data: Buffer) => createHash("sha256").update(data).digest("hex");

/**
 * Ambil hasil bacaan tersimpan untuk berkas ini, atau baca sekarang lalu simpan. Hasil tanpa mata kuliah tidak
 * disimpan supaya bisa dicoba lagi. Galat penyimpanan tidak menggagalkan pembacaan.
 */
export async function bacaSekali(
  data: Buffer,
  baca: () => Promise<KhsPreview>,
  gudang: Penyimpanan,
): Promise<KhsPreview> {
  const sidik = sidikBerkas(data);
  const catat = (e: unknown) => console.warn("BACAAN_KHS_CACHE:", e instanceof Error ? e.message : String(e));
  try {
    const ada = await gudang.ambil(sidik);
    if (ada) return ada;
  } catch (e) {
    catat(e);
  }
  const hasil = await baca();
  if (!hasil.nilai?.length) return hasil;
  try {
    return await gudang.simpan(sidik, hasil);
  } catch (e) {
    catat(e);
    return hasil;
  }
}
