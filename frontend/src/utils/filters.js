import { IDENTITY_FIELDS } from "../constants.js";

export function matches(s, filters) {
  return IDENTITY_FIELDS.every(
    (f) => !filters[f]?.length || filters[f].includes(s.identity[f]),
  );
}
// Filter choices retain exact report labels while allowing case-insensitive discovery.
export function matchingFilterOptions(values, input) {
  const needle = input.trim().toLocaleLowerCase();
  return values.filter((v) => v.toLocaleLowerCase().includes(needle));
}
