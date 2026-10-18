import { useState, useEffect } from "react";

// index.html applies the saved theme before React loads; this keeps it in sync.
export function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme || "light");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "dark" ? "#111a16" : "#164f43");
    try { localStorage.setItem("sentinel-theme", theme); } catch { /* Storage may be disabled. */ }
  }, [theme]);
  const toggle = () => setTheme(theme === "dark" ? "light" : "dark");
  return [theme, toggle];
}
