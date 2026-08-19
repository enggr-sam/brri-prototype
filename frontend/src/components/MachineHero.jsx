const VIDEO_SRC = "/media/brri-winnower-2024.mp4";

export default function MachineHero({ onStart }) {
  return (
    <section className="machine-hero relative isolate min-h-[min(72vh,560px)] w-full overflow-hidden">
      <video
        className="absolute inset-0 h-full w-full object-cover"
        src={VIDEO_SRC}
        autoPlay
        muted
        loop
        playsInline
        preload="metadata"
        aria-label="BRRI Winnower 2024 operating animation"
      />
      <div className="machine-hero__veil absolute inset-0" aria-hidden />

      <div className="relative z-10 flex min-h-[min(72vh,560px)] flex-col justify-end px-5 pb-10 pt-16 sm:px-8 sm:pb-12">
        <p className="font-display text-[11px] font-semibold uppercase tracking-[0.28em] text-leaf-100/90">
          Bangladesh Rice Research Institute
        </p>
        <h1 className="mt-3 max-w-xl font-display text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl">
          BRRI Winnower
          <span className="mt-1 block text-leaf-200">২০২৪</span>
        </h1>
        <p className="mt-4 max-w-md font-bengali text-base leading-relaxed text-white/85 sm:text-lg">
          ধান ঝাড়ার মেশিনের যন্ত্রাংশ, সমস্যা ও মেরামত — ছবি, কণ্ঠ বা লেখায় জিজ্ঞেস করুন।
        </p>
        <div className="mt-7">
          <button
            type="button"
            onClick={onStart}
            className="bg-leaf-400 px-5 py-2.5 font-bengali text-sm font-semibold text-leaf-950 transition hover:bg-leaf-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/70"
          >
            কথা শুরু করুন
          </button>
        </div>
      </div>
    </section>
  );
}
