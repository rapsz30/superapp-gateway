"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { NILAI_UII_OPTIONS, calcRingkasan, type NilaiUII } from "@/src/lib/uii-grade";

type Kegiatan =
  | "Pengembangan Diri Qur'ani"
  | "Student Soft Skill Development"
  | "Pelatihan Kepemimpinan dan Dakwah"
  | "Pendalaman Nilai Dasar Islam"
  | "Pelatihan Pengembangan Diri";

type NilaiManualKegiatan = {
  kegiatan: Kegiatan;
  kelasKelompok: string;
  nilaiAkhir: string;
  tahun: number | null;
};

type MataKuliahRow = {
  kode?: string;
  nama?: string;
  sks?: number | null;
  nilai?: string;
  semester?: string | number | null;
};

type KhsPreview = {
  mahasiswa?: Record<string, any>;
  nilai?: MataKuliahRow[];
};

const KEGIATAN_OPTIONS: Kegiatan[] = [
    "Pengembangan Diri Qur'ani",
    "Student Soft Skill Development",
    "Pelatihan Kepemimpinan dan Dakwah",
    "Pendalaman Nilai Dasar Islam",
    "Pelatihan Pengembangan Diri",
];

const STORAGE_KEY = "khs_nilai_manual_kegiatan";
const KHS_KEY = "khs_preview";

function isValidYear(y: number) {
  return Number.isFinite(y) && y >= 1900 && y <= 2100;
}

