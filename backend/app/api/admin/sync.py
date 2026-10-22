"""Admin routes to start the Unsplash sync and see how it is doing."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.api.admin.deps import Auditor, get_auditor
from app.schemas.sync import SyncStatusOut
from app.services.sync import SyncAlreadyRunning, SyncService

router = APIRouter(prefix="/sync", tags=["admin-sync"])


def get_sync_service(request: Request) -> SyncService:
    state = request.app.state
    return SyncService(
        state.session_factory, state.unsplash, state.storage, state.settings, state.clock
    )


def _start(
    full: bool, background: BackgroundTasks, sync: SyncService, audit: Auditor
) -> dict[str, str]:
    try:
        sync.acquire()  # refuse immediately if one is running
    except SyncAlreadyRunning:
        raise HTTPException(status_code=409, detail="a sync is already running") from None
    audit("sync.start", "full" if full else "incremental")
    background.add_task(sync.execute, full)
    return {"status": "started"}


@router.post("", status_code=202)
def start(
    background: BackgroundTasks,
    sync: SyncService = Depends(get_sync_service),
    audit: Auditor = Depends(get_auditor),
) -> dict[str, str]:
    return _start(False, background, sync, audit)


@router.post("/full", status_code=202)
def start_full(
    background: BackgroundTasks,
    sync: SyncService = Depends(get_sync_service),
    audit: Auditor = Depends(get_auditor),
) -> dict[str, str]:
    return _start(True, background, sync, audit)


@router.get("/status")
def status(sync: SyncService = Depends(get_sync_service)) -> SyncStatusOut:
    s = sync.status()
    return SyncStatusOut(
        running=s.running,
        last_started_at=s.last_started_at,
        last_finished_at=s.last_finished_at,
        last_imported=s.last_imported,
        last_error=s.last_error,
        rate_limit_remaining=s.rate_limit_remaining,
        pending=s.pending,
    )
