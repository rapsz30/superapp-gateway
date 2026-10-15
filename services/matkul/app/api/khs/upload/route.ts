import { NextResponse } from "next/server";
import { createRequire } from "module";
import { extractKhsFromText } from "@/src/lib/openai";

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
  matkul?: Array<{ kode?: string; nama?: string; sks?: number; nilai?: string; semester?: any }>;

  _debugTextSample?: string;
};

function asNumber(x: any): number | null {
  if (typeof x === "number" && Number.isFinite(x)) return x;
  const n = Number(String(x ?? "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function normalizePreview(ai: any, text: string): KhsPreview {
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
    _debugTextSample: text.slice(0, 2000),
  };
}

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json({ ok: false, error: "file wajib PDF" }, { status: 400 });
    }

    const buf = Buffer.from(await file.arrayBuffer());

    const require = createRequire(import.meta.url);
    const pdfParse = require("pdf-parse/lib/pdf-parse.js");
    if (typeof pdfParse !== "function") {
      return NextResponse.json(
        { ok: false, error: "pdf-parse tidak terbaca sebagai function" },
        { status: 500 }
      );
    }

    const parsed = await pdfParse(buf);
    const text = String(parsed?.text ?? "").trim();
    console.log("=== PANJANG TEKS ===", text.length);
    console.log("=== TEKS MENTAH KHS ===");
    console.log(text);

    if (!text) {
      return NextResponse.json(
        { ok: false, error: "Teks PDF kosong. Jika scan, perlu OCR." },
        { status: 400 }
      );
    }

    // AI extract -> normalisasi ke format rekomendasi
    const ai = await extractKhsFromText(text);
    console.log("=== HASIL EKSTRAKSI AI ===");
    console.log(JSON.stringify(ai, null, 2));
    console.log("=== JUMLAH ROW ===", (ai?.nilai ?? ai?.matkul ?? []).length);
    const preview = normalizePreview(ai, text);

    // minimal validation biar ketahuan kalau AI gagal parse matkul
    if (!preview.nilai || preview.nilai.length === 0) {
      return NextResponse.json({
        ok: true,
        preview,
        warning: "AI tidak menemukan daftar mata kuliah. Cek format KHS / hasil ekstraksi.",
      });
    }

    return NextResponse.json({ ok: true, preview });
  } catch (err: any) {
    console.error("UPLOAD_KHS_ERROR:", err);
    return NextResponse.json({ ok: false, error: err?.message ?? "Unknown error" }, { status: 500 });
  }
}
