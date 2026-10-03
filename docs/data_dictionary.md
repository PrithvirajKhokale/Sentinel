# Sentinel — Data Dictionary

## 1. Purpose

This document defines the data fields used by Sentinel, including their meaning, expected type, role in the system, and whether they are original or derived features.

The data dictionary will be updated as the actual project dataset is inspected and the final schema is established.

---

## 2. Project Identification Fields

| Field | Type | Description | Role |
|---|---|---|---|
| `project_id` | String | Unique identifier for a project | Identifier |
| `project_name` | String | Name of the project | Descriptive |
| `ministry` | Categorical | Ministry associated with the project | Feature |
| `sector` | Categorical | Sector/category associated with the project | Feature |

---

## 3. Financial Fields

| Field | Type | Description | Role |
|---|---|---|---|
| `project_cost` | Numeric | Approved or estimated project cost | Feature |
| `expenditure` | Numeric | Expenditure incurred on the project | Feature |

Additional financial fields will be added after the source dataset is analyzed.

---

## 4. Schedule Fields

| Field | Type | Description | Role |
|---|---|---|---|
| `start_date` | Date | Date on which the project started | Feature |
| `expected_completion_date` | Date | Planned completion date | Feature |
| `actual_completion_date` | Date | Actual completion date, when available | Target-related |
| `snapshot_date` | Date | Date associated with a project monitoring record | Temporal |

---

## 5. Progress Fields

| Field | Type | Description | Role |
|---|---|---|---|
| `planned_physical_progress` | Numeric | Expected physical progress at a particular point in time | Feature |
| `actual_physical_progress` | Numeric | Actual physical progress at a particular point in time | Feature |

---

## 6. Project Status and Issue Fields

| Field | Type | Description | Role |
|---|---|---|---|
| `milestone_status` | Categorical | Status of relevant project milestones | Feature |
| `issues` | Text/Categorical | Recorded issues or problems associated with the project | Feature |
| `project_status` | Categorical | Current status of the project | Feature/Descriptive |

The exact values and categories will be determined from the source dataset.

---

## 7. Derived Features

Sentinel may derive additional features from the original project data.

### 7.1 Progress Variance

Difference between actual and planned physical progress.

```text
Progress Variance =
Actual Physical Progress - Planned Physical Progress
```

## 8. Observed August 2026 report schema

See [Table 6 extraction notes](data-extraction.md) for the observed source columns, units, raw-value policy, and validated first 10 records. The fields above remain provisional; they are not all present in this report.

## 9. Full August extraction context

The full Table 6 output adds ministry, sector, all contributing PDF/printed pages, and raw physical cells as JSON. See [full extraction audit](august-full-extraction.md) for definitions, coverage and explicit missing-marker counts.
