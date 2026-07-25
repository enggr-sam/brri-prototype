const LOGO_SRC = "/brri-logo.jpg";

export default function Header() {
  return (
    <header className="shrink-0 bg-gradient-to-r from-brri-dark to-brri-green text-white shadow-lg">
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white p-1">
            <img
              src={LOGO_SRC}
              alt="BRRI logo"
              className="h-full w-full object-contain"
            />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                BRRI Winnower 2024 Support
              </h1>
              <span className="rounded-full bg-amber-300 px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide text-brri-dark">
                Prototype / Demo
              </span>
            </div>
            <p className="text-sm text-brri-light/90">
              কথোপকথন · উত্তর বাংলা ভাষায়
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
