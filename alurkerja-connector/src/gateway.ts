import type { Config } from "./config.js";
import { postJson } from "./http.js";

export type ExtractKhsResult = {
  khs_ref: string;
  ipk: number | null;
  sks_lulus: number | null;
  mk_lulus: string[];
  mk_ulang: string[];
  keyakinan: number;
  /** Program studi (bukan data pribadi); dipakai untuk rekap laporan prodi. */
  prodi?: string | null;
  /** false bila NIM pada KHS berbeda dari NIM akun (KHS milik orang lain). */
  nim_cocok?: boolean;
};

export type RencanaResult = {
  rencana_ref: string;
  rencana_mk: { kode: string; nama: string; sks: number | null; alasan: string }[];
  total_sks: number;
  alasan: string;
  peringatan: string[];
  /** HTML ringkas untuk form dosen di Tasklist. */
  ringkasan_dosen?: string;
};

export function gatewayClient(c: Config) {
  const headers: Record<string, string> = c.gatewayToken ? { authorization: `Bearer ${c.gatewayToken}` } : {};
  const call = <T>(path: string, body: unknown) => postJson<T>(`${c.gatewayUrl}/api/matkul/${path}`, body, headers);
  return {
    extractKhs: (khs_file_id: string, semester_target?: number, id_pengajuan?: string) =>
      call<ExtractKhsResult>("extract-khs", { khs_file_id, semester_target, id_pengajuan }),
    recommend: (khs_ref: string, semester_target?: number) =>
      call<RencanaResult>("recommend", { khs_ref, semester_target }),
    revise: (rencana_ref: string, catatan_dosen: string) =>
      call<RencanaResult>("revise", { rencana_ref, catatan_dosen }),
  };
}
