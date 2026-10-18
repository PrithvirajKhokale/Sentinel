import { RefreshCw } from "lucide-react";

export function Loading() {
  return (
    <div className="loading" role="status">
      <RefreshCw size={19} /> Loading reported data…
    </div>
  );
}
