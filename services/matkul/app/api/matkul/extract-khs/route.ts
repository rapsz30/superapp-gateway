import { NextResponse } from "next/server";
import { createRequire } from "module";
import { extractKhsFromText } from "@/src/lib/openai";
import { evaluateRows } from "@/src/lib/proses/recommend";
import { hitungKeyakinan, nimCocok } from "@/src/lib/proses/keyakinan";
import { ambilKonteksPengajuan, periksaTokenLayanan } from "@/src/lib/proses/layanan";
import { calcRingkasan } from "@/src/lib/uii-grade";
import { newId, query } from "@/src/lib/proses/db";

export const runtime = "nodejs";

/**
 * POST /api/matkul/extract-khs  (token layanan)
 * { khs_file_id, semester_target, id_pengajuan }
 *   -> { khs_ref, ipk, sks_lulus, mk_lulus, mk_ulang, keyakinan, prodi, nim_cocok }
 *
 * `id_pengajuan` mengaitkan KHS dengan prodi mahasiswa: panduan aktif prodi itu diambil dari identity dan
 * DISIMPAN bersama KHS, sehingga rekomendasi dan semua revisi memakai versi panduan yang sama.
 * JSON lengkap (termasuk nama, NIM, DPA) hanya disimpan di PostgreSQL matkul, tidak dikirim keluar.
 */
export async function POST(req: Request) {
  const ditolak = periksaTokenLayanan(req);
  if (ditolak) return ditolak;
  try {
    const { khs_file_id, id_pengajuan } = (await req.json()) as {
      khs_file_id?: string;
      semester_target?: number;
      id_pengajuan?: string;
    };
    if (!khs_file_id) return NextResponse.json({ error: "khs_file_id wajib dikirim" }, { status: 400 });
    if (!id_pengajuan) return NextResponse.json({ error: "id_pengajuan wajib dikirim" }, { status: 400 });

    const [file] = await query<{ data: Buffer }>("SELECT data FROM matkul_file WHERE id = $1", [khs_file_id]);
    if (!file) return NextResponse.json({ error: "khs_file_id tidak ditemukan" }, { status: 404 });

    const konteks = await ambilKonteksPengajuan(id_pengajuan);

    const require = createRequire(import.meta.url);
    const pdfParse = require("pdf-parse/lib/pdf-parse.js");
    // Buffer dari pg bisa berupa potongan memori bersama; pdf-parse 1.1.1 (mesin PDF lama) kadang salah baca
    // ("bad XRef entry"). Salin ke buffer sendiri (Buffer.alloc tidak memakai pool) dan coba sekali lagi bila gagal.
    const parsePdf = async () => {
      const own = Buffer.alloc(file.data.length);
      file.data.copy(own);
      return String((await pdfParse(own))?.text ?? "").trim();
    };
    let text: string;
    try {
      text = await parsePdf();
    } catch {
      text = await parsePdf();
    }
    if (!text) {
      return NextResponse.json({ error: "Teks PDF kosong. Jika scan, perlu OCR." }, { status: 400 });
    }

    const khs = await extractKhsFromText(text);
    // KHS milik orang lain: keyakinan dipaksa 0 sehingga proses berhenti di langkah "Periksa" dan tidak
    // pernah sampai ke dosen sebagai rencana orang yang salah.
    const cocok = nimCocok(khs.mahasiswa.nim, konteks.mahasiswa?.nim);
    const keyakinan = cocok ? hitungKeyakinan(khs) : 0;

    const rows = evaluateRows(khs);
    const mk_lulus = rows.filter((r) => r.lulus).map((r) => r.kode);
    // mk_ulang = wajib diulang (E/F) + disarankan diulang (lulus bersyarat); mk_lulus tetap memuat yang bersyarat.
    const mk_ulang = rows.filter((r) => r.status_lulus !== "Lulus").map((r) => r.kode);
    // Dihitung dari baris nilai, bukan dari sksKumulatif hasil LLM: model kadang mengarang angka itu bila tidak tercetak di KHS.
    const sks_lulus = rows.filter((r) => r.lulus).reduce((a, r) => a + (r.sks ?? 0), 0);
    const ipk = khs.mahasiswa.ipk ?? calcRingkasan(khs.nilai).ipk;

    const khs_ref = newId("khs");
    await query(
      "INSERT INTO matkul_khs (ref, file_id, data, keyakinan, pengajuan_id, panduan_versi, panduan_teks, maks_sks) " +
        "VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
      [
        khs_ref,
        khs_file_id,
        JSON.stringify(khs),
        keyakinan,
        id_pengajuan,
        konteks.panduan.versi,
        konteks.panduan.teks,
        konteks.prodi.maks_sks_semester,
      ]
    );

    // prodi bukan data pribadi dan dibutuhkan untuk rekap laporan per program studi.
    return NextResponse.json({
      khs_ref,
      ipk,
      sks_lulus,
      mk_lulus,
      mk_ulang,
      keyakinan,
      prodi: konteks.prodi.nama,
      nim_cocok: cocok,
    });
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e));
    console.error("EXTRACT_KHS_ERROR:", err?.message);
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}
