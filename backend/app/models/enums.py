"""Enums shared by several models."""

from enum import StrEnum


class Status(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
