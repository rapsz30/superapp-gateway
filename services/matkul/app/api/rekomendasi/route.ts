import OpenAI from "openai";
import { NextResponse } from "next/server";
import type { NilaiUII } from "@/src/lib/uii-grade";
import { getMutu, getStatusLulus } from "@/src/lib/uii-grade";


export const runtime = "nodejs";

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

type KhsRow = { kode?: string; nama?: string; sks?: number; nilai?: string; semester?: string | number };
type KhsPreview = {
  mahasiswa?: { nama?: string; nim?: string; fakultas?: string; prodi?: string; semester?: string | number };
  nilai?: KhsRow[];
  ringkasan?: { total_sks?: number; total_mk?: number; ipk?: number | null };
};

const normalizeNilai = (n?: string): NilaiUII | null => {
  const s = String(n ?? "").trim().toUpperCase();
  if (!s) return null;
  const alias: Record<string, NilaiUII> = { "A/B": "A/B", "B/C": "B/C", "C/D": "C/D" };
  return (alias[s] ?? (s as NilaiUII)) || null;
};

const isPassed = (status: string) => String(status ?? "").toLowerCase().startsWith("lulus");

const parseSemester = (sem: any): number | null => {
  if (sem == null) return null;
  if (typeof sem === "number" && Number.isFinite(sem)) return sem;

  const s = String(sem).trim().toUpperCase();
  if (!s) return null;

  const m = s.match(/(?:SEM(?:ESTER)?\s*)?(\d{1,2})/i);
  if (m?.[1]) {
    const n = Number(m[1]);
    return Number.isFinite(n) && n > 0 ? n : null;
  }

  const roman: Record<string, number> = {
    I: 1, II: 2, III: 3, IV: 4, V: 5, VI: 6, VII: 7, VIII: 8, IX: 9, X: 10, XI: 11, XII: 12, XIII: 13, XIV: 14,
  };
  for (const t of s.split(/[\s\-_/]+/).filter(Boolean)) if (roman[t] != null) return roman[t];
  return null;
};

const calcSemesterTarget = (khs: KhsPreview, evaluated: any[]): number => {
  let mx = 0;
  for (const r of khs.nilai ?? []) {
    const sem = parseSemester(r.semester);
    if (sem && sem > mx) mx = sem;
  }
  if (mx > 0) return mx + 1;

  const totalSks = evaluated.reduce((a, r) => a + (Number(r.sks) || 0), 0);
  if (totalSks > 0) return Math.max(1, Math.min(14, Math.ceil(totalSks / 18) + 1));

  const msem = parseSemester(khs.mahasiswa?.semester);
  if (msem && msem > 0) return msem + 1;

  return 1;
};

const safeJson = (raw: string) => {
  try {
    return JSON.parse(raw);
  } catch {
    const s = raw.indexOf("{");
    const e = raw.lastIndexOf("}");
    if (s >= 0 && e > s) return JSON.parse(raw.slice(s, e + 1));
    throw new Error("AI output bukan JSON valid.");
  }
};

