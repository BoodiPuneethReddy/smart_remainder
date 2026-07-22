"""seed/seed_colleges.py — College + Alias seeder

Runs once on startup if the colleges table is empty.
Loads colleges_raw.json (AISHE-derived, ~38K entries) and college_aliases.json.

Dataset source: VarthanV/Indian-Colleges-List (GitHub)
Derived from: All India Survey on Higher Education (AISHE), Ministry of Education
Coverage: ~38,376 colleges across all Indian states and union territories
License: Derived from publicly available government data (Open Government License, India)
"""

import os
import json
import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SEED_DIR = os.path.dirname(os.path.abspath(__file__))


def seed_colleges(db: Session) -> None:
    """
    Insert colleges and aliases if the colleges table is empty.
    Uses bulk_insert_mappings for performance (~38K records in a few seconds).
    """
    from app.models.college import College, CollegeAlias

    existing_count = db.query(College).count()
    if existing_count > 0:
        logger.info("College seeder: %d colleges already present, skipping.", existing_count)
        return

    # ── Load colleges ─────────────────────────────────────────────────────────
    colleges_file = os.path.join(_SEED_DIR, "colleges_raw.json")
    if not os.path.exists(colleges_file):
        logger.warning("College seeder: colleges_raw.json not found at %s", colleges_file)
        return

    with open(colleges_file, "r", encoding="utf-8-sig") as f:
        raw_data = json.load(f)

    college_mappings = []
    college_name_to_id: dict[str, int] = {}

    for i, entry in enumerate(raw_data, start=1):
        college_name = entry.get("college", "").strip()
        # Strip the AISHE ID suffix from college names: "ABC College (Id: C-12345)"
        if "(Id:" in college_name:
            college_name = college_name[:college_name.index("(Id:")].strip()

        university = entry.get("university", "").strip()
        if "(Id:" in university:
            university = university[:university.index("(Id:")].strip()

        state = entry.get("state", "").strip()
        district = entry.get("district", "").strip()
        college_type = entry.get("college_type", "").strip()

        if not college_name or not state:
            continue

        college_mappings.append({
            "id": i,
            "college_name": college_name,
            "university": university or None,
            "state": state,
            "district": district or None,
            "college_type": college_type or None,
            "is_active": True,
        })
        college_name_to_id[college_name.lower()] = i

    logger.info("College seeder: inserting %d colleges...", len(college_mappings))
    db.bulk_insert_mappings(College, college_mappings)
    db.flush()
    logger.info("College seeder: college insert complete.")

    # ── Load aliases ──────────────────────────────────────────────────────────
    aliases_file = os.path.join(_SEED_DIR, "college_aliases.json")
    if not os.path.exists(aliases_file):
        logger.warning("College seeder: college_aliases.json not found, skipping aliases.")
        db.commit()
        return

    with open(aliases_file, "r", encoding="utf-8") as f:
        alias_data = json.load(f)

    # Re-query to get actual DB IDs (handles autoincrement)
    all_colleges = db.query(College).all()
    name_to_db_id: dict[str, int] = {c.college_name.lower(): c.id for c in all_colleges}

    alias_mappings = []
    alias_id = 1
    for entry in alias_data:
        college_name = entry.get("college_name", "").strip().lower()
        # Fuzzy match: try exact, then substring
        matched_id = name_to_db_id.get(college_name)
        if not matched_id:
            # Try substring match
            for db_name, db_id in name_to_db_id.items():
                if college_name in db_name or db_name in college_name:
                    matched_id = db_id
                    break

        if not matched_id:
            logger.debug("College seeder: no match for alias source '%s'", college_name)
            continue

        for alias in entry.get("aliases", []):
            if alias and alias.strip():
                alias_mappings.append({
                    "id": alias_id,
                    "college_id": matched_id,
                    "alias": alias.strip(),
                })
                alias_id += 1

    if alias_mappings:
        logger.info("College seeder: inserting %d aliases...", len(alias_mappings))
        db.bulk_insert_mappings(CollegeAlias, alias_mappings)

    db.commit()
    logger.info(
        "College seeder: done. %d colleges, %d aliases.",
        len(college_mappings), len(alias_mappings),
    )
