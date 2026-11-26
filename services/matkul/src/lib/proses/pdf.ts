import { execFile } from "node:child_process";
import { createRequire } from "node:module";

type Pembaca = (data: Buffer) => Promise<string>;

const lewatPdfParse: Pembaca = async (data) => {
  const require = createRequire(import.meta.url);
  const pdfParse = require("pdf-parse/lib/pdf-parse.js");
  // Buffer dari pg bisa berupa potongan memori bersama; salin ke buffer sendiri (Buffer.alloc tidak memakai pool).
  const own = Buffer.alloc(data.length);
  data.copy(own);
  return String((await pdfParse(own))?.text ?? "");
};

const lewatPdftotext: Pembaca = (data) =>
  new Promise((resolve, reject) => {
    const anak = execFile(
      process.env.PDFTOTEXT_PATH || "pdftotext",
      ["-layout", "-enc", "UTF-8", "-", "-"],
      { timeout: 30_000, maxBuffer: 10 * 1024 * 1024 },
      (galat, keluaran) => (galat ? reject(galat) : resolve(String(keluaran))),
    );
    anak.stdin?.on("error", () => undefined); // galat sebenarnya dilaporkan lewat callback di atas
    anak.stdin?.end(data);
  });

/**
 * Teks sebuah PDF. pdf-parse 1.1.1 (mesin PDF lama) kadang gagal ("bad XRef entry") pada pembacaan pertama
 * setelah proses dimulai, jadi dicoba dua kali, lalu memakai pdftotext (tersedia di image Docker).
 */
export async function bacaTeksPdf(
  data: Buffer,
  utama: Pembaca = lewatPdfParse,
  cadangan: Pembaca = lewatPdftotext,
): Promise<string> {
  let galatUtama: unknown;
  for (let i = 0; i < 2; i++) {
    try {
      return (await utama(data)).trim();
    } catch (e) {
      galatUtama = e;
    }
  }
  try {
    return (await cadangan(data)).trim();
  } catch {
    throw galatUtama; // pesan pembaca utama lebih menjelaskan daripada "pdftotext tidak ada"
  }
}
