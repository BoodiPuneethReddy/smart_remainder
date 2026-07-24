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
    Search colleges by name, university, state, district, or alias.
    Supports case-insensitive partial matching across all fields.
    """
    q_stripped = q.strip()
    if not q_stripped:
        return []

    q_lower = q_stripped.lower()
    q_like = f"%{q_stripped}%"

    colleges = (
        db.query(College)
        .outerjoin(CollegeAlias, College.id == CollegeAlias.college_id)
        .filter(
            College.is_active == True,
            or_(
                College.college_name.ilike(q_like),
                College.university.ilike(q_like),
                College.state.ilike(q_like),
                College.district.ilike(q_like),
                CollegeAlias.alias.ilike(q_like),
            )
        )
        .distinct()
        .limit(limit * 3)
        .all()
    )

    def rank(c: College) -> int:
        name_lower = c.college_name.lower()
        if name_lower.startswith(q_lower):
            return 0
        if q_lower in name_lower:
            return 1
        if c.district and q_lower in c.district.lower():
            return 2
        if c.state and q_lower in c.state.lower():
            return 3
        return 4

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
