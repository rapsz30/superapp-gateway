import { NextResponse } from "next/server";
import { query } from "@/src/lib/proses/db";
import { periksaTokenLayanan } from "@/src/lib/proses/layanan";
import { buatRencana } from "@/src/lib/proses/rencana";

export const runtime = "nodejs";

/** POST /api/matkul/revise  { rencana_ref, catatan_dosen } -> format recommend, dengan rencana_ref baru (token layanan) */
export async function POST(req: Request) {
  const ditolak = periksaTokenLayanan(req);
  if (ditolak) return ditolak;
  try {
    const { rencana_ref, catatan_dosen } = (await req.json()) as { rencana_ref?: string; catatan_dosen?: string };
    if (!rencana_ref || !catatan_dosen?.trim()) {
      return NextResponse.json({ error: "rencana_ref dan catatan_dosen wajib dikirim" }, { status: 400 });
    }

    const [prev] = await query<{ khs_ref: string; semester_target: number | null; data: unknown; revisi_ke: number }>(
      "SELECT khs_ref, semester_target, data, revisi_ke FROM matkul_rencana WHERE ref = $1",
      [rencana_ref]
    );
    if (!prev) return NextResponse.json({ error: "rencana_ref tidak ditemukan" }, { status: 404 });

    const out = await buatRencana({
      khs_ref: prev.khs_ref,
      semester_target: prev.semester_target,
      parent: { ref: rencana_ref, revisi_ke: prev.revisi_ke, data: prev.data },
      catatan_dosen: catatan_dosen.trim(),
    });
    return NextResponse.json(out);
  } catch (e: unknown) {
    const err = e instanceof Error ? e : new Error(String(e));
    console.error("REVISE_ERROR:", err?.message);
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}
