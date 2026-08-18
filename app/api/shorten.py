from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from app.core.database import get_db
from app.core.redis import set_cache, rate_limit_check
from app.core.shortener import generate_short_code, is_valid_url, is_safe_slug
from app.models.url import URL
from app.core.config import settings

router = APIRouter()


class ShortenRequest(BaseModel):
    url: str = Field(..., description="The long URL to shorten")
    custom_slug: Optional[str] = Field(None, description="Custom short code (3-50 chars, alphanumeric/hyphens)")
    expires_in_days: Optional[int] = Field(None, ge=1, le=365, description="URL expiration in days")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://github.com/Manziine",
                "custom_slug": "portfolio",
                "expires_in_days": 30,
            }
        }


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    expires_at: Optional[datetime]
    created_at: datetime


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
async def create_short_url(
    payload: ShortenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a shortened URL.
    
    - Validates URL format and safety
    - Supports custom slugs
    - Rate limited: 10/min anonymous, 100/min authenticated
    - Returns short URL with analytics-ready metadata
    """
    client_ip = request.client.host

    # Rate limit check
    allowed = await rate_limit_check(client_ip, limit=10, window=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again in 60 seconds.",
            headers={"Retry-After": "60"},
        )

    # Validate URL
    if not is_valid_url(payload.url):
        raise HTTPException(status_code=422, detail="Invalid URL. Must start with http:// or https://")

    # Determine short code
    if payload.custom_slug:
        if not is_safe_slug(payload.custom_slug):
            raise HTTPException(
                status_code=422,
                detail="Custom slug must be 3-50 characters: letters, digits, hyphens, underscores only",
            )
        # Check if slug is taken
        existing = await db.execute(select(URL).where(URL.short_code == payload.custom_slug))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail=f"Slug '{payload.custom_slug}' is already taken")
        short_code = payload.custom_slug
    else:
        # Auto-generate unique code (with collision retry)
        short_code = await _generate_unique_code(db)

    # Calculate expiry
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    # Save to database
    url_record = URL(
        short_code=short_code,
        original_url=payload.url,
        expires_at=expires_at,
        created_by_ip=client_ip,
    )
    db.add(url_record)
    await db.commit()
    await db.refresh(url_record)

    # Warm the cache immediately
    cache_ttl = payload.expires_in_days * 86400 if payload.expires_in_days else 86400
    await set_cache(f"url:{short_code}", payload.url, expire=cache_ttl)

    short_url = f"{settings.BASE_URL}/{short_code}"

    return ShortenResponse(
        short_code=short_code,
        short_url=short_url,
        original_url=payload.url,
        expires_at=expires_at,
        created_at=url_record.created_at,
    )


async def _generate_unique_code(db: AsyncSession, max_attempts: int = 5) -> str:
    """Generate a unique short code, retrying on collision."""
    for attempt in range(max_attempts):
        code = generate_short_code(length=6 + (attempt // 3))  # Increase length on repeated collisions
        existing = await db.execute(select(URL).where(URL.short_code == code))
        if not existing.scalar_one_or_none():
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique short code. Please try again.")