export async function POST(req: Request) {
  try {
    const { khs, panduan_text } = (await req.json()) as { khs?: KhsPreview; panduan_text?: string };
    if (!khs || !panduan_text) {
      return NextResponse.json({ error: "khs dan panduan_text wajib dikirim" }, { status: 400 });
    }

    const panduanText = String(panduan_text ?? "").trim();
    if (!panduanText) {
      return NextResponse.json(
        { error: "Teks panduan kosong. Pastikan PDF panduan berhasil diekstrak." },
        { status: 400 }
      );
    }

    const evaluatedRows = (khs.nilai ?? []).map((r) => {
      const nilaiNorm = normalizeNilai(r.nilai);
      const nilaiSafe = (nilaiNorm ?? "F") as NilaiUII;
      const mutu = getMutu(nilaiSafe);
      const status_lulus = getStatusLulus(nilaiSafe);

      return {
        kode: String(r.kode ?? "").trim(),
        nama: String(r.nama ?? "").trim(),
        sks: typeof r.sks === "number" ? r.sks : null,
        semester: r.semester ?? "",
        nilai: nilaiNorm ? nilaiSafe : String(r.nilai ?? "").trim() || "-",
        mutu,
        status_lulus,
        lulus: isPassed(status_lulus),
      };
    });

    const semesterTarget = calcSemesterTarget(khs, evaluatedRows);

    const repeatRows = evaluatedRows.filter((r) => r.status_lulus !== "Lulus");

    const totalSks = evaluatedRows.reduce((a, r) => a + (Number(r.sks) || 0), 0);
    const totalMk = evaluatedRows.length;
    const ipk = typeof khs.ringkasan?.ipk === "number" ? khs.ringkasan.ipk : null;

    const prompt = `
Kamu asisten akademik UII. WAJIB mengikuti PANDUAN AKADEMIK.

ATURAN NILAI:
- Nilai sudah dievaluasi sistem (mutu/status_lulus/lulus). JANGAN ubah.
- Tugasmu hanya memberi SARAN per mata kuliah + rekomendasi MATA KULIAH BARU untuk Semester ${semesterTarget}.
- JANGAN merekomendasikan mata kuliah yang sudah lulus (lulus=true).
- Mata kuliah yang statusnya "Tidak Lulus" atau "Lulus (bersyarat)" SUDAH otomatis ditandai sistem untuk diulang/diperbaiki — kamu TIDAK perlu memasukkannya ke "rekomendasi_semester_depan", cukup beri SARAN untuk masing-masing di "evaluasi_nilai".
- Gunakan angka total_sks, total_mk, dan ipk persis seperti yang diberikan di bawah ini saat menulis "ringkasan" — JANGAN mengarang angka lain.

PANDUAN AKADEMIK:
"""
${panduanText.slice(0, 120000)}
"""

DATA MAHASISWA:
${JSON.stringify(
  {
    nama: khs.mahasiswa?.nama ?? "",
    nim: khs.mahasiswa?.nim ?? "",
    fakultas: khs.mahasiswa?.fakultas ?? khs.mahasiswa?.prodi ?? "",
    total_sks: totalSks,
    total_mk: totalMk,
    ipk: ipk,
    semester_target: semesterTarget,
  },
  null,
  2
)}

DATA KHS (SUDAH DIEVALUASI):
${JSON.stringify(evaluatedRows, null, 2)}

MATA KULIAH YANG PERLU PERHATIAN (sudah ditandai sistem, beri saran spesifik untuk masing-masing):
${JSON.stringify(repeatRows.map((r) => ({ kode: r.kode, nama: r.nama, nilai: r.nilai, status_lulus: r.status_lulus })), null, 2)}

OUTPUT JSON VALID SAJA:
{
  "ringkasan": string,
  "evaluasi_nilai": [{"kode": string, "nama": string, "saran": string}],
  "rekomendasi_semester_depan": [{"kode": string, "nama": string, "sks": number|null, "alasan": string}]
}

ATURAN:
- "evaluasi_nilai" WAJIB berisi saran untuk SEMUA kode di "MATA KULIAH YANG PERLU PERHATIAN" di atas (jangan ada yang terlewat).
- "rekomendasi_semester_depan" HANYA berisi mata kuliah BARU (belum pernah diambil, dan bukan mata kuliah yang sudah lulus), sesuai urutan kurikulum di panduan akademik untuk Semester ${semesterTarget}.
`.trim();

    const completion = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || "gpt-4o-mini",
      temperature: 0.3,
      max_tokens: 1500,
      messages: [
        { role: "system", content: "Kamu asisten akademik yang patuh panduan akademik." },
        { role: "user", content: prompt },
      ],
    });

    const parsed = safeJson(completion.choices[0]?.message?.content?.trim() ?? "{}");

    //evaluasi nilai
    const aiEval = Array.isArray(parsed?.evaluasi_nilai) ? parsed.evaluasi_nilai : [];
    const aiSaranByKode = new Map(
      aiEval
        .map((x: any) => [String(x?.kode ?? "").toUpperCase().trim(), String(x?.saran ?? "").trim()] as const)
        .filter(([k]: [string, string]) => k)
    );

    const defaultSaran = (status_lulus: string) =>
      status_lulus === "Tidak Lulus"
        ? "Wajib diulang sesuai ketentuan panduan akademik."
        : "Lulus bersyarat. Disarankan diulang untuk memperbaiki nilai/IPK sesuai panduan akademik.";

    const autoEval = repeatRows.map((r) => ({
      kode: r.kode,
      nama: r.nama,
      nilai: r.nilai,
      mutu: r.mutu,
      status_lulus: r.status_lulus,
      lulus: r.lulus,
      saran: aiSaranByKode.get(r.kode.toUpperCase()) || defaultSaran(r.status_lulus),
    }));

    // ===== rekomendasi_semester_depan: (wajib/boleh diulang) + saran mata kuliah baru dari AI =====
    const repeatRekom = repeatRows.map((r) => ({
      kode: r.kode,
      nama: r.nama,
      sks: r.sks,
      alasan:
        r.status_lulus === "Tidak Lulus"
          ? `Nilai ${r.nilai} (Tidak Lulus) — wajib diulang sesuai panduan akademik.`
          : `Nilai ${r.nilai} (Lulus bersyarat) — disarankan diulang untuk memperbaiki IPK.`,
      jenis: "ulang" as const,
    }));

    const repeatKodes = new Set(repeatRekom.map((r) => r.kode.toUpperCase()));
    const passedKodes = new Set(
      evaluatedRows
        .filter((r) => r.lulus)
        .map((r) => String(r.kode ?? "").toUpperCase().trim())
        .filter(Boolean)
    );

    const aiRekomRaw = Array.isArray(parsed?.rekomendasi_semester_depan) ? parsed.rekomendasi_semester_depan : [];
    const newRekom = aiRekomRaw
      .map((x: any) => ({
        kode: String(x?.kode ?? "").trim(),
        nama: String(x?.nama ?? "").trim(),
        sks: typeof x?.sks === "number" ? x.sks : null,
        alasan: String(x?.alasan ?? "").trim(),
        jenis: "baru" as const,
      }))
      .filter((x: { kode: string }) => {
        const k = x.kode.toUpperCase();
        return k && !passedKodes.has(k) && !repeatKodes.has(k);
      });

    const rekomendasiSemesterDepan = [...repeatRekom, ...newRekom];

    return NextResponse.json({
      semester_target: semesterTarget,
      ringkasan: String(parsed?.ringkasan ?? "").trim(),
      evaluasi_nilai: autoEval,
      rekomendasi_semester_depan: rekomendasiSemesterDepan,
    });
  } catch (err: any) {
    return NextResponse.json({ error: err?.message ?? "Internal error" }, { status: 500 });
  }
}