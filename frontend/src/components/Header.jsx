export default function Header() {
  return (
    <header className="bg-gradient-to-r from-brri-dark to-brri-green text-white shadow-lg">
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-white/15 text-2xl">
            🌾
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
              BRRI Winnower 2024 Support
            </h1>
            <p className="text-sm text-brri-light/90">
              কথোপকথন · উত্তর বাংলা ভাষায়
            </p>
          </div>
        </div>
      </div>
    </header>
  );
}
