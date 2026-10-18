import { Shield } from "lucide-react";

export function Footer() {
  return (
    <footer className="page-footer">
      <span>
        <Shield size={13} />
        SENTINEL
      </span>
      <p>Reported observations. Source values preserved.</p>
      <span>CONTRACT v1</span>
    </footer>
  );
}
