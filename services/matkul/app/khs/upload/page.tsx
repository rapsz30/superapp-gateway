"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

function MenuButton({
  href,
  variant,
  icon,
  label,
  disabled,
}: {
  href: string;
  variant: "primary" | "secondary";
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
}) {
  const base =
    "w-full h-[110px] rounded-[12px] flex items-center justify-center gap-4 text-[24px] leading-[28px] font-normal transition";

  const styles =
    variant === "primary"
      ? "bg-[#1565C0] text-white shadow-sm"
      : "bg-[#F6F7F8] text-[#1565C0] border-[5px] border-[#1565C0]";

  const disabledStyle = disabled
    ? "opacity-50 pointer-events-none"
    : "hover:opacity-95";

  return (
    <Link href={href} className={`${base} ${styles} ${disabledStyle}`}>
      <span className="inline-flex items-center justify-center w-[50px] h-[50px]">
        {icon}
      </span>
      <span>{label}</span>
    </Link>
  );
}

export default function UploadMenuPage() {
  const [khsDone, setKhsDone] = useState(false);

  useEffect(() => {
    setKhsDone(sessionStorage.getItem("khs_confirmed") === "true");
  }, []);

  function resetKhs() {
    sessionStorage.removeItem("khs_confirmed");
    sessionStorage.removeItem("khs_preview");
    sessionStorage.removeItem("khs_file_name");
    setKhsDone(false);
  }

  return (
    <main className="min-h-screen bg-[#E8ECF3] flex items-center justify-center px-4">
    <div className="w-full max-w-[707px] rounded-[16px] bg-white shadow-[0px_10px_15px_-3px_rgba(0,0,0,0.1),0px_4px_6px_-4px_rgba(0,0,0,0.1)] overflow-hidden">        
      <div className="px-[32px] pt-[15px] pb-4">
          <h1 className="text-[24px] leading-[36px] font-bold text-[#101828]">
            Unggah KHS dan Input Nilai
          </h1>
        </div>

        <div className="h-px bg-black/40" />

        <div className="px-[32px] py-8 space-y-6">
          <MenuButton
            href="/khs/upload/file"
            variant="primary"
            label={khsDone ? "KHS Berhasil" : "Upload KHS"}
            disabled={khsDone}
            icon={
              <svg width="50" height="50" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path
                  d="M12 16V4m0 0 4 4m-4-4-4 4"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path d="M4 20h16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              </svg>
            }
          />

          <MenuButton
            href="/khs/nilai-manual"
            variant="secondary"
            label="Input Nilai"
            disabled={!khsDone}
            icon={
              <svg width="50" height="50" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M7 3h10v18H7V3z" stroke="currentColor" strokeWidth="2" />
                <path d="M9 7h6M9 11h6M9 15h6" stroke="currentColor" strokeLinecap="round" />
              </svg>
            }
          />

          {!khsDone && (
            <p className="text-sm text-[#4A5565]">
              * Input Nilai akan aktif setelah KHS berhasil dikonfirmasi di halaman Preview.
            </p>
          )}

          {khsDone && (
            <button type="button" onClick={resetKhs} className="text-sm text-red-600">
              Reset KHS
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
