"""api/routes/colleges.py — College search endpoint"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.college import College, CollegeAlias
from pydantic import BaseModel

router = APIRouter(prefix="/api/colleges", tags=["colleges"])


class CollegeResponse(BaseModel):
    id: int
    college_name: str
    university: str | None
    state: str
    district: str | None

    model_config = {"from_attributes": True}


@router.get("/search", response_model=List[CollegeResponse])
def search_colleges(
    q: str = Query(..., min_length=1, max_length=100, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Search colleges by name, state, district, or alias.
    Supports partial matches, substring matches, and curated acronyms (e.g. 'SVCE').

    Returns top results ranked by relevance:
      1. Alias exact match
      2. College name prefix
      3. College name substring
      4. State/district match
    """
    q_stripped = q.strip()
    if not q_stripped:
        return []

    q_lower = q_stripped.lower()
    q_like = f"%{q_stripped}%"

    # Find college IDs that match via alias first
    alias_matches = (
        db.query(CollegeAlias.college_id)
        .filter(CollegeAlias.alias.ilike(q_like))
        .all()
    )
    alias_college_ids = {row[0] for row in alias_matches}

    # Query colleges
    colleges = (
        db.query(College)
        .filter(
            College.is_active == True,
            or_(
                College.id.in_(alias_college_ids),
                College.college_name.ilike(q_like),
                College.state.ilike(q_like),
                College.district.ilike(q_like),
            )
        )
        .limit(limit * 3)  # Over-fetch for ranking
        .all()
    )

    # Rank results: alias match first, then prefix, then substring
    def rank(c: College) -> int:
        name_lower = c.college_name.lower()
        if c.id in alias_college_ids:
            return 0
        if name_lower.startswith(q_lower):
            return 1
        if q_lower in name_lower:
            return 2
        return 3

    colleges_sorted = sorted(colleges, key=rank)[:limit]

    return [
        CollegeResponse(
            id=c.id,
            college_name=c.college_name,
            university=c.university,
            state=c.state,
            district=c.district,
        )
        for c in colleges_sorted
    ]
