import { AlertTriangle } from "lucide-react";

export function ErrorBox({ error }) {
  return (
    <div className="error-box" role="alert">
      <AlertTriangle size={19} />
      <div>
        <strong>{error.code || "Unable to load data"}</strong>
        <p>{error.message}</p>
        {error.details?.map((d, i) => (
          <p key={i}>
            {d.location}: {d.message}
          </p>
        ))}
      </div>
    </div>
  );
}
