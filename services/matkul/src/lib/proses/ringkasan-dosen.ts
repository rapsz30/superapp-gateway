// Rangkuman yang dibaca dosen di atas pilihan keputusan pada form Tasklist AlurKerja (variabel `ringkasan_dosen`,
// komponen "Rich Text From Variable"). Berisi HTML sederhana tanpa nama dan NIM.
import { calcRingkasan } from "../uii-grade.ts";
import { evaluateRows, type KhsPreview } from "./recommend.ts";

/** Camunda menyimpan variabel String paling panjang 4000 karakter. */
export const MAKS_KARAKTER = 3900;

const aman = (t: unknown) =>
  String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const daftar = (tag: "ul" | "ol", butir: string[]) =>
  butir.length ? `<${tag}>${butir.map((b) => `<li>${b}</li>`).join("")}</${tag}>` : "";

export function ringkasanDosen(
  rencana: {
    rencana_mk: { kode: string; nama: string; sks: number | null }[];
    total_sks: number;
    alasan: string;
    peringatan: string[];
  },
  khs: KhsPreview,
  revisi?: { ke: number; catatan: string },
): string {
  const lulus = evaluateRows(khs).filter((r) => r.lulus).reduce((a, r) => a + (r.sks ?? 0), 0);
  const ipk = khs.mahasiswa?.ipk ?? calcRingkasan(khs.nilai ?? []).ipk;
  const angka = typeof ipk === "number" ? ipk.toFixed(2).replace(".", ",") : "-";

  const bagian = [
    `<p><strong>IPK ${angka} · SKS lulus ${lulus} · Rencana ${rencana.total_sks} SKS (${rencana.rencana_mk.length} mata kuliah)</strong></p>`,
    revisi ? `<p><strong>Revisi ke-${revisi.ke}</strong> atas catatan: ${aman(revisi.catatan)}</p>` : "",
    rencana.peringatan.length ? `<p><strong>Perlu diperhatikan</strong></p>${daftar("ul", rencana.peringatan.map(aman))}` : "",
    "<p><strong>Mata kuliah yang diajukan</strong></p>",
    daftar("ol", rencana.rencana_mk.map((m) => `${aman(m.kode)} ${aman(m.nama)}${m.sks ? ` (${m.sks} SKS)` : ""}`)),
    rencana.alasan ? `<p>${aman(rencana.alasan)}</p>` : "",
  ];

  // Bila terlalu panjang, bagian paling belakang dibuang utuh supaya tag HTML tidak terpotong.
  let hasil = "";
  for (const b of bagian) {
    if (hasil.length + b.length > MAKS_KARAKTER) {
      return `${hasil}<p>Rangkuman dipotong. Lihat tab History untuk isi lengkap.</p>`;
    }
    hasil += b;
  }
  return hasil;
}
