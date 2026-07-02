from fastapi import APIRouter
from core.db import fetchval
import httpx
from core.config import settings

router = APIRouter(prefix="/metrics", tags=["metrics"])

@router.get("/global")
async def get_global_metrics():
    """Get global metrics: max demand (entire history), inference latency, staleness."""
    max_demand = await fetchval("SELECT MAX(demand_mw) FROM silver.demand_5min")
    
    # Round up to nearest 5000
    gradient_max = ((int(max_demand) + 4999) // 5000) * 5000 if max_demand else 20000
    
    # Fetch VM metrics
    vm_metrics = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Inference latency
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query",
                params={"query": "inference_latency_seconds"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data", {}).get("result"):
                    vm_metrics["inference_latency"] = float(data["data"]["result"][0]["value"][1])
            
            # Demand staleness
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query",
                params={"query": "demand_staleness_seconds"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data", {}).get("result"):
                    vm_metrics["demand_staleness"] = float(data["data"]["result"][0]["value"][1])
            
            # NATS messages
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query",
                params={"query": "nats_messages_received_total"}
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data", {}).get("result"):
                    vm_metrics["nats_messages"] = float(data["data"]["result"][0]["value"][1])
    except Exception:
        pass
    
    return {
        "max_demand": float(max_demand) if max_demand else 0,
        "gradient_max": gradient_max,
        "vm_metrics": vm_metrics
    }