import { useCallback, useEffect, useState } from "react";

const THEME_KEY = "brri_theme";
const THEME_EVENT = "brri-theme";

export const LIGHT = "light";
export const DARK = "dark";

function normalize(value) {
  return value === DARK ? DARK : LIGHT;
}

export function getTheme() {
  try {
    return normalize(localStorage.getItem(THEME_KEY));
  } catch {
    return LIGHT;
  }
}

export function applyTheme(theme) {
  const root = document.documentElement;
  root.classList.toggle(DARK, theme === DARK);
  root.style.colorScheme = theme;
}

export function setTheme(theme) {
  const next = normalize(theme);
  try {
    localStorage.setItem(THEME_KEY, next);
  } catch {
    /* private mode — theme still applies for this session */
  }
  applyTheme(next);
  window.dispatchEvent(new Event(THEME_EVENT));
  return next;
}

export function useTheme() {
  const [theme, setThemeState] = useState(getTheme);

  useEffect(() => {
    const sync = () => setThemeState(getTheme());
    sync();
    window.addEventListener(THEME_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(THEME_EVENT, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);

  const select = useCallback((next) => setTheme(next), []);
  const toggle = useCallback(() => setTheme(getTheme() === DARK ? LIGHT : DARK), []);

  return { theme, isDark: theme === DARK, setTheme: select, toggleTheme: toggle };
}
