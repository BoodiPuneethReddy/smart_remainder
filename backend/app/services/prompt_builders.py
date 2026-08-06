"""
services/prompt_builders.py — Grounded & Adaptive Mentor Prompt Architecture

Dedicated prompt builders for Gemini AI Client & Multi-Agent Swarm.
Enforces strict grounding and adaptive tutoring strategy:
  - Beginner: Simple analogies, real-world examples, small check-in quizzes, avoid dense jargon.
  - Intermediate: Clear definitions, standard SQL examples, balanced theory & practice.
  - Advanced: Technical depth, edge cases, interview-style questions, query optimization.
"""

import json
from typing import Dict, Any, List


def _format_conversation_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return ""
    lines = ["CONVERSATION HISTORY (Recent turns with student):"]
    for turn in history[-4:]:
        sender = "Student" if turn.get("role") == "user" or turn.get("user_query") else "Mentor"
        content = turn.get("content", turn.get("user_query", "")).strip()
        lines.append(f"{sender}: {content}")
    lines.append("")
    return "\n".join(lines)


def build_tutor_prompt(context: Dict[str, Any]) -> str:
    """Builds Socratic tutoring prompt for concepts."""
    return build_grounded_mentor_prompt(context)


def build_planner_explanation_prompt(context: Dict[str, Any]) -> str:
    """Builds a natural mentor rationale for prioritized study schedules."""
    available_minutes = context.get("available_minutes", 240)
    user_time_str = f"{available_minutes // 60}h {available_minutes % 60}m" if available_minutes >= 60 else f"{available_minutes}m"
    tasks = context.get("tasks", [])

    prompt_lines = [
        "You are a personal academic study coach helping a student structure their study session.",
        f"Available Study Time Today: {user_time_str} ({available_minutes}m).",
        "",
        "RECOMMENDED SESSIONS:",
    ]
    for t in tasks:
        p_score = t.get('priority_score', 50)
        prompt_lines.append(f"  - {t.get('subject')} '{t.get('title')}': {t.get('recommended_minutes')}m (Priority: {int(p_score)}/100)")

    return "\n".join(prompt_lines)


def build_reflection_prompt(context: Dict[str, Any]) -> str:
    """Builds a plan feasibility audit prompt."""
    avail = context.get("available_minutes", 60)
    alloc = context.get("allocated_minutes", 90)
    return f"Audit plan feasibility: {alloc}m allocated vs {avail}m available budget."


def build_chat_recommendation_prompt(context: Dict[str, Any]) -> str:
    """Builds general chat recommendation prompt."""
    return build_grounded_mentor_prompt(context)


def build_document_analysis_prompt(text: str, filename: str) -> str:
    """Builds document extraction prompt."""
    return f"Analyze document text from '{filename}': {text[:300]}"


