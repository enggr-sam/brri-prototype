import { useEffect, useState } from "react";
import { logoutUser } from "../services/api.js";
import { clearAuth, getUser, isLoggedIn } from "../utils/auth.js";
import { goTo, handleAppLink } from "../utils/nav.js";

const LOGO_SRC = "/brri-logo.jpg";

export default function Header({
  compact = false,
  overlay = false,
  showChatHome = false,
}) {
  const onDark = compact || overlay;
  const [user, setUser] = useState(() => getUser());

  useEffect(() => {
    const sync = () => setUser(getUser());
    window.addEventListener("brri-auth", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("brri-auth", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch {
      /* ignore */
    }
    clearAuth();
    goTo("/");
  };

  return (
    <header
      className={`shrink-0 ${
        overlay
          ? "absolute inset-x-0 top-0 z-20 border-b border-white/10 bg-gradient-to-b from-leaf-950/55 to-transparent"
          : compact
            ? "relative border-b border-white/10 bg-leaf-950 text-white"
            : "relative border-b border-slate-200 bg-white shadow-sm"
      }`}
    >
      <div
        className={`mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 sm:px-6 ${
          compact || overlay ? "py-3" : "py-4"
        }`}
      >
        <a
          href="/"
          onClick={(e) => handleAppLink(e, "/")}
          className="flex min-w-0 items-center gap-3"
        >
          <div
            className={`flex shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white ${
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
                  onDark ? "text-base text-white" : "text-lg text-slate-900"
                }`}
              >
                BRRI Multicrop Winnower
              </p>
              {!compact && (
                <p className="font-bengali text-xs text-slate-500">
                  ব্রি শস্য ঝাড়াই যন্ত্র · BRRI Win2024
                </p>
              )}
            </div>
          )}
        </a>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {showChatHome && (
            <a
              href="/winnower"
              onClick={(e) => handleAppLink(e, isLoggedIn() ? "/winnower" : "/login?next=/winnower")}
              className={`px-3 py-1.5 font-bengali text-sm transition ${
                onDark
                  ? "text-white/85 hover:text-white"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              ← চ্যাট
            </a>
          )}
          {user ? (
            <>
              <span
                className={`hidden font-bengali text-xs sm:inline ${
                  onDark ? "text-white/70" : "text-slate-500"
                }`}
              >
                {user.mobile}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className={`rounded-lg px-2 py-1.5 font-bengali text-sm transition ${
                  onDark
                    ? "text-white/85 hover:text-white"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                লগআউট
              </button>
            </>
          ) : (
            <a
              href="/login"
              onClick={(e) => handleAppLink(e, "/login?next=/winnower")}
              className={`rounded-lg px-3 py-1.5 font-bengali text-sm font-medium transition ${
                onDark
                  ? "bg-white/15 text-white hover:bg-white/25"
                  : "bg-leaf-500 text-white hover:bg-leaf-600"
              }`}
            >
              লগইন
            </a>
          )}
        </div>
      </div>
    </header>
  );
}
