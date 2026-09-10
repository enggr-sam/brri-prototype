import { useEffect, useState } from "react";
import { loginUser, registerUser } from "../services/api.js";
import { getToken, safeNextPath, setAuth } from "../utils/auth.js";
import { goTo, handleAppLink } from "../utils/nav.js";

function nextPath() {
  const query = new URLSearchParams(window.location.search);
  return safeNextPath(query.get("next"));
}

export default function LoginPage() {
  const [mode, setMode] = useState("login");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (getToken()) goTo(nextPath());
  }, []);

  const submit = async (event) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data =
        mode === "register"
          ? await registerUser({ mobile, password })
          : await loginUser({ mobile, password });
      setAuth(data);
      goTo(nextPath());
    } catch (err) {
      setError(err.message || "কাজটি সম্পন্ন হয়নি।");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-4 py-10 sm:px-6 sm:py-16">
      <div className="mx-auto w-full max-w-md">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8">
          <p className="font-display text-[10px] font-semibold uppercase tracking-[0.18em] text-leaf-500 dark:text-leaf-400">
            BRRI Win2024
          </p>
          <h1 className="mt-1 font-display text-2xl font-semibold text-slate-900 dark:text-slate-100">
            {mode === "register" ? "📝 একাউন্ট খুলুন" : "🔐 লগইন করুন"}
          </h1>
          <p className="mt-2 font-bengali text-sm leading-relaxed text-slate-500 dark:text-slate-400">
            মোবাইল নম্বর ও একটি পাসওয়ার্ড দিন। চ্যাট ইতিহাস শুধু আপনার একাউন্টে থাকবে।
          </p>

          <form className="mt-6 space-y-4" onSubmit={submit}>
            <label className="block">
              <span className="font-bengali text-xs text-slate-500 dark:text-slate-400">
                📱 মোবাইল নম্বর
              </span>
              <input
                type="tel"
                inputMode="numeric"
                autoComplete="tel"
                required
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                placeholder="01XXXXXXXXX"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 font-bengali text-[15px] text-slate-900 outline-none ring-leaf-500/25 focus:border-leaf-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-leaf-400"
              />
            </label>

            <label className="block">
              <span className="font-bengali text-xs text-slate-500 dark:text-slate-400">
                🔒 পাসওয়ার্ড (মনে রাখার মতো)
              </span>
              <input
                type="password"
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                required
                minLength={4}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="কমপক্ষে ৪ অক্ষর"
                className="mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 font-bengali text-[15px] text-slate-900 outline-none ring-leaf-500/25 focus:border-leaf-500 focus:ring-2 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500 dark:focus:border-leaf-400"
              />
            </label>

            {error && (
              <p className="font-bengali text-sm text-red-700 dark:text-red-400">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-lg bg-leaf-500 px-4 py-2.5 font-bengali text-sm font-semibold text-white shadow-sm transition hover:bg-leaf-600 disabled:opacity-50"
            >
              {loading
                ? "⏳ অপেক্ষা করুন…"
                : mode === "register"
                  ? "📝 নিবন্ধন করুন"
                  : "🔐 লগইন"}
            </button>
          </form>

          <p className="mt-5 text-center font-bengali text-sm text-slate-500 dark:text-slate-400">
            {mode === "register" ? "আগে একাউন্ট আছে?" : "নতুন ব্যবহারকারী?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "register" ? "login" : "register");
                setError(null);
              }}
              className="font-semibold text-leaf-500 hover:text-leaf-600 dark:text-leaf-400 dark:hover:text-leaf-300"
            >
              {mode === "register" ? "🔐 লগইন করুন" : "📝 একাউন্ট খুলুন"}
            </button>
          </p>
        </div>

        <p className="mt-4 text-center">
          <a
            href="/"
            onClick={(e) => handleAppLink(e, "/")}
            className="font-bengali text-sm text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
          >
            ← 🏠 হোমে ফিরুন
          </a>
        </p>
      </div>
    </main>
  );
}
