from pathlib import Path
import os
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from .db import engine_from_env
from .models import ActiveDataset, Revision, Snapshot, Comparison
from .monitoring import (month_range, month_number, present_comparison, portfolio_comparison,
                         quality_counts, scoped_codes, history_pair_warnings)
from .presentation import warning
from .risk_intelligence import signals_for_pair, summarize
from .schemas import DetailQuery, Envelope, ListQuery, HistoryQuery, PortfolioQuery, PortfolioEnvelope, FilterOptionsEnvelope, SignalsEnvelope, SignalsQuery


class APIError(Exception):
    def __init__(self, status, code, message, version=None):
        self.status, self.code, self.message, self.version = status, code, message, version


def create_app(engine=None):
    app = FastAPI(title="Sentinel monitoring", version="1", docs_url="/docs", redoc_url="/redoc",
                  openapi_url="/openapi.json")
    app.state.engine = engine if engine is not None else engine_from_env()

    def error(status,code,message,version=None,details=None):
        return JSONResponse(status_code=status,content=dict(error=dict(code=code,message=message,details=details or []),
                            meta=dict(contract_version="1",dataset_version=version)))

    @app.middleware("http")
    async def headers(request, call_next):
        response = await call_next(request)
        if request.url.path == "/api" or request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    # Public read-only API: any site may call it; no credentials are involved.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                       allow_methods=["GET"], allow_headers=["Content-Type"])

    @app.get("/healthz", include_in_schema=False)
    def health():
        return {"status": "ok"}

    @app.exception_handler(APIError)
    async def api_error(request,exc):
        return error(exc.status,exc.code,exc.message,exc.version)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        details = []
        for item in exc.errors():
            location = ".".join(map(str,item["loc"]))
            if item["type"] == "string_pattern_mismatch" and location in {"query.report_month", "query.from_month", "query.to_month", "query.comparison_month"}:
                details.append(dict(location=location,code="invalid_month_format",message="Expected YYYY-MM."))
            else:
                details.append(dict(location=location,code=item["type"],message=item["msg"]))
        return error(422,"VALIDATION_ERROR","Request parameters are invalid.",details=details)

    @app.exception_handler(HTTPException)
    async def http_error(request,exc):
        return error(exc.status_code,"NOT_FOUND" if exc.status_code==404 else "HTTP_ERROR","Requested route is unavailable.")

    @app.exception_handler(Exception)
    async def internal(request,exc):
        return error(500,"INTERNAL_ERROR","Unexpected service failure.")

    def revision(session,query):
        version = query.dataset_version
        if version is None:
            active = session.get(ActiveDataset,1)
            version = active.version if active else None
            if version is None:
                raise APIError(503,"DATASET_NOT_VALIDATED","No validated active dataset is available.")
        row = session.get(Revision,version)
        if row is None:
            raise APIError(404,"DATASET_NOT_FOUND","Dataset version is unavailable.",version)
        if getattr(query,"report_month",None) is not None and query.report_month not in row.reports:
            raise APIError(404,"REPORT_NOT_AVAILABLE","Report month is unavailable.",version)
        return row

    def envelope(data,revision,filters,pagination=None):
        meta = dict(contract_version="1",dataset_version=revision.version,validation_status="validated_history",filters=filters)
        if pagination is not None:
            meta["pagination"] = pagination
        # Snapshot/list selects one report; history selects all reports in its range.
        months = {filters["report_month"]} if "report_month" in filters else set(month_range(filters["from_month"],filters["to_month"]))
        if filters.get("comparison_month"):
            months.add(filters["comparison_month"])
        return dict(data=data,meta=meta,warnings=[w for w in revision.warnings if w["report_month"] in months])

    @app.get("/api/v1/risk-signals",response_model=SignalsEnvelope)
    def risk_signals(query: Annotated[SignalsQuery, Query()]):
        """Factual reported-change flags for *adjacent*, same-code observations.

        No risk probability, score, verified field-wise comparability or
        completion outcome is inferred. The response is dataset-pinned.
        """
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            current = query.report_month
            prior = next((m for m in rev.reports if month_number(current)-month_number(m)==1),None)
            values = dict(report_month=current)
            conditions = [Snapshot.version==rev.version,Snapshot.report_month==current]
            for field in ("ministry","sector","state","agency","project_code"):
                selected = sorted(set(getattr(query,field)))
                if selected:
                    conditions.append(getattr(Snapshot,field).in_(selected))
                    values[field] = selected
            if query.q is not None:
                literal = query.q.lower().replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
                conditions.append(func.lower(Snapshot.project_name).like("%"+literal+"%",escape="\\"))
                values["q"] = query.q
            if prior is None:
                summary = summarize([],0)
                results = []
            else:
                values["comparison_month"] = prior
                after = {s.project_code:s for s in session.scalars(select(Snapshot).where(*conditions)).all()}
                codes = list(after)
                before = {s.project_code:s for s in session.scalars(select(Snapshot).where(
                    Snapshot.version==rev.version,Snapshot.report_month==prior,
                    Snapshot.project_code.in_(codes))).all()} if codes else {}
                shared = sorted(set(after) & set(before))
                pairs = {c.project_code:c for c in session.scalars(select(Comparison).where(
                    Comparison.version==rev.version,Comparison.before_month==prior,
                    Comparison.after_month==current,Comparison.project_code.in_(shared))).all()} if shared else {}
                if set(pairs) != set(shared):
                    raise APIError(500,"INTERNAL_ERROR","Validated adjacent comparison data is incomplete.",rev.version)
                results = []
                for code in shared:
                    pair = present_comparison(pairs[code].payload)
                    results.extend(signals_for_pair(pair,before[code].payload,after[code].payload))
                summary = summarize(results,len(shared))
            if query.signal_type:
                values["signal_type"] = query.signal_type
                results = [r for r in results if r["type"] == query.signal_type]
            offset = (query.page-1)*query.page_size
            pagination = dict(page=query.page,page_size=query.page_size,
                              total_items=len(results),total_pages=(len(results)+query.page_size-1)//query.page_size)
            reply = envelope(dict(report_month=current,comparison_month=prior,
                                  scope="shared_observed_projects",summary=summary,
                                  signals=results[offset:offset+query.page_size]),rev,values,pagination)
            reply["warnings"].append(warning("reported_signals_not_predictions",[],current,[],
                "Reported changes are factual screening cues, not independent project-risk assessments. Pair-wide review flags remain in each signal.","report"))
            return reply

    @app.get("/api/v1/filter-options",response_model=FilterOptionsEnvelope)
    def filter_options(query: Annotated[PortfolioQuery, Query()]):
        """Discover exact labels across the selected report and optional prior report.

        Exposes only distinct already-public reported identity labels, not project
        records. Values remain exact (including punctuation, case and spacing).
        """
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            months = [query.report_month]
            if query.comparison_month:
                if query.comparison_month not in rev.reports:
                    raise APIError(404,"REPORT_NOT_AVAILABLE","Comparison report month is unavailable.",rev.version)
                months.append(query.comparison_month)
            data = {}
            for field in ("sector","ministry","state","agency"):
                values = session.scalars(select(getattr(Snapshot,field)).where(
                    Snapshot.version==rev.version, Snapshot.report_month.in_(months)).distinct()).all()
                data[field] = sorted((value for value in values if value), key=str.casefold)
            filters = dict(report_month=query.report_month)
            if query.comparison_month:
                filters["comparison_month"] = query.comparison_month
            return envelope(data,rev,filters)

    @app.get("/api/v1/projects",response_model=Envelope)
    def projects(query: Annotated[ListQuery, Query()]):
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            conditions = [Snapshot.version==rev.version,Snapshot.report_month==query.report_month]
            filters = dict(report_month=query.report_month)
            for field in ("ministry","sector","state","agency","project_code"):
                values = sorted(set(getattr(query,field)))
                if values:
                    conditions.append(getattr(Snapshot,field).in_(values))
                    filters[field] = values
            if query.q is not None:
                # Escape SQL wildcard metacharacters: the contract promises a literal substring.
                text = query.q.lower().replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
                conditions.append(func.lower(Snapshot.project_name).like("%"+text+"%",escape="\\"))
                filters["q"] = query.q
            count = session.scalar(select(func.count()).select_from(Snapshot).where(*conditions))
            records = session.scalars(select(Snapshot).where(*conditions).order_by(Snapshot.project_code)
                                      .offset((query.page-1)*query.page_size).limit(query.page_size)).all()
            return envelope([r.payload for r in records],rev,filters,
                            dict(page=query.page,page_size=query.page_size,total_items=count,
                                 total_pages=(count+query.page_size-1)//query.page_size))

    @app.get("/api/v1/projects/{project_code}",response_model=Envelope)
    def project(project_code: str, query: Annotated[DetailQuery, Query()]):
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            record = session.get(Snapshot,(rev.version,project_code,query.report_month))
            if record is None:
                raise APIError(404,"PROJECT_NOT_OBSERVED","Project is not observed in this report's ongoing table.",rev.version)
            return envelope(record.payload,rev,dict(report_month=query.report_month))

    @app.get("/api/v1/projects/{project_code}/history",response_model=Envelope)
    def history(project_code: str, query: Annotated[HistoryQuery, Query()]):
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            start = query.from_month or min(rev.reports)
            end = query.to_month or max(rev.reports)
            for bound in (start,end):
                if bound not in rev.reports:
                    raise APIError(404,"REPORT_NOT_AVAILABLE","Report month is unavailable.",rev.version)
            if start > end:
                raise APIError(422,"VALIDATION_ERROR","from_month must not exceed to_month.",rev.version)
            known = session.scalar(select(Snapshot.project_code).where(Snapshot.version==rev.version,
                                    Snapshot.project_code==project_code).limit(1))
            if known is None:
                raise APIError(404,"PROJECT_NOT_FOUND","Project code is unknown in this dataset.",rev.version)
            rows = session.scalars(select(Snapshot).where(Snapshot.version==rev.version,
                                   Snapshot.project_code==project_code, Snapshot.report_month>=start,
                                   Snapshot.report_month<=end).order_by(Snapshot.report_month)).all()
            observed = {row.report_month:row.payload for row in rows}
            stored = session.scalars(select(Comparison).where(Comparison.version==rev.version,
                                     Comparison.project_code==project_code, Comparison.before_month>=start,
                                     Comparison.after_month<=end).order_by(Comparison.before_month)).all()
            pairs = [present_comparison(row.payload) for row in stored
                     if row.before_month in observed and row.after_month in observed
                     and month_number(row.after_month)-month_number(row.before_month)==1]
            ordered_months = month_range(start,end)
            expected = {(first,last) for first,last in zip(ordered_months,ordered_months[1:])
                        if first in observed and last in observed}
            if {(pair["before_month"],pair["after_month"]) for pair in pairs} != expected:
                raise APIError(500,"INTERNAL_ERROR","Validated adjacent comparison data is incomplete.",rev.version)
            filters = dict(from_month=start,to_month=end)
            offset = (query.page-1)*query.page_size
            result = envelope([row.payload for row in rows[offset:offset+query.page_size]],rev,filters,
                              dict(page=query.page,page_size=query.page_size,total_items=len(rows),
                                   total_pages=(len(rows)+query.page_size-1)//query.page_size))
            result["meta"].update(comparisons=pairs,
                                  not_observed_months=[month for month in month_range(start,end) if month not in observed])
            for pair in pairs:
                result["warnings"].extend(history_pair_warnings(pair,observed[pair["before_month"]],observed[pair["after_month"]]))
            return result

    @app.get("/api/v1/portfolio-summary",response_model=PortfolioEnvelope)
    def portfolio(query: Annotated[PortfolioQuery, Query()]):
        with Session(app.state.engine) as session:
            rev = revision(session,query)
            if query.comparison_month and query.comparison_month not in rev.reports:
                raise APIError(404,"REPORT_NOT_AVAILABLE","Comparison report month is unavailable.",rev.version)
            filters = dict(report_month=query.report_month)
            for field in ("ministry","sector","state","agency"):
                values = sorted(set(getattr(query,field)))
                if values:
                    filters[field] = values
            if query.comparison_month:
                filters["comparison_month"] = query.comparison_month
            after = {row.project_code:row for row in session.scalars(select(Snapshot).where(
                     Snapshot.version==rev.version,Snapshot.report_month==query.report_month)).all()}
            after_scope = scoped_codes(after,filters)
            payloads = [after[code].payload for code in sorted(after_scope)]
            data = dict(report_month=query.report_month,
                        counts=dict(snapshot_records=len(payloads),distinct_project_codes=len(after_scope),
                                    ministries=len({after[code].ministry for code in after_scope}),
                                    sectors=len({after[code].sector for code in after_scope})),
                        quality_counts=quality_counts(payloads),comparison=None)
            if query.comparison_month:
                before = {row.project_code:row for row in session.scalars(select(Snapshot).where(
                          Snapshot.version==rev.version,Snapshot.report_month==query.comparison_month)).all()}
                before_scope = scoped_codes(before,filters)
                common = before_scope & after_scope
                stored = {row.project_code:row.payload for row in session.scalars(select(Comparison).where(
                          Comparison.version==rev.version,Comparison.before_month==query.comparison_month,
                          Comparison.after_month==query.report_month,Comparison.project_code.in_(common))).all()}
                if set(stored) != common:
                    raise APIError(500,"INTERNAL_ERROR","Validated adjacent comparison data is incomplete.",rev.version)
                data["comparison"] = portfolio_comparison(before,after,before_scope,after_scope,stored,
                                                         query.comparison_month,query.report_month)
            result = envelope(data,rev,filters)
            if data["comparison"]:
                comparison = data["comparison"]
                if comparison["exclusion_reasons"]:
                    result["warnings"].append(warning("conservative_pair_screen",[],None,[],
                        "Pair-wide exclusions are review gates, not proof of usability or unusability of individual fields. See exclusion_reasons.","pair"))
                decrease_fields = [field for statuses,field in
                                   [("progress_changes","physical_progress_pct"),
                                    ("expenditure_changes","cumulative_expenditure_rs_crore")]
                                   if comparison[statuses].get("decreased",0)]
                if decrease_fields:
                    result["warnings"].append(warning("reported_decreases",decrease_fields,None,[],
                        "Counts retain reported decreases; their causes are unknown.","pair"))
            return result

    frontend = os.environ.get("SENTINEL_FRONTEND_DIR")
    if frontend:
        directory = Path(frontend).resolve()
        if not (directory / "index.html").is_file():
            raise ValueError("SENTINEL_FRONTEND_DIR must contain a built index.html")
        # Mount last so API routes and their contract errors retain precedence.
        app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return app
