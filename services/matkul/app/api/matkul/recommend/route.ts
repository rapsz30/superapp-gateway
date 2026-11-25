import { NextResponse } from "next/server";
import { periksaTokenLayanan } from "@/src/lib/proses/layanan";
import { buatRencana } from "@/src/lib/proses/rencana";

export const runtime = "nodejs";

/** POST /api/matkul/recommend  { khs_ref, semester_target } -> { rencana_ref, rencana_mk, total_sks, alasan, peringatan } (token layanan) */
export async function POST(req: Request) {
  const ditolak = periksaTokenLayanan(req);
  if (ditolak) return ditolak;
  try {
    const { khs_ref, semester_target } = (await req.json()) as { khs_ref?: string; semester_target?: number };
    if (!khs_ref) return NextResponse.json({ error: "khs_ref wajib dikirim" }, { status: 400 });

    const out = await buatRencana({ khs_ref, semester_target });
    if (!out) return NextResponse.json({ error: "khs_ref tidak ditemukan" }, { status: 404 });
    return NextResponse.json(out);
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e));
    console.error("RECOMMEND_ERROR:", err?.message);
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}
