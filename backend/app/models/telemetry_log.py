"""
models/telemetry_log.py — Multi-Agent Swarm Telemetry & Grounding Persistence Model

Stores complete, un-truncated runtime telemetry for every user query:
  - Execution graph (active & skipped agents)
  - Memory before & memory after
  - Step logs (status, confidence, latency_ms, memory_read, memory_written)
  - Reflection audit JSON (violations, recommendations, attempt count)
  - Grounding telemetry report (knowledge_nodes_used, used_definitions, used_examples, used_sql, used_formulas)
  - Exact system prompt & raw Gemini response
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base


class SwarmTelemetryLog(Base):
    __tablename__ = "swarm_telemetry_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user = relationship("User", backref="swarm_telemetry_logs")

    query = Column(Text, nullable=False)
    intent = Column(String(50), nullable=False, index=True)
    subject = Column(String(100), nullable=True)

    # Runtime Execution Graph & Timing
    active_agents = Column(JSON, nullable=False)
    skipped_agents = Column(JSON, nullable=False)
    total_latency_ms = Column(Float, nullable=False)
    dynamic_confidence = Column(Float, nullable=False)

    # Shared Memory Evolution
    memory_before = Column(JSON, nullable=False)
    memory_after = Column(JSON, nullable=False)

    # Detailed Step Logs & Telemetry
    step_logs = Column(JSON, nullable=False)

    # Reflection Audit & Planner Data
    reflection_audit = Column(JSON, nullable=True)
    planner_output = Column(JSON, nullable=True)

    # Grounding Metadata & Citations
    grounding_report = Column(JSON, nullable=False)
    retrieved_nodes = Column(JSON, nullable=True)

    # Gemini Prompt & Response
    exact_prompt = Column(Text, nullable=True)
    raw_gemini_output = Column(Text, nullable=True)
    final_response = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<SwarmTelemetryLog id={self.id} user_id={self.user_id} intent={self.intent!r} latency={self.total_latency_ms}ms>"
