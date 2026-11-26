import type { KhsPreview } from "../openai.ts";
import { extractKhsFromText } from "@/src/lib/openai";
import { bacaSekali, UMUR_BACAAN_HARI, type Penyimpanan } from "./bacaan";
import { query } from "./db";
import { bacaTeksPdf } from "./pdf";

const BATAS = `now() - interval '${UMUR_BACAAN_HARI} days'`;

const gudang: Penyimpanan = {
  async ambil(sidik) {
    const [row] = await query<{ data: KhsPreview }>(
      `SELECT data FROM matkul_bacaan WHERE sidik = $1 AND created_at > ${BATAS}`,
      [sidik],
    );
    return row?.data ?? null;
  },
  async simpan(sidik, hasil) {
    await query(`DELETE FROM matkul_bacaan WHERE created_at <= ${BATAS}`);
    await query("INSERT INTO matkul_bacaan (sidik, data) VALUES ($1, $2) ON CONFLICT (sidik) DO NOTHING", [
      sidik,
      JSON.stringify(hasil),
    ]);
    return (await this.ambil(sidik)) ?? hasil;
  },
};

/** Hasil bacaan tersimpan untuk sidik berkas tertentu. */
export const ambilBacaan = (sidik: string) => gudang.ambil(sidik);

/** Baca KHS dari PDF, memakai hasil tersimpan bila berkas yang sama sudah pernah dibaca. Null bila PDF tanpa teks. */
export async function bacaKhs(data: Buffer): Promise<KhsPreview | null> {
  const text = await bacaTeksPdf(data);
  if (!text) return null;
  return bacaSekali(data, () => extractKhsFromText(text), gudang);
}
