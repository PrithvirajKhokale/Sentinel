from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListQuery(StrictModel):
    report_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    dataset_version: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    ministry: list[str] = Field(default_factory=list)
    sector: list[str] = Field(default_factory=list)
    state: list[str] = Field(default_factory=list)
    agency: list[str] = Field(default_factory=list)
    project_code: list[str] = Field(default_factory=list)
    q: str | None = Field(default=None, min_length=1, max_length=200)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class DetailQuery(StrictModel):
    report_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    dataset_version: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class Value(StrictModel):
    raw: str
    normalized: str | None
    unit: Literal["Rs. crore", "percent", "month"] | None
    missing_reason: Literal["source_blank", "source_marker"] | None


class Warning(StrictModel):
    scope: Literal["snapshot", "pair", "report"]
    code: str
    fields: list[str]
    report_month: str | None
    source_pdf_pages: list[int]
    message: str


class Identity(StrictModel):
    project_name: str
    agency: str
    ministry: str
    sector: str
    state: str


class Values(StrictModel):
    legacy_ocms_code: Value
    pmgid: Value
    approval_date: Value
    start_date: Value
    original_target_doc: Value
    revised_doc: Value
    original_cost_rs_crore: Value
    revised_cost_rs_crore: Value
    cumulative_expenditure_rs_crore: Value
    physical_progress_pct: Value


class Provenance(StrictModel):
    source_filename: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    pdf_pages: list[int]
    printed_pages: list[int]
    physical_cells: list[str] = Field(min_length=8,max_length=8)


class Temporal(StrictModel):
    reporting_cutoff_date: str | None
    reporting_cutoff_raw: str
    source_pdf_page: int = Field(ge=1)
    publication_date: str | None
    first_available_date: str | None
    source_platform: str


class Quality(StrictModel):
    snapshot_flags: list[Warning]
    source_notes: list[dict]


class SnapshotResponse(StrictModel):
    project_code: str
    report_month: str
    report_month_label: str
    serial_no: str
    identity: Identity
    values: Values
    provenance: Provenance
    temporal: Temporal
    quality: Quality


class Envelope(StrictModel):
    data: list[SnapshotResponse] | SnapshotResponse
    meta: dict
    warnings: list[Warning]
