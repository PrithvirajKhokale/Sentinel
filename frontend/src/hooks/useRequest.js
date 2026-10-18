import { useState, useEffect } from "react";

export function useRequest(client, path, params) {
  const [state, set] = useState({ loading: true });
  const key = JSON.stringify(params);
  useEffect(() => {
    const a = new AbortController();
    set({ loading: true });
    client
      .get(path, params, a.signal)
      .then((result) => {
        if (!a.signal.aborted) set({ result, loading: false });
      })
      .catch((error) => {
        if (!a.signal.aborted) set({ error, loading: false });
      });
    return () => a.abort();
  }, [client, path, key]);
  return state;
}
