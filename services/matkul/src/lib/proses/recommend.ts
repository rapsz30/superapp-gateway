import OpenAI from "openai";
import type { NilaiUII } from "../uii-grade.ts";
import { getMutu, getStatusLulus } from "../uii-grade.ts";

// Logika dipindahkan apa adanya dari app/api/rekomendasi/route.ts.
// Satu-satunya tambahan: semesterTarget bisa ditentukan pemanggil, dan blok
// catatan dosen PA (hanya dipakai saat revisi).

export type KhsRow = { kode?: string; nama?: string; sks?: number | null; nilai?: string; semester?: string | number | null };
export type KhsPreview = {
  mahasiswa?: { nama?: string | null; nim?: string | null; fakultas?: string | null; prodi?: string | null; semester?: string | number | null; ipk?: number | null };
  nilai?: KhsRow[];
  ringkasan?: { total_sks?: number; total_mk?: number; ipk?: number | null };
};

export type RekomItem = {
  kode: string;
  nama: string;
  sks: number | null;
  alasan: string;
  jenis: "ulang" | "baru";
};

export type RecommendResult = {
  semester_target: number;
  ringkasan: string;
  evaluasi_nilai: any[];
  rekomendasi_semester_depan: RekomItem[];
};

let _openai: OpenAI | null = null;
const openai = () => (_openai ??= new OpenAI({ apiKey: process.env.OPENAI_API_KEY }));

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

