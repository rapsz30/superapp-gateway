/**
 * Logika murni untuk konteks akademik (tanpa jaringan), supaya mudah diuji.
 * Sumber konteks: layanan identity (/akademik/konteks).
 */

export type KonteksAkademik = {
  mahasiswa: { id: string; nama_lengkap: string; nim: string | null } | null;
  prodi: {
    id: string;
    kode: string;
    nama: string;
    jenjang: string;
    maks_sks_semester?: number | null;
    jurusan: { id: string; kode: string; nama: string } | null;
    fakultas: { id: string; kode: string; nama: string } | null;
  };
  pembimbing_akademik: { id: string; nama_lengkap: string; email: string | null } | null;
  panduan: {
    id: string;
    versi: number;
    judul: string;
    berlaku_mulai: string | null;
    teks_karakter: number | null;
    teks?: string;
  };
};

const digits = (s: unknown) => String(s ?? "").replace(/\D+/g, "");

/**
 * true bila NIM pada KHS jelas milik orang lain. Hanya salah bila keduanya ada dan berbeda;
 * bila salah satu kosong, tidak diblokir (ekstraksi AI bisa gagal membaca NIM).
 */
export function nimBerbeda(nimKhs: unknown, nimAkun: unknown): boolean {
  const a = digits(nimKhs);
  const b = digits(nimAkun);
  return a.length > 0 && b.length > 0 && a !== b;
}

const buangKataUmum = (s: string) =>
  s
    .toLowerCase()
    .replace(/program\s+studi|prodi|program\s+sarjana|sarjana|\bs1\b|\(|\)|-|–/g, " ")
    .replace(/[^a-z0-9]+/g, "");

/**
 * Perbandingan longgar nama prodi di KHS dengan prodi akun. Mengembalikan true bila cocok
 * atau tidak bisa dibandingkan. Dipakai hanya untuk peringatan, bukan pemblokiran.
 */
export function prodiCocok(prodiKhs: unknown, prodiAkun: string): boolean {
  const a = buangKataUmum(String(prodiKhs ?? ""));
  const b = buangKataUmum(prodiAkun);
  if (!a || !b) return true;
  return a.includes(b) || b.includes(a);
}

export function peringatanKonteks(
  khs: { mahasiswa?: { prodi?: string | null; fakultas?: string | null } },
  konteks: KonteksAkademik,
): string[] {
  const hasil: string[] = [];
  const prodiKhs = khs.mahasiswa?.prodi ?? khs.mahasiswa?.fakultas;
  if (!prodiCocok(prodiKhs, konteks.prodi.nama)) {
    hasil.push(
      `Program studi pada KHS ("${String(prodiKhs)}") berbeda dengan prodi akun Anda ("${konteks.prodi.nama}"). ` +
        `Rekomendasi memakai panduan prodi akun Anda.`,
    );
  }
  return hasil;
}
