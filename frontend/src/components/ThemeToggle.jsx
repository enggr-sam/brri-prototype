import { DARK, LIGHT, useTheme } from "../utils/theme.js";

/**
 * `segmented` shows both choices side by side (sidebar), `icon` is a compact
 * single button for headers. `onDark` picks the palette for dark backdrops.
 */
export default function ThemeToggle({ variant = "icon", onDark = false }) {
  const { isDark, setTheme, toggleTheme } = useTheme();

  if (variant === "segmented") {
    return (
      <div
        role="group"
        aria-label="থিম নির্বাচন"
        className="flex items-center gap-1 rounded-lg bg-white/10 p-1"
      >
        <Segment
          active={!isDark}
          onClick={() => setTheme(LIGHT)}
          icon={<SunIcon />}
          label="উজ্জ্বল"
        />
        <Segment
          active={isDark}
          onClick={() => setTheme(DARK)}
          icon={<MoonIcon />}
          label="অন্ধকার"
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      title={isDark ? "উজ্জ্বল থিম" : "অন্ধকার থিম"}
      aria-label={isDark ? "উজ্জ্বল থিমে যান" : "অন্ধকার থিমে যান"}
      aria-pressed={isDark}
      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition ${
        onDark
          ? "text-white/75 hover:bg-white/15 hover:text-white"
          : "text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      }`}
    >
      {isDark ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}

function Segment({ active, onClick, icon, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 font-bengali text-xs font-medium transition ${
        active
          ? "bg-white/20 text-white shadow-sm"
          : "text-white/55 hover:text-white/85"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function SunIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
      <circle cx="8" cy="8" r="3.1" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M8 1.4v1.6M8 13v1.6M14.6 8H13M3 8H1.4M12.67 3.33l-1.13 1.13M4.46 11.54l-1.13 1.13M12.67 12.67l-1.13-1.13M4.46 4.46 3.33 3.33"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden>
      <path
        d="M13.6 9.85A5.9 5.9 0 0 1 6.15 2.4a6 6 0 1 0 7.45 7.45Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}
