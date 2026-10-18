import { Shield } from "lucide-react";
import { cn } from "../../utils/cn.js";
import { PAGES } from "./navigation.js";

export function Sidebar({ page, onNavigate }) {
  return (
    <aside className="sidebar">
      <a
        className="brand"
        href="#"
        onClick={(e) => {
          e.preventDefault();
          onNavigate("explore");
        }}
      >
        <span className="brand-mark">
          <Shield size={24} strokeWidth={1.7} />
        </span>
        <span>
          sentinel<span className="brand-period">.</span>
        </span>
      </a>
      <div className="workspace-label">PROJECT INTELLIGENCE</div>
      <nav aria-label="Main navigation">
        {PAGES.map(([k, l, IC]) => (
          <button
            key={k}
            className={cn("nav-item", page === k && "selected")}
            onClick={() => onNavigate(k)}
          >
            <IC size={18} />
            <span>{l}</span>
            {page === k && <i />}
          </button>
        ))}
      </nav>
      <div className="sidebar-note">
        <div className="orbit-mark">
          <Shield size={33} strokeWidth={1} />
        </div>
        <strong>Evidence over assumption.</strong>
        <p>Explore what the reports say, with their limits intact.</p>
        <span>APR — AUG 2026</span>
      </div>
      <div className="sidebar-footer">
        <div className="avatar">PK</div>
        <div>
          <strong>Sentinel workspace</strong>
          <span>Public read-only data</span>
        </div>
      </div>
    </aside>
  );
}
