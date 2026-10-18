import { APIError } from "./errors.js";
import { exampleResponse } from "./reference.js";

export function queryString(params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    for (const x of Array.isArray(v) ? v : [v]) q.append(k, String(x));
  }
  return q.toString();
}
export function createClient(db, config = { mode: "examples" }) {
  let pinned = null;
  return {
    get version() {
      return pinned;
    },
    async get(path, params = {}, signal) {
      let result;
      if (config.mode === "examples")
        result = exampleResponse(db, path, {
          ...params,
          dataset_version: params.dataset_version || pinned,
        });
      else {
        const base = config.base.replace(/\/$/, "");
        const q = {
          ...params,
          dataset_version: params.dataset_version || pinned,
        };
        delete q.full_reference;
        const timeout = AbortSignal.timeout(15000);
        const requestSignal = signal
          ? AbortSignal.any([signal, timeout])
          : timeout;
        let response;
        try {
          response = await fetch(`${base}${path}?${queryString(q)}`, {
            signal: requestSignal,
            credentials: "include",
            headers: config.token
              ? { Authorization: `Bearer ${config.token}` }
              : {},
          });
        } catch (e) {
          if (e.name === "AbortError") throw e;
          throw new APIError(
            "CONNECTION_FAILED",
            "Could not reach the API. Check its URL, authentication, and CORS settings.",
          );
        }
        try {
          result = await response.json();
        } catch {
          throw new APIError(
            "INVALID_RESPONSE",
            "API returned a non-JSON response.",
          );
        }
        if (!response.ok || result.error)
          throw new APIError(
            result.error?.code || `HTTP_${response.status}`,
            result.error?.message || "Request failed.",
            result.error?.details || [],
          );
      }
      if (
        result.meta?.contract_version !== "1" ||
        !Array.isArray(result.warnings) ||
        !result.meta?.dataset_version
      )
        throw new APIError(
          "INVALID_RESPONSE",
          "Response does not match Sentinel contract v1.",
        );
      if (pinned && result.meta.dataset_version !== pinned)
        throw new APIError(
          "DATASET_CHANGED",
          "Dataset revision changed. Reconnect to start a consistent session.",
        );
      pinned = result.meta.dataset_version;
      return result;
    },
  };
}
