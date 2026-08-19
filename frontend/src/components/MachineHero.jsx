const VIDEO_SRC = "/media/brri-winnower-2024.mp4";

export default function MachineHero({ onStart }) {
  return (
    <section className="machine-hero relative isolate min-h-[min(58vh,420px)] w-full overflow-hidden sm:min-h-[min(72vh,560px)]">
      <video
        className="absolute inset-0 h-full w-full object-cover object-center"
        src={VIDEO_SRC}
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        aria-label="BRRI Winnower 2024 operating animation"
      />
      <div className="machine-hero__veil absolute inset-0" aria-hidden />

      <div className="relative z-10 flex min-h-[min(58vh,420px)] flex-col justify-end px-4 pb-8 pt-14 sm:min-h-[min(72vh,560px)] sm:px-8 sm:pb-12 sm:pt-16">
        <p className="animate-fade-up font-display text-[10px] font-semibold uppercase tracking-[0.22em] text-leaf-100/90 sm:text-[11px] sm:tracking-[0.28em]">
          Bangladesh Rice Research Institute
        </p>
        <h1 className="animate-fade-up mt-2 max-w-xl font-display text-[2rem] font-semibold leading-[1.08] tracking-tight text-white sm:mt-3 sm:text-5xl">
          BRRI Winnower
          <span className="mt-0.5 block text-leaf-200 sm:mt-1">২০২৪</span>
        </h1>
        <p className="animate-fade-up mt-3 max-w-md font-bengali text-sm leading-relaxed text-white/85 sm:mt-4 sm:text-lg">
          ধান ঝাড়ার মেশিনের যন্ত্রাংশ, সমস্যা ও মেরামত — ছবি, কণ্ঠ বা লেখায় জিজ্ঞেস করুন।
        </p>
        <div className="animate-fade-up mt-5 sm:mt-7">
          <button
            type="button"
            onClick={onStart}
            className="w-full bg-leaf-400 px-5 py-3 font-bengali text-sm font-semibold text-leaf-950 transition hover:bg-leaf-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70 sm:w-auto sm:py-2.5"
          >
            কথা শুরু করুন
          </button>
        </div>
      </div>
    </section>
  );
}
