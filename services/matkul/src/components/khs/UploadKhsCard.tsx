"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function UploadKhsCard() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function pickFile() {
    inputRef.current?.click();
  }

  function onChangeFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setFileName(f?.name ?? "");
    setError("");
  }

  async function goPreview() {
    if (!file) return setError("Silakan pilih file PDF dulu.");

    setLoading(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("file", file);

      const res = await fetch("/api/khs/upload", { method: "POST", body: fd });
      const json = await res.json().catch(() => ({}));

      if (!res.ok || !json?.ok) throw new Error(json?.error ?? "Gagal ekstraksi KHS");

      // simpan hasil ekstraksi (dari AI/route) untuk halaman /khs/preview
      sessionStorage.setItem("khs_preview", JSON.stringify(json.preview));

      router.push("/khs/preview");
    } catch (e: any) {
      setError(e?.message ?? "Terjadi kesalahan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-[1024px] rounded-[12px] bg-white border border-[#F3F4F6] shadow-sm overflow-hidden">
      <div className="px-5 sm:px-[32px] pt-[24px] pb-4">
        <h1 className="text-[24px] leading-[36px] font-normal text-[#101828]">Unggah KHS</h1>
        <p className="text-[16px] leading-[24px] text-[#4A5565]">
          Pastikan file KHS anda dalam format PDF.
        </p>
      </div>

      <div className="h-px bg-black/5" />

      <div className="px-5 sm:px-[32px] py-6">
        <div className="w-full rounded-[12px] bg-[#F9FAFB] border border-[#E5E7EB] px-6 sm:px-[60px] lg:px-[121px] py-10 sm:py-[57px] flex flex-col items-center gap-[20px]">
          <div className="flex flex-col items-center gap-[7px]">
            <svg width="50" height="50" viewBox="0 0 24 24" fill="none" aria-hidden="true" className="text-zinc-500">
              <path d="M12 16V4m0 0 4 4m-4-4-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M4 20h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>

            <p className="text-[16px] leading-[18px] text-black/60 text-center">Klik untuk memilih file</p>
            {fileName ? <p className="text-[14px] text-black/60 text-center break-all">Dipilih: {fileName}</p> : null}
            {error ? <p className="text-[14px] text-red-600 text-center">{error}</p> : null}
          </div>

          <button
            type="button"
            onClick={pickFile}
            className="h-[37px] px-[30px] rounded-[12px] bg-black/25 text-[16px] leading-[18px] text-black"
          >
            Pilih File
          </button>

          <input ref={inputRef} type="file" accept="application/pdf" className="hidden" onChange={onChangeFile} />
        </div>

        <button
          type="button"
          onClick={goPreview}
          disabled={loading}
          className="mt-6 h-[48px] w-full rounded-[10px] bg-[#1565C0] text-white font-bold text-[16px] leading-[24px] disabled:opacity-60"
        >
          {loading ? "Memproses..." : "Preview"}
        </button>
      </div>
    </div>
  );
}