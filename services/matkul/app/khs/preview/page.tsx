"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { calcRingkasan } from "@/src/lib/uii-grade";

type KhsRow = {
  kode?: string;
  nama?: string;
  sks?: number | null;
  nilai?: string;
  semester?: string | number | null;
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
    status?: "Aktif" | "Nonaktif" | string | null;
  };
  // format baru (dipakai rekomendasi)
  nilai?: KhsRow[];
  // format lama (compat)
  matkul?: Array<{ kode: string; nama: string; sks: number; nilai: string }>;
  ringkasan?: {
    total_sks?: number;
    total_mk?: number;
    ipk?: number | null;
  };
};

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[#4A5565] text-[16px] leading-[24px]">{label}</div>
      <div className="text-[#101828] text-[16px] leading-[24px]">{value}</div>
    </div>
  );
}

function BadgeStatus({ status }: { status?: string | null }) {
  const isAktif = (status ?? "").toLowerCase() === "aktif";
  return isAktif ? (
    <span className="inline-flex items-center px-3 h-8 rounded-full bg-[#DCFCE7] text-[#016630] text-[16px] leading-[24px]">
      Aktif
    </span>
  ) : (
    <span className="inline-flex items-center px-3 h-8 rounded-full bg-black/10 text-black/70 text-[16px] leading-[24px]">
      Nonaktif
    </span>
  );
}

export default function PreviewPage() {
  const router = useRouter();
  const [data, setData] = useState<KhsPreview | null>(null);

  useEffect(() => {
    const raw = sessionStorage.getItem("khs_preview");
    if (!raw) return;
    try {
      setData(JSON.parse(raw));
    } catch {
      setData(null);
    }
  }, []);

  const rows: KhsRow[] = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data.nilai) && data.nilai.length > 0) return data.nilai;

    // compat: convert matkul -> nilai
    if (Array.isArray(data.matkul) && data.matkul.length > 0) {
      return data.matkul.map((m) => ({ ...m, semester: null }));
    }
    return [];
  }, [data]);

  const showSemesterCol = useMemo(
    () => rows.some((r) => r.semester != null && String(r.semester).trim() !== ""),
    [rows]
  );

  if (!data) return <p className="text-center mt-20">Data tidak ditemukan</p>;

  const m = data.mahasiswa ?? {};

  function confirmKhs() {
    sessionStorage.setItem("khs_confirmed", "true");

    // hitung ulang ringkasan (total SKS, total MK, IPK) dari baris nilai final
    const ringkasan = calcRingkasan(rows);

    // simpan format konsisten supaya step berikutnya aman
    const normalized: KhsPreview = {
      mahasiswa: m,
      nilai: rows,
      ringkasan,
    };
    sessionStorage.setItem("khs_preview", JSON.stringify(normalized));

    router.push("/khs/nilai-manual");
  }

  return (
    <main className="min-h-screen bg-[#E8EAEE] flex justify-center py-10 px-4">
      <div className="w-full max-w-[1024px] bg-white rounded-[14px] border border-[#F3F4F6] shadow-sm overflow-hidden">
        {/* header */}
<div className="px-5 sm:px-8 py-6">
            <h1 className="text-[24px] leading-[36px] text-[#101828]">Preview KHS</h1>
          <p className="text-[#4A5565] text-[16px] leading-[24px]">
            Pastikan data hasil ekstraksi sudah benar sebelum melanjutkan.
          </p>
        </div>

        <div className="h-px bg-[#E5E7EB]" />

<div className="px-5 sm:px-8 py-8 space-y-8">
            {/* Informasi Mahasiswa */}
          <section className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-[10px] p-6">
            <h2 className="text-[16px] leading-[24px] text-[#101828] mb-6">
              Informasi Mahasiswa
            </h2>

            <div className="grid grid-cols-2 gap-x-8 gap-y-5">
              <InfoItem label="Nama" value={m.nama ?? "-"} />
              <InfoItem label="NIM" value={m.nim ?? "-"} />
              <InfoItem label="Fakultas" value={m.fakultas ?? "-"} />
              <InfoItem label="Program Studi" value={m.prodi ?? "-"} />
              <InfoItem label="DPA" value={m.dpa ?? "-"} />
              <InfoItem
                label="SKS Kumulatif"
                value={m.sksKumulatif != null ? `${m.sksKumulatif} SKS` : "-"}
              />
              <InfoItem label="IPK" value={m.ipk != null ? String(m.ipk) : "-"} />

              <div className="flex flex-col gap-2">
                <div className="text-[#4A5565] text-[16px] leading-[24px]">Status</div>
                <BadgeStatus status={m.status} />
              </div>
            </div>
          </section>

          {/* Daftar Mata Kuliah */}
          <section className="space-y-4">
            <h2 className="text-[16px] leading-[24px] text-[#101828]">Daftar Mata Kuliah</h2>

<div className="border border-[#E5E7EB] rounded-[10px] overflow-x-auto">
              <table className="w-full text-left min-w-[640px]">
                                <thead className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
                  <tr className="text-[#364153] text-[16px] font-bold">
                    <th className="p-3 w-[64px]">No</th>
                    <th className="p-3 w-[128px]">Kode</th>
                    <th className="p-3">Mata Kuliah</th>
                    <th className="p-3 w-[96px]">SKS</th>
                    <th className="p-3 w-[96px]">Nilai</th>
                    {showSemesterCol && <th className="p-3 w-[140px]">Semester</th>}
                  </tr>
                </thead>

                <tbody>
                  {rows.length > 0 ? (
                    rows.map((x, i) => (
                      <tr
                        key={`${x.kode ?? "NA"}-${i}`}
                        className="border-b border-[#F3F4F6] last:border-b-0 text-[16px]"
                      >
                        <td className="p-3 text-[#364153]">{i + 1}</td>
                        <td className="p-3 text-[#364153]">{x.kode ?? "-"}</td>
                        <td className="p-3 text-[#101828]">{x.nama ?? "-"}</td>
                        <td className="p-3 text-[#364153]">
                          {x.sks != null ? String(x.sks) : "-"}
                        </td>
                        <td className="p-3">
                          <span className="inline-flex items-center justify-center px-2 h-7 rounded bg-[#EFF6FF] text-[#1447E6]">
                            {x.nilai ?? "-"}
                          </span>
                        </td>
                        {showSemesterCol && (
                          <td className="p-3 text-[#364153]">
                            {x.semester != null && String(x.semester).trim() !== ""
                              ? String(x.semester)
                              : "-"}
                          </td>
                        )}
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="p-3 text-[#4A5565]" colSpan={showSemesterCol ? 6 : 5}>
                        Tidak ada data mata kuliah.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {/* tombol bawah */}
          <button
            type="button"
            onClick={confirmKhs}
            className="h-[48px] w-full rounded-[10px] bg-[#1565C0] text-white font-bold text-[16px] leading-[24px]"
          >
            Unggah
          </button>
        </div>
      </div>
    </main>
  );
}