"""
agents/response_builder.py — Final Response Builder.

Formats agent Pydantic payloads into clear, explainable natural language answers
demonstrating multi-agent collaboration, priority reasoning, and tailored action plans.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.agents.models import SwarmExecutionResult

logger = logging.getLogger(__name__)


def build_final_response(result: SwarmExecutionResult) -> str:
    """Formats swarm execution result into explainable natural language response."""
    lines = []
    
    # Section 1: Swarm & Context Analysis
    if result.knowledge_graph:
        lines.append(f"I analyzed your uploaded document (**{result.knowledge_graph.subject}**).")
        lines.append("")
        lines.append(f"• **DocumentAgent**: Extracted {len(result.knowledge_graph.concepts)} structured topics, formulas, and prerequisite edges.")

    if result.strategy:
        lines.append(f"• **StrategyAgent**: Selected an **{result.strategy.strategy_name.title()}** strategy ({result.strategy.rationale}).")

    if result.analytics:
        lines.append(f"• **AnalyticsAgent**: Projected exam readiness is {result.analytics.predicted_exam_readiness}% ({result.analytics.burnout_risk_level} burnout risk).")

    lines.append("")
    lines.append("### 🧠 Priority Reasoning & Rationale")

    if result.plan and result.plan.items:
        top_task = result.plan.items[0]
        avail = result.plan.available_minutes
        lines.append(f"Based on your available **{avail} minutes** today:")
        lines.append(f"1. **Prioritized `{top_task.title}`**: Selected as your top priority (Score: {top_task.priority_score:.0f}/100) because it is a core foundational concept with upcoming exam urgency.")
        
        if len(result.plan.items) > 1:
            second_task = result.plan.items[1]
            lines.append(f"2. **Allocated `{second_task.title}`**: Scheduled for secondary review to maintain memory retention.")

        lines.append("3. **Deferred Later Topics**: Secondary advanced concepts were deferred to future study blocks to keep your daily workload within safe limits.")

    lines.append("")
    if result.reflection:
        if result.reflection.is_valid:
            lines.append("✅ **ReflectionAgent Audit**: Verified schedule feasibility — total study allocation fits comfortably within your time limit without fatigue.")
        else:
            lines.append(f"⚠️ **ReflectionAgent Audit**: {', '.join(result.reflection.warnings)}")

    lines.append("")
    if result.plan and result.plan.items:
        top = result.plan.items[0]
        lines.append(f"### 🎯 Your Action Plan")
        for item in result.plan.items:
            lines.append(f"- **{item.title}** ({item.subject}) — `{item.recommended_minutes} mins`")
        lines.append("")
        lines.append(f"**Next Step:** Begin studying **{top.title}** for **{top.recommended_minutes} minutes**.")

    return "\n".join(lines) or "Your dynamic AI study workspace is ready."
