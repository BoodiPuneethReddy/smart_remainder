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
    
    if result.knowledge_graph:
        lines.append(f"I analyzed your uploaded document (**{result.knowledge_graph.subject}**).")
        lines.append("")
        lines.append(f"• **DocumentAgent**: Detected {len(result.knowledge_graph.concepts)} chapters/topics from your material.")

    if result.strategy:
        lines.append(f"• **StrategyAgent**: Selected an **{result.strategy.strategy_name.title()}** strategy because the document contains a structured syllabus with sequential concepts.")

    if result.plan:
        lines.append(f"• **PlannerAgent**: Created a study roadmap with {len(result.plan.items)} focus sessions.")

    if result.reflection:
        if result.reflection.is_valid:
            lines.append("• **ReflectionAgent**: Verified schedule feasibility and confirmed daily workload is balanced.")
        else:
            lines.append(f"• **ReflectionAgent**: Adjusted workload ceiling to protect study performance.")

    if result.analytics:
        lines.append(f"• **AnalyticsAgent**: Predicts completion with projected {result.analytics.predicted_exam_readiness}% readiness ({result.analytics.burnout_risk_level} burnout risk).")

    lines.append("")
    if result.plan and result.plan.items:
        top = result.plan.items[0]
        lines.append(f"**Your next action is:**")
        lines.append(f"Study **{top.title}** for **{top.recommended_minutes} minutes**.")
        lines.append("")
        lines.append("After that, I will automatically generate your adaptive review quiz.")

    return "\n".join(lines) or "Your dynamic AI study workspace is ready."
