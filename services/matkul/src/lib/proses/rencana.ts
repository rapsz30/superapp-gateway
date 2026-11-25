import { newId, query } from "./db.ts";
import { evaluateRows, recommendCourses, type KhsPreview, type RecommendResult } from "./recommend.ts";

const esc = (t: string) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/**
 * Minimalisasi data: LLM menerima nama dan NIM di prompt dan kadang mengulangnya di teks.
 * Teks yang dikirim keluar (ke AlurKerja) harus bebas dari keduanya.
 */
export function redactIdentity(text: string, khs: KhsPreview): string {
  let out = String(text ?? "");
  const nim = String(khs.mahasiswa?.nim ?? "").trim();
  const nama = String(khs.mahasiswa?.nama ?? "").trim();
  if (nim) out = out.replace(new RegExp(`(NIM\\s*:?\\s*)?${esc(nim)}`, "gi"), "");
  if (nama) {
    out = out.replace(new RegExp(esc(nama), "gi"), "mahasiswa");
    for (const bagian of nama.split(/\s+/).filter((b) => b.length >= 4)) {
      out = out.replace(new RegExp(`\\b${esc(bagian)}\\b`, "gi"), "mahasiswa");
    }
  }
  return out.replace(/\s+,/g, ",").replace(/,\s*,/g, ",").replace(/\s{2,}/g, " ").trim();
}

/** Bentuk respons recommend/revise sesuai kontrak brief. */
export function toContract(rencana_ref: string, r: RecommendResult, khs: KhsPreview) {
  const rencana_mk = r.rekomendasi_semester_depan.map((x) => ({
    kode: x.kode,
    nama: x.nama,
    sks: x.sks,
    alasan: redactIdentity(x.alasan, khs),
  }));
  const total_sks = rencana_mk.reduce((a, x) => a + (x.sks ?? 0), 0);

  // Peringatan diturunkan dari data (bukan dari LLM): semua yang "perlu perhatian"
  // (tidak lulus, atau lulus bersyarat), konsisten dengan mk_ulang di extract-khs.
  const peringatan = evaluateRows(khs)
    .filter((x) => x.status_lulus !== "Lulus")
    .map((x) =>
      x.status_lulus === "Tidak Lulus"
        ? `${x.kode} belum lulus (nilai ${x.nilai}), wajib diulang`
        : `${x.kode} lulus bersyarat (nilai ${x.nilai}), disarankan diulang`
    );

  return { rencana_ref, rencana_mk, total_sks, alasan: redactIdentity(r.ringkasan, khs), peringatan };
}

export async function buatRencana(opts: {
  khs_ref: string;
  semester_target?: number | null;
  /** Diisi saat revisi: rencana yang direvisi. */
  parent?: { ref: string; revisi_ke: number; data: unknown };
  catatan_dosen?: string;
}) {
  const [row] = await query<{ data: KhsPreview; panduan_teks: string | null; maks_sks: number | null }>(
    "SELECT data, panduan_teks, maks_sks FROM matkul_khs WHERE ref = $1",
    [opts.khs_ref]
  );
  if (!row) return null;
  // Panduan disimpan bersama KHS saat ekstraksi (versi yang berlaku saat proses dimulai), bukan dibaca ulang.
  if (!row.panduan_teks) throw new Error("KHS ini belum terkait panduan prodi (ekstraksi tanpa id_pengajuan).");

  const result = await recommendCourses({
    khs: row.data,
    panduanText: row.panduan_teks,
    maksSksPanduan: row.maks_sks,
    semesterTarget: opts.semester_target,
    catatanDosen: opts.catatan_dosen,
    rencanaSebelumnya: opts.parent?.data,
  });

  const rencana_ref = newId("rnc");
  await query(
    "INSERT INTO matkul_rencana (ref, khs_ref, semester_target, data, parent_ref, revisi_ke) VALUES ($1,$2,$3,$4,$5,$6)",
    [
      rencana_ref,
      opts.khs_ref,
      result.semester_target,
      JSON.stringify(result),
      opts.parent?.ref ?? null,
      opts.parent ? opts.parent.revisi_ke + 1 : 0,
    ]
  );
  return toContract(rencana_ref, result, row.data);
}
