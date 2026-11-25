import type { KonteksAkademik } from "@/src/lib/konteks";

export class IdentityError extends Error {
  status: number;
  kode: string;
  constructor(message: string, status: number, kode: string) {
    super(message);
    this.name = "IdentityError";
    this.status = status;
    this.kode = kode;
  }
}

const identityUrl = () => (process.env.IDENTITY_URL || "http://identity-api:8002").replace(/\/+$/, "");

/**
 * Ambil prodi, pembimbing akademik, dan panduan aktif milik pemanggil dari layanan identity.
 * Header Authorization pengguna diteruskan apa adanya; identity yang memvalidasi token.
 */
export async function ambilKonteks(authorization: string): Promise<KonteksAkademik> {
  let res: Response;
  try {
    res = await fetch(`${identityUrl()}/akademik/konteks`, {
      headers: { Authorization: authorization },
      signal: AbortSignal.timeout(10_000),
      cache: "no-store",
    });
  } catch {
    throw new IdentityError("Layanan identitas tidak dapat dihubungi. Coba lagi beberapa saat lagi.", 502, "identity_mati");
  }

  const body = (await res.json().catch(() => ({}))) as { detail?: unknown };
  const detail = typeof body.detail === "string" ? body.detail : "";

  if (res.ok) return body as unknown as KonteksAkademik;
  if (res.status === 401) throw new IdentityError("Sesi berakhir. Silakan masuk kembali.", 401, "tidak_login");
  if (res.status === 403) {
    throw new IdentityError(detail || "Hanya mahasiswa yang dapat membuat rekomendasi.", 403, "bukan_mahasiswa");
  }
  if (res.status === 404) {
    throw new IdentityError(detail || "Panduan akademik prodi Anda belum tersedia.", 409, "panduan_belum_ada");
  }
  throw new IdentityError(detail || "Konteks akademik tidak dapat dimuat.", 502, "identity_galat");
}
