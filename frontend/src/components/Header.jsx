const LOGO_SRC = "/brri-logo.jpg";

export default function Header({
  compact = false,
  overlay = false,
  showChatHome = false,
}) {
  const onDark = compact || overlay;

  return (
    <header
      className={`shrink-0 ${
        overlay
          ? "absolute inset-x-0 top-0 z-20 border-b border-white/10 bg-gradient-to-b from-leaf-950/55 to-transparent"
          : compact
            ? "relative border-b border-leaf-900/10 bg-leaf-950 text-white"
            : "relative border-b border-leaf-900/10 bg-white/55 backdrop-blur-md"
      }`}
    >
      <div
        className={`mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 sm:px-6 ${
          compact || overlay ? "py-3" : "py-4"
        }`}
      >
        <a href="#/" className="flex min-w-0 items-center gap-3">
          <div
            className={`flex shrink-0 items-center justify-center overflow-hidden bg-white ${
              compact || overlay ? "h-9 w-9" : "h-10 w-10"
            }`}
          >
            <img
              src={LOGO_SRC}
              alt="BRRI"
              className="h-full w-full object-contain"
            />
          </div>
          {!overlay && (
            <div className="min-w-0">
              <p
                className={`font-display font-semibold tracking-tight ${
                  onDark ? "text-base text-white" : "text-lg text-leaf-950"
                }`}
              >
                BRRI Winnower
              </p>
              {!compact && (
                <p className="font-bengali text-xs text-leaf-800/70">
                  BRRI Win2024 · মাঠ পর্যায়ের সহায়ক
                </p>
              )}
            </div>
          )}
        </a>

        {showChatHome && (
          <a
            href="#/"
            className={`px-3 py-1.5 font-bengali text-sm transition ${
              onDark
                ? "text-white/85 hover:text-white"
                : "text-leaf-900/70 hover:text-leaf-950"
            }`}
          >
            ← চ্যাট
          </a>
        )}
      </div>
    </header>
  );
}
