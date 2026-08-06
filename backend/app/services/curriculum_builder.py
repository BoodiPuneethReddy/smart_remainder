"""
services/curriculum_builder.py — Deterministic Curriculum Selection Engine

The Backend decides WHAT to teach based on:
  - Extracted KnowledgeGraph nodes & metadata
  - User session selections (Learning Mode, Goal, Difficulty, Duration)
  - Student mastery & weak topics

Gemini NEVER chooses topics, node counts, or prerequisites.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class CurriculumBuilder:
    """
    Deterministic Curriculum Engine that selects target concepts and constructs
    a tailored learning path from an extracted KnowledgeGraph.
    """

    @staticmethod
    def parse_duration_minutes(session_length: str) -> int:
        """Parses duration string like '30 min', '15', '90 min' into integer minutes."""
        if not session_length:
            return 60
        cleaned = "".join([c for c in str(session_length) if c.isdigit()])
        try:
            val = int(cleaned)
            return val if val > 0 else 60
        except ValueError:
            return 60

    @classmethod
    def build_curriculum(
        cls,
        nodes: List[Dict[str, Any]],
        learning_mode: str = "Teach Me",
        target_goal: str = "General Learning",
        difficulty: str = "Intermediate",
        session_length: str = "60 min",
        mastery_score: float = 65.0
    ) -> Dict[str, Any]:
        """
        Determines the exact concept nodes and learning sequence for a session.
        """
        if not nodes:
            return {
                "selected_nodes": [],
                "selected_concept_ids": [],
                "learning_path": [],
                "time_budget_minutes": 60,
                "target_concept_count": 0,
                "strategy_summary": "Empty Knowledge Graph."
            }

        duration_mins = cls.parse_duration_minutes(session_length)
        total_available_nodes = len(nodes)

        # Estimate target concept count based on duration and mode
        if duration_mins <= 20:
            target_count = min(2, total_available_nodes)
        elif duration_mins <= 45:
            target_count = min(3, total_available_nodes)
        elif duration_mins <= 75:
            target_count = min(5, total_available_nodes)
        else:
            target_count = min(8, total_available_nodes)

        mode_clean = (learning_mode or "Teach Me").strip()

        # ── Mode-Specific Concept Selection Algorithms ────────────────────────

        if mode_clean in ["Revise", "Revision"]:
            # Sort by importance / exam weight descending; pick top high-yield nodes
            sorted_nodes = sorted(
                nodes,
                key=lambda n: (n.get("importance", 0.8), len(n.get("definitions", []))),
                reverse=True
            )
            selected = sorted_nodes[:target_count]
            strategy = f"Revise Mode: Selected top {len(selected)} high-yield exam concepts for {duration_mins}m rapid review."

        elif mode_clean in ["Challenge Me", "Challenge"]:
            # Sort by difficulty descending; pick hardest / edge-case concepts
            sorted_nodes = sorted(
                nodes,
                key=lambda n: (n.get("difficulty", 3), len(n.get("code_snippets", []))),
                reverse=True
            )
            selected = sorted_nodes[:target_count]
            strategy = f"Challenge Me Mode: Selected top {len(selected)} highest difficulty concepts (Tier 4-5) for advanced problem solving."

        elif mode_clean in ["Interview Me", "Interview"]:
            # Prioritize nodes with code_snippets, practical definitions, and technical depth
            sorted_nodes = sorted(
                nodes,
                key=lambda n: (
                    1.5 if n.get("code_snippets") or n.get("has_code") else 1.0,
                    n.get("importance", 0.75)
                ),
                reverse=True
            )
            selected = sorted_nodes[:target_count]
            strategy = f"Interview Me Mode: Selected {len(selected)} practical technical concepts for mock interview evaluation."

        elif mode_clean in ["Test Me", "Quiz"]:
            # Select balanced spread across topics with definition & code coverage
            selected = nodes[:target_count]
            strategy = f"Test Me Mode: Selected {len(selected)} concepts for questions-only assessment."

        else:  # "Teach Me" or "Mixed" (Default Sequential Learning Path)
            # Maintain foundational prerequisite order (Chapter 1 -> Chapter 2 -> ...)
            selected = nodes[:target_count]
            strategy = f"Teach Me Mode: Selected {len(selected)} sequential concepts in prerequisite order for {duration_mins}m session."

        selected_concept_ids = [
            n.get("node_key", n.get("id", f"node_{i}")) for i, n in enumerate(selected)
        ]
        learning_path = [n.get("title", f"Concept {i+1}") for i, n in enumerate(selected)]

        return {
            "selected_nodes": selected,
            "selected_concept_ids": selected_concept_ids,
            "learning_path": learning_path,
            "time_budget_minutes": duration_mins,
            "target_concept_count": len(selected),
            "strategy_summary": strategy
        }
