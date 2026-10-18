import { Moon, Sun, ChevronRight, ChevronDown } from "lucide-react";
import { cn } from "../../utils/cn.js";
import { pageLabel } from "./navigation.js";

export function Topbar({ page, theme, onToggleTheme, mode, onOpenConnection }) {
  const nextTheme = theme === "dark" ? "Switch to light mode" : "Switch to dark mode";
  return (
    <header className="topbar">
      <div className="breadcrumbs">
        <span>Sentinel</span>
        <ChevronRight size={13} />
        <strong>{pageLabel(page)}</strong>
      </div>
      <div className="topbar-actions">
        <button
          className="theme-toggle"
          type="button"
          aria-label={nextTheme}
          aria-pressed={theme === "dark"}
          title={nextTheme}
          onClick={onToggleTheme}
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
        <button className="source-button" onClick={onOpenConnection}>
          <span className={cn("live-dot", mode === "live" && "connected")} />
          {mode === "examples" ? "Reference examples" : "Live API"}
          <ChevronDown size={13} />
        </button>
      </div>
    </header>
  );
}