/** Baris KHS yang sudah dievaluasi (mutu, status lulus) — dipakai juga oleh endpoint extract-khs. */
export function evaluateRows(khs: KhsPreview) {
  return (khs.nilai ?? []).map((r) => {
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
}

export async function recommendCourses(opts: {
  khs: KhsPreview;
  panduanText: string;
  semesterTarget?: number | null;
  /** Hanya untuk revisi. */
  catatanDosen?: string;
  /** Batas SKS per semester menurut panduan prodi (bawaan 24). */
  maksSksPanduan?: number | null;
  rencanaSebelumnya?: unknown;
}): Promise<RecommendResult> {
  const { khs, catatanDosen } = opts;
  const panduanText = String(opts.panduanText ?? "").trim();
  if (!panduanText) throw new Error("Teks panduan kosong.");

  const evaluatedRows = evaluateRows(khs);

  const semesterTarget =
    opts.semesterTarget && opts.semesterTarget > 0 ? opts.semesterTarget : calcSemesterTarget(khs, evaluatedRows);

  const repeatRows = evaluatedRows.filter((r) => r.status_lulus !== "Lulus");

  const totalSks = evaluatedRows.reduce((a, r) => a + (Number(r.sks) || 0), 0);
  const totalMk = evaluatedRows.length;
  const ipk =
    typeof khs.ringkasan?.ipk === "number"
      ? khs.ringkasan.ipk
      : typeof khs.mahasiswa?.ipk === "number"
      ? khs.mahasiswa.ipk
      : null;

  const revisiBlock = catatanDosen
    ? `
CATATAN DOSEN PA (WAJIB DIPATUHI, ini permintaan revisi atas rencana sebelumnya):
"""
${catatanDosen}
"""

RENCANA SEBELUMNYA (revisi dari rencana ini):
${JSON.stringify(opts.rencanaSebelumnya ?? null, null, 2)}
`
    : "";

  // Hanya untuk revisi: ditaruh di AKHIR prompt supaya tidak dikalahkan aturan di atasnya.
  const repeatSks = repeatRows.reduce((a, r) => a + (Number(r.sks) || 0), 0);
  const aturanRevisi = catatanDosen
    ? `

ATURAN REVISI (PRIORITAS TERTINGGI, mengalahkan aturan lain bila bertentangan):
- Ini revisi atas rencana sebelumnya berdasarkan catatan dosen PA: "${catatanDosen}".
- Mata kuliah ulang/perbaikan otomatis dimasukkan sistem ke rencana (${repeatRows.length} mata kuliah, total ${repeatSks} SKS) dan SUDAH dihitung dalam total SKS rencana. Jangan memasukkannya lagi ke "rekomendasi_semester_depan".
- Susun ulang "rekomendasi_semester_depan" (hanya mata kuliah BARU) agar TOTAL SKS rencana akhir (SKS mata kuliah ulang di atas + SKS mata kuliah baru yang kamu pilih) memenuhi catatan dosen. Jika catatan membatasi SKS, kurangi mata kuliah baru (utamakan yang wajib/prasyarat) sampai batas terpenuhi; boleh mengosongkan daftar bila perlu.
- Tulis di "ringkasan" bagaimana catatan dosen diterapkan.`
    : "";

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
${revisiBlock}
OUTPUT JSON VALID SAJA:
{
  "ringkasan": string,
  "evaluasi_nilai": [{"kode": string, "nama": string, "saran": string}],
  "rekomendasi_semester_depan": [{"kode": string, "nama": string, "sks": number|null, "alasan": string}]
}

ATURAN:
- "evaluasi_nilai" WAJIB berisi saran untuk SEMUA kode di "MATA KULIAH YANG PERLU PERHATIAN" di atas (jangan ada yang terlewat).
- "rekomendasi_semester_depan" HANYA berisi mata kuliah BARU (belum pernah diambil, dan bukan mata kuliah yang sudah lulus), sesuai urutan kurikulum di panduan akademik untuk Semester ${semesterTarget}.${aturanRevisi}
`.trim();

  const completion = await openai().chat.completions.create({
    model: process.env.LLM_MODEL || process.env.OPENAI_MODEL || "gpt-4o-mini",
    temperature: 0.3,
    max_tokens: 1500,
    messages: [
      { role: "system", content: "Kamu asisten akademik yang patuh panduan akademik." },
      { role: "user", content: prompt },
    ],
  });

  const parsed = safeJson(completion.choices[0]?.message?.content?.trim() ?? "{}");

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

  const repeatRekom: RekomItem[] = repeatRows.map((r) => ({
    kode: r.kode,
    nama: r.nama,
    sks: r.sks,
    alasan:
      r.status_lulus === "Tidak Lulus"
        ? `Nilai ${r.nilai} (Tidak Lulus) — wajib diulang sesuai panduan akademik.`
        : `Nilai ${r.nilai} (Lulus bersyarat) — disarankan diulang untuk memperbaiki IPK.`,
    jenis: "ulang",
  }));

  const repeatKodes = new Set(repeatRekom.map((r) => r.kode.toUpperCase()));
  const passedKodes = new Set(
    evaluatedRows
      .filter((r) => r.lulus)
      .map((r) => String(r.kode ?? "").toUpperCase().trim())
      .filter(Boolean)
  );

  const aiRekomRaw = Array.isArray(parsed?.rekomendasi_semester_depan) ? parsed.rekomendasi_semester_depan : [];
  const newRekom: RekomItem[] = aiRekomRaw
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

  let ringkasan = String(parsed?.ringkasan ?? "").trim();

  // Pengaman beban SKS (deterministik; LLM kadang melanggar): batas panduan akademik 24 SKS per semester,
  // atau batas lebih kecil bila catatan dosen menyebutnya ("maksimal 18 SKS"). Yang dipangkas hanya
  // mata kuliah BARU dari belakang; mata kuliah ulang tidak disentuh.
  const batasCatatan = catatanDosen ? catatanDosen.match(/maks(?:imal|imum)?\.?\s*(\d{1,2})\s*sks/i) : null;
  const dariCatatan = batasCatatan ? Number(batasCatatan[1]) : undefined;
  const batasPanduan = opts.maksSksPanduan && opts.maksSksPanduan > 0 ? opts.maksSksPanduan : MAKS_SKS_SEMESTER;
  const batas = terapkanBatasSks(repeatRekom, newRekom, dariCatatan, batasPanduan);
  const baru = batas.baru;
  if (batas.dipangkas) {
    ringkasan +=
      dariCatatan !== undefined && dariCatatan < batasPanduan
        ? ` Rencana disesuaikan agar total tidak melebihi ${batas.max} SKS sesuai catatan pembimbing akademik.`
        : ` Rencana disesuaikan agar total tidak melebihi ${batas.max} SKS per semester sesuai panduan akademik.`;
  }

  return {
    semester_target: semesterTarget,
    ringkasan,
    evaluasi_nilai: autoEval,
    rekomendasi_semester_depan: [...repeatRekom, ...baru],
  };
}

/** Batas bawaan beban studi per semester (24 SKS, panduan Informatika) bila prodi belum menetapkan batasnya. */
export const MAKS_SKS_SEMESTER = 24;

/**
 * Memangkas mata kuliah baru dari belakang sampai total (ulang + baru) tidak melebihi batas.
 * Batas = batas panduan (24), atau batas catatan dosen bila lebih kecil. Mata kuliah ulang tidak dipangkas.
 */
export function terapkanBatasSks<T extends { sks: number | null }>(
  ulang: T[],
  baru: T[],
  batasCatatan?: number,
  batasPanduan: number = MAKS_SKS_SEMESTER,
): { baru: T[]; max: number; dipangkas: boolean } {
  const max = Math.min(batasCatatan ?? batasPanduan, batasPanduan);
  let total = [...ulang, ...baru].reduce((a, r) => a + (r.sks ?? 0), 0);
  const hasil = [...baru];
  let dipangkas = false;
  while (hasil.length > 0 && total > max) {
    total -= hasil.pop()?.sks ?? 0;
    dipangkas = true;
  }
  return { baru: hasil, max, dipangkas };
}
