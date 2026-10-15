"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function UploadPanduanPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  function pickFile() {
    inputRef.current?.click();
  }

  async function submit() {
    setErr("");

    if (!file) {
      setErr("Pilih file PDF panduan akademik dulu.");
      return;
    }

    if (file.type !== "application/pdf") {
      setErr("File harus berformat PDF.");
      return;
    }

    setLoading(true);

    try {
      const form = new FormData();
      form.append("file_pdf", file);

      const res = await fetch("/api/panduan/extract-upload", {
        method: "POST",
        body: form,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data?.error || "Gagal memproses panduan.");
      }

      // Hanya disimpan sementara di sesi browser, TIDAK dikirim ke database.
      sessionStorage.setItem("panduan_text", data.text);
      sessionStorage.setItem("panduan_file_name", file.name);

      router.push("/khs/rekomendasi");
    } catch (e: any) {
      setErr(e?.message ?? "Gagal memproses panduan.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#E8EAEE] flex justify-center py-10 px-4">
      <div className="w-full max-w-[720px] bg-white rounded-[14px] border border-[#F3F4F6] shadow-sm overflow-hidden">
<div className="px-5 sm:px-8 py-6">
            <h1 className="text-[24px] text-[#101828]">Unggah Panduan Akademik</h1>
          <p className="text-[#4A5565] text-[16px] mt-1">
            Unggah PDF panduan akademik program studimu. File hanya diproses
            untuk membuat rekomendasi dan{" "}
            <b>tidak disimpan ke database</b> — file akan hilang begitu kamu
            meninggalkan halaman ini.
          </p>
        </div>

        <div className="h-px bg-[#E5E7EB]" />

<div className="px-5 sm:px-8 py-6 space-y-4">
            {err ? <p className="text-red-600 text-sm">{err}</p> : null}

          <div className="rounded-[10px] border border-[#E5E7EB] bg-[#F9FAFB] p-4">
            <p className="text-sm text-[#101828] font-semibold">File Panduan (PDF)</p>

            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={pickFile}
                className="h-10 px-4 rounded bg-black/10 text-black"
              >
                Pilih File
              </button>

              <span className="text-sm text-[#4A5565]">
                {file?.name ?? "Belum ada file"}
              </span>
            </div>

            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={submit}
            className="h-[48px] w-full rounded-[10px] bg-[#1565C0] text-white font-bold disabled:opacity-60"
          >
            {loading ? "Memproses..." : "Lanjut Rekomendasi"}
          </button>
        </div>
      </div>
    </main>
  );
}