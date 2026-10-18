import { LABELS } from "../constants.js";

export const pretty = (s) =>
  LABELS[s?.replace(/_raw$/, "")] ||
  (s || "").replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
export function monthLabel(m, short = false) {
  if (!m) return "Unknown";
  const [y, n] = m.split("-");
  return `${["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][Number(n) - 1]}${short ? "" : ` ${y}`}`;
}
// Decimal values remain strings. Formatting never rounds or converts money to floats.
export function decimal(s) {
  if (s === null || s === undefined) return "Unknown";
  const [whole, frac] = String(s).split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return grouped + (frac === undefined ? "" : "." + frac);
}
export function formatValue(v) {
  if (!v || v.normalized === null) return "Unknown";
  if (v.unit === "month") return monthLabel(v.normalized);
  return `${v.unit === "Rs. crore" ? "₹" : ""}${decimal(v.normalized)}${v.unit === "percent" ? "%" : ""}`;
}
