import MachineHero from "../components/MachineHero.jsx";
import { isLoggedIn } from "../utils/auth.js";
import { handleAppLink } from "../utils/nav.js";

const VIDEO_SRC = "/media/brri-winnower-2024.mp4";

export default function HomePage() {
  const chatHref = isLoggedIn() ? "/winnower" : "/login?next=/winnower";

  return (
    <main className="min-h-0 flex-1 overflow-y-auto overscroll-y-contain">
      <div className="animate-fade-up">
        <MachineHero startHref={chatHref} />
      </div>

      <section className="mx-auto w-full max-w-3xl px-3 py-6 sm:px-4 sm:py-8">
        <p className="font-bengali text-sm text-leaf-800/75">
          কোন যন্ত্র নিয়ে সাহায্য লাগবে?
        </p>
        <h2 className="mt-1 font-display text-lg font-semibold text-leaf-950 sm:text-xl">
          যন্ত্র বেছে নিন
        </h2>

        <a
          href={chatHref}
          onClick={(e) => handleAppLink(e, chatHref)}
          className="mt-4 flex overflow-hidden border border-leaf-900/10 bg-white/80 shadow-sm backdrop-blur-sm transition hover:-translate-y-0.5 hover:border-leaf-500/30 hover:shadow-md"
        >
          <div className="relative h-28 w-32 shrink-0 bg-leaf-950 sm:h-32 sm:w-40">
            <video
              className="absolute inset-0 h-full w-full object-cover"
              src={VIDEO_SRC}
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              aria-hidden
            />
          </div>
          <div className="flex min-w-0 flex-1 flex-col justify-center px-4 py-3 sm:px-5">
            <p className="font-display text-[10px] font-semibold uppercase tracking-[0.16em] text-leaf-500">
              BRRI Win2024
            </p>
            <p className="mt-0.5 font-display text-base font-semibold text-leaf-950 sm:text-lg">
              BRRI Multicrop Winnower
            </p>
            <p className="mt-0.5 font-bengali text-sm text-leaf-800/75">
              ব্রি শস্য ঝাড়াই যন্ত্র — চ্যাট খুলুন
            </p>
          </div>
          <span
            className="flex items-center pr-3 text-leaf-500 sm:pr-4"
            aria-hidden
          >
            →
          </span>
        </a>
      </section>
    </main>
  );
}
