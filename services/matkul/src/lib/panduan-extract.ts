import { createRequire } from "module";

function normalizeText(s: string) {
  return s
    .replace(/\r/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
}

export async function extractTextFromPdfBuffer(
  buf: Buffer
): Promise<string> {
  const require = createRequire(import.meta.url);
  const pdfParse = require("pdf-parse/lib/pdf-parse.js");

  const data = await pdfParse(buf);

  return normalizeText(data?.text ?? "");
}