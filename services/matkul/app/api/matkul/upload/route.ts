import { NextResponse } from "next/server";
import { newId, query } from "@/src/lib/proses/db";
import { periksaTokenLayanan } from "@/src/lib/proses/layanan";

export const runtime = "nodejs";

const MAX_FILE_SIZE = 15 * 1024 * 1024;

/**
 * POST /api/matkul/upload  (multipart, field "file"; token layanan)
 * Menyimpan PDF KHS di PostgreSQL matkul dan mengembalikan khs_file_id, yang menjadi variabel proses AlurKerja.
 * Dipanggil layanan identity saat mahasiswa memulai pengajuan, bukan langsung oleh browser.
 */
export async function POST(req: Request) {
  const ditolak = periksaTokenLayanan(req);
  if (ditolak) return ditolak;
  try {
    const form = await req.formData();
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) {
      return NextResponse.json({ error: "file PDF wajib diunggah" }, { status: 400 });
    }
    if (file.type !== "application/pdf") {
      return NextResponse.json({ error: "file harus berformat PDF" }, { status: 400 });
    }
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json({ error: "ukuran file maksimal 15MB" }, { status: 400 });
    }

    const id = newId("file");
    await query("INSERT INTO matkul_file (id, nama_file, data) VALUES ($1, $2, $3)", [
      id,
      file.name,
      Buffer.from(await file.arrayBuffer()),
    ]);
    return NextResponse.json({ khs_file_id: id });
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e));
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}
