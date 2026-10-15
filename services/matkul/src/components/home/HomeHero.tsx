import Image from 'next/image';
import StartButton from './StartButton';

export default function HomeHero() {
    return (
        <section className="relative min-h-screen bg-[#f5f7fa] overflow-hidden">
        {/*background image*/}
        <Image
        src="/home-bg.png"
        alt="background"
        fill priority
        className="object-cover"
        />

        {/*content*/}
        <div className="relative z-10 mx-auto max-w-[1440px] min-h-screen flex items-center">
        <div className="w-full px-6 sm:px-10 lg:px-[39px] py-24">
            <h1 className="text-white font-bold text-[32px] sm:text-[44px] lg:text-[64px] leading-tight lg:leading-[70px] max-w-[840px]">
           Mari tingkatkan perjalanan <br className="hidden sm:block" />
            akademik anda
            </h1>

        {/*description*/}
        <p className="mt-4 text-white font-normal text-[16px] sm:text-[20px] lg:text-[24px] leading-relaxed lg:leading-[29px] max-w-[1213px]">
            Platform ini membantu anda dalam memahami status akademik dan memberikan rekomendasi mata kuliah untuk mendukung keputusan studi anda. Unggah transkrip, pantau perkembangan akademik dengan mudah dan efisien.</p>

        {/*start button*/}
        <div className="mt-8 lg:mt-10">
            <StartButton />
        </div>
        </div>
        </div>
        </section>
    );
}