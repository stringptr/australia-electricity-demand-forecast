from fastapi import APIRouter
from core.db import fetch, fetchrow
from datetime import datetime, timedelta

router = APIRouter(prefix="/demand", tags=["demand"])

@router.get("/latest")
async def get_latest_demand():
    """Get latest demand for all 5 regions."""
    rows = await fetch(
        """
        SELECT DISTINCT ON (region_id) region_id, time, demand_mw
        FROM silver.demand_5min
        ORDER BY region_id, time DESC
        """
    )
    return {
        "regions": [
            {
                "region_id": row["region_id"],
                "time": row["time"].isoformat(),
                "demand_mw": float(row["demand_mw"])
            }
            for row in rows
        ]
    }

@router.get("/history")
async def get_demand_history(region_id: str, hours: int = 24):
    """Get hourly demand history for a region."""
    since = datetime.utcnow() - timedelta(hours=hours)
    rows = await fetch(
        """
        SELECT time, demand_mw
        FROM silver.demand_5min
        WHERE region_id = $1 AND time >= $2
        ORDER BY time
        """,
        region_id, since
    )
    return {
        "region_id": region_id,
        "hours": hours,
        "data": [
            {"time": row["time"].isoformat(), "demand_mw": float(row["demand_mw"])}
            for row in rows
        ]
    }