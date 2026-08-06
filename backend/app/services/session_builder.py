"""
services/session_builder.py — SessionBuilder Service

Executes the deterministic session creation pipeline:
  1. Reads user choices (Personality, Goal, Mode, Assessment, Difficulty, Length).
  2. Fetches/extracts persistent KnowledgeGraph from SQLite DB.
  3. Calls CurriculumBuilder to select concept nodes deterministically on Backend.
  4. Creates & persists LearningSession DB record (WITHOUT calling Gemini).
"""

import logging
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.tutor_session import TutorSession
from app.services.knowledge_graph_service import KnowledgeGraphService
from app.services.curriculum_builder import CurriculumBuilder

logger = logging.getLogger(__name__)


class SessionBuilder:

    @classmethod
    def create_learning_session(
        cls,
        db: Session,
        user_id: int,
        document_id: int,
        personality: str = "Socratic Tutor",
        goal: str = "General Learning",
        learning_mode: str = "Teach Me",
        assessment_type: str = "Mixed",
        difficulty: str = "Intermediate",
        session_length: str = "60 min"
    ) -> Tuple[TutorSession, Dict[str, Any]]:
        """
        Creates a LearningSession object and deterministically selects the curriculum.
        Do NOT call Gemini here.
        """
        # 1. Fetch persistent KnowledgeGraph
        graph = KnowledgeGraphService.get_or_create_graph(db, document_id)
        nodes_dicts = KnowledgeGraphService.get_nodes_as_dicts(graph)

        # 2. Call CurriculumBuilder (Backend selects concepts)
        curriculum = CurriculumBuilder.build_curriculum(
            nodes=nodes_dicts,
            learning_mode=learning_mode,
            target_goal=goal,
            difficulty=difficulty,
            session_length=session_length
        )

        selected_concept_ids = curriculum["selected_concept_ids"]
        learning_path = curriculum["learning_path"]

        first_concept = learning_path[0] if learning_path else graph.subject
        remaining_concepts = learning_path[1:] if len(learning_path) > 1 else []

        # 3. Create & Persist TutorSession DB record (No Gemini call!)
        session = TutorSession(
            user_id=user_id,
            document_id=document_id,
            subject=graph.subject,
            topic=first_concept,
            teacher_personality=personality,
            target_goal=goal,
            learning_mode=learning_mode,
            assessment_type=assessment_type,
            difficulty_level=3 if difficulty == "Intermediate" else (5 if difficulty == "Advanced" else 1),
            difficulty_name=difficulty,
            session_length=session_length,
            selected_topics=learning_path,
            current_concept=first_concept,
            remaining_concepts=remaining_concepts,
            status="active"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        logger.info("SessionBuilder: Created session ID=%d for user_id=%d on topic '%s'", session.id, user_id, first_concept)

        return session, curriculum