def build_grounded_mentor_prompt(context: Dict[str, Any]) -> str:
    """
    Constructs a minimized, strictly grounded, and adaptively tailored prompt for Gemini reasoning engine.
    """
    user_query = context.get("user_query", context.get("user_answer", ""))
    topic = context.get("topic", "")
    intent = context.get("intent", "general")
    subject = context.get("subject", "General Academic Study")
    history = context.get("history", [])
    learning_ctx = context.get("learning_ctx", {})
    retrieved_nodes = context.get("retrieved_nodes", [])
    kg_dict = context.get("knowledge_graph", {})
    if not retrieved_nodes and isinstance(kg_dict, dict) and kg_dict.get("nodes"):
        retrieved_nodes = kg_dict.get("nodes")

    plan = context.get("plan", {})
    reflection = context.get("reflection", {})
    analytics = context.get("analytics", {})
    mistakes = context.get("mistakes", [])

    mastery_pct = context.get("mastery", learning_ctx.get("mastery_score", 65.0))
    mastery_level = context.get("mastery_level", "Intermediate")
    if mastery_pct < 40:
        mastery_level = "Beginner"
    elif mastery_pct > 75:
        mastery_level = "Advanced"

    # Adaptive Pedagogy Guidance
    if mastery_level == "Beginner":
        adaptive_guidance = (
            "ADAPTIVE PEDAGOGY (BEGINNER TIER):\n"
            "• Use intuitive real-world analogies (e.g. library books, Excel sheets).\n"
            "• Provide concrete step-by-step examples before formal definitions.\n"
            "• Keep mathematical formulas minimal and explain every variable.\n"
            "• End with a lightweight 1-question check-in."
        )
    elif mastery_level == "Advanced":
        adaptive_guidance = (
            "ADAPTIVE PEDAGOGY (ADVANCED TIER):\n"
            "• Focus on technical depth, edge cases, and query optimization.\n"
            "• Present interview-style questions and system design tradeoffs.\n"
            "• Use formal relational algebra notation and SQL schema constraints.\n"
            "• Skip elementary analogies."
        )
    else:
        adaptive_guidance = (
            "ADAPTIVE PEDAGOGY (INTERMEDIATE TIER):\n"
            "• Provide clear definitions balanced with executable SQL code snippets.\n"
            "• Explain both core theory and practical database design implications.\n"
            "• Highlight common student misconceptions directly."
        )

    prompt_sections = [
        "================================================================================",
        "SYSTEM ROLE:",
        "You are a personal academic AI study mentor with perfect memory of this student's progress.",
        "Talk like ChatGPT or an expert professor in office hours: direct, empathetic, intelligent, and natural.",
        "",
        "GROUNDING DIRECTIVES (CRITICAL):",
        "1. Everything you state MUST originate strictly from the RETRIEVED KNOWLEDGE NODES, PLANNER OUTPUT, or LEARNING PROFILE below.",
        "2. Do NOT fabricate facts, invent unprovided exam dates, or guess missing concepts.",
        "3. Do NOT use template headers or mention internal agent names ('PlannerAgent', 'ReflectionAgent', 'DocumentAgent').",
        "",
        adaptive_guidance,
        "================================================================================",
        "",
        "CURRENT GOAL & CONTEXT:",
        f"  • User Query: \"{user_query}\"",
        f"  • Subject Focus: {subject}" + (f" | Topic: {topic}" if topic else ""),
        f"  • Intent: {intent}",
        f"  • Student Mastery Tier: {mastery_level} ({mastery_pct:.0f}%) | Retention: {context.get('retention', 100.0):.0f}%",
        "",
        "RECENT CONVERSATION HISTORY (Pruned):",
        _format_conversation_history(history),
        "",
    ]

    if mistakes:
        prompt_sections.append("PAST MISCONCEPTIONS TO ADDRESS:")
        for m in mistakes:
            prompt_sections.append(f"  - [{m.get('topic')}]: {m.get('mistake_summary')}")
        prompt_sections.append("")

    if retrieved_nodes:
        prompt_sections.append("RETRIEVED KNOWLEDGE GRAPH NODES (Top-5 Grounded Source):")
        for n in retrieved_nodes[:5]:
            prompt_sections.append(json.dumps({
                "citation_node_id": n.get("id", n.get("title")),
                "title": n.get("title"),
                "similarity_score": n.get("similarity_score", "100.0%"),
                "summary": n.get("summary"),
                "difficulty": n.get("difficulty", 3),
                "definitions": n.get("definitions", []),
                "examples": n.get("examples", []),
                "formulas": n.get("formulas", []),
                "code_snippets": n.get("code_snippets", []),
                "parents_prerequisites": n.get("parents", []),
                "children": n.get("children", [])
            }, indent=2))
        prompt_sections.append("")

    if plan:
        prompt_sections.append("PLANNER OUTPUT (Deterministic Schedule & Score Calculations):")
        prompt_sections.append(json.dumps(plan, indent=2))
        prompt_sections.append("")

    if reflection:
        prompt_sections.append("REFLECTION AUDIT (Feasibility & Quality Verification):")
        prompt_sections.append(json.dumps(reflection, indent=2))
        prompt_sections.append("")

    if analytics and intent != "greeting":
        comp_rate = analytics.get("completion_rate", 75.0)
        prompt_sections.append(f"ANALYTICS SUMMARY (Completion Rate: {comp_rate:.0f}%):")
        prompt_sections.append(json.dumps(analytics, indent=2))
        prompt_sections.append("")

    prompt_sections.append("TASK:")
    prompt_sections.append("Generate a helpful, grounded Markdown response directly addressing the user query.")

    return "\n".join(prompt_sections)
