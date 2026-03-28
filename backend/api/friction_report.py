"""API endpoints for friction reporting and analytics."""

from fastapi import APIRouter
from typing import Any

from civic_agent.friction_detector import aggregate_friction_stats, load_friction_events


router = APIRouter(prefix="/api", tags=["friction"])


@router.get("/friction-stats")
async def get_friction_stats() -> dict[str, Any]:
    """Get aggregated friction statistics for bias detection.
    
    Returns:
        Dictionary with total_events, by_algorithm, by_sentiment, top_questions
    """
    return aggregate_friction_stats()


@router.get("/friction-events")
async def get_friction_events(limit: int = 50) -> dict[str, Any]:
    """Get recent friction events.
    
    Args:
        limit: Maximum number of events to return (default 50, max 100)
        
    Returns:
        Dictionary with events list
    """
    limit = min(max(limit, 1), 100)
    events = load_friction_events(limit=limit)
    
    return {
        "count": len(events),
        "events": events
    }
