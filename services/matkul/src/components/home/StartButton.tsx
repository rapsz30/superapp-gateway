import Link from 'next/link';

export default function StartButton() {
    return (
        <Link href="/khs/upload" 
        className="inline-flex items-center justify-center 
        w-full max-w-[301px] h-[55px] rounded-[15px] bg-[rgba(0,69,181,0.63)]
        shadow-[8px_4px_15,1px_-5px_rgba(0,0,0,0.47)] text-white text-[20px] sm:text-[24px]
        font-normal hover:opacity-90 transition">
            Mulai
        </Link>
    );
}