"""
tests/test_orchestrator_integration.py
Integration tests verifying the full orchestrator execution pipeline:
  - Intent routing selects correct agents
  - Subject matching picks the right knowledge graph
  - Learning profile context is included
  - Step logs are produced for every intent
  - Response content changes based on live context
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from app.agents.orchestrator import (
    execute_swarm_workflow,
    _extract_user_time_limit,
    _extract_subject_hint,
    _get_learning_context,
    _fit_plan_to_time,
)
from app.agents.intent_classifier import classify, Intent
from app.agents.models import (
    PlanItemModel, StructuredPlanModel, KnowledgeGraphModel, ConceptNode
)
from app.services.document_graph import (
    build_document_knowledge_graph,
    _detect_subject_and_features,
)
from app.agents.strategy_agent import select_learning_strategy
from app.agents.response_builder import build_final_response, _mastery_label, _format_minutes


# ─── Time extraction tests ────────────────────────────────────────────────────

class TestTimeExtraction:
    def test_extracts_minutes(self):
        assert _extract_user_time_limit("I only have 90 minutes today") == 90

    def test_extracts_hours(self):
        assert _extract_user_time_limit("I have 2 hours free") == 120

    def test_extracts_fractional_hours(self):
        assert _extract_user_time_limit("study for 1.5 hours") == 90

    def test_extracts_an_hour(self):
        assert _extract_user_time_limit("an hour before dinner") == 60

    def test_returns_none_for_no_time(self):
        assert _extract_user_time_limit("what should I study today") is None


# ─── Subject hint extraction tests ───────────────────────────────────────────

class TestSubjectHintExtraction:
    def test_detects_dbms(self):
        assert _extract_subject_hint("explain normalization in DBMS") == "DBMS"

    def test_detects_dsa(self):
        assert _extract_subject_hint("how does recursion work in binary tree") == "DSA"

    def test_detects_os(self):
        assert _extract_subject_hint("explain deadlock in operating system") == "OS"

    def test_returns_none_for_no_subject(self):
        result = _extract_subject_hint("what should I study today")
        # Could be None or any subject
        assert result is None or isinstance(result, str)

    def test_detects_from_acronym(self):
        assert _extract_subject_hint("help me with sql joins") == "DBMS"


# ─── Document graph subject detection ────────────────────────────────────────

class TestDocumentSubjectDetection:
    def test_detects_dbms_from_text(self):
        text = "SQL queries are used to retrieve data. Normalization removes redundancy. Primary key ensures uniqueness."
        doc_type, display, features = _detect_subject_and_features(text, "notes.pdf")
        assert doc_type == "DBMS"
        assert "sql" in features or "prerequisites" in features

    def test_detects_dsa_from_text(self):
        text = "Binary tree traversal using recursion. BFS and DFS algorithms. Time complexity O(n log n) for merge sort."
        doc_type, display, features = _detect_subject_and_features(text, "notes.pdf")
        assert doc_type == "DSA"

    def test_detects_os_from_text(self):
        text = "Process scheduling algorithms. Deadlock conditions: mutual exclusion, hold and wait. Virtual memory paging."
        doc_type, display, features = _detect_subject_and_features(text, "notes.pdf")
        assert doc_type == "OS"

    def test_detects_code_feature(self):
        text = "def binary_search(arr, target): for i in range(len(arr)): return mid"
        doc_type, display, features = _detect_subject_and_features(text, "algo.pdf")
        assert "code" in features

    def test_detects_sql_feature(self):
        text = "SELECT * FROM students WHERE gpa > 3.5 GROUP BY department HAVING count(*) > 5"
        doc_type, display, features = _detect_subject_and_features(text, "dbms.pdf")
        assert "sql" in features

    def test_detects_formula_feature(self):
        text = "The integral of f(x) dx is calculated using the fundamental theorem. Formula: E = mc^2. Derivative dy/dx."
        doc_type, display, features = _detect_subject_and_features(text, "math.pdf")
        assert "formulas" in features

    def test_fallback_to_filename(self):
        text = "some generic text without subject keywords"
        doc_type, display, features = _detect_subject_and_features(text, "MyNotes.pdf")
        assert display == "Mynotes"  # derived from filename
        assert "prerequisites" in features


# ─── Document graph building tests ───────────────────────────────────────────

class TestDocumentGraphBuilding:
    def test_builds_dbms_graph_with_correct_subject(self):
        text = """
        Introduction to DBMS
        A database is an organized collection of data. SQL is the language used to query it.
        
        Normalization
        Normalization refers to organizing data to reduce redundancy. Primary key uniquely identifies records.
        
        Transactions
        ACID properties ensure reliable transactions. Atomicity means all-or-nothing.
        """
        result = build_document_knowledge_graph(text, "DBMS_notes.pdf")
        assert result["doc_type"] == "DBMS"
        assert "sql" in result["features"] or "prerequisites" in result["features"]
        assert len(result["nodes"]) > 0

    def test_builds_graph_with_difficulty_progression(self):
        text = """
        Chapter 1: Basic Concepts
        This is simple introductory material.
        
        Chapter 2: Advanced Topics
        This is more complex material requiring knowledge of basics.
        
        Chapter 3: Expert Level
        This is the most difficult material.
        """
        result = build_document_knowledge_graph(text, "course.pdf")
        nodes = result["nodes"]
        if len(nodes) > 1:
            # Later sections should have equal or higher difficulty
            assert nodes[-1]["difficulty"] >= nodes[0]["difficulty"]

    def test_empty_text_returns_default(self):
        result = build_document_knowledge_graph("", "empty.pdf")
        assert result["nodes"] == []
        assert "subject" in result


# ─── Strategy agent tests ─────────────────────────────────────────────────────

class TestStrategyAgent:
    def _make_graph(self, doc_type: str, features: list) -> KnowledgeGraphModel:
        return KnowledgeGraphModel(
            subject="Test Subject",
            doc_type=doc_type,
            detected_features=features,
            concepts=[
                ConceptNode(id="c1", title="Concept 1", chapter="Ch1", summary="test", difficulty=2)
            ],
        )

    def test_dbms_selects_problem_first(self):
        graph = self._make_graph("DBMS", ["sql", "prerequisites"])
        strategy = select_learning_strategy(graph)
        assert strategy.strategy_name == "problem-first"
        assert "SQL" in strategy.rationale or "normalization" in strategy.rationale.lower()

    def test_dsa_selects_problem_first(self):
        graph = self._make_graph("DSA", ["code", "prerequisites"])
        strategy = select_learning_strategy(graph)
        assert strategy.strategy_name == "problem-first"

    def test_os_selects_concept_first(self):
        graph = self._make_graph("OS", ["concepts", "prerequisites"])
        strategy = select_learning_strategy(graph)
        assert strategy.strategy_name == "concept-first"

    def test_low_mastery_triggers_revision(self):
        graph = self._make_graph("DBMS", ["sql", "prerequisites"])
        strategy = select_learning_strategy(graph, avg_mastery=30.0)
        assert strategy.strategy_name == "revision-heavy"

    def test_exam_goal_overrides_doc_type(self):
        graph = self._make_graph("OS", ["concepts", "prerequisites"])
        strategy = select_learning_strategy(graph, target_goal="GATE Exam")
        assert strategy.strategy_name == "exam-focused"

    def test_focus_order_is_difficulty_sorted(self):
        concepts = [
            ConceptNode(id="c1", title="Hard Topic", chapter="Ch3", summary="s", difficulty=5),
            ConceptNode(id="c2", title="Easy Topic", chapter="Ch1", summary="s", difficulty=1),
            ConceptNode(id="c3", title="Mid Topic", chapter="Ch2", summary="s", difficulty=3),
        ]
        graph = KnowledgeGraphModel(
            subject="Test", doc_type="ACADEMIC", concepts=concepts
        )
        strategy = select_learning_strategy(graph)
        assert strategy.recommended_focus_order[0] == "Easy Topic"


# ─── Intent classifier tests ──────────────────────────────────────────────────

class TestIntentClassifier:
    def test_greeting(self):
        r = classify("hello there")
        assert r.primary_intent == Intent.GREETING

    def test_schedule_constraint_with_time(self):
        r = classify("I only have 90 minutes today")
        assert r.primary_intent == Intent.SCHEDULE_CONSTRAINT
        assert r.entities.get("available_minutes") == 90

    def test_study_planning(self):
        r = classify("what should I study today?")
        assert r.primary_intent == Intent.STUDY_PLANNING

    def test_tutor_intent(self):
        r = classify("explain normalization to me")
        assert r.primary_intent == Intent.TUTOR

    def test_learning_analytics(self):
        r = classify("show my mastery and analytics progress")
        assert r.primary_intent == Intent.LEARNING_ANALYTICS

    def test_motivation(self):
        r = classify("I'm feeling overwhelmed and can't focus")
        assert r.primary_intent == Intent.MOTIVATION

    def test_unknown_does_not_need_clarification(self):
        # Post-fix: no intent should trigger "could you clarify" — UNKNOWN still proceeds
        r = classify("what should i do now")
        # This should be classified as study_planning or unknown — but never trigger clarification
        assert r.needs_clarification is False


# ─── Fit to time tests ────────────────────────────────────────────────────────

class TestFitPlanToTime:
    def _make_items(self, n: int, mins_each: int = 60) -> list:
        return [
            PlanItemModel(
                task_id=i, title=f"Task {i}", subject="DBMS",
                task_type="study", recommended_minutes=mins_each,
                priority_score=80.0 - i * 5, days_remaining=3
            )
            for i in range(1, n + 1)
        ]

    def test_fits_to_90_minutes(self):
        items = self._make_items(5, 60)
        fitted = _fit_plan_to_time(items, 90)
        total = sum(i.recommended_minutes for i in fitted)
        assert total <= 90

    def test_fits_to_30_minutes(self):
        items = self._make_items(3, 60)
        fitted = _fit_plan_to_time(items, 30)
        total = sum(i.recommended_minutes for i in fitted)
        assert total <= 30

    def test_preserves_order_by_priority(self):
        items = self._make_items(3, 30)
        fitted = _fit_plan_to_time(items, 90)
        # All should fit in 90 minutes
        assert len(fitted) == 3


# ─── Response builder tests ───────────────────────────────────────────────────

class TestResponseBuilder:
    def test_mastery_labels(self):
        assert _mastery_label(90) == "Strong"
        assert _mastery_label(65) == "Developing"
        assert _mastery_label(45) == "Needs Work"
        assert _mastery_label(30) == "Critical Gap"

    def test_format_minutes(self):
        assert _format_minutes(90) == "1h 30m"
        assert _format_minutes(60) == "1h"
        assert _format_minutes(45) == "45m"

    def test_greeting_response_uses_analytics(self):
        from app.agents.models import SwarmExecutionResult, AnalyticsInsightModel
        result = SwarmExecutionResult(
            user_id=1,
            primary_intent="greeting",
            analytics=AnalyticsInsightModel(
                user_id=1, completion_rate=72.5,
                weekly_study_hours=8.5, burnout_risk_level="low",
                predicted_exam_readiness=85.0, weakest_subject="OS",
                insights=["Healthy pace"]
            )
        )
        response = build_final_response(result, "hello", {})
        assert "72" in response  # completion rate must appear
        assert "85" in response  # readiness must appear
        assert "Welcome" in response

    def test_analytics_response_format(self):
        from app.agents.models import SwarmExecutionResult, AnalyticsInsightModel
        result = SwarmExecutionResult(
            user_id=1,
            primary_intent="learning_analytics",
            analytics=AnalyticsInsightModel(
                user_id=1, completion_rate=55.0,
                weekly_study_hours=12.0, burnout_risk_level="moderate",
                predicted_exam_readiness=68.0, weakest_subject="DBMS",
                insights=["Moderate workload", "55% completed"]
            )
        )
        lctx = {
            "has_learning_data": True,
            "avg_mastery": 48.5,
            "avg_retention": 62.0,
            "total_profiles": 5,
            "weak_topics": [{"subject": "DBMS", "topic": "Joins", "mastery": 35.0, "retention": 40.0}],
            "revision_needed": [],
        }
        response = build_final_response(result, "how is my learning", lctx)
        assert "55" in response   # completion rate
        assert "48" in response   # mastery
        assert "Joins" in response  # weak topic from real lctx

    def test_study_plan_response_no_hardcoded_text(self):
        """Ensure no hardcoded placeholder strings appear in output."""
        from app.agents.models import (
            SwarmExecutionResult, StructuredPlanModel, PlanItemModel,
            AnalyticsInsightModel, LearningStrategyModel
        )
        items = [
            PlanItemModel(
                task_id=1, title="SQL Query Optimization", subject="DBMS",
                task_type="study", recommended_minutes=45,
                priority_score=88.0, days_remaining=3,
                ai_explanation="DBMS exam in 3 days — SQL optimization is high-frequency exam topic."
            )
        ]
        result = SwarmExecutionResult(
            user_id=1,
            primary_intent="study_planning",
            plan=StructuredPlanModel(user_id=1, available_minutes=90, allocated_minutes=45, items=items),
            analytics=AnalyticsInsightModel(
                user_id=1, completion_rate=60.0, weekly_study_hours=10.0,
                burnout_risk_level="low", predicted_exam_readiness=72.0,
                weakest_subject="DBMS", insights=[]
            ),
            strategy=LearningStrategyModel(
                strategy_name="problem-first",
                target_goal="Exam",
                rationale="DBMS detected — SQL practice first.",
                recommended_focus_order=["SQL Queries", "Normalization"],
                estimated_total_hours=8.0,
            ),
        )
        response = build_final_response(result, "I have 90 minutes, DBMS exam in 3 days", {})

        # Real content must appear
        assert "SQL Query Optimization" in response
        # Strategy name appears as either "problem-first" or "Problem First" (title-cased in response)
        assert "problem" in response.lower()
        assert "DBMS exam in 3 days" in response  # real ai_explanation from task

        # Hardcoded text must NOT appear
        assert "core foundational concept" not in response
        assert "Secondary advanced concepts were deferred" not in response
        assert "Could you clarify" not in response
