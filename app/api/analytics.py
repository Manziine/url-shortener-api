from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.url import URL, Click

router = APIRouter()


@router.get("/analytics/{code}")
async def get_analytics(code: str, db: AsyncSession = Depends(get_db)):
    """Get detailed click analytics for a short URL."""
    url = (await db.execute(select(URL).where(URL.short_code == code))).scalar_one_or_none()
    if not url:
        raise HTTPException(status_code=404, detail=f"URL '{code}' not found")

    clicks = (await db.execute(select(Click).where(Click.short_code == code))).scalars().all()

    # Top referrers
    referrer_counts: dict = {}
    for c in clicks:
        ref = c.referrer or "direct"
        referrer_counts[ref] = referrer_counts.get(ref, 0) + 1

    top_referrers = sorted(referrer_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "short_code": code,
        "original_url": url.original_url,
        "total_clicks": url.click_count,
        "created_at": url.created_at,
        "expires_at": url.expires_at,
        "is_active": url.is_active,
        "top_referrers": [{"referrer": r, "count": c} for r, c in top_referrers],
        "recent_clicks": [
            {
                "clicked_at": c.clicked_at,
                "ip": c.ip_address,
                "referrer": c.referrer,
            }
            for c in sorted(clicks, key=lambda x: x.clicked_at, reverse=True)[:20]
        ],
    }
