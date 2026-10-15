"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { NilaiUII } from "@/src/lib/uii-grade";
import { badgeClass, getMutu, getStatusLulus } from "@/src/lib/uii-grade";
import { KEGIATAN_OPTIONS, KEGIATAN_KODE, loadNilaiKegiatanMap } from "@/src/lib/kegiatan-manual";

type KhsRow = {
  kode?: string;
  nama?: string;
  sks?: number;
  nilai?: string; // NilaiUII
  semester?: string | number | null;
};

type KhsPreview = {
  mahasiswa?: {
    nama?: string;
    nim?: string;
    jurusan?: string;
    prodi?: string;
  };
  ringkasan?: {
    total_sks?: number;
    total_mk?: number;
    ipk?: number; // IPK kumulatif
  };
  nilai?: KhsRow[];
};

type ApiResponse = {
  semester_target: number;
  ringkasan: string;
  evaluasi_nilai: Array<{
    kode: string;
    nama: string;
    nilai: string;
    mutu: string;
    status_lulus: string;
    lulus: boolean;
    saran: string;
  }>;
  rekomendasi_semester_depan: Array<{
    kode: string;
    nama: string;
    sks: number | null;
    alasan: string;
    jenis?: "ulang" | "baru";
  }>;
};

function parseSemester(sem: any): number | null {
  if (sem == null) return null;
  if (typeof sem === "number" && Number.isFinite(sem)) return sem;

  const raw = String(sem).trim();
  if (!raw) return null;
  const s = raw.toUpperCase();

  const m = s.match(/(?:SEM(?:ESTER)?\s*)?(\d{1,2})/i);
  if (m?.[1]) {
    const n = Number(m[1]);
    if (Number.isFinite(n) && n > 0) return n;
  }

  const roman: Record<string, number> = {
    I: 1,
    II: 2,
    III: 3,
    IV: 4,
    V: 5,
    VI: 6,
    VII: 7,
    VIII: 8,
    IX: 9,
    X: 10,
    XI: 11,
    XII: 12,
    XIII: 13,
    XIV: 14,
  };

  const tokens = s.split(/[\s\-_/]+/).filter(Boolean);
  for (const t of tokens) if (roman[t] != null) return roman[t];

  return null;
}

function normalizeNilai(n?: string): NilaiUII | null {
  const s = String(n ?? "").trim().toUpperCase();
  return s ? (s as NilaiUII) : null;
}

function Title({ children }: { children: React.ReactNode }) {
  return <h2 className="text-[20px] font-bold text-[#101828]">{children}</h2>;
}

function CardStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-5 flex flex-col items-center justify-center">
      <div className="text-[#101828] font-bold text-[18px] text-center">{label}</div>
      <div className="mt-2 text-[42px] font-bold text-[#101828] leading-none">{value}</div>
    </div>
  );
}

function KegiatanCard({
  label,
  kode,
  nilai,
}: {
  label: string;
  kode: string;
  nilai?: string;
}) {
  const hasValue = Boolean(nilai && nilai.trim());
  return (
    <div className="bg-white rounded-[12px] border border-[#E5E7EB] shadow-sm p-4 flex flex-col gap-2">
      <span className="w-fit text-xs font-bold text-[#1565C0] bg-[#EFF6FF] px-2 py-0.5 rounded">
        {kode}
      </span>
      <div className="text-sm text-[#101828] font-medium leading-snug">{label}</div>
      <div className="mt-auto text-[22px] font-bold text-[#101828]">
        {hasValue ? nilai : "-"}
      </div>
    </div>
  );
}

function NilaiBadge({ nilai }: { nilai: string }) {
  const n = normalizeNilai(nilai);
  const cn = n ? badgeClass(n) : "bg-black/10 text-black/70";
  return (
    <span className={`px-3 py-1 rounded-[10px] text-sm font-bold ${cn}`}>
      {nilai || "-"}
    </span>
  );
}