export default function NilaiManualPage() {
  const router = useRouter();

  // ----- Kegiatan non-akademik (form lama, tetap dipakai) -----
  const [items, setItems] = useState<NilaiManualKegiatan[]>([]);

  const [kegiatan, setKegiatan] = useState<Kegiatan>(KEGIATAN_OPTIONS[0]);
  const [kelasKelompok, setKelasKelompok] = useState("");
  const [nilaiAkhir, setNilaiAkhir] = useState("");
  const [tahun, setTahun] = useState<number | "">("");

  // ----- Nilai mata kuliah manual (baru) -----
  const [mahasiswa, setMahasiswa] = useState<Record<string, any>>({});
  const [mkRows, setMkRows] = useState<MataKuliahRow[]>([]);
  const [mkErr, setMkErr] = useState("");

  // load existing kegiatan
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) setItems(parsed);
    } catch {
      // ignore
    }
  }, []);

  // load existing KHS (mahasiswa + daftar mata kuliah hasil unggah/sebelumnya)
  useEffect(() => {
    try {
      const raw = sessionStorage.getItem(KHS_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as KhsPreview;
      setMahasiswa(parsed.mahasiswa ?? {});
      setMkRows(Array.isArray(parsed.nilai) ? parsed.nilai : []);
    } catch {
      // ignore
    }
  }, []);

  function save(next: NilaiManualKegiatan[]) {
    setItems(next);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  }

  function add() {
    const kk = kelasKelompok.trim();
    const na = nilaiAkhir.trim();
    const y = tahun === "" ? null : Number(tahun);

    if (!kk || !na) return;

    const row: NilaiManualKegiatan = {
      kegiatan,
      kelasKelompok: kk,
      nilaiAkhir: na,
      tahun: y != null && isValidYear(y) ? y : null,
    };

    save([row, ...items]);

    // reset ringan
    setKelasKelompok("");
    setNilaiAkhir("");
    setTahun("");
  }

  function removeAt(idx: number) {
    save(items.filter((_, i) => i !== idx));
  }

  const total = useMemo(() => items.length, [items]);

  // ----- Handler nilai mata kuliah manual -----
  function addMkRow() {
    setMkRows((prev) => [
      ...prev,
      { kode: "", nama: "", sks: null, nilai: "A", semester: "" },
    ]);
  }

  function updateMkRow(idx: number, patch: Partial<MataKuliahRow>) {
    setMkRows((prev) => prev.map((r, i) => (i === idx ? { ...r, ...patch } : r)));
  }

  function removeMkRow(idx: number) {
    setMkRows((prev) => prev.filter((_, i) => i !== idx));
  }

  const ringkasanPreview = useMemo(() => calcRingkasan(mkRows), [mkRows]);

  function goNext() {
    setMkErr("");

    const invalid = mkRows.some(
      (r) => !String(r.kode ?? "").trim() || !String(r.nama ?? "").trim()
    );
    if (invalid) {
      setMkErr("Kode dan nama mata kuliah tidak boleh kosong (hapus baris kosong, atau lengkapi dulu).");
      return;
    }

    // simpan perubahan nilai mata kuliah + ringkasan (IPK dihitung ulang)
    const normalized: KhsPreview & {
      ringkasan: { total_sks: number; total_mk: number; ipk: number | null };
    } = {
      mahasiswa,
      nilai: mkRows,
      ringkasan: calcRingkasan(mkRows),
    };
    sessionStorage.setItem(KHS_KEY, JSON.stringify(normalized));

    router.push("/khs/panduan");
  }

  return (
    <main className="min-h-screen bg-[#E8EAEE] flex justify-center py-10 px-4">
      <div className="w-full max-w-[1024px] space-y-6">
        {/* ===== Nilai Mata Kuliah (manual) ===== */}
        <div className="bg-white rounded-[14px] shadow-sm overflow-hidden">
          <div className="px-8 py-6">
            <h1 className="text-[24px] font-semibold text-[#101828]">
              Input/Edit Nilai Mata Kuliah
            </h1>
            <p className="text-[#4A5565] text-[16px]">
              Perbaiki hasil
              ekstraksi KHS sebelum lanjut ke rekomendasi.
            </p>
          </div>

          <div className="h-px bg-black/5" />

          <div className="px-8 py-6">
            {mkErr ? <p className="text-red-600 text-sm mb-4">{mkErr}</p> : null}

<div className="border border-[#E5E7EB] rounded-[10px] overflow-x-auto">
              <table className="w-full text-left min-w-[760px]">
                <thead className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  <tr className="text-[#364153] text-sm font-bold">
                    <th className="p-3 w-[64px]">No</th>
                    <th className="p-3 w-[120px]">Kode</th>
                                        <th className="p-3">Mata Kuliah</th>
                    <th className="p-3 w-[90px]">SKS</th>
                    <th className="p-3 w-[110px]">Nilai</th>
                    <th className="p-3 w-[80px]" />
                  </tr>
                </thead>
                <tbody>
                  {mkRows.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-3 text-[#4A5565]">
                        Belum ada mata kuliah. Tambahkan secara manual di bawah.
                      </td>
                    </tr>
                  ) : (
                    mkRows.map((r, i) => (
                      <tr key={i} className="border-b border-[#F3F4F6] last:border-b-0">
                        <td className="p-3 text-[#364153]">{i + 1}</td>
                        <td className="p-2">
                          <input
                            value={r.kode ?? ""}
                            onChange={(e) => updateMkRow(i, { kode: e.target.value })}
                            className="w-full h-9 px-2 rounded border border-[#E5E7EB]"
                            placeholder="IF1234"
                          />
                        </td>
                        <td className="p-2">
                          <input
                            value={r.nama ?? ""}
                            onChange={(e) => updateMkRow(i, { nama: e.target.value })}
                            className="w-full h-9 px-2 rounded border border-[#E5E7EB]"
                            placeholder="Nama mata kuliah"
                          />
                        </td>
                        <td className="p-2">
                          <input
                            type="number"
                            min={0}
                            value={r.sks ?? ""}
                            onChange={(e) =>
                              updateMkRow(i, {
                                sks: e.target.value === "" ? null : Number(e.target.value),
                              })
                            }
                            className="w-full h-9 px-2 rounded border border-[#E5E7EB]"
                          />
                        </td>
                        <td className="p-2">
                          <select
                            value={r.nilai ?? "A"}
                            onChange={(e) => updateMkRow(i, { nilai: e.target.value as NilaiUII })}
                            className="w-full h-9 px-2 rounded border border-[#E5E7EB] bg-white"
                          >
                            {NILAI_UII_OPTIONS.map((n) => (
                              <option key={n} value={n}>
                                {n}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td className="p-2">
                          <button
                            type="button"
                            onClick={() => removeMkRow(i)}
                            className="text-red-600 text-sm"
                          >
                            Hapus
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="rounded-[10px] border border-[#E5E7EB] bg-[#F9FAFB] p-4 text-center">
                <div className="text-sm text-[#4A5565]">Total SKS</div>
                <div className="text-[22px] font-bold text-[#101828]">
                  {ringkasanPreview.total_sks}
                </div>
              </div>
              <div className="rounded-[10px] border border-[#E5E7EB] bg-[#F9FAFB] p-4 text-center">
                <div className="text-sm text-[#4A5565]">Total Mata Kuliah</div>
                <div className="text-[22px] font-bold text-[#101828]">
                  {ringkasanPreview.total_mk}
                </div>
              </div>
              <div className="rounded-[10px] border border-[#E5E7EB] bg-[#F9FAFB] p-4 text-center">
                <div className="text-sm text-[#4A5565]">IPK (perkiraan)</div>
                <div className="text-[22px] font-bold text-[#101828]">
                  {ringkasanPreview.ipk != null ? ringkasanPreview.ipk.toFixed(2) : "-"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ===== Kegiatan non-akademik (form lama) ===== */}
        <div className="bg-white rounded-[14px] shadow-sm overflow-hidden">
        <div className="px-8 py-6">
          <h1 className="text-[24px] font-semibold text-[#101828]">
            Input Nilai Manual (Kegiatan)
          </h1>
          <p className="text-[#4A5565] text-[16px]">
            Isi kegiatan non-mata kuliah (cukup tahun saja untuk tanggal).
          </p>
        </div>

        <div className="h-px bg-black/5" />

        <div className="px-8 py-6">
          {/* Form */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="md:col-span-2">
              <label className="text-sm text-[#4A5565]">Nama kegiatan</label>
              <select
                value={kegiatan}
                onChange={(e) => setKegiatan(e.target.value as Kegiatan)}
                className="mt-1 w-full h-10 px-3 rounded border border-[#E5E7EB]"
              >
                {KEGIATAN_OPTIONS.map((k) => (
                  <option key={k} value={k}>
                    {k}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm text-[#4A5565]">Kelas/Kelompok</label>
              <input
                value={kelasKelompok}
                onChange={(e) => setKelasKelompok(e.target.value)}
                placeholder="PTA-N"
                className="mt-1 w-full h-10 px-3 rounded border border-[#E5E7EB]"
              />
            </div>

            <div>
              <label className="text-sm text-[#4A5565]">Tahun</label>
              <input
                type="number"
                value={tahun}
                onChange={(e) => {
                  const v = e.target.value;
                  setTahun(v === "" ? "" : Number(v));
                }}
                placeholder="2026"
                className="mt-1 w-full h-10 px-3 rounded border border-[#E5E7EB]"
              />
              <div className="mt-1 text-xs text-[#4A5565]">Opsional</div>
            </div>

            <div className="md:col-span-3">
              <label className="text-sm text-[#4A5565]">Nilai akhir</label>
              <input
                value={nilaiAkhir}
                onChange={(e) => setNilaiAkhir(e.target.value)}
                placeholder="A/Pradasar"
                className="mt-1 w-full h-10 px-3 rounded border border-[#E5E7EB]"
              />
            </div>

            <div className="flex items-end">
              <button
                type="button"
                onClick={add}
                className="w-full h-10 rounded bg-[#1565C0] text-white font-semibold"
              >
                Tambah
              </button>
            </div>
          </div>

          {/* List */}
          <div className="mt-8">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-[16px] font-medium text-[#101828]">
                Daftar Kegiatan
              </h2>
              <span className="text-sm text-[#4A5565]">Total: {total}</span>
            </div>

<div className="border border-[#E5E7EB] rounded-[10px] overflow-x-auto">
              <table className="w-full text-left min-w-[640px]">
                <thead className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  <tr className="text-[#364153] text-sm font-bold">
                    <th className="p-3 w-[64px]">No</th>
                    <th className="p-3">Kegiatan</th>
                                        <th className="p-3 w-[180px]">Kelas/Kelompok</th>
                    <th className="p-3 w-[140px]">Nilai akhir</th>
                    <th className="p-3 w-[100px]">Tahun</th>
                    <th className="p-3 w-[90px]" />
                  </tr>
                </thead>

                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-3 text-[#4A5565]">
                        Belum ada data.
                      </td>
                    </tr>
                  ) : (
                    items.map((x, i) => (
                      <tr
                        key={`${x.kegiatan}-${x.kelasKelompok}-${i}`}
                        className="border-b border-[#F3F4F6] last:border-b-0"
                      >
                        <td className="p-3 text-[#364153]">{i + 1}</td>
                        <td className="p-3 text-[#101828]">{x.kegiatan}</td>
                        <td className="p-3 text-[#364153]">{x.kelasKelompok}</td>
                        <td className="p-3 text-[#364153]">{x.nilaiAkhir}</td>
                        <td className="p-3 text-[#364153]">
                          {x.tahun ?? "-"}
                        </td>
                        <td className="p-3">
                          <button
                            type="button"
                            onClick={() => removeAt(i)}
                            className="text-red-600 text-sm"
                          >
                            Hapus
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Next step */}
            <button
              type="button"
              onClick={goNext}
              className="mt-6 h-[48px] w-full rounded-[10px] bg-[#1565C0] text-white font-bold"
            >
              Simpan & Lanjut Pilih Panduan
            </button>

            <button
              type="button"
              onClick={() => router.push("/khs/upload/file")}
              className="mt-3 w-full text-sm text-[#4A5565]"
            >
              Kembali
            </button>
          </div>
        </div>
      </div>
      </div>
    </main>
  );
}