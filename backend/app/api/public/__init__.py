"""Public, read-only routes. No login."""

from fastapi import APIRouter

from app.api.public import collections, contact, photos

router = APIRouter()
router.include_router(photos.router)
router.include_router(collections.router)
router.include_router(contact.router)
