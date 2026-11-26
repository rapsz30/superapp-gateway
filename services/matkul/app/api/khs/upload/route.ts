import { NextResponse } from "next/server";
import { sidikBerkas } from "@/src/lib/proses/bacaan";
import { bacaKhs } from "@/src/lib/proses/bacaan-db";

export const runtime = "nodejs";

type KhsRow = {
  kode?: string;
  nama?: string;
  sks?: number;
  nilai?: string;
  semester?: string | number;
};

type KhsPreview = {
  mahasiswa?: {
    nama?: string | null;
    nim?: string | null;
    fakultas?: string | null;
    prodi?: string | null;
    dpa?: string | null;
    sksKumulatif?: number | null;
    ipk?: number | null;
    status?: string | null;
    semester?: string | number | null; // optional fallback
  };
  // IMPORTANT: ini yang dipakai route rekomendasi
  nilai?: KhsRow[];

  // fallback compat (kalau AI masih return "matkul")
  matkul?: Array<{
    kode?: string;
    nama?: string;
    sks?: number;
    nilai?: string;
    semester?: any;
  }>;
};

function asNumber(x: any): number | null {
  if (typeof x === "number" && Number.isFinite(x)) return x;
  const n = Number(String(x ?? "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function normalizePreview(ai: any): KhsPreview {
  const p: KhsPreview = ai && typeof ai === "object" ? ai : {};

  // sumber rows bisa "nilai" atau "matkul"
  const rowsRaw: any[] = Array.isArray(p.nilai)
    ? p.nilai
    : Array.isArray(p.matkul)
      ? p.matkul
      : [];

  const rows: KhsRow[] = rowsRaw.map((r: any) => ({
    kode: String(r?.kode ?? "").trim(),
    nama: String(r?.nama ?? "").trim(),
    sks: asNumber(r?.sks) ?? undefined,
    nilai: String(r?.nilai ?? "").trim(),
    semester: r?.semester ?? "", // biarkan kosong kalau memang tidak ada
  }));

  return {
    mahasiswa: {
      nama: p.mahasiswa?.nama ?? null,
      nim: p.mahasiswa?.nim ?? null,
      fakultas: p.mahasiswa?.fakultas ?? null,
      prodi: p.mahasiswa?.prodi ?? null,
      dpa: p.mahasiswa?.dpa ?? null,
      sksKumulatif: asNumber(p.mahasiswa?.sksKumulatif),
      ipk: asNumber(p.mahasiswa?.ipk),
      status: p.mahasiswa?.status ?? null,
      semester: p.mahasiswa?.semester ?? null,
    },
    nilai: rows,
  };
}

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json(
        { ok: false, error: "file wajib PDF" },
        { status: 400 },
      );
    }

    const buf = Buffer.from(await file.arrayBuffer());

    // Hasil bacaan disimpan dan dipakai lagi oleh proses pengajuan, sehingga KHS yang sama dibaca satu kali.
    const khs = await bacaKhs(buf);
    if (!khs) {
      return NextResponse.json(
        { ok: false, error: "Teks PDF kosong. Jika scan, perlu OCR." },
        { status: 400 },
      );
    }
    const preview = normalizePreview(khs);

    // minimal validation biar ketahuan kalau AI gagal parse matkul
    if (!preview.nilai || preview.nilai.length === 0) {
      return NextResponse.json({
        ok: true,
        preview,
        warning:
          "AI tidak menemukan daftar mata kuliah. Cek format KHS / hasil ekstraksi.",
      });
    }

    return NextResponse.json({ ok: true, preview, sidik: sidikBerkas(buf) });
  } catch (err: any) {
    console.error("UPLOAD_KHS_ERROR:", err);
    return NextResponse.json(
      { ok: false, error: err?.message ?? "Unknown error" },
      { status: 500 },
    );
  }
}
