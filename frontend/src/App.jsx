import { useState, useMemo } from "react";
import { createClient } from "./api/client.js";
import { useTheme } from "./hooks/useTheme.js";
import { useReferenceData } from "./hooks/useReferenceData.js";
import { ErrorBox } from "./components/common/ErrorBox.jsx";
import { Loading } from "./components/common/Loading.jsx";
import { Sidebar } from "./components/layout/Sidebar.jsx";
import { Topbar } from "./components/layout/Topbar.jsx";
import { SourceBanner } from "./components/layout/SourceBanner.jsx";
import { Footer } from "./components/layout/Footer.jsx";
import { Inspector } from "./components/inspector/Inspector.jsx";
import { Connection } from "./components/Connection.jsx";
import { Explorer } from "./pages/Explorer.jsx";
import { Portfolio } from "./pages/Portfolio.jsx";
import { RiskIntelligence } from "./pages/RiskIntelligence.jsx";
import { Evidence } from "./pages/Evidence.jsx";

// Dev uses the Vite /api proxy; a build without VITE_API_BASE_URL starts in reference mode.
function initialConfig() {
  const base = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? "/api/v1" : "");
  return base ? { mode: "live", base } : { mode: "examples" };
}

export function App() {
  const [theme, toggleTheme] = useTheme();
  const { db, error: loadError } = useReferenceData();
  const [page, setPage] = useState("explore"),
    [month, setMonth] = useState("2026-08"),
    [filters, setFilters] = useState({}),
    [selection, setSelection] = useState(null),
    [connection, setConnection] = useState(false),
    [config, setConfig] = useState(initialConfig);
  const client = useMemo(
    () => (db ? createClient(db, config) : null),
    [db, config],
  );
  const inspect = (code, m, tab) => setSelection({ code, month: m, tab });
  if (loadError) return <ErrorBox error={loadError} />;
  if (!db) return <Loading />;
  const shared = {
    db, client, mode: config.mode, month, setMonth, filters, setFilters, onInspect: inspect,
  };
  return (
    <div className="app-shell">
      <Sidebar page={page} onNavigate={setPage} />
      <div className="main-shell">
        <Topbar
          page={page}
          theme={theme}
          onToggleTheme={toggleTheme}
          mode={config.mode}
          onOpenConnection={() => setConnection(true)}
        />
        <main>
          <SourceBanner mode={config.mode} onOpenConnection={() => setConnection(true)} />
          {page === "explore" ? (
            <Explorer {...shared} onGap={() => setPage("evidence")} />
          ) : page === "portfolio" ? (
            <Portfolio {...shared} />
          ) : page === "risk" ? (
            <RiskIntelligence {...shared} />
          ) : (
            <Evidence db={db} onInspect={inspect} />
          )}
          <Footer />
        </main>
      </div>
      {selection && (
        <Inspector
          key={selection.code}
          selection={selection}
          client={client}
          mode={config.mode}
          onClose={() => setSelection(null)}
          onSelect={setSelection}
        />
      )}
      {connection && (
        <Connection
          config={config}
          onApply={(c) => {
            setConfig(c);
            setSelection(null);
            setFilters({});
          }}
          onClose={() => setConnection(false)}
        />
      )}
    </div>
  );
}
