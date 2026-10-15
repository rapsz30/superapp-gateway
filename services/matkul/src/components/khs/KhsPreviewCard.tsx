export type KhsCourseRow = {
  kode: string;
  mataKuliah: string;
  sks: number;
  nilai: string;
};

export type KhsPreviewData = {
  mahasiswa: {
    nama: string;
    nim: string;
    fakultas: string;
    prodi: string;
    dpa: string;
    sksKumulatif: number;
    ipk: number;
    status: "Aktif" | "Nonaktif";
  };
  matkul: KhsCourseRow[];
};

function BadgeStatus({ status }: { status: KhsPreviewData["mahasiswa"]["status"] }) {
  return status === "Aktif" ? (
    <span className="inline-flex items-center px-3 h-8 rounded-full bg-[#DCFCE7] text-[#016630] text-[16px] leading-[24px]">
      Aktif
    </span>
  ) : (
    <span className="inline-flex items-center px-3 h-8 rounded-full bg-black/10 text-black/70 text-[16px] leading-[24px]">
      Nonaktif
    </span>
  );
}

function InfoItem({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="text-[#4A5565] text-[16px] leading-[24px]">{label}</div>
      <div className="text-[#101828] text-[16px] leading-[24px]">{value}</div>
    </div>
  );
}

export default function KhsPreviewCard({ data }: { data: KhsPreviewData }) {
  const m = data.mahasiswa;

  return (
    <div className="w-[1024px] rounded-[14px] bg-white border border-[#F3F4F6] shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-8 pt-6 pb-4">
        <h1 className="text-[24px] leading-[36px] font-normal text-[#101828]">
          Preview KHS
        </h1>
        <p className="text-[16px] leading-[24px] text-[#4A5565]">
          Pastikan data hasil ekstraksi sudah benar sebelum melanjutkan.
        </p>
      </div>
      <div className="h-px bg-[#E5E7EB]" />

      {/* Content */}
      <div className="px-8 py-8 space-y-8">
        {/* Informasi Mahasiswa */}
        <section className="bg-[#F9FAFB] border border-[#E5E7EB] rounded-[10px] p-6">
          <h2 className="text-[16px] leading-[24px] text-[#101828] mb-6">
            Informasi Mahasiswa
          </h2>

          <div className="grid grid-cols-2 gap-x-8 gap-y-5">
            <InfoItem label="Nama" value={m.nama} />
            <InfoItem label="NIM" value={m.nim} />
            <InfoItem label="Fakultas" value={m.fakultas} />
            <InfoItem label="Program Studi" value={m.prodi} />
            <InfoItem label="DPA" value={m.dpa} />
            <InfoItem label="SKS Kumulatif" value={`${m.sksKumulatif} SKS`} />
            <InfoItem label="IPK" value={m.ipk} />

            <div className="flex flex-col gap-2">
              <div className="text-[#4A5565] text-[16px] leading-[24px]">Status</div>
              <BadgeStatus status={m.status} />
            </div>
          </div>
        </section>

        {/* Daftar Mata Kuliah */}
        <section className="space-y-4">
          <h2 className="text-[16px] leading-[24px] text-[#101828]">Daftar Mata Kuliah</h2>

          <div className="border border-[#E5E7EB] rounded-[10px] overflow-hidden">
            <div className="bg-[#F9FAFB] border-b border-[#E5E7EB]">
              <div className="grid grid-cols-[64px_128px_1fr_96px_96px] px-4 h-12 items-center text-[#364153] font-bold text-[16px]">
                <div>No</div>
                <div>Kode</div>
                <div>Mata Kuliah</div>
                <div>SKS</div>
                <div>Nilai</div>
              </div>
            </div>

            <div className="bg-white">
              {data.matkul.map((row, idx) => (
                <div
                  key={`${row.kode}-${idx}`}
                  className="grid grid-cols-[64px_128px_1fr_96px_96px] px-4 h-[52px] items-center border-b border-[#F3F4F6] text-[16px]"
                >
                  <div className="text-[#364153]">{idx + 1}</div>
                  <div className="text-[#364153]">{row.kode}</div>
                  <div className="text-[#101828]">{row.mataKuliah}</div>
                  <div className="text-[#364153]">{row.sks}</div>
                  <div>
                    <span className="inline-flex items-center justify-center px-2 h-7 rounded bg-[#EFF6FF] text-[#1447E6]">
                      {row.nilai}
                    </span>
                  </div>
                </div>
              ))}

              {data.matkul.length === 0 && (
                <div className="p-4 text-[#4A5565]">Tidak ada data mata kuliah.</div>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
