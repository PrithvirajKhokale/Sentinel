import { FileText, Info } from "lucide-react";

export function Provenance({ s, meta }) {
  return (
    <>
      <div className="source-file">
        <FileText size={29} />
        <div>
          <strong>{s.provenance.source_filename}</strong>
          <p>
            PDF pages {s.provenance.pdf_pages.join(", ")} · printed pages{" "}
            {s.provenance.printed_pages.join(", ")} · serial {s.serial_no}
          </p>
        </div>
      </div>
      <div className="definition-list">
        <div>
          <span>Source platform</span>
          <strong>{s.temporal.source_platform}</strong>
        </div>
        <div>
          <span>Reporting cutoff</span>
          <strong>{s.temporal.reporting_cutoff_date || "Unknown"}</strong>
        </div>
        <div>
          <span>Cutoff source text</span>
          <strong>{s.temporal.reporting_cutoff_raw}</strong>
        </div>
        <div>
          <span>Cutoff source page</span>
          <strong>PDF {s.temporal.source_pdf_page}</strong>
        </div>
        <div>
          <span>Publication date</span>
          <strong>{s.temporal.publication_date || "Unknown"}</strong>
        </div>
        <div>
          <span>First available date</span>
          <strong>{s.temporal.first_available_date || "Unknown"}</strong>
        </div>
      </div>
      <div className="notice">
        <Info size={17} />
        <p>
          A reporting cutoff is not a publication date. Unknown availability is
          retained explicitly.
        </p>
      </div>
      <h3 className="subheading">Source fingerprint</h3>
      <code className="hash-block">{s.provenance.source_sha256}</code>
      <h3 className="subheading">Dataset revision</h3>
      <code className="hash-block">{meta.dataset_version}</code>
      <h3 className="subheading">Original physical cells</h3>
      {s.provenance.physical_cells?.length ? (
        <ol className="physical-cells">
          {s.provenance.physical_cells.map((c, i) => (
            <li key={i}>
              <pre>{c}</pre>
            </li>
          ))}
        </ol>
      ) : (
        <p className="hint">
          Original cell text is not included in this reference fixture. The
          source fields above are preserved; no physical cells have been
          reconstructed.
        </p>
      )}
      {s.quality.source_notes?.length > 0 && (
        <>
          <h3 className="subheading">Source notes</h3>
          <pre>{JSON.stringify(s.quality.source_notes, null, 2)}</pre>
        </>
      )}
    </>
  );
}
