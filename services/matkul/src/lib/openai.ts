import OpenAI from "openai";

const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export type KhsRow = {
  kode: string;
  nama: string;
  sks: number | null;
  nilai: string;
  semester: string | number | null; 
}

export type KhsPreview = {
  mahasiswa: {
    nama: string | null;
    nim: string | null;
    fakultas: string | null;
    prodi: string | null;
    dpa: string | null;
    sksKumulatif: number | null;
    ipk: number | null;
    status: string | null;
  };

  nilai: KhsRow[];
};

function safeJsonParse(raw: string): any {
  const t = String(raw ?? "").trim();
  try {
    return JSON.parse(t);
  } catch {
    const s = t.indexOf("{");
    const e = t.lastIndexOf("}");
    if (s >= 0 && e > s) return JSON.parse(t.slice(s, e + 1));
    throw new Error("AI gagal mengembalikan JSON valid");
  }
}

export async function extractKhsFromText(text: string): Promise<KhsPreview> {
  const prompt = `
Kamu adalah ekstraktor data KHS (Kartu Hasil Studi). Keluarkan HANYA JSON valid (tanpa markdown, tanpa penjelasan).

FORMAT OUTPUT (JSON WAJIB):
{
  "mahasiswa": {
    "nama": string|null,
    "nim": string|null,
    "fakultas": string|null,
    "prodi": string|null,
    "dpa": string|null,
    "sksKumulatif": number|null,
    "ipk": number|null,
    "status": string|null
  },
  "nilai": [
    { "kode": string, "nama": string, "sks": number|null, "nilai": string, "semester": string|number|null }
  ]
}

ATURAN EKSTRAK:
- "nilai" berisi SEMUA mata kuliah yang ada di KHS.
- "semester" untuk setiap mata kuliah:
  - isi angka jika tertulis (mis "Semester 7" -> 7)
  - jika romawi, isi romawinya apa adanya (mis "VII")
  - jika hanya ada "Ganjil/Genap" + tahun (mis "2024/2025 Ganjil"), isi string itu
  - jika tidak ada info semester per matkul, boleh null
- "sks" boleh null jika tidak ditemukan.
- Jika data tidak ditemukan: gunakan null atau [] (jangan mengarang).

TEKS KHS:
"""
${text}
"""
`.trim();

  const res = await client.chat.completions.create({
    model: process.env.OPENAI_MODEL || "gpt-4o-mini",
    temperature: 0,
    max_tokens: 4000,
    messages: [
      { role: "system", content: "Keluarkan HANYA JSON valid sesuai format. Tanpa markdown." },
      { role: "user", content: prompt },
    ],
  });

  const content = res.choices[0]?.message?.content ?? "{}";
  const parsed = safeJsonParse(content);

  // hardening minimal: pastikan bentuknya sesuai
  const mahasiswa = parsed?.mahasiswa ?? {};
  const nilaiRaw = Array.isArray(parsed?.nilai) ? parsed.nilai : [];

  const nilai: KhsRow[] = nilaiRaw.map((r: any) => ({
    kode: String(r?.kode ?? "").trim(),
    nama: String(r?.nama ?? "").trim(),
    sks:
      typeof r?.sks === "number"
        ? r.sks
        : r?.sks == null
        ? null
        : Number.isFinite(Number(String(r.sks).replace(",", ".")))
        ? Number(String(r.sks).replace(",", "."))
        : null,
    nilai: String(r?.nilai ?? "").trim(),
    semester: r?.semester ?? null,
  }));

  return {
    mahasiswa: {
      nama: mahasiswa?.nama ?? null,
      nim: mahasiswa?.nim ?? null,
      fakultas: mahasiswa?.fakultas ?? null,
      prodi: mahasiswa?.prodi ?? null,
      dpa: mahasiswa?.dpa ?? null,
      sksKumulatif:
        typeof mahasiswa?.sksKumulatif === "number" ? mahasiswa.sksKumulatif : null,
      ipk: typeof mahasiswa?.ipk === "number" ? mahasiswa.ipk : null,
      status: mahasiswa?.status ?? null,
    },
    nilai,
  };
}
