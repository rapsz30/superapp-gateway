"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

function MenuButton({
  href,
  variant,
  icon,
  label,
  disabled = false,
}: {
  href: string;
  variant: "primary" | "secondary";
  icon: React.ReactNode;
  label: string;
  disabled?: boolean;
}) {
  const base =
    "w-full h-[110px] rounded-[12px] flex items-center gap-4 text-[24px] transition";

  const styles =
    variant === "primary"
      ? "bg-[#1565C0] text-white"
      : "bg-[#f6f7f8] text-[#1565C0] border-[5px] border-[#1565C0]";

  if (disabled) {
    return (
      <div className={`${base} bg-gray-200 text-gray-400 cursor-not-allowed`}>
        <span className="w-[100px] flex justify-center">{icon}</span>
        <span>{label}</span>
      </div>
    );
  }

  return (
    <Link href={href} className={`${base} ${styles} hover:opacity-95`}>
      <span className="w-[100px] flex justify-center">{icon}</span>
      <span>{label}</span>
    </Link>
  );
}

export default function UploadMenuCard() {
  const [khsDone, setKhsDone] = useState(false);

  useEffect(() => {
    setKhsDone(sessionStorage.getItem("khs_confirmed") === "true");
  }, []);

  return (
    <div className="w-[707px] rounded-[16px] bg-white shadow-sm overflow-hidden">
      {/* header */}
      <div className="px-[32px] pt-[15px] pb-4">
        <h1 className="text-[24px] font-bold text-[#101828]">
          Unggah KHS dan Input Nilai
        </h1>
      </div>

      <div className="h-px bg-black/40" />

      <div className="px-[32px] py-8 space-y-6">
        {/* Upload KHS */}
        <MenuButton
          href="/khs/upload/file"
          variant="primary"
          disabled={khsDone}
          label={khsDone ? "KHS Berhasil" : "Upload KHS"}
          icon={<UploadIcon />}
        />

        {/* Input Nilai */}
        <MenuButton
          href="/khs/nilai-manual"
          variant="secondary"
          disabled={!khsDone}
          label="Input Nilai"
          icon={<NoteIcon />}
        />
      </div>
    </div>
  );
}

/* ICONS */
function UploadIcon() {
  return (
    <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M16 3v14m0-14 5 5m-5-5-5 5M3 29h26" />
    </svg>
  );
}

function NoteIcon() {
  return (
    <svg width="32" height="32" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M6 3h20v26H6zM10 9h12M10 15h12M10 21h12" />
    </svg>
  );
}
