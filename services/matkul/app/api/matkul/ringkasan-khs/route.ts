import { NextResponse } from "next/server";
import { query } from "@/src/lib/proses/db";
import { periksaTokenLayanan } from "@/src/lib/proses/layanan";
import { bangunRingkasanAkademik } from "@/src/lib/proses/ringkasan";
import type { KhsPreview } from "@/src/lib/proses/recommend";

export const runtime = "nodejs";

/**
 * POST /api/matkul/ringkasan-khs  { khs_ref } -> ringkasan nilai tanpa nama dan NIM (token layanan).
 * Dipanggil identity untuk dasbor mahasiswa; identity yang memeriksa kepemilikan.
 */
export async function POST(req: Request) {
  const ditolak = periksaTokenLayanan(req);
  if (ditolak) return ditolak;
  try {
    const { khs_ref } = (await req.json()) as { khs_ref?: string };
    if (!khs_ref) return NextResponse.json({ error: "khs_ref wajib dikirim" }, { status: 400 });

    const [row] = await query<{ data: KhsPreview }>("SELECT data FROM matkul_khs WHERE ref = $1", [khs_ref]);
    if (!row) return NextResponse.json({ error: "khs_ref tidak ditemukan" }, { status: 404 });
    return NextResponse.json(bangunRingkasanAkademik(row.data));
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e));
    console.error("RINGKASAN_KHS_ERROR:", err?.message);
    return NextResponse.json({ error: "Ringkasan nilai tidak dapat disusun." }, { status: 500 });
  }
}
