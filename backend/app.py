from typing import Annotated
from fastapi import FastAPI, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException
from .db import engine_from_env
from .models import ActiveDataset, Revision, Snapshot
from .schemas import DetailQuery, Envelope, ListQuery


class APIError(Exception):
    def __init__(self, status, code, message, version=None):
        self.status, self.code, self.message, self.version = status, code, message, version


def create_app(engine=None):
    app = FastAPI(title="Sentinel local monitoring", version="1", docs_url="/docs")
    app.state.engine = engine if engine is not None else engine_from_env()

    def error(status,code,message,version=None,details=None):
        return JSONResponse(status_code=status,content=dict(error=dict(code=code,message=message,details=details or []),
                            meta=dict(contract_version="1",dataset_version=version)))

    @app.exception_handler(APIError)
    async def api_error(request,exc):
        return error(exc.status,exc.code,exc.message,exc.version)

    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):
        details = []
        for item in exc.errors():
            location = ".".join(map(str,item["loc"]))
            if item["type"] == "string_pattern_mismatch" and location == "query.report_month":
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
        if query.report_month not in row.reports:
            raise APIError(404,"REPORT_NOT_AVAILABLE","Report month is unavailable.",version)
        return row

    def envelope(data,revision,filters,pagination=None):
        meta = dict(contract_version="1",dataset_version=revision.version,validation_status="validated_history",filters=filters)
        if pagination is not None:
            meta["pagination"] = pagination
        return dict(data=data,meta=meta,warnings=[w for w in revision.warnings if w["report_month"]==filters["report_month"]])

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

    return app
