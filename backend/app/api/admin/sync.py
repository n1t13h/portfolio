"""Admin routes to start the Unsplash sync and see how it is doing."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.api.admin.deps import get_audit_trail
from app.schemas.sync import SyncStatusOut
from app.services.audit import AuditTrail
from app.services.sync import SyncAlreadyRunning, SyncService

router = APIRouter(prefix="/sync", tags=["admin-sync"])


def get_sync_service(request: Request) -> SyncService:
    state = request.app.state
    return SyncService(
        state.uow_factory, state.unsplash, state.storage, state.settings, state.clock
    )


def _start(
    full: bool, background: BackgroundTasks, sync: SyncService, audit: AuditTrail
) -> dict[str, str]:
    try:
        # refuse immediately if one is running; a start is recorded with the lock
        sync.acquire(audit, "full" if full else "incremental")
    except SyncAlreadyRunning:
        raise HTTPException(status_code=409, detail="a sync is already running") from None
    background.add_task(sync.execute, full)
    return {"status": "started"}


@router.post("", status_code=202)
def start(
    background: BackgroundTasks,
    sync: SyncService = Depends(get_sync_service),
    audit: AuditTrail = Depends(get_audit_trail),
) -> dict[str, str]:
    return _start(False, background, sync, audit)


@router.post("/full", status_code=202)
def start_full(
    background: BackgroundTasks,
    sync: SyncService = Depends(get_sync_service),
    audit: AuditTrail = Depends(get_audit_trail),
) -> dict[str, str]:
    return _start(True, background, sync, audit)


@router.get("/status")
def status(sync: SyncService = Depends(get_sync_service)) -> SyncStatusOut:
    return sync.status()
