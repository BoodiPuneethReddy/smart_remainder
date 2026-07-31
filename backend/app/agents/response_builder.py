"""
agents/response_builder.py — Final Response Builder.

Formats agent Pydantic payloads into natural language answers and UI workspace state structures.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.models import SwarmExecutionResult

logger = logging.getLogger(__name__)


def build_final_response(result: SwarmExecutionResult) -> str:
    """Formats swarm execution result into natural language response."""
    lines = []
    
    if result.strategy:
        lines.append(f"**Strategy Selected**: {result.strategy.strategy_name.title()} ({result.strategy.rationale})")
        lines.append("")

    if result.plan:
        lines.append("### 📅 Personalized Study Roadmap")
        for item in result.plan.items[:5]:
            lines.append(f"- **{item.title}** ({item.subject}) — `{item.recommended_minutes} mins` (Priority: {item.priority_score:.0f}/100)")
        lines.append("")

    if result.reflection:
        if result.reflection.is_valid:
            lines.append("✅ *Schedule verified by ReflectionAgent: Feasible and workload-balanced.*")
        else:
            lines.append(f"⚠️ *ReflectionAgent Guardrail*: {', '.join(result.reflection.warnings)}")
        lines.append("")

    if result.analytics:
        lines.append(f"📊 **Workload Insight**: {result.analytics.insights[0] if result.analytics.insights else 'Pace is optimal.'}")

    return "\n".join(lines) or "Your dynamic AI study workspace is ready."
