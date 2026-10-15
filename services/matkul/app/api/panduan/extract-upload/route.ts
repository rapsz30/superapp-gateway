import { NextResponse } from "next/server";
import { extractTextFromPdfBuffer } from "@/src/lib/panduan-extract";

export const runtime = "nodejs";

const MAX_FILE_SIZE = 15 * 1024 * 1024; 

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file_pdf");

    if (!(file instanceof File) || file.size === 0) {
      return NextResponse.json({ error: "File PDF wajib diunggah." }, { status: 400 });
    }

    if (file.type !== "application/pdf") {
      return NextResponse.json({ error: "File harus berformat PDF." }, { status: 400 });
    }

    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json({ error: "Ukuran file maksimal 15MB." }, { status: 400 });
    }

    const buf = Buffer.from(await file.arrayBuffer());
    const text = await extractTextFromPdfBuffer(buf);

    if (!text) {
      return NextResponse.json(
        { error: "Teks PDF kosong (kemungkinan hasil scan/gambar)." },
        { status: 400 }
      );
    }

    const capped = text.slice(0, 120000);

    return NextResponse.json({
      ok: true,
      text: capped,
      extracted_chars: text.length,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}
