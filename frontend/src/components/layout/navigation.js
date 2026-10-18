import { Search, GitCompareArrows, AlertTriangle, FileText } from "lucide-react";

// Main pages, in sidebar order: [key, label, icon].
export const PAGES = [
  ["explore", "Project explorer", Search],
  ["portfolio", "Portfolio comparisons", GitCompareArrows],
  ["risk", "Risk intelligence", AlertTriangle],
  ["evidence", "Evidence & gaps", FileText],
];

export const pageLabel = (key) => PAGES.find(([k]) => k === key)?.[1];
