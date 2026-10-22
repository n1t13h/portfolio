"""Public contact form endpoint."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.core.deps import client_ip
from app.schemas.contact import ContactBody
from app.services.contact import ContactService, RateLimited

router = APIRouter(tags=["contact"])


@router.post("/contact", status_code=202)
def contact(body: ContactBody, request: Request, background: BackgroundTasks) -> dict[str, str]:
    if body.website:  # a bot filled the hidden field: pretend success, keep nothing
        return {"status": "received"}
    state = request.app.state
    service = ContactService(state.uow_factory, state.notifier, state.settings, state.clock)
    try:
        service.submit(body.name, body.email, body.message, client_ip(request))
    except RateLimited:
        raise HTTPException(status_code=429, detail="too many messages, try again later") from None
    background.add_task(service.deliver_pending)  # after the response, so Telegram can't slow it
    return {"status": "received"}
