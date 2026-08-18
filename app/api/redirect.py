from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.redis import get_cache, set_cache
from app.models.url import URL, Click

router = APIRouter()


@router.get("/{code}", summary="Redirect short URL to original")
async def redirect_to_url(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Redirect a short code to the original URL.
    
    Cache-first: checks Redis before hitting PostgreSQL.
    Records click analytics asynchronously.
    """
    # 1. Check Redis cache first (fastest path)
    cached_url = await get_cache(f"url:{code}")
    if cached_url:
        # Record click in background (fire-and-forget)
        await _record_click(code, request, db)
        return RedirectResponse(url=cached_url, status_code=301)

    # 2. Cache miss — query PostgreSQL
    result = await db.execute(
        select(URL).where(URL.short_code == code, URL.is_active == True)
    )
    url_record = result.scalar_one_or_none()

    if not url_record:
        raise HTTPException(status_code=404, detail=f"Short URL '{code}' not found or expired")

    # Check expiration
    if url_record.is_expired:
        await db.execute(
            update(URL).where(URL.id == url_record.id).values(is_active=False)
        )
        await db.commit()
        raise HTTPException(status_code=410, detail="This short URL has expired")

    # 3. Re-populate cache (24h TTL)
    await set_cache(f"url:{code}", url_record.original_url, expire=86400)

    # 4. Record click
    await _record_click(code, request, db, url_record.id)

    return RedirectResponse(url=url_record.original_url, status_code=301)


async def _record_click(
    code: str,
    request: Request,
    db: AsyncSession,
    url_id: int = None,
):
    """Record a click event for analytics."""
    try:
        click = Click(
            short_code=code,
            url_id=url_id,
            ip_address=request.client.host,
            referrer=request.headers.get("referer", ""),
            user_agent=request.headers.get("user-agent", ""),
        )
        db.add(click)
        await db.execute(
            update(URL)
            .where(URL.short_code == code)
            .values(click_count=URL.click_count + 1)
        )
        await db.commit()
    except Exception:
        pass  # Never fail a redirect due to analytics error
