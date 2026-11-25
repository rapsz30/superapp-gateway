import { timingSafeEqual } from "node:crypto";

/**
 * Autentikasi layanan-ke-layanan untuk endpoint /api/matkul/* (dipanggil connector AlurKerja).
 * Token layanan BUKAN token pengguna: JWT pengguna yang lewat gateway tidak akan cocok.
 * Mengembalikan Response galat, atau null bila token benar.
 */
export function periksaTokenLayanan(req: Request): Response | null {
  const diharapkan = process.env.MATKUL_SERVICE_TOKEN ?? "";
  if (diharapkan.length < 16) {
    return Response.json({ error: "MATKUL_SERVICE_TOKEN belum diatur di layanan matkul." }, { status: 503 });
  }
  const header = req.headers.get("authorization") ?? "";
  const token = header.toLowerCase().startsWith("bearer ") ? header.slice(7).trim() : "";
  const a = Buffer.from(token);
  const b = Buffer.from(diharapkan);
  if (a.length !== b.length || !timingSafeEqual(a, b)) {
    return Response.json({ error: "Tidak diizinkan." }, { status: 401 });
  }
  return null;
}

export type KonteksPengajuan = {
  mahasiswa: { nim: string | null } | null;
  prodi: { id: string; kode: string; nama: string; maks_sks_semester: number | null };
  panduan: { id: string; versi: number; teks: string };
};

/** Ambil prodi dan panduan aktif untuk sebuah pengajuan dari layanan identity (jaringan internal). */
export async function ambilKonteksPengajuan(pengajuanId: string): Promise<KonteksPengajuan> {
  const base = (process.env.IDENTITY_URL || "http://identity-api:8002").replace(/\/+$/, "");
  const res = await fetch(`${base}/internal/pengajuan/${encodeURIComponent(pengajuanId)}/konteks`, {
    headers: { "X-Internal-Token": process.env.INTERNAL_TOKEN ?? "" },
    signal: AbortSignal.timeout(10_000),
    cache: "no-store",
  });
  if (!res.ok) {
    const detail = ((await res.json().catch(() => ({}))) as { detail?: string }).detail;
    throw new Error(detail || `Konteks pengajuan tidak dapat dimuat (HTTP ${res.status}).`);
  }
  return (await res.json()) as KonteksPengajuan;
}
