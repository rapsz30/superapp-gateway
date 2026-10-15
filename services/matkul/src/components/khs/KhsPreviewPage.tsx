"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import KhsPreviewCard, { type KhsPreviewData } from "./KhsPreviewCard";

export default function KhsPreviewPage() {
  const router = useRouter();
  const [data, setData] = useState<KhsPreviewData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("khs_preview");
    if (!raw) return;
    try {
      setData(JSON.parse(raw));
    } catch {
      setData(null);
    }
  }, []);

  async function handleUnggah() {
    const raw = sessionStorage.getItem("khs_preview");
    if (!raw) return alert("Data preview tidak ada");

    setLoading(true);
    try {
      const khs = JSON.parse(raw);

      const res = await fetch("/api/khs/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ khs }),
      });

      const json = await res.json();
      if (!res.ok) return alert(json.error || "Gagal");

      sessionStorage.setItem("khs_uploaded", "1");
      sessionStorage.setItem("khs_confirmed", "true");
      router.push("/khs/upload");
    } catch (e: any) {
      alert(e?.message ?? "Terjadi error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#E8EAEE] flex flex-col items-center px-4 py-10">
      {data ? (
        <>
          <KhsPreviewCard data={data} />

          <button
            type="button"
            onClick={handleUnggah}
            disabled={loading}
            className="mt-6 w-[1024px] h-[48px] rounded-[10px] bg-[#1565C0] text-white font-bold text-[16px] leading-[24px] disabled:opacity-60"
          >
            {loading ? "Memproses..." : "Unggah"}
          </button>
        </>
      ) : (
        <div className="w-[1024px] rounded-[14px] bg-white border border-[#F3F4F6] shadow-sm p-6">
          <h1 className="text-[24px] leading-[36px] text-[#101828]">
            Preview KHS
          </h1>
          <p className="text-[#4A5565] mt-1">
            Data preview belum ada. Silakan unggah KHS dulu.
          </p>
        </div>
      )}
    </main>
  );
}
