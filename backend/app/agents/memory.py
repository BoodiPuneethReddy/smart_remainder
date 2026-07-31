"""
agents/memory.py — Shared Memory Layer for Collaborative Multi-Agent System.

Provides thread-safe access to structured state across agents:
  - active_goals
  - completed_goals
  - current_schedule (StructuredPlanModel)
  - knowledge_graphs (KnowledgeGraphModel)
  - active_strategy (LearningStrategyModel)
  - reflection_history (List[ReflectionValidationResult])
  - analytics_snapshots (AnalyticsInsightModel)
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, Any, Optional, List

from app.agents.models import (
    KnowledgeGraphModel,
    LearningStrategyModel,
    StructuredPlanModel,
    ReflectionValidationResult,
    AnalyticsInsightModel,
)

logger = logging.getLogger(__name__)


class SharedMemoryStore:
    """In-memory thread-safe shared memory store for agent state."""
    
    _instance: Optional[SharedMemoryStore] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._user_memory: Dict[int, Dict[str, Any]] = {}

    @classmethod
    def get_instance(cls) -> SharedMemoryStore:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = SharedMemoryStore()
        return cls._instance

    def _get_user_space(self, user_id: int) -> Dict[str, Any]:
        if user_id not in self._user_memory:
            self._user_memory[user_id] = {
                "active_goals": [],
                "completed_goals": [],
                "current_schedule": None,
                "knowledge_graphs": {},  # doc_id -> KnowledgeGraphModel
                "latest_graph": None,
                "active_strategy": None,
                "reflection_history": [],
                "analytics": None,
                "session_state": {},
            }
        return self._user_memory[user_id]

    def set_knowledge_graph(self, user_id: int, graph: KnowledgeGraphModel) -> None:
        with self._lock:
            space = self._get_user_space(user_id)
            if graph.document_id:
                space["knowledge_graphs"][graph.document_id] = graph
            space["latest_graph"] = graph
            logger.info("SharedMemory: Set KnowledgeGraph for user=%d subject=%r", user_id, graph.subject)

    def get_latest_graph(self, user_id: int) -> Optional[KnowledgeGraphModel]:
        with self._lock:
            return self._get_user_space(user_id).get("latest_graph")

    def set_strategy(self, user_id: int, strategy: LearningStrategyModel) -> None:
        with self._lock:
            space = self._get_user_space(user_id)
            space["active_strategy"] = strategy
            logger.info("SharedMemory: Set Strategy for user=%d strategy=%r", user_id, strategy.strategy_name)

    def get_strategy(self, user_id: int) -> Optional[LearningStrategyModel]:
        with self._lock:
            return self._get_user_space(user_id).get("active_strategy")

    def set_schedule(self, user_id: int, schedule: StructuredPlanModel) -> None:
        with self._lock:
            space = self._get_user_space(user_id)
            space["current_schedule"] = schedule
            logger.info("SharedMemory: Set Schedule for user=%d items=%d", user_id, len(schedule.items))

    def get_schedule(self, user_id: int) -> Optional[StructuredPlanModel]:
        with self._lock:
            return self._get_user_space(user_id).get("current_schedule")

    def add_reflection(self, user_id: int, reflection: ReflectionValidationResult) -> None:
        with self._lock:
            space = self._get_user_space(user_id)
            space["reflection_history"].append(reflection)
            logger.info("SharedMemory: Recorded Reflection for user=%d valid=%s", user_id, reflection.is_valid)

    def get_latest_reflection(self, user_id: int) -> Optional[ReflectionValidationResult]:
        with self._lock:
            history = self._get_user_space(user_id).get("reflection_history", [])
            return history[-1] if history else None

    def set_analytics(self, user_id: int, analytics: AnalyticsInsightModel) -> None:
        with self._lock:
            space = self._get_user_space(user_id)
            space["analytics"] = analytics

    def get_analytics(self, user_id: int) -> Optional[AnalyticsInsightModel]:
        with self._lock:
            return self._get_user_space(user_id).get("analytics")


def get_shared_memory() -> SharedMemoryStore:
    return SharedMemoryStore.get_instance()
