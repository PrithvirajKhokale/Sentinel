// Public surface of the data layer: the contract client plus shared helpers.
export { createClient, queryString } from "./client.js";
export { exampleResponse, qualityCounts } from "./reference.js";
export { APIError } from "./errors.js";
export { MONTHS, IDENTITY_FIELDS, VERSION, LABELS } from "../constants.js";
export { pretty, monthLabel, decimal, formatValue } from "../utils/format.js";
export { matches, matchingFilterOptions } from "../utils/filters.js";
