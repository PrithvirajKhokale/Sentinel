import { useState, useEffect } from "react";
import { ArrowRight, X } from "lucide-react";
import { cn } from "../utils/cn.js";
import { createClient } from "../api/client.js";

export function Connection({ config, onApply, onClose }) {
  const [mode, setMode] = useState(config.mode),
    [base, setBase] = useState(config.base || ""),
    [token, setToken] = useState(""),
    [error, setError] = useState(""),
    [connecting, setConnecting] = useState(false);
  useEffect(() => {
    const fn = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", fn);
    return () => document.removeEventListener("keydown", fn);
  }, []);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (mode === "live") {
      try {
        const u = new URL(base, location.origin);
        if (
          u.origin !== location.origin && u.protocol !== "https:" &&
          !(
            location.protocol === "http:" &&
            ["127.0.0.1", "localhost", "[::1]"].includes(u.hostname)
          )
        )
          throw Error(
            "Use an authenticated HTTPS endpoint. Loopback HTTP is supported when the frontend also runs locally.",
          );
        if (u.username || u.password || u.search || u.hash)
          throw Error(
            "Use an API base URL without embedded credentials, queries, or fragments.",
          );
      } catch (e) {
        setError(e.message);
        return;
      }
    }
    const next = { mode, base: base.trim().replace(/\/$/, ""), token };
    if (mode === "live") {
      setConnecting(true);
      try {
        await createClient(null, next).get("/projects", { report_month: "2026-08", page_size: 1 });
      } catch (e) {
        setError(e.message);
        setConnecting(false);
        return;
      }
    }
    onApply(next);
    onClose();
  };
  return (
    <div className="modal-backdrop">
      <section
        className="connection-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="connection-title"
      >
        <div className="panel-title">
          <h2 id="connection-title">Data connection</h2>
          <button
            className="icon-button"
            aria-label="Close connection"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>
        <p>
          Explore the source examples, or connect your existing Sentinel API.
        </p>
        <form onSubmit={submit}>
          <div className="source-choice">
            <label className={cn(mode === "examples" && "selected")}>
              <input
                type="radio"
                name="source"
                value="examples"
                checked={mode === "examples"}
                onChange={() => setMode("examples")}
              />
              <span>
                <strong>Reference examples</strong>
                <small>Checked excerpts and documented comparisons</small>
              </span>
            </label>
            <label className={cn(mode === "live" && "selected")}>
              <input
                type="radio"
                name="source"
                value="live"
                checked={mode === "live"}
                onChange={() => setMode("live")}
              />
              <span>
                <strong>Live Sentinel API</strong>
                <small>List, detail, history & portfolio contract v1</small>
              </span>
            </label>
          </div>
          {mode === "live" && (
            <>
              <label className="form-label">
                API base URL
                <input
                  autoFocus
                  // Not type="url": relative same-origin bases like /api/v1 are valid; submit() checks them.
                  type="text"
                  inputMode="url"
                  aria-label="API base URL"
                  placeholder="https://your-api.example/api/v1"
                  value={base}
                  onChange={(e) => setBase(e.target.value)}
                  required
                />
              </label>
              <label className="form-label">
                Bearer token (if required)
                <input
                  type="password"
                  aria-label="API bearer token"
                  autoComplete="off"
                  placeholder="Optional · held only in memory"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                />
              </label>
              <p className="hint">
                Use a reachable authenticated service with CORS configured for
                this site's origin. Use /api/v1 when the API and interface share
                a host. Credentials are never saved in
                browser storage. A failed API request stays visible.
              </p>
            </>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="button primary wide" type="submit" disabled={connecting}>
            {connecting ? "Checking connection…" : mode === "examples" ? "Use reference examples" : "Connect API"}
            <ArrowRight size={16} />
          </button>
        </form>
      </section>
    </div>
  );
}
