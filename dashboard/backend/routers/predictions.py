from datetime import timedelta
from fastapi import APIRouter, HTTPException
from core.db import fetchrow, fetch

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("/latest")
async def get_latest_predictions(region_id: str):
    """Get latest 24h prediction for a region."""
    row = await fetchrow(
        """
        SELECT created_at, 
            horizon_h01, horizon_h02, horizon_h03, horizon_h04,
            horizon_h05, horizon_h06, horizon_h07, horizon_h08,
            horizon_h09, horizon_h10, horizon_h11, horizon_h12,
            horizon_h13, horizon_h14, horizon_h15, horizon_h16,
            horizon_h17, horizon_h18, horizon_h19, horizon_h20,
            horizon_h21, horizon_h22, horizon_h23, horizon_h24
        FROM silver.predictions
        WHERE region_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        region_id
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="No predictions found")
    
    predictions = []
    for i in range(1, 25):
        val = row[f"horizon_h{i:02d}"]
        predictions.append(float(val) if val is not None else None)
    
    return {
        "region_id": region_id,
        "created_at": row["created_at"].isoformat(),
        "predictions": predictions
    }

@router.get("/accuracy")
async def get_prediction_accuracy(region_id: str):
    """Get MAPE per horizon (h+1 to h+24) for the latest prediction."""
    row = await fetchrow(
        """
        SELECT created_at,
            horizon_h01, horizon_h02, horizon_h03, horizon_h04,
            horizon_h05, horizon_h06, horizon_h07, horizon_h08,
            horizon_h09, horizon_h10, horizon_h11, horizon_h12,
            horizon_h13, horizon_h14, horizon_h15, horizon_h16,
            horizon_h17, horizon_h18, horizon_h19, horizon_h20,
            horizon_h21, horizon_h22, horizon_h23, horizon_h24
        FROM silver.predictions
        WHERE region_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        region_id
    )
    
    if not row:
        raise HTTPException(status_code=404, detail="No predictions found")
    
    created_at = row["created_at"]
    
    # Build dynamic query to get actual demand for each horizon
    horizon_data = []
    for h in range(1, 25):
        pred_val = row[f"horizon_h{h:02d}"]
        if pred_val is None:
            horizon_data.append({"horizon": h, "mape": None})
            continue
        
        # Get actual demand at created_at + h hours
        actual_row = await fetchrow(
            """
            SELECT demand_mw FROM silver.features_ml
            WHERE region_id = $1 AND time = $2
            """,
            region_id,
            created_at + timedelta(hours=h)
        )
        
        if actual_row and actual_row["demand_mw"] and actual_row["demand_mw"] > 0:
            actual = float(actual_row["demand_mw"])
            predicted = float(pred_val)
            mape = abs((actual - predicted) / actual) * 100
            horizon_data.append({"horizon": h, "mape": round(mape, 2)})
        else:
            horizon_data.append({"horizon": h, "mape": None})
    
    return {
        "region_id": region_id,
        "created_at": created_at.isoformat(),
        "accuracy": horizon_data
    }