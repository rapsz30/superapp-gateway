import { AsyncLocalStorage } from "node:async_hooks";

type Pemilik = { akunId?: string; pengajuanId?: string };
type Catatan = { layanan: "matkul"; model: string; token_masuk: number; token_keluar: number; durasi_ms: number; berhasil: boolean };
const konteks = new AsyncLocalStorage<Pemilik>();

export function denganPemilik<T>(pemilik: Pemilik, fn: () => T): T {
  return konteks.run(pemilik, fn);
}

export function catatPemakaianAi(fitur: string, catatan: Catatan): void {
  const token = process.env.AI_CATAT_TOKEN;
  if (!token) return;
  const pemilik = konteks.getStore() ?? {};
  const pemilikApi = {
    ...(pemilik.akunId ? { akun_id: pemilik.akunId } : {}),
    ...(pemilik.pengajuanId ? { pengajuan_id: pemilik.pengajuanId } : {}),
  };
  const url = `${(process.env.IDENTITY_URL || "http://identity-api:8002").replace(/\/+$/, "")}/internal/ai-pemakaian`;
  void fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json", "X-AI-Token": token },
    body: JSON.stringify({ ...catatan, fitur, ...pemilikApi }),
    signal: AbortSignal.timeout(3000),
  }).catch((e) => console.warn("Gagal mencatat pemakaian AI matkul:", e instanceof Error ? e.name : "Error"));
}
