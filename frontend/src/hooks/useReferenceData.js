import { useState, useEffect } from "react";

// Checked reference examples bundled in public/; also supplies the report register.
export function useReferenceData() {
  const [db, setDb] = useState();
  const [error, setError] = useState();
  useEffect(() => {
    fetch("/reference-data.json")
      .then((r) => {
        if (!r.ok) throw Error("Could not load reference data.");
        return r.json();
      })
      .then(setDb)
      .catch(setError);
  }, []);
  return { db, error };
}