function CourseCard({
  kode,
  nama,
  sks,
  nilai,
}: {
  kode: string;
  nama: string;
  sks: number | null;
  nilai?: string;
}) {
  return (
    <div className="rounded-[14px] border border-[#E5E7EB] bg-[#F9FAFB] p-4 flex flex-col gap-3">
      <div>
        <div className="font-semibold text-[#101828] leading-snug">{nama || "-"}</div>
        <div className="text-xs text-[#4A5565] mt-1">{kode || "-"}</div>
      </div>
      <div className="flex items-center justify-between mt-auto">
        <span className="text-xs text-[#4A5565]">{sks != null ? `${sks} SKS` : "- SKS"}</span>
        <NilaiBadge nilai={String(nilai ?? "-")} />
      </div>
    </div>
  );
}
function TableMK({
  rows,
  showAlasan,
}: {
  rows: Array<{ kode: string; nama: string; sks: number | null; nilai?: string; alasan?: string }>;
  showAlasan?: boolean;
}) {
  return (
    <div className="p-6 overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-black text-white text-left">
            <th className="py-3 px-4 w-[70px] rounded-tl-[10px]">No</th>
            <th className="py-3 px-4 min-w-[280px]">Mata Kuliah</th>
            <th className="py-3 px-4 w-[90px]">SKS</th>
            {showAlasan ? (
              <th className="py-3 px-4 rounded-tr-[10px]">Alasan</th>
            ) : (
              <th className="py-3 px-4 w-[140px] rounded-tr-[10px]">Nilai</th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => (
            <tr
              key={`${r.kode}-${idx}`}
              className={idx % 2 === 0 ? "bg-white" : "bg-[#EFF6FF]"}
            >
              <td className="py-4 px-4 border-b border-[#93C5FD]">{idx + 1}</td>
              <td className="py-4 px-4 border-b border-[#93C5FD]">
                <div className="font-medium text-[#101828]">{r.nama}</div>
                <div className="text-xs text-[#4A5565] mt-1">{r.kode}</div>
              </td>
              <td className="py-4 px-4 border-b border-[#93C5FD]">{r.sks ?? "-"}</td>

              {showAlasan ? (
                <td className="py-4 px-4 border-b border-[#93C5FD] text-sm text-[#1565C0]">
                  {r.alasan || "-"}
                </td>
              ) : (
                <td className="py-4 px-4 border-b border-[#93C5FD]">
                  <NilaiBadge nilai={String(r.nilai ?? "-")} />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SectionCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-[18px] border border-[#DBEAFE] bg-[#F8FAFF] shadow-sm overflow-hidden">
      <div className="px-6 py-4 bg-[#1565C0] text-white">
        <div className="text-[18px] font-bold">{title}</div>
        {subtitle ? <div className="text-sm opacity-90 mt-1">{subtitle}</div> : null}
      </div>
      {children}
    </section>
  );
}

export default function RekomendasiPage() {
  const router = useRouter();

  const [khs, setKhs] = useState<KhsPreview | null>(null);
  const [data, setData] = useState<ApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [nilaiKegiatan, setNilaiKegiatan] = useState<Record<string, string>>({}); 

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("khs_preview");
      const panduanText = sessionStorage.getItem("panduan_text");
      setNilaiKegiatan(loadNilaiKegiatanMap()); 

      if (!raw) {
        setErr("KHS preview tidak ditemukan. Silakan unggah KHS lagi.");
        setLoading(false);
        return;
      }
      if (!panduanText) {
        setErr("Panduan akademik belum diunggah. Silakan unggah panduan dulu.");
        setLoading(false);
        return;
      }

      const parsed = JSON.parse(raw) as KhsPreview;
      setKhs(parsed);

      (async () => {
        setLoading(true);
        setErr("");
        try {
          const res = await fetch("/api/rekomendasi", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ khs: parsed, panduan_text: panduanText }),
          });
          const json = await res.json();
          if (!res.ok) throw new Error(json?.error ?? "Gagal memuat rekomendasi");
          setData(json as ApiResponse);
        } catch (e: any) {
          setErr(e?.message ?? "Gagal memuat rekomendasi");
        } finally {
          setLoading(false);
        }
      })();
    } catch {
      setErr("Data KHS tidak valid. Silakan unggah ulang.");
      setLoading(false);
    }
  }, []);

  const mahasiswaNama = khs?.mahasiswa?.nama || "Mahasiswa";
  const jurusan = khs?.mahasiswa?.jurusan ?? khs?.mahasiswa?.prodi ?? "-";
  const allRows = useMemo(() => khs?.nilai ?? [], [khs]);

  const stats = useMemo(() => {
    const totalMk = khs?.ringkasan?.total_mk ?? allRows.length;
    const totalSks =
      khs?.ringkasan?.total_sks ??
      allRows.reduce((acc, r) => acc + (typeof r.sks === "number" ? r.sks : 0), 0);

    const ipk =
      typeof khs?.ringkasan?.ipk === "number" ? khs.ringkasan.ipk.toFixed(2) : "-";

    return { totalMk, totalSks, ipk };
  }, [khs, allRows]);

  const semesterBlocks = useMemo(() => {
    const rows = allRows.map((r) => ({
      kode: String(r.kode ?? "").trim(),
      nama: String(r.nama ?? "").trim(),
      sks: typeof r.sks === "number" ? r.sks : null,
      nilai: String(r.nilai ?? "").trim(),
      semester: parseSemester(r.semester) ?? 0,
    }));

    const hasSemester = rows.some((r) => r.semester > 0);
    if (!hasSemester) {
      return [
        {
          key: "ALL",
          title: "Riwayat Mata Kuliah (Semua)",
          rows: rows.map((x) => ({ kode: x.kode, nama: x.nama, sks: x.sks, nilai: x.nilai })),
        },
      ];
    }

    const map = new Map<number, typeof rows>();
    const noSemesterRows: typeof rows = [];

    for (const r of rows) {
      if (r.semester <= 0) {
        noSemesterRows.push(r);
        continue;
      }
      if (!map.has(r.semester)) map.set(r.semester, []);
      map.get(r.semester)!.push(r);
    }

    const semesters = Array.from(map.keys()).sort((a, b) => b - a);
    const blocks = semesters.map((sem) => ({
      key: `SEM_${sem}`,
      title: `Semester ${sem}`,
      rows: map.get(sem)!.map((x) => ({ kode: x.kode, nama: x.nama, sks: x.sks, nilai: x.nilai })),
    }));

    if (noSemesterRows.length > 0) {
      blocks.push({
        key: "NO_SEM",
        title: "Mata Kuliah Tambahan (Tanpa Semester)",
        rows: noSemesterRows.map((x) => ({ kode: x.kode, nama: x.nama, sks: x.sks, nilai: x.nilai })),
      });
    }

    return blocks;
  }, [allRows]);

  const evaluasi = useMemo(() => {
    const list = data?.evaluasi_nilai ?? [];
    return list.map((x) => {
      const nilaiNorm = normalizeNilai(x.nilai);
      const nilaiSafe = (nilaiNorm ?? "F") as NilaiUII;
      return {
        ...x,
        status_lulus: x.status_lulus || getStatusLulus(nilaiSafe),
        mutu: x.mutu || getMutu(nilaiSafe),
      };
    });
  }, [data]);

  if (loading) {
    return (
      <main className="min-h-screen bg-white px-6 py-10">
        <div className="max-w-[1200px] mx-auto">
          <p className="text-[#4A5565]">Memuat rekomendasi...</p>
        </div>
      </main>
    );
  }

  if (err) {
    return (
      <main className="min-h-screen bg-white px-6 py-10">
        <div className="max-w-[1200px] mx-auto space-y-4">
          <p className="text-red-600 font-semibold">{err}</p>
          <button
            className="h-10 px-4 rounded bg-[#1565C0] text-white font-semibold"
            onClick={() => router.push("/khs/panduan")}
          >
            Kembali unggah panduan
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white px-6 py-10">
      <div className="max-w-[1200px] mx-auto space-y-8">
        {/* Header */}
        <div className="space-y-1">
          <h1 className="text-[36px] font-bold text-[#101828]">Halo, {mahasiswaNama}!</h1>
          <p className="text-[18px] text-[#101828]">
            Pantau perkembangan akademik Anda dengan mudah dan efisien.
          </p>
          <p className="text-sm text-[#4A5565]">
            Jurusan/Prodi: <b>{jurusan}</b>
          </p>
        </div>

        {/* Stats (NO IPS) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardStat label="Total SKS" value={stats.totalSks} />
          <CardStat label="Total Mata Kuliah" value={stats.totalMk} />
          <CardStat label="IPK Kumulatif" value={stats.ipk} />
        </div>
      {/* Nilai Kegiatan Non-Akademik (PDQ/PNDI/PKD/PPD/dst) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {KEGIATAN_OPTIONS.map((k) => (
            <KegiatanCard
              key={k}
              label={k}
              kode={KEGIATAN_KODE[k]}
              nilai={nilaiKegiatan[k]}
            />
          ))}
        </div>
        {/* Ringkasan AI */}
        <section className="rounded-[14px] border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <Title>Ringkasan</Title>
          <p className="mt-2 text-[#4A5565] leading-relaxed">{data?.ringkasan || "—"}</p>
        </section>

        {/* Mata Kuliah Perlu Diulang */}
        {(() => {
          const ulang = data?.rekomendasi_semester_depan?.filter((r) => r.jenis === "ulang") ?? [];
          if (ulang.length === 0) return null;
          return (
            <SectionCard
              title="Mata Kuliah Perlu Diulang"
              subtitle="Nilai belum memenuhi standar lulus penuh menurut panduan akademik."
            >
              <TableMK
                showAlasan
                rows={ulang.map((r) => ({
                  kode: r.kode,
                  nama: r.nama,
                  sks: r.sks,
                  alasan: r.alasan,
                }))}
              />
            </SectionCard>
          );
        })()}

        {/* Rekomendasi Mata Kuliah Baru */}
        <SectionCard
          title={`Semester ${data?.semester_target ?? "-"} (Mata Kuliah Baru)`}
          subtitle="Disusun berdasarkan panduan akademik yang kamu unggah."
        >
          {(() => {
            const baru = data?.rekomendasi_semester_depan?.filter((r) => r.jenis !== "ulang") ?? [];
            if (baru.length === 0) {
              return (
                <div className="p-6">
                  <p className="text-[#4A5565]">AI belum memberi rekomendasi mata kuliah baru.</p>
                </div>
              );
            }
            return (
              <TableMK
                showAlasan
                rows={baru.map((r) => ({
                  kode: r.kode,
                  nama: r.nama,
                  sks: r.sks,
                  alasan: r.alasan,
                }))}
              />
            );
          })()}
        </SectionCard>

        {/* Evaluasi Nilai & Saran */}
        <section className="rounded-[14px] border border-[#E5E7EB] bg-white p-6 shadow-sm">
          <Title>Evaluasi Nilai & Saran</Title>

          {evaluasi.length === 0 ? (
            <p className="mt-2 text-[#4A5565]">Tidak ada nilai yang perlu perhatian khusus.</p>
          ) : (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              {evaluasi.map((x) => (
                <div key={x.kode} className="rounded-[14px] border border-[#E5E7EB] p-4 bg-[#F9FAFB]">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold text-[#101828]">{x.nama}</div>
                      <div className="text-xs text-[#4A5565] mt-1">{x.kode}</div>
                      <div className="text-xs text-[#4A5565] mt-1">
                        Mutu: <b>{x.mutu}</b> • Status: <b>{x.status_lulus}</b>
                      </div>
                    </div>
                    <NilaiBadge nilai={x.nilai} />
                  </div>

                  {x.saran ? (
                    <p className="mt-3 text-sm text-[#1565C0] italic">{x.saran}</p>
                  ) : null}
                </div>
              ))}
            </div>
          )}
        </section>

{/* Progres Akademik */}
        <section className="space-y-4">
          <Title>Progres Akademik</Title>
          <div className="space-y-6">
            {semesterBlocks.map((b) => (
              <SectionCard key={b.key} title={b.title}>
                <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {b.rows.map((r, idx) => (
                    <CourseCard
                      key={`${r.kode}-${idx}`}
                      kode={r.kode}
                      nama={r.nama}
                      sks={r.sks}
                      nilai={r.nilai}
                    />
                  ))}
                </div>
              </SectionCard>
            ))}
          </div>
        </section>
        
        {/* Actions */}
        <div className="pt-2 flex flex-col sm:flex-row gap-3">
          <button
            className="h-11 px-5 rounded bg-[#1565C0] text-white font-semibold"
            onClick={() => router.push("/khs/panduan")}
          >
            Ganti Panduan Akademik
          </button>
          <button
            className="h-11 px-5 rounded border border-[#E5E7EB] text-[#101828] font-semibold"
            onClick={() => router.push("/khs/upload")}
          >
            Unggah KHS Baru
          </button>
        </div>
      </div>
    </main>
  );
}